#!/usr/bin/env python3
"""Direct-base compatibility preflight only; never export or modify production pins."""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), TOOLS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def candidate_config(legacy, pin, engine):
    if pin["scope"] != "isolated preflight only" or pin["approved_for_build"] is not False:
        raise ValueError("Invalid review-only pin")
    if pin["godot_version"] != engine:
        raise ValueError("Candidate engine mismatch")
    return {**legacy, **{k: pin[k] for k in ("archive_size", "pck_size", "pck_crc32", "pck_sha256")},
            "project_base_version": pin["version"]}

def preflight(work, report, runtime=False):
    cloud = load("cloud-build-original")
    pin = json.loads((ROOT / "review/upstream-0.2.11-pin.json").read_text(encoding="utf-8"))
    legacy = json.loads((ROOT / "config/official-client.json").read_text(encoding="utf-8"))
    config = json.loads((ROOT / "config/cloud-tools.json").read_text(encoding="utf-8"))
    review_config = candidate_config(legacy, pin, config["godot_version"])
    config_path = work / "candidate-fetch.json"
    config_path.write_text(json.dumps(review_config), encoding="utf-8")
    client = work / "MidgardSurvivors.pck"
    report["stage"] = "download_pinned_candidate"
    # Same strict existing fetcher; only the isolated config differs.
    cloud.run([sys.executable, TOOLS / "fetch-original-client.py", "--config", config_path, "--output", client])
    if cloud.digest(client) != pin["pck_sha256"]:
        raise ValueError("Candidate hash mismatch")
    report["candidate_hash_matched"] = True
    report["stage"] = "recover_direct_base"
    tool_zip = cloud.download(config["gdre_linux"], work / "gdre.zip")
    cloud.extract_safe(tool_zip, work / "gdre")
    gdre = cloud.executable(work / "gdre", "gdre")
    recovered = work / "recovered"
    # The new full client is recovered directly. No 0.2.7 patch is applied.
    subprocess.run([str(gdre), "--headless", "--recover=" + str(client),
                    "--output=" + str(recovered), "--exclude=res://eos/credentials.cfg"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=600)
    if not (recovered / "project.godot").is_file():
        raise ValueError("Recovered project missing")
    report["direct_recovery_passed"] = True
    report["stage"] = "native_api_audit"
    audit = load("audit-world-boss-maps").inventory(recovered)
    report["native_world_boss_contract"] = audit["native_world_boss_contract"]
    report["native_world_boss_flow"] = audit["native_world_boss_flow"]
    report["scene_candidate_count"] = audit["scene_candidate_count"]
    report["stage"] = "offline_patch_preflight"
    prepared = work / "prepared"
    patches = load("prepare-original-offline").prepare(recovered, prepared)
    report["offline_patch_preflight_passed"] = True
    report["patched_module_count"] = len(patches["changes"])
    report["stage"] = "addon_install_preflight"
    load("install-original-assistant").install(prepared)
    report["addon_install_preflight_passed"] = True
    report["stage"] = "translation_source_review"
    localizer = load("localize_original")
    source = localizer.read_po(prepared / "locale/en.po")
    source_keys = {entry.get("en") or entry["id"] for entry in source}
    authored = set()
    for n in range(21, 62):
        authored.update(json.loads((ROOT / "patches" / f"vi-ui-batch-{n:03d}.json").read_text(encoding="utf-8")))
    missing = authored - source_keys
    legacy_retired = set(json.loads((ROOT / "config/retired-translation-keys.json").read_text(
        encoding="utf-8"))["retired_source_keys"])
    report["translation_review"] = {"recent_keys": len(authored),
                                    "matching_source_keys": len(authored & source_keys),
                                    "missing_source_keys_count": len(missing),
                                    "previously_retired_missing": len(missing & legacy_retired),
                                    "newly_missing_count": len(missing - legacy_retired),
                                    "previously_retired_now_present": len(legacy_retired & source_keys),
                                    "newly_missing_authored_keys": sorted(missing - legacy_retired),
                                    "new_retired_keys_approved": False}
    if runtime:
        runtime_preflight(work, report, cloud, config, recovered, prepared)
    report["stage"] = "complete"

EXPECTED_MVPS = ("baphomet", "osiris", "eddga", "mistress", "maya", "dark_lord")

def evaluate_boss_roster(result):
    """A successful subprocess alone is not a combat acceptance result."""
    expected = set(EXPECTED_MVPS)
    candidates = result.get("mvp_candidates", {})
    evidence = result.get("evidence", [])
    primary = {row.split(" ", 1)[1] for row in evidence
               if row.startswith("NATIVE_BOSS ")}
    rows = {}
    for name in EXPECTED_MVPS:
        if candidates.get(name) is not True:
            rows[name] = "unsupported_or_unreported"
            continue
        if primary == {name}:
            row = result
        else:
            row = result.get("additional_bosses", {}).get(name, {})
        rows[name] = ("combat_observed" if row.get("status") == "native_combat_observed"
                      and row.get("visual_change_verified") is True
                      and ("NATIVE_BOSS " + name) in row.get("evidence", [])
                      and "RESULT COMBAT_MECHANICS_VERIFIED errors=0" in row.get("evidence", [])
                      else "unverified")
    return {"expected": len(expected), "combat_passed": sum(v == "combat_observed" for v in rows.values()),
            "all_six_combat_observed": all(v == "combat_observed" for v in rows.values()),
            "by_boss": rows}

def self_test():
    def evidence(name):
        return ["NATIVE_BOSS " + name, "RESULT COMBAT_MECHANICS_VERIFIED errors=0"]
    def sample(name):
        return {"status": "native_combat_observed", "visual_change_verified": True,
                "evidence": evidence(name)}
    result = {**sample("baphomet"), "mvp_candidates": {n: True for n in EXPECTED_MVPS},
              "additional_bosses": {n: sample(n) for n in EXPECTED_MVPS[1:]}}
    assert evaluate_boss_roster(result)["all_six_combat_observed"]
    result["additional_bosses"]["maya"]["visual_change_verified"] = False
    assert evaluate_boss_roster(result)["combat_passed"] == 5
    result["additional_bosses"]["osiris"] = sample("eddga")
    assert evaluate_boss_roster(result)["combat_passed"] == 4
    assert not evaluate_boss_roster({})["all_six_combat_observed"]
    assert diagnostic_locations("res://scripts/core/main.gd:123\nres://scripts/../private.gd:1") == [{"path": "scripts/core/main.gd", "line": 123}]
    print("DIRECT_RUNTIME_ROSTER_SELFTEST PASS")

def diagnostic_locations(output):
    """Only sanitized script paths and line numbers, not original error text."""
    matches = re.findall(r"res://((?:scripts|addons/svv_offline)/[A-Za-z0-9_./-]+\.gd):(\d+)", output)
    return [{"path": path, "line": int(line)} for path, line in sorted(set(matches))[:50]
            if ".." not in Path(path).parts]

def runtime_preflight(work, report, cloud, config, recovered, prepared):
    """Run only test-profile smoke and map QA; never export a client."""
    report["stage"] = "runtime_prepare"
    godot_zip = cloud.download(config["godot_linux"], work / "godot.zip")
    cloud.extract_safe(godot_zip, work / "godot")
    godot = cloud.executable(work / "godot", "godot")
    (godot.parent / "_sc_").touch()
    fonts = work / "fonts"
    for name, spec in config["fonts"].items():
        cloud.download(spec, fonts / name)
    load("install-start-background").install(prepared)
    cloud.seed_cache(recovered, prepared)
    report["translation_runtime"] = load("localize_original").localize(
        prepared, ROOT / "patches/vi-ui.json", fonts / "NotoSans-Regular.ttf",
        fonts / "NotoSans-Bold.ttf")
    import shutil
    shutil.copyfile(fonts / "OFL.txt", prepared / "assets/ro/fonts/NotoSans-OFL.txt")
    profile = work / "runtime-test-profile"
    env = dict(os.environ)
    for variable, suffix in (("XDG_DATA_HOME", "data"), ("XDG_CONFIG_HOME", "config"),
                             ("XDG_CACHE_HOME", "cache")):
        directory = profile / suffix
        directory.mkdir(parents=True, exist_ok=True)
        env[variable] = str(directory)
    def run_private(args, timeout):
        return subprocess.run([str(a) for a in args], env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout)
    report["stage"] = "godot_import"
    imported = run_private([godot, "--headless", "--editor", "--path", prepared,
                            "--import", "--quit"], 600)
    report["import_returncode"] = imported.returncode
    report["import_script_error_count"] = imported.stdout.count("SCRIPT ERROR:")
    report["import_diagnostic_locations"] = diagnostic_locations(imported.stdout) if imported.returncode or report["import_script_error_count"] else []
    if imported.returncode or report["import_script_error_count"]:
        raise ValueError("Godot import failed")
    report["stage"] = "isolated_smoke"
    smoke = run_private([godot, "--headless", "--path", prepared, "--",
                         "--offline-test", "--offline-qa"], 180)
    report["smoke_returncode"] = smoke.returncode
    report["smoke_script_error_count"] = smoke.stdout.count("SCRIPT ERROR:")
    report["smoke_diagnostic_locations"] = diagnostic_locations(smoke.stdout) if smoke.returncode or report["smoke_script_error_count"] else []
    report["smoke_pass_count"] = smoke.stdout.count("OFFLINE_QA PASS ")
    report["smoke_completed"] = "OFFLINE_QA COMPLETE failures=0" in smoke.stdout
    if smoke.returncode or report["smoke_script_error_count"] or not report["smoke_completed"]:
        raise ValueError("Isolated smoke failed")
    report["runtime_smoke_passed"] = True
    wallet_checks = ("QA receipt credits wallet once", "QA wallet credit exact amount",
                     "QA wallet and receipt persist together", "QA reload reward replay blocked",
                     "QA cross MVP credit blocked")
    report["qa_fixture_wallet_credit_verified"] = all(
        "OFFLINE_QA PASS " + label in smoke.stdout for label in wallet_checks)
    if not report["qa_fixture_wallet_credit_verified"]:
        raise ValueError("QA wallet transaction fixture incomplete")
    # Execute independently: one failed gameplay probe must not suppress the other.
    # Fail the overall workflow at the end if either gate fails.
    try:
        menu_runtime_check(work, report, godot, prepared, env, run_private)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        report["menu_qa_passed"] = False
        report["menu_qa_error_type"] = type(error).__name__
    try:
        boss_runtime_check(work, report, godot, prepared, run_private)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        report["boss_qa_error_type"] = type(error).__name__
    report["stage"] = "runtime_acceptance"
    if not report.get("menu_qa_passed") or not report.get("menu_terminal_qa_passed") or not report.get("boss_roster_gate", {}).get("all_six_combat_observed"):
        raise ValueError("Independent runtime QA gate incomplete")
    # Preserve the release and reward gates; this is only QA.

def boss_runtime_check(work, report, godot, prepared, run_private):
    report["stage"] = "native_boss_runtime"
    # Do not reuse the menu profile for the runner itself.
    # The native runner additionally creates a fresh sandbox per MVP.
    boss = run_private([sys.executable, TOOLS / "run-world-boss-map-qa.py",
                        "--godot", godot, "--project", prepared, "--work", work], 1200)
    report["boss_runner_returncode"] = boss.returncode
    artifact = work / "artifacts/WORLD_BOSS_MAP_QA.json"
    if boss.returncode or not artifact.is_file():
        raise ValueError("Native boss report missing")
    result = json.loads(artifact.read_text(encoding="utf-8"))
    report["boss_runtime_summary"] = {
        key: result.get(key) for key in ("status", "damage_reconciliation",
            "native_death_verified", "local_rewards_verified", "local_victory_ledger_verified",
            "local_victory_observation", "terminal_observation",
            "mvp_candidates", "attribution_status")
    }
    report["boss_runtime_summary"]["additional_bosses"] = {
        name: {key: value.get(key) for key in ("status", "visual_change_verified",
               "returncode", "script_error_count", "diagnostic_locations",
               "combat_telemetry", "terminal_observation", "failure_markers")}
        for name, value in result.get("additional_bosses", {}).items()
    }
    report["boss_runtime_summary"]["primary_failure_markers"] = [
        line for line in result.get("evidence", [])
        if line.startswith(("FAIL ", "RESULT ", "BLOCKED", "DENIED", "SPAWN_DIAG "))][:20]
    report["boss_roster_gate"] = evaluate_boss_roster(result)
    if not report["boss_roster_gate"]["all_six_combat_observed"]:
        raise ValueError("Native boss roster incomplete")

def menu_runtime_check(work, report, godot, prepared, env, run_private):
    report["stage"] = "native_menu_runtime"
    # Separate from the smoke and boss QA profiles; no shared test saves.
    for variable, suffix in (("XDG_DATA_HOME", "data"), ("XDG_CONFIG_HOME", "config"),
                             ("XDG_CACHE_HOME", "cache")):
        directory = work / "menu-test-profile" / suffix
        directory.mkdir(parents=True, exist_ok=True)
        env[variable] = str(directory)
    # Observe native death only inside the disposable menu test process.
    # Restore original script bytes before any subsequent QA.
    death_file = prepared / "scripts/core/enemy.gd"
    death_original = death_file.read_bytes()
    instrument = load("run-world-boss-map-qa").instrument_native_death
    death_patched = instrument(death_original.decode("utf-8"))
    report["menu_death_hook_installed"] = death_patched is not None
    env["SVV_WORLD_BOSS_QA_SANDBOX"] = "1"
    terminal = None
    try:
        if death_patched is not None:
            death_file.write_text(death_patched, encoding="utf-8")
        menu = run_private([godot, "--headless", "--path", prepared,
                            "res://addons/svv_offline/qa/offline_mvp_menu_qa.tscn", "--",
                            "--offline-test", "--offline-mvp-menu-preview"], 180)
        if menu.returncode == 0 and death_patched is not None:
            for variable, suffix in (("XDG_DATA_HOME", "data"), ("XDG_CONFIG_HOME", "config"),
                                     ("XDG_CACHE_HOME", "cache")):
                directory = work / "menu-terminal-test-profile" / suffix
                directory.mkdir(parents=True, exist_ok=True)
                env[variable] = str(directory)
            terminal = run_private([godot, "--headless", "--path", prepared,
                                    "res://addons/svv_offline/qa/offline_mvp_menu_qa.tscn", "--",
                                    "--offline-test", "--offline-mvp-menu-preview",
                                    "--offline-mvp-menu-terminal", "--offline-mvp-wallet-preview"], 300)
    finally:
        death_file.write_bytes(death_original)
        env.pop("SVV_WORLD_BOSS_QA_SANDBOX", None)
    report["menu_qa_returncode"] = menu.returncode
    report["menu_qa_script_error_count"] = menu.stdout.count("SCRIPT ERROR:")
    report["menu_qa_diagnostics"] = diagnostic_locations(menu.stdout)
    report["menu_qa_markers"] = [line.strip() for line in menu.stdout.splitlines()
                                if line.startswith(("MVP_MENU_TEST ", "OFFLINE_MVP_MENU_QA ", "WORLD_BOSS_MAP_QA SPAWN_DIAG "))][:40]
    report["menu_qa_passed"] = (menu.returncode == 0 and not report["menu_qa_script_error_count"]
                               and "MVP_MENU_TEST COMPLETE errors=0" in report["menu_qa_markers"])
    report["menu_terminal_qa_passed"] = False
    report["menu_victory_ledger_verified"] = False
    report["menu_reward_receipt_verified"] = False
    report["native_reward_credit_verified"] = False
    if terminal is not None:
        report["menu_terminal_returncode"] = terminal.returncode
        report["menu_terminal_script_error_count"] = terminal.stdout.count("SCRIPT ERROR:")
        report["menu_terminal_markers"] = [line.strip() for line in terminal.stdout.splitlines()
            if line.startswith(("MVP_MENU_TEST ", "OFFLINE_MVP_MENU_QA HUD_TERMINAL "))][-50:]
        report["menu_terminal_qa_passed"] = (terminal.returncode == 0 and not report["menu_terminal_script_error_count"]
            and "MVP_MENU_TEST COMPLETE errors=0" in report["menu_terminal_markers"])
        report["menu_victory_ledger_verified"] = (report["menu_terminal_qa_passed"]
            and "MVP_MENU_TEST TERMINAL outcome=victory saved=true replay_blocked=true persisted=true" in report["menu_terminal_markers"])
        report["menu_reward_receipt_verified"] = (report["menu_victory_ledger_verified"]
            and "MVP_MENU_TEST PASS single_reward_receipt_persisted" in report["menu_terminal_markers"])
        report["native_reward_credit_verified"] = (report["menu_reward_receipt_verified"] and all(
            "MVP_MENU_TEST PASS " + label in report["menu_terminal_markers"] for label in (
                "menu_wallet_exact_credit", "menu_wallet_replay_blocked_and_persisted", "menu_wallet_reload_replay_blocked")))
    # Do not equate smoke or native combat with full compatibility or release approval.

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "work/upstream-direct-preflight.json")
    parser.add_argument("--runtime", action="store_true", help="Run isolated Godot QA after source preflight")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    report = {"version": "0.2.11", "stage": "initial", "candidate_hash_matched": False,
              "direct_recovery_passed": False, "offline_patch_preflight_passed": False,
              "addon_install_preflight_passed": False, "runtime_compatibility_verified": False,
              "approved_for_build": False, "old_patch_applied": False, "exported": False}
    root = ROOT / "work"
    root.mkdir(exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="upstream-direct-", dir=root) as folder:
            preflight(Path(folder), report, runtime=args.runtime)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        report["error_type"] = type(error).__name__
        # Fixed stages and types only; no recovered code/credentials or signed URLs.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("native_world_boss_contract", "native_world_boss_flow")}))
    if report["stage"] != "complete":
        raise SystemExit(1)

if __name__ == "__main__":
    main()
