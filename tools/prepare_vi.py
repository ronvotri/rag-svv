#!/usr/bin/env python3
"""Combine a locally extracted Vietnamese reference with RAG-SVV curated translations.

Default mode is conservative: only import 'lang/' menu/UI strings from the
Vampire Survivors translation, then apply RAG-SVV overrides for Ragnarok names.
'--mode all' enables all translated categories for manual review, not final QA.
"""
import argparse
import json
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]


def read_map(path: Path) -> dict[str, str]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"Expected a key-to-string JSON object: {path}")
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in obj.items()):
        raise ValueError(f"All I2 keys and values must be text: {path}")
    return {k: unicodedata.normalize("NFC", v) for k, v in obj.items() if v.strip()}


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge private VI reference with curated Ragnarok Vietnamese terms.")
    ap.add_argument("--source", type=Path, default=ROOT / "work" / "source-vi.private.json",
                    help="Locally extracted reference from Vampire Survivors 1.16.100")
    ap.add_argument("--overrides", type=Path, default=ROOT / "locales" / "vi-VN.json",
                    help="Reviewed Ragnarok-specific translation overrides")
    ap.add_argument("--out", type=Path, default=ROOT / "work" / "vi-merged.private.json")
    ap.add_argument("--mode", choices=("ui", "all"), default="ui",
                    help="ui = import only lang/ shared UI strings (recommended); all = every source term")
    args = ap.parse_args()

    source = read_map(args.source)
    overrides = read_map(args.overrides)
    if args.mode == "ui":
        selected = {k: v for k, v in source.items() if k.startswith("lang/")}
    else:
        selected = dict(source)
    # 'lang/intro_start' in the supplied patch is translator credits rather than a
    # start instruction. Keep original translator credit in README, not as UI text.
    selected.pop("lang/intro_start", None)

    collisions = len(set(selected).intersection(overrides))
    selected.update(overrides)
    if not selected:
        raise RuntimeError("No strings selected.")
    out = args.out.expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(selected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Reference strings: {len(source)}; selected {args.mode}: {len(selected) - len(overrides) + collisions}")
    print(f"Overrides: {len(overrides)}; collisions overridden: {collisions}; final strings: {len(selected)}")
    print(f"Saved (private): {out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
