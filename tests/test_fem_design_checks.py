"""Tests for src/fem/design_checks.py — Gates B, C, D + Flexural/Shear."""

import math
import pytest

from src.fem.fem_engine import Element, ElementType, FEMModel, Node
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
    rho_check,
    select_top_n,
    shear_stress_check,
    suggest_links,
    suggest_rebar,
)


# ── Helpers ──────────────────────────────────────────────

def _make_model_with_element(elem_type, geometry=None, node_coords=None):
    """Build a minimal FEMModel with a single element."""
    model = FEMModel()
    if node_coords is None:
        node_coords = {1: (0, 0, 0), 2: (1, 0, 0)}
    for tag, (x, y, z) in node_coords.items():
        model.add_node(Node(tag=tag, x=x, y=y, z=z))

    elem = Element(
        tag=100,
        element_type=elem_type,
        node_tags=list(node_coords.keys()),
        material_tag=1,
        geometry=geometry or {},
    )
    model.add_element(elem)
    return model


# ── Gate B: classify_element ─────────────────────────────

class TestClassifyElement:
    def test_secondary_beam(self):
        model = _make_model_with_element(ElementType.SECONDARY_BEAM)
        assert classify_element(model, 100) == StructuralClass.SECONDARY_BEAM

    def test_coupling_beam(self):
        model = _make_model_with_element(ElementType.COUPLING_BEAM)
        assert classify_element(model, 100) == StructuralClass.COUPLING_BEAM

    def test_elastic_beam_with_parent_column_id(self):
        model = _make_model_with_element(
            ElementType.ELASTIC_BEAM,
            geometry={"parent_column_id": "C1"},
        )
        assert classify_element(model, 100) == StructuralClass.COLUMN

    def test_elastic_beam_without_parent_column_id(self):
        model = _make_model_with_element(ElementType.ELASTIC_BEAM)
        assert classify_element(model, 100) == StructuralClass.PRIMARY_BEAM

    def test_shell_element_raises(self):
        model = _make_model_with_element(
            ElementType.SHELL_MITC4,
            node_coords={1: (0, 0, 0), 2: (1, 0, 0), 3: (1, 1, 0), 4: (0, 1, 0)},
        )
        with pytest.raises(ValueError, match="not a frame element"):
            classify_element(model, 100)


# ── Gate B: classify_shell_orientation ────────────────────

class TestClassifyShellOrientation:
    def test_horizontal_slab(self):
        """Nodes in XY plane → slab_shell."""
        model = _make_model_with_element(
            ElementType.SHELL_MITC4,
            node_coords={1: (0, 0, 5), 2: (1, 0, 5), 3: (1, 1, 5), 4: (0, 1, 5)},
        )
        assert classify_shell_orientation(model, 100) == StructuralClass.SLAB_SHELL

    def test_vertical_wall_xz(self):
        """Nodes in XZ plane → wall_shell."""
        model = _make_model_with_element(
            ElementType.SHELL_MITC4,
            node_coords={1: (0, 0, 0), 2: (1, 0, 0), 3: (1, 0, 3), 4: (0, 0, 3)},
        )
        assert classify_shell_orientation(model, 100) == StructuralClass.WALL_SHELL

    def test_vertical_wall_yz(self):
        """Nodes in YZ plane → wall_shell."""
        model = _make_model_with_element(
            ElementType.SHELL_MITC4,
            node_coords={1: (0, 0, 0), 2: (0, 1, 0), 3: (0, 1, 3), 4: (0, 0, 3)},
        )
        assert classify_shell_orientation(model, 100) == StructuralClass.WALL_SHELL

    def test_slightly_tilted_slab(self):
        """5-degree tilt should still be slab (|nz| ≈ cos5° ≈ 0.996)."""
        tilt = math.radians(5)
        z_offset = math.sin(tilt)
        model = _make_model_with_element(
            ElementType.SHELL_MITC4,
            node_coords={
                1: (0, 0, 0),
                2: (1, 0, z_offset),
                3: (1, 1, z_offset),
                4: (0, 1, 0),
            },
        )
        assert classify_shell_orientation(model, 100) == StructuralClass.SLAB_SHELL


# ── Gate C: shear_stress_check ────────────────────────────

