#!/usr/bin/env python3
"""Append a local Android debug export preset to a recovered private Godot project.

Contains configuration only, no recovered game source or assets. Run only against
the ignored local project, after the offline preparation and localization steps.
"""
from pathlib import Path
import argparse
import re


def quoted(value: str) -> str:
    return '"' + value.replace('\\', '/').replace('"', '\\"') + '"'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('--templates', required=True, type=Path)
    parser.add_argument('--debug-keystore', required=True, type=Path)
    args = parser.parse_args()
    project = args.project.resolve(strict=True)
    if not (project / 'project.godot').is_file():
        parser.error('project.godot not found')
    template = (args.templates / 'android_debug.apk').resolve(strict=True)
    keystore = args.debug_keystore.resolve(strict=True)
    path = project / 'export_presets.cfg'
    current = path.read_text(encoding='utf-8') if path.exists() else ''
    if 'name="Android Offline"' in current:
        parser.error('Android Offline preset already exists; inspect it before editing')
    indices = [int(x) for x in re.findall(r'^\[preset\.(\d+)\]', current, re.MULTILINE)]
    index = max(indices, default=-1) + 1
    preset = f'''

[preset.{index}]

name="Android Offline"
platform="Android"
runnable=false
advanced_options=true
dedicated_server=false
custom_features="offline"
export_filter="all_resources"
include_filter="*.json,*.gat,*.bin,*.po,*.txt"
exclude_filter=".autoconverted/*,*.log,*.private.json"
export_path="../original-builds/android/MidgardSVVOffline-DEBUG-TEST.apk"
script_export_mode=2

[preset.{index}.options]

custom_template/debug={quoted(str(template))}
custom_template/release=""
gradle_build/use_gradle_build=false
gradle_build/min_sdk="26"
gradle_build/target_sdk="36"
architectures/armeabi-v7a=false
architectures/arm64-v8a=true
architectures/x86=false
architectures/x86_64=false
keystore/debug={quoted(str(keystore))}
keystore/debug_user="androiddebugkey"
keystore/debug_password="android"
version/code=10273
version/name="0.1.273-offline-test"
package/unique_name="com.votrivalley.midgardsvvoffline"
package/name="Quái Triều Xâm Lăng"
package/signed=true
user_data_backup/allow=false
screen/immersive_mode=true
permissions/internet=false
permissions/access_network_state=false
permissions/read_external_storage=false
permissions/write_external_storage=false
'''
    path.write_text(current + preset, encoding='utf-8')
    (project.parent / 'original-builds' / 'android').mkdir(parents=True, exist_ok=True)
    print(f'Added Android Offline preset {index}; arm64 debug build only.')
    print('No permanent release signing identity is configured.')


if __name__ == '__main__':
    main()
