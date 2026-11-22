extends CanvasLayer
## Authored offline party selector and contextual guide for the local recovery.
## This guide is rule-based. A language model is not impersonated here.

var panel: PanelContainer
var messages: RichTextLabel
var entry: LineEdit
var friend_list: VBoxContainer
var detail_card: PanelContainer
var friend_details: RichTextLabel
var friend_portrait: TextureRect
var portrait_atlas: Texture2D
var friend_action: Button
var selected_class := "acolyte"
# Authored local NPC friendship profiles; class IDs come from recovered GameData.
# These are story characters, not simulated online player accounts.
const FRIEND_PROFILES := {
	"acolyte": {"name": "Mira", "rarity": "Normal", "kills": 8, "runs": 1, "role": "Hồi máu · hỗ trợ cả đội", "intro": "Mira: Đứng lại cho tôi chữa thương nào! Ham đánh quá là hết cả bông băng đấy.", "quest": "Tiếp tế y viện: giúp Mira chống trả 8 quái và hoàn thành 1 lượt phiêu lưu."},
	"swordsman": {"name": "Alden", "rarity": "Normal", "kills": 20, "runs": 1, "role": "Tuyến đầu · chịu đòn và giữ quái", "location": "Prontera", "quest": "Lời thề vệ binh: chiến đấu với 20 quái và trở về an toàn sau 1 lượt."},
	"mage": {"name": "Eira", "rarity": "Normal", "kills": 25, "runs": 1, "role": "Tấn công phép · gây sát thương diện rộng", "location": "Prontera", "quest": "Thí nghiệm phép thuật: xử lý 25 quái trong hành trình cùng Eira."},
	"archer": {"name": "Elowen", "rarity": "Normal", "kills": 25, "runs": 1, "role": "Đánh xa · giữ khoảng cách", "intro": "Elowen: Cung không tự bắn trúng đâu nhé. Muốn theo tôi đi tuần thì chứng minh tay nghề trước!", "quest": "Tuần tra cung thủ: hạ 25 quái qua ít nhất 1 lượt phiêu lưu."},
	"thief": {"name": "Riku", "rarity": "Normal", "kills": 30, "runs": 1, "role": "Cận chiến cơ động · né tránh", "intro": "Riku: Đừng nhìn tôi kiểu đó. Ví của cậu còn nguyên mà... chắc thế.", "quest": "Bài kiểm tra của Riku: vượt qua 30 quái, đừng bỏ cuộc giữa đường."},
	"merchant": {"name": "Mino", "rarity": "Normal", "kills": 30, "runs": 2, "role": "Đấu sĩ hỗ trợ · Merchant", "intro": "Mino: Đi săn quái thì được, nhưng phá hàng của tôi là phải đền. Có hóa đơn đầy đủ!", "quest": "Bảo vệ thương đoàn: hạ 30 quái qua ít nhất 2 lượt."},
	"novice": {"name": "Nao", "rarity": "Normal", "kills": 15, "runs": 2, "role": "Tân binh · học hỏi và hỗ trợ", "intro": "Nao: Tôi mới vào nghề thôi. Nếu thấy tôi chạy ngược hướng, gọi với nhé!", "quest": "Đường của tân binh: giúp Nao vượt qua 15 quái trong 2 lượt."},
	"gunslinger": {"name": "Cole", "rarity": "Rare", "kills": 90, "runs": 3, "role": "Xạ thủ · bắn xa liên tục", "intro": "Cole: Đứng yên cho tôi ngắm. Đùa thôi, quái đông thế ai mà đứng yên!", "quest": "Hợp đồng của Cole: hạ 90 quái trong ít nhất 3 lượt."},
	"taekwon": {"name": "Haneul", "rarity": "Rare", "kills": 100, "runs": 3, "role": "Võ sư · cận chiến cơ động", "intro": "Haneul: Tôi đá nhanh hơn lời đồn. Cứ xem trận tới là biết!", "quest": "Rèn luyện của Haneul: hạ 100 quái và hoàn thành 3 lượt."},
	"ninja": {"name": "Kira", "rarity": "Ultra Rare", "kills": 220, "runs": 5, "role": "Ninja · áp sát và đánh úp", "intro": "Kira: Tôi không biến mất đâu. Chỉ là cậu chớp mắt quá lâu thôi.", "quest": "Thử thách bóng đêm: hạ 220 quái và hoàn thành 5 lượt."},
	"doram": {"name": "Lumi", "rarity": "Ultra Rare", "kills": 240, "runs": 5, "role": "Triệu hồi · hỗ trợ phép", "intro": "Lumi: Cục bông này hiền lắm! Trừ lúc đụng đến bạn tôi.", "quest": "Giao ước với Lumi: hạ 240 quái và hoàn thành 5 lượt."},
}


