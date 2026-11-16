#!/usr/bin/env python3
"""Report narrow, non-secret navigation cues from the privately reconstructed game.

This prints targeted functions, not bundled game source. For identifying the
real Preparation->Adventure and authentication paths during offline QA.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re

NEEDLES = (
    "to adventure", "adventure", "prepare", "preparation", "start_run",
    "enter_town", "login", "sign_in", "auth", "account", "opening_screens",
    "show_class", "show_map", "show_region", "show_stage", "game_over",
    "exit_run", "end_run", "return_to", "world.running",
)
PRIORITY = {"main.gd", "menus.gd", "ui_kit.gd", "save.gd", "run_save.gd"}
SAFE_LINE = re.compile(r"(?:https?://|token|secret|password|credential|api_key)", re.I)

def collect(project: Path):
    files = sorted((project / "scripts").rglob("*.gd"))
    records = []
    for f in files:
        name = f.name
        if name not in PRIORITY and not any(x in name.lower() for x in
            ("prepar", "login", "auth", "region", "stage", "map_select")):
            continue
        lines = f.read_text(encoding="utf-8").splitlines()
        heads = [i for i,x in enumerate(lines) if re.match(r"^(?:static )?func\s+[A-Za-z_]", x)]
        for j, start in enumerate(heads):
            end = heads[j+1] if j+1<len(heads) else len(lines)
            section = lines[start:end]
            method = re.search(r"\bfunc\s+(\w+)\s*\(",lines[start])
            if not method:
                continue
            hit = [(k, ln.strip()) for k,ln in enumerate(section) if any(
                term in ln.lower() for term in NEEDLES
            ) and not SAFE_LINE.search(ln)]
            important = any(x in method.group(1).lower() for x in
                ("adventure", "start", "run", "prepare", "login", "auth",
                "opening", "class", "region", "stage", "map", "ready"))
            if not hit and not important: continue
            if not hit and important and name not in PRIORITY: continue
            # Limit source context to concise navigation cues; no entire script.
            records.append((f.relative_to(project).as_posix(), start+1,
                            method.group(1), hit[:6], len(section)))
    return records[:140]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    args=parser.parse_args()
    print("ORIGINAL_UI_FLOW_SCAN_BEGIN")
    for path, line, name, hits, total in collect(args.project):
        cue=" | ".join(str(line+n)+":"+txt[:135] for n,txt in hits)
        print(f"UIFLOW {path}:{line} func={name} body_lines={total} cues={cue}")
    print("ORIGINAL_UI_FLOW_SCAN_END")

if __name__ == "__main__":
    main()
