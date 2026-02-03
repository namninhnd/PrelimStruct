
import sys
import os
sys.path.append(os.getcwd())
import pytest
import logging
from src.core.data_models import (
    ProjectData, GeometryInput, LateralInput, CoreWallConfig
)
from src.fem.model_builder import build_fem_model, ModelBuilderOptions
from src.fem.fem_engine import ElementType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SlabSubdivisionTest")

def test_slab_subdivision_y_direction():
    """Test slab subdivision when secondary beams run in Y-direction."""
    project = ProjectData()
    project.geometry = GeometryInput(
        bay_x=6.0, bay_y=6.0, floors=1, story_height=3.0,
        num_bays_x=1, num_bays_y=1
    )
    # No core wall for simplicity
    # No core wall for simplicity
    project.lateral = LateralInput(
        building_width=6.0, building_depth=6.0,
        core_wall_config=None
    )
    
    # 1 secondary beam in Y direction => 2 slab strips
    options = ModelBuilderOptions(
        include_slabs=True,
        num_secondary_beams=1,
        secondary_beam_direction="Y",
        slab_elements_per_bay=2,
        apply_gravity_loads=False
    )
    
    model = build_fem_model(project, options)
    
    slab_elements = [e for e in model.elements.values() 
                     if e.element_type == ElementType.SHELL_MITC4]
    
    # We expect 2 strips. 
    # Each strip width = 3.0m. Bay width = 6.0m.
    # Mesh density adjustment: elements_along_x = max(1, int(2 * (3.0/6.0))) = 1
    # elements_along_y = max(1, int(2 * (6.0/6.0))) = 2
    # Total elements per strip = 1 * 2 = 2.
    # Total elements = 2 strips * 2 = 4 elements.
    
    assert len(slab_elements) == 4, f"Expected 4 slab elements, got {len(slab_elements)}"
    
    # Check Y-coordinates of nodes to verify vertical orientation
    # Secondary beam at x=3.0.
    # Nodes should be at x=0, x=3, x=6.
    xs = set()
    for n in model.nodes.values():
        xs.add(round(n.x, 3))
    
    assert 3.0 in xs, "Missing nodes at mid-span (x=3.0) where secondary beam should be."
    logger.info("✅ Y-direction subdivision verified.")

def test_slab_subdivision_x_direction():
    """Test slab subdivision when secondary beams run in X-direction."""
    project = ProjectData()
    project.geometry = GeometryInput(
        bay_x=6.0, bay_y=6.0, floors=1, story_height=3.0,
        num_bays_x=1, num_bays_y=1
    )
    # No core wall for simplicity
    project.lateral = LateralInput(
        building_width=6.0, building_depth=6.0,
        core_wall_config=None
    )
    
    # 2 secondary beams in X direction => 3 slab strips
    options = ModelBuilderOptions(
        include_slabs=True,
        num_secondary_beams=2,
        secondary_beam_direction="X",
        slab_elements_per_bay=3,
        apply_gravity_loads=False
    )
    
    model = build_fem_model(project, options)
    
    slab_elements = [e for e in model.elements.values() 
                     if e.element_type == ElementType.SHELL_MITC4]
    
    # We expect 3 strips.
    # Strip height = 2.0m. Bay height = 6.0m.
    # elements_along_x = max(1, int(3 * (6.0/6.0))) = 3
    # elements_along_y = max(1, int(3 * (2.0/6.0))) = 1
    # Total per strip = 3 * 1 = 3.
    # Total = 3 strips * 3 = 9 elements.
    
    assert len(slab_elements) == 9, f"Expected 9 slab elements, got {len(slab_elements)}"
    
    # Check Y-coordinates: 0, 2, 4, 6
    ys = set()
    for n in model.nodes.values():
        ys.add(round(n.y, 3))
        
    assert 2.0 in ys and 4.0 in ys, "Missing nodes at y=2.0 and y=4.0."
    logger.info("✅ X-direction subdivision verified.")

if __name__ == "__main__":
    test_slab_subdivision_y_direction()
    test_slab_subdivision_x_direction()
