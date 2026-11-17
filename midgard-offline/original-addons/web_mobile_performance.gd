extends Node
## Mobile Web-only adaptive raster quality. The original gameplay, map,
## collisions, AI, saves, and native builds remain untouched.
## Larger mobile UI via a smaller virtual canvas (~18% vs. 800x450) with
## adaptive raster detail. Strong phones can run up to 60 FPS. Never scale
## native builds or alter gameplay coordinates/collisions.

const HIGH_LANDSCAPE := Vector2i(680, 382)
const MEDIUM_LANDSCAPE := Vector2i(640, 360)
const LOW_LANDSCAPE := Vector2i(600, 338)
const FPS_TARGET := 60
const SAMPLE_SECONDS := 5.0

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
