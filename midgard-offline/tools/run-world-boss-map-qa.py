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
    if len(enemy) != 1 or len(players) > 1 or "svv_qa_before" in body:
        return None
    e = enemy[0]
    # Recovered scripts may omit type annotations for a nullable source.
    # Restrict fallback to simple untyped null defaults, never arbitrary expressions.
    candidates = players or re.findall(
        r"(?:^|,)\s*(\w+)\s*(?::=|=)\s*null\s*(?=,|$)", args)
    # If no source contract is known, still measure damage under "unknown".
    # This is a total-damage observer, not evidence of per-AI attribution.
    source_lines = [
        "var svv_qa_source_ids: Array[String] = []",
    ]
    for candidate in candidates:
        source_lines.extend([
            f"if {candidate} is Player and is_instance_valid({candidate}):",
            f"\tvar svv_qa_candidate_id: String = str({candidate}.get_instance_id())",
            "\tif not svv_qa_source_ids.has(svv_qa_candidate_id):",
            "\t\tsvv_qa_source_ids.append(svv_qa_candidate_id)",
        ])
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
        *["\t\t" + line for line in source_lines],
        "\t\tvar svv_qa_id: String = svv_qa_source_ids[0] if svv_qa_source_ids.size() == 1 else \"unknown\"",
        f"\t\tvar svv_qa_hits: Dictionary = {e}.get_meta(\"svv_qa_boss_hits\", {{}})",
        "\t\tvar svv_qa_row: Dictionary = svv_qa_hits.get(svv_qa_id, {})",
        "\t\tsvv_qa_row[\"damage\"] = float(svv_qa_row.get(\"damage\", 0.0)) + svv_qa_delta",
        "\t\tsvv_qa_row[\"hits\"] = int(svv_qa_row.get(\"hits\", 0)) + 1",
        "\t\tsvv_qa_hits[svv_qa_id] = svv_qa_row",
        f"\t\t{e}.set_meta(\"svv_qa_boss_hits\", svv_qa_hits)",
    ]
    patched = body[:m.start()] + "\n".join(i + line for line in lines) + body[m.end():]
    return source[:method.start(2)] + patched + source[method.end(2):]


