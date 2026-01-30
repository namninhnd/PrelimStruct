# PrelimStruct v3.6 Upgrade Plan (UI + Backend Refactors)

## Context

### Original Request
Reorganize V3.6 upgrade planning into a 9-track structure with fine-grained sub-tasks for smoother execution.

### Scope Summary
- **UI Consolidation**: Merge 3 redundant view systems into ONE unified Plotly-based visualization (built on `src/fem/visualization.py` `create_*_view()`); opsvis remains an optional extraction backend
- **Theme**: Gemini-style dark mode with consistent typography
- **app.py Modularization**: Split ~2,444-line monolith into UI modules (<500 lines target)
- **Backend Refactors**: model_builder.py, visualization.py, ai/providers.py
- **Testing**: TDD/characterization-first approach throughout

### Guardrails (from Metis Review)
- NO new features (refactoring only)
- NO solver/engine logic changes
- NO changes to `src/engines/**` calculation logic
- NO new Python dependencies unless explicitly approved
- Preserve all existing public API signatures
- Capture before/after screenshots for visual changes
- Branch/rollback strategy: do all work on `feature/v36-upgrade`; merge to main only after Track 9 passes (tests + perf + UI smoke)

---

## Track 1: Baselines & Evidence

**Purpose**: Establish measurable baselines before any refactoring begins.
**Blocking**: All other tracks depend on Track 1 completion.
**Effort**: ~2 hours

### 1.1 Create Evidence Directory Structure

**What to do**:
- Create `.sisyphus/evidence/` directory if missing
- Create `scripts/` directory for benchmark scripts

**Commands**:
```powershell
New-Item -ItemType Directory -Force .sisyphus/evidence | Out-Null
New-Item -ItemType Directory -Force scripts | Out-Null
```

**Acceptance Criteria**:
- [x] `.sisyphus/evidence/` directory exists
- [x] `scripts/` directory exists

**Parallelizable**: YES (with nothing - first task)
**Commit**: NO (groups with 1.2)

---

### 1.2 Capture Test & Coverage Baseline

**What to do**:
- Run full pytest suite and capture results
- Run coverage report and save to evidence file
- Record the "TOTAL" summary line for later comparison

**Commands**:
```powershell
pytest tests/ --tb=short -q | Tee-Object -FilePath .sisyphus/evidence/v36-test-baseline.txt
pytest --cov=src --cov-report=term-missing | Tee-Object -FilePath .sisyphus/evidence/v36-coverage-baseline.txt
```

**References**:
- `pytest.ini` - Test configuration
- `tests/` - All test files

**Acceptance Criteria**:
- [x] `pytest` → All tests pass (record the total collected/passed from the baseline output; do not assume a fixed count)
- [x] `.sisyphus/evidence/v36-test-baseline.txt` contains test results
- [x] `.sisyphus/evidence/v36-coverage-baseline.txt` contains coverage report with TOTAL line

**Parallelizable**: NO (depends on 1.1)
**Commit**: YES
- Message: `chore(v36): capture test and coverage baselines`
- Files: `.sisyphus/evidence/v36-*.txt`

---

### 1.3 Inventory Session State Keys

**What to do**:
- Search `app.py` for all `st.session_state` usage
- Document each key: name, line number, data type, purpose
- Save inventory to evidence file

**Known keys from research** (24 total):
| Key | Lines | Purpose |
|-----|-------|---------|
| `project` | 981-983, 1713 | Main ProjectData container |
| `selected_combinations` | 1597-1710 | Active load combinations (set) |
| `omit_columns` | 1517-1537 | Column omission approvals (dict) |
| `fem_active_view` | 1927-1935 | Active FEM view type |
| `fem_include_wind` | 1872 | Include wind in FEM views |
| `fem_preview_*` | 2012-2133 | 13 FEM preview control keys |
| `fem_view_*` | 1919, 1969 | Floor/elevation selection |

**References**:
- `app.py` - Lines with `st.session_state`

**Commands**:
```powershell
# Extract all session state keys and save to evidence
Select-String -Path app.py -Pattern "st\.session_state" | Tee-Object -FilePath .sisyphus/evidence/v36-session-keys.raw.txt
```

**Acceptance Criteria**:
- [x] `.sisyphus/evidence/v36-session-keys.raw.txt` contains raw search output
- [x] `.sisyphus/evidence/v36-session-keys.md` lists all 24+ keys
- [x] Each key has: name, line numbers, data type, purpose
- [x] Verification: `(Get-Content .sisyphus/evidence/v36-session-keys.md | Select-String -Pattern \"^\\|\").Count -ge 24`

**Parallelizable**: YES (with 1.4, 1.5)
**Commit**: NO (groups with 1.6)

---

### 1.4 Build Feature Parity Matrix for View Systems

**What to do**:
- Enumerate all toggles/controls in the 3 view systems:
  1. "FEM Views" section (app.py lines 1863-1993)
  2. "Structural Layout" section (app.py lines 1994-2004)
  3. "FEM Analysis" section (app.py lines 2006-2250)
- Mark each feature as: KEEP, MERGE, or DROP
- Document decision rationale

**View System Features** (from research):
```
FEM Views (lines 1863-1993):
├── Floor selector dropdown
├── View buttons (Plan/Elevation/3D)
├── Elevation direction selector
└── Basic visualization config

Structural Layout (lines 1994-2004):
├── create_framing_grid() - 337 lines custom Plotly
├── create_lateral_diagram() - 85 lines custom Plotly
└── NO FEM integration

FEM Analysis (lines 2006-2250):
├── 13 toggle checkboxes (nodes, supports, loads, labels, slabs, mesh, ghost, wind)
├── Floor level selector
├── Color mode selector
├── Grid spacing input
├── Analysis overlay toggle
├── Load pattern selector
├── Plan/Elevation/3D tabs
├── Model statistics display
└── Export controls (format, view selection)
```

**Commands**:
```powershell
# Extract all toggles/controls from the 3 view sections
Select-String -Path app.py -Pattern "st\.(checkbox|selectbox|radio|slider|tabs|button)" | Tee-Object -FilePath .sisyphus/evidence/v36-view-controls.raw.txt
```

**Acceptance Criteria**:
- [x] `.sisyphus/evidence/v36-view-controls.raw.txt` contains raw search output
- [x] `.sisyphus/evidence/v36-view-parity.md` lists all features with columns: Feature | Location | KEEP/MERGE/DROP | Rationale
- [x] Each feature marked KEEP/MERGE/DROP with rationale
- [x] Decision on `create_framing_grid()` → migrate features to Plan View
- [x] Decision on `create_lateral_diagram()` → keep until wind shown in FEM

**Parallelizable**: YES (with 1.3, 1.5)
**Commit**: NO (groups with 1.6)

---

### 1.5 Capture UI Screenshot Baseline

**What to do**:
- Run Streamlit app: `streamlit run app.py`
- Capture screenshots of:
  1. Sidebar controls (scrolled view)
  2. FEM Views section
  3. Structural Layout section (framing grid + lateral diagram)
  4. FEM Analysis section with controls
  5. Detailed Results tabs
- Save to `.sisyphus/evidence/v36-ui-baseline-*.png`

**References**:
- `app.py` - Dashboard layout

**Acceptance Criteria**:
- [ ] 5+ screenshots saved to `.sisyphus/evidence/` **[BLOCKED - Manual user action required]**
- [ ] Screenshots show current controls and outputs **[BLOCKED - Manual user action required]**
- [ ] Screenshots named consistently: `v36-ui-baseline-{section}.png` **[BLOCKED - Manual user action required]**

**Parallelizable**: YES (with 1.3, 1.4)
**Commit**: NO (groups with 1.6)

---

### 1.6 Create Performance Benchmark Script

**What to do**:
- Create `scripts/bench_v36.py` that:
  1. Builds a representative FEM model (e.g., 10-story, 3x3 bays)
  2. Warms up once
  3. Times 5 runs each for: model build, plan render, elevation render, 3D render
  4. Reports min/avg/max times in milliseconds
  5. Saves results to `.sisyphus/evidence/v36-perf-baseline.md`

**Script structure** (runnable; reuse a known-good project factory):
```python
# scripts/bench_v36.py
import platform
import time
from pathlib import Path

from src.core.data_models import (
    BeamResult,
    ColumnResult,
    GeometryInput,
    LoadInput,
    LateralInput,
    MaterialInput,
    ProjectData,
)
from src.fem.model_builder import build_fem_model, ModelBuilderOptions
from src.fem.visualization import create_plan_view, create_elevation_view, create_3d_view, VisualizationConfig

# Reuse the minimal, tested project builder pattern
# (mirrors `tests/test_model_builder.py:_make_project`)
def create_test_project(floors: int = 10, num_bays_x: int = 3, num_bays_y: int = 3) -> ProjectData:
    bay_x = 6.0
    bay_y = 5.0
    story_height = 3.0
    project = ProjectData(
        geometry=GeometryInput(
            bay_x=bay_x,
            bay_y=bay_y,
            floors=floors,
            story_height=story_height,
            num_bays_x=num_bays_x,
            num_bays_y=num_bays_y,
        ),
        loads=LoadInput(live_load_class="2", live_load_sub="2.5", dead_load=2.0),
        materials=MaterialInput(fcu_slab=35, fcu_beam=40, fcu_column=45),
        lateral=LateralInput(building_width=bay_x * num_bays_x, building_depth=bay_y * num_bays_y),
    )
    project.primary_beam_result = BeamResult(
        element_type="Primary Beam",
        size="300x600",
        width=300,
        depth=600,
    )
    project.secondary_beam_result = BeamResult(
        element_type="Secondary Beam",
        size="250x500",
        width=250,
        depth=500,
    )
    project.column_result = ColumnResult(
        element_type="Column",
        size="400",
        dimension=400,
    )
    return project

def benchmark(func, *args, runs=5):
    """Time function execution over multiple runs."""
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        func(*args)
        times.append((time.perf_counter() - start) * 1000)
    return {"min": min(times), "avg": sum(times)/len(times), "max": max(times)}

def main():
    project = create_test_project(floors=10, num_bays_x=3, num_bays_y=3)
    
    # Warmup
    options = ModelBuilderOptions(
        include_core_wall=False,
        include_slabs=False,
        apply_wind_loads=False,
        apply_gravity_loads=True,
    )
    model = build_fem_model(project, options)
    
    # Benchmark model build
    build_times = benchmark(build_fem_model, project, options)
    
    # Benchmark rendering
    config = VisualizationConfig()
    top_floor = max((n.z for n in model.nodes.values()), default=0.0)
    plan_times = benchmark(create_plan_view, model, config, floor_elevation=top_floor)
    elev_times = benchmark(create_elevation_view, model, config, view_direction="X")
    view3d_times = benchmark(create_3d_view, model, config)
    
    # Save results
    report = Path(".sisyphus/evidence/v36-perf-baseline.md")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "\n".join(
            [
                "# v3.6 Performance Baseline",
                "",
                f"- Platform: {platform.platform()}",
                "- Benchmark project: floors=10, bays=3x3, bay=6.0x5.0m, story=3.0m",
                "- Options: include_core_wall=False, include_slabs=False, apply_wind_loads=False, apply_gravity_loads=True",
                "",
                f"- build_fem_model (ms): {build_times}",
                f"- create_plan_view (ms): {plan_times}",
                f"- create_elevation_view (ms): {elev_times}",
                f"- create_3d_view (ms): {view3d_times}",
                "",
            ]
        ),
        encoding="utf-8",
    )

if __name__ == "__main__":
    main()
```

**Acceptance Criteria**:
- [x] `scripts/bench_v36.py` created and runnable
- [x] Script produces timing results for all 4 operations
- [x] `.sisyphus/evidence/v36-perf-baseline.md` contains:
  - Model inputs used (floors, bays)
  - Timing results (min/avg/max in ms)
  - Machine info (optional but helpful)

**Parallelizable**: NO (depends on 1.1)
**Commit**: YES
- Message: `chore(v36): add performance benchmark and capture baselines`
- Files: `scripts/bench_v36.py`, `.sisyphus/evidence/v36-*.md`

**References**:
- `tests/test_model_builder.py:114` - `_make_project()` minimal ProjectData factory pattern

---

## Track 1 Summary

| Task | Description | Effort | Parallelizable |
|------|-------------|--------|----------------|
| 1.1 | Create evidence directory | 5 min | First |
| 1.2 | Test & coverage baseline | 15 min | After 1.1 |
| 1.3 | Session state inventory | 30 min | With 1.4, 1.5 |
| 1.4 | Feature parity matrix | 45 min | With 1.3, 1.5 |
| 1.5 | UI screenshots | 15 min | With 1.3, 1.4 |
| 1.6 | Performance benchmark | 30 min | After 1.1 |

