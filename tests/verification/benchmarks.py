from src.core.constants import CONCRETE_DENSITY
from src.core.data_models import (
    BeamResult,
    ColumnResult,
    GeometryInput,
    LateralInput,
    LoadInput,
    MaterialInput,
    ProjectData,
    SlabResult,
)
from src.fem.model_builder import ModelBuilderOptions

SDL_KPA = 1.5
LL_KPA = 3.0


def build_benchmark_project_1x1(
    sdl_kpa: float = SDL_KPA,
    ll_kpa: float = LL_KPA,
) -> ProjectData:
    project = ProjectData(
        geometry=GeometryInput(
            bay_x=6.0,
            bay_y=6.0,
            floors=1,
            story_height=4.0,
            num_bays_x=1,
            num_bays_y=1,
        ),
        loads=LoadInput(
            live_load_class="9",
            live_load_sub="",
            dead_load=sdl_kpa,
            custom_live_load=ll_kpa,
        ),
        materials=MaterialInput(fcu_slab=40, fcu_beam=40, fcu_column=40),
        lateral=LateralInput(),
    )

    project.slab_result = SlabResult(
        element_type="Slab",
        size="150",
        thickness=150,
        self_weight=0.150 * CONCRETE_DENSITY,
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
        size="500",
        dimension=500,
    )

    return project


def build_benchmark_project_2x3(
    sdl_kpa: float = SDL_KPA,
    ll_kpa: float = LL_KPA,
) -> ProjectData:
    project = build_benchmark_project_1x1(sdl_kpa=sdl_kpa, ll_kpa=ll_kpa)
    project.geometry.num_bays_x = 2
    project.geometry.num_bays_y = 3
    return project


def make_benchmark_options(
    slab_elements_per_bay: int = 1,
) -> ModelBuilderOptions:
    return ModelBuilderOptions(
        include_core_wall=False,
        include_slabs=True,
        num_secondary_beams=0,
        slab_elements_per_bay=slab_elements_per_bay,
        apply_gravity_loads=True,
        apply_wind_loads=False,
    )


def _get_plan_area(project: ProjectData) -> float:
    total_x = project.geometry.bay_x * project.geometry.num_bays_x
    total_y = project.geometry.bay_y * project.geometry.num_bays_y
    return total_x * total_y


def calc_sdl_total_load(project: ProjectData) -> float:
    return project.loads.dead_load * _get_plan_area(project)


def calc_ll_total_load(project: ProjectData) -> float:
    return project.loads.live_load * _get_plan_area(project)


def calc_slab_self_weight(
    project: ProjectData, slab_thickness_m: float = 0.150
) -> float:
    return CONCRETE_DENSITY * slab_thickness_m * _get_plan_area(project)


def _get_total_beam_length(project: ProjectData) -> float:
    geo = project.geometry
    x_gridline_beams = (geo.num_bays_y + 1) * geo.num_bays_x * geo.bay_x
    y_gridline_beams = (geo.num_bays_x + 1) * geo.num_bays_y * geo.bay_y
    return x_gridline_beams + y_gridline_beams


def calc_beam_self_weight(project: ProjectData) -> float:
    if project.primary_beam_result is None:
        raise ValueError("primary_beam_result not set")
    beam_b_m = project.primary_beam_result.width / 1000.0
    beam_h_m = project.primary_beam_result.depth / 1000.0
    line_load_kn_m = CONCRETE_DENSITY * beam_b_m * beam_h_m
    return line_load_kn_m * _get_total_beam_length(project)


def _get_column_count(project: ProjectData) -> int:
    return (project.geometry.num_bays_x + 1) * (project.geometry.num_bays_y + 1)


def calc_column_self_weight(project: ProjectData) -> float:
    if project.column_result is None:
        raise ValueError("column_result not set")
    dim = project.column_result.dimension
    col_b_m = dim / 1000.0
    col_h_m = dim / 1000.0
    story_height = project.geometry.story_height
    n_columns = _get_column_count(project)
    floors = project.geometry.floors
    return CONCRETE_DENSITY * col_b_m * col_h_m * story_height * n_columns * floors


def calc_dl_total_load(project: ProjectData, slab_thickness_m: float = 0.150) -> float:
    return (
        calc_slab_self_weight(project, slab_thickness_m=slab_thickness_m)
        + calc_beam_self_weight(project)
        + calc_column_self_weight(project)
    )
