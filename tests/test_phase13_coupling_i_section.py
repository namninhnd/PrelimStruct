import pytest

from src.core.data_models import CoreWallConfig, CoreWallGeometry
from src.fem.coupling_beam import CouplingBeamGenerator


def test_i_section_generator_returns_two_parallel_beams() -> None:
    geometry = CoreWallGeometry(
        config=CoreWallConfig.I_SECTION,
        wall_thickness=500.0,
        flange_width=3000.0,
        web_length=6000.0,
    )
    generator = CouplingBeamGenerator(geometry)

    beams = generator.generate_coupling_beams(
        story_height=3000.0,
        top_clearance=200.0,
        bottom_clearance=200.0,
    )

    assert len(beams) == 2
    assert beams[0].clear_span == pytest.approx(3000.0)
    assert beams[1].clear_span == pytest.approx(3000.0)
    assert beams[0].location_x == pytest.approx(1500.0)
    assert beams[1].location_x == pytest.approx(1500.0)
    assert beams[0].location_y == pytest.approx(0.0)
    assert beams[1].location_y == pytest.approx(6000.0)


def test_i_section_generator_beam_depth_uses_story_clearances() -> None:
    geometry = CoreWallGeometry(
        config=CoreWallConfig.I_SECTION,
        wall_thickness=500.0,
        flange_width=2800.0,
        web_length=5400.0,
    )
    generator = CouplingBeamGenerator(geometry)

    beams = generator.generate_coupling_beams(
        story_height=3200.0,
        top_clearance=300.0,
        bottom_clearance=250.0,
    )

    assert len(beams) == 2
    assert beams[0].depth == pytest.approx(2650.0)
    assert beams[1].depth == pytest.approx(2650.0)
