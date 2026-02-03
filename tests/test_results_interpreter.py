"""
Unit tests for the AI Results Interpreter module.

Tests the FEM results interpretation, critical element identification,
discrepancy calculation, and code compliance checking.
"""

import pytest
from unittest.mock import Mock, MagicMock

from src.ai.results_interpreter import (
    ResultsInterpreter,
    ResultsInterpretation,
    FEMResultsSummary,
    SimplifiedResultsSummary,
    CriticalElement,
    DesignDiscrepancy,
    CodeComplianceCheck,
    CriticalityLevel,
    IssueCategory,
    interpret_fem_results,
    create_fem_summary_from_dict,
    create_simplified_summary_from_project,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_fem_results():
    """Create sample FEM results for testing."""
    return FEMResultsSummary(
        max_beam_moment=(450.0, "Floor 5, Grid A-B"),
        max_beam_shear=(180.0, "Floor 5, Grid A-B"),
        max_column_axial=(8500.0, "Ground Floor, Grid A-1"),
        max_column_moment=(120.0, "Ground Floor, Grid A-1"),
        max_drift=(45.0, 450.0),  # 45mm, H/450
        max_stress=(22.5, "Column A-1, Base"),
        max_deflection=(32.0, "Floor 5, Grid A-B"),
        critical_load_case="ULS1: 1.4Gk + 1.6Qk",
        element_count=1250,
        node_count=450,
    )


@pytest.fixture
def sample_simplified_results():
    """Create sample simplified results for comparison."""
    return SimplifiedResultsSummary(
        beam_moment=420.0,
        beam_shear=165.0,
        column_axial=7800.0,
        column_moment=100.0,
        drift_estimate=40.0,
        beam_utilization=0.75,
        column_utilization=0.68,
        core_wall_utilization=0.55,
    )


@pytest.fixture
def project_params():
    """Create sample project parameters."""
    return {
        "num_floors": 20,
        "f_cu": 40,  # MPa
        "height": 70.0,  # m
        "span": 9.0,  # m
    }


@pytest.fixture
def mock_ai_service():
    """Create a mock AI service."""
    service = Mock()
    service.chat.return_value = '''```json
{
    "summary": "The FEM analysis shows satisfactory results with minor areas of concern.",
    "critical_elements": [],
    "discrepancies": [
        {
            "parameter": "moment",
            "fem_value": 450,
            "simplified_value": 420,
            "difference_percent": 7.1,
            "explanation": "FEM captures continuity effects"
        }
    ],
    "code_compliance": [
        {
            "check_name": "Drift",
            "status": "pass",
            "notes": "Within H/500 limit"
        }
    ],
    "recommendations": ["Proceed with detailed design"],
    "confidence_score": 85
}
```'''
    return service


# ============================================================================
# TEST FEMResultsSummary
# ============================================================================

class TestFEMResultsSummary:
    """Tests for FEMResultsSummary dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        summary = FEMResultsSummary()
        assert summary.max_beam_moment == (0.0, "")
        assert summary.element_count == 0
        assert summary.critical_load_case == ""

    def test_with_values(self, sample_fem_results):
        """Test FEMResultsSummary with values."""
        assert sample_fem_results.max_beam_moment[0] == 450.0
        assert sample_fem_results.max_drift[0] == 45.0
        assert sample_fem_results.max_drift[1] == 450.0
        assert sample_fem_results.element_count == 1250

    def test_create_from_dict(self):
        """Test creating summary from dictionary."""
        data = {
            "max_beam_moment": 500.0,
            "beam_moment_location": "Grid B-C",
            "max_drift_mm": 50.0,
            "drift_ratio": 400.0,
            "critical_load_case": "ULS2",
        }
        summary = create_fem_summary_from_dict(data)
        assert summary.max_beam_moment[0] == 500.0
        assert summary.max_beam_moment[1] == "Grid B-C"
        assert summary.max_drift[0] == 50.0
        assert summary.critical_load_case == "ULS2"


# ============================================================================
# TEST SimplifiedResultsSummary
# ============================================================================

class TestSimplifiedResultsSummary:
    """Tests for SimplifiedResultsSummary dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        summary = SimplifiedResultsSummary()
        assert summary.beam_moment == 0.0
        assert summary.column_axial == 0.0
        assert summary.beam_utilization == 0.0

    def test_with_values(self, sample_simplified_results):
        """Test SimplifiedResultsSummary with values."""
        assert sample_simplified_results.beam_moment == 420.0
        assert sample_simplified_results.beam_utilization == 0.75
        assert sample_simplified_results.column_utilization == 0.68


# ============================================================================
# TEST CriticalElement
# ============================================================================

class TestCriticalElement:
    """Tests for CriticalElement dataclass."""

    def test_critical_element_creation(self):
        """Test creating a critical element."""
        element = CriticalElement(
            element_id="COL_A1",
            element_type="column",
            location="Ground Floor, Grid A-1",
            issue="High stress concentration",
            category=IssueCategory.STRESS,
            criticality=CriticalityLevel.HIGH,
            value=28.0,
            limit=26.8,
            utilization=1.04,
            load_case="ULS1",
            recommendation="Increase column size",
        )
        assert element.element_id == "COL_A1"
        assert element.criticality == CriticalityLevel.HIGH
        assert element.utilization == 1.04

    def test_criticality_levels(self):
        """Test all criticality levels."""
        assert CriticalityLevel.CRITICAL.value == "critical"
        assert CriticalityLevel.HIGH.value == "high"
        assert CriticalityLevel.MEDIUM.value == "medium"
        assert CriticalityLevel.LOW.value == "low"


# ============================================================================
# TEST DesignDiscrepancy
# ============================================================================

class TestDesignDiscrepancy:
    """Tests for DesignDiscrepancy dataclass."""

    def test_discrepancy_creation(self):
        """Test creating a design discrepancy."""
        discrepancy = DesignDiscrepancy(
            element_type="beam",
            parameter="moment",
            fem_value=450.0,
            simplified_value=420.0,
            difference_percent=7.14,
            is_significant=False,
            possible_cause="FEM captures continuity",
        )
        assert discrepancy.difference_percent == pytest.approx(7.14, rel=0.01)
        assert not discrepancy.is_significant

    def test_significant_discrepancy(self):
        """Test significant discrepancy detection."""
        discrepancy = DesignDiscrepancy(
            element_type="column",
            parameter="axial_load",
            fem_value=9500.0,
            simplified_value=7800.0,
            difference_percent=21.8,
            is_significant=True,
            possible_cause="FEM includes frame action",
        )
        assert discrepancy.is_significant


# ============================================================================
# TEST CodeComplianceCheck
# ============================================================================

class TestCodeComplianceCheck:
    """Tests for CodeComplianceCheck dataclass."""

    def test_passing_check(self):
        """Test a passing code check."""
        check = CodeComplianceCheck(
            check_name="Lateral Drift",
            clause="HK Code 2013 Cl 7.3.2",
            status="pass",
            actual_value=45.0,
            limit_value=140.0,
            utilization=0.32,
        )
        assert check.status == "pass"
        assert check.utilization < 1.0

    def test_failing_check(self):
        """Test a failing code check."""
        check = CodeComplianceCheck(
            check_name="Concrete Stress",
            clause="HK Code 2013 Cl 6.1.2.4",
            status="fail",
            actual_value=30.0,
            limit_value=26.8,
            utilization=1.12,
            notes="Exceeds limit by 12%",
        )
        assert check.status == "fail"
        assert check.utilization > 1.0


# ============================================================================
# TEST ResultsInterpretation
# ============================================================================

class TestResultsInterpretation:
    """Tests for ResultsInterpretation dataclass."""

    def test_interpretation_creation(self):
        """Test creating a results interpretation."""
        interpretation = ResultsInterpretation(
            summary="FEM analysis shows satisfactory results.",
            critical_elements=[],
            discrepancies=[],
            code_compliance=[],
            recommendations=["Proceed with detailed design"],
            confidence_score=85,
        )
        assert interpretation.confidence_score == 85
        assert not interpretation.has_critical_issues

    def test_has_critical_issues(self):
        """Test critical issues detection."""
        critical_elem = CriticalElement(
            element_id="COL_A1",
            element_type="column",
            location="Ground Floor",
            issue="Overstressed",
            category=IssueCategory.STRESS,
            criticality=CriticalityLevel.CRITICAL,
            value=30.0,
            limit=26.8,
            utilization=1.12,
        )
        interpretation = ResultsInterpretation(
            summary="Critical issues found.",
            critical_elements=[critical_elem],
            discrepancies=[],
            code_compliance=[],
            recommendations=["Address critical issues"],
        )
        assert interpretation.has_critical_issues

    def test_overall_status_critical(self):
        """Test overall status with critical issues."""
        critical_elem = CriticalElement(
            element_id="COL_A1",
            element_type="column",
            location="Ground Floor",
            issue="Overstressed",
            category=IssueCategory.STRESS,
            criticality=CriticalityLevel.CRITICAL,
            value=30.0,
            limit=26.8,
            utilization=1.12,
        )
        interpretation = ResultsInterpretation(
            summary="Critical issues found.",
            critical_elements=[critical_elem],
            discrepancies=[],
            code_compliance=[],
            recommendations=[],
        )
        assert interpretation.overall_status == "REQUIRES IMMEDIATE ACTION"

    def test_overall_status_satisfactory(self):
        """Test overall status when satisfactory."""
        interpretation = ResultsInterpretation(
            summary="All checks passed.",
            critical_elements=[],
            discrepancies=[],
            code_compliance=[],
            recommendations=[],
        )
        assert interpretation.overall_status == "SATISFACTORY"


# ============================================================================
# TEST ResultsInterpreter
# ============================================================================

class TestResultsInterpreter:
    """Tests for ResultsInterpreter class."""

    def test_interpreter_initialization(self):
        """Test interpreter initialization."""
        interpreter = ResultsInterpreter()
        assert interpreter.design_code == "HK2013"
        assert interpreter.ai_service is None

    def test_interpreter_with_ai_service(self, mock_ai_service):
        """Test interpreter with AI service."""
        interpreter = ResultsInterpreter(ai_service=mock_ai_service)
        assert interpreter.ai_service is not None

    def test_interpret_results_basic(self, sample_fem_results, project_params):
        """Test basic results interpretation without AI."""
        interpreter = ResultsInterpreter()
        interpretation = interpreter.interpret_results(
            fem_results=sample_fem_results,
            project_params=project_params,
        )
        assert interpretation is not None
        assert len(interpretation.summary) > 0
        assert interpretation.confidence_score > 0

    def test_interpret_results_with_simplified(
        self, sample_fem_results, sample_simplified_results, project_params
    ):
        """Test interpretation with simplified results comparison."""
        interpreter = ResultsInterpreter()
        interpretation = interpreter.interpret_results(
            fem_results=sample_fem_results,
            simplified_results=sample_simplified_results,
            project_params=project_params,
        )
        assert interpretation is not None
        assert len(interpretation.discrepancies) > 0

    def test_identify_critical_stress(self, project_params):
        """Test identification of critical stress."""
        fem_results = FEMResultsSummary(
            max_stress=(30.0, "Column A-1"),  # Exceeds 0.67 * 40 = 26.8 MPa
        )
        interpreter = ResultsInterpreter()
        interpretation = interpreter.interpret_results(
            fem_results=fem_results,
            project_params=project_params,
        )
        # Should identify critical stress
        stress_elements = [
            e for e in interpretation.critical_elements
            if e.category == IssueCategory.STRESS
        ]
        assert len(stress_elements) > 0

    def test_identify_critical_drift(self, project_params):
        """Test identification of critical drift."""
        # H/500 = 70000/500 = 140mm limit
        fem_results = FEMResultsSummary(
            max_drift=(160.0, 437.5),  # Exceeds 140mm limit
        )
        interpreter = ResultsInterpreter()
        interpretation = interpreter.interpret_results(
            fem_results=fem_results,
            project_params=project_params,
        )
        # Should identify critical drift
        drift_elements = [
            e for e in interpretation.critical_elements
            if e.category == IssueCategory.DRIFT
        ]
        assert len(drift_elements) > 0

    def test_code_compliance_checks(self, sample_fem_results, project_params):
        """Test code compliance checks."""
        interpreter = ResultsInterpreter()
        interpretation = interpreter.interpret_results(
            fem_results=sample_fem_results,
            project_params=project_params,
        )
        # Should have compliance checks for drift, stress, deflection
        check_names = [c.check_name for c in interpretation.code_compliance]
        assert "Lateral Drift" in check_names
        assert "Concrete Stress" in check_names
        assert "Beam Deflection" in check_names

    def test_discrepancy_calculation(
        self, sample_fem_results, sample_simplified_results, project_params
    ):
        """Test discrepancy calculation."""
        interpreter = ResultsInterpreter()
        interpretation = interpreter.interpret_results(
            fem_results=sample_fem_results,
            simplified_results=sample_simplified_results,
            project_params=project_params,
        )
        # Should have discrepancies for moment, shear, axial, drift
        params = [d.parameter for d in interpretation.discrepancies]
        assert "moment" in params
        assert "shear" in params

    def test_significant_discrepancy_detection(self, project_params):
        """Test significant discrepancy detection (>15%)."""
        fem_results = FEMResultsSummary(
            max_beam_moment=(600.0, "Grid A-B"),
        )
        simplified_results = SimplifiedResultsSummary(
            beam_moment=420.0,  # 43% difference
        )
        interpreter = ResultsInterpreter()
        interpretation = interpreter.interpret_results(
            fem_results=fem_results,
            simplified_results=simplified_results,
            project_params=project_params,
        )
        moment_disc = [d for d in interpretation.discrepancies if d.parameter == "moment"]
        assert len(moment_disc) > 0
        assert moment_disc[0].is_significant

    def test_interpret_with_ai_service(
        self, sample_fem_results, sample_simplified_results, project_params, mock_ai_service
    ):
        """Test interpretation with AI service."""
        interpreter = ResultsInterpreter(ai_service=mock_ai_service)
        interpretation = interpreter.interpret_results(
            fem_results=sample_fem_results,
            simplified_results=sample_simplified_results,
            project_params=project_params,
        )
        # AI service should have been called
        mock_ai_service.chat.assert_called_once()
        assert interpretation is not None

    def test_quick_summary(self, sample_fem_results, project_params):
        """Test quick summary generation."""
        interpreter = ResultsInterpreter()
        summary = interpreter.get_quick_summary(
            fem_results=sample_fem_results,
            project_params=project_params,
        )
        assert len(summary) > 0
        assert "[" in summary  # Should have status prefix
        assert "FEM analysis" in summary


# ============================================================================
# TEST CONVENIENCE FUNCTIONS
# ============================================================================

class TestConvenienceFunctions:
    """Tests for module convenience functions."""

    def test_interpret_fem_results_function(self, sample_fem_results, project_params):
        """Test interpret_fem_results convenience function."""
        interpretation = interpret_fem_results(
            fem_results=sample_fem_results,
            project_params=project_params,
        )
        assert interpretation is not None
        assert isinstance(interpretation, ResultsInterpretation)

    def test_create_fem_summary_from_dict(self):
        """Test create_fem_summary_from_dict function."""
        data = {
            "max_beam_moment": 500.0,
            "beam_moment_location": "Grid B-C",
            "max_drift_mm": 50.0,
            "drift_ratio": 400.0,
            "element_count": 1000,
        }
        summary = create_fem_summary_from_dict(data)
        assert summary.max_beam_moment[0] == 500.0
        assert summary.element_count == 1000

    def test_create_simplified_summary_from_project(self):
        """Test create_simplified_summary_from_project function."""
        # Create mock project data
        mock_project = Mock()
        mock_project.primary_beam_result = Mock()
        mock_project.primary_beam_result.moment = 420.0
        mock_project.primary_beam_result.shear = 165.0
        mock_project.primary_beam_result.utilization = 0.75

        mock_project.column_result = Mock()
        mock_project.column_result.axial_load = 7800.0
        mock_project.column_result.lateral_moment = 100.0
        mock_project.column_result.utilization = 0.68

        mock_project.wind_result = Mock()
        mock_project.wind_result.drift_mm = 40.0

        mock_project.core_wall_result = None

        summary = create_simplified_summary_from_project(mock_project)
        assert summary.beam_moment == 420.0
        assert summary.column_axial == 7800.0
        assert summary.drift_estimate == 40.0


# ============================================================================
# TEST EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_fem_results(self, project_params):
        """Test with empty FEM results."""
        interpreter = ResultsInterpreter()
        interpretation = interpreter.interpret_results(
            fem_results=FEMResultsSummary(),
            project_params=project_params,
        )
        assert interpretation is not None
        assert len(interpretation.code_compliance) > 0

    def test_zero_simplified_values(self, sample_fem_results, project_params):
        """Test with zero simplified values (avoid division by zero)."""
        simplified = SimplifiedResultsSummary()  # All zeros
        interpreter = ResultsInterpreter()
        interpretation = interpreter.interpret_results(
            fem_results=sample_fem_results,
            simplified_results=simplified,
            project_params=project_params,
        )
        assert interpretation is not None

    def test_missing_project_params(self, sample_fem_results):
        """Test with missing project parameters (use defaults)."""
        interpreter = ResultsInterpreter()
        interpretation = interpreter.interpret_results(
            fem_results=sample_fem_results,
            project_params=None,
        )
        assert interpretation is not None

    def test_ai_service_failure(self, sample_fem_results, project_params):
        """Test fallback when AI service fails."""
        failing_service = Mock()
        failing_service.chat.side_effect = Exception("API Error")

        interpreter = ResultsInterpreter(ai_service=failing_service)
        interpretation = interpreter.interpret_results(
            fem_results=sample_fem_results,
            project_params=project_params,
        )
        # Should fall back to rule-based interpretation
        assert interpretation is not None
        assert interpretation.confidence_score > 0

    def test_ai_service_invalid_json(self, sample_fem_results, project_params):
        """Test handling of invalid JSON from AI service."""
        bad_service = Mock()
        bad_service.chat.return_value = "This is not valid JSON"

        interpreter = ResultsInterpreter(ai_service=bad_service)
        interpretation = interpreter.interpret_results(
            fem_results=sample_fem_results,
            project_params=project_params,
        )
        # Should handle gracefully
        assert interpretation is not None


# ============================================================================
# TEST INTEGRATION
# ============================================================================

class TestIntegration:
    """Integration tests for results interpreter."""

    def test_full_workflow(self, sample_fem_results, sample_simplified_results, project_params):
        """Test complete interpretation workflow."""
        interpreter = ResultsInterpreter()

        # Interpret results
        interpretation = interpreter.interpret_results(
            fem_results=sample_fem_results,
            simplified_results=sample_simplified_results,
            project_params=project_params,
        )

        # Verify all components
        assert interpretation.summary is not None
        assert len(interpretation.summary) > 50  # Should have substantial summary

        # Verify code compliance
        assert len(interpretation.code_compliance) >= 3  # Drift, stress, deflection

        # Verify discrepancies calculated
        assert len(interpretation.discrepancies) >= 1

        # Verify recommendations
        assert len(interpretation.recommendations) >= 1

        # Verify status
        assert interpretation.overall_status in [
            "SATISFACTORY",
            "REQUIRES ATTENTION",
            "REQUIRES IMMEDIATE ACTION",
            "CODE COMPLIANCE ISSUE",
            "REVIEW RECOMMENDED",
        ]

    def test_interpretation_with_all_failures(self, project_params):
        """Test interpretation when all checks fail."""
        fem_results = FEMResultsSummary(
            max_stress=(35.0, "Column A-1"),  # Exceeds limit
            max_drift=(200.0, 350.0),  # Exceeds H/500
            max_deflection=(50.0, "Beam B-C"),  # Exceeds L/250
        )

        interpreter = ResultsInterpreter()
        interpretation = interpreter.interpret_results(
            fem_results=fem_results,
            project_params=project_params,
        )

        # Should have critical elements
        assert len(interpretation.critical_elements) > 0

        # Should have failing code compliance
        failing_checks = [c for c in interpretation.code_compliance if c.status == "fail"]
        assert len(failing_checks) >= 1

        # Overall status should indicate problems
        assert interpretation.overall_status in [
            "REQUIRES IMMEDIATE ACTION",
            "REQUIRES ATTENTION",
            "CODE COMPLIANCE ISSUE",
        ]
