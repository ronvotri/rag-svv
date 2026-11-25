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

# Compare only the exact requested identifier in plausible native ID fields.
# An ambiguous deferred spawn is never accepted merely because it appeared first.
static func _identity_matches(enemy: Enemy, boss_id: String) -> bool:
	for property in enemy.get_property_list():
		var key: String = str(property.get("name", ""))
		if key not in ["mob_id", "enemy_id", "monster_id", "id", "mob", "kind", "key"]:
			continue
		var value: Variant = enemy.get(key)
		if (value is String or value is StringName) and str(value) == boss_id:
			return true
	return false

static func _new_enemies(world: World, previous: Array) -> Array[Enemy]:
	var found: Array[Enemy] = []
	var latest: Variant = world.get("enemies")
	if latest is Array:
		for item in latest:
			if is_instance_valid(item) and item is Enemy and not previous.has(item):
				found.append(item)
	return found

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
	# Read the registry before the next process frame adds ordinary enemies.
	var immediate: Array[Enemy] = _new_enemies(world, previous)
	var selected: Enemy = null
	if immediate.size() == 1:
		selected = immediate[0]
	await world.get_tree().process_frame
	if not allowed(world, boss_id):
		return null
	var found: Array[Enemy] = _new_enemies(world, previous)
	if is_instance_valid(selected) and found.has(selected):
		print("WORLD_BOSS_MAP_QA SPAWN_DIAG synchronous_unique=", immediate.size(), " after_frame=", found.size())
		return selected
	var matches: Array[Enemy] = []
	for enemy in found:
		if _identity_matches(enemy, boss_id):
			matches.append(enemy)
	print("WORLD_BOSS_MAP_QA SPAWN_DIAG synchronous=", immediate.size(), " after_frame=", found.size(), " exact_id_matches=", matches.size())
	if matches.size() != 1:
		return null
	return matches[0]
