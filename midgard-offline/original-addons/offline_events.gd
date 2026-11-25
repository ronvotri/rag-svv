extends CanvasLayer
## Local-only optional encounters. These do NOT impersonate online players or
## change the official World Boss, Festival rankings, saved builds or rewards.
## NPC companions are driven by deterministic combat rules in a separate menu.

const MVPEncounter = preload("res://addons/svv_offline/offline_mvp_encounter.gd")
const MVP_NAMES := ["Baphomet", "Osiris", "Eddga", "Mistress", "Maya", "Dark Lord"]

const MODE_LABELS := {
	"training": "Bài tập · Thử sát thương",
	"festival": "Emperium Festival · Luyện Solo",
	"world_boss": "World Boss · Thử thách riêng",
}
const MODE_CARD_TAGLINES := {
	"training": "Hình nộm · Thử sát thương cùng Party",
	"festival": "Luyện Solo · 60 giây đấu với máy",
	"world_boss": "Boss riêng · Kỷ lục trên thiết bị",
}
const MODE_HINTS := {
	"training": "Hình nộm tập luyện cùng đồng đội; không tốn trang bị.",
	"festival": "60 giây phá Emperium. So điểm với đối thủ do máy điều khiển, không tính bảng xếp hạng online.",
	"world_boss": "Đánh Boss bằng đội hình offline. Máu và kỷ lục được lưu riêng trên thiết bị này, không dùng máu chung cộng đồng.",
}

var mode_buttons: Dictionary = {}
var mode_icons: Dictionary = {}
var open_button: Button
var veil: ColorRect
var panel: PanelContainer
var title: Label
var help: Label
var status: Label
var result: Label
var meter: ProgressBar
var start_button: Button
var attack_button: Button
var skill_button: Button
var selected_mode := "training"
var running := false
var elapsed := 0.0
var duration := 60.0
var target_hp := 100.0
var target_max := 100.0
var score := 0
var rival_score := 0
var total_damage := 0
var player_hp := 100
var auto_timer := 0.0
var skill_cd := 0.0
var party_jobs: Array[String] = []
var previous_pause := false
var status_timer := 0.0
var mvp_picker: OptionButton
var mvp_preview := false
var mvp_launching := false


