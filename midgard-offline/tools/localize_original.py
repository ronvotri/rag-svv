"""Apply authored Vietnamese UI strings to a locally recovered original project.

Does not redistribute the source catalog. Untranslated entries retain English and
are counted explicitly in a local report. Python standard library only.
"""
from pathlib import Path
import argparse
import ast
import json
import re
import shutil


def read_po(path):
    entries, record, field = [], {}, None
    for line in path.read_text(encoding="utf-8").splitlines() + [""]:
        if line.startswith("msgid "):
            field = "id"
            record[field] = ast.literal_eval(line[6:])
        elif line.startswith("msgstr "):
            field = "en"
            record[field] = ast.literal_eval(line[7:])
        elif line.startswith('"') and field:
            record[field] += ast.literal_eval(line)
        elif not line.strip():
            if record.get("id"):
                entries.append(record)
            record, field = {}, None
    return entries


def placeholders(text):
    # "40% of HP" is prose, not the printf token "% o". Preserve locations
    # while hiding %% so literal percentages cannot masquerade as arguments.
    prepared = text.replace("%%", "  ")
    tokens = []
    for match in re.finditer(r"%(?:\d+\$)?[-+0 #]*\d*(?:\.\d+)?[sdfioxXc]", prepared):
        if match.group().startswith("% ") and match.start() and prepared[match.start()-1].isdigit():
            continue
        tokens.append(match.group())
    return tokens



# Preserve item, skill, pet and card names from the recovered GameData tables. These
# are exact names, NOT substring filters: descriptions are still translated.
PROTECTED_TABLES = ("SKILLS", "ITEMS", "CARDS", "PETS")
KEEP_TERMS_FILE = "vi-keep-english.json"
# Some offline-only UI overrides are new strings, absent from upstream en.po.
# Add these keys to vi.po as well so tr("Guest") does not fall back to English.
SUPPLEMENTAL_UI_KEYS = (
    "Guest", "Guest mode", "Guest account", "Play as guest",
    "Continue as guest", "Midgard Survivors",
    # Skill descriptions exposed by the mobile level-up UI. The names of
    # skills remain English; only explanatory prose is localized.
    "Passive: more sword damage on basic attacks.",
    "Lets you evolve: Bash (Lv 5)",
    "First aid: you heal every few seconds and bandage yourself: a barrier that holds a share of your max HP.",
    "+5D and +3% max HP, more regeneration, -0.5% damage taken, +3% healing received and +0.5% to the barriers you get. Your autocasts when hit grow with the higher of STR and VIT.",
    # Observed Web UI strings absent from upstream en.po on some clients.
    # Supplemental catalog entries help when code calls tr() dynamically.
    "Guard the Chef's cart for 60 s.",
    "Klaws opens a stall in Prontera",
    "Not now",
    "I'll help!",
    "A Golden Poring with treasure! Hit it before it gets away",
    "Magic skills: +15% damage, +6% area and +0.4% chance to cast twice (max 25%).",
    "A recharging energy shield.",
    "Ice shards fall from the sky: they slow enemies and sometimes freeze them.",
)

# Regression contract for the Collections / Sets screen reported by players.
# These are descriptions, never names of the original Ragnarok set items.
COLLECTION_SET_DESCRIPTION_KEYS = (
    "The sets, legendaries and uniques you've found in any run.",
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
)


def collection_translation_audit(entries, translations):
    """Verify that all recognized collection descriptions in this source are
    translated. A changed upstream English catalog is reported, not invented.
    """
    source_strings = {entry.get("en") or entry["id"] for entry in entries}
    matched = [s for s in COLLECTION_SET_DESCRIPTION_KEYS if s in source_strings]
    missing = [s for s in matched if s not in translations or translations[s] == s]
    unknown = [s for s in COLLECTION_SET_DESCRIPTION_KEYS if s not in source_strings]
    return {
        "schema": 1,
        "required": len(COLLECTION_SET_DESCRIPTION_KEYS),
        "found_in_source": len(matched),
        "translated": len(matched) - len(missing),
        "untranslated": missing,
        "not_found_in_this_source_version": unknown,
        "passed": not missing,
        "note": "Only the photographed Collections screen is gated, not complete game localization.",
    }


def protected_names(project, keep_file=None):
    protected = set()
    if keep_file is None:
        keep_file = Path(__file__).resolve().parents[1] / "patches" / KEEP_TERMS_FILE
    if keep_file.is_file():
        values = json.loads(keep_file.read_text(encoding="utf-8"))
        if not isinstance(values, list) or not all(isinstance(x, str) and x for x in values):
            raise ValueError("Keep-English list must be an array of nonempty strings")
        protected.update(values)
    game_data_files = list((project / "scripts").rglob("game_data.gd"))
    if not game_data_files:
        return protected
    content = game_data_files[0].read_text(encoding="utf-8")
    for table in PROTECTED_TABLES:
        expression = r"(?m)^\s*(?:const|static var|var)\s+" + table + r"(?:\s*:[^=\n]+)?\s*=\s*\{"
        match = re.search(expression, content)
        if not match:
            continue
        start = match.end()
        depth = 1
        position = start
        quote = ""
        escaped = False
        while position < len(content) and depth:
            char = content[position]
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = ""
            elif char in ('"', "'"):
                quote = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            position += 1
        if depth:
            raise ValueError("Unbalanced GameData table: " + table)
        block = content[start:position-1]
        # Both name: "..." and "name": "..." are used by authored tables.
        for m in re.finditer(r"""(?<![\w])(?:["']name["']|\bname)\s*:\s*(?:tr\()?["']([^"'\\\n]+)["']""", block):
            protected.add(m.group(1))
    return protected