**Total Effort**: ~2 hours
**Commits**: 2 (after 1.2, after 1.6)
**Blocking**: Tracks 2-9 depend on Track 1 completion

---

## Track 2: Visualization Consolidation

**Purpose**: Merge 3 redundant view systems into ONE unified Plotly-based visualization.

**Clarification**:
- Rendering stays Plotly (`create_plan_view`, `create_elevation_view`, `create_3d_view`).
- opsvis is treated as an optional extraction backend (data source), not the primary renderer.
**Depends On**: Track 1 (baselines must exist)
**Effort**: ~6 hours

### 2.1 Add Characterization Tests for View Functions

**What to do**:
- Add tests that capture current behavior of visualization functions
- Test that `create_plan_view()`, `create_elevation_view()`, `create_3d_view()` return valid Plotly figures
- Test key configuration options (show_nodes, show_loads, show_labels, etc.)

**References**:
- `src/fem/visualization.py:603-1323` - `create_plan_view()` (721 lines)
- `src/fem/visualization.py:1326-1741` - `create_elevation_view()` (417 lines)
- `src/fem/visualization.py:1744-2269` - `create_3d_view()` (526 lines)
- `tests/test_visualization_*.py` - Existing visualization tests (50 tests)

**Acceptance Criteria**:
- [x] New characterization tests added to `tests/test_visualization_characterization.py`
- [x] Tests verify figure objects have expected traces for each view type
- [x] Tests cover at least 5 config options per view function
- [x] `pytest tests/test_visualization_*.py` → PASS

**Parallelizable**: YES (with 2.2)
**Commit**: YES
- Message: `test(viz): add characterization tests for view functions`
- Files: `tests/test_visualization_characterization.py`

---

### 2.2 Create Unified FEM Views Module

**Depends On**:
- Track 1.4 output exists: `.sisyphus/evidence/v36-view-parity.md`
- Track 2.3 must complete first (creates `src/ui/` and `src/ui/views/` directories)

**What to do**:
- Create `src/ui/views/fem_views.py` with single entry point (directory exists from 2.3)
- Function signature (pinned): `render_unified_fem_views(project, analysis_result=None, config_overrides=None)`
- This module is responsible for building (and caching) the FEM model used for visualization, so we don’t rebuild the same model multiple times per rerun.
- Include ALL controls from parity matrix marked KEEP/MERGE:
  - View type selector (Plan/Elevation/3D)
  - Floor level selector (formatted as "G/F (+0.00)", "1/F (+4.00)", etc.)
  - Elevation direction (X/Y)
  - 13 visibility toggles (nodes, supports, loads, labels, slabs, mesh, ghost, wind, etc.)
  - Color mode selector
  - Grid spacing input
  - Analysis overlay toggle
  - Export controls
  - Model statistics display

**Analysis overlay integration (pinned behavior)**:
- `analysis_result` is optional.
- If `analysis_result` is present and indicates success:
  - compute `displaced_nodes` via a local helper `_analysis_result_to_displacements()` (copy the current logic from `app.py:722-728` into `src/ui/views/fem_views.py` to avoid importing `app.py`)
  - set `reactions = analysis_result.node_reactions`
  - pass `displaced_nodes` / `reactions` into `create_elevation_view()` and `create_3d_view()` (matching existing behavior in `app.py:2191-2214`)
- If missing or not successful:
  - do not pass displacement/reaction overlays; views render as baseline.

**Wind toggle semantics (no guesswork)**:
- Wind inclusion is a model-build option, not just a visualization flag.
- Toggling wind must trigger a rebuild with `ModelBuilderOptions.apply_wind_loads=True/False`.
- To control performance, cache the built FEM model in session state keyed by a stable options key (geometry + builder options + omission list).

**Cache key + invalidation (pinned recipe)**:
- Cache storage: `st.session_state["fem_model_cache"]: Dict[str, FEMModel]`
- Cache key string should be deterministic, built from:
  - geometry inputs (`project.geometry` fields used by FEM)
  - builder options fields that affect model topology/loading:
    - `include_core_wall`, `trim_beams_at_core`, `apply_gravity_loads`, `apply_wind_loads`, `apply_rigid_diaphragms`
    - `secondary_beam_direction`, `num_secondary_beams`
    - `omit_columns_near_core`, `suggested_omit_columns` (sorted)
    - `include_slabs` (if exposed as a UI toggle)
- Rebuild triggers (must invalidate cached model): any change to the above.
- Re-render-only toggles (must NOT rebuild): view type, floor selection, show_nodes/supports/loads/labels, utilization color mode, grid spacing.

**Module structure**:
```python
# src/ui/views/fem_views.py
import streamlit as st
from src.fem.model_builder import build_fem_model, ModelBuilderOptions
from src.fem.visualization import (
    create_plan_view, create_elevation_view, create_3d_view,
    VisualizationConfig, get_model_statistics
)

def render_unified_fem_views(
    project,
    analysis_result=None,
    config_overrides: dict = None,
) -> None:
    """Render unified FEM visualization with all controls."""

    # Build/cached model (options derived from UI toggles, including wind)
    # model = _get_or_build_cached_model(project, ModelBuilderOptions(...))
    
    # View selector row
    _render_view_selector()
    
    # Visualization controls (collapsible)
    with st.expander("Display Options", expanded=False):
        _render_visibility_toggles()
        _render_color_mode()
        _render_grid_spacing()
    
    # Active view
    _render_active_view(model, config)
    
    # Model statistics
    _render_statistics(model)
    
    # Export controls
    _render_export_controls(fig)
```

**References**:
- `app.py:1863-1993` - FEM Views section (source patterns)
- `app.py:2006-2250` - FEM Analysis section (source patterns)
- `.sisyphus/evidence/v36-view-parity.md` - Feature decisions

**Acceptance Criteria**:
- [x] `src/ui/views/fem_views.py` created
- [x] `render_unified_fem_views()` is the single entry point
- [x] All KEEP/MERGE features from parity matrix are included
- [x] Session state keys follow existing naming convention
- [x] Export controls:
  - If `export_plotly_figure_image()` fails due to missing kaleido/renderer backend, UI shows a clear install hint and does not crash
  - Detection guidance: treat exceptions with message containing "kaleido" (case-insensitive) as missing-export-backend and show `pip install -U kaleido`

**Parallelizable**: NO (depends on 2.3)
**Commit**: NO (groups with 2.3)

---

### 2.3 Create src/ui Package Structure

**What to do**:
- Create `src/ui/__init__.py` with package exports
- Create `src/ui/views/__init__.py`
- Ensure proper import structure

**Note**: This task MUST run BEFORE 2.2 to create the directory structure.

**Commands**:
```powershell
# Create directory structure
New-Item -ItemType Directory -Force src/ui/views | Out-Null
# Create empty __init__.py files (to be populated after 2.2)
New-Item -ItemType File -Force src/ui/__init__.py | Out-Null
New-Item -ItemType File -Force src/ui/views/__init__.py | Out-Null
```

**Directory structure**:
```
src/ui/
├── __init__.py           # Package root
├── views/
│   ├── __init__.py       # Views subpackage
│   └── fem_views.py      # Unified FEM views (from 2.2)
```

**Acceptance Criteria**:
- [x] `src/ui/__init__.py` exists
- [x] `src/ui/views/__init__.py` exists
- [x] Directories ready for 2.2 to create fem_views.py
- [x] After 2.2: `from src.ui.views import render_unified_fem_views` works

**Parallelizable**: YES (with 2.1, runs before 2.2)
**Commit**: NO (groups with 2.2 completion)
- Message: `feat(ui): create unified FEM views module`
- Files: `src/ui/**/*.py`

---

### 2.4 Migrate Framing Grid Features to Plan View

**What to do**:
- Ensure `create_plan_view()` supports all features from `create_framing_grid()`:
  - Multi-bay grid lines
  - Core wall outline with fill
  - Coupling beams
  - Beam trimming visualization
  - Ghost/omitted columns
- Do NOT add new features (refactor-only). If a feature is not already present in `create_plan_view()`, it must either:
  - stay in the legacy `Structural Layout` block temporarily, or
  - be explicitly approved as a UI enhancement with screenshot-based acceptance.

**Features to check** (from `create_framing_grid()` at app.py:348-685):
| Feature | In Plan View? | Action |
|---------|---------------|--------|
| Grid lines | YES | Already exists |
| Core wall outline | YES | Already exists (wall elements) |
| Core wall fill | PARTIAL | Verify fill color |
| Coupling beams | YES | `classification["coupling_beams"]` |
| Beam trimming | YES | Trimmed beams shown |
| Ghost columns | YES | `config.show_ghost_columns` |
| Dimension annotations | NO | OUT (would be new behavior) |

**References**:
- `app.py:348-685` - `create_framing_grid()` (337 lines)
- `src/fem/visualization.py:603-1323` - `create_plan_view()` (721 lines)

**Acceptance Criteria**:
- [x] All existing (non-new) framing-grid features listed above are available via the unified Plan View flow
- [x] Visual comparison shows feature parity
- [x] `pytest` → PASS

**Parallelizable**: NO (depends on 2.2)
**Commit**: YES
- Message: `refactor(viz): ensure plan view covers framing grid parity`
- Files: `src/fem/visualization.py`

---

### 2.5 Migrate Lateral Diagram Features (or Keep Temporarily)

**What to do**:
- Evaluate if `create_lateral_diagram()` features can be shown in FEM elevation view:
  - Wind arrow direction
  - Drift indicator
- If YES: Add wind load visualization to elevation view
- If NO: Keep `create_lateral_diagram()` temporarily with dev flag

**Decision criteria**:
- If wind loads visible in FEM model already → MIGRATE
- If wind visualization requires significant work → KEEP (flag)

**References**:
- `app.py:731-816` - `create_lateral_diagram()` (86 lines)
- `src/fem/visualization.py:1326-1741` - `create_elevation_view()`

**Acceptance Criteria**:
- [x] Decision documented: MIGRATE or KEEP
- [x] If MIGRATE: Wind arrows visible in elevation view
- [x] If KEEP: Dev flag `PRELIMSTRUCT_SHOW_LEGACY_VIEWS=1` gates visibility
- [x] `pytest` → PASS

**Parallelizable**: YES (with 2.4)
**Commit**: YES
- Message: `refactor(viz): handle lateral diagram migration`
- Files: `src/fem/visualization.py` or `app.py`

---

### 2.6 Integrate Unified Views into app.py

**What to do**:
- Replace the 3 view sections in app.py with single call to `render_unified_fem_views()`
- Remove or gate legacy view code
- Ensure all session state keys still work

**Current structure** (to replace):
```python
# Lines 1863-1993: FEM Views section → REMOVE
# Lines 1994-2004: Structural Layout section → REMOVE (or gate)
# Lines 2006-2250: FEM Analysis section → REMOVE
```

**New structure**:
```python
# Single unified section
from src.ui.views import render_unified_fem_views

st.header("FEM Visualization")
 render_unified_fem_views(
     project=project,
     analysis_result=st.session_state.get("fem_preview_analysis_result"),
 )
```

**References**:
- `app.py:1863-2250` - Current view sections (388 lines to remove/replace)
- `src/ui/views/fem_views.py` - New unified module

**Acceptance Criteria**:
- [x] `app.py` calls `render_unified_fem_views()` instead of 3 sections
- [x] Legacy view code removed or gated behind dev flag
- [x] All visualization features still work
- [x] Session state persistence verified
- [x] `streamlit run app.py` works correctly

**Parallelizable**: NO (depends on 2.4, 2.5)
**Commit**: YES
- Message: `refactor(app): integrate unified FEM views`
- Files: `app.py`

---

### 2.7 Remove Legacy View Functions from app.py

**What to do**:
- Remove `create_framing_grid()` function (lines 348-685)
- Remove `create_lateral_diagram()` function (lines 731-816) OR gate behind flag

**Note on core-wall helpers**:
- Do NOT move core-wall helper functions in this task; ownership for moving `calculate_core_wall_properties()`, `get_core_wall_outline()`, and `get_coupling_beams()` is Track 5.5.
- This task ONLY removes `create_framing_grid()` and `create_lateral_diagram()`.

**Lines to remove** (~420 lines):
| Function | Lines | Action |
|----------|-------|--------|
| `create_framing_grid()` | 348-685 | REMOVE (features in plan view) |
| `create_lateral_diagram()` | 731-816 | REMOVE or GATE |

**References**:
- `app.py:348-816` - Functions to remove

