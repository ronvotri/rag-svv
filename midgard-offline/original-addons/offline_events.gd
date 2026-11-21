extends CanvasLayer
## Local-only optional encounters. These do NOT impersonate online players or
## change the official World Boss, Festival rankings, saved builds or rewards.
## NPC companions are driven by deterministic combat rules in a separate menu.

const MODE_LABELS := {
	"training": "Bài tập · Thử sát thương",
	"festival": "Emperium Festival · Luyện Solo",
	"world_boss": "World Boss · Thử thách riêng",
}
const MODE_HINTS := {
	"training": "Hình nộm tập luyện cùng đồng đội; không tốn trang bị.",
	"festival": "60 giây phá Emperium. So điểm với đối thủ do máy điều khiển, không tính bảng xếp hạng online.",
	"world_boss": "Đánh Boss bằng đội hình offline. Máu và kỷ lục được lưu riêng trên thiết bị này, không dùng máu chung cộng đồng.",
}

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


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 117
	open_button = Button.new()
	open_button.text = "Hoạt động offline"
	open_button.custom_minimum_size = Vector2(164, 38)
	open_button.tooltip_text = "Các trận luyện mô phỏng, không cần máy chủ và không tính hạng trực tuyến"
	open_button.pressed.connect(_open)
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
	title.text = "Hoạt động offline · Luyện với đồng đội"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 23)
	title.add_theme_color_override("font_color", Color("ffe39b"))
	col.add_child(title)
	help = Label.new()
	help.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	help.add_theme_color_override("font_color", Color("ccebd7"))
	col.add_child(help)
	for key in MODE_LABELS:
		var option := Button.new()
		option.text = MODE_LABELS[key]
		option.custom_minimum_size.y = 40
		option.pressed.connect(_choose_mode.bind(str(key)))
		col.add_child(option)
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


func _in_town() -> bool:
	return SVVCompanionTown._town() != null


func _fit() -> void:
	var screen: Vector2 = get_viewport().get_visible_rect().size
	open_button.position = Vector2(maxf(8.0, screen.x - 176.0), 12.0 if screen.x > 560.0 else 102.0)
	var width := minf(560.0, screen.x - 20.0)
	var height := minf(615.0, screen.y - 20.0)
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
	help.text = MODE_HINTS[selected_mode]
	start_button.disabled = false
	attack_button.disabled = true
	skill_button.disabled = true
	meter.max_value = 100
	meter.value = 100
	status.text = "Chọn chế độ rồi nhấn Bắt đầu. Có thể dùng Party đã kết bạn."
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
	if running or not _in_town():
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
	start_button.disabled = true
	attack_button.disabled = false
	skill_button.disabled = false
	result.text = "Đồng đội: " + _party_names()
	_render()


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
