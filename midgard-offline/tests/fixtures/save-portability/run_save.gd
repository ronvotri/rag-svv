class_name RunSave
extends RefCounted
static var prevent_clear := false
static func path() -> String:
 return "user://profile_offline_test.run"
static func clear():
 if prevent_clear: return
 if FileAccess.file_exists(path()):
  DirAccess.remove_absolute(ProjectSettings.globalize_path(path()))