def load_translations(dictionary, extra_dictionary=None):
    translations = json.loads(dictionary.read_text(encoding="utf-8"))
    files = []
    extra_dictionary = extra_dictionary or dictionary.with_name("vi-ui-extra.json")
    if extra_dictionary.is_file():
        files.append(extra_dictionary)
    files.extend(sorted(dictionary.parent.glob("vi-ui-batch-*.json")))
    for file in files:
        incoming = json.loads(file.read_text(encoding="utf-8"))
        if not isinstance(incoming, dict):
            raise ValueError("Expected translation dictionary: " + file.name)
        for key, value in incoming.items():
            if key in translations and translations[key] != value:
                raise ValueError("Translation conflict for " + key + " in " + file.name)
            translations[key] = value
    return translations


def localize(project, dictionary, regular_font=None, bold_font=None, extra_dictionary=None):
    if not (project / "project.godot").is_file():
        raise ValueError("Thư mục không phải project Godot đã khôi phục.")
    if "work" not in project.resolve().parts:
        raise ValueError("Chỉ áp dụng vào bản project cục bộ dưới thư mục work/.")
    translations = load_translations(dictionary, extra_dictionary)
    preserve = protected_names(project)
    preserved = 0
    entries = read_po(project / "locale/en.po")
    output = ['msgid ""', 'msgstr ""', '"Content-Type: text/plain; charset=UTF-8\\n"', '"Language: vi\\n"', '"Plural-Forms: nplurals=1; plural=0;\\n"', ""]
    translated = 0
    english_fallback = 0
    source_fallback = 0
    for entry in entries:
        english = entry.get("en") or entry["id"]
        if english in preserve:
            vietnamese = english
            preserved += 1
            output += ["msgid " + json.dumps(entry["id"], ensure_ascii=False), "msgstr " + json.dumps(vietnamese, ensure_ascii=False), ""]
            continue
        vietnamese = translations.get(english)
        if vietnamese is not None:
            if placeholders(english) != placeholders(vietnamese):
                raise ValueError("Placeholder không khớp: " + english)
            translated += 1
        else:
            vietnamese = english
            if entry.get("en"):
                english_fallback += 1
            else:
                source_fallback += 1
        output += ["msgid " + json.dumps(entry["id"], ensure_ascii=False), "msgstr " + json.dumps(vietnamese, ensure_ascii=False), ""]
    present_ids = {entry["id"] for entry in entries}
    supplemental_ui_entries = 0
    for key in SUPPLEMENTAL_UI_KEYS:
        value = translations.get(key)
        if value is None or key in present_ids or key in preserve:
            continue
        if placeholders(key) != placeholders(value):
            raise ValueError("Placeholder không khớp: " + key)
        output += ["msgid " + json.dumps(key, ensure_ascii=False), "msgstr " + json.dumps(value, ensure_ascii=False), ""]
        supplemental_ui_entries += 1
    (project / "locale/vi.po").write_text("\n".join(output), encoding="utf-8")
    lang = project / "scripts/ui/lang.gd"
    text = lang.read_text(encoding="utf-8")
    if '"vi": "Tiếng Việt"' not in text:
        text = text.replace('const NATIVE_NAMES: = {', 'const NATIVE_NAMES: = {\n\t"vi": "Tiếng Việt",')
    text = text.replace('const DEFAULT: = "en"', 'const DEFAULT: = "vi"')
    text = text.replace('str(Save.setting(SETTING, ""))', 'str(Save.setting(SETTING, "vi"))')
    if '"res://locale/vi.po"' not in text:
        text = text.replace('const RUNTIME_CATALOGS: = [', 'const RUNTIME_CATALOGS: = ["res://locale/vi.po", ')
    lang.write_text(text, encoding="utf-8")
    for source, name in [(regular_font, "SCDream4.otf"), (bold_font, "SCDream6.otf")]:
        if source:
            shutil.copyfile(source, project / "assets/ro/fonts" / name)
    report = {"catalog_entries": len(entries), "authored_vietnamese_entries": translated, "fallback_entries": len(entries)-translated, "english_fallback_entries": english_fallback, "source_language_fallback_entries": source_fallback, "complete_translation": translated + preserved == len(entries), "protected_english_entries": preserved, "protected_names_count": len(preserve), "supplemental_ui_entries": supplemental_ui_entries}
    (project.parent / "localization-report.private.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--dictionary", type=Path, default=Path(__file__).resolve().parents[1] / "patches/vi-ui.json")
    parser.add_argument("--regular-font", type=Path)
    parser.add_argument("--bold-font", type=Path)
    parser.add_argument("--extra-dictionary", type=Path)
    args = parser.parse_args()
    print(json.dumps(localize(args.project, args.dictionary, args.regular_font, args.bold_font, args.extra_dictionary), ensure_ascii=True))
