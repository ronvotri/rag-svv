extends Node
## Offline browser save manager. No upload/network sync: downloads and chosen files
## stay on the player's device. The current encrypted Save.PATH bytes are used.
const MAX_SAVE_BYTES := 8 * 1024 * 1024
const BEFORE_IMPORT := "user://svv-before-import.svvsave"
var dialog: AcceptDialog
var confirm_import: ConfirmationDialog
var callback_import: JavaScriptObject


func open_manager() -> void:
	if not OS.has_feature("web"):
		return
	var scene := get_tree().current_scene
	if scene is World and (scene as World).running:
		_alert("Hãy về Prontera trước khi nhập hoặc khôi phục save.")
		return
	if dialog == null:
		_build_dialog()
	dialog.popup_centered(Vector2i(570, 330))


func _build_dialog() -> void:
	dialog = AcceptDialog.new()
	dialog.title = "Sao lưu dữ liệu"
	dialog.get_ok_button().text = "Đóng"
	get_tree().root.add_child(dialog)
	var holder: VBoxContainer = dialog.get_vbox()
	var description := Label.new()
	description.text = "Dữ liệu chỉ nằm trên thiết bị của bạn.\nHãy tải một bản save về máy trước khi cập nhật game, xóa cache hay đổi điện thoại."
	description.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	holder.add_child(description)
	var spacer := Control.new()
	spacer.custom_minimum_size.y = 10
	holder.add_child(spacer)
	var export_button := Button.new()
	export_button.text = "Tải save xuống máy"
	export_button.tooltip_text = "Xuất hồ sơ offline hiện tại thành tệp .svvsave"
	export_button.pressed.connect(export_save)
	holder.add_child(export_button)
	var import_button := Button.new()
	import_button.text = "Nạp save từ tệp"
	import_button.tooltip_text = "Chọn tệp .svvsave đã tải xuống trước đây"
	import_button.pressed.connect(_confirm_choose_import)
	holder.add_child(import_button)
	var restore_button := Button.new()
	restore_button.text = "Khôi phục save trước lần nhập gần nhất"
	restore_button.pressed.connect(_restore_previous)
	holder.add_child(restore_button)
	var note := Label.new()
	note.text = "Nhập hoặc khôi phục sẽ thay thế save đang chơi và khởi động lại Web."
	note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	holder.add_child(note)


func _alert(message: String) -> void:
	var popup := AcceptDialog.new()
	popup.title = "Quái Triều Xâm Lăng – Save"
	popup.dialog_text = message
	get_tree().root.add_child(popup)
	popup.confirmed.connect(popup.queue_free)
	popup.close_requested.connect(popup.queue_free)
	popup.popup_centered(Vector2i(540, 220))


func _save_path() -> String:
	return str(Save.PATH)


func _current_save_bytes() -> PackedByteArray:
	Save.flush()
	var path := _save_path()
	if not FileAccess.file_exists(path):
		return PackedByteArray()
	return FileAccess.get_file_as_bytes(path)


func export_save() -> void:
	if not OS.has_feature("web"):
		return
	var bytes := _current_save_bytes()
	if bytes.size() < 32 or bytes.size() > MAX_SAVE_BYTES:
		_alert("Save chưa tồn tại hoặc không hợp lệ. Hãy tạo nhân vật rồi lưu trước.")
		return
	SVVSaveGuardian.backup_now()
	var b64: String = Marshalls.raw_to_base64(bytes)
	var filename: String = "Quai-Trieu-Xam-Lang-" + Time.get_date_string_from_system().replace("-", "") + ".svvsave"
	# The click comes directly from a Godot button; browser Blob never leaves
	# the device. JSON.stringify protects the generated JS string literals.
	var js := "(function(){const s=atob(%s), b=new Uint8Array(s.length);for(let i=0;i<s.length;i++)b[i]=s.charCodeAt(i);const u=URL.createObjectURL(new Blob([b],{type:'application/octet-stream'}));const a=document.createElement('a');a.href=u;a.download=%s;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),30000);return true;})()" % [JSON.stringify(b64), JSON.stringify(filename)]
	if JavaScriptBridge.eval(js) != true:
		_alert("Chrome chưa cho tải tệp. Hãy thử lại bằng trình duyệt Chrome thông thường.")


