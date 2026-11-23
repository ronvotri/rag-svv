"""Unit QA for metadata-only World Boss API reconnaissance.

No publisher code or assets are stored in this test fixture.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
spec = importlib.util.spec_from_file_location("world_boss_map_audit", TOOLS / "audit-world-boss-maps.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class WorldBossAuditTests(unittest.TestCase):
    def test_extracts_signatures_without_copying_function_bodies_or_defaults(self):
        source = """func start_world_boss(boss: String, difficulty: int = 2) -> void:
    var secret_server_value = \"must_not_export\"
func _load_map(
    region: String,
    spawn: Vector2 = Vector2(1, 2)
) -> void:
    var secret_map_data = \"must_not_export\"
"""
        result = audit.api_signatures(source, ("start_world_boss", "_load_map"))
        self.assertEqual(result["start_world_boss"], {
            "parameters": ["boss: String", "difficulty: int"], "required": 1, "total": 2,
        })
        self.assertEqual(result["_load_map"], {
            "parameters": ["region: String", "spawn: Vector2"], "required": 1, "total": 2,
        })
        self.assertNotIn("must_not_export", str(result))
        self.assertNotIn("Vector2(1, 2)", str(result))


    def test_flow_hints_mask_literals_and_keep_native_save_risks_explicit(self):
        source = """func start_world_boss(index: int, state: Dictionary) -> void:
    # start_route("comment-only")
    print("Save.flush(); WorldBoss.new(self, state); SECRET_PROFILE")
    var boss = WorldBoss.new(self, state)
    start_run("swordsman")
    Save.flush()
func _finish() -> void:
    # NetSync.send("do_not_export")
    GameData.wb_chest_items("tier", 0)
    var reward_due = true
"""
        result = audit.method_flow_hints(
            source, ("start_world_boss", "_finish")
        )
        self.assertEqual(result["start_world_boss"]["call_cues"], [
            "save_flush", "start_run", "world_boss_constructor",
        ])
        self.assertEqual(result["start_world_boss"]["review_signals"], [
            "save_reference",
        ])
        self.assertIn("reward_reference", result["_finish"]["review_signals"])
        self.assertIn("wb_chest_items", result["_finish"]["call_cues"])
        self.assertNotIn("network_reference", result["_finish"]["review_signals"])
        self.assertNotIn("SECRET_PROFILE", str(result))

    def test_native_flow_never_approves_gameplay_from_static_recon(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            main = root / "scripts/core/main.gd"
            main.parent.mkdir(parents=True)
            main.write_text(
                "func start_world_boss(index: int, state: Dictionary):\n"
                "    start_run(\"swordsman\")\n", encoding="utf-8"
            )
            flow = audit.native_flow_metadata(root)
            self.assertTrue(flow["metadata_only"])
            self.assertIn(
                "start_run",
                flow["methods"]["scripts/core/main.gd"]["methods"]["start_world_boss"]["call_cues"]
            )
            self.assertFalse(flow["gates"]["safe_to_enable"])
            self.assertFalse(flow["gates"]["offline_save_and_reward_isolation_verified"])

    def test_inventory_marks_available_contract_without_claiming_playability(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "project.godot").write_text("[application]\n", encoding="utf-8")
            main = root / "scripts/core/main.gd"
            main.parent.mkdir(parents=True)
            main.write_text("func start_world_boss(which: String) -> void:\n    pass\n", encoding="utf-8")
            report = audit.inventory(root)
            native = report["native_world_boss_contract"]
            self.assertFalse(report["native_world_boss_flow"]["gates"]["safe_to_enable"])
            self.assertEqual(native["scripts/core/main.gd"]["methods"]["start_world_boss"]["parameters"], ["which: String"])
            self.assertTrue(native["scripts/core/world_boss.gd"]["missing_file"])
            self.assertFalse(report["verified_playable_world_boss_map"])
            self.assertEqual(report["scene_candidate_count"], 0)
            self.assertEqual(report["resource_extension_counts"][".tscn"], 0)


if __name__ == "__main__":
    unittest.main()
