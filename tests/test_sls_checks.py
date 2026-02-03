"""
Tests for SLS (Serviceability Limit State) Checks Module

This module tests:
- MemberType enum values
- ExposureCondition enum values
- SpanDepthCheckResult dataclass
- DeflectionCheckResult dataclass
- CrackWidthCheckResult dataclass
- SLSChecker.check_span_depth_ratio() method (HK Code 2013 Cl 7.3.4)
- SLSChecker.check_deflection() method (HK Code 2013 Cl 7.3.2-7.3.3)
- SLSChecker.check_crack_width() method (HK Code 2013 Cl 7.2)
- SLSChecker.get_summary_report() method
"""

from src.fem.sls_checks import (
    MemberType,
    ExposureCondition,
    SpanDepthCheckResult,
    DeflectionCheckResult,
    CrackWidthCheckResult,
    SLSChecker,
)


class TestEnums:
    """Test enum definitions and values."""
    
    def test_member_type_enum_values(self):
        """Test all MemberType enum values are accessible."""
        assert MemberType.CANTILEVER.value == "cantilever"
        assert MemberType.SIMPLY_SUPPORTED_BEAM.value == "simply_supported"
        assert MemberType.CONTINUOUS_BEAM.value == "continuous"
        assert MemberType.RECTANGULAR_FLANGED_BEAM.value == "rectangular"
        assert MemberType.T_BEAM.value == "flanged"
        assert MemberType.ONE_WAY_SLAB.value == "one_way_slab"
        assert MemberType.TWO_WAY_SLAB_RESTRAINED.value == "two_way_slab_restrained"
        assert MemberType.TWO_WAY_SLAB_SIMPLE.value == "two_way_slab_simple"
    
    def test_member_type_enum_count(self):
        """Test MemberType enum has 8 members."""
        assert len(MemberType) == 8
    
    def test_exposure_condition_enum_values(self):
        """Test all ExposureCondition enum values are accessible."""
        assert ExposureCondition.MILD.value == "mild"
        assert ExposureCondition.MODERATE.value == "moderate"
        assert ExposureCondition.SEVERE.value == "severe"
    
    def test_exposure_condition_enum_count(self):
        """Test ExposureCondition enum has 3 members."""
        assert len(ExposureCondition) == 3


class TestSpanDepthCheckResult:
    """Test SpanDepthCheckResult dataclass."""
    
    def test_span_depth_check_result_creation_minimal(self):
        """Test creation with required fields only."""
        result = SpanDepthCheckResult(
            member_id="B1",
            actual_ratio=25.0,
            allowable_ratio=26.0,
        )
        assert result.member_id == "B1"
        assert result.actual_ratio == 25.0
        assert result.allowable_ratio == 26.0
        assert result.modification_factor == 1.0  # default
        assert result.is_compliant == False  # default
        assert result.note == ""  # default
    
    def test_span_depth_check_result_creation_with_all_fields(self):
        """Test creation with all fields specified."""
        result = SpanDepthCheckResult(
            member_id="B2",
            actual_ratio=20.0,
            allowable_ratio=26.0,
            modification_factor=1.5,
            is_compliant=True,
            note="Compliant with modification"
        )
        assert result.member_id == "B2"
        assert result.actual_ratio == 20.0
        assert result.allowable_ratio == 26.0
        assert result.modification_factor == 1.5
        assert result.is_compliant == True
        assert result.note == "Compliant with modification"
    
    def test_span_depth_check_result_defaults(self):
        """Test default values are applied correctly."""
        result = SpanDepthCheckResult(
            member_id="B3",
            actual_ratio=30.0,
            allowable_ratio=26.0,
        )
        # Defaults should be applied
        assert result.modification_factor == 1.0
        assert result.is_compliant == False
        assert result.note == ""
    
    def test_span_depth_check_result_edge_case_zero_ratio(self):
        """Test with zero ratio edge case."""
        result = SpanDepthCheckResult(
            member_id="B_zero",
            actual_ratio=0.0,
            allowable_ratio=26.0,
        )
        assert result.actual_ratio == 0.0


class TestDeflectionCheckResult:
    """Test DeflectionCheckResult dataclass."""
    
    def test_deflection_check_result_creation_minimal(self):
        """Test creation with required fields only."""
        result = DeflectionCheckResult(
            member_id="S1",
            actual_deflection=15.0,
            allowable_deflection=20.0,
            span_length=10000.0,
            deflection_limit_ratio="L/500",
        )
        assert result.member_id == "S1"
        assert result.actual_deflection == 15.0
        assert result.allowable_deflection == 20.0
        assert result.span_length == 10000.0
        assert result.deflection_limit_ratio == "L/500"
        assert result.is_compliant == False  # default
        assert result.note == ""  # default
    
    def test_deflection_check_result_creation_with_all_fields(self):
        """Test creation with all fields specified."""
        result = DeflectionCheckResult(
            member_id="S2",
            actual_deflection=12.0,
            allowable_deflection=20.0,
            span_length=10000.0,
            deflection_limit_ratio="L/500",
            is_compliant=True,
            note="Within limit"
        )
        assert result.member_id == "S2"
        assert result.actual_deflection == 12.0
        assert result.allowable_deflection == 20.0
        assert result.span_length == 10000.0
        assert result.deflection_limit_ratio == "L/500"
        assert result.is_compliant == True
        assert result.note == "Within limit"
    
    def test_deflection_check_result_defaults(self):
        """Test default values are applied correctly."""
        result = DeflectionCheckResult(
            member_id="S3",
            actual_deflection=25.0,
            allowable_deflection=20.0,
            span_length=8000.0,
            deflection_limit_ratio="L/350",
        )
        # Defaults should be applied
        assert result.is_compliant == False
        assert result.note == ""
    
    def test_deflection_check_result_different_limit_ratios(self):
        """Test with different deflection limit ratios."""
        # L/500
        result1 = DeflectionCheckResult(
            member_id="S_500",
            actual_deflection=10.0,
            allowable_deflection=20.0,
            span_length=10000.0,
            deflection_limit_ratio="L/500",
        )
        assert result1.deflection_limit_ratio == "L/500"
        
        # L/350
        result2 = DeflectionCheckResult(
            member_id="S_350",
            actual_deflection=15.0,
            allowable_deflection=28.6,
            span_length=10000.0,
            deflection_limit_ratio="L/350",
        )
        assert result2.deflection_limit_ratio == "L/350"
        
        # L/250
        result3 = DeflectionCheckResult(
            member_id="S_250",
            actual_deflection=30.0,
            allowable_deflection=40.0,
            span_length=10000.0,
            deflection_limit_ratio="L/250",
        )
        assert result3.deflection_limit_ratio == "L/250"