func _ready() -> void:
	mvp_preview = Save._name == "profile_offline_test" and OS.get_cmdline_user_args().has("--offline-test") and OS.get_cmdline_user_args().has("--offline-mvp-menu-preview")
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 117
	open_button = Button.new()
	open_button.text = "Luyện offline"
	open_button.custom_minimum_size = Vector2(164, 38)
	open_button.tooltip_text = "Mini-game mô phỏng cùng Party, không thay thế Điểm đến gốc"
	open_button.pressed.connect(_open)
	_style_launcher_button(open_button)
	add_child(open_button)
	veil = ColorRect.new()
	veil.color = Color(0.01, 0.05, 0.04, 0.8)
	veil.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	veil.mouse_filter = Control.MOUSE_FILTER_STOP
	veil.hide()
	add_child(veil)
	panel = PanelContainer.new()
	panel.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	var frame := StyleBoxFlat.new()
	frame.bg_color = Color("12392f")
	frame.border_color = Color("f4c76a")
	frame.set_border_width_all(3)
	frame.set_corner_radius_all(12)
	frame.set_content_margin_all(16)
	panel.add_theme_stylebox_override("panel", frame)
	panel.hide()
	add_child(panel)
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	panel.add_child(scroll)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 12)
	col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(col)
	title = Label.new()
	title.text = "Phòng luyện offline · Mini-game Party"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 23)
	title.add_theme_color_override("font_color", Color("ffe39b"))
	col.add_child(title)
	var notice := Label.new()
	notice.text = "Mô phỏng trong menu, không thay thế Điểm đến / nearQ của game gốc."
	notice.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	notice.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	notice.add_theme_font_size_override("font_size", 12)
	notice.add_theme_color_override("font_color", Color("a4c9bb"))
	col.add_child(notice)
	help = Label.new()
	help.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	help.add_theme_color_override("font_color", Color("ccebd7"))
	col.add_child(help)
	# The previous three bare text buttons removed the destination imagery.
	# Replace them with illustrated cards and a clearly selected mode, while
	# keeping simulated offline modes distinct from the official destinations.
	for key in ["training", "festival", "world_boss"]:
		var option := Button.new()
		option.text = str(MODE_LABELS[key]) + "\n" + str(MODE_CARD_TAGLINES[key])
		option.tooltip_text = str(MODE_HINTS[key])
		option.custom_minimum_size.y = 84
		option.alignment = HORIZONTAL_ALIGNMENT_LEFT
		option.icon_alignment = HORIZONTAL_ALIGNMENT_LEFT
		option.expand_icon = false
		option.add_theme_font_size_override("font_size", 16)
		option.icon = _mode_icon(str(key))
		option.pressed.connect(_choose_mode.bind(str(key)))
		col.add_child(option)
		mode_buttons[str(key)] = option
	mvp_picker = OptionButton.new()
	for boss_name in MVP_NAMES:
		mvp_picker.add_item(boss_name)
	mvp_picker.select(0)
	mvp_picker.custom_minimum_size.y = 42
	mvp_picker.hide()
	col.add_child(mvp_picker)
	if mvp_preview:
		mode_buttons["world_boss"].text = "World Boss · Săn MVP thật (QA)"
		mode_buttons["world_boss"].tooltip_text = "Chọn MVP để thử combat trên bản đồ gốc"
	status = Label.new()
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	status.add_theme_color_override("font_color", Color("fff0c5"))
	col.add_child(status)
	meter = ProgressBar.new()
	meter.custom_minimum_size.y = 25
	meter.show_percentage = false
	col.add_child(meter)
	result = Label.new()
	result.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	result.add_theme_color_override("font_color", Color("b3f3cb"))
	col.add_child(result)
	var actions := HBoxContainer.new()
	actions.add_theme_constant_override("separation", 8)
	col.add_child(actions)
	start_button = Button.new()
	start_button.text = "Bắt đầu mô phỏng"
	start_button.add_theme_font_size_override("font_size", 18)
	_style_start_button(start_button)
	start_button.custom_minimum_size.y = 48
	start_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	start_button.pressed.connect(_begin)
	actions.add_child(start_button)
	attack_button = Button.new()
	attack_button.text = "Tấn công"
	attack_button.pressed.connect(_attack)
	actions.add_child(attack_button)
	skill_button = Button.new()
	skill_button.text = "Kỹ năng"
	skill_button.pressed.connect(_skill)
	actions.add_child(skill_button)
	var footer := Label.new()
	footer.text = "Chỉ là trận mô phỏng trên máy: không nhận thưởng, vé, bảng hạng hay người chơi online."
	footer.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	footer.add_theme_font_size_override("font_size", 12)
	col.add_child(footer)
	var close_button := Button.new()
	close_button.text = "Trở lại Prontera"
	close_button.custom_minimum_size.y = 42
	close_button.pressed.connect(_close)
	col.add_child(close_button)
	get_viewport().size_changed.connect(_fit)
	_fit()
	_choose_mode("training")


# Small crisp vector-style thumbnails drawn at runtime: no missing
# font glyphs, no network assets, no player/online icons represented as live.
func _mode_icon(mode: String) -> Texture2D:
	if mode_icons.has(mode):
		return mode_icons[mode]
	var pixels := Image.create(64, 64, false, Image.FORMAT_RGBA8)
	pixels.fill(Color.TRANSPARENT)
	var base: Color = Color("244e42")
	var accent: Color = Color("ffe3a4")
	if mode == "festival":
		base = Color("353963")
		accent = Color("f6cb7a")
	elif mode == "world_boss":
		base = Color("623242")
		accent = Color("f7d5aa")
	for y in 64:
		for x in 64:
			var dx := float(x) - 31.5
			var dy := float(y) - 31.5
			var radius := sqrt(dx * dx + dy * dy)
			if radius < 29.0:
				pixels.set_pixel(x, y, base)
			if absf(radius - 27.0) < 1.6:
				pixels.set_pixel(x, y, accent)
			if mode == "training":
				if absf(radius - 20.0) < 2.5 or absf(radius - 11.0) < 2.7 or radius < 4.4:
					pixels.set_pixel(x, y, accent)
			elif mode == "festival":
				# Castle / Emperium marker.
				if (x >= 17 and x <= 47 and y >= 31 and y <= 48) or (x >= 13 and x <= 19 and y >= 24 and y <= 46) or (x >= 45 and x <= 51 and y >= 24 and y <= 46):
					pixels.set_pixel(x, y, accent)
				if y >= 20 and y <= 28 and ((x >= 14 and x <= 19) or (x >= 27 and x <= 37) or (x >= 45 and x <= 50)):
					pixels.set_pixel(x, y, accent)
				if x >= 27 and x <= 37 and y >= 37 and y <= 48:
					pixels.set_pixel(x, y, base)
			else:
				# Horned boss silhouette with luminous eyes.
				var face_dx := dx / 16.0
				var face_dy := (dy - 6.0) / 17.0
				if face_dx * face_dx + face_dy * face_dy <= 1.0:
					pixels.set_pixel(x, y, accent)
				if (x >= 12 and x <= 23 and y >= 14 and y <= 31 and x + y <= 45) or (x >= 41 and x <= 52 and y >= 14 and y <= 31 and y - x <= -24):
					pixels.set_pixel(x, y, accent)
				if (y >= 35 and y <= 39 and x >= 20 and x <= 26) or (y >= 35 and y <= 39 and x >= 38 and x <= 44):
					pixels.set_pixel(x, y, Color("942b42"))
	var icon: Texture2D = ImageTexture.create_from_image(pixels)
	mode_icons[mode] = icon
	return icon


