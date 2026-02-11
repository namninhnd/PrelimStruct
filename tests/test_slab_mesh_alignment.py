"""
Test slab mesh alignment with beam subdivision nodes.

This module validates that slab mesh divisions are multiples of NUM_SUBDIVISIONS (4)
to ensure beam intermediate nodes are reused for proper load transfer.

TDD RED phase: Tests should fail until model_builder.py removes 0.1L sizing.
"""

import sys
import os
sys.path.append(os.getcwd())
import pytest
import logging
from src.core.data_models import (
    ProjectData, GeometryInput, LateralInput, CoreWallConfig
)
from src.fem.model_builder import build_fem_model, ModelBuilderOptions, NUM_SUBDIVISIONS
from src.fem.fem_engine import ElementType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SlabMeshAlignmentTest")


@pytest.fixture
def simple_1bay_project():
    """Create a simple 1-bay project for testing slab alignment."""
    project = ProjectData()
    project.geometry = GeometryInput(
        bay_x=8.0, bay_y=6.0, floors=1, story_height=4.0,
        num_bays_x=1, num_bays_y=1
    )
    project.lateral = LateralInput(
        building_width=8.0, building_depth=6.0,
        core_wall_config=None
    )
    return project


def _max_shell_aspect_ratio(model) -> float:
    """Return maximum edge-length aspect ratio over slab shell elements."""
    max_aspect_ratio = 0.0

    for elem in model.elements.values():
        if elem.element_type != ElementType.SHELL_MITC4:
            continue

        n1 = model.nodes[elem.node_tags[0]]
        n2 = model.nodes[elem.node_tags[1]]
        n3 = model.nodes[elem.node_tags[2]]
        n4 = model.nodes[elem.node_tags[3]]

        edge_lengths = [
            ((n2.x - n1.x) ** 2 + (n2.y - n1.y) ** 2 + (n2.z - n1.z) ** 2) ** 0.5,
            ((n3.x - n2.x) ** 2 + (n3.y - n2.y) ** 2 + (n3.z - n2.z) ** 2) ** 0.5,
            ((n4.x - n3.x) ** 2 + (n4.y - n3.y) ** 2 + (n4.z - n3.z) ** 2) ** 0.5,
            ((n1.x - n4.x) ** 2 + (n1.y - n4.y) ** 2 + (n1.z - n4.z) ** 2) ** 0.5,
        ]
        min_edge = min(edge_lengths)
        if min_edge <= 0.0:
            continue

        aspect_ratio = max(edge_lengths) / min_edge
        if aspect_ratio > max_aspect_ratio:
            max_aspect_ratio = aspect_ratio

    return max_aspect_ratio


