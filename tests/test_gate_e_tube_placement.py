import pytest

from src.core.data_models import (
    CoreWallConfig,
    CoreWallGeometry,
    GeometryInput,
    LateralInput,
    LoadInput,
    MaterialInput,
    ProjectData,
    TubeOpeningPlacement,
)
from src.fem.builders.core_wall_builder import CoreWallBuilder
from src.fem.coupling_beam import CouplingBeamGenerator
from src.fem.core_wall_geometry import TubeWithOpeningsCoreWall
from src.fem.fem_engine import FEMModel


def _make_project(geometry: CoreWallGeometry) -> ProjectData:
    return ProjectData(
        geometry=GeometryInput(
            bay_x=8.0,
            bay_y=8.0,
            floors=2,
            story_height=3.6,
            num_bays_x=2,
            num_bays_y=2,
        ),
        loads=LoadInput(live_load_class="2", live_load_sub="2.5", dead_load=2.0),
        materials=MaterialInput(fcu_slab=35, fcu_beam=40, fcu_column=45),
        lateral=LateralInput(
            building_width=16.0,
            building_depth=16.0,
            core_geometry=geometry,
        ),
    )


class TestGateETubeOutlinePlacement:
    def test_top_bot_opening_generates_two_opening_loops(self):
        geometry = CoreWallGeometry(
            config=CoreWallConfig.TUBE_WITH_OPENINGS,
            wall_thickness=500.0,
            length_x=6000.0,
            length_y=8000.0,
            opening_width=2000.0,
            opening_placement=TubeOpeningPlacement.TOP_BOT,
        )
        tube = TubeWithOpeningsCoreWall(geometry)
        coords = tube.get_outline_coordinates()

        assert len(coords) == 15
        outer = coords[0:5]
        bottom = coords[5:10]
        top = coords[10:15]

        assert outer[0] == outer[-1]
        assert bottom[0] == bottom[-1]
        assert top[0] == top[-1]

    def test_none_opening_generates_outer_loop_only(self):
        geometry = CoreWallGeometry(
            config=CoreWallConfig.TUBE_WITH_OPENINGS,
            wall_thickness=500.0,
            length_x=6000.0,
            length_y=8000.0,
            opening_width=None,
            opening_placement=TubeOpeningPlacement.NONE,
        )
        tube = TubeWithOpeningsCoreWall(geometry)
        coords = tube.get_outline_coordinates()

        assert len(coords) == 5
        assert coords[0] == coords[-1]


class TestGateEWallPanelSplit:
    def test_top_bot_placement_produces_symmetric_side_mesh(self):
        geometry = CoreWallGeometry(
            config=CoreWallConfig.TUBE_WITH_OPENINGS,
            wall_thickness=500.0,
            length_x=6000.0,
            length_y=8000.0,
            opening_width=2000.0,
            opening_placement=TubeOpeningPlacement.TOP_BOT,
        )
        project = _make_project(geometry)

        from src.fem.model_builder import ModelBuilderOptions

        builder = CoreWallBuilder(model=FEMModel(), project=project, options=ModelBuilderOptions())
        panels = builder._extract_wall_panels(core_geometry=geometry, offset_x=0.0, offset_y=0.0)

        assert len(panels) == 6
        panel_ids = {p.wall_id for p in panels}
        assert panel_ids == {"TW1_left", "TW1_right", "TW2", "TW3_left", "TW3_right", "TW4"}

        tw2 = next(p for p in panels if p.wall_id == "TW2")
        tw4 = next(p for p in panels if p.wall_id == "TW4")
        assert tw2.length == pytest.approx(tw4.length)

    def test_none_placement_produces_closed_tube_panels(self):
        geometry = CoreWallGeometry(
            config=CoreWallConfig.TUBE_WITH_OPENINGS,
            wall_thickness=500.0,
            length_x=6000.0,
            length_y=8000.0,
            opening_width=None,
            opening_placement=TubeOpeningPlacement.NONE,
        )
        project = _make_project(geometry)

        from src.fem.model_builder import ModelBuilderOptions

        builder = CoreWallBuilder(model=FEMModel(), project=project, options=ModelBuilderOptions())
        panels = builder._extract_wall_panels(core_geometry=geometry, offset_x=0.0, offset_y=0.0)

        assert len(panels) == 4
        assert {p.wall_id for p in panels} == {"TW1", "TW2", "TW3", "TW4"}


class TestGateECouplingBeamAlignment:
    def test_coupling_beams_match_top_bot(self):
        geometry = CoreWallGeometry(
            config=CoreWallConfig.TUBE_WITH_OPENINGS,
            wall_thickness=500.0,
            length_x=6000.0,
            length_y=8000.0,
            opening_width=2000.0,
            opening_placement=TubeOpeningPlacement.TOP_BOT,
        )

        generator = CouplingBeamGenerator(geometry)
        beams = generator.generate_coupling_beams(
            story_height=3600.0,
            top_clearance=200.0,
            bottom_clearance=200.0,
        )

        assert len(beams) == 2
        y_locations = {b.location_y for b in beams}
        assert y_locations == {0.0, 8000.0}

    def test_coupling_beams_none_returns_empty(self):
        geometry = CoreWallGeometry(
            config=CoreWallConfig.TUBE_WITH_OPENINGS,
            wall_thickness=500.0,
            length_x=6000.0,
            length_y=8000.0,
            opening_width=None,
            opening_placement=TubeOpeningPlacement.NONE,
        )

        generator = CouplingBeamGenerator(geometry)
        beams = generator.generate_coupling_beams(
            story_height=3600.0,
            top_clearance=200.0,
            bottom_clearance=200.0,
        )

        assert beams == []
