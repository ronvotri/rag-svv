"""Regression checks for mobile/fullscreen layout and offline save file flow."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ADDONS = ROOT / "original-addons"


class TestOfflineWebSaveAndUI(unittest.TestCase):
    def test_export_csp_allows_godot_save_bridge_without_external_network(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / 'project.godot').write_text('config_version=5\n', encoding='utf-8')
            subprocess.run([sys.executable, ROOT / 'tools/create-original-presets.py', project, project],
                           check=True, capture_output=True)
            preset = (project / 'export_presets.cfg').read_text(encoding='utf-8')
            policy = next(line for line in preset.splitlines() if line.startswith('html/head_include='))
            # wasm-unsafe-eval alone does not permit JavaScriptBridge.eval.
            self.assertIn("script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval' 'unsafe-eval'", policy)
            self.assertIn("connect-src 'self' blob:", policy)
            self.assertNotIn('https:', policy)

    def test_save_tools_visible_from_menu_and_paused_in_battle(self):
        src = (ADDONS / "web_save_manager.gd").read_text(encoding="utf-8")
        self.assertIn('open_button.text = "Sao lưu" if compact else "Sao lưu / Nạp save"', src)
        self.assertIn('var compact: bool = size.x < 680.0', src)
        self.assertIn('var toolbar_y: float = 68.0 if OS.has_feature("web") else (56.0 if narrow else 10.0)', src)
        self.assertIn('open_button.position = Vector2(start_x + friend_width + 8.0, toolbar_y)', src)
        self.assertIn('button.add_theme_stylebox_override("normal", normal)', src)
        friends = (ADDONS / "offline_assistant.gd").read_text(encoding="utf-8")
        self.assertIn('open_button.position = Vector2(start_x, toolbar_y)', friends)
        self.assertIn('var toolbar_y: float = 68.0 if OS.has_feature("web") else (56.0 if narrow else 10.0)', friends)
        self.assertIn('_style_toolbar_button(open_button)', friends)
        self.assertIn("open_button.pressed.connect(open_manager)", src)
        self.assertIn("open_button.visible = not in_battle", src)
        self.assertIn('dialog.popup_centered(_popup_size(', src)
        self.assertIn('confirm_import.popup_centered(_popup_size(', src)
        self.assertIn('get_viewport().size_changed.connect(_fit_button)', src)

    def test_json_export_has_format_version_and_integrity(self):
        src = (ADDONS / "web_save_manager.gd").read_text(encoding="utf-8")
        for marker in (
            'const JSON_FORMAT := "rag-svv-offline-save"',
            "const JSON_VERSION := 1",
            '"encoding": "base64"',
            '"sha256": checksum',
            '"payload": Marshalls.raw_to_base64(bytes)',
            'new Blob([b],{type:\'application/json\'})',
            '"Ragnarok-Quai-Vat-Troi-Day-"',
            'if _sha256(bytes) != str(container.get("sha256", "")).to_lower():',
            'if not SVVSaveGuardian._write_atomically(_before_import_path(), old_data):',
            'SVVSaveGuardian.adopt_imported_profile(bytes)',
            'SVVSaveGuardian._write_atomically(_save_path(), old_data)',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, src)
        self.assertIn("picker.accept='.json,.svvsave'", src)
        self.assertIn("JSON.parse_string(encoded)", src)
        self.assertIn("MAX_SAVE_BYTES", src)
        self.assertIn('window.location.reload', src)
        self.assertIn('FS.syncfs(false', src)
        self.assertIn('func _validated_profile', src)
        self.assertIn('Save._read(VALIDATION_PATH)', src)
        self.assertNotIn("fetch(", src)
        self.assertNotIn("XMLHttpRequest", src)

    def test_mobile_text_and_fullscreen_bounds(self):
        perf = (ADDONS / "web_mobile_performance.gd").read_text(encoding="utf-8")
        safe = (ADDONS / "web_map_safe_fit.gd").read_text(encoding="utf-8")
        self.assertIn("const TEXT_SCALE := 1.5", perf)
        self.assertIn("Window.CONTENT_SCALE_ASPECT_KEEP", perf)
        self.assertNotIn("Window.CONTENT_SCALE_ASPECT_EXPAND", perf)
        self.assertIn("EDGE_PADDING := 18.0", safe)
        self.assertIn("BOTTOM_HINT_PADDING := 34.0", safe)
        self.assertIn("func _is_region_menu_visible(", safe)
        self.assertIn("func _find_world_select_root(", safe)
        self.assertIn('ends_with("/world_select.gd")', safe)
        self.assertIn("if _find_world_select_root(root) != null:", safe)
        self.assertIn("Prontera Field", safe)
        self.assertIn("Prontera Culvert", safe)
        self.assertIn("func _shared_control_parent(", safe)
        self.assertIn("get_global_rect()", safe)
        self.assertIn("func _reset_fit()", safe)
        self.assertIn('if not OS.has_feature("web"):', safe)

    def test_addons_installed_in_original_private_godot_project(self):
        install = (ROOT / "tools" / "install-original-assistant.py").read_text(encoding="utf-8")
        for name in ("web_save_manager.gd", "web_mobile_performance.gd",
                     "web_map_safe_fit.gd", "offline_save_guardian.gd"):
            self.assertIn(name, install)
        self.assertIn('SVVSaveManager="*res://addons/svv_offline/web_save_manager.gd"', install)
        self.assertIn('SVVWebMapSafeFit="*res://addons/svv_offline/web_map_safe_fit.gd"', install)

    def test_npc_help_links_to_real_download_upload_flow(self):
        npc = (ADDONS / "offline_assistant.gd").read_text(encoding="utf-8")
        self.assertIn("Sao lưu / Nạp save", npc)
        self.assertIn("Tải save về máy (JSON)", npc)
        self.assertIn("Nạp save từ máy (JSON)", npc)
        self.assertIn("Save không tự đồng bộ lên mạng", npc)


if __name__ == "__main__":
    unittest.main()
