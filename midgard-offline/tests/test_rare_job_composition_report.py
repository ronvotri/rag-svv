"""Composed sprite evidence must be fail-closed and independently hashed."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "rare_job_composition_report", ROOT / "tools/rare_job_composition_report.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class ComposedSpriteValidationTests(unittest.TestCase):
    def test_missing_manifest_cannot_approve_town(self):
        with tempfile.TemporaryDirectory() as temp:
            report = helper.validate_composed_frames(temp)
            self.assertEqual(report["status"], "invalid_composed_evidence")
            self.assertFalse(report["approved_for_town"])
            self.assertFalse(report["head_hair_verified"])

    def test_forged_approval_flag_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "RARE_NPC_COMPOSED.json").write_text(
                json.dumps({"source": helper.SOURCE, "scope": "offmap_qa_only",
                            "factory": "RoAssets.styled_character",
                            "approved_for_town": True, "animation_verified": False,
                            "directions_verified": False, "head_hair_verified": False,
                            "entries": []}), encoding="utf-8")
            report = helper.validate_composed_frames(root)
            self.assertEqual(report["status"], "invalid_composed_evidence")
            self.assertFalse(report["approved_for_town"])

    def test_missing_pngs_do_not_count_as_success(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            entries = []
            for ident, (name, body, gender) in helper.TARGETS.items():
                entries.append({"npc": name, "sprite_id": ident, "body": body,
                                "gender": gender, "factory": "RoAssets.styled_character",
                                "actions_present": {"PC_IDLE": True, "PC_WALK": True},
                                "samples": []})
            (root / "RARE_NPC_COMPOSED.json").write_text(
                json.dumps({"source": helper.SOURCE, "scope": "offmap_qa_only",
                            "factory": "RoAssets.styled_character",
                            "approved_for_town": False, "animation_verified": False,
                            "directions_verified": False, "head_hair_verified": False,
                            "entries": entries}), encoding="utf-8")
            report = helper.validate_composed_frames(root)
            self.assertEqual(report["status"], "partial_composed_evidence")
            self.assertEqual(report["verified_samples"], 0)
            self.assertFalse(report["head_hair_verified"])


if __name__ == "__main__":
    unittest.main()
