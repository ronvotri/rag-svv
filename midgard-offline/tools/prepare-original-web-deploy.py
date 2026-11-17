#!/usr/bin/env python3
"""Prepare the original Godot Web export for Cloudflare Pages Free (no R2).

Splits exported .pck/.wasm or any oversized file into versioned <= 16 MiB
static parts. A browser Service Worker streams the original URL transparently.
No assets or third-party game data are committed to this public repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

PAGES_FILE_LIMIT = 25 * 1024 * 1024
PART_BYTES = 16 * 1024 * 1024
MAX_FREE_FILES = 20_000
PROJECT_NAME = "rag-svv-web"
BUILD_NAME = "MidgardSVV-Original-Offline-Web-TEST"
ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for part in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def _split(source: Path, public: Path, version: str, part_bytes: int) -> dict:
    name = source.name
    full_hash = hashlib.sha256()
    pieces = []
    with source.open("rb") as reader:
        index = 0
        while True:
            payload = reader.read(part_bytes)
            if not payload:
                break
            full_hash.update(payload)
            # Content-addressed chunk URLs survive code-only updates. If a
            # 16 MiB piece does not change, browser/cache need not download
            # it again when the next version of the game is published.
            piece_hash = hashlib.sha256(payload).hexdigest()
            relative = f"parts/{piece_hash}/{name}/{index:04d}.bin"
            destination = public / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
            pieces.append({
                "path": relative,
                "size": len(payload),
                "sha256": piece_hash,
            })
            index += 1
    if not pieces or sum(x["size"] for x in pieces) != source.stat().st_size:
        raise ValueError("Split size mismatch: " + name)
    return {
        "name": name,
        "size": source.stat().st_size,
        "sha256": full_hash.hexdigest(),
        "type": ("application/wasm" if source.suffix == ".wasm" else
                 "text/javascript" if source.suffix == ".js" else
                 "application/octet-stream"),
        "parts": pieces,
    }


def stage(source: Path, output: Path, version: str,
          limit: int = PAGES_FILE_LIMIT, part_bytes: int = PART_BYTES) -> dict:
    if not re.fullmatch(r"[a-f0-9]{7,64}", version):
        raise ValueError("Version must be a Git commit hash")
    if not (0 < part_bytes < limit <= PAGES_FILE_LIMIT):
        raise ValueError("Expected chunk size < Pages file size limit <= 25 MiB")
    source = source.resolve(strict=True)
    output = output.resolve()
    if not source.is_dir() or not (source / "index.html").is_file():
        raise ValueError("Expected Godot Web export containing index.html")
    if output.exists() or source == output or source in output.parents or output in source.parents:
        raise ValueError("Output must be a new, separate directory")
    if any(p.is_symlink() or not p.is_file() for p in source.iterdir()):
        raise ValueError("Unexpected symlink or subdirectory in Web export")
    files = sorted(source.iterdir())
    if not {".pck", ".wasm", ".js"}.issubset({p.suffix for p in files}):
        raise ValueError("Missing required Godot JS/WASM/PCK export files")

    public = output / "public"
    public.mkdir(parents=True)
    manifest = {
        "schema": 1, "project": PROJECT_NAME, "version": version,
        "static_assets": [], "large_assets": {},
    }
    reserved = {"_headers", "_redirects", "_routes.json", "_worker.js",
                "godot-split-sw.js", "asset-map.json", "game.html", "fullscreen-toggle.js",
                "game-entry-guard.js"}
    for file in files:
        name = file.name
        if (name.startswith(".") or not re.fullmatch(r"[A-Za-z0-9_.-]+", name)
                or name in reserved):
            raise ValueError("Unsafe or reserved Web file: " + name)
        destination_name = "game.html" if name == "index.html" else name
        if file.stat().st_size > limit:
            if name == "index.html":
                raise ValueError("Godot HTML entry cannot exceed Pages file limit")
            manifest["large_assets"][destination_name] = _split(
                file, public, version, part_bytes
            )
        else:
            destination = public / destination_name
            if name == "index.html":
                # Add a fullscreen control to the real Godot page, not the
                # temporary bootstrap page; it must survive navigation.
                html = file.read_text(encoding="utf-8")
                if html.lower().count("</body>") != 1:
                    raise ValueError("Unexpected original Godot HTML body")
                # Directly opening /game.html bypasses the bootstrap and causes
                # the multi-hundred-MiB Godot loader to hang without its SW.
                # Place the guard before Godot's own HEAD scripts execute.
                match = re.search(r"<head(?:\s[^>]*)?>", html, flags=re.IGNORECASE)
                if not match:
                    raise ValueError("Expected original Godot HTML head")
                html = (html[:match.end()] +
                        '\n<script src="./game-entry-guard.js"></script>\n' +
                        html[match.end():])
                html = re.sub(
                    r"</body>",
                    '<script src="./fullscreen-toggle.js" defer></script>\\n</body>',
                    html, count=1, flags=re.IGNORECASE,
                )
                destination.write_text(html, encoding="utf-8")
            else:
                shutil.copyfile(file, destination)
            manifest["static_assets"].append({
                "name": destination_name,
                "size": destination.stat().st_size,
                "sha256": sha256(destination),
            })

    asset_map = {
        "schema": 1, "version": version,
        "large_assets": manifest["large_assets"],
    }
    (public / "asset-map.json").write_text(
        json.dumps(asset_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    worker = (ROOT / "cloudflare/godot-split-sw.js").read_text(encoding="utf-8")
    # Changing the SW bytes on every deployment forces browsers to activate
    # the manifest matching the current versioned chunk paths.
    (public / "godot-split-sw.js").write_text(
        "// Ragnarok Pages build: " + version + "\n" + worker, encoding="utf-8"
    )
    shutil.copyfile(ROOT / "cloudflare/fullscreen-toggle.js", public / "fullscreen-toggle.js")
    shutil.copyfile(ROOT / "cloudflare/game-entry-guard.js", public / "game-entry-guard.js")
    shutil.copyfile(ROOT / "cloudflare/pages-bootstrap.html", public / "index.html")
    (public / "_headers").write_text(
        "/index.html\n  Cache-Control: no-cache\n"
        "/game.html\n  Cache-Control: no-cache\n"
        "/game-entry-guard.js\n  Cache-Control: no-cache\n"
        "/fullscreen-toggle.js\n  Cache-Control: no-cache\n"
        "/asset-map.json\n  Cache-Control: no-store\n"
        "/godot-split-sw.js\n  Cache-Control: no-cache\n"
        "/parts/*\n  Cache-Control: public, max-age=31536000, immutable\n"
        "/*.wasm\n  Content-Type: application/wasm\n",
        encoding="utf-8",
    )
    static_files = [p for p in public.rglob("*") if p.is_file()]
    # Tests may lower the split threshold. Pages itself always allows 25 MiB
    # for wrapper HTML, manifest, SW and all other static deployment files.
    too_large = [str(p.relative_to(public)) for p in static_files if p.stat().st_size > PAGES_FILE_LIMIT]
    if too_large:
        raise ValueError("Asset(s) exceed the Pages single-file limit: " + repr(too_large))
    if len(static_files) > MAX_FREE_FILES:
        raise ValueError("Cloudflare Pages Free exceeds 20,000 files")
    manifest["deployment_files"] = len(static_files)
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--source", type=Path, default=ROOT / "work/cloud/artifacts" / BUILD_NAME)
    cli.add_argument("--output", type=Path, default=ROOT / "work/cloud/cloudflare-deploy")
    cli.add_argument("--version", required=True)
    args = cli.parse_args()
    result = stage(args.source, args.output, args.version)
    print("Pages Free staged:", result["deployment_files"], "files,",
          len(result["large_assets"]), "streamed assets;",
          "R2 is NOT used. This command does not publish the game.")
