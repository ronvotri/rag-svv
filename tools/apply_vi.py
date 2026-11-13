#!/usr/bin/env python3
"""Áp dụng bản dịch Việt vào I2Languages của bản mod Ragnarok Survivors đã build.

Không thay đổi mã nguồn upstream, ROMFS gốc hay số liệu gameplay.
Chỉ tương thích định dạng I2Languages/Unity đã được upstream kiểm tra ở VS 1.15.113.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import unicodedata

PT_BR_SLOT = 5
ROOT = Path(__file__).resolve().parents[1]


def load_translations(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict) or not data:
        raise ValueError("Bảng dịch phải là một JSON object không rỗng.")
    result = {}
    for key, value in data.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Khóa I2 không hợp lệ.")
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Bản dịch của {key!r} không hợp lệ.")
        result[key] = unicodedata.normalize("NFC", value)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Áp dụng bản Việt vào I2Languages (slot PT-BR 5).")
    parser.add_argument("--upstream", required=True, type=Path,
                        help="Thư mục clone type0labs-dev/ragnarok-survivors")
    parser.add_argument("--data", required=True, type=Path,
                        help="Tệp Data/data.unity3d của bản mod đã build, KHÔNG phải bản game gốc")
    parser.add_argument("--translations", type=Path, default=ROOT / "locales" / "vi-VN.json")
    parser.add_argument("--dry-run", action="store_true", help="Đếm khóa khớp, không ghi tệp")
    args = parser.parse_args()

    upstream_tools = args.upstream.expanduser().resolve() / "tools"
    data_path = args.data.expanduser().resolve()
    if not (upstream_tools / "unitypatch.py").is_file():
        parser.error("--upstream phải trỏ tới thư mục mã nguồn Ragnarok Survivors gốc.")
    if not data_path.is_file():
        parser.error(f"Không thấy file mod: {data_path}")

    translations = load_translations(args.translations)
    sys.path.insert(0, str(upstream_tools))
    from unitypatch import Bundle, I2Terms

    bundle = Bundle(str(data_path))
    seen = set()
    table_count = 0
    applied = 0
    for file_name, serialized in bundle.serialized():
        for obj in list(serialized.objects.values()):
            raw = obj.get_raw_data()
            if obj.type.name != "MonoBehaviour" or b"I2Languages" not in raw[:64]:
                continue
            table_count += 1
            table = I2Terms(raw)
            edits = 0
            for key, value in translations.items():
                entry = table.index.get(key)
                if entry is None or len(entry[2]) <= PT_BR_SLOT:
                    continue
                seen.add(key)
                if entry[2][PT_BR_SLOT] == value:
                    continue
                entry[2][PT_BR_SLOT] = value
                edits += 1
            if edits and not args.dry_run:
                bundle.replace_object(file_name, obj, table.save())
            applied += edits

    missing = sorted(set(translations) - seen)
    print(f"Bảng I2: {table_count}; khóa tìm thấy: {len(seen)}/{len(translations)}; chuỗi cần thay: {applied}")
    if missing:
        print("Khóa chưa khớp:", ", ".join(missing[:15]))
    if not table_count or not seen:
        raise RuntimeError("Không tìm thấy bảng I2 hay khóa Việt hóa phù hợp. Kiểm tra phiên bản và đường dẫn.")
    if args.dry_run:
        print("Dry-run: không thay đổi dữ liệu.")
        return 0
    if not applied:
        print("Không có thay đổi (có thể đã áp dụng trước đó).")
        return 0

    # Giữ đúng một bản gốc .bak; không chép dữ liệu game vào repo.
    backup = data_path.with_name(data_path.name + ".bak")
    if not backup.exists():
        shutil.copy2(data_path, backup)
    temp = data_path.with_name(data_path.name + ".vi.tmp")
    try:
        size = bundle.save(str(temp))
        if size <= 0:
            raise RuntimeError("Tệp đã vá không hợp lệ (0 byte).")
        temp.replace(data_path)
    finally:
        temp.unlink(missing_ok=True)
    print(f"Đã ghi {applied} chuỗi Việt: {data_path}")
    print(f"Bản sao trước vá: {backup}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"LỖI: {exc}", file=sys.stderr)
        raise SystemExit(1)
