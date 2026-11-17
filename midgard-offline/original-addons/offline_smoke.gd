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
	check(SVVAssistant.open_button.text == "Tìm party", "party discovery UI uses natural wording")
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
	Save.set_setting("svv_offline_party", expected_party)
	Save.flush()
	Save.load_profile()
	check(Save.setting("svv_offline_party", []) == expected_party, "chosen AI roster survives profile reload")
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
