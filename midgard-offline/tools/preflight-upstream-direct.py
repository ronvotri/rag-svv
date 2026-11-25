#!/usr/bin/env python3
"""Direct-base compatibility preflight only; never export or modify production pins."""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
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
    report["translation_review"] = {"recent_keys": len(authored),
                                    "matching_source_keys": len(authored & source_keys),
                                    "missing_source_keys_count": len(authored - source_keys),
                                    "new_retired_keys_approved": False}
    if runtime:
        runtime_preflight(work, report, cloud, config, recovered, prepared)
    report["stage"] = "complete"

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
    if imported.returncode or report["import_script_error_count"]:
        raise ValueError("Godot import failed")
    report["stage"] = "isolated_smoke"
    smoke = run_private([godot, "--headless", "--path", prepared, "--",
                         "--offline-test", "--offline-qa"], 180)
    report["smoke_returncode"] = smoke.returncode
    report["smoke_script_error_count"] = smoke.stdout.count("SCRIPT ERROR:")
    report["smoke_pass_count"] = smoke.stdout.count("OFFLINE_QA PASS ")
    report["smoke_completed"] = "OFFLINE_QA COMPLETE failures=0" in smoke.stdout
    if smoke.returncode or report["smoke_script_error_count"] or not report["smoke_completed"]:
        raise ValueError("Isolated smoke failed")
    report["stage"] = "native_boss_runtime"
    boss = run_private([sys.executable, TOOLS / "run-world-boss-map-qa.py",
                        "--godot", godot, "--project", prepared, "--work", work], 1200)
    report["boss_runner_returncode"] = boss.returncode
    artifact = work / "artifacts/WORLD_BOSS_MAP_QA.json"
    if boss.returncode or not artifact.is_file():
        raise ValueError("Native boss report missing")
    result = json.loads(artifact.read_text(encoding="utf-8"))
    report["boss_runtime_summary"] = {
        key: result.get(key) for key in ("status", "damage_reconciliation",
            "native_death_verified", "local_rewards_verified", "terminal_observation",
            "mvp_candidates", "attribution_status")
    }
    report["boss_runtime_summary"]["additional_bosses"] = {
        name: {"status": value.get("status")} for name, value in result.get("additional_bosses", {}).items()
    }
    # Do not equate smoke or native combat with full compatibility or release approval.
    report["runtime_smoke_passed"] = True

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "work/upstream-direct-preflight.json")
    parser.add_argument("--runtime", action="store_true", help="Run isolated Godot QA after source preflight")
    args = parser.parse_args()
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
