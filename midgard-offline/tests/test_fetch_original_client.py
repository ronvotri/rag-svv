"""Small synthetic archive tests. No official asset download or account required."""
import hashlib
import io
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile
import zlib

SCRIPT = Path(__file__).resolve().parents[1] / "tools/fetch-original-client.py"
spec = importlib.util.spec_from_file_location("fetch_original_client", SCRIPT)
fetcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetcher)


class FetchOriginalClientTests(unittest.TestCase):
    def fixture(self, folder, *, unsafe=False, duplicate=False, corrupt_other=False):
        data = b"GDPC-synthetic-test-payload"
        archive = folder / "client.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as output:
            output.writestr("MidgardSurvivors.pck", data)
            output.writestr("../escape.txt" if unsafe else "ignored.exe", b"never-extracted")
            if duplicate:
                output.writestr("MidgardSurvivors.pck", data)
        if corrupt_other:
            content = archive.read_bytes().replace(b"never-extracted", b"never-extractee", 1)
            archive.write_bytes(content)
        config = {"archive_size": archive.stat().st_size, "max_archive_entries": 32,
                  "max_total_uncompressed": 10000, "pck_member": "MidgardSurvivors.pck",
                  "pck_size": len(data), "pck_crc32": f"{zlib.crc32(data):08x}",
                  "pck_sha256": hashlib.sha256(data).hexdigest(), "upload_id": "test"}
        return archive, config, data

    def test_extracts_only_verified_pck_and_preserves_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            archive, config, data = self.fixture(folder)
            output = folder / "result" / "MidgardSurvivors.pck"
            report = fetcher.extract_pck(archive, output, config)
            self.assertEqual(output.read_bytes(), data)
            self.assertTrue(report["pck_sha256_verified"])
            self.assertTrue(archive.is_file())
            self.assertEqual([p.name for p in output.parent.iterdir()], ["MidgardSurvivors.pck"])
            with self.assertRaises(ValueError):
                fetcher.extract_pck(archive, output, config)
            self.assertEqual(output.read_bytes(), data)

    def test_repacked_zip_size_is_allowed_only_for_the_same_pck(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            archive, config, data = self.fixture(folder)
            config["archive_size"] += 17  # stale wrapper pin; PCK remains pinned
            payload = archive.read_bytes()

            class RangeResponse(io.BytesIO):
                status = 206

                def __init__(self):
                    super().__init__(payload)
                    self.headers = {"Content-Range": f"bytes 0-{len(payload)-1}/{len(payload)}"}

            class RangeOpener:
                def open(self, _req, timeout=60):
                    return RangeResponse()

            inspection = fetcher.metadata(RangeOpener(), "https://nearq.itch.io/test", config)
            self.assertEqual(inspection["archive_size"], len(payload))
            self.assertEqual(inspection["original_archive_size"], config["archive_size"])
            destination = folder / "verified.pck"
            fetcher.extract_pck(archive, destination, config)
            self.assertEqual(destination.read_bytes(), data)
            config["pck_sha256"] = "f" * 64
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                fetcher.extract_pck(archive, folder / "wrong.pck", config)

    def test_wrong_sha_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            archive, config, _ = self.fixture(folder)
            config["pck_sha256"] = "0" * 64
            output = folder / "result.pck"
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                fetcher.extract_pck(archive, output, config)
            self.assertFalse(output.exists())

    def test_unsafe_and_duplicate_members_are_rejected(self):
        for option in ["unsafe", "duplicate"]:
            with self.subTest(option=option), tempfile.TemporaryDirectory() as temporary:
                folder = Path(temporary)
                archive, config, _ = self.fixture(folder, **{option: True})
                with self.assertRaises(ValueError):
                    fetcher.extract_pck(archive, folder / "result.pck", config)

    def test_crc_is_checked_for_all_archive_members(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            archive, config, _ = self.fixture(folder, corrupt_other=True)
            with self.assertRaisesRegex(ValueError, "CRC"):
                fetcher.extract_pck(archive, folder / "result.pck", config)

    def test_anonymous_form_and_download_host_boundaries(self):
        page = fetcher.PageFields()
        page.feed('<meta name="csrf_token" value="synthetic-token"><a data-upload_id="123"></a>')
        self.assertEqual(page.csrf, "synthetic-token")
        self.assertEqual(page.uploads, {"123"})
        self.assertTrue(fetcher.allowed_url("https://nearq.itch.io/midgard-survivors"))
        self.assertTrue(fetcher.allowed_url("https://itchio-mirror.example.r2.cloudflarestorage.com/file"))
        for url in ["http://nearq.itch.io/file", "https://evil.example/file", "file:///secret", "https://user:pass@nearq.itch.io/file"]:
            self.assertFalse(fetcher.allowed_url(url))
        for name in ["../file", "C:/file", "/file", "a\\file", "bad\0name"]:
            with self.assertRaises(ValueError):
                fetcher.safe_member(name)


if __name__ == "__main__":
    unittest.main()
