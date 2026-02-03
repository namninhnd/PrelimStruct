"""
Unit tests for Core Wall Data Models (Task 8.1.1)

Tests the new data models and enums added for FEM v3.0:
- CoreWallConfig enum
- CoreWallGeometry dataclass
- CoreWallSectionProperties dataclass
- Updated LateralInput dataclass
"""

import pytest
from src.core.data_models import (
    CoreWallConfig,
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
        assert CoreWallConfig.TWO_C_FACING.value == "two_c_facing"
        assert CoreWallConfig.TWO_C_BACK_TO_BACK.value == "two_c_back_to_back"
        assert CoreWallConfig.TUBE_CENTER_OPENING.value == "tube_center_opening"
        assert CoreWallConfig.TUBE_SIDE_OPENING.value == "tube_side_opening"

    def test_enum_count(self):
        """Test that we have exactly 5 configuration types."""
        assert len(CoreWallConfig) == 5


class TestCoreWallGeometry:
    """Tests for CoreWallGeometry dataclass."""

    def test_default_values(self):
        """Test default values for core wall geometry."""
        geom = CoreWallGeometry(config=CoreWallConfig.I_SECTION)
        
        assert geom.config == CoreWallConfig.I_SECTION
        assert geom.wall_thickness == 500.0  # mm
        assert geom.length_x == 6000.0  # mm
        assert geom.length_y == 6000.0  # mm
        assert geom.opening_width is None
        assert geom.opening_height is None
        assert geom.flange_width is None
        assert geom.web_length is None

    def test_custom_values(self):
        """Test creating geometry with custom values."""
        geom = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            wall_thickness=600.0,
            length_x=8000.0,
            length_y=10000.0,
            opening_width=2000.0,
            opening_height=2400.0,
            flange_width=3000.0,
            web_length=6000.0,
        )
        
        assert geom.config == CoreWallConfig.TWO_C_FACING
        assert geom.wall_thickness == 600.0
        assert geom.length_x == 8000.0
        assert geom.length_y == 10000.0
        assert geom.opening_width == 2000.0
        assert geom.opening_height == 2400.0
        assert geom.flange_width == 3000.0
        assert geom.web_length == 6000.0

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
            I_xx=1.5e12,  # mm⁴
            I_yy=2.0e12,  # mm⁴
            I_xy=0.1e12,  # mm⁴
            A=3.0e6,      # mm²
            J=2.5e12,     # mm⁴
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
            I_xy=0.0,  # Symmetric section
            A=2.0e6,
        )
        
        assert props.I_xy == 0.0


class TestLateralInputUpdates:
    """Tests for updated LateralInput dataclass with v3.0 fields."""

    def test_legacy_fields_removed(self):
        """Test that legacy v2.1 fields are no longer accepted."""
        with pytest.raises(TypeError):
            LateralInput(
                core_dim_x=6.0,
                core_dim_y=6.0,
                core_thickness=0.5,
                core_location="center",
                terrain=TerrainCategory.URBAN,
                building_width=30.0,
                building_depth=20.0,
            )

    def test_v3_fields_default_values(self):
        """Test v3.0 FEM fields have correct default values."""
        lateral = LateralInput()
        
        assert lateral.core_wall_config is None
        assert lateral.wall_thickness == 500.0  # mm
        assert lateral.core_geometry is None
        assert lateral.section_properties is None

    def test_v3_fields_with_values(self):
        """Test setting v3.0 FEM fields."""
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
        )
        
        assert lateral.core_wall_config == CoreWallConfig.I_SECTION
        assert lateral.wall_thickness == 600.0
        assert lateral.core_geometry == geom
        assert lateral.section_properties == props

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

    def test_two_c_facing_config(self):
        """Test two C-walls facing each other configuration."""
        geom = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_FACING,
            opening_width=2000.0,
        )
        assert geom.config == CoreWallConfig.TWO_C_FACING
        assert geom.opening_width == 2000.0

    def test_two_c_back_to_back_config(self):
        """Test two C-walls back to back configuration."""
        geom = CoreWallGeometry(
            config=CoreWallConfig.TWO_C_BACK_TO_BACK,
        )
        assert geom.config == CoreWallConfig.TWO_C_BACK_TO_BACK

    def test_tube_center_opening_config(self):
        """Test tube with center opening configuration."""
        geom = CoreWallGeometry(
            config=CoreWallConfig.TUBE_CENTER_OPENING,
            opening_width=2000.0,
            opening_height=2400.0,
        )
        assert geom.config == CoreWallConfig.TUBE_CENTER_OPENING
        assert geom.opening_width == 2000.0
        assert geom.opening_height == 2400.0

    def test_tube_side_opening_config(self):
        """Test tube with side opening configuration."""
        geom = CoreWallGeometry(
            config=CoreWallConfig.TUBE_SIDE_OPENING,
            opening_width=1500.0,
        )
        assert geom.config == CoreWallConfig.TUBE_SIDE_OPENING
        assert geom.opening_width == 1500.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
