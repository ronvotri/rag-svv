extends Node
## Mobile Web-only adaptive raster quality. The original gameplay, map,
## collisions, AI, saves, and native builds remain untouched.
## Larger mobile UI via a smaller virtual canvas (~33% vs. 800x450) with
## adaptive raster detail. Strong phones can run up to 60 FPS. Never scale
## native builds or alter gameplay coordinates/collisions.

const HIGH_LANDSCAPE := Vector2i(600, 338)
const MEDIUM_LANDSCAPE := Vector2i(560, 315)
const LOW_LANDSCAPE := Vector2i(520, 293)
const FPS_TARGET := 60
const SAMPLE_SECONDS := 5.0
# Text-only readability target. Gameplay coordinates and PC visuals stay intact.
const TEXT_SCALE := 1.5
const TEXT_MIN_SIZE := 15
const TEXT_MAX_SIZE := 32

var _mobile_web: bool = false
var _quality: int = 2
var _timer: float = -8.0 # Skip shader/scene startup spikes.
var _slow_samples: int = 0
var _fast_samples: int = 0


func _ready() -> void:
	if not OS.has_feature("web"):
		return
	# User agent decides display quality only: no network, account changes,
	# cookies, or player-save writes. Touch tablets also qualify.
	var detected: Variant = JavaScriptBridge.eval(
		"Boolean((navigator.userAgentData && navigator.userAgentData.mobile) || " +
		"/Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent) || " +
		"(navigator.maxTouchPoints > 1 && Math.min(screen.width, screen.height) <= 1024))"
	)
	if detected != true:
		return
	_mobile_web = true
	Engine.max_fps = FPS_TARGET
	# Listen for new HUD, party and popup controls after scenes load.
	get_tree().node_added.connect(_on_ui_node_added)
	call_deferred("_refresh_ui_text")
	get_window().size_changed.connect(_apply_mobile_scale)
	_apply_mobile_scale()
	set_process(true)


func _process(delta: float) -> void:
	if not _mobile_web or get_tree().paused:
		return
	_timer += delta
	if _timer < SAMPLE_SECONDS:
		return
	_timer = 0.0
	var fps: int = Engine.get_frames_per_second()
	if fps <= 0:
		return
	if fps < 28:
		_slow_samples += 1
		_fast_samples = 0
		if _slow_samples >= 2 and _quality > 0:
			_quality -= 1
			_slow_samples = 0
			_apply_mobile_scale()
	elif fps >= 52:
		_fast_samples += 1
		_slow_samples = 0
		if _fast_samples >= 3 and _quality < 2:
			_quality += 1
			_fast_samples = 0
			_apply_mobile_scale()
	else:
		# Hysteresis: transient level-up/map effects never trigger oscillation.
		_slow_samples = 0
		_fast_samples = 0


func _apply_mobile_scale() -> void:
	if not _mobile_web:
		return
	var window: Window = get_window()
	var landscape: Vector2i = HIGH_LANDSCAPE
	if _quality == 1:
		landscape = MEDIUM_LANDSCAPE
	elif _quality == 0:
		landscape = LOW_LANDSCAPE
	var target: Vector2i = Vector2i(landscape.y, landscape.x) if window.size.y > window.size.x else landscape
	if window.content_scale_mode == Window.CONTENT_SCALE_MODE_VIEWPORT and window.content_scale_size == target:
		return
	window.content_scale_aspect = Window.CONTENT_SCALE_ASPECT_EXPAND
	window.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	window.content_scale_size = target
	print("SVV mobile Web target: ", target, " at up to ", FPS_TARGET, " FPS")

# Grow text instead of zooming the entire scene/joysticks. UI-only, mobile
# Web-only; run on newly opened menus and HUD panels as well as the first scene.
var _ui_refresh_queued: bool = false


func _on_ui_node_added(node: Node) -> void:
	if not _mobile_web or not (node is Control):
		return
	if not _ui_refresh_queued:
		_ui_refresh_queued = true
		call_deferred("_refresh_ui_text")


func _refresh_ui_text() -> void:
	_ui_refresh_queued = false
	if not _mobile_web or not is_inside_tree():
		return
	for node in get_tree().root.find_children("*", "Control", true, false):
		var control: Control = node as Control
		if _is_world_space_control(control):
			continue
		_apply_readable_font(control)


func _is_world_space_control(control: Control) -> bool:
	# Floating enemy labels, damage numbers and in-world UI must not be
	# enlarged. CanvasLayer marks the explicit screen-space HUD boundary.
	var parent: Node = control.get_parent()
	while parent != null:
		if parent is CanvasLayer:
			return false
		if parent is Node2D:
			return true
		parent = parent.get_parent()
	return false


func _apply_readable_font(control: Control) -> void:
	if control.has_meta("svv_mobile_text_scaled"):
		return
	if control is Label:
		var label: Label = control as Label
		if label.label_settings != null and label.label_settings.font_size > 0:
			# LabelSettings outrank theme overrides; duplicate to avoid changing
			# shared fonts/theme resources and native platform appearance.
			var style: LabelSettings = label.label_settings.duplicate() as LabelSettings
			style.font_size = _target_text_size(style.font_size)
			label.label_settings = style
		else:
			_scale_theme_font(control, "font_size")
	elif control is RichTextLabel:
		for key in ["normal_font_size", "bold_font_size", "italics_font_size", "bold_italics_font_size", "mono_font_size"]:
			_scale_theme_font(control, key)
	elif control is Button or control is CheckBox or control is CheckButton or control is OptionButton or control is MenuButton or control is LinkButton or control is LineEdit or control is TextEdit or control is ItemList or control is Tree or control is TabBar:
		_scale_theme_font(control, "font_size")
	else:
		return
	control.set_meta("svv_mobile_text_scaled", true)


func _scale_theme_font(control: Control, theme_key: String) -> void:
	var original: int = control.get_theme_font_size(theme_key)
	if original > 0:
		control.add_theme_font_size_override(theme_key, _target_text_size(original))


func _target_text_size(original: int) -> int:
	return clampi(int(ceil(float(original) * TEXT_SCALE)), TEXT_MIN_SIZE, TEXT_MAX_SIZE)
