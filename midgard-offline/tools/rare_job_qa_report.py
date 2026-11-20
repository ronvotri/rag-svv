"""Fail-closed parser for Godot rare NPC sprite audit stdout.

This report is QA evidence, never a character unlock/placement approval.
"""
from __future__ import annotations
import json

PREFIX = "RARE_NPC_QA_JSON "
EXPECTED = {
    "gunslinger": ["gunslinger", "gunslinger_f"],
    "taekwon": ["taekwon", "taekwon_f"],
    "ninja": ["ninja", "ninja_f"],
    "doram": ["summoner", "summoner_f"],
}


def _unverified(reason: str) -> dict:
    return {
        "schema_version": 4,
        "status": "unverified",
        "reason": reason,
        "runtime_probe_completed": False,
        "approved_for_town": False,
        "jobs": {},
    }


def from_log(log: str) -> dict:
    matches = [line.split(PREFIX, 1)[1].strip() for line in log.splitlines()
               if PREFIX in line]
    if len(matches) != 1:
        return _unverified("expected exactly one rare NPC audit marker")
    try:
        payload = json.loads(matches[0])
    except (ValueError, TypeError):
        return _unverified("invalid audit JSON")
    if not isinstance(payload, dict):
        return _unverified("audit payload is not an object")
    if (payload.get("schema_version") != 4
            or payload.get("source") != "godot_recovered_original_runtime"
            or payload.get("all_jobs_approved") is not False):
        return _unverified("invalid audit schema or approval flag")
    jobs = payload.get("jobs")
    if not isinstance(jobs, dict) or set(jobs) != set(EXPECTED):
        return _unverified("missing or unexpected rare NPC job")
    for job, expected_ids in EXPECTED.items():
        value = jobs[job]
        if not isinstance(value, dict):
            return _unverified("invalid job entry: " + job)
        if (type(value.get("class_present")) is not bool
                or value.get("approved_for_town") is not False
                or value.get("alias_only") is not (job == "doram")):
            return _unverified("unsafe class/alias/approval state: " + job)
        rows = value.get("sprite_candidates")
        if not isinstance(rows, list) or [r.get("sprite_id") if isinstance(r, dict) else None for r in rows] != expected_ids:
            return _unverified("unexpected sprite IDs for: " + job)
        for row in rows:
            if any(type(row.get(flag)) is not bool for flag in ("found", "loadable", "renderable")):
                return _unverified("invalid sprite probe flags for: " + job)
            if (row["renderable"] and not row["loadable"]) or (row["loadable"] and not row["found"]):
                return _unverified("contradictory sprite probe flags for: " + job)
    return {
        "schema_version": 4,
        "status": "runtime_evidence_recorded",
        "runtime_probe_completed": True,
        "approved_for_town": False,
        "manual_art_identity_qa": "pending",
        "town_and_mobile_visual_qa": "pending",
        "jobs": jobs,
    }



