"""Regression tests: font-safe class navigation and original character art."""
from __future__ import annotations
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "svv_start_bg", ROOT / "tools/install-start-background.py"
)
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class StartBackgroundTests(unittest.TestCase):
    def source(self, directory):
        project = Path(directory) / "project"
        (project / "scripts/ui").mkdir(parents=True)
        script = project / "scripts/ui/menus.gd"
        script.write_text(
            "extends Control\n"
            'var _mode = "class_select"\n\n'
            "func show_class_select() -> void:\n"
            "\tvar original_buttons = 3\n"
            "\tprint(original_buttons)\n\n"
            "func show_loading() -> void:\n"
            "\tpass\n",
            encoding="utf-8")
        return project, script

    def test_authored_image_is_installed_without_replacing_menu_logic(self):
        with tempfile.TemporaryDirectory() as directory:
            project, script = self.source(directory)
            report = installer.install(project)
            patched = script.read_text(encoding="utf-8")
            self.assertTrue(report["installed"])
            self.assertIn('call_deferred("_svv_fix_class_select_navigation")', patched)
            self.assertIn("func _svv_class_arrow_texture(point_left: bool)", patched)
            self.assertIn("func _svv_fix_class_select_navigation()", patched)
            self.assertIn("prev_button.icon = _svv_class_arrow_texture(true)", patched)
            self.assertIn("next_button.icon = _svv_class_arrow_texture(false)", patched)
            self.assertIn('prev_button.text = ""', patched)
            self.assertIn('next_button.text = ""', patched)
            self.assertIn("button.get_global_rect()", patched)
            self.assertNotIn("next_button.pressed.disconnect", patched)
            self.assertNotIn("prev_button.pressed.disconnect", patched)
            self.assertIn("var original_buttons = 3", patched)
            self.assertIn("func show_loading() -> void:", patched)
            self.assertNotIn("func _svv_replace_class_screen_backdrop()", patched)
            self.assertIn('if _mode != "class_select":', patched)
            self.assertIn('if not is_inside_tree():', patched)
            self.assertIn('tree_entered.connect(_svv_fix_class_select_navigation, CONNECT_ONE_SHOT)', patched)
            self.assertIn('if viewport == null:', patched)
            self.assertIn('var viewport_size: Vector2 = viewport.get_visible_rect().size', patched)
            self.assertNotIn('get_viewport().get_visible_rect()', patched)
            source = ROOT / "original-addons/svv_home_background.jpg"
            self.assertFalse((project / "assets/svv/svv_home_background.jpg").exists())
            self.assertEqual(source.read_bytes()[:3], b"\xff\xd8\xff")
            self.assertLess(source.stat().st_size, 3_000_000)
            with self.assertRaisesRegex(ValueError, "already installed"):
                installer.install(project)

    def test_fails_closed_if_menu_implementation_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            project, script = self.source(directory)
            script.write_text("extends Control\nfunc unknown() -> void:\n\tpass\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "show_class_select hook"):
                installer.install(project)
            self.assertNotIn("SVV", script.read_text(encoding="utf-8"))

    def test_only_accepts_jpeg_and_checks_size(self):
        with tempfile.TemporaryDirectory() as directory:
            project, _ = self.source(directory)
            image = Path(directory) / "bad.png"
            image.write_bytes(b"\x89PNG" + b"\0" * 50)
            with self.assertRaisesRegex(ValueError, "must be JPEG"):
                installer.install(project, image)
            with self.assertRaises(FileNotFoundError):
                installer.install(project, image.with_name("missing.jpg"))


if __name__ == "__main__":
    unittest.main()
