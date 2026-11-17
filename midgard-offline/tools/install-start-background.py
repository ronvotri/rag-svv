#!/usr/bin/env python3
"""Replace the original class-select background with the user's own RO art.

The recovered publisher client stays outside Git. Inject only a small,
checked, reversible hook into its class-selection method and copy the
self-contained authored image before Godot imports the project.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "original-addons" / "svv_home_background.jpg"
RESOURCE = "res://assets/svv/svv_home_background.jpg"
HOOK = 'call_deferred("_svv_replace_class_screen_backdrop")'

GDSCRIPT = r'''
# Quái Triều Xâm Lăng: authored, static title image; original menu is intact.
# Run after show_class_select builds its buttons. No loading/gameplay changes.
func _svv_replace_class_screen_backdrop() -> void:
	if _mode != "class_select":
		return
	var artwork: Texture2D = load("res://assets/svv/svv_home_background.jpg") as Texture2D
	if artwork == null:
		push_warning("SVV title art missing; original background unchanged")
		return
	var viewport_size: Vector2 = get_viewport().get_visible_rect().size
	var largest: TextureRect = null
	var largest_area: float = 0.0
	for node in find_children("*", "TextureRect", true, false):
		var texture_rect: TextureRect = node as TextureRect
		if texture_rect == null or not texture_rect.is_visible_in_tree():
			continue
		var bounds: Rect2 = texture_rect.get_global_rect()
		if bounds.size.x < viewport_size.x * 0.68 or bounds.size.y < viewport_size.y * 0.68:
			continue
		var area: float = bounds.size.x * bounds.size.y
		if area > largest_area:
			largest_area = area
			largest = texture_rect
	if largest != null:
		# Swap the existing full-screen texture in place. Its draw order,
		# resize constraints, input and UI children remain intact.
		largest.texture = artwork
		largest.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		largest.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		print("SVV home art: replaced class-select backdrop texture")
		return

	# Fallback for upstream screens whose backdrop is a ColorRect instead
	# of a TextureRect. Never replace a regular small menu panel.
	var color_bg: ColorRect = null
	var bg_area: float = 0.0
	for node in find_children("*", "ColorRect", true, false):
		var color_rect: ColorRect = node as ColorRect
		if color_rect == null or not color_rect.is_visible_in_tree():
			continue
		var bounds: Rect2 = color_rect.get_global_rect()
		if bounds.size.x < viewport_size.x * 0.68 or bounds.size.y < viewport_size.y * 0.68:
			continue
		var area: float = bounds.size.x * bounds.size.y
		if area > bg_area:
			bg_area = area
			color_bg = color_rect
	if color_bg != null:
		var host: Control = color_bg.get_parent() as Control
		if host == null:
			return
		var old: Node = host.get_node_or_null("SVVHomeBackground")
		if old != null:
			old.queue_free()
		var image: TextureRect = TextureRect.new()
		image.name = "SVVHomeBackground"
		image.texture = artwork
		image.mouse_filter = Control.MOUSE_FILTER_IGNORE
		image.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		image.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		host.add_child(image)
		host.move_child(image, color_bg.get_index())
		image.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		color_bg.hide()
		print("SVV home art: replaced class-select ColorRect")
		return
	push_warning("SVV home art: no full-screen background target found; menus unchanged")
'''


def install(project: Path, image_file: Path = ART) -> dict:
    project = Path(project).resolve(strict=True)
    if not image_file.is_file():
        raise FileNotFoundError("Authored start background missing: " + str(image_file))
    if image_file.stat().st_size > 3_000_000:
        raise ValueError("Title image must be optimized below 3MB")
    if image_file.read_bytes()[:3] != b"\xff\xd8\xff":
        raise ValueError("Title image must be JPEG")
    original = project / "scripts/ui/menus.gd"
    text = original.read_text(encoding="utf-8")
    if "_svv_replace_class_screen_backdrop" in text:
        raise ValueError("Title backdrop patch was already installed")
    pattern = re.compile(r"(?m)^func show_class_select\([^\n]*\)[^\n]*:$")
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise ValueError("Expected one show_class_select hook; got " + str(len(matches)))
    # Defer so the actual original UI has been built. Do not override, close,
    # or reconstruct class-selection and character-preview controls.
    anchor = matches[0].group(0)
    patched = text[:matches[0].end()] + "\n\t" + HOOK + text[matches[0].end():]
    patched = patched.rstrip() + "\n\n" + GDSCRIPT.strip() + "\n"
    target = project / "assets/svv/svv_home_background.jpg"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(image_file, target)
    original.write_text(patched, encoding="utf-8", newline="\n")
    return {"installed": True, "image": str(target.relative_to(project)),
            "source_file": "scripts/ui/menus.gd", "hook": HOOK}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    print(install(args.project))
