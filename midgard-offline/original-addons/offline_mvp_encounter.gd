extends RefCounted
## Shared native encounter entry for isolated QA and the gated MVP menu.
## No official raid, rank, reward, stat changes or profile writes.
const ROSTER := ["baphomet", "osiris", "eddga", "mistress", "maya", "dark_lord"]

static func allowed(world: World, boss_id: String) -> bool:
	if Save._name != "profile_offline_test" or not OS.get_cmdline_user_args().has("--offline-test"):
		return false
	if not ROSTER.has(boss_id) or not is_instance_valid(world):
		return false
	return world.running and world.map != null and is_instance_valid(world.player) \
		and world.net.mode == "" and world.net.eos() == null and not world.cloud._enabled() \
		and not Updater._enabled() and not Leaderboard.enabled()

static func spawn(world: World, boss_id: String) -> Enemy:
	if not allowed(world, boss_id):
		return null
	var script: Script = load("res://scripts/core/mvp_raid.gd")
	if script == null or not script.can_instantiate():
		return null
	var validator: Object = script.new()
	if validator == null:
		return null
	var supported: bool = validator.has_method("supports") and bool(validator.call("supports", boss_id))
	if validator is Node:
		(validator as Node).queue_free()
	if not supported:
		return null
	var registry: Variant = world.get("enemies")
	if not registry is Array:
		return null
	var previous: Array = (registry as Array).duplicate()
	var point: Vector3 = world.player.position + Vector3(8.0, 0.0, 2.0)
	point.y = world.map.height_at(point)
	world.spawn_enemy(boss_id, point, true)
	await world.get_tree().process_frame
	if not allowed(world, boss_id):
		return null
	var latest: Variant = world.get("enemies")
	if not latest is Array:
		return null
	var found: Array[Enemy] = []
	for item in latest:
		if item is Enemy and is_instance_valid(item) and not previous.has(item):
			found.append(item)
	# Ambiguous registry changes never identify an unrelated enemy as the MVP.
	if found.size() != 1:
		return null
	return found[0]
