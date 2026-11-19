extends CanvasLayer
## Two recruitable offline town NPCs using ORIGINAL Ragnarok job sprites.
## No simulated human accounts, replacement artwork or new map assets.
## Placement is confined to the one town currently verified by runtime QA:
## Prontera. Move NPCs to actual other towns only after those scenes are found.

const JOBS := ["swordsman", "mage"]
const SPRITE_CANDIDATES := {
	"swordsman": ["swordsman_m", "swordsman_f"],
	"mage": ["mage_f", "mage_m"],
}
const NPC_NAMES := {
	"swordsman": "Alden",
	"mage": "Eira",
}
# Start near the original Kafra anchor, separated from Mira's (1.5, 0, 0.6)
# and each other. Do not wander into unverified town collision tiles.
const POSITIONS := {
	"swordsman": Vector3(-2.2, 0.0, 0.4),
	"mage": Vector3(2.25, 0.0, -1.8),
}

var town_node: Node3D
var npc_visuals: Dictionary = {}
var missing_sprites: Dictionary = {}
var fallback_buttons: Dictionary = {}
var elapsed := 0.0
var veil: ColorRect
var dialog: PanelContainer
var story: Label
var description: Label
var action: Button
var header: Label
var selected_job := ""


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 112
	_build_ui()
	get_viewport().size_changed.connect(_fit)
	_fit()


func _build_ui() -> void:
	for job in JOBS:
		var button := Button.new()
		button.text = "%s · %s" % [NPC_NAMES[job], SVVAssistant._job_name(job)]
		button.tooltip_text = "Gặp NPC %s tại Prontera" % NPC_NAMES[job]
		button.custom_minimum_size = Vector2(196, 46)
		button.add_theme_font_size_override("font_size", 17)
		button.pressed.connect(_show_dialog.bind(job))
		button.hide()
		add_child(button)
		fallback_buttons[job] = button

	veil = ColorRect.new()
	veil.color = Color(0.02, 0.07, 0.06, 0.78)
	veil.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	veil.mouse_filter = Control.MOUSE_FILTER_STOP
	veil.hide()
	add_child(veil)

	dialog = PanelContainer.new()
	dialog.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	var frame := StyleBoxFlat.new()
	frame.bg_color = Color("17342d")
	frame.border_color = Color("d7c48b")
	frame.set_border_width_all(2)
	frame.set_corner_radius_all(9)
	frame.set_content_margin_all(16)
	dialog.add_theme_stylebox_override("panel", frame)
	dialog.hide()
	add_child(dialog)
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	dialog.add_child(scroll)
	var column := VBoxContainer.new()
	column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	column.add_theme_constant_override("separation", 12)
	scroll.add_child(column)
	header = Label.new()
	header.add_theme_font_size_override("font_size", 22)
	header.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(header)
	story = Label.new()
	story.add_theme_font_size_override("font_size", 18)
	story.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(story)
	description = Label.new()
	description.add_theme_font_size_override("font_size", 17)
	description.add_theme_color_override("font_color", Color("ffe4a0"))
	description.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(description)
	action = Button.new()
	action.custom_minimum_size.y = 48
	action.add_theme_font_size_override("font_size", 18)
	action.pressed.connect(_do_action)
	column.add_child(action)
	var close_button := Button.new()
	close_button.text = "Tạm biệt"
	close_button.custom_minimum_size.y = 46
	close_button.pressed.connect(_close_dialog)
	column.add_child(close_button)


func _fit() -> void:
	var size := get_viewport().get_visible_rect().size
	for index in JOBS.size():
		var job: String = JOBS[index]
		# Used only when the ORIGINAL sprite cannot be resolved.
		fallback_buttons[job].position = Vector2(12, maxf(10.0, size.y - 177.0 - 55.0 * index))
	var width := minf(490.0, size.x - 24.0)
	var height := minf(430.0, size.y - 24.0)
	dialog.offset_left = -width / 2.0
	dialog.offset_right = width / 2.0
	dialog.offset_top = -height / 2.0
	dialog.offset_bottom = height / 2.0
	veil.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)


func _town() -> Node3D:
	var world = SVVAssistant._world()
	if world == null or world.running or world.menus == null:
		return null
	if str(world.menus._mode) in ["login", "server_select", "class_select", "loading"]:
		return null
	var candidate = world.get("town")
	if candidate is Node3D and is_instance_valid(candidate) and candidate.is_inside_tree():
		return candidate
	return null


func _process(delta: float) -> void:
	elapsed += delta
	if elapsed < 0.35:
		return
	elapsed = 0.0
	var current_town: Node3D = _town()
	if current_town != town_node:
		_clear_world()
		if current_town != null:
			_spawn_in_town(current_town)
	for job in JOBS:
		var visual = npc_visuals.get(job)
		var is_visible: bool = current_town != null and not dialog.visible and not is_instance_valid(visual)
		fallback_buttons[job].visible = is_visible
	if dialog.visible and current_town == null:
		_close_dialog()