func _style_mode_button(button: Button, active: bool) -> void:
	var normal := StyleBoxFlat.new()
	normal.bg_color = Color("2d5548") if active else Color("1c3e35")
	normal.border_color = Color("f3c56a") if active else Color("66877a")
	normal.set_border_width_all(3 if active else 1)
	normal.set_corner_radius_all(10)
	normal.set_content_margin_all(10)
	button.add_theme_stylebox_override("normal", normal)
	var hover := normal.duplicate() as StyleBoxFlat
	hover.bg_color = Color("3b6758")
	button.add_theme_stylebox_override("hover", hover)
	button.add_theme_color_override("font_color", Color("ffe6a2") if active else Color("f0f7ed"))
	button.add_theme_color_override("font_hover_color", Color("ffffff"))


# Match the existing native-style Friends/Save toolbar, not a dark gray box.
func _style_launcher_button(button: Button) -> void:
	var normal := StyleBoxFlat.new()
	normal.bg_color = Color("eef4ff")
	normal.border_color = Color("a3b9e6")
	normal.set_border_width_all(2)
	normal.set_corner_radius_all(10)
	normal.set_content_margin_all(5)
	button.add_theme_stylebox_override("normal", normal)
	var hover := normal.duplicate() as StyleBoxFlat
	hover.bg_color = Color("dce9ff")
	button.add_theme_stylebox_override("hover", hover)
	button.add_theme_color_override("font_color", Color("253d74"))
	button.add_theme_color_override("font_hover_color", Color("1d356c"))
	button.add_theme_font_size_override("font_size", 16)


func _style_start_button(button: Button) -> void:
	var normal := StyleBoxFlat.new()
	normal.bg_color = Color("e8b657")
	normal.border_color = Color("ffe6a2")
	normal.set_border_width_all(2)
	normal.set_corner_radius_all(10)
	normal.set_content_margin_all(8)
	button.add_theme_stylebox_override("normal", normal)
	var hover := normal.duplicate() as StyleBoxFlat
	hover.bg_color = Color("ffd27b")
	button.add_theme_stylebox_override("hover", hover)
	button.add_theme_color_override("font_color", Color("38240b"))
	button.add_theme_color_override("font_hover_color", Color("38240b"))


func _in_town() -> bool:
	return SVVCompanionTown._town() != null