# 4-column, 192px source atlas. All portraits are authored art; names and
# party/recruitment data remain the original offline profiles.
const FRIEND_PORTRAIT_IDS := {
	"acolyte": 0, "swordsman": 1, "mage": 2, "archer": 3,
	"thief": 4, "merchant": 5, "novice": 6, "gunslinger": 7,
	"taekwon": 8, "ninja": 9, "doram": 10,
}

var status: Label
var open_button: Button
var veil: ColorRect
var was_paused := false
var available_ids: Array[String] = []
# Offline-only safety net: a limited recovery pulse for a living Acolyte party member.
# This is a separate support perk, NOT a pretend cast of the original Heal skill.
var support_hint: Label
var support_check_seconds := 0.0
var support_cooldown_seconds := 0.0
var support_world_id := 0
var support_flash_seconds := 0.0

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 110
	var portrait_path := "res://addons/svv_offline/friend_portraits.jpg"
	if ResourceLoader.exists(portrait_path):
		portrait_atlas = load(portrait_path) as Texture2D
	else:
		push_warning("SVV: friend portrait atlas unavailable; retain text-only fallback")
	open_button = Button.new()
	open_button.text = "Bạn bè"
	open_button.custom_minimum_size = Vector2(132, 38)
	open_button.pressed.connect(_open)
	_style_toolbar_button(open_button)
	add_child(open_button)
	support_hint = Label.new()
	support_hint.text = ""
	support_hint.add_theme_color_override("font_color", Color("a5f1ba"))
	support_hint.add_theme_font_size_override("font_size", 14)
	support_hint.mouse_filter = Control.MOUSE_FILTER_IGNORE
	support_hint.hide()
	add_child(support_hint)
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
	background.bg_color = Color("10332b")
	background.border_color = Color("f6ca68")
	background.set_border_width_all(3)
	background.set_corner_radius_all(14)
	background.set_content_margin_all(16)
	panel.add_theme_stylebox_override("panel", background)
	add_child(panel)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 12)
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	panel.add_child(scroll)
	column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(column)
	var title := Label.new()
	title.text = "Friends List · Bằng hữu Midgard"
	title.add_theme_font_size_override("font_size", 24)
	title.add_theme_color_override("font_color", Color("fff8e8"))
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	column.add_child(title)
	status = Label.new()
	status.text = "Làm nhiệm vụ của NPC, kết bạn rồi mới có thể mời vào party (tối đa 3)."
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	status.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	status.add_theme_font_size_override("font_size", 14)
	status.add_theme_color_override("font_color", Color("cbded8"))
	column.add_child(status)
	for key in GameData.CLASSES:
		available_ids.append(str(key))
	available_ids.sort()
	if available_ids.has("acolyte"):
		available_ids.erase("acolyte")
		available_ids.insert(0, "acolyte")
	elif not available_ids.is_empty():
		selected_class = available_ids[0]
	detail_card = PanelContainer.new()
	detail_card.add_theme_stylebox_override("panel", _friend_style("17473b", "508772", 2, 12))
	column.add_child(detail_card)
	friend_details = RichTextLabel.new()
	friend_details.bbcode_enabled = true
	friend_details.fit_content = true
	friend_details.scroll_active = false
	friend_details.selection_enabled = false
	friend_details.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	friend_details.add_theme_font_size_override("normal_font_size", 16)
	friend_details.add_theme_color_override("default_color", Color("eff7f1"))
	var hero_line := HBoxContainer.new()
	hero_line.add_theme_constant_override("separation", 14)
	detail_card.add_child(hero_line)
	friend_portrait = _portrait_view(selected_class, 170)
	friend_portrait.custom_minimum_size = Vector2(170, 190)
	hero_line.add_child(friend_portrait)
	friend_details.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hero_line.add_child(friend_details)
	friend_action = Button.new()
	friend_action.text = "Nhận nhiệm vụ"
	friend_action.custom_minimum_size.y = 50
	friend_action.add_theme_font_size_override("font_size", 19)
	friend_action.add_theme_color_override("font_color", Color("472606"))
	friend_action.add_theme_color_override("font_hover_color", Color("341902"))
	friend_action.add_theme_stylebox_override("normal", _friend_style("ffce64", "fff0ad", 2, 10))
	friend_action.add_theme_stylebox_override("hover", _friend_style("ffdf89", "ffffff", 2, 10))
	friend_action.add_theme_stylebox_override("pressed", _friend_style("e9ae42", "fff0ad", 2, 10))
	friend_action.add_theme_stylebox_override("disabled", _friend_style("435a4f", "6d8475", 1, 10))
	friend_action.pressed.connect(_friend_action_pressed)
	column.add_child(friend_action)
	var roster_heading := Label.new()
	roster_heading.text = "Cư dân Midgard · chọn NPC để xem nhiệm vụ"
	roster_heading.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	roster_heading.add_theme_font_size_override("font_size", 18)
	roster_heading.add_theme_color_override("font_color", Color("b4f0cd"))
	column.add_child(roster_heading)
	friend_list = VBoxContainer.new()
	friend_list.add_theme_constant_override("separation", 7)
	column.add_child(friend_list)
	_refresh_friends()
	var explanation := Label.new()
	explanation.text = "NPC đồng hành được game điều khiển, không phải người chơi online. Hỏi NPC Linh nếu cần trợ giúp."
	explanation.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	explanation.add_theme_font_size_override("font_size", 12)
	column.add_child(explanation)
	var npc_heading := Label.new()
	npc_heading.text = "Hỏi NPC Linh"
	npc_heading.add_theme_font_size_override("font_size", 18)
	column.add_child(npc_heading)
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