class TestCrackWidthCheckResult:
    """Test CrackWidthCheckResult dataclass."""
    
    def test_crack_width_check_result_creation_minimal(self):
        """Test creation with required fields only."""
        result = CrackWidthCheckResult(
            member_id="W1",
            calculated_crack_width=0.25,
            allowable_crack_width=0.3,
            exposure=ExposureCondition.MODERATE,
        )
        assert result.member_id == "W1"
        assert result.calculated_crack_width == 0.25
        assert result.allowable_crack_width == 0.3
        assert result.exposure == ExposureCondition.MODERATE
        assert result.is_compliant == False  # default
        assert result.note == ""  # default
    
    def test_crack_width_check_result_creation_with_all_fields(self):
        """Test creation with all fields specified."""
        result = CrackWidthCheckResult(
            member_id="W2",
            calculated_crack_width=0.2,
            allowable_crack_width=0.3,
            exposure=ExposureCondition.MILD,
            is_compliant=True,
            note="Crack width acceptable"
        )
        assert result.member_id == "W2"
        assert result.calculated_crack_width == 0.2
        assert result.allowable_crack_width == 0.3
        assert result.exposure == ExposureCondition.MILD
        assert result.is_compliant == True
        assert result.note == "Crack width acceptable"
    
    def test_crack_width_check_result_defaults(self):
        """Test default values are applied correctly."""
        result = CrackWidthCheckResult(
            member_id="W3",
            calculated_crack_width=0.35,
            allowable_crack_width=0.3,
            exposure=ExposureCondition.SEVERE,
        )
        # Defaults should be applied
        assert result.is_compliant == False
        assert result.note == ""
    
    def test_crack_width_check_result_all_exposure_conditions(self):
        """Test with all exposure conditions."""
        # Mild
        result_mild = CrackWidthCheckResult(
            member_id="W_mild",
            calculated_crack_width=0.25,
            allowable_crack_width=0.3,
            exposure=ExposureCondition.MILD,
        )
        assert result_mild.exposure == ExposureCondition.MILD
        assert result_mild.allowable_crack_width == 0.3
        
        # Moderate
        result_moderate = CrackWidthCheckResult(
            member_id="W_moderate",
            calculated_crack_width=0.25,
            allowable_crack_width=0.3,
            exposure=ExposureCondition.MODERATE,
        )
        assert result_moderate.exposure == ExposureCondition.MODERATE
        assert result_moderate.allowable_crack_width == 0.3
        
        # Severe
        result_severe = CrackWidthCheckResult(
            member_id="W_severe",
            calculated_crack_width=0.08,
            allowable_crack_width=0.1,
            exposure=ExposureCondition.SEVERE,
        )
        assert result_severe.exposure == ExposureCondition.SEVERE
        assert result_severe.allowable_crack_width == 0.1
    
    def test_crack_width_check_result_edge_case_zero_width(self):
        """Test with zero crack width edge case."""
        result = CrackWidthCheckResult(
            member_id="W_zero",
            calculated_crack_width=0.0,
            allowable_crack_width=0.3,
            exposure=ExposureCondition.MODERATE,
        )
        assert result.calculated_crack_width == 0.0


class TestDataclassFieldTypes:
    """Test dataclass field types and validation."""
    
    def test_span_depth_check_result_field_types(self):
        """Test field types for SpanDepthCheckResult."""
        result = SpanDepthCheckResult(
            member_id="test",
            actual_ratio=1.0,
            allowable_ratio=2.0,
        )
        assert isinstance(result.member_id, str)
        assert isinstance(result.actual_ratio, float)
        assert isinstance(result.allowable_ratio, float)
        assert isinstance(result.modification_factor, float)
        assert isinstance(result.is_compliant, bool)
        assert isinstance(result.note, str)
    
    def test_deflection_check_result_field_types(self):
        """Test field types for DeflectionCheckResult."""
        result = DeflectionCheckResult(
            member_id="test",
            actual_deflection=1.0,
            allowable_deflection=2.0,
            span_length=1000.0,
            deflection_limit_ratio="L/500",
        )
        assert isinstance(result.member_id, str)
        assert isinstance(result.actual_deflection, float)
        assert isinstance(result.allowable_deflection, float)
        assert isinstance(result.span_length, float)
        assert isinstance(result.deflection_limit_ratio, str)
        assert isinstance(result.is_compliant, bool)
        assert isinstance(result.note, str)
    
    def test_crack_width_check_result_field_types(self):
        """Test field types for CrackWidthCheckResult."""
        result = CrackWidthCheckResult(
            member_id="test",
            calculated_crack_width=0.1,
            allowable_crack_width=0.3,
            exposure=ExposureCondition.MODERATE,
        )
        assert isinstance(result.member_id, str)
        assert isinstance(result.calculated_crack_width, float)
        assert isinstance(result.allowable_crack_width, float)
        assert isinstance(result.exposure, ExposureCondition)
        assert isinstance(result.is_compliant, bool)
        assert isinstance(result.note, str)


class TestEnumComparison:
    """Test enum comparison operations."""
    
    def test_member_type_equality(self):
        """Test MemberType enum equality."""
        assert MemberType.CANTILEVER == MemberType.CANTILEVER
        assert MemberType.CONTINUOUS_BEAM != MemberType.SIMPLY_SUPPORTED_BEAM
    
    def test_exposure_condition_equality(self):
        """Test ExposureCondition enum equality."""
        assert ExposureCondition.MILD == ExposureCondition.MILD
        assert ExposureCondition.MODERATE != ExposureCondition.SEVERE
    
    def test_enum_in_dataclass(self):
        """Test enum usage within dataclass."""
        result = CrackWidthCheckResult(
            member_id="test",
            calculated_crack_width=0.2,
            allowable_crack_width=0.3,
            exposure=ExposureCondition.MODERATE,
        )
        # Should be able to compare enum
        assert result.exposure == ExposureCondition.MODERATE
        assert result.exposure != ExposureCondition.SEVERE


