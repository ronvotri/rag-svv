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
        "enter_town", "leave_town", "spawn_enemy", "damage_enemy",
        "clear_battlefield",
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
    "scripts/core/enemy.gd": ("_init", "setup", "_show_look", "hurt", "die"),
    "scripts/ro/ro_map.gd": ("load_map", "spawn_point", "_build_meadow"),
    "scripts/core/festival_run.gd": ("_init", "begin"),
    "scripts/core/raid_trials.gd": ("start", "owns", "pins_boss"),
    "scripts/autoload/game_data.gd": ("wb_locked", "wb_chest_items"),
}
ENTRYPOINT_RE = re.compile(r"(?m)^[ \t]*(?:static[ \t]+)?func[ \t]+([A-Za-z_][A-Za-z_0-9]*)[ \t]*\(")


def api_signatures(source: str, wanted: tuple[str, ...]) -> dict:
    """Return only function parameter *declarations*, never bodies/defaults."""
    result = {}
    # Mask prose before finding headers, so a multiline help string cannot
    # masquerade as an API declaration. Offsets remain stable after masking.
    for match in ENTRYPOINT_RE.finditer(_masked_gd_code(source)):
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
            if not re.fullmatch(r"[A-Za-z_]\w*(?:\s*:\s*[A-Za-z_]\w*(?:\[[A-Za-z_0-9, \t]+\])?)?", declaration):
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



# Read-only, allowlisted call-flow hints for the recovered native client.
# These are discovery signals, not evidence that local rewards/save are safe.
FLOW_TARGETS = {
    "scripts/core/main.gd": ("start_world_boss", "start_run", "_load_map",
                             "spawn_enemy", "damage_enemy", "clear_battlefield"),
    "scripts/core/world_boss.gd": ("_init", "on_boss", "on_hit", "_finish"),
    "scripts/core/enemy.gd": ("setup", "hurt", "die"),
    "scripts/core/wb_portal.gd": ("_show_boss",),
    "scripts/core/mvp_raid.gd": (
        "start_route", "_enter", "_build_arena", "_spawn_boss", "on_boss_killed",
    ),
    "scripts/ro/ro_map.gd": ("load_map", "spawn_point"),
    "scripts/autoload/game_data.gd": ("wb_locked", "wb_chest_items"),
}
# Only static, preapproved labels can enter an artifact. No discovered token,
# argument, literal, recovered source line or file body is ever exported.
FLOW_CALL_PROBES = {
    "world_boss_constructor": r"\bWorldBoss\s*\.\s*new\s*\(",
    "enemy_constructor": r"\bEnemy\s*\.\s*new\s*\(",
    "boss_brain_constructor": r"\bBossBrain\s*\.\s*new\s*\(",
    "spawn_enemy": r"\bspawn_enemy\s*\(",
    "damage_enemy": r"\bdamage_enemy\s*\(",
    "mvp_raid_constructor": r"\bMvpRaid\s*\.\s*new\s*\(",
    "start_world_boss": r"\bstart_world_boss\s*\(",
    "start_run": r"\bstart_run\s*\(",
    "load_map": r"\b(?:_load_map|load_map)\s*\(",
    "spawn_point": r"\bspawn_point\s*\(",
    "start_route": r"\bstart_route\s*\(",
    "open_portal": r"\bopen_portal\s*\(",
    "build_arena": r"\b_build_arena\s*\(",
    "spawn_boss": r"\b_spawn_boss\s*\(",
    "boss_killed": r"\bon_boss_killed\s*\(",
    "world_boss_finish": r"\b_finish\s*\(",
    "wb_locked": r"\bwb_locked\s*\(",
    "wb_chest_items": r"\bwb_chest_items\s*\(",
    "save_setting_write": r"\bSave\s*\.\s*set_setting\s*\(",
    "save_flush": r"\bSave\s*\.\s*flush\s*\(",
    "run_save_write": r"\bRunSave\s*\.\s*save\s*\(",
    "official_zeny_write": r"\b(?:Save\s*\.\s*add_zeny|add_zeny)\s*\(",
}
FLOW_RISK_PROBES = {
    "save_reference": r"\b(?:Save|RunSave)\s*\.",
    "network_reference": r"\b(?:NetSync|Net|RelayNet|EosNet|WorldChat)\s*\.",
    "reward_reference": r"\b(?:reward|rewards|loot|chest|claim|zeny|exp|xp)\w*\b",
    "ranking_reference": r"\b(?:ranking|leaderboard|rankings)\w*\b",
    "profile_reference": r"\b(?:profile|account|cloud_save)\w*\b",
}
# Mask strings first, then strip comments. Only code is checked; e.g. a help
# string containing 'Save.flush()' must never produce a false save cue.
GD_LITERAL = re.compile(
    r"(?s)\"\"\".*?\"\"\"|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'"
)


