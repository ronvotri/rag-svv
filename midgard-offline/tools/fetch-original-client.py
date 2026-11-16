#!/usr/bin/env python3
"""Fetch the publicly free official client and extract only a pinned Godot PCK.

Python standard library only; no account, API key or machine-local game required.
Temporary itch.io cookies/CSRF and signed CDN URLs are never printed or persisted.
The upstream upload may change; size/CRC/SHA mismatch is a hard failure.
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import http.cookiejar
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PAGE = "https://nearq.itch.io/midgard-survivors"
USER_AGENT = "RAG-SVV-official-client-fetch/1.0 (+https://github.com/ronvotri/rag-svv)"


def safe_member(name: str) -> None:
    path = PurePosixPath(name)
    if not name or "\0" in name or "\\" in name or ":" in name or path.is_absolute() or ".." in path.parts:
        raise ValueError("Unsafe ZIP member name; refusing extraction.")


def digest_file(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def allowed_url(url: str) -> bool:
    parsed = urllib.parse.urlsplit(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and not parsed.username and not parsed.password and (
        host == "nearq.itch.io" or host.endswith(".r2.cloudflarestorage.com")
        or host.endswith(".itch.zone") or host.endswith(".hwcdn.net")
    )


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        if not allowed_url(new_url):
            raise ValueError("Official download redirected to an unsupported host.")
        return super().redirect_request(request, file_pointer, code, message, headers, new_url)


def request(opener, url, *, data=None, headers=None):
    if not allowed_url(url):
        raise ValueError("Unsupported official-download URL.")
    options = {"User-Agent": USER_AGENT, **(headers or {})}
    try:
        return opener.open(urllib.request.Request(url, data=data, headers=options), timeout=60)
    except urllib.error.HTTPError as error:
        # HTTPError includes an expiring signed URL in its repr; expose only code.
        raise ValueError(f"Official download HTTP {error.code}; no login or paywall bypass attempted.") from None
    except urllib.error.URLError:
        raise ValueError("Could not reach the official free download endpoint.") from None


class PageFields(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.csrf = None
        self.uploads = set()

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag in {"input", "meta"} and attrs.get("name") == "csrf_token":
            self.csrf = attrs.get("value") or attrs.get("content")
        if attrs.get("data-upload_id"):
            self.uploads.add(attrs["data-upload_id"])


def official_download(config):
    if config["page"] != PAGE or not re.fullmatch(r"\d+", str(config["upload_id"])):
        raise ValueError("Config is not the pinned official game page/upload.")
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()), SafeRedirect())
    with request(opener, PAGE) as response:
        page = response.read(2_000_001)
    if len(page) > 2_000_000:
        raise ValueError("Official page exceeded the metadata limit.")
    html = page.decode("utf-8")
    fields = PageFields()
    fields.feed(html)
    minimum = re.search(r'"min_price"\s*:\s*([0-9]+(?:\.[0-9]+)?)', html)
    if not minimum or float(minimum.group(1)) != 0:
        raise ValueError("The official page is no longer verifiably free; stopping.")
    if str(config["upload_id"]) not in fields.uploads or not fields.csrf:
        raise ValueError("Pinned free upload or anonymous page form changed; review upstream.")
    data = urllib.parse.urlencode({"csrf_token": fields.csrf}).encode("ascii")
    with request(opener, PAGE + "/file/" + str(config["upload_id"]), data=data, headers={
        "Content-Type": "application/x-www-form-urlencoded", "Referer": PAGE, "Origin": "https://nearq.itch.io"
    }) as response:
        body = response.read(65537)
    if len(body) > 65536:
        raise ValueError("Official download metadata exceeded the limit.")
    result = json.loads(body)
    if result.get("errors") or result.get("external") or not allowed_url(str(result.get("url", ""))):
        raise ValueError("Official download was not available as an anonymous free mirrored upload.")
    return opener, result["url"]


def metadata(opener, url, config):
    with request(opener, url, headers={"Range": "bytes=-131072"}) as response:
        if response.status != 206:
            raise ValueError("Official CDN did not honor the small metadata range request.")
        content_range = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
        if not content_range or int(content_range.group(3)) != config["archive_size"]:
            raise ValueError("Upstream archive size changed; refusing a different client.")
        tail = response.read(131073)
    if len(tail) > 131072:
        raise ValueError("Metadata response exceeded the requested range.")
    eocd = tail.rfind(b"PK\x05\x06")
    if eocd < 0 or eocd + 22 > len(tail):
        raise ValueError("ZIP directory footer missing.")
    _, disk, central_disk, disk_count, count, central_size, central_offset, comment = struct.unpack_from("<4s4H2IH", tail, eocd)
    if disk or central_disk or disk_count != count or count > config["max_archive_entries"] or comment:
        raise ValueError("Unsupported ZIP directory layout.")
    at = central_offset - (config["archive_size"] - len(tail))
    if at < 0 or at + central_size != eocd:
        raise ValueError("ZIP directory does not fit the bounded metadata read.")
    entries = []
    for _ in range(count):
        if at + 46 > eocd or tail[at:at+4] != b"PK\x01\x02":
            raise ValueError("Invalid ZIP central directory.")
        flags = struct.unpack_from("<H", tail, at+8)[0]
        crc, compressed, size = struct.unpack_from("<3I", tail, at+16)
        name_size, extra_size, comment_size = struct.unpack_from("<3H", tail, at+28)
        name = tail[at+46:at+46+name_size].decode("utf-8" if flags & 0x800 else "cp437")
        safe_member(name)
        if flags & 1:
            raise ValueError("Encrypted ZIP uploads are not supported.")
        entries.append({"name": name, "size": size, "compressed_size": compressed, "crc32": f"{crc:08x}"})
        at += 46 + name_size + extra_size + comment_size
    if at != eocd:
        raise ValueError("Unexpected ZIP directory bytes.")
    pcks = [item for item in entries if item["name"] == config["pck_member"]]
    if len(pcks) != 1 or pcks[0]["size"] != config["pck_size"] or pcks[0]["crc32"] != config["pck_crc32"]:
        raise ValueError("Official archive PCK metadata does not match the pinned local base.")
    return {"source_page": PAGE, "upload_id": config["upload_id"], "archive_size": config["archive_size"], "entries": entries,
            "pck_sha256_verified": False, "metadata_only": True}


def download_archive(opener, url, destination, config):
    with request(opener, url) as response:
        if response.status != 200 or int(response.headers.get("Content-Length", "0")) != config["archive_size"]:
            raise ValueError("Official archive response size changed.")
        total = 0
        with destination.open("xb") as output:
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > config["archive_size"]:
                    raise ValueError("Archive exceeded pinned size.")
                output.write(chunk)
    if total != config["archive_size"]:
        raise ValueError("Incomplete official archive download.")


def extract_pck(archive, destination, config):
    if archive.stat().st_size != config["archive_size"]:
        raise ValueError("Archive does not match the pinned size.")
    with zipfile.ZipFile(archive) as source:
        infos = source.infolist()
        if len(infos) > config["max_archive_entries"] or sum(item.file_size for item in infos) > config["max_total_uncompressed"]:
            raise ValueError("Archive exceeds extraction safety limits.")
        for item in infos:
            safe_member(item.filename)
            if item.flag_bits & 1 or (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Encrypted ZIP members and symbolic links are not supported.")
        members = [item for item in infos if item.filename == config["pck_member"]]
        if len(members) != 1 or members[0].file_size != config["pck_size"] or f"{members[0].CRC:08x}" != config["pck_crc32"]:
            raise ValueError("Pinned PCK member metadata mismatch.")
        if source.testzip() is not None:
            raise ValueError("ZIP CRC verification failed.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="pck-verify-", dir=destination.parent) as temporary:
            verified = Path(temporary) / "verified.pck"
            digest, total = hashlib.sha256(), 0
            with source.open(members[0]) as member, verified.open("xb") as output:
                while chunk := member.read(1024 * 1024):
                    total += len(chunk)
                    if total > config["pck_size"]:
                        raise ValueError("PCK expanded beyond the pinned size.")
                    output.write(chunk)
                    digest.update(chunk)
            if total != config["pck_size"] or digest.hexdigest() != config["pck_sha256"]:
                raise ValueError("PCK SHA-256 verification failed; a changed client was not accepted.")
            if destination.exists():
                raise ValueError("Output appeared during verification; refusing to replace it.")
            # Exclusive creation also works in restricted Windows workspaces where
            # hard links are forbidden. Never overwrite an output that raced us.
            created = False
            try:
                with destination.open("xb") as target, verified.open("rb") as verified_source:
                    created = True
                    shutil.copyfileobj(verified_source, target, length=1024 * 1024)
            except BaseException:
                if created:
                    destination.unlink(missing_ok=True)
                raise
    return {"source_page": PAGE, "upload_id": config["upload_id"], "pck_size": total, "pck_sha256": digest.hexdigest(),
            "pck_sha256_verified": True, "output": str(destination)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/official-client.json")
    parser.add_argument("--output", type=Path, default=ROOT / "work/client/MidgardSurvivors.pck")
    parser.add_argument("--archive", type=Path, help="Use a previously downloaded official ZIP; no network request")
    parser.add_argument("--metadata", action="store_true", help="Inspect only a 128 KiB public ZIP directory range")
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        if config.get("schema_version") != 1 or not re.fullmatch(r"[0-9a-f]{64}", config.get("pck_sha256", "")):
            raise ValueError("Invalid pinned official client config.")
        output = args.output.resolve()
        if not args.metadata and output.exists():
            if output.stat().st_size != config["pck_size"] or digest_file(output) != config["pck_sha256"]:
                raise ValueError("Existing output does not match the pin; refusing to overwrite it.")
            print(json.dumps({"cached": True, "pck_sha256_verified": True, "output": str(output)}))
            return
        if args.archive:
            if args.metadata:
                raise ValueError("Use --metadata for the public endpoint, or --archive for verified local extraction.")
            result = extract_pck(args.archive.resolve(strict=True), output, config)
        else:
            opener, url = official_download(config)
            inspection = metadata(opener, url, config)
            if args.metadata:
                print(json.dumps(inspection, ensure_ascii=True))
                return
            output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="official-download-", dir=output.parent) as temporary:
                archive = Path(temporary) / "official-client.zip"
                download_archive(opener, url, archive, config)
                result = extract_pck(archive, output, config)
        print(json.dumps(result, ensure_ascii=True))
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, json.JSONDecodeError):
        # Avoid accidental expiring-token disclosure in nested request exceptions.
        import sys
        error = sys.exc_info()[1]
        message = str(error)
        if "https://" in message:
            message = "Official download failed; signed URLs are not logged."
        parser.exit(1, "Error: " + message + "\n")


if __name__ == "__main__":
    main()
