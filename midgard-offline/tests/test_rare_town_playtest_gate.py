"""Wave 28: the playable Town QA path must remain strictly opt-in."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RareTownPlaytestGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qa = (ROOT / "original-addons" / "rare_town_qa.gd").read_text(encoding="utf-8")
        cls.install = (ROOT / "tools" / "install-original-assistant.py").read_text(encoding="utf-8")
        cls.build = (ROOT / "tools" / "cloud-build-original.py").read_text(encoding="utf-8")

    def test_both_qa_flags_required(self):
        self.assertIn('return "--offline-test" in args and "--rare-town-qa" in args', self.qa)
        self.assertIn("set_process(false)", self.qa)
        self.assertIn("set_process_unhandled_input(false)", self.qa)

    def test_not_recruitable_or_saved_by_visual_probe(self):
        for forbidden in ("Save.set_setting", "Save.flush", "_friend_action_pressed",
                          "_unlocked_friends", "SVVCompanionTown.JOBS"):
            self.assertNotIn(forbidden, self.qa)
        self.assertIn("RoAssets.styled_character(", self.qa)
        self.assertIn('get_meta("svv_offline_town_place", "")', self.qa)
        self.assertIn('"prontera"', self.qa)
        self.assertIn("func _clear_world", self.qa)

    def test_only_cole_and_haneul_placed(self):
        self.assertIn('"name": "Cole"', self.qa)
        self.assertIn('"name": "Haneul"', self.qa)
        for forbidden in ('"name": "Kira"', '"name": "Lumi"', '"name": "Nao"'):
            self.assertNotIn(forbidden, self.qa)

    def test_installer_and_windows_launcher(self):
        self.assertIn('rare_town_qa.gd', self.install)
        self.assertIn('SVVRareTownQA="*res://addons/svv_offline/rare_town_qa.gd"', self.install)
        self.assertIn("TEST-PRONTERA-NPC-QA.cmd", self.build)
        self.assertIn("-- --offline-test --rare-town-qa", self.build)
        self.assertIn('archive_folder(folder, output / (folder.name + ".zip"))', self.build)


if __name__ == "__main__":
    unittest.main()
