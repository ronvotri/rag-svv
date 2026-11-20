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
