#!/usr/bin/env python3
"""Audit recovered Midgard map and MVP wiring without copying publisher assets.

Run only against a temporarily recovered client. Emits a compact JSON inventory
of resource paths and function *names*, not source code or binary content.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

RELEVANT = ("map", "world", "mvp", "boss", "raid", "festival", "arena", "field")
FUNC = re.compile(r"(?m)^\s*(?:static\s+)?func\s+([A-Za-z_][A-Za-z_0-9]*)\s*\(")
# Extract identifiers solely from map-related script sources, not full scripts.
INTERESTING_SCRIPT_NAMES = ("world_select", "ro_map", "mvp_raid", "boss_brain", "raid_alerts", "game_data")
MAX_FILE_SIZE = 2_000_000


def inventory(root: Path) -> dict:
    if not (root / "project.godot").is_file():
        raise ValueError("Expected a recovered Godot project with project.godot")
    scene_paths = sorted(
        p.relative_to(root).as_posix()
        for folder in ("scenes", "assets")
        if (root / folder).exists()
        for p in (root / folder).rglob("*")
        if p.is_file() and p.suffix.lower() in (".tscn", ".scn", ".tres", ".res")
        and any(word in p.stem.lower() for word in RELEVANT)
    )
    scripts = {}
    for name in INTERESTING_SCRIPT_NAMES:
        matches = list((root / "scripts").rglob(name + ".gd")) if (root / "scripts").exists() else []
        for p in matches:
            if p.stat().st_size > MAX_FILE_SIZE:
                continue
            src = p.read_text(encoding="utf-8", errors="replace")
            functions = sorted(set(FUNC.findall(src)))
            scripts[p.relative_to(root).as_posix()] = {
                "functions": functions,
                "map_and_boss_entrypoints": [
                    f for f in functions if any(w in f.lower() for w in RELEVANT)
                ],
            }
    return {
        "schema": 1,
        "source": "recovered_client_inventory_only",
        "scene_candidates": scene_paths,
        "scene_candidate_count": len(scene_paths),
        "script_apis": scripts,
        "verified_playable_world_boss_map": False,
        "notes": [
            "Filename candidates do not prove a map is playable.",
            "Do not publish recovered scenes or source scripts.",
            "Verify map scene loading, player/AI spawn and boss AI before enabling gameplay.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recovered_project", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = inventory(args.recovered_project)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print("WORLD_BOSS_MAP_AUDIT " + json.dumps({
        "scene_candidates": report["scene_candidate_count"],
        "relevant_scripts": len(report["script_apis"]),
        "verified_playable": False,
    }))


if __name__ == "__main__":
    main()
