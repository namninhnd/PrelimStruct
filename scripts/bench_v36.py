# scripts/bench_v36.py
import platform
import sys
import time
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.data_models import (
    BeamResult,
    ColumnResult,
    GeometryInput,
    LoadInput,
    LateralInput,
    MaterialInput,
    ProjectData,
)
from src.fem.model_builder import build_fem_model, ModelBuilderOptions
from src.fem.visualization import create_plan_view, create_elevation_view, create_3d_view, VisualizationConfig

# Reuse the minimal, tested project builder pattern
# (mirrors `tests/test_model_builder.py:_make_project`)
def create_test_project(floors: int = 10, num_bays_x: int = 3, num_bays_y: int = 3) -> ProjectData:
    bay_x = 6.0
    bay_y = 5.0
    story_height = 3.0
    project = ProjectData(
        geometry=GeometryInput(
            bay_x=bay_x,
            bay_y=bay_y,
            floors=floors,
            story_height=story_height,
            num_bays_x=num_bays_x,
            num_bays_y=num_bays_y,
        ),
        loads=LoadInput(live_load_class="2", live_load_sub="2.5", dead_load=2.0),
        materials=MaterialInput(fcu_slab=35, fcu_beam=40, fcu_column=45),
        lateral=LateralInput(building_width=bay_x * num_bays_x, building_depth=bay_y * num_bays_y),
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

def benchmark(func, *args, runs=5, **kwargs):
    """Time function execution over multiple runs."""
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        func(*args, **kwargs)
        times.append((time.perf_counter() - start) * 1000)
    return {"min": min(times), "avg": sum(times)/len(times), "max": max(times)}

def main():
    project = create_test_project(floors=10, num_bays_x=3, num_bays_y=3)
    
    # Warmup
    options = ModelBuilderOptions(
        include_core_wall=False,
        include_slabs=False,
        apply_wind_loads=False,
        apply_gravity_loads=True,
    )
    model = build_fem_model(project, options)
    
    # Benchmark model build
    build_times = benchmark(build_fem_model, project, options)
    
    # Benchmark rendering
    config = VisualizationConfig()
    top_floor = max((n.z for n in model.nodes.values()), default=0.0)
    plan_times = benchmark(create_plan_view, model, config, floor_elevation=top_floor)
    elev_times = benchmark(create_elevation_view, model, config, view_direction="X")
    view3d_times = benchmark(create_3d_view, model, config)
    
    # Save results
    report = Path(".sisyphus/evidence/v36-perf-baseline.md")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "\n".join(
            [
                "# v3.6 Performance Baseline",
                "",
                f"- Platform: {platform.platform()}",
                "- Benchmark project: floors=10, bays=3x3, bay=6.0x5.0m, story=3.0m",
                "- Options: include_core_wall=False, include_slabs=False, apply_wind_loads=False, apply_gravity_loads=True",
                "",
                f"- build_fem_model (ms): {build_times}",
                f"- create_plan_view (ms): {plan_times}",
                f"- create_elevation_view (ms): {elev_times}",
                f"- create_3d_view (ms): {view3d_times}",
                "",
            ]
        ),
        encoding="utf-8",
    )

if __name__ == "__main__":
    main()
