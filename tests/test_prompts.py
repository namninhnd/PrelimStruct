"""
Unit tests for AI Prompts module.

Tests cover:
- PromptTemplate dataclass and formatting
- System prompts content
- Prompt template registry
- Context injection
- Design review prompt creation

Author: PrelimStruct Development Team
Date: 2026-01-22
"""

import pytest

from src.ai.prompts import (
    PromptType,
    PromptTemplate,
    SYSTEM_PROMPT_BASE,
    SYSTEM_PROMPT_DESIGN_REVIEW,
    SYSTEM_PROMPT_RESULTS,
    SYSTEM_PROMPT_OPTIMIZATION,
    DESIGN_REVIEW_TEMPLATE,
    RESULTS_INTERPRETATION_TEMPLATE,
    OPTIMIZATION_TEMPLATE,
    MODEL_SETUP_TEMPLATE,
    MESH_GENERATION_TEMPLATE,
    get_template,
    inject_project_context,
    create_design_review_prompt,
)


# ============================================================================
# TEST PromptType Enum
# ============================================================================

class TestPromptType:
    """Tests for PromptType enum."""

    def test_all_prompt_types_exist(self):
        """Test all expected prompt types are defined."""
        assert PromptType.DESIGN_REVIEW.value == "design_review"
        assert PromptType.RESULTS_INTERPRETATION.value == "results_interpretation"
        assert PromptType.OPTIMIZATION.value == "optimization"
        assert PromptType.MODEL_SETUP.value == "model_setup"
        assert PromptType.MESH_GENERATION.value == "mesh_generation"
        assert PromptType.GENERAL_QUERY.value == "general_query"

    def test_prompt_type_count(self):
        """Test the number of prompt types."""
        assert len(PromptType) == 6


# ============================================================================
# TEST System Prompts
# ============================================================================

class TestSystemPrompts:
    """Tests for system prompt content."""

    def test_base_prompt_contains_hk_code(self):
        """Test base prompt mentions HK Code 2013."""
        assert "HK Code 2013" in SYSTEM_PROMPT_BASE

    def test_base_prompt_contains_tall_buildings(self):
        """Test base prompt mentions tall buildings expertise."""
        assert "tall building" in SYSTEM_PROMPT_BASE.lower()

    def test_base_prompt_contains_word_limit(self):
        """Test base prompt specifies response length."""
        assert "150-300 words" in SYSTEM_PROMPT_BASE

    def test_design_review_prompt_extends_base(self):
        """Test design review prompt extends base."""
        assert "Senior Structural Engineer" in SYSTEM_PROMPT_DESIGN_REVIEW
        assert "efficiency" in SYSTEM_PROMPT_DESIGN_REVIEW.lower()

    def test_results_prompt_extends_base(self):
        """Test results prompt extends base."""
        assert "Senior Structural Engineer" in SYSTEM_PROMPT_RESULTS
        assert "stress" in SYSTEM_PROMPT_RESULTS.lower()

    def test_optimization_prompt_extends_base(self):
        """Test optimization prompt extends base."""
        assert "Senior Structural Engineer" in SYSTEM_PROMPT_OPTIMIZATION
        assert "cost" in SYSTEM_PROMPT_OPTIMIZATION.lower()


# ============================================================================
# TEST PromptTemplate Dataclass
# ============================================================================

class TestPromptTemplate:
    """Tests for PromptTemplate dataclass."""

    def test_create_basic_template(self):
        """Test creating a basic prompt template."""
        template = PromptTemplate(
            name="test_template",
            prompt_type=PromptType.GENERAL_QUERY,
            template="Hello, {name}!",
            system_prompt="You are a helpful assistant.",
        )

        assert template.name == "test_template"
        assert template.prompt_type == PromptType.GENERAL_QUERY
        assert template.max_tokens == 300  # Default
        assert template.temperature == 0.7  # Default
        assert template.json_mode is False  # Default

    def test_template_with_all_parameters(self):
        """Test template with all parameters set."""
        template = PromptTemplate(
            name="full_template",
            prompt_type=PromptType.DESIGN_REVIEW,
            template="Review: {design}",
            system_prompt="You are an engineer.",
            max_tokens=500,
            temperature=0.5,
            json_mode=True,
        )

        assert template.max_tokens == 500
        assert template.temperature == 0.5
        assert template.json_mode is True

    def test_template_format_single_variable(self):
        """Test formatting template with single variable."""
        template = PromptTemplate(
            name="greeting",
            prompt_type=PromptType.GENERAL_QUERY,
            template="Hello, {name}!",
            system_prompt="Test",
        )

        result = template.format(name="Alice")
        assert result == "Hello, Alice!"

    def test_template_format_multiple_variables(self):
        """Test formatting template with multiple variables."""
        template = PromptTemplate(
            name="building_info",
            prompt_type=PromptType.GENERAL_QUERY,
            template="Building: {floors} floors, {height}m tall",
            system_prompt="Test",
        )

        result = template.format(floors=20, height=70)
        assert result == "Building: 20 floors, 70m tall"

    def test_template_format_missing_variable_raises(self):
        """Test that missing variable raises KeyError."""
        template = PromptTemplate(
            name="test",
            prompt_type=PromptType.GENERAL_QUERY,
            template="Hello, {name}! Your age is {age}.",
            system_prompt="Test",
        )

        with pytest.raises(KeyError):
            template.format(name="Bob")  # Missing age


