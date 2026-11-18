#!/usr/bin/env python3
"""Repair class-select navigation icons without changing its original artwork.

The new Ragnarok picture belongs to the Web startup loading splash only.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "original-addons" / "svv_home_background.jpg"
RESOURCE = "res://assets/svv/svv_home_background.jpg"
NAV_HOOK = 'call_deferred("_svv_fix_class_select_navigation")'

GDSCRIPT = r'''
# Character-class page buttons: use generated raster icons instead of a Unicode
# glyph which was rendered as a missing-glyph square on mobile. Keep original
# Button nodes, layout, navigation signals and focus handling unchanged.
func _svv_class_arrow_texture(point_left: bool) -> Texture2D:
	var size_px: int = 28
	var image: Image = Image.create(size_px, size_px, false, Image.FORMAT_RGBA8)
	image.fill(Color(0, 0, 0, 0))
	var blue: Color = Color("#4762b9")
	for y in range(5, 23):
		var step: int = absi(y - 13)
		if point_left:
			for x in range(5 + step, 22):
				image.set_pixel(x, y, blue)
		else:
			for x in range(6, 23 - step):
				image.set_pixel(x, y, blue)
	return ImageTexture.create_from_image(image)


func _svv_fix_class_select_navigation() -> void:
	if _mode != "class_select":
		return
	# Find the existing NEXT button first. Its ▶ glyph renders correctly.
	# Its sibling PREVIOUS button is at the same height on the left side of
	# the class-selector row. Use geometry rather than the broken glyph text.
	var viewport_size: Vector2 = get_viewport().get_visible_rect().size
	var next_button: Button = null
	for node in find_children("*", "Button", true, false):
		var button: Button = node as Button
		if button == null or not button.is_visible_in_tree():
			continue
		var rect: Rect2 = button.get_global_rect()
		if button.text.strip_edges() in ["▶", "►", "❯", ">"] and rect.get_center().x > viewport_size.x * 0.6 and rect.get_center().y < viewport_size.y * 0.65:
			next_button = button
			break
	if next_button == null:
		push_warning("SVV: class-selector next arrow not found; leave buttons unchanged")
		return
	var next_rect: Rect2 = next_button.get_global_rect()
	var prev_button: Button = null
	var best_score: float = INF
	for node in find_children("*", "Button", true, false):
		var button: Button = node as Button
		if button == null or button == next_button or not button.is_visible_in_tree():
			continue
		var rect: Rect2 = button.get_global_rect()
		if rect.get_center().x > viewport_size.x * 0.48:
			continue
		if next_rect.get_center().x - rect.get_center().x < viewport_size.x * 0.35:
			continue
		if absf(rect.size.x - next_rect.size.x) > 24.0 or absf(rect.size.y - next_rect.size.y) > 24.0:
			continue
		var y_distance: float = absf(rect.get_center().y - next_rect.get_center().y)
		if y_distance > maxf(18.0, next_rect.size.y * 0.75):
			continue
		var score: float = y_distance * 8.0 + absf(rect.size.x - next_rect.size.x) + absf(rect.size.y - next_rect.size.y)
		if score < best_score:
			best_score = score
			prev_button = button
	if prev_button == null:
		push_warning("SVV: class-selector previous arrow not matched; leave buttons unchanged")
		return
	# Presentation only. Do NOT disconnect signals, replace buttons or adjust
	# their coordinates: this must not change the selection flow.
	prev_button.text = ""
	prev_button.icon = _svv_class_arrow_texture(true)
	prev_button.expand_icon = true
	prev_button.icon_alignment = HORIZONTAL_ALIGNMENT_CENTER
	next_button.text = ""
	next_button.icon = _svv_class_arrow_texture(false)
	next_button.expand_icon = true
	next_button.icon_alignment = HORIZONTAL_ALIGNMENT_CENTER



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
    if "_svv_fix_class_select_navigation" in text:
        raise ValueError("Class arrows already installed")
    pattern = re.compile(r"(?m)^func show_class_select\([^\n]*\)[^\n]*:$")
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        raise ValueError("Expected one show_class_select hook; got " + str(len(matches)))
    # Defer so the actual original UI has been built. Do not override, close,
    # or reconstruct class-selection and character-preview controls.
    anchor = matches[0].group(0)
    patched = text[:matches[0].end()] + "\n\t" + NAV_HOOK + text[matches[0].end():]
    patched = patched.rstrip() + "\n\n" + GDSCRIPT.strip() + "\n"
    original.write_text(patched, encoding="utf-8", newline="\n")
    return {"installed": True, "class_select_background": "original",
            "source_file": "scripts/ui/menus.gd", "nav_hook": NAV_HOOK}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    print(install(args.project))
