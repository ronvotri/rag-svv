extends RefCounted
## Visual QA only: extract the currently rendered ORIGINAL RoVisual texture frame
## for each candidate. Does not place/animate/recruit NPCs, never changes save.
## These previews prove frame identity only; a real town and direction review
## is still required before accepting any sprite for production.

const PREVIEWS := {
	"Cole": ["gunslinger", "gunslinger_f"],
	"Haneul": ["taekwon", "taekwon_f"],
	"Kira": ["ninja", "ninja_f"],
	"Lumi": ["summoner", "summoner_f"], # Doram alias unverified
}

func capture(folder: String) -> Dictionary:
	var result := {
		"source": "recovered_original_RoVisual_texture_frame",
		"scope": "visual_qa_only",
		"approved_for_town": false,
		"animation_verified": false,
		"directions_verified": false,
		"entries": [],
	}
	var parent := Node3D.new()
	Engine.get_main_loop().root.add_child(parent)
	for npc_name in PREVIEWS:
		for sprite_id in PREVIEWS[npc_name]:
			var entry := {
				"npc": npc_name,
				"sprite_id": sprite_id,
				"candidate_alias_only": npc_name == "Lumi",
				"saved": false,
			}
			if not RoAssets.has_sprite(sprite_id):
				entry["reason"] = "sprite_missing"
				result["entries"].append(entry)
				continue
			var data = RoAssets.sprite([sprite_id])
			if data == null:
				entry["reason"] = "sprite_not_loadable"
				result["entries"].append(entry)
				continue
			var visual := RoVisual.new()
			parent.add_child(visual)
			visual.setup(data, Color(0.8, 0.8, 0.9), 40)
			if not (visual.sprite is Sprite3D) or visual.sprite.texture == null:
				entry["reason"] = "texture_not_renderable"
			else:
				var frame: Image = visual.sprite.texture.get_image()
				if frame == null or frame.is_empty():
					entry["reason"] = "texture_image_empty"
				else:
					var original_size := frame.get_size()
					var filename := "rare-frame-" + sprite_id + ".png"
					var save_error := frame.save_png(folder.path_join(filename))
					entry["saved"] = save_error == OK
					entry["filename"] = filename
					entry["image_size"] = [original_size.x, original_size.y]
					if save_error != OK:
						entry["reason"] = "png_save_failed"
			print("RARE_NPC_VISUAL_FRAME " + JSON.stringify(entry))
			result["entries"].append(entry)
			visual.queue_free()
	parent.queue_free()
	var json_path := folder.path_join("RARE_NPC_VISUAL.json")
	var output := FileAccess.open(json_path, FileAccess.WRITE)
	if output != null:
		output.store_string(JSON.stringify(result, "\t") + "\n")
		output.close()
	return result
