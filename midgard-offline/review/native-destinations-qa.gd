extends Node
## Isolated native destination and card-navigation probe. No fake build or direct damage.
var errors: Array[String] = []

func _ready() -> void:
	_run.call_deferred()


func _check(condition: bool, label: String) -> void:
	print("NATIVE_DESTINATION_QA ", "PASS " if condition else "FAIL ", label)
	if not condition:
		errors.append(label)


func _collect_visible(node: Node, texts: Array[String]) -> void:
	if node is Label or node is Button or node is RichTextLabel:
		if node.is_visible_in_tree():
			texts.append(str(node.text).to_lower())
	for child in node.get_children():
		_collect_visible(child, texts)


func _visible_buttons(node: Node, buttons: Array[Button]) -> void:
	if node is Button and node.is_visible_in_tree() and not node.disabled:
		buttons.append(node)
	for child in node.get_children():
		_visible_buttons(child, buttons)


func _card_category(text: String) -> String:
	var found: Array[String] = []
	if text.contains("world boss") or text.contains("boss thế giới"):
		found.append("world_boss")
	if text.contains("emperium"):
		found.append("festival")
	if text.contains("training") or text.contains("practice") or text.contains("bài tập") or text.contains("luyện tập"):
		found.append("training")
	return found[0] if found.size() == 1 else ""


# Match the Go button by its nearest unique native card container. No
# click coordinates, indexing assumptions, or pressing a disabled button.
func _card_button(world: World, activity: String) -> Button:
	var buttons: Array[Button] = []
	_visible_buttons(world.menus, buttons)
	var candidates: Array[Button] = []
	for button in buttons:
		var caption: String = button.text.strip_edges().to_lower()
		if caption not in ["go", "go!", "let's go", "let’s go", "đi thôi", "đi thôi!", "đi"]:
			continue
		var parent: Node = button.get_parent()
		for level in range(7):
			if parent == null or parent == world.menus:
				break
			var texts: Array[String] = []
			_collect_visible(parent, texts)
			if _card_category("\n".join(texts)) == activity:
				candidates.append(button)
				break
			parent = parent.get_parent()
	return candidates[0] if candidates.size() == 1 else null


func _native_training_choice(world: World) -> Button:
	var buttons: Array[Button] = []
	_visible_buttons(world.menus, buttons)
	var matches: Array[Button] = []
	for button in buttons:
		for connection in button.pressed.get_connections():
			var callback: Callable = connection.get("callable", Callable())
			if not callback.is_valid() or str(callback.get_method()) != "_start_training":
				continue
			if callback.get_bound_arguments().has("swordsman"):
				matches.append(button)
				break
	return matches[0] if matches.size() == 1 else null


func _native_training_observation(world: World) -> Dictionary:
	var flags: Dictionary = {}
	for property in world.get_property_list():
		var name: String = str(property.get("name", ""))
		if not ("training" in name.to_lower() or "dummy" in name.to_lower()):
			continue
		if int(property.get("usage", 0)) & PROPERTY_USAGE_SCRIPT_VARIABLE:
			var value: Variant = world.get(name)
			if value is bool or value is int or value is float:
				flags[name] = value
	var registry: Variant = world.get("enemies")
	return {"running": world.running, "map_ready": world.map != null,
		"hero_ready": is_instance_valid(world.player), "training_fields": flags,
		"enemies": registry.size() if registry is Array else -1}


func _probe_card(world: World, activity: String) -> void:
	var button: Button = _card_button(world, activity)
	if not is_instance_valid(button):
		print("NATIVE_DESTINATION_QA CARD_BLOCKED ", activity, " no_unique_enabled_native_button")
		return
	var before: String = str(world.menus._mode)
	button.pressed.emit()
	for frame in range(30):
		await get_tree().process_frame
	print("NATIVE_DESTINATION_QA CARD_OPENED ", activity, " before=", before, " after=", world.menus._mode, " running=", world.running)
	if activity != "training":
		# Festival opens its genuine saved-build selector. Do not fabricate a
		# saved build or submit results just to force entry.
		return
	var choice: Button = _native_training_choice(world)
	if not is_instance_valid(choice):
		print("NATIVE_DESTINATION_QA TRAINING_BLOCKED native_class_choice_not_identified")
		return
	choice.pressed.emit()
	var deadline: int = Time.get_ticks_msec() + 15000
	while Time.get_ticks_msec() < deadline:
		if world.running and world.map != null and is_instance_valid(world.player):
			break
		await get_tree().process_frame
	print("NATIVE_DESTINATION_QA TRAINING_OBSERVED ", JSON.stringify(_native_training_observation(world)))


func _run() -> void:
	await get_tree().process_frame
	_check(Save._name == "profile_offline_test" and SVVOfflineEvents.native_destination_review, "isolated_profile_and_explicit_flag")
	if not errors.is_empty():
		get_tree().quit(1)
		return
	Save.set_setting("privacy_seen", true)
	Save.set_setting("onboarded", true)
	var packed: PackedScene = load("res://scenes/main.tscn")
	var world: World = packed.instantiate() as World
	get_tree().root.add_child(world)
	await get_tree().create_timer(1.0).timeout
	world.enter_town("swordsman")
	var deadline: int = Time.get_ticks_msec() + 12000
	while Time.get_ticks_msec() < deadline and SVVCompanionTown._town() == null:
		await get_tree().process_frame
	_check(SVVCompanionTown._town() != null, "native_prontera")
	SVVOfflineEvents.open_button.pressed.emit()
	for index in range(30):
		await get_tree().process_frame
	_check(SVVOfflineEvents.native_destination_opened, "toolbar_invokes_original_dialog")
	_check(not SVVOfflineEvents.panel.visible, "no_simulation_panel")
	var texts: Array[String] = []
	_collect_visible(get_tree().root, texts)
	var all_text: String = "\n".join(texts)
	_check(all_text.contains("world boss") or all_text.contains("boss thế giới"), "native_boss_card_visible")
	_check(all_text.contains("emperium"), "native_festival_card_visible")
	_check(all_text.contains("training") or all_text.contains("practice") or all_text.contains("bài tập") or all_text.contains("luyện tập"), "native_training_card_visible")
	_check(not world.running and world.net.mode == "" and world.net.eos() == null and not world.cloud._enabled(), "no_run_or_online_session_started")
	if errors.is_empty():
		for arg in OS.get_cmdline_user_args():
			if arg == "--destination-card=training":
				await _probe_card(world, "training")
			elif arg == "--destination-card=festival":
				await _probe_card(world, "festival")
	_check(world.net.mode == "" and world.net.eos() == null and not world.cloud._enabled(), "card_probe_remains_offline")
	print("NATIVE_DESTINATION_QA COMPLETE errors=", errors.size())
	get_tree().quit(0 if errors.is_empty() else 1)
