"""Install only the authored overlay into an already prepared private project."""
import argparse
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
    qa = destination.parent / "qa"
    qa.mkdir(exist_ok=True)
    for name in ("offline_smoke", "offline_visual"):
        own_script = source.parent / (name + ".gd")
        if not own_script.is_file():
            raise ValueError("Authored QA script missing: " + name)
        shutil.copyfile(own_script, qa / own_script.name)
        scene = '[gd_scene load_steps=2 format=3]\n\n[ext_resource type="Script" path="res://addons/svv_offline/qa/' + name + '.gd" id="1"]\n\n[node name="OfflineQA" type="Node"]\nscript = ExtResource("1")\n'
        (qa / (name + ".tscn")).write_text(scene, encoding="utf-8")
    config = project / "project.godot"
    text = config.read_text(encoding="utf-8")
    line = 'SVVAssistant="*res://addons/svv_offline/offline_assistant.gd"'
    if line not in text:
        if "[autoload]" not in text:
            raise ValueError("Autoload section missing")
        text = text.replace("[autoload]", "[autoload]\n\n" + line, 1)
        # Save must initialize first; append assistant after existing autoloads.
        text = text.replace("\n" + line, "", 1)
        start = text.index("[autoload]")
        end = text.find("\n[", start + 1)
        if end < 0:
            text = text.rstrip() + "\n" + line + "\n"
        else:
            text = text[:end].rstrip() + "\n" + line + "\n\n" + text[end:]
        config.write_text(text, encoding="utf-8")
    return destination

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    print(install(args.project))
