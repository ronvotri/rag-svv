#!/usr/bin/env python3
"""Apply a pinned publisher update before authored offline patches, never at runtime.

The publisher's updater format is decoded by Godot with its own recovered
updater constant. Neither that constant nor any original resources enter Git.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def inventory(path):
    spec = importlib.util.spec_from_file_location("pck_inventory", ROOT / "tools/inspect_pck.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.inspect(path)


def merge_packs(packs, output):
    """Last pack wins, matching load_resource_pack(replace_files=true)."""
    output = Path(output)
    if output.exists() or output.resolve() in [Path(p).resolve() for p in packs]:
        raise ValueError("Refusing to overwrite a source or existing output")
    entries = {}
    engine = None
    for pack in map(Path, packs):
        info = inventory(pack)
        version = info["godot_version"]
        if engine is not None and version != engine:
            raise ValueError("Pack engine mismatch")
        engine = version
        seen = set()
        for entry in info["entries"]:
            name = entry["path"].removeprefix("res://")
            if name in seen:
                raise ValueError("Duplicate pack path")
            seen.add(name)
            entries[name] = (pack, entry)
    # Godot v2 index, absolute data offsets (flags=0, file_base=0).
    names = {name: name.encode("utf-8") + b"\0" for name in entries}
    names = {name: raw + b"\0" * (-len(raw) % 4) for name, raw in names.items()}
    offset = 100 + sum(4 + len(raw) + 8 + 8 + 16 + 4 for raw in names.values())
    offset += -offset % 16
    records = []
    for name in sorted(entries):
        pack, entry = entries[name]
        records.append((name, pack, entry, offset))
        offset += entry["size"]
        offset += -offset % 16
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("xb") as dst:
            dst.write(b"GDPC" + struct.pack("<I3IIQ", 2, *map(int, engine.split(".")), 0, 0))
            dst.write(b"\0" * 64 + struct.pack("<I", len(records)))
            for name, _, entry, position in records:
                raw = names[name]
                dst.write(struct.pack("<I", len(raw)) + raw)
                dst.write(struct.pack("<QQ", position, entry["size"]))
                dst.write(bytes.fromhex(entry["md5"]) + struct.pack("<I", 0))
            for _, pack, entry, position in records:
                dst.write(b"\0" * (position - dst.tell()))
                md5 = hashlib.md5()
                with pack.open("rb") as src:
                    src.seek(entry["offset"])
                    remaining = entry["size"]
                    while remaining:
                        data = src.read(min(remaining, 1024 * 1024))
                        if not data:
                            raise ValueError("Truncated resource")
                        dst.write(data)
                        md5.update(data)
                        remaining -= len(data)
                if md5.hexdigest() != entry["md5"]:
                    raise ValueError("Resource checksum mismatch")
        inventory(output)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return output


def download_patch(spec, output):
    output = Path(output)
    if not output.exists():
        partial = output.with_suffix(".part")
        request = urllib.request.Request(spec["url"], headers={"User-Agent": "MidgardSVV-offline-build"})
        try:
            with urllib.request.urlopen(request, timeout=120) as src, partial.open("wb") as dst:
                total = 0
                while chunk := src.read(1024 * 1024):
                    total += len(chunk)
                    if total > spec["size"]:
                        raise ValueError("Patch exceeds pinned size")
                    dst.write(chunk)
            verify_patch(partial, spec)
            partial.replace(output)
        finally:
            partial.unlink(missing_ok=True)
    verify_patch(output, spec)
    return output


def verify_patch(path, spec):
    with Path(path).open("rb") as stream:
        signature = hashlib.file_digest(stream, "sha256").hexdigest()
    if Path(path).stat().st_size != spec["size"] or signature != spec["sha256"]:
        raise ValueError("Publisher patch size/SHA-256 mismatch")


def decrypt_patch(godot, recovered, encrypted, output, work):
    source = (Path(recovered) / "scripts/autoload/updater.gd").read_text(encoding="utf-8")
    match = re.search(r'^const PATCH_KEY\s*(?::\s*)?=\s*("[^"\r\n]+")', source, re.M)
    if not match:
        raise ValueError("Publisher updater format changed; review before applying")
    if Path(output).exists():
        raise ValueError("Decrypted pack already exists")
    script = Path(work) / "decode-publisher-update.private.gd"
    script.write_text('extends SceneTree\nfunc _initialize():\n'
        + '\tvar src = FileAccess.open_encrypted_with_pass(' + json.dumps(str(encrypted)) + ', FileAccess.READ, ' + match[1] + ')\n'
        + '\tif src == null:\n\t\tquit(1)\n\t\treturn\n'
        + '\tvar dst = FileAccess.open(' + json.dumps(str(output)) + ', FileAccess.WRITE)\n'
        + '\tif dst == null:\n\t\tquit(2)\n\t\treturn\n'
        + '\tdst.store_buffer(src.get_buffer(src.get_length()))\n\tdst.close()\n\tsrc.close()\n\tquit(0)\n', encoding="utf-8")
    try:
        subprocess.run([str(godot), "--headless", "--path", str(work), "--script", str(script)], check=True)
        inventory(Path(output))
    finally:
        script.unlink(missing_ok=True)
    return Path(output)


def apply_update(godot, base, recovered, work, config=None):
    config = config or json.loads((ROOT / "config/official-update.json").read_text(encoding="utf-8"))
    base_config = json.loads((ROOT / "config/official-client.json").read_text(encoding="utf-8"))
    if config["base_version"] != base_config["project_base_version"]:
        raise ValueError("Update requires a different publisher base")
    if inventory(Path(base))["sha256"] != base_config["pck_sha256"]:
        raise ValueError("Unverified publisher base")
    work = Path(work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    encrypted = download_patch(config, work / "publisher-update.bin")
    patch = decrypt_patch(godot, recovered, encrypted, work / "publisher-update.pck", work)
    return merge_packs([base, patch], work / "MidgardSurvivors-updated.pck")
