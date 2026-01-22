"""
Unit tests for AI response parser module.

Tests cover:
- DesignReviewResponse parsing and validation
- OptimizationResponse parsing and validation
- UnstructuredResponse fallback
- JSON extraction from markdown code blocks
- Error handling and edge cases
"""

import pytest
import json

from src.ai.response_parser import (
    DesignReviewResponse,
    OptimizationResponse,
    UnstructuredResponse,
    PriorityLevel,
    parse_design_review_response,
    parse_optimization_response,
    safe_parse_design_review,
    safe_parse_optimization,
    extract_json_from_markdown,
)


class TestDesignReviewResponse:
    """Tests for DesignReviewResponse dataclass."""

    def test_create_valid_response(self):
        """Test creating a valid design review response."""
        response = DesignReviewResponse(
            efficiency_score=75,
            concerns=["High wind load", "Long beam spans"],
            code_issues=["Drift exceeds H/500"],
            recommendations=["Increase column size", "Add shear walls"],
            summary="Overall design is adequate with minor improvements needed.",
        )
        assert response.efficiency_score == 75
        assert len(response.concerns) == 2
        assert len(response.recommendations) == 2

    def test_efficiency_score_validation(self):
        """Test efficiency score validation (0-100 range)."""
        # Valid scores
        DesignReviewResponse(80, [], [], [], "Good")
        DesignReviewResponse(0, [], [], [], "Poor")
        DesignReviewResponse(100, [], [], [], "Excellent")

        # Invalid scores
        with pytest.raises(ValueError):
            DesignReviewResponse(-1, [], [], [], "Invalid")
        
        with pytest.raises(ValueError):
            DesignReviewResponse(101, [], [], [], "Invalid")


class TestOptimizationResponse:
    """Tests for OptimizationResponse dataclass."""

    def test_create_valid_response(self):
        """Test creating a valid optimization response."""
        response = OptimizationResponse(
            material_savings=["Reduce concrete grade to C35"],
            system_improvements=["Optimize grid spacing"],
            constructability=["Use precast columns"],
            estimated_savings_percent=15.5,
            priority_action="Reduce concrete grade",
        )
        assert response.estimated_savings_percent == 15.5
        assert len(response.material_savings) == 1

    def test_savings_percent_validation(self):
        """Test savings percentage validation (0-30% range)."""
        # Valid percentages
        OptimizationResponse([], [], [], 0.0, "None")
        OptimizationResponse([], [], [], 15.0, "Moderate")
        OptimizationResponse([], [], [], 30.0, "Maximum")

        # Invalid percentages
        with pytest.raises(ValueError):
            OptimizationResponse([], [], [], -1.0, "Invalid")
        
        with pytest.raises(ValueError):
            OptimizationResponse([], [], [], 31.0, "Invalid")


class TestParseDesignReview:
    """Tests for design review JSON parsing."""

    def test_parse_valid_json(self):
        """Test parsing valid design review JSON."""
        json_str = json.dumps({
            "efficiency_score": 85,
            "concerns": ["High lateral drift"],
            "code_issues": [],
            "recommendations": ["Add dampers", "Stiffen core walls"],
            "summary": "Design meets code with recommendations for improvement."
        })

        response = parse_design_review_response(json_str)
        assert response.efficiency_score == 85
        assert len(response.concerns) == 1
        assert len(response.recommendations) == 2
        assert response.summary.startswith("Design meets")

    def test_parse_with_raw_response(self):
        """Test that raw_response is preserved."""
        json_str = '{"efficiency_score": 70, "concerns": [], "code_issues": [], "recommendations": [], "summary": "OK"}'
        response = parse_design_review_response(json_str)
        assert response.raw_response is not None
        assert response.raw_response["efficiency_score"] == 70

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON raises ValueError."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            parse_design_review_response("not valid json")

    def test_parse_missing_required_field(self):
        """Test parsing with missing required field raises ValueError."""
        json_str = json.dumps({
            "efficiency_score": 80,
            "concerns": [],
            # Missing code_issues
            "recommendations": [],
            "summary": "Test"
        })
        
        # Should not raise - code_issues defaults to []
        response = parse_design_review_response(json_str)
        assert response.code_issues == []

    def test_parse_missing_summary(self):
        """Test parsing with missing summary raises ValueError."""
        json_str = json.dumps({
            "efficiency_score": 80,
            "concerns": [],
            "code_issues": [],
            "recommendations": [],
            # Missing summary
        })
        
        with pytest.raises(ValueError, match="'summary' is required"):
            parse_design_review_response(json_str)

    def test_parse_invalid_field_type(self):
        """Test parsing with invalid field type raises ValueError."""
        json_str = json.dumps({
            "efficiency_score": 80,
            "concerns": "should be a list",  # Invalid type
            "code_issues": [],
            "recommendations": [],
            "summary": "Test"
        })
        
        with pytest.raises(ValueError, match="'concerns' must be a list"):
            parse_design_review_response(json_str)


