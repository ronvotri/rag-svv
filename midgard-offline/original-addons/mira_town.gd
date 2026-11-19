extends CanvasLayer
## Offline Mira Acolyte interaction at the Prontera town UI.
## Uses existing class visuals where available. No fake online presence.

var npc_button: Button
var veil: ColorRect
var dialog: PanelContainer
var description: Label
var story: Label
var action: Button
var heal_float: Label
var heal_tween: Tween
var elapsed := 0.0
var patrol_time := 0.0
var last_sprite_action := -1
var visual_town: Node3D
var kafra_anchor: Node3D
var mira_visual: RoVisual
# Keep native sprite and its walkable position in the scene; this is not
# a UI-only portrait, an imported replacement sprite or a remote player.
const MIRA_SPRITE := "acolyte_f"
const KAFRA_NPC := "kafra"
const STAND_OFFSET := Vector3(1.5, 0.0, 0.6)
# Patrons stop at Mira's sprite, not at Kafra; small slow steps stay near
# an existing occupied (safe) town tile instead of random-map roaming.
const PATROL_STEP := Vector3(0.32, 0.0, 0.10)
const PATROL_PERIOD := 12.0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 111
	_build_ui()
	get_viewport().size_changed.connect(_fit)
	_fit()


func _build_ui() -> void:
	npc_button = Button.new()
	npc_button.text = "✚ Mira · Acolyte"
	npc_button.tooltip_text = "Trò chuyện với Mira ở y viện Prontera"
	npc_button.custom_minimum_size = Vector2(194, 48)
	npc_button.add_theme_font_size_override("font_size", 17)
	npc_button.pressed.connect(_show_dialog)
	npc_button.hide()
	add_child(npc_button)

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
	frame.set_content_margin_all(17)
	dialog.add_theme_stylebox_override("panel", frame)
	dialog.hide()
	add_child(dialog)

	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 12)
	dialog.add_child(column)
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 14)
	column.add_child(header)
	var portrait := Label.new()
	portrait.text = "✚"
	portrait.custom_minimum_size = Vector2(62, 68)
	portrait.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	portrait.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	portrait.add_theme_font_size_override("font_size", 43)
	portrait.add_theme_color_override("font_color", Color("a9f1bf"))
	header.add_child(portrait)
	var identity := Label.new()
	identity.text = "Mira · Acolyte\nY viện Prontera · Normal"
	identity.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	identity.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	identity.add_theme_font_size_override("font_size", 20)
	header.add_child(identity)
	story = Label.new()
	story.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	story.add_theme_font_size_override("font_size", 17)
	column.add_child(story)
	description = Label.new()
	description.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	description.add_theme_font_size_override("font_size", 15)
	description.add_theme_color_override("font_color", Color("ffe4a0"))
	column.add_child(description)
	action = Button.new()
	action.custom_minimum_size.y = 48
	action.add_theme_font_size_override("font_size", 17)
	action.pressed.connect(_do_action)
	column.add_child(action)
	var close := Button.new()
	close.text = "Tạm biệt Mira"
	close.custom_minimum_size.y = 42
	close.pressed.connect(_close_dialog)
	column.add_child(close)

	heal_float = Label.new()
	heal_float.add_theme_font_size_override("font_size", 23)
	heal_float.add_theme_color_override("font_color", Color("b2ffd0"))
	heal_float.add_theme_color_override("font_shadow_color", Color.BLACK)
	heal_float.add_theme_constant_override("shadow_offset_x", 1)
	heal_float.add_theme_constant_override("shadow_offset_y", 2)
	heal_float.mouse_filter = Control.MOUSE_FILTER_IGNORE
	heal_float.hide()
	add_child(heal_float)


func _fit() -> void:
	var viewport_size := get_viewport().get_visible_rect().size
	npc_button.position = Vector2(12, maxf(70, viewport_size.y - 116))
	var width := minf(460, viewport_size.x - 22)
	var height := minf(400, viewport_size.y - 22)
	dialog.offset_left = -width / 2
	dialog.offset_right = width / 2
	dialog.offset_top = -height / 2
	dialog.offset_bottom = height / 2
	veil.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)


func _process(delta: float) -> void:
	elapsed += delta
	if elapsed < 0.25:
		return
	var frame_seconds := elapsed
	elapsed = 0.0
	var in_town := _town_active()
	if in_town:
		_sync_world_sprite()
	else:
		_clear_world_sprite()
	# Fallback action is visible only if the native town visual cannot spawn.
	npc_button.visible = in_town and not dialog.visible and not is_instance_valid(mira_visual)
	if dialog.visible and not in_town:
		_close_dialog()
	if in_town and not dialog.visible:
		_tick_patrol(frame_seconds)


