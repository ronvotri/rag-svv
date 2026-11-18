extends Node
## Keep the original game menu's Discord entry; turn the adjacent publisher
## donation button into an actual local-save export reminder. Web only.
## This is event-driven (not per frame) and does not touch game/saved state.
const DISCORD_INVITE_URL := "" # Configure only with owner's verified invite.
const SAVE_BUTTON_NAME := "SVVSaveBackupButton"
var _pending: bool = false


func _ready() -> void:
	if not OS.has_feature("web"):
		return
	process_mode = Node.PROCESS_MODE_ALWAYS
	get_tree().node_added.connect(_on_node_added)
	_schedule_cleanup()


func _on_node_added(node: Node) -> void:
	if node is BaseButton:
		_schedule_cleanup()


func _schedule_cleanup() -> void:
	if _pending:
		return
	_pending = true
	call_deferred("_cleanup")


func _button_hints(button: BaseButton) -> String:
	var result: String = str(button.name) + " " + str(button.tooltip_text)
	if button is Button:
		result += " " + (button as Button).text
	return result.to_lower()


func _find_donation_button(root: Node) -> BaseButton:
	if root is BaseButton:
		var hints: String = _button_hints(root)
		if "buy me a coffee" in hints or "ko-fi" in hints or str(root.name) == SAVE_BUTTON_NAME:
			return root as BaseButton
	for child in root.get_children():
		var match_button: BaseButton = _find_donation_button(child)
		if match_button != null:
			return match_button
	return null


func _disconnect_original_actions(button: BaseButton) -> void:
	for connection in button.pressed.get_connections():
		var old_action: Callable = connection.get("callable", Callable())
		if old_action.is_valid() and old_action != Callable(self, "_show_backup_dialog"):
			button.pressed.disconnect(old_action)


func _cleanup() -> void:
	_pending = false
	var donate: BaseButton = _find_donation_button(get_tree().root)
	if donate == null or not is_instance_valid(donate):
		return
	var strip: Array[BaseButton] = []
	for child in donate.get_parent().get_children():
		if child is BaseButton:
			strip.append(child as BaseButton)
	# Don't accidentally hide unrelated game menus/buttons.
	if strip.size() < 3 or strip.size() > 6:
		return
	var discord: BaseButton
	for button in strip:
		if "discord" in _button_hints(button):
			discord = button
			break
	if discord == null:
		var index: int = strip.find(donate)
		if index >= 0 and index + 1 < strip.size():
			discord = strip[index + 1] # Screenshot: coffee, Discord, YouTube, X.
	if discord == null or discord == donate:
		return
	for button in strip:
		if button != donate and button != discord:
			button.hide()
	if str(donate.name) != SAVE_BUTTON_NAME:
		_disconnect_original_actions(donate)
		donate.name = SAVE_BUTTON_NAME
		donate.tooltip_text = "Sao lưu: Tải xuống / Nhập / Khôi phục dữ liệu"
		if donate is Button:
			(donate as Button).text = "Sao lưu"
			(donate as Button).icon = _make_save_icon()
			_style_save_button(donate as Button)
		if not donate.pressed.is_connected(_show_backup_dialog):
			donate.pressed.connect(_show_backup_dialog)
	# Discord is kept; replace its original destination only if the owner
	# supplied a verified invitation, never invent a community link.
	if not DISCORD_INVITE_URL.is_empty() and not discord.pressed.is_connected(_open_discord):
		_disconnect_original_actions(discord)
		discord.pressed.connect(_open_discord)
	donate.show()
	discord.show()


func _make_save_icon() -> Texture2D:
	# Compact high-contrast 32px disk icon with a clear white label:
	# unlike emoji it displays identically on Web, mobile and desktop.
	var image: Image = Image.create(32, 32, false, Image.FORMAT_RGBA8)
	image.fill(Color.TRANSPARENT)
	image.fill_rect(Rect2i(3, 2, 26, 28), Color("#1b3656"))
	image.fill_rect(Rect2i(5, 4, 22, 24), Color("#63b9e8"))
	image.fill_rect(Rect2i(8, 4, 16, 11), Color("#f6fcff"))
	image.fill_rect(Rect2i(19, 5, 4, 8), Color("#275784"))
	image.fill_rect(Rect2i(8, 18, 16, 10), Color("#f6fcff"))
	image.fill_rect(Rect2i(10, 20, 12, 2), Color("#6d91b7"))
	image.fill_rect(Rect2i(10, 24, 10, 2), Color("#6d91b7"))
	return ImageTexture.create_from_image(image)


func _style_save_button(button: Button) -> void:
	var normal: StyleBoxFlat = StyleBoxFlat.new()
	normal.bg_color = Color("#e8f5ff")
	normal.border_color = Color("#5b9bd5")
	normal.set_border_width_all(2)
	normal.set_corner_radius_all(8)
	normal.set_content_margin_all(7)
	button.add_theme_stylebox_override("normal", normal)
	var hover: StyleBoxFlat = normal.duplicate() as StyleBoxFlat
	hover.bg_color = Color("#cfebff")
	button.add_theme_stylebox_override("hover", hover)
	button.add_theme_color_override("font_color", Color("#21466e"))
	button.add_theme_color_override("font_hover_color", Color("#173c6c"))
	button.custom_minimum_size = Vector2(140, 40)


func _show_backup_dialog() -> void:
	# The dedicated manager supports Download, Import and Recovery.
	# Keep this button as a simple entry point in the town menu.
	SVVSaveManager.open_manager()


func _open_discord() -> void:
	if not DISCORD_INVITE_URL.begins_with("https://discord.gg/") and not DISCORD_INVITE_URL.begins_with("https://discord.com/invite/"):
		return
	if OS.has_feature("web"):
		var browser: JavaScriptObject = JavaScriptBridge.get_interface("window")
		if browser != null:
			browser.open(DISCORD_INVITE_URL, "_blank", "noopener,noreferrer")
	else:
		OS.shell_open(DISCORD_INVITE_URL)
