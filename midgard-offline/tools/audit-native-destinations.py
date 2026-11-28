#!/usr/bin/env python3
"""Discover the original nearQ destination UI and activity routes without exporting source.

The contract is an isolated review aid, not permission to call online services.
The known menus.gd show_teleporter contract is validated against actual
card-builder and route references, rather than depending on localized prose.
"""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import re
import tempfile

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("boss_audit", ROOT / "audit-world-boss-maps.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

LABELS = {
    "training": re.compile(r"\b(?:training|practice|test dummy|damage test)\b", re.I),
    "festival": re.compile(r"\bemperium festival\b", re.I),
    "world_boss": re.compile(r"\bworld boss\b", re.I),
    "destinations": re.compile(r"\bdestinations?\b", re.I),
    "nearq": re.compile(r"\bnearq\b", re.I),
}
ROUTE_NAMES = re.compile(r"training|practice|dummy|festival|emperium|world_boss|nearq|destination|teleport|daily|build", re.I)
CALL_NAMES = re.compile(r"\b(?:[A-Za-z_]\w*\.)?([A-Za-z_]\w*)\s*\(")
ASSET_ID = re.compile(r"^(?:training|practice|dummy|emperium|festival|comodo)[a-z0-9_]*$", re.I)

def inspect(root: Path) -> dict:
    candidates, routes, ids, scripts, callers, teleporter = [], [], set(), [], [], None
    for path in sorted((root / "scripts").rglob("*.gd")):
        if path.stat().st_size > base.MAX_FILE_SIZE:
            continue
        relative = path.relative_to(root).as_posix()
        source = path.read_text(encoding="utf-8", errors="replace")
        masked = base._masked_gd_code(source)
        # Only top-level instance/static methods, not anonymous inner callbacks.
        headers = list(re.finditer(r"(?m)^(static\s+)?func\s+([A-Za-z_]\w*)\s*\(", masked))
        for index, header in enumerate(headers):
            name = header.group(2)
            end = headers[index + 1].start() if index + 1 < len(headers) else len(source)
            body = source[header.start():end]
            code = masked[header.start():end]
            literals = [m.group(0) for m in base.GD_LITERAL.finditer(body)]
            labels = sorted(key for key, pattern in LABELS.items() if any(pattern.search(lit) for lit in literals))
            for lit in literals:
                value = lit.strip("\"'")
                if ASSET_ID.fullmatch(value):
                    ids.add(value)
            if name != "show_teleporter" and re.search(r"\bshow_teleporter\b", code):
                callers.append({"script": "res://" + relative, "method": name})
            interesting = ROUTE_NAMES.search(name) or ("festival" in labels and "world_boss" in labels)
            if not interesting:
                continue
            sig = base.api_signatures(source, (name,)).get(name, {})
            if not sig:
                continue
            calls = sorted(set(CALL_NAMES.findall(code)) - {name})
            calls = [call for call in calls if ROUTE_NAMES.search(call) or call in (
                "start_run", "leave_town", "enter_town", "show_loading", "set_stage",
                "spawn_enemy", "show_dialog", "show_menu", "show_end", "add_zeny",
                "flush", "connect", "bind", "close", "eos", "send", "request",
                "is_coop", "clear_battlefield", "set_setting", "load_map",
                "is_online", "is_connected", "get_build", "load_build",
            )][:40]
            row = {"script": "res://" + relative, "method": name,
                   "static": bool(header.group(1)), **sig, "labels": labels,
                   "calls": calls,
                   "network_cue": bool(re.search(r"\b(?:net|eos|cloud|leaderboard|ranking|relay)\b", code, re.I)),
                   "save_cue": bool(re.search(r"\b(?:Save|RunSave)\s*\.", code)),
                   "button_connection": bool(re.search(r"\bpressed\s*\.\s*connect\s*\(", code))}
            if relative == "scripts/ui/menus.gd" and name == "show_teleporter":
                refs = ["_teleport_card", "show_training_setup", "show_festival", "show_world_boss"]
                row["native_route_references"] = [item for item in refs if re.search(r"\b" + re.escape(item) + r"\b", code)]
                teleporter = row
            if "festival" in labels and "world_boss" in labels and (
                    "training" in labels or "destinations" in labels):
                candidates.append(row)
            if ROUTE_NAMES.search(name):
                routes.append(row)
        if re.search(r"nearq|festival|training|dummy|emperium", path.stem, re.I):
            scripts.append(relative)
    # We intentionally refuse uncertain owners, static methods and required
    # arguments. Do not guess a build index, online state, or a callback.
    # Actual UI inventory from the earlier client identifies this owner/method.
    # Confirm it on the pinned 0.2.11 client, including the card builder.
    # Do not choose an unrelated dialog merely because it mentions all labels.
    selected = None
    if teleporter is not None and not teleporter["static"] and teleporter["required"] == 0:
        refs = set(teleporter["native_route_references"])
        if "_teleport_card" in refs and len(refs & {"show_training_setup", "show_festival", "show_world_boss"}) >= 2:
            selected = teleporter
    return {"schema": 2, "candidate_count": len(candidates),
            "known_teleporter_contract": teleporter, "native_teleporter_callers": callers[:30],
            "menu_candidates": candidates[:30], "selected_native_menu": selected,
            "activity_routes": routes[:150], "related_scripts": scripts[:50],
            "candidate_asset_ids": sorted(ids)[:100],
            "native_training_playable": False, "native_festival_playable": False,
            "native_world_boss_card_routed": False, "release_approved": False}

def self_test():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        scripts = root / "scripts/ui"
        scripts.mkdir(parents=True)
        script = scripts / "menus.gd"
        fixture = ('extends Node\nfunc show_teleporter() -> void:\n'
                   '\t_teleport_card(tr("TRAINING_KEY"), show_training_setup.bind("training"))\n'
                   '\t_teleport_card(tr("FESTIVAL_KEY"), show_festival)\n'
                   '\t_teleport_card(tr("BOSS_KEY"), show_world_boss)\n'
                   '\nfunc show_training_setup(what: String):\n\tpass\n'
                   '\nfunc show_festival():\n\tpass\n\nfunc show_world_boss():\n\tpass\n')
        script.write_text(fixture, encoding="utf-8")
        report = inspect(root)
        assert report["selected_native_menu"]["method"] == "show_teleporter"
        assert report["selected_native_menu"]["required"] == 0
        assert report["known_teleporter_contract"]["native_route_references"] == [
            "_teleport_card", "show_training_setup", "show_festival", "show_world_boss"]
        assert not report["native_festival_playable"]
        script.write_text(fixture.replace("show_teleporter()", "show_teleporter(slot: int)"), encoding="utf-8")
        assert inspect(root)["selected_native_menu"] is None
        script.write_text(fixture.replace("_teleport_card(", "unknown_card("), encoding="utf-8")
        assert inspect(root)["selected_native_menu"] is None
    print("NATIVE_DESTINATIONS_DISCOVERY_SELFTEST PASS")

if __name__ == "__main__":
    self_test()
