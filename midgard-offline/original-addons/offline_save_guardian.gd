extends Node
## Offline Save Guardian: local rolling snapshots of the ORIGINAL encrypted profile.
## Inspired by PKMSVV's protection principle, but uses Godot FileAccess, not localStorage.
## Never uploads data or mixes test and normal player profiles.

const MIN_BYTES = 32
const INTERVAL_SECONDS = 15.0
var elapsed := 0.0
var last_warning := ""

static func _path(profile_name: String, slot: String) -> String:
	return "user://%s.guard.%s" % [profile_name, slot]

static func _read_bytes(path: String) -> PackedByteArray:
	if not FileAccess.file_exists(path):
		return PackedByteArray()
	return FileAccess.get_file_as_bytes(path)

static func _read_meta(profile_name: String, slot: String) -> Dictionary:
	var path := _path(profile_name, slot) + ".json"
	if not FileAccess.file_exists(path):
		return {}
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(path))
	return parsed if parsed is Dictionary else {}

static func _verified(profile_name: String, slot: String) -> bool:
	var path := _path(profile_name, slot)
	var meta := _read_meta(profile_name, slot)
	if not meta.has("sha256") or not meta.has("size"):
		return false
	var payload := _read_bytes(path)
	return payload.size() >= MIN_BYTES and payload.size() == int(meta["size"]) and FileAccess.get_sha256(path) == str(meta["sha256"])

static func _write_atomically(path: String, data: PackedByteArray) -> bool:
	var temp := path + ".svvtmp"
	var writer := FileAccess.open(temp, FileAccess.WRITE)
	if writer == null:
		return false
	writer.store_buffer(data)
	writer.flush()
	writer.close()
	var result := DirAccess.rename_absolute(ProjectSettings.globalize_path(temp), ProjectSettings.globalize_path(path))
	if result != OK:
		DirAccess.remove_absolute(ProjectSettings.globalize_path(temp))
	return result == OK

static func restore_missing_profile(primary: String, profile_name: String) -> bool:
	# Never overwrite an existing, nonempty profile, even if it looks suspect.
	# The original Save.load_profile() remains responsible for its own validation.
	if _read_bytes(primary).size() >= MIN_BYTES:
		return false
	for slot in ["latest", "previous"]:
		if _verified(profile_name, slot):
			return _write_atomically(primary, _read_bytes(_path(profile_name, slot)))
	return false

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	call_deferred("snapshot")

func _process(delta: float) -> void:
	elapsed += delta
	if elapsed >= INTERVAL_SECONDS:
		elapsed = 0.0
		snapshot()

func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST or what == NOTIFICATION_APPLICATION_PAUSED:
		if Save != null:
			Save.flush()
			snapshot()

func latest_path() -> String:
	return _path(str(Save._name), "latest")

func backup_now() -> bool:
	Save.flush()
	return snapshot()

func snapshot() -> bool:
	var profile_name := str(Save._name)
	if not profile_name.begins_with("profile_offline"):
		return false
	var primary := str(Save.PATH)
	var content := _read_bytes(primary)
	if content.size() < MIN_BYTES:
		return false
	var signature := FileAccess.get_sha256(primary)
	var latest_meta := _read_meta(profile_name, "latest")
	if _verified(profile_name, "latest") and str(latest_meta.get("sha256", "")) == signature:
		return true
	var runs := int(Save.stat("runs"))
	var kills := int(Save.stat("kills"))
	# These counters must never drop on a normal profile. Legitimate purchases
	# can reduce Zeny, bag quantities and materials, so NEVER compare them.
	if _verified(profile_name, "latest"):
		if runs < int(latest_meta.get("runs", 0)) or kills < int(latest_meta.get("kills", 0)):
			last_warning = "Save có dấu hiệu mất tiến trình. Đã giữ nguyên bản sao an toàn."
			push_warning("SVV Save Guardian: " + last_warning)
			return false
		var older := _read_bytes(_path(profile_name, "latest"))
		if not _write_atomically(_path(profile_name, "previous"), older):
			return false
		var older_json := JSON.stringify(latest_meta).to_utf8_buffer()
		if not _write_atomically(_path(profile_name, "previous") + ".json", older_json):
			return false
	var meta := {"schema": 1, "size": content.size(), "sha256": signature, "runs": runs, "kills": kills, "profile": profile_name}
	if not _write_atomically(_path(profile_name, "latest"), content):
		return false
	if not _write_atomically(_path(profile_name, "latest") + ".json", JSON.stringify(meta).to_utf8_buffer()):
		return false
	last_warning = ""
	return true
