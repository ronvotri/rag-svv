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

    def test_five_recovered_catalog_batches_are_translated_and_safe(self):
        """UI texts from the successful original Web QA 141 catalog.

        These are exact source strings, not invented keys. Prose is translated,
        while proper names, skill names and printf parameters stay stable.
        """
        root = MODULE_PATH.parents[1]
        patches = root / "patches"
        translations = locale.load_translations(patches / "vi-ui.json")
        expected = {
            "vi-ui-batch-021.json": 137,
            "vi-ui-batch-022.json": 147,
            "vi-ui-batch-023.json": 115,
            "vi-ui-batch-024.json": 89,
            "vi-ui-batch-025.json": 109,
        }
        touched = set()
        for filename, count in expected.items():
            entries = json.loads((patches / filename).read_text(encoding="utf-8"))
            self.assertEqual(len(entries), count, filename)
            for english, vietnamese in entries.items():
                with self.subTest(batch=filename, english=english):
                    self.assertNotEqual(english, vietnamese)
                    self.assertNotIn(english, touched, "Duplicate source in current batches")
                    self.assertEqual(locale.placeholders(english),
                                     locale.placeholders(vietnamese))
                    self.assertEqual(translations[english], vietnamese)
                    touched.add(english)
        self.assertEqual(len(touched), 597)
        # These are named game objects, not user-interface prose.
        for name in ("Baphomet", "Naght Sieger", "Poring", "Lucile",
                     "Prontera", "Kafra", "Star Crumb", "Ymir"):
            self.assertNotIn(name, touched)
        for source in (
            "The souls of Niflheim feed him! Stand in their way to break them!",
            "The fallen echo rises! They had to fall together",
            "Your gear, cards and dishes give no bonuses yet.",
            "You have no +%d pieces in the Kafra Storage. Refine one to +%d to grade it.",
        ):
            self.assertIn(source, touched)
            self.assertNotEqual(translations[source], source)

    def test_new_skill_guide_batches_match_source_and_formatting(self):
        """Recovered Godot catalog: guide, skill evolution and glossary."""
        root = MODULE_PATH.parents[1] / "patches"
        translations = locale.load_translations(root / "vi-ui.json")
        expected_counts = {
            "vi-ui-batch-026.json": 35,
            "vi-ui-batch-027.json": 47,
            "vi-ui-batch-028.json": 58,
            "vi-ui-batch-029.json": 57,
            "vi-ui-batch-030.json": 45,
        }
        seen = set()
        for filename, expected in expected_counts.items():
            d = json.loads((root / filename).read_text(encoding="utf-8"))
            self.assertEqual(len(d), expected, filename)
            for english, vietnamese in d.items():
                with self.subTest(filename=filename, source=english):
                    self.assertNotEqual(english, vietnamese)
                    self.assertNotIn(english, seen, "Duplicate translation key")
                    self.assertEqual(locale.placeholders(english),
                                     locale.placeholders(vietnamese))
                    self.assertEqual(translations[english], vietnamese)
                    seen.add(english)
        self.assertEqual(len(seen), 242)
        for protected in ("Baphomet", "MVP", "Quiver", "Kafra", "Star Crumb",
                          "Poring", "Gospel", "Asura Strike", "Homunculus"):
            self.assertNotIn(protected, seen,
                             "Do not replace the name of a game entity")
        self.assertIn("Mỗi điểm STR", translations[
            "Each STR point (physical) or INT point (magic) gives +%s chance for an attack skill to go off twice, up to %s."])
        self.assertEqual(translations["Skill damage"], "Sát thương kỹ năng")

    def test_literal_percentage_in_attribute_placeholder_guard(self):
        self.assertEqual(locale.placeholders("Damage (+X% damage)"), [])
        self.assertEqual(locale.placeholders("Sát thương (+X% sát thương)"), [])
        self.assertEqual(locale.placeholders("+30% chance, and %d more hits"), ["%d"])
        self.assertEqual(locale.placeholders("+30%% chance, and %s more hits"), ["%s"])

    def test_new_upgrades_npc_achievements_cards_and_boss_warnings(self):
        """Audit the exact new strings, formatter tokens and glossary policy."""
        root = MODULE_PATH.parents[1] / "patches"
        translations = locale.load_translations(root / "vi-ui.json")
        expected = {
            "vi-ui-batch-031.json": 33,
            "vi-ui-batch-032.json": 51,
            "vi-ui-batch-033.json": 79,
            "vi-ui-batch-034.json": 40,
            "vi-ui-batch-035.json": 58,
        }
        seen = set()
        for filename, count in expected.items():
            entries = json.loads((root / filename).read_text(encoding="utf-8"))
            self.assertEqual(len(entries), count, filename)
            for source, vietnamese in entries.items():
                with self.subTest(filename=filename, source=source):
                    self.assertNotEqual(source, vietnamese)
                    self.assertNotIn(source, seen)
                    self.assertEqual(locale.placeholders(source),
                                     locale.placeholders(vietnamese))
                    self.assertEqual(translations[source], vietnamese)
                    seen.add(source)
        self.assertEqual(len(seen), 261)
        for protected in ("Baphomet", "Eddga", "Moonlight Flower", "Prontera",
                          "Chingue", "Kafra", "Morroc", "Oridecon", "Eternal Card"):
            self.assertNotIn(protected, seen, "Proper names must stay English")
        self.assertEqual(translations["Gather 10 cards in the album."],
                         "Sưu tập 10 Card trong Bộ sưu tập.")
        self.assertEqual(translations["Brandish Spear: get out from in front of Baphomet!"],
                         "Brandish Spear: tránh khỏi phía trước Baphomet!")

    def test_remaining_abstraction_legendary_unique_and_tower_batches(self):
        """Exact 278 source-key translations recovered from Web QA 162.

        Preserve named RO equipment, skills, MVPs, printf placeholders, and
        verify the produced dictionary contains every translated tooltip.
        """
        root = MODULE_PATH.parents[1] / "patches"
        translations = locale.load_translations(root / "vi-ui.json")
        expected = {
            "vi-ui-batch-036.json": 60,
            "vi-ui-batch-037.json": 42,
            "vi-ui-batch-038.json": 40,
            "vi-ui-batch-039.json": 27,
            "vi-ui-batch-040.json": 39,
            "vi-ui-batch-041.json": 70,
        }
        seen = set()
        for filename, count in expected.items():
            entries = json.loads((root / filename).read_text(encoding="utf-8"))
            self.assertEqual(len(entries), count, filename)
            for source, translated in entries.items():
                with self.subTest(filename=filename, source=source):
                    self.assertNotEqual(source, translated)
                    self.assertNotIn(source, seen, "duplicate key across new batches")
                    self.assertEqual(locale.placeholders(source),
                                     locale.placeholders(translated))
                    self.assertEqual(translations[source], translated)
                    seen.add(source)
        self.assertEqual(len(seen), 278)
        for name in ("Baphomet", "Moonlight Flower", "Oridecon", "Spear Boomerang",
                     "Eternal Card", "Thanatos", "Naght Sieger", "MVP"):
            self.assertNotIn(name, seen)
        self.assertTrue(translations["Baphomet's unique: your basic attack reaps in a crescent around you, and every 7 hits the Demon Lord's scythe falls on everyone around you and heals you for each one ×Lv."].startswith("Unique của Baphomet"))
        self.assertEqual(translations["Open slot"], "Mở ô Card")

    def test_qa182_remaining_boss_and_localization_batches(self):
        """Exact untranslated source strings taken from QA 182 Godot worklist."""
        root = MODULE_PATH.parents[1] / "patches"
        translated = locale.load_translations(root / "vi-ui.json")
        counts = {"vi-ui-batch-042.json": 83,
                  "vi-ui-batch-043.json": 90,
                  "vi-ui-batch-044.json": 66}
        seen = set()
        for name, count in counts.items():
            records = json.loads((root / name).read_text(encoding="utf-8"))
            self.assertEqual(len(records), count, name)
            for original, target in records.items():
                with self.subTest(batch=name, source=original):
                    self.assertNotEqual(original, target)
                    self.assertNotIn(original, seen, "Duplicate new translation key")
                    self.assertEqual(locale.placeholders(original),
                                     locale.placeholders(target))
                    self.assertEqual(translated[original], target)
                    seen.add(original)
        self.assertEqual(len(seen), 239)
        self.assertEqual(translated["Update available!"], "Đã có bản cập nhật!")
        self.assertTrue(translated["Icy Breath: get out from in front of Ktullanux!"].startswith("Icy Breath: tránh"))
        self.assertNotIn("Baphomet", seen)
        self.assertNotIn("Oridecon", seen)

    def test_qa187_guide_cards_map_hints_and_tower_hud(self):
        """Exact source strings selected from Web QA 187 untranslated worklist."""
        root = MODULE_PATH.parents[1] / "patches"
        translated = locale.load_translations(root / "vi-ui.json")
        batches = {
            "vi-ui-batch-045.json": 25,
            "vi-ui-batch-046.json": 69,
            "vi-ui-batch-047.json": 64,
            "vi-ui-batch-048.json": 74,
            "vi-ui-batch-049.json": 36,
        }
        seen = set()
        for name, expected in batches.items():
            records = json.loads((root / name).read_text(encoding="utf-8"))
            self.assertEqual(len(records), expected, name)
            for original, vietnamese in records.items():
                with self.subTest(batch=name, source=original):
                    self.assertNotEqual(original, vietnamese)
                    self.assertNotIn(original, seen, "duplicate new source key")
                    self.assertEqual(locale.placeholders(original),
                                     locale.placeholders(vietnamese))
                    self.assertEqual(translated[original], vietnamese)
                    seen.add(original)
        self.assertEqual(len(seen), 268)
        for game_name in ("MVP", "Oridecon", "Baphomet", "Double Strafe",
                          "Star Crumb", "Holy", "ASPD", "Kafra"):
            self.assertNotIn(game_name, seen)
        self.assertTrue(translated["MVP: Ifrit · Fire creatures of the volcano: use Water"].endswith("dùng Water"))
        self.assertEqual(translated["You fill bosses' Poise %s%% faster"],
                         "Tích Poise của boss nhanh hơn %s%%")

    def test_qa199_followup_combat_npc_and_card_batches(self):
        """All new localized strings must be authored, unique and printf-safe.

        The cloud build also checks every key against recovered en.po so a
        plausible but mistyped English sentence cannot silently go unused.
        """
        root = MODULE_PATH.parents[1] / "patches"
        merged = locale.load_translations(root / "vi-ui.json")
        counts = {
            "vi-ui-batch-050.json": 130,
            "vi-ui-batch-051.json": 75,
        }
        seen = set()
        for filename, count in counts.items():
            records = json.loads((root / filename).read_text(encoding="utf-8"))
            self.assertEqual(len(records), count, filename)
            for english, vietnamese in records.items():
                with self.subTest(filename=filename, source=english):
                    self.assertTrue(english.strip())
                    self.assertTrue(vietnamese.strip())
                    self.assertNotEqual(english, vietnamese)
                    self.assertNotIn(english, seen, "duplicate new source key")
                    self.assertEqual(locale.placeholders(english),
                                     locale.placeholders(vietnamese))
                    self.assertEqual(merged[english], vietnamese)
                    seen.add(english)
        self.assertEqual(len(seen), 205)
        # Names and canonical Ragnarok mechanics stay English.
        for term in ("Baphomet", "Prontera", "Oridecon", "Red Potion",
                     "Double Attack", "Kafra", "MVP", "STR", "AGI"):
            self.assertNotIn(term, seen)

    def test_qa203_legacy_interface_and_privacy_translation_batches(self):
        """Recovered QA 203 exact strings: 217 additional localized entries."""
        root = MODULE_PATH.parents[1] / "patches"
        merged = locale.load_translations(root / "vi-ui.json")
        expected = {
            "vi-ui-batch-052.json": 77,
            "vi-ui-batch-053.json": 119,
            "vi-ui-batch-054.json": 21,
        }
        seen = set()
        for filename, count in expected.items():
            pairs = json.loads((root / filename).read_text(encoding="utf-8"))
            self.assertEqual(len(pairs), count, filename)
            for english, vietnamese in pairs.items():
                with self.subTest(filename=filename, english=english):
                    self.assertTrue(english.strip())
                    self.assertTrue(vietnamese.strip())
                    self.assertNotEqual(english, vietnamese)
                    self.assertNotIn(english, seen)
                    self.assertEqual(locale.placeholders(english),
                                     locale.placeholders(vietnamese))
                    self.assertEqual(merged[english], vietnamese)
                    seen.add(english)
        self.assertEqual(len(seen), 217)
        for protected in ("Prontera", "Baphomet", "Red Potion",
                          "Double Attack", "Eternal Card", "Kafra",
                          "MVP", "ATK", "DEF", "EXP"):
            self.assertNotIn(protected, seen)

    def test_qa203_achievement_title_translations(self):
        """Achievement titles can be localized without renaming Ragnarok gear,
        monster, skill or map names; formatter placeholders must be intact.
        """
        root = MODULE_PATH.parents[1] / "patches"
        merged = locale.load_translations(root / "vi-ui.json")
        rows = json.loads((root / "vi-ui-batch-055.json").read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 70)
        for english, vietnamese in rows.items():
            with self.subTest(english=english):
                self.assertTrue(english.strip() and vietnamese.strip())
                self.assertNotEqual(english, vietnamese)
                self.assertEqual(locale.placeholders(english),
                                 locale.placeholders(vietnamese))
                self.assertEqual(merged[english], vietnamese)
        for unmodified_name in ("Baphomet", "Oridecon", "Prontera",
                                "Double Attack", "Kafra", "MVP", "Red Potion",
                                "Endless Tower", "Eternal Card"):
            self.assertNotIn(unmodified_name, rows)
        self.assertIn("Endless Tower", rows["The End of Endless"])
        self.assertIn("Naght Sieger", rows["Naght Sieger's Bane"])

    def test_qa203_residual_hud_and_status_batch(self):
        """17 genuine untranslated UI/status labels from the recovered catalog."""
        patches = MODULE_PATH.parents[1] / "patches"
        merged = locale.load_translations(patches / "vi-ui.json")
        rows = json.loads((patches / "vi-ui-batch-056.json").read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 17)
        for english, vietnamese in rows.items():
            with self.subTest(english=english):
                self.assertTrue(english.strip() and vietnamese.strip())
                self.assertNotEqual(english, vietnamese)
                self.assertEqual(locale.placeholders(english),
                                 locale.placeholders(vietnamese))
                self.assertEqual(merged[english], vietnamese)
        self.assertEqual(rows[" and "], " và ")
        self.assertIn("Eternal", rows["ETERNAL CARD!"].title())
        self.assertEqual(rows["Sturdy monsters"], "Quái lì đòn")
        for game_name in ("Baphomet", "Oridecon", "Double Attack",
                          "Red Potion", "Prontera", "Kafra"):
            self.assertNotIn(game_name, rows)

    def test_qa216_account_hud_localization_batch_057(self):
        """QA 216 remaining interface strings: real catalog keys, preserved tokens."""
        patches = MODULE_PATH.parents[1] / "patches"
        merged = locale.load_translations(patches / "vi-ui.json")
        rows = json.loads((patches / "vi-ui-batch-057.json").read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 18)
        for english, vietnamese in rows.items():
            with self.subTest(english=english):
                self.assertTrue(english.strip() and vietnamese.strip())
                self.assertNotEqual(english, vietnamese)
                self.assertEqual(locale.placeholders(english),
                                 locale.placeholders(vietnamese))
                self.assertEqual(merged[english], vietnamese)
        self.assertEqual(rows["Nv %d/%d"], "Cấp %d/%d")
        self.assertIn("nearQ", rows["El líder empieza con nearQ"])
        self.assertEqual(rows["Juramento"], "Lời thề")
        self.assertEqual(rows["Postura"], "Thế chiến đấu")
        for protected in ("Baphomet", "Prontera", "Oridecon",
                          "Red Potion", "Double Attack", "Eternal Card"):
            self.assertNotIn(protected, rows)

    def test_advanced_first_job_titles_match_vietnamese_baseline(self):
        """High first-job classes use the same Vietnamese roots as base classes."""
        patches = MODULE_PATH.parents[1] / "patches"
        merged = locale.load_translations(patches / "vi-ui.json")
        rows = json.loads((patches / "vi-ui-batch-058.json").read_text(encoding="utf-8"))
        expected = {
            "High Swordsman": "Kiếm sĩ cao cấp",
            "High Mage": "Pháp sư cao cấp",
            "High Archer": "Cung thủ cao cấp",
            "High Thief": "Đạo tặc cao cấp",
            "High Acolyte": "Tu sĩ cao cấp",
            "High Merchant": "Thương nhân cao cấp",
        }
        self.assertEqual(rows, expected)
        for name, localized in rows.items():
            with self.subTest(name=name):
                self.assertEqual(merged[name], localized)
                self.assertEqual(locale.placeholders(name),
                                 locale.placeholders(localized))
        for name in ("Poring", "Baphomet", "Prontera", "Red Potion",
                     "Double Attack", "Hyper Novice", "Oridecon"):
            self.assertNotIn(name, rows)

    def test_source_spanish_hud_batch_059(self):
        """Verify Spanish-source HUD strings, literal percentages and format slots."""
        patches = MODULE_PATH.parents[1] / "patches"
        merged = locale.load_translations(patches / "vi-ui.json")
        rows = json.loads((patches / "vi-ui-batch-059.json").read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 30)
        for original, localized in rows.items():
            with self.subTest(original=original):
                self.assertTrue(original.strip() and localized.strip())
                self.assertNotEqual(original, localized)
                self.assertEqual(locale.placeholders(original),
                                 locale.placeholders(localized))
                self.assertEqual(merged[original], localized)
        self.assertEqual(rows["+8% de vida"], "+8% HP")
        self.assertEqual(rows["−25% de vida"], "−25% HP")
        self.assertEqual(rows["%+d vida"], "%+d HP")
        self.assertEqual(rows["%d%% FUE · %d%% INT"],
                         "%d%% STR · %d%% INT")
        self.assertEqual(rows["%s  (%s)\\n%d de %d tipos · %s"],
                         "%s  (%s)\\n%d/%d loại · %s")
        for protected in ("Baphomet", "Prontera", "Oridecon",
                          "Red Potion", "Double Attack"):
            self.assertNotIn(protected, rows)

    def test_literal_percent_is_not_printf_argument(self):
        src = ("The orange bar under your HP is your forge: your hits heat the "
               "weapon and when it fills it goes +1. Past the safe limit it "
               "can break (the % is the risk).")
        self.assertEqual(locale.placeholders(src), [])
        self.assertEqual(locale.placeholders("30% is safe"), [])
        self.assertEqual(locale.placeholders("Survive %ds"), ["%d"])
        self.assertEqual(locale.placeholders("On the %dth cut"), ["%d"])
        self.assertEqual(locale.placeholders("Cost %sM zeny"), ["%s"])
        self.assertEqual(locale.placeholders("Works at %d%%, and %s HP"),
                         ["%d", "%s"])

    def test_keep_english_list_contains_core_terminology(self):
        keep = json.loads((MODULE_PATH.parents[1] / "patches/vi-keep-english.json").read_text(encoding="utf-8"))
        for term in ("ASPD", "Flee", "ATK", "DEF", "MVP", "Zeny"):
            self.assertIn(term, keep)


if __name__ == "__main__":
    unittest.main()
