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
var native_file_dialog: FileDialog
var pending_export := PackedByteArray()
var callback_sync: JavaScriptObject
var import_in_progress := false
var import_old_bytes := PackedByteArray()
var import_guardian_state: Dictionary = {}
var import_run_captured := false
var import_run_existed := false
var import_run_path := ""
var import_run_bytes := PackedByteArray()
var import_was_paused := false
const VALIDATION_PATH := "user://svv-import-validation.tmp"
# Newer original clients rescue a closed tab from localStorage by save_seq.
# An explicit import must replace that rescue too, even when its sequence is
# lower. Keep the prior rescue in memory until the IndexedDB transaction ends.
const RESCUE_IMPORT_JS := """
(function (key, payload) {
    if (window._svvRescueBeforeImport) return false;
    try {
        const previous = localStorage.getItem(key);
        window._svvRescueBeforeImport = {key: key, value: previous};
        localStorage.setItem(key, payload);
        return localStorage.getItem(key) === payload;
    } catch (error) { return false; }
})
"""
const RESCUE_ROLLBACK_JS := """
(function () {
    const prior = window._svvRescueBeforeImport;
    if (!prior) return true;
    try {
        if (localStorage.getItem(prior.key) !== prior.value) {
            if (prior.value === null) localStorage.removeItem(prior.key);
            else localStorage.setItem(prior.key, prior.value);
        }
        if (localStorage.getItem(prior.key) !== prior.value) return false;
        delete window._svvRescueBeforeImport;
        return true;
    } catch (error) { return false; }
})()
"""
# JavaScriptBridge.eval's local context is the pinned Godot runtime. Wait for
# its in-flight sync, then commit IDBFS and reload ONLY after the callback.
const IMPORT_SYNC_JS := """
(function () {
    if (typeof FS === 'undefined' || typeof GodotFS === 'undefined' || !GodotFS.is_persistent()) return false;
    const deadline = Date.now() + 30000;
    function sync() {
        if (GodotFS._syncing) {
            if (Date.now() >= deadline) { window._svvSaveSynced('TIMEOUT'); return; }
            setTimeout(sync, 25); return;
        }
        GodotFS._syncing = true;
        FS.syncfs(false, function (error) {
            GodotFS._syncing = false;
            window._svvSaveSynced(error ? 'ERROR' : 'OK');
        });
    }
    sync();
    return true;
})()
"""


