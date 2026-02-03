# FEM Architecture Documentation

## Overview

PrelimStruct uses a multi-phase FEM model construction workflow based on OpenSeesPy. The architecture follows a **Director/Builder pattern** where `FEMModelDirector` orchestrates specialized builders.

---

## 1. Module Structure

```
src/fem/
├── fem_engine.py          # FEMModel class, Node, Element, Load dataclasses
├── model_builder.py       # Legacy monolithic builder + utilities
├── solver.py              # FEMSolver for OpenSeesPy analysis
├── visualization.py       # Plan/Elevation/3D rendering
├── load_combinations.py   # HK Code 2013 load combination factors
│
├── builders/              # Director/Builder pattern
│   ├── director.py        # FEMModelDirector - orchestrates all builders
│   ├── node_grid_builder.py   # Creates grid nodes
│   ├── column_builder.py      # Creates column elements
│   ├── beam_builder.py        # Creates beam elements (primary, secondary, coupling)
│   ├── core_wall_builder.py   # Creates core wall shell elements
│   └── slab_builder.py        # Creates slab shell elements
│
├── core_wall_geometry.py  # Core wall shape generators
├── coupling_beam.py       # Coupling beam geometry
├── beam_trimmer.py        # Beam trimming at walls
├── slab_element.py        # SlabPanel, SlabMeshGenerator
├── wall_element.py        # WallPanel, WallMeshGenerator
└── materials.py           # ConcreteProperties, section generators
```

---

## 2. Model Building Pipeline

```
ProjectData (user input)
        │
        ▼
┌───────────────────────┐
│   FEMModelDirector    │  ← Entry point: director.build()
└───────────────────────┘
        │
        ├─────────────────────────────────────────────────┐
        │                                                 │
        ▼                                                 ▼
┌──────────────┐  Phase 1: Setup             ┌──────────────────┐
│ Materials    │  ─────────────────────────► │ Sections Created │
│ • beam_mat   │  Concrete01 materials       │ • primary_beam   │
│ • column_mat │  ElasticBeamSection         │ • secondary_beam │
└──────────────┘                             │ • column         │
        │                                    └──────────────────┘
        ▼
┌──────────────────────┐  Phase 2: Nodes
│   NodeGridBuilder    │  ─────────────────────────────────────►
│   Floor-based IDs:   │
│   • Ground: 1-999    │  Creates grid nodes at column intersections
│   • Floor N: N*1000+ │  Fixed supports at z=0
└──────────────────────┘
        │
        ▼
┌──────────────────────┐  Phase 3: Elements
│   ColumnBuilder      │  ─────────────────────────────────────►
│   Creates vertical   │  Columns from floor to floor
│   beam-column elems  │  Omits columns near core (optional)
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│   BeamBuilder        │  ─────────────────────────────────────►
│   • Primary beams    │  Along gridlines (trimmed at core)
│   • Secondary beams  │  Interior subdivision beams
│   • Coupling beams   │  At core wall openings
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│   CoreWallBuilder    │  ─────────────────────────────────────►
│   ShellMITC4 quads   │  Vertical shell elements
│   5 configurations   │  PlateFiberSection material
└──────────────────────┘
        │
        ▼
┌──────────────────────┐
│   SlabBuilder        │  ─────────────────────────────────────►
│   ShellMITC4 quads   │  Horizontal shell mesh
│   With core opening  │  ElasticMembranePlateSection
└──────────────────────┘
        │
        ▼
┌──────────────────────┐  Phase 4: Loads
│   Load Application   │  ─────────────────────────────────────►
│   • Rigid diaphragms │  Per floor
│   • Wind loads       │  Applied to diaphragm masters
│   • Gravity loads    │  Already applied during element creation
└──────────────────────┘
        │
        ▼
┌──────────────────────┐  Phase 5: Validation
│   Model Validation   │  ─────────────────────────────────────►
│   • Node connectivity│
│   • Element validity │
└──────────────────────┘
        │
        ▼
     FEMModel (complete)
```

---

## 3. Load Application Details

### 3.1 Load Types

| Load Type | Applied To | Application Method |
|-----------|------------|-------------------|
| **Dead Load (DL)** | Beam elements | UniformLoad (N/m) based on self-weight |
| **Dead Load (DL)** | Slab elements | SurfaceLoad (N/m²) |
| **Superimposed Dead (SDL)** | Slab elements | Included in SurfaceLoad pressure |
| **Live Load (LL)** | Slab elements | Included in SurfaceLoad pressure |
| **Wind Load (W)** | Diaphragm masters | Point load at floor center of mass |

### 3.2 Gravity Load Path

#### A. Beam Self-Weight

**Location:** `src/fem/builders/beam_builder.py` lines 147-161

```python
# Beam self-weight calculation
width_m = section_dims[0] / 1000.0
depth_m = section_dims[1] / 1000.0
beam_self_weight = CONCRETE_DENSITY * width_m * depth_m  # kN/m
w_total = beam_self_weight * 1000.0  # Convert to N/m

model.add_uniform_load(UniformLoad(
    element_tag=current_tag,
    load_type="Gravity",
    magnitude=w_total,
    load_pattern=load_pattern,
))
```

**Example:**
- Primary beam: 450mm × 700mm
- Self-weight = 24.5 kN/m³ × 0.45m × 0.70m = 7.72 kN/m = 7720 N/m

#### B. Slab Surface Load

**Location:** `src/fem/builders/slab_builder.py` lines 227-267

```python
def _get_slab_design_load(self) -> float:
    """Get factored slab load in kPa."""
    # Calculate total dead load
    slab_self_weight = slab_thickness * CONCRETE_DENSITY  # kPa
    total_dead = project.loads.dead_load + slab_self_weight
    total_live = project.loads.live_load
    
    # HK Code load factors
    return GAMMA_G * total_dead + GAMMA_Q * total_live
```

