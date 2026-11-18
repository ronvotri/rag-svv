extends Node
## Offline browser save manager. No upload/network sync: downloads and chosen files
## stay on the player's device. The current encrypted Save.PATH bytes are used.
const MAX_SAVE_BYTES := 8 * 1024 * 1024
const BEFORE_IMPORT := "user://svv-before-import.svvsave"
var dialog: AcceptDialog
var confirm_import: ConfirmationDialog
var callback_import: JavaScriptObject
const JSON_FORMAT := "rag-svv-offline-save"
const JSON_VERSION := 1
const MAX_JSON_BYTES := 12 * 1024 * 1024
var open_button: Button
var open_layer: CanvasLayer


func _ready() -> void:
	if not OS.has_feature("web"):
		return
	process_mode = Node.PROCESS_MODE_ALWAYS
	open_layer = CanvasLayer.new()
	open_layer.layer = 5
	open_layer.name = "SVVSaveTools"
	get_tree().root.call_deferred("add_child", open_layer)
	open_button = Button.new()
	open_button.name = "SVVSaveImportExport"
	open_button.text = "Sao lưu / Nạp save"
	open_button.tooltip_text = "Tải save về máy hoặc nạp save từ máy khác"
	open_button.custom_minimum_size = Vector2(184, 42)
	open_button.process_mode = Node.PROCESS_MODE_ALWAYS
	open_button.pressed.connect(open_manager)
	open_layer.add_child(open_button)
	get_viewport().size_changed.connect(_fit_button)
	call_deferred("_fit_button")
	set_process(true)


func _process(_delta: float) -> void:
	if not OS.has_feature("web") or not is_instance_valid(open_button):
		return
	var scene := get_tree().current_scene
	var in_battle: bool = scene is World and (scene as World).running
	open_button.visible = not in_battle and not (dialog != null and dialog.visible)


func _fit_button() -> void:
	if not is_instance_valid(open_button):
		return
	var size := get_viewport().get_visible_rect().size
	# Companion "Tìm party" stays centered; place save beside it without
	# covering the map, screen edges or mobile touch controls.
	open_button.position = Vector2(
		clampf(size.x * 0.5 + 96.0, 8.0, maxf(8.0, size.x - 192.0)),
		maxf(8.0, minf(12.0, size.y * 0.02))
	)


func _popup_size(width: int, height: int) -> Vector2i:
	var size: Vector2 = get_viewport().get_visible_rect().size
	return Vector2i(mini(width, maxi(260, int(size.x - 24.0))),
		mini(height, maxi(180, int(size.y - 24.0))))


func _sha256(bytes: PackedByteArray) -> String:
	var context := HashingContext.new()
	if context.start(HashingContext.HASH_SHA256) != OK:
		return ""
	if context.update(bytes) != OK:
		return ""
	return context.finish().hex_encode()



func open_manager() -> void:
	if not OS.has_feature("web"):
		return
	var scene := get_tree().current_scene
	if scene is World and (scene as World).running:
		_alert("Hãy về Prontera trước khi nhập hoặc khôi phục save.")
		return
	if dialog == null:
		_build_dialog()
	dialog.popup_centered(_popup_size(570, 350))


func _build_dialog() -> void:
	dialog = AcceptDialog.new()
	dialog.title = "Sao lưu / Nạp save – Quái Vật Trỗi Dậy"
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
	export_button.text = "Tải save về máy (JSON)"
	export_button.tooltip_text = "Xuất bản sao mã hóa thành một tệp .json để chuyển máy"
	export_button.pressed.connect(export_save)
	holder.add_child(export_button)
	var import_button := Button.new()
	import_button.text = "Nạp save từ máy (JSON)"
	import_button.tooltip_text = "Chọn .json mới hoặc .svvsave đã xuất trước đây"
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
	popup.title = "Ragnarok: Quái Vật Trỗi Dậy – Save"
	popup.dialog_text = message
	get_tree().root.add_child(popup)
	popup.confirmed.connect(popup.queue_free)
	popup.close_requested.connect(popup.queue_free)
	popup.popup_centered(_popup_size(540, 220))


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
	var checksum := _sha256(bytes)
	if checksum.is_empty():
		_alert("Không xác minh được dữ liệu save. Chưa tải file.")
		return
	SVVSaveGuardian.backup_now()
	# JSON container stores the original encrypted save intact. Never put
	# decrypted player information into browser storage or external servers.
	var data := {
		"format": JSON_FORMAT,
		"version": JSON_VERSION,
		"game": "Ragnarok: Quái Vật Trỗi Dậy",
		"encoding": "base64",
		"sha256": checksum,
		"payload": Marshalls.raw_to_base64(bytes),
		"saved_at": Time.get_datetime_string_from_system()
	}
	var filename := "Ragnarok-Quai-Vat-Troi-Day-" + Time.get_date_string_from_system().replace("-", "") + ".json"
	var encoded := Marshalls.raw_to_base64(JSON.stringify(data).to_utf8_buffer())
	var js := "(function(){const s=atob(%s),b=new Uint8Array(s.length);for(let i=0;i<s.length;i++)b[i]=s.charCodeAt(i);const u=URL.createObjectURL(new Blob([b],{type:'application/json'}));const a=document.createElement('a');a.href=u;a.download=%s;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),30000);return true;})()" % [JSON.stringify(encoded), JSON.stringify(filename)]
	if JavaScriptBridge.eval(js) != true:
		_alert("Trình duyệt chưa cho tải save. Hãy thử bằng Chrome hoặc chọn lại nút tải.")



