extends Node
## Add a browser-fullscreen exit action inside the original Godot Options popup.
## The floating Web control is deliberately hidden once fullscreen is active.
var _check_seconds: float = 0.0
var _exit_button: Button


func _ready() -> void:
	if not OS.has_feature("web"):
		set_process(false)
		return
	process_mode = Node.PROCESS_MODE_ALWAYS


func _process(delta: float) -> void:
	_check_seconds += delta
	if _check_seconds < 0.7:
		return
	_check_seconds = 0.0
	var fullscreen: Variant = JavaScriptBridge.eval("Boolean(document.fullscreenElement)")
	if fullscreen != true:
		if is_instance_valid(_exit_button):
			_exit_button.hide()
		return
	_attach_to_open_options()


func _attach_to_open_options() -> void:
	var root: Window = get_tree().root
	# Original settings may use either a native AcceptDialog title or a
	# title Label in a custom VBoxContainer. Target the actual options window,
	# never the small "Tùy chọn" HUD button.
	for node in root.find_children("*", "AcceptDialog", true, false):
		var win: AcceptDialog = node as AcceptDialog
		if win.visible and _is_options_title(win.title):
			_ensure_button(win.get_vbox())
			return
	for node in root.find_children("*", "Label", true, false):
		var heading: Label = node as Label
		if not heading.is_visible_in_tree() or not _is_options_title(heading.text):
			continue
		var cursor: Node = heading.get_parent()
		while cursor != null and not (cursor is VBoxContainer):
			cursor = cursor.get_parent()
		if cursor is VBoxContainer:
			_ensure_button(cursor as VBoxContainer)
			return


func _is_options_title(value: String) -> bool:
	var name: String = value.strip_edges().to_lower()
	return name in ["tùy chọn", "cài đặt", "options", "settings"]


func _ensure_button(holder: VBoxContainer) -> void:
	if is_instance_valid(_exit_button) and _exit_button.get_parent() == holder:
		_exit_button.show()
		return
	if is_instance_valid(_exit_button):
		_exit_button.queue_free()
	_exit_button = Button.new()
	_exit_button.name = "SVVExitFullscreenInOptions"
	_exit_button.text = "Thoát toàn màn hình"
	_exit_button.tooltip_text = "Trở về chế độ cửa sổ, không thoát game"
	_exit_button.process_mode = Node.PROCESS_MODE_ALWAYS
	_exit_button.custom_minimum_size = Vector2(178, 38)
	_exit_button.pressed.connect(_exit_fullscreen)
	holder.add_child(_exit_button)


func _exit_fullscreen() -> void:
	if not OS.has_feature("web"):
		return
	JavaScriptBridge.eval("(function(){if(!document.fullscreenElement)return false;try{if(screen.orientation&&screen.orientation.unlock)screen.orientation.unlock()}catch(e){}document.exitFullscreen();return true;})()")
	if is_instance_valid(_exit_button):
		_exit_button.hide()
