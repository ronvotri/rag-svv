import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "rare_job_motion_report", ROOT / "tools/rare_job_motion_report.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def png():
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff))
    raw_rows = (b"\\x00" + b"\\xff\\x00\\x00\\xff" * 2) * 2
    return (b"\\x89PNG\\r\\n\\x1a\\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 6, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(raw_rows)) + chunk(b"IEND", b""))


class MotionEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.raw = png()
        entries = []
        for sprite_id, npc in checker.TARGETS.items():
            samples = []
            for action, ticks in checker.ACTIONS.items():
                for direction in range(8):
                    for tick in range(ticks):
                        filename = ("rare-motion-" + sprite_id + "-" +
                                    action.lower() + "-" + str(direction) +
                                    "-" + str(tick) + ".png")
                        (self.root / filename).write_bytes(self.raw)
                        samples.append({
                            "action": action, "direction_index": direction,
                            "tick": tick, "filename": filename,
                            "sha256": hashlib.sha256(self.raw).hexdigest(),
                            "image_size": [2, 2],
                        })
            entries.append({
                "npc": npc, "sprite_id": sprite_id,
                "actions_present": {"PC_IDLE": True, "PC_WALK": True},
                "samples": samples,
            })
        self.manifest = {
            "source": "recovered_original_RoVisual_motion_probe",
            "scope": "offmap_qa_only",
            "approved_for_town": False, "animation_verified": False,
            "directions_verified": False, "entries": entries,
        }
        self.write()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self):
        (self.root / "RARE_NPC_MOTION.json").write_text(
            json.dumps(self.manifest), encoding="utf-8")

    def test_all_samples_can_be_reviewed_but_never_approved(self):
        checked = checker.validate_motion_frames(self.root)
        self.assertEqual(checked["status"], "motion_samples_ready_for_manual_review")
        self.assertEqual(checked["verified_samples"], 96)
        self.assertEqual(checked["observed_walk_frame_changes"], 0)
        self.assertFalse(checked["approved_for_town"])
        self.assertFalse(checked["animation_verified"])
        self.assertFalse(checked["directions_verified"])

    def test_bad_manifest_or_approval_flags_rejected(self):
        self.manifest["approved_for_town"] = True
        self.write()
        self.assertEqual(checker.validate_motion_frames(self.root)["status"],
                         "invalid_motion_evidence")
        self.manifest["approved_for_town"] = False
        self.manifest["entries"][0]["npc"] = "Lumi"
        self.write()
        self.assertEqual(checker.validate_motion_frames(self.root)["status"],
                         "invalid_motion_evidence")

    def test_missing_or_modified_png_rejected(self):
        filename = self.manifest["entries"][0]["samples"][0]["filename"]
        (self.root / filename).write_bytes(self.raw[:-8])
        self.assertEqual(checker.validate_motion_frames(self.root)["status"],
                         "invalid_motion_evidence")
        (self.root / filename).unlink()
        self.assertEqual(checker.validate_motion_frames(self.root)["status"],
                         "invalid_motion_evidence")

    def test_partial_action_is_not_approval(self):
        entry = self.manifest["entries"][0]
        entry["actions_present"]["PC_WALK"] = False
        entry["samples"] = [s for s in entry["samples"]
                            if s["action"] == "PC_IDLE"]
        for path in self.root.glob("rare-motion-" + entry["sprite_id"] + "-pc_walk-*.png"):
            path.unlink()
        self.write()
        checked = checker.validate_motion_frames(self.root)
        self.assertEqual(checked["status"], "partial_motion_evidence")
        self.assertFalse(checked["animation_verified"])

    def test_probe_uses_original_rovisual_and_remains_offmap(self):
        source = (ROOT / "original-addons/rare_job_motion.gd").read_text()
        runner = (ROOT / "original-addons/offline_visual.gd").read_text()
        installer = (ROOT / "tools/install-original-assistant.py").read_text()
        self.assertIn("RoAssets.sprite([sprite_id])", source)
        self.assertIn("visual.face(DIRECTIONS[direction_index])", source)
        self.assertIn("visual.play(int(constants[action_name]), true, true)", source)
        self.assertIn('"approved_for_town": false', source)
        self.assertNotIn("SVVCompanionTown._spawn_in_town", source)
        self.assertIn('await motion_helper.capture(folder)', runner)
        self.assertIn("shutil.copyfile(rare_motion, qa / rare_motion.name)", installer)


if __name__ == "__main__":
    unittest.main()