class TestParseOptimization:
    """Tests for optimization JSON parsing."""

    def test_parse_valid_json(self):
        """Test parsing valid optimization JSON."""
        json_str = json.dumps({
            "material_savings": ["Use C35 instead of C40"],
            "system_improvements": ["Reduce column spacing"],
            "constructability": ["Standardize formwork"],
            "estimated_savings_percent": 12.5,
            "priority_action": "Use C35 concrete"
        })

        response = parse_optimization_response(json_str)
        assert response.estimated_savings_percent == 12.5
        assert response.priority_action == "Use C35 concrete"

    def test_parse_with_empty_lists(self):
        """Test parsing with empty suggestion lists."""
        json_str = json.dumps({
            "material_savings": [],
            "system_improvements": [],
            "constructability": [],
            "estimated_savings_percent": 0,
            "priority_action": "None"
        })

        response = parse_optimization_response(json_str)
        assert len(response.material_savings) == 0
        assert response.estimated_savings_percent == 0


class TestExtractJsonFromMarkdown:
    """Tests for JSON extraction from markdown code blocks."""

    def test_extract_from_json_code_block(self):
        """Test extracting JSON from ```json code block."""
        markdown = """Here's the response:
```json
{"key": "value", "number": 42}
```
Additional text."""

        extracted = extract_json_from_markdown(markdown)
        assert extracted == '{"key": "value", "number": 42}'

    def test_extract_from_generic_code_block(self):
        """Test extracting JSON from ``` code block."""
        markdown = """Response:
```
{"key": "value"}
```"""

        extracted = extract_json_from_markdown(markdown)
        assert extracted == '{"key": "value"}'

    def test_no_code_block_returns_original(self):
        """Test that text without code block is returned as-is."""
        text = '{"key": "value"}'
        extracted = extract_json_from_markdown(text)
        assert extracted == text

    def test_generic_code_block_non_json_ignored(self):
        """Test that non-JSON code blocks are ignored."""
        markdown = """Text:
```
not json content
just regular text
```"""

        extracted = extract_json_from_markdown(markdown)
        # Should return original since content doesn't look like JSON
        assert "not json content" in extracted

    def test_multiple_code_blocks_first_extracted(self):
        """Test that first JSON code block is extracted."""
        markdown = """```json
{"first": true}
```
Some text
```json
{"second": true}
```"""

        extracted = extract_json_from_markdown(markdown)
        assert '{"first": true}' in extracted


class TestSafeParseDesignReview:
    """Tests for safe parsing with fallback."""

    def test_safe_parse_valid_json(self):
        """Test safe parse with valid JSON returns DesignReviewResponse."""
        json_str = json.dumps({
            "efficiency_score": 90,
            "concerns": [],
            "code_issues": [],
            "recommendations": ["Good design"],
            "summary": "Excellent"
        })

        response = safe_parse_design_review(json_str)
        assert isinstance(response, DesignReviewResponse)
        assert response.efficiency_score == 90

    def test_safe_parse_invalid_json_fallback(self):
        """Test safe parse with invalid JSON returns UnstructuredResponse."""
        invalid_json = "This is not JSON at all"
        
        response = safe_parse_design_review(invalid_json)
        assert isinstance(response, UnstructuredResponse)
        assert response.has_structure is False
        assert response.content == invalid_json
        assert response.parse_error is not None

    def test_safe_parse_markdown_wrapped_json(self):
        """Test safe parse extracts JSON from markdown."""
        markdown = """```json
{
  "efficiency_score": 75,
  "concerns": ["High drift"],
  "code_issues": [],
  "recommendations": ["Add bracing"],
  "summary": "Needs improvement"
}
```"""

        response = safe_parse_design_review(markdown)
        assert isinstance(response, DesignReviewResponse)
        assert response.efficiency_score == 75


class TestSafeParseOptimization:
    """Tests for safe optimization parsing with fallback."""

    def test_safe_parse_valid_json(self):
        """Test safe parse with valid JSON returns OptimizationResponse."""
        json_str = json.dumps({
            "material_savings": ["Save 10%"],
            "system_improvements": [],
            "constructability": [],
            "estimated_savings_percent": 10,
            "priority_action": "Material optimization"
        })

        response = safe_parse_optimization(json_str)
        assert isinstance(response, OptimizationResponse)
        assert response.estimated_savings_percent == 10

    def test_safe_parse_invalid_json_fallback(self):
        """Test safe parse with invalid JSON returns UnstructuredResponse."""
        response = safe_parse_optimization("Invalid response")
        assert isinstance(response, UnstructuredResponse)
        assert response.has_structure is False


class TestUnstructuredResponse:
    """Tests for UnstructuredResponse fallback."""

    def test_create_unstructured_response(self):
        """Test creating unstructured response."""
        response = UnstructuredResponse(
            content="Plain text response",
            has_structure=False,
            parse_error="JSON decode failed"
        )
        assert response.content == "Plain text response"
        assert response.has_structure is False
        assert response.parse_error == "JSON decode failed"

    def test_unstructured_response_defaults(self):
        """Test unstructured response default values."""
        response = UnstructuredResponse(content="Test")
        assert response.has_structure is False
        assert response.parse_error is None


class TestPriorityLevel:
    """Tests for PriorityLevel enum."""

    def test_priority_levels_exist(self):
        """Test all priority levels are defined."""
        assert PriorityLevel.CRITICAL.value == "critical"
        assert PriorityLevel.HIGH.value == "high"
        assert PriorityLevel.MEDIUM.value == "medium"
        assert PriorityLevel.LOW.value == "low"

    def test_priority_level_count(self):
        """Test exactly 4 priority levels are defined."""
        assert len(PriorityLevel) == 4
