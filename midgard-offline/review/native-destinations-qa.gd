extends Node
## Native destination panel probe. No activity button is pressed or rewarded.
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
	print("NATIVE_DESTINATION_QA COMPLETE errors=", errors.size())
	get_tree().quit(0 if errors.is_empty() else 1)
