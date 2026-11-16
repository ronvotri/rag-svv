extends CanvasLayer
## Authored offline party selector and contextual guide for the local recovery.
## This guide is rule-based. A language model is not impersonated here.

var panel: PanelContainer
var messages: RichTextLabel
var entry: LineEdit
var selectors: Array[OptionButton] = []
var status: Label
var open_button: Button
var veil: ColorRect
var was_paused := false
var available_ids: Array[String] = []

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 110
	open_button = Button.new()
	open_button.text = "Đội AI · Hỏi NPC"
	open_button.position = Vector2(12, 56)
	open_button.custom_minimum_size = Vector2(168, 36)
	open_button.pressed.connect(_open)
	add_child(open_button)
	veil = ColorRect.new()
	veil.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	veil.color = Color(0, 0, 0, 0.6)
	veil.mouse_filter = Control.MOUSE_FILTER_STOP
	veil.hide()
	add_child(veil)
	panel = PanelContainer.new()
	panel.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	panel.offset_left = -260
	panel.offset_right = 260
	panel.offset_top = -275
	panel.offset_bottom = 275
	panel.visible = false
	var background := StyleBoxFlat.new()
	background.bg_color = Color("172e26")
	background.border_color = Color("d8bd84")
	background.set_border_width_all(2)
	background.set_content_margin_all(18)
	panel.add_theme_stylebox_override("panel", background)
	add_child(panel)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 10)
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	panel.add_child(scroll)
	column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(column)
	var title := Label.new()
	title.text = "Đồng hành cùng Midgard"
	title.add_theme_font_size_override("font_size", 23)
	column.add_child(title)
	status = Label.new()
	status.text = "Chơi cục bộ · Không kết nối dịch vụ game"
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(status)
	for key in GameData.CLASSES:
		available_ids.append(str(key))
	for i in 3:
		var option := OptionButton.new()
		option.add_item("Không chọn đồng đội")
		for id in available_ids:
			option.add_item(tr(str(GameData.CLASSES[id].get("name", id))))
		column.add_child(option)
		selectors.append(option)
	var apply := Button.new()
	apply.text = "Lưu đội hình cho lượt tiếp theo"
	apply.pressed.connect(_apply_party)
	column.add_child(apply)
	var explanation := Label.new()
	explanation.text = "NPC trả lời theo kiến thức và tình huống. Chưa tích hợp mô hình ngôn ngữ trong client Godot."
	explanation.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	explanation.add_theme_font_size_override("font_size", 12)
	column.add_child(explanation)
	messages = RichTextLabel.new()
	messages.custom_minimum_size.y = 180
	messages.size_flags_vertical = Control.SIZE_EXPAND_FILL
	messages.scroll_following = true
	messages.bbcode_enabled = false
	column.add_child(messages)
	entry = LineEdit.new()
	entry.placeholder_text = "Hỏi về nghề, boss, thẻ, trang bị hoặc lưu game…"
	entry.max_length = 500
	entry.text_submitted.connect(_answer)
	column.add_child(entry)
	var actions := HBoxContainer.new()
	column.add_child(actions)
	var send := Button.new()
	send.text = "Gửi"
	send.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	send.pressed.connect(func(): _answer(entry.text))
	actions.add_child(send)
	var close_button := Button.new()
	close_button.text = "Trở lại game"
	close_button.pressed.connect(_close)
	actions.add_child(close_button)
	get_viewport().size_changed.connect(_fit)
	_fit()
	call_deferred("_restore_party")
	# Fixed test scenes only, debug builds only, and a separate test profile.
	var arguments := OS.get_cmdline_user_args()
	if OS.has_feature("debug") and "--offline-test" in arguments:
		if "--offline-qa" in arguments:
			get_tree().change_scene_to_file.call_deferred("res://addons/svv_offline/qa/offline_smoke.tscn")
		elif "--offline-visual" in arguments:
			get_tree().change_scene_to_file.call_deferred("res://addons/svv_offline/qa/offline_visual.tscn")

func _fit() -> void:
	var size := get_viewport().get_visible_rect().size
	open_button.position = Vector2(maxf(12, (size.x - 168) / 2), 10)
	var width := minf(520, size.x - 24)
	var height := minf(550, size.y - 24)
	panel.offset_left = -width / 2
	panel.offset_right = width / 2
	panel.offset_top = -height / 2
	panel.offset_bottom = height / 2

func _restore_party() -> void:
	var ids = Save.setting("svv_offline_party", ["acolyte", "mage", "archer"])
	if not ids is Array:
		ids = []
	var valid: Array[String] = []
	for id in ids:
		if GameData.CLASSES.has(str(id)) and not valid.has(str(id)) and valid.size() < 3:
			valid.append(str(id))
	var world := _world()
	if world != null:
		world.coop_classes.assign(valid)
	for i in selectors.size():
		selectors[i].select(available_ids.find(valid[i]) + 1 if i < valid.size() else 0)

func _apply_party() -> void:
	var ids: Array[String] = []
	for option in selectors:
		if option.selected > 0:
			var id: String = available_ids[option.selected - 1]
			if ids.has(id):
				status.text = "Hãy chọn các nghề khác nhau trong đội hình."
				return
			ids.append(id)
	Save.set_setting("svv_offline_party", ids)
	Save.flush()
	var world := _world()
	if world != null:
		world.coop_classes.assign(ids)
	status.text = "Đã lưu %d đồng đội. Đội hiện tại được giữ đến hết lượt." % ids.size()

