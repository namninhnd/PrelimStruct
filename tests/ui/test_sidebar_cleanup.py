from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


def test_quick_presets_removed_from_ui_files():
    for rel_path in ("app.py", "src/ui/sidebar.py"):
        text = _read(rel_path)
        assert "Quick Presets" not in text
        assert "Apply Preset" not in text


def test_wind_controls_located_in_lateral_system():
    for rel_path in ("app.py", "src/ui/sidebar.py"):
        text = _read(rel_path)
        terrain_idx = text.index('"Terrain Category"')
        wind_idx = text.index('"Wind Input Mode"')
        core_idx = text.index('"Core Wall System"')

        assert terrain_idx < wind_idx < core_idx
        assert '"Base Shear Vx (kN)"' in text
        assert '"Base Shear Vy (kN)"' in text
        assert '"Reference Pressure q0 (kPa)"' in text
        assert '"Force Coefficient Cf"' in text


def test_opening_placement_control_exists_for_tube_config():
    for rel_path in ("app.py", "src/ui/sidebar.py"):
        text = _read(rel_path)
        tube_idx = text.index("TUBE_WITH_OPENINGS")
        opening_placement_idx = text.index('"Opening Placement"')
        assert tube_idx < opening_placement_idx


def test_lock_and_fem_wind_cleanup_behavior():
    app_text = _read("app.py")
    sidebar_text = _read("src/ui/sidebar.py")
    fem_views_text = _read("src/ui/views/fem_views.py")

    app_patterns = [
        r'key="sidebar_wind_input_mode"[\s\S]*?disabled=inputs_locked',
        r'key="sidebar_wind_base_shear_x"[\s\S]*?disabled=inputs_locked',
        r'key="sidebar_wind_base_shear_y"[\s\S]*?disabled=inputs_locked',
        r'key="sidebar_wind_reference_pressure_manual"[\s\S]*?disabled=inputs_locked',
        r'key="sidebar_wind_reference_pressure_calc"[\s\S]*?disabled=inputs_locked',
        r'key="sidebar_wind_force_coefficient"[\s\S]*?disabled=inputs_locked',
    ]
    for pattern in app_patterns:
        assert re.search(pattern, app_text)

    sidebar_patterns = [
        r'key="sidebar_module_wind_input_mode"[\s\S]*?disabled=inputs_locked',
        r'key="sidebar_module_wind_base_shear_x"[\s\S]*?disabled=inputs_locked',
        r'key="sidebar_module_wind_base_shear_y"[\s\S]*?disabled=inputs_locked',
        r'key="sidebar_module_wind_reference_pressure_manual"[\s\S]*?disabled=inputs_locked',
        r'key="sidebar_module_wind_reference_pressure_calc"[\s\S]*?disabled=inputs_locked',
        r'key="sidebar_module_wind_force_coefficient"[\s\S]*?disabled=inputs_locked',
    ]
    for pattern in sidebar_patterns:
        assert re.search(pattern, sidebar_text)

    assert '"Wind Loads (Read-only)"' in fem_views_text
    assert '"🔓 Unlock to Modify"' in fem_views_text
    assert "disabled=not is_locked" in fem_views_text
    assert "Run analysis to lock inputs" not in fem_views_text
    assert '"Input Mode"' not in fem_views_text
    assert "fem_wind_input_mode" not in fem_views_text