class TestSlabMeshDivisionsMultipleOfBeamDiv:
    """Test that slab mesh divisions are multiples of NUM_SUBDIVISIONS."""

    def test_slab_mesh_divisions_are_multiple_of_beam_div_no_secondary(self, simple_1bay_project):
        """Slab mesh X/Y divisions should be multiples of NUM_SUBDIVISIONS (4)."""
        options = ModelBuilderOptions(
            include_slabs=True,
            num_secondary_beams=0,
            secondary_beam_direction="Y",
            slab_elements_per_bay=1,
            apply_gravity_loads=False
        )
        
        model = build_fem_model(simple_1bay_project, options)
        
        slab_elements = [e for e in model.elements.values() 
                         if e.element_type == ElementType.SHELL_MITC4]
        
        # With no secondary beams, slab should have beam_div * beam_div elements
        # beam_div = NUM_SUBDIVISIONS = 4
        # Expected: 4 * 4 = 16 elements
        expected_elem_count = NUM_SUBDIVISIONS * NUM_SUBDIVISIONS
        assert len(slab_elements) == expected_elem_count, \
            f"Expected {expected_elem_count} slab elements (4x4 grid), got {len(slab_elements)}"

    def test_slab_mesh_divisions_with_secondary_beams_y(self, simple_1bay_project):
        """With secondary beams in Y direction, X divisions use LCM(beam_div, sec_div)."""
        options = ModelBuilderOptions(
            include_slabs=True,
            num_secondary_beams=3,  # sec_div = 4
            secondary_beam_direction="Y",
            slab_elements_per_bay=1,
            apply_gravity_loads=False
        )
        
        model = build_fem_model(simple_1bay_project, options)
        
        slab_elements = [e for e in model.elements.values() 
                         if e.element_type == ElementType.SHELL_MITC4]
        
        # sec_div = 3+1 = 4, beam_div = 4
        # lcm(4, 4) = 4 for X, beam_div = 4 for Y
        # Total slab panels = sec_div = 4 (strips)
        # Each strip: elements_along_x = 4, elements_along_y = 4
        # But we have 4 slab sub-panels (due to secondary beams)
        # Expected: 4 strips * (4 * 4) = 64 elements? No, each strip gets 4*4 elements
        # Actually: 4 strips, each has 4*4 elements = 64 total
        # Wait, if num_secondary_beams=3, we have 4 slab strips along X
        # Each strip should have 4 elements along X (whole strip is 1/4 of bay width) * 4 along Y = 16 per strip
        # But the strip width is bay_x/sec_div = 8/4 = 2.0m
        # With beam_div=4 for X: elements_along_x for each strip should still be 4
        # Total = 4 strips * 4 * 4 = 64
        
        # The key assertion is that element count is a multiple of NUM_SUBDIVISIONS squared
        assert len(slab_elements) % (NUM_SUBDIVISIONS * NUM_SUBDIVISIONS) == 0, \
            f"Slab element count {len(slab_elements)} should be multiple of {NUM_SUBDIVISIONS**2}"

    def test_slab_mesh_divisions_with_refinement(self, simple_1bay_project):
        """With refinement multiplier, divisions remain aligned."""
        options = ModelBuilderOptions(
            include_slabs=True,
            num_secondary_beams=0,
            secondary_beam_direction="Y",
            slab_elements_per_bay=2,  # 2x refinement
            apply_gravity_loads=False
        )
        
        model = build_fem_model(simple_1bay_project, options)
        
        slab_elements = [e for e in model.elements.values() 
                         if e.element_type == ElementType.SHELL_MITC4]
        
        # With 2x refinement: 4*2 = 8 elements along each axis
        # Expected: 8 * 8 = 64 elements
        expected_elem_count = (NUM_SUBDIVISIONS * 2) * (NUM_SUBDIVISIONS * 2)
        assert len(slab_elements) == expected_elem_count, \
            f"Expected {expected_elem_count} slab elements (8x8 grid with 2x refinement), got {len(slab_elements)}"

    def test_secondary_y_direction_mesh_aspect_ratio_within_limit(self):
        """Y-direction secondary beams should keep slab shell AR within limit."""
        project = ProjectData()
        project.geometry = GeometryInput(
            bay_x=9.0,
            bay_y=6.0,
            floors=1,
            story_height=4.0,
            num_bays_x=1,
            num_bays_y=1,
        )
        project.lateral = LateralInput(
            building_width=9.0,
            building_depth=6.0,
            core_wall_config=None,
        )

        options = ModelBuilderOptions(
            include_slabs=True,
            num_secondary_beams=3,
            secondary_beam_direction="Y",
            slab_elements_per_bay=1,
            include_core_wall=False,
            trim_beams_at_core=False,
            apply_gravity_loads=False,
        )

        model = build_fem_model(project, options)
        assert _max_shell_aspect_ratio(model) <= 5.0

    def test_secondary_x_direction_mesh_aspect_ratio_within_limit(self):
        """X-direction secondary beams should keep slab shell AR within limit."""
        project = ProjectData()
        project.geometry = GeometryInput(
            bay_x=6.0,
            bay_y=18.0,
            floors=1,
            story_height=4.0,
            num_bays_x=1,
            num_bays_y=1,
        )
        project.lateral = LateralInput(
            building_width=6.0,
            building_depth=18.0,
            core_wall_config=None,
        )

        options = ModelBuilderOptions(
            include_slabs=True,
            num_secondary_beams=1,
            secondary_beam_direction="X",
            slab_elements_per_bay=1,
            include_core_wall=False,
            trim_beams_at_core=False,
            apply_gravity_loads=False,
        )

        model = build_fem_model(project, options)
        assert _max_shell_aspect_ratio(model) <= 5.0