# Visual styling only: independent of quest/save state and safe to refresh.
func _portrait_texture(job: String) -> Texture2D:
	if portrait_atlas == null:
		return null
	var slot: int = int(FRIEND_PORTRAIT_IDS.get(job, 11))
	var atlas := AtlasTexture.new()
	atlas.atlas = portrait_atlas
	atlas.region = Rect2(Vector2((slot % 4) * 192 + 2, floori(float(slot) / 4.0) * 192 + 2), Vector2(188, 188))
	return atlas


func _portrait_view(job: String, side_px: int) -> TextureRect:
	var icon := TextureRect.new()
	icon.custom_minimum_size = Vector2(side_px, side_px)
	icon.texture = _portrait_texture(job)
	icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return icon


# Match the game's native pale-blue top tabs. Keep a solid surface;
# a transparent CanvasLayer Button becomes unreadable on the town fountain.
func _style_toolbar_button(button: Button) -> void:
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
	var pressed := normal.duplicate() as StyleBoxFlat
	pressed.bg_color = Color("c9dcfd")
	button.add_theme_stylebox_override("pressed", pressed)
	button.add_theme_color_override("font_color", Color("253d74"))
	button.add_theme_color_override("font_hover_color", Color("1d356c"))
	button.add_theme_color_override("font_pressed_color", Color("1d356c"))
	button.add_theme_font_size_override("font_size", 16)


func _friend_style(background_hex: String, border_hex: String, border_px: int, radius_px: int) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = Color(background_hex)
	style.border_color = Color(border_hex)
	style.set_border_width_all(border_px)
	style.set_corner_radius_all(radius_px)
	style.set_content_margin_all(12)
	return style


func _friend_rarity_color(rarity: String) -> String:
	match rarity:
		"Ultra Rare":
			return "cf9cfc"
		"Rare":
			return "85c8ff"
		_:
			return "cbd7e4"


