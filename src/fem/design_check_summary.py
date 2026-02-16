from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.fem.combination_processor import combine_results, compute_envelope, get_applicable_combinations
from src.fem.design_checks import (
    FlexuralCheckResult,
    GoverningItem,
    ShearCapacityResult,
    StructuralClass,
    beam_flexural_check,
    classify_element,
    classify_shell_orientation,
    compute_governing_score,
    concrete_shear_capacity,
    ductility_check,
    select_top_n,
    shear_stress_check,
)
from src.fem.load_combinations import LoadCombinationLibrary


ORDERED_TYPE_LABELS: Tuple[str, ...] = (
    "Slab Strip X",
    "Slab Strip Y",
    "Primary Beam",
    "Secondary Beam",
    "Column",
    "Wall",
    "Coupling Beam",
)


@dataclass
class DesignChecksSummary:
    top3_by_type: Dict[str, List[Dict[str, Any]]]
    warnings: List[str]


def _elem_dims_mm(project: Any, element: Any, elem_class: StructuralClass) -> Tuple[float, float]:
    """Return (b_mm, d_mm) for an element. d is effective depth (total - cover)."""
    width_m = element.geometry.get("width", 0.0)
    depth_m = element.geometry.get("depth", 0.0)

    if width_m and depth_m:
        b = width_m * 1000.0
        d = depth_m * 1000.0 - 40.0
        return max(b, 100.0), max(d, 100.0)

    if elem_class == StructuralClass.COLUMN and getattr(project, "column_result", None):
        col = project.column_result
        return max(float(col.width or 400.0), 100.0), max(float(col.depth or col.dimension or 400.0) - 40.0, 100.0)

    if elem_class == StructuralClass.SECONDARY_BEAM and getattr(project, "secondary_beam_result", None):
        beam = project.secondary_beam_result
        return max(float(beam.width or 300.0), 100.0), max(float(beam.depth or 500.0) - 40.0, 100.0)

    if elem_class == StructuralClass.COUPLING_BEAM:
        cb_w = float(getattr(project, "coupling_beam_width_mm", 500.0))
        cb_d = float(getattr(project, "coupling_beam_depth_mm", 800.0))
        return max(cb_w, 100.0), max(cb_d - 40.0, 100.0)

    if getattr(project, "primary_beam_result", None):
        beam = project.primary_beam_result
        return max(float(beam.width or 300.0), 100.0), max(float(beam.depth or 600.0) - 40.0, 100.0)

    return 300.0, 500.0


def _element_span_m(model: Any, element: Any) -> float:
    if len(element.node_tags) < 2:
        return 0.0
    n1 = model.nodes[element.node_tags[0]]
    n2 = model.nodes[element.node_tags[-1]]
    return hypot(float(n2.x) - float(n1.x), float(n2.y) - float(n1.y))


def _beam_orientation(model: Any, element: Any) -> str:
    if len(element.node_tags) < 2:
        return "X"
    n1 = model.nodes[element.node_tags[0]]
    n2 = model.nodes[element.node_tags[-1]]
    dx = abs(float(n2.x) - float(n1.x))
    dy = abs(float(n2.y) - float(n1.y))
    return "X" if dx >= dy else "Y"


def _build_type_dict(items: Dict[str, List[GoverningItem]], top_n: int) -> Dict[str, List[Dict[str, Any]]]:
    result: Dict[str, List[Dict[str, Any]]] = {label: [] for label in ORDERED_TYPE_LABELS}
    for label in ORDERED_TYPE_LABELS:
        top_items = select_top_n(items.get(label, []), n=top_n)
        result[label] = [
            {
                "element_id": it.element_id,
                "key_metric": it.key_metric,
                "score": it.governing_score,
                "warnings": it.warnings,
                "combo": it.governing_combo,
                "flexural": getattr(it, "flexural", None),
                "shear_capacity": getattr(it, "shear_capacity", None),
                "span_m": getattr(it, "span_m", None),
            }
            for it in top_items
        ]
    return result


