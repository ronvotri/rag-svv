"""Ensure a recovered-client character factory is reported, never auto-approved."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "cloud_build_original", ROOT / "tools/cloud-build-original.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class OriginalCharacterLayerMetadataTests(unittest.TestCase):
    def test_original_styled_character_factory_is_surfaced_without_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            ro = project / "scripts/ro"
            ro.mkdir(parents=True)
            (ro / "ro_assets.gd").write_text(
                "class_name RoAssets\n"
                "static func styled_character(job: String, gender: String, look: String) -> RoSprite:\n"
                "\tvar head = RoAssets.sprite([look])\n"
                "\tvar body = RoAssets.sprite([job, gender])\n"
                "\treturn RoSprite.new([body, head])\n",
                encoding="utf-8",
            )
            report = builder.inspect_town_visual_api(project)
            methods = report["modules"]["scripts/ro/ro_assets.gd"]["methods"]
            self.assertIn("styled_character", methods)
            self.assertIn("gender: String", methods["styled_character"]["signature"])
            self.assertTrue(any(
                "head" in hint for hint in methods["styled_character"]["visual_hints"]))
            self.assertTrue(report["metadata_only"])
            self.assertFalse(report["rare_npc_composition_review"]["town_placement_approved"])
            self.assertEqual(
                report["rare_npc_composition_review"]["state"],
                "body_frames_only_head_hair_unverified")

    def test_missing_factory_is_explicitly_unverified(self):
        with tempfile.TemporaryDirectory() as temp:
            report = builder.inspect_town_visual_api(Path(temp))
            self.assertTrue(report["modules"]["scripts/ro/ro_assets.gd"]["missing"])
            self.assertFalse(report["rare_npc_composition_review"]["town_placement_approved"])


if __name__ == "__main__":
    unittest.main()
