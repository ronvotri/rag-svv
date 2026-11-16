#!/usr/bin/env python3
"""Write private Godot Web/Windows export presets using local official templates."""
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("project", type=Path)
parser.add_argument("templates", type=Path)
args = parser.parse_args()
project = args.project.resolve(strict=True)
templates = args.templates.resolve(strict=True)
if not (project / "project.godot").exists():
    parser.error("Project must contain project.godot")
destination = project / "export_presets.cfg"
if destination.exists():
    parser.error("Export presets already exist; refusing to overwrite")
web = (templates / "web_nothreads_debug.zip").as_posix()
windows = (templates / "windows_debug_x86_64.exe").as_posix()
destination.write_text(f'''[preset.0]

name="Web Offline"
platform="Web"
runnable=true
advanced_options=true
dedicated_server=false
custom_features="offline"
export_filter="all_resources"
include_filter="*.json,*.gat,*.bin,*.po,*.txt"
exclude_filter=".autoconverted/*,*.log,*.private.json"
export_path="../original-builds/web/index.html"
script_export_mode=2

[preset.0.options]

custom_template/debug="{web}"
custom_template/release=""
variant/extensions_support=false
variant/thread_support=false
vram_texture_compression/for_desktop=true
vram_texture_compression/for_mobile=true
html/export_icon=true
html/custom_html_shell=""
html/head_include="<meta http-equiv=\\"Content-Security-Policy\\" content=\\"default-src 'self' data: blob:; connect-src 'self' blob:; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline';\\">"
html/canvas_resize_policy=2
html/focus_canvas_on_start=true
html/experimental_virtual_keyboard=false
progressive_web_app/enabled=false
progressive_web_app/ensure_cross_origin_isolation_headers=false
progressive_web_app/offline_page=""
progressive_web_app/display=1
progressive_web_app/orientation=2
progressive_web_app/icon_144x144=""
progressive_web_app/icon_180x180=""
progressive_web_app/icon_512x512=""

[preset.1]

name="Windows Offline"
platform="Windows Desktop"
runnable=false
advanced_options=true
dedicated_server=false
custom_features="offline"
export_filter="all_resources"
include_filter="*.json,*.gat,*.bin,*.po,*.txt"
exclude_filter=".autoconverted/*,*.log,*.private.json"
export_path="../original-builds/windows/MidgardSVVOffline.exe"
script_export_mode=2

[preset.1.options]

custom_template/debug="{windows}"
custom_template/release=""
debug/export_console_wrapper=1
binary_format/embed_pck=false
binary_format/architecture="x86_64"
codesign/enable=false
application/modify_resources=false
texture_format/s3tc_bptc=true
texture_format/etc2_astc=false
''', encoding="utf-8", newline="\n")
print("Created Web Offline (index 0) and Windows Offline (index 1) export presets.")