class TestShearStressCheck:
    def test_basic_pass(self):
        result = shear_stress_check(V=100_000, b=300, d=500, fcu=40)
        assert result.passed
        assert result.v == pytest.approx(100_000 / (300 * 500))
        assert result.v_max == pytest.approx(min(0.8 * math.sqrt(40), 7.0))

    def test_fcu_limit_caps_at_7(self):
        # For fcu=100, 0.8*sqrt(100) = 8.0, should cap at 7.0
        result = shear_stress_check(V=0, b=300, d=500, fcu=100)
        assert result.v_max == pytest.approx(7.0)

    def test_fail_high_shear(self):
        # v = 1e6 / (300*500) = 6.67 MPa; v_max for fcu=30 ≈ 4.38
        result = shear_stress_check(V=1_000_000, b=300, d=500, fcu=30)
        assert not result.passed
        assert result.ratio > 1.0

    def test_slab_strip_b_1000(self):
        result = shear_stress_check(V=200_000, b=1000, d=150, fcu=35)
        assert result.v == pytest.approx(200_000 / (1000 * 150))

    def test_invalid_dimensions(self):
        result = shear_stress_check(V=100_000, b=0, d=500, fcu=40)
        assert not result.passed


# ── Gate C: rho_check ─────────────────────────────────────

class TestRhoCheck:
    def test_beam_within_limits(self):
        result = rho_check(1.0, StructuralClass.PRIMARY_BEAM)
        assert result.passed
        assert len(result.warnings) == 0

    def test_beam_below_min(self):
        result = rho_check(0.1, StructuralClass.PRIMARY_BEAM)
        assert not result.passed
        assert any("ρ_min" in w for w in result.warnings)

    def test_beam_above_max(self):
        result = rho_check(3.0, StructuralClass.PRIMARY_BEAM)
        assert not result.passed
        assert any("ρ_max" in w for w in result.warnings)

    def test_column_limits(self):
        result = rho_check(0.5, StructuralClass.COLUMN)
        assert not result.passed  # below 0.8%
        result2 = rho_check(3.0, StructuralClass.COLUMN)
        assert result2.passed

    def test_wall_min_025(self):
        result = rho_check(0.2, StructuralClass.WALL_SHELL)
        assert not result.passed
        assert any("ρ_min" in w for w in result.warnings)
        result2 = rho_check(0.3, StructuralClass.WALL_SHELL)
        assert result2.passed


# ── Gate C: ductility_check ───────────────────────────────

class TestDuctilityCheck:
    def test_below_threshold(self):
        # N/(fcu*Ag) = 1e6 / (40 * 500*500) = 0.1
        result = ductility_check(N=1_000_000, fcu=40, Ag=250_000)
        assert result.passed
        assert result.n_ratio == pytest.approx(0.1)

    def test_above_threshold(self):
        # N/(fcu*Ag) = 8e6 / (40 * 250_000) = 0.8
        result = ductility_check(N=8_000_000, fcu=40, Ag=250_000)
        assert not result.passed
        assert any("ductility" in w for w in result.warnings)

    def test_invalid_inputs(self):
        result = ductility_check(N=1e6, fcu=0, Ag=250_000)
        assert not result.passed


# ── Gate D: governing selection ───────────────────────────

class TestGoverningSelection:
    def test_compute_governing_score(self):
        score = compute_governing_score(
            shear_ratio=0.6, rho_ratio=0.8, deflection_ratio=0.3
        )
        assert score == pytest.approx(0.8)

    def test_select_top_3(self):
        items = [
            GoverningItem(1, StructuralClass.PRIMARY_BEAM, 0.3),
            GoverningItem(2, StructuralClass.PRIMARY_BEAM, 0.9),
            GoverningItem(3, StructuralClass.PRIMARY_BEAM, 0.5),
            GoverningItem(4, StructuralClass.PRIMARY_BEAM, 0.7),
            GoverningItem(5, StructuralClass.PRIMARY_BEAM, 0.1),
        ]
        top3 = select_top_n(items, n=3)
        assert len(top3) == 3
        assert [it.element_id for it in top3] == [2, 4, 3]

    def test_select_top_n_fewer_items(self):
        items = [GoverningItem(1, StructuralClass.COLUMN, 0.5)]
        top3 = select_top_n(items, n=3)
        assert len(top3) == 1


# ── Beam Flexural Design ────────────────────────────────

