extends CanvasLayer
## Local-only optional encounters. These do NOT impersonate online players or
## change the official World Boss, Festival rankings, saved builds or rewards.
## NPC companions are driven by deterministic combat rules in a separate menu.

const MVPEncounter = preload("res://addons/svv_offline/offline_mvp_encounter.gd")
const MVPResult = preload("res://addons/svv_offline/offline_mvp_result.gd")
const MVPCredit = preload("res://addons/svv_offline/offline_mvp_credit_qa.gd")
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
# Explicit QA only; the public Beta stays on the last released implementation.
var native_destination_review := false
var native_destination_contract: Dictionary = {}
var native_destination_opened := false
var mvp_launching := false
var mvp_last_spawn: Enemy
var mvp_last_id := ""
var mvp_loading_callback_completed := false
var mvp_hud: PanelContainer
var mvp_hud_name: Label
var mvp_hud_hp: ProgressBar
var mvp_hud_detail: Label
var mvp_return_button: Button
var mvp_returning := false
var mvp_hud_world: World
var mvp_hud_player: Player
var mvp_hud_started := 0.0
var mvp_hud_initial_hp := 1.0
var mvp_hud_outcome := ""
var mvp_hud_expires := 0
var mvp_session_token := ""
var mvp_death_hp: Variant = null
var mvp_death_seen := false
var mvp_victory_saved := false
var mvp_reward_credited := false
var mvp_reward_balance_before := 0
var mvp_reward_balance_after := 0


func _ready() -> void:
	mvp_preview = Save._name == "profile_offline_test" and OS.get_cmdline_user_args().has("--offline-test") and OS.get_cmdline_user_args().has("--offline-mvp-menu-preview")
	native_destination_review = Save._name == "profile_offline_test" and "--offline-test" in OS.get_cmdline_user_args() and "--offline-native-destinations" in OS.get_cmdline_user_args()
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 117
	open_button = Button.new()
	open_button.text = "Luyện offline"
	open_button.custom_minimum_size = Vector2(164, 38)
	open_button.tooltip_text = "Mini-game mô phỏng cùng Party, không thay thế Điểm đến gốc"
	if native_destination_review:
		open_button.text = "Điểm đến"
		open_button.tooltip_text = "Mở bảng Điểm đến gốc của nearQ"
		var contract_file := FileAccess.open("res://addons/svv_offline/native_destination_review.json", FileAccess.READ)
		if contract_file != null:
			var parsed: Variant = JSON.parse_string(contract_file.get_as_text())
			if parsed is Dictionary:
				native_destination_contract = parsed
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
	mvp_picker.item_selected.connect(_refresh_mvp_summary)
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
	if mvp_preview:
		_create_mvp_hud()
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
	if is_instance_valid(mvp_hud):
		var hud_width: float = minf(340.0, screen.x - 20.0)
		mvp_hud.position = Vector2((screen.x - hud_width) * 0.5, 80.0)
		mvp_hud.size.x = hud_width


func _create_mvp_hud() -> void:
	mvp_hud = PanelContainer.new()
	mvp_hud.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var frame := StyleBoxFlat.new()
	frame.bg_color = Color(0.07, 0.16, 0.13, 0.92)
	frame.border_color = Color("e8b657")
	frame.set_border_width_all(1)
	frame.set_corner_radius_all(8)
	frame.set_content_margin_all(8)
	mvp_hud.add_theme_stylebox_override("panel", frame)
	var content := VBoxContainer.new()
	content.mouse_filter = Control.MOUSE_FILTER_IGNORE
	mvp_hud.add_child(content)
	mvp_hud_name = Label.new()
	mvp_hud_name.mouse_filter = Control.MOUSE_FILTER_IGNORE
	mvp_hud_name.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	mvp_hud_name.add_theme_color_override("font_color", Color("ffe39b"))
	content.add_child(mvp_hud_name)
	mvp_hud_hp = ProgressBar.new()
	mvp_hud_hp.mouse_filter = Control.MOUSE_FILTER_IGNORE
	mvp_hud_hp.show_percentage = false
	mvp_hud_hp.step = 0.01
	mvp_hud_hp.custom_minimum_size.y = 12
	content.add_child(mvp_hud_hp)
	mvp_hud_detail = Label.new()
	mvp_hud_detail.mouse_filter = Control.MOUSE_FILTER_IGNORE
	mvp_hud_detail.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	mvp_hud_detail.add_theme_font_size_override("font_size", 13)
	content.add_child(mvp_hud_detail)
	mvp_return_button = Button.new()
	mvp_return_button.text = "Về Prontera"
	mvp_return_button.custom_minimum_size.y = 36
	mvp_return_button.mouse_filter = Control.MOUSE_FILTER_STOP
	mvp_return_button.pressed.connect(_return_from_mvp)
	content.add_child(mvp_return_button)
	mvp_return_button.hide()
	add_child(mvp_hud)
	mvp_hud.hide()


