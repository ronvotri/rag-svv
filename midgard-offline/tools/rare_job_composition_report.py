"""Integrity-only validation of original-client full-character QA captures.

Never treats a syntactically correct PNG or different hash as art approval,
Town placement permission, a companion unlock, or proof of correct head/hair.
"""
import hashlib
import json
from pathlib import Path
import re
import struct

TARGETS = {
    "gunslinger": ("Cole", "gunslinger", "m"),
    "gunslinger_f": ("Cole", "gunslinger", "f"),
    "taekwon": ("Haneul", "taekwon", "m"),
    "taekwon_f": ("Haneul", "taekwon", "f"),
}
ACTIONS = {"PC_IDLE": 1, "PC_WALK": 2}
SOURCE = "recovered_original_RoAssets_styled_character_motion_probe"


def validate_composed_frames(folder):
    folder = Path(folder)
    base = {
        "approved_for_town": False,
        "animation_verified": False,
        "directions_verified": False,
        "head_hair_verified": False,
        "manual_art_identity_qa": "pending",
    }

    def reject(reason):
        return {**base, "status": "invalid_composed_evidence",
                "verified_samples": 0, "reason": reason}

    manifest = folder / "RARE_NPC_COMPOSED.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return reject("missing or invalid composed motion manifest")
    if not isinstance(data, dict) or any(data.get(k) != v for k, v in {
        "source": SOURCE, "scope": "offmap_qa_only",
        "factory": "RoAssets.styled_character",
        "approved_for_town": False, "animation_verified": False,
        "directions_verified": False, "head_hair_verified": False,
    }.items()):
        return reject("unsafe composition origin or approval flag")
    entries = data.get("entries")
    if not isinstance(entries, list) or len(entries) != 4:
        return reject("requires four original Cole/Haneul variants")
    seen = set()
    files = set()
    total, body_differences, variants_differing = 0, 0, 0
    complete = True
    for entry in entries:
        if not isinstance(entry, dict):
            return reject("invalid variant row")
        ident = entry.get("sprite_id")
        if ident not in TARGETS or ident in seen:
            return reject("unknown or duplicate variant")
        seen.add(ident)
        name, body, gender = TARGETS[ident]
        if any(entry.get(k) != v for k, v in {
            "npc": name, "body": body, "gender": gender,
            "factory": "RoAssets.styled_character",
        }.items()):
            return reject("incorrect body/gender/factory")
        actions = entry.get("actions_present")
        if (not isinstance(actions, dict) or set(actions) != set(ACTIONS)
                or any(type(actions[a]) is not bool for a in ACTIONS)):
            return reject("invalid action metadata")
        if not all(actions.values()):
            complete = False
        expected = {(act, direction, tick)
                    for act, ticks in ACTIONS.items() if actions[act]
                    for direction in range(8) for tick in range(ticks)}
        got = set()
        row_differences = 0
        samples = entry.get("samples")
        if not isinstance(samples, list):
            return reject("no PNG sample list")
        for sample in samples:
            if not isinstance(sample, dict):
                return reject("bad sample record")
            action = sample.get("action")
            direction = sample.get("direction_index")
            tick = sample.get("tick")
            key = (action, direction, tick)
            if (action not in ACTIONS or type(direction) is not int
                    or type(tick) is not int or key not in expected or key in got):
                return reject("unexpected/duplicate action or facing direction")
            filename = f"rare-composed-{ident}-{action.lower()}-{direction}-{tick}.png"
            dims = sample.get("image_size")
            sha = sample.get("sha256")
            if (sample.get("filename") != filename or filename in files
                    or not isinstance(sha, str)
                    or not re.fullmatch(r"[0-9a-f]{64}", sha)
                    or not isinstance(dims, list) or len(dims) != 2
                    or any(type(n) is not int or n < 2 or n > 4096 for n in dims)):
                return reject("invalid PNG filename/dimensions/hash")
            try:
                raw = (folder / filename).read_bytes()
            except OSError:
                return reject("missing composed PNG " + filename)
            if (len(raw) < 45 or len(raw) > 16 * 1024 * 1024
                    or raw[:8] != b"\x89PNG\r\n\x1a\n"
                    or raw[12:16] != b"IHDR"
                    or int.from_bytes(raw[8:12], "big") != 13
                    or list(struct.unpack(">II", raw[16:24])) != dims
                    or not raw.endswith(b"IEND\xaeB\x60\x82")
                    or hashlib.sha256(raw).hexdigest() != sha):
                return reject("PNG payload or sha mismatch " + filename)
            old = folder / f"rare-motion-{ident}-{action.lower()}-{direction}-{tick}.png"
            if old.is_file() and hashlib.sha256(old.read_bytes()).hexdigest() != sha:
                body_differences += 1
                row_differences += 1
            files.add(filename)
            got.add(key)
            total += 1
        if got != expected:
            complete = False
        if row_differences:
            variants_differing += 1
    if seen != set(TARGETS):
        return reject("missing variant")
    if files != {p.name for p in folder.glob("rare-composed-*.png")}:
        return reject("unexpected or stale composed PNG")
    return {
        **base,
        "status": ("composed_samples_ready_for_manual_review"
                   if complete and total == 96 and variants_differing == 4
                   else "partial_composed_evidence"),
        "verified_samples": total,
        "expected_full_samples": 96,
        "different_from_body_source": body_differences,
        "variants_different_from_body": variants_differing,
        "reason": "Requires manual head/hair/body, 8-direction and walk review; never auto-approved",
    }
