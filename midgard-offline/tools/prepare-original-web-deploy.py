#!/usr/bin/env python3
"""Stage a large Godot Web export for Cloudflare Pages + private R2 binding.

Files above the Pages 25 MiB per-file limit are NOT included in the Pages
deployment. The same-origin Pages Function streams those files from R2.
This prepares files only; it never publishes the original game's assets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

PAGES_FILE_LIMIT = 25 * 1024 * 1024
PROJECT_NAME = "rag-svv-web"
R2_BUCKET = "rag-svv-game-assets"
BUILD_NAME = "MidgardSVV-Original-Offline-Web-TEST"
REQUIRED_SUFFIXES = {".pck", ".wasm", ".js"}
ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stage(source: Path, output: Path, version: str, limit: int = PAGES_FILE_LIMIT) -> dict:
    if not re.fullmatch(r"[a-f0-9]{7,64}", version):
        raise ValueError("Version must be a Git commit hash")
    source = source.resolve(strict=True)
    output = output.resolve()
    if not source.is_dir() or not (source / "index.html").is_file():
        raise ValueError("Expected the original Godot Web export, including index.html")
    if output.exists():
        raise ValueError("Refusing to overwrite an existing deployment directory")
    if output == source or source in output.parents or output in source.parents:
        raise ValueError("Source and destination must be separate")
    if limit > PAGES_FILE_LIMIT or limit < 1:
        raise ValueError("Invalid static asset limit")

    files = [file for file in source.iterdir() if file.is_file()]
    if any(file.is_symlink() for file in source.iterdir()):
        raise ValueError("Web export cannot contain symlinks")
    if not all(any(file.suffix == suffix for file in files) for suffix in REQUIRED_SUFFIXES):
        raise ValueError("Missing the original Godot .pck, .wasm or .js")

    public = output / "public"
    large = output / "r2"
    public.mkdir(parents=True)
    large.mkdir()
    manifest = {
        "version": version,
        "project": PROJECT_NAME,
        "bucket": R2_BUCKET,
        "pages_assets": [],
        "large_assets": [],
    }
    for file in sorted(files):
        name = file.name
        if name.startswith(".") or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            raise ValueError("Unexpected export filename: " + name)
        if name in ("_routes.json", "wrangler.toml", "_worker.js"):
            raise ValueError("Reserved deployment filename: " + name)
        dest_group = "large_assets" if file.stat().st_size > limit else "pages_assets"
        destination = large if dest_group == "large_assets" else public
        shutil.copyfile(file, destination / name)
        manifest[dest_group].append({
            "name": name,
            "size": file.stat().st_size,
            "sha256": sha256(file),
            "content_type": (
                "application/wasm" if file.suffix == ".wasm" else
                "application/octet-stream" if file.suffix == ".pck" else
                "text/javascript" if file.suffix == ".js" else
                "application/octet-stream"
            ),
        })

    # Pages Functions only executes for paths declared here; other requests
    # are served directly from Pages' static CDN without invoking a Worker.
    routes = {
        "version": 1,
        "include": ["/" + item["name"] for item in manifest["large_assets"]],
        "exclude": [],
    }
    (public / "_routes.json").write_text(json.dumps(routes, indent=2) + "\n", encoding="utf-8")
    (public / "_headers").write_text(
        "/index.html\n  Cache-Control: no-cache\n"
        "/*.wasm\n  Content-Type: application/wasm\n",
        encoding="utf-8",
    )
    # Wrangler supports a Pages R2 binding. The bucket is intentionally
    # private; large assets are fetched by same-origin Pages Functions.
    allowed = ",".join(item["name"] for item in manifest["large_assets"])
    configuration = (
        f'name = "{PROJECT_NAME}"\n'
        'compatibility_date = "2026-11-16"\n'
        'pages_build_output_dir = "./public"\n\n'
        '[[r2_buckets]]\n'
        'binding = "GAME_ASSETS"\n'
        f'bucket_name = "{R2_BUCKET}"\n\n'
        '[vars]\n'
        f'ASSET_VERSION = "{version}"\n'
        f'LARGE_ASSETS = "{allowed}"\n'
    )
    (output / "wrangler.toml").write_text(configuration, encoding="utf-8")
    target_functions = output / "functions"
    target_functions.mkdir()
    shutil.copyfile(
        ROOT / "cloudflare/functions/[[path]].js", target_functions / "[[path]].js"
    )
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--source", type=Path, default=ROOT / "work/cloud/artifacts" / BUILD_NAME)
    cli.add_argument("--output", type=Path, default=ROOT / "work/cloud/cloudflare-deploy")
    cli.add_argument("--version", required=True)
    args = cli.parse_args()
    result = stage(args.source, args.output, args.version)
    print(
        "Cloudflare staging ready: "
        f'{len(result["pages_assets"])} Pages assets, '
        f'{len(result["large_assets"])} R2 assets. '
        "Public deployment has NOT been performed."
    )
