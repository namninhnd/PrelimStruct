"""
Baseline force validation tests.

This module validates the hand calculation baseline fixture data.
These tests can be placeholders that pass, confirming the fixture data is accessible.
"""

import pytest
from tests.fixtures.hand_calc_baseline import (
    SIMPLY_SUPPORTED_UDL,
    FIXED_END_UDL,
    CANTILEVER_POINT_LOAD,
    ALL_BASELINE_CASES,
    TOLERANCE,
    get_baseline_case,
    get_expected_forces_at_position,
)


class TestBaselineFixtureAccess:
    """Validate baseline fixture data is accessible and well-formed."""
    
    def test_simply_supported_udl_accessible(self):
        """GIVEN simply supported UDL baseline case
        WHEN accessing the fixture
        THEN should have correct configuration"""
        assert SIMPLY_SUPPORTED_UDL.name == "simply_supported_udl"
        assert SIMPLY_SUPPORTED_UDL.length == 6.0
        assert SIMPLY_SUPPORTED_UDL.udl == 10.0
        assert len(SIMPLY_SUPPORTED_UDL.forces) == 5
    
    def test_simply_supported_udl_max_moment(self):
        """GIVEN simply supported UDL baseline case
        WHEN checking midspan moment
        THEN should equal wL²/8 = 45 kN.m"""
        midspan_forces = get_expected_forces_at_position(SIMPLY_SUPPORTED_UDL, 0.5)
        assert midspan_forces.moment == 45.0
        assert midspan_forces.shear == 0.0
    
    def test_simply_supported_udl_max_shear(self):
        """GIVEN simply supported UDL baseline case
        WHEN checking support shear
        THEN should equal wL/2 = 30 kN"""
        left_support = get_expected_forces_at_position(SIMPLY_SUPPORTED_UDL, 0.0)
        assert left_support.shear == 30.0
        assert left_support.moment == 0.0
        
        right_support = get_expected_forces_at_position(SIMPLY_SUPPORTED_UDL, 1.0)
        assert right_support.shear == -30.0
        assert right_support.moment == 0.0
    
    def test_fixed_end_udl_accessible(self):
        """GIVEN fixed-end UDL baseline case
        WHEN accessing the fixture
        THEN should have correct configuration"""
        assert FIXED_END_UDL.name == "fixed_end_udl"
        assert FIXED_END_UDL.length == 6.0
        assert FIXED_END_UDL.udl == 10.0
        assert len(FIXED_END_UDL.forces) == 5
    
    def test_fixed_end_udl_support_moment(self):
        """GIVEN fixed-end UDL baseline case
        WHEN checking support moment
        THEN should equal -wL²/12 = -30 kN.m"""
        left_support = get_expected_forces_at_position(FIXED_END_UDL, 0.0)
        assert left_support.moment == -30.0
        assert left_support.shear == 30.0
    
    def test_fixed_end_udl_midspan_moment(self):
        """GIVEN fixed-end UDL baseline case
        WHEN checking midspan moment
        THEN should equal wL²/24 = 15 kN.m"""
        midspan_forces = get_expected_forces_at_position(FIXED_END_UDL, 0.5)
        assert midspan_forces.moment == 15.0
        assert midspan_forces.shear == 0.0
    
    def test_cantilever_point_load_accessible(self):
        """GIVEN cantilever point load baseline case
        WHEN accessing the fixture
        THEN should have correct configuration"""
        assert CANTILEVER_POINT_LOAD.name == "cantilever_point_load"
        assert CANTILEVER_POINT_LOAD.length == 4.0
        assert CANTILEVER_POINT_LOAD.point_load == 50.0
        assert len(CANTILEVER_POINT_LOAD.forces) == 5
    
    def test_cantilever_point_load_base_moment(self):
        """GIVEN cantilever point load baseline case
        WHEN checking base moment
        THEN should equal P*H = 200 kN.m"""
        base_forces = get_expected_forces_at_position(CANTILEVER_POINT_LOAD, 0.0)
        assert base_forces.moment == 200.0
        assert base_forces.shear == 50.0
        assert base_forces.axial == 50.0
    
    def test_cantilever_point_load_mid_moment(self):
        """GIVEN cantilever point load baseline case
        WHEN checking mid-height moment
        THEN should equal P*H/2 = 100 kN.m"""
        mid_forces = get_expected_forces_at_position(CANTILEVER_POINT_LOAD, 0.5)
        assert mid_forces.moment == 100.0
        assert mid_forces.shear == 50.0
        assert mid_forces.axial == 50.0
    
    def test_all_baseline_cases_list(self):
        """GIVEN ALL_BASELINE_CASES constant
        WHEN checking the list
        THEN should contain all 3 cases"""
        assert len(ALL_BASELINE_CASES) == 3
        case_names = [case.name for case in ALL_BASELINE_CASES]
        assert "simply_supported_udl" in case_names
        assert "fixed_end_udl" in case_names
        assert "cantilever_point_load" in case_names
    
    def test_tolerance_constant(self):
        """GIVEN TOLERANCE constant
        WHEN checking the value
        THEN should equal 0.01 (1%)"""
        assert TOLERANCE == 0.01


