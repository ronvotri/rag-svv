"""Fail-closed guardrails for the private boss-on-map QA experiment."""
from pathlib import Path
import unittest
import runpy

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "original-addons/world_boss_map_qa.gd"
INSTALLER = ROOT / "tools/install-original-assistant.py"
BUILDER = ROOT / "tools/cloud-build-original.py"
RUNNER = ROOT / "tools/run-world-boss-map-qa.py"


class WorldBossMapTests(unittest.TestCase):
    def test_qa_scene_stays_off_menu_and_uses_native_world(self):
        code = SCRIPT.read_text(encoding="utf-8")
        for expected in (
            "--offline-test", "--offline-boss-map-qa",
            "SVV_WORLD_BOSS_QA_SANDBOX", "profile_offline_test",
            "RunSave.path()", "world.spawn_enemy(boss_id, point, true)",
            "world.heroes.size() == 4", "HeroInput.BotHero",
            'world.set_stage("prontera")', "res://scenes/main.tscn",
            "WORLD_BOSS_MAP_QA RESULT", "boss-start.png",
            "native_boss_hp_readable", "boss_loses_hp_without_forced_damage",
            "original_ai_moves_during_encounter", "COMBAT_MECHANICS_VERIFIED",
            "_native_number",
        ):
            self.assertIn(expected, code)
        active = "\n".join(
            line for line in code.splitlines() if not line.lstrip().startswith("#")
        )
        for prohibited in (
            "WorldBoss.new(", "start_world_boss(", "MvpRaid.start_route(",
            "Save.add_zeny(", "Save.add_item(", "Leaderboard.submit(",
        ):
            self.assertNotIn(prohibited, active)

    def test_native_damage_hook_fails_closed_and_preserves_call(self):
        instrument = runpy.run_path(str(RUNNER))["instrument_native_damage"]
        source = ('func damage_enemy(e: Enemy, base: float, src: Player = null) -> void:\n'
                  '\tvar amount: float = base\n'
                  '\te.hurt(amount, Vector3.ZERO)\n'
                  'func other():\n\tpass\n')
        result = instrument(source)
        self.assertIsNotNone(result)
        self.assertEqual(result.count("e.hurt(amount, Vector3.ZERO)"), 1)
        self.assertIn('svv_qa_before - e.hp', result)
        self.assertIn('src.get_instance_id()', result)
        self.assertTrue(result.endswith('func other():\n\tpass\n'))
        self.assertIsNone(instrument(source.replace("src: Player", "src: Object")))
        untyped = instrument(source.replace("src: Player = null", "src = null, extra = null"))
        self.assertIsNotNone(untyped)
        self.assertIn("if src is Player", untyped)
        self.assertIn("if extra is Player", untyped)
        self.assertIn("svv_qa_source_ids.size() == 1", untyped)
        self.assertEqual(untyped.count("e.hurt(amount, Vector3.ZERO)"), 1)
        self.assertIsNone(instrument(source.replace("\te.hurt", "\te.hurt(amount, Vector3.ZERO)\n\te.hurt")))
        self.assertIsNone(instrument(result))
        self.assertIn('native.write_bytes(original)', RUNNER.read_text(encoding="utf-8"))

    def test_candidate_inventory_and_alternate_isolation(self):
        runner = runpy.run_path(str(RUNNER))
        self.assertEqual(runner["parse_candidates"]([
            "MVP_CANDIDATE baphomet supported=true",
            "MVP_CANDIDATE osiris supported=false",
            "MVP_CANDIDATE invalid supported=maybe",
        ]), {"baphomet": True, "osiris": False})
        self.assertEqual(runner["damage_hook_diagnostics"]("func unrelated():\n\tpass\n"),
                         {"header_matched": False})
        code = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('validator.call("supports", candidate)', code)
        self.assertIn("--offline-boss-id=", code)
        source = RUNNER.read_text(encoding="utf-8")
        self.assertIn("boss-alternate-profile-sandbox", source)
        self.assertIn("env=alt_env", source)
        self.assertIn('report["alternate_boss"]', source)

    def test_terminal_observation_does_not_assert_victory_or_rewards(self):
        code = SCRIPT.read_text(encoding="utf-8")
        for label in ("player_zero_hp_observed", "boss_zero_hp_observed",
                      "simultaneous_zero_hp", "node_or_hp_missing_unverified",
                      "world_stopped_unverified", "observation_limit"):
            self.assertIn(label, code)
        self.assertIn("Time.get_ticks_msec() + 20000", code)
        self.assertIn("terminal-observation.png", code)
        source = RUNNER.read_text(encoding="utf-8")
        self.assertIn('"native_death_verified": False', source)
        self.assertIn('"local_rewards_verified": False', source)
        self.assertIn('row.startswith("TERMINAL ")', source)

    def test_runner_isolated_and_does_not_approve_playability(self):
        code = RUNNER.read_text(encoding="utf-8")
        for expected in (
            "XDG_DATA_HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME",
            "SVV_WORLD_BOSS_QA_SANDBOX", "runtime_boss_playable_approved",
            '"status": "not_run"', "world-boss-runtime-qa.json",
            "native_combat_observed", "visual_change_verified",
            "combat_telemetry", '"official_rewards_approved": False',
        ):
            self.assertIn(expected, code)
        installer = INSTALLER.read_text(encoding="utf-8")
        builder = BUILDER.read_text(encoding="utf-8")
        self.assertIn('"world_boss_map_qa"', installer)
        self.assertIn("run-world-boss-map-qa.py", builder)
        self.assertIn('os.environ.get("SVV_WORLD_BOSS_MAP_QA") == "1"', builder)

    def test_combat_probe_never_injects_damage_or_activates_reward_route(self):
        code = SCRIPT.read_text(encoding="utf-8")
        active = "\\n".join(line for line in code.splitlines()
                           if not line.lstrip().startswith("#"))
        for prohibited in (
            "spawned.hurt(", "world.damage_enemy(", "Enemy.hurt(",
            "Save.add_zeny(", "Save.add_item(", "start_world_boss(",
        ):
            self.assertNotIn(prohibited, active)
        self.assertIn('boss_hp_after', code)
        self.assertIn('ai_start_positions', code)
        self.assertIn('boss-after-120frames.png', code)
        self.assertIn('runtime_boss_playable_approved', RUNNER.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