class TestSLSCheckerSpanDepthRatio:
    """Test SLSChecker.check_span_depth_ratio method per HK Code 2013 Cl 7.3.4."""
    
    def test_span_depth_check_init(self):
        """Test SLSChecker initialization has empty results list."""
        checker = SLSChecker()
        assert checker.span_depth_results == []
        assert checker.deflection_results == []
        assert checker.crack_width_results == []
    
    def test_span_depth_ratio_compliant(self):
        """Test span/depth ratio check passes when actual < allowable."""
        checker = SLSChecker()
        result = checker.check_span_depth_ratio(
            member_id="B1",
            span_length=6000.0,  # 6m span
            effective_depth=300.0,  # 300mm depth
            member_type=MemberType.SIMPLY_SUPPORTED_BEAM,
        )
        # Actual L/d = 6000/300 = 20
        # Basic = 20 for simply supported beam
        # Total factor = (500/500) * 1.0 * 1.0 = 1.0
        # Allowable = 20 * 1.0 = 20
        # Compliant since actual (20) == allowable (20)
        assert result.actual_ratio == 20.0
        assert result.allowable_ratio == 20.0
        assert result.modification_factor == 1.0
        assert result.is_compliant == True
    
    def test_span_depth_ratio_non_compliant(self):
        """Test span/depth ratio check fails when actual > allowable."""
        checker = SLSChecker()
        result = checker.check_span_depth_ratio(
            member_id="B2",
            span_length=8000.0,  # 8m span
            effective_depth=300.0,  # 300mm depth
            member_type=MemberType.SIMPLY_SUPPORTED_BEAM,
        )
        # Actual L/d = 8000/300 = 26.67
        # Basic = 20 for simply supported beam
        # Total factor = 1.0
        # Allowable = 20
        # Non-compliant since actual (26.67) > allowable (20)
        assert result.actual_ratio == 8000.0 / 300.0
        assert result.allowable_ratio == 20.0
        assert result.is_compliant == False
    
    def test_span_depth_ratio_cantilever(self):
        """Test cantilever basic ratio = 7 per HK Code Table 7.3."""
        checker = SLSChecker()
        result = checker.check_span_depth_ratio(
            member_id="C1",
            span_length=2100.0,  # 2.1m cantilever
            effective_depth=300.0,  # 300mm depth
            member_type=MemberType.CANTILEVER,
        )
        # Actual L/d = 2100/300 = 7
        # Basic = 7 for cantilever
        # Allowable = 7
        assert result.actual_ratio == 7.0
        assert result.allowable_ratio == 7.0
        assert result.is_compliant == True
    
    def test_span_depth_ratio_continuous_beam(self):
        """Test continuous beam basic ratio = 26 per HK Code Table 7.3."""
        checker = SLSChecker()
        result = checker.check_span_depth_ratio(
            member_id="B3",
            span_length=7800.0,  # 7.8m span
            effective_depth=300.0,  # 300mm depth
            member_type=MemberType.CONTINUOUS_BEAM,
        )
        # Actual L/d = 7800/300 = 26
        # Basic = 26 for continuous beam
        # Allowable = 26
        assert result.actual_ratio == 26.0
        assert result.allowable_ratio == 26.0
        assert result.is_compliant == True
    
    def test_span_depth_ratio_one_way_slab(self):
        """Test one-way slab basic ratio = 30 per HK Code Table 7.3."""
        checker = SLSChecker()
        result = checker.check_span_depth_ratio(
            member_id="S1",
            span_length=4500.0,  # 4.5m span
            effective_depth=150.0,  # 150mm depth
            member_type=MemberType.ONE_WAY_SLAB,
        )
        # Actual L/d = 4500/150 = 30
        # Basic = 30 for one-way slab
        # Allowable = 30
        assert result.actual_ratio == 30.0
        assert result.allowable_ratio == 30.0
        assert result.is_compliant == True
    
    def test_span_depth_ratio_two_way_slab_restrained(self):
        """Test two-way slab restrained basic ratio = 48 per HK Code Table 7.3."""
        checker = SLSChecker()
        result = checker.check_span_depth_ratio(
            member_id="S2",
            span_length=7200.0,  # 7.2m span
            effective_depth=150.0,  # 150mm depth
            member_type=MemberType.TWO_WAY_SLAB_RESTRAINED,
        )
        # Actual L/d = 7200/150 = 48
        # Basic = 48 for two-way slab restrained
        # Allowable = 48
        assert result.actual_ratio == 48.0
        assert result.allowable_ratio == 48.0
        assert result.is_compliant == True
    
    def test_span_depth_ratio_tension_factor(self):
        """Test tension factor modification when steel_stress < 500 MPa."""
        checker = SLSChecker()
        result = checker.check_span_depth_ratio(
            member_id="B4",
            span_length=8000.0,  # 8m span
            effective_depth=300.0,  # 300mm depth
            member_type=MemberType.SIMPLY_SUPPORTED_BEAM,
            steel_stress=250.0,  # Low steel stress increases allowable
        )
        # Actual L/d = 8000/300 = 26.67
        # Basic = 20
        # Tension factor = 500/250 = 2.0
        # Total factor = 2.0 * 1.0 * 1.0 = 2.0
        # Allowable = 20 * 2.0 = 40
        # Compliant since actual (26.67) < allowable (40)
        assert result.actual_ratio == 8000.0 / 300.0
        assert result.modification_factor == 2.0
        assert result.allowable_ratio == 40.0
        assert result.is_compliant == True
    
    def test_span_depth_ratio_tension_factor_high_stress(self):
        """Test tension factor modification when steel_stress > 500 MPa."""
        checker = SLSChecker()
        result = checker.check_span_depth_ratio(
            member_id="B5",
            span_length=6000.0,  # 6m span
            effective_depth=300.0,  # 300mm depth
            member_type=MemberType.SIMPLY_SUPPORTED_BEAM,
            steel_stress=600.0,  # High steel stress reduces allowable
        )
        # Actual L/d = 6000/300 = 20
        # Basic = 20
        # Tension factor = 500/600 = 0.833
        # Total factor = 0.833
        # Allowable = 20 * 0.833 = 16.67
        # Non-compliant since actual (20) > allowable (16.67)
        tension_factor = 500.0 / 600.0
        assert result.actual_ratio == 20.0
        assert result.modification_factor == tension_factor
        assert result.allowable_ratio == 20.0 * tension_factor
        assert result.is_compliant == False
    
    def test_span_depth_ratio_compression_factor(self):
        """Test compression reinforcement factor modification."""
        checker = SLSChecker()
        result = checker.check_span_depth_ratio(
            member_id="B6",
            span_length=8400.0,  # 8.4m span
            effective_depth=300.0,  # 300mm depth
            member_type=MemberType.SIMPLY_SUPPORTED_BEAM,
            compression_reinf_ratio=0.30,  # 30% compression reinforcement
        )
        # Actual L/d = 8400/300 = 28
        # Basic = 20
        # Tension factor = 1.0
        # Compression factor = 1 + (0.30 / 3) = 1.1
        # Total factor = 1.0 * 1.1 * 1.0 = 1.1
        # Allowable = 20 * 1.1 = 22
        # Non-compliant since actual (28) > allowable (22)
        compression_factor = 1.0 + (0.30 / 3.0)
        assert result.actual_ratio == 28.0
        assert result.modification_factor == compression_factor
        assert result.allowable_ratio == 20.0 * compression_factor
        assert result.is_compliant == False
    
    def test_span_depth_ratio_long_span_factor(self):
        """Test long span (>10m) reduction factor per HK Code Cl 7.3.4.2."""
        checker = SLSChecker()
        result = checker.check_span_depth_ratio(
            member_id="B7",
            span_length=12000.0,  # 12m span (> 10m)
            effective_depth=600.0,  # 600mm depth
            member_type=MemberType.CONTINUOUS_BEAM,
            span_gt_10m=True,
        )
        # Actual L/d = 12000/600 = 20
        # Basic = 26
        # Tension factor = 1.0
        # Compression factor = 1.0
        # Long span factor = 10 / (12000/1000) = 10/12 = 0.833
        # Total factor = 1.0 * 1.0 * 0.833 = 0.833
        # Allowable = 26 * 0.833 = 21.67
        # Compliant since actual (20) < allowable (21.67)
        long_span_factor = 10.0 / 12.0
        assert result.actual_ratio == 20.0
        assert abs(result.modification_factor - long_span_factor) < 0.001
        assert abs(result.allowable_ratio - 26.0 * long_span_factor) < 0.01
        assert result.is_compliant == True
    
    def test_span_depth_ratio_combined_factors(self):
        """Test combined modification factors."""
        checker = SLSChecker()
        result = checker.check_span_depth_ratio(
            member_id="B8",
            span_length=12000.0,  # 12m span
            effective_depth=400.0,  # 400mm depth
            member_type=MemberType.CONTINUOUS_BEAM,
            steel_stress=400.0,  # Low stress
            compression_reinf_ratio=0.15,  # Some compression reinforcement
            span_gt_10m=True,
        )
        # Actual L/d = 12000/400 = 30
        # Basic = 26
        # Tension factor = 500/400 = 1.25
        # Compression factor = 1 + (0.15 / 3) = 1.05
        # Long span factor = 10/12 = 0.833
        # Total factor = 1.25 * 1.05 * 0.833 = 1.093
        # Allowable = 26 * 1.093 = 28.42
        # Non-compliant since actual (30) > allowable (28.42)
        tension_factor = 500.0 / 400.0
        compression_factor = 1.0 + (0.15 / 3.0)
        long_span_factor = 10.0 / 12.0
        total_factor = tension_factor * compression_factor * long_span_factor
        
        assert result.actual_ratio == 30.0
        assert abs(result.modification_factor - total_factor) < 0.001
        assert abs(result.allowable_ratio - 26.0 * total_factor) < 0.01
        assert result.is_compliant == False
    
    def test_span_depth_ratio_result_stored(self):
        """Test that result is added to span_depth_results list."""
        checker = SLSChecker()
        
        # Initially empty
        assert len(checker.span_depth_results) == 0
        
        # Add first check
        result1 = checker.check_span_depth_ratio(
            member_id="B1",
            span_length=6000.0,
            effective_depth=300.0,
            member_type=MemberType.SIMPLY_SUPPORTED_BEAM,
        )
        assert len(checker.span_depth_results) == 1
        assert checker.span_depth_results[0] == result1
        
        # Add second check
        result2 = checker.check_span_depth_ratio(
            member_id="B2",
            span_length=8000.0,
            effective_depth=300.0,
            member_type=MemberType.CONTINUOUS_BEAM,
        )
        assert len(checker.span_depth_results) == 2
        assert checker.span_depth_results[0] == result1
        assert checker.span_depth_results[1] == result2
    
    def test_span_depth_ratio_zero_depth_edge_case(self):
        """Test edge case with zero effective depth."""
        checker = SLSChecker()
        result = checker.check_span_depth_ratio(
            member_id="B_zero",
            span_length=6000.0,
            effective_depth=0.0,  # Zero depth
            member_type=MemberType.SIMPLY_SUPPORTED_BEAM,
        )
        # Should handle division by zero gracefully
        assert result.actual_ratio == 0.0
        assert result.is_compliant == True  # 0 <= allowable
    
    def test_span_depth_ratio_note_field(self):
        """Test that note field contains calculation details."""
        checker = SLSChecker()
        result = checker.check_span_depth_ratio(
            member_id="B9",
            span_length=6000.0,
            effective_depth=300.0,
            member_type=MemberType.SIMPLY_SUPPORTED_BEAM,
            steel_stress=450.0,
        )
        # Note should contain modification factors
        assert "Basic L/d = 20" in result.note
        assert "Tension factor" in result.note
        assert "Compression factor" in result.note
        assert "Long span factor" in result.note
    
    def test_span_depth_ratio_all_member_types(self):
        """Test all member types have basic ratios defined."""
        checker = SLSChecker()
        
        member_types_and_expected_basic = [
            (MemberType.CANTILEVER, 7.0),
            (MemberType.SIMPLY_SUPPORTED_BEAM, 20.0),
            (MemberType.CONTINUOUS_BEAM, 26.0),
            (MemberType.RECTANGULAR_FLANGED_BEAM, 20.0),
            (MemberType.T_BEAM, 26.0),
            (MemberType.ONE_WAY_SLAB, 30.0),
            (MemberType.TWO_WAY_SLAB_RESTRAINED, 48.0),
            (MemberType.TWO_WAY_SLAB_SIMPLE, 40.0),
        ]
        
        for member_type, expected_basic in member_types_and_expected_basic:
            result = checker.check_span_depth_ratio(
                member_id=f"test_{member_type.value}",
                span_length=1000.0,
                effective_depth=1000.0,  # L/d = 1
                member_type=member_type,
            )
            # Actual L/d = 1, so allowable should equal basic ratio
            assert result.allowable_ratio == expected_basic


