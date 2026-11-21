"""Protect offline simulation from pretending to be live multiplayer."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVENTS = ROOT / "original-addons/offline_events.gd"
INSTALLER = ROOT / "tools/install-original-assistant.py"


class OfflineEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = EVENTS.read_text("utf-8")
        cls.installer = INSTALLER.read_text("utf-8")

    def test_training_festival_world_boss_are_local_only(self):
        for mode in ("training", "festival", "world_boss"):
            with self.subTest(mode=mode):
                self.assertIn('"' + mode + '"', self.code)
        for blocked in ("Leaderboard.", "EosNet.", "RelayNet.",
                        "WebSocketPeer", "HTTPClient", "HTTPRequest"):
            self.assertNotIn(blocked, self.code)
        self.assertIn("SVVAssistant._party_members()", self.code)
        self.assertIn("SVVCompanionTown._town()", self.code)
        self.assertIn("không tính bảng xếp hạng online", self.code)
        self.assertIn("Không ảnh hưởng thưởng hoặc bảng hạng chính thức", self.code)

    def test_only_local_record_keys_and_preserved_official_save(self):
        self.assertIn('"svv_local_world_boss_best"', self.code)
        self.assertIn('"svv_local_festival_best"', self.code)
        self.assertIn('"svv_local_training_best"', self.code)
        self.assertIn("Save.set_setting(key, achieved)", self.code)
        self.assertNotIn("Save.reset_profile(", self.code)
        self.assertNotIn("Save.reset_progress(", self.code)

    def test_installer_registers_offline_event_addon(self):
        self.assertIn('event_source = source.parent / "offline_events.gd"', self.installer)
        self.assertIn('SVVOfflineEvents="*res://addons/svv_offline/offline_events.gd"', self.installer)


if __name__ == "__main__":
    unittest.main()
