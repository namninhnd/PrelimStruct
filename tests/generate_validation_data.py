
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.data_models import (
    ProjectData, GeometryInput, LoadInput, 
    MaterialInput, CoreWallConfig, CoreWallGeometry,
    TerrainCategory, ExposureClass, LateralInput
)
from src.fem.model_builder import build_fem_model
from src.fem.solver import analyze_model, AnalysisResult
from src.fem.analysis_summary import get_base_shear_from_reactions, get_top_drift

TERRAIN_MAP = {
    "A": TerrainCategory.OPEN_SEA,
    "B": TerrainCategory.OPEN_COUNTRY,
    "C": TerrainCategory.URBAN,
    "D": TerrainCategory.CITY_CENTRE,
}

def run_analysis(building_id):
    json_path = Path(".sisyphus/validation") / f"{building_id}.json"
    if not json_path.exists():
        return
    
    with open(json_path, "r") as f:
        data = json.load(f)
    
    geom = data["geometry"]
    loads = data["loads"]
    mats = data["materials"]
    lat = data["lateral"]
    cw = data["core_wall_geometry"]
    
    project = ProjectData(
        project_name=data["name"],
        project_number=data["project_metadata"]["project_number"],
        engineer=data["project_metadata"]["engineer"],
        geometry=GeometryInput(
            bay_x=geom["bay_x"],
            bay_y=geom["bay_y"],
            floors=geom["floors"],
            story_height=geom["story_height"],
            num_bays_x=geom["num_bays_x"],
            num_bays_y=geom["num_bays_y"],
        ),
        loads=LoadInput(
            live_load_class=loads["live_load_class"],
            live_load_sub=loads["live_load_sub"],
            dead_load=loads["dead_load"],
        ),
        materials=MaterialInput(
            fcu_slab=mats["fcu_slab"],
            fcu_beam=mats["fcu_beam"],
            fcu_column=mats["fcu_column"],
        ),
        lateral=LateralInput(
            core_wall_config=CoreWallConfig[lat["core_wall_config"].upper()],
            wall_thickness=lat["wall_thickness_mm"],
            terrain=TERRAIN_MAP.get(lat["terrain"].upper(), TerrainCategory.URBAN),
            core_geometry=CoreWallGeometry(
                config=CoreWallConfig[lat["core_wall_config"].upper()],
                wall_thickness=cw.get("wall_thickness_mm", 400),
                length_x=cw.get("length_x_mm", 6000),
                length_y=cw.get("length_y_mm", 6000),
                web_length=cw.get("web_length_mm", 4000),
                flange_width=cw.get("flange_width_mm", 2000),
                opening_width=cw.get("opening_width_mm"),
                opening_height=cw.get("opening_height_mm"),
            )
        )
    )
    
    model = build_fem_model(project)
    results_dict = analyze_model(model, load_pattern=1)
    result = results_dict.get("combined") or next(iter(results_dict.values()))
    
    if result.success:
        base_shear = get_base_shear_from_reactions(result.node_reactions, "X") / 1000.0
        top_drift = get_top_drift(model, result.node_displacements, "X")
        total_weight = sum(abs(v[2]) for v in result.node_reactions.values()) / 1000.0
        max_axial = max(abs(v[2]) for v in result.node_reactions.values()) / 1000.0
        
        results_data = {
            "building_id": building_id,
            "results": {
                "max_lateral_drift_mm": top_drift,
                "base_shear_kN": base_shear,
                "total_weight_kN": total_weight,
                "max_column_axial_kN": max_axial,
                "max_story_drift_ratio": top_drift / (geom["floors"] * geom["story_height"] * 1000.0) if top_drift else None,
                "overturning_moment_kNm": 0.0,
                "max_beam_moment_kNm": 0.0,
                "first_mode_period_s": 0.0,
            }
        }
        
        output_dir = Path(".sisyphus/validation/prelimstruct_results")
        output_dir.mkdir(exist_ok=True)
        with open(output_dir / f"{building_id}_results.json", "w") as f:
            json.dump(results_data, f, indent=2)

if __name__ == "__main__":
    for i in range(1, 6):
        run_analysis(f"building_0{i}")
