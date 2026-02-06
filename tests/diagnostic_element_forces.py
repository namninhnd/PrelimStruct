"""
Diagnostic script to check if FEM element_forces are populated after analysis.
"""
import sys
sys.path.insert(0, '.')

from src.core.data_models import (
    ProjectData, GeometryInputs, LoadingInputs, MaterialInputs, LateralInputs,
    CoreGeometry, CoreConfiguration
)
from src.fem.model_builder import build_fem_model, ModelBuilderOptions
from src.fem.solver import analyze_model

def run_diagnostic():
    print("="*60)
    print("FEM ELEMENT FORCES DIAGNOSTIC")
    print("="*60)
    
    # Create minimal project data
    geo = GeometryInputs(
        floors=3,
        story_height=3.5,
        num_bays_x=2,
        num_bays_y=2,
        bay_x=6.0,
        bay_y=6.0,
        perimeter_cladding=True,
        core_x_offset=0.0,
        core_y_offset=0.0
    )
    
    loading = LoadingInputs(
        sdl_floor=1.5,
        ll_floor=3.0,
        ll_roof=1.5,
        cladding=1.2,
        live_load_reduction_enabled=False
    )
    
    materials = MaterialInputs(fcu_slab=35, fcu_beam=40, fcu_column=50)
    
    core_geo = CoreGeometry(
        config=CoreConfiguration.I_SECTION,
        length_x=4.0,
        length_y=6.0,
        wall_thickness=0.3
    )
    
    lateral = LateralInputs(
        terrain_category=2,
        core_x_position=0.5,
        core_y_position=0.5,
        custom_center_x=6.0,
        custom_center_y=6.0,
        core_geometry=core_geo
    )
    
    project = ProjectData(
        geometry=geo,
        loading=loading,
        materials=materials,
        lateral=lateral
    )
    
    # Build FEM model
    print("\n[1] Building FEM model...")
    options = ModelBuilderOptions(
        apply_gravity_loads=True,
        apply_wind_loads=False
    )
    model = build_fem_model(project, options)
    
    print(f"    Nodes: {len(model.nodes)}")
    print(f"    Elements: {len(model.elements)}")
    print(f"    Loads: {len(model.loads)}")
    
    # Run analysis
    print("\n[2] Running analysis...")
    results_dict = analyze_model(model, load_pattern=1)
    result = results_dict.get("combined") or next(iter(results_dict.values()))
    
    print(f"    Success: {result.success}")
    print(f"    Converged: {result.converged}")
    print(f"    Message: {result.message}")
    
    # Check element_forces
    print("\n[3] Checking element_forces...")
    print(f"    element_forces count: {len(result.element_forces)}")
    
    if result.element_forces:
        print("\n    Sample element forces:")
        for i, (elem_tag, forces) in enumerate(result.element_forces.items()):
            if i >= 3:
                print(f"    ... and {len(result.element_forces) - 3} more elements")
                break
            print(f"    Element {elem_tag}:")
            for key, value in forces.items():
                print(f"      {key}: {value:.2f}")
    else:
        print("    WARNING: element_forces is EMPTY!")
    
    # Check node_displacements
    print("\n[4] Checking node_displacements...")
    print(f"    node_displacements count: {len(result.node_displacements)}")
    
    # Check node_reactions
    print("\n[5] Checking node_reactions...")
    print(f"    node_reactions count: {len(result.node_reactions)}")
    
    print("\n" + "="*60)
    print("DIAGNOSTIC COMPLETE")
    print("="*60)

if __name__ == "__main__":
    run_diagnostic()
