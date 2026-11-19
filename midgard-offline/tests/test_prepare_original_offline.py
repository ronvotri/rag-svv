"""Regressions for the authored native Godot offline party bootstrap."""
from pathlib import Path
import importlib.util
import unittest

module_path = Path(__file__).resolve().parents[1] / "tools/prepare-original-offline.py"
spec = importlib.util.spec_from_file_location("prepare_original_offline", module_path)
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class OriginalPartyBootstrap(unittest.TestCase):
    def test_only_recruited_friends_can_enter_new_run(self):
        body = prepare.offline_party_bootstrap()
        self.assertIn('Save.setting("svv_offline_party", [])', body)
        self.assertIn('Save.setting("svv_offline_friends", [])', body)
        self.assertIn("for candidate in saved_offline_party:", body)
        self.assertIn("recruited_friends.has(offline_class)", body)
        self.assertIn("coop_classes.clear()", body)
        self.assertLess(body.index('Save.setting("svv_offline_friends"'), body.index("_build_scene()"))

    def test_empty_malformed_and_duplicate_rosters_are_safe(self):
        body = prepare.offline_party_bootstrap()
        self.assertIn("if not saved_offline_party is Array:", body)
        self.assertIn("if not recruited_friends is Array:", body)
        self.assertIn("GameData.CLASSES.has(offline_class)", body)
        self.assertIn("not coop_classes.has(offline_class)", body)
        self.assertIn("coop_classes.size() < 3", body)
        self.assertNotIn('begins_with("--offline-party=")', body)
        self.assertTrue(body.rstrip().endswith("_build_scene()"))

    def test_friends_list_is_sole_party_selection_surface(self):
        root = module_path.parents[1]
        assistant = (root / "original-addons/offline_assistant.gd").read_text(encoding="utf-8")
        self.assertIn('open_button.text = "Bạn bè"', assistant)
        self.assertIn('title.text = "Friends List · Bằng hữu Midgard"', assistant)
        self.assertIn('Save.setting("svv_offline_friends", [])', assistant)
        self.assertIn('Save.set_setting("svv_friend_quests", quests)', assistant)
        self.assertIn('Save.set_setting("svv_offline_party", party)', assistant)
        self.assertIn('if not bool(progress["started"]):', assistant)
        self.assertIn('elif bool(progress["ready"]):', assistant)
        self.assertIn('world.coop_classes.assign(party)', assistant)
        self.assertNotIn('open_button.text = "Tìm party"', assistant)
        self.assertIn('"acolyte": {"name": "Mira", "rarity": "Normal"', assistant)
        for rarity in ('Normal', 'Rare', 'Ultra Rare'):
            self.assertIn('"rarity": "' + rarity + '"', assistant)
        self.assertIn('const FRIEND_PROFILES := {', assistant)

    def test_mira_town_dialog_and_heal_are_installed(self):
        root = module_path.parents[1]
        installer = (root / "tools/install-original-assistant.py").read_text(encoding="utf-8")
        script = (root / "original-addons/mira_town.gd").read_text(encoding="utf-8")
        assistant = (root / "original-addons/offline_assistant.gd").read_text(encoding="utf-8")
        self.assertIn('SVVMiraTown="*res://addons/svv_offline/mira_town.gd"', installer)
        self.assertIn('func _town_active() -> bool:', script)
        self.assertIn('func _show_dialog() -> void:', script)
        self.assertIn('func play_heal_fx(target: Player, recovered: float)', script)
        self.assertIn('SVVAssistant._friend_action_pressed()', script)
        self.assertIn('SVVAssistant._quest_progress("acolyte")', script)
        self.assertIn('mira_npc.play_heal_fx(recipient, recovered)', assistant)
        self.assertIn('if not _unlocked_friends().has("acolyte"):', assistant)
        self.assertNotIn('http', script.lower())

    def test_mira_heal_projection_is_3d_safe(self):
        root = module_path.parents[1]
        script = (root / "original-addons/mira_town.gd").read_text(encoding="utf-8")
        self.assertIn('target.global_position', script)
        self.assertIn('viewport.get_camera_3d()', script)
        self.assertIn('camera.unproject_position(', script)
        self.assertIn('if camera != null', script)
        self.assertNotIn('get_global_transform_with_canvas()', script)

    def test_mira_native_world_sprite_uses_recovered_ro_assets(self):
        root = module_path.parents[1]
        script = (root / "original-addons/mira_town.gd").read_text(encoding="utf-8")
        for phrase in (
            'const MIRA_SPRITE := "acolyte_f"',
            'const KAFRA_NPC := "kafra"',
            'RoAssets.has_sprite(MIRA_SPRITE)',
            'RoAssets.sprite([MIRA_SPRITE])',
            'RoVisual.new()',
            'candidate.npc_node(KAFRA_NPC)',
            'func _unhandled_input(event: InputEvent)',
            'camera.unproject_position(point)',
            'var nameplate := Label3D.new()',
            'func _clear_world_sprite()',
        ):
            self.assertIn(phrase, script)
        self.assertNotIn('load("res://assets/ro/sprites/acolyte_f.png")', script)
        self.assertNotIn('TextureRect.new()', script)

    def test_native_mira_animation_and_town_lifecycle(self):
        root = module_path.parents[1]
        script = (root / "original-addons/mira_town.gd").read_text(encoding="utf-8")
        smoke = (root / "original-addons/offline_smoke.gd").read_text(encoding="utf-8")
        self.assertIn('func _tick_patrol(delta: float) -> void:', script)
        self.assertIn('_set_mira_animation("PC_WALK")', script)
        self.assertIn('_set_mira_animation("PC_IDLE")', script)
        self.assertIn('script.get_script_constant_map()', script)
        self.assertIn('town.is_inside_tree()', script)
        self.assertIn('world.enter_town("swordsman")', smoke)
        self.assertIn('world.leave_town()', smoke)
        self.assertIn('mira.sprite is Sprite3D', smoke)
        self.assertIn('click on Mira world sprite opens NPC dialogue', smoke)

    def test_original_boot_skips_online_login_and_preloads_guard(self):
        source = module_path.read_text(encoding="utf-8")
        self.assertIn('"show_login": "show_class_select()"', source)
        self.assertNotIn('{"_opening_screens": "menus.show_class_select()"}', source)
        self.assertIn("Keep the ORIGINAL _opening_screens", source)
        self.assertIn('svv_guard.restore_missing_profile(PATH, _name)', source)
        self.assertLess(source.index('svv_guard.restore_missing_profile(PATH, _name)'), source.index('"load_profile()"'))


    def test_redirecting_login_preserves_preparation_route(self):
        original = (
            'func show_login() -> void:\n'
            '\tprint("online-only login")\n'
            '\n'
            'func show_prep() -> void:\n'
            '\tworld.start_run("swordsman", true)\n'
        )
        actual = prepare.replace_function(original, "show_login", "show_class_select()")
        self.assertIn("func show_login() -> void:\n\tshow_class_select()", actual)
        self.assertIn('world.start_run("swordsman", true)', actual)
        self.assertNotIn("online-only login", actual)


