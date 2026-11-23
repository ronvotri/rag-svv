extends Node
## QA-only: not an autoload and never exposed in the player UI.
## Requires --offline-test, --offline-boss-map-qa and an isolated data dir.

const BOSS_CANDIDATES := [
	"baphomet", "osiris", "eddga", "mistress", "maya", "dark_lord",
	"phreeoni", "moonlight_flower", "golden_thief_bug",
]
var world: World
var errors: Array[String] = []
var screenshot_folder := ""

func _ready() -> void:
	_run.call_deferred()

func _check(ok: bool, label: String) -> void:
	print("WORLD_BOSS_MAP_QA ", "PASS " if ok else "FAIL ", label)
	if not ok:
		errors.append(label)

func _finish(message: String, exit_code: int = 2) -> void:
	print("WORLD_BOSS_MAP_QA RESULT ", message, " errors=", errors.size())
	if world != null and is_instance_valid(world):
		world.running = false
	get_tree().quit(exit_code)

func _candidate() -> String:
	# Call only the native pure support classifier; never begin the MVP raid.
	var script: Script = load("res://scripts/core/mvp_raid.gd")
	if script == null or not script.can_instantiate():
		return ""
	var validator: Object = script.new()
	if validator == null or not validator.has_method("supports"):
		return ""
	for candidate in BOSS_CANDIDATES:
		if bool(validator.call("supports", candidate)):
			if validator is Node:
				(validator as Node).queue_free()
			return candidate
	if validator is Node:
		(validator as Node).queue_free()
	return ""

func _snapshot(filename: String) -> void:
	if screenshot_folder.is_empty():
		return
	await RenderingServer.frame_post_draw
	var image: Image = get_viewport().get_texture().get_image()
	if image.is_empty() or image.save_png(screenshot_folder.path_join(filename)) != OK:
		errors.append("native_viewport_screenshot_missing")

func _run() -> void:
	await get_tree().process_frame
	var args: PackedStringArray = OS.get_cmdline_user_args()
	if not args.has("--offline-test") or not args.has("--offline-boss-map-qa"):
		_finish("DENIED_test_flags_missing")
		return
	if OS.get_environment("SVV_WORLD_BOSS_QA_SANDBOX") != "1":
		_finish("DENIED_sandbox_environment_missing")
		return
	for arg in args:
		if str(arg).begins_with("--offline-output="):
			screenshot_folder = str(arg).substr(len("--offline-output="))
	if not screenshot_folder.is_empty():
		DirAccess.make_dir_recursive_absolute(screenshot_folder)
	_check(Save._name == "profile_offline_test", "isolated_test_profile")
	_check(RunSave.path().contains("profile_offline_test"), "isolated_run_snapshot")
	_check(not Updater._enabled(), "original_updater_disabled")
	_check(not Leaderboard.enabled(), "official_leaderboard_disabled")
	if not errors.is_empty():
		_finish("DENIED_profile_or_services")
		return
	Save.set_setting("onboarded", true)
	Save.set_setting("privacy_seen", true)
	Save.set_setting("svv_offline_friends", ["mage", "archer", "acolyte"])
	Save.set_setting("svv_offline_party", ["mage", "archer", "acolyte"])
	Save.flush()
	var scene: PackedScene = load("res://scenes/main.tscn")
	if scene == null:
		_finish("BLOCKED_native_scene_missing")
		return
	world = scene.instantiate() as World
	if world == null:
		_finish("BLOCKED_world_scene_type")
		return
	get_tree().root.add_child(world)
	await get_tree().process_frame
	_check(world.net.mode == "", "network_session_inactive")
	_check(world.net.eos() == null, "eos_unavailable")
	_check(not world.cloud._enabled(), "cloud_account_disabled")
	if not errors.is_empty():
		_finish("DENIED_network_routes")
		return
	world.set_stage("prontera")
	world.start_run("swordsman", false)
	world.menus.close()
	get_tree().paused = false
	for frame in 12:
		await get_tree().process_frame
	_check(world.running and world.map != null and world.player != null, "original_map_with_player")
	_check(world.heroes.size() == 4, "human_plus_three_original_ai")
	if not errors.is_empty():
		_finish("BLOCKED_native_party")
		return
	for index in range(1, world.heroes.size()):
		var hero: Player = world.heroes[index]
		_check(hero != null and hero.input is HeroInput.BotHero, "original_bot_ai_%d" % index)
	if not errors.is_empty():
		_finish("BLOCKED_party_ai")
		return
	var boss_id: String = _candidate()
	if boss_id.is_empty():
		_finish("BLOCKED_no_supported_native_mvp", 3)
		return
	print("WORLD_BOSS_MAP_QA NATIVE_BOSS ", boss_id)
	# Use original in-world spawn only. Do not call start_world_boss(),
	# MvpRaid.start_route(), reward settlement, online chests or rankings.
	var registry: Variant = world.get("enemies")
	if not registry is Array:
		_finish("BLOCKED_native_enemy_registry_unknown", 3)
		return
	var previous: Array = (registry as Array).duplicate()
	var point: Vector3 = world.player.position + Vector3(8.0, 0.0, 2.0)
	point.y = world.map.height_at(point)
	var before_time: float = world.time
	world.spawn_enemy(boss_id, point, true)
	await get_tree().process_frame
	var latest: Variant = world.get("enemies")
	var spawned: Enemy = null
	if latest is Array:
		for item in latest:
			if item is Enemy and not previous.has(item):
				spawned = item
				break
	_check(spawned != null and is_instance_valid(spawned), "native_enemy_spawned_in_world")
	if not errors.is_empty():
		_finish("BLOCKED_native_spawn")
		return
	var rendered: Variant = spawned.get("visual")
	_check(rendered is Node and is_instance_valid(rendered), "original_boss_render_node")
	await _snapshot("boss-start.png")
	for frame in 120:
		await get_tree().process_frame
	_check(world.time > before_time, "real_world_time_advances")
	_check(is_instance_valid(spawned), "boss_survives_observation")
	if is_instance_valid(spawned):
		_check(spawned.position.is_finite(), "boss_has_valid_map_position")
	for index in range(1, world.heroes.size()):
		var friend: Player = world.heroes[index]
		_check(is_instance_valid(friend) and friend.position.is_finite(), "ai_position_%d" % index)
	await _snapshot("boss-after-120frames.png")
	# Node-level evidence is NOT proof of complete attacks, animation or rewards.
	_finish("NODE_LEVEL_WIRING_VERIFIED" if errors.is_empty() else "FAIL",
		0 if errors.is_empty() else 1)
