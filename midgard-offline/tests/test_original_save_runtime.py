"""Execute the real authored manager with isolated encrypted fixtures in Godot.

No publisher files, real save directories or third-party assets are required.
Set SVV_GODOT to a Godot 4.7.2 binary on runners; a local pinned binary is detected.
"""
import os
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / 'fixtures/save-portability'


class SavePortabilityRuntime(unittest.TestCase):
    def test_encrypted_import_preserves_previous_and_rejects_invalid_payload(self):
        candidate = os.environ.get('SVV_GODOT')
        if not candidate:
            pinned = ROOT / 'work/tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe'
            candidate = str(pinned) if pinned.is_file() else shutil.which('godot')
        if not candidate:
            self.skipTest('Godot unavailable; set SVV_GODOT for encrypted runtime QA')
        godot = str(Path(candidate).resolve())
        work = ROOT / 'work'
        work.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='save-qa-', dir=work) as directory:
            project = Path(directory)
            for source in FIXTURES.glob('*.gd'):
                shutil.copyfile(source, project / source.name)
            spec = importlib.util.spec_from_file_location('offline_prepare', ROOT / 'tools/prepare-original-offline.py')
            preparer = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(preparer)
            save_fixture = project / 'save.gd'
            body = save_fixture.read_text(encoding='utf-8')
            body = '\n'.join('\t' * (len(line) - len(line.lstrip(' '))) + line.lstrip(' ')
                             for line in body.splitlines()) + '\n'
            body = body.replace('const VERSION = 1', 'const VERSION = 1\nconst SAVE_KEY = "isolated-qa-only"\nvar TMP_PATH = "user://profile_offline_test.tmp"\nvar BACKUP_PATH = "user://profile_offline_test.bak"')
            save_fixture.write_text(preparer.replace_function(body, 'flush', preparer.offline_save_flush()), encoding='utf-8')
            for name in ('web_save_manager.gd', 'offline_save_guardian.gd'):
                shutil.copyfile(ROOT / 'original-addons' / name, project / name)
            (project / 'project.godot').write_text('''config_version=5
[application]
config/name="SVV Isolated Save QA"
config/use_custom_user_dir=true
config/custom_user_dir_name="SVV-SavePortability-QA"
[autoload]
Save="*res://save.gd"
SVVSaveGuardian="*res://offline_save_guardian.gd"
SVVSaveManager="*res://web_save_manager.gd"
[rendering]
renderer/rendering_method="gl_compatibility"
''', encoding='utf-8')
            env = os.environ.copy()
            # These changes affect only the QA subprocess. Keep every generated
            # save under this disposable work directory, never the player profile.
            env.update(APPDATA=str(project), XDG_DATA_HOME=str(project))
            for arguments in (['--editor', '--import', '--quit'], ['--script', 'qa.gd']):
                result = subprocess.run([godot, '--headless', '--path', str(project), *arguments],
                                        env=env, capture_output=True, text=True, timeout=45,
                                        encoding='utf-8', errors='replace')
                output = result.stdout + result.stderr
                self.assertEqual(result.returncode, 0, output[-5000:])
                self.assertNotIn('SCRIPT ERROR', output, output[-5000:])
            self.assertIn('SAVE_PORTABILITY_QA_OK', output)


if __name__ == '__main__':
    unittest.main()
