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

    def test_keep_english_list_contains_core_terminology(self):
        keep = json.loads((MODULE_PATH.parents[1] / "patches/vi-keep-english.json").read_text(encoding="utf-8"))
        for term in ("ASPD", "Flee", "ATK", "DEF", "MVP", "Zeny"):
            self.assertIn(term, keep)


if __name__ == "__main__":
    unittest.main()