func _friend_status(unlocked: Array, party: Array[String], job: String) -> String:
	if party.has(job):
		return "[color=#9dd7ff]● Đang đi cùng[/color]"
	if unlocked.has(job):
		return "[color=#9ef0c7]● Đã kết bạn[/color]"
	return "[color=#e4d4ad]⌛ Chưa kết bạn[/color]"


func _fit() -> void:
	var size := get_viewport().get_visible_rect().size
	# Pair Friends + Save in one right-aligned top strip. On narrow
	# screens move the two buttons together below the game's native tabs
	# rather than overlapping the menu/character/channel controls.
	var narrow: bool = size.x < 1200.0
	var friend_width: float = 98.0 if size.x < 680.0 else (112.0 if narrow else 132.0)
	var save_width: float = 114.0 if size.x < 680.0 else (154.0 if narrow else 188.0)
	var start_x: float = maxf(8.0, size.x - 12.0 - friend_width - 8.0 - save_width)
	var toolbar_y: float = 56.0 if narrow else 10.0
	open_button.custom_minimum_size = Vector2(friend_width, 38.0)
	open_button.position = Vector2(start_x, toolbar_y)
	support_hint.position = Vector2(start_x, toolbar_y + 43.0)
	var width := minf(710, size.x - 24)
	var height := minf(700, size.y - 24)
	panel.offset_left = -width / 2
	panel.offset_right = width / 2
	panel.offset_top = -height / 2
	panel.offset_bottom = height / 2

func _process(delta: float) -> void:
	if get_tree().paused:
		return
	if support_flash_seconds > 0.0:
		support_flash_seconds = maxf(0.0, support_flash_seconds - delta)
		if support_flash_seconds == 0.0:
			support_hint.hide()
	support_check_seconds += delta
	if support_check_seconds < 0.4:
		return
	var elapsed := support_check_seconds
	support_check_seconds = 0.0
	var world := _world()
	# This is a pre-adventure party setup control, not a gameplay HUD item.
	# Hide it as soon as a battle starts, restore it in town/lobby.
	open_button.visible = (world == null or not world.running)
	if world == null or not world.running:
		support_cooldown_seconds = 0.0
		support_world_id = 0
		return
	var current_id := world.get_instance_id()
	if current_id != support_world_id:
		support_world_id = current_id
		support_cooldown_seconds = 3.0
	support_cooldown_seconds = maxf(0.0, support_cooldown_seconds - elapsed)
	if support_cooldown_seconds > 0.0:
		return
	if _try_support_heal(world):
		support_cooldown_seconds = 9.0
	else:
		support_cooldown_seconds = 0.8

func _try_support_heal(world: World) -> bool:
	# Support only NPC party members, not the human Acolyte. No effect when
	# the Acolyte is downed, the battle is over, or the party is healthy.
	if world == null or not world.running:
		return false
	# The upstream 0.2.0 BotHero's runtime class_id does not reliably
	# identify its original chosen class. The offline roster remains authoritative.
	# An old run snapshot must not bypass the new recruitment gate.
	if not _unlocked_friends().has("acolyte"):
		return false
	var support_slot: int = world.coop_classes.find("acolyte")
	if support_slot < 0 or support_slot + 1 >= world.heroes.size():
		return false
	var acolyte: Player = world.heroes[support_slot + 1]
	if acolyte == null or not is_instance_valid(acolyte) or acolyte.downed or acolyte.hp <= 0.0:
		return false
	var recipient: Player = null
	var lowest_health := 0.78
	for ally in world.heroes:
		if ally == null or not is_instance_valid(ally) or ally.downed or ally.hp <= 0.0 or ally.max_hp <= 0.0:
			continue
		var health_ratio: float = ally.hp / ally.max_hp
		if health_ratio < lowest_health:
			lowest_health = health_ratio
			recipient = ally
	if recipient == null:
		return false
	var recovered: float = ceilf(recipient.max_hp * 0.17)
	recipient.hp = minf(recipient.max_hp, recipient.hp + recovered)
	support_hint.text = "✚ Tu Sĩ tiếp sức: +%d HP" % int(recovered)
	support_hint.show()
	support_flash_seconds = 1.5
	var mira_npc := get_tree().root.get_node_or_null("SVVMiraTown")
	if mira_npc != null and mira_npc.has_method("play_heal_fx"):
		mira_npc.play_heal_fx(recipient, recovered)
	return true

