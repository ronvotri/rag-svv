extends Node
## Capture the real local game's own rendered viewport for visual verification.

var world: World
var folder: String

func _ready() -> void:
	_run.call_deferred()

func snap(name: String) -> void:
	await RenderingServer.frame_post_draw
	var image: Image = get_viewport().get_texture().get_image()
	if image.is_empty():
		push_error("VISUAL_QA empty viewport")
		return
	var error: Error = image.save_png(folder.path_join(name + ".png"))
	print("VISUAL_QA ", name, " saved=", error == OK)

func _run() -> void:
	await get_tree().process_frame
	if Save._name != "profile_offline_test":
		push_error("VISUAL_QA requires --offline-test")
		get_tree().quit(2)
		return
	folder = ProjectSettings.globalize_path("user://qa-screenshots")
	for argument in OS.get_cmdline_user_args():
		if str(argument).begins_with("--offline-output="):
			folder = str(argument).substr(17)
	DirAccess.make_dir_recursive_absolute(folder)
	Save.set_setting("privacy_seen", true)
	Save.set_setting("onboarded", true)
	var packed: PackedScene = load("res://scenes/main.tscn")
	world = packed.instantiate()
	get_tree().root.add_child(world)
	await get_tree().create_timer(1.0).timeout
	await snap("original-menu")
	world.enter_town("swordsman")
	await get_tree().create_timer(1.0).timeout
	await snap("original-town")
	# Capture actual NPC encounters in the recovered town scene; do not
	# synthesize alternate sprite art or claim an off-map preview is placed.
	for job in ["swordsman", "mage"]:
		SVVCompanionTown._show_dialog(job)
		if SVVCompanionTown.dialog.visible and SVVCompanionTown.selected_job == job:
			await snap("town-dialog-" + job)
		else:
			push_warning("VISUAL_QA cannot capture town dialogue for " + job)
		SVVCompanionTown._close_dialog()
	# Off-map job audit: do not instantiate unverified NPCs in town.
	for job in ["archer", "thief", "merchant", "novice"]:
		var sprite_id: String = SVVCompanionTown._first_original_sprite(job)
		print("VISUAL_QA WAVE2_SPRITE ", job, "=", sprite_id if not sprite_id.is_empty() else "MISSING")

	world.set_stage("prontera")
	world.start_run("swordsman", false)
	world.menus.close()
	get_tree().paused = false
	for index in 18:
		var angle: float = TAU * float(index) / 18.0
		var offset: Vector3 = Vector3(cos(angle), 0, sin(angle)) * (6.0 + float(index % 3))
		var position: Vector3 = world.player.position + offset
		position.y = world.map.height_at(position)
		world.spawn_enemy("poring" if index % 2 == 0 else "lunatic", position, true)
	for frame in 180:
		world.menus.close()
		get_tree().paused = false
		await get_tree().process_frame
	await snap("original-combat")
	world.running = false
	RunSave.clear()
	Save.flush()
	get_tree().quit()
