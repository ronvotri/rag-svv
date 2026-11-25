#!/usr/bin/env python3
"""Direct-base compatibility preflight only; never export or modify production pins."""
from __future__ import annotations
import argparse
import importlib.util
import json
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

def preflight(work, report):
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
    report["stage"] = "complete"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "work/upstream-direct-preflight.json")
    args = parser.parse_args()
    report = {"version": "0.2.11", "stage": "initial", "candidate_hash_matched": False,
              "direct_recovery_passed": False, "offline_patch_preflight_passed": False,
              "addon_install_preflight_passed": False, "runtime_compatibility_verified": False,
              "approved_for_build": False, "old_patch_applied": False, "exported": False}
    root = ROOT / "work"
    root.mkdir(exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="upstream-direct-", dir=root) as folder:
            preflight(Path(folder), report)
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
