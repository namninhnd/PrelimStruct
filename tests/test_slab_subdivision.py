
import sys
import os
sys.path.append(os.getcwd())
import pytest
import logging
import math
from src.core.data_models import (
    ProjectData, GeometryInput, LateralInput, CoreWallConfig
)
from src.fem.model_builder import build_fem_model, ModelBuilderOptions, NUM_SUBDIVISIONS
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
    project.lateral = LateralInput(
        building_width=6.0, building_depth=6.0,
        core_wall_config=None
    )
    
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
    
    beam_div = NUM_SUBDIVISIONS
    sec_div = 1 + 1
    refinement = 2
    split_axis_global_div = math.lcm(beam_div, sec_div)
    elements_along_x = (split_axis_global_div // sec_div) * refinement
    elements_along_y = beam_div * refinement
    num_strips = sec_div
    expected_elements = num_strips * elements_along_x * elements_along_y
    
    assert len(slab_elements) == expected_elements, \
        f"Expected {expected_elements} slab elements, got {len(slab_elements)}"
    
    xs = set()
    for n in model.nodes.values():
        xs.add(round(n.x, 3))
    
    assert 3.0 in xs, "Missing nodes at mid-span (x=3.0) where secondary beam should be."
    logger.info("Y-direction subdivision verified.")

def test_slab_subdivision_x_direction():
    """Test slab subdivision when secondary beams run in X-direction."""
    project = ProjectData()
    project.geometry = GeometryInput(
        bay_x=6.0, bay_y=6.0, floors=1, story_height=3.0,
        num_bays_x=1, num_bays_y=1
    )
    project.lateral = LateralInput(
        building_width=6.0, building_depth=6.0,
        core_wall_config=None
    )
    
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
    
    beam_div = NUM_SUBDIVISIONS
    sec_div = 2 + 1
    refinement = 3
    split_axis_global_div = math.lcm(beam_div, sec_div)
    elements_along_x = beam_div * refinement
    elements_along_y = (split_axis_global_div // sec_div) * refinement
    num_strips = sec_div
    expected_elements = num_strips * elements_along_x * elements_along_y
    
    assert len(slab_elements) == expected_elements, \
        f"Expected {expected_elements} slab elements, got {len(slab_elements)}"
    
    ys = set()
    for n in model.nodes.values():
        ys.add(round(n.y, 3))
        
    assert 2.0 in ys and 4.0 in ys, "Missing nodes at y=2.0 and y=4.0."
    logger.info("X-direction subdivision verified.")

if __name__ == "__main__":
    test_slab_subdivision_y_direction()
    test_slab_subdivision_x_direction()
