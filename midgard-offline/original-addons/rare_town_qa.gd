extends CanvasLayer
## Wave 28 — interactive Prontera visual QA for Cole and Haneul.
## Strict opt-in: paired Windows CLI flags or a separate Web preview export setting.
## NO recruitment, save writes, production spawn or NPC roster changes.

const TARGETS := [
	{"key": "cole", "name": "Cole", "job": "gunslinger", "gender": "m", "offset": Vector3(-4.3, 0.0, 4.1)},
	{"key": "haneul", "name": "Haneul", "job": "taekwon", "gender": "m", "offset": Vector3(4.3, 0.0, 4.1)},
]

var town_node: Node3D
var visuals: Dictionary = {}
var check_seconds := 0.0
var note: Label
var dialog: AcceptDialog


func _enabled() -> bool:
	var args := OS.get_cmdline_user_args()
	return ("--offline-test" in args and "--rare-town-qa" in args) or (OS.has_feature("web") and bool(ProjectSettings.get_setting("application/config/svv_web_npc_qa", false)))


func _ready() -> void:
	if not _enabled():
		set_process(false)
		set_process_unhandled_input(false)
		return
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 114
	note = Label.new()
	note.text = "QA RIÊNG: Cole / Haneul tại Prontera · Chưa thể tuyển vào Party"
	note.add_theme_font_size_override("font_size", 15)
	note.add_theme_color_override("font_color", Color("ffe4a0"))
	note.position = Vector2(12, 12)
	note.mouse_filter = Control.MOUSE_FILTER_IGNORE
	note.hide()
	add_child(note)
	dialog = AcceptDialog.new()
	dialog.title = "Kiểm tra NPC — chỉ QA"
	add_child(dialog)


func _town() -> Node3D:
	var world = SVVAssistant._world()
	if world == null or world.running or world.menus == null:
		return null
	if str(world.menus._mode) in ["login", "server_select", "class_select", "loading"]:
		return null
	if str(world.get_meta("svv_offline_town_place", "")) != "prontera":
		return null
	var candidate = world.get("town")
	if candidate is Node3D and is_instance_valid(candidate) and candidate.is_inside_tree():
		return candidate
	return null


func _process(delta: float) -> void:
	check_seconds += delta
	if check_seconds < 0.35:
		return
	check_seconds = 0.0
	var current: Node3D = _town()
	if note != null:
		note.visible = current != null
	if current != town_node:
		_clear_world()
		if current != null:
			_spawn(current)
	elif current != null and visuals.size() < TARGETS.size():
		_spawn(current)


func _spawn(parent: Node3D) -> void:
	if not parent.has_method("npc_node"):
		return
	var kafra = parent.npc_node("kafra")
	if not (kafra is Node3D) or not is_instance_valid(kafra):
		return
	town_node = parent
	for target in TARGETS:
		var key: String = str(target["key"])
		if is_instance_valid(visuals.get(key)):
			continue
		var job: String = str(target["job"])
		if not RoAssets.has_sprite(job):
			push_warning("RARE_TOWN_QA missing original sprite: " + job)
			continue
		var look: Dictionary = SVVCompanionTown._resolved_look(job)
		if look.is_empty() or not RoAssets.has_sprite(str(look["head_key"])):
			push_warning("RARE_TOWN_QA no distinct head: " + job)
			continue
		var composed: RoSprite = RoAssets.styled_character(
			job, "", "", [RoVisual.PC_ATTACK], "", look)
		if composed == null:
			push_warning("RARE_TOWN_QA cannot compose original character: " + job)
			continue
		var visual := RoVisual.new()
		parent.add_child(visual)
		visual.name = "SVV_RARE_QA_" + key
		visual.setup(composed, Color(0.8, 0.8, 0.9), 40)
		if not (visual.sprite is Sprite3D) or visual.sprite.texture == null:
			visual.queue_free()
			continue
		visual.global_position = kafra.global_position + target["offset"]
		var tag := Label3D.new()
		tag.text = str(target["name"]) + " · " + job.capitalize() + " · QA"
		tag.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		tag.font_size = 38
		tag.pixel_size = 0.006
		tag.position = Vector3(0, 1.3, 0)
		visual.add_child(tag)
		SVVCompanionTown._set_idle(visual)
		visual.set_meta("svv_friend_head", str(look["head_key"]))
		visuals[key] = visual
		print("RARE_TOWN_QA SPAWN ", key, " position=", visual.global_position)


func _screen_point(visual: RoVisual) -> Vector2:
	var camera := get_viewport().get_camera_3d()
	if camera == null or camera.is_position_behind(visual.global_position):
		return Vector2.INF
	return camera.unproject_position(visual.global_position + Vector3(0, 0.9, 0))


func _unhandled_input(event: InputEvent) -> void:
	if _town() == null or dialog == null or dialog.visible:
		return
	var pointer := Vector2.INF
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		pointer = event.position
	elif event is InputEventScreenTouch and event.pressed:
		pointer = event.position
	else:
		return
	var nearest := ""
	var nearest_distance := INF
	var radius := 76.0 if DisplayServer.is_touchscreen_available() else 48.0
	for target in TARGETS:
		var key: String = str(target["key"])
		var visual: RoVisual = visuals.get(key)
		if visual == null or not is_instance_valid(visual):
			continue
		var point := _screen_point(visual)
		var distance := pointer.distance_to(point)
		if point.is_finite() and distance < nearest_distance and distance <= radius:
			nearest = key
			nearest_distance = distance
	if not nearest.is_empty():
		show_qa_dialog(nearest)
		get_viewport().set_input_as_handled()


func show_qa_dialog(key: String) -> void:
	if not _enabled() or _town() == null or dialog == null:
		return
	for target in TARGETS:
		if str(target["key"]) == key and is_instance_valid(visuals.get(key)):
			dialog.dialog_text = str(target["name"]) + " (" + str(target["job"]) + ")\nĐây chỉ là bản kiểm tra ngoại hình trong Prontera. Chưa có nhiệm vụ kết bạn hay mở khóa cho NPC này.\nKiểm tra đầu/tóc/thân, chiều sâu và vị trí; hãy báo lỗi nếu thấy sprite lệch."
			dialog.popup_centered()
			return


func _clear_world() -> void:
	for visual in visuals.values():
		if is_instance_valid(visual):
			visual.queue_free()
	visuals.clear()
	town_node = null
	if dialog != null:
		dialog.hide()


func _exit_tree() -> void:
	_clear_world()
