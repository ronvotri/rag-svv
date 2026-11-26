extends Node
## Disposable rendered QA scene. Uses actual live town visuals and authored portraits.
var output_dir := ""
var entries: Array[Dictionary] = []

func _ready() -> void:
	_run.call_deferred()

func _capture(name: String) -> bool:
	await RenderingServer.frame_post_draw
	var img: Image = get_viewport().get_texture().get_image()
	return img != null and not img.is_empty() and img.save_png(output_dir.path_join(name)) == OK

func _visual(job: String) -> RoVisual:
	if job == "acolyte":
		return SVVMiraTown.mira_visual
	return SVVCompanionTown.npc_visuals.get(job) as RoVisual

func _frame_digest(visual: RoVisual) -> String:
	if not is_instance_valid(visual) or not (visual.sprite is Sprite3D) or visual.sprite.texture == null:
		return ""
	var image: Image = visual.sprite.texture.get_image()
	if image == null or image.is_empty() or not image.get_used_rect().has_area():
		return ""
	var hashing := HashingContext.new()
	hashing.start(HashingContext.HASH_SHA256)
	hashing.update(image.get_data())
	return hashing.finish().hex_encode()

func _label(value: String, font_size: int) -> Label:
	var label := Label.new()
	label.text = value
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", font_size)
	return label

func _run() -> void:
	await get_tree().process_frame
	if Save._name != "profile_offline_test":
		get_tree().quit(2)
		return
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--friend-visual-output="):
			output_dir = arg.trim_prefix("--friend-visual-output=")
	if output_dir.is_empty():
		get_tree().quit(2)
		return
	DirAccess.make_dir_recursive_absolute(output_dir)
	Save.set_setting("privacy_seen", true)
	Save.set_setting("onboarded", true)
	var packed: PackedScene = load("res://scenes/main.tscn")
	var world: World = packed.instantiate() as World
	get_tree().root.add_child(world)
	await get_tree().create_timer(1.0).timeout
	world.enter_town("swordsman")
	var jobs := ["acolyte", "swordsman", "mage", "archer", "thief", "merchant"]
	var deadline: int = Time.get_ticks_msec() + 15000
	while Time.get_ticks_msec() < deadline:
		var all_ready := true
		for job in jobs:
			if not is_instance_valid(_visual(job)):
				all_ready = false
		if all_ready:
			break
		await get_tree().process_frame
	await get_tree().create_timer(0.5).timeout
	var map_saved: bool = await _capture("prontera-npcs.png")
	var first: Dictionary = {}
	for job in jobs:
		first[job] = _frame_digest(_visual(job))
	await get_tree().create_timer(2.0).timeout

	var layer := CanvasLayer.new()
	layer.layer = 200
	add_child(layer)
	var bg := ColorRect.new()
	bg.color = Color("172b27")
	layer.add_child(bg)
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var body := VBoxContainer.new()
	body.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	body.offset_left = 24
	body.offset_top = 18
	body.offset_right = -24
	body.offset_bottom = -18
	body.add_theme_constant_override("separation", 12)
	bg.add_child(body)
	body.add_child(_label("PRONTERA — Portrait / Native Town Sprite", 28))
	body.add_child(_label("Actual rendered frames · visual likeness pending manual review", 17))
	var grid := GridContainer.new()
	grid.columns = 3
	grid.add_theme_constant_override("h_separation", 18)
	grid.add_theme_constant_override("v_separation", 16)
	body.add_child(grid)
	var heads: Dictionary = {}
	var complete := true
	for job in jobs:
		var visual: RoVisual = _visual(job)
		var profile: Dictionary = SVVAssistant._friend_profile(job)
		var head := ""
		var digest: String = _frame_digest(visual)
		var portrait: Texture2D = SVVAssistant._portrait_texture(job)
		if is_instance_valid(visual):
			head = str(visual.get_meta("svv_friend_head", ""))
		var unique_head: bool = not head.is_empty() and not heads.has(head) and RoAssets.has_sprite(head)
		heads[head] = true
		var stable: bool = not digest.is_empty() and digest == str(first.get(job, ""))
		var valid: bool = unique_head and stable and portrait != null
		complete = complete and valid
		entries.append({"job": job, "head_key": head, "unique_native_head": unique_head,
			"rendered_frame_stable_2s": stable, "portrait_present": portrait != null})
		var card := VBoxContainer.new()
		card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		card.custom_minimum_size.x = 360
		grid.add_child(card)
		card.add_child(_label(str(profile.get("name", job)) + " · " + job, 20))
		var pair := HBoxContainer.new()
		pair.alignment = BoxContainer.ALIGNMENT_CENTER
		card.add_child(pair)
		var face := TextureRect.new()
		face.texture = portrait
		face.custom_minimum_size = Vector2(155, 180)
		face.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		face.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		pair.add_child(face)
		var sprite := TextureRect.new()
		sprite.custom_minimum_size = Vector2(155, 180)
		sprite.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		sprite.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		if is_instance_valid(visual) and visual.sprite is Sprite3D:
			sprite.texture = visual.sprite.texture
		pair.add_child(sprite)
		card.add_child(_label(head if not head.is_empty() else "Missing head", 15))
		card.add_child(_label("Stable frame" if stable else "Frame unverified", 15))
	await get_tree().process_frame
	await get_tree().process_frame
	var board_saved: bool = await _capture("portrait-sprite-review.png")
	var report := {"map_screenshot": map_saved, "comparison_screenshot": board_saved,
		"all_six_unique_heads_and_stable_frames": complete, "portrait_likeness_approved": false,
		"entries": entries}
	var file := FileAccess.open(output_dir.path_join("friend-visual-report.json"), FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(report, "\t"))
		file.close()
	get_tree().quit(0 if map_saved and board_saved and complete else 1)
