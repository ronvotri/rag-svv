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

    def test_original_npc_looks_are_distinct_and_town_idle_is_stable(self):
        self.assertIn('const NPC_LOOK := {', self.npcs)
        for job, gender in (("acolyte", "f"), ("swordsman", "m"), ("mage", "f"),
                            ("archer", "f"), ("thief", "m"), ("merchant", "m")):
            self.assertIn('"' + job + '": {"gender": "' + gender + '", "hair":', self.npcs)
        self.assertIn('var style: Dictionary = NPC_LOOK[current]', self.npcs)
        self.assertIn('var gender: String = str(style["gender"])', self.npcs)
        self.assertIn('RoAssets.has_sprite(key) and not used.has(key)', self.npcs)
        self.assertIn('RoAssets.has_palette(', self.npcs)
        self.assertIn('visual.process_mode = Node.PROCESS_MODE_DISABLED', self.npcs)
        self.assertIn('uses existing unique native head', self.smoke)
        self.assertIn('matches portrait gender', self.smoke)
        self.assertIn('composite frame stable', self.smoke)
        self.assertIn('visual.face(Vector3(0.0, 0.0, 1.0))', self.npcs)
        self.assertIn('visual.set_process(false)', self.npcs)
        self.assertIn('visual.set_physics_process(false)', self.npcs)
        self.assertNotIn('var look := {"gender": gender, "hair": 2, "hair_color": 0, "cloth": 0}', self.npcs)

    def test_new_characters_use_original_sprites_not_placeholder_art(self):
        for string in ('"swordsman": ["swordsman", "swordsman_m"]', '"mage": ["mage_f"]',
                       "RoAssets.has_sprite(sprite_id)", "RoAssets.styled_character(",
                       "RoVisual.new()", "parent.add_child(visual)"):
            self.assertIn(string, self.npcs)
        self.assertNotIn('"swordsman_f"', self.npcs)
        self.assertNotIn('"mage_m"', self.npcs)
        self.assertNotIn("Emoji", self.npcs)
        self.assertNotIn("SpriteFrames.new()", self.npcs)
        self.assertNotIn("Image.create(", self.npcs)
        self.assertNotIn("RoAssets.sprite([sprite_id])", self.npcs)
        self.assertIn('if composed == null:', self.npcs)
        self.assertIn('missing_sprites[job] = true', self.npcs)
        self.assertIn('nameplate.position = Vector3(0.0, 1.65, 0.0)', self.npcs)

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

    def test_companions_are_scoped_to_verified_prontera_only(self):
        self.assertIn('get_meta("svv_offline_town_place", "")', self.npcs)
        self.assertIn('!= "prontera":', self.npcs)
        self.assertIn('SVVCompanionTown._town() == null', self.smoke)
        self.assertIn('SVVCompanionTown._town() == actual_town', self.smoke)

    def test_missing_original_sprite_retries_without_cloning_a_live_npc(self):
        self.assertIn("sprite_retry_seconds += frame_seconds", self.npcs)
        self.assertIn("if sprite_retry_seconds >= 4.0:", self.npcs)
        self.assertIn("if is_instance_valid(npc_visuals.get(job)):", self.npcs)
        self.assertIn("missing_sprites.erase(job)", self.npcs)
        self.assertIn("sprite_retry_seconds = 0.0", self.npcs)
        self.assertIn("SVVCompanionTown.sprite_retry_seconds = 4.0", self.smoke)
        self.assertIn('SVVCompanionTown._process(0.35)', self.smoke)
        self.assertIn("SVVCompanionTown._unhandled_input(pointer_event)", self.smoke)
        self.assertIn('for pointer_kind in ["mouse", "touch"]:', self.smoke)

    def test_cross_city_transition_cleans_live_npcs_and_dialogue(self):
        self.assertIn('world.set_meta("svv_offline_town_place", "payon")', self.smoke)
        self.assertIn("cross-city transition removes old companion visuals", self.smoke)
        self.assertIn("cross-city transition closes old companion dialogue", self.smoke)
        self.assertIn("cross-city transition hides fallback buttons", self.smoke)
        self.assertIn("returning to Prontera restores exactly five companion NPCs", self.smoke)

    def test_wave_two_profiles_ready_but_town_spawn_allowlist_unchanged(self):
        self.assertIn('const JOBS := ["swordsman", "mage", "archer", "thief", "merchant"]', self.npcs)
        for job, name in (("archer", "Elowen"), ("thief", "Riku"),
                          ("merchant", "Mino"), ("novice", "Nao")):
            self.assertIn('"' + job + '": "' + name + '"', self.npcs)
            self.assertIn('"' + job + '": {', self.assistant)
            self.assertIn('"' + job + '": "' + name + ':', self.npcs)
        self.assertIn('NPC_GREETINGS.get(selected_job', self.npcs)
        self.assertIn('"archer": Vector3(', self.npcs)
        self.assertIn('"thief": Vector3(', self.npcs)
        self.assertIn('"merchant": Vector3(', self.npcs)
        self.assertNotIn('"novice": Vector3(', self.npcs)

    def test_visual_qa_captures_real_town_dialogues_without_spawning_wave_two(self):
        visual = (ROOT / "original-addons/offline_visual.gd").read_text(encoding="utf-8")
        self.assertIn('await snap("town-dialog-" + job)', visual)
        self.assertIn('for job in ["swordsman", "mage", "archer", "thief", "merchant"]:', visual)
        self.assertIn('SVVCompanionTown._show_dialog(job)', visual)
        self.assertIn('SVVCompanionTown._close_dialog()', visual)
        self.assertIn('VISUAL_QA WAVE2_SPRITE ', visual)
        self.assertNotIn('"novice": Vector3(', self.npcs)

    def test_installed_for_each_original_client_build_and_runtime_qa(self):
        self.assertIn('companions_source = source.parent / "companions_town.gd"', self.installer)
        self.assertIn('SVVCompanionTown="*res://addons/svv_offline/companions_town.gd"', self.installer)
        self.assertIn('SVVCompanionTown._spawn_in_town(actual_town)', self.smoke)
        self.assertIn('npc.sprite.texture != null', self.smoke)
        self.assertIn('Alden town NPC and Friends List share quest state', self.smoke)


    def test_wave_two_sprite_candidates_and_staged_prontera_npcs(self):
        self.assertIn('const JOBS := ["swordsman", "mage", "archer", "thief", "merchant"]', self.npcs)
        for candidate in ('"archer": ["archer_f"]', '"thief": ["thief", "thief_m"]',
                          '"merchant": ["merchant", "merchant_m"]', '"novice": ["novice_f", "novice_m"]'):
            self.assertIn(candidate, self.npcs)
        self.assertIn('job + " original Ragnarok sprite renders for later town placement"', self.smoke)
        self.assertIn('OFFLINE_QA WAVE2_SPRITE ', self.smoke)
        self.assertIn('"novice": ["novice_f", "novice_m"]', self.npcs)
        self.assertNotIn('"super_novice_f"', self.npcs)
        self.assertNotIn('"super_novice",', self.npcs)
        self.assertIn("Nao never uses Super Novice substitute", self.smoke)
        self.assertIn("OFFLINE_QA NAO_VISUAL basic Novice ", self.smoke)


    def test_wave_six_spatial_and_mobile_visual_audits(self):
        # A green headless build alone cannot sign off map props or walkable lanes.
        self.assertIn("OFFLINE_QA NPC_PLACEMENT ", self.smoke)
        self.assertIn("screen target remains near town viewport", self.smoke)
        self.assertIn(" has space from Mira patrol", self.smoke)
        self.assertIn(" has space from ", self.smoke)
        visual = (ROOT / "original-addons/offline_visual.gd").read_text(encoding="utf-8")
        self.assertIn("Vector2i(390, 844)", visual)
        self.assertIn("Vector2i(844, 390)", visual)
        self.assertIn('await snap("town-npcs-"', visual)
        self.assertIn("VISUAL_QA NPC_FRAME", visual)
        self.assertNotIn('"novice": Vector3(', self.npcs)

if __name__ == "__main__":
    unittest.main()
