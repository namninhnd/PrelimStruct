"""
Unit tests for Core Wall Data Models (Phase 12A - Gate C)

Tests the simplified data models for FEM v3.5:
- CoreWallConfig enum (2 options)
- TubeOpeningPlacement enum
- CoreLocationPreset enum
- CoreWallGeometry dataclass with opening_placement field
- CoreWallSectionProperties dataclass
- Updated LateralInput dataclass with location_preset
"""

import pytest
from src.core.data_models import (
    CoreWallConfig,
    TubeOpeningPlacement,
    CoreLocationPreset,
    CoreWallGeometry,
    CoreWallSectionProperties,
    LateralInput,
    TerrainCategory,
)


class TestCoreWallConfig:
    """Tests for CoreWallConfig enum."""

    def test_enum_values(self):
        """Test that all core wall configuration types are defined."""
        assert CoreWallConfig.I_SECTION.value == "i_section"
        assert CoreWallConfig.TUBE_WITH_OPENINGS.value == "tube_with_openings"

    def test_enum_count(self):
        """Test that we have exactly 2 configuration types."""
        assert len(CoreWallConfig) == 2


class TestTubeOpeningPlacement:
    """Tests for TubeOpeningPlacement enum."""

    def test_enum_values(self):
        """Test that all tube opening placement options are defined."""
        assert TubeOpeningPlacement.TOP_BOT.value == "top_bot"
        assert TubeOpeningPlacement.NONE.value == "none"
        assert TubeOpeningPlacement.TOP.value == "top"
        assert TubeOpeningPlacement.BOTTOM.value == "bottom"
        assert TubeOpeningPlacement.BOTH.value == "both"

    def test_enum_count(self):
        """Test that we have 5 placement options (including legacy values)."""
        assert len(TubeOpeningPlacement) == 5


class TestCoreLocationPreset:
    """Tests for CoreLocationPreset enum."""

    def test_enum_values(self):
        """Test that all core location presets are defined."""
        assert CoreLocationPreset.CENTER.value == "center"
        assert CoreLocationPreset.NORTH.value == "north"
        assert CoreLocationPreset.SOUTH.value == "south"
        assert CoreLocationPreset.EAST.value == "east"
        assert CoreLocationPreset.WEST.value == "west"
        assert CoreLocationPreset.NORTHEAST.value == "northeast"
        assert CoreLocationPreset.NORTHWEST.value == "northwest"
        assert CoreLocationPreset.SOUTHEAST.value == "southeast"
        assert CoreLocationPreset.SOUTHWEST.value == "southwest"

    def test_enum_count(self):
        """Test that we have exactly 9 location presets."""
        assert len(CoreLocationPreset) == 9


class TestCoreWallGeometry:
    """Tests for CoreWallGeometry dataclass."""

    def test_default_values(self):
        """Test default values for core wall geometry."""
        geom = CoreWallGeometry(config=CoreWallConfig.I_SECTION)
        
        assert geom.config == CoreWallConfig.I_SECTION
        assert geom.wall_thickness == 500.0
        assert geom.length_x == 6000.0
        assert geom.length_y == 6000.0
        assert geom.opening_width is None
        assert geom.opening_height is None
        assert geom.flange_width is None
        assert geom.web_length is None
        assert geom.opening_placement == TubeOpeningPlacement.TOP_BOT

    def test_custom_values(self):
        """Test creating geometry with custom values."""
        geom = CoreWallGeometry(
            config=CoreWallConfig.TUBE_WITH_OPENINGS,
            wall_thickness=600.0,
            length_x=8000.0,
            length_y=10000.0,
            opening_width=2000.0,
            opening_height=2400.0,
            opening_placement=TubeOpeningPlacement.TOP_BOT,
        )
        
        assert geom.config == CoreWallConfig.TUBE_WITH_OPENINGS
        assert geom.wall_thickness == 600.0
        assert geom.length_x == 8000.0
        assert geom.length_y == 10000.0
        assert geom.opening_width == 2000.0
        assert geom.opening_height == 2400.0
        assert geom.opening_placement == TubeOpeningPlacement.TOP_BOT

    def test_i_section_geometry(self):
        """Test I-section specific geometry parameters."""
        geom = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            wall_thickness=500.0,
            flange_width=3000.0,
            web_length=6000.0,
        )
        
        assert geom.config == CoreWallConfig.I_SECTION
        assert geom.flange_width == 3000.0
        assert geom.web_length == 6000.0

    def test_tube_opening_placement_options(self):
        """Test all tube opening placement options."""
        for placement in [
            TubeOpeningPlacement.TOP_BOT,
            TubeOpeningPlacement.NONE,
            TubeOpeningPlacement.TOP,
            TubeOpeningPlacement.BOTTOM,
            TubeOpeningPlacement.BOTH,
        ]:
            geom = CoreWallGeometry(
                config=CoreWallConfig.TUBE_WITH_OPENINGS,
                opening_placement=placement,
            )
            assert geom.opening_placement == placement