func _attach_mvp_hud(world: World, boss: Enemy) -> void:
	if not mvp_preview or not is_instance_valid(mvp_hud):
		return
	mvp_hud_world = world
	mvp_hud_player = world.player
	mvp_hud_started = world.time
	# Prefer a readable native maximum. Otherwise use observed starting HP,
	# not an invented boss stat.
	mvp_hud_initial_hp = maxf(1.0, boss.hp)
	for property in boss.get_property_list():
		if str(property.get("name", "")) == "max_hp":
			var native_max: Variant = boss.get("max_hp")
			if (native_max is int or native_max is float) and is_finite(float(native_max)):
				mvp_hud_initial_hp = maxf(mvp_hud_initial_hp, float(native_max))
			break
	mvp_hud_outcome = "active"
	mvp_returning = false
	mvp_return_button.hide()
	mvp_return_button.disabled = false
	mvp_session_token = Crypto.new().generate_random_bytes(16).hex_encode()
	mvp_death_hp = null
	mvp_death_seen = false
	mvp_victory_saved = false
	mvp_reward_credited = false
	mvp_reward_balance_before = 0
	mvp_reward_balance_after = 0
	mvp_hud_hp.show()
	# Temporary QA death hook observes only tagged enemies. No direct damage.
	boss.set_meta("svv_qa_boss_hits", {})
	boss.set_meta("svv_qa_death_observer", _observe_mvp_native_death)
	_update_mvp_hud()


# Test-only native death observer: retain evidence before Enemy is freed.
func _observe_mvp_native_death(boss: Enemy) -> void:
	if not mvp_preview or Save._name != "profile_offline_test" or OS.get_environment("SVV_WORLD_BOSS_QA_SANDBOX") != "1":
		return
	if mvp_hud_outcome != "active" or mvp_death_seen or not is_instance_valid(boss) or boss != mvp_last_spawn:
		return
	if boss.hp > 0.0 or not bool(boss.get_meta("svv_qa_native_death", false)):
		return
	mvp_death_hp = boss.hp
	mvp_death_seen = true


func _settle_mvp_victory(outcome: String) -> bool:
	if not mvp_preview or Save._name != "profile_offline_test" or OS.get_environment("SVV_WORLD_BOSS_QA_SANDBOX") != "1":
		return false
	if outcome != "victory" or not mvp_death_seen or not MVPEncounter.allowed(mvp_hud_world, mvp_last_id):
		return false
	if not is_instance_valid(mvp_hud_player) or mvp_hud_player != mvp_hud_world.player or mvp_hud_player.hp <= 0.0:
		return false
	var ledger: Dictionary = Save.setting("svv_offline_mvp_victories", {})
	var updated: Dictionary = MVPResult.next_reward_receipt_ledger(ledger, mvp_last_id, mvp_session_token, outcome)
	if updated.is_empty():
		return false
	Save.set_setting("svv_offline_mvp_victories", updated)
	Save.flush()
	return not Save._dirty


