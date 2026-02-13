import pytest
from src.core.data_models import (
    CoreWallConfig,
    CoreWallGeometry,
)
from src.fem.model_builder import _get_core_opening_for_slab


class TestGateFSlabOpening:
    def test_i_section_returns_coupling_band_rectangle_opening(self):
        core_geo = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            wall_thickness=500.0,
            flange_width=3000.0,
            web_length=6000.0,
        )
        
        opening = _get_core_opening_for_slab(core_geo, offset_x=5.0, offset_y=5.0)
        
        assert opening is not None
        assert opening.opening_id == "CORE_I_SECTION_COUPLING_BAND"
        assert opening.opening_type == "core_footprint"
        assert opening.polygon_vertices is None
        
        expected_width = 3000.0 / 1000.0
        expected_height = 6000.0 / 1000.0
        
        assert opening.origin == (5.0, 5.0)
        assert opening.width_x == pytest.approx(expected_width, abs=1e-6)
        assert opening.width_y == pytest.approx(expected_height, abs=1e-6)

    def test_tube_returns_full_bounding_box_opening(self):
        core_geo = CoreWallGeometry(
            config=CoreWallConfig.TUBE_WITH_OPENINGS,
            wall_thickness=500.0,
            length_x=4000.0,
            length_y=8000.0,
            opening_width=1200.0,
            opening_height=2400.0,
        )
        
        opening = _get_core_opening_for_slab(core_geo, offset_x=3.0, offset_y=4.0)
        
        assert opening is not None
        assert opening.opening_id == "CORE_FULL_FOOTPRINT"
        assert opening.opening_type == "core_footprint"
        
        expected_width = 4000.0 / 1000.0
        expected_height = 8000.0 / 1000.0
        
        assert opening.origin == (3.0, 4.0)
        assert opening.width_x == pytest.approx(expected_width, abs=1e-6)
        assert opening.width_y == pytest.approx(expected_height, abs=1e-6)

class TestGateFConservativeExclusion:
    def test_i_section_uses_full_footprint_rectangle(self):
        core_geo = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            wall_thickness=500.0,
            flange_width=3000.0,
            web_length=6000.0,
        )
        
        opening = _get_core_opening_for_slab(core_geo, offset_x=0.0, offset_y=0.0)
        assert opening is not None
        
        assert opening.width_x == 3.0
        assert opening.width_y == 6.0