def validate_visual_frames(folder) -> dict:
    """Validate 8 genuine exported PNGs and their fail-closed Godot manifest.

    This proves file integrity / consistent capture metadata, NOT that the
    artwork depicts the correct character or that animations are usable.
    """
    from pathlib import Path
    import struct
    import zlib

    expected = {
        "gunslinger": "Cole", "gunslinger_f": "Cole",
        "taekwon": "Haneul", "taekwon_f": "Haneul",
        "ninja": "Kira", "ninja_f": "Kira",
        "summoner": "Lumi", "summoner_f": "Lumi",
    }
    base = {
        "approved_for_town": False,
        "manual_art_identity_qa": "pending",
        "animation_verified": False,
        "directions_verified": False,
    }

    def reject(reason):
        return {**base, "status": "incomplete_frames", "verified_frames": 0, "reason": reason}

    def checked_png_size(path):
        raw = path.read_bytes()
        if not 45 <= len(raw) <= 16 * 1024 * 1024 or not raw.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("invalid PNG signature or file length")
        offset = 8
        size = None
        pixel_chunks = []
        found_end = False
        while offset < len(raw):
            if offset + 12 > len(raw):
                raise ValueError("truncated PNG chunk")
            length = int.from_bytes(raw[offset:offset + 4], "big")
            kind = raw[offset + 4:offset + 8]
            end = offset + 12 + length
            if end > len(raw):
                raise ValueError("truncated PNG payload")
            data = raw[offset + 8:offset + 8 + length]
            crc = int.from_bytes(raw[offset + 8 + length:end], "big")
            if zlib.crc32(kind + data) & 0xffffffff != crc:
                raise ValueError("PNG CRC mismatch")
            if size is None:
                if kind != b"IHDR" or length != 13:
                    raise ValueError("PNG missing IHDR")
                width, height, bits, kind_id, compression, filtering, interlace = struct.unpack(">IIBBBBB", data)
                if not (2 <= width <= 4096 and 2 <= height <= 4096
                        and bits in (8, 16) and kind_id in (0, 2, 4, 6)
                        and compression == filtering == interlace == 0):
                    raise ValueError("unsupported PNG dimensions or encoding")
                size = width, height, bits, kind_id
            elif kind == b"IDAT":
                pixel_chunks.append(data)
            elif kind == b"IEND":
                if length or end != len(raw):
                    raise ValueError("invalid PNG end")
                found_end = True
                break
            offset = end
        if not found_end or not pixel_chunks:
            raise ValueError("missing PNG pixels or end")
        width, height, bits, kind_id = size
        channels = {0: 1, 2: 3, 4: 2, 6: 4}[kind_id]
        expected_bytes = height * (1 + ((width * channels * bits + 7) // 8))
        if expected_bytes > 140 * 1024 * 1024:
            raise ValueError("oversized PNG pixels")
        decoder = zlib.decompressobj()
        decoded = decoder.decompress(b"".join(pixel_chunks), expected_bytes + 1)
        if (len(decoded) != expected_bytes or not decoder.eof
                or decoder.unconsumed_tail or decoder.unused_data):
            raise ValueError("PNG scanline data invalid")
        return width, height

    folder = Path(folder)
    manifest = folder / "RARE_NPC_VISUAL.json"
    if not manifest.is_file():
        return reject("missing source-frame manifest")
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError, OSError):
        return reject("invalid source-frame manifest")
    if (not isinstance(payload, dict)
            or payload.get("source") != "recovered_original_RoVisual_texture_frame"
            or payload.get("scope") != "visual_qa_only"
            or payload.get("approved_for_town") is not False
            or payload.get("animation_verified") is not False
            or payload.get("directions_verified") is not False):
        return reject("unsafe or unknown source-frame manifest")
    entries = payload.get("entries")
    if not isinstance(entries, list) or len(entries) != len(expected):
        return reject("expected exactly eight source-frame records")
    seen = set()
    for row in entries:
        if not isinstance(row, dict):
            return reject("invalid frame record")
        sprite_id = row.get("sprite_id")
        if sprite_id not in expected or sprite_id in seen:
            return reject("unexpected or duplicate sprite ID")
        seen.add(sprite_id)
        npc = expected[sprite_id]
        if (row.get("npc") != npc
                or row.get("candidate_alias_only") is not (npc == "Lumi")
                or row.get("saved") is not True
                or row.get("visible_content") is not True
                or row.get("filename") != "rare-frame-" + sprite_id + ".png"):
            return reject("unsafe sprite mapping, missing image or empty texture: " + sprite_id)
        dims = row.get("image_size")
        bounds = row.get("visible_bounds")
        if (not isinstance(dims, list) or len(dims) != 2
                or any(type(n) is not int or n < 2 for n in dims)
                or not isinstance(bounds, list) or len(bounds) != 4
                or any(type(n) is not int for n in bounds)
                or bounds[0] < 0 or bounds[1] < 0
                or bounds[2] <= 0 or bounds[3] <= 0
                or bounds[0] + bounds[2] > dims[0]
                or bounds[1] + bounds[3] > dims[1]):
            return reject("invalid visible bounds or dimensions: " + sprite_id)
        try:
            actual = checked_png_size(folder / row["filename"])
        except (ValueError, OSError, zlib.error):
            return reject("corrupt/missing PNG: " + sprite_id)
        if tuple(dims) != actual:
            return reject("PNG and manifest dimensions disagree: " + sprite_id)
    if seen != set(expected):
        return reject("source-frame inventory incomplete")
    return {
        **base,
        "status": "frames_ready_for_manual_review",
        "verified_frames": len(expected),
        "reason": "integrity checked; character identity and animations NOT approved",
    }


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logfile", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = from_log(args.logfile.read_text(encoding="utf-8", errors="replace"))
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