func _confirm_choose_import() -> void:
	if confirm_import == null:
		confirm_import = ConfirmationDialog.new()
		confirm_import.title = "Nhập save từ máy"
		confirm_import.dialog_text = "Save hiện tại sẽ bị thay thế. Game giữ một bản dự phòng ngay trên thiết bị trước khi nhập.\n\nChỉ chọn .json của Ragnarok: Quái Vật Trỗi Dậy hoặc bản .svvsave cũ. Tiếp tục?"
		confirm_import.ok_button_text = "Chọn tệp save"
		confirm_import.cancel_button_text = "Hủy"
		confirm_import.confirmed.connect(_choose_import_file)
		get_tree().root.add_child(confirm_import)
	confirm_import.popup_centered(_popup_size(540, 285))


func _choose_import_file() -> void:
	if not OS.has_feature("web"):
		return
	if callback_import == null:
		callback_import = JavaScriptBridge.create_callback(_receive_import_file)
	var browser: JavaScriptObject = JavaScriptBridge.get_interface("window")
	browser._svvReceiveFile = callback_import
	# File input stays on-device. JSON is handled as text and legacy native
	# .svvsave as an encrypted byte payload.
	var js := "(function(){const picker=document.createElement('input');picker.type='file';picker.accept='.json,.svvsave';picker.style.display='none';document.body.appendChild(picker);picker.onchange=()=>{const f=picker.files&&picker.files[0];picker.remove();if(!f)return;if(f.size<32||f.size>12582912){window._svvReceiveFile('', 'INVALID_SIZE');return;}const r=new FileReader();r.onerror=()=>window._svvReceiveFile('', 'READ_ERROR');r.onload=()=>{if(f.name.toLowerCase().endsWith('.json'))window._svvReceiveFile(String(r.result),f.name);else window._svvReceiveFile(String(r.result).split(',')[1]||'',f.name);};if(f.name.toLowerCase().endsWith('.json'))r.readAsText(f,'utf-8');else r.readAsDataURL(f);};picker.oncancel=()=>picker.remove();picker.click();return true;})()"
	if JavaScriptBridge.eval(js) != true:
		_alert("Trình duyệt chưa mở được bộ chọn save.")


func _receive_import_file(arguments: Array) -> void:
	if arguments.size() < 2:
		return
	var encoded: String = str(arguments[0])
	var filename: String = str(arguments[1])
	if filename == "INVALID_SIZE" or filename == "READ_ERROR":
		_alert("Không đọc được file hoặc file vượt giới hạn 12 MB. Save cũ được giữ nguyên.")
		return
	if encoded.length() > MAX_JSON_BYTES * 2:
		_alert("Tệp save quá lớn; dữ liệu cũ được giữ nguyên.")
		return
	var bytes := PackedByteArray()
	if filename.to_lower().ends_with(".json"):
		var parsed: Variant = JSON.parse_string(encoded)
		if not parsed is Dictionary:
			_alert("JSON không hợp lệ. Chưa thay thế save.")
			return
		var container: Dictionary = parsed
		if str(container.get("format", "")) != JSON_FORMAT or int(container.get("version", 0)) != JSON_VERSION or str(container.get("encoding", "")) != "base64":
			_alert("Đây không phải bản sao lưu đúng định dạng của Ragnarok.")
			return
		var payload: String = str(container.get("payload", ""))
		if payload.length() < 44 or payload.length() > MAX_SAVE_BYTES * 2:
			_alert("Dữ liệu save trong JSON không hợp lệ.")
			return
		bytes = Marshalls.base64_to_raw(payload)
		if _sha256(bytes) != str(container.get("sha256", "")).to_lower():
			_alert("Checksum không khớp: file có thể đã hỏng. Save cũ không bị thay thế.")
			return
	elif filename.to_lower().ends_with(".svvsave"):
		bytes = Marshalls.base64_to_raw(encoded)
	else:
		_alert("Chỉ nhận file .json hoặc .svvsave do game này xuất.")
		return
	if bytes.size() < 32 or bytes.size() > MAX_SAVE_BYTES:
		_alert("Tệp save không hợp lệ hoặc vượt 8 MB. Dữ liệu cũ được giữ nguyên.")
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
		# Failure must not strand the player with a newly written, unguarded
		# profile. The old file remains on disk and can be restored atomically.
		if old_data.size() >= 32:
			SVVSaveGuardian._write_atomically(_save_path(), old_data)
		_alert("Không xác nhận được bản bảo hiểm save nhập. Đã thử phục hồi save cũ.")
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