def instrument_native_death(source: str) -> str | None:
    """Observe entry into the actual Enemy.die callback, without invoking it."""
    headers = list(re.finditer(r"(?m)^func die\(\s*\)(?:\s*->\s*void)?\s*:[ \t]*\n", source))
    if len(headers) != 1 or "SVV_QA_NATIVE_DEATH" in source:
        return None
    at = headers[0].end()
    line = re.match(r"([ \t]+)\S", source[at:])
    if not line:
        return None
    indent = line.group(1)
    observer = (indent + 'if has_meta("svv_qa_boss_hits"):\n'
                + indent + '\tset_meta("svv_qa_native_death", hp <= 0.0)\n'
                + indent + '\tprint("WORLD_BOSS_MAP_QA NATIVE_DEATH hp=", hp, " SVV_QA_NATIVE_DEATH")\n'
                + indent + '\tif has_meta("svv_qa_death_observer"):\n'
                + indent + '\t\tvar svv_qa_observer: Variant = get_meta("svv_qa_death_observer")\n'
                + indent + '\t\tif svv_qa_observer is Callable and svv_qa_observer.is_valid():\n'
                + indent + '\t\t\tsvv_qa_observer.call(self)\n')
    return source[:at] + observer + source[at:]


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
        "untyped_nullable_parameters": len(re.findall(
            r"(?:^|,)\s*(\w+)\s*(?::=|=)\s*null\s*(?=,|$)", args)),
        "standalone_hurt_call_lines": len(re.findall(
            r"(?m)^[ \t]+(?:(?:var\s+\w+(?:\s*:\s*\w+)?\s*[:=]=?\s*|\w+\s*=\s*))?"
            + re.escape(enemy[0]) + r"\.hurt\([^\n]*\)[ \t]*(?:#[^\n]*)?$", body)) if len(enemy) == 1 else 0,
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
        "additional_bosses": {},
        "terminal_observation": [],
        "extended_primary_observation": True,
        "progress_samples": [],
        "native_death_verified": False,
        "death_hook_installed": False,
        "death_callback_observation": [],
        "damage_reconciliation": "not_run",
        "local_rewards_verified": False,
        "local_victory_ledger_verified": False,
        "local_victory_observation": [],
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
        death_file = project / "scripts/core/enemy.gd"
        death_original = death_file.read_bytes() if death_file.is_file() else None
        death_patched = instrument_native_death(death_original.decode("utf-8")) if death_original else None
        report["death_hook_installed"] = death_patched is not None
        report["attribution_status"] = "hook_installed" if patched else "blocked_hook_contract"
        if original:
            report["hook_diagnostics"] = damage_hook_diagnostics(original.decode("utf-8"))
        try:
            if patched is not None:
                native.write_text(patched, encoding="utf-8", newline="\n")
            if death_patched is not None:
                death_file.write_text(death_patched, encoding="utf-8", newline="\n")
            # Primary only: preserve the ordinary short checks for the other MVPs.
            completed = subprocess.run(
                command + ["--offline-boss-extended"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                env=env, timeout=max(timeout, 300), check=False,
            )
            # Export only authored status labels, never original source or logs.
            markers = [
                line.split("WORLD_BOSS_MAP_QA ", 1)[1].strip()[:220]
                for line in completed.stdout.splitlines()
                if "WORLD_BOSS_MAP_QA " in line
            ]
            report["evidence"] = markers[:60]
            report["mvp_candidates"] = parse_candidates(markers)
            report["terminal_observation"] = [row for row in markers if row.startswith("TERMINAL ")][:1]
            report["progress_samples"] = [row for row in markers if row.startswith("PROGRESS ")][:12]
            report["death_callback_observation"] = [row for row in markers if row.startswith("NATIVE_DEATH ")][:4]
            if death_patched is not None and completed.returncode == 0:
                for row in report["death_callback_observation"]:
                    hp = re.fullmatch(r"NATIVE_DEATH hp=([-+0-9.eE]+) SVV_QA_NATIVE_DEATH", row)
                    if hp and float(hp.group(1)) <= 0.0:
                        report["native_death_verified"] = True
            report["local_victory_observation"] = [row for row in markers if row.startswith("LOCAL_VICTORY ")][:1]
            report["local_victory_ledger_verified"] = (
                report["native_death_verified"] and completed.returncode == 0
                and report["local_victory_observation"] ==
                ["LOCAL_VICTORY recorded=true duplicate_blocked=true persisted=true"])
            report["combat_telemetry"] = [
                row for row in markers if row.startswith("COMBAT ")
            ][:4]
            report["attribution_telemetry"] = [row for row in markers if row.startswith("ATTRIBUTION")][:5]
            if patched is not None:
                summary = next((row for row in markers if row.startswith("ATTRIBUTION_SUMMARY ")), "")
                match = re.search(r"ai_hitters=(\d+)", summary)
                amounts = re.search(r"hp_loss=([-+0-9.eE]+) recorded=([-+0-9.eE]+)", summary)
                report["damage_reconciliation"] = ("total_hp_loss_reconciled"
                    if completed.returncode == 0 and amounts and float(amounts.group(1)) > 0
                    and abs(float(amounts.group(1)) - float(amounts.group(2))) < 0.1
                    else "unverified")
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
            if death_patched is not None and death_original is not None:
                death_file.write_bytes(death_original)
        # Separate process and data directory: do not carry Baphomet state or
        # rewards into the second encounter. No native raid entrypoint is used.
        if report["status"] == "native_combat_observed":
            first = next((row.split(" ", 1)[1] for row in report["evidence"]
                          if row.startswith("NATIVE_BOSS ")), "")
            # Bounded allowlist; never treat unrecognized output as a path or boss ID.
            allowed = ("baphomet", "osiris", "eddga", "mistress", "maya", "dark_lord",
                       "phreeoni", "moonlight_flower", "golden_thief_bug")
            alternatives = [boss for boss in allowed
                            if report["mvp_candidates"].get(boss) is True and boss != first]
            if not alternatives:
                report["alternate_boss"] = {"status": "no_other_supported_candidate"}
            for alternate in alternatives:
                alt_dir = qa_dir / "bosses" / alternate
                alt_dir.mkdir(parents=True, exist_ok=True)
                alt_data = work / "boss-alternate-profile-sandbox" / alternate
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
                    report["additional_bosses"][alternate] = {
                        "id": alternate,
                        "status": "native_combat_observed" if observed else "blocked_or_failed_runtime_probe",
                        "visual_change_verified": visual_ok,
                        "returncode": alt_run.returncode,
                        "script_error_count": alt_run.stdout.count("SCRIPT ERROR:"),
                        "diagnostic_locations": [
                            {"path": path, "line": int(line)}
                            for path, line in sorted(set(re.findall(
                                r"res://((?:scripts|addons/svv_offline)/[A-Za-z0-9_./-]+\.gd):(\d+)",
                                alt_run.stdout)))[:30]
                            if ".." not in Path(path).parts
                        ],
                        "failure_markers": [
                            row for row in alt_markers
                            if row.startswith(("FAIL ", "RESULT ", "BLOCKED", "DENIED"))
                        ][:20],
                        "evidence": alt_markers[:60],
                        "combat_telemetry": [row for row in alt_markers if row.startswith("COMBAT ")],
                        "terminal_observation": [row for row in alt_markers if row.startswith("TERMINAL ")][:1],
                    }
                except subprocess.TimeoutExpired:
                    report["additional_bosses"][alternate] = {"id": alternate, "status": "blocked_runtime_timeout",
                                                             "failure_markers": ["BLOCKED runtime_timeout"]}
                if alternate == alternatives[0]:
                    report["alternate_boss"] = report["additional_bosses"][alternate]
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
            terminal = qa_dir / "terminal-observation.png"
            if terminal.is_file():
                archive.write(terminal, terminal.name)
            for boss in report["additional_bosses"]:
                folder = qa_dir / "bosses" / boss
                for item in sorted(folder.glob("boss-*.png")):
                    archive.write(item, "bosses/" + boss + "/" + item.name)
                terminal = folder / "terminal-observation.png"
                if terminal.is_file():
                    archive.write(terminal, "bosses/" + boss + "/" + terminal.name)
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
