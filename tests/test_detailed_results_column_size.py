from src.core.data_models import ColumnResult, GeometryInput, LoadInput, MaterialInput, ProjectData
from src.ui.utils import format_column_size_mm


def _project_with_column(column_result: ColumnResult) -> ProjectData:
    project = ProjectData(
        geometry=GeometryInput(bay_x=6.0, bay_y=6.0, floors=5),
        loads=LoadInput(live_load_class="2", live_load_sub="2.5", dead_load=2.0),
        materials=MaterialInput(),
    )
    project.column_result = column_result
    return project


def test_detailed_results_uses_width_depth_when_available() -> None:
    project = _project_with_column(
        ColumnResult(
            element_type="Column",
            size="500x800",
            width=500,
            depth=800,
            dimension=800,
        )
    )

    assert format_column_size_mm(project) == "500 x 800 mm"


def test_detailed_results_falls_back_to_dimension() -> None:
    project = _project_with_column(
        ColumnResult(
            element_type="Column",
            size="600",
            width=0,
            depth=0,
            dimension=600,
        )
    )

    assert format_column_size_mm(project) == "600 x 600 mm"
