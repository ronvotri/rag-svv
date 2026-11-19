#!/usr/bin/env python3
"""Prepare a private, offline-only copy of a recovered Godot project.

This utility contains no original game scripts, assets, or credentials. The source
directory must be a local GDRE recovery supplied by the user. Output stays local.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


def replace_function(text: str, name: str, body: str) -> str:
    """Replace one simple GDScript function body; preserve following constants."""
    lines = text.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines)
               if re.match(r"^(?:static )?func " + re.escape(name) + r"\(", line)]
    if len(matches) != 1:
        raise ValueError(f"Expected one function {name}, found {len(matches)}")
    start = matches[0]
    if not lines[start].rstrip().endswith(":"):
        raise ValueError(f"Unsupported multiline function signature: {name}")
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line.strip() and not line[0].isspace() and not line.startswith("#"):
            end = index
            break
    replacement = lines[start].rstrip() + "\n" + "\n".join("\t" + row if row else "" for row in body.splitlines()) + "\n\n"
    return "".join(lines[:start]) + replacement + "".join(lines[end:])


def block_shell_calls(text: str) -> tuple[str, int]:
    count = 0
    marker = "OS.shell_open("
    while marker in text:
        start = text.index(marker)
        position = start + len(marker)
        depth, quote, escaped = 1, "", False
        while position < len(text) and depth:
            char = text[position]
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = ""
            elif char in "\"'":
                quote = char
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            position += 1
        if depth:
            raise ValueError("Unbalanced OS.shell_open call")
        text = text[:start] + "(func(): return ERR_UNAVAILABLE).call()" + text[position:]
        count += 1
    return text, count


def set_setting(text: str, section: str, key: str, value: str) -> str:
    section_marker = f"[{section}]"
    if section_marker not in text:
        return text.rstrip() + f"\n\n{section_marker}\n\n{key}={value}\n"
    start = text.index(section_marker) + len(section_marker)
    end = text.find("\n[", start)
    if end < 0:
        end = len(text)
    block = text[start:end]
    entry = re.compile(r"^" + re.escape(key) + r"=.*$", re.MULTILINE)
    block = entry.sub(f"{key}={value}", block) if entry.search(block) else block.rstrip() + f"\n{key}={value}\n"
    return text[:start] + block + text[end:]



def offline_party_bootstrap() -> str:
    """Spawn only recruited NPC jobs selected from Friends List; new saves start solo.

    Previously saved class-only parties are not automatically considered friends.
    CLI overrides cannot bypass recruitment in a production or QA build.
    """
    return "\n".join([
        '\tvar saved_offline_party = Save.setting("svv_offline_party", [])',
        '\tvar recruited_friends = Save.setting("svv_offline_friends", [])',
        '\tif not saved_offline_party is Array:',
        '\t\tsaved_offline_party = []',
        '\tif not recruited_friends is Array:',
        '\t\trecruited_friends = []',
        '\tcoop_classes.clear()',
        '\tfor candidate in saved_offline_party:',
        '\t\tvar offline_class: String = str(candidate)',
        '\t\tif recruited_friends.has(offline_class) and GameData.CLASSES.has(offline_class) and not coop_classes.has(offline_class) and coop_classes.size() < 3:',
        '\t\t\tcoop_classes.append(offline_class)',
        '\t_build_scene()',
    ])

def patch_party_run_save(text: str) -> str:
    """Extend existing per-hero snapshots to an offline AI party."""
    if '"offline_party"' in text:
        raise ValueError("Party run-save patch already applied")
    # 0.1.x used hero_snapshot(w) and an implicit local player binding.
    # Official 0.2.0 already supports hero_snapshot(w, hero = null), which is
    # precisely what the offline-party records need. Preserve the original
    # implementation when this newer, per-hero interface is present.
    legacy_signature = re.search(
        r"static func hero_snapshot\(w:\s*World\)\s*->\s*Dictionary\s*:", text)
    new_signature = re.search(
        r"static func hero_snapshot\(w:\s*World,\s*hero:\s*Player\s*=\s*null\)\s*->\s*Dictionary\s*:", text)
    if legacy_signature and not new_signature:
        text, count = re.subn(
            r"(static func hero_snapshot\(w:\s*World)(\)\s*->\s*Dictionary\s*:)",
            r"\1, p: Player = null\2", text, count=1)
        if count != 1:
            raise ValueError("Legacy hero snapshot signature patch was ambiguous")
        start = text.index("static func hero_snapshot(")
        end = text.find("\nstatic func ", start + 1)
        if end < 0:
            end = len(text)
        block = text[start:end]
        block, count = re.subn(
            r"\tvar p:\s*= w\.player\s*\n",
            "\tif p == null:\n\t\tp = w.player\n", block, count=1)
        if count != 1:
            raise ValueError("Legacy hero snapshot player binding changed")
        text = text[:start] + block + text[end:]
    elif new_signature and not legacy_signature:
        start = text.index("static func hero_snapshot(")
        end = text.find("\nstatic func ", start + 1)
        if end < 0:
            end = len(text)
        body = text[start:end].partition("\n")[2]
        # A dummy new argument that is never used would silently save the
        # wrong party member. Require actual per-hero use before patching.
        if not re.search(r"(?m)^\s+[^#\n]*\bhero\b", body):
            raise ValueError("0.2.0 hero snapshot ignores explicit hero argument")
    else:
        signatures = re.findall(
            r"^(?:static )?func hero_snapshot[^\r\n]*", text, re.MULTILINE)
        raise ValueError(
            "Unsupported hero snapshot signature: " + repr(signatures[:2]))
    if "or w.is_coop():" not in text:
        raise ValueError("Run-save co-op guard changed")
    text = text.replace('or w.is_coop():', 'or w.net.mode != "":', 1)
    anchor = "\tvar tmp: = path() + \".tmp\""
    if anchor not in text:
        raise ValueError("Run-save write anchor changed")
    text = text.replace(anchor, '\n'.join([
        '\tvar offline_party: Array = []',
        '\tfor offline_hero in w.heroes:',
        '\t\tif offline_hero == w.player:',
        '\t\t\tcontinue',
        '\t\tvar offline_record: Dictionary = hero_snapshot(w, offline_hero)',
        '\t\toffline_record["offline_hp"] = offline_hero.hp',
        '\t\toffline_record["offline_downed"] = offline_hero.downed',
        '\t\toffline_record["offline_revive_t"] = offline_hero.revive_t',
        '\t\toffline_party.append(offline_record)',
        '\td["offline_party"] = offline_party',
        anchor,
    ]), 1)
    anchor = '\tw.start_run(str(d["class"]))'
    if anchor not in text:
        raise ValueError("Resume start anchor changed")
    text = text.replace(anchor, '\n'.join([
        '\tvar offline_party: Array = d.get("offline_party", [])',
        '\tif d.has("offline_party"):',
        '\t\tw.coop_classes.clear()',
        '\t\tfor offline_record in offline_party.slice(0, 3):',
        '\t\t\tif offline_record is Dictionary and GameData.CLASSES.has(str(offline_record.get("class", ""))):',
        '\t\t\t\tw.coop_classes.append(str(offline_record["class"]))',
        anchor,
    ]), 1)
    anchor = '\tapply_hero(w, d)'
    if anchor not in text:
        raise ValueError("Resume hero anchor changed")
    text = text.replace(anchor, '\n'.join([
        anchor,
        '\tfor offline_index in mini(offline_party.size(), maxi(0, w.heroes.size() - 1)):',
        '\t\tvar offline_record: Dictionary = offline_party[offline_index]',
        '\t\tvar offline_hero: Player = w.heroes[offline_index + 1]',
        '\t\tapply_hero(w, offline_record, offline_hero, false)',
        '\t\toffline_hero.downed = bool(offline_record.get("offline_downed", false))',
        '\t\toffline_hero.hp = 0.0 if offline_hero.downed else clampf(float(offline_record.get("offline_hp", offline_hero.max_hp)), 1.0, offline_hero.max_hp)',
        '\t\toffline_hero.revive_t = maxf(0.0, float(offline_record.get("offline_revive_t", 0.0)))',
    ]), 1)
    return text


def patch_main_town_place(text: str) -> str:
    """Tag the actual city request so authored NPCs never bleed into other towns."""
    if 'svv_offline_town_place' in text:
        raise ValueError("Town metadata patch already applied")
    header = re.search(r'(?m)^func enter_town\([^\n]*\)\s*->\s*void\s*:\s*$', text)
    if header is None:
        raise ValueError("Original enter_town signature changed; inspect source")
    end = text.find("\n", header.start())
    if end < 0:
        raise ValueError("Original enter_town has no function body")
    return text[:end + 1] + '\tset_meta("svv_offline_town_place", str(place))\n' + text[end + 1:]


def prepare(source: Path, output: Path, vi_catalog: Path | None = None) -> dict:
    source = source.resolve(strict=True)
    output = output.resolve()
    if not (source / "project.godot").is_file():
        raise ValueError("Source must contain recovered project.godot")
    if output == source or source in output.parents or output in source.parents:
        raise ValueError("Source and output must be separate sibling directories")
    if output.exists():
        raise ValueError("Output already exists; choose a new directory")
    if vi_catalog is not None:
        vi_catalog = vi_catalog.resolve(strict=True)
        if vi_catalog.stat().st_size > 5_000_000:
            raise ValueError("Translation catalog exceeds 5 MB")

    def ignore(directory: str, names: list[str]) -> list[str]:
        ignored = [name for name in names if name in {".godot", "credentials.cfg"}]
        if Path(directory).name == "addons":
            ignored.extend(name for name in names if name == "epic-online-services-godot")
        return ignored

    shutil.copytree(source, output, ignore=ignore)
    # Preserve original imported resource payloads, but never native-extension
    # registries, editor state, or script caches. This retains fidelity and avoids
    # expensive reconstruction of already-compatible Godot 4.7 map scenes.
    imported = source / ".godot/imported"
    if imported.is_dir():
        shutil.copytree(imported, output / ".godot/imported", dirs_exist_ok=True)
    changes: list[dict] = []

    def patch(relative: str, functions: dict[str, str]) -> None:
        file = output / relative
        original = file.read_text(encoding="utf-8")
        content = original
        for name, body in functions.items():
            content = replace_function(content, name, body)
        file.write_text(content, encoding="utf-8", newline="\n")
        changes.append({"file": relative, "functions": list(functions), "source_sha256": hashlib.sha256(original.encode()).hexdigest()})

    patch("scripts/autoload/updater.gd", {"_enabled": "return false"})
    patch("scripts/core/cloud_save.gd", {"_enabled": "return false"})
    patch("scripts/core/leaderboard.gd", {
        "enabled": "return false",
        "_ready": "process_mode = Node.PROCESS_MODE_ALWAYS",
        "_call": "if done.is_valid():\n\tdone.call_deferred(false, null)",
    })
    # Every account/login entry point goes to the original offline class selector.
    # This also handles the Back button on character selection.
    patch("scripts/ui/menus.gd", {
        "_ask_notes": "pass",
        "show_login": "show_class_select()",
    })
    patch("scripts/net/net_sync.gd", {"eos": "return null", "host": "return false", "join": "return false"})
    patch("scripts/net/town_channel.gd", {"join_enet": "return false"})
    patch("scripts/net/channel_bot.gd", {"connect_now": "pass"})
    # The original test --coop flag resets profiles. Use a permanent, isolated
    # save instead and a distinct flag that never enters the test-profile branch.
    patch("scripts/autoload/save.gd", {"_ready": "\n".join([
        "process_mode = Node.PROCESS_MODE_ALWAYS",
        '_name = "profile_offline_test" if "--offline-test" in OS.get_cmdline_user_args() else "profile_offline"',
        'PATH = "user://%s.json" % _name',
        'TMP_PATH = "user://%s.tmp" % _name',
        'BACKUP_PATH = "user://%s.bak.json" % _name',
        'var svv_guard = load("res://addons/svv_offline/offline_save_guardian.gd")',
        "svv_guard.restore_missing_profile(PATH, _name)",
        "load_profile()",
        "Lang.apply_saved()",
    ])})
    main = output / "scripts/core/main.gd"
    text = main.read_text(encoding="utf-8")
    anchor = "\t_build_scene()"
    if anchor not in text:
        raise ValueError("Main scene boot anchor missing")
    party = offline_party_bootstrap()
    main.write_text(text.replace(anchor, party, 1), encoding="utf-8", newline="\n")
    text = main.read_text(encoding="utf-8")
    text = patch_main_town_place(text)
    text = text.replace('if coop_classes.is_empty() and net.mode == "":', 'if net.mode == "":', 1)
    text = re.sub(r'if not is_coop\(\):\n(\s+)RunSave\.clear\(\)', r'if net.mode == "":\n\1RunSave.clear()', text)
    main.write_text(text, encoding="utf-8", newline="\n")
    # Keep the ORIGINAL _opening_screens. The preparation-screen action calls
    # start_run(class_id, true), which reaches _opening_screens during combat
    # startup. Overriding it to show_class_select caused "To adventure!" to
    # jump back to the menu instead of finishing battle initialization.
    # Offline login is redirected by the patched menus.show_login above.
    # A second regression was possible when a stale login/class-select overlay
    # survived the preparation callback even after the real battle started.
    # Only dismiss these impossible *online/pre-run* overlays. Never auto-close
    # stage selection, leveling, pause or tutorial dialogs here.
    opening_anchor = "\t_opening_screens(choose_start)"
    if text.count(opening_anchor) != 1:
        raise ValueError("Original battle opening anchor changed; inspect source")
    before, sep, after = text.partition(opening_anchor)
    # The preceding update was written before this guard is inserted.
    text = before + opening_anchor + "\n" + "\n".join([
        '\tif net.mode == "" and running and menus != null:',
        '\t\tif menus._mode in ["login", "server_select", "class_select"]:',
        '\t\t\tmenus.close()',
        '\t\t\tget_tree().paused = false',
    ]) + after
    main.write_text(text, encoding="utf-8", newline="\n")
    assets = output / "scripts/autoload/ro_assets.gd"
    content = assets.read_text(encoding="utf-8")
    audio_anchor = 'var path: = ROOT + "audio/%s.wav" % key'
    if content.count(audio_anchor) != 1:
        raise ValueError("Audio lookup path changed")
    assets.write_text(content.replace(audio_anchor, audio_anchor + ".to_lower()", 1), encoding="utf-8", newline="\n")
    run_save = output / "scripts/core/run_save.gd"
    run_save.write_text(patch_party_run_save(run_save.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    # No native EOS dependencies or developer-only networking diagnostics.
    (output / "scripts/net/eos_net.gd").write_text('extends Node\n# Offline build: EOS is intentionally unavailable.\n', encoding="utf-8")
    (output / "scripts/ui/debug_menu.gd").write_text('class_name DebugMenu\nextends Node\n\nfunc _init(_world = null):\n\tpass\n\nstatic func enabled() -> bool:\n\treturn false\n', encoding="utf-8")
    links = 0
    for file in (output / "scripts").rglob("*.gd"):
        original = file.read_text(encoding="utf-8")
        text, count = block_shell_calls(original)
        if count:
            file.write_text(text, encoding="utf-8", newline="\n")
            links += count

    config = output / "project.godot"
    settings = config.read_text(encoding="utf-8")
    settings = re.sub(r'^\w+="\*res://addons/epic-online-services-godot/[^\n]*\n', "", settings, flags=re.MULTILINE)
    settings = re.sub(r'^enabled=PackedStringArray\([^\n]*epic-online-services-godot[^\n]*\)\n', "enabled=PackedStringArray()\n", settings, flags=re.MULTILINE)
    settings = set_setting(settings, "application", "config/name", '"Ragnarok: Quái Vật Trỗi Dậy"')
    settings = set_setting(settings, "application", "config/use_custom_user_dir", "true")
    settings = set_setting(settings, "application", "config/custom_user_dir_name", '"VotriValley/MidgardSVVOffline"')
    settings = set_setting(settings, "rendering", "renderer/rendering_method", '"gl_compatibility"')
    settings = set_setting(settings, "rendering", "renderer/rendering_method.mobile", '"gl_compatibility"')
    if vi_catalog:
        shutil.copyfile(vi_catalog, output / "locale/vi.po")
        pattern = re.compile(r'^(locale/translations=PackedStringArray\()(.*)(\))$', re.MULTILINE)
        match = pattern.search(settings)
        if match:
            contents = match.group(2)
            if '"res://locale/vi.po"' not in contents:
                contents += (", " if contents else "") + '"res://locale/vi.po"'
                settings = settings[:match.start()] + match.group(1) + contents + match.group(3) + settings[match.end():]
        else:
            settings = set_setting(settings, "internationalization", "locale/translations", 'PackedStringArray("res://locale/vi.po")')
        lang = output / "scripts/ui/lang.gd"
        contents = lang.read_text(encoding="utf-8")
        contents = re.sub(r'^(const DEFAULT\s*:?\s*=\s*)"[^"]+"', r'\1"vi"', contents, flags=re.MULTILINE)
        lang.write_text(contents, encoding="utf-8", newline="\n")
        settings = set_setting(settings, "internationalization", "locale/fallback", '"vi"')
    config.write_text(settings, encoding="utf-8", newline="\n")
    # A copy may include previous GDRE logs; keep the project output private.
    report = {"schema": 1, "offline_profile": "profile_offline", "source_project_sha256": hashlib.sha256((source / "project.godot").read_bytes()).hexdigest(), "changes": changes, "blocked_shell_calls": links, "translation": "vi" if vi_catalog else None, "runtime_tested": False}
    (output / "offline-patch-report.private.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--vi-catalog", type=Path)
    args = parser.parse_args()
    try:
        result = prepare(args.source, args.output, args.vi_catalog)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Error: {error}\n")
    print(f"Prepared {len(result['changes'])} patches; {result['blocked_shell_calls']} external links blocked. Runtime verification still required.")


if __name__ == "__main__":
    main()
