"""Preflight checks for wave-2 offline companions; no publisher assets."""
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "original-addons/offline_assistant.gd"


class FriendWave2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = SOURCE.read_text(encoding="utf-8")

    def test_all_four_profiles_have_distinct_dialogue_and_roles(self):
        names = {"archer": "Elowen", "thief": "Riku", "merchant": "Mino", "novice": "Nao"}
        for job, name in names.items():
            with self.subTest(job=job):
                line = next(row for row in self.script.splitlines() if row.startswith('\t"' + job + '":'))
                self.assertIn('"name": "' + name + '"', line)
                self.assertIn('"intro": "' + name + ': ', line)
                self.assertIn('"role": ', line)
                self.assertIn('"quest": ', line)
        self.assertIn('if profile.has("intro"):', self.script)
        self.assertIn('str(profile["intro"]).trim_prefix(', self.script)
        self.assertIn('friend_details.bbcode_enabled = true', self.script)
        self.assertIn('description += "\\n[color=#b3f3d0][b]Nhiệm vụ kết bạn', self.script)

    def test_recruitment_gate_save_and_full_party_remain_unchanged(self):
        self.assertIn('Save.setting("svv_offline_friends", [])', self.script)
        self.assertIn('Save.set_setting("svv_friend_quests", quests)', self.script)
        self.assertIn('Save.set_setting("svv_offline_party", party)', self.script)
        self.assertIn('party.size() >= 3', self.script)
        self.assertIn('elif selected_class != "acolyte" and not unlocked.has("acolyte")', self.script)
        self.assertNotIn('"\\n"\tif profile.has(', self.script)

    def test_no_unverified_city_claim_for_new_four(self):
        for job in ("archer", "thief", "merchant", "novice"):
            line = next(row for row in self.script.splitlines() if row.startswith('\t"' + job + '":'))
            self.assertNotIn('"location":', line)


if __name__ == "__main__":
    unittest.main()
