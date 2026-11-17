extends Node
## Web-browser-only raster workload reduction. Never hide map sprites,
## change collisions or modify battle state. Native builds are unaffected.
const MOBILE_LANDSCAPE := Vector2i(960, 540)
const MOBILE_PORTRAIT := Vector2i(540, 960)

var _mobile_web: bool = false


func _ready() -> void:
	if not OS.has_feature("web"):
		return
	# User agent is used only to choose display quality. No network requests,
	# cookies or game-save changes. Tablet touch devices also qualify.
	var detected: Variant = JavaScriptBridge.eval(
		"Boolean((navigator.userAgentData && navigator.userAgentData.mobile) || " +
		"/Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent) || " +
		"(navigator.maxTouchPoints > 1 && Math.min(screen.width, screen.height) <= 1024))"
	)
	if detected != true:
		return
	_mobile_web = true
	get_window().size_changed.connect(_apply_mobile_scale)
	_apply_mobile_scale()


func _apply_mobile_scale() -> void:
	if not _mobile_web:
		return
	var window: Window = get_window()
	var target: Vector2i = MOBILE_PORTRAIT if window.size.y > window.size.x else MOBILE_LANDSCAPE
	if window.content_scale_mode == Window.CONTENT_SCALE_MODE_VIEWPORT and window.content_scale_size == target:
		return
	# Render the original scene at an inexpensive internal resolution, then
	# upscale. EXPAND respects phone aspect ratios without letterboxing.
	window.content_scale_aspect = Window.CONTENT_SCALE_ASPECT_EXPAND
	window.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	window.content_scale_size = target
	print("SVV mobile Web render target: ", target)
