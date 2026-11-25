#!/usr/bin/env python3
"""Read-only official ZIP directory inspection. Never extract or approve new PCK."""
from __future__ import annotations
import argparse
import importlib.util
import io
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TAIL_BYTES = 131072

class TailView(io.RawIOBase):
    """Expose the final bytes at their true offset; deny reads outside the tail."""
    def __init__(self, tail, size):
        self.tail, self.size, self.pos = tail, size, 0
    def seekable(self):
        return True
    def readable(self):
        return True
    def tell(self):
        return self.pos
    def seek(self, offset, whence=0):
        pos = offset if whence == 0 else self.pos + offset if whence == 1 else self.size + offset
        if pos < 0:
            raise OSError("Negative archive offset")
        self.pos = pos
        return pos
    def read(self, n=-1):
        start = self.size - len(self.tail)
        if self.pos < start:
            raise OSError("ZIP directory is outside bounded metadata")
        end = self.size if n < 0 else min(self.pos + n, self.size)
        data = self.tail[self.pos-start:end-start]
        self.pos += len(data)
        return data

def parse_tail(tail, size, config, fetch):
    if not 0 < len(tail) <= TAIL_BYTES or size < len(tail) or size > fetch.MAX_ARCHIVE_BYTES:
        raise ValueError("Archive size out of bounds")
    with zipfile.ZipFile(TailView(tail, size)) as archive:
        infos = archive.infolist()
        if len(infos) > config["max_archive_entries"] or sum(i.file_size for i in infos) > config["max_total_uncompressed"]:
            raise ValueError("Archive directory exceeds bounds")
        for i in infos:
            fetch.safe_member(i.filename)
            if i.flag_bits & 1 or (i.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Unsupported member")
        members = [i for i in infos if i.filename == config["pck_member"]]
        if len(members) != 1:
            raise ValueError("Expected exactly one named PCK")
        pck = members[0]
        crc = f"{pck.CRC:08x}"
        return {"archive_size": size, "pck_member": pck.filename,
                "observed_pck_size": pck.file_size, "observed_pck_crc32": crc,
                "pinned_pck_size": config["pck_size"], "pinned_pck_crc32": config["pck_crc32"],
                "matches_pinned_metadata": pck.file_size == config["pck_size"] and crc == config["pck_crc32"],
                "metadata_only": True, "pck_sha256_verified": False,
                "approved_for_build": False}

def load_fetch():
    spec = importlib.util.spec_from_file_location("pinned_fetch", ROOT / "tools/fetch-original-client.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def audit(config, fetch):
    opener, url = fetch.official_download(config)
    with fetch.request(opener, url, headers={"Range": f"bytes=-{TAIL_BYTES}"}) as response:
        match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
        if response.status != 206 or not match:
            raise ValueError("Official CDN did not return bounded range")
        start, end, size = map(int, match.groups())
        tail = response.read(TAIL_BYTES + 1)
    if end != size-1 or start != size-len(tail) or len(tail) != min(size, TAIL_BYTES):
        raise ValueError("Invalid bounded range")
    return parse_tail(tail, size, config, fetch)

def self_test(fetch):
    config = {"pck_member": "MidgardSurvivors.pck", "pck_size": 1,
              "pck_crc32": "00000000", "max_archive_entries": 32,
              "max_total_uncompressed": 2**30}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        z.writestr(config["pck_member"], b"a" * 200000)
    raw = buffer.getvalue()
    report = parse_tail(raw[-TAIL_BYTES:], len(raw), config, fetch)
    assert report["observed_pck_size"] == 200000
    assert not report["matches_pinned_metadata"] and not report["approved_for_build"]
    config["pck_size"] = report["observed_pck_size"]
    config["pck_crc32"] = report["observed_pck_crc32"]
    report = parse_tail(raw[-TAIL_BYTES:], len(raw), config, fetch)
    assert report["matches_pinned_metadata"] and not report["pck_sha256_verified"]
    print("UPSTREAM_METADATA_SELFTEST PASS")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "work/upstream-metadata-review.json")
    args = parser.parse_args()
    fetch = load_fetch()
    if args.self_test:
        self_test(fetch)
        return
    config = json.loads((ROOT / "config/official-client.json").read_text(encoding="utf-8"))
    try:
        report = audit(config, fetch)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        # Do not include URLs or exception text from remote responses.
        report = {"status": "blocked_metadata_review", "error_type": type(error).__name__,
                  "approved_for_build": False, "pck_sha256_verified": False}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        raise SystemExit("Metadata review blocked; no PCK downloaded.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))

if __name__ == "__main__":
    main()