**Example (typical residential):**
- Slab thickness: 200mm → self-weight = 0.2m × 24.5 kN/m³ = 4.90 kPa
- SDL (finishes): 1.5 kPa
- Live load: 2.0 kPa
- Total DL = 4.90 + 1.5 = 6.40 kPa
- **Design load = 1.4 × 6.40 + 1.6 × 2.0 = 8.96 + 3.20 = 12.16 kPa**

### 3.3 Wind Load Path

**Location:** `src/fem/builders/director.py` lines 353-387

1. **Wind result** comes from `project.wind_result` (calculated by wind_engine.py)
2. **Floor shears** computed by `_compute_floor_shears()`
3. **Applied to diaphragm masters** via `apply_lateral_loads_to_diaphragms()`

```
Wind Result (total base shear)
        │
        ▼
Floor Shears (story shear at each level)
        │
        ▼
Diaphragm Master Node (point load Fx or Fy)
```

---

## 4. HK Code 2013 Load Factors

**Source:** `src/core/constants.py`

| Factor | Value | Description |
|--------|-------|-------------|
| γ_G (GAMMA_G) | 1.4 | Dead load - ULS |
| γ_Q (GAMMA_Q) | 1.6 | Live load - ULS |
| γ_W (GAMMA_W) | 1.4 | Wind load - ULS |
| γ_G_SLS | 1.0 | Dead load - SLS |
| γ_Q_SLS | 1.0 | Live load - SLS |

### Load Combinations (from load_combinations.py)

| Combo | Equation | Description |
|-------|----------|-------------|
| LC1 | 1.4Gk + 1.6Qk | ULS Gravity |
| LC2 | 1.2Gk + 1.2Qk + 1.2Wk | ULS Wind + Gravity |
| SLS1 | 1.0Gk + 1.0Qk | SLS Full Live |
| SLS2 | 1.0Gk + 0.4Qk | SLS Permanent + 40% LL |
| SLS3 | 1.0Gk + 0.4Qk + 1.0Wk | SLS + Wind |

---

## 5. Element Types

### 5.1 Beam/Column Elements

**Type:** `ElementType.ELASTIC_BEAM`

OpenSeesPy element: `elasticBeamColumn`

Properties defined by `get_elastic_beam_section()`:
- E: Elastic modulus (from HK Code Cl 3.1.7)
- A: Cross-sectional area
- Iz, Iy: Moments of inertia
- J: Torsional constant

### 5.2 Shell Elements (Walls and Slabs)

**Type:** `ElementType.SHELL_MITC4`

OpenSeesPy element: `ShellMITC4`

For walls: `PlateFiberSection` with `PlaneStress` material
For slabs: `ElasticMembranePlateSection`

---

## 6. Node Numbering Convention

**OpenSees BuildingTcl convention:**

| Level | Node Range | Example |
|-------|------------|---------|
| Ground (0) | 1-999 | Node 5 = 5th column at ground |
| Floor 1 | 1000-1999 | Node 1005 = 5th column at Level 1 |
| Floor N | N×1000 to N×1000+999 | Node 5003 = 3rd column at Level 5 |
| Wall shells | 50000-59999 | Special range for wall mesh nodes |
| Slab shells | 60000-69999 | Special range for slab mesh nodes |

---

## 7. Analysis Flow

```
FEMModel (complete)
        │
        ▼
┌───────────────────────┐
│   OpenSeesPy Build    │  model.build_opensees_model()
│   • ops.wipe()        │
│   • ops.model()       │
│   • Create nodes      │
│   • Create elements   │
│   • Apply loads       │
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│   FEMSolver           │  solver.run_linear_static_analysis()
│   • ops.constraints   │  Plain
│   • ops.numberer      │  RCM
│   • ops.system        │  BandGeneral
│   • ops.algorithm     │  Linear
│   • ops.integrator    │  LoadControl(1.0)
│   • ops.analyze(1)    │  Single step
└───────────────────────┘
        │
        ▼
┌───────────────────────┐
│   AnalysisResult      │  solver.extract_results()
│   • node_displacements│  {node_tag: [ux,uy,uz,rx,ry,rz]}
│   • node_reactions    │  {node_tag: [Fx,Fy,Fz,Mx,My,Mz]}
│   • element_forces    │  {elem_tag: {N,Vy,Vz,My,Mz,T}}
└───────────────────────┘
```

---

## 8. Session State & Caching

**Location:** `src/ui/views/fem_views.py`

| Session Key | Type | Purpose |
|-------------|------|---------|
| `fem_model_cache` | FEMModel | Cached model object |
| `fem_model_hash` | str | Hash for cache invalidation |
| `fem_preview_analysis_result` | AnalysisResult | Cached analysis results |
| `fem_inputs_locked` | bool | Prevents edits after analysis |
| `fem_selected_load_combo` | str | Current load combination |

**Cache invalidation:** When model geometry changes, `_get_or_build_cached_model()` detects hash mismatch and calls `_clear_analysis_state()` to clear stale results.

---

## 9. Key File References

| File | Line | Description |
|------|------|-------------|
| `director.py:81-116` | FEMModelDirector.build() | Main entry point |
| `beam_builder.py:147-161` | Beam self-weight | UniformLoad application |
| `slab_builder.py:227-267` | Slab surface load | Design load calculation |
| `director.py:353-387` | Wind load application | Diaphragm lateral loads |
| `solver.py:96-150` | Linear static analysis | OpenSeesPy commands |
| `constants.py:17-20` | Load factors | GAMMA_G, GAMMA_Q |

---

*Last Updated: 2026-02-03*