# Use native abandonment to bank/clear the run, then the original town
# entry only after the engine confirms the run is stopped. No forced state.
func _return_from_mvp() -> void:
	if not mvp_preview or Save._name != "profile_offline_test" or mvp_returning or mvp_hud_outcome != "victory" or not mvp_victory_saved:
		return
	var world: World = mvp_hud_world
	if not is_instance_valid(world) or not is_instance_valid(world.menus) or world.net.mode != "" or world.net.eos() != null or world.cloud._enabled():
		return
	if world.menus._mode not in ["", "closed"] or get_tree().paused:
		return
	mvp_returning = true
	mvp_return_button.disabled = true
	Save.flush()
	if not Save._dirty:
		if world.running:
			world.abandon_run()
		var deadline: int = Time.get_ticks_msec() + 12000
		while is_instance_valid(world) and Time.get_ticks_msec() < deadline:
			if not world.running and world.menus._mode in ["", "closed"] and not get_tree().paused:
				if SVVCompanionTown._town() == null:
					world.enter_town("swordsman")
				break
			await get_tree().process_frame
		while is_instance_valid(world) and Time.get_ticks_msec() < deadline and SVVCompanionTown._town() == null:
			await get_tree().process_frame
		if is_instance_valid(world) and not world.running and SVVCompanionTown._town() != null:
			Save.flush()
			mvp_hud_outcome = ""
			mvp_hud.hide()
			mvp_last_spawn = null
			mvp_returning = false
			print("OFFLINE_MVP_MENU_QA RETURN_PRONTERA success=true")
			return
	mvp_returning = false
	mvp_return_button.disabled = false
	mvp_hud_detail.text = "Chưa về thành được · Thử lại"
	print("OFFLINE_MVP_MENU_QA RETURN_PRONTERA success=false")


func _update_mvp_hud() -> void:
	if not is_instance_valid(mvp_hud) or mvp_hud_outcome.is_empty():
		return
	if not is_instance_valid(mvp_hud_world):
		mvp_hud.hide()
		mvp_hud_outcome = ""
		return
	var world: World = mvp_hud_world
	if not is_instance_valid(world.menus):
		mvp_hud.hide()
		mvp_hud_outcome = ""
		return
	# Never obscure the original level-up, pause or other modal controls.
	var clear_ui: bool = world.menus._mode in ["", "closed"] and not get_tree().paused
	if mvp_hud_outcome != "active":
		var return_ready: bool = mvp_hud_outcome == "victory" and mvp_victory_saved and SVVCompanionTown._town() == null
		mvp_return_button.visible = return_ready and not mvp_returning
		mvp_hud.visible = clear_ui and (return_ready or Time.get_ticks_msec() < mvp_hud_expires)
		return
	var boss_hp: Variant = mvp_death_hp if mvp_death_seen else (mvp_last_spawn.hp if is_instance_valid(mvp_last_spawn) else null)
	var player_health: Variant = mvp_hud_player.hp if is_instance_valid(mvp_hud_player) else null
	var native_death: bool = mvp_death_seen
	var outcome: String = MVPResult.classify(boss_hp, player_health, native_death, world.running, false)
	var seconds: int = maxi(0, int(world.time - mvp_hud_started))
	mvp_hud_name.text = "MVP · " + MVP_NAMES[MVPEncounter.ROSTER.find(mvp_last_id)]
	if boss_hp != null:
		mvp_hud_initial_hp = maxf(mvp_hud_initial_hp, float(boss_hp))
		mvp_hud_hp.max_value = mvp_hud_initial_hp
		mvp_hud_hp.value = maxf(0.0, float(boss_hp))
		mvp_hud_detail.text = "%d / %d HP · %02d:%02d" % [int(maxf(0.0, float(boss_hp))), int(mvp_hud_initial_hp), int(seconds / 60.0), seconds % 60]
	else:
		mvp_hud_hp.hide()
		mvp_hud_detail.text = "Không đọc được HP"
	if outcome != "active":
		mvp_hud_outcome = outcome
		mvp_victory_saved = _settle_mvp_victory(outcome)
		if mvp_victory_saved and OS.get_cmdline_user_args().has("--offline-mvp-wallet-preview"):
			mvp_reward_balance_before = Save.zeny()
			mvp_reward_credited = MVPCredit.redeem_menu(mvp_last_id, mvp_session_token)
			mvp_reward_balance_after = Save.zeny()
			print("OFFLINE_MVP_MENU_QA WALLET credited=", mvp_reward_credited, " delta=", mvp_reward_balance_after - mvp_reward_balance_before)
		mvp_hud_name.text = MVPResult.title_for(outcome)
		var record_label: String = "Đã lưu thành tích · Phiếu thưởng QA" if mvp_victory_saved else "Không cộng thành tích"
		if mvp_reward_credited:
			record_label = "+%d Zeny · +%d huy hiệu (QA)" % [MVPResult.QA_ZENY_QUOTE, MVPResult.QA_MVP_MARKS]
		mvp_hud_detail.text = "%02d:%02d · %s" % [int(seconds / 60.0), seconds % 60, record_label]
		mvp_hud_expires = Time.get_ticks_msec() + 8000
		print("OFFLINE_MVP_MENU_QA HUD_TERMINAL outcome=", outcome, " saved=", mvp_victory_saved)
	mvp_hud.visible = clear_ui


