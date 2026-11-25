#!/usr/bin/env python3
"""Inspect a separately identified public client candidate; never change production pins."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def inspect_candidate(archive, destination, config, expected, fetch, inventory):
    """Read only one explicitly expected PCK into ephemeral storage."""
    if archive.stat().st_size != expected["archive_size"]:
        raise ValueError("Candidate ZIP size changed")
    with zipfile.ZipFile(archive) as source:
        entries = source.infolist()
        if len(entries) > config["max_archive_entries"] or sum(i.file_size for i in entries) > config["max_total_uncompressed"]:
            raise ValueError("ZIP directory exceeds bounds")
        for item in entries:
            fetch.safe_member(item.filename)
            if item.flag_bits & 1 or (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Unsupported ZIP member")
        members = [i for i in entries if i.filename == config["pck_member"]]
        if len(members) != 1:
            raise ValueError("Expected one PCK")
        member = members[0]
        if member.file_size != expected["pck_size"] or f"{member.CRC:08x}" != expected["pck_crc32"]:
            raise ValueError("Candidate metadata changed")
        digest = hashlib.sha256()
        total = 0
        with source.open(member) as inp, destination.open("xb") as out:
            while chunk := inp.read(1024 * 1024):
                total += len(chunk)
                if total > expected["pck_size"]:
                    raise ValueError("Candidate expanded beyond bound")
                digest.update(chunk)
                out.write(chunk)
        if total != expected["pck_size"]:
            raise ValueError("Candidate truncated")
    info = inventory.inspect(destination)
    if info["sha256"] != digest.hexdigest():
        raise ValueError("Candidate digest inconsistent")
    paths = {i["path"].removeprefix("res://") for i in info["entries"]}
    required = ("project.binary", "scenes/main.tscn", "scripts/core/main.gdc",
                "scripts/core/enemy.gdc", "scripts/core/mvp_raid.gdc",
                "scripts/core/boss_brain.gdc", "scripts/autoload/updater.gdc")
    # Compiled or remapped resource names are inventory hints, not runtime proof.
    return {"status": "candidate_inspected", "pck_size": total,
            "pck_crc32": expected["pck_crc32"], "observed_sha256": info["sha256"],
            "godot_version": info["godot_version"], "pack_version": info["pack_version"],
            "file_count": info["file_count"],
            "resource_path_hints": {p: p in paths or p + ".remap" in paths for p in required},
            "approved_for_build": False, "runtime_compatibility_verified": False,
            "independent_publisher_hash_verified": False,
            "old_patch_applied": False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "work/upstream-candidate-review.json")
    args = parser.parse_args()
    config = json.loads((ROOT / "config/official-client.json").read_text(encoding="utf-8"))
    expected = json.loads((ROOT / "config/upstream-client-candidate.json").read_text(encoding="utf-8"))
    fetch = load("official_fetch", "fetch-original-client.py")
    inventory = load("pck_inventory", "inspect_pck.py")
    metadata = load("metadata_audit", "audit-upstream-client.py")
    try:
        opener, url = fetch.official_download(config)
        with fetch.request(opener, url, headers={"Range": "bytes=-131072"}) as response:
            import re
            match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
            if response.status != 206 or not match:
                raise ValueError("Invalid CDN metadata response")
            start, end, size = map(int, match.groups())
            tail = response.read(131073)
        if start != size-len(tail) or end != size-1 or len(tail) != min(size, 131072):
            raise ValueError("Invalid range")
        report = metadata.parse_tail(tail, size, config, fetch)
        if (report["archive_size"], report["observed_pck_size"], report["observed_pck_crc32"]) != (
                expected["archive_size"], expected["pck_size"], expected["pck_crc32"]):
            raise ValueError("Candidate metadata changed; review again")
        with tempfile.TemporaryDirectory(prefix="upstream-candidate-") as folder:
            archive = Path(folder) / "official.zip"
            fetch.download_archive(opener, url, archive, size)
            result = inspect_candidate(archive, Path(folder) / "candidate.pck", config, expected, fetch, inventory)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        result = {"status": "blocked_candidate_review", "error_type": type(error).__name__,
                  "approved_for_build": False, "runtime_compatibility_verified": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    if result["status"] != "candidate_inspected":
        raise SystemExit(1)

if __name__ == "__main__":
    main()