class TestSLSCheckerDeflection:
    """Test SLSChecker.check_deflection method per HK Code 2013 Cl 7.3.2-7.3.3."""
    
    def test_deflection_check_compliant(self):
        """Test deflection check passes when deflection under limit."""
        checker = SLSChecker()
        result = checker.check_deflection(
            member_id="B1",
            actual_deflection=8.0,  # 8mm immediate deflection
            span_length=5000.0,  # 5m span
            deflection_type="post_construction",
            creep_factor=1.0,  # No creep for simplicity
        )
        # Allowable = min(5000/500, 20) = min(10, 20) = 10mm
        # Actual with creep = 8.0 * 1.0 = 8mm
        # Compliant since 8mm < 10mm
        assert result.actual_deflection == 8.0
        assert result.allowable_deflection == 10.0
        assert result.is_compliant == True
    
    def test_deflection_check_non_compliant(self):
        """Test deflection check fails when deflection over limit."""
        checker = SLSChecker()
        result = checker.check_deflection(
            member_id="B2",
            actual_deflection=15.0,  # 15mm immediate deflection
            span_length=5000.0,  # 5m span
            deflection_type="post_construction",
            creep_factor=1.0,
        )
        # Allowable = min(5000/500, 20) = 10mm
        # Actual with creep = 15.0 * 1.0 = 15mm
        # Non-compliant since 15mm > 10mm
        assert result.actual_deflection == 15.0
        assert result.allowable_deflection == 10.0
        assert result.is_compliant == False
    
    def test_deflection_type_post_construction(self):
        """Test post-construction deflection limit L/500 per HK Code Cl 7.3.2."""
        checker = SLSChecker()
        result = checker.check_deflection(
            member_id="B3",
            actual_deflection=8.0,  # 8mm
            span_length=5000.0,  # 5m = 5000mm
            deflection_type="post_construction",
            creep_factor=1.0,
        )
        # Allowable = min(5000/500, 20) = min(10, 20) = 10mm
        assert result.deflection_limit_ratio == "L/500"
        assert result.allowable_deflection == 10.0
        assert result.is_compliant == True  # 8mm < 10mm
    
    def test_deflection_type_partition(self):
        """Test partition deflection limit L/350 per HK Code Cl 7.3.2."""
        checker = SLSChecker()
        result = checker.check_deflection(
            member_id="B4",
            actual_deflection=12.0,  # 12mm
            span_length=5000.0,  # 5m = 5000mm
            deflection_type="partition",
            creep_factor=1.0,
        )
        # Allowable = 5000/350 = 14.29mm
        assert result.deflection_limit_ratio == "L/350"
        assert abs(result.allowable_deflection - 5000.0/350.0) < 0.01
        assert result.is_compliant == True  # 12mm < 14.29mm
    
    def test_deflection_type_total(self):
        """Test total deflection limit L/250 per HK Code Cl 7.3.2 (default)."""
        checker = SLSChecker()
        result = checker.check_deflection(
            member_id="B5",
            actual_deflection=18.0,  # 18mm
            span_length=5000.0,  # 5m = 5000mm
            deflection_type="total",
            creep_factor=1.0,
        )
        # Allowable = 5000/250 = 20mm
        assert result.deflection_limit_ratio == "L/250"
        assert result.allowable_deflection == 20.0
        assert result.is_compliant == True  # 18mm < 20mm
    
    def test_deflection_type_default(self):
        """Test default deflection type is 'total' (L/250)."""
        checker = SLSChecker()
        result = checker.check_deflection(
            member_id="B6",
            actual_deflection=15.0,
            span_length=5000.0,
        )
        # Default should be "total" = L/250
        assert result.deflection_limit_ratio == "L/250"
        assert result.allowable_deflection == 20.0
    
    def test_deflection_post_construction_max_20mm(self):
        """Test post-construction deflection capped at 20mm per HK Code Cl 7.3.2."""
        checker = SLSChecker()
        result = checker.check_deflection(
            member_id="B7",
            actual_deflection=18.0,  # 18mm
            span_length=15000.0,  # 15m = 15000mm (large span)
            deflection_type="post_construction",
            creep_factor=1.0,
        )
        # L/500 = 15000/500 = 30mm
        # But capped at 20mm per code
        # Allowable = min(30, 20) = 20mm
        assert result.deflection_limit_ratio == "L/500"
        assert result.allowable_deflection == 20.0  # Capped at 20mm
        assert result.is_compliant == True  # 18mm < 20mm
    
    def test_deflection_post_construction_no_cap_small_span(self):
        """Test post-construction deflection not capped for small spans."""
        checker = SLSChecker()
        result = checker.check_deflection(
            member_id="B8",
            actual_deflection=5.0,  # 5mm
            span_length=3000.0,  # 3m = 3000mm (small span)
            deflection_type="post_construction",
            creep_factor=1.0,
        )
        # L/500 = 3000/500 = 6mm
        # min(6, 20) = 6mm (not capped)
        assert result.deflection_limit_ratio == "L/500"
        assert result.allowable_deflection == 6.0
        assert result.is_compliant == True  # 5mm < 6mm
    
    def test_deflection_creep_factor_applied(self):
        """Test creep factor multiplier per HK Code Cl 7.3.3."""
        checker = SLSChecker()
        result = checker.check_deflection(
            member_id="B9",
            actual_deflection=5.0,  # 5mm immediate
            span_length=5000.0,  # 5m
            deflection_type="post_construction",
            creep_factor=2.0,  # Long-term creep factor
        )
        # Immediate = 5mm
        # With creep = 5 * 2.0 = 10mm
        # Allowable = min(5000/500, 20) = 10mm
        # Compliant since 10mm == 10mm
        assert result.actual_deflection == 10.0  # After creep
        assert result.allowable_deflection == 10.0
        assert result.is_compliant == True
    
    def test_deflection_creep_factor_causes_failure(self):
        """Test creep factor can cause non-compliance."""
        checker = SLSChecker()
        result = checker.check_deflection(
            member_id="B10",
            actual_deflection=6.0,  # 6mm immediate
            span_length=5000.0,  # 5m
            deflection_type="post_construction",
            creep_factor=2.5,  # High creep factor
        )
        # Immediate = 6mm
        # With creep = 6 * 2.5 = 15mm
        # Allowable = min(5000/500, 20) = 10mm
        # Non-compliant since 15mm > 10mm
        assert result.actual_deflection == 15.0  # After creep
        assert result.allowable_deflection == 10.0
        assert result.is_compliant == False
    
    def test_deflection_creep_factor_default(self):
        """Test default creep factor is 1.0."""
        checker = SLSChecker()
        result = checker.check_deflection(
            member_id="B11",
            actual_deflection=8.0,
            span_length=5000.0,
            deflection_type="post_construction",
            # creep_factor not specified
        )
        # Default creep_factor should be 1.0
        # Actual with creep = 8 * 1.0 = 8mm
        assert result.actual_deflection == 8.0
    
    def test_deflection_result_stored(self):
        """Test that result is added to deflection_results list."""
        checker = SLSChecker()
        
        # Initially empty
        assert len(checker.deflection_results) == 0
        
        # Add first check
        result1 = checker.check_deflection(
            member_id="B1",
            actual_deflection=8.0,
            span_length=5000.0,
            deflection_type="post_construction",
        )
        assert len(checker.deflection_results) == 1
        assert checker.deflection_results[0] == result1
        
        # Add second check
        result2 = checker.check_deflection(
            member_id="B2",
            actual_deflection=12.0,
            span_length=6000.0,
            deflection_type="partition",
        )
        assert len(checker.deflection_results) == 2
        assert checker.deflection_results[0] == result1
        assert checker.deflection_results[1] == result2
    
    def test_deflection_note_field(self):
        """Test that note field contains calculation details."""
        checker = SLSChecker()
        result = checker.check_deflection(
            member_id="B12",
            actual_deflection=5.0,
            span_length=5000.0,
            deflection_type="post_construction",
            creep_factor=2.5,
        )
        # Note should contain deflection breakdown
        assert "Immediate deflection = 5.00 mm" in result.note
        assert "Creep factor = 2.50" in result.note
        assert "Long-term deflection" in result.note
    
    def test_deflection_partition_vs_total(self):
        """Test partition limit is stricter than total limit."""
        checker = SLSChecker()
        span = 7000.0  # 7m
        
        # Partition: L/350
        result_partition = checker.check_deflection(
            member_id="partition",
            actual_deflection=15.0,
            span_length=span,
            deflection_type="partition",
            creep_factor=1.0,
        )
        
        # Total: L/250
        result_total = checker.check_deflection(
            member_id="total",
            actual_deflection=15.0,
            span_length=span,
            deflection_type="total",
            creep_factor=1.0,
        )
        
        # Partition limit (L/350 = 20mm) < Total limit (L/250 = 28mm)
        assert result_partition.allowable_deflection < result_total.allowable_deflection
        assert result_partition.allowable_deflection == 7000.0 / 350.0
        assert result_total.allowable_deflection == 7000.0 / 250.0
    
    def test_deflection_all_limit_types(self):
        """Test all three deflection limit types."""
        checker = SLSChecker()
        span = 10000.0  # 10m
        
        # Post-construction: L/500 (max 20mm)
        result_post = checker.check_deflection(
            member_id="post",
            actual_deflection=15.0,
            span_length=span,
            deflection_type="post_construction",
            creep_factor=1.0,
        )
        assert result_post.deflection_limit_ratio == "L/500"
        assert result_post.allowable_deflection == 20.0  # min(10000/500, 20) = 20
        
        # Partition: L/350
        result_partition = checker.check_deflection(
            member_id="partition",
            actual_deflection=25.0,
            span_length=span,
            deflection_type="partition",
            creep_factor=1.0,
        )
        assert result_partition.deflection_limit_ratio == "L/350"
        assert abs(result_partition.allowable_deflection - 10000.0/350.0) < 0.01
        
        # Total: L/250
        result_total = checker.check_deflection(
            member_id="total",
            actual_deflection=35.0,
            span_length=span,
            deflection_type="total",
            creep_factor=1.0,
        )
        assert result_total.deflection_limit_ratio == "L/250"
        assert result_total.allowable_deflection == 40.0  # 10000/250
    
    def test_deflection_edge_case_zero_deflection(self):
        """Test edge case with zero deflection."""
        checker = SLSChecker()
        result = checker.check_deflection(
            member_id="B_zero",
            actual_deflection=0.0,
            span_length=5000.0,
            deflection_type="total",
            creep_factor=2.0,
        )
        # 0 * 2.0 = 0mm
        # Always compliant
        assert result.actual_deflection == 0.0
        assert result.is_compliant == True
    
    def test_deflection_high_creep_factor(self):
        """Test with realistic long-term creep factor (3.0)."""
        checker = SLSChecker()
        result = checker.check_deflection(
            member_id="B_creep",
            actual_deflection=5.0,  # 5mm immediate
            span_length=8000.0,  # 8m
            deflection_type="total",
            creep_factor=3.0,  # Typical long-term value per HK Code Cl 3.1.8
        )
        # Immediate = 5mm
        # Long-term = 5 * 3.0 = 15mm
        # Allowable = 8000/250 = 32mm
        # Compliant
        assert result.actual_deflection == 15.0
        assert result.allowable_deflection == 32.0
        assert result.is_compliant == True


