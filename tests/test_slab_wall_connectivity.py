
import sys
import os
sys.path.append(os.getcwd())
import pytest
import logging
from src.core.data_models import (
    ProjectData, GeometryInput, LateralInput, CoreWallGeometry, CoreWallConfig, 
    MaterialInput, LoadInput
)
from src.fem.model_builder import build_fem_model, ModelBuilderOptions
from src.fem.fem_engine import ElementType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SlabWallConnectivityTest")

def test_slab_wall_connectivity():
    """Integration test: Verify slabs connect to core walls by sharing nodes."""
    
    # 1. Setup Project with Core Wall
    project = ProjectData()
    project.geometry = GeometryInput(
        bay_x=6.0, bay_y=6.0, floors=1, story_height=3.0,
        num_bays_x=3, num_bays_y=3
    )
    
    # Central 6x6m Core Wall
    core_config = CoreWallConfig.TUBE_CENTER_OPENING
    project.lateral = LateralInput(
        building_width=18.0,
        building_depth=18.0,
        core_wall_config=core_config,
        wall_thickness=500,
        core_geometry=CoreWallGeometry(
            config=core_config,
            wall_thickness=500,
            length_x=6000,
            length_y=6000,
            opening_width=2000,
            opening_height=2000
        )
    )
    
    options = ModelBuilderOptions(
        include_core_wall=True,
        include_slabs=True,
        slab_elements_per_bay=2, # Keep mesh coarse for easier debugging
        omit_columns_near_core=True # Standard behavior
    )
    
    logger.info("Building model with Core Wall + Slabs...")
    model = build_fem_model(project, options)
    
    # 2. Extract Wall Nodes & Slab Nodes
    wall_elements = [e for e in model.elements.values() 
                     if e.element_type == ElementType.SHELL_MITC4 and e.section_tag == 10]
    slab_elements = [e for e in model.elements.values() 
                     if e.element_type == ElementType.SHELL_MITC4 and e.section_tag == 5]
    
    assert len(wall_elements) > 0, "No wall elements generated"
    assert len(slab_elements) > 0, "No slab elements generated"
    
    wall_node_tags = set()
    for e in wall_elements:
        wall_node_tags.update(e.node_tags)
        
    slab_node_tags = set()
    for e in slab_elements:
        slab_node_tags.update(e.node_tags)
        
    # 3. Verify Node Sharing
    # There should be nodes that belong to BOTH sets (the interface)
    shared_nodes = wall_node_tags.intersection(slab_node_tags)
    
    logger.info(f"Wall Nodes: {len(wall_node_tags)}")
    logger.info(f"Slab Nodes: {len(slab_node_tags)}")
    logger.info(f"Shared Nodes: {len(shared_nodes)}")
    
    assert len(shared_nodes) > 0, "Slabs are NOT connected to walls (no shared nodes)"
    
    # Verify roughly expected connectivity
    # A 6x6m core perimeter is 24m. 
    # Mesh density is approx 3m (bay/2). 
    # Should be at least 8-12 shared nodes along the perimeter.
    assert len(shared_nodes) >= 4, f"Too few shared nodes ({len(shared_nodes)}). Connection might be partial."
    
    # 4. Verify No Overlap
    # No slab element center should be inside the core opening
    # Core opening is roughly [6,12] x [6,12]
    # Check center of all slab elements
    elements_inside_core = 0
    for e in slab_elements:
        nodes = [model.nodes[tag] for tag in e.node_tags]
        cx = sum(n.x for n in nodes) / 4.0
        cy = sum(n.y for n in nodes) / 4.0
        
        # Core bounds (approx 6.0 to 12.0)
        # Add slight tolerance for boundary elements
        if 6.1 < cx < 11.9 and 6.1 < cy < 11.9:
            elements_inside_core += 1
            
    assert elements_inside_core == 0, f"Found {elements_inside_core} slab elements generated INSIDE the core wall void!"
    
    logger.info("✅ Connectivity and geometry checks passed.")

if __name__ == "__main__":
    test_slab_wall_connectivity()
