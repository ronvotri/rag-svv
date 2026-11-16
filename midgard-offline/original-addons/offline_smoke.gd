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
	if Save._name != "profile_offline_test":
		get_tree().quit(2)
		return
	check(GameData.CLASSES.size() == 11, "11 original base classes")
	check(GameData.STAGES.size() == 20, "20 original stages")
	check(GameData.SKILLS.size() == 349, "349 original skill records")
	check(GameData.CARDS.size() == 163, "163 original cards")
	check(GameData.ITEMS.size() == 209, "209 original items")
	check(GameData.PETS.size() == 46, "46 original pets")
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
	check(world.coop_classes == expected_party, "new World restores selected AI roster")
	check(world.net.mode == "", "network session inactive")
	check(world.net.eos() == null, "EOS route unavailable")
	check(not world.cloud._enabled(), "cloud account route disabled")
	world.start_run("swordsman", false)
	world.menus.close()
	get_tree().paused = false
	await get_tree().process_frame
	check(world.running, "original battle starts")
	check(world.heroes.size() == 4, "human plus three AI companions")
	for hero in world.heroes:
		check(hero != null and is_instance_valid(hero), "party hero alive")
		if hero != world.player:
			check(hero.input is HeroInput.BotHero, "companion uses original tactical bot")
	for step in 120:
		world.menus.close()
		get_tree().paused = false
		await get_tree().process_frame
	check(world.time > 0.0, "battle simulation advances")
	for hero in world.heroes:
		check(hero.position.is_finite(), "party position remains finite")
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
