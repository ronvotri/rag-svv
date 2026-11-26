#!/usr/bin/env python3
"""Ephemeral Web export compatibility probe. No client distribution or deployment."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def load(path):
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    work = ROOT / "work"
    work.mkdir(exist_ok=True)
    report = {"scope": "ephemeral export compatibility only", "stage": "initial",
              "version": "0.2.11", "candidate_hash_matched": False,
              "export_passed": False, "browser_tested": False,
              "uploaded_client": False, "deployed": False}
    try:
        with tempfile.TemporaryDirectory(prefix="mvp-web-export-") as folder:
            private = Path(folder)
            pin = json.loads((ROOT / "review/upstream-0.2.11-pin.json").read_text(encoding="utf-8"))
            legacy = json.loads((ROOT / "config/official-client.json").read_text(encoding="utf-8"))
            config = json.loads((ROOT / "config/cloud-tools.json").read_text(encoding="utf-8"))
            preflight = load(ROOT / "tools/preflight-upstream-direct.py")
            candidate = preflight.candidate_config(legacy, pin, config["godot_version"])
            candidate_file = private / "candidate.json"
            candidate_file.write_text(json.dumps(candidate), encoding="utf-8")
            client = private / "MidgardSurvivors.pck"
            report["stage"] = "download_pinned_candidate"
            subprocess.run([sys.executable, str(ROOT / "tools/fetch-original-client.py"),
                            "--config", str(candidate_file), "--output", str(client)],
                           check=True, timeout=600)
            cloud = load(ROOT / "tools/cloud-build-original.py")
            if cloud.digest(client) != pin["pck_sha256"]:
                raise ValueError("Candidate checksum mismatch")
            report["candidate_hash_matched"] = True
            report["stage"] = "prepare_export_tools"
            exporter = load(ROOT / "review/build-local-mvp-web-preview.py")
            from argparse import Namespace
            args = Namespace(pck=client, output=private / "web", gdre=None, godot=None,
                             templates=None, fonts=None)
            exporter.provision_linux_tools(args)
            report["stage"] = "build"
            # Keep recovered client and detailed logs inside the runner only.
            log_path = private / "build.log"
            command = [sys.executable, str(ROOT / "review/build-local-mvp-web-preview.py"),
                       "--pck", str(client), "--gdre", str(args.gdre),
                       "--godot", str(args.godot), "--templates", str(args.templates),
                       "--fonts", str(args.fonts), "--output", str(args.output),
                       "--authorized-local-client"]
            with log_path.open("w", encoding="utf-8") as log:
                result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=2400)
            stages = []
            error_count = 0
            with log_path.open(encoding="utf-8", errors="replace") as log:
                for line in log:
                    if line.strip() in ("LOCAL_MVP_WEB_STAGE recover", "LOCAL_MVP_WEB_STAGE prepare",
                                        "LOCAL_MVP_WEB_STAGE import", "LOCAL_MVP_WEB_STAGE export"):
                        stages.append(line.strip().split()[-1])
                    if "SCRIPT ERROR:" in line:
                        error_count += 1
            report["build_stages"] = stages
            report["script_error_count"] = error_count
            report["build_returncode"] = result.returncode
            if result.returncode or error_count:
                raise ValueError("Web export failed")
            report["stage"] = "verify_export"
            files = {}
            for name in ("index.html", "index.js", "index.wasm", "index.pck"):
                path = args.output / name
                if not path.is_file() or path.stat().st_size == 0:
                    raise ValueError("Missing expected Web export file")
                files[name] = path.stat().st_size
            report["export_file_sizes"] = files
            report["export_passed"] = True
            report["stage"] = "complete"
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        report["error_type"] = type(error).__name__
    (work / "world-boss-web-export-probe.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))
    if not report["export_passed"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