class TestCoreWallSectionProperties:
    """Tests for CoreWallSectionProperties dataclass."""

    def test_default_values(self):
        """Test default values for section properties."""
        props = CoreWallSectionProperties()
        
        assert props.I_xx == 0.0
        assert props.I_yy == 0.0
        assert props.I_xy == 0.0
        assert props.A == 0.0
        assert props.J == 0.0
        assert props.centroid_x == 0.0
        assert props.centroid_y == 0.0
        assert props.shear_center_x == 0.0
        assert props.shear_center_y == 0.0

    def test_custom_values(self):
        """Test creating section properties with custom values."""
        props = CoreWallSectionProperties(
            I_xx=1.5e12,
            I_yy=2.0e12,
            I_xy=0.1e12,
            A=3.0e6,
            J=2.5e12,
            centroid_x=3000.0,
            centroid_y=3000.0,
            shear_center_x=3000.0,
            shear_center_y=3000.0,
        )
        
        assert props.I_xx == pytest.approx(1.5e12, rel=1e-6)
        assert props.I_yy == pytest.approx(2.0e12, rel=1e-6)
        assert props.I_xy == pytest.approx(0.1e12, rel=1e-6)
        assert props.A == pytest.approx(3.0e6, rel=1e-6)
        assert props.J == pytest.approx(2.5e12, rel=1e-6)
        assert props.centroid_x == 3000.0
        assert props.centroid_y == 3000.0
        assert props.shear_center_x == 3000.0
        assert props.shear_center_y == 3000.0

    def test_symmetric_section(self):
        """Test section properties for symmetric section (I_xy should be zero)."""
        props = CoreWallSectionProperties(
            I_xx=1.0e12,
            I_yy=1.0e12,
            I_xy=0.0,
            A=2.0e6,
        )
        
        assert props.I_xy == 0.0


class TestLateralInputUpdates:
    """Tests for updated LateralInput dataclass with Phase 12A fields."""

    def test_v3_fields_default_values(self):
        """Test v3.5 FEM fields have correct default values."""
        lateral = LateralInput()
        
        assert lateral.core_wall_config is None
        assert lateral.wall_thickness == 500.0
        assert lateral.core_geometry is None
        assert lateral.section_properties is None
        assert lateral.location_preset == CoreLocationPreset.CENTER
        assert lateral.custom_center_x is None
        assert lateral.custom_center_y is None

    def test_v3_fields_with_values(self):
        """Test setting v3.5 FEM fields."""
        geom = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            wall_thickness=600.0,
        )
        
        props = CoreWallSectionProperties(
            I_xx=1.0e12,
            I_yy=1.5e12,
            A=3.0e6,
        )
        
        lateral = LateralInput(
            core_wall_config=CoreWallConfig.I_SECTION,
            wall_thickness=600.0,
            core_geometry=geom,
            section_properties=props,
            location_preset=CoreLocationPreset.NORTHEAST,
        )
        
        assert lateral.core_wall_config == CoreWallConfig.I_SECTION
        assert lateral.wall_thickness == 600.0
        assert lateral.core_geometry == geom
        assert lateral.section_properties == props
        assert lateral.location_preset == CoreLocationPreset.NORTHEAST

    def test_all_location_presets(self):
        """Test all location preset options."""
        for preset in [
            CoreLocationPreset.CENTER,
            CoreLocationPreset.NORTH,
            CoreLocationPreset.SOUTH,
            CoreLocationPreset.EAST,
            CoreLocationPreset.WEST,
            CoreLocationPreset.NORTHEAST,
            CoreLocationPreset.NORTHWEST,
            CoreLocationPreset.SOUTHEAST,
            CoreLocationPreset.SOUTHWEST,
        ]:
            lateral = LateralInput(location_preset=preset)
            assert lateral.location_preset == preset


class TestCoreWallConfigurationTypes:
    """Tests for different core wall configuration types."""

    def test_i_section_config(self):
        """Test I-section configuration."""
        geom = CoreWallGeometry(
            config=CoreWallConfig.I_SECTION,
            flange_width=3000.0,
            web_length=6000.0,
        )
        assert geom.config == CoreWallConfig.I_SECTION

    def test_tube_with_openings_config(self):
        """Test tube with openings configuration."""
        geom = CoreWallGeometry(
            config=CoreWallConfig.TUBE_WITH_OPENINGS,
            opening_width=2000.0,
            opening_height=2400.0,
            opening_placement=TubeOpeningPlacement.TOP_BOT,
        )
        assert geom.config == CoreWallConfig.TUBE_WITH_OPENINGS
        assert geom.opening_width == 2000.0
        assert geom.opening_height == 2400.0
        assert geom.opening_placement == TubeOpeningPlacement.TOP_BOT


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