# ============================================================================
# TEST Pre-defined Templates
# ============================================================================

class TestDesignReviewTemplate:
    """Tests for design review template."""

    def test_design_review_template_properties(self):
        """Test design review template properties."""
        assert DESIGN_REVIEW_TEMPLATE.name == "design_review"
        assert DESIGN_REVIEW_TEMPLATE.prompt_type == PromptType.DESIGN_REVIEW
        assert DESIGN_REVIEW_TEMPLATE.json_mode is True
        assert DESIGN_REVIEW_TEMPLATE.max_tokens == 400

    def test_design_review_template_contains_json_format(self):
        """Test design review template requests JSON output."""
        assert "JSON" in DESIGN_REVIEW_TEMPLATE.template
        assert "efficiency_score" in DESIGN_REVIEW_TEMPLATE.template

    def test_design_review_template_formatting(self):
        """Test design review template can be formatted."""
        result = DESIGN_REVIEW_TEMPLATE.format(
            height=70,
            num_floors=20,
            grid_x=9,
            grid_y=9,
            total_area=5000,
            concrete_grade="C40",
            beam_sections="400x700",
            column_sections="600x600",
            core_wall_config="I_SECTION",
            lateral_system="Core wall",
            design_summary="Preliminary design complete.",
        )

        assert "70m" in result
        assert "20 floors" in result
        assert "C40" in result
        assert "I_SECTION" in result


class TestResultsInterpretationTemplate:
    """Tests for results interpretation template."""

    def test_results_template_properties(self):
        """Test results template properties."""
        assert RESULTS_INTERPRETATION_TEMPLATE.name == "results_interpretation"
        assert RESULTS_INTERPRETATION_TEMPLATE.prompt_type == PromptType.RESULTS_INTERPRETATION
        assert RESULTS_INTERPRETATION_TEMPLATE.temperature == 0.5  # Lower for factual
        assert RESULTS_INTERPRETATION_TEMPLATE.json_mode is False

    def test_results_template_contains_code_limits(self):
        """Test results template mentions code limits."""
        assert "H/500" in RESULTS_INTERPRETATION_TEMPLATE.template
        assert "0.67f_cu" in RESULTS_INTERPRETATION_TEMPLATE.template


class TestOptimizationTemplate:
    """Tests for optimization template."""

    def test_optimization_template_properties(self):
        """Test optimization template properties."""
        assert OPTIMIZATION_TEMPLATE.name == "optimization"
        assert OPTIMIZATION_TEMPLATE.prompt_type == PromptType.OPTIMIZATION
        assert OPTIMIZATION_TEMPLATE.json_mode is True
        assert OPTIMIZATION_TEMPLATE.max_tokens == 400

    def test_optimization_template_contains_cost_fields(self):
        """Test optimization template has cost fields."""
        assert "estimated_cost" in OPTIMIZATION_TEMPLATE.template
        assert "material_savings" in OPTIMIZATION_TEMPLATE.template


class TestModelSetupTemplate:
    """Tests for model setup template."""

    def test_model_setup_template_properties(self):
        """Test model setup template properties."""
        assert MODEL_SETUP_TEMPLATE.name == "model_setup"
        assert MODEL_SETUP_TEMPLATE.prompt_type == PromptType.MODEL_SETUP
        assert MODEL_SETUP_TEMPLATE.temperature == 0.6

    def test_model_setup_template_contains_questions(self):
        """Test model setup template has modeling questions."""
        assert "mesh density" in MODEL_SETUP_TEMPLATE.template.lower()
        assert "boundary conditions" in MODEL_SETUP_TEMPLATE.template.lower()


class TestMeshGenerationTemplate:
    """Tests for mesh generation template."""

    def test_mesh_template_properties(self):
        """Test mesh generation template properties."""
        assert MESH_GENERATION_TEMPLATE.name == "mesh_generation"
        assert MESH_GENERATION_TEMPLATE.prompt_type == PromptType.MESH_GENERATION
        assert MESH_GENERATION_TEMPLATE.max_tokens == 200

    def test_mesh_template_contains_geometry_fields(self):
        """Test mesh template has geometry fields."""
        assert "beam_span" in MESH_GENERATION_TEMPLATE.template.lower()
        assert "wall_thickness" in MESH_GENERATION_TEMPLATE.template


