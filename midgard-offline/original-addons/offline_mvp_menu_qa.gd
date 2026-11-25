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
	var deadline: int = Time.get_ticks_msec() + 15000
	while SVVOfflineEvents.mvp_launching and Time.get_ticks_msec() < deadline:
		await get_tree().process_frame
	print("MVP_MENU_TEST TRANSITION mode=", str(world.menus._mode), " paused=", get_tree().paused, " callback=", SVVOfflineEvents.mvp_loading_callback_completed)
	var boss: Enemy = SVVOfflineEvents.mvp_last_spawn
	_check(SVVOfflineEvents.mvp_last_id == "osiris", "requested_boss_id")
	_check(is_instance_valid(boss), "native_boss_spawned")
	_check(world.running and world.map != null and world.player != null, "native_map_and_player")
	_check(not SVVOfflineEvents.panel.visible and not get_tree().paused and world.menus._mode == "", "no_stuck_overlay")
	_check(world.heroes.size() == 4, "human_plus_three_party")
	for hero in world.heroes:
		if hero != world.player:
			_check(hero.input is HeroInput.BotHero, "native_bot_input")
	if is_instance_valid(boss):
		_check(world.get("enemies").has(boss) and boss.hp > 0.0, "live_boss_in_native_registry")
		var initial_hp: float = boss.hp
		var combat_deadline: int = Time.get_ticks_msec() + 12000
		var start_time: float = world.time
		while is_instance_valid(boss) and boss.hp >= initial_hp and world.time - start_time < 10.0 and Time.get_ticks_msec() < combat_deadline:
			await get_tree().process_frame
		_check(is_instance_valid(boss) and boss.hp < initial_hp, "native_combat_damage")
	_finish()
