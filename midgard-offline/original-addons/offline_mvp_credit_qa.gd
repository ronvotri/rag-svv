extends RefCounted
## Private QA wallet transaction; never called by production or battle UI.
const Rules = preload("res://addons/svv_offline/offline_mvp_result.gd")
const KEY := "svv_offline_mvp_credit_fixture"

static func redeem(boss_id: String, token: String) -> bool:
	if Save._name != "profile_offline_test" or not OS.get_cmdline_user_args().has("--offline-test") or not OS.get_cmdline_user_args().has("--offline-qa"):
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
	var ledger: Variant = old_settings.get(KEY, {})
	if not ledger is Dictionary:
		return false
	var plan: Dictionary = Rules.next_qa_credit(ledger, boss_id, token, old_balance)
	if plan.is_empty():
		return false
	# No await, signals or intermediate native setters: both fields are
	# serialized by the existing temporary-file/rename save operation.
	var next_settings: Dictionary = old_settings.duplicate(true)
	next_settings[KEY] = plan["ledger"]
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
