#!/usr/bin/env python3
"""Optional isolated Godot boss-map QA; no live encounter activation."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED


def run_probe(godot: Path, project: Path, work: Path, *, timeout: int = 110) -> dict:
    context = work / "context"
    context.mkdir(parents=True, exist_ok=True)
    qa_dir = work / "artifacts" / "World-Boss-Map-QA"
    qa_dir.mkdir(parents=True, exist_ok=True)
    data = work / "boss-profile-sandbox"
    for part in ("data", "config", "cache"):
        (data / part).mkdir(parents=True, exist_ok=True)
    report = {
        "schema": 1,
        "scope": "qa_only_real_godot_map_native_boss_spawn",
        "isolated_profile": "profile_offline_test",
        "isolated_user_directory": True,
        "native_world_boss_start_called": False,
        "native_mvp_raid_route_called": False,
        "official_rewards_approved": False,
        "runtime_boss_playable_approved": False,
        "status": "not_run",
        "evidence": [],
        "screenshots": [],
    }
    xvfb = shutil.which("xvfb-run")
    if not xvfb:
        report["status"] = "blocked_no_virtual_display"
    elif not (project / "addons/svv_offline/qa/world_boss_map_qa.tscn").is_file():
        report["status"] = "blocked_qa_scene_missing"
    else:
        command = [
            xvfb, "--auto-servernum", "--server-args=-screen 0 1280x1024x24",
            str(godot), "--path", str(project),
            "res://addons/svv_offline/qa/world_boss_map_qa.tscn", "--",
            "--offline-test", "--offline-boss-map-qa",
            "--offline-output=" + str(qa_dir),
        ]
        env = {
            **os.environ,
            "SVV_WORLD_BOSS_QA_SANDBOX": "1",
            "XDG_DATA_HOME": str(data / "data"),
            "XDG_CONFIG_HOME": str(data / "config"),
            "XDG_CACHE_HOME": str(data / "cache"),
        }
        try:
            completed = subprocess.run(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                env=env, timeout=timeout, check=False,
            )
            # Export only authored status labels, never original source or logs.
            markers = [
                line.split("WORLD_BOSS_MAP_QA ", 1)[1].strip()[:220]
                for line in completed.stdout.splitlines()
                if "WORLD_BOSS_MAP_QA " in line
            ]
            report["evidence"] = markers[:60]
            report["status"] = (
                "native_node_wiring_pass"
                if completed.returncode == 0
                and any("RESULT NODE_LEVEL_WIRING_VERIFIED" in row for row in markers)
                else "blocked_or_failed_runtime_probe"
            )
        except subprocess.TimeoutExpired:
            report["status"] = "blocked_runtime_timeout"
    images = sorted(qa_dir.glob("boss-*.png"))
    report["screenshots"] = [p.name for p in images]
    if images:
        with ZipFile(work / "artifacts" / "World-Boss-Map-QA.zip", "w", ZIP_DEFLATED) as archive:
            for item in images:
                archive.write(item, item.name)
    # Never grant release approval automatically, even if node wiring passes.
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    (context / "world-boss-runtime-qa.json").write_text(payload, encoding="utf-8")
    (work / "artifacts" / "WORLD_BOSS_MAP_QA.json").write_text(payload, encoding="utf-8")
    print("WORLD_BOSS_PROBE " + json.dumps({
        "status": report["status"], "screenshots": len(images),
        "approved": report["runtime_boss_playable_approved"],
    }), flush=True)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--godot", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    args = parser.parse_args()
    run_probe(args.godot.resolve(strict=True), args.project.resolve(strict=True), args.work.resolve())


if __name__ == "__main__":
    main()
