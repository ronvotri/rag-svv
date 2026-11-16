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
