extends RefCounted
## Isolated, off-map motion/direction evidence from the ORIGINAL recovered client.
## Samples genuine RoVisual textures; DOES NOT recruit, place or approve NPCs.

const TARGETS := {
	"Cole": ["gunslinger", "gunslinger_f"],
	"Haneul": ["taekwon", "taekwon_f"],
}
const DIRECTIONS := [
	Vector3(0, 0, -1),
	Vector3(1, 0, -1),
	Vector3(1, 0, 0),
	Vector3(1, 0, 1),
	Vector3(0, 0, 1),
	Vector3(-1, 0, 1),
	Vector3(-1, 0, 0),
	Vector3(-1, 0, -1),
]

func _save_frame(visual: RoVisual, folder: String, entry: Dictionary, sprite_id: String,
		action_name: String, direction_index: int, tick: int) -> void:
	if not (visual.sprite is Sprite3D) or visual.sprite.texture == null:
		return
	var frame: Image = visual.sprite.texture.get_image()
	if frame == null or frame.is_empty() or not frame.get_used_rect().has_area():
		return
	var filename: String = "rare-motion-" + sprite_id + "-" + action_name.to_lower() + "-" + str(direction_index) + "-" + str(tick) + ".png"
	var path: String = folder.path_join(filename)
	if frame.save_png(path) != OK:
		return
	var dims: Vector2i = frame.get_size()
	entry["samples"].append({
		"action": action_name,
		"direction_index": direction_index,
		"tick": tick,
		"filename": filename,
		"sha256": FileAccess.get_sha256(path),
		"image_size": [dims.x, dims.y],
	})

func capture(folder: String) -> Dictionary:
	var report := {
		"source": "recovered_original_RoVisual_motion_probe",
		"scope": "offmap_qa_only",
		"approved_for_town": false,
		"animation_verified": false,
		"directions_verified": false,
		"entries": [],
	}
	var tree := Engine.get_main_loop() as SceneTree
	if tree == null:
		return report
	var parent := Node3D.new()
	tree.root.add_child(parent)
	for npc_name in TARGETS:
		for candidate in TARGETS[npc_name]:
			var sprite_id: String = str(candidate)
			var entry := {
				"npc": npc_name,
				"sprite_id": sprite_id,
				"actions_present": {"PC_IDLE": false, "PC_WALK": false},
				"samples": [],
			}
			if not RoAssets.has_sprite(sprite_id):
				entry["reason"] = "sprite_missing"
				report["entries"].append(entry)
				continue
			var source_sprite = RoAssets.sprite([sprite_id])
			if source_sprite == null:
				entry["reason"] = "sprite_unavailable"
				report["entries"].append(entry)
				continue
			var visual := RoVisual.new()
			parent.add_child(visual)
			visual.setup(source_sprite, Color(0.8, 0.8, 0.9), 40)
			var script: Script = visual.get_script()
			if script == null or not (visual.sprite is Sprite3D) or visual.sprite.texture == null:
				entry["reason"] = "render_api_unavailable"
			else:
				var constants: Dictionary = script.get_script_constant_map()
				for action_name in ["PC_IDLE", "PC_WALK"]:
					var available: bool = constants.has(action_name)
					entry["actions_present"][action_name] = available
					if not available:
						continue
					for direction_index in DIRECTIONS.size():
						# Real RoVisual.face(v: Vector3) verified in the recovered API.
						# A different exported image is not automatically a correct
						# facing direction or valid walking animation.
						visual.face(DIRECTIONS[direction_index])
						visual.play(int(constants[action_name]), true, true)
						await tree.create_timer(0.07).timeout
						_save_frame(visual, folder, entry, sprite_id, action_name, direction_index, 0)
						if action_name == "PC_WALK":
							await tree.create_timer(0.17).timeout
							_save_frame(visual, folder, entry, sprite_id, action_name, direction_index, 1)
			report["entries"].append(entry)
			print("RARE_NPC_MOTION_ENTRY " + JSON.stringify(entry))
			visual.queue_free()
	parent.queue_free()
	var json_file: FileAccess = FileAccess.open(folder.path_join("RARE_NPC_MOTION.json"), FileAccess.WRITE)
	if json_file != null:
		json_file.store_string(JSON.stringify(report, "\t") + "\n")
		json_file.close()
	print("RARE_NPC_MOTION_SUMMARY entries=", report["entries"].size(), " approved_for_town=false")
	return report
