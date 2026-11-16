"""Regressions for the authored native Godot offline party bootstrap."""
from pathlib import Path
import importlib.util
import unittest

module_path = Path(__file__).resolve().parents[1] / "tools/prepare-original-offline.py"
spec = importlib.util.spec_from_file_location("prepare_original_offline", module_path)
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class OriginalPartyBootstrap(unittest.TestCase):
    def test_saved_party_is_used_instead_of_hardcoded_defaults(self):
        body = prepare.offline_party_bootstrap()
        self.assertIn('Save.setting("svv_offline_party", ["acolyte", "mage", "archer"])', body)
        self.assertIn("for candidate in saved_offline_party:", body)
        self.assertIn("coop_classes.clear()", body)
        self.assertLess(body.index('Save.setting("svv_offline_party"'), body.index("_build_scene()"))

    def test_empty_and_malformed_roster_and_cli_override(self):
        body = prepare.offline_party_bootstrap()
        self.assertIn("if not saved_offline_party is Array:", body)
        self.assertNotIn("if saved_offline_party.is_empty():", body)
        self.assertIn("GameData.CLASSES.has(offline_class)", body)
        self.assertIn("not coop_classes.has(offline_class)", body)
        self.assertIn("coop_classes.size() < 3", body)
        self.assertIn('begins_with("--offline-party=")', body)
        self.assertIn("substr(16)", body)
        self.assertLess(body.index("for candidate in saved_offline_party:"), body.index('begins_with("--offline-party=")'))
        self.assertTrue(body.rstrip().endswith("_build_scene()"))


if __name__ == "__main__":
    unittest.main()
