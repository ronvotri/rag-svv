"""Fail-closed integrity check for original-client rare NPC motion samples.

Images are evidence for human QA, never proof of correct eight-direction art,
a playable town placement, or permission to unlock a companion.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import struct

TARGETS = {
    "gunslinger": "Cole",
    "gunslinger_f": "Cole",
    "taekwon": "Haneul",
    "taekwon_f": "Haneul",
}
ACTIONS = {"PC_IDLE": 1, "PC_WALK": 2}


def validate_motion_frames(folder) -> dict:
    folder = Path(folder)
    base = {
        "approved_for_town": False,
        "animation_verified": False,
        "directions_verified": False,
        "manual_art_identity_qa": "pending",
    }

    def reject(reason):
        return {**base, "status": "invalid_motion_evidence",
                "verified_samples": 0, "reason": reason}

    manifest = folder / "RARE_NPC_MOTION.json"
    if not manifest.is_file():
        return reject("missing motion manifest")
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return reject("invalid motion JSON")
    if (not isinstance(payload, dict)
            or payload.get("source") != "recovered_original_RoVisual_motion_probe"
            or payload.get("scope") != "offmap_qa_only"
            or payload.get("approved_for_town") is not False
            or payload.get("animation_verified") is not False
            or payload.get("directions_verified") is not False):
        return reject("unsafe motion manifest or approval flag")
    entries = payload.get("entries")
    if not isinstance(entries, list) or len(entries) != len(TARGETS):
        return reject("expected exactly four Cole/Haneul sprite records")
    seen = set()
    used_files = set()
    observed_walk_changes = 0
    observed_idle_direction_variants = 0
    completed = True
    sample_count = 0
    for row in entries:
        if not isinstance(row, dict):
            return reject("invalid sprite record")
        sprite_id = row.get("sprite_id")
        if sprite_id not in TARGETS or sprite_id in seen:
            return reject("unexpected or duplicate motion sprite ID")
        seen.add(sprite_id)
        if row.get("npc") != TARGETS[sprite_id]:
            return reject("incorrect NPC and sprite pairing")
        present = row.get("actions_present")
        if (not isinstance(present, dict) or set(present) != set(ACTIONS)
                or any(type(present[a]) is not bool for a in ACTIONS)):
            return reject("invalid action availability metadata")
        samples = row.get("samples")
        if not isinstance(samples, list):
            return reject("missing motion samples list")
        expected_frames = {
            (action, direction, tick)
            for action, ticks in ACTIONS.items() if present[action]
            for direction in range(8) for tick in range(ticks)
        }
        received = {}
        for sample in samples:
            if not isinstance(sample, dict):
                return reject("invalid sample record")
            action = sample.get("action")
            direction = sample.get("direction_index")
            tick = sample.get("tick")
            key = (action, direction, tick)
            if (action not in ACTIONS or type(direction) is not int
                    or type(tick) is not int or key not in expected_frames
                    or key in received):
                return reject("unexpected or duplicate action/direction/time sample")
            filename = ("rare-motion-" + sprite_id + "-" + action.lower() +
                        "-" + str(direction) + "-" + str(tick) + ".png")
            digest = sample.get("sha256")
            dims = sample.get("image_size")
            if (sample.get("filename") != filename or filename in used_files
                    or not isinstance(digest, str)
                    or re.fullmatch(r"[0-9a-f]{64}", digest) is None
                    or not isinstance(dims, list) or len(dims) != 2
                    or any(type(v) is not int or v < 2 or v > 4096 for v in dims)):
                return reject("invalid file identity, digest or dimensions")
            try:
                raw = (folder / filename).read_bytes()
            except OSError:
                return reject("missing motion PNG: " + filename)
            if (not 45 <= len(raw) <= 16 * 1024 * 1024
                    or not raw.startswith(b"\\x89PNG\\r\\n\\x1a\\n")
                    or raw[12:16] != b"IHDR"
                    or int.from_bytes(raw[8:12], "big") != 13
                    or list(struct.unpack(">II", raw[16:24])) != dims
                    or not raw.endswith(b"IEND\\xaeB\\x60\\x82")
                    or hashlib.sha256(raw).hexdigest() != digest):
                return reject("PNG payload/hash disagree: " + filename)
            used_files.add(filename)
            received[key] = digest
            sample_count += 1
        if set(received) != expected_frames:
            completed = False
        if not all(present.values()):
            completed = False
        for direction in range(8):
            first = received.get(("PC_WALK", direction, 0))
            second = received.get(("PC_WALK", direction, 1))
            if first is not None and second is not None and first != second:
                observed_walk_changes += 1
        idle = {received.get(("PC_IDLE", direction, 0))
                for direction in range(8)}
        idle.discard(None)
        if len(idle) > 1:
            observed_idle_direction_variants += 1
    if seen != set(TARGETS):
        return reject("missing expected source variant")
    if used_files != {p.name for p in folder.glob("rare-motion-*.png")}:
        return reject("unexpected or stale motion PNG in archive")
    return {
        **base,
        "status": ("motion_samples_ready_for_manual_review" if completed
                   else "partial_motion_evidence"),
        "verified_samples": sample_count,
        "expected_full_samples": 96,
        "observed_walk_frame_changes": observed_walk_changes,
        "sprites_with_idle_direction_variation": observed_idle_direction_variants,
        "reason": "Image samples require manual 8-direction and Idle/Walk review; not approved",
    }