func _unlocked_friends() -> Array:
	var friends = Save.setting("svv_offline_friends", [])
	return friends if friends is Array else []


func _friend_quests() -> Dictionary:
	var quests = Save.setting("svv_friend_quests", {})
	return quests if quests is Dictionary else {}


func _friend_profile(job: String) -> Dictionary:
	if FRIEND_PROFILES.has(job):
		return FRIEND_PROFILES[job]
	return {"name": "Lữ khách " + job, "rarity": "Normal", "kills": 35, "runs": 2,
		"quest": "Giúp lữ khách vượt qua 35 quái và hoàn thành 2 lượt phiêu lưu."}


func _job_name(job: String) -> String:
	if GameData.CLASSES.has(job):
		return tr(str(GameData.CLASSES[job].get("name", job)))
	return job


func _party_members() -> Array[String]:
	var saved = Save.setting("svv_offline_party", [])
	var friends: Array = _unlocked_friends()
	var result: Array[String] = []
	if saved is Array:
		for candidate in saved:
			var job: String = str(candidate)
			if friends.has(job) and GameData.CLASSES.has(job) and not result.has(job) and result.size() < 3:
				result.append(job)
	return result


func _quest_progress(job: String) -> Dictionary:
	var profile: Dictionary = _friend_profile(job)
	var quest = _friend_quests().get(job, {})
	if not quest is Dictionary or quest.is_empty():
		return {"started": false, "ready": false, "kills": 0, "runs": 0}
	var kills: int = maxi(0, int(Save.stat("kills")) - int(quest.get("kills_at_start", 0)))
	var runs: int = maxi(0, int(Save.stat("runs")) - int(quest.get("runs_at_start", 0)))
	return {"started": true, "ready": kills >= int(profile["kills"]) and runs >= int(profile["runs"]),
		"kills": mini(kills, int(profile["kills"])), "runs": mini(runs, int(profile["runs"]))}


