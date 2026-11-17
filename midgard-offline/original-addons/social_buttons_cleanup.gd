extends Node
## Prune the original publisher's social strip from the offline client.
## Keep only Discord. Do not rewrite its destination without an explicit
## verified community invite URL supplied by the game owner.
## A deferred check is cheap: it runs when UI buttons are added, not per frame.

# Set ONLY after the owner supplies their actual server invitation.
# A blank value preserves the Discord icon without inventing a destination.
const DISCORD_INVITE_URL := ""
var _pending := false
var _discord_wired := false


func _ready() -> void:
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
	var hints: String = str(button.name) + " " + str(button.tooltip_text)
	if button is Button:
		hints += " " + (button as Button).text
	return hints.to_lower()


func _find_coffee(node: Node) -> BaseButton:
	if node is BaseButton:
		var hints: String = _button_hints(node)
		if "buy me a coffee" in hints or "ko-fi" in hints:
			return node as BaseButton
	for child in node.get_children():
		var result: BaseButton = _find_coffee(child)
		if result != null:
			return result
	return null


func _cleanup() -> void:
	_pending = false
	var coffee: BaseButton = _find_coffee(get_tree().root)
	if coffee == null or not is_instance_valid(coffee):
		return
	var siblings: Array[BaseButton] = []
	for node in coffee.get_parent().get_children():
		if node is BaseButton:
			siblings.append(node as BaseButton)
	# Only touch the compact original publisher/social strip. Never prune
	# unrelated menus or the independent full-screen control on the web page.
	if siblings.size() < 3 or siblings.size() > 6:
		return
	var keep: BaseButton = null
	for button in siblings:
		if "discord" in _button_hints(button):
			keep = button
			break
	if keep == null:
		var coffee_index: int = siblings.find(coffee)
		if coffee_index >= 0 and coffee_index + 1 < siblings.size():
			keep = siblings[coffee_index + 1] # screenshot: coffee, Discord, YouTube, X
	if keep == null:
		return
	for button in siblings:
		if button != keep:
			button.hide()
	# Once a verified invite is configured, point Discord to that community.
	if not DISCORD_INVITE_URL.is_empty() and not _discord_wired:
		for connection in keep.pressed.get_connections():
			var callback: Callable = connection.get("callable", Callable())
			if callback.is_valid():
				keep.pressed.disconnect(callback)
		keep.pressed.connect(_open_discord)
		_discord_wired = true


func _open_discord() -> void:
	if not DISCORD_INVITE_URL.begins_with("https://discord.gg/") and not DISCORD_INVITE_URL.begins_with("https://discord.com/invite/"):
		push_warning("Discord invite not configured: refusing unverified URL")
		return
	if OS.has_feature("web"):
		var browser: JavaScriptObject = JavaScriptBridge.get_interface("window")
		if browser != null:
			browser.open(DISCORD_INVITE_URL, "_blank", "noopener,noreferrer")
	else:
		OS.shell_open(DISCORD_INVITE_URL)
