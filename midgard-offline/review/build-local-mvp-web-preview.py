#!/usr/bin/env python3
"""Local-only Web MVP preview from an authorized, user-supplied 0.2.11 PCK.

No network fetch, CI upload, deployment or production pin changes.
Requires local Godot 4.7.2, GDRE 2.7.4, official templates and pinned fonts.
The result is experimental: actual browser and repeat-hunt QA still required.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
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
    if args.output.exists() or args.output == ROOT or ROOT in args.output.parents:
        raise ValueError("Choose a new output directory outside the repository")
    version = subprocess.check_output([str(args.godot), "--version"], text=True, timeout=30).strip()
    if not version.startswith(config["godot_version"] + "."):
        raise ValueError("Godot version mismatch")
    # The installer intentionally requires work/ for private preparation.
    work_root = ROOT / "work"
    work_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="local-mvp-web-", dir=work_root) as folder:
        work = Path(folder)
        recovered, project = work / "recovered", work / "prepared"
        run([args.gdre, "--headless", "--recover=" + str(args.pck),
             "--output=" + str(recovered), "--exclude=res://eos/credentials.cfg"])
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
        run([godot, "--headless", "--editor", "--path", project, "--import", "--quit"])
        args.output.mkdir(parents=True, exist_ok=False)
        run([godot, "--headless", "--path", project, "--export-release", "Web Offline", args.output / "index.html"])
        if not (args.output / "index.html").is_file():
            raise ValueError("Web entry file missing")
        (args.output / "PREVIEW-NOT-RELEASED.txt").write_text(
            "Experimental local MVP preview. Browser QA and native return/repeat validation pending.\n"
            "Use a distinct localhost origin, not the existing public site. Do not redistribute.\n"
            "Zeny amount and MVP achievement marks are provisional QA rewards.\n", encoding="utf-8")
    print("Local preview exported; not browser-tested or approved for distribution.")
    print("Serve only locally: python -m http.server 8765 --bind 127.0.0.1 --directory", args.output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("pck", "gdre", "godot", "templates", "fonts", "output"):
        parser.add_argument("--" + name, type=lambda p: Path(p).expanduser().resolve(), required=True)
    parser.add_argument("--authorized-local-client", action="store_true",
                        help="Confirm permission to prepare and run the supplied client locally")
    args = parser.parse_args()
    if not args.authorized_local_client:
        parser.error("An authorized local client is required")
    build(args)


if __name__ == "__main__":
    main()
