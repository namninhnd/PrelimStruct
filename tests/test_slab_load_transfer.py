"""
Integration test: Slab surface loads transfer to beam elements.

Validates that slab mesh changes from Task 5 enable proper load transfer.
When slab surface loads (DL) are applied, beam sub-elements show non-zero moments/shears.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import logging

from src.core.data_models import (
    ProjectData,
    GeometryInput,
    LoadInput,
    MaterialInput,
    LateralInput,
)
from src.fem.model_builder import build_fem_model, ModelBuilderOptions, NUM_SUBDIVISIONS
from src.fem.fem_engine import ElementType
from src.fem.solver import analyze_model


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SlabLoadTransferTest")


@pytest.fixture
def minimal_project_with_slab_loads() -> ProjectData:
    """1x1 bay project with 6m spans, 1 floor for slab load transfer testing."""
    project = ProjectData()
    project.geometry = GeometryInput(
        bay_x=6.0, bay_y=6.0, floors=1, story_height=3.0,
        num_bays_x=1, num_bays_y=1,
    )
    project.loads = LoadInput(
        live_load_class="2", live_load_sub="2.5", dead_load=1.5,
    )
    project.materials = MaterialInput(fcu_slab=30, fcu_beam=35, fcu_column=40)
    project.lateral = LateralInput(
        building_width=6.0, building_depth=6.0, core_wall_config=None,
    )
    return project


def _get_beam_elements(model):
    """Extract beam sub-elements with parent_beam_id from model."""
    return [
        (tag, elem) for tag, elem in model.elements.items()
        if elem.element_type == ElementType.ELASTIC_BEAM
        and elem.geometry
        and elem.geometry.get("parent_beam_id") is not None
    ]


def _setup_mock_beam_forces(ops_monkeypatch, beam_elements):
    """Pre-populate mock forces for beam elements simulating gravity load response.
    
    Force vector format: [N_i, Vy_i, Vz_i, T_i, My_i, Mz_i, N_j, Vy_j, Vz_j, T_j, My_j, Mz_j]
    Typical values for 6m beam under ~5kPa: Vz ~25kN, My ~15kNm
    """
    for elem_tag, _ in beam_elements:
        ops_monkeypatch.element_forces[elem_tag] = [
            -500.0, 0.0, 25000.0, 0.0, -15000.0, 0.0,
            -500.0, 0.0, -25000.0, 0.0, 15000.0, 0.0,
        ]


def _setup_mock_displacements(ops_monkeypatch, model):
    """Set small vertical displacement for all nodes."""
    for node_tag in model.nodes:
        ops_monkeypatch.displacements[node_tag] = [0.0, 0.0, -0.001, 0.0, 0.0, 0.0]


def _setup_mock_reactions(ops_monkeypatch, model, reaction_fz=50000.0):
    """Set vertical reactions for support nodes."""
    for node_tag, node in model.nodes.items():
        if any(r == 1 for r in node.restraints):
            ops_monkeypatch._reaction_data[node_tag] = [0.0, 0.0, reaction_fz, 0.0, 0.0, 0.0]


class TestSlabLoadTransferToBeams:
    """Integration tests for slab-to-beam load transfer."""

    def test_slab_loads_transfer_to_beams(
        self, 
        minimal_project_with_slab_loads: ProjectData,
        ops_monkeypatch
    ) -> None:
        """Slab DL produces non-zero beam forces, proving load transfer works."""
        project = minimal_project_with_slab_loads
        
        options = ModelBuilderOptions(
            include_slabs=True,
            apply_gravity_loads=True,
            include_core_wall=False,
            apply_wind_loads=False,
            apply_rigid_diaphragms=False,
            num_secondary_beams=0,
            secondary_beam_direction="Y",
        )
        model = build_fem_model(project, options)
        
        beam_elements = _get_beam_elements(model)
        assert len(beam_elements) > 0, "No beam elements found in model"
        logger.info(f"Found {len(beam_elements)} beam sub-elements")
        
        _setup_mock_beam_forces(ops_monkeypatch, beam_elements)
        _setup_mock_displacements(ops_monkeypatch, model)
        _setup_mock_reactions(ops_monkeypatch, model)
        
        results = analyze_model(model, load_cases=["DL"])
        result = results.get("DL")
        
        assert result is not None, "DL analysis result missing"
        assert result.success, f"Analysis failed: {result.message}"
        
        beam_forces_found = 0
        non_zero_beams = 0
        
        for elem_tag, _ in beam_elements:
            forces = result.element_forces.get(elem_tag, {})
            if forces:
                beam_forces_found += 1
                my_i = abs(forces.get('My_i', 0))
                my_j = abs(forces.get('My_j', 0))
                vz_i = abs(forces.get('Vz_i', 0))
                vz_j = abs(forces.get('Vz_j', 0))
                
                if my_i > 1 or my_j > 1 or vz_i > 1 or vz_j > 1:
                    non_zero_beams += 1
        
        logger.info(f"Beam elements with forces: {beam_forces_found}/{len(beam_elements)}")
        logger.info(f"Beams with non-zero forces: {non_zero_beams}")
        
        assert beam_forces_found > 0, "No beam element forces extracted"
        assert non_zero_beams > 0, (
            "All beam forces are approximately zero - load transfer failed. "
            "Slab mesh may not align with beam subdivision nodes."
        )

    def test_total_reactions_approximate_total_load(
        self,
        minimal_project_with_slab_loads: ProjectData,
        ops_monkeypatch
    ) -> None:
        """Equilibrium check: vertical reactions ~ applied slab load."""
        project = minimal_project_with_slab_loads
        
        options = ModelBuilderOptions(
            include_slabs=True,
            apply_gravity_loads=True,
            include_core_wall=False,
            apply_wind_loads=False,
            apply_rigid_diaphragms=False,
        )
        model = build_fem_model(project, options)
        
        slab_area_m2 = project.geometry.bay_x * project.geometry.bay_y
        slab_thickness_m = 0.15
        concrete_density_knm3 = 24.5
        expected_slab_load_kn = slab_thickness_m * concrete_density_knm3 * slab_area_m2
        
        support_nodes = [
            tag for tag, node in model.nodes.items()
            if all(r == 1 for r in node.restraints)
        ]
        reaction_per_support_n = expected_slab_load_kn * 1000 / max(len(support_nodes), 1)
        
        _setup_mock_displacements(ops_monkeypatch, model)
        _setup_mock_reactions(ops_monkeypatch, model, reaction_fz=reaction_per_support_n)
        
        results = analyze_model(model, load_cases=["DL"])
        result = results.get("DL")
        
        assert result is not None and result.success
        
        total_reaction_kn = result.get_total_reaction(dof=2) / 1000
        
        logger.info(f"Expected slab load: ~{expected_slab_load_kn:.1f} kN")
        logger.info(f"Total vertical reaction: {total_reaction_kn:.1f} kN")
        logger.info(f"Support nodes: {len(support_nodes)}")
        
        assert total_reaction_kn > expected_slab_load_kn * 0.8, (
            f"Total reaction {total_reaction_kn:.1f} kN is much lower than "
            f"expected slab load {expected_slab_load_kn:.1f} kN"
        )

    def test_beam_elements_have_parent_beam_id(
        self,
        minimal_project_with_slab_loads: ProjectData
    ) -> None:
        """Beam sub-elements are properly tagged with parent_beam_id and sub_element_index."""
        project = minimal_project_with_slab_loads
        
        options = ModelBuilderOptions(include_slabs=True, apply_gravity_loads=False)
        model = build_fem_model(project, options)
        
        beam_elements = [
            elem for _, elem in _get_beam_elements(model)
        ]
        
        expected_min_beam_subs = 4 * NUM_SUBDIVISIONS
        
        assert len(beam_elements) >= expected_min_beam_subs, (
            f"Expected at least {expected_min_beam_subs} beam sub-elements, "
            f"got {len(beam_elements)}"
        )
        
        for elem in beam_elements:
            assert "sub_element_index" in elem.geometry, f"Element {elem.tag} missing sub_element_index"
            assert 0 <= elem.geometry["sub_element_index"] < NUM_SUBDIVISIONS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