func _ready() -> void:
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
	if not is_instance_valid(open_button):
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
	var compact: bool = size.x < 720.0
	open_button.text = "Sao lưu" if compact else "Sao lưu / Nạp save"
	open_button.custom_minimum_size = Vector2(116, 40) if compact else Vector2(184, 42)
	var width: float = open_button.custom_minimum_size.x
	open_button.position = Vector2(
		clampf(size.x * 0.5 + 96.0, 8.0, maxf(8.0, size.x - width - 8.0)),
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
	if import_in_progress:
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
	var holder := VBoxContainer.new()
	dialog.add_child(holder)
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
	note.text = "Nhập hoặc khôi phục thay thế save đang chơi. Web sẽ tải lại; ứng dụng sẽ đóng để bạn mở lại."
	note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	holder.add_child(note)


func _alert(message: String) -> void:
	var popup := AcceptDialog.new()
	popup.title = "Ragnarok: Quái Vật Trỗi Dậy – Save"
	popup.dialog_text = message
	var popup_parent: Node = get_tree().root
	if confirm_import != null and confirm_import.visible:
		popup_parent = confirm_import
	elif dialog != null and dialog.visible:
		popup_parent = dialog
	popup_parent.add_child(popup)
	popup.confirmed.connect(popup.queue_free)
	popup.close_requested.connect(popup.queue_free)
	popup.popup_centered(_popup_size(540, 220))


func _save_path() -> String:
	return str(Save.PATH)


func _before_import_path() -> String:
	return _save_path().get_basename() + ".before-import.svvsave"


func _current_save_bytes() -> PackedByteArray:
	Save.flush()
	if Save._dirty:
		return PackedByteArray()
	var path := _save_path()
	if not FileAccess.file_exists(path):
		return PackedByteArray()
	return FileAccess.get_file_as_bytes(path)


func export_save() -> void:
	if import_in_progress:
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
	var json_bytes := JSON.stringify(data).to_utf8_buffer()
	if not OS.has_feature("web"):
		pending_export = json_bytes
		_open_native_picker(true, filename)
		return
	var encoded := Marshalls.raw_to_base64(json_bytes)
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
		if dialog != null:
			dialog.add_child(confirm_import)
		else:
			get_tree().root.add_child(confirm_import)
	confirm_import.popup_centered(_popup_size(540, 285))


func _choose_import_file() -> void:
	if import_in_progress:
		return
	if not OS.has_feature("web"):
		_open_native_picker(false)
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



func _validated_profile(bytes: PackedByteArray) -> bool:
	# A container checksum proves byte integrity, not that the original loader
	# can decrypt/parse it. Validate on a separate staging file before touching
	# either the real profile or its pre-import backup.
	if bytes.size() < 32 or bytes.size() > MAX_SAVE_BYTES:
		return false
	if not SVVSaveGuardian._write_atomically(VALIDATION_PATH, bytes):
		return false
	var parsed: Dictionary = Save._read(VALIDATION_PATH)
	DirAccess.remove_absolute(ProjectSettings.globalize_path(VALIDATION_PATH))
	if not parsed.get("version") is float and not parsed.get("version") is int:
		return false
	if float(parsed.get("version", 0)) != float(Save.VERSION):
		return false
	for field in ["settings", "stats", "classes", "cards", "upgrades", "stages"]:
		if not parsed.get(field) is Dictionary:
			return false
	if not parsed.get("zeny") is float and not parsed.get("zeny") is int:
		return false
	return is_finite(float(parsed.zeny)) and float(parsed.zeny) >= 0.0


func _web_rescue_key() -> String:
	# Read only the publisher's rescue prefix, never duplicate format constants
	# or assume that an older base client has this newer rescue mechanism.
	var constants: Dictionary = Save.get_script().get_script_constant_map()
	var prefix: String = str(constants.get("WEB_RESCUE", ""))
	return "" if prefix.is_empty() else prefix + str(Save._name)


func _begin_web_rescue_import(bytes: PackedByteArray) -> bool:
	if not OS.has_feature("web"):
		return true
	var key := _web_rescue_key()
	if key.is_empty():
		return true
	var js := "(%s)(%s,%s)" % [RESCUE_IMPORT_JS, JSON.stringify(key), JSON.stringify(Marshalls.raw_to_base64(bytes))]
	if JavaScriptBridge.eval(js) == true:
		return true
	_rollback_web_rescue()
	return false


func _rollback_web_rescue() -> bool:
	if not OS.has_feature("web"):
		return true
	return JavaScriptBridge.eval(RESCUE_ROLLBACK_JS) == true


func _apply_import(bytes: PackedByteArray) -> void:
	if import_in_progress:
		return
	var scene := get_tree().current_scene
	if scene is World and (scene as World).running:
		_alert("Hãy về Prontera trước khi nhập hoặc khôi phục save.")
		return
	if not _validated_profile(bytes):
		_alert("Save không giải mã được hoặc thiếu dữ liệu của game. Save hiện tại được giữ nguyên.")
		return
	if OS.has_feature("web") and not OS.is_userfs_persistent():
		_alert("Trình duyệt chưa cho lưu bền vững. Chưa nhập save. Hãy dùng cửa sổ thường và cho phép dữ liệu trang web.")
		return
	# Preserve the old encrypted profile before any replacement.
	var old_data := _current_save_bytes()
	if Save._dirty:
		_alert("Chưa ghi được tiến trình hiện tại. Đã hủy nhập; hãy kiểm tra dung lượng lưu và thử lại.")
		return
	if old_data.size() >= 32:
		if not SVVSaveGuardian._write_atomically(_before_import_path(), old_data):
			_alert("Không tạo được bản dự phòng. Đã hủy nhập để tránh mất save.")
			return
		SVVSaveGuardian.backup_now()
	var guard_state: Dictionary = SVVSaveGuardian.capture_import_state()
	if not _begin_web_rescue_import(bytes):
		_alert("Không đọc/ghi được bản cứu hộ của trình duyệt. Chưa thay profile; hãy kiểm tra quyền lưu và dung lượng trang web.")
		return
	if not SVVSaveGuardian._write_atomically(_save_path(), bytes):
		_rollback_web_rescue()
		_alert("Không ghi được save mới. Bản cũ đã được giữ để khôi phục.")
		return
	if not SVVSaveGuardian.adopt_imported_profile(bytes):
		if old_data.size() >= 32:
			SVVSaveGuardian._write_atomically(_save_path(), old_data)
		SVVSaveGuardian.restore_import_state(guard_state)
		_rollback_web_rescue()
		_alert("Không xác nhận được bản bảo hiểm save nhập. Đã thử phục hồi save cũ.")
		return
	import_in_progress = true
	import_old_bytes = old_data
	import_guardian_state = guard_state
	import_was_paused = get_tree().paused
	get_tree().paused = true
	# Prevent autosave/close handlers from flushing the old in-memory profile
	# over the imported bytes while the browser commits IndexedDB.
	Save._dirty = false
	Save.set_process(false)
	SVVSaveGuardian.set_process(false)
	if OS.has_feature("web"):
		if not _stage_import_run():
			_import_synced(["RUN_CLEAR_ERROR"])
			return
		if callback_sync == null:
			callback_sync = JavaScriptBridge.create_callback(_import_synced)
		var browser: JavaScriptObject = JavaScriptBridge.get_interface("window")
		browser._svvSaveSynced = callback_sync
		if JavaScriptBridge.eval(IMPORT_SYNC_JS) != true:
			_import_synced(["UNAVAILABLE"])
	else:
		_finish_native_import()


func _stage_import_run() -> bool:
	# Profile replacement and removal of the previous character's run must
	# reach IndexedDB in the SAME sync. Keep its exact bytes for rollback.
	import_run_captured = false
	import_run_path = RunSave.path()
	import_run_existed = FileAccess.file_exists(import_run_path)
	import_run_bytes = PackedByteArray()
	if import_run_existed:
		var reader := FileAccess.open(import_run_path, FileAccess.READ)
		if reader == null:
			return false
		var expected_size := reader.get_length()
		import_run_bytes = reader.get_buffer(expected_size)
		reader.close()
		if import_run_bytes.size() != expected_size:
			return false
	import_run_captured = true
	RunSave.clear()
	return not FileAccess.file_exists(import_run_path)


func _rollback_import_run() -> bool:
	if not import_run_captured:
		return true
	if import_run_existed:
		if FileAccess.file_exists(import_run_path) and FileAccess.get_file_as_bytes(import_run_path) == import_run_bytes:
			return true
		return SVVSaveGuardian._write_atomically(import_run_path, import_run_bytes)
	if FileAccess.file_exists(import_run_path):
		return DirAccess.remove_absolute(ProjectSettings.globalize_path(import_run_path)) == OK
	return true


func _import_synced(arguments: Array) -> void:
	if not import_in_progress:
		return
	if arguments.is_empty() or str(arguments[0]) != "OK":
		if import_old_bytes.size() >= 32:
			SVVSaveGuardian._write_atomically(_save_path(), import_old_bytes)
		else:
			DirAccess.remove_absolute(ProjectSettings.globalize_path(_save_path()))
		SVVSaveGuardian.restore_import_state(import_guardian_state)
		var rescue_restored := _rollback_web_rescue()
		var run_restored := _rollback_import_run()
		if OS.has_feature("web"):
			JavaScriptBridge.force_fs_sync()
		import_in_progress = false
		Save.set_process(true)
		SVVSaveGuardian.set_process(true)
		get_tree().paused = import_was_paused
		if not run_restored:
			_alert("Lỗi ghi trình duyệt; profile cũ đã được giữ nhưng chưa phục hồi được snapshot lượt chơi. Hãy giữ game mở và sao lưu trước khi thử lại.")
		elif rescue_restored:
			_alert("Không lưu được save nhập vào trình duyệt. Đã giữ save cũ; hãy kiểm tra dung lượng và quyền lưu của trang.")
		else:
			_alert("Lỗi ghi trình duyệt; không phục hồi được bản cứu hộ localStorage. Bản profile cũ vẫn ở tệp trước-lần-nhập. Hãy xuất một bản sao trước khi đóng game.")
		return
	# Profile, Guardian files and stale-run removal are already durable in a
	# single completed sync. Never start a second transaction before reload.
	if JavaScriptBridge.eval("window.location.reload(); true") != true:
		_alert("Save đã nhập. Hãy đóng rồi mở lại game.")


func _finish_native_import() -> void:
	RunSave.clear()
	if confirm_import != null:
		confirm_import.hide()
	if dialog != null:
		dialog.hide()
	var done := AcceptDialog.new()
	done.title = "Đã nhập save"
	done.dialog_text = "Save đã nhập và có bản dự phòng. Nhấn Đóng game rồi mở lại để chơi save vừa nhập."
	done.ok_button_text = "Đóng game"
	done.process_mode = Node.PROCESS_MODE_ALWAYS
	done.confirmed.connect(func(): get_tree().quit())
	done.close_requested.connect(func(): get_tree().quit())
	get_tree().root.add_child(done)
	done.popup_centered(_popup_size(540, 220))


func _open_native_picker(exporting: bool, filename: String = "") -> void:
	if native_file_dialog != null:
		native_file_dialog.queue_free()
	native_file_dialog = FileDialog.new()
	native_file_dialog.access = FileDialog.ACCESS_FILESYSTEM
	native_file_dialog.use_native_dialog = true
	native_file_dialog.file_mode = FileDialog.FILE_MODE_SAVE_FILE if exporting else FileDialog.FILE_MODE_OPEN_FILE
	native_file_dialog.filters = PackedStringArray(["*.json ; Save JSON", "*.svvsave ; Save cũ"])
	native_file_dialog.title = "Lưu bản sao save ngoài game" if exporting else "Chọn file save để nhập"
	native_file_dialog.current_file = filename
	native_file_dialog.file_selected.connect(_native_export_selected if exporting else _native_import_selected)
	if dialog != null and dialog.visible:
		dialog.add_child(native_file_dialog)
	else:
		get_tree().root.add_child(native_file_dialog)
	native_file_dialog.popup_centered(_popup_size(800, 560))


func _native_export_selected(path: String) -> void:
	# A native document picker may return an Android content:// URI. It cannot
	# be renamed to a sibling temporary file; this is an external backup only.
	var writer := FileAccess.open(path, FileAccess.WRITE)
	var succeeded := false
	if writer != null:
		writer.store_buffer(pending_export)
		writer.flush()
		succeeded = writer.get_error() == OK
		writer.close()
	if not succeeded:
		_alert("Không ghi được file sao lưu. Hãy chọn một thư mục cho phép lưu.")
	else:
		_alert("Đã lưu bản sao JSON. Bạn có thể chuyển file này sang máy khác.")
	pending_export = PackedByteArray()


func _native_import_selected(path: String) -> void:
	var reader := FileAccess.open(path, FileAccess.READ)
	if reader == null or reader.get_length() > MAX_JSON_BYTES:
		_alert("Không đọc được file save hoặc file vượt 12 MB.")
		return
	var bytes := reader.get_buffer(reader.get_length())
	reader.close()
	if path.to_lower().ends_with(".json") or bytes.get_string_from_utf8().strip_edges().begins_with("{"):
		_receive_import_file([bytes.get_string_from_utf8(), "native-import.json"])
	else:
		_receive_import_file([Marshalls.raw_to_base64(bytes), "native-import.svvsave"])


func _restore_previous() -> void:
	var backup_path := _before_import_path()
	# Existing web builds used a shared legacy path. Offer it only to the
	# normal offline profile, never to an isolated QA profile.
	if not FileAccess.file_exists(backup_path) and str(Save._name) == "profile_offline":
		backup_path = BEFORE_IMPORT
	if not FileAccess.file_exists(backup_path):
		_alert("Chưa có bản dự phòng từ lần nhập save trước.")
		return
	var bytes := FileAccess.get_file_as_bytes(backup_path)
	if bytes.size() < 32 or bytes.size() > MAX_SAVE_BYTES:
		_alert("Bản dự phòng không hợp lệ, chưa khôi phục.")
		return
	_apply_import(bytes)
