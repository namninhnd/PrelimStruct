# Local Axis Convention Fix — Phase Index

## ETABS Convention Target
- **Mz = M33 = ALWAYS major-axis bending** for ALL frame elements
- **My = M22 = ALWAYS minor-axis bending**
- **Iz = I33 = strong-axis MOI**, **Iy = I22 = weak-axis MOI**
- **Positive Mz = sagging** (tension at bottom)

## The Core Bug
`vecxz = (0,0,1)` for beams makes `local_z = vertical`, so gravity bending → `My` → uses `Iy` (weak axis) = WRONG stiffness. The fix changes vecxz per element so `local_y = vertical` and `Mz = major-axis bending`.

## Phase Dependency Chain

```
Phase 0 (rename)
    │
    ├── Phase 1 (beams) ──┐
    │                      ├── Phase 4 (envelope)
    ├── Phase 2 (columns) ─┤        │
    │                      │        ├── Phase 5 (visualization)
    └── Phase 3 (coupling) ┘        │        │
                                    └────────┴── Phase 6 (tests)
```

**Sequential gates:**
- Phase 0 must complete before ALL others
- Phases 1, 2, 3 can run in parallel after Phase 0 (but sequential is safer)
- Phase 4 requires Phases 1-3
- Phase 5 requires Phase 4
- Phase 6 requires Phase 5

## Phase Summary

| Phase | File | Scope | Gate Criteria |
|-------|------|-------|---------------|
| **0** | `phase-0-rename-vecxz.md` | Rename `local_y` → `vecxz` in 10 locations | All 793 tests pass, zero grep matches |
| **1** | `phase-1-beam-vecxz-fix.md` | Compute beam vecxz = (dy,-dx,0) | Hand calc: Mz = wL²/8, positive |
| **2** | `phase-2-column-verify-mapping.md` | Verify columns + add h/b mapping | Hand calc: column Mz = P*H for X-load |
| **3** | `phase-3-coupling-beam-vecxz.md` | Compute coupling beam vecxz | X-span and Y-span both give Mz = major |
| **4** | `phase-4-envelope-separation.md` | Split M→Mz/My, V→Vy/Vz | Envelope fields separated, consumers updated |
| **5** | `phase-5-visualization-tables.md` | Fix labels, headers, add axis arrows | Mz labeled "Major", tables annotated |
| **6** | `phase-6-integration-tests.md` | Rewrite tests, full suite green | ALL tests pass, zero xfails |
| **7** | (Post-phase fix) | Fix `eleForce` (global) -> `localForce` (local) + gravity `wz`->`wy` | 167 passed, 0 failed |

### Phase 7: Post-Phase Fix (2026-02-08)

Phases 0-6 left two critical bugs that caused Mz/My to remain inverted:

1. **Gravity direction** (`fem_engine.py`): After Phase 1 changed vecxz, gravity should be `wy=-magnitude` (not `wz`), because local_y is now vertical.
2. **Force extraction** (`solver.py`): `ops.eleForce()` returns GLOBAL coordinates. Switched to `ops.eleResponse(tag, 'localForce')` which returns true LOCAL coordinates.

Full details: `.sisyphus/HANDOFF_20260208_LOCAL_AXIS_FINAL.md`

## Key Technical Reference

### vecxz Formula (Horizontal Beams)
```
vecxz = (dy / length, -dx / length, 0.0)
```
Where `(dx, dy)` = beam direction in plan. This gives `local_y = (0,0,1)` vertical for ANY horizontal beam angle.

### OpenSeesPy API
```python
ops.geomTransf('Linear', tag, *vecxz)         # Linear only, no PDelta/Corotational
ops.element('elasticBeamColumn', tag, *nodes,
            A, E, G, J, Iy, Iz, transfTag)     # Iy before Iz
```
- `My` stiffness = `E * Iy`
- `Mz` stiffness = `E * Iz`

### Force Extraction API (CRITICAL)
```python
# WRONG - returns GLOBAL coordinates:
forces = ops.eleForce(tag)

# CORRECT - returns LOCAL coordinates:
forces = ops.eleResponse(tag, 'localForce')
# [N_i, Vy_i, Vz_i, T_i, My_i, Mz_i, N_j, Vy_j, Vz_j, T_j, My_j, Mz_j]
```

### Section Properties (materials.py)
```python
Iz = b * h**3 / 12   # Strong axis when h > b
Iy = h * b**3 / 12   # Weak axis when h > b
```

### Files Touched Across All Phases
| File | Phases |
|------|--------|
| `src/fem/builders/beam_builder.py` | 0, 1, 3 |
| `src/fem/builders/column_builder.py` | 0, 2 |
| `src/fem/fem_engine.py` | 0, 7 |
| `src/fem/model_builder.py` | 0, 1, 3 |
| `src/fem/materials.py` | 2 |
| `src/fem/results_processor.py` | 4 |
| `src/fem/visualization.py` | 5 |
| `src/ui/components/beam_forces_table.py` | 5 |
| `src/ui/components/column_forces_table.py` | 5 |
| `src/fem/solver.py` | 7 |
| `tests/` (various) | 0, 1, 2, 3, 4, 6, 7 |

## Decisions Record (Confirmed by User)

| Decision | Choice |
|----------|--------|
| Beam vecxz formula | General: `vecxz = (dy, -dx, 0)` from node coords |
| Column approach | Verify → add explicit h/b mapping (both sides) |
| Variable rename | `local_y` → `vecxz` throughout, separate commit |
| Moment envelope | Separate: `Mz` (major) / `My` (minor) |
| Shear envelope | Separate: `Vy` / `Vz` |
| Envelope key naming | Local axis names (Mz, My, Vy, Vz) |
| Column mapping | Belt and suspenders (materials.py + column_builder.py) |
| Sign convention | Positive Mz = sagging for ALL line elements |
| Shell elements | Already correct, document only |
| Column rotation | Not adding rotation angle property |
