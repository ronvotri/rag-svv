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

# Inspect only selected native gameplay API *signatures*. These identify how
# World Boss is entered without shipping the publisher's game code/assets.
NATIVE_ENTRYPOINTS = {
    "scripts/core/main.gd": (
        "_load_map", "start_run", "start_world_boss", "start_festival",
        "enter_town", "leave_town",
    ),
    "scripts/core/world_boss.gd": (
        "_init", "_ready", "on_boss", "on_hit", "_finish", "time_left",
    ),
    "scripts/core/wb_portal.gd": (
        "_init", "_ask", "_show_boss", "_window_open",
    ),
    "scripts/core/mvp_raid.gd": (
        "supports", "in_arena", "open_portal", "_enter", "_build_arena",
        "_spawn_boss", "start_route", "leave", "reset",
    ),
    "scripts/core/boss_brain.gd": ("_init", "tick", "_start_attack"),
    "scripts/ro/ro_map.gd": ("load_map", "spawn_point", "_build_meadow"),
    "scripts/core/festival_run.gd": ("_init", "begin"),
    "scripts/core/raid_trials.gd": ("start", "owns", "pins_boss"),
    "scripts/autoload/game_data.gd": ("wb_locked", "wb_chest_items"),
}
ENTRYPOINT_RE = re.compile(r"(?m)^[ \\t]*(?:static[ \\t]+)?func[ \\t]+([A-Za-z_][A-Za-z_0-9]*)[ \\t]*\\(")


def api_signatures(source: str, wanted: tuple[str, ...]) -> dict:
    """Return only function parameter *declarations*, never bodies/defaults."""
    result = {}
    for match in ENTRYPOINT_RE.finditer(source):
        name = match.group(1)
        if name not in wanted or name in result:
            continue
        # GDScript permits nested parentheses in default arguments. Bound the
        # scan so malformed recovered text cannot cause an unbounded read.
        depth, raw, complete = 1, [], False
        for ch in source[match.end():match.end() + 2400]:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    complete = True
                    break
            raw.append(ch)
        if not complete:
            continue
        parts, current, inner = [], [], 0
        for ch in raw:
            if ch == "(":
                inner += 1
            elif ch == ")":
                inner -= 1
            if ch == "," and inner == 0:
                parts.append("".join(current))
                current = []
            else:
                current.append(ch)
        parts.append("".join(current))
        params = []
        required = 0
        for arg in parts:
            arg = arg.strip()
            if not arg:
                continue
            has_default = "=" in arg
            declaration = " ".join(arg.split("=", 1)[0].split())
            # Exclude literal default values and any unexpected syntax.
            if not re.fullmatch(r"[A-Za-z_]\\w*(?:\\s*:\\s*[A-Za-z_]\\w*(?:\\[[A-Za-z_0-9, \\t]+\\])?)?", declaration):
                declaration = "<complex_parameter>"
            params.append(declaration)
            if not has_default:
                required += 1
        result[name] = {"parameters": params, "required": required, "total": len(params)}
    return result


def native_contract(root: Path) -> dict:
    found = {}
    for relative, wanted in NATIVE_ENTRYPOINTS.items():
        path = root / relative
        if not path.is_file() or path.stat().st_size > MAX_FILE_SIZE:
            found[relative] = {"missing_file": True}
            continue
        signatures = api_signatures(path.read_text(encoding="utf-8", errors="replace"), wanted)
        found[relative] = {
            "methods": signatures,
            "missing_methods": sorted(set(wanted) - signatures.keys()),
        }
    return found



def inventory(root: Path) -> dict:
    if not (root / "project.godot").is_file():
        raise ValueError("Expected a recovered Godot project with project.godot")
    # Map content in this client may be data-driven instead of named scenes.
    # Inventory the full scene/resource counts as well as filename candidates.
    resources = [
        p for folder in ("scenes", "assets")
        if (root / folder).exists()
        for p in (root / folder).rglob("*")
        if p.is_file() and p.suffix.lower() in (".tscn", ".scn", ".tres", ".res")
    ]
    scene_paths = sorted(
        p.relative_to(root).as_posix() for p in resources
        if any(word in p.stem.lower() for word in RELEVANT)
    )
    resource_counts = {
        suffix: sum(p.suffix.lower() == suffix for p in resources)
        for suffix in (".tscn", ".scn", ".tres", ".res")
    }
    # Bounded path hints help identify generic game scene names without
    # exporting scene contents or making assumptions about playability.
    scene_hints = sorted(
        p.relative_to(root).as_posix() for p in resources
        if p.suffix.lower() in (".tscn", ".scn")
    )[:150]
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
        "scene_hints": scene_hints,
        "resource_extension_counts": resource_counts,
        "scene_candidate_count": len(scene_paths),
        "script_apis": scripts,
        "native_world_boss_contract": native_contract(root),
        "verified_playable_world_boss_map": False,
        "notes": [
            "No filename match does not mean zero maps: map rendering may be data-driven.",
            "Filename candidates do not prove a map is playable.",
            "Do not publish recovered scenes or source scripts.",
            "Verify map scene loading, player/AI spawn and boss AI before enabling gameplay.",
            "Native method signatures are metadata only; they are not proof offline World Boss is playable.",
            "Do not bypass official network checks or use publisher-only rewards.",
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