# ============================================================================
# TEST get_template Function
# ============================================================================

class TestGetTemplate:
    """Tests for get_template function."""

    def test_get_design_review_template(self):
        """Test getting design review template."""
        template = get_template(PromptType.DESIGN_REVIEW)
        assert template is DESIGN_REVIEW_TEMPLATE

    def test_get_results_template(self):
        """Test getting results interpretation template."""
        template = get_template(PromptType.RESULTS_INTERPRETATION)
        assert template is RESULTS_INTERPRETATION_TEMPLATE

    def test_get_optimization_template(self):
        """Test getting optimization template."""
        template = get_template(PromptType.OPTIMIZATION)
        assert template is OPTIMIZATION_TEMPLATE

    def test_get_model_setup_template(self):
        """Test getting model setup template."""
        template = get_template(PromptType.MODEL_SETUP)
        assert template is MODEL_SETUP_TEMPLATE

    def test_get_mesh_template(self):
        """Test getting mesh generation template."""
        template = get_template(PromptType.MESH_GENERATION)
        assert template is MESH_GENERATION_TEMPLATE

    def test_get_unknown_template_raises(self):
        """Test getting unknown template raises ValueError."""
        with pytest.raises(ValueError, match="No template found"):
            get_template(PromptType.GENERAL_QUERY)


# ============================================================================
# TEST inject_project_context Function
# ============================================================================

class TestInjectProjectContext:
    """Tests for inject_project_context function."""

    def test_inject_context_basic(self):
        """Test basic context injection."""
        template = PromptTemplate(
            name="test",
            prompt_type=PromptType.GENERAL_QUERY,
            template="Building height: {height}m",
            system_prompt="Test",
        )

        result = inject_project_context(template, {"height": 70})
        assert result == "Building height: 70m"

    def test_inject_context_design_review(self):
        """Test context injection for design review."""
        project_data = {
            "height": 70,
            "num_floors": 20,
            "grid_x": 9,
            "grid_y": 9,
            "total_area": 5000,
            "concrete_grade": "C40",
            "beam_sections": "400x700",
            "column_sections": "600x600",
            "core_wall_config": "I_SECTION",
            "lateral_system": "Core wall",
            "design_summary": "Complete",
        }

        result = inject_project_context(DESIGN_REVIEW_TEMPLATE, project_data)

        assert "70m" in result
        assert "20 floors" in result
        assert "C40" in result


# ============================================================================
# TEST create_design_review_prompt Function
# ============================================================================

class TestCreateDesignReviewPrompt:
    """Tests for create_design_review_prompt function."""

    def test_returns_tuple(self):
        """Test function returns tuple of system and user prompts."""
        result = create_design_review_prompt(
            height=70,
            num_floors=20,
            grid_x=9,
            grid_y=9,
            total_area=5000,
            concrete_grade="C40",
            beam_sections="400x700",
            column_sections="600x600",
            core_wall_config="I_SECTION",
            lateral_system="Core wall",
            design_summary="Complete",
        )

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_system_prompt_is_design_review(self):
        """Test system prompt is design review prompt."""
        system_prompt, _ = create_design_review_prompt(
            height=70,
            num_floors=20,
            grid_x=9,
            grid_y=9,
            total_area=5000,
            concrete_grade="C40",
            beam_sections="400x700",
            column_sections="600x600",
            core_wall_config="I_SECTION",
            lateral_system="Core wall",
            design_summary="Complete",
        )

        assert system_prompt == SYSTEM_PROMPT_DESIGN_REVIEW

    def test_user_prompt_contains_parameters(self):
        """Test user prompt contains provided parameters."""
        _, user_prompt = create_design_review_prompt(
            height=85,
            num_floors=25,
            grid_x=10,
            grid_y=8,
            total_area=6000,
            concrete_grade="C50",
            beam_sections="500x800",
            column_sections="700x700",
            core_wall_config="TUBE_WITH_OPENINGS",
            lateral_system="Core wall + Outriggers",
            design_summary="High-rise design",
        )

        assert "85m" in user_prompt
        assert "25 floors" in user_prompt
        assert "C50" in user_prompt
        assert "TUBE_WITH_OPENINGS" in user_prompt
        assert "High-rise design" in user_prompt


# ============================================================================
# TEST HK Code References
# ============================================================================

class TestHKCodeReferences:
    """Tests for HK Code references in prompts."""

    def test_base_prompt_cites_hk_code(self):
        """Test base prompt mentions HK Code citation requirement."""
        assert "HK Code 2013" in SYSTEM_PROMPT_BASE
        assert "clause" in SYSTEM_PROMPT_BASE.lower()

    def test_results_template_cites_code_limits(self):
        """Test results template cites code limits."""
        assert "H/500" in RESULTS_INTERPRETATION_TEMPLATE.template
        assert "0.67f_cu" in RESULTS_INTERPRETATION_TEMPLATE.template
