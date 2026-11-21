#!/usr/bin/env python3
"""Use the outer class-page arrows and remove the redundant broken in-card previous glyph.

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


func _svv_reapply_class_navigation() -> void:
	# Original handlers own the page change. We only restyle the freshly built UI.
	call_deferred("_svv_fix_class_select_navigation")


func _svv_fix_class_select_navigation() -> void:
	if not is_inside_tree():
		if not tree_entered.is_connected(_svv_fix_class_select_navigation):
			tree_entered.connect(_svv_fix_class_select_navigation, CONNECT_ONE_SHOT)
		return
	var viewport: Viewport = get_viewport()
	if viewport == null:
		return
	if _mode != "class_select":
		return
	var viewport_size: Vector2 = viewport.get_visible_rect().size
	var outer_left: Button = null
	var outer_right: Button = null
	var inner_previous: Array[Button] = []
	# Only classify page arrows; never touch the in-card PLAY / confirmation
	# button. In particular, its existing pressed signal is preserved.
	var left_glyphs := ["◀", "◁", "❮", "‹", "〈", "<", "◄", "⬅", "«"]
	var right_glyphs := ["▶", "►", "❯", "›", "〉", ">", "►", "➡", "»"]
	for node in find_children("*", "Button", true, false):
		var button: Button = node as Button
		if button == null or not button.is_visible_in_tree():
			continue
		var rect: Rect2 = button.get_global_rect()
		if rect.size.x > 100.0 or rect.size.y > 88.0:
			continue
		var center: Vector2 = rect.get_center()
		var label: String = button.text.strip_edges()
		if center.y < viewport_size.y * 0.20 or center.y > viewport_size.y * 0.85:
			continue
		if center.x <= viewport_size.x * 0.15 and (label in left_glyphs or button.icon != null):
			outer_left = button
		elif center.x >= viewport_size.x * 0.85 and (label in right_glyphs or button.icon != null):
			outer_right = button
		elif center.x > viewport_size.x * 0.24 and center.x < viewport_size.x * 0.54 and center.y > viewport_size.y * 0.60 and label in left_glyphs:
			inner_previous.append(button)
	# Do not hide any in-card control unless BOTH native outer arrows exist.
	# Otherwise the screen still has its original functional navigation.
	if outer_left == null or outer_right == null:
		push_warning("SVV: could not verify both outer class page arrows; preserve original controls")
		return
	var pair: Array[Button] = [outer_left, outer_right]
	for arrow in pair:
		arrow.text = ""
		arrow.icon = _svv_class_arrow_texture(arrow == outer_left)
		arrow.expand_icon = true
		arrow.icon_alignment = HORIZONTAL_ALIGNMENT_CENTER
		if not arrow.pressed.is_connected(_svv_reapply_class_navigation):
			arrow.pressed.connect(_svv_reapply_class_navigation)
	# Hide only redundant interior PREVIOUS glyphs (the broken tofu on Web).
	# The outside arrows keep their upstream page/selection handlers.
	for duplicate in inner_previous:
		duplicate.hide()



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