class TestSLSCheckerCrackWidth:
    """Test SLSChecker.check_crack_width method per HK Code 2013 Cl 7.2."""
    
    def test_crack_width_compliant(self):
        """Test crack width check passes when under limit."""
        checker = SLSChecker()
        result = checker.check_crack_width(
            member_id="W1",
            steel_strain=0.0008,  # 0.08% strain
            bar_spacing=150.0,  # 150mm spacing
            concrete_cover=40.0,  # 40mm cover
            exposure=ExposureCondition.MODERATE,
        )
        # w_k should be less than 0.3mm for moderate exposure
        assert result.calculated_crack_width < 0.3
        assert result.allowable_crack_width == 0.3
        assert result.is_compliant == True
    
    def test_crack_width_non_compliant(self):
        """Test crack width check fails when over limit."""
        checker = SLSChecker()
        result = checker.check_crack_width(
            member_id="W2",
            steel_strain=0.003,  # 0.3% high strain
            bar_spacing=250.0,  # 250mm wide spacing
            concrete_cover=80.0,  # 80mm thick cover
            exposure=ExposureCondition.MODERATE,
        )
        # High strain + wide spacing + thick cover = large crack width
        # Should exceed 0.3mm limit
        assert result.calculated_crack_width > 0.3
        assert result.allowable_crack_width == 0.3
        assert result.is_compliant == False
    
    def test_crack_width_mild_exposure(self):
        """Test mild exposure allowable crack width = 0.3mm per HK Code Table 7.1."""
        checker = SLSChecker()
        result = checker.check_crack_width(
            member_id="W_mild",
            steel_strain=0.001,
            bar_spacing=150.0,
            concrete_cover=40.0,
            exposure=ExposureCondition.MILD,
        )
        assert result.exposure == ExposureCondition.MILD
        assert result.allowable_crack_width == 0.3
    
    def test_crack_width_moderate_exposure(self):
        """Test moderate exposure allowable crack width = 0.3mm per HK Code Table 7.1."""
        checker = SLSChecker()
        result = checker.check_crack_width(
            member_id="W_moderate",
            steel_strain=0.001,
            bar_spacing=150.0,
            concrete_cover=40.0,
            exposure=ExposureCondition.MODERATE,
        )
        assert result.exposure == ExposureCondition.MODERATE
        assert result.allowable_crack_width == 0.3
    
    def test_crack_width_severe_exposure(self):
        """Test severe exposure allowable crack width = 0.1mm per HK Code Table 7.1."""
        checker = SLSChecker()
        result = checker.check_crack_width(
            member_id="W_severe",
            steel_strain=0.001,
            bar_spacing=150.0,
            concrete_cover=40.0,
            exposure=ExposureCondition.SEVERE,
        )
        assert result.exposure == ExposureCondition.SEVERE
        assert result.allowable_crack_width == 0.1  # Stricter limit
    
    def test_crack_width_calculation(self):
        """Test crack width calculation formula per HK Code Cl 7.2.4."""
        checker = SLSChecker()
        result = checker.check_crack_width(
            member_id="B1",
            steel_strain=0.001,  # 0.1% strain
            bar_spacing=150.0,  # 150mm spacing
            concrete_cover=40.0,  # 40mm cover
            exposure=ExposureCondition.MODERATE,
        )
        # s_rm = 3.4 * 40 + 0.17 * 150 = 136 + 25.5 = 161.5mm
        # w_k = 1.7 * 161.5 * 0.001 = 0.2745mm
        expected_s_rm = 3.4 * 40.0 + 0.17 * 150.0
        expected_w_k = 1.7 * expected_s_rm * 0.001
        
        assert abs(result.calculated_crack_width - expected_w_k) < 0.001
        assert abs(result.calculated_crack_width - 0.2745) < 0.01
        assert result.is_compliant == True  # 0.2745 < 0.3
    
    def test_crack_width_calculation_severe_limit(self):
        """Test same crack width fails severe exposure limit."""
        checker = SLSChecker()
        result = checker.check_crack_width(
            member_id="B2",
            steel_strain=0.001,  # Same as above
            bar_spacing=150.0,
            concrete_cover=40.0,
            exposure=ExposureCondition.SEVERE,  # But severe exposure
        )
        # Same w_k = 0.2745mm
        # But allowable = 0.1mm for severe
        assert abs(result.calculated_crack_width - 0.2745) < 0.01
        assert result.allowable_crack_width == 0.1
        assert result.is_compliant == False  # 0.2745 > 0.1
    
    def test_crack_width_mean_crack_spacing_formula(self):
        """Test mean crack spacing s_rm calculation per HK Code Cl 7.2.4.2."""
        checker = SLSChecker()
        
        # Test with different cover and spacing values
        result = checker.check_crack_width(
            member_id="W3",
            steel_strain=0.0005,  # Low strain to stay compliant
            bar_spacing=200.0,  # 200mm spacing
            concrete_cover=50.0,  # 50mm cover
            exposure=ExposureCondition.MODERATE,
        )
        # s_rm = 3.4 * 50 + 0.17 * 200 = 170 + 34 = 204mm
        # w_k = 1.7 * 204 * 0.0005 = 0.1734mm
        expected_s_rm = 3.4 * 50.0 + 0.17 * 200.0
        expected_w_k = 1.7 * expected_s_rm * 0.0005
        
        assert abs(result.calculated_crack_width - expected_w_k) < 0.001
        assert abs(result.calculated_crack_width - 0.1734) < 0.01
    
    def test_crack_width_beta_coefficient(self):
        """Test beta coefficient = 1.7 per HK Code Cl 7.2.4."""
        checker = SLSChecker()
        result = checker.check_crack_width(
            member_id="W4",
            steel_strain=0.002,
            bar_spacing=100.0,
            concrete_cover=30.0,
            exposure=ExposureCondition.MODERATE,
        )
        # s_rm = 3.4 * 30 + 0.17 * 100 = 102 + 17 = 119mm
        # w_k = 1.7 * 119 * 0.002 = 0.4046mm (beta = 1.7)
        expected_w_k = 1.7 * (3.4 * 30 + 0.17 * 100) * 0.002
        
        assert abs(result.calculated_crack_width - expected_w_k) < 0.001
        assert abs(result.calculated_crack_width - 0.4046) < 0.01
    
    def test_crack_width_result_stored(self):
        """Test that result is added to crack_width_results list."""
        checker = SLSChecker()
        
        # Initially empty
        assert len(checker.crack_width_results) == 0
        
        # Add first check
        result1 = checker.check_crack_width(
            member_id="W1",
            steel_strain=0.001,
            bar_spacing=150.0,
            concrete_cover=40.0,
            exposure=ExposureCondition.MODERATE,
        )
        assert len(checker.crack_width_results) == 1
        assert checker.crack_width_results[0] == result1
        
        # Add second check
        result2 = checker.check_crack_width(
            member_id="W2",
            steel_strain=0.0008,
            bar_spacing=120.0,
            concrete_cover=35.0,
            exposure=ExposureCondition.MILD,
        )
        assert len(checker.crack_width_results) == 2
        assert checker.crack_width_results[0] == result1
        assert checker.crack_width_results[1] == result2
    
    def test_crack_width_note_field(self):
        """Test that note field contains calculation details."""
        checker = SLSChecker()
        result = checker.check_crack_width(
            member_id="W5",
            steel_strain=0.0012,
            bar_spacing=150.0,
            concrete_cover=40.0,
            exposure=ExposureCondition.MODERATE,
        )
        # Note should contain calculation details
        assert "Mean crack spacing s_rm" in result.note
        assert "Steel strain" in result.note
        assert "0.001200" in result.note  # Strain value
        assert "Calculated w_k" in result.note
    
    def test_crack_width_all_exposure_conditions(self):
        """Test all three exposure conditions with same crack width."""
        checker = SLSChecker()
        
        # Same parameters for all
        strain = 0.00075
        spacing = 150.0
        cover = 40.0
        
        # Mild: w_max = 0.3mm
        result_mild = checker.check_crack_width(
            member_id="mild",
            steel_strain=strain,
            bar_spacing=spacing,
            concrete_cover=cover,
            exposure=ExposureCondition.MILD,
        )
        
        # Moderate: w_max = 0.3mm
        result_moderate = checker.check_crack_width(
            member_id="moderate",
            steel_strain=strain,
            bar_spacing=spacing,
            concrete_cover=cover,
            exposure=ExposureCondition.MODERATE,
        )
        
        # Severe: w_max = 0.1mm
        result_severe = checker.check_crack_width(
            member_id="severe",
            steel_strain=strain,
            bar_spacing=spacing,
            concrete_cover=cover,
            exposure=ExposureCondition.SEVERE,
        )
        
        # All should have same calculated crack width
        assert abs(result_mild.calculated_crack_width - result_moderate.calculated_crack_width) < 0.0001
        assert abs(result_mild.calculated_crack_width - result_severe.calculated_crack_width) < 0.0001
        
        # But different allowable limits
        assert result_mild.allowable_crack_width == 0.3
        assert result_moderate.allowable_crack_width == 0.3
        assert result_severe.allowable_crack_width == 0.1
        
        # w_k = 1.7 * (3.4*40 + 0.17*150) * 0.00075 ≈ 0.206mm
        # Mild/Moderate should pass (0.206 < 0.3)
        # Severe should fail (0.206 > 0.1)
        assert result_mild.is_compliant == True
        assert result_moderate.is_compliant == True
        assert result_severe.is_compliant == False
    
    def test_crack_width_bar_diameter_parameter(self):
        """Test bar_diameter parameter (currently not used in simplified formula)."""
        checker = SLSChecker()
        result = checker.check_crack_width(
            member_id="W6",
            steel_strain=0.001,
            bar_spacing=150.0,
            concrete_cover=40.0,
            exposure=ExposureCondition.MODERATE,
            bar_diameter=20.0,  # Specify bar diameter
        )
        # Formula doesn't use bar_diameter in simplified version
        # But should accept parameter without error
        assert result.calculated_crack_width > 0
        assert result.is_compliant in [True, False]
    
    def test_crack_width_effect_of_cover(self):
        """Test effect of concrete cover on crack width."""
        checker = SLSChecker()
        
        # Small cover
        result_small_cover = checker.check_crack_width(
            member_id="W_small",
            steel_strain=0.001,
            bar_spacing=150.0,
            concrete_cover=25.0,  # Small cover
            exposure=ExposureCondition.MODERATE,
        )
        
        # Large cover
        result_large_cover = checker.check_crack_width(
            member_id="W_large",
            steel_strain=0.001,
            bar_spacing=150.0,
            concrete_cover=60.0,  # Large cover
            exposure=ExposureCondition.MODERATE,
        )
        
        # Larger cover increases s_rm, thus increases w_k
        assert result_large_cover.calculated_crack_width > result_small_cover.calculated_crack_width
    
    def test_crack_width_effect_of_spacing(self):
        """Test effect of bar spacing on crack width."""
        checker = SLSChecker()
        
        # Small spacing
        result_small_spacing = checker.check_crack_width(
            member_id="W_tight",
            steel_strain=0.001,
            bar_spacing=100.0,  # Tight spacing
            concrete_cover=40.0,
            exposure=ExposureCondition.MODERATE,
        )
        
        # Large spacing
        result_large_spacing = checker.check_crack_width(
            member_id="W_wide",
            steel_strain=0.001,
            bar_spacing=250.0,  # Wide spacing
            concrete_cover=40.0,
            exposure=ExposureCondition.MODERATE,
        )
        
        # Larger spacing increases s_rm, thus increases w_k
        assert result_large_spacing.calculated_crack_width > result_small_spacing.calculated_crack_width
    
    def test_crack_width_effect_of_strain(self):
        """Test effect of steel strain on crack width."""
        checker = SLSChecker()
        
        # Low strain
        result_low_strain = checker.check_crack_width(
            member_id="W_low",
            steel_strain=0.0005,  # Low strain
            bar_spacing=150.0,
            concrete_cover=40.0,
            exposure=ExposureCondition.MODERATE,
        )
        
        # High strain
        result_high_strain = checker.check_crack_width(
            member_id="W_high",
            steel_strain=0.002,  # High strain
            bar_spacing=150.0,
            concrete_cover=40.0,
            exposure=ExposureCondition.MODERATE,
        )
        
        # Higher strain directly increases w_k
        assert result_high_strain.calculated_crack_width > result_low_strain.calculated_crack_width
        # Should be proportional (4x strain = 4x crack width)
        ratio = result_high_strain.calculated_crack_width / result_low_strain.calculated_crack_width
        assert abs(ratio - 4.0) < 0.01
    
    def test_crack_width_edge_case_zero_strain(self):
        """Test edge case with zero steel strain."""
        checker = SLSChecker()
        result = checker.check_crack_width(
            member_id="W_zero",
            steel_strain=0.0,  # No strain
            bar_spacing=150.0,
            concrete_cover=40.0,
            exposure=ExposureCondition.MODERATE,
        )
        # Zero strain should give zero crack width
        assert result.calculated_crack_width == 0.0
        assert result.is_compliant == True
    
    def test_crack_width_realistic_values(self):
        """Test with realistic design values."""
        checker = SLSChecker()
        result = checker.check_crack_width(
            member_id="W_realistic",
            steel_strain=0.00085,  # Typical service strain (fy/Es ≈ 460/200000)
            bar_spacing=175.0,  # Typical spacing
            concrete_cover=50.0,  # Typical cover to HK Code
            exposure=ExposureCondition.MODERATE,
        )
        # s_rm = 3.4 * 50 + 0.17 * 175 = 170 + 29.75 = 199.75mm
        # w_k = 1.7 * 199.75 * 0.00085 = 0.2886mm
        expected_w_k = 1.7 * (3.4 * 50 + 0.17 * 175) * 0.00085
        
        assert abs(result.calculated_crack_width - expected_w_k) < 0.001
        assert result.calculated_crack_width < 0.3
        assert result.is_compliant == True


