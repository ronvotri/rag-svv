extends Node
## Keep the original game menu's Discord entry; turn the adjacent publisher
## donation button into an actual local-save export reminder. Web only.
## This is event-driven (not per frame) and does not touch game/saved state.
const DISCORD_INVITE_URL := "" # Configure only with owner's verified invite.
const SAVE_BUTTON_NAME := "SVVSaveBackupButton"
var _pending: bool = false
var _dialog: ConfirmationDialog


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
		donate.tooltip_text = "Sao lưu save về máy để phòng mất dữ liệu"
		if donate is Button:
			(donate as Button).text = "Sao lưu"
			(donate as Button).icon = _make_save_icon()
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
	# Small pixel-art floppy disk so this does not depend on mobile emoji fonts.
	var pixels: Image = Image.create(24, 24, false, Image.FORMAT_RGBA8)
	pixels.fill(Color(0, 0, 0, 0))
	pixels.fill_rect(Rect2i(2, 1, 20, 22), Color("#25415b"))
	pixels.fill_rect(Rect2i(4, 3, 16, 18), Color("#75b4db"))
	pixels.fill_rect(Rect2i(7, 3, 10, 8), Color("#f0f3f4"))
	pixels.fill_rect(Rect2i(14, 4, 2, 5), Color("#35465c"))
	pixels.fill_rect(Rect2i(6, 13, 12, 8), Color("#ecf0e8"))
	pixels.fill_rect(Rect2i(8, 15, 8, 2), Color("#9cb9cb"))
	pixels.fill_rect(Rect2i(8, 18, 8, 1), Color("#9cb9cb"))
	return ImageTexture.create_from_image(pixels)


func _show_backup_dialog() -> void:
	if _dialog == null:
		_dialog = ConfirmationDialog.new()
		_dialog.title = "Sao lưu save"
		_dialog.dialog_text = "Hãy thường xuyên tải bản sao save về máy, nhất là trước khi xóa dữ liệu trình duyệt hoặc đổi điện thoại.\n\nTệp sao lưu sẽ được lưu trên thiết bị của bạn, không tải lên máy chủ."
		_dialog.ok_button_text = "Tải bản save"
		_dialog.cancel_button_text = "Để sau"
		_dialog.confirmed.connect(_export_save)
		get_tree().root.add_child(_dialog)
	_dialog.popup_centered(Vector2i(550, 280))


func _notify_save_error(message: String) -> void:
	var alert: AcceptDialog = AcceptDialog.new()
	alert.title = "Sao lưu chưa thành công"
	alert.dialog_text = message
	get_tree().root.add_child(alert)
	alert.confirmed.connect(alert.queue_free)
	alert.popup_centered(Vector2i(470, 190))


func _export_save() -> void:
	if not OS.has_feature("web"):
		return
	Save.flush()
	var save_path: String = str(Save.PATH)
	if not FileAccess.file_exists(save_path):
		_notify_save_error("Chưa có save để xuất. Hãy tạo nhân vật và lưu game trước.")
		return
	var data: PackedByteArray = FileAccess.get_file_as_bytes(save_path)
	if data.size() < 32:
		_notify_save_error("Tệp save trống hoặc chưa hoàn chỉnh. Chưa xuất dữ liệu.")
		return
	if SVVSaveGuardian != null:
		SVVSaveGuardian.backup_now()
	var encoded: String = Marshalls.raw_to_base64(data)
	var date_tag: String = Time.get_date_string_from_system().replace("-", "")
	var filename: String = "Quai-Trieu-Xam-Lang-%s.svvsave" % date_tag
	# JSON.stringify safely escapes both JS string literals. No network calls:
	# Blob creates a local download of the same encrypted profile bytes.
	var js: String = "(function(){var b=atob(%s);var a=new Uint8Array(b.length);for(var i=0;i<b.length;i++)a[i]=b.charCodeAt(i);var url=URL.createObjectURL(new Blob([a],{type:'application/octet-stream'}));var link=document.createElement('a');link.href=url;link.download=%s;document.body.appendChild(link);link.click();link.remove();setTimeout(function(){URL.revokeObjectURL(url)},30000);return true;})()" % [JSON.stringify(encoded), JSON.stringify(filename)]
	var succeeded: Variant = JavaScriptBridge.eval(js)
	if succeeded != true:
		_notify_save_error("Trình duyệt chưa cho tải save. Hãy thử lại trong Chrome.")


func _open_discord() -> void:
	if not DISCORD_INVITE_URL.begins_with("https://discord.gg/") and not DISCORD_INVITE_URL.begins_with("https://discord.com/invite/"):
		return
	if OS.has_feature("web"):
		var browser: JavaScriptObject = JavaScriptBridge.get_interface("window")
		if browser != null:
			browser.open(DISCORD_INVITE_URL, "_blank", "noopener,noreferrer")
	else:
		OS.shell_open(DISCORD_INVITE_URL)
