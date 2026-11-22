extends CanvasLayer
## Five recruitable offline town NPCs using the ORIGINAL Ragnarok composed character factory.
## No simulated human accounts, replacement artwork or new map assets.
## Placement is confined to the one town currently verified by runtime QA:
## Prontera. Move NPCs to actual other towns only after those scenes are found.

const JOBS := ["swordsman", "mage", "archer", "thief", "merchant"]
const SPRITE_CANDIDATES := {
	"swordsman": ["swordsman_m", "swordsman_f"],
	"mage": ["mage_f", "mage_m"],
	# Wave two: audit original sprites BEFORE any city placement.
	"archer": ["archer_f", "archer_m"],
	"thief": ["thief_m", "thief_f"],
	"merchant": ["merchant_m", "merchant_f"],
	# Never substitute Super Novice for Nao: a valid source asset is not
	# automatically a correct visual match for the basic Novice job.
	# A missing Novice remains visibly unverified during QA, not silently faked.
	"novice": ["novice_f", "novice_m"],
}
# Character profiles can be authored now, independently of physical placement.
# JOBS above includes three experimental Prontera placements for visual QA.
const NPC_NAMES := {
	"swordsman": "Alden",
	"mage": "Eira",
	"archer": "Elowen",
	"thief": "Riku",
	"merchant": "Mino",
	"novice": "Nao",
}
# Stable individual appearances in Prontera: the previous implementation used
# hair=2/hair_color=0 for all five jobs, making everyone look cloned.
# These deliberately conservative values use the original styled_character
# factory; no replacement texture or fake sprite is created.
const NPC_LOOK := {
	"swordsman": {"hair": 1, "hair_color": 3},
	"mage": {"hair": 5, "hair_color": 6},
	"archer": {"hair": 3, "hair_color": 2},
	"thief": {"hair": 4, "hair_color": 0},
	"merchant": {"hair": 2, "hair_color": 5},
}

const NPC_GREETINGS := {
	"swordsman": "Alden: Đứng sau tôi. Quái đông thế nào cũng phải có người giữ tuyến đầu chứ!",
	"mage": "Eira: Đừng chạm vào cuốn sách đó! Lần trước có người chạm, cả phòng thơm mùi khét ba ngày.",
	"archer": "Elowen: Cung không tự bắn trúng đâu nhé. Muốn theo tôi đi tuần thì chứng minh tay nghề trước!",
	"thief": "Riku: Đừng nhìn tôi kiểu đó. Ví của cậu còn nguyên mà... chắc thế.",
	"merchant": "Mino: Đi săn quái thì được, nhưng phá hàng của tôi là phải đền. Có hóa đơn đầy đủ!",
	"novice": "Nao: Tôi mới vào nghề thôi. Nếu thấy tôi chạy ngược hướng, gọi với nhé!",
}
# Experimental offsets near Kafra; visually inspect walking lanes and props
# before accepting these placements. Nao has NO town coordinate.
const POSITIONS := {
	"swordsman": Vector3(-2.2, 0.0, 0.4),
	"mage": Vector3(2.25, 0.0, -1.8),
	"archer": Vector3(-4.4, 0.0, -1.8),
	"thief": Vector3(4.4, 0.0, 1.6),
	"merchant": Vector3(-0.3, 0.0, -4.2),
}

var town_node: Node3D
var npc_visuals: Dictionary = {}
var missing_sprites: Dictionary = {}
var fallback_buttons: Dictionary = {}
var elapsed := 0.0
# Some original RO sprite textures load late or their visual node gets freed.
# Retry without duplicating living NPCs; keep the button fallback meanwhile.
var sprite_retry_seconds := 0.0
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
		var columns: int = 2 if size.x >= 430.0 else 1
		var column_index: int = index % columns
		var row_index: int = floori(float(index) / float(columns))
		fallback_buttons[job].position = Vector2(12.0 + float(column_index) * 205.0, maxf(10.0, size.y - 177.0 - 55.0 * row_index))
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
	# The core client has a city argument; only Prontera positions are audited.
	# An unknown/missing city tag fails closed instead of copying NPCs into Payon.
	if str(world.get_meta("svv_offline_town_place", "")) != "prontera":
		return null
	var candidate = world.get("town")
	if candidate is Node3D and is_instance_valid(candidate) and candidate.is_inside_tree():
		return candidate
	return null


