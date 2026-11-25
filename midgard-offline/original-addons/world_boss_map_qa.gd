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

func _candidate(requested: String) -> String:
	# Call only the native pure support classifier; never begin the MVP raid.
	var script: Script = load("res://scripts/core/mvp_raid.gd")
	if script == null or not script.can_instantiate():
		return ""
	var validator: Object = script.new()
	if validator == null or not validator.has_method("supports"):
		return ""
	var selected := ""
	for candidate in BOSS_CANDIDATES:
		var supported: bool = bool(validator.call("supports", candidate))
		print("WORLD_BOSS_MAP_QA MVP_CANDIDATE ", candidate, " supported=", supported)
		if supported and selected.is_empty() and (requested.is_empty() or requested == candidate):
			selected = candidate
	if validator is Node:
		(validator as Node).queue_free()
	return selected

func _snapshot(filename: String) -> void:
	if screenshot_folder.is_empty():
		return
	await RenderingServer.frame_post_draw
	var image: Image = get_viewport().get_texture().get_image()
	if image.is_empty() or image.save_png(screenshot_folder.path_join(filename)) != OK:
		errors.append("native_viewport_screenshot_missing")

# Read native runtime values only; do not call Enemy.hurt() or force damage.
func _native_number(obj: Object, name: String) -> Variant:
	if obj == null or not is_instance_valid(obj):
		return null
	for property in obj.get_property_list():
		if str(property.get("name", "")) == name:
			var value: Variant = obj.get(name)
			if value is float or value is int:
				return float(value)
	return null

# Observation only: a disappearing node is not proof of a boss kill.
# The real death callback and reward settlement require separate verification.
func _observe_terminal(boss: Enemy, human: Player, extended: bool) -> void:
	var deadline: int = Time.get_ticks_msec() + (240000 if extended else 20000)
	var world_limit: float = 180.0 if extended else 30.0
	var frame_limit: int = 36000 if extended else 1800
	var start_time: float = world.time
	var next_sample: float = 15.0
	print("WORLD_BOSS_MAP_QA OBSERVATION extended=", extended, " world_limit=", world_limit)
	var outcome := "observation_limit"
	var boss_hp: Variant = null
	var human_hp: Variant = null
	for frame in frame_limit:
		boss_hp = _native_number(boss, "hp") if is_instance_valid(boss) else null
		human_hp = _native_number(human, "hp") if is_instance_valid(human) else null
		if boss_hp != null and human_hp != null and float(boss_hp) <= 0.0 and float(human_hp) <= 0.0:
			outcome = "simultaneous_zero_hp"
			break
		if human_hp != null and float(human_hp) <= 0.0:
			outcome = "player_zero_hp_observed"
			break
		if boss_hp != null and float(boss_hp) <= 0.0:
			outcome = "boss_zero_hp_observed"
			break
		if boss_hp == null or human_hp == null:
			outcome = "node_or_hp_missing_unverified"
			break
		if not world.running:
			outcome = "world_stopped_unverified"
			break
		var elapsed: float = world.time - start_time
		if extended and elapsed >= next_sample:
			print("WORLD_BOSS_MAP_QA PROGRESS elapsed_world=", elapsed,
				" boss_hp=", boss_hp, " player_hp=", human_hp,
				" paused=", get_tree().paused)
			next_sample += 15.0
		if Time.get_ticks_msec() >= deadline or elapsed >= world_limit:
			break
		await get_tree().process_frame
	print("WORLD_BOSS_MAP_QA TERMINAL outcome=", outcome,
		" boss_hp=", boss_hp, " player_hp=", human_hp,
		" elapsed_world=", world.time - start_time)
	# Separate name: the original two-image combat acceptance gate is unchanged.
	await _snapshot("terminal-observation.png")

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
	var requested_boss := ""
	for arg in args:
		if str(arg).begins_with("--offline-boss-id="):
			requested_boss = str(arg).substr(len("--offline-boss-id="))
	var boss_id: String = _candidate(requested_boss)
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
	var boss_hp_before: Variant = _native_number(spawned, "hp")
	var player_hp_before: float = world.player.hp
	var hero_ids: Array[String] = []
	for member in world.heroes:
		hero_ids.append(str(member.get_instance_id()))
	spawned.set_meta("svv_qa_boss_hits", {})
	var ai_start_positions: Array[Vector3] = []
	for index in range(1, world.heroes.size()):
		ai_start_positions.append(world.heroes[index].position)
	await _snapshot("boss-start.png")
	for frame in 120:
		await get_tree().process_frame
	_check(world.time > before_time, "real_world_time_advances")
	_check(is_instance_valid(spawned), "boss_survives_observation")
	if is_instance_valid(spawned):
		_check(spawned.position.is_finite(), "boss_has_valid_map_position")
	var ai_moved: int = 0
	for index in range(1, world.heroes.size()):
		var friend: Player = world.heroes[index]
		_check(is_instance_valid(friend) and friend.position.is_finite(), "ai_position_%d" % index)
		if is_instance_valid(friend) and friend.position.distance_to(ai_start_positions[index - 1]) > 0.5:
			ai_moved += 1
	var boss_hp_after: Variant = _native_number(spawned, "hp") if is_instance_valid(spawned) else null
	print("WORLD_BOSS_MAP_QA COMBAT boss_hp_before=", boss_hp_before,
		" boss_hp_after=", boss_hp_after, " ai_moved=", ai_moved,
		" player_hp_before=", player_hp_before,
		" player_hp_after=", world.player.hp)
	_check(boss_hp_before != null and boss_hp_after != null, "native_boss_hp_readable")
	if boss_hp_before != null and boss_hp_after != null:
		_check(float(boss_hp_after) < float(boss_hp_before), "boss_loses_hp_without_forced_damage")
	_check(ai_moved > 0, "original_ai_moves_during_encounter")
	if is_instance_valid(spawned) and boss_hp_before != null and boss_hp_after != null:
		var hits: Dictionary = spawned.get_meta("svv_qa_boss_hits", {})
		var total: float = 0.0
		var party_total: float = 0.0
		var ai_hitters: int = 0
		for index in range(hero_ids.size()):
			var row: Dictionary = hits.get(hero_ids[index], {})
			var damage: float = float(row.get("damage", 0.0))
			var count: int = int(row.get("hits", 0))
			party_total += damage
			if index > 0 and damage > 0.0 and count > 0:
				ai_hitters += 1
			print("WORLD_BOSS_MAP_QA ATTRIBUTION slot=", index, " damage=", damage, " hits=", count)
		for key in hits:
			total += float(hits[key].get("damage", 0.0))
		var hp_loss: float = float(boss_hp_before) - float(boss_hp_after)
		var reconciled: bool = hp_loss > 0.0 and absf(total - hp_loss) < 0.1 and absf(total - party_total) < 0.1
		print("WORLD_BOSS_MAP_QA ATTRIBUTION_SUMMARY ai_hitters=", ai_hitters,
			" hp_loss=", hp_loss, " recorded=", total, " unknown=", total - party_total,
			" reconciled=", reconciled)
	await _snapshot("boss-after-120frames.png")
	if errors.is_empty():
		await _observe_terminal(spawned, world.player,
			args.has("--offline-boss-extended") and boss_id == "baphomet")
	# Gameplay mechanics observed; not proof of a full raid, AI attribution, safe loot, or rewards.
	_finish("COMBAT_MECHANICS_VERIFIED" if errors.is_empty() else "FAIL",
		0 if errors.is_empty() else 1)