func _spawn_in_town(parent: Node3D) -> void:
	if not parent.has_method("npc_node"):
		return
	var kafra = parent.npc_node("kafra")
	if not kafra is Node3D or not is_instance_valid(kafra):
		return
	town_node = parent
	missing_sprites.clear()
	for job in JOBS:
		var sprite_id: String = _first_original_sprite(job)
		if sprite_id.is_empty():
			missing_sprites[job] = true
			push_warning("SVV Town companion: no original sprite for %s; not creating substitute art" % job)
			continue
		var original_sprite = RoAssets.sprite([sprite_id])
		if original_sprite == null:
			missing_sprites[job] = true
			push_warning("SVV Town companion: sprite asset unavailable for " + job)
			continue
		var visual := RoVisual.new()
		parent.add_child(visual)
		visual.name = "SVV" + job.capitalize() + "FriendNPC"
		visual.setup(original_sprite, Color(0.8, 0.8, 0.9), 40)
		visual.global_position = kafra.global_position + POSITIONS[job]
		var nameplate := Label3D.new()
		nameplate.text = "%s · %s" % [NPC_NAMES[job], SVVAssistant._job_name(job)]
		nameplate.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		nameplate.font_size = 38
		nameplate.pixel_size = 0.006
		nameplate.position = Vector3(0.0, 1.3, 0.0)
		visual.add_child(nameplate)
		_set_idle(visual)
		npc_visuals[job] = visual


func _first_original_sprite(job: String) -> String:
	if not SPRITE_CANDIDATES.has(job):
		return ""
	for sprite_id in SPRITE_CANDIDATES[job]:
		if RoAssets.has_sprite(sprite_id):
			return sprite_id
	return ""


func _set_idle(visual: RoVisual) -> void:
	var script: Script = visual.get_script()
	if script == null:
		return
	var action_id: int = int(script.get_script_constant_map().get("PC_IDLE", -1))
	if action_id >= 0:
		visual.play(action_id, true, true)


func _clear_world() -> void:
	for visual in npc_visuals.values():
		if is_instance_valid(visual):
			visual.queue_free()
	npc_visuals.clear()
	town_node = null
	missing_sprites.clear()


func _screen_point(visual: RoVisual) -> Vector2:
	var camera := get_viewport().get_camera_3d()
	if camera == null or camera.is_position_behind(visual.global_position):
		return Vector2.INF
	return camera.unproject_position(visual.global_position + Vector3(0.0, 0.9, 0.0))


func _unhandled_input(event: InputEvent) -> void:
	if dialog.visible or _town() == null:
		return
	var pointer := Vector2.INF
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		pointer = event.position
	elif event is InputEventScreenTouch and event.pressed:
		pointer = event.position
	else:
		return
	var closest := ""
	var closest_distance := INF
	var radius := 76.0 if DisplayServer.is_touchscreen_available() else 48.0
	for job in JOBS:
		var visual = npc_visuals.get(job)
		if not is_instance_valid(visual):
			continue
		var location := _screen_point(visual)
		var distance := pointer.distance_to(location)
		if location.is_finite() and distance <= radius and distance < closest_distance:
			closest = job
			closest_distance = distance
	if not closest.is_empty():
		_show_dialog(closest)
		get_viewport().set_input_as_handled()


func _show_dialog(job: String) -> void:
	if not JOBS.has(job) or _town() == null:
		return
	selected_job = job
	_refresh_dialog()
	veil.show()
	dialog.show()
	for button in fallback_buttons.values():
		button.hide()


func _refresh_dialog() -> void:
	if not JOBS.has(selected_job):
		return
	var profile: Dictionary = SVVAssistant._friend_profile(selected_job)
	var unlocked: Array = SVVAssistant._unlocked_friends()
	var party: Array[String] = SVVAssistant._party_members()
	var progress: Dictionary = SVVAssistant._quest_progress(selected_job)
	header.text = "%s · %s · %s" % [
		NPC_NAMES[selected_job], SVVAssistant._job_name(selected_job), str(profile["rarity"])]
	var greeting := ""
	if selected_job == "swordsman":
		greeting = "Alden: Đứng sau tôi. Quái đông thế nào cũng phải có người giữ tuyến đầu chứ!"
	else:
		greeting = "Eira: Đừng chạm vào cuốn sách đó! Lần trước có người chạm, cả phòng thơm mùi khét ba ngày."
	story.text = greeting
	if unlocked.has(selected_job):
		description.text = "Đã kết bạn! Mời tôi từ Friends List hoặc ngay tại đây trước khi phiêu lưu."
		action.text = "Để %s nghỉ" % NPC_NAMES[selected_job] if party.has(selected_job) else "Mời %s vào party" % NPC_NAMES[selected_job]
		action.disabled = not party.has(selected_job) and party.size() >= 3
	elif not unlocked.has("acolyte"):
		description.text = "Hãy giúp Mira (Acolyte) ở y viện Prontera trước. Cô ấy sẽ giới thiệu chúng ta."
		action.text = "Chưa mở khóa"
		action.disabled = true
	elif bool(progress["started"]):
		description.text = "%s\nTiến độ: %d/%d quái · %d/%d lượt phiêu lưu." % [
			str(profile["quest"]), int(progress["kills"]), int(profile["kills"]),
			int(progress["runs"]), int(profile["runs"])]
		action.text = "Kết bạn với %s" % NPC_NAMES[selected_job] if bool(progress["ready"]) else "Chưa hoàn thành nhiệm vụ"
		action.disabled = not bool(progress["ready"])
	else:
		description.text = "%s\nHoàn thành nhiệm vụ mới có thể kết bạn và mời vào party." % str(profile["quest"])
		action.text = "Nhận nhiệm vụ"
		action.disabled = false


func _do_action() -> void:
	if action.disabled or selected_job.is_empty():
		return
	# One authoritative save/roster path shared with Friends List and Mira.
	SVVAssistant._select_friend(selected_job)
	SVVAssistant._friend_action_pressed()
	_refresh_dialog()


func _close_dialog() -> void:
	dialog.hide()
	veil.hide()
	selected_job = ""


func _unhandled_key_input(event: InputEvent) -> void:
	if dialog.visible and event.is_action_pressed("ui_cancel"):
		_close_dialog()
		get_viewport().set_input_as_handled()