class TestBeamFlexuralCheck:
    def test_hand_calc_200kNm(self):
        """Hand-calc: M=200kNm, b=300mm, d=500mm, fcu=40, fy=500.

        K = 200e6 / (40 * 300 * 500^2) = 200e6 / 3e9 = 0.0667
        K < K'=0.156 → singly reinforced
        z = d*(0.5 + sqrt(0.25 - K/0.9)) = 500*(0.5 + sqrt(0.25 - 0.0741))
          = 500*(0.5 + sqrt(0.1759)) = 500*(0.5 + 0.4194) = 459.7mm
        z capped at 0.95*500 = 475mm → z = 459.7mm
        As_req = 200e6 / (0.87 * 500 * 459.7) = 200e6 / 199970 = 1000.2 mm2
        """
        result = beam_flexural_check(M=200e6, b=300, d=500, fcu=40, fy=500)
        assert not result.is_doubly
        assert result.K == pytest.approx(0.0667, abs=0.001)
        assert result.z == pytest.approx(459.7, abs=2.0)
        assert result.As_req == pytest.approx(1000, rel=0.02)
        assert result.passed

    def test_zero_moment(self):
        result = beam_flexural_check(M=0, b=300, d=500, fcu=40)
        assert result.As_req == 0.0
        assert result.passed

    def test_doubly_reinforced(self):
        """Very large moment should trigger K > K'."""
        # K = 800e6 / (40 * 300 * 500^2) = 0.267 > 0.156
        result = beam_flexural_check(M=800e6, b=300, d=500, fcu=40, fy=500)
        assert result.is_doubly
        assert result.K == pytest.approx(0.267, abs=0.001)
        assert result.As_req > 0

    def test_rebar_suggestion_nonempty(self):
        result = beam_flexural_check(M=200e6, b=300, d=500, fcu=40)
        assert result.rebar_suggestion != "N/A"
        assert "T" in result.rebar_suggestion


# ── Concrete Shear Capacity ─────────────────────────────

class TestConcreteShearCapacity:
    def test_vc_formula_spot_check(self):
        """Verify vc for typical beam: b=300, d=500, fcu=40, As=1000mm2.

        100*As/(b*d) = 100*1000/150000 = 0.667
        (400/d)^0.25 = (400/500)^0.25 = 0.8^0.25 = 0.9457
        (fcu/25)^(1/3) = (40/25)^(1/3) = 1.6^0.333 = 1.170
        vc = 0.79 * 0.667^(1/3) * 0.9457 * 1.170 / 1.25
           = 0.79 * 0.8736 * 0.9457 * 1.170 / 1.25
           = 0.79 * 0.967 / 1.25 = 0.611 MPa
        """
        result = concrete_shear_capacity(V=100_000, b=300, d=500, fcu=40, As_prov=1000)
        assert result.vc == pytest.approx(0.61, abs=0.05)
        assert result.Vc == pytest.approx(result.vc * 300 * 500, rel=0.01)
        assert result.passed  # v = 100000/(300*500) = 0.667 < v_max

    def test_links_required_when_V_exceeds_Vc(self):
        """Large shear should require links."""
        result = concrete_shear_capacity(V=500_000, b=300, d=500, fcu=40, As_prov=1000)
        assert result.Asv_sv_req > 0
        assert result.link_suggestion != "N/A"

    def test_invalid_dims(self):
        result = concrete_shear_capacity(V=100_000, b=0, d=500, fcu=40, As_prov=1000)
        assert not result.passed


# ── Rebar Suggestion ────────────────────────────────────

class TestSuggestRebar:
    def test_typical_beam(self):
        # ~1000 mm2 in 300mm wide beam
        suggestion = suggest_rebar(1000, 300)
        assert "T" in suggestion
        assert "mm2" in suggestion

    def test_zero_area(self):
        assert suggest_rebar(0, 300) == "N/A"

    def test_narrow_beam(self):
        # Very narrow beam, bars may not fit
        suggestion = suggest_rebar(5000, 150)
        # Should still try to suggest something or return N/A
        assert isinstance(suggestion, str)


class TestSuggestLinks:
    def test_typical_links(self):
        # Asv/sv = 0.5 mm2/mm → ~T10@200 (2*78.5/0.5=314 → 300mm)
        suggestion = suggest_links(0.5, 300)
        assert "T" in suggestion
        assert "@" in suggestion

    def test_zero_req(self):
        assert suggest_links(0, 300) == "N/A"
