#!/usr/bin/env python3
"""Inventory a standalone Godot PCK without extracting or executing its contents.

Uses Python's standard library. Encrypted directories are intentionally unsupported.
The JSON output contains metadata and filenames, never resource payloads or secrets.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct
import sys
from typing import BinaryIO


def read_exact(stream: BinaryIO, length: int) -> bytes:
    result = stream.read(length)
    if len(result) != length:
        raise ValueError("PCK bị cắt ngắn hoặc mục lục không hợp lệ.")
    return result


def u32(stream: BinaryIO) -> int:
    return struct.unpack("<I", read_exact(stream, 4))[0]


def u64(stream: BinaryIO) -> int:
    return struct.unpack("<Q", read_exact(stream, 8))[0]


def inspect(path: Path) -> dict:
    file_size = path.stat().st_size
    with path.open("rb") as stream:
        if read_exact(stream, 4) != b"GDPC":
            raise ValueError("Cần tệp PCK độc lập bắt đầu bằng GDPC.")
        version = u32(stream)
        if version not in (2, 3, 4):
            raise ValueError(f"Chưa hỗ trợ định dạng PCK {version}.")
        engine = [u32(stream) for _ in range(3)]
        flags = u32(stream)
        if flags & 1:
            raise ValueError("Mục lục được mã hóa; công cụ không giải mã.")
        if flags & ~2:
            raise ValueError(f"Cờ PCK chưa hỗ trợ: {flags:#x}.")
        file_base = u64(stream)
        if version >= 3:
            directory_offset = u64(stream)
        else:
            read_exact(stream, 16 * 4)
            directory_offset = stream.tell()
        if not 0 <= directory_offset <= file_size - 4:
            raise ValueError("Vị trí mục lục nằm ngoài tệp.")
        stream.seek(directory_offset)
        count = u32(stream)
        if count > 1_000_000:
            raise ValueError("Số tài nguyên vượt giới hạn an toàn.")
        entries = []
        for _ in range(count):
            path_length = u32(stream)
            if path_length == 0 or path_length > 65_536:
                raise ValueError("Độ dài tên tài nguyên không hợp lệ.")
            name = read_exact(stream, path_length).rstrip(b"\0").decode("utf-8")
            normalized = name.removeprefix("res://")
            if "\0" in name or "\\" in name or ":" in normalized:
                raise ValueError("Tên tài nguyên không hợp lệ.")
            resource_path = PurePosixPath(normalized)
            if resource_path.is_absolute() or ".." in resource_path.parts:
                raise ValueError("Tên tài nguyên chứa đường dẫn không an toàn.")
            offset = u64(stream) + file_base
            size = u64(stream)
            digest = read_exact(stream, 16).hex()
            entry_flags = u32(stream)
            if entry_flags:
                raise ValueError("Tài nguyên có cờ mã hóa/đặc biệt chưa hỗ trợ.")
            if offset > file_size or size > file_size - offset:
                raise ValueError("Tài nguyên nằm ngoài tệp PCK.")
            entries.append({"path": name, "offset": offset, "size": size, "md5": digest, "flags": entry_flags})
        stream.seek(0)
        sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
    extension_counts = Counter(PurePosixPath(entry["path"]).suffix or "(none)" for entry in entries)
    return {
        "source_name": path.name,
        "size": file_size,
        "sha256": sha256,
        "pack_version": version,
        "godot_version": ".".join(map(str, engine)),
        "pack_flags": flags,
        "file_base": file_base,
        "directory_offset": directory_offset,
        "file_count": count,
        "extensions": dict(extension_counts.most_common()),
        "entries": entries,
    }


def main() -> None:
    for console in (sys.stdout, sys.stderr):
        if hasattr(console, "reconfigure"):
            console.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pck", type=Path, help="Tệp .pck cần kiểm kê (chỉ đọc)")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "work" / "client-inventory.private.json")
    args = parser.parse_args()
    try:
        source = args.pck.resolve(strict=True)
        destination = args.output.resolve()
        if destination == source:
            raise ValueError("Đầu ra không được ghi đè tệp PCK nguồn.")
        if destination.exists():
            raise ValueError("Tệp đầu ra đã tồn tại; hãy chọn tên khác để giữ bản kiểm kê cũ.")
        result = inspect(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents an accidental overwrite after validation.
        with destination.open("x", encoding="utf-8") as output:
            json.dump(result, output, ensure_ascii=False, indent=2)
        print(f"Godot {result['godot_version']} / PCK v{result['pack_version']}: {result['file_count']:,} resources")
        print(f"SHA-256: {result['sha256']}")
        print(f"Inventory: {destination}")
    except (OSError, ValueError, UnicodeError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
