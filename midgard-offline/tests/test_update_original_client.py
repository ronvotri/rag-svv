"""Real binary overlay regressions; no original game resources in fixtures."""
import hashlib
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("update_original", ROOT / "tools/update-original-client.py")
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


def pack(path, files):
    names = {name: name.encode() for name in files}
    offset = 100 + sum(40 + len(name) for name in names.values())
    content = b"GDPC" + struct.pack("<I3IIQ", 2, 4, 7, 2, 0, 0) + b"\0" * 64
    content += struct.pack("<I", len(files))
    for name, data in files.items():
        raw = names[name]
        content += struct.pack("<I", len(raw)) + raw + struct.pack("<QQ", offset, len(data))
        content += hashlib.md5(data).digest() + struct.pack("<I", 0)
        offset += len(data)
    path.write_bytes(content + b"".join(files.values()))


def contents(path):
    result = {}
    with path.open("rb") as stream:
        for entry in update.inventory(path)["entries"]:
            stream.seek(entry["offset"])
            result[entry["path"]] = stream.read(entry["size"])
    return result


class PublisherUpdate(unittest.TestCase):
    def test_overlay_keeps_unchanged_assets_and_replaces_matching_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base, patch, out = [root / name for name in ("base.pck", "patch.pck", "out.pck")]
            pack(base, {"res://same.gdc": b"old", "res://sprite.bin": b"unchanged"})
            pack(patch, {"same.gdc": b"new", "added.bin": b"addition"})
            before = base.read_bytes()
            update.merge_packs([base, patch], out)
            self.assertEqual(contents(out), {"same.gdc": b"new", "sprite.bin": b"unchanged", "added.bin": b"addition"})
            self.assertEqual(base.read_bytes(), before)
            with self.assertRaises(ValueError):
                update.merge_packs([base, patch], base)
            with self.assertRaises(ValueError):
                update.merge_packs([base, patch], out)

    def test_corrupt_payload_leaves_no_usable_output(self):
        with tempfile.TemporaryDirectory() as directory:
            base, out = Path(directory) / "base.pck", Path(directory) / "out.pck"
            pack(base, {"a": b"valid"})
            base.write_bytes(base.read_bytes()[:-1] + b"!")
            with self.assertRaisesRegex(ValueError, "checksum"):
                update.merge_packs([base], out)
            self.assertFalse(out.exists())

    def test_download_pin_rejects_wrong_size_or_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "patch.bin"
            path.write_bytes(b"not-the-publisher-patch")
            with self.assertRaises(ValueError):
                update.verify_patch(path, {"size": path.stat().st_size, "sha256": "0" * 64})
            with self.assertRaises(ValueError):
                update.verify_patch(path, {"size": 1, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})


if __name__ == "__main__":
    unittest.main()
