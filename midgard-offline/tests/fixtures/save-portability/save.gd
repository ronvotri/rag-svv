extends Node
const VERSION = 1
const WEB_RESCUE = "isolated_rescue_"
var _name = "profile_offline_test"
var PATH = "user://profile_offline_test.json"
var data: Dictionary = {}
var _dirty = false
func flush():
 if not _dirty: return
 var f = FileAccess.open_encrypted_with_pass(PATH, FileAccess.WRITE, "isolated-qa-only")
 f.store_string(JSON.stringify(data))
 f.close()
 _dirty = false
func _read(path: String) -> Dictionary:
 var text = ""
 var raw = FileAccess.get_file_as_bytes(path)
 if raw.slice(0,4).get_string_from_ascii() == "GDEC":
  var f = FileAccess.open_encrypted_with_pass(path,FileAccess.READ,"isolated-qa-only")
  if f == null: return {}
  text = f.get_as_text()
  f.close()
 else: text = raw.get_string_from_utf8()
 var parser = JSON.new()
 if parser.parse(text) != OK: return {}
 return parser.data if parser.data is Dictionary else {}
func stat(key: String): return data.get("stats",{}).get(key,0)
