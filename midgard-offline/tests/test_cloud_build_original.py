import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile
import hashlib

spec = importlib.util.spec_from_file_location("cloud_original", Path(__file__).resolve().parents[1] / "tools/cloud-build-original.py")
cloud = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cloud)

class CloudInputs(unittest.TestCase):
    def test_untranslated_long_prose_triage(self):
        """New dialogue/help text is flagged, but equipment and skills stay."""
        pending = [
            {"msgid": "Mantén la distancia", "english": "Keep your distance when the enemy starts the attack."},
            {"msgid": "Cofre", "english": "Treasure Box"},
            {"msgid": "Valhalla", "english": "Valhalla"},
            {"msgid": "Ayuda", "english": "Choose a class and start your next battle in this region."},
            {"msgid": "Épico", "english": "Union of the Sun, Moon and Stars!"},
        ]
        reported = cloud.find_untranslated_prose_candidates(pending)
        self.assertEqual([entry["msgid"] for entry in reported],
                         ["Mantén la distancia", "Ayuda"])
        self.assertEqual(cloud.find_untranslated_prose_candidates([]), [])
        script = (Path(__file__).resolve().parents[1] /
                  "tools/cloud-build-original.py").read_text(encoding="utf-8")
        self.assertIn("untranslated-prose-review.json", script)
        self.assertIn("likely_untranslated_prose", script)

    def test_town_visual_inspection_exports_only_targeted_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            town = root / "scripts/core/town.gd"
            town.parent.mkdir(parents=True)
            town.write_text(
                "func _draw_member(look: Dictionary) -> void:\\n"
                "\\tvar sprite = Sprite3D.new()\\n"
                "\\tsprite.texture = load(\\\"res://assets/ro/acolyte.png\\\")\\n"
                "func tick(delta: float) -> void:\\n\\tpass\\n",
                encoding="utf-8")
            result = cloud.inspect_town_visual_api(root)
            self.assertTrue(result["metadata_only"])
            entry = result["modules"]["scripts/core/town.gd"]["methods"]["_draw_member"]
            self.assertIn("look: Dictionary", entry["signature"])
            self.assertIn("Sprite3D", entry["node_types"])
            self.assertTrue(any("Sprite3D.new" in row for row in entry["visual_hints"]))
            self.assertNotIn("tick", result["modules"]["scripts/core/town.gd"]["methods"])
            self.assertTrue(result["modules"]["scripts/core/town_crowd.gd"]["missing"])

    def test_archive_paths_cannot_escape_and_templates_are_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            safe = root / "safe.zip"
            with ZipFile(safe, "w") as archive:
                archive.writestr("templates/android_debug.apk", b"template")
                archive.writestr("templates/unneeded.bin", b"other")
            cloud.extract_safe(safe, root / "out", {"android_debug.apk"})
            self.assertEqual((root / "out/android_debug.apk").read_bytes(), b"template")
            self.assertFalse((root / "out/unneeded.bin").exists())
            bad = root / "bad.zip"
            with ZipFile(bad, "w") as archive:
                archive.writestr("../outside.txt", b"no")
            with self.assertRaises(ValueError):
                cloud.extract_safe(bad, root / "out")
            self.assertFalse((root / "outside.txt").exists())

    def test_download_promotes_only_bytes_matching_the_pinned_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "tool.zip"
            expected = b"known official artifact"
            config = {"url": "https://example.invalid/official", "sha256": hashlib.sha256(expected).hexdigest()}
            with patch.object(cloud.urllib.request, "urlopen", side_effect=lambda *a, **k: io.BytesIO(b"wrong")), patch.object(cloud.time, "sleep"):
                with self.assertRaises(ValueError):
                    cloud.download(config, destination)
            self.assertFalse(destination.exists())
            with patch.object(cloud.urllib.request, "urlopen", side_effect=lambda *a, **k: io.BytesIO(expected)):
                cloud.download(config, destination)
            self.assertEqual(destination.read_bytes(), expected)

    def test_portable_web_templates_include_release_and_debug(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            editor = root / "tools" / "godot"
            editor.parent.mkdir()
            editor.write_bytes(b"godot")
            templates = root / "templates"
            templates.mkdir()
            (templates / "web_nothreads_debug.zip").write_bytes(b"debug")
            (templates / "web_nothreads_release.zip").write_bytes(b"release")
            installed = cloud.install_web_templates(editor, templates, "4.7.2")
            self.assertEqual(
                installed,
                editor.parent / "editor_data" / "export_templates" / "4.7.2.stable",
            )
            self.assertEqual((installed / "web_nothreads_debug.zip").read_bytes(), b"debug")
            self.assertEqual((installed / "web_nothreads_release.zip").read_bytes(), b"release")
            (templates / "web_nothreads_release.zip").unlink()
            with self.assertRaises(FileNotFoundError):
                cloud.install_web_templates(editor, templates, "4.7.2")

    def test_android_texture_import_is_enabled_once_on_private_project(self):
        with tempfile.TemporaryDirectory() as directory:
            prepared = Path(directory) / "work" / "prepared"
            prepared.mkdir(parents=True)
            project_config = prepared / "project.godot"
            project_config.write_text('[application]\nconfig/name="Midgard SVV Offline"\n\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n', encoding="utf-8")
            first = cloud.configure_android_texture_import(prepared)
            second = cloud.configure_android_texture_import(prepared)
            self.assertEqual(first, second)
            self.assertEqual(first.count("textures/vram_compression/import_etc2_astc=true"), 1)
            self.assertIn('renderer/rendering_method="gl_compatibility"', first)

    def test_web_export_disables_pwa_without_icons(self):
        script = Path(__file__).resolve().parents[1] / "tools" / "create-original-presets.py"
        source = script.read_text(encoding="utf-8")
        self.assertIn("progressive_web_app/enabled=false", source)
        self.assertNotIn("progressive_web_app/enabled=true", source)
        self.assertIn('custom_template/release="{web_release}"', source)
        self.assertIn('web_release = (templates / "web_nothreads_release.zip").as_posix()', source)

    def test_web_uses_release_build_and_mobile_optimizer_autoload(self):
        root = Path(__file__).resolve().parents[1]
        build_script = (root / "tools/cloud-build-original.py").read_text(encoding="utf-8")
        installer = (root / "tools/install-original-assistant.py").read_text(encoding="utf-8")
        addon = (root / "original-addons/web_mobile_performance.gd").read_text(encoding="utf-8")
        self.assertIn('"--export-release", "Web Offline"', build_script)
        self.assertIn("web_mobile_performance.gd", installer)
        self.assertIn("SVVWebMobilePerformance", installer)
        self.assertIn('OS.has_feature("web")', addon)
        self.assertIn("JavaScriptBridge.eval(", addon)
        self.assertIn("CONTENT_SCALE_MODE_VIEWPORT", addon)
        self.assertIn("CONTENT_SCALE_ASPECT_KEEP", addon)
        # The Web optimizer now rotates the selected viewport dynamically
        # and permits up to 60 FPS instead of hardcoding the old 450x800/30.
        # Keep test expectations in sync with the adaptive quality policy.
        self.assertIn("HIGH_LANDSCAPE := Vector2i(600, 338)", addon)
        self.assertIn("MEDIUM_LANDSCAPE := Vector2i(560, 315)", addon)
        self.assertIn("LOW_LANDSCAPE := Vector2i(520, 293)", addon)
        self.assertIn("FPS_TARGET := 60", addon)
        self.assertIn("Engine.max_fps = FPS_TARGET", addon)
        self.assertIn("Vector2i(landscape.y, landscape.x)", addon)
        self.assertIn("if window.size.y > window.size.x else landscape", addon)
        self.assertIn("Engine.get_frames_per_second()", addon)
        self.assertNotIn("Engine.max_fps = 30", addon)

    def test_social_strip_removes_publisher_links_but_not_discord(self):
        root = Path(__file__).resolve().parents[1]
        installer = (root / "tools/install-original-assistant.py").read_text(encoding="utf-8")
        addon = (root / "original-addons/social_buttons_cleanup.gd").read_text(encoding="utf-8")
        self.assertIn("SVVSocialCleanup", installer)
        self.assertIn("social_buttons_cleanup.gd", installer)
        self.assertIn("button.hide()", addon)
        self.assertIn("if button != donate and button != discord:", addon)
        self.assertIn('const DISCORD_INVITE_URL := ""', addon)
        self.assertIn('SAVE_BUTTON_NAME := "SVVSaveBackupButton"', addon)
        self.assertIn("SVVSaveManager.open_manager()", addon)
        manager = (root / "original-addons/web_save_manager.gd").read_text(encoding="utf-8")
        guardian = (root / "original-addons/offline_save_guardian.gd").read_text(encoding="utf-8")
        self.assertIn("SVVSaveManager", installer)
        self.assertIn("web_save_manager.gd", installer)
        self.assertIn("func export_save()", manager)
        self.assertIn("func _receive_import_file(arguments: Array)", manager)
        self.assertIn("func _restore_previous()", manager)
        self.assertIn("func adopt_imported_profile(content: PackedByteArray)", guardian)
        self.assertIn("Marshalls.raw_to_base64", manager)
        self.assertIn("Marshalls.base64_to_raw", manager)
        self.assertIn("SVVSaveGuardian.backup_now()", manager)
        self.assertIn("ImageTexture.create_from_image", addon)
        self.assertIn("discord.com/invite/", addon)
        self.assertIn("discord.gg/", addon)

    def test_cache_seeding_does_not_restore_native_extensions_or_old_fonts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / "source/.godot/imported"
            cache.mkdir(parents=True)
            for name in ("map.scn", "sprite.ctex", "map.md5", "old.fontdata", "native.gdextension"):
                (cache / name).write_bytes(b"data")
            cloud.seed_cache(root / "source", root / "target")
            names = {p.name for p in (root / "target/.godot/imported").iterdir()}
            self.assertEqual(names, {"map.scn", "sprite.ctex", "map.md5"})

if __name__ == "__main__":
    unittest.main()