func _fit() -> void:
	var screen: Vector2 = get_viewport().get_visible_rect().size
	# Reserve the Friends/Save pair that already owns the right edge.
	# On desktop the launcher sits immediately to their left; on mobile
	# we use the second or third toolbar row instead of overlapping Save.
	var narrow: bool = screen.x < 1200.0
	var compact: bool = screen.x < 680.0
	var friend_width: float = 98.0 if compact else (112.0 if narrow else 132.0)
	var save_width: float = 114.0 if compact else (154.0 if narrow else 188.0)
	var friends_x: float = maxf(8.0, screen.x - 12.0 - friend_width - 8.0 - save_width)
	var bar_y: float = 56.0 if narrow else 10.0
	var offline_width: float = 164.0
	var offline_x: float = friends_x - offline_width - 8.0
	if offline_x >= 8.0:
		open_button.position = Vector2(offline_x, bar_y)
	else:
		open_button.position = Vector2(8.0, bar_y + 44.0)
	open_button.custom_minimum_size = Vector2(minf(offline_width, screen.x - 16.0), 38.0)
	var width := minf(560.0, screen.x - 20.0)
	var height := minf(730.0, screen.y - 20.0)
	panel.offset_left = -width * 0.5
	panel.offset_right = width * 0.5
	panel.offset_top = -height * 0.5
	panel.offset_bottom = height * 0.5
	veil.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)


func _process(delta: float) -> void:
	status_timer += delta
	if status_timer >= 0.5:
		status_timer = 0.0
		open_button.visible = _in_town() and not panel.visible
		if panel.visible and not _in_town():
			_close()
	if not running or not panel.visible:
		return
	elapsed += delta
	auto_timer += delta
	skill_cd = maxf(0.0, skill_cd - delta)
	if auto_timer >= 1.0:
		auto_timer -= 1.0
		_party_attack()
		if selected_mode == "festival":
			rival_score += 1 if int(elapsed) % 4 == 0 else 0
		elif selected_mode == "world_boss":
			player_hp = maxi(0, player_hp - 2)
			if player_hp == 0:
				_finish("Đội hình cạn sức. Có thể luyện lại ngay.")
	if running and elapsed >= duration:
		_finish("Đã hết thời gian mô phỏng.")
	if running:
		_render()


func _choose_mode(next_mode: String) -> void:
	if running or not MODE_LABELS.has(next_mode):
		return
	selected_mode = next_mode
	for key in mode_buttons:
		_style_mode_button(mode_buttons[key], str(key) == selected_mode)
	help.text = MODE_HINTS[selected_mode]
	var native_preview: bool = mvp_preview and selected_mode == "world_boss"
	mvp_picker.visible = native_preview
	start_button.text = "Vào trận thật (QA)" if native_preview else "Bắt đầu mô phỏng"
	if native_preview:
		help.text = "Thử nghiệm Swordsman cùng Party hiện tại trên bản đồ Prontera. Chưa trao thưởng."
	start_button.disabled = mvp_launching
	attack_button.disabled = true
	skill_button.disabled = true
	meter.hide()
	meter.max_value = 100
	meter.value = 100
	status.text = "Chế độ đã chọn: " + str(MODE_LABELS[selected_mode]) + ". Có thể dùng Party đã kết bạn."
	result.text = ""


func _open() -> void:
	if panel.visible or not _in_town():
		return
	previous_pause = get_tree().paused
	get_tree().paused = true
	veil.show()
	panel.show()
	_choose_mode(selected_mode)
	open_button.hide()


func _close() -> void:
	# A session is local-only; leaving early discards the unfinished result.
	running = false
	panel.hide()
	veil.hide()
	get_tree().paused = previous_pause
	open_button.visible = _in_town()


func _begin() -> void:
	if running or mvp_launching or not _in_town():
		return
	if mvp_preview and selected_mode == "world_boss":
		_begin_native_mvp_preview()
		return
	party_jobs = SVVAssistant._party_members()
	elapsed = 0.0
	auto_timer = 0.0
	skill_cd = 0.0
	score = 0
	rival_score = 0
	total_damage = 0
	player_hp = 100
	target_max = 100.0 if selected_mode == "training" else (130.0 if selected_mode == "festival" else 12000.0)
	target_hp = target_max
	duration = 45.0 if selected_mode == "training" else (60.0 if selected_mode == "festival" else 120.0)
	running = true
	meter.show()
	start_button.disabled = true
	attack_button.disabled = false
	skill_button.disabled = false
	result.text = "Đồng đội: " + _party_names()
	_render()


