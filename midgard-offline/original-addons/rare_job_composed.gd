extends RefCounted
## QA-only: render original client composed character (body + head/hair) OFF-MAP.
## No Prontera spawn, no recruit, no save changes and no auto art approval.
## Uses the recovered client's own RoAssets.styled_character API.

const TARGETS := [
	{"npc": "Cole", "sprite_id": "gunslinger", "body": "gunslinger", "gender": "m"},
	{"npc": "Cole", "sprite_id": "gunslinger_f", "body": "gunslinger", "gender": "f"},
	{"npc": "Haneul", "sprite_id": "taekwon", "body": "taekwon", "gender": "m"},
	{"npc": "Haneul", "sprite_id": "taekwon_f", "body": "taekwon", "gender": "f"},
]
const DIRECTIONS := [
	Vector3(0, 0, -1), Vector3(1, 0, -1),
	Vector3(1, 0, 0), Vector3(1, 0, 1),
	Vector3(0, 0, 1), Vector3(-1, 0, 1),
	Vector3(-1, 0, 0), Vector3(-1, 0, -1),
]

func _save_frame(visual: RoVisual, folder: String, entry: Dictionary,
		sprite_id: String, action_name: String, direction_index: int, tick: int) -> void:
	if not (visual.sprite is Sprite3D) or visual.sprite.texture == null:
		return
	var frame: Image = visual.sprite.texture.get_image()
	if frame == null or frame.is_empty() or not frame.get_used_rect().has_area():
		return
	var filename: String = "rare-composed-" + sprite_id + "-" + action_name.to_lower() + "-" + str(direction_index) + "-" + str(tick) + ".png"
	var path: String = folder.path_join(filename)
	if frame.save_png(path) != OK:
		return
	var size: Vector2i = frame.get_size()
	entry["samples"].append({
		"action": action_name,
		"direction_index": direction_index,
		"tick": tick,
		"filename": filename,
		"sha256": FileAccess.get_sha256(path),
		"image_size": [size.x, size.y],
	})

func capture(folder: String) -> Dictionary:
	var report := {
		"source": "recovered_original_RoAssets_styled_character_motion_probe",
		"scope": "offmap_qa_only",
		"factory": "RoAssets.styled_character",
		"approved_for_town": false,
		"animation_verified": false,
		"directions_verified": false,
		"head_hair_verified": false,
		"entries": [],
	}
	var tree := Engine.get_main_loop() as SceneTree
	if tree == null:
		return report
	var root := Node3D.new()
	tree.root.add_child(root)
	for target in TARGETS:
		var sprite_id: String = str(target["sprite_id"])
		var entry := {
			"npc": str(target["npc"]),
			"sprite_id": sprite_id,
			"body": str(target["body"]),
			"gender": str(target["gender"]),
			"factory": "RoAssets.styled_character",
			"actions_present": {"PC_IDLE": false, "PC_WALK": false},
			"samples": [],
		}
		if not RoAssets.has_sprite(sprite_id):
			entry["reason"] = "body_source_missing"
			report["entries"].append(entry)
			continue
		# This exact parameter order is from recovered-client Build #342.
		# The body key remains UNGENDERED; the factory picks _f internally.
		# No equipment is needed for a clean head/hair composition baseline.
		var look := {"gender": entry["gender"], "hair": 2, "hair_color": 0, "cloth": 0}
		var composite: RoSprite = RoAssets.styled_character(
			str(target["body"]), "", "", [RoVisual.PC_ATTACK], "", look)
		if composite == null:
			entry["reason"] = "composite_factory_returned_null"
			report["entries"].append(entry)
			continue
		var visual := RoVisual.new()
		root.add_child(visual)
		visual.setup(composite, Color(0.8, 0.8, 0.9), 40)
		var script: Script = visual.get_script()
		if script == null or not (visual.sprite is Sprite3D) or visual.sprite.texture == null:
			entry["reason"] = "composed_render_api_unavailable"
		else:
			var constants: Dictionary = script.get_script_constant_map()
			for action_name in ["PC_IDLE", "PC_WALK"]:
				var available: bool = constants.has(action_name)
				entry["actions_present"][action_name] = available
				if not available:
					continue
				for direction_index in DIRECTIONS.size():
					visual.face(DIRECTIONS[direction_index])
					visual.play(int(constants[action_name]), true, true)
					await tree.create_timer(0.07).timeout
					_save_frame(visual, folder, entry, sprite_id, action_name, direction_index, 0)
					if action_name == "PC_WALK":
						await tree.create_timer(0.17).timeout
						_save_frame(visual, folder, entry, sprite_id, action_name, direction_index, 1)
		report["entries"].append(entry)
		print("RARE_NPC_COMPOSED_ENTRY " + JSON.stringify(entry))
		visual.queue_free()
	root.queue_free()
	var output := FileAccess.open(folder.path_join("RARE_NPC_COMPOSED.json"), FileAccess.WRITE)
	if output != null:
		output.store_string(JSON.stringify(report, "\t") + "\n")
		output.close()
	print("RARE_NPC_COMPOSED_SUMMARY entries=", report["entries"].size(), " approved_for_town=false")
	return report
