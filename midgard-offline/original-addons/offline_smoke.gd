extends Node
## Authored integration checks for a locally supplied, recovered original project.
## Run with --offline-test; never mutate the normal player profile.

var failures: Array[String] = []

func _ready() -> void:
	_run.call_deferred()

func check(condition: bool, label: String) -> void:
	if condition:
		print("OFFLINE_QA PASS ", label)
	else:
		failures.append(label)
		push_error("OFFLINE_QA FAIL " + label)

func _run() -> void:
	await get_tree().process_frame
	check(Save._name == "profile_offline_test", "isolated QA profile")
	check(RunSave.path().contains("profile_offline_test"), "QA run snapshot isolated from player")
	check(get_tree().root.get_node_or_null("SVVAssistant") != null, "authored party and NPC assistant loaded")
	check(SVVAssistant.open_button.text == "Bạn bè", "Friends List replaces standalone party selector")
	check(get_tree().root.get_node_or_null("SVVMiraTown") != null, "Mira town encounter addon autoloaded")
	check(SVVMiraTown.npc_button.text == "✚ Mira · Acolyte", "Mira has a town interaction fallback")
	check(RoAssets.has_sprite("acolyte_f"), "original Acolyte female sprite is present")
	check(get_tree().root.get_node_or_null("SVVCompanionTown") != null, "Alden/Eira town encounters autoloaded")
	# Front-end icon rendering is part of recovered Godot runtime, not only
	# static screenshot tests. All three offline destinations need real icons.
	check(get_tree().root.get_node_or_null("SVVOfflineEvents") != null, "local event UI autoloaded")
	for mode in ["training", "festival", "world_boss"]:
		var option: Button = SVVOfflineEvents.mode_buttons.get(mode)
		check(option != null and option.icon != null,
			"offline mode " + mode + " has a rendered icon")
	check(SVVOfflineEvents.mvp_picker.item_count == 6, "native MVP preview picker contains six bosses")
	check(not SVVOfflineEvents.mvp_preview and not SVVOfflineEvents.mvp_picker.visible,
		"native MVP preview stays hidden without explicit test flag")
	# Pure result rules, independent of combat fixtures; never grant loot.
	var rules: Script = load("res://addons/svv_offline/offline_mvp_result.gd")
	check(rules != null, "offline MVP outcome rules load")
	if rules != null:
		check(rules.classify(0.0, 100.0, true, true, false) == "victory", "MVP confirmed death wins")
		check(rules.classify(0.0, 100.0, false, true, false) == "unverified", "zero boss HP alone cannot win")
		check(rules.classify(100.0, 0.0, false, true, false) == "defeat", "player death loses")
		check(rules.classify(0.0, 0.0, true, true, false) == "draw", "simultaneous death never wins")
		check(rules.classify(null, 100.0, true, true, false) == "unverified", "missing boss never wins")
		check(rules.classify(0.0, 100.0, true, true, true) == "cancelled", "cancelled encounter never wins")
		check(rules.classify(100.0, 100.0, false, false, false) == "unverified", "stopped world never wins")
		var token_a: String = "a".repeat(32)
		var token_b: String = "b".repeat(32)
		var first: Dictionary = rules.next_victory_ledger({}, "baphomet", token_a, "victory")
		var second: Dictionary = rules.next_victory_ledger(first, "baphomet", token_b, "victory")
		check(int(second.get("baphomet", {}).get("wins", 0)) == 2, "two distinct MVP wins")
		check(rules.next_victory_ledger(second, "baphomet", token_a, "victory").is_empty(), "old encounter replay blocked")
		check(rules.next_victory_ledger(second, "osiris", token_a, "victory").is_empty(), "cross MVP replay blocked")
		check(rules.next_victory_ledger(second, "osiris", "c".repeat(32), "defeat").is_empty(), "no victory count on defeat")
		check(int(first.get("baphomet", {}).get("wins", 0)) == 1, "result ledger copy leaves original unchanged")
	# Five stable Prontera character looks must not reuse the same hair.
	var seen_looks: Dictionary = {}
	for job in SVVCompanionTown.JOBS:
		var style: Dictionary = SVVCompanionTown.NPC_LOOK.get(job, {})
		var signature := str(style.get("hair", -1)) + ":" + str(style.get("hair_color", -1))
		check(not seen_looks.has(signature), "unique town hair " + job)
		seen_looks[signature] = true

	for job in ["swordsman", "mage", "archer", "thief", "merchant", "novice"]:
		var original_id: String = SVVCompanionTown._first_original_sprite(job)
		if job == "novice":
			# Missing basic Novice is an honest pending-art state, not a build failure.
			# Super Novice is not interchangeable with the requested job.
			check(not original_id.begins_with("super_novice"), "Nao never uses Super Novice substitute")
			print("OFFLINE_QA NAO_VISUAL basic Novice ", "available=" if not original_id.is_empty() else "missing=", original_id)
		else:
			check(not original_id.is_empty(), "original " + job + " job sprite available for companion NPC")

	# Exercise the same RoVisual constructor used for town Mira, with a
	# temporary tree. No custom artwork, live network or normal save involved.
	var preview_anchor := Node3D.new()
	var preview_root := Node3D.new()
	get_tree().root.add_child(preview_root)
	preview_root.add_child(preview_anchor)
	preview_anchor.global_position = Vector3(2.0, 0.0, 2.0)
	var preview: RoVisual = SVVMiraTown._create_world_sprite(preview_root, preview_anchor)
	check(preview != null and is_instance_valid(preview), "original Acolyte sprite renders as RoVisual")
	if preview != null:
		check(preview.name == "MiraAcolyteNPC", "Mira sprite has stable NPC scene identity")
	# Audit wave-two originals off-map; no extra NPCs in Prontera yet.
	for job in ["archer", "thief", "merchant", "novice"]:
		var candidate_id: String = SVVCompanionTown._first_original_sprite(job)
		print("OFFLINE_QA WAVE2_SPRITE ", job, "=", candidate_id)
		if candidate_id.is_empty():
			continue
		var source_sprite = RoAssets.sprite([candidate_id])
		check(source_sprite != null, job + " recovered sprite data loads")
		if source_sprite != null:
			var preview_job := RoVisual.new()
			preview_root.add_child(preview_job)
			preview_job.setup(source_sprite, Color(0.8, 0.8, 0.9), 40)
			check(preview_job.sprite is Sprite3D and preview_job.sprite.texture != null,
				job + " original Ragnarok sprite renders for later town placement")
	# Probe rare-class IDs and ORIGINAL sprites without spawning or recruiting
	# any of the four unapproved NPCs. Machine-readable JSON is report-only.
	var rare_audit_script: Script = load("res://addons/svv_offline/qa/rare_job_asset_audit.gd")
	check(rare_audit_script != null, "rare NPC sprite audit helper loaded")
	if rare_audit_script != null:
		var rare_audit = rare_audit_script.new()
		var rare_report: Dictionary = rare_audit.run(preview_root)
		check(rare_report.get("all_jobs_approved", true) == false,
			"rare jobs remain locked pending sprite identity and town visual QA")
		check(rare_report.get("jobs", {}).size() == 4, "all four rare NPC jobs audited")
	preview_root.queue_free()

	check(SVVAssistant._unlocked_friends().is_empty(), "fresh QA profile starts with no recruited friends")
	check(SVVAssistant._party_members().is_empty(), "no unbefriended NPC can enter party")
	if Save._name != "profile_offline_test":
		get_tree().quit(2)
		return
	check(GameData.CLASSES.size() == 11, "11 original base classes")
	# Content evolves upstream. Verify a conservative baseline instead of
	# rejecting a legitimate release whenever it adds maps, equipment or pets.
	# The official 0.2.0 notes announce three additional playable maps.
	var stage_ids: Array[String] = []
	for stage_entry in GameData.STAGES:
		if stage_entry is Dictionary:
			stage_ids.append(str(stage_entry.get("id", stage_entry.get("key", stage_entry.get("name", "")))))
		else:
			stage_ids.append(str(stage_entry))
	print("OFFLINE_QA ORIGINAL_STAGE_IDS ", stage_ids)
	print("OFFLINE_QA ORIGINAL_COUNTS stages=", GameData.STAGES.size(),
		" skills=", GameData.SKILLS.size(),
		" cards=", GameData.CARDS.size(),
		" items=", GameData.ITEMS.size(),
		" pets=", GameData.PETS.size())
	check(GameData.STAGES.size() >= 23, "0.2.0 stage catalog includes three new maps")
	check(GameData.SKILLS.size() >= 349, "original skill catalog not truncated")
	check(GameData.CARDS.size() >= 163, "original card catalog not truncated")
	check(GameData.ITEMS.size() >= 209, "original item catalog not truncated")
	check(GameData.PETS.size() >= 46, "original pet catalog not truncated")
	check(not Updater._enabled(), "updater disabled")
	check(not Leaderboard.enabled(), "external leaderboard disabled")
	check(not ClassDB.class_exists("EOSGMultiplayerPeer"), "native EOS dependency removed")
	Save.set_setting("onboarded", true)
	Save.set_setting("privacy_seen", true)
	Save.set_setting("offline_qa_marker", "persistent")
	var before_gold: int = Save.zeny()
	Save.add_zeny(17)
	Save.flush()
	Save.data.zeny = 0
	Save.load_profile()
	check(Save.zeny() == before_gold + 17, "encrypted profile gold survives reload")
	check(Save.setting("offline_qa_marker", "") == "persistent", "profile settings survive reload")
	check(SVVSaveGuardian.backup_now(), "Save Guardian creates verified offline backup")
	check(FileAccess.file_exists(SVVSaveGuardian.latest_path()), "Save Guardian latest snapshot exists")
	var expected_party: Array[String] = ["mage", "archer", "acolyte"]
	# Test a completed starter quest on the isolated QA profile only.
	Save.set_setting("svv_friend_quests", {"acolyte": {
		"kills_at_start": int(Save.stat("kills")) - 8,
		"runs_at_start": int(Save.stat("runs")) - 1,
	}})
	SVVAssistant._select_friend("acolyte")
	SVVAssistant._friend_action_pressed()
	check(SVVAssistant._unlocked_friends().has("acolyte"), "Acolyte Mira is recruited after her quest")
	SVVMiraTown._show_dialog()
	check(SVVMiraTown.dialog.visible, "Mira dialogue opens")
	check(SVVMiraTown.action.text == "Mời Mira vào party", "recruited Mira can be invited from town")
	SVVMiraTown._close_dialog()
	check(not SVVMiraTown.dialog.visible, "Mira dialogue closes cleanly")

	# Both new quests must unlock through the same Friends List state machine.
	for job in ["swordsman", "mage"]:
		SVVAssistant._select_friend(job)
		SVVAssistant._friend_action_pressed()
		check(bool(SVVAssistant._quest_progress(job)["started"]), job + " quest starts after Mira")
		var companion_profile: Dictionary = SVVAssistant._friend_profile(job)
		var scripted_progress: Dictionary = SVVAssistant._friend_quests()
		scripted_progress[job] = {
			"kills_at_start": int(Save.stat("kills")) - int(companion_profile["kills"]),
			"runs_at_start": int(Save.stat("runs")) - int(companion_profile["runs"]),
		}
		Save.set_setting("svv_friend_quests", scripted_progress)
		SVVAssistant._friend_action_pressed()
		check(SVVAssistant._unlocked_friends().has(job), job + " is recruitable after quest")
	# Remaining companions are fixture recruits for legacy 3-ally run-save QA.

	Save.set_setting("svv_offline_friends", ["acolyte", "mage", "archer"])
	Save.set_setting("svv_offline_party", expected_party)
	Save.flush()
	Save.load_profile()
	check(Save.setting("svv_offline_party", []) == expected_party, "Friends List party survives profile reload")
	check(Save.setting("svv_offline_friends", []) == ["acolyte", "mage", "archer"], "recruited friends survive profile reload")
	var packed: PackedScene = load("res://scenes/main.tscn")
	check(packed != null, "main scene resource loaded")
	if packed == null:
		get_tree().quit(1)
		return
	var world: World = packed.instantiate()
	get_tree().root.add_child(world)
	await get_tree().process_frame
	await get_tree().process_frame
	check(world.menus != null, "original menu constructed")
	# Enter the real Prontera town flow, not just a fake RoVisual preview.
	world.enter_town("swordsman")
	for frame in 6:
		await get_tree().process_frame
	var actual_town = world.get("town")
	check(actual_town is Town and is_instance_valid(actual_town), "original Prontera Town instantiated")
	check(str(world.get_meta("svv_offline_town_place", "")) == "prontera",
		"original town entry records the requested city")
	world.set_meta("svv_offline_town_place", "payon")
	check(SVVCompanionTown._town() == null, "Alden/Eira are not assigned to an unverified Payon town")
	check(not SVVMiraTown._town_active(), "Mira is not assigned to an unverified Payon town")
	world.set_meta("svv_offline_town_place", "prontera")
	check(SVVCompanionTown._town() == actual_town, "Prontera restores valid companion town context")
	SVVMiraTown._sync_world_sprite()
	var kafra: Node3D = actual_town.npc_node("kafra") if actual_town != null else null
	check(kafra != null and is_instance_valid(kafra), "native Kafra NPC available as Mira anchor")
	check(SVVMiraTown._town_active(), "Mira visible only in actual town")
	check(SVVMiraTown.mira_visual != null and is_instance_valid(SVVMiraTown.mira_visual), "Mira spawned inside actual Prontera Town")
	if SVVMiraTown.mira_visual != null and is_instance_valid(SVVMiraTown.mira_visual) and kafra != null:
		var mira: RoVisual = SVVMiraTown.mira_visual
		check(mira.get_parent() == actual_town, "Mira sprite belongs to actual Town scene")
		check(mira.sprite is Sprite3D and mira.sprite.texture != null, "Mira has rendered original sprite texture")
		var old_pos: Vector3 = mira.global_position
		SVVMiraTown._tick_patrol(1.0)
		check(mira.global_position.distance_to(old_pos) <= 0.7, "Mira patrol stays safely near Kafra")
		check(mira.global_position.distance_to(kafra.global_position) > 1.0, "Mira does not overlap Kafra")
		var cam: Camera3D = get_viewport().get_camera_3d()
		if cam != null:
			var hit: Vector2 = SVVMiraTown._mira_screen_point()
			if hit.is_finite():
				var tap := InputEventMouseButton.new()
				tap.pressed = true
				tap.button_index = MOUSE_BUTTON_LEFT
				tap.position = hit
				SVVMiraTown._unhandled_input(tap)
				check(SVVMiraTown.dialog.visible, "click on Mira world sprite opens NPC dialogue")
				SVVMiraTown._close_dialog()

	# In-world encounters must use genuine rendered Ragnarok job sprites.
	SVVCompanionTown._clear_world()
	SVVCompanionTown._spawn_in_town(actual_town)
	# Wave 6: objective placement guard rails before any human visual signoff.
	# Spacing between sprites is verifiable; collision with original town props
	# and walkable lanes still needs real desktop/mobile screenshot review.
	var staged_jobs: Array[String] = ["swordsman", "mage", "archer", "thief", "merchant"]
	var frame_rect := Rect2(Vector2.ZERO, get_viewport().get_visible_rect().size)
	var staged_mira: RoVisual = SVVMiraTown.mira_visual
	for index in staged_jobs.size():
		var current_job: String = staged_jobs[index]
		var current_npc: RoVisual = SVVCompanionTown.npc_visuals.get(current_job)
		if current_npc == null or not is_instance_valid(current_npc):
			continue
		var hit_point: Vector2 = SVVCompanionTown._screen_point(current_npc)
		print("OFFLINE_QA NPC_PLACEMENT ", current_job, " world=", current_npc.global_position,
			" screen=", hit_point, " viewport=", frame_rect.size)
		check(hit_point.is_finite() and frame_rect.grow(48.0).has_point(hit_point),
			current_job + " screen target remains near town viewport")
		for next_index in range(index + 1, staged_jobs.size()):
			var other_job: String = staged_jobs[next_index]
			var other_npc: RoVisual = SVVCompanionTown.npc_visuals.get(other_job)
			if other_npc == null or not is_instance_valid(other_npc):
				continue
			var separation := Vector2(current_npc.global_position.x, current_npc.global_position.z).distance_to(
				Vector2(other_npc.global_position.x, other_npc.global_position.z))
			check(separation >= 1.75, current_job + " has space from " + other_job)
		if is_instance_valid(staged_mira):
			var mira_gap := Vector2(current_npc.global_position.x, current_npc.global_position.z).distance_to(
				Vector2(staged_mira.global_position.x, staged_mira.global_position.z))
			check(mira_gap >= 1.75, current_job + " has space from Mira patrol")
	for job in ["swordsman", "mage", "archer", "thief", "merchant"]:
		var npc: RoVisual = SVVCompanionTown.npc_visuals.get(job)
		check(npc != null and is_instance_valid(npc), job + " physically appears in Prontera")
		if npc != null and is_instance_valid(npc):
			check(npc.get_parent() == actual_town, job + " belongs to the original Town scene")
			check(npc.sprite is Sprite3D and npc.sprite.texture != null, job + " uses genuine rendered Ragnarok sprite")
			if kafra != null:
				check(npc.global_position.distance_to(kafra.global_position) >= 1.0, job + " does not overlap Kafra")
	# Regression: switching city context removes living visuals, dialogue,
	# and fallback buttons before the player can interact in another town.
	SVVCompanionTown._show_dialog("swordsman")
	check(SVVCompanionTown.dialog.visible, "Alden dialogue opens before changing town")
	world.set_meta("svv_offline_town_place", "payon")
	SVVCompanionTown._process(0.35)
	check(SVVCompanionTown.npc_visuals.is_empty(), "cross-city transition removes old companion visuals")
	check(not SVVCompanionTown.dialog.visible, "cross-city transition closes old companion dialogue")
	var hidden_fallbacks := true
	for fallback in SVVCompanionTown.fallback_buttons.values():
		if fallback.visible:
			hidden_fallbacks = false
	check(hidden_fallbacks, "cross-city transition hides fallback buttons")
	await get_tree().process_frame
	world.set_meta("svv_offline_town_place", "prontera")
	SVVCompanionTown._process(0.35)
	check(SVVCompanionTown.npc_visuals.size() == 5, "returning to Prontera restores exactly five companion NPCs")
	# Exercise the real click/tap projection path, not only _show_dialog().
	# The game is still headless here: full PC/mobile visual QA remains separate.
	for job in ["swordsman", "mage", "archer", "thief", "merchant"]:
		var click_target: RoVisual = SVVCompanionTown.npc_visuals.get(job)
		if click_target != null and is_instance_valid(click_target):
			var npc_camera: Camera3D = get_viewport().get_camera_3d()
			if npc_camera != null:
				var hit_point: Vector2 = SVVCompanionTown._screen_point(click_target)
				check(hit_point.is_finite(), job + " projects a valid click target")
				if hit_point.is_finite():
					for pointer_kind in ["mouse", "touch"]:
						var pointer_event: InputEvent
						if pointer_kind == "mouse":
							var mouse_event := InputEventMouseButton.new()
							mouse_event.button_index = MOUSE_BUTTON_LEFT
							mouse_event.pressed = true
							mouse_event.position = hit_point
							pointer_event = mouse_event
						else:
							var touch_event := InputEventScreenTouch.new()
							touch_event.pressed = true
							touch_event.position = hit_point
							pointer_event = touch_event
						SVVCompanionTown._unhandled_input(pointer_event)
						check(SVVCompanionTown.dialog.visible and SVVCompanionTown.selected_job == job,
							job + " opens correct dialogue from " + pointer_kind)
						SVVCompanionTown._close_dialog()
	# Lost/free'd sprites should restore on a later tick, without a
	# duplicate Alden visual and without replacing the original textures.
	var persistent_alden: RoVisual = SVVCompanionTown.npc_visuals.get("swordsman")
	var disposable_eira: RoVisual = SVVCompanionTown.npc_visuals.get("mage")
	if disposable_eira != null and is_instance_valid(disposable_eira):
		var previous_eira_id: int = disposable_eira.get_instance_id()
		disposable_eira.queue_free()
		await get_tree().process_frame
		SVVCompanionTown.sprite_retry_seconds = 4.0
		SVVCompanionTown._process(0.35)
		var restored_eira: RoVisual = SVVCompanionTown.npc_visuals.get("mage")
		check(restored_eira != null and is_instance_valid(restored_eira)
			and restored_eira.get_instance_id() != previous_eira_id,
			"Eira recreates original sprite after it is freed")
		check(SVVCompanionTown.npc_visuals.get("swordsman") == persistent_alden,
			"Alden remains one stable NPC during Eira's retry")
		if restored_eira != null and is_instance_valid(restored_eira):
			check(restored_eira.sprite is Sprite3D and restored_eira.sprite.texture != null,
				"recreated Eira still renders genuine Ragnarok textures")
	SVVCompanionTown._show_dialog("swordsman")
	check(SVVCompanionTown.dialog.visible, "Alden town dialogue opens")
	check(SVVCompanionTown.action.text == "Nhận nhiệm vụ", "Alden quest is available from town after Mira")
	SVVCompanionTown._do_action()
	check(bool(SVVAssistant._quest_progress("swordsman")["started"]), "Alden town NPC and Friends List share quest state")
	SVVCompanionTown._close_dialog()
	# Eira already belongs to the saved party: her town action must REMOVE,
	# not recruit her again. Test party-limit separately with Alden temporarily
	# flagged recruited; restore the fixture before starting the battle.
	SVVCompanionTown._show_dialog("mage")
	check(SVVCompanionTown.action.text == "Để Eira nghỉ" and not SVVCompanionTown.action.disabled,
		"Eira already in party has a working leave action")
	SVVCompanionTown._close_dialog()
	Save.set_setting("svv_offline_friends", ["acolyte", "mage", "archer", "swordsman"])
	SVVCompanionTown._show_dialog("swordsman")
	check(SVVCompanionTown.action.text == "Mời Alden vào party" and SVVCompanionTown.action.disabled,
		"new Alden cannot enter a full three-companion party")
	SVVCompanionTown._close_dialog()
	Save.set_setting("svv_offline_friends", ["acolyte", "mage", "archer"])
	Save.flush()
	world.leave_town()
	SVVMiraTown._clear_world_sprite()
	SVVCompanionTown._clear_world()
	await get_tree().process_frame
	world.menus.show_login()
	await get_tree().process_frame
	check(world.menus._mode == "class_select", "offline login redirects to character selection")
	check(world.coop_classes == expected_party, "new World restores selected AI roster")
	check(world.net.mode == "", "network session inactive")
	check(world.net.eos() == null, "EOS route unavailable")
	check(not world.cloud._enabled(), "cloud account route disabled")
	# Real player route: the menu's loading/transition callback, NOT a direct
	# start_run() call followed by manually closing the class-selection UI.
	# A previous QA forced menus.close() and could pass while the user was
	# trapped in a loop between To adventure! and the character selector.
	world.menus.show_loading(func(): world.start_run("swordsman", true))
	for frame in 180:
		if world.running and world.menus._mode not in ["login", "server_select", "class_select"]:
			break
		await get_tree().process_frame
	print("OFFLINE_QA ADVENTURE_TRANSITION state=", world.menus._mode,
		" running=", world.running, " paused=", get_tree().paused)
	check(world.running, "real menu loading flow starts battle")
	check(world.menus._mode not in ["login", "server_select", "class_select"],
		"To adventure never loops back to the character selector")
	check(not get_tree().paused or world.menus._mode != "",
		"gameplay is not silently paused beneath an invisible menu")
	# Only dismiss the remaining loading overlay after asserting its state.
	world.menus.close()
	get_tree().paused = false
	await get_tree().process_frame
	check(world.running, "original battle starts")
	check(world.map != null and is_instance_valid(world.map), "actual playable map is loaded")
	check(world.player != null and is_instance_valid(world.player), "player is spawned into the map")
	check(world.heroes.size() == 4, "human plus three AI companions")
	for hero in world.heroes:
		check(hero != null and is_instance_valid(hero), "party hero alive")
		if hero != world.player:
			check(hero.input is HeroInput.BotHero, "companion uses original tactical bot")
	var time_before: float = world.time
	for step in 120:
		# Do not force-close menus or unpause every frame: that would mask a
		# real-world re-entry loop or an invisible modal trapping gameplay.
		await get_tree().process_frame
	check(world.time > time_before, "battle simulation advances without QA forcing menu closed")
	check(world.menus._mode not in ["login", "server_select", "class_select"],
		"real gameplay does not bounce back to login or character selection")
	for hero in world.heroes:
		check(hero.position.is_finite(), "party position remains finite")
	# Regression: a living Acolyte must actually restore party HP,
	# and must not heal while downed or when there is no injury.
	var healer_slot: int = world.coop_classes.find("acolyte")
	var test_healer: Player = world.heroes[healer_slot + 1] if healer_slot >= 0 and healer_slot + 1 < world.heroes.size() else null
	check(test_healer != null, "offline roster includes Acolyte support")
	if test_healer != null:
		for hero in world.heroes:
			hero.downed = false
			hero.hp = hero.max_hp
		world.player.hp = maxf(1.0, world.player.max_hp * 0.42)
		var before_heal: float = world.player.hp
		check(SVVAssistant._try_support_heal(world), "Acolyte emergency support activates below HP threshold")
		check(world.player.hp > before_heal and world.player.hp <= world.player.max_hp, "support restores real player HP without overhealing")
		check(SVVMiraTown.heal_float.visible, "Mira support displays floating Heal effect")
		world.player.hp = maxf(1.0, world.player.max_hp * 0.35)
		test_healer.downed = true
		test_healer.hp = 0.0
		var downed_hp: float = world.player.hp
		check(not SVVAssistant._try_support_heal(world), "downed Acolyte cannot support")
		check(is_equal_approx(world.player.hp, downed_hp), "downed Acolyte never restores HP")
		test_healer.downed = false
		test_healer.hp = test_healer.max_hp
		for hero in world.heroes:
			hero.hp = hero.max_hp
		check(not SVVAssistant._try_support_heal(world), "healthy party does not waste healing")
	var ally: Player = world.heroes[1]
	ally.level = 4
	ally.xp = 3.0
	ally.hp = maxf(1.0, ally.max_hp * 0.7)
	var saved_hp: float = ally.hp
	var saved_gear: Dictionary = ally.equipment.slots.duplicate(true)
	var downed_ally: Player = world.heroes[2]
	downed_ally.downed = true
	downed_ally.hp = 0.0
	downed_ally.revive_t = 0.8
	var saved_time: float = world.time
	check(RunSave.save(world), "AI party run saves")
	var snapshot: Dictionary = RunSave.info()
	check(snapshot.get("offline_party", []).size() == 3, "snapshot includes three allies")
	check(RunSave.resume(world), "AI party run resumes")
	world.menus.close()
	get_tree().paused = false
	check(world.heroes.size() == 4, "resumed party roster preserved")
	check(world.heroes[1].level == 4, "ally level preserved after resume")
	check(is_equal_approx(world.heroes[1].hp, saved_hp), "ally HP preserved after resume")
	check(world.heroes[1].equipment.slots == saved_gear, "ally equipment preserved after resume")
	check(world.heroes[2].downed and world.heroes[2].hp == 0.0, "downed ally state preserved")
	check(is_equal_approx(world.heroes[2].revive_t, 0.8), "ally revive progress preserved")
	check(world.time >= saved_time - 0.01, "battle clock preserved after resume")
	var runs_before: int = int(Save.stat("runs"))
	var kills_before: int = int(Save.stat("kills"))
	world.kills = 7
	world.player.xp_gained = 45.0
	world._bank_run(false)
	check(int(Save.stat("runs")) == runs_before + 1, "human progression settles with AI party")
	check(int(Save.stat("kills")) == kills_before + 7, "human kill progress settles")
	world._bank_run(false)
	check(int(Save.stat("runs")) == runs_before + 1, "settlement cannot pay twice")
	Save.flush()
	Save.load_profile()
	check(int(Save.stat("runs")) == runs_before + 1, "settled progress survives profile reload")
	RunSave.clear()
	print("OFFLINE_QA COMPLETE failures=", failures.size())
	world.queue_free()
	await get_tree().process_frame
	get_tree().quit(0 if failures.is_empty() else 1)
