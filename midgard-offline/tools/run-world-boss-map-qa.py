#!/usr/bin/env python3
"""Optional isolated Godot boss-map QA; no live encounter activation."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
from zipfile import ZipFile, ZIP_DEFLATED



def instrument_native_damage(source: str) -> str | None:
    """Observe one actual native hurt call; reject ambiguous recovered APIs."""
    method = re.search(r"(?ms)^func damage_enemy\((.*?)\)(?:\s*->\s*[\w.]+)?\s*:\s*\n(.*?)(?=^func |^static func |\Z)", source)
    if not method:
        return None
    args, body = method.groups()
    enemy = re.findall(r"\b(\w+)\s*:\s*Enemy\b", args)
    players = re.findall(r"\b(\w+)\s*:\s*Player\b", args)
    if len(enemy) != 1 or len(players) != 1 or "svv_qa_before" in body:
        return None
    e, src = enemy[0], players[0]
    call = re.compile(r"(?m)^([ \t]+)(?:(?:var\s+\w+(?:\s*:\s*\w+)?\s*[:=]=?\s*|\w+\s*=\s*))?" + re.escape(e) + r"\.hurt\([^\n]*\)[ \t]*(?:#[^\n]*)?$")
    found = list(call.finditer(body))
    if len(found) != 1:
        return None
    m = found[0]
    i = m.group(1)
    lines = [
        f"var svv_qa_before: float = {e}.hp if is_instance_valid({e}) and {e}.has_meta(\"svv_qa_boss_hits\") else -1.0",
        m.group(0).lstrip(),
        f"if svv_qa_before >= 0.0 and is_instance_valid({e}):",
        f"\tvar svv_qa_delta: float = svv_qa_before - {e}.hp",
        "\tif svv_qa_delta > 0.0:",
        f"\t\tvar svv_qa_id: String = str({src}.get_instance_id()) if is_instance_valid({src}) else \"unknown\"",
        f"\t\tvar svv_qa_hits: Dictionary = {e}.get_meta(\"svv_qa_boss_hits\", {{}})",
        "\t\tvar svv_qa_row: Dictionary = svv_qa_hits.get(svv_qa_id, {})",
        "\t\tsvv_qa_row[\"damage\"] = float(svv_qa_row.get(\"damage\", 0.0)) + svv_qa_delta",
        "\t\tsvv_qa_row[\"hits\"] = int(svv_qa_row.get(\"hits\", 0)) + 1",
        "\t\tsvv_qa_hits[svv_qa_id] = svv_qa_row",
        f"\t\t{e}.set_meta(\"svv_qa_boss_hits\", svv_qa_hits)",
    ]
    patched = body[:m.start()] + "\n".join(i + line for line in lines) + body[m.end():]
    return source[:method.start(2)] + patched + source[method.end(2):]


def damage_hook_diagnostics(source: str) -> dict:
    """Export only counts and booleans, never recovered source or literals."""
    method = re.search(r"(?ms)^func damage_enemy\((.*?)\)(?:\s*->\s*[\w.]+)?\s*:\s*\n(.*?)(?=^func |^static func |\Z)", source)
    if not method:
        return {"header_matched": False}
    args, body = method.groups()
    enemy = re.findall(r"\b(\w+)\s*:\s*Enemy\b", args)
    players = re.findall(r"\b(\w+)\s*:\s*Player\b", args)
    return {
        "header_matched": True,
        "enemy_parameters": len(enemy),
        "player_parameters": len(players),
        "enemy_hurt_references": len(re.findall(r"\b" + re.escape(enemy[0]) + r"\.hurt\s*\(", body)) if len(enemy) == 1 else 0,
    }


def parse_candidates(markers: list[str]) -> dict[str, bool]:
    candidates = {}
    for row in markers:
        match = re.fullmatch(r"MVP_CANDIDATE ([a-z_]+) supported=(true|false)", row)
        if match:
            candidates[match.group(1)] = match.group(2) == "true"
    return candidates


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
        "visual_change_verified": False,
        "combat_telemetry": [],
        "attribution_status": "not_run",
        "attribution_telemetry": [],
        "hook_diagnostics": {},
        "mvp_candidates": {},
        "alternate_boss": {"status": "not_run"},
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
        native = project / "scripts/core/main.gd"
        original = native.read_bytes() if native.is_file() else None
        patched = instrument_native_damage(original.decode("utf-8")) if original else None
        report["attribution_status"] = "hook_installed" if patched else "blocked_hook_contract"
        if original:
            report["hook_diagnostics"] = damage_hook_diagnostics(original.decode("utf-8"))
        try:
            if patched is not None:
                native.write_text(patched, encoding="utf-8", newline="\n")
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
            report["mvp_candidates"] = parse_candidates(markers)
            report["combat_telemetry"] = [
                row for row in markers if row.startswith("COMBAT ")
            ][:4]
            report["attribution_telemetry"] = [row for row in markers if row.startswith("ATTRIBUTION")][:5]
            if patched is not None:
                summary = next((row for row in markers if row.startswith("ATTRIBUTION_SUMMARY ")), "")
                match = re.search(r"ai_hitters=(\d+)", summary)
                report["attribution_status"] = ("all_three_ai_hits_reconciled"
                    if completed.returncode == 0 and match and int(match.group(1)) == 3
                    and "reconciled=true" in summary else "partial_or_unverified")
            report["status"] = (
                "native_combat_observed"
                if completed.returncode == 0
                and any("RESULT COMBAT_MECHANICS_VERIFIED" in row for row in markers)
                else "blocked_or_failed_runtime_probe"
            )
        except subprocess.TimeoutExpired:
            report["status"] = "blocked_runtime_timeout"
            if patched is not None:
                report["attribution_status"] = "blocked_runtime_timeout"
        finally:
            if patched is not None and original is not None:
                native.write_bytes(original)  # Restore byte-for-byte before any export.
        # Separate process and data directory: do not carry Baphomet state or
        # rewards into the second encounter. No native raid entrypoint is used.
        if report["status"] == "native_combat_observed":
            first = next((row.split(" ", 1)[1] for row in report["evidence"]
                          if row.startswith("NATIVE_BOSS ")), "")
            alternate = next((boss for boss, supported in report["mvp_candidates"].items()
                              if supported and boss != first), "")
            if alternate:
                alt_dir = qa_dir / "alternate"
                alt_dir.mkdir(parents=True, exist_ok=True)
                alt_data = work / "boss-alternate-profile-sandbox"
                for part in ("data", "config", "cache"):
                    (alt_data / part).mkdir(parents=True, exist_ok=True)
                alt_env = {**env, "XDG_DATA_HOME": str(alt_data / "data"),
                           "XDG_CONFIG_HOME": str(alt_data / "config"),
                           "XDG_CACHE_HOME": str(alt_data / "cache")}
                alt_command = command[:-1] + ["--offline-output=" + str(alt_dir),
                                              "--offline-boss-id=" + alternate]
                try:
                    alt_run = subprocess.run(alt_command, stdout=subprocess.PIPE,
                                             stderr=subprocess.STDOUT, text=True,
                                             encoding="utf-8", errors="replace",
                                             env=alt_env, timeout=timeout, check=False)
                    alt_markers = [line.split("WORLD_BOSS_MAP_QA ", 1)[1].strip()[:220]
                                   for line in alt_run.stdout.splitlines()
                                   if "WORLD_BOSS_MAP_QA " in line]
                    alt_images = sorted(alt_dir.glob("boss-*.png"))
                    visual_ok = ({p.name for p in alt_images} ==
                                 {"boss-start.png", "boss-after-120frames.png"}
                                 and len({hashlib.sha256(p.read_bytes()).digest()
                                          for p in alt_images}) == 2)
                    observed = (alt_run.returncode == 0 and visual_ok
                                and "NATIVE_BOSS " + alternate in alt_markers
                                and "RESULT COMBAT_MECHANICS_VERIFIED errors=0" in alt_markers)
                    report["alternate_boss"] = {
                        "id": alternate,
                        "status": "native_combat_observed" if observed else "blocked_or_failed_runtime_probe",
                        "visual_change_verified": visual_ok,
                        "evidence": alt_markers[:60],
                        "combat_telemetry": [row for row in alt_markers if row.startswith("COMBAT ")],
                    }
                except subprocess.TimeoutExpired:
                    report["alternate_boss"] = {"id": alternate, "status": "blocked_runtime_timeout"}
            else:
                report["alternate_boss"] = {"status": "no_other_supported_candidate"}
    images = sorted(qa_dir.glob("boss-*.png"))
    report["screenshots"] = [p.name for p in images]
    if {p.name for p in images} == {"boss-start.png", "boss-after-120frames.png"}:
        report["visual_change_verified"] = len({
            hashlib.sha256(p.read_bytes()).digest() for p in images
        }) == 2
    if report["status"] == "native_combat_observed" and not report["visual_change_verified"]:
        report["status"] = "blocked_no_visual_change"
    if images:
        with ZipFile(work / "artifacts" / "World-Boss-Map-QA.zip", "w", ZIP_DEFLATED) as archive:
            for item in images:
                archive.write(item, item.name)
            for item in sorted((qa_dir / "alternate").glob("boss-*.png")):
                archive.write(item, "alternate/" + item.name)
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