func _open() -> void:
	if panel.visible:
		return
	was_paused = get_tree().paused
	get_tree().paused = true
	veil.show()
	panel.show()
	entry.grab_focus()
	if messages.text.is_empty():
		messages.add_text("Linh: Chào nhà thám hiểm! Bạn có thể hỏi về kỹ năng, boss, trang bị, thẻ, nhiệm vụ hoặc save.\n\n")

func _close() -> void:
	panel.hide()
	veil.hide()
	get_tree().paused = was_paused

func _unhandled_key_input(event: InputEvent) -> void:
	if panel.visible and event.is_action_pressed("ui_cancel"):
		_close()
		get_viewport().set_input_as_handled()

func _answer(input: String) -> void:
	var text := input.strip_edges().substr(0, 500)
	if text.is_empty():
		return
	entry.clear()
	var query := text.to_lower()
	var answer := "Mình chưa có câu trả lời cho câu này. Thử hỏi ngắn về nghề, nâng cấp, boss, trang bị, thẻ, đồng đội hoặc lưu game nhé."
	if _has(query, ["xin chào", "chào", "hello", "cảm ơn"]):
		answer = "Chào bạn! Mình có thể hướng dẫn ngay cả khi máy không có mạng."
	elif _has(query, ["chatgpt", "mô hình", "llm", "internet", "ai thật"]):
		answer = "NPC này dùng hội thoại theo luật và ngữ cảnh, chưa phải mô hình ngôn ngữ lớn. Đồng đội bot chạy trực tiếp bằng AI chiến đấu của game."
	elif _has(query, ["đồng đội", "đội hình", "bot", "hồi sinh"]):
		answer = "Chọn tối đa ba nghề đồng hành ở phía trên, rồi lưu đội hình. Đội mới có hiệu lực từ lượt tiếp theo. Bot dùng kỹ năng, chỉ số và luật chiến đấu thật; họ cũng có thể bị hạ. Chọn Tu sĩ để tăng hỗ trợ hồi phục."
	elif _has(query, ["lưu", "save", "đổi máy", "dữ liệu"]):
		answer = "Bản offline dùng hồ sơ riêng, tách khỏi game gốc. Hãy sao lưu profile_offline.json và các tệp lưu lượt trong thư mục dữ liệu ứng dụng trước khi đổi máy, gỡ app hoặc xóa dữ liệu. Save không tự đồng bộ lên mạng."
	elif _has(query, ["boss", "mvp", "thủ lĩnh"]):
		answer = "Giữ khoảng trống để né dấu cảnh báo và đòn diện rộng. Nâng sát thương chính trước khi đấu MVP; đừng lao vào nhặt đồ giữa lúc boss chuẩn bị ra đòn. Kiểm tra hệ và khả năng phòng thủ của bộ trang bị."
	elif _has(query, ["thẻ", "hợp nhất", "card"]):
		answer = "Mở Bộ sưu tập để xem thẻ đã có, nguồn rơi và hiệu ứng. Hợp nhất cần đủ bản sao đúng loại; thẻ Vĩnh cửu dùng trong hệ khảm. Đọc số ô và giới hạn trước khi gắn thẻ."
	elif _has(query, ["trang bị", "tinh luyện", "khảm", "kho", "zeny"]):
		answer = "Kho Kafra giữ vật phẩm giữa các lượt. Chọn bộ khởi đầu phù hợp nghề; tinh luyện, phẩm cấp và khảm thẻ dùng nguyên liệu riêng. Vượt ngưỡng an toàn có thể thất bại, nên đọc tỉ lệ và hậu quả trước khi xác nhận."
	elif _has(query, ["nghề", "kỹ năng", "nâng cấp", "build"]):
		answer = "Ưu tiên kỹ năng chính và chỉ số ghi trong phần mô tả. Kỹ năng vật lý thường tăng theo STR, phép theo INT; tiến hóa cần đúng kỹ năng và bị động. Chọn một nhánh tấn công rồi thêm hồi phục hoặc phòng thủ."
	elif _has(query, ["nhiệm vụ", "thành tựu", "pet", "thú cưng", "tái sinh", "tháp"]):
		answer = "Bộ sưu tập theo dõi nhiệm vụ, thành tựu và thú cưng. Hoàn thành điều kiện bản đồ để mở vùng mới; Tháp Vô Tận và tái sinh có yêu cầu riêng. Hãy xem phần điều kiện trên từng màn thay vì tiêu tài nguyên trước."
	elif _has(query, ["máu", "chết", "khó", "hồi phục"]):
		var world := _world()
		if world != null and world.player != null:
			answer = "Bạn còn %d / %d máu. Giữ khoảng trống để lùi, tránh vòng vây và ưu tiên hồi phục hoặc phòng thủ nếu thường bị hạ." % [world.player.hp, world.player.max_hp]
		else:
			answer = "Nếu thường bị hạ, hãy tăng phòng thủ và hồi phục, chọn độ nguy hiểm thấp hơn và giữ kỹ năng né cho thời điểm bị vây."
	if messages.text.length() > 12000:
		messages.clear()
	messages.add_text("Bạn: " + text + "\nLinh: " + answer + "\n\n")

func _has(query: String, words: Array) -> bool:
	for word in words:
		if query.contains(str(word)):
			return true
	return false

func _world() -> World:
	var scene := get_tree().current_scene
	if scene is World:
		return scene as World
	# QA harnesses can own a World as a child instead of being the main scene.
	return _find_world(get_tree().root)

func _find_world(node: Node) -> World:
	if node is World:
		return node as World
	for child in node.get_children():
		var result := _find_world(child)
		if result != null:
			return result
	return null
