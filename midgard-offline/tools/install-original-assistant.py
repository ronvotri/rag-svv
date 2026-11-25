"""Install only the authored overlay into an already prepared private project."""
import argparse
import hashlib
from pathlib import Path
import shutil
import sys

def install(project):
    project = project.resolve(strict=True)
    if "work" not in project.parts or not (project / "project.godot").is_file():
        raise ValueError("Expected a private Godot project under work/.")
    source = Path(__file__).resolve().parents[1] / "original-addons/offline_assistant.gd"
    destination = project / "addons/svv_offline/offline_assistant.gd"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    # Authored, style-consistent 4x3 headshot atlas (11 party members + crest).
    # Verify source asset bytes before including them in Windows/Web exports.
    portraits = source.parent / "friend_portraits.jpg"
    if not portraits.is_file() or portraits.stat().st_size != 231582:
        raise ValueError("Friends List portrait atlas missing or unexpected size")
    if hashlib.sha256(portraits.read_bytes()).hexdigest() != "a4f8dd78ccf12fcdb5cab274e6d9ebb1c50b4281aea72252061d9a994857ea6f":
        raise ValueError("Friends List portrait atlas checksum mismatch")
    shutil.copyfile(portraits, destination.parent / portraits.name)
    # Web optimization is a no-op on native platforms; ship one reproducible addon.
    web_perf_source = source.parent / "web_mobile_performance.gd"
    if not web_perf_source.is_file():
        raise ValueError("Authored mobile web optimizer missing")
    shutil.copyfile(web_perf_source, destination.parent / web_perf_source.name)
    map_safe_source = source.parent / "web_map_safe_fit.gd"
    if not map_safe_source.is_file():
        raise ValueError("Authored map safe-fit addon missing")
    shutil.copyfile(map_safe_source, destination.parent / map_safe_source.name)
    # Remove external publisher links from the social strip without changing
    # gameplay or guessing the user's own Discord invite.
    social_source = source.parent / "social_buttons_cleanup.gd"
    if not social_source.is_file():
        raise ValueError("Authored social UI cleanup missing")
    shutil.copyfile(social_source, destination.parent / social_source.name)
    save_manager_source = source.parent / "web_save_manager.gd"
    if not save_manager_source.is_file():
        raise ValueError("Authored save upload/download manager missing")
    shutil.copyfile(save_manager_source, destination.parent / save_manager_source.name)
    fullscreen_option_source = source.parent / "web_fullscreen_options.gd"
    if not fullscreen_option_source.is_file():
        raise ValueError("Web fullscreen Options addon missing")
    shutil.copyfile(fullscreen_option_source, destination.parent / fullscreen_option_source.name)
    mira_source = source.parent / "mira_town.gd"
    if not mira_source.is_file():
        raise ValueError("Authored Mira town NPC addon missing")
    shutil.copyfile(mira_source, destination.parent / mira_source.name)
    companions_source = source.parent / "companions_town.gd"
    if not companions_source.is_file():
        raise ValueError("Authored companion town NPC addon missing")
    shutil.copyfile(companions_source, destination.parent / companions_source.name)
    # Explicitly separate local practice/party simulation from publisher online
    # World Boss health, Festival standings and any official reward paths.
    event_source = source.parent / "offline_events.gd"
    if not event_source.is_file():
        raise ValueError("Local-only event simulator missing")
    shutil.copyfile(event_source, destination.parent / event_source.name)
    mvp_source = source.parent / "offline_mvp_encounter.gd"
    if not mvp_source.is_file():
        raise ValueError("Shared native MVP encounter helper missing")
    shutil.copyfile(mvp_source, destination.parent / mvp_source.name)
    # Gated on --offline-test AND --rare-town-qa; production ignores it.
    rare_town = source.parent / "rare_town_qa.gd"
    if not rare_town.is_file():
        raise ValueError("Wave 28 rare Town QA addon missing")
    shutil.copyfile(rare_town, destination.parent / rare_town.name)
    guardian_source = source.parent / "offline_save_guardian.gd"
    if not guardian_source.is_file():
        raise ValueError("Authored offline save guardian missing")
    shutil.copyfile(guardian_source, destination.parent / guardian_source.name)
    qa = destination.parent / "qa"
    qa.mkdir(exist_ok=True)
    # World Boss runtime scene is never autoloaded or available from game menus.
    for name in ("offline_smoke", "offline_visual", "world_boss_map_qa"):
        own_script = source.parent / (name + ".gd")
        if not own_script.is_file():
            raise ValueError("Authored QA script missing: " + name)
        shutil.copyfile(own_script, qa / own_script.name)
        scene = '[gd_scene load_steps=2 format=3]\n\n[ext_resource type="Script" path="res://addons/svv_offline/qa/' + name + '.gd" id="1"]\n\n[node name="OfflineQA" type="Node"]\nscript = ExtResource("1")\n'
        (qa / (name + ".tscn")).write_text(scene, encoding="utf-8")
    # Audit is a RefCounted helper loaded ONLY by offline_smoke, not an autoload
    # or an in-game scene. It does not create real NPCs.
    rare_audit = source.parent / "rare_job_asset_audit.gd"
    if not rare_audit.is_file():
        raise ValueError("Authored rare-job QA script missing")
    shutil.copyfile(rare_audit, qa / rare_audit.name)
    # Original-frame captures are installed only in the isolated visual-QA
    # subdirectory; no runtime/autoload/production Town change.
    rare_visual = source.parent / "rare_job_visual.gd"
    if not rare_visual.is_file():
        raise ValueError("Authored rare-job visual QA script missing")
    shutil.copyfile(rare_visual, qa / rare_visual.name)
    # Wave 9: off-map Cole/Haneul animation probe, never an autoload or NPC unlock.
    rare_motion = source.parent / "rare_job_motion.gd"
    if not rare_motion.is_file():
        raise ValueError("Authored rare-job motion QA script missing")
    shutil.copyfile(rare_motion, qa / rare_motion.name)
    # Wave 11: original RoAssets.styled_character full-layer evidence.
    # QA-only helper, deliberately not an autoload or production Town actor.
    composed = source.parent / "rare_job_composed.gd"
    if not composed.is_file():
        raise ValueError("Authored rare composed-character QA script missing")
    shutil.copyfile(composed, qa / composed.name)
    config = project / "project.godot"
    text = config.read_text(encoding="utf-8")
    if "[autoload]" not in text:
        raise ValueError("Autoload section missing")
    start = text.index("[autoload]") + len("[autoload]")
    next_section = text.find("\n[", start)
    end = next_section if next_section >= 0 else len(text)
    block = text[start:end]
    for registration in (
        'SVVAssistant="*res://addons/svv_offline/offline_assistant.gd"',
        'SVVMiraTown="*res://addons/svv_offline/mira_town.gd"',
        'SVVCompanionTown="*res://addons/svv_offline/companions_town.gd"',
        'SVVOfflineEvents="*res://addons/svv_offline/offline_events.gd"',
        'SVVRareTownQA="*res://addons/svv_offline/rare_town_qa.gd"',
        'SVVSaveGuardian="*res://addons/svv_offline/offline_save_guardian.gd"',
        'SVVWebMobilePerformance="*res://addons/svv_offline/web_mobile_performance.gd"',
        'SVVWebMapSafeFit="*res://addons/svv_offline/web_map_safe_fit.gd"',
        'SVVSocialCleanup="*res://addons/svv_offline/social_buttons_cleanup.gd"',
        'SVVSaveManager="*res://addons/svv_offline/web_save_manager.gd"',
        'SVVFullscreenOptions="*res://addons/svv_offline/web_fullscreen_options.gd"',
    ):
        if registration not in block:
            block = block.rstrip() + "\n" + registration + "\n"
    new_text = text[:start] + block + text[end:]
    if new_text != text:
        config.write_text(new_text, encoding="utf-8")
    return destination

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    print(install(args.project))