func _confirm_choose_import() -> void:
	if confirm_import == null:
		confirm_import = ConfirmationDialog.new()
		confirm_import.title = "Nhập save từ máy"
		confirm_import.dialog_text = "Save hiện tại sẽ bị thay thế. Game giữ một bản dự phòng ngay trên thiết bị trước khi nhập.\n\nChỉ chọn tệp .svvsave mà bạn đã xuất từ Quái Triều Xâm Lăng. Tiếp tục?"
		confirm_import.ok_button_text = "Chọn tệp save"
		confirm_import.cancel_button_text = "Hủy"
		confirm_import.confirmed.connect(_choose_import_file)
		get_tree().root.add_child(confirm_import)
	confirm_import.popup_centered(Vector2i(540, 260))


func _choose_import_file() -> void:
	if not OS.has_feature("web"):
		return
	# Store callback object on the Godot Node so JS doesn't lose the reference.
	if callback_import == null:
		callback_import = JavaScriptBridge.create_callback(_receive_import_file)
	var browser: JavaScriptObject = JavaScriptBridge.get_interface("window")
	browser._svvReceiveFile = callback_import
	var js := "(function(){const picker=document.createElement('input');picker.type='file';picker.accept='.svvsave';picker.style.display='none';document.body.appendChild(picker);picker.onchange=()=>{const f=picker.files&&picker.files[0];picker.remove();if(!f)return;if(f.size<32||f.size>8388608){window._svvReceiveFile('', 'INVALID_SIZE');return;}const r=new FileReader();r.onerror=()=>window._svvReceiveFile('', 'READ_ERROR');r.onload=()=>window._svvReceiveFile(String(r.result).split(',')[1]||'', f.name);r.readAsDataURL(f);};picker.click();return true;})()"
	if JavaScriptBridge.eval(js) != true:
		_alert("Trình duyệt chưa mở được bộ chọn save.")


func _receive_import_file(arguments: Array) -> void:
	if arguments.size() < 2:
		return
	var encoded: String = str(arguments[0])
	var filename: String = str(arguments[1])
	if not filename.to_lower().ends_with(".svvsave"):
		_alert("Chỉ nhận tệp .svvsave do game này xuất ra.")
		return
	if encoded.length() > MAX_SAVE_BYTES * 2:
		_alert("Tệp save quá lớn.")
		return
	var bytes := Marshalls.base64_to_raw(encoded)
	if bytes.size() < 32 or bytes.size() > MAX_SAVE_BYTES:
		_alert("Tệp save không hợp lệ, quá nhỏ hoặc quá lớn. Dữ liệu cũ được giữ nguyên.")
		return
	_apply_import(bytes)


func _apply_import(bytes: PackedByteArray) -> void:
	# Preserve the old encrypted profile before any replacement.
	var old_data := _current_save_bytes()
	if old_data.size() >= 32:
		if not SVVSaveGuardian._write_atomically(BEFORE_IMPORT, old_data):
			_alert("Không tạo được bản dự phòng. Đã hủy nhập để tránh mất save.")
			return
		SVVSaveGuardian.backup_now()
	if not SVVSaveGuardian._write_atomically(_save_path(), bytes):
		_alert("Không ghi được save mới. Bản cũ đã được giữ để khôi phục.")
		return
	if not SVVSaveGuardian.adopt_imported_profile(bytes):
		_alert("Không lưu được bản bảo hiểm của save nhập. Hãy xuất save dự phòng trước khi tiếp tục.")
		return
	# Reload through the bootstrap to reopen the encrypted profile. Never
	# mix new bytes with existing in-memory save/state.
	JavaScriptBridge.eval("window.location.replace('./?save_imported=' + Date.now())")


func _restore_previous() -> void:
	if not FileAccess.file_exists(BEFORE_IMPORT):
		_alert("Chưa có bản dự phòng từ lần nhập save trước.")
		return
	var bytes := FileAccess.get_file_as_bytes(BEFORE_IMPORT)
	if bytes.size() < 32 or bytes.size() > MAX_SAVE_BYTES:
		_alert("Bản dự phòng không hợp lệ, chưa khôi phục.")
		return
	_apply_import(bytes)
