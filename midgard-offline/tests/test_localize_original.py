"""Original Godot localization policy regression tests."""
from pathlib import Path
import importlib.util
import json
import tempfile
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools/localize_original.py"
spec = importlib.util.spec_from_file_location("original_l10n", MODULE_PATH)
locale = importlib.util.module_from_spec(spec)
spec.loader.exec_module(locale)


class OriginalLocalization(unittest.TestCase):
    def test_skill_and_item_names_stay_english_but_jobs_are_translated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "work" / "project"
            (root / "scripts/autoload").mkdir(parents=True)
            (root / "scripts/ui").mkdir(parents=True)
            (root / "locale").mkdir()
            (root / "project.godot").write_text("[application]\n", encoding="utf-8")
            (root / "scripts/ui/lang.gd").write_text('const DEFAULT: = "en"\n', encoding="utf-8")
            (root / "scripts/autoload/game_data.gd").write_text(
                'const ITEMS: = {"red": {"name": "Red Potion", "description": "Restores HP"}}\n'
                'const SKILLS: = {"hit": {"name": "Double Attack"}}\n'
                'const CLASSES: = {"mage": {"name": "Mage"}}\n', encoding="utf-8")
            (root / "locale/en.po").write_text(
                'msgid "a"\nmsgstr "Red Potion"\n\n'
                'msgid "b"\nmsgstr "Double Attack"\n\n'
                'msgid "c"\nmsgstr "Mage"\n\n'
                'msgid "d"\nmsgstr "Restores HP"\n\n', encoding="utf-8")
            original = root / "original.json"
            original.write_text(json.dumps({
                "Red Potion": "Thuốc đỏ", "Double Attack": "Song kích",
                "Mage": "Pháp sư", "Restores HP": "Hồi HP",
            }, ensure_ascii=False), encoding="utf-8")
            custom_keep = root / "none.json"
            protected = locale.protected_names(root, custom_keep)
            self.assertTrue({"Red Potion", "Double Attack"} <= protected)
            self.assertNotIn("Mage", protected)
            # Explicitly isolated test patch folder; no repository dictionaries.
            result = locale.localize(root, original, extra_dictionary=custom_keep)
            output = locale.read_po(root / "locale/vi.po")
            self.assertEqual([x["en"] for x in output], ["Red Potion", "Double Attack", "Pháp sư", "Hồi HP"])
            self.assertEqual(result["protected_english_entries"], 2)
            self.assertEqual(result["authored_vietnamese_entries"], 2)

    def test_guest_label_gets_translation_even_without_upstream_po_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "work" / "project"
            (root / "scripts/ui").mkdir(parents=True)
            (root / "locale").mkdir()
            (root / "project.godot").write_text("[application]\n", encoding="utf-8")
            (root / "scripts/ui/lang.gd").write_text('const DEFAULT: = "en"\n', encoding="utf-8")
            (root / "locale/en.po").write_text('msgid "x"\nmsgstr "Play"\n\n', encoding="utf-8")
            dictionary = root / "l10n.json"
            dictionary.write_text(json.dumps({
                "Play": "Chơi", "Guest": "Nhà thám hiểm",
                "Midgard Survivors": "Quái triều xâm lăng"
            }, ensure_ascii=False), encoding="utf-8")
            report = locale.localize(root, dictionary)
            entries = locale.read_po(root / "locale/vi.po")
            localized = {entry["id"]: entry["en"] for entry in entries}
            self.assertEqual(localized["Guest"], "Nhà thám hiểm")
            self.assertEqual(localized["Midgard Survivors"], "Quái triều xâm lăng")
            self.assertEqual(report["supplemental_ui_entries"], 2)

    def test_mobile_skill_descriptions_are_translated_without_renaming_skills(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "work" / "project"
            (root / "scripts/ui").mkdir(parents=True)
            (root / "locale").mkdir()
            (root / "project.godot").write_text("[application]\n", encoding="utf-8")
            (root / "scripts/ui/lang.gd").write_text('const DEFAULT: = "en"\n', encoding="utf-8")
            (root / "locale/en.po").write_text(
                'msgid "Sword Mastery"\nmsgstr "Sword Mastery"\n\n'
                'msgid "description"\nmsgstr "Passive: more sword damage on basic attacks."\n\n',
                encoding="utf-8")
            dictionary = root / "l10n.json"
            dictionary.write_text(json.dumps({
                "Sword Mastery": "Sword Mastery",
                "Passive: more sword damage on basic attacks.":
                    "Nội tại: tăng sát thương kiếm cho các đòn đánh thường.",
                "Lets you evolve: Bash (Lv 5)": "Giúp tiến hóa kỹ năng Bash (cấp 5)."
            }, ensure_ascii=False), encoding="utf-8")
            result = locale.localize(root, dictionary)
            entries = {row["id"]: row["en"] for row in locale.read_po(root / "locale/vi.po")}
            self.assertEqual(entries["Sword Mastery"], "Sword Mastery")
            self.assertIn("tăng sát thương kiếm", entries["description"])
            self.assertEqual(entries["Lets you evolve: Bash (Lv 5)"],
                             "Giúp tiến hóa kỹ năng Bash (cấp 5).")
            self.assertGreaterEqual(result["supplemental_ui_entries"], 1)

    def test_reported_town_dialogue_and_character_labels_are_translated(self):
        root = MODULE_PATH.parents[1]
        translations = locale.load_translations(root / "patches/vi-ui.json")
        self.assertEqual(translations["Class"], "Nghề")
        for key in (
            "Parties (co-op)",
            "I can't gather adventurers in the browser yet: group play is coming soon to this version. I'm already waiting for you on PC and Android!",
            "A pact changes the way you fight. Choose well: you can't have them all at once.",
            "Pact of Fury",
            "+40% attack speed (ASPD) for basic attacks.",
            "Wardrobe",
            "One for your whole account: it shows over your name in Prontera, in the chat and on the rankings.",
            "Select\nCharacter",
            "←/→ or 1-3: choose   ·   Enter or double click: continue   ·   WASD or click: move   ·   Q: equipment & inventory   ·   Esc: pause",
        ):
            self.assertIn(key, translations)
            self.assertNotEqual(translations[key], key)
            self.assertEqual(locale.placeholders(key), locale.placeholders(translations[key]))

    def test_new_quest_skill_and_battle_batches_preserve_formatting(self):
        root = MODULE_PATH.parents[1]
        patches = root / "patches"
        dictionary = locale.load_translations(patches / "vi-ui.json")
        for name in ("vi-ui-batch-008.json", "vi-ui-batch-009.json", "vi-ui-batch-010.json"):
            entries = json.loads((patches / name).read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(entries), 100)
            for source, translated in entries.items():
                self.assertTrue(source and translated)
                self.assertEqual(
                    locale.placeholders(source), locale.placeholders(translated),
                    "Formatting mismatch for " + source
                )
                self.assertEqual(dictionary[source], translated)
        for term in ("Cold Bolt", "Energy Coat", "Klaws", "Prontera", "MVP", "ASPD"):
            self.assertNotIn(term, {
                source for name in ("vi-ui-batch-008.json", "vi-ui-batch-009.json", "vi-ui-batch-010.json")
                for source in json.loads((patches / name).read_text(encoding="utf-8"))
                if source == term
            })

    def test_collection_sets_and_rewards_no_longer_fall_back_to_english(self):
        """Actual strings from the collection screenshot: descriptions get Vietnamese,
        named Ragnarok sets keep their original English names.
        """
        root = MODULE_PATH.parents[1]
        dictionary = locale.load_translations(root / "patches/vi-ui.json")
        required = (
            "The sets, legendaries and uniques you've found in any run.",
            "Sets  %d / %d",
            "Legendaries  %d / %d",
            "Uniques  %d / %d",
            "Poison grows x1.06 per stack (instead of x1.05) and +10% damage",
            "Poison grows x1.08 per stack, each dose adds one more stack and +15% damage",
            "Each skill cuts the others' cooldowns by another 0.1 s, -10% cooldown and +15% skill damage",
            "Each skill cuts the others' cooldowns by another 0.2 s, -10% cooldown and +25% skill damage",
            "Fire jumps to 2 more monsters when a burning one dies, and +10% damage",
            "Your burns burn 60% harder, fire jumps to 2 more monsters and +15% damage",
            "Every bleeding burst heals you 1.5% HP, and +10% attack speed",
            "Bleeding bursts one stack sooner, the burst leaves those it splashes bleeding and +15% attack speed",
            "Your statuses last 50% longer, monsters under a status take another +20% and +10% skill damage",
            "Your status effects last another 50%, monsters with a status effect take another +30% and +15% skill damage",
            "Your basic attack procs trigger 50% more often, all your procs hit 50% harder and +15% attack speed",
            "Your basic attack procs trigger another 50% more often, hit another 50% harder and +15% attack speed",
            "Your when-hit cards trigger 30% more often and hit 20% harder, each heals you another 2%, and +15% max HP",
            "Your when-hit cards trigger another 50% more often and hit another 30% harder, each heals you another 3%, and +20% max HP",
            "Your buffs are another 50% stronger, your heals heal another 30% and -10% cooldown",
            "Your buffs are another 50% stronger, your heals heal another 50% and -10% cooldown",
        )
        for english in required:
            with self.subTest(english=english):
                translated = dictionary.get(english)
                self.assertIsNotNone(translated, "Missing Vietnamese: " + english)
                self.assertNotEqual(translated, english)
                self.assertEqual(locale.placeholders(english), locale.placeholders(translated))
        # Set names are owned by the original game data; no altered set labels.
        for set_name in ("Diabolus: Venom", "Diabolus: Arcane",
                         "Flames of Ifrit", "Vampire Blood", "Dream of Morpheus",
                         "Flame Rings", "Bloody Oath", "Odin's Grace"):
            self.assertNotIn(set_name, dictionary)

    def test_new_collection_and_skill_batches_have_no_placeholder_errors(self):
        root = MODULE_PATH.parents[1]
        patches = root / "patches"
        expected_minimums = {
            "vi-ui-batch-011.json": 50,
            "vi-ui-batch-012.json": 100,
            "vi-ui-batch-013.json": 35,
        }
        merged = locale.load_translations(patches / "vi-ui.json")
        for name, minimum in expected_minimums.items():
            entries = json.loads((patches / name).read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(entries), minimum)
            for english, vietnamese in entries.items():
                self.assertNotEqual(english, vietnamese)
                self.assertEqual(locale.placeholders(english), locale.placeholders(vietnamese),
                                 "Formatting mismatch: " + english)
                self.assertEqual(merged[english], vietnamese)

    def test_collection_audit_detects_real_english_fallback_in_source(self):
        desc = "Poison grows x1.06 per stack (instead of x1.05) and +10% damage"
        catalog = [{"id": "El veneno crece...", "en": desc}]
        untranslated = locale.collection_translation_audit(catalog, {})
        self.assertFalse(untranslated["passed"])
        self.assertEqual(untranslated["untranslated"], [desc])
        translated = locale.collection_translation_audit(catalog, {desc: "Mỗi tầng Độc tăng x1,06."})
        self.assertTrue(translated["passed"])
        self.assertEqual(translated["translated"], 1)
        self.assertEqual(translated["found_in_source"], 1)
        self.assertEqual(translated["required"],
                         len(locale.COLLECTION_SET_DESCRIPTION_KEYS))

    def test_new_town_tower_and_kafra_translation_batches(self):
        """No omitted placeholders or untranslated prose in the four new batches.
        Names of skills, items and places are not rewritten as dictionary keys.
        """
        patches = MODULE_PATH.parents[1] / "patches"
        translations = locale.load_translations(patches / "vi-ui.json")
        expected = {
            "vi-ui-batch-014.json": 137,
            "vi-ui-batch-015.json": 142,
            "vi-ui-batch-016.json": 99,
            "vi-ui-batch-017.json": 117,
        }
        total = 0
        for name, count in expected.items():
            entries = json.loads((patches / name).read_text(encoding="utf-8"))
            self.assertEqual(len(entries), count, name)
            total += count
            for english, vietnamese in entries.items():
                with self.subTest(batch=name, source=english):
                    self.assertNotEqual(english, vietnamese)
                    self.assertEqual(locale.placeholders(english),
                                     locale.placeholders(vietnamese))
                    self.assertEqual(translations[english], vietnamese)
        self.assertEqual(total, 495)
        protected = {
            "Cold Bolt", "Energy Coat", "Prontera", "Kafra",
            "Hollgrehenn", "Lucile", "Valkyrie", "Star Crumb",
            "Double Casting", "Ymir",
        }
        for original_name in protected:
            self.assertNotIn(original_name, translations,
                             "Do not translate source proper name: " + original_name)
        self.assertIn("Sát thương", translations["Damage taken  ·  %s"])
        self.assertIn("Kho", translations["Your Kafra Storage is empty."])
        self.assertIn("tỉ lệ chí mạng", translations[
            "Chance of a critical hit, up to 100%%. Anything past 100%% is not wasted: every extra 1%% is +%d%% crit damage."].lower())

    def test_new_combat_guide_and_skill_localization_both_batches(self):
        """The original names stay English, while player-visible descriptions
        in the newly audited Godot catalog cannot silently fall back.
        """
        root = MODULE_PATH.parents[1]
        patches = root / "patches"
        merged = locale.load_translations(patches / "vi-ui.json")
        total = 0
        for filename, expected in (
            ("vi-ui-batch-018.json", 86),
            ("vi-ui-batch-019.json", 91),
        ):
            entries = json.loads((patches / filename).read_text(encoding="utf-8"))
            self.assertEqual(len(entries), expected)
            total += len(entries)
            for source, translated in entries.items():
                with self.subTest(filename=filename, source=source):
                    self.assertNotEqual(source, translated)
                    self.assertEqual(locale.placeholders(source),
                                     locale.placeholders(translated))
                    self.assertEqual(merged[source], translated)
        self.assertEqual(total, 177)
        for name in ("Bash", "Flying Side Kick", "Peco Peco", "Niflheim",
                     "Star Crumb", "Raging Thrust", "Huuma", "Gatling Fever"):
            self.assertNotIn(name, merged,
                             "Important named game terms must not be localized")
        for source in (
            "On the 9th floor of each stretch comes the shadow of the MVP waiting on the 10th, with one of its mechanics",
            "Tornado Stance: sometimes after a hit you spin, kicking everyone around you and pushing them back.",
            "Passive: your poison, bleed and burn deal more damage.",
        ):
            self.assertIn(source, merged)
            self.assertNotEqual(merged[source], source)

    def test_keep_english_list_contains_core_terminology(self):
        keep = json.loads((MODULE_PATH.parents[1] / "patches/vi-keep-english.json").read_text(encoding="utf-8"))
        for term in ("ASPD", "Flee", "ATK", "DEF", "MVP", "Zeny"):
            self.assertIn(term, keep)


if __name__ == "__main__":
    unittest.main()
