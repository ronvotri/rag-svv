class_name RunSave
extends RefCounted
static func clear():
 if FileAccess.file_exists("user://profile_offline_test.run"):
  DirAccess.remove_absolute(ProjectSettings.globalize_path("user://profile_offline_test.run"))
