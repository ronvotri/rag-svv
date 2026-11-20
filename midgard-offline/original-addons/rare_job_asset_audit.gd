extends RefCounted
## QA-only source sprite inventory for rare NPCs.
## Runs from offline_smoke.gd after original Godot autoloads are initialized.
## A filename or a renderable texture never grants town placement approval.

const SPRITE_CANDIDATES := {
	"gunslinger": ["gunslinger", "gunslinger_f"],
	"taekwon": ["taekwon", "taekwon_f"],
	"ninja": ["ninja", "ninja_f"],
	# The original Build #309 recorded "summoner", not "doram".
	# This is an alias to investigate, NOT proof that Lumi is a Doram.
	"doram": ["summoner", "summoner_f"],
}

func run(preview_root: Node3D) -> Dictionary:
	var jobs: Dictionary = {}
	for job in SPRITE_CANDIDATES:
		var rows: Array[Dictionary] = []
		for sprite_id in SPRITE_CANDIDATES[job]:
			var found: bool = RoAssets.has_sprite(sprite_id)
			var loadable := false
			var renderable := false
			if found:
				var source_sprite = RoAssets.sprite([sprite_id])
				loadable = source_sprite != null
				if loadable:
					var preview := RoVisual.new()
					preview_root.add_child(preview)
					preview.setup(source_sprite, Color(0.8, 0.8, 0.9), 40)
					renderable = preview.sprite is Sprite3D and preview.sprite.texture != null
					preview.queue_free()
			rows.append({
				"sprite_id": sprite_id,
				"found": found,
				"loadable": loadable,
				"renderable": renderable,
			})
		jobs[job] = {
			"class_present": GameData.CLASSES.has(job),
			"sprite_candidates": rows,
			"alias_only": job == "doram",
			"approved_for_town": false,
		}
	var report: Dictionary = {
		"schema_version": 4,
		"source": "godot_recovered_original_runtime",
		"jobs": jobs,
		"all_jobs_approved": false,
	}
	print("RARE_NPC_QA_JSON " + JSON.stringify(report))
	return report