**Acceptance Criteria**:
- [x] `create_framing_grid()` removed from app.py
- [x] `create_lateral_diagram()` removed or gated
- [x] Core-wall helpers (`get_core_wall_outline()`, `get_coupling_beams()`) remain in app.py (moved in Track 5.5)
- [x] ~420 lines removed from app.py
- [x] `pytest` → PASS
- [x] `streamlit run app.py` works correctly

**Parallelizable**: NO (depends on 2.6)
**Commit**: YES
- Message: `refactor(app): remove legacy view functions`
- Files: `app.py`, `src/fem/core_wall_helpers.py`

---

### 2.8 Capture "After" Screenshots and Verify Parity

**What to do**:
- Run Streamlit app after consolidation
- Capture screenshots of unified FEM views
- Compare with baseline screenshots from Track 1.5
- Document any intentional differences

**References**:
- `.sisyphus/evidence/v36-ui-baseline-*.png` - Before screenshots
- `.sisyphus/evidence/v36-view-parity.md` - Feature decisions

**Acceptance Criteria**:
- [ ] \"After\" screenshots saved as `v36-ui-after-*.png` **[BLOCKED - Manual user action required]**
- [ ] Visual comparison checklist (against Track 1.5 baseline screenshots): **[BLOCKED - Manual user action required]**
  - Plan View: floor selector works; utilization coloring still works; slabs + ghost columns still visible when toggled on
  - Elevation View: X/Y direction toggle works; floor lines still shown; legend/captions still readable
  - 3D View: supports/nodes toggles work; camera/axes labels still present
  - Analysis overlay: when analysis_result is successful and overlay enabled, elevation + 3D show deflected shape + reactions
- [ ] Any differences documented and intentional **[BLOCKED - Manual user action required]**
- [ ] No regression in visualization quality **[BLOCKED - Manual user action required]**
- [ ] Parity sign-off: every KEEP/MERGE item in `.sisyphus/evidence/v36-view-parity.md` is checked off with a screenshot reference (or documented as intentionally changed) **[BLOCKED - Manual user action required]**

**Parallelizable**: NO (final task)
**Commit**: YES
- Message: `docs(v36): capture after screenshots for view consolidation`
- Files: `.sisyphus/evidence/v36-ui-after-*.png`

---

## Track 2 Summary

| Task | Description | Effort | Parallelizable |
|------|-------------|--------|----------------|
| 2.1 | Characterization tests | 45 min | With 2.3 |
| 2.3 | Create src/ui package | 15 min | With 2.1 (runs first) |
| 2.2 | Create unified views module | 90 min | After 2.3 |
| 2.4 | Migrate framing grid features | 60 min | After 2.2 |
| 2.5 | Handle lateral diagram | 30 min | With 2.4 |
| 2.6 | Integrate into app.py | 45 min | After 2.4, 2.5 |
| 2.7 | Remove legacy functions | 30 min | After 2.6 |
| 2.8 | Capture after screenshots | 15 min | After 2.7 |

**Task Order**: 2.1 & 2.3 (parallel) → 2.2 → 2.4 & 2.5 (parallel) → 2.6 → 2.7 → 2.8

**Total Effort**: ~6 hours
**Commits**: 7
**Lines Removed from app.py**: ~420 (view functions + sections)
**New Module**: `src/ui/views/fem_views.py`

---

## Track 3: Theme & Typography

**Purpose**: Apply Gemini-style dark theme with consistent typography throughout the app.
**Depends On**: Track 2 (unified views should exist)
**Effort**: ~3 hours

### 3.1 Create Theme Tokens Module

**What to do**:
- Create `src/ui/theme.py` with centralized design tokens
- Define color palette, typography, spacing, and border radius
- Match Gemini dark mode aesthetic

**Typography decision (reproducible)**:
- Use Google Fonts via CSS `@import` for consistent typography across machines:
  - UI font: Inter (400/500/600)
  - Mono font: JetBrains Mono (400/500)
- Provide safe fallbacks if external font loading is blocked.

**Design tokens** (from research):
```python
# src/ui/theme.py
GEMINI_TOKENS = {
    "colors": {
        "bg_base": "#131314",        # Near-black background
        "bg_surface": "#1f1f1f",     # Elevated surface
        "bg_elevated": "#2d2e2f",    # Cards/panels
        "text_primary": "#e3e3e3",   # Main text
        "text_secondary": "#9aa0a6", # Secondary text
        "accent_blue": "#8ab4f8",    # Primary accent
        "accent_purple": "#c58af9",  # Secondary accent
        "success": "#81c995",        # Pass status
        "warning": "#fdd663",        # Warning status
        "error": "#f28b82",          # Error status
        "border_subtle": "rgba(255, 255, 255, 0.08)"
    },
    "typography": {
        "font_family": "'Inter', 'Segoe UI', system-ui, sans-serif",
        "font_mono": "'JetBrains Mono', 'Consolas', monospace",
        "size_xs": "12px",
        "size_sm": "14px",
        "size_base": "16px",
        "size_lg": "18px",
        "size_xl": "24px",
        "size_2xl": "32px",
        "weight_normal": 400,
        "weight_medium": 500,
        "weight_bold": 600
    },
    "spacing": {
        "xs": "4px",
        "sm": "8px",
        "md": "16px",
        "lg": "24px",
        "xl": "32px"
    },
    "radius": {
        "sm": "8px",
        "md": "12px",
        "lg": "16px",
        "xl": "20px"
    }
}

def get_streamlit_css() -> str:
    """Generate Streamlit custom CSS from tokens."""
    ...

def apply_theme() -> None:
    """Inject theme CSS into Streamlit app."""
    import streamlit as st
    st.markdown(f"<style>{get_streamlit_css()}</style>", unsafe_allow_html=True)
```

**References**:
- `.sisyphus/drafts/v36-upgrade-planning.md:162-186` - Initial token research
- (Inspiration only) https://gemini.google.com - Visual reference; acceptance is based on our tokens + baseline screenshots, not pixel-perfect Gemini matching

**Acceptance Criteria**:
- [ ] `src/ui/theme.py` created with all tokens
- [ ] `apply_theme()` function generates valid CSS
- [x] Colors, typography, spacing, radius all centralized
- [x] Verification: `python -m py_compile src/ui/theme.py` → no syntax errors
- [x] Verification: `python -c \"from src.ui.theme import GEMINI_TOKENS, apply_theme; print('OK')\"` → prints OK

**Parallelizable**: YES (independent)
**Commit**: YES
- Message: `feat(ui): create Gemini-style theme tokens module`
- Files: `src/ui/theme.py`

---

### 3.2 Generate Streamlit CSS Injection

**What to do**:
- Implement `get_streamlit_css()` in theme.py
- Target key Streamlit elements:
  - `.stApp` - Main app container
  - `.stSidebar` - Sidebar styling
  - `.stButton` - Button styling
  - `.stMetric` - Metric cards
  - `.stExpander` - Collapsible sections
  - `.stTabs` - Tab styling
  - Headers (h1, h2, h3)

**CSS targets**:
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