func _set_mira_animation(action_name: String) -> void:
	if not is_instance_valid(mira_visual):
		return
	# Action indices belong to the recovered RoVisual class, not hard-coded
	# sprite-frame assumptions. Unsupported animations leave the last pose.
	var script: Script = mira_visual.get_script()
	if script == null:
		return
	var actions: Dictionary = script.get_script_constant_map()
	var action: int = int(actions.get(action_name, -1))
	if action >= 0 and action != last_sprite_action:
		mira_visual.play(action, true, true)
		last_sprite_action = action


func _tick_patrol(delta: float) -> void:
	if not is_instance_valid(mira_visual) or not is_instance_valid(kafra_anchor):
		return
	patrol_time += maxf(0.0, delta)
	var phase := fposmod(patrol_time, PATROL_PERIOD)
	var step_fraction := 0.0
	if phase < 2.0:
		step_fraction = phase / 2.0
	elif phase < 6.0:
		step_fraction = 1.0
	elif phase < 8.0:
		step_fraction = 1.0 - (phase - 6.0) / 2.0
	var next_position: Vector3 = kafra_anchor.global_position + STAND_OFFSET + PATROL_STEP * step_fraction
	var motion: Vector3 = next_position - mira_visual.global_position
	if motion.length() > 0.005:
		mira_visual.face(motion)
		_set_mira_animation("PC_WALK")
	else:
		_set_mira_animation("PC_IDLE")
	mira_visual.global_position = next_position


func _town_active() -> bool:
	var world = SVVAssistant._world()
	if world == null or world.running or world.menus == null:
		return false
	var mode := str(world.menus._mode)
	if mode in ["login", "server_select", "class_select", "loading"]:
		return false
	# Never show Mira in a lobby/menu just because a mode name contains town.
	# Require the original Town node to be active in the scene tree.
	var town = world.get("town")
	return town is Node3D and is_instance_valid(town) and town.is_inside_tree()


func _sync_world_sprite() -> void:
	var world = SVVAssistant._world()
	if world == null:
		return
	var candidate = world.get("town")
	if not candidate is Node3D or not candidate.is_inside_tree():
		return
	if visual_town == candidate and is_instance_valid(mira_visual):
		return
	_clear_world_sprite()
	if not candidate.has_method("npc_node"):
		return
	var kafra = candidate.npc_node(KAFRA_NPC)
	if not kafra is Node3D or not is_instance_valid(kafra):
		return
	visual_town = candidate
	kafra_anchor = kafra
	mira_visual = _create_world_sprite(candidate, kafra)
	if mira_visual == null:
		visual_town = null
		kafra_anchor = null


func _create_world_sprite(parent: Node3D, anchor: Node3D) -> RoVisual:
	if parent == null or anchor == null or not is_instance_valid(anchor):
		return null
	if not RoAssets.has_sprite(MIRA_SPRITE):
		push_warning("Mira: missing original Acolyte sprite, using town interaction fallback")
		return null
	var original_sprite = RoAssets.sprite([MIRA_SPRITE])
	if original_sprite == null:
		return null
	var character := RoVisual.new()
	parent.add_child(character)
	character.name = "MiraAcolyteNPC"
	character.setup(original_sprite, Color(0.8, 0.8, 0.9), 40)
	character.global_position = anchor.global_position + STAND_OFFSET
	var nameplate := Label3D.new()
	nameplate.text = "Mira · Acolyte"
	nameplate.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	nameplate.font_size = 38
	nameplate.pixel_size = 0.006
	nameplate.position = Vector3(0.0, 1.3, 0.0)
	character.add_child(nameplate)
	return character


func _clear_world_sprite() -> void:
	if is_instance_valid(mira_visual):
		mira_visual.queue_free()
	mira_visual = null
	visual_town = null
	kafra_anchor = null
	patrol_time = 0.0
	last_sprite_action = -1


func _mira_screen_point() -> Vector2:
	var camera := get_viewport().get_camera_3d()
	if camera == null or not is_instance_valid(mira_visual):
		return Vector2.INF
	var point: Vector3 = mira_visual.global_position + Vector3(0.0, 0.9, 0.0)
	if camera.is_position_behind(point):
		return Vector2.INF
	return camera.unproject_position(point)


