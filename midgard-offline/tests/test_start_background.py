"""Regression tests for the optional authored Ragnarok start wallpaper."""
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
            self.assertIn('call_deferred("_svv_replace_class_screen_backdrop")', patched)
            self.assertIn("var original_buttons = 3", patched)
            self.assertIn("func show_loading() -> void:", patched)
            self.assertIn("func _svv_replace_class_screen_backdrop() -> void:", patched)
            self.assertIn("TextureRect.STRETCH_KEEP_ASPECT_COVERED", patched)
            self.assertIn('if _mode != "class_select":', patched)
            source = ROOT / "original-addons/svv_home_background.jpg"
            target = project / "assets/svv/svv_home_background.jpg"
            self.assertEqual(hashlib.sha256(source.read_bytes()).digest(),
                             hashlib.sha256(target.read_bytes()).digest())
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
