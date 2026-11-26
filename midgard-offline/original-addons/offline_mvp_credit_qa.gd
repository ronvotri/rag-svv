extends RefCounted
## Private QA wallet transaction; available only in isolated smoke or explicit menu wallet preview.
const Rules = preload("res://addons/svv_offline/offline_mvp_result.gd")
const KEY := "svv_offline_mvp_credit_fixture"

static func redeem(boss_id: String, token: String) -> bool:
	if Save._name != "profile_offline_test" or not OS.get_cmdline_user_args().has("--offline-test") or not OS.get_cmdline_user_args().has("--offline-qa"):
		return false
	return _redeem(KEY, boss_id, token)


static func redeem_menu(boss_id: String, token: String) -> bool:
	var args := OS.get_cmdline_user_args()
	if Save._name != "profile_offline_test" or not args.has("--offline-test") or not args.has("--offline-mvp-menu-preview") or not args.has("--offline-mvp-wallet-preview") or OS.get_environment("SVV_WORLD_BOSS_QA_SANDBOX") != "1":
		return false
	return _redeem("svv_offline_mvp_victories", boss_id, token)


static func _redeem(key: String, boss_id: String, token: String) -> bool:
	if Save._name != "profile_offline_test":
		return false
	var importer = Save.get_node_or_null("/root/SVVSaveManager")
	if importer != null and importer.import_in_progress:
		return false
	Save.flush()
	if Save._dirty or not Save.data.get("settings") is Dictionary:
		return false
	var old_balance: int = Save.zeny()
	var raw: Variant = Save.data.get("zeny")
	if not (raw is int or raw is float) or raw != old_balance:
		return false
	var old_settings: Dictionary = Save.data.settings.duplicate(true)
	var ledger: Variant = old_settings.get(key, {})
	if not ledger is Dictionary:
		return false
	var plan: Dictionary = Rules.next_qa_credit(ledger, boss_id, token, old_balance)
	if plan.is_empty():
		return false
	# No await, signals or intermediate native setters: both fields are
	# serialized by the existing temporary-file/rename save operation.
	var next_settings: Dictionary = old_settings.duplicate(true)
	next_settings[key] = plan["ledger"]
	Save.data.settings = next_settings
	Save.data.zeny = plan["balance"]
	Save._dirty = true
	Save.flush()
	if Save._dirty:
		# Existing flush failed before successful rename. Roll back both
		# fields together in memory; do not issue a partial reward.
		Save.data.settings = old_settings
		Save.data.zeny = old_balance
		# Keep dirty state for the existing retry mechanism. A failed flush
		# must not be reported as a successful reward.
		return false
	return true
