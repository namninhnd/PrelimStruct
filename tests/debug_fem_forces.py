"""Quick diagnostic script to test FEM analysis and force extraction."""
import sys
sys.path.insert(0, '.')

from src.core.data_models import (
    ProjectData, GeometryInput, LoadInput, MaterialInput, 
    LateralInput, BeamResult, ColumnResult
)
from src.fem.model_builder import build_fem_model, ModelBuilderOptions
from src.fem.solver import analyze_model, print_analysis_summary
from src.fem.results_processor import ResultsProcessor

def create_simple_model():
    geometry = GeometryInput(
        num_bays_x=2,
        num_bays_y=2,
        bay_x=6.0,
        bay_y=6.0,
        floors=2,
        story_height=3.0,
    )
    
    loads = LoadInput(
        live_load_class="2",
        live_load_sub="2.5",
        dead_load=2.0,
    )
    
    materials = MaterialInput(
        fcu_slab=30,
        fcu_beam=40,
        fcu_column=45,
    )
    
    lateral = LateralInput(
        building_width=12.0,
        building_depth=12.0,
    )
    
    project = ProjectData(
        geometry=geometry,
        loads=loads,
        materials=materials,
        lateral=lateral,
    )
    
    project.primary_beam_result = BeamResult(
        element_type="Primary Beam",
        size="300x600",
        width=300,
        depth=600,
    )
    project.secondary_beam_result = BeamResult(
        element_type="Secondary Beam",
        size="250x500",
        width=250,
        depth=500,
    )
    project.column_result = ColumnResult(
        element_type="Column",
        size="400",
        dimension=400,
    )
    
    return project

def main():
    print("=" * 60)
    print("FEM DIAGNOSTIC TEST")
    print("=" * 60)
    
    project = create_simple_model()
    print(f"Geometry: {project.geometry.num_bays_x}x{project.geometry.num_bays_y} bays, {project.geometry.floors} floors")
    
    # Build model
    options = ModelBuilderOptions(
        include_core_wall=False,
        apply_gravity_loads=True,
        apply_wind_loads=False,
        include_slabs=True,
    )
    
    print("\nBuilding FEM model...")
    model = build_fem_model(project, options)
    
    summary = model.get_summary()
    print(f"Nodes: {summary['n_nodes']}")
    print(f"Elements: {summary['n_elements']}")
    print(f"Uniform loads: {summary['n_uniform_loads']}")
    print(f"Surface loads: {summary['n_surface_loads']}")
    
    # Sample uniform loads
    print(f"\nFirst 3 uniform loads:")
    for i, uload in enumerate(model.uniform_loads[:3]):
        print(f"  Element {uload.element_tag}: {uload.load_type} = {uload.magnitude:.2f} N/m, pattern {uload.load_pattern}")
    
    # Run analysis
    print("\nRunning analysis...")
    results_dict = analyze_model(model, load_pattern=1)
    result = results_dict.get("combined") or next(iter(results_dict.values()))
    
    print(f"\nAnalysis success: {result.success}")
    print(f"Message: {result.message}")
    print(f"Nodes with displacements: {len(result.node_displacements)}")
    print(f"Nodes with reactions: {len(result.node_reactions)}")
    print(f"Elements with forces: {len(result.element_forces)}")
    
    # Sample element forces
    if result.element_forces:
        print(f"\nFirst 3 element forces:")
        for elem_tag in list(result.element_forces.keys())[:3]:
            forces = result.element_forces[elem_tag]
            print(f"  Element {elem_tag}:")
            for key, val in forces.items():
                print(f"    {key}: {val:.2f}")
    else:
        print("\n*** NO ELEMENT FORCES EXTRACTED! ***")
        
    # Check reaction totals
    if result.node_reactions:
        total_fz = sum(r[2] for r in result.node_reactions.values())
        print(f"\nTotal vertical reaction (Fz): {total_fz/1000:.2f} kN")
    
    # Extract section forces for Mz
    print("\n--- Extracting section forces (Mz) ---")
    try:
        forces = ResultsProcessor.extract_section_forces(
            result=result,
            model=model,
            force_type="Mz"
        )
        print(f"Elements with Mz: {len(forces.elements)}")
        print(f"Min Mz: {forces.min_value:.2f} kNm")
        print(f"Max Mz: {forces.max_value:.2f} kNm")
        
        if forces.elements:
            # Sample
            elem_id = list(forces.elements.keys())[0]
            ef = forces.elements[elem_id]
            print(f"\nElement {elem_id}: Mz_i={ef.force_i:.2f} kNm, Mz_j={ef.force_j:.2f} kNm")
        else:
            print("\n*** NO Mz FORCES FOUND! ***")
    except Exception as e:
        print(f"Error extracting forces: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