/* Background */
.stApp { background-color: #131314; }
.stSidebar { background-color: #1f1f1f; }

/* Typography */
.stApp { font-family: 'Inter', system-ui, sans-serif; color: #e3e3e3; }
h1, h2, h3 { color: #e3e3e3; font-weight: 500; }

/* Buttons */
.stButton > button { background-color: #2d2e2f; border-radius: 12px; }
.stButton > button:hover { background-color: #3d3e3f; }

/* Cards/Metrics */
div[data-testid="metric-container"] { 
    background-color: #2d2e2f; 
    border-radius: 12px; 
    padding: 16px; 
}

/* Inputs */
.stTextInput input, .stNumberInput input, .stSelectbox select {
    background-color: #2d2e2f;
    border-color: rgba(255, 255, 255, 0.08);
    color: #e3e3e3;
}
```

**References**:
- `src/ui/theme.py` - Token definitions (from 3.1)
- `app.py:61-158` - Current custom CSS (replace)

**Acceptance Criteria**:
- [ ] CSS covers all major Streamlit components
- [ ] Dark background applied consistently
- [ ] Text is readable (proper contrast)
- [ ] Buttons and inputs styled correctly
- [ ] Verification: `python -c "from src.ui.theme import get_streamlit_css; css = get_streamlit_css(); assert '.stApp' in css; print('OK')"` → prints OK

**Parallelizable**: NO (depends on 3.1)
**Commit**: NO (groups with 3.3)

---

### 3.3 Apply Theme to app.py

**What to do**:
- Import and call `apply_theme()` at app startup
- Remove existing inline CSS from app.py (lines 61-158)
- Ensure theme applies before any content renders

**Current CSS location**: `app.py:61-158` (~98 lines to replace)

**New app.py structure**:
```python
import streamlit as st
from src.ui.theme import apply_theme

st.set_page_config(page_title="PrelimStruct", layout="wide", ...)

# Apply theme immediately after page config
apply_theme()

# Rest of app...
```

**Acceptance Criteria**:
- [ ] `apply_theme()` called after `set_page_config()`
- [ ] Old inline CSS removed from app.py (~98 lines)
- [ ] Theme applies consistently across all pages
- [ ] `streamlit run app.py` shows dark theme

**Parallelizable**: NO (depends on 3.2)
**Commit**: YES
- Message: `feat(ui): apply Gemini-style dark theme`
- Files: `app.py`, `src/ui/theme.py`

---

### 3.4 Fix Legend and Axis Label Spacing

**What to do**:
- Update Plotly figure layout in visualization functions
- Ensure legends have proper spacing from charts
- Ensure axis labels are readable

**Sizing rules** (from research):
- Axis title font: >= 14px
- Axis tick font: >= 12px
- Legend font: >= 12px
- Legend offset/margins: no overlap with chart content

**Apply to**:
- `src/fem/visualization.py:create_plan_view()` (lines 1292-1321)
- `src/fem/visualization.py:create_elevation_view()` (lines 1710-1739)
- `src/fem/visualization.py:create_3d_view()` (lines 2233-2247)

**Layout updates**:
```python
fig.update_layout(
    font=dict(family="Google Sans, system-ui", size=14, color="#e3e3e3"),
    xaxis=dict(
        title_font=dict(size=14),
        tickfont=dict(size=12),
    ),
    yaxis=dict(
        title_font=dict(size=14),
        tickfont=dict(size=12),
    ),
    legend=dict(
        font=dict(size=12),
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=1.02,  # Position outside chart
    ),
    paper_bgcolor="#131314",
    plot_bgcolor="#1f1f1f",
)
```

**References**:
- `src/fem/visualization.py` - Layout configuration sections
- `src/ui/theme.py` - Token values

**Acceptance Criteria**:
- [ ] Legends don't overlap chart content
- [ ] Axis labels readable at default zoom
- [ ] Font sizes follow minimum rules (14/12/12)
- [ ] Colors match theme tokens
- [ ] Verification: `pytest tests/test_visualization*.py -k "legend or axis or font" --tb=short` → PASS (or no matching tests is OK)
- [ ] Verification: `python -m py_compile src/fem/visualization.py` → no syntax errors

**Parallelizable**: YES (with 3.5)
**Commit**: YES
- Message: `style(viz): improve legend and axis label spacing`
- Files: `src/fem/visualization.py`

---

### 3.5 Update Status Badges to Match Theme

**What to do**:
- Update `get_status_badge()` function to use theme colors
- Preserve current badge semantics and labels (OK / WARN / FAIL / --) while restyling to match the Gemini aesthetic
- Use theme tokens for colors

**Current location**: `app.py:161-170` (or extracted to `src/ui/utils.py`)

**Updated badge styles**:
```python
def get_status_badge(status: str, utilization: float) -> str:
    from src.ui.theme import GEMINI_TOKENS
    colors = GEMINI_TOKENS["colors"]

    # Preserve existing behavior from `app.py:get_status_badge`:
    # FAIL if status == "FAIL" OR utilization > 1.0
    # WARN if status == "WARNING" OR utilization > 0.85
    # -- if status == "PENDING"
    # OK otherwise
    if status == "FAIL" or utilization > 1.0:
        label = "FAIL"
        bg = colors["error"]
    elif status == "WARNING" or utilization > 0.85:
        label = "WARN"
        bg = colors["warning"]
    elif status == "PENDING":
        label = "--"
        bg = colors["text_secondary"]
    else:
        label = "OK"
        bg = colors["success"]

    return f"<span style=\"background-color:{bg};color:#131314;padding:4px 12px;border-radius:12px;font-size:12px;font-weight:600;\">{label}</span>"
```

**References**:
- `app.py:161-170` - Current badge implementation
- `src/ui/theme.py` - Theme colors

**Acceptance Criteria**:
- [ ] Badges use theme colors (success/warning/error)
- [ ] Badge styling matches Gemini aesthetic (rounded, proper padding)
- [ ] Text is readable on colored backgrounds
- [ ] Badge labels and thresholds unchanged from the baseline screenshots
- [ ] Verification: `python -m py_compile app.py` → no syntax errors

**Parallelizable**: YES (with 3.4)
**Commit**: YES
- Message: `style(ui): update status badges to match theme`
- Files: `app.py` or `src/ui/utils.py`

---

### 3.6 Verify Theme Consistency

**What to do**:
- Review all UI sections for theme consistency
- Identify and fix any remaining hardcoded colors
- Capture "after" screenshots showing theme

**Verification checklist**:
- [ ] Sidebar: dark background, readable text
- [ ] Main content: dark background
- [ ] Metrics: styled cards with proper contrast
- [ ] Charts: dark plot backgrounds, readable labels
- [ ] Buttons: consistent styling
- [ ] Inputs: dark backgrounds, visible borders
- [ ] Expanders: proper styling
- [ ] Tabs: active/inactive states clear

**References**:
- `.sisyphus/evidence/v36-ui-baseline-*.png` - Before screenshots
- `src/ui/theme.py` - Token reference

**Acceptance Criteria**:
- [ ] No hardcoded color values remain in UI layer (`app.py` and `src/ui/**`), aside from the single theme injection point
- [ ] All major UI sections follow theme
- [ ] Screenshots show consistent dark theme
- [ ] PowerShell check for hex colors (allow exceptions only in the theme module itself):
  - `Select-String -Path app.py, src/ui/**/*.py -Pattern "#[0-9a-fA-F]{6}"` returns 0 matches

**Parallelizable**: NO (final task)
**Commit**: YES
- Message: `style(v36): verify theme consistency throughout app`
- Files: Any remaining fixes

---

## Track 3 Summary

| Task | Description | Effort | Parallelizable |
|------|-------------|--------|----------------|
| 3.1 | Create theme tokens module | 45 min | Independent |
| 3.2 | Generate Streamlit CSS | 30 min | After 3.1 |
| 3.3 | Apply theme to app.py | 20 min | After 3.2 |
| 3.4 | Fix legend/axis spacing | 30 min | With 3.5 |
| 3.5 | Update status badges | 20 min | With 3.4 |
| 3.6 | Verify consistency | 30 min | After all |

**Total Effort**: ~3 hours
**Commits**: 5
**Lines Removed from app.py**: ~98 (inline CSS)
**New Module**: `src/ui/theme.py`

---

## Track 4: State & Components

**Purpose**: Centralize session state management and extract reusable UI components.
**Depends On**: Track 2 (ui package structure exists)
**Effort**: ~3.5 hours

### 4.1 Create Centralized State Module

**What to do**:
- Create `src/ui/state.py` with all session state initialization
- Define default values for all 24+ keys
- Create single `init_session_state()` function

**Guardrail (baseline-faithful defaults)**:
- `STATE_DEFAULTS` must match the current baseline widget defaults in `app.py` (each widget's `value=` and any explicit `st.session_state.get(..., default)` usage). If a default in this plan conflicts with current app behavior, treat it as a plan bug and update it to match baseline.

**Module structure**:
```python
# src/ui/state.py
import streamlit as st
from src.core.data_models import ProjectData

# Default values for all session state keys
STATE_DEFAULTS = {
    # Core data
    # NOTE: `ProjectData()` is the baseline initialization used today in `app.py`.
    # Presets are applied later via sidebar actions (loads/materials assignment), not at state init.
    "project": None,
    
    # Load combinations
    "selected_combinations": {"LC1", "SLS1"},
    
    # Column omission
    "omit_columns": {},
    
    # FEM view state
    "fem_active_view": "plan",
    "fem_include_wind": True,
    "fem_view_elev_dir": "X",
    
    # FEM preview controls
    "fem_preview_show_nodes": False,
    "fem_preview_show_supports": True,
    "fem_preview_show_loads": True,
    "fem_preview_show_labels": False,
    "fem_preview_show_slabs": True,
    "fem_preview_show_slab_mesh": True,
    "fem_preview_show_ghost": True,
    "fem_preview_include_wind": True,
    "fem_preview_color_mode": "Element Type",
    "fem_preview_grid_spacing": 1.0,
    "fem_preview_overlay_analysis": False,
    "fem_preview_elevation_direction": "X",
    
    # FEM analysis results
    "fem_preview_analysis_result": None,
    "fem_preview_analysis_message": "",
    
    # Export
    "fem_export_view": "Plan View",
    "fem_export_format": "png",
}

# Keys that must NOT be pre-initialized because their valid values depend on runtime options lists.
# These should be initialized lazily at the point where their options are computed.
DEFERRED_KEYS = [
    # Options are computed after `get_model_statistics(model)` / floor levels known.
    "fem_view_floor_select",        # int index into range(len(floor_options))
    # Options are computed after `get_model_statistics(model)` / floor_levels known.
    "fem_preview_floor_level",      # float chosen from floor_levels list (defaults to top floor)
    # Options are computed after `ModelBuilderOptions` created (gravity/wind pattern IDs).
    "fem_preview_analysis_pattern", # int load pattern ID
]

def init_session_state() -> None:
    """Initialize all session state keys with defaults."""
    for key, default in STATE_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default
    
    # Special handling for project initialization
    if st.session_state.project is None:
        st.session_state.project = ProjectData()

def get_state(key: str, default=None):
    """Get session state value with fallback."""
    return st.session_state.get(key, STATE_DEFAULTS.get(key, default))

def set_state(key: str, value) -> None:
    """Set session state value."""
    st.session_state[key] = value
```

**References**:
- `.sisyphus/evidence/v36-session-keys.md` - Key inventory from Track 1.3
- `app.py` - Current scattered initialization

**Acceptance Criteria**:
- [ ] `src/ui/state.py` created with all 24+ keys
- [ ] `init_session_state()` initializes all keys
- [ ] Helper functions `get_state()` and `set_state()` provided
- [ ] Documentation for each key's purpose
- [ ] State defaults table documented (baseline-faithful): key → stored type/domain → init rule (set now vs defer)

**Parallelizable**: YES (independent)
**Commit**: YES
- Message: `feat(ui): create centralized session state module`
- Files: `src/ui/state.py`

---

### 4.2 Migrate State Initialization to Centralized Module

**What to do**:
- Update app.py to call `init_session_state()` once at startup
- Remove scattered state initialization throughout app.py
- Update all state access to use centralized module (optional)

**Current scattered initialization** (lines to modify):
| Location | Key | Action |
|----------|-----|--------|
| `app.py:981-983` | `project` | REMOVE (use central init) |
| `app.py:1597-1599` | `selected_combinations` | REMOVE |
| `app.py:1517-1537` | `omit_columns` | REMOVE |
| `app.py:2012-2036` | `fem_preview_*` | REMOVE |

**New app.py structure**:
```python
from src.ui.state import init_session_state

def main():
    # Initialize all session state ONCE
    init_session_state()
    
    # Rest of app can assume all keys exist
    ...
```

**Acceptance Criteria**:
- [ ] `init_session_state()` called once in main()
- [ ] All scattered `if key not in st.session_state` blocks removed
- [ ] Session state persistence verified (keys don't reset unexpectedly)
- [ ] `streamlit run app.py` works correctly

**Parallelizable**: NO (depends on 4.1)
**Commit**: YES
- Message: `refactor(app): centralize session state initialization`
- Files: `app.py`

---

### 4.3 Extract Status Badge Component

**What to do**:
- Create `src/ui/components.py` with reusable UI components
- Move `get_status_badge()` to components module
- Make badge customizable (colors, sizes)
- Preserve existing badge behavior (labels + thresholds) from `app.py:161-170`

**Component structure**:
```python
# src/ui/components.py
import streamlit as st
from src.ui.theme import GEMINI_TOKENS

def status_badge(
    status: str,
    utilization: float,
    size: str = "sm"  # sm, md, lg
) -> str:
    """Generate themed status badge HTML."""
    colors = GEMINI_TOKENS["colors"]

    # Preserve baseline mapping:
    # FAIL if status == "FAIL" OR utilization > 1.0
    # WARN if status == "WARNING" OR utilization > 0.85
    # -- if status == "PENDING"
    # OK otherwise
    if status == "FAIL" or utilization > 1.0:
        label = "FAIL"
        bg = colors["error"]
    elif status == "WARNING" or utilization > 0.85:
        label = "WARN"
        bg = colors["warning"]
    elif status == "PENDING":
        label = "--"
        bg = colors["text_secondary"]
    else:
        label = "OK"
        bg = colors["success"]
    
    sizes = {"sm": "12px", "md": "14px", "lg": "16px"}
    padding = {"sm": "4px 12px", "md": "6px 16px", "lg": "8px 20px"}
    
    return f'''
        <span style="
            background-color: {bg};
            color: #131314;
            padding: {padding[size]};
            border-radius: 12px;
            font-size: {sizes[size]};
            font-weight: 600;
        ">
            {label}
        </span>
    '''

def render_status_badge(status: str, utilization: float, size: str = "sm") -> None:
    """Render status badge in Streamlit."""
    st.markdown(status_badge(status, utilization, size), unsafe_allow_html=True)
```

**References**:
- `app.py:161-170` - Current `get_status_badge()` implementation
- `src/ui/theme.py` - Theme tokens

**Acceptance Criteria**:
- [ ] `src/ui/components.py` created
- [ ] `status_badge()` function uses theme colors
- [ ] `render_status_badge()` convenience function provided
- [ ] Component is reusable with size variants
- [ ] Badge labels and thresholds unchanged from baseline

**Parallelizable**: YES (with 4.4)
**Commit**: NO (groups with 4.5)

---

### 4.4 Extract Metric Card Component

**What to do**:
- Add metric card component to `src/ui/components.py`
- Style with theme tokens (dark background, rounded corners)
- Support title, value, unit, and optional delta

**Component structure**:
```python
def metric_card(
    title: str,
    value: str | float,
    unit: str = "",
    delta: float = None,
    delta_color: str = "normal"  # normal, inverse, off
) -> None:
    """Render themed metric card."""
    colors = GEMINI_TOKENS["colors"]
    
    value_str = f"{value} {unit}" if unit else str(value)
    
    delta_html = ""
    if delta is not None:
        delta_color_val = colors["success"] if delta >= 0 else colors["error"]
        if delta_color == "inverse":
            delta_color_val = colors["error"] if delta >= 0 else colors["success"]
        delta_html = f'<span style="color: {delta_color_val}">{"+" if delta >= 0 else ""}{delta:.1%}</span>'
    
    st.markdown(f'''
        <div style="
            background-color: {colors["bg_elevated"]};
            border-radius: 12px;
            padding: 16px;
            text-align: center;
        ">
            <div style="color: {colors["text_secondary"]}; font-size: 12px; margin-bottom: 4px;">
                {title}
            </div>
            <div style="color: {colors["text_primary"]}; font-size: 24px; font-weight: 500;">
                {value_str}
            </div>
            {f'<div style="margin-top: 4px;">{delta_html}</div>' if delta_html else ''}
        </div>
    ''', unsafe_allow_html=True)
```

**References**:
- `app.py:1829-1861` - Key Metrics section (current implementation)
- `src/ui/theme.py` - Theme tokens

**Acceptance Criteria**:
- [ ] `metric_card()` component added to components.py
- [ ] Uses theme colors for styling
- [ ] Supports value with units and optional delta
- [ ] Matches Gemini aesthetic (rounded, dark background)

**Parallelizable**: YES (with 4.3)
**Commit**: NO (groups with 4.5)

---

### 4.5 Extract Collapsible Section Component

**What to do**:
- Add themed expander/collapsible component
- Customize Streamlit expander appearance
- Support icon and expanded state

**Component structure**:
```python
def collapsible_section(
    title: str,
    expanded: bool = False,
    icon: str = None
) -> st.delta_generator.DeltaGenerator:
    """Create themed collapsible section."""
    display_title = f"{icon} {title}" if icon else title
    return st.expander(display_title, expanded=expanded)

# Usage:
with collapsible_section("Display Options", expanded=False, icon="⚙️"):
    # Section content here
    ...
```

**References**:
- `app.py` - Various `st.expander()` usages
- `src/ui/theme.py` - Theme tokens for styling

**Acceptance Criteria**:
- [ ] `collapsible_section()` component added
- [ ] Themed via CSS (dark background, rounded corners)
- [ ] Optional icon support
- [ ] Consistent appearance across app

**Parallelizable**: NO (depends on 4.3, 4.4)
**Commit**: YES
- Message: `feat(ui): extract reusable UI components`
- Files: `src/ui/components.py`

---

### 4.6 Update app.py to Use Extracted Components

**What to do**:
- Replace inline badge code with `status_badge()` calls
- Replace metric displays with `metric_card()` calls
- Use `collapsible_section()` for expandable areas

**Locations to update**:
| Location | Current | Replace With |
|----------|---------|--------------|
| `app.py:1768-1828` | Inline status badges | `render_status_badge()` |
| `app.py:1829-1861` | `st.metric()` calls | `metric_card()` |
| `app.py:2006-2010` | `st.expander()` | `collapsible_section()` |

**Acceptance Criteria**:
- [ ] All status badges use `render_status_badge()`
- [ ] Key metrics use `metric_card()`
- [ ] Collapsible sections use `collapsible_section()`
- [ ] Visual appearance matches previous (or improves)
- [ ] `streamlit run app.py` works correctly

**Parallelizable**: NO (depends on 4.5)
**Commit**: YES
- Message: `refactor(app): use extracted UI components`
- Files: `app.py`

---

### 4.7 Add Component Documentation

**What to do**:
- Add docstrings to all component functions
- Create `src/ui/README.md` with usage examples
- Document component API (parameters, return values)

**Documentation structure**:
```markdown
# src/ui/README.md

## UI Components

### status_badge(status, utilization, size)
Generates themed status badge HTML.

**Parameters:**
- `status` (str): Status string - accepts "FAIL", "WARNING", "PENDING", or any other value (renders as OK)
- `utilization` (float): 0.0 to 1.0+ (values > 1.0 trigger FAIL, > 0.85 triggers WARN)
- `size` (str): "sm", "md", or "lg"

**Rendered Labels** (baseline behavior from `app.py:get_status_badge`):
- FAIL: when `status == "FAIL"` OR `utilization > 1.0`
- WARN: when `status == "WARNING"` OR `utilization > 0.85`
- --: when `status == "PENDING"`
- OK: otherwise

**Example:**
```python
from src.ui.components import render_status_badge
render_status_badge("WARNING", 0.75)  # renders WARN badge
render_status_badge("OK", 0.5)        # renders OK badge
```

### metric_card(title, value, unit, delta, delta_color)
...
```

**Acceptance Criteria**:
- [ ] All functions have comprehensive docstrings
- [ ] `src/ui/README.md` created with usage examples
- [ ] API documentation matches baseline behavior (status inputs: FAIL/WARNING/PENDING/other; labels: FAIL/WARN/--/OK)

**Parallelizable**: NO (final task)
**Commit**: YES
- Message: `docs(ui): add component documentation`
- Files: `src/ui/README.md`, `src/ui/components.py`

---

## Track 4 Summary

| Task | Description | Effort | Parallelizable |
|------|-------------|--------|----------------|
| 4.1 | Create state module | 45 min | Independent |
| 4.2 | Migrate state init | 30 min | After 4.1 |
| 4.3 | Extract status badge | 20 min | With 4.4 |
| 4.4 | Extract metric card | 30 min | With 4.3 |
| 4.5 | Extract collapsible section | 20 min | After 4.3, 4.4 |
| 4.6 | Update app.py | 30 min | After 4.5 |
| 4.7 | Add documentation | 20 min | After 4.6 |

**Total Effort**: ~3.5 hours
**Commits**: 5
**New Modules**: `src/ui/state.py`, `src/ui/components.py`, `src/ui/README.md`

---

## Track 5: app.py Modularization

**Purpose**: Split the ~2,444-line app.py monolith into smaller, maintainable UI modules.
**Depends On**: Tracks 2, 3, 4 (ui package, theme, state, components exist)
**Effort**: ~5 hours
**Target**: app.py < 500 lines after extraction

### 5.1 Extract Sidebar Controls Module

**What to do**:
- Create `src/ui/sidebar.py` with all sidebar input logic
- Extract lines 984-1711 (728 lines) from app.py
- Create `render_sidebar()` function that returns all input values

**Module structure**:
```python
# src/ui/sidebar.py
import streamlit as st
from src.ui.state import get_state, set_state
from src.core.data_models import ProjectData, PRESETS, ...

def render_sidebar(project: ProjectData) -> dict:
    """Render sidebar and return updated input values."""
    with st.sidebar:
        inputs = {}
        
        # Presets section
        inputs.update(_render_preset_selector())
        
        # Geometry section
        inputs.update(_render_geometry_inputs(project))
        
        # Loading section
        inputs.update(_render_loading_inputs(project))
        
        # Materials section
        inputs.update(_render_material_inputs(project))
        
        # Beam configuration
        inputs.update(_render_beam_config())
        
        # Lateral system
        inputs.update(_render_lateral_system(project))
        
        # Column omission
        inputs.update(_render_column_omission(project))
        
        # Overrides
        inputs.update(_render_overrides(project))
        
        # Load combinations
        inputs.update(_render_load_combinations())
        
    return inputs

def _render_preset_selector() -> dict: ...
def _render_geometry_inputs(project) -> dict: ...
def _render_loading_inputs(project) -> dict: ...
def _render_material_inputs(project) -> dict: ...
def _render_beam_config() -> dict: ...
def _render_lateral_system(project) -> dict: ...
def _render_column_omission(project) -> dict: ...
def _render_overrides(project) -> dict: ...
def _render_load_combinations() -> dict: ...
```

**References**:
- `app.py:984-1711` - Current sidebar implementation (728 lines)

**Acceptance Criteria**:
- [ ] `src/ui/sidebar.py` created (~750 lines)
- [ ] `render_sidebar()` returns dict of all user inputs
- [ ] All widget keys preserved (no state loss)
- [ ] `streamlit run app.py` works correctly

**Parallelizable**: YES (independent)
**Commit**: YES
- Message: `refactor(ui): extract sidebar controls to separate module`
- Files: `src/ui/sidebar.py`, `app.py`

---

### 5.2 Extract Results Display Module

**What to do**:
- Create `src/ui/views/results_display.py`
- Extract detailed results tabs from app.py
- Handle Slab, Beams, Columns, Lateral tabs

**Module structure**:
```python
# src/ui/views/results_display.py
import streamlit as st

def render_detailed_results(project) -> None:
    """Render tabbed detailed results section."""
    tab_slab, tab_beams, tab_columns, tab_lateral = st.tabs([
        "Slab", "Beams", "Columns", "Lateral"
    ])
    
    with tab_slab:
        _render_slab_results(project)
    
    with tab_beams:
        _render_beam_results(project)
    
    with tab_columns:
        _render_column_results(project)
    
    with tab_lateral:
        _render_lateral_results(project)

def _render_slab_results(project) -> None: ...
def _render_beam_results(project) -> None: ...
def _render_column_results(project) -> None: ...
def _render_lateral_results(project) -> None: ...
```

**References**:
- `app.py:2252-2376` - Detailed Results section (125 lines)

**Acceptance Criteria**:
- [ ] `src/ui/views/results_display.py` created (~130 lines)
- [ ] All 4 tabs render correctly
- [ ] Project data displayed accurately
- [ ] `pytest` → PASS

**Parallelizable**: YES (with 5.1, 5.3)
**Commit**: NO (groups with 5.4)

---

### 5.3 Extract Report Generation Module

**What to do**:
- Create `src/ui/views/report_section.py`
- Extract report generation UI from app.py
- Handle inputs and download functionality

**Module structure**:
```python
# src/ui/views/report_section.py
import streamlit as st
from src.report.report_generator import ReportGenerator

def render_report_section(project) -> None:
    """Render report generation section."""
    st.header("Generate Report")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        project_name = st.text_input("Project Name", "PrelimStruct Project")
    with col2:
        project_number = st.text_input("Project Number", "PS-001")
    with col3:
        engineer = st.text_input("Engineer", "")
    
    if st.button("Generate HTML Report"):
        _generate_and_download_report(project, project_name, project_number, engineer)

def _generate_and_download_report(project, name, number, engineer) -> None: ...
```

**References**:
- `app.py:2378-2431` - Report Generation section (54 lines)

**Acceptance Criteria**:
- [ ] `src/ui/views/report_section.py` created (~60 lines)
- [ ] Report generation works correctly
- [ ] Download functionality preserved

**Parallelizable**: YES (with 5.1, 5.2)
**Commit**: NO (groups with 5.4)

---

### 5.4 Extract Utility Functions Module

**What to do**:
- Create `src/ui/utils.py` with shared UI utilities
- Move helper functions from app.py:
  - `calculate_carbon_emission()` (lines 173-214)
  - `build_preview_utilization_map()` (lines 688-719)
  - `_analysis_result_to_displacements()` (baseline in `app.py:722-728`; may temporarily live in `src/ui/views/fem_views.py` after Track 2.2)
  - `create_beam_geometries_from_project()` (lines 299-345)

**References**:
- `app.py:173-214` - Carbon calculation
- `app.py:688-728` - Preview utilities
- `app.py:299-345` - Beam geometry helper

**Acceptance Criteria**:
- [ ] `src/ui/utils.py` created (~130 lines)
- [ ] All utility functions moved and working
- [ ] No circular imports
- [ ] `pytest` → PASS

**Parallelizable**: NO (depends on 5.1-5.3)
**Commit**: YES
- Message: `refactor(ui): extract results, report, and utility modules`
- Files: `src/ui/views/results_display.py`, `src/ui/views/report_section.py`, `src/ui/utils.py`, `app.py`

---

### 5.5 Move Core Wall Helpers to FEM Module

**What to do**:
- Create `src/fem/core_wall_helpers.py`
- Move misplaced functions from app.py:
  - `calculate_core_wall_properties()` (lines 217-246)
  - `get_core_wall_outline()` (lines 249-278)
  - `get_coupling_beams()` (lines 281-296)

**These functions belong in FEM, not UI.**

**References**:
- `app.py:217-296` - Core wall helpers (80 lines)
- `src/fem/` - Proper location for FEM utilities

**Acceptance Criteria**:
- [ ] `src/fem/core_wall_helpers.py` created (~85 lines)
- [ ] Functions accessible from app.py via import
- [ ] `pytest` → PASS

**Parallelizable**: YES (independent)
**Commit**: YES
- Message: `refactor(fem): extract core wall helpers from app.py`
- Files: `src/fem/core_wall_helpers.py`, `app.py`

---

### 5.6 Refactor main() to Orchestrator Pattern

**What to do**:
- Refactor app.py main() to be a thin orchestrator
- Call extracted modules instead of inline code
- Aim for < 500 lines total

**New main() structure**:
```python
# app.py (target: <500 lines)

import streamlit as st
from src.ui.theme import apply_theme
from src.ui.state import init_session_state
from src.ui.sidebar import render_sidebar
from src.ui.views.fem_views import render_unified_fem_views
from src.ui.views.results_display import render_detailed_results
from src.ui.views.report_section import render_report_section
from src.ui.components import render_status_badge, metric_card
from src.ui.utils import calculate_carbon_emission
from src.engines import SlabEngine, BeamEngine, ColumnEngine, WindEngine
from src.fem.model_builder import build_fem_model, ModelBuilderOptions

def main():
    # Page config
    st.set_page_config(...)
    
    # Initialize
    apply_theme()
    init_session_state()
    
    # Sidebar inputs
    inputs = render_sidebar(st.session_state.project)
    
    # Update project from inputs
    project = _update_project(inputs)
    
    # Run calculations
    project = _run_calculations(project, inputs)
    
    # Main content
    st.title("PrelimStruct v3.6")
    
    # Status badges row
    _render_status_row(project)
    
    # Key metrics row
    _render_metrics_row(project)
    
    # FEM visualization (unified)
    render_unified_fem_views(project, analysis_result=st.session_state.get("fem_preview_analysis_result"))
    
    # Detailed results
    render_detailed_results(project)
    
    # Report generation
    render_report_section(project)

def _update_project(inputs: dict) -> ProjectData: ...
def _run_calculations(project, inputs) -> ProjectData: ...
def _render_status_row(project) -> None: ...
def _render_metrics_row(project) -> None: ...

if __name__ == "__main__":
    main()
```

**Acceptance Criteria**:
- [ ] app.py reduced to < 500 lines
- [ ] main() is orchestration only (no inline UI code)
- [ ] All functionality preserved
- [ ] `streamlit run app.py` works correctly

**Parallelizable**: NO (final integration)
**Commit**: YES
- Message: `refactor(app): convert to thin orchestrator pattern`
- Files: `app.py`

---

### 5.7 Verify Line Count and Test

**What to do**:
- Count lines in app.py (target: < 500)
- Run full test suite
- Verify all UI sections work correctly

**Verification commands**:
```powershell
# Count lines
(Get-Content app.py).Count

# Run tests
pytest tests/ --tb=short

# Run app
streamlit run app.py
```

**Expected line distribution**:
| Module | Lines | Purpose |
|--------|-------|---------|
| `app.py` | <500 | Thin orchestrator |
| `src/ui/sidebar.py` | ~750 | Sidebar controls |
| `src/ui/views/fem_views.py` | ~300 | FEM visualization |
| `src/ui/views/results_display.py` | ~130 | Results tabs |
| `src/ui/views/report_section.py` | ~60 | Report UI |
| `src/ui/utils.py` | ~130 | Shared utilities |
| `src/ui/theme.py` | ~100 | Theme tokens |
| `src/ui/state.py` | ~80 | State management |
| `src/ui/components.py` | ~150 | UI components |
| `src/fem/core_wall_helpers.py` | ~85 | Core wall utils |

**Acceptance Criteria**:
- [ ] `app.py` is < 500 lines (~80% reduction from ~2,444)
- [ ] All tests pass
- [ ] All UI sections render correctly
- [ ] No functionality regression

**Parallelizable**: NO (final verification)
**Commit**: YES
- Message: `refactor(v36): verify app.py modularization complete`
- Files: Documentation updates

---

## Track 5 Summary

| Task | Description | Effort | Parallelizable |
|------|-------------|--------|----------------|
| 5.1 | Extract sidebar | 90 min | Independent |
| 5.2 | Extract results display | 30 min | With 5.1, 5.3 |
| 5.3 | Extract report section | 20 min | With 5.1, 5.2 |
| 5.4 | Extract utilities | 30 min | After 5.1-5.3 |
| 5.5 | Move core wall helpers | 20 min | Independent |
| 5.6 | Refactor main() | 60 min | After 5.4 |
| 5.7 | Verify and test | 30 min | After 5.6 |

**Total Effort**: ~5 hours
**Commits**: 5
**Lines Removed from app.py**: ~1,944 (~2,444 → 500)
**New Modules**: 5 extracted modules

---

## Track 6: Backend: model_builder.py (Builder/Director Refactor)

**Purpose**: Refactor `src/fem/model_builder.py` to be maintainable while preserving all current behavior.

Key drivers (evidence-based):
- `build_fem_model()` is a large monolith starting at `src/fem/model_builder.py:988`.
- Beam creation logic is duplicated across 4 blocks (gridline beams X/Y + internal secondary beams X/Y), centered around `src/fem/model_builder.py:1157`.
- Walls/slabs already use specialized generators (`WallMeshGenerator`, `SlabMeshGenerator`), which is a good internal pattern to extend to beams/columns.

**Target shape**: Keep BuildingTcl 3-phase structure, but implement as Director + specialized builders:
- Phase 1 (Model Definition): materials/sections/nodes/elements
- Phase 2 (Load Application): diaphragms + gravity/wind load application
- Phase 3 (Analysis Preparation): validate/diagnostics

**Guardrails (Track 6)**:
- Preserve floor-based node numbering scheme (via `FLOOR_NODE_BASE` / NodeRegistry floor logic)
- Preserve tag ranges globally: walls 50000-59999, slabs 60000-69999, coupling beams 70000+
- Preserve optional `shapely` dependency behavior (ImportError fallback remains graceful)
- Do not change which beams/columns/elements are created; this is refactor-only

**External references (why they matter)**:
- OpenSees “3-phase” workflow overview: https://opensees.berkeley.edu/OpenSees/manuals/usermanual/1412.htm (canonical command grouping: model → patterns/loads → analysis)
- BuildingTcl getting started: https://opensees.berkeley.edu/wiki/index.php?title=Getting_Started_with_BuildingTcl (same sequencing principle; library abstractions)
- OpenSeesPy docs (command grouping):
  - Model commands: https://openseespydoc.readthedocs.io/en/latest/src/modelcmds.html
  - Pattern/load commands: https://openseespydoc.readthedocs.io/en/latest/src/pattern.html
  - Analysis commands: https://openseespydoc.readthedocs.io/en/latest/src/analysiscmds.html

**Reference implementations to borrow structure from (not code)**:
- CAD2Sees (director + builder-like decomposition, private step methods; analysis separated):
  - https://raw.githubusercontent.com/BsmYksln/CAD2Sees/8244794046d376274c87d1028451f2285d6897da/cad2sees/model_generation/component_modeller/frame_modeller.py
  - https://raw.githubusercontent.com/BsmYksln/CAD2Sees/8244794046d376274c87d1028451f2285d6897da/cad2sees/model_generation/frame.py
- o3seespy (object wrappers, auto-tagging, command logging; helps tag-collision avoidance):
  - https://raw.githubusercontent.com/o3seespy/o3seespy/8b23ce732b27d1a595a1ef45ef2e12b0f6932155/o3seespy/base_model.py

**Depends On**: Track 1 (tests + perf baseline)
**Effort**: ~8-12 hours

### 6.1 Add Characterization Tests for build_fem_model (Refactor Safety Net)

**What to do**:
- Add characterization tests that lock down current invariants that refactors tend to accidentally change.
- Prefer small, focused tests that assert stable invariants (counts, tag ranges, element types, load patterns), not exact tag ordering.

**Must-cover invariants (current gaps)**:
- Coupling beams: created (or not) based on core opening conditions.
- Slabs: mesh generation + surface load application paths when `include_slabs=True`.
- Custom core location offsets (`location_type="Custom"` with `custom_center_x/y`).
- Column omission: ghost columns list (`model.omitted_columns`) and omission set behavior.
- Tag range constraints: wall nodes/elements 50000-59999, slab 60000-69999, coupling beams 70000+.

**References**:
- `src/fem/model_builder.py:988` - `build_fem_model()`
- `src/fem/model_builder.py:1157` - beam blocks (duplication target)
- `src/fem/model_builder.py:1447` - wall + coupling beam creation
- `src/fem/model_builder.py:1622` - slab mesh + surface loads
- `tests/test_model_builder.py` - existing unit tests + helper tests
- `tests/test_model_builder_wall_integration.py` - wall mesh integration tests
- `tests/test_integration_e2e.py` - end-to-end invariants (large model counts)
- `tests/test_verify_task_17_3_integration.py` - column omission integration

**Acceptance Criteria**:
- [ ] New tests added (recommended file: `tests/test_model_builder_characterization.py`)
- [ ] At least 10-15 characterization tests added covering the listed gaps
- [ ] `pytest tests/test_model_builder*.py` → PASS
- [ ] `pytest tests/test_integration_e2e.py -k build_fem_model` → PASS

**Parallelizable**: YES (with 6.2 design doc / skeleton work)
**Commit**: YES
- Message: `test(fem): add characterization tests for model_builder refactor`
- Files: `tests/test_model_builder_characterization.py`

---

### 6.2 Extract BeamBuilder (Remove 4x Duplicated Beam Creation)

**What to do**:
- Create a dedicated builder (class or module-level functions) that consolidates:
  - Primary gridline beams along X and Y
  - Secondary internal subdivision beams along X and Y
- The extracted builder must encapsulate:
  - trimming (`trim_beam_segment_against_polygon`)
  - node creation (`NodeRegistry.get_or_create`)
  - element creation (`ElementType.ELASTIC_BEAM`)
  - optional self-weight uniform loads (`UniformLoad`) when `options.apply_gravity_loads`
  - `core_boundary_points` tracking for moment connections

**Proposed API (one reasonable option)**:
- `BeamBuilder.add_gridline_beams(direction, section_tag, section_dims, ...) -> next_element_tag`
- `BeamBuilder.add_internal_secondary_beams(direction, num_secondary_beams, ...) -> next_element_tag`

**Default applied (override if needed)**:
- Place extracted builders in a small package `src/fem/builders/` (keeps `model_builder.py` readable; aligns with existing generator modules like `src/fem/wall_element.py` and `src/fem/slab_element.py`).

**Guardrails**:
- Do not change which beams are created (gridlines vs internal).
- Keep trimming behavior identical (including tolerance checks and moment/pinned decisions).
- Preserve gravity load pattern usage (`options.gravity_load_pattern`).

**References**:
- `src/fem/model_builder.py:1157` - gridline X beams
- `src/fem/model_builder.py:1223` - gridline Y beams
- `src/fem/model_builder.py:1289` - internal secondary subdivision
- `src/fem/model_builder.py:572` - `trim_beam_segment_against_polygon()` implementation (geometry helper)
- `tests/test_model_builder.py` - trim behavior tests for enter/exit/tangent/no-intersection cases
- `src/core/constants.py` - concrete density / constants used for self-weight calculations

**Acceptance Criteria**:
- [ ] 4 beam blocks replaced by calls into BeamBuilder
- [ ] `pytest tests/test_model_builder.py -k secondary` → PASS
- [ ] No change in counts of beam elements/uniform loads for existing fixtures

**Parallelizable**: NO (depends on 6.1 tests)
**Commit**: YES
- Message: `refactor(fem): extract BeamBuilder and dedupe beam creation`
- Files: `src/fem/model_builder.py`, (new builder module)

---

### 6.3 Extract MaterialSectionBuilder (Materials + Sections Setup)

**What to do**:
- Extract the top-of-function setup into a dedicated builder:
  - ConcreteProperties instantiation
  - material tags + `model.add_material(...)`
  - section tags + `get_elastic_beam_section(...)` + `model.add_section(...)`
- Keep tag values stable (existing tests assume section tags 1/2/3 in several places).

**References**:
- `src/fem/model_builder.py:1000` - beam/column concrete and material tags
- `src/fem/model_builder.py:1024` - primary/secondary/column section tags
- `tests/test_model_builder.py` - asserts section tags for primary/secondary/columns

**Acceptance Criteria**:
- [ ] Material/section creation moved out of `build_fem_model()` into builder
- [ ] All existing model_builder tests pass

**Parallelizable**: NO (depends on 6.1)
**Commit**: YES
- Message: `refactor(fem): extract materials/sections setup from build_fem_model`

---

### 6.4 Extract NodeGridBuilder (Grid Nodes + Base Fixity)

**What to do**:
- Extract grid node creation loop into a builder responsible for:
  - floor-based node numbering convention usage (via `NodeRegistry`)
  - base restraints (fixed at z=0)
  - returning `grid_nodes[(ix, iy, level)] -> node_tag`

**References**:
- `src/fem/model_builder.py:1054` - grid node creation
- `tests/test_model_builder.py:143` - basic frame node counts + base fixity

**Acceptance Criteria**:
- [ ] Node creation moved into builder
- [ ] Base fixity behavior unchanged (tests still pass)

**Parallelizable**: NO
**Commit**: NO (group with 6.5)

---

### 6.5 Extract ColumnBuilder (Columns + Omission + Ghost Columns)

**What to do**:
- Extract columns loop (including omission logic) into a dedicated builder.
- Ensure omission list behavior remains:
  - `options.suggested_omit_columns` is treated as the user-approved omission list
  - `model.omitted_columns` is populated for visualization (ghost columns)

**References**:
- `src/fem/model_builder.py:1068` - omission setup
- `src/fem/model_builder.py:1084` - columns loop
- `tests/test_verify_task_17_3_integration.py` - omission integration

**Acceptance Criteria**:
- [ ] Column omission behavior unchanged (including logging and ghost columns)
- [ ] `pytest tests/test_verify_task_17_3_integration.py` → PASS

**Parallelizable**: NO
**Commit**: YES
- Message: `refactor(fem): extract node/column builders and keep omission behavior`
- Files: `src/fem/model_builder.py`, (new builder module)

---

### 6.6 Extract CoreWallBuilder (Shell Walls + Coupling Beams)

**What to do**:
- Move core wall creation into a builder that:
  - creates wall NDMaterial + PlateFiberSection (stable tags)
  - uses `_extract_wall_panels()` + `WallMeshGenerator.generate_mesh()`
  - updates `registry.nodes_by_floor` for diaphragm creation
  - creates coupling beams when openings exist (using `CouplingBeamGenerator`)

**Guardrails**:
- Preserve tag ranges currently used:
  - wall nodes/elements: 50000-59999
  - coupling beams: 70000+

**References**:
- `src/fem/model_builder.py:1447` - wall mesh creation
- `src/fem/model_builder.py:1523` - coupling beams
- `tests/test_model_builder_wall_integration.py` - wall mesh tests

**Acceptance Criteria**:
- [ ] All wall integration tests pass
- [ ] Coupling beam creation is covered by at least one test (added in 6.1)

**Parallelizable**: NO
**Commit**: YES
- Message: `refactor(fem): extract core wall builder and preserve tag ranges`

---

### 6.7 Extract SlabBuilder (Slab Mesh + Openings + Surface Loads)

**What to do**:
- Move slab creation into a builder that:
  - defines slab section and adds it to the model
  - uses `SlabMeshGenerator.generate_mesh()` and shares existing nodes (snapping)
  - derives internal core opening via `_get_core_opening_for_slab()`
  - tracks slab tags for surface loads and applies `_apply_slab_surface_loads()`
  - updates `registry.nodes_by_floor` for diaphragms

**Guardrails**:
- Preserve tag ranges: slab nodes/elements 60000-69999.
- Preserve R3 behavior: slab openings represent internal void, not full core footprint.

**References**:
- `src/fem/model_builder.py:1622` - slab section/mesh
- `src/fem/model_builder.py:1646` - slab opening logic
- `src/fem/model_builder.py:1766` - surface loads application

**Acceptance Criteria**:
- [ ] Slab path covered by tests (added in 6.1)
- [ ] Surface loads applied to slab elements when enabled

**Parallelizable**: NO
**Commit**: NO (group with 6.8)

---

### 6.8 Introduce Director (Thin build_fem_model Wrapper)

**What to do**:
- Convert `build_fem_model()` into a thin orchestration wrapper (Director) that calls builders in phase order.
- Keep public API stable (`build_fem_model(project, options=None) -> FEMModel`).
- Keep the explicit phase boundaries readable in the code (Phase 1/2/3).

**References**:
- `src/fem/model_builder.py:1781` - Phase 2 (diaphragms + wind)
- `src/fem/model_builder.py:1806` - Phase 3 (validate)
- OpenSees BuildingTcl reference already linked in file header: `https://opensees.berkeley.edu/wiki/index.php?title=Getting_Started_with_BuildingTcl`

**Acceptance Criteria**:
- [ ] `build_fem_model()` body reduced substantially (target: <250 lines)
- [ ] All model_builder-related tests pass
- [ ] Performance benchmark from Track 1.6 shows no material regression (target: within ±10% build time)

**Parallelizable**: NO
**Commit**: YES
- Message: `refactor(fem): implement director + builders for model_builder phases`

---

### 6.9 Cleanup: Tag Management + Exports + Documentation

**What to do**:
- Ensure tag allocations are centralized or at least documented (avoid accidental collisions).
- Ensure `__all__` stays correct and imports remain stable.
- Add/refresh internal developer notes in module docstring explaining the phase/builder structure.

**Acceptance Criteria**:
- [ ] `pytest tests/test_model_builder*.py` → PASS
- [ ] `pytest tests/test_integration_e2e.py -k build_fem_model` → PASS

**Parallelizable**: NO
**Commit**: YES
- Message: `chore(fem): document model_builder builder structure and verify exports`

---

## Track 6 Summary

| Task | Description | Effort | Parallelizable |
|------|-------------|--------|----------------|
| 6.1 | Characterization tests (refactor safety net) | 60-90 min | With 6.2 (design only) |
| 6.2 | BeamBuilder extraction (dedupe 4 blocks) | 2-3 hours | No |
| 6.3 | Materials/sections builder extraction | 45-60 min | No |
| 6.4 | Node grid builder extraction | 30-45 min | No |
| 6.5 | Column builder + omissions extraction | 45-60 min | No |
| 6.6 | CoreWallBuilder + coupling beams extraction | 1-2 hours | No |
| 6.7 | SlabBuilder extraction | 1-2 hours | No |
| 6.8 | Director orchestration + phase structure | 60-90 min | No |
| 6.9 | Cleanup + exports + doc | 30 min | No |

**Total Effort**: ~8-12 hours
**Commits**: 6-7
**Primary Risk**: Behavioral regressions in trimming/tag allocation → mitigated by 6.1 characterization tests

---

## Track 7: Backend: visualization.py (Renderer + Overlay Refactor)

**Purpose**: Refactor `src/fem/visualization.py` into composable, testable components while preserving the public API and existing plot behaviors.

Evidence-based drivers:
- `create_plan_view()` is ~720 lines (`src/fem/visualization.py:603`).
- `create_elevation_view()` is ~415 lines (`src/fem/visualization.py:1326`).
- `create_3d_view()` is ~525 lines (`src/fem/visualization.py:1744`).
- Large duplicated blocks exist for: element-group rendering, utilization coloring + colorbar, deflected shape, reactions, supports, ghost columns, slabs.

**Target shape** (Plotly-friendly refactor patterns):
- Trace factory functions + explicit `fig.add_trace()` ordering (preserves z-order and legend ordering).
- Layout/scene builders separated from trace generation.
- Overlay renderers (utilization colorbar, deflection, reactions, loads) decoupled from base geometry rendering.

**Guardrails (Track 7)**:
- Do not change Plotly trace `name`s relied upon by tests (e.g., "Primary Beams", "Columns", "Omitted Columns")
- Preserve z-order (render order): slabs → beams → columns (avoid visual occlusion regressions)
- Preserve hover templates and `customdata` shapes used for tooltips

**External references (why they matter)**:
- Plotly incremental construction + serialization for testability: https://plotly.com/python/creating-and-updating-figures/ (supports `fig.to_dict()`-based assertions)
- Plotly figure factory pattern (modular trace/layout builders): https://github.com/plotly/plotly.py/blob/main/plotly/figure_factory/README.md
 - Plotly figure factory pattern (modular trace/layout builders): https://raw.githubusercontent.com/plotly/plotly.py/main/plotly/figure_factory/README.md

**Depends On**: Track 1 (baselines), Track 2.1 (visualization characterization tests)
**Effort**: ~6-10 hours

### 7.1 Add Visualization Regression/Characterization Tests (Before Refactor)

**What to do**:
- Add tests that lock down refactor-sensitive invariants that are not fully protected today:
  - utilization color mapping invariants (clamping behavior and stable output type)
  - trace ordering/z-order rules (e.g., slabs render below beams)
  - `grid_spacing` behavior (layout axis dtick)
  - deflection exaggeration scaling affects plotted coordinates (not just trace presence)
  - reaction/load arrow counts and presence (annotations + traces)
- Keep assertions resilient to harmless internal changes (avoid exact tag ordering unless required).

**References**:
- `src/fem/visualization.py:494` - `_get_utilization_color()`
- `src/fem/visualization.py:760` - utilization colorbar trace
- `src/fem/visualization.py:1619` - deflected shape overlay (elevation)
- `src/fem/visualization.py:2125` - deflected shape overlay (3D)
- `src/fem/visualization.py:1650` - reactions overlay (elevation)
- `src/fem/visualization.py:1202` - loads overlay (plan)
- `tests/test_visualization_plan_view.py`
- `tests/test_visualization_elevation_view.py`
- `tests/test_visualization_3d_view.py`
- `tests/test_visualization.py`
- `tests/test_integration_e2e.py` - visualization integration calls

**Acceptance Criteria**:
- [ ] New regression tests added (recommended file: `tests/test_visualization_regression.py`)
- [ ] At least 8-12 regression tests added covering the listed invariants
- [ ] `pytest tests/test_visualization*.py` → PASS
- [ ] `pytest tests/test_integration_e2e.py -k "visualization or plan_view or 3d_view"` → PASS

**Parallelizable**: YES (with 7.2 skeleton/package prep)
**Commit**: YES
- Message: `test(viz): add regression tests for plotly view refactor`

---

### 7.2 Create Visualization Subpackage and Keep Backward-Compatible Imports

**What to do**:
- Convert `src/fem/visualization.py` into a real package at the same import path:
  - Move the existing file to `src/fem/visualization/__init__.py` (so `import src.fem.visualization` still works, now as a package)
  - Then extract submodules under `src/fem/visualization/` while keeping `__init__.py` as the public compatibility surface (re-exports)

**Why this is required**:
- Python cannot safely have both `src/fem/visualization.py` and `src/fem/visualization/` as peers for the same import name.

**Note on file paths**:
- Before 7.2, references in this plan may point to `src/fem/visualization.py` line numbers.
- After 7.2, all subsequent edits must target `src/fem/visualization/__init__.py` and submodules under `src/fem/visualization/`.

**Proposed structure** (default):
```
src/fem/visualization/
├── __init__.py
├── config.py
├── projections.py
├── element_renderer.py
├── overlays.py
├── slab_renderer.py
├── ghost_elements.py
└── layouts.py
```

**References**:
- `src/fem/visualization.py:136` - `VisualizationConfig`
- `app.py:1941` - `VisualizationConfig(...)` call site

**Acceptance Criteria**:
- [ ] `src/fem/visualization.py` no longer exists as a module file; package exists at `src/fem/visualization/`
- [ ] Public imports remain stable (re-exported from `src/fem/visualization/__init__.py`), matching the current `__all__` surface:
  - `VisualizationBackend`, `VisualizationExtractionConfig`, `VisualizationData`
  - `build_visualization_data_from_fem_model`, `extract_visualization_data_from_opensees`, `export_plotly_figure_image`
  - `ViewType`, `VisualizationConfig`, `COLORS`
  - `create_plan_view`, `create_elevation_view`, `create_3d_view`, `create_model_summary_figure`, `get_model_statistics`
- [ ] Import check passes:
  - `python -c "from src.fem.visualization import VisualizationBackend, VisualizationExtractionConfig, VisualizationData, build_visualization_data_from_fem_model, extract_visualization_data_from_opensees, export_plotly_figure_image, ViewType, VisualizationConfig, COLORS, create_plan_view, create_elevation_view, create_3d_view, create_model_summary_figure, get_model_statistics"`
- [ ] `pytest tests/test_visualization_infrastructure.py` → PASS

**Migration checklist (after conversion)**:
- Re-run import-dependent consumers:
  - `python -c "import src.fem.visualization"`
  - `python -c "import app"` (import-time checks only)
- Re-run tests: `pytest tests/test_visualization*.py`
- Smoke import spike: `python -c "import src.fem.visualization_spike"` (if kept)

**Parallelizable**: YES (with 7.1)
**Commit**: NO (group with 7.3)

---

### 7.3 Extract View Projections (Plan/Elevation/3D Coordinate Mapping)

**What to do**:
- Extract projection logic into small, testable helpers/classes:
  - Plan: XY projection + floor visibility filter
  - Elevation: XZ or YZ mapping based on `view_direction`
  - 3D: XYZ passthrough

**References**:
- `src/fem/visualization.py:622` - plan floor selection/filtering
- `src/fem/visualization.py:1354` - elevation coordinate mapping
- `src/fem/visualization.py:1770` - 3D helpers

**Acceptance Criteria**:
- [ ] `create_*_view()` functions consume projection helpers instead of inline mapping
- [ ] `pytest tests/test_visualization_*.py` → PASS

**Parallelizable**: NO
**Commit**: YES
- Message: `refactor(viz): extract projection helpers for plan/elevation/3d`

---

### 7.4 Extract ElementRenderer (Deduplicate Element-Group Rendering)

**What to do**:
- Create a generic element rendering helper that consolidates repeated patterns:
  - batch rendering when no utilization
  - per-element traces when utilization is provided
  - consistent hover/customdata structure
  - consistent styling (line width, colorscale)
- Ensure all existing trace names remain stable where tests rely on them.

**References**:
- `src/fem/visualization.py:631` - `_classify_elements()` usage in each view
- `src/fem/visualization.py:708` - plan beam rendering (representative pattern)
- `src/fem/visualization.py:1364` - elevation columns rendering
- `src/fem/visualization.py:1923` - 3D beams rendering
- `tests/test_visualization.py` - `_classify_elements()` invariants

**Acceptance Criteria**:
- [ ] Duplicated element-group rendering blocks removed from all 3 view functions
- [ ] `pytest tests/test_visualization_plan_view.py` → PASS
- [ ] `pytest tests/test_visualization_elevation_view.py` → PASS
- [ ] `pytest tests/test_visualization_3d_view.py` → PASS

**Parallelizable**: NO
**Commit**: YES
- Message: `refactor(viz): add ElementRenderer and dedupe element rendering`

---

### 7.5 Extract Overlay Renderers (Utilization/Deflection/Reactions/Loads)

**What to do**:
- Implement overlay renderers as standalone functions/classes:
  - utilization colorbar (shared by plan/elevation/3D)
  - deflected shape overlay (elevation + 3D)
  - reactions overlay (elevation + 3D)
  - loads overlay (plan; optional extension to other views if already present)
- Preserve scaling math and config flags (`exaggeration`, `load_scale`, `show_supports`, `show_loads`).

**References**:
- `src/fem/visualization.py:760` - colorbar trace
- `src/fem/visualization.py:1619` - deflection overlay (elevation)
- `src/fem/visualization.py:1650` - reactions overlay (elevation)
- `src/fem/visualization.py:1202` - plan loads overlay

**Acceptance Criteria**:
- [ ] Overlay code removed from monolith view functions
- [ ] `pytest tests/test_visualization_regression.py` → PASS

**Parallelizable**: NO
**Commit**: YES
- Message: `refactor(viz): extract overlay renderers for deflection/reactions/loads`

---

### 7.6 Extract Slab and Ghost-Column Renderers

**What to do**:
- Move slab rendering into a dedicated renderer:
  - plan: filled polygons + optional mesh grid
  - 3D: `Mesh3d` surface
- Move ghost/omitted column rendering into a dedicated renderer used by all views.

**Known issue (treat as cleanup during refactor)**:
- Ghost/omitted columns appear to be rendered twice in plan view in current code. During extraction, consolidate to a single render path while preserving the visible result and trace name.

**References**:
- `src/fem/visualization.py:1043` - plan slab rendering
- `src/fem/visualization.py:2039` - 3D slab rendering
- `src/fem/visualization.py:863` - plan ghost columns
- `src/fem/visualization.py:1407` - elevation ghost columns
- `src/fem/visualization.py:1887` - 3D ghost columns

**Acceptance Criteria**:
- [ ] `tests/test_visualization.py` slab tooltip tests still pass
- [ ] Ghost columns remain visually distinct and appear under expected trace name(s)

**Parallelizable**: NO
**Commit**: NO (group with 7.7)

---

### 7.7 Refactor create_*_view() Functions into Thin Orchestrators + Cleanup

**What to do**:
- Convert `create_plan_view()`, `create_elevation_view()`, `create_3d_view()` into orchestration functions:
  - classify → render base geometry (renderer) → render overlays → apply layout
- Ensure `create_model_summary_figure()` keeps working (it calls create_* functions).
- Decide what to do with `src/fem/visualization_spike.py`:
  - default: keep as experimental (no production imports), but ensure it still runs or clearly marked as a spike.

**References**:
- `src/fem/visualization.py:2272` - `create_model_summary_figure()`
- `src/fem/visualization_spike.py` - spike usage

**Acceptance Criteria**:
- [ ] Public API signatures unchanged
- [ ] After 7.2 conversion, the compatibility surface stays small (target: `src/fem/visualization/__init__.py` < 400 lines)
- [ ] `pytest tests/test_visualization*.py` → PASS
- [ ] `pytest tests/test_integration_e2e.py -k visualization` → PASS

**Parallelizable**: NO
**Commit**: YES
- Message: `refactor(viz): split visualization into submodules and keep API stable`

---

## Track 7 Summary

| Task | Description | Effort | Parallelizable |
|------|-------------|--------|----------------|
| 7.1 | Add regression tests for refactor-sensitive behavior | 60-90 min | With 7.2 |
| 7.2 | Create visualization subpackage + compatibility surface | 30-45 min | With 7.1 |
| 7.3 | Extract projection helpers | 45-60 min | No |
| 7.4 | Extract ElementRenderer + dedupe element rendering | 2-3 hours | No |
| 7.5 | Extract overlay renderers (util/defl/reactions/loads) | 60-90 min | No |
| 7.6 | Extract slab + ghost renderers | 45-60 min | No |
| 7.7 | Thin orchestrators + cleanup + keep API stable | 60-90 min | No |

**Total Effort**: ~6-10 hours
**Commits**: 4-5
**Primary Risk**: subtle plot regressions (trace order/hover/annotations) → mitigated by 7.1

---

## Track 8: Backend: AI Providers (Deduplicate LLM Providers)

**Purpose**: Reduce ~850 lines of near-identical code in `src/ai/providers.py` while preserving behavior, error semantics, and public APIs.

Evidence-based drivers:
- `DeepSeekProvider`, `GrokProvider`, `OpenRouterProvider` each implement near-identical `chat()`, retry/backoff, error parsing, response parsing, health checks.
- Provider-specific behavior is minimal (OpenRouter extra headers; pricing differences).

**Guardrails (Track 8)**:
- Preserve exception hierarchy and semantics: `RateLimitError`, `AuthenticationError`, `ProviderUnavailableError`, `LLMProviderError`
- Preserve cost calculation formulas exactly (including OpenRouter returning 0.0 for dynamic pricing)
- Preserve `httpx` optional dependency error messaging (ImportError remains clear and provider-specific)

**Depends On**: Track 1 (test baseline)
**Effort**: ~3-5 hours

### 8.1 Provider Regression Tests (Small Additions Only)

**What to do**:
- Add minimal characterization tests that ensure provider-specific hooks stay intact after dedupe:
  - OpenRouter must send its extra headers when configured
  - Retry logic retries for 429/5xx and does not retry for auth errors

**References**:
- `src/ai/providers.py:1243` - OpenRouter headers
- `src/ai/providers.py:241` - exception hierarchy
- `tests/test_ai_providers.py` - extensive provider tests

**Acceptance Criteria**:
- [ ] New tests added (recommended: append to `tests/test_ai_providers.py`)
- [ ] `pytest tests/test_ai_providers.py` → PASS

**Parallelizable**: YES (with 8.2 scaffolding)
**Commit**: YES
- Message: `test(ai): add regression coverage for provider-specific headers and retry`

---

### 8.2 Move 100% Identical Utilities to Base Class

**What to do**:
- Move truly identical methods to `LLMProvider`:
  - `_calculate_backoff_delay()`
  - `estimate_tokens()`
- Keep behavior identical; do not change defaults.

**References**:
- `src/ai/providers.py:451` / `:833` / `:1221` - retry/backoff usage

**Acceptance Criteria**:
- [ ] Provider test suite remains green

**Parallelizable**: NO (small, but sequentially safest)
**Commit**: YES
- Message: `refactor(ai): move shared retry/token utilities into LLMProvider base`

---

### 8.3 Parameterize Error and Response Parsing (Remove Duplicates)

**What to do**:
- Consolidate `_handle_error_response()` and `_parse_response()` into base class using `self.provider_type` for provider labeling.
- Delete duplicate copies from provider subclasses.

**References**:
- `src/ai/providers.py:550` / `:932` / `:1324` - `_handle_error_response()`
- `src/ai/providers.py` response parsing blocks within provider classes

**Acceptance Criteria**:
- [ ] `pytest tests/test_ai_providers.py` → PASS
- [ ] Exception types raised for status codes unchanged

**Parallelizable**: NO
**Commit**: YES
- Message: `refactor(ai): unify error/response parsing across providers`

---

### 8.4 Extract HTTP Request + Retry Loop into Base With Provider Hooks

**What to do**:
- Move the core `_make_request_with_retry()` into base class.
- Introduce provider hook(s):
  - `_build_request_headers()` default uses bearer auth
  - OpenRouter override adds `HTTP-Referer` and `X-Title`
- Preserve retry conditions and backoff.

**References**:
- `src/ai/providers.py:477` / `:859` / `:1251` - `httpx.Client(...)` blocks
- `src/ai/providers.py:1243` - OpenRouter header injection

**Acceptance Criteria**:
- [ ] Provider-specific headers still present for OpenRouter
- [ ] Retry behavior unchanged (timeouts, request errors, 429, 5xx)
- [ ] `pytest tests/test_ai_providers.py` → PASS

**Parallelizable**: NO
**Commit**: YES
- Message: `refactor(ai): centralize HTTP request+retry logic with provider hooks`

---

### 8.5 Extract chat() Template Method (Delete Provider chat() Duplicates)

**What to do**:
- Implement `LLMProvider.chat()` as a template method in the base class.
- Add a payload builder hook (default OpenAI-compatible payload; supports `json_mode`).
- Delete duplicate `chat()` methods from subclasses.

**References**:
- `src/ai/providers.py:193` - base class abstract `chat()`
- `src/ai/llm_service.py:158` - AIService.chat call contract

**Acceptance Criteria**:
- [ ] `pytest tests/test_ai_providers.py` → PASS
- [ ] `pytest tests/test_ai_integration.py -m "not slow"` → PASS (if configured)

**Parallelizable**: NO
**Commit**: YES
- Message: `refactor(ai): implement base chat() template and remove duplicate provider methods`

---

## Track 8 Summary

| Task | Description | Effort | Parallelizable |
|------|-------------|--------|----------------|
| 8.1 | Add small regression tests for provider-specific hooks | 30-45 min | With 8.2 |
| 8.2 | Move identical utilities to base | 20-30 min | No |
| 8.3 | Unify error/response parsing | 45-60 min | No |
| 8.4 | Centralize HTTP retry logic with hooks | 60-90 min | No |
| 8.5 | Base chat() template + remove duplicates | 45-60 min | No |

**Total Effort**: ~3-5 hours
**Commits**: 4-5
**Primary Risk**: subtle change in error handling/retry semantics → mitigated by existing provider test suite + 8.1

---

## Track 9: Regression & Cleanup

**Purpose**: Prove v3.6 refactors are safe (tests, perf, UI smoke), then remove sharp edges and consolidate remaining loose ends.

**Depends On**: Tracks 2-8 completion
**Effort**: ~2-4 hours

### 9.1 Run Full Test Suite + Coverage and Capture Evidence

**What to do**:
- Run the full suite and save results/coverage summary to evidence.

**Verification commands** (PowerShell):
```powershell
# Run tests and capture output to evidence file
pytest tests/ --tb=short | Tee-Object -FilePath .sisyphus/evidence/v36-tests-and-coverage.md
pytest tests/ --cov=src --cov-report=term-missing | Tee-Object -FilePath .sisyphus/evidence/v36-tests-and-coverage.md -Append
```

**Acceptance Criteria**:
- [ ] Full suite passes
- [ ] `.sisyphus/evidence/v36-tests-and-coverage.md` exists and contains test results + coverage report
- [ ] Verification: `Test-Path .sisyphus/evidence/v36-tests-and-coverage.md` → True

**Parallelizable**: NO
**Commit**: NO (group with 9.4)

---

### 9.2 Re-run Performance Benchmark and Compare to Baseline

**What to do**:
- Re-run the benchmark from Track 1.6 and compare to baseline numbers.
- The benchmark script writes to `v36-perf-baseline.md` by default; copy/rename output to `v36-perf-after.md` for comparison.

**Verification commands** (PowerShell):
```powershell
# Run benchmark (outputs to v36-perf-baseline.md by design)
python scripts/bench_v36.py

# Copy baseline output to after file for comparison
Copy-Item .sisyphus/evidence/v36-perf-baseline.md .sisyphus/evidence/v36-perf-after.md

# Alternatively, modify script to accept --out parameter if needed
```

**Acceptance Criteria**:
- [ ] `.sisyphus/evidence/v36-perf-after.md` created (copy from benchmark output)
- [ ] Model build time within ±10% of baseline (or explain and accept regression)
- [ ] If regression exceeds 20%, treat as blocking until investigated and either fixed or explicitly accepted
- [ ] Verification: `Test-Path .sisyphus/evidence/v36-perf-after.md` → True

**Parallelizable**: NO
**Commit**: NO

---

### 9.3 Streamlit UI Smoke Test + Screenshot Evidence

**What to do**:
- Run the app locally and verify the primary user paths still work:
  - sidebar updates project
  - unified FEM views render plan/elevation/3D
  - FEM analysis overlay toggles work (loads/reactions/deflection)
  - export controls still function
- Capture a small screenshot set for regression evidence.

**Verification**:
- Command: `streamlit run app.py`
- Save screenshots to `.sisyphus/evidence/v36-ui-*.png`

**Acceptance Criteria**:
- [ ] No runtime errors
- [ ] Screenshots captured (at least: plan, elevation, 3D, analysis overlay)

**Parallelizable**: NO
**Commit**: NO

---

### 9.4 Cleanup Pass (Dead Code, Exports, Docs) + Final Commit

**What to do**:
- Remove or clearly quarantine experimental/spike modules that are no longer needed.
- Ensure public exports remain stable (`src/ai/__init__.py`, `src/fem/visualization/__init__.py` compatibility surface).
- Update any developer notes / docstrings that describe the new modular architecture.

**References**:
- `src/fem/visualization_spike.py` - spike module
- `src/fem/visualization/__init__.py` - compatibility surface (post-7.2)
- `src/ai/__init__.py` - provider exports

**Acceptance Criteria**:
- [ ] `pytest tests/ --tb=short` → PASS
- [ ] Evidence files present: `.sisyphus/evidence/v36-tests-and-coverage.md`, `.sisyphus/evidence/v36-perf-after.md`, `.sisyphus/evidence/v36-ui-*.png`

**Parallelizable**: NO
**Commit**: YES
- Message: `chore(v36): regression evidence and cleanup after refactors`

---

## Track 9 Summary

| Task | Description | Effort | Parallelizable |
|------|-------------|--------|----------------|
| 9.1 | Full tests + coverage evidence | 30-60 min | No |
| 9.2 | Performance benchmark comparison | 20-40 min | No |
| 9.3 | UI smoke + screenshots | 30-60 min | No |
| 9.4 | Cleanup + exports + final commit | 30-60 min | No |

**Total Effort**: ~2-4 hours
**Commits**: 1
