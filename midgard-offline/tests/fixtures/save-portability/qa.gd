extends SceneTree
func _initialize():
 call_deferred("run_checks")
func run_checks():
 var save = root.get_node("Save")
 var manager = root.get_node("SVVSaveManager")
 save.data = {"version":1,"zeny":17,"settings":{},"stats":{"kills":40,"runs":4},"classes":{},"cards":{},"upgrades":{},"stages":{}}
 save._dirty = true
 var temporary = save.TMP_PATH
 save.TMP_PATH = "user://missing-directory/cannot-write.tmp"
 save.flush()
 assert(save._dirty,"Failed disk write must retain pending save for retry")
 save.TMP_PATH = temporary
 save.flush()
 assert(not save._dirty,"Successful durable write clears pending save")
 root.size = Vector2i(1280,720)
 manager.open_manager()
 assert(manager.dialog.visible,"Native save manager can open from main menu")
 manager._confirm_choose_import()
 assert(manager.confirm_import.get_parent() == manager.dialog,"Import confirmation is nested under its existing modal")
 manager.confirm_import.hide()
 manager.dialog.hide()
 var old = FileAccess.get_file_as_bytes(save.PATH)
 assert(manager._validated_profile(old), "Valid encrypted profile accepted")
 assert(not manager._validated_profile("{\"version\":1,\"zeny\":18,\"junk\":\"long enough for size limit\"}".to_utf8_buffer()), "Hash-valid incomplete profile rejected")
 assert(not manager._validated_profile("this is not a valid save of the game at all".to_utf8_buffer()), "Malformed profile rejected")
 var invalid = "this is not a valid save of the game at all".to_utf8_buffer()
 var envelope = {"format":"rag-svv-offline-save","version":1,"encoding":"base64","payload":Marshalls.raw_to_base64(invalid),"sha256":manager._sha256(invalid)}
 manager._receive_import_file([JSON.stringify(envelope),"invalid.json"])
 assert(FileAccess.get_file_as_bytes(save.PATH) == old,"Invalid import leaves real profile intact")
 assert(not manager.import_in_progress,"Invalid import does not lock UI")
 for child in root.get_children():
  if child is Window: child.hide()
 save.data.zeny = 99
 save._dirty = true
 save.flush()
 var imported = FileAccess.get_file_as_bytes(save.PATH)
 FileAccess.open(save.PATH,FileAccess.WRITE).store_buffer(old)
 save.data.zeny = 17
 FileAccess.open("user://profile_offline_test.run",FileAccess.WRITE).store_string("old run")
 envelope.payload = Marshalls.raw_to_base64(imported)
 envelope.sha256 = manager._sha256(imported)
 manager._receive_import_file([JSON.stringify(envelope),"valid.json"])
 assert(save._read(save.PATH).zeny == 99,"Valid JSON import installs encrypted profile")
 assert(FileAccess.get_file_as_bytes(manager._before_import_path()) == old,"Before-import backup retains previous profile")
 assert(not FileAccess.file_exists("user://profile_offline_test.run"),"Stale run cleared on profile replacement")
 assert(manager.import_in_progress,"Native import stops gameplay until restart")
 assert(not save.is_processing(),"Old in-memory autosave cannot overwrite imported profile")
 save._dirty = true
 save.flush()
 assert(save._read(save.PATH).zeny == 99,"Focus notification flush cannot overwrite import")
 assert(save._dirty,"Flush waits while import is active")
 save._dirty = false
 var guardian = root.get_node("SVVSaveGuardian")
 var guarded = guardian.capture_import_state()
 assert(guardian.adopt_imported_profile(old),"Can adopt an explicit older import")
 assert(guardian.restore_import_state(guarded),"Can restore exact prior guardian transaction")
 assert(guardian.capture_import_state() == guarded,"Rollback retains byte-identical metadata and snapshots")
 print("SAVE_PORTABILITY_QA_OK")
 quit(0)
