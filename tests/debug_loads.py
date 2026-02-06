import sys
sys.path.insert(0, ".")

from src.core.data_models import ProjectData, GeometryInput, MaterialInput, LoadInput, LateralInput, BeamResult, ColumnResult
from src.fem.model_builder import build_fem_model, ModelBuilderOptions

geo = GeometryInput(floors=3, story_height=3.0, num_bays_x=1, num_bays_y=1, bay_x=6.0, bay_y=6.0)
mat = MaterialInput(fcu_slab=35, fcu_beam=40, fcu_column=50)
loading = LoadInput(live_load_class="2", live_load_sub="2.5", dead_load=1.5)
lateral = LateralInput(building_width=6.0, building_depth=6.0)

project = ProjectData(geometry=geo, materials=mat, loads=loading, lateral=lateral)
project.primary_beam_result = BeamResult(element_type="Primary Beam", size="300x600", width=300, depth=600)
project.secondary_beam_result = BeamResult(element_type="Secondary Beam", size="250x500", width=250, depth=500)
project.column_result = ColumnResult(element_type="Column", size="400", dimension=400)

options = ModelBuilderOptions(
    include_core_wall=False,
    trim_beams_at_core=False,
    apply_gravity_loads=True,
    apply_wind_loads=False,
    apply_rigid_diaphragms=True,
    include_slabs=False
)

print("Building FEM model...")
model = build_fem_model(project, options)

print(f"\n=== MODEL STATISTICS ===")
print(f"Nodes: {len(model.nodes)}")
print(f"Elements: {len(model.elements)}")
print(f"Point loads (model.loads): {len(model.loads)}")
print(f"Uniform loads (model.uniform_loads): {len(model.uniform_loads)}")
print(f"Surface loads (model.surface_loads): {len(model.surface_loads)}")

if model.uniform_loads:
    print(f"\n=== SAMPLE UNIFORM LOADS ===")
    for i, ul in enumerate(model.uniform_loads[:5]):
        print(f"  [{i}] Element {ul.element_tag}: {ul.magnitude:.2f} N/m, pattern={ul.load_pattern}")
else:
    print("\n⚠️ NO UNIFORM LOADS FOUND!")
