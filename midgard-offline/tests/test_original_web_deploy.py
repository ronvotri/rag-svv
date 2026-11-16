"""Tests for Cloudflare Pages + R2 package staging (no public upload)."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

module_file = Path(__file__).resolve().parents[1] / "tools/prepare-original-web-deploy.py"
spec = importlib.util.spec_from_file_location("original_web_deploy", module_file)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class CloudflareStagingTests(unittest.TestCase):
    def test_oversized_godot_files_go_only_to_r2(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "export"
            source.mkdir()
            (source / "index.html").write_text("<html>Godot</html>", encoding="utf-8")
            (source / "index.js").write_text("console.log('game')", encoding="utf-8")
            (source / "index.pck").write_bytes(b"x" * 30)
            (source / "index.wasm").write_bytes(b"y" * 32)
            result = mod.stage(source, root / "deploy", "abcdef0123456", limit=20)
            self.assertEqual([x["name"] for x in result["large_assets"]], ["index.pck", "index.wasm"])
            self.assertFalse((root / "deploy/public/index.pck").exists())
            self.assertTrue((root / "deploy/r2/index.pck").exists())
            self.assertEqual(json.loads((root / "deploy/public/_routes.json").read_text())["include"], ["/index.pck", "/index.wasm"])
            cfg = (root / "deploy/wrangler.toml").read_text()
            self.assertIn('ASSET_VERSION = "abcdef0123456"', cfg)
            self.assertIn('binding = "GAME_ASSETS"', cfg)
            self.assertTrue((root / "deploy/functions/[[path]].js").is_file())

    def test_invalid_version_and_missing_core_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            src = root / "export"
            src.mkdir()
            (src / "index.html").write_text("hi")
            with self.assertRaises(ValueError):
                mod.stage(src, root / "out", "../bad")
            with self.assertRaises(ValueError):
                mod.stage(src, root / "out", "abcdef0123456")


if __name__ == "__main__":
    unittest.main()