func _refresh_friends() -> void:
	if friend_list == null:
		return
	var unlocked: Array = _unlocked_friends()
	var party: Array[String] = _party_members()
	status.text = "Party: %d/3 · Chỉ mời NPC đã kết bạn. Tất cả hoạt động offline." % party.size()
	for child in friend_list.get_children():
		friend_list.remove_child(child)
		child.queue_free()
	for job in available_ids:
		var profile: Dictionary = _friend_profile(job)
		var is_selected: bool = job == selected_class
		var row := PanelContainer.new()
		row.add_theme_stylebox_override("panel", _friend_style(
			"295243" if is_selected else "183b31",
			"f8cb68" if is_selected else "4b7768", 2 if is_selected else 1, 9))
		var main_line := HBoxContainer.new()
		main_line.add_theme_constant_override("separation", 10)
		row.add_child(main_line)
		var face := _portrait_view(job, 52)
		main_line.add_child(face)
		var identity := VBoxContainer.new()
		identity.add_theme_constant_override("separation", 5)
		identity.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		main_line.add_child(identity)
		var button := Button.new()
		button.text = str(profile["name"]) + " · " + _job_name(job)
		button.alignment = HORIZONTAL_ALIGNMENT_LEFT
		button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		button.clip_text = true
		button.flat = true
		button.add_theme_font_size_override("font_size", 17)
		button.add_theme_color_override("font_color", Color("ffdc89"))
		button.add_theme_color_override("font_hover_color", Color("fff0b0"))
		button.pressed.connect(_select_friend.bind(job))
		identity.add_child(button)
		var rarity := Label.new()
		rarity.text = str(profile["rarity"])
		rarity.add_theme_color_override("font_color", Color(_friend_rarity_color(str(profile["rarity"]))))
		rarity.add_theme_font_size_override("font_size", 13)
		identity.add_child(rarity)
		var state := Label.new()
		state.text = "Đang đi cùng" if party.has(job) else ("Đã kết bạn" if unlocked.has(job) else "Chưa kết bạn")
		state.add_theme_font_size_override("font_size", 13)
		state.add_theme_color_override("font_color", Color("9dd7ff") if party.has(job) else (Color("9ef0c7") if unlocked.has(job) else Color("e4d4ad")))
		state.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		state.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		main_line.add_child(state)
		friend_list.add_child(row)
	if not available_ids.has(selected_class):
		selected_class = available_ids[0] if not available_ids.is_empty() else ""
	if selected_class.is_empty():
		return
	var profile: Dictionary = _friend_profile(selected_class)
	if friend_portrait != null:
		friend_portrait.texture = _portrait_texture(selected_class)
		friend_portrait.visible = portrait_atlas != null and get_viewport().get_visible_rect().size.x > 470.0
	var progress: Dictionary = _quest_progress(selected_class)
	var rarity_tint: String = _friend_rarity_color(str(profile["rarity"]))
	var description: String = "[font_size=22][color=#ffdc89][b]" + str(profile["name"]) + "[/b][/color][/font_size]"
	description += "  [color=#f0f5ee]" + _job_name(selected_class) + "[/color]"
	description += "  [color=#" + rarity_tint + "][b]" + str(profile["rarity"]) + "[/b][/color]\n"
	if profile.has("role"):
		description += "[color=#b3f3d0][b]Vai trò:[/b][/color] " + str(profile["role"]) + "\n"
	if profile.has("location"):
		description += "[color=#b3f3d0][b]Khu vực:[/b][/color] " + str(profile["location"]) + "\n"
	if profile.has("intro"):
		description += "[color=#cedbd5][i]“" + str(profile["intro"]).trim_prefix(str(profile["name"]) + ": ") + "”[/i][/color]\n"
	description += "\n[color=#b3f3d0][b]Nhiệm vụ kết bạn[/b][/color]\n"
	if unlocked.has(selected_class):
		description += "[color=#a9ffcf][b]Đã kết bạn![/b][/color] Mời vào party trước khi phiêu lưu."
		friend_action.text = "Rời party" if party.has(selected_class) else "Mời vào party"
		friend_action.disabled = not party.has(selected_class) and party.size() >= 3
	elif selected_class != "acolyte" and not unlocked.has("acolyte") and available_ids.has("acolyte"):
		description += str(profile["quest"]) + "\n[color=#f3d49e][b]Yêu cầu:[/b][/color] Hãy giúp Mira trước để mở khóa kết bạn."
		friend_action.text = "Chưa mở khóa"
		friend_action.disabled = true
	elif bool(progress["started"]):
		description += str(profile["quest"]) + "\n[color=#b3f3d0][b]Tiến độ:[/b][/color] %d/%d quái · %d/%d lượt." % [
			int(progress["kills"]), int(profile["kills"]), int(progress["runs"]), int(profile["runs"])]
		friend_action.text = "Thu nhận NPC" if bool(progress["ready"]) else "Đang làm nhiệm vụ"
		friend_action.disabled = not bool(progress["ready"])
	else:
		description += str(profile["quest"]) + "\n[color=#f3d49e][b]Yêu cầu:[/b][/color] Hoàn thành nhiệm vụ mới có thể kết bạn."
		friend_action.text = "Nhận nhiệm vụ"
		friend_action.disabled = false
	friend_details.text = description


func _select_friend(job: String) -> void:
	if not available_ids.has(job):
		return
	selected_class = job
	_refresh_friends()


func _friend_action_pressed() -> void:
	if not available_ids.has(selected_class):
		return
	var unlocked: Array = _unlocked_friends()
	if unlocked.has(selected_class):
		var party: Array[String] = _party_members()
		if party.has(selected_class):
			party.erase(selected_class)
		elif party.size() < 3:
			party.append(selected_class)
		else:
			return
		Save.set_setting("svv_offline_party", party)
		Save.flush()
		var world := _world()
		if world != null and not world.running:
			world.coop_classes.assign(party)
	elif selected_class == "acolyte" or unlocked.has("acolyte") or not available_ids.has("acolyte"):
		var quests: Dictionary = _friend_quests()
		var progress: Dictionary = _quest_progress(selected_class)
		if not bool(progress["started"]):
			quests[selected_class] = {
				"kills_at_start": int(Save.stat("kills")),
				"runs_at_start": int(Save.stat("runs")),
			}
			Save.set_setting("svv_friend_quests", quests)
			Save.flush()
		elif bool(progress["ready"]):
			unlocked.append(selected_class)
			quests.erase(selected_class)
			Save.set_setting("svv_offline_friends", unlocked)
			Save.set_setting("svv_friend_quests", quests)
			Save.flush()
	_refresh_friends()