class RunSaveVersionCompatibility(unittest.TestCase):
    @staticmethod
    def fixture(hero_snapshot: str) -> str:
        return "\n".join([
            hero_snapshot,
            "static func save(w: World) -> void:",
            "\tif w.is_dead() or w.is_coop():",
            "\t\treturn",
            '\tvar tmp: = path() + ".tmp"',
            "",
            "static func resume(w: World, d: Dictionary) -> void:",
            '\tw.start_run(str(d["class"]))',
            "\tapply_hero(w, d)",
            "",
        ])

    def test_0_2_0_native_per_hero_snapshot_remains_unchanged(self):
        snapshot = "\n".join([
            "static func hero_snapshot(w: World, hero: Player = null) -> Dictionary:",
            "\tvar p: = hero if hero != null else w.player",
            '\treturn {"class": p.class_id}',
            "",
        ])
        result = prepare.patch_party_run_save(self.fixture(snapshot))
        self.assertIn(snapshot, result)
        self.assertIn("hero_snapshot(w, offline_hero)", result)
        self.assertIn('d["offline_party"] = offline_party', result)
        self.assertIn("apply_hero(w, offline_record, offline_hero, false)", result)

    def test_0_1_x_legacy_snapshot_is_extended(self):
        snapshot = "\n".join([
            "static func hero_snapshot(w: World) -> Dictionary:",
            "\tvar p: = w.player",
            '\treturn {"class": p.class_id}',
            "",
        ])
        result = prepare.patch_party_run_save(self.fixture(snapshot))
        self.assertIn("static func hero_snapshot(w: World, p: Player = null)", result)
        self.assertIn("\tif p == null:\n\t\tp = w.player", result)

    def test_changed_snapshot_without_per_hero_binding_fails_closed(self):
        snapshot = "\n".join([
            "static func hero_snapshot(w: World, hero: Player = null) -> Dictionary:",
            "\tvar p: = w.player",
            '\treturn {"class": p.class_id}',
            "",
        ])
        with self.assertRaisesRegex(ValueError, "ignores explicit hero"):
            prepare.patch_party_run_save(self.fixture(snapshot))


if __name__ == "__main__":
    unittest.main()
