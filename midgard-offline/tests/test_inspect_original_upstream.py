"""Synthetic ZIP validation for the upstream inspector, no official assets used."""
from pathlib import Path
import hashlib
import importlib.util
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / "tools/inspect-original-upstream.py"
SPEC = importlib.util.spec_from_file_location("svv_inspect_original_upstream", SCRIPT)
inspect = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inspect)


class OfficialSourceInspectorTests(unittest.TestCase):
    def test_reports_changed_pck_hash_without_accepting_it_as_a_pin(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "source.zip"
            pck = b"synthetic new PCK"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as out:
                out.writestr("MidgardSurvivors.pck", pck)
                out.writestr("readme.txt", "test")
            config = {"upload_id": "20348959", "max_archive_entries": 32,
                      "max_total_uncompressed": 1024, "pck_member": "MidgardSurvivors.pck",
                      "pck_sha256": "0" * 64}
            report = inspect.inspect_archive(archive, config)
            self.assertTrue(report["pck_changed"])
            self.assertEqual(report["pck_sha256"], hashlib.sha256(pck).hexdigest())
            self.assertEqual(report["pck_size"], len(pck))
            self.assertEqual(report["old_pck_sha256"], "0" * 64)

    def test_refuses_untrusted_or_ambiguous_zip(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            config = {"upload_id": "20348959", "max_archive_entries": 32,
                      "max_total_uncompressed": 1024, "pck_member": "MidgardSurvivors.pck",
                      "pck_sha256": "0" * 64}
            for label, name in (("traversal", "../evil.pck"), ("missing", "other.pck")):
                archive = folder / (label + ".zip")
                with zipfile.ZipFile(archive, "w") as out:
                    out.writestr(name, b"data")
                with self.subTest(label=label), self.assertRaises(ValueError):
                    inspect.inspect_archive(archive, config)


if __name__ == "__main__":
    unittest.main()