func _unhandled_input(event: InputEvent) -> void:
	if dialog.visible or not _town_active() or not is_instance_valid(mira_visual):
		return
	var pointer := Vector2.INF
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		pointer = event.position
	elif event is InputEventScreenTouch and event.pressed:
		pointer = event.position
	else:
		return
	var projected := _mira_screen_point()
	if not projected.is_finite():
		return
	var hit_radius := 72.0 if DisplayServer.is_touchscreen_available() else 48.0
	if pointer.distance_to(projected) <= hit_radius:
		_show_dialog()
		get_viewport().set_input_as_handled()


func _show_dialog() -> void:
	if dialog.visible:
		return
	_update_dialog()
	veil.show()
	dialog.show()
	npc_button.hide()


func _close_dialog() -> void:
	dialog.hide()
	veil.hide()


func _update_dialog() -> void:
	var friends: Array = SVVAssistant._unlocked_friends()
	var progress: Dictionary = SVVAssistant._quest_progress("acolyte")
	var party: Array[String] = SVVAssistant._party_members()
	if friends.has("acolyte"):
		story.text = "Mira: Lại tính ra ngoài săn quái à? Nhớ mang đủ Potion nhé. Tôi là Tu sĩ, không phải cả cái bệnh viện đâu!"
		description.text = "Đã kết bạn! Mira có thể đi cùng và hồi máu khi party gặp nguy hiểm."
		action.text = "Để Mira nghỉ" if party.has("acolyte") else "Mời Mira vào party"
		action.disabled = not party.has("acolyte") and party.size() >= 3
	elif bool(progress["started"]):
		story.text = "Mira: Cảm ơn đã nhận giúp y viện. Đám quái ngoài Prontera cứ làm tôi chạy cứu thương muốn hụt hơi!"
		var profile: Dictionary = SVVAssistant._friend_profile("acolyte")
		description.text = "Tiếp tế y viện: %d/%d quái · %d/%d lượt phiêu lưu." % [
			int(progress["kills"]), int(profile["kills"]), int(progress["runs"]), int(profile["runs"])]
		action.text = "Kết bạn với Mira" if bool(progress["ready"]) else "Chưa xong nhiệm vụ"
		action.disabled = not bool(progress["ready"])
	else:
		story.text = "Mira: Này nhà thám hiểm! Y viện đang thiếu băng gạc, ngoài kia quái lại kéo đến. Giúp tôi một chuyến, rồi mình cùng phiêu lưu nhé?"
		description.text = "Nhiệm vụ mở đầu · Normal\nHạ 8 quái và hoàn thành 1 lượt phiêu lưu để nhận Mira làm bạn."
		action.text = "Nhận nhiệm vụ của Mira"
		action.disabled = false


func _do_action() -> void:
	SVVAssistant._select_friend("acolyte")
	SVVAssistant._friend_action_pressed()
	_update_dialog()


func play_heal_fx(target: Player, recovered: float) -> void:
	if target == null or not is_instance_valid(target):
		return
	if heal_tween != null and heal_tween.is_running():
		heal_tween.kill()
	heal_float.text = "✚ +%d HP" % int(recovered)
	# Player is Node3D in the original Godot client, never CanvasItem.
	# Camera3D projects the healing world position into the CanvasLayer.
	# Headless QA can have no camera: place the cue in the viewport center.
	var viewport := get_viewport()
	var screen_position: Vector2 = viewport.get_visible_rect().size * 0.5
	var camera: Camera3D = viewport.get_camera_3d()
	if camera != null and not camera.is_position_behind(target.global_position):
		screen_position = camera.unproject_position(target.global_position + Vector3(0.0, 1.2, 0.0))
	var safe_size := viewport.get_visible_rect().size
	heal_float.position = Vector2(
		clampf(screen_position.x - 54.0, 8.0, maxf(8.0, safe_size.x - 120.0)),
		clampf(screen_position.y - 88.0, 8.0, maxf(8.0, safe_size.y - 72.0)))
	heal_float.scale = Vector2.ONE
	heal_float.modulate = Color(1.0, 1.0, 1.0, 1.0)
	heal_float.show()
	heal_tween = create_tween().set_parallel(true)
	heal_tween.tween_property(heal_float, "position", heal_float.position + Vector2(0, -56), 1.1)
	heal_tween.tween_property(heal_float, "modulate:a", 0.0, 1.1)
	heal_tween.finished.connect(func(): heal_float.hide())


func _unhandled_key_input(event: InputEvent) -> void:
	if dialog.visible and event.is_action_pressed("ui_cancel"):
		_close_dialog()
		get_viewport().set_input_as_handled()