def _extract_envelope_value(env: Any, field: str) -> Tuple[float, str]:
    """Extract (max_value, governing_case_name) from an envelope field."""
    obj = getattr(env, field, None)
    if obj is None:
        return 0.0, ""
    val = float(getattr(obj, "max_value", 0.0) or 0.0)
    case = str(getattr(obj, "governing_max_case_name", "") or "")
    return val, case


def _get_fcu(project: Any) -> float:
    if getattr(project, "materials", None):
        return float(getattr(project.materials, "fcu_beam", 40.0))
    return 40.0


def _get_fy(project: Any) -> float:
    if getattr(project, "materials", None):
        return float(getattr(project.materials, "fy", 500.0))
    return 500.0


def compute_design_checks_summary(
    project: Any,
    model: Any,
    results_by_case: Dict[str, Any],
    selected_combination_names: Optional[Sequence[str]] = None,
    top_n: int = 3,
) -> DesignChecksSummary:
    if not results_by_case:
        return DesignChecksSummary(
            top3_by_type={label: [] for label in ORDERED_TYPE_LABELS},
            warnings=["No solved load cases available"],
        )

    warnings: List[str] = []
    fcu = _get_fcu(project)
    fy = _get_fy(project)

    # Build combined results from load combinations
    all_defs = LoadCombinationLibrary.get_all_combinations()
    selected_name_set = set(selected_combination_names or [])
    selected_defs = [c for c in all_defs if c.name in selected_name_set] if selected_name_set else all_defs

    available_cases = list(results_by_case.keys())
    applicable_defs = get_applicable_combinations(selected_defs, available_cases)
    if not applicable_defs:
        applicable_defs = get_applicable_combinations(all_defs, available_cases)
        warnings.append("Selected combinations were not applicable; used available canonical combinations instead")

    combined_results: Dict[str, Any] = {}
    for comb in applicable_defs:
        combined_results[comb.name] = combine_results(results_by_case, comb)

    if not combined_results:
        return DesignChecksSummary(
            top3_by_type={label: [] for label in ORDERED_TYPE_LABELS},
            warnings=["Could not build applicable combined results"],
        )

    envelope = compute_envelope(combined_results)
    items_by_label: Dict[str, List[GoverningItem]] = {label: [] for label in ORDERED_TYPE_LABELS}

    class_to_label = {
        StructuralClass.PRIMARY_BEAM: "Primary Beam",
        StructuralClass.SECONDARY_BEAM: "Secondary Beam",
        StructuralClass.COUPLING_BEAM: "Coupling Beam",
        StructuralClass.COLUMN: "Column",
    }

    # --- Frame elements (beams, columns, coupling beams) ---
    for eid, element in model.elements.items():
        try:
            elem_class = classify_element(model, eid)
        except ValueError:
            continue

        env = envelope.get(eid)
        if env is None:
            continue

        b, d = _elem_dims_mm(project, element, elem_class)

        # Extract envelope forces (OpenSeesPy outputs N and N-m)
        vy, vy_case = _extract_envelope_value(env, "Vy_max")
        mz, mz_case = _extract_envelope_value(env, "Mz_max")
        n_axial, n_case = _extract_envelope_value(env, "N_max")

        # Convert: forces are in N, moments in N-m
        # HK COP formulas use N and mm
        V_N = abs(vy)
        M_Nmm = abs(mz) * 1e3       # N-m -> N-mm (1 N-m = 1000 N-mm)
        N_N = abs(n_axial)

        label = class_to_label.get(elem_class)
        if label is None:
            continue

        warnings_local: List[str] = []
        span_m = _element_span_m(model, element)

        if elem_class in (StructuralClass.PRIMARY_BEAM, StructuralClass.SECONDARY_BEAM):
            # --- Beam design: flexural + shear capacity + span/depth ---
            flex = beam_flexural_check(M_Nmm, b, d, fcu, fy)
            shear_cap = concrete_shear_capacity(V_N, b, d, fcu, flex.As_req, fyv=250.0)

            # Span/depth ratio check (basic continuous beam = 26)
            Ld_actual = (span_m * 1000.0) / d if d > 0 else 0.0
            Ld_limit = 26.0  # continuous beam
            Ld_ok = Ld_actual <= Ld_limit

            # Governing score: max of shear ratio, flexural rho ratio
            shear_util = shear_cap.v / shear_cap.vc if shear_cap.vc > 0 else 0.0
            flex_util = flex.rho / 2.5 if flex.rho > 0 else 0.0  # rho / rho_max_beam
            score = compute_governing_score(
                shear_ratio=shear_util,
                rho_ratio=flex_util,
                deflection_ratio=Ld_actual / Ld_limit if Ld_limit > 0 else 0.0,
            )

            if flex.is_doubly:
                warnings_local.append("Doubly reinforced (K > K')")
            if not Ld_ok:
                warnings_local.append(f"L/d={Ld_actual:.1f} > {Ld_limit:.0f}")

            governing_combo = mz_case or vy_case
            key_metric = (
                f"M={abs(mz):.0f}kNm As={flex.As_req:.0f}mm2 {flex.rebar_suggestion} | "
                f"V={V_N/1000:.0f}kN v/vc={shear_util:.2f} {shear_cap.link_suggestion} | "
                f"L/d={Ld_actual:.1f}/{Ld_limit:.0f}"
            )

            item = GoverningItem(
                element_id=eid,
                element_class=elem_class,
                governing_score=score,
                governing_combo=governing_combo,
                key_metric=key_metric,
                warnings=warnings_local,
            )
            # Attach extra data for UI tables
            item.flexural = flex  # type: ignore[attr-defined]
            item.shear_capacity = shear_cap  # type: ignore[attr-defined]
            item.span_m = span_m  # type: ignore[attr-defined]
            items_by_label[label].append(item)

            # Slab strip proxy
            orientation = _beam_orientation(model, element)
            strip_label = "Slab Strip X" if orientation == "X" else "Slab Strip Y"
            # Slab strip: per-metre values (divide by tributary width ~ beam spacing)
            strip_item = GoverningItem(
                element_id=eid,
                element_class=StructuralClass.SLAB_SHELL,
                governing_score=score,
                governing_combo=governing_combo,
                key_metric=(
                    f"Proxy from beam ({orientation}), span={span_m:.2f}m, "
                    f"As={flex.As_req:.0f}mm2, v/vc={shear_util:.2f}"
                ),
                warnings=[],
            )
            strip_item.flexural = flex  # type: ignore[attr-defined]
            strip_item.span_m = span_m  # type: ignore[attr-defined]
            items_by_label[strip_label].append(strip_item)

        elif elem_class == StructuralClass.COLUMN:
            # --- Column design: axial ratio + shear ---
            # Note: for columns, b is width, d is depth-cover
            ag = b * (d + 40.0)  # gross area uses full depth (d + cover)
            duct = ductility_check(N_N, fcu, ag)
            shear = shear_stress_check(V_N, b, d, fcu)
            n_ratio = (duct.n_ratio / duct.threshold) if duct.threshold > 0 else 0.0
            score = compute_governing_score(shear_ratio=shear.ratio, n_ratio=n_ratio)
            warnings_local.extend(duct.warnings)

            key_metric = (
                f"N={N_N/1000:.0f}kN M={abs(mz):.0f}kNm "
                f"N/(fcuAg)={duct.n_ratio:.3f} v/vmax={shear.ratio:.2f}"
            )

            items_by_label[label].append(
                GoverningItem(
                    element_id=eid,
                    element_class=elem_class,
                    governing_score=score,
                    governing_combo=n_case or vy_case,
                    key_metric=key_metric,
                    warnings=warnings_local,
                )
            )

        elif elem_class == StructuralClass.COUPLING_BEAM:
            # --- Coupling beam: shear check + span/depth ---
            shear = shear_stress_check(V_N, b, d, fcu)
            span_depth = (span_m * 1000.0) / d if d > 0 else 0.0
            score = compute_governing_score(shear_ratio=shear.ratio)
            if span_depth < 2.0:
                warnings_local.append(
                    f"l/d={span_depth:.1f} < 2.0 — diagonal reinforcement may be required"
                )

            key_metric = f"V={V_N/1000:.0f}kN v/vmax={shear.ratio:.2f} l/d={span_depth:.1f}"

            items_by_label[label].append(
                GoverningItem(
                    element_id=eid,
                    element_class=elem_class,
                    governing_score=score,
                    governing_combo=vy_case,
                    key_metric=key_metric,
                    warnings=warnings_local,
                )
            )

    # --- Wall shells ---
    wall_items: List[GoverningItem] = []
    wall_thickness = float(getattr(getattr(project, "lateral", None), "wall_thickness", 500.0) or 500.0)
    for eid, element in model.elements.items():
        if len(element.node_tags) < 3:
            continue
        try:
            shell_class = classify_shell_orientation(model, eid)
        except Exception:
            continue
        if shell_class != StructuralClass.WALL_SHELL:
            continue

        node_tags = element.node_tags
        z_min = min(float(model.nodes[n].z) for n in node_tags)
        base_nodes = [n for n in node_tags if abs(float(model.nodes[n].z) - z_min) < 1e-6]
        if not base_nodes:
            continue

        coords = [(float(model.nodes[n].x), float(model.nodes[n].y)) for n in base_nodes]
        if len(coords) >= 2:
            span_m = max(hypot(x2 - x1, y2 - y1) for (x1, y1) in coords for (x2, y2) in coords)
        else:
            span_m = 1.0
        d_mm = max(span_m * 1000.0 * 0.8, 100.0)
        b_mm = max(wall_thickness, 100.0)
        ag = b_mm * max(span_m * 1000.0, 100.0)

        best_score = 0.0
        best_combo = ""
        best_metric = ""
        best_warns: List[str] = []
        for combo_name, res in combined_results.items():
            node_reactions = getattr(res, "node_reactions", {}) or {}
            n_axial = 0.0
            v_shear = 0.0
            for n in base_nodes:
                reaction = node_reactions.get(n)
                if reaction is None:
                    continue
                if len(reaction) >= 3:
                    n_axial += abs(float(reaction[2]))
                    v_shear += hypot(float(reaction[0]), float(reaction[1]))

            shear = shear_stress_check(v_shear, b_mm, d_mm, fcu)
            duct = ductility_check(n_axial, fcu, ag)
            n_ratio = (duct.n_ratio / duct.threshold) if duct.threshold > 0 else 0.0
            score = compute_governing_score(shear_ratio=shear.ratio, n_ratio=n_ratio)
            if score > best_score:
                best_score = score
                best_combo = combo_name
                best_metric = (
                    f"N={n_axial/1000:.0f}kN V={v_shear/1000:.0f}kN "
                    f"N/(fcuAg)={duct.n_ratio:.3f} v/vmax={shear.ratio:.2f}"
                )
                best_warns = list(duct.warnings)

        if best_combo:
            wall_items.append(
                GoverningItem(
                    element_id=eid,
                    element_class=StructuralClass.WALL_SHELL,
                    governing_score=best_score,
                    governing_combo=best_combo,
                    key_metric=best_metric,
                    warnings=best_warns,
                )
            )

    items_by_label["Wall"] = wall_items
    return DesignChecksSummary(
        top3_by_type=_build_type_dict(items_by_label, top_n=top_n),
        warnings=warnings,
    )
