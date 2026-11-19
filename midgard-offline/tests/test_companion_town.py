"""Static guard rails for the additive Alden/Eira Godot town encounters.

Real RoVisual construction, textures, and input are checked by offline_smoke.gd
when the official PCK has been recovered on a GitHub Actions runner.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class NativeCompanionTownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.npcs = (ROOT / "original-addons/companions_town.gd").read_text(encoding="utf-8")
        cls.installer = (ROOT / "tools/install-original-assistant.py").read_text(encoding="utf-8")
        cls.assistant = (ROOT / "original-addons/offline_assistant.gd").read_text(encoding="utf-8")
        cls.smoke = (ROOT / "original-addons/offline_smoke.gd").read_text(encoding="utf-8")

    def test_new_characters_use_original_sprites_not_placeholder_art(self):
        for string in ('"swordsman_m"', '"swordsman_f"', '"mage_f"', '"mage_m"',
                       "RoAssets.has_sprite(sprite_id)", "RoAssets.sprite([sprite_id])",
                       "RoVisual.new()", "parent.add_child(visual)"):
            self.assertIn(string, self.npcs)
        self.assertNotIn("Emoji", self.npcs)
        self.assertNotIn("SpriteFrames.new()", self.npcs)
        self.assertNotIn("Image.create(", self.npcs)

    def test_companions_live_only_in_actual_town_not_lobby_or_battle(self):
        self.assertIn('world.running', self.npcs)
        self.assertIn('candidate.is_inside_tree()', self.npcs)
        self.assertIn('parent.npc_node("kafra")', self.npcs)
        self.assertIn('if current_town != town_node:', self.npcs)
        self.assertIn('func _clear_world()', self.npcs)
        self.assertIn('if dialog.visible and current_town == null:', self.npcs)

    def test_town_and_friends_list_share_authoritative_recruitment(self):
        self.assertIn('SVVAssistant._friend_action_pressed()', self.npcs)
        self.assertIn('SVVAssistant._quest_progress(selected_job)', self.npcs)
        self.assertIn('SVVAssistant._unlocked_friends()', self.npcs)
        self.assertIn('SVVAssistant._party_members()', self.npcs)
        self.assertIn('party.size() >= 3', self.npcs)
        self.assertIn('if not unlocked.has("acolyte"):', self.npcs)
        self.assertIn('"swordsman": {"name": "Alden"', self.assistant)
        self.assertIn('"mage": {"name": "Eira"', self.assistant)
        self.assertIn('world.coop_classes.assign(party)', self.assistant)

    def test_installed_for_each_original_client_build_and_runtime_qa(self):
        self.assertIn('companions_source = source.parent / "companions_town.gd"', self.installer)
        self.assertIn('SVVCompanionTown="*res://addons/svv_offline/companions_town.gd"', self.installer)
        self.assertIn('SVVCompanionTown._spawn_in_town(actual_town)', self.smoke)
        self.assertIn('npc.sprite.texture != null', self.smoke)
        self.assertIn('Alden town NPC and Friends List share quest state', self.smoke)


if __name__ == "__main__":
    unittest.main()
