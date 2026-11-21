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

def find_untranslated_prose_candidates(pending):
    """Surface possible missed dialogue/help text, not short proper names.

    This is an advisory filter, not a claim that every short fallback is
    translated or that long named skills should be converted. A manual QA
    review decides whether a candidate is actual prose.
    """
    candidates = []
    for entry in pending:
        english = str(entry.get("english", ""))
        words = re.findall(r"[A-Za-zÀ-ỹ]+", english)
        if len(english) >= 45 and len(words) >= 8:
            candidates.append(entry)
    return candidates


def inspect_town_visual_api(project):
    """Report the recovered town renderer's API without shipping game assets.

    Metadata and tiny filtered construction hints are enough to choose the
    original Acolyte sprite factory; do not publish recovered full sources.
    """
    modules = {
        "scripts/core/town.gd": {"setup", "_town_npcs", "npc_node",
                                 "_at", "_draw_member", "_sprite_args", "_party_hero"},
        "scripts/core/town_crowd.gd": {"setup", "_spawn", "_collect_looks",
                                       "_place_sign", "_at"},
        "scripts/autoload/ro_assets.gd": {"styled_character", "_gendered", "_load_part", "_recolored_part", "sprite", "has_sprite"},
        "scripts/ro/ro_sprite.gd": {"_init", "get_frame", "compose_image"},
        "scripts/ro/ro_visual.gd": {"setup", "play", "face", "_ready"},
        "scripts/core/player.gd": {"_build_visual", "setup"},
    }
    report = {"schema": 1, "modules": {}, "acolyte_asset_paths": [],
              "metadata_only": True,
              "rare_npc_composition_review": {
                  "state": "body_frames_only_head_hair_unverified",
                  "full_character_factory_to_inspect": "RoAssets.styled_character",
                  "town_placement_approved": False,
              }}
    visible = re.compile(r"(?i)\b(?:Sprite3D|AnimatedSprite3D|ROSprite|RoSprite|"
                         r"SpriteFrames|ImageTexture|AtlasTexture|Texture2D|"
                         r"sprite|draw_member|draw_npc|styled_character|head|hair|body|gender|look|set_texture|\.texture|"
                         r"instantiate|\.load\(|\.new\(|npc_node)\b")
    for filename, methods in modules.items():
        path = project / filename
        if not path.is_file():
            report["modules"][filename] = {"missing": True}
            continue
        body = path.read_text(encoding="utf-8")
        headers = list(re.finditer(
            r"(?m)^(?:static )?func\s+([A-Za-z_][\w]*)\s*\([^\n]*\)[^\n]*:", body))
        matches = {}
        for index, entry in enumerate(headers):
            method = entry.group(1)
            if method not in methods:
                continue
            end = headers[index + 1].start() if index + 1 < len(headers) else len(body)
            fragment = body[entry.end():end]
            hints = [line.strip()[:220] for line in fragment.splitlines()
                     if visible.search(line) and "http" not in line.lower()]
            matches[method] = {
                "signature": entry.group(0).strip()[:300],
                "visual_hints": hints[:18],
                "node_types": sorted(set(re.findall(
                    r"\b(?:Sprite3D|AnimatedSprite3D|Node3D|MeshInstance3D|"
                    r"ROSprite|RoSprite|SpriteFrames|ImageTexture)\b", fragment))),
            }
        report["modules"][filename] = {"methods": matches}
    assets = []
    for root in (project / "assets", project / "scenes"):
        if root.is_dir():
            for path in root.rglob("*"):
                if path.is_file() and re.search(r"(?i)(acolyte|sprite.*job|job.*sprite)", path.name):
                    assets.append(path.relative_to(project).as_posix())
    report["acolyte_asset_paths"] = sorted(assets)[:80]
    report["acolyte_asset_path_count"] = len(assets)
    return report


