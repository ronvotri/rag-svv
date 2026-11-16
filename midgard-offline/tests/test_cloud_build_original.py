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
