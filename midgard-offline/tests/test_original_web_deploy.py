"""Regression tests for Cloudflare Pages Free split Godot export."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

module_file = Path(__file__).resolve().parents[1] / "tools/prepare-original-web-deploy.py"
spec = importlib.util.spec_from_file_location("original_web_deploy", module_file)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def original_fixture(root):
    source = root / "export"
    source.mkdir()
    (source / "index.html").write_text("<html><head></head><body></body></html>", encoding="utf-8")
    (source / "index.js").write_text("console.log('godot');", encoding="utf-8")
    (source / "index.pck").write_bytes(bytes(range(100)))
    (source / "index.wasm").write_bytes(bytes(range(100))[::-1])
    return source


class CloudflarePagesOnlyTests(unittest.TestCase):
    def test_files_split_without_r2_and_reassemble_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = original_fixture(root)
            # 64-byte artificial ceiling exceeds the minimal HTML fixture
            # (~40 bytes), yet still forces the 100-byte PCK/WASM to split.
            # A 32-byte ceiling wrongly rejects this valid fixture HTML.
            self.assertLess((source / "index.html").stat().st_size, 64)
            result = mod.stage(source, root / "deploy", "abcdef0123456",
                               limit=64, part_bytes=16)
            public = root / "deploy/public"
            self.assertTrue((public / "index.html").is_file())
            self.assertTrue((public / "game.html").is_file())
            self.assertIn("fullscreen-toggle.js", (public / "game.html").read_text(encoding="utf-8"))
            self.assertIn("game-entry-guard.js", (public / "game.html").read_text(encoding="utf-8"))
            self.assertLess(
                (public / "game.html").read_text(encoding="utf-8").index("game-entry-guard.js"),
                (public / "game.html").read_text(encoding="utf-8").index("</head>")
            )
            self.assertTrue((public / "ragnarok-loading.jpg").is_file())
            self.assertGreater((public / "ragnarok-loading.jpg").stat().st_size, 250_000)
            self.assertFalse((public / "ragnarok-loading.avif").exists())
            self.assertIn("ragnarok-loading.jpg", (public / "game.html").read_text(encoding="utf-8"))
            self.assertIn("ragnarok-loading.jpg", (public / "index.html").read_text(encoding="utf-8"))
            self.assertEqual((public / "ragnarok-loading.jpg").read_bytes()[:3], b"\xff\xd8\xff")
            self.assertTrue((public / "fullscreen-toggle.js").is_file())
            self.assertTrue((public / "game-entry-guard.js").is_file())
            self.assertIn("Cache-Control: no-cache", (public / "_headers").read_text(encoding="utf-8"))
            self.assertTrue((public / "godot-split-sw.js").is_file())
            self.assertFalse((public / "index.pck").exists())
            self.assertFalse((public / "index.wasm").exists())
            self.assertFalse((root / "deploy/r2").exists())
            self.assertFalse((root / "deploy/wrangler.toml").exists())
            self.assertFalse((public / "_routes.json").exists())
            self.assertEqual(set(result["large_assets"]), {"index.pck", "index.wasm"})
            self.assertEqual(result["deployment_files"], sum(1 for p in public.rglob("*") if p.is_file()))

            for name, meta in result["large_assets"].items():
                self.assertTrue(all(part["size"] <= 16 for part in meta["parts"]))
                parts = [public / entry["path"] for entry in meta["parts"]]
                assembled = b"".join(p.read_bytes() for p in parts)
                self.assertEqual(assembled, (source / name).read_bytes())
                self.assertEqual(hashlib.sha256(assembled).hexdigest(), meta["sha256"])
                self.assertTrue(all(
                    hashlib.sha256(p.read_bytes()).hexdigest() == info["sha256"]
                    for p, info in zip(parts, meta["parts"])
                ))
            self.assertTrue(all(p.stat().st_size <= 25 for p in public.rglob("*") if p.is_file()
                                and p.name not in ("index.html", "game.html", "godot-split-sw.js",
                                                   "asset-map.json", "_headers", "fullscreen-toggle.js", "game-entry-guard.js",
                                                   "ragnarok-loading.jpg")))
            asset_map = json.loads((public / "asset-map.json").read_text(encoding="utf-8"))
            self.assertEqual(asset_map["version"], "abcdef0123456")
            self.assertEqual(asset_map["large_assets"], result["large_assets"])

    def test_splash_is_correct_in_initial_html_not_delayed_javascript(self):
        cover_url = mod.splash_url(mod.startup_cover())
        original = ('<html><head></head><body><div id="status">'
                    '<img src="index.png" srcset="old.png 2x" id="status-splash" alt="Loading">'
                    '<progress id="status-progress"></progress></div></body></html>')
        html = mod.replace_startup_splash(original, cover_url, require_image=True)
        self.assertIn('src="' + cover_url + '"', html)
        self.assertIn('href="' + cover_url + '"', html)
        self.assertIn('id="status-progress"', html)
        self.assertNotIn("index.png", html)
        self.assertNotIn("old.png", html)
        self.assertNotIn("DOMContentLoaded", html)
        again = mod.replace_startup_splash(html, cover_url, require_image=True)
        self.assertEqual(again.count('id="status-splash"'), 1)
        self.assertEqual(again.count('rel="preload"'), 1)
        with self.assertRaises(ValueError):
            mod.replace_startup_splash("<html><head></head></html>", cover_url, require_image=True)

    def test_raw_export_with_cover_stages_without_duplicate_and_uses_same_url(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = original_fixture(root)
            cover = mod.startup_cover()
            (source / "ragnarok-loading.jpg").write_bytes(cover.read_bytes())
            url = mod.splash_url(cover)
            raw = '<html><head></head><body><img id="status-splash" src="index.png"></body></html>'
            (source / "index.html").write_text(mod.replace_startup_splash(raw, url, require_image=True), encoding="utf-8")
            result = mod.stage(source, root / "deploy", "abcdef0123456")
            public = root / "deploy/public"
            self.assertEqual(sum(x["name"] == "ragnarok-loading.jpg" for x in result["static_assets"]), 1)
            for entry in ("index.html", "game.html"):
                page = (public / entry).read_text(encoding="utf-8")
                self.assertIn('src="' + url + '"', page)
                self.assertIn('href="' + url + '"', page)
                self.assertNotIn('img.src="./ragnarok-loading.jpg"', page)
            self.assertNotIn('src="index.png"', (public / "game.html").read_text(encoding="utf-8"))

    def test_unchanged_chunks_keep_urls_across_commits(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = original_fixture(root)
            first = mod.stage(source, root / "one", "abcdef0123456", limit=64, part_bytes=16)
            second = mod.stage(source, root / "two", "abcdef0123457", limit=64, part_bytes=16)
            pck_first = first["large_assets"]["index.pck"]["parts"]
            pck_second = second["large_assets"]["index.pck"]["parts"]
            self.assertEqual([p["path"] for p in pck_first],
                             [p["path"] for p in pck_second])
            self.assertTrue(all(part["sha256"] in part["path"] for part in pck_first))

            changed = bytearray((source / "index.pck").read_bytes())
            changed[0] ^= 0xFF
            (source / "index.pck").write_bytes(changed)
            third = mod.stage(source, root / "three", "abcdef0123458", limit=64, part_bytes=16)
            pck_third = third["large_assets"]["index.pck"]["parts"]
            self.assertNotEqual(pck_first[0]["path"], pck_third[0]["path"])
            self.assertEqual([p["path"] for p in pck_first[1:]],
                             [p["path"] for p in pck_third[1:]])

    def test_invalid_version_no_export_or_reusing_output_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = original_fixture(root)
            with self.assertRaises(ValueError):
                mod.stage(source, root / "out", "../bad", limit=25, part_bytes=16)
            with self.assertRaises(ValueError):
                mod.stage(source, root / "out", "abcdef0123456", limit=25, part_bytes=25)
            (source / "index.wasm").unlink()
            with self.assertRaises(ValueError):
                mod.stage(source, root / "out", "abcdef0123456", limit=25, part_bytes=16)

    def test_reject_subdirectories_and_symlinks(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = original_fixture(root)
            (source / "other").mkdir()
            with self.assertRaises(ValueError):
                mod.stage(source, root / "out", "abcdef0123456", limit=25, part_bytes=16)

    def test_reject_asset_count_over_free_plan(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = original_fixture(root)
            old = mod.MAX_FREE_FILES
            try:
                mod.MAX_FREE_FILES = 2
                with self.assertRaises(ValueError):
                    mod.stage(source, root / "out", "abcdef0123456", limit=64, part_bytes=16)
            finally:
                mod.MAX_FREE_FILES = old


if __name__ == "__main__":
    unittest.main()