def write_context(project, work, translation):
    """Small text artifacts help a web chat continue without downloading a game."""
    context = work / "context"
    context.mkdir(exist_ok=True)
    localizer = own_tool("localize_original")
    dictionary = localizer.load_translations(ROOT / "patches/vi-ui.json")
    protected = localizer.protected_names(project)
    source_entries = localizer.read_po(project / "locale/en.po")
    # Protect the current QA 141 translation pass from typos in English keys:
    # every newly translated source must exist in this recovered en.po version.
    source_strings = {entry.get("en") or entry["id"] for entry in source_entries}
    new_sources = set()
    for number in range(21, 62):
        file = ROOT / "patches" / f"vi-ui-batch-{number:03d}.json"
        entries = json.loads(file.read_text(encoding="utf-8"))
        new_sources.update(entries)
    not_found = sorted(new_sources - source_strings)
    missing_translation = sorted(key for key in new_sources if key not in dictionary)
    recent_audit = {
        "batch_range": "021-061",
        "new_unique_strings": len(new_sources),
        "found_in_catalog": len(new_sources) - len(not_found),
        "unmatched_source_keys": not_found,
        "missing_translation_keys": missing_translation,
        "passed": not not_found and not missing_translation,
    }
    (context / "recent-localization-qa.json").write_text(
        json.dumps(recent_audit, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if not recent_audit["passed"]:
        raise ValueError("Recent localization has mismatched source keys: "
                         + repr(not_found[:8] + missing_translation[:8]))
    collection_audit = localizer.collection_translation_audit(source_entries, dictionary)
    (context / "collection-translation-qa.json").write_text(
        json.dumps(collection_audit, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if not collection_audit["passed"]:
        raise ValueError("Collections screen still has untranslated descriptions: "
                         + repr(collection_audit["untranslated"][:6]))
    pending = []
    for entry in source_entries:
        english = entry.get("en") or entry["id"]
        if english not in dictionary and english not in protected:
            pending.append({"msgid": entry["id"], "english": english})
    for start in range(0, len(pending), 200):
        (context / f"translation-worklist-{start//200+1:03d}.json").write_text(json.dumps(pending[start:start+200], ensure_ascii=False, indent=2), encoding="utf-8")
    # Track long, potentially player-facing prose separately from names and
    # short stat labels. This must remain advisory: a boss skill can be long.
    review = {
        "catalog_entries": len(source_entries),
        "unprotected_fallback_entries": len(pending),
        "likely_untranslated_prose": find_untranslated_prose_candidates(pending),
        "largest_fallback_chars": max((len(item["english"]) for item in pending), default=0),
        "policy": "Candidate prose requires manual review; names, skills, items and music stay English.",
    }
    (context / "untranslated-prose-review.json").write_text(
        json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    town_api = inspect_town_visual_api(project)
    (context / "town-rendering-api.json").write_text(
        json.dumps(town_api, ensure_ascii=False, indent=2),
        encoding="utf-8")
    # The Windows export can take longer than metadata recovery. Surface the
    # minimum composition API contract in streaming CI logs before export,
    # without publishing recovered code, assets or claiming NPC approval.
    factory = town_api["modules"].get("scripts/autoload/ro_assets.gd", {})
    styled = factory.get("methods", {}).get("styled_character", {})
    print("RARE_NPC_COMPOSITION_FACTORY " + json.dumps({
        "signature": styled.get("signature", "missing"),
        "layer_hint_count": len(styled.get("visual_hints", [])),
        "metadata_only": True,
        "town_placement_approved": False,
    }, ensure_ascii=False), flush=True)
    # Inspector for the exact recovered character-selection background.
    # Only sampled UI-construction lines, not the publisher's full source.
    # Avoid replacing the wrong scene or adding a front-layer image over buttons.
    menus_source = (project / "scripts/ui/menus.gd").read_text(encoding="utf-8")
    match = re.search(r"(?m)^func show_class_select\\([^\\n]*\\)[^\\n]*:", menus_source)
    if match:
        end = re.search(r"(?m)^func [A-Za-z_]", menus_source[match.end():])
        block = menus_source[match.start():match.end() + end.start() if end else len(menus_source)]
        hints = []
        for index, line in enumerate(block.splitlines(), 1):
            if re.search(r"bg|back|texture|TextureRect|ColorRect|screen|layer|image|\.png|\.webp|\.jpg|add_child|Panel", line, re.I):
                hints.append({"relative_line": index, "code": line[:260]})
        (context / "character-select-background-hints.json").write_text(
            json.dumps({"method": "show_class_select", "ui_hints": hints[:130]},
                       ensure_ascii=False, indent=2), encoding="utf-8"
        )
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
    # User-authored title art replaces the old character-selection wallpaper
    # after the original menu builds. It does not change the game scene or save.
    own_tool("install-start-background").install(project)
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
    # Capture authentic recovered-client QA stdout for machine-readable
    # rare-job preflight evidence. Preserve the full log in Actions output.
    qa_command = [str(x) for x in (godot, "--headless", "--path", project,
                                   "--", "--offline-test", "--offline-qa")]
    qa_process = subprocess.run(qa_command, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                encoding="utf-8", errors="replace")
    print(qa_process.stdout, end="")
    output = work / "artifacts"
    output.mkdir(exist_ok=True)
    rare_report = own_tool("rare_job_qa_report").from_log(qa_process.stdout)
    (output / "RARE_JOB_QA.json").write_text(
        json.dumps(rare_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    if qa_process.returncode:
        raise subprocess.CalledProcessError(qa_process.returncode, qa_command)
    if not rare_report["runtime_probe_completed"]:
        raise RuntimeError("Rare NPC QA marker missing/invalid: " + rare_report["reason"])
    # Optional proof for the staging Windows build: real Godot viewport PNGs
    # from the recovered town and its ORIGINAL sprite assets. Never label the
    # ordinary headless test as an approval of prop collisions or mobile UI.
    visual_qa = "not_applicable"
    rare_visual_qa = "not_applicable"
    rare_motion_qa = "not_applicable"
    rare_composed_qa = "not_applicable"
    if target == "windows":
        xvfb = shutil.which("xvfb-run")
        visual_qa = "xvfb_missing" if not xvfb else "not_captured"
        if xvfb:
            visual_folder = output / "Prontera-Visual-QA"
            visual_folder.mkdir(exist_ok=True)
            # Fast independent run: do NOT depend on the full Town/phone/combat
            # screenshot sequence, which may exceed its 150s timeout.
            try:
                run([
                    xvfb, "--auto-servernum",
                    "--server-args=-screen 0 1280x1024x24",
                    godot, "--path", project, "--",
                    "--offline-test", "--offline-visual", "--rare-only",
                    "--offline-output=" + str(visual_folder),
                ], timeout=75)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
                print("RARE_NPC_VISUAL fast capture failed:", error, file=sys.stderr)

            rare_expected = {
                "rare-frame-gunslinger.png", "rare-frame-gunslinger_f.png",
                "rare-frame-taekwon.png", "rare-frame-taekwon_f.png",
                "rare-frame-ninja.png", "rare-frame-ninja_f.png",
                "rare-frame-summoner.png", "rare-frame-summoner_f.png",
            }
            found_rare = {p.name for p in visual_folder.glob("*.png")}
            rare_found = sorted(rare_expected.intersection(found_rare))
            rare_validation = own_tool("rare_job_qa_report").validate_visual_frames(visual_folder)
            # Independent motion evidence: original RoVisual.play/face sampled
            # off-map. This report NEVER grants Town or eight-direction approval.
            motion_validation = own_tool("rare_job_motion_report").validate_motion_frames(visual_folder)
            rare_motion_qa = motion_validation["status"]
            composition_validation = own_tool("rare_job_composition_report").validate_composed_frames(visual_folder)
            rare_composed_qa = composition_validation["status"]
            composition_path = output / "RARE_NPC_COMPOSED_CHECK.json"
            composition_path.write_text(
                json.dumps(composition_validation, indent=2) + "\n", encoding="utf-8")
            motion_path = output / "RARE_NPC_MOTION_CHECK.json"
            motion_path.write_text(json.dumps(motion_validation, indent=2) + "\n", encoding="utf-8")
            rare_visual_qa = rare_validation["status"]
            validation_path = output / "RARE_NPC_VISUAL_CHECK.json"
            validation_path.write_text(json.dumps(rare_validation, indent=2) + "\n", encoding="utf-8")
            motion_found = sorted(visual_folder.glob("rare-motion-*.png"))
            composed_found = sorted(visual_folder.glob("rare-composed-*.png"))
            if rare_found or motion_found or composed_found:
                # Upload original frames and explicit validation result even
                # if subsequent full-Town screenshot QA times out.
                rare_zip = output / "Rare-NPC-Sprite-QA.zip"
                with ZipFile(rare_zip, "w", ZIP_DEFLATED) as archive:
                    for name in rare_found:
                        archive.write(visual_folder / name, name)
                    rare_metadata = visual_folder / "RARE_NPC_VISUAL.json"
                    if rare_metadata.is_file():
                        archive.write(rare_metadata, rare_metadata.name)
                    archive.write(validation_path, validation_path.name)
                    for motion_frame in motion_found:
                        archive.write(motion_frame, motion_frame.name)
                    motion_manifest = visual_folder / "RARE_NPC_MOTION.json"
                    if motion_manifest.is_file():
                        archive.write(motion_manifest, motion_manifest.name)
                    archive.write(motion_path, motion_path.name)
                    for composed_frame in composed_found:
                        archive.write(composed_frame, composed_frame.name)
                    composed_manifest = visual_folder / "RARE_NPC_COMPOSED.json"
                    if composed_manifest.is_file():
                        archive.write(composed_manifest, composed_manifest.name)
                    archive.write(composition_path, composition_path.name)
            print("RARE_NPC_COMPOSED_STATUS", rare_composed_qa)
            print("RARE_NPC_COMPOSED_CHECK", composition_validation["reason"])
            print("RARE_NPC_VISUAL_STATUS", rare_visual_qa)
            print("RARE_NPC_MOTION_STATUS", rare_motion_qa)
            print("RARE_NPC_MOTION_CHECK", motion_validation["reason"])
            print("RARE_NPC_VISUAL_CHECK", rare_validation["reason"])
            if rare_visual_qa != "frames_ready_for_manual_review":
                print("RARE_NPC_VISUAL_MISSING", sorted(rare_expected - found_rare))

            # Separate optional full scene QA. Failure here must NEVER erase
            # or prevent uploading the independent source sprite evidence.
            try:
                run([
                    xvfb, "--auto-servernum",
                    "--server-args=-screen 0 1280x1024x24",
                    godot, "--path", project, "--",
                    "--offline-test", "--offline-visual",
                    "--offline-output=" + str(visual_folder),
                ], timeout=150)
                expected = {
                    "original-town.png",
                    "town-npcs-390x844.png",
                    "town-npcs-844x390.png",
                }
                found = {p.name for p in visual_folder.glob("*.png")}
                if expected.issubset(found):
                    visual_qa = "screenshots_ready_for_manual_review"
                else:
                    visual_qa = "incomplete_screenshots"
                    print("VISUAL_QA MISSING", sorted(expected - found))
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
                visual_qa = "capture_failed"
                print("VISUAL_QA capture failed; Windows build remains separate:", error, file=sys.stderr)
            finally:
                if any(visual_folder.glob("original-*.png")) or any(visual_folder.glob("town-*.png")):
                    archive_folder(visual_folder, output / "Prontera-Visual-QA.zip")
        print("VISUAL_QA STATUS", visual_qa)
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
        # The Godot debug Web runtime adds overhead on mobile browsers; keep
        # headless gameplay QA separate and ship the optimized release template.
        run([godot, "--headless", "--path", project, "--export-release", "Web Offline", folder / "index.html"])
        (folder / "READ-ME.txt").write_text(notice + "Serve through localhost or install the PWA; file:// is unsupported.\n", encoding="utf-8")
        archive_folder(folder, output / (folder.name + ".zip"))
    else:
        java = Path(os.environ["JAVA_HOME"])
        sdk = Path(os.environ.get("ANDROID_SDK_ROOT") or os.environ["ANDROID_HOME"])
        keystore = work / "android-debug.keystore"
        run([java / "bin/keytool", "-genkeypair", "-keystore", keystore, "-storepass", "android", "-alias", "androiddebugkey", "-keypass", "android", "-dname", "CN=Android Debug,O=Android,C=US", "-keyalg", "RSA", "-keysize", "2048", "-validity", "3650"])
        run([sys.executable, TOOLS / "create-original-android-preset.py", project, "--templates", templates, "--debug-keystore", keystore])
        run([sys.executable, TOOLS / "export-original-android.py", "--godot", godot, "--project", project, "--java-home", java, "--android-sdk", sdk, "--debug-keystore", keystore, "--output", output / "MidgardSVV-Original-Offline-Android-DEBUG-TEST.apk"])
    report = {"target": target, "base_pck_sha256": digest(client), "godot": config["godot_version"], "gdre": config["gdre_version"], "translation": translation, "source_runtime_qa": "passed", "full_feature_acceptance": False, "native_llm": False, "prontera_visual_qa": visual_qa, "rare_job_visual_qa": rare_visual_qa, "rare_job_motion_qa": rare_motion_qa, "rare_job_composition_qa": rare_composed_qa}
    (output / "BUILD_STATUS.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    sums = [digest(path) + "  " + path.name for path in output.iterdir() if path.is_file()]
    (output / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    print("Original-based cloud build completed:", target)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=["windows", "web", "android"], required=True)
    build(parser.parse_args().target)