def _masked_gd_code(source: str) -> str:
    literals_masked = GD_LITERAL.sub(
        lambda m: "".join("\n" if c == "\n" else " " for c in m.group()), source
    )
    return re.sub(r"#[^\n]*", lambda m: " " * len(m.group()), literals_masked)


def method_flow_hints(source: str, wanted: tuple[str, ...]) -> dict:
    """Summarize allowlisted symbols inside method bodies only."""
    # Header detection must use masked text; preserve its original offsets.
    headers = list(ENTRYPOINT_RE.finditer(_masked_gd_code(source)))
    found = {}
    for index, entry in enumerate(headers):
        name = entry.group(1)
        if name not in wanted or name in found:
            continue
        end = headers[index + 1].start() if index + 1 < len(headers) else len(source)
        first_newline = source.find("\n", entry.start(), end)
        if first_newline < 0:
            continue
        body = _masked_gd_code(source[first_newline + 1:end])
        found[name] = {
            "call_cues": sorted(
                label for label, pattern in FLOW_CALL_PROBES.items()
                if re.search(pattern, body)
            ),
            "review_signals": sorted(
                label for label, pattern in FLOW_RISK_PROBES.items()
                if re.search(pattern, body, re.IGNORECASE)
            ),
        }
    return found


def native_flow_metadata(root: Path) -> dict:
    targets = {}
    for relative, wanted in FLOW_TARGETS.items():
        path = root / relative
        if not path.is_file() or path.stat().st_size > MAX_FILE_SIZE:
            targets[relative] = {"missing_file": True}
            continue
        observed = method_flow_hints(
            path.read_text(encoding="utf-8", errors="replace"), wanted
        )
        targets[relative] = {
            "methods": observed,
            "missing_methods": sorted(set(wanted) - observed.keys()),
        }
    return {
        "metadata_only": True,
        "methods": targets,
        "gates": {
            "native_runtime_boss_playtested": False,
            "offline_party_spawn_playtested": False,
            "world_boss_rendered_in_map": False,
            "native_spawn_api_runtime_verified": False,
            "offline_save_and_reward_isolation_verified": False,
            "safe_to_enable": False,
        },
    }


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
        "native_world_boss_flow": native_flow_metadata(root),
        "verified_playable_world_boss_map": False,
        "notes": [
            "No filename match does not mean zero maps: map rendering may be data-driven.",
            "Filename candidates do not prove a map is playable.",
            "Do not publish recovered scenes or source scripts.",
            "Verify map scene loading, player/AI spawn and boss AI before enabling gameplay.",
            "Native method signatures are metadata only; they are not proof offline World Boss is playable.",
            "Call cues and review signals are a conservative static scan, not an assurance of safe writes.",
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
    flow = report["native_world_boss_flow"]
    main_flow = flow["methods"].get("scripts/core/main.gd", {}).get("methods", {})
    boss_flow = flow["methods"].get("scripts/core/world_boss.gd", {}).get("methods", {})
    mvp_flow = flow["methods"].get("scripts/core/mvp_raid.gd", {}).get("methods", {})
    native = report["native_world_boss_contract"]
    world_methods = native.get("scripts/core/main.gd", {}).get("methods", {})
    enemy_methods = native.get("scripts/core/enemy.gd", {}).get("methods", {})
    print("WORLD_BOSS_FLOW_AUDIT " + json.dumps({
        "start_world_boss_calls": main_flow.get("start_world_boss", {}).get("call_cues", []),
        "native_boss_finish_review": boss_flow.get("_finish", {}).get("review_signals", []),
        "world_boss_init_calls": boss_flow.get("_init", {}).get("call_cues", []),
        "mvp_route_calls": mvp_flow.get("start_route", {}).get("call_cues", []),
        "spawn_enemy_contract_present": "spawn_enemy" in world_methods,
        "enemy_setup_contract_present": "setup" in enemy_methods,
        "safe_to_enable": flow["gates"]["safe_to_enable"],
    }), flush=True)
    print("WORLD_BOSS_MAP_AUDIT " + json.dumps({
        "scene_candidates": report["scene_candidate_count"],
        "relevant_scripts": len(report["script_apis"]),
        "verified_playable": False,
    }))


if __name__ == "__main__":
    main()
