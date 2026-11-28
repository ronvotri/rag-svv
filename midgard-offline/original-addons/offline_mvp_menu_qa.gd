extends Node
const MVPCredit = preload("res://addons/svv_offline/offline_mvp_credit_qa.gd")
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

# Test-only: follow the game's native exit entrypoint. Never clear enemies,
# force running=false or enter town directly to manufacture a passing result.
func _press_native_end_leave(node: Node) -> bool:
	if node is BaseButton and node.is_visible_in_tree() and not node.disabled:
		for connection in node.pressed.get_connections():
			var callback: Callable = connection.get("callable", Callable())
			if callback.is_valid() and str(callback.get_method()) == "_end_leave":
				node.pressed.emit()
				return true
	for child in node.get_children():
		if _press_native_end_leave(child):
			return true
	return false


func _repeat_hunt(world: World, previous_token: String) -> void:
	if not OS.get_cmdline_user_args().has("--offline-mvp-repeat-preview"):
		return
	if Save._name != "profile_offline_test" or OS.get_environment("SVV_WORLD_BOSS_QA_SANDBOX") != "1":
		_check(false, "repeat_sandbox")
		return
	var prior: Dictionary = Save.setting("svv_offline_mvp_victories", {}).duplicate(true)
	# A boss kill can trigger a native level-up at the same moment as victory.
	# Finish any real choices via the original UI rather than forcing unpause.
	var deadline: int = Time.get_ticks_msec() + 30000
	var next_postkill_choice: int = 0
	var last_mode := ""
	while Time.get_ticks_msec() < deadline and not SVVOfflineEvents.mvp_return_button.is_visible_in_tree():
		var mode: String = str(world.menus._mode)
		if mode != last_mode:
			print("MVP_MENU_TEST RETURN_WAIT mode=", mode, " paused=", get_tree().paused, " running=", world.running)
			last_mode = mode
		if mode in ["level_up", "start_skill"] and Time.get_ticks_msec() >= next_postkill_choice:
			next_postkill_choice = Time.get_ticks_msec() + 700
			if not _press_native_choice(world.menus):
				await _native_choice_input()
		await get_tree().process_frame
	print("MVP_MENU_TEST RETURN_VISIBILITY mode=", world.menus._mode, " paused=", get_tree().paused, " running=", world.running, " town=", SVVCompanionTown._town() != null, " outcome=", SVVOfflineEvents.mvp_hud_outcome, " saved=", SVVOfflineEvents.mvp_victory_saved, " hud=", SVVOfflineEvents.mvp_hud.visible, " button=", SVVOfflineEvents.mvp_return_button.visible)
	_check(SVVOfflineEvents.mvp_return_button.is_visible_in_tree() and not SVVOfflineEvents.mvp_return_button.disabled, "repeat_return_button_visible")
	if not errors.is_empty():
		return
	SVVOfflineEvents.mvp_return_button.pressed.emit()
	deadline = Time.get_ticks_msec() + 15000
	while Time.get_ticks_msec() < deadline and SVVOfflineEvents.mvp_returning:
		await get_tree().process_frame
	_check(SVVCompanionTown._town() != null and not world.running and not SVVOfflineEvents.mvp_returning, "repeat_native_return_to_prontera")
	if not errors.is_empty():
		print("MVP_MENU_TEST REPEAT_RETURN mode=", world.menus._mode, " running=", world.running)
		return
	_check(Save.setting("svv_offline_mvp_victories", {}) == prior, "repeat_first_victory_unchanged")
	SVVOfflineEvents.open_button.pressed.emit()
	_check(SVVOfflineEvents.panel.visible, "repeat_menu_reopens")
	SVVOfflineEvents.mode_buttons["world_boss"].pressed.emit()
	SVVOfflineEvents.mvp_picker.select(1)
	SVVOfflineEvents.start_button.pressed.emit()
	deadline = Time.get_ticks_msec() + 30000
	var next_choice: int = 0
	while SVVOfflineEvents.mvp_launching and Time.get_ticks_msec() < deadline:
		if world.menus._mode in ["level_up", "start_skill"] and Time.get_ticks_msec() >= next_choice:
			next_choice = Time.get_ticks_msec() + 700
			if not _press_native_choice(world.menus):
				await _native_choice_input()
		await get_tree().process_frame
	var boss: Enemy = SVVOfflineEvents.mvp_last_spawn
	_check(not SVVOfflineEvents.mvp_launching and is_instance_valid(boss) and SVVOfflineEvents.mvp_last_id == "osiris", "repeat_second_mvp_spawn")
	_check(world.running and world.heroes.size() == 4 and SVVOfflineEvents.mvp_session_token != previous_token, "repeat_new_session_and_party")
	_check(Save.setting("svv_offline_mvp_victories", {}) == prior, "repeat_no_extra_victory_on_spawn")
	if is_instance_valid(boss):
		var hp_before: float = boss.hp
		deadline = Time.get_ticks_msec() + 12000
		while is_instance_valid(boss) and boss.hp >= hp_before and Time.get_ticks_msec() < deadline:
			await get_tree().process_frame
		_check(is_instance_valid(boss) and boss.hp < hp_before, "repeat_second_mvp_combat")


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
	var shared_hub: bool = SVVOfflineEvents.native_destination_review
	SVVOfflineEvents.open_button.pressed.emit()
	if shared_hub:
		for frame in range(30):
			await get_tree().process_frame
		_check(SVVOfflineEvents.native_destination_opened and not SVVOfflineEvents.panel.visible, "original_hub_not_simulator")
		var card: Button = SVVOfflineEvents.shared_mvp_button
		_check(is_instance_valid(card) and card.is_visible_in_tree() and not card.disabled, "native_world_boss_card_bound")
		if not errors.is_empty():
			_finish()
			return
		card.pressed.emit()
		await get_tree().process_frame
		_check(is_instance_valid(SVVOfflineEvents.shared_mvp_dialog) and SVVOfflineEvents.shared_mvp_dialog.visible, "native_card_opens_local_mvp_picker")
		_check(is_instance_valid(SVVOfflineEvents.shared_mvp_picker) and SVVOfflineEvents.shared_mvp_picker.item_count == 6, "six_mvp_choices")
	else:
		_check(SVVOfflineEvents.panel.visible, "open_real_menu")
		SVVOfflineEvents.mode_buttons["world_boss"].pressed.emit()
		_check(SVVOfflineEvents.mvp_picker.visible and SVVOfflineEvents.mvp_picker.item_count == 6, "six_mvp_choices")
	var extended: bool = OS.get_cmdline_user_args().has("--offline-mvp-menu-terminal")
	var boss_index: int = 0 if extended else 1
	var requested_id: String = "baphomet" if extended else "osiris"
	if not errors.is_empty():
		_finish()
		return
	var picker: OptionButton = SVVOfflineEvents.shared_mvp_picker if shared_hub else SVVOfflineEvents.mvp_picker
	picker.select(boss_index)
	_check(picker.get_item_text(boss_index) == ("Baphomet" if extended else "Osiris"), "select_requested_mvp")
	if not errors.is_empty():
		_finish()
		return
	if shared_hub:
		SVVOfflineEvents.shared_mvp_dialog.get_ok_button().pressed.emit()
	else:
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
	_check(SVVOfflineEvents.mvp_last_id == requested_id, "requested_boss_id")
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
	if extended and errors.is_empty():
		var terminal_deadline: int = Time.get_ticks_msec() + 240000
		var start_world: float = world.time
		var next_input: int = 0
		while SVVOfflineEvents.mvp_hud_outcome == "active" and world.time - start_world < 180.0 and Time.get_ticks_msec() < terminal_deadline:
			if world.menus._mode in ["level_up", "start_skill"] and Time.get_ticks_msec() >= next_input:
				next_input = Time.get_ticks_msec() + 700
				if not _press_native_choice(world.menus):
					await _native_choice_input()
			await get_tree().process_frame
		var outcome: String = SVVOfflineEvents.mvp_hud_outcome
		var saved: bool = SVVOfflineEvents.mvp_victory_saved
		var token: String = SVVOfflineEvents.mvp_session_token
		var replay_blocked := true
		if outcome == "victory":
			replay_blocked = not SVVOfflineEvents._settle_mvp_victory(outcome)
		var wallet_preview: bool = OS.get_cmdline_user_args().has("--offline-mvp-wallet-preview")
		var wallet_replay_blocked := true
		var wallet_before_reload: int = Save.zeny()
		if outcome == "victory" and wallet_preview:
			wallet_replay_blocked = not MVPCredit.redeem_menu(requested_id, token)
		Save.flush()
		Save.load_profile()
		var ledger: Dictionary = Save.setting("svv_offline_mvp_victories", {})
		var row: Dictionary = ledger.get(requested_id, {})
		var persisted: bool = int(row.get("wins", 0)) == 1 and str(row.get("last_token", "")) == token
		var receipts: Dictionary = row.get("reward_receipts", {})
		var receipt: Dictionary = receipts.get(token, {})
		print("MVP_MENU_TEST TERMINAL outcome=", outcome, " saved=", saved, " replay_blocked=", replay_blocked, " persisted=", persisted)
		if outcome == "victory":
			_check(saved and replay_blocked and persisted, "menu_victory_persisted_once")
			var expected_status: String = "qa_credited" if wallet_preview else "qa_pending"
			_check(receipts.size() == 1 and int(receipt.get("zeny_quote", 0)) == 100 and int(receipt.get("mvp_marks", 0)) == 1 and receipt.get("status", "") == expected_status, "single_reward_receipt_persisted")
			if wallet_preview:
				_check(SVVOfflineEvents.mvp_reward_credited and SVVOfflineEvents.mvp_reward_balance_after - SVVOfflineEvents.mvp_reward_balance_before == 100, "menu_wallet_exact_credit")
				_check(wallet_replay_blocked and Save.zeny() == wallet_before_reload, "menu_wallet_replay_blocked_and_persisted")
				_check(not MVPCredit.redeem_menu(requested_id, token) and Save.zeny() == wallet_before_reload, "menu_wallet_reload_replay_blocked")
				SVVOfflineEvents._refresh_mvp_summary(boss_index)
				_check(SVVOfflineEvents.result.text.contains("1 huy hiệu MVP") and SVVOfflineEvents.result.text.contains("1 lần hạ"), "menu_achievement_summary_after_reload")
				if errors.is_empty():
					await _repeat_hunt(world, token)
		else:
			_check(not saved and not persisted and int(row.get("wins", 0)) == 0, "no_unverified_victory_saved")
			_check(receipts.is_empty() and not SVVOfflineEvents.mvp_reward_credited, "no_reward_receipt_without_victory")
	_finish()
