#!/usr/bin/env python3
"""Reconstruct and build the original-based client on an ephemeral Linux runner.

Only authored patches/configuration live in Git. Original assets are fetched
from the publisher's free download and hash-checked before recovery.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import time
import urllib.request
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def download(spec, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and digest(destination) == spec["sha256"]:
        return destination
    partial = destination.with_suffix(destination.suffix + ".part")
    for attempt in range(3):
        try:
            request = urllib.request.Request(spec["url"], headers={"User-Agent": "MidgardSVV-offline-build"})
            with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as output:
                shutil.copyfileobj(response, output, length=1024*1024)
            if digest(partial) != spec["sha256"]:
                raise ValueError("Checksum mismatch for " + destination.name)
            partial.replace(destination)
            return destination
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2)

def extract_safe(archive, destination, selected=None):
    destination.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive) as source:
        for member in source.infolist():
            relative = PurePosixPath(member.filename)
            if relative.is_absolute() or ".." in relative.parts or "\\" in member.filename:
                raise ValueError("Unsafe archive path")
            if (member.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Archive symlinks are not allowed")
            if member.is_dir():
                continue
            if selected is not None:
                if relative.name not in selected:
                    continue
                target = destination / relative.name
            else:
                target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open(member) as data, target.open("wb") as output:
                shutil.copyfileobj(data, output, length=1024*1024)

def executable(directory, marker):
    candidates = []
    for path in directory.rglob("*"):
        if not path.is_file() or marker.lower() not in path.name.lower():
            continue
        with path.open("rb") as stream:
            if stream.read(4) == b"\x7fELF":
                candidates.append(path)
    if len(candidates) != 1:
        raise ValueError("Expected one Linux executable for " + marker)
    candidates[0].chmod(0o755)
    return candidates[0]

def run(arguments, **options):
    subprocess.run([str(x) for x in arguments], check=True, **options)

def own_tool(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), TOOLS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def seed_cache(source, destination):
    """Reuse recovered binary textures/geometry; do not re-enable extensions."""
    cache = source / ".godot/imported"
    target = destination / ".godot/imported"
    target.mkdir(parents=True, exist_ok=True)
    if cache.is_dir():
        for path in cache.iterdir():
            if path.is_file() and path.suffix in {".scn", ".ctex", ".sample", ".mp3str", ".md5"}:
                shutil.copyfile(path, target / path.name)

def install_web_templates(godot, templates, version):
    """Install the official debug AND release Web templates for portable Godot.

    Godot validates the conventional editor_data location even with a custom
    debug template in export_presets.cfg. _sc_ is placed next to the editor.
    """
    destination = godot.parent / "editor_data" / "export_templates" / (version + ".stable")
    required = ("web_nothreads_debug.zip", "web_nothreads_release.zip")
    for filename in required:
        source = templates / filename
        if not source.is_file():
            raise FileNotFoundError("Official Web export template missing: " + str(source))
    destination.mkdir(parents=True, exist_ok=True)
    for filename in required:
        shutil.copyfile(templates / filename, destination / filename)
    return destination


def configure_android_texture_import(project):
    """Ensure ETC2/ASTC textures are imported before Godot's Android export.

    Windows desktop default settings often leave this option disabled. Modifying
    only the private prepared project keeps the public original-client patch
    cross-platform while satisfying Android export validation.
    """
    preparer = own_tool("prepare-original-offline")
    config = project / "project.godot"
    original = config.read_text(encoding="utf-8")
    changed = preparer.set_setting(original, "rendering", "textures/vram_compression/import_etc2_astc", "true")
    if changed != original:
        config.write_text(changed, encoding="utf-8", newline="\n")
    return changed


def archive_folder(folder, output):
    with ZipFile(output, "w", ZIP_DEFLATED, compresslevel=1) as archive:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                archive.write(path, Path(folder.name) / path.relative_to(folder))

def write_context(project, work, translation):
    """Small text artifacts help a web chat continue without downloading a game."""
    context = work / "context"
    context.mkdir(exist_ok=True)
    localizer = own_tool("localize_original")
    dictionary = localizer.load_translations(ROOT / "patches/vi-ui.json")
    protected = localizer.protected_names(project)
    pending = []
    for entry in localizer.read_po(project / "locale/en.po"):
        english = entry.get("en") or entry["id"]
        if english not in dictionary and english not in protected:
            pending.append({"msgid": entry["id"], "english": english})
    for start in range(0, len(pending), 200):
        (context / f"translation-worklist-{start//200+1:03d}.json").write_text(json.dumps(pending[start:start+200], ensure_ascii=False, indent=2), encoding="utf-8")
    interfaces = {}
    for source in (project / "scripts").rglob("*.gd"):
        # Names only: no function bodies, credentials or private endpoint values.
        names = re.findall(r"^(?:static )?func\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source.read_text(encoding="utf-8"), re.MULTILINE)
        interfaces[source.relative_to(project).as_posix()] = names
    (context / "runtime-functions.json").write_text(json.dumps(interfaces, indent=2), encoding="utf-8")
    (context / "localization-status.json").write_text(json.dumps(translation, indent=2), encoding="utf-8")

def build(target):
    if not sys.platform.startswith("linux"):
        raise SystemExit("This entry point targets Linux GitHub runners. Local Windows helpers remain available.")
    config = json.loads((ROOT / "config/cloud-tools.json").read_text(encoding="utf-8"))
    work = ROOT / "work/cloud"
    work.mkdir(parents=True, exist_ok=True)
    archives = work / "archives"
    tool_dir = work / "tools"
    for name in ("godot_linux", "gdre_linux"):
        path = download(config[name], archives / (name + ".zip"))
        extract_safe(path, tool_dir / name)
    godot = executable(tool_dir / "godot_linux", "godot")
    gdre = executable(tool_dir / "gdre_linux", "gdre")
    # Portable editor settings stay inside this workspace.
    (godot.parent / "_sc_").touch()
    templates_archive = download(config["templates"], archives / "templates.tpz")
    templates = work / "templates"
    selected = {"web_nothreads_debug.zip", "web_nothreads_release.zip", "windows_debug_x86_64.exe", "android_debug.apk"}
    extract_safe(templates_archive, templates, selected)
    if any(not (templates / name).is_file() for name in selected):
        raise ValueError("Official export template entries missing")
    if target == "web":
        install_web_templates(godot, templates, config["godot_version"])
    fonts = work / "fonts"
    for name, spec in config["fonts"].items():
        download(spec, fonts / name)
    client = work / "client/MidgardSurvivors.pck"
    run([sys.executable, TOOLS / "fetch-original-client.py", "--output", client])
    recovered = work / "recovered"
    project = work / "prepared"
    if recovered.exists() or project.exists():
        raise ValueError("Use a fresh runner/work directory; refusing to overwrite a recovered project")
    run([gdre, "--headless", "--recover=" + str(client), "--output=" + str(recovered), "--exclude=res://eos/credentials.cfg"])
    own_tool("prepare-original-offline").prepare(recovered, project)
    run([sys.executable, TOOLS / "diagnose-original-flow.py", project])
    # Web and Android exports both require ETC2/ASTC import to be enabled.
    # Godot 4 can fail Web preset validation with an empty error message
    # when the restored desktop project does not enable these textures.
    if target in ("web", "android"):
        configure_android_texture_import(project)
    seed_cache(recovered, project)
    translation = own_tool("localize_original").localize(project, ROOT / "patches/vi-ui.json", fonts / "NotoSans-Regular.ttf", fonts / "NotoSans-Bold.ttf")
    shutil.copyfile(fonts / "OFL.txt", project / "assets/ro/fonts/NotoSans-OFL.txt")
    own_tool("install-original-assistant").install(project)
    write_context(project, work, translation)
    run([sys.executable, TOOLS / "create-original-presets.py", project, templates])
    run([godot, "--headless", "--editor", "--path", project, "--import", "--quit"])
    run([godot, "--headless", "--path", project, "--", "--offline-test", "--offline-qa"])
    output = work / "artifacts"
    output.mkdir(exist_ok=True)
    notice = "Original-based offline test client. Original game art and code retain their respective owners.\nVietnamese translation and feature parity are not complete; NPC guide is rule-based, not a native LLM.\nKeep save backups. Android output is DEBUG-TEST, not a stable signed update.\n"
    if target == "windows":
        folder = output / "MidgardSVV-Original-Offline-Windows-TEST"
        folder.mkdir(exist_ok=True)
        run([godot, "--headless", "--path", project, "--export-debug", "Windows Offline", folder / "MidgardSVVOffline.exe"])
        (folder / "READ-ME.txt").write_text(notice, encoding="utf-8")
        archive_folder(folder, output / (folder.name + ".zip"))
    elif target == "web":
        folder = output / "MidgardSVV-Original-Offline-Web-TEST"
        folder.mkdir(exist_ok=True)
        run([godot, "--headless", "--path", project, "--export-debug", "Web Offline", folder / "index.html"])
        (folder / "READ-ME.txt").write_text(notice + "Serve through localhost or install the PWA; file:// is unsupported.\n", encoding="utf-8")
        archive_folder(folder, output / (folder.name + ".zip"))
    else:
        java = Path(os.environ["JAVA_HOME"])
        sdk = Path(os.environ.get("ANDROID_SDK_ROOT") or os.environ["ANDROID_HOME"])
        keystore = work / "android-debug.keystore"
        run([java / "bin/keytool", "-genkeypair", "-keystore", keystore, "-storepass", "android", "-alias", "androiddebugkey", "-keypass", "android", "-dname", "CN=Android Debug,O=Android,C=US", "-keyalg", "RSA", "-keysize", "2048", "-validity", "3650"])
        run([sys.executable, TOOLS / "create-original-android-preset.py", project, "--templates", templates, "--debug-keystore", keystore])
        run([sys.executable, TOOLS / "export-original-android.py", "--godot", godot, "--project", project, "--java-home", java, "--android-sdk", sdk, "--debug-keystore", keystore, "--output", output / "MidgardSVV-Original-Offline-Android-DEBUG-TEST.apk"])
    report = {"target": target, "base_pck_sha256": digest(client), "godot": config["godot_version"], "gdre": config["gdre_version"], "translation": translation, "source_runtime_qa": "passed", "full_feature_acceptance": False, "native_llm": False}
    (output / "BUILD_STATUS.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    sums = [digest(path) + "  " + path.name for path in output.iterdir() if path.is_file()]
    (output / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    print("Original-based cloud build completed:", target)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=["windows", "web", "android"], required=True)
    build(parser.parse_args().target)
