extends Node
## Isolated menu-to-native-combat regression. Never loaded from production UI.
var errors: Array[String] = []

func _ready() -> void:
	_run.call_deferred()

func _check(condition: bool, label: String) -> void:
	print("MVP_MENU_TEST ", "PASS " if condition else "FAIL ", label)
	if not condition:
		errors.append(label)

func _finish() -> void:
	print("MVP_MENU_TEST COMPLETE errors=", errors.size())
	get_tree().quit(0 if errors.is_empty() else 1)

# Exercise a genuine connected native choice button when its callable is
# explicit; otherwise use the original keyboard input path. No direct skill
# grant, no call to menus.close(), no forced unpause.
func _press_native_choice(node: Node) -> bool:
	if node is BaseButton and node.is_visible_in_tree() and not node.disabled:
		for connection in node.pressed.get_connections():
			var callback: Callable = connection.get("callable", Callable())
			if callback.is_valid() and str(callback.get_method()) in ["_pick", "_pick_start"]:
				node.pressed.emit()
				return true
	for child in node.get_children():
		if _press_native_choice(child):
			return true
	return false

func _native_choice_input() -> void:
	var press := InputEventKey.new()
	press.keycode = KEY_1
	press.physical_keycode = KEY_1
	press.pressed = true
	Input.parse_input_event(press)
	await get_tree().process_frame
	var release := press.duplicate() as InputEventKey
	release.pressed = false
	Input.parse_input_event(release)

func _run() -> void:
	await get_tree().process_frame
	if Save._name != "profile_offline_test" or not OS.get_cmdline_user_args().has("--offline-mvp-menu-preview"):
		_check(false, "test_profile_and_opt_in")
		_finish()
		return
	Save.set_setting("onboarded", true)
	Save.set_setting("privacy_seen", true)
	Save.set_setting("svv_offline_friends", ["mage", "archer", "acolyte"])
	Save.set_setting("svv_offline_party", ["mage", "archer", "acolyte"])
	Save.flush()
	var packed: PackedScene = load("res://scenes/main.tscn")
	var world: World = packed.instantiate() as World
	get_tree().root.add_child(world)
	await get_tree().process_frame
	await get_tree().process_frame
	world.enter_town("swordsman")
	for frame in 12:
		await get_tree().process_frame
	_check(SVVCompanionTown._town() != null, "original_prontera")
	_check(SVVOfflineEvents.mvp_preview, "explicit_preview_enabled")
	if not errors.is_empty():
		_finish()
		return
	SVVOfflineEvents.open_button.pressed.emit()
	_check(SVVOfflineEvents.panel.visible, "open_real_menu")
	SVVOfflineEvents.mode_buttons["world_boss"].pressed.emit()
	_check(SVVOfflineEvents.mvp_picker.visible and SVVOfflineEvents.mvp_picker.item_count == 6, "six_mvp_choices")
	SVVOfflineEvents.mvp_picker.select(1)
	_check(SVVOfflineEvents.mvp_picker.get_item_text(1) == "Osiris", "select_nondefault_osiris")
	if not errors.is_empty():
		_finish()
		return
	SVVOfflineEvents.start_button.pressed.emit()
	var deadline: int = Time.get_ticks_msec() + 30000
	var next_choice: int = 0
	var choice_attempts: int = 0
	var observed_native_choice := false
	while SVVOfflineEvents.mvp_launching and Time.get_ticks_msec() < deadline:
		if world.menus._mode in ["level_up", "start_skill"] and SVVOfflineEvents.mvp_loading_callback_completed:
			if not observed_native_choice:
				observed_native_choice = true
				# Prove the launcher leaves the original choice visible.
				_check(SVVOfflineEvents.mvp_launching and not is_instance_valid(SVVOfflineEvents.mvp_last_spawn), "native_choice_preserved_before_spawn")
			if Time.get_ticks_msec() >= next_choice and choice_attempts < 12:
				choice_attempts += 1
				next_choice = Time.get_ticks_msec() + 700
				var clicked: bool = _press_native_choice(world.menus)
				print("MVP_MENU_TEST CHOICE attempt=", choice_attempts, " connected_button=", clicked)
				if not clicked:
					await _native_choice_input()
		await get_tree().process_frame
	_check(not observed_native_choice or world.menus._mode not in ["level_up", "start_skill"], "opening_choice_completed")
	print("MVP_MENU_TEST TRANSITION mode=", str(world.menus._mode), " paused=", get_tree().paused, " callback=", SVVOfflineEvents.mvp_loading_callback_completed)
	_check(not SVVOfflineEvents.mvp_launching, "launcher_completed_before_deadline")
	var boss: Enemy = SVVOfflineEvents.mvp_last_spawn
	_check(SVVOfflineEvents.mvp_last_id == "osiris", "requested_boss_id")
	_check(is_instance_valid(boss), "native_boss_spawned")
	_check(world.running and world.map != null and world.player != null, "native_map_and_player")
	_check(not SVVOfflineEvents.panel.visible and not get_tree().paused and world.menus._mode in ["", "closed"], "no_stuck_overlay")
	_check(world.heroes.size() == 4, "human_plus_three_party")
	for hero in world.heroes:
		if hero != world.player:
			_check(hero.input is HeroInput.BotHero, "native_bot_input")
	if is_instance_valid(boss):
		_check(world.get("enemies").has(boss) and boss.hp > 0.0, "live_boss_in_native_registry")
		_check(is_instance_valid(SVVOfflineEvents.mvp_hud) and SVVOfflineEvents.mvp_hud.visible, "native_boss_hud_visible")
		_check(SVVOfflineEvents.mvp_hud_hp.max_value >= boss.hp, "native_hp_bar_range")
		# Verify the HUD's actual behavior under a normal tree pause, then
		# restore the exact state. No forced opening-choice dismissal.
		var original_pause: bool = get_tree().paused
		get_tree().paused = true
		await get_tree().process_frame
		await get_tree().process_frame
		_check(not SVVOfflineEvents.mvp_hud.visible, "hud_hidden_during_pause")
		get_tree().paused = original_pause
		await get_tree().process_frame
		await get_tree().process_frame
		_check(SVVOfflineEvents.mvp_hud.visible, "hud_returns_after_pause")
		_check(SVVOfflineEvents.mvp_hud.mouse_filter == Control.MOUSE_FILTER_IGNORE and SVVOfflineEvents.mvp_hud_hp.mouse_filter == Control.MOUSE_FILTER_IGNORE, "hud_does_not_capture_combat_input")
		var initial_hp: float = boss.hp
		var combat_deadline: int = Time.get_ticks_msec() + 12000
		var start_time: float = world.time
		while is_instance_valid(boss) and boss.hp >= initial_hp and world.time - start_time < 10.0 and Time.get_ticks_msec() < combat_deadline:
			await get_tree().process_frame
		_check(is_instance_valid(boss) and boss.hp < initial_hp, "native_combat_damage")
		await get_tree().process_frame
		if is_instance_valid(boss):
			_check(absf(SVVOfflineEvents.mvp_hud_hp.value - maxf(0.0, boss.hp)) < 0.1, "hud_reads_native_boss_hp")
	_finish()
