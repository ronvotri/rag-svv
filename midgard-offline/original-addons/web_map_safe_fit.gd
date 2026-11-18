extends Node
## Web-only bounds guard for the ORIGINAL region/map-selection menu.
## Do not edit original scenes, battle transforms or gameplay coordinates.
## The two map/info panels are fitted together only when visibly overflowing.
const CHECK_SECONDS := 0.75
const EDGE_PADDING := 18.0
const BOTTOM_HINT_PADDING := 34.0

var _elapsed := 0.0
var _target: Control
var _original_scale := Vector2.ONE
var _original_global_position := Vector2.ZERO
var _previous_viewport := Vector2.ZERO


func _ready() -> void:
	if not OS.has_feature("web"):
		set_process(false)
		return
	process_mode = Node.PROCESS_MODE_ALWAYS
	get_viewport().size_changed.connect(_on_viewport_resize)


func _process(delta: float) -> void:
	_elapsed += delta
	if _elapsed < CHECK_SECONDS:
		return
	_elapsed = 0.0
	_check_region_ui()


func _on_viewport_resize() -> void:
	_reset_fit()
	_previous_viewport = Vector2.ZERO


func _check_region_ui() -> void:
	var root: Window = get_tree().root
	if not _is_region_menu_visible(root):
		_reset_fit()
		return
	var size: Vector2 = get_viewport().get_visible_rect().size
	if is_instance_valid(_target) and size == _previous_viewport:
		return
	_reset_fit()
	var panels: Array[Control] = _find_main_panels(root, size)
	if panels.size() != 2:
		return
	var common: Control = _shared_control_parent(panels[0], panels[1])
	if common == null:
		return
	var bounds: Rect2 = panels[0].get_global_rect().merge(panels[1].get_global_rect())
	var available_width: float = maxf(100.0, size.x - EDGE_PADDING * 2.0)
	var available_height: float = maxf(100.0, size.y - EDGE_PADDING * 2.0 - BOTTOM_HINT_PADDING)
	var ratio: float = minf(1.0, minf(available_width / maxf(1.0, bounds.size.x),
			available_height / maxf(1.0, bounds.size.y)))
	# The original layout may have anchored its pair beyond the visible
	# viewport. Scaling the common parent preserves the controls' hitboxes.
	_target = common
	_original_scale = common.scale
	_original_global_position = common.global_position
	_previous_viewport = size
	if ratio < 0.995:
		common.scale = common.scale * ratio
	# Godot Control global rects incorporate the parent scale. Translate
	# the whole group to center the map and detail panel inside safe edges.
	var fitted: Rect2 = panels[0].get_global_rect().merge(panels[1].get_global_rect())
	var wanted := Vector2((size.x - fitted.size.x) * 0.5,
			(size.y - BOTTOM_HINT_PADDING - fitted.size.y) * 0.5)
	common.global_position += wanted - fitted.position


func _reset_fit() -> void:
	if is_instance_valid(_target):
		_target.scale = _original_scale
		_target.global_position = _original_global_position
	_target = null
	_previous_viewport = Vector2.ZERO


func _is_region_menu_visible(root: Node) -> bool:
	# Require both named map entries. A minimap in gameplay alone does
	# not qualify, so the battle camera, HUD, controls and saves stay intact.
	var field := false
	var culvert := false
	for node in root.find_children("*", "Control", true, false):
		var item: Control = node as Control
		if not item.is_visible_in_tree():
			continue
		var value := ""
		if item is Label:
			value = (item as Label).text
		elif item is RichTextLabel:
			value = (item as RichTextLabel).text
		elif item is BaseButton:
			value = (item as BaseButton).text
		if value.contains("Prontera Field"):
			field = true
		if value.contains("Prontera Culvert"):
			culvert = true
		if field and culvert:
			return true
	return false


func _find_main_panels(root: Node, size: Vector2) -> Array[Control]:
	var candidates: Array[Control] = []
	for node in root.find_children("*", "Control", true, false):
		var item: Control = node as Control
		if not item.is_visible_in_tree():
			continue
		if not (item is Panel or item is PanelContainer):
			continue
		var rect: Rect2 = item.get_global_rect()
		# Ignore sub-cards, the full-screen background and modal dialogs.
		if rect.size.x < size.x * 0.28 or rect.size.x > size.x * 0.95:
			continue
		if rect.size.y < size.y * 0.48:
			continue
		candidates.append(item)
	var chosen: Array[Control] = []
	var best_area := -1.0
	for i in range(candidates.size()):
		for j in range(i + 1, candidates.size()):
			var left: Rect2 = candidates[i].get_global_rect()
			var right: Rect2 = candidates[j].get_global_rect()
			if left.get_center().x > right.get_center().x:
				var temp: Rect2 = left
				left = right
				right = temp
			# Only take the two distinct side-by-side major panels.
			if left.end.x > right.position.x + size.x * 0.045:
				continue
			var overlap: float = minf(left.end.y, right.end.y) - maxf(left.position.y, right.position.y)
			if overlap < minf(left.size.y, right.size.y) * 0.45:
				continue
			var area: float = left.size.x * left.size.y + right.size.x * right.size.y
			if area > best_area:
				best_area = area
				chosen = [candidates[i], candidates[j]]
	return chosen


func _shared_control_parent(a: Control, b: Control) -> Control:
	var ancestors: Array[Node] = []
	var cursor: Node = a.get_parent()
	while cursor != null:
		if cursor is Control:
			ancestors.append(cursor)
		cursor = cursor.get_parent()
	cursor = b.get_parent()
	while cursor != null:
		if cursor in ancestors and cursor is Control:
			return cursor as Control
		cursor = cursor.get_parent()
	return null
