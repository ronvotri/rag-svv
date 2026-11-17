#!/usr/bin/env python3
"""Inspect a current, anonymous official download without modifying the PCK pin.

Outputs verifiable archive and game-PCK metadata only. Never uploads, publishes,
or persists the proprietary asset. The official downloader remains fail-closed
until the new pinned PCK is explicitly reviewed and updated.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MAX_UNCOMPRESSED_INSPECTION = 2 * 1024 * 1024 * 1024
MAX_PCK_INSPECTION = 1024 * 1024 * 1024
FETCHER = ROOT / "tools/fetch-original-client.py"
_spec = importlib.util.spec_from_file_location("svv_fetch_original_client", FETCHER)
_fetcher = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fetcher)


def inspect_archive(path: Path, config: dict) -> dict:
    if not 0 < path.stat().st_size <= _fetcher.MAX_ARCHIVE_BYTES:
        raise ValueError("Official archive outside the accepted size range")
    with zipfile.ZipFile(path) as packed:
        entries = packed.infolist()
        if len(entries) > config["max_archive_entries"]:
            raise ValueError("Official ZIP has too many members")
        if sum(item.file_size for item in entries) > MAX_UNCOMPRESSED_INSPECTION:
            raise ValueError("Official ZIP has excessive uncompressed content")
        for item in entries:
            _fetcher.safe_member(item.filename)
            if item.flag_bits & 1 or (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Encrypted or symlink ZIP entries are unsupported")
        pcks = [entry for entry in entries if entry.filename == config["pck_member"]]
        if len(pcks) != 1:
            raise ValueError("Expected exactly one original PCK in the ZIP")
        pck = pcks[0]
        digest = hashlib.sha256()
        amount = 0
        with packed.open(pck) as source:
            while chunk := source.read(1024 * 1024):
                amount += len(chunk)
                if amount > MAX_PCK_INSPECTION:
                    raise ValueError("PCK exceeds the uncompressed safety bound")
                digest.update(chunk)
        if amount != pck.file_size:
            raise ValueError("Incomplete PCK read")
        if packed.testzip() is not None:
            raise ValueError("Official ZIP failed CRC validation")
        return {
            "upload_id": str(config["upload_id"]),
            "archive_size": path.stat().st_size,
            "pck_member": pck.filename,
            "pck_size": amount,
            "pck_crc32": f"{pck.CRC:08x}",
            "pck_sha256": digest.hexdigest(),
            "old_pck_sha256": config["pck_sha256"],
            "pck_changed": digest.hexdigest() != config["pck_sha256"],
            "security": "ZIP members, CRC and PCK SHA-256 verified",
        }


def main() -> None:
    config = json.loads((ROOT / "config/official-client.json").read_text(encoding="utf-8"))
    opener, url = _fetcher.official_download(config)
    # This inspection does not trust the old ZIP size; a source update changes it.
    # Verify only the CDN's response length and fail if it exceeds the safety cap.
    with _fetcher.request(opener, url, headers={"Range": "bytes=-131072"}) as response:
        if response.status != 206:
            raise ValueError("Official CDN cannot serve the bounded ZIP tail request")
        match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
        if not match:
            raise ValueError("Official CDN returned malformed range metadata")
        first, last, archive_size = map(int, match.groups())
        if (not 0 < archive_size <= _fetcher.MAX_ARCHIVE_BYTES or last != archive_size - 1
                or first != max(0, archive_size - 131072)):
            raise ValueError("Official CDN returned an inconsistent archive range")
    with tempfile.TemporaryDirectory(prefix="svv-upstream-inspect-") as directory:
        path = Path(directory) / "official-client.zip"
        _fetcher.download_archive(opener, url, path, archive_size)
        report = inspect_archive(path, config)
    print("OFFICIAL_UPSTREAM_METADATA=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