func _process(delta: float) -> void:
	elapsed += delta
	if elapsed < 0.35:
		return
	var frame_seconds := elapsed
	elapsed = 0.0
	var current_town: Node3D = _town()
	if current_town != town_node:
		_clear_world()
		if current_town != null:
			_spawn_in_town(current_town)
	elif current_town != null:
		sprite_retry_seconds += frame_seconds
		if sprite_retry_seconds >= 4.0:
			sprite_retry_seconds = 0.0
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
	for job in JOBS:
		# A late retry must preserve the existing visual, nameplate and identity.
		if is_instance_valid(npc_visuals.get(job)):
			continue
		npc_visuals.erase(job)
		var sprite_id: String = _first_original_sprite(job)
		if sprite_id.is_empty():
			if not missing_sprites.has(job):
				push_warning("SVV Town companion: no original sprite for %s; not creating substitute art" % job)
			missing_sprites[job] = true
			continue
		# A single job sprite is BODY-ONLY. Use the publisher's full
		# body/head/hair composition (same API verified by rare-job QA).
		var original_sprite: RoSprite = _composed_original_sprite(job, sprite_id)
		if original_sprite == null:
			if not missing_sprites.has(job):
				push_warning("SVV Town companion: sprite asset unavailable for " + job)
			missing_sprites[job] = true
			continue
		missing_sprites.erase(job)
		var visual := RoVisual.new()
		parent.add_child(visual)
		visual.name = "SVV" + job.capitalize() + "FriendNPC"
		visual.setup(original_sprite, Color(0.8, 0.8, 0.9), 40)
		if not (visual.sprite is Sprite3D) or visual.sprite.texture == null:
			# A half-built sprite must NOT appear in town as a headless NPC.
			visual.queue_free()
			missing_sprites[job] = true
			continue
		visual.global_position = kafra.global_position + POSITIONS[job]
		var nameplate := Label3D.new()
		nameplate.text = "%s · %s" % [NPC_NAMES[job], SVVAssistant._job_name(job)]
		nameplate.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		nameplate.font_size = 32
		nameplate.pixel_size = 0.005
		nameplate.position = Vector3(0.0, 1.65, 0.0)
		visual.add_child(nameplate)
		_set_idle(visual)
		npc_visuals[job] = visual


# No body-only fallback: that was the source of the severed head.
# Parameter order is pinned by Build #342's original-client composed QA.
func _composed_original_sprite(job: String, sprite_id: String) -> RoSprite:
	if not RoAssets.has_sprite(sprite_id):
		return null
	var gender: String = "f" if sprite_id.ends_with("_f") else "m"
	var style: Dictionary = NPC_LOOK.get(job, {"hair": 2, "hair_color": 0})
	var look := {
		"gender": gender,
		"hair": int(style.get("hair", 2)),
		"hair_color": int(style.get("hair_color", 0)),
		"cloth": 0,
	}
	var composed: RoSprite = RoAssets.styled_character(
		job, "", "", [RoVisual.PC_ATTACK], "", look)
	if composed == null:
		push_warning("SVV: full head/hair/body sprite unavailable for " + job)
	return composed


func _first_original_sprite(job: String) -> String:
	if not SPRITE_CANDIDATES.has(job):
		return ""
	for sprite_id in SPRITE_CANDIDATES[job]:
		if RoAssets.has_sprite(sprite_id):
			return sprite_id
	return ""


func _set_idle(visual: RoVisual) -> void:
	# These NPCs are STATIONARY town contacts, not roaming players.
	# Face one stable direction and render one Idle pose. Playing looping
	# PC_IDLE on a layered head/hair composite caused a distracting bob/jitter.
	visual.face(Vector3(0.0, 0.0, 1.0))
	var script: Script = visual.get_script()
	if script != null:
		var action_id: int = int(script.get_script_constant_map().get("PC_IDLE", -1))
		if action_id >= 0:
			visual.play(action_id, true, true)
	# Freeze frame advancement for stationary NPCs; remain visible and clickable.
	visual.set_process(false)
	visual.set_physics_process(false)


func _clear_world() -> void:
	for visual in npc_visuals.values():
		if is_instance_valid(visual):
			visual.queue_free()
	npc_visuals.clear()
	town_node = null
	missing_sprites.clear()
	sprite_retry_seconds = 0.0


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
	story.text = str(NPC_GREETINGS.get(selected_job, str(profile.get("intro", ""))))
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
