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
	# Independent fast path for original sprite frames. This skips the expensive
	# Town, full viewport screenshots and combat sequence (150s CI timeout).
	# Still uses the recovered original RoVisual / RoAssets, never fake art.
	if "--rare-only" in OS.get_cmdline_user_args():
		var rare_script: Script = load("res://addons/svv_offline/qa/rare_job_visual.gd")
		if rare_script == null:
			push_error("RARE_NPC_VISUAL missing original-frame capture script")
			get_tree().quit(2)
			return
		var rare_visual = rare_script.new()
		var rare_frames: Dictionary = rare_visual.capture(folder)
		print("RARE_NPC_VISUAL_SUMMARY frames=", rare_frames.get("entries", []).size(),
			" approved_for_town=", rare_frames.get("approved_for_town", true))
		var motion_script: Script = load("res://addons/svv_offline/qa/rare_job_motion.gd")
		if motion_script != null:
			var motion_helper = motion_script.new()
			var motion_report: Dictionary = await motion_helper.capture(folder)
			print("RARE_NPC_MOTION_CHECK entries=", motion_report.get("entries", []).size(),
				" approved_for_town=", motion_report.get("approved_for_town", true))
		else:
			push_warning("RARE_NPC_MOTION missing optional original motion probe")
		# Source character factory composes gendered body + head/hair. QA only.
		var composed_script: Script = load("res://addons/svv_offline/qa/rare_job_composed.gd")
		if composed_script != null:
			var composed_helper = composed_script.new()
			var composed_report: Dictionary = await composed_helper.capture(folder)
			print("RARE_NPC_COMPOSED_CHECK entries=", composed_report.get("entries", []).size(),
				" approved_for_town=", composed_report.get("approved_for_town", true))
		else:
			push_warning("RARE_NPC_COMPOSED missing full-character QA probe")
		get_tree().quit()
		return
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
	# Capture the REAL offline mode cards with their rendered thumbnails;
	# a successful headless unit test alone cannot prove readable game UI.
	SVVOfflineEvents._open()
	if SVVOfflineEvents.panel.visible:
		await get_tree().create_timer(0.25).timeout
		await snap("town-offline-cards")
		SVVOfflineEvents._close()
	else:
		push_warning("VISUAL_QA offline mode cards not available in Prontera")
	# Wave 6: capture the original town and real job sprites in phone-sized
	# viewports, not substitute textures or an off-map mockup. These are
	# inspection evidence only, not proof of walkability or collision-free lanes.
	var original_window_size: Vector2i = get_window().size
	for phone_size in [Vector2i(390, 844), Vector2i(844, 390)]:
		get_window().size = phone_size
		await get_tree().create_timer(0.45).timeout
		var frame_size: Vector2 = get_viewport().get_visible_rect().size
		var frame_rect := Rect2(Vector2.ZERO, frame_size)
		for job in ["swordsman", "mage", "archer", "thief", "merchant"]:
			var npc: RoVisual = SVVCompanionTown.npc_visuals.get(job)
			if npc != null and is_instance_valid(npc):
				var point: Vector2 = SVVCompanionTown._screen_point(npc)
				print("VISUAL_QA NPC_FRAME job=", job, " requested=", phone_size,
					" actual=", frame_size, " screen=", point,
					" visible=", point.is_finite() and frame_rect.has_point(point))
		await snap("town-npcs-" + str(phone_size.x) + "x" + str(phone_size.y))
	get_window().size = original_window_size
	await get_tree().create_timer(0.35).timeout
	# Capture actual NPC encounters in the recovered town scene; do not
	# synthesize alternate sprite art or claim an off-map preview is placed.
	for job in ["swordsman", "mage", "archer", "thief", "merchant"]:
		SVVCompanionTown._show_dialog(job)
		if SVVCompanionTown.dialog.visible and SVVCompanionTown.selected_job == job:
			await snap("town-dialog-" + job)
		else:
			push_warning("VISUAL_QA cannot capture town dialogue for " + job)
		SVVCompanionTown._close_dialog()
	# Extract currently rendered genuine Ragnarok frames OFF-MAP for manual
	# Cole/Haneul/Kira/Lumi art identity checks. These are not 8-direction
	# animation proof and never spawn NPCs into Prontera.
	var rare_visual_script: Script = load("res://addons/svv_offline/qa/rare_job_visual.gd")
	if rare_visual_script != null:
		var rare_visual = rare_visual_script.new()
		var rare_frames: Dictionary = rare_visual.capture(folder)
		print("RARE_NPC_VISUAL_SUMMARY ", "frames=", rare_frames.get("entries", []).size(),
			" approved_for_town=", rare_frames.get("approved_for_town", true))
	else:
		push_warning("VISUAL_QA rare NPC frame helper unavailable")
	# Off-map job audit: do not instantiate unverified NPCs in town.
	for job in ["novice"]:
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
