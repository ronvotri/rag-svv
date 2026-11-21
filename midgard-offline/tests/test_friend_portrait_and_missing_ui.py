"""Regression checks for illustrated Friends List portraits and localized prose."""
from pathlib import Path
import hashlib
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "original-addons/friend_portraits.jpg"
GD = ROOT / "original-addons/offline_assistant.gd"
INSTALLER = ROOT / "tools/install-original-assistant.py"
BATCH = ROOT / "patches/vi-ui-batch-063.json"


class FriendPortraitAndTextTests(unittest.TestCase):
    def test_atlas_is_approved_jpeg(self):
        contents = ASSET.read_bytes()
        self.assertEqual(len(contents), 231582)
        self.assertEqual(hashlib.sha256(contents).hexdigest(),
                         "a4f8dd78ccf12fcdb5cab274e6d9ebb1c50b4281aea72252061d9a994857ea6f")
        self.assertEqual(contents[:3], bytes([0xff, 0xd8, 0xff]))

    def test_all_eleven_jobs_have_portraits_and_preserve_save_paths(self):
        script = GD.read_text("utf-8")
        jobs = ["acolyte", "swordsman", "mage", "archer", "thief",
                "merchant", "novice", "gunslinger", "taekwon", "ninja", "doram"]
        for job in jobs:
            self.assertIn('"' + job + '":', script)
        self.assertIn('var atlas := AtlasTexture.new()', script)
        self.assertIn('friend_portrait.texture = _portrait_texture(selected_class)', script)
        self.assertIn('var face := _portrait_view(job, 52)', script)
        self.assertIn('Save.set_setting("svv_offline_party", party)', script)
        self.assertIn('Save.set_setting("svv_friend_quests", quests)', script)
        installer = INSTALLER.read_text("utf-8")
        self.assertIn('shutil.copyfile(portraits, destination.parent / portraits.name)', installer)

    def test_telescope_and_world_boss_descriptions_are_translated(self):
        data = json.loads(BATCH.read_text("utf-8"))
        telescope = "Basic attack: +0.5 ranged reach per upgrade level;"
        boss = "An MVP for the whole community, open all week:"
        self.assertTrue(any(k.startswith(telescope) for k in data))
        self.assertTrue(any(k.startswith(boss) for k in data))
        for key, value in data.items():
            self.assertTrue(value.strip(), key)
            self.assertNotEqual(value, key, key)
        # Names of equipment/skills are deliberately preserved in English.
        self.assertNotIn("Telescope", data)
        self.assertNotIn("Emperium Festival", data)


if __name__ == "__main__":
    unittest.main()
