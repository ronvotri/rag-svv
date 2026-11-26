#!/usr/bin/env python3
"""Local-only Web MVP preview from an authorized, user-supplied 0.2.11 PCK.

No client network fetch, CI upload, deployment or production pin changes.
Accepts local tools or --auto-tools on Linux (hash-checked official tools/fonts).
The result is experimental: actual browser and repeat-hunt QA still required.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
PREVIEW = '(OS.has_feature("web") and OS.has_feature("svv_mvp_preview") and bool(ProjectSettings.get_setting("application/config/svv_local_mvp_preview", false)))'


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), TOOLS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replace_exact(source, old, new, count=1):
    if source.count(old) != count:
        raise ValueError("Preview patch anchor mismatch: " + old[:80])
    return source.replace(old, new)


def patch_file(path, transform):
    old = path.read_text(encoding="utf-8")
    path.write_text(transform(old), encoding="utf-8", newline="\n")


def configure_preview(project):
    # Only the disposable project is changed. The normal branch and build
    # configuration retain their existing CLI/environment guards.
    preparer = load("prepare-original-offline")
    config = project / "project.godot"
    settings = config.read_text(encoding="utf-8")
    settings = preparer.set_setting(settings, "application", "config/svv_local_mvp_preview", "true")
    settings = preparer.set_setting(settings, "application", "config/custom_user_dir_name", '"VotriValley/MidgardSVVMVPPreview"')
    settings = preparer.set_setting(settings, "application", "config/name", '"Ragnarok: MVP Preview"')
    config.write_text(settings, encoding="utf-8", newline="\n")
    patch_file(project / "scripts/autoload/save.gd", lambda s: replace_exact(
        s, '"profile_offline_test" if "--offline-test" in OS.get_cmdline_user_args() else "profile_offline"',
        '"profile_offline_test" if ("--offline-test" in OS.get_cmdline_user_args() or ' + PREVIEW + ') else "profile_offline"'))
    addon = project / "addons/svv_offline"
    patch_file(addon / "offline_mvp_encounter.gd", lambda s: replace_exact(
        s, 'not OS.get_cmdline_user_args().has("--offline-test")',
        '(not OS.get_cmdline_user_args().has("--offline-test") and not ' + PREVIEW + ')'))

    def event_gate(s):
        cli = 'OS.get_cmdline_user_args().has("--offline-test") and OS.get_cmdline_user_args().has("--offline-mvp-menu-preview")'
        s = replace_exact(s, cli, '((' + cli + ') or ' + PREVIEW + ')')
        s = replace_exact(s, 'OS.get_environment("SVV_WORLD_BOSS_QA_SANDBOX") != "1"',
                          '(OS.get_environment("SVV_WORLD_BOSS_QA_SANDBOX") != "1" and not ' + PREVIEW + ')', 2)
        return replace_exact(s, 'OS.get_cmdline_user_args().has("--offline-mvp-wallet-preview")',
                             '(OS.get_cmdline_user_args().has("--offline-mvp-wallet-preview") or ' + PREVIEW + ')')
    patch_file(addon / "offline_events.gd", event_gate)

    def credit_gate(s):
        cli = 'not args.has("--offline-test") or not args.has("--offline-mvp-menu-preview") or not args.has("--offline-mvp-wallet-preview") or OS.get_environment("SVV_WORLD_BOSS_QA_SANDBOX") != "1"'
        return replace_exact(s, cli, '((' + cli + ') and not ' + PREVIEW + ')', 2)
    patch_file(addon / "offline_mvp_credit_qa.gd", credit_gate)
    # The actual native death observer is required; disappearing nodes alone
    # never count as a kill. This patch stays in the local preview copy.
    enemy = project / "scripts/core/enemy.gd"
    hooked = load("run-world-boss-map-qa").instrument_native_death(enemy.read_text(encoding="utf-8"))
    if hooked is None:
        raise ValueError("Native death observer anchor changed")
    enemy.write_text(hooked, encoding="utf-8", newline="\n")


def run(args, timeout=900):
    subprocess.run([str(x) for x in args], check=True, timeout=timeout)


def build(args):
    cloud = load("cloud-build-original")
    pin = json.loads((ROOT / "review/upstream-0.2.11-pin.json").read_text(encoding="utf-8"))
    config = json.loads((ROOT / "config/cloud-tools.json").read_text(encoding="utf-8"))
    if args.pck.stat().st_size != pin["pck_size"] or cloud.digest(args.pck) != pin["pck_sha256"]:
        raise ValueError("Local PCK differs from reviewed 0.2.11 bytes")
    for name, spec in config["fonts"].items():
        if cloud.digest(args.fonts / name) != spec["sha256"]:
            raise ValueError("Font checksum mismatch: " + name)
    if args.output.exists() or args.output == ROOT.parent or ROOT.parent in args.output.parents:
        raise ValueError("Choose a new output directory outside the repository")
    version = subprocess.check_output([str(args.godot), "--version"], text=True, timeout=30).strip()
    if not version.startswith(config["godot_version"] + "."):
        raise ValueError("Godot version mismatch")
    # The installer intentionally requires work/ for private preparation.
    work_root = ROOT / "work"
    work_root.mkdir(exist_ok=True)
    print("LOCAL_MVP_WEB_STAGE recover", flush=True)
    with tempfile.TemporaryDirectory(prefix="local-mvp-web-", dir=work_root) as folder:
        work = Path(folder)
        recovered, project = work / "recovered", work / "prepared"
        run([args.gdre, "--headless", "--recover=" + str(args.pck),
             "--output=" + str(recovered), "--exclude=res://eos/credentials.cfg"])
        print("LOCAL_MVP_WEB_STAGE prepare", flush=True)
        load("prepare-original-offline").prepare(recovered, project)
        load("install-original-assistant").install(project)
        load("install-start-background").install(project)
        cloud.configure_android_texture_import(project)
        cloud.seed_cache(recovered, project)
        load("localize_original").localize(project, ROOT / "patches/vi-ui.json",
                                           args.fonts / "NotoSans-Regular.ttf", args.fonts / "NotoSans-Bold.ttf")
        shutil.copyfile(args.fonts / "OFL.txt", project / "assets/ro/fonts/NotoSans-OFL.txt")
        configure_preview(project)
        # Use a portable copy so the user's normal Godot editor is untouched.
        godot = work / args.godot.name
        shutil.copy2(args.godot, godot)
        (work / "_sc_").touch()
        cloud.install_web_templates(godot, args.templates, config["godot_version"])
        (project / "export_presets.cfg").unlink(missing_ok=True)
        run([sys.executable, TOOLS / "create-original-presets.py", project, args.templates])
        preset = project / "export_presets.cfg"
        text = preset.read_text(encoding="utf-8")
        # Restrict the feature to Web preset 0, not the Windows preset.
        old = 'custom_features="offline"'
        if text.count(old) != 2:
            raise ValueError("Export preset layout changed")
        preset.write_text(text.replace(old, 'custom_features="offline,svv_mvp_preview"', 1), encoding="utf-8")
        visual_output = getattr(args, "town_visual_output", None)
        review_script = project / "svv_friend_visual_review.gd"
        review_scene = project / "svv_friend_visual_review.tscn"
        if visual_output is not None:
            visual_output.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / "review/friend-town-visual-review.gd", review_script)
            review_scene.write_text(
                '[gd_scene load_steps=2 format=3]\n\n'
                '[ext_resource type="Script" path="res://svv_friend_visual_review.gd" id="1"]\n\n'
                '[node name="FriendVisualReview" type="Node"]\nscript = ExtResource("1")\n',
                encoding="utf-8")
        print("LOCAL_MVP_WEB_STAGE import", flush=True)
        run([godot, "--headless", "--editor", "--path", project, "--import", "--quit"])
        if visual_output is not None:
            try:
                xvfb = shutil.which("xvfb-run")
                if not xvfb:
                    raise ValueError("Xvfb unavailable")
                env = dict(os.environ)
                for variable, suffix in (("XDG_DATA_HOME", "data"), ("XDG_CONFIG_HOME", "config"), ("XDG_CACHE_HOME", "cache")):
                    directory = work / "friend-visual-profile" / suffix
                    directory.mkdir(parents=True, exist_ok=True)
                    env[variable] = str(directory)
                subprocess.run([xvfb, "--auto-servernum", "--server-args=-screen 0 1280x960x24",
                                str(godot), "--path", str(project), "--resolution", "1280x900",
                                "res://svv_friend_visual_review.tscn", "--", "--offline-test",
                                "--friend-visual-output=" + str(visual_output)], env=env, check=True, timeout=100)
                print("LOCAL_MVP_FRIEND_VISUAL completed", flush=True)
            except (OSError, ValueError, subprocess.SubprocessError):
                print("LOCAL_MVP_FRIEND_VISUAL failed", flush=True)
            finally:
                review_script.unlink(missing_ok=True)
                review_scene.unlink(missing_ok=True)
                review_script.with_suffix(".gd.uid").unlink(missing_ok=True)
        args.output.mkdir(parents=True, exist_ok=False)
        print("LOCAL_MVP_WEB_STAGE export", flush=True)
        run([godot, "--headless", "--path", project, "--export-release", "Web Offline", args.output / "index.html"])
        if not (args.output / "index.html").is_file():
            raise ValueError("Web entry file missing")
        (args.output / "PREVIEW-NOT-RELEASED.txt").write_text(
            "Experimental local MVP preview. Browser QA and native return/repeat validation pending.\n"
            "Use a distinct localhost origin, not the existing public site. Do not redistribute.\n"
            "Zeny amount and MVP achievement marks are provisional QA rewards.\n", encoding="utf-8")
    print("Local preview exported; not browser-tested or approved for distribution.")
    print("Serve only locally: python -m http.server 8765 --bind 127.0.0.1 --directory", args.output)


def provision_linux_tools(args):
    if not sys.platform.startswith("linux"):
        raise ValueError("--auto-tools requires Linux (including WSL)")
    cloud = load("cloud-build-original")
    config = json.loads((ROOT / "config/cloud-tools.json").read_text(encoding="utf-8"))
    cache = ROOT / "work" / "local-mvp-tool-cache"
    archives = cache / "archives"
    for name in ("godot_linux", "gdre_linux"):
        archive = cloud.download(config[name], archives / (name + ".zip"))
        cloud.extract_safe(archive, cache / name)
    args.godot = cloud.executable(cache / "godot_linux", "godot")
    args.gdre = cloud.executable(cache / "gdre_linux", "gdre")
    args.templates = cache / "templates"
    archive = cloud.download(config["templates"], archives / "templates.tpz")
    cloud.extract_safe(archive, args.templates, {"web_nothreads_debug.zip", "web_nothreads_release.zip", "windows_debug_x86_64.exe"})
    args.fonts = cache / "fonts"
    for name, spec in config["fonts"].items():
        cloud.download(spec, args.fonts / name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pck", "output"):
        parser.add_argument("--" + name, type=lambda p: Path(p).expanduser().resolve(), required=True)
    for name in ("gdre", "godot", "templates", "fonts"):
        parser.add_argument("--" + name, type=lambda p: Path(p).expanduser().resolve())
    parser.add_argument("--town-visual-output", type=lambda p: Path(p).expanduser().resolve(), help="Optional isolated renderer screenshot review (Linux/Xvfb)")
    parser.add_argument("--auto-tools", action="store_true", help="Download verified build tools/fonts only on Linux/WSL")
    parser.add_argument("--authorized-local-client", action="store_true",
                        help="Confirm permission to prepare and run the supplied client locally")
    args = parser.parse_args()
    if not args.authorized_local_client:
        parser.error("An authorized local client is required")
    if not args.pck.is_file():
        parser.error("Provide your authorized local 0.2.11 PCK")
    if args.auto_tools:
        if any(getattr(args, name) is not None for name in ("gdre", "godot", "templates", "fonts")):
            parser.error("Use --auto-tools or explicit local tool paths, not both")
        pin = json.loads((ROOT / "review/upstream-0.2.11-pin.json").read_text(encoding="utf-8"))
        if args.pck.stat().st_size != pin["pck_size"] or load("cloud-build-original").digest(args.pck) != pin["pck_sha256"]:
            parser.error("Local PCK differs from reviewed 0.2.11 bytes")
        provision_linux_tools(args)
    elif any(getattr(args, name) is None for name in ("gdre", "godot", "templates", "fonts")):
        parser.error("Provide local tools/fonts or use --auto-tools")
    build(args)


if __name__ == "__main__":
    main()
