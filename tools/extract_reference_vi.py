#!/usr/bin/env python3
"""Extract Vietnamese I2 text from a legally obtained Vampire Survivors Switch translation patch.

Outputs a private JSON to use as translation *reference*, not a repackaged game.
The supplied 1.16.100 reference uses language index 0 for Vietnamese.
Requires the upstream Ragnarok Survivors checkout and its Python dependencies.
"""
import argparse
import json
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract I2 translation strings from a UnityFS data.unity3d.")
    parser.add_argument("--upstream", required=True, type=Path, help="Local clone of type0labs-dev/ragnarok-survivors")
    parser.add_argument("--data", required=True, type=Path, help="Input patched 1.16.100 data.unity3d")
    parser.add_argument("--out", type=Path, default=ROOT / "work" / "source-vi.private.json")
    parser.add_argument("--slot", type=int, default=0, help="Source language index (Vietnamese patch: 0)")
    args = parser.parse_args()

    lib = args.upstream.expanduser().resolve() / "tools"
    if not (lib / "unitypatch.py").is_file():
        parser.error("Cannot find upstream tools/unitypatch.py: check --upstream")
    src = args.data.expanduser().resolve()
    if not src.is_file():
        parser.error(f"Source file not found: {src}")
    if args.slot < 0:
        parser.error("--slot must be >= 0")
    dest = args.out.expanduser().resolve()
    if src == dest:
        parser.error("--out must not overwrite --data")

    sys.path.insert(0, str(lib))
    from unitypatch import Bundle, I2Terms

    bundle = Bundle(str(src))
    result = {}
    table_count = 0
    all_keys = 0
    for _, assets in bundle.serialized():
        for obj in assets.objects.values():
            if obj.type.name != "MonoBehaviour":
                continue
            raw = obj.get_raw_data()
            if b"I2Languages" not in raw[:64]:
                continue
            table_count += 1
            terms = I2Terms(raw)
            for key, _, langs, _, _ in terms.terms:
                all_keys += 1
                if len(langs) <= args.slot or not langs[args.slot].strip():
                    continue
                if key in result and result[key] != langs[args.slot]:
                    raise ValueError(f"Ambiguous duplicate I2 key: {key}")
                result[key] = unicodedata.normalize("NFC", langs[args.slot])

    if not table_count or not result:
        raise RuntimeError("No I2Languages text found: wrong file, version or slot.")
    if "lang/menu_start" not in result:
        raise RuntimeError("Expected I2 anchor 'lang/menu_start' is absent; check source file.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Source I2 tables: {table_count}; total keys: {all_keys}; nonempty translations: {len(result)}")
    print(f"Saved private reference: {dest}")
    print("IMPORTANT: do not publish third-party translation data without permission.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