class TestSLSCheckerSummaryReport:
    """Test SLSChecker.get_summary_report method."""
    
    def test_summary_report_empty(self):
        """Test empty checker produces header-only report."""
        checker = SLSChecker()
        report = checker.get_summary_report()
        
        # Should contain main header
        assert "=" * 80 in report
        assert "SERVICEABILITY LIMIT STATE (SLS) CHECKS SUMMARY" in report
        
        # Should show zero checks for all sections
        assert "SPAN/DEPTH RATIO CHECKS" in report
        assert "DEFLECTION CHECKS" in report
        assert "CRACK WIDTH CHECKS" in report
        assert "Total members checked: 0" in report
    
    def test_summary_report_with_span_depth_results(self):
        """Test summary report with span/depth ratio checks."""
        checker = SLSChecker()
        
        # Add passing check
        checker.check_span_depth_ratio(
            member_id="B1",
            span_length=6000.0,
            effective_depth=300.0,
            member_type=MemberType.SIMPLY_SUPPORTED_BEAM,
        )
        
        report = checker.get_summary_report()
        
        # Should show span/depth section
        assert "SPAN/DEPTH RATIO CHECKS (HK Code Cl 7.3.4, Table 7.3):" in report
        assert "Total members checked: 1" in report
        assert "Compliant: 1/1" in report
        assert "B1" in report
        assert "PASS" in report
    
    def test_summary_report_with_span_depth_fail(self):
        """Test summary report with failing span/depth ratio check."""
        checker = SLSChecker()
        
        # Add failing check
        checker.check_span_depth_ratio(
            member_id="B_fail",
            span_length=10000.0,  # Excessive span
            effective_depth=300.0,
            member_type=MemberType.SIMPLY_SUPPORTED_BEAM,
        )
        
        report = checker.get_summary_report()
        
        assert "Total members checked: 1" in report
        assert "Compliant: 0/1" in report  # None compliant
        assert "B_fail" in report
        assert "FAIL" in report
    
    def test_summary_report_with_deflection_results(self):
        """Test summary report with deflection checks."""
        checker = SLSChecker()
        
        # Add passing deflection check
        checker.check_deflection(
            member_id="S1",
            actual_deflection=8.0,
            span_length=5000.0,
            deflection_type="post_construction",
        )
        
        report = checker.get_summary_report()
        
        # Should show deflection section
        assert "DEFLECTION CHECKS (HK Code Cl 7.3.2-7.3.3):" in report
        assert "Total members checked: 1" in report
        assert "Compliant: 1/1" in report
        assert "S1" in report
        assert "L/500" in report
        assert "PASS" in report
    
    def test_summary_report_with_deflection_fail(self):
        """Test summary report with failing deflection check."""
        checker = SLSChecker()
        
        # Add failing deflection check
        checker.check_deflection(
            member_id="S_fail",
            actual_deflection=25.0,  # Excessive deflection
            span_length=5000.0,
            deflection_type="post_construction",
        )
        
        report = checker.get_summary_report()
        
        assert "Compliant: 0/1" in report
        assert "S_fail" in report
        assert "FAIL" in report
    
    def test_summary_report_with_crack_width_results(self):
        """Test summary report with crack width checks."""
        checker = SLSChecker()
        
        # Add passing crack width check
        checker.check_crack_width(
            member_id="W1",
            steel_strain=0.0008,
            bar_spacing=150.0,
            concrete_cover=40.0,
            exposure=ExposureCondition.MODERATE,
        )
        
        report = checker.get_summary_report()
        
        # Should show crack width section
        assert "CRACK WIDTH CHECKS (HK Code Cl 7.2):" in report
        assert "Total members checked: 1" in report
        assert "Compliant: 1/1" in report
        assert "W1" in report
        assert "moderate" in report
        assert "PASS" in report
    
    def test_summary_report_with_crack_width_fail(self):
        """Test summary report with failing crack width check."""
        checker = SLSChecker()
        
        # Add failing crack width check
        checker.check_crack_width(
            member_id="W_fail",
            steel_strain=0.003,  # High strain
            bar_spacing=250.0,
            concrete_cover=80.0,
            exposure=ExposureCondition.MODERATE,
        )
        
        report = checker.get_summary_report()
        
        assert "Compliant: 0/1" in report
        assert "W_fail" in report
        assert "FAIL" in report
    
    def test_summary_report_complete(self):
        """Test summary report with all three check types."""
        checker = SLSChecker()
        
        # Add span/depth check (pass)
        checker.check_span_depth_ratio(
            member_id="B1",
            span_length=6000.0,
            effective_depth=300.0,
            member_type=MemberType.SIMPLY_SUPPORTED_BEAM,
        )
        
        # Add deflection check (pass)
        checker.check_deflection(
            member_id="S1",
            actual_deflection=8.0,
            span_length=5000.0,
            deflection_type="post_construction",
        )
        
        # Add crack width check (pass)
        checker.check_crack_width(
            member_id="W1",
            steel_strain=0.0008,
            bar_spacing=150.0,
            concrete_cover=40.0,
            exposure=ExposureCondition.MODERATE,
        )
        
        report = checker.get_summary_report()
        
        # Verify all three sections present
        assert "SPAN/DEPTH RATIO CHECKS" in report
        assert "DEFLECTION CHECKS" in report
        assert "CRACK WIDTH CHECKS" in report
        
        # Verify member IDs
        assert "B1" in report
        assert "S1" in report
        assert "W1" in report
        
        # All should pass
        assert report.count("PASS") == 3
        assert "FAIL" not in report
    
    def test_summary_report_mixed_results(self):
        """Test summary report with mixed pass/fail results."""
        checker = SLSChecker()
        
        # Span/depth: 1 pass, 1 fail
        checker.check_span_depth_ratio(
            member_id="B_pass",
            span_length=6000.0,
            effective_depth=300.0,
            member_type=MemberType.SIMPLY_SUPPORTED_BEAM,
        )
        checker.check_span_depth_ratio(
            member_id="B_fail",
            span_length=10000.0,
            effective_depth=300.0,
            member_type=MemberType.SIMPLY_SUPPORTED_BEAM,
        )
        
        # Deflection: 1 pass, 1 fail
        checker.check_deflection(
            member_id="S_pass",
            actual_deflection=8.0,
            span_length=5000.0,
            deflection_type="post_construction",
        )
        checker.check_deflection(
            member_id="S_fail",
            actual_deflection=25.0,
            span_length=5000.0,
            deflection_type="post_construction",
        )
        
        # Crack width: 1 pass, 1 fail
        checker.check_crack_width(
            member_id="W_pass",
            steel_strain=0.0008,
            bar_spacing=150.0,
            concrete_cover=40.0,
            exposure=ExposureCondition.MODERATE,
        )
        checker.check_crack_width(
            member_id="W_fail",
            steel_strain=0.003,
            bar_spacing=250.0,
            concrete_cover=80.0,
            exposure=ExposureCondition.MODERATE,
        )
        
        report = checker.get_summary_report()
        
        # Check compliance ratios
        assert "Compliant: 1/2" in report  # Should appear 3 times (once per section)
        
        # Check for both pass and fail
        assert report.count("PASS") == 3
        assert report.count("FAIL") == 3
    
    def test_summary_report_format_header(self):
        """Test summary report header formatting."""
        checker = SLSChecker()
        report = checker.get_summary_report()
        
        # Check separator lines (80 characters)
        assert "=" * 80 in report
        
        # Check main title centered formatting
        assert "SERVICEABILITY LIMIT STATE (SLS) CHECKS SUMMARY" in report
        
        # Should start and end with separator
        lines = report.split('\n')
        assert lines[0] == "=" * 80
        assert lines[-1] == "=" * 80
    
    def test_summary_report_format_tables(self):
        """Test summary report table formatting."""
        checker = SLSChecker()
        
        # Add one of each type
        checker.check_span_depth_ratio(
            member_id="B1",
            span_length=6000.0,
            effective_depth=300.0,
            member_type=MemberType.SIMPLY_SUPPORTED_BEAM,
        )
        
        checker.check_deflection(
            member_id="S1",
            actual_deflection=8.0,
            span_length=5000.0,
            deflection_type="post_construction",
        )
        
        checker.check_crack_width(
            member_id="W1",
            steel_strain=0.0008,
            bar_spacing=150.0,
            concrete_cover=40.0,
            exposure=ExposureCondition.MODERATE,
        )
        
        report = checker.get_summary_report()
        
        # Check table headers present
        assert "Member ID | Actual L/d | Allowable L/d | Status" in report
        assert "Member ID | Actual (mm) | Allowable (mm) | Limit | Status" in report
        assert "Member ID | w_k (mm) | w_allow (mm) | Exposure | Status" in report
        
        # Check table separators (dashes)
        assert "-" * 55 in report  # Span/depth table
        assert "-" * 65 in report  # Deflection and crack width tables
    
    def test_summary_report_multiple_members(self):
        """Test summary report with multiple members per section."""
        checker = SLSChecker()
        
        # Add multiple span/depth checks
        for i in range(1, 4):
            checker.check_span_depth_ratio(
                member_id=f"B{i}",
                span_length=6000.0,
                effective_depth=300.0,
                member_type=MemberType.SIMPLY_SUPPORTED_BEAM,
            )
        
        report = checker.get_summary_report()
        
        # Should show 3 members
        assert "Total members checked: 3" in report
        assert "Compliant: 3/3" in report
        
        # All members should appear
        assert "B1" in report
        assert "B2" in report
        assert "B3" in report
    
    def test_summary_report_hk_code_references(self):
        """Test that summary report includes HK Code references."""
        checker = SLSChecker()
        report = checker.get_summary_report()
        
        # Check HK Code clause references
        assert "HK Code Cl 7.3.4" in report  # Span/depth
        assert "Table 7.3" in report
        assert "HK Code Cl 7.3.2-7.3.3" in report  # Deflection
        assert "HK Code Cl 7.2" in report  # Crack width
    
    def test_summary_report_deflection_limit_types(self):
        """Test summary report shows deflection limit types correctly."""
        checker = SLSChecker()
        
        # Add different deflection types
        checker.check_deflection(
            member_id="S1",
            actual_deflection=8.0,
            span_length=5000.0,
            deflection_type="post_construction",
        )
        
        checker.check_deflection(
            member_id="S2",
            actual_deflection=12.0,
            span_length=5000.0,
            deflection_type="partition",
        )
        
        checker.check_deflection(
            member_id="S3",
            actual_deflection=18.0,
            span_length=5000.0,
            deflection_type="total",
        )
        
        report = checker.get_summary_report()
        
        # Should show limit ratios
        assert "L/500" in report
        assert "L/350" in report
        assert "L/250" in report
    
    def test_summary_report_exposure_conditions(self):
        """Test summary report shows exposure conditions correctly."""
        checker = SLSChecker()
        
        # Add different exposure conditions
        checker.check_crack_width(
            member_id="W_mild",
            steel_strain=0.001,
            bar_spacing=150.0,
            concrete_cover=40.0,
            exposure=ExposureCondition.MILD,
        )
        
        checker.check_crack_width(
            member_id="W_moderate",
            steel_strain=0.001,
            bar_spacing=150.0,
            concrete_cover=40.0,
            exposure=ExposureCondition.MODERATE,
        )
        
        checker.check_crack_width(
            member_id="W_severe",
            steel_strain=0.0003,  # Low strain for severe
            bar_spacing=100.0,
            concrete_cover=30.0,
            exposure=ExposureCondition.SEVERE,
        )
        
        report = checker.get_summary_report()
        
        # Should show exposure types
        assert "mild" in report
        assert "moderate" in report
        assert "severe" in report
    
    def test_summary_report_is_string(self):
        """Test that get_summary_report returns a string."""
        checker = SLSChecker()
        report = checker.get_summary_report()
        
        assert isinstance(report, str)
        assert len(report) > 0
    
    def test_summary_report_newlines(self):
        """Test that summary report uses proper line breaks."""
        checker = SLSChecker()
        report = checker.get_summary_report()
        
        # Should contain newlines
        assert '\n' in report
        
        # Should be multiple lines
        lines = report.split('\n')
        assert len(lines) > 10




