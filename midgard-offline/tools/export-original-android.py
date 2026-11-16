#!/usr/bin/env python3
"""Export a prepared private Godot project as a local Android debug test APK.

Requires an Android Offline preset and official Godot/JDK/Android SDK already
available locally. Recovered content is never copied into public source paths.
"""
from pathlib import Path
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import tempfile


def replace_setting(text: str, key: str, value: str) -> str:
    line = key + ' = "' + value.replace('\\', '/').replace('"', '\\"') + '"'
    pattern = '^' + re.escape(key) + r'\s*=.*$'
    return re.sub(pattern, lambda _: line, text, flags=re.MULTILINE) if re.search(pattern, text, re.MULTILINE) else text + '\n' + line + '\n'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--godot', required=True, type=Path)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--java-home', required=True, type=Path)
    parser.add_argument('--android-sdk', required=True, type=Path)
    parser.add_argument('--debug-keystore', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    godot = args.godot.resolve(strict=True)
    project = args.project.resolve(strict=True)
    java_home = args.java_home.resolve(strict=True)
    sdk = args.android_sdk.resolve(strict=True)
    keystore = args.debug_keystore.resolve(strict=True)
    output = (args.output or project.parent / 'original-builds' / 'android' / 'MidgardSVVOffline-DEBUG-TEST.apk').resolve()
    if not (project / 'project.godot').is_file():
        parser.error('Prepared project.godot not found')
    presets = project / 'export_presets.cfg'
    original_presets = presets.read_text(encoding='utf-8')
    match = re.search(r'^\[preset\.(\d+)\]\s*\n(?:(?!\[preset\.).)*?name="Android Offline"', original_presets, re.MULTILINE | re.DOTALL)
    if not match:
        parser.error('Run create-original-android-preset.py first')
    index = match.group(1)
    # Editor settings stay beside the downloaded editor, not in a global profile.
    (godot.parent / '_sc_').touch()
    settings_dir = godot.parent / 'editor_data'
    settings_dir.mkdir(exist_ok=True)
    settings = settings_dir / 'editor_settings-4.7.tres'
    editor_settings = settings.read_text(encoding='utf-8') if settings.exists() else '[gd_resource type="EditorSettings" format=3]\n\n[resource]\n'
    editor_settings = replace_setting(editor_settings, 'export/android/java_sdk_path', str(java_home))
    editor_settings = replace_setting(editor_settings, 'export/android/android_sdk_path', str(sdk))
    settings.write_text(editor_settings, encoding='utf-8')
    output.parent.mkdir(parents=True, exist_ok=True)
    log = output.parent / 'android-export.log'
    executable = '.exe' if os.name == 'nt' else ''
    with tempfile.TemporaryDirectory(prefix='midgard-original-android-') as temporary:
        stage = Path(temporary)
        if stage.resolve().parent != Path(tempfile.gettempdir()).resolve() or not stage.name.startswith('midgard-original-android-'):
            raise SystemExit('Unexpected staging path; refusing temporary export')
        staged_key = stage / 'debug.keystore'
        shutil.copyfile(keystore, staged_key)
        section = '[preset.' + index + '.options]'
        start = original_presets.index(section) + len(section)
        end_match = re.search(r'\n\[preset\.', original_presets[start:])
        end = start + end_match.start() if end_match else len(original_presets)
        options = original_presets[start:end]
        options = replace_setting(options, 'keystore/debug', str(staged_key))
        working_presets = original_presets[:start] + options + original_presets[end:]
        staged_apk = stage / 'MidgardSVVOffline-DEBUG-TEST.apk'
        env = dict(os.environ, JAVA_HOME=str(java_home), ANDROID_HOME=str(sdk), ANDROID_SDK_ROOT=str(sdk),
                   GODOT_ANDROID_KEYSTORE_DEBUG_PATH=str(staged_key),
                   GODOT_ANDROID_KEYSTORE_DEBUG_USER='androiddebugkey',
                   GODOT_ANDROID_KEYSTORE_DEBUG_PASSWORD='android')
        try:
            presets.write_text(working_presets, encoding='utf-8')
            with log.open('w', encoding='utf-8') as stream:
                result = subprocess.run([str(godot), '--headless', '--path', str(project), '--export-debug', 'Android Offline', str(staged_apk)], stdout=stream, stderr=subprocess.STDOUT, env=env)
            if result.returncode or not staged_apk.exists():
                raise SystemExit(f'Godot export failed ({result.returncode}); inspect {log}')
            signer = sdk / 'build-tools' / '36.0.0' / 'lib' / 'apksigner.jar'
            subprocess.run([str(java_home / 'bin' / ('java' + executable)), '-jar', str(signer), 'verify', '--verbose', str(staged_apk)], check=True, env=env)
            badging = subprocess.check_output([str(sdk / 'build-tools' / '36.0.0' / ('aapt' + executable)), 'dump', 'badging', str(staged_apk)], env=env).decode('utf-8', errors='replace')
            (output.parent / 'android-manifest-check.txt').write_text(badging, encoding='utf-8')
            if "package: name='com.votrivalley.midgardsvvoffline'" not in badging:
                raise SystemExit('Unexpected Android application ID; refusing delivery')
            if "name='android.permission.INTERNET'" in badging:
                raise SystemExit('Offline APK unexpectedly requests Internet permission; refusing delivery')
            shutil.copyfile(staged_apk, output)
        finally:
            presets.write_text(original_presets, encoding='utf-8')
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.apk.sha256').write_text(digest + '  ' + output.name + '\n', encoding='utf-8')
    print(f'Original-based private Android test APK: {output}')
    print(f'SHA256: {digest}')
    print('Not a stable signed release; physical-device QA and feature parity acceptance remain required.')


if __name__ == '__main__':
    main()
