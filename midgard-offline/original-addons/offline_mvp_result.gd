extends RefCounted
## Pure offline encounter result rules. No native stat changes, rewards or save I/O.
const ROSTER := ["baphomet", "osiris", "eddga", "mistress", "maya", "dark_lord"]

static func classify(boss_hp: Variant, player_hp: Variant, native_death: bool, running: bool, cancelled: bool) -> String:
	if cancelled:
		return "cancelled"
	if not (boss_hp is float or boss_hp is int) or not (player_hp is float or player_hp is int):
		return "unverified"
	var boss: float = float(boss_hp)
	var player: float = float(player_hp)
	if not is_finite(boss) or not is_finite(player):
		return "unverified"
	if boss <= 0.0 and player <= 0.0:
		return "draw" if native_death else "unverified"
	if player <= 0.0:
		return "defeat"
	if boss <= 0.0:
		return "victory" if native_death else "unverified"
	return "active" if running else "unverified"

# Return an empty dictionary for invalid or duplicate settlement.
# Copy the caller's ledger, preserving other MVPs and legacy counters.
static func next_victory_ledger(ledger: Dictionary, boss_id: String, token: String, outcome: String) -> Dictionary:
	if outcome != "victory" or not ROSTER.has(boss_id) or token.length() != 32 or not token.is_valid_hex_number():
		return {}
	# Reject replays across different bosses as well as the same boss.
	for key in ledger:
		var existing: Variant = ledger[key]
		if not existing is Dictionary:
			return {}
		var settled: Variant = existing.get("settled_tokens", [])
		if not settled is Array:
			return {}
		if str(existing.get("last_token", "")) == token or settled.has(token):
			return {}
	var updated: Dictionary = ledger.duplicate(true)
	var row: Dictionary = updated.get(boss_id, {})
	var tokens: Array = row.get("settled_tokens", []).duplicate()
	var previous: String = str(row.get("last_token", ""))
	if not previous.is_empty() and not tokens.has(previous):
		tokens.append(previous)
	tokens.append(token)
	row["settled_tokens"] = tokens
	row["last_token"] = token
	row["wins"] = int(row.get("wins", 0)) + 1
	updated[boss_id] = row
	return updated

# Test-only receipt. It does not change the native wallet or inventory.
# The victory token and receipt are committed in the same settings dictionary.
const QA_ZENY_QUOTE := 100
const QA_MVP_MARKS := 1

static func next_reward_receipt_ledger(ledger: Dictionary, boss_id: String, token: String, outcome: String) -> Dictionary:
	var updated: Dictionary = next_victory_ledger(ledger, boss_id, token, outcome)
	if updated.is_empty():
		return {}
	var row: Dictionary = updated[boss_id]
	var receipts: Variant = row.get("reward_receipts", {})
	if not receipts is Dictionary or receipts.has(token):
		return {}
	receipts[token] = {
		"zeny_quote": QA_ZENY_QUOTE,
		"mvp_marks": QA_MVP_MARKS,
		"status": "qa_pending",
	}
	row["reward_receipts"] = receipts
	updated[boss_id] = row
	return updated

# A credit plan is pure and non-spendable until the QA transaction commits
# both the wallet and the receipt in the same encrypted profile.
static func next_qa_credit(ledger: Dictionary, boss_id: String, token: String, balance: int) -> Dictionary:
	if not ROSTER.has(boss_id) or token.length() != 32 or not token.is_valid_hex_number():
		return {}
	if balance < 0 or balance > 2147483647 - QA_ZENY_QUOTE:
		return {}
	var updated: Dictionary = ledger.duplicate(true)
	var row: Variant = updated.get(boss_id, {})
	if not row is Dictionary or not row.get("settled_tokens", []) is Array:
		return {}
	if not row.get("settled_tokens", []).has(token):
		return {}
	var receipts: Variant = row.get("reward_receipts", {})
	if not receipts is Dictionary:
		return {}
	var receipt: Variant = receipts.get(token, {})
	if not receipt is Dictionary or receipt.get("status", "") != "qa_pending":
		return {}
	if receipt.get("zeny_quote", 0) != QA_ZENY_QUOTE or receipt.get("mvp_marks", 0) != QA_MVP_MARKS:
		return {}
	receipt["status"] = "qa_credited"
	receipts[token] = receipt
	row["reward_receipts"] = receipts
	updated[boss_id] = row
	return {"ledger": updated, "balance": balance + QA_ZENY_QUOTE}

static func title_for(outcome: String) -> String:
	match outcome:
		"victory": return "Săn MVP thành công!"
		"defeat": return "Thất bại"
		"draw": return "Hai bên cùng gục ngã"
		"cancelled": return "Đã rời trận"
		"active": return "Đang chiến đấu"
		_: return "Chưa xác nhận kết quả"