class TestBaselineHelperFunctions:
    """Validate helper functions for accessing baseline data."""
    
    def test_get_baseline_case_by_name(self):
        """GIVEN baseline case name
        WHEN calling get_baseline_case
        THEN should return the correct case"""
        case = get_baseline_case("simply_supported_udl")
        assert case.name == "simply_supported_udl"
        assert case.length == 6.0
    
    def test_get_baseline_case_invalid_name(self):
        """GIVEN invalid baseline case name
        WHEN calling get_baseline_case
        THEN should raise ValueError"""
        with pytest.raises(ValueError, match="Baseline case 'invalid_name' not found"):
            get_baseline_case("invalid_name")
    
    def test_get_expected_forces_at_position_valid(self):
        """GIVEN valid position in baseline case
        WHEN calling get_expected_forces_at_position
        THEN should return forces at that position"""
        forces = get_expected_forces_at_position(SIMPLY_SUPPORTED_UDL, 0.5)
        assert forces.position == 0.5
        assert forces.moment == 45.0
    
    def test_get_expected_forces_at_position_invalid(self):
        """GIVEN invalid position in baseline case
        WHEN calling get_expected_forces_at_position
        THEN should raise ValueError"""
        with pytest.raises(ValueError, match="Position 0.333 not found"):
            get_expected_forces_at_position(SIMPLY_SUPPORTED_UDL, 0.333)
    
    def test_get_expected_forces_at_position_with_tolerance(self):
        """GIVEN position within tolerance
        WHEN calling get_expected_forces_at_position
        THEN should return nearest matching position"""
        forces = get_expected_forces_at_position(SIMPLY_SUPPORTED_UDL, 0.501, tolerance=0.01)
        assert forces.position == 0.5
        assert forces.moment == 45.0


class TestSubdivisionPointCoverage:
    """Validate that all required subdivision points are present."""
    
    @pytest.mark.parametrize("case_name", [
        "simply_supported_udl",
        "fixed_end_udl",
        "cantilever_point_load",
    ])
    def test_all_subdivision_points_present(self, case_name):
        """GIVEN baseline case
        WHEN checking force data points
        THEN should have all 5 subdivision points (0L to 1.0L)"""
        case = get_baseline_case(case_name)
        positions = [f.position for f in case.forces]
        
        expected_positions = [0.0, 0.25, 0.5, 0.75, 1.0]
        
        for expected_pos in expected_positions:
            assert any(
                abs(pos - expected_pos) < 0.01 for pos in positions
            ), f"Position {expected_pos} not found in {case_name}"
    
    @pytest.mark.parametrize("case", [
        SIMPLY_SUPPORTED_UDL,
        FIXED_END_UDL,
        CANTILEVER_POINT_LOAD,
    ])
    def test_all_forces_have_labels(self, case):
        """GIVEN baseline case
        WHEN checking force data
        THEN all force points should have position labels"""
        for force_point in case.forces:
            assert force_point.position_label is not None
            assert len(force_point.position_label) > 0
