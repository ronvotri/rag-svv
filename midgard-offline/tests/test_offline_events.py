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

    def test_offline_modes_have_original_style_illustrated_cards(self):
        for marker in ('func _mode_icon(mode: String)', 'ImageTexture.create_from_image(pixels)',
                       'option.icon = _mode_icon(str(key))', 'mode_buttons[str(key)] = option',
                       'func _style_mode_button(button: Button, active: bool)',
                       'for key in mode_buttons:', 'meter.hide()', 'meter.show()'):
            self.assertIn(marker, self.code)
        for mode in ('training', 'festival', 'world_boss'):
            self.assertIn('"' + mode + '"', self.code)
        self.assertNotIn('option.custom_minimum_size.y = 40', self.code)

    def test_offline_launcher_does_not_overlap_friends_and_save(self):
        self.assertIn('var friends_x: float = maxf(8.0, screen.x - 12.0 - friend_width - 8.0 - save_width)', self.code)
        self.assertIn('var offline_x: float = friends_x - offline_width - 8.0', self.code)
        self.assertIn('if offline_x >= 8.0:', self.code)
        self.assertIn('Vector2(8.0, bar_y + 44.0)', self.code)
        self.assertIn('_style_launcher_button(open_button)', self.code)
        self.assertIn('var bar_y: float = 68.0 if OS.has_feature("web") else (56.0 if narrow else 10.0)', self.code)
        # Keep all three launchers on the same Web row even at desktop widths.
        for addon, marker in (("offline_assistant.gd", "toolbar_y"), ("web_save_manager.gd", "toolbar_y")):
            source = (EVENTS.parent / addon).read_text("utf-8")
            self.assertIn(f'var {marker}: float = 68.0 if OS.has_feature("web")', source)
        # Desktop: the illustrated simulation launcher must end before Friends.
        width = 1280
        friend_width, save_width, offline_width = 132, 188, 164
        friends_x = width - 12 - friend_width - 8 - save_width
        offline_x = friends_x - offline_width - 8
        self.assertGreaterEqual(offline_x, 8)
        self.assertLessEqual(offline_x + offline_width + 8, friends_x)

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