func _begin_native_mvp_preview() -> void:
	# Only explicitly opted-in test profiles can leave the simulation menu.
	if not mvp_preview or Save._name != "profile_offline_test" or mvp_launching:
		return
	var world: World = SVVAssistant._world()
	var index: int = mvp_picker.selected
	if not is_instance_valid(world) or index < 0 or index >= MVPEncounter.ROSTER.size():
		return
	if world.net.mode != "" or world.net.eos() != null or world.cloud._enabled():
		return
	var boss_id: String = MVPEncounter.ROSTER[index]
	mvp_launching = true
	_close()
	world.leave_town()
	world.set_stage("prontera")
	# Same native loading callback as the smoke-tested adventure route.
	# No forced menu close or unpause; a stuck transition is a QA failure.
	world.menus.show_loading(func(): world.start_run("swordsman", false))
	for frame in 240:
		if not is_instance_valid(world):
			break
		if world.running and world.map != null and world.player != null \
			and world.menus._mode == "" and not get_tree().paused:
			var boss: Enemy = await MVPEncounter.spawn(world, boss_id)
			print("OFFLINE_MVP_MENU_QA SPAWN id=", boss_id, " success=", is_instance_valid(boss))
			mvp_launching = false
			return
		await get_tree().process_frame
	print("OFFLINE_MVP_MENU_QA BLOCKED native_transition")
	mvp_launching = false

func _party_names() -> String:
	if party_jobs.is_empty():
		return "chỉ có bạn"
	var names := PackedStringArray()
	for job in party_jobs:
		names.append(str(SVVAssistant._friend_profile(job).get("name", job)))
	return ", ".join(names)


func _party_attack() -> void:
	var damage := 0.0
	for job in party_jobs:
		damage += 8.0 if job == "acolyte" else (19.0 if job in ["mage", "gunslinger", "archer"] else 15.0)
	if damage > 0.0:
		_deal(damage)


func _attack() -> void:
	if running:
		_deal(35.0)
		_render()


func _skill() -> void:
	if running and skill_cd <= 0.0:
		skill_cd = 6.0
		_deal(140.0)
		_render()


func _deal(damage: float) -> void:
	if not running:
		return
	var actual: float = minf(damage, target_hp)
	total_damage += int(actual)
	target_hp = maxf(0.0, target_hp - damage)
	if target_hp > 0.0:
		return
	score += 1
	if selected_mode == "world_boss":
		_finish("Đã hạ World Boss trong mô phỏng offline!")
	else:
		target_hp = target_max


func _render() -> void:
	meter.max_value = target_max
	meter.value = target_hp
	var remaining := maxi(0, ceili(duration - elapsed))
	var progress := "%d/%d HP" % [int(target_hp), int(target_max)]
	match selected_mode:
		"training":
			status.text = "Hình nộm: %s · %d giây · Hạ mục tiêu: %d" % [progress, remaining, score]
		"festival":
			status.text = "Emperium: %s · %d giây · Bạn và Party: %d | Đối thủ máy: %d" % [progress, remaining, score, rival_score]
		"world_boss":
			status.text = "World Boss (chỉ trên máy này): %s · %d giây · Đội còn %d HP" % [progress, remaining, player_hp]
	skill_button.disabled = not running or skill_cd > 0.0
	skill_button.text = "Kỹ năng (%ds)" % ceili(skill_cd) if skill_cd > 0.0 else "Kỹ năng"


func _finish(message: String) -> void:
	if not running:
		return
	running = false
	attack_button.disabled = true
	skill_button.disabled = true
	start_button.disabled = false
	var personal_best: int = 0
	var score_name := "Số mục tiêu" if selected_mode != "world_boss" else "Sát thương"
	var achieved: int = total_damage if selected_mode == "world_boss" else score
	var key := "svv_local_training_best"
	if selected_mode == "festival":
		key = "svv_local_festival_best"
	elif selected_mode == "world_boss":
		key = "svv_local_world_boss_best"
	personal_best = int(Save.setting(key, 0))
	if achieved > personal_best:
		Save.set_setting(key, achieved)
		Save.flush()
		personal_best = achieved
	result.text = "%s\n%s: %d · Kỷ lục máy này: %d. Không ảnh hưởng thưởng hoặc bảng hạng chính thức." % [
		message, score_name, achieved, personal_best]
	if selected_mode == "festival":
		result.text += "\nĐối thủ máy phá %d Emperium." % rival_score
	_render()


func _unhandled_key_input(event: InputEvent) -> void:
	if panel.visible and event.is_action_pressed("ui_cancel"):
		_close()
		get_viewport().set_input_as_handled()
