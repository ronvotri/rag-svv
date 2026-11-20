import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rare_job_qa_report", ROOT / "tools/rare_job_qa_report.py")
reporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reporter)


def sample():
    jobs = {}
    for job, candidates in reporter.EXPECTED.items():
        jobs[job] = {
            "class_present": job == "gunslinger",
            "sprite_candidates": [
                {"sprite_id": candidate, "found": True, "loadable": True, "renderable": True}
                for candidate in candidates
            ],
            "alias_only": job == "doram",
            "approved_for_town": False,
        }
    return {
        "schema_version": 4, "source": "godot_recovered_original_runtime",
        "jobs": jobs, "all_jobs_approved": False,
    }


def log(data):
    return "Godot booted\nRARE_NPC_QA_JSON " + json.dumps(data) + "\nOFFLINE_QA COMPLETE failures=0\n"


class RareNpcPreflight(unittest.TestCase):
    def test_source_filenames_are_exact_from_build_309(self):
        self.assertEqual(reporter.EXPECTED["gunslinger"], ["gunslinger", "gunslinger_f"])
        self.assertEqual(reporter.EXPECTED["taekwon"], ["taekwon", "taekwon_f"])
        self.assertEqual(reporter.EXPECTED["ninja"], ["ninja", "ninja_f"])
        self.assertEqual(reporter.EXPECTED["doram"], ["summoner", "summoner_f"])
        self.assertNotIn("novice", reporter.EXPECTED)

    def test_valid_runtime_evidence_still_does_not_approve_town(self):
        report = reporter.from_log(log(sample()))
        self.assertEqual(report["status"], "runtime_evidence_recorded")
        self.assertTrue(report["runtime_probe_completed"])
        self.assertFalse(report["approved_for_town"])
        self.assertEqual(report["manual_art_identity_qa"], "pending")
        self.assertEqual(report["town_and_mobile_visual_qa"], "pending")

    def test_missing_duplicate_or_broken_logs_fail_closed(self):
        self.assertFalse(reporter.from_log("Godot started")["runtime_probe_completed"])
        self.assertFalse(reporter.from_log(log(sample()) + log(sample()))["runtime_probe_completed"])
        self.assertFalse(reporter.from_log("RARE_NPC_QA_JSON {broken")["runtime_probe_completed"])

    def test_unexpected_candidate_or_job_fails_closed(self):
        data = sample()
        data["jobs"]["doram"]["sprite_candidates"][0]["sprite_id"] = "doram"
        self.assertFalse(reporter.from_log(log(data))["runtime_probe_completed"])
        data = sample()
        del data["jobs"]["taekwon"]
        self.assertFalse(reporter.from_log(log(data))["runtime_probe_completed"])

    def test_contradictory_flags_fail_closed(self):
        data = sample()
        data["jobs"]["ninja"]["sprite_candidates"][0]["loadable"] = False
        self.assertFalse(reporter.from_log(log(data))["runtime_probe_completed"])
        data = sample()
        data["jobs"]["ninja"]["sprite_candidates"][0]["found"] = False
        self.assertFalse(reporter.from_log(log(data))["runtime_probe_completed"])

    def test_no_job_or_alias_can_be_approved_by_a_filename(self):
        data = sample()
        data["jobs"]["gunslinger"]["approved_for_town"] = True
        self.assertFalse(reporter.from_log(log(data))["runtime_probe_completed"])
        data = sample()
        data["jobs"]["doram"]["alias_only"] = False
        self.assertFalse(reporter.from_log(log(data))["runtime_probe_completed"])
        data = sample()
        data["all_jobs_approved"] = True
        self.assertFalse(reporter.from_log(log(data))["runtime_probe_completed"])

    def test_runtime_probe_is_qa_only_and_installed_in_private_project(self):
        addon = (ROOT / "original-addons/rare_job_asset_audit.gd").read_text(encoding="utf-8")
        installer = (ROOT / "tools/install-original-assistant.py").read_text(encoding="utf-8")
        smoke = (ROOT / "original-addons/offline_smoke.gd").read_text(encoding="utf-8")
        cloud = (ROOT / "tools/cloud-build-original.py").read_text(encoding="utf-8")
        town = (ROOT / "original-addons/companions_town.gd").read_text(encoding="utf-8")
        self.assertIn("RARE_NPC_QA_JSON ", addon)
        self.assertIn('GameData.CLASSES.has(job)', addon)
        self.assertIn("RoAssets.has_sprite(sprite_id)", addon)
        self.assertIn("preview.sprite.texture != null", addon)
        self.assertIn('shutil.copyfile(rare_audit, qa / rare_audit.name)', installer)
        self.assertIn('rare_audit.run(preview_root)', smoke)
        self.assertIn('RARE_JOB_QA.json', cloud)
        self.assertIn('const JOBS := ["swordsman", "mage", "archer", "thief", "merchant"]', town)
        self.assertNotIn('"gunslinger": Vector3(', town)
        self.assertNotIn('"doram": Vector3(', town)

    def test_rare_sprite_frames_are_visual_qa_only(self):
        visual = (ROOT / "original-addons/rare_job_visual.gd").read_text(encoding="utf-8")
        visual_runner = (ROOT / "original-addons/offline_visual.gd").read_text(encoding="utf-8")
        installer = (ROOT / "tools/install-original-assistant.py").read_text(encoding="utf-8")
        cloud = (ROOT / "tools/cloud-build-original.py").read_text(encoding="utf-8")
        workflow = (ROOT.parent / ".github/workflows/original-client.yml").read_text(encoding="utf-8")
        for name in ("gunslinger", "taekwon", "ninja", "summoner"):
            self.assertIn('"' + name + '"', visual)
            self.assertIn('"' + name + '_f"', visual)
        self.assertIn('"approved_for_town": false', visual)
        self.assertIn('"animation_verified": false', visual)
        self.assertIn("visual.sprite.texture.get_image()", visual)
        self.assertIn("RARE_NPC_VISUAL.json", visual)
        self.assertIn('rare_visual.capture(folder)', visual_runner)
        self.assertIn('shutil.copyfile(rare_visual, qa / rare_visual.name)', installer)
        self.assertIn("Rare-NPC-Sprite-QA.zip", cloud)
        self.assertIn('"rare_job_visual_qa": rare_visual_qa', cloud)
        self.assertIn("rare-npc-source-sprite-QA", workflow)
        self.assertIn("retention-days: 7", workflow)


if __name__ == "__main__":
    unittest.main()