class TestSlabMeshReusesBeamIntermediateNodes:
    """Test that slab mesh reuses beam intermediate node tags."""

    def test_beam_intermediate_nodes_shared_with_slab(self, simple_1bay_project):
        """Beam intermediate nodes (0.25L, 0.5L, 0.75L) should be shared with slab mesh."""
        options = ModelBuilderOptions(
            include_slabs=True,
            num_secondary_beams=0,
            secondary_beam_direction="Y",
            slab_elements_per_bay=1,
            apply_gravity_loads=False
        )
        
        model = build_fem_model(simple_1bay_project, options)
        z_slab = simple_1bay_project.geometry.story_height
        bay_x = simple_1bay_project.geometry.bay_x
        
        expected_beam_x_positions = [bay_x * i / NUM_SUBDIVISIONS 
                                     for i in range(1, NUM_SUBDIVISIONS)]
        
        slab_elements = [e for e in model.elements.values() 
                         if e.element_type == ElementType.SHELL_MITC4]
        slab_node_tags = set()
        for elem in slab_elements:
            slab_node_tags.update(elem.node_tags)
        
        intermediate_nodes_shared = []
        for node_tag, node in model.nodes.items():
            if abs(node.y) < 1e-6 and abs(node.z - z_slab) < 1e-6:
                for expected_x in expected_beam_x_positions:
                    if abs(node.x - expected_x) < 1e-6:
                        if node_tag in slab_node_tags:
                            intermediate_nodes_shared.append(node_tag)
                        break
        
        assert len(intermediate_nodes_shared) >= 3, \
            f"Expected at least 3 beam intermediate nodes shared with slab, found {len(intermediate_nodes_shared)}"
        
        logger.info(f"Beam intermediate nodes shared with slab on Y=0 edge: {intermediate_nodes_shared}")

    def test_beam_nodes_at_all_four_edges_shared(self, simple_1bay_project):
        """Beam intermediate nodes along all 4 bay edges should be shared with slab."""
        options = ModelBuilderOptions(
            include_slabs=True,
            num_secondary_beams=0,
            secondary_beam_direction="Y",
            slab_elements_per_bay=1,
            apply_gravity_loads=False
        )
        
        model = build_fem_model(simple_1bay_project, options)
        z_slab = simple_1bay_project.geometry.story_height
        bay_x = simple_1bay_project.geometry.bay_x
        bay_y = simple_1bay_project.geometry.bay_y
        
        # Collect slab node tags
        slab_elements = [e for e in model.elements.values() 
                         if e.element_type == ElementType.SHELL_MITC4]
        slab_node_tags = set()
        for elem in slab_elements:
            slab_node_tags.update(elem.node_tags)
        
        # Check expected intermediate node positions on all 4 edges
        tolerance = 1e-6
        edges_checked = 0
        shared_per_edge = []
        
        for edge_name, edge_check in [
            ("bottom (Y=0)", lambda n: abs(n.y) < tolerance),
            ("top (Y=bay_y)", lambda n: abs(n.y - bay_y) < tolerance),
            ("left (X=0)", lambda n: abs(n.x) < tolerance),
            ("right (X=bay_x)", lambda n: abs(n.x - bay_x) < tolerance),
        ]:
            edge_beam_nodes = []
            for node_tag, node in model.nodes.items():
                if abs(node.z - z_slab) < tolerance and edge_check(node):
                    edge_beam_nodes.append(node_tag)
            
            # Count how many are shared with slab
            shared = set(edge_beam_nodes) & slab_node_tags
            shared_per_edge.append((edge_name, len(shared), len(edge_beam_nodes)))
            edges_checked += 1
        
        # Log results
        for edge_name, shared_count, total_count in shared_per_edge:
            logger.info(f"Edge {edge_name}: {shared_count}/{total_count} nodes shared with slab")
        
        # All 4 edges should have at least NUM_SUBDIVISIONS+1 = 5 shared nodes
        for edge_name, shared_count, total_count in shared_per_edge:
            assert shared_count >= NUM_SUBDIVISIONS + 1, \
                f"Edge {edge_name}: expected at least {NUM_SUBDIVISIONS+1} shared nodes, got {shared_count}"


class TestNoZeroPointOneLSizing:
    """Test that 0.1L mesh sizing is removed."""

    def test_slab_mesh_deterministic_not_size_based(self, simple_1bay_project):
        """
        Slab mesh should use deterministic divisions based on beam subdivision count,
        not 0.1 * max(width) sizing.
        
        With bay_x=8.0m, old logic would give: target_size = 0.1 * 8.0 = 0.8m
        elements_along_x = int(8.0 / 0.8) = 10
        elements_along_y = int(6.0 / 0.8) = 7 or 8
        
        New logic: 4 x 4 = 16 elements (or multiple thereof)
        """
        options = ModelBuilderOptions(
            include_slabs=True,
            num_secondary_beams=0,
            secondary_beam_direction="Y",
            slab_elements_per_bay=1,
            apply_gravity_loads=False
        )
        
        model = build_fem_model(simple_1bay_project, options)
        
        slab_elements = [e for e in model.elements.values() 
                         if e.element_type == ElementType.SHELL_MITC4]
        
        # Old 0.1L sizing with 8m bay would give ~70-80 elements
        # New deterministic sizing gives exactly 16 elements (4x4)
        # Element count should NOT be near 70-80
        assert len(slab_elements) < 50, \
            f"Slab element count {len(slab_elements)} is too high, 0.1L sizing may still be in use"
        
        # Should be exactly 16 with no refinement
        assert len(slab_elements) == 16, \
            f"Expected exactly 16 slab elements (4x4), got {len(slab_elements)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