func _restore_party() -> void:
	# Legacy class-only rosters are retained in the profile, but unbefriended
	# companions never spawn in a new run after switching to Friends List.
	var party: Array[String] = _party_members()
	Save.set_setting("svv_offline_party", party)
	Save.flush()
	var world := _world()
	if world != null and not world.running:
		world.coop_classes.assign(party)
	_refresh_friends()


func _open() -> void:
	var world := _world()
	if world != null and world.running:
		return
	if panel.visible:
		return
	was_paused = get_tree().paused
	get_tree().paused = true
	veil.show()
	panel.show()
	_refresh_friends()
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
		answer = "NPC Linh trò chuyện theo kịch bản offline, không phải mô hình ngôn ngữ lớn. Thành viên party do game tự điều khiển, không phải người chơi trực tuyến."
	elif _has(query, ["party", "bạn bè", "friends list", "tổ đội", "đồng đội", "đội hình", "bot", "hồi sinh"]):
		answer = "Mở Bạn bè, nhận và hoàn thành nhiệm vụ NPC để kết bạn. Sau đó mời tối đa ba người vào party. Mira là Tu sĩ hỗ trợ hồi máu đầu tiên."
	elif _has(query, ["lưu", "save", "đổi máy", "dữ liệu"]):
		answer = "Để chuyển save sang máy khác, nhấn Sao lưu / Nạp save ở màn hình chính rồi chọn Tải save về máy (JSON). Trên máy mới, mở cùng mục và chọn Nạp save từ máy (JSON). Game kiểm tra file và giữ một bản dự phòng trước khi nhập. Save không tự đồng bộ lên mạng."
	elif _has(query, ["boss", "mvp", "thủ lĩnh"]):
		answer = "Giữ khoảng trống để né dấu cảnh báo và đòn diện rộng. Nâng sát thương chính trước khi đấu MVP; đừng lao vào nhặt đồ giữa lúc boss chuẩn bị ra đòn. Kiểm tra hệ và khả năng phòng thủ của bộ trang bị."
	elif _has(query, ["thẻ", "hợp nhất", "card"]):
		answer = "Mở Bộ sưu tập để xem thẻ đã có, nguồn rơi và hiệu ứng. Hợp nhất cần đủ bản sao đúng loại; Eternal Card dùng trong hệ khảm. Đọc số ô và giới hạn trước khi gắn thẻ."
	elif _has(query, ["trang bị", "tinh luyện", "khảm", "kho", "zeny"]):
		answer = "Kho Kafra giữ vật phẩm giữa các lượt. Chọn bộ khởi đầu phù hợp nghề; tinh luyện, phẩm cấp và khảm thẻ dùng nguyên liệu riêng. Vượt ngưỡng an toàn có thể thất bại, nên đọc tỉ lệ và hậu quả trước khi xác nhận."
	elif _has(query, ["nghề", "kỹ năng", "nâng cấp", "build"]):
		answer = "Ưu tiên kỹ năng chính và chỉ số ghi trong phần mô tả. Kỹ năng vật lý thường tăng theo STR, phép theo INT; tiến hóa cần đúng kỹ năng và bị động. Chọn một nhánh tấn công rồi thêm hồi phục hoặc phòng thủ."
	elif _has(query, ["nhiệm vụ", "thành tựu", "pet", "thú cưng", "tái sinh", "tháp"]):
		answer = "Bộ sưu tập theo dõi nhiệm vụ, thành tựu và thú cưng. Hoàn thành điều kiện bản đồ để mở vùng mới; Endless Tower và tái sinh có yêu cầu riêng. Hãy xem phần điều kiện trên từng màn thay vì tiêu tài nguyên trước."
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