func _process(delta: float) -> void:
	if mvp_preview:
		_update_mvp_hud()
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
		help.text = "Swordsman cùng Party hiện tại trên bản đồ Prontera. Thưởng QA: Zeny và huy hiệu thành tích; không phải vật phẩm."
	start_button.disabled = mvp_launching
	attack_button.disabled = true
	skill_button.disabled = true
	meter.hide()
	meter.max_value = 100
	meter.value = 100
	status.text = "Chế độ đã chọn: " + str(MODE_LABELS[selected_mode]) + ". Có thể dùng Party đã kết bạn."
	result.text = ""
	if native_preview:
		_refresh_mvp_summary(mvp_picker.selected)


func _refresh_mvp_summary(index: int) -> void:
	if not mvp_preview or selected_mode != "world_boss" or index < 0 or index >= MVPEncounter.ROSTER.size():
		return
	var raw: Variant = Save.setting("svv_offline_mvp_victories", {})
	var ledger: Dictionary = raw if raw is Dictionary else {}
	var total: Dictionary = MVPResult.achievement_summary(ledger)
	var selected: Dictionary = MVPResult.achievement_summary(ledger, MVPEncounter.ROSTER[index])
	result.text = "%s: %d lần hạ · Tổng: %d lần hạ · %d huy hiệu MVP (QA)" % [
		MVP_NAMES[index], selected["wins"], total["wins"], total["marks"]]


# Open the exact native dialog using its reviewed owning instance.
# No simulated fallback when the explicit native-destination QA flag is set.
func _native_destination_owners(world: World, script_path: String) -> Array[Object]:
	var found: Array[Object] = []
	var seen: Dictionary = {}
	var queue: Array[Object] = [world, world.menus]
	var town: Variant = world.get("town")
	if town is Node:
		queue.append(town)
	var inspected := 0
	while not queue.is_empty() and inspected < 6000:
		var candidate: Object = queue.pop_front()
		if not is_instance_valid(candidate) or seen.has(candidate.get_instance_id()):
			continue
		seen[candidate.get_instance_id()] = true
		inspected += 1
		var script: Variant = candidate.get_script()
		if script is Script and script.resource_path == script_path:
			found.append(candidate)
		if candidate is Node:
			for child in candidate.get_children():
				queue.append(child)
		# Town controllers can be RefCounted and held in script properties
		# rather than appearing as children. Follow only exact script matches,
		# not arbitrary resources or the whole object graph.
		for property in candidate.get_property_list():
			if not (int(property.get("usage", 0)) & PROPERTY_USAGE_SCRIPT_VARIABLE) or int(property.get("type", 0)) != TYPE_OBJECT:
				continue
			var value: Variant = candidate.get(str(property["name"]))
			if value is Object and is_instance_valid(value):
				var value_script: Variant = value.get_script()
				if value_script is Script and value_script.resource_path == script_path:
					queue.append(value)
	return found


