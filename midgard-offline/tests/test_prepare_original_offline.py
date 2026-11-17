"""Regressions for the authored native Godot offline party bootstrap."""
from pathlib import Path
import importlib.util
import unittest

module_path = Path(__file__).resolve().parents[1] / "tools/prepare-original-offline.py"
spec = importlib.util.spec_from_file_location("prepare_original_offline", module_path)
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class OriginalPartyBootstrap(unittest.TestCase):
    def test_saved_party_is_used_instead_of_hardcoded_defaults(self):
        body = prepare.offline_party_bootstrap()
        self.assertIn('Save.setting("svv_offline_party", ["acolyte", "mage", "archer"])', body)
        self.assertIn("for candidate in saved_offline_party:", body)
        self.assertIn("coop_classes.clear()", body)
        self.assertLess(body.index('Save.setting("svv_offline_party"'), body.index("_build_scene()"))

    def test_empty_and_malformed_roster_and_cli_override(self):
        body = prepare.offline_party_bootstrap()
        self.assertIn("if not saved_offline_party is Array:", body)
        self.assertNotIn("if saved_offline_party.is_empty():", body)
        self.assertIn("GameData.CLASSES.has(offline_class)", body)
        self.assertIn("not coop_classes.has(offline_class)", body)
        self.assertIn("coop_classes.size() < 3", body)
        self.assertIn('begins_with("--offline-party=")', body)
        self.assertIn("substr(16)", body)
        self.assertLess(body.index("for candidate in saved_offline_party:"), body.index('begins_with("--offline-party=")'))
        self.assertTrue(body.rstrip().endswith("_build_scene()"))


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