func _open_native_destination_review() -> void:
	native_destination_opened = false
	if not native_destination_review or not _in_town():
		return
	var world: World = SVVAssistant._world()
	if not is_instance_valid(world) or world.net.mode != "" or world.net.eos() != null or world.cloud._enabled():
		return
	var path: String = str(native_destination_contract.get("script", ""))
	var method: String = str(native_destination_contract.get("method", ""))
	if not path.begins_with("res://scripts/") or method.is_empty() or int(native_destination_contract.get("required", -1)) != 0:
		print("NATIVE_DESTINATION_QA BLOCKED source_contract")
		return
	var owners: Array[Object] = _native_destination_owners(world, path)
	if owners.size() != 1 or not owners[0].has_method(method):
		print("NATIVE_DESTINATION_QA BLOCKED owner_count=", owners.size())
		return
	var opener := Callable(owners[0], method)
	if not opener.is_valid():
		return
	opener.call()
	native_destination_opened = true
	print("NATIVE_DESTINATION_QA INVOKED ", path, "::", method)


func _open() -> void:
	if native_destination_review:
		_open_native_destination_review()
		return
	if panel.visible or not _in_town():
		return
	previous_pause = get_tree().paused
	get_tree().paused = true
	veil.show()
	panel.show()
	if mvp_preview:
		var recovered: int = MVPCredit.recover_menu_pending()
		if recovered > 0:
			print("OFFLINE_MVP_MENU_QA RECOVERED_PENDING count=", recovered)
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
	mvp_last_spawn = null
	mvp_last_id = ""
	mvp_hud_outcome = ""
	if is_instance_valid(mvp_hud):
		mvp_hud.hide()
	mvp_loading_callback_completed = false
	_close()
	world.leave_town()
	world.set_stage("prontera")
	# This callback belongs to this launch only. Do not close unrelated
	# level-up, skill-choice, pause, or tutorial overlays.
	world.menus.show_loading(func():
		world.start_run("swordsman", false)
		mvp_loading_callback_completed = true
	)
	var deadline: int = Time.get_ticks_msec() + 12000
	var waiting_for_choice := false
	while Time.get_ticks_msec() < deadline:
		if not is_instance_valid(world):
			break
		if mvp_loading_callback_completed and not world.running:
			break
		if mvp_loading_callback_completed and world.running and world.map != null and is_instance_valid(world.player):
			# An opening skill/level choice is legitimate. Human reading time
			# must not consume the loading timeout or dismiss this native UI.
			if world.menus._mode in ["level_up", "start_skill"]:
				if not waiting_for_choice:
					print("OFFLINE_MVP_MENU_QA WAIT_NATIVE_CHOICE")
				waiting_for_choice = true
				deadline = Time.get_ticks_msec() + 12000
				await get_tree().process_frame
				continue
			waiting_for_choice = false
			if world.menus._mode == "loading":
				world.menus.close()
				# The loading overlay is owned by this transition.
				if world.menus._mode in ["", "closed"]:
					get_tree().paused = false
			if world.menus._mode not in ["", "closed"] or get_tree().paused:
				await get_tree().process_frame
				continue
			var boss: Enemy = await MVPEncounter.spawn(world, boss_id)
			if is_instance_valid(boss):
				mvp_last_spawn = boss
				mvp_last_id = boss_id
				_attach_mvp_hud(world, boss)
			print("OFFLINE_MVP_MENU_QA SPAWN id=", boss_id, " success=", is_instance_valid(boss))
			mvp_launching = false
			return
		await get_tree().process_frame
	print("OFFLINE_MVP_MENU_QA BLOCKED native_transition callback=", mvp_loading_callback_completed)
	if is_instance_valid(world):
		print("OFFLINE_MVP_MENU_QA TRANSITION mode=", str(world.menus._mode), " paused=", get_tree().paused, " running=", world.running)
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
