"""
Integration tests for AI Assistant Module (Feature 15).

These tests verify end-to-end workflows across the AI module:
- Provider → Prompt → Response parsing pipeline
- Mesh generation → Quality validation workflow
- Model setup → Boundary conditions → Load combinations
- Optimization → Convergence → AI suggestions
- Results interpretation → Code compliance → Recommendations

Author: PrelimStruct Development Team
Date: 2026-01-22
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch

# AI Module imports
from src.ai.config import AIConfig
from src.ai.providers import (
    LLMProviderType,
    LLMProvider,
    LLMMessage,
    LLMResponse,
    LLMUsage,
    LLMProviderFactory,
)
from src.ai.prompts import (
    PromptType,
    PromptTemplate,
    get_template,
    create_design_review_prompt,
    DESIGN_REVIEW_TEMPLATE,
    OPTIMIZATION_TEMPLATE,
)
from src.ai.response_parser import (
    parse_design_review_response,
    parse_optimization_response,
    safe_parse_design_review,
    safe_parse_optimization,
    DesignReviewResponse,
    OptimizationResponse,
    UnstructuredResponse,
)
from src.ai.llm_service import AIService
from src.ai.mesh_generator import (
    MeshDensity,
    MeshConfig,
    MeshQuality,
    MeshGenerator,
)
from src.ai.auto_setup import (
    SupportType,
    BoundaryCondition,
    ModelSetup,
    ModelSetupConfig,
)
from src.ai.optimizer import (
    DesignVariable,
    OptimizationConstraint,
    OptimizationConfig,
    OptimizationResult,
    OptimizationStatus,
    DesignOptimizer,
    create_beam_optimizer,
    get_ai_optimization_suggestions,
)
from src.ai.results_interpreter import (
    ResultsInterpreter,
    FEMResultsSummary,
    SimplifiedResultsSummary,
    ResultsInterpretation,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_llm_response_design_review():
    """Create a mock LLM response for design review."""
    return LLMResponse(
        content=json.dumps({
            "efficiency_score": 78,
            "concerns": [
                "Core wall stiffness may be insufficient for target drift",
                "Column utilization varies significantly across floors"
            ],
            "code_issues": [
                "Check HK Code 2013 Cl 7.3.2 drift limit compliance"
            ],
            "recommendations": [
                "Consider increasing core wall thickness to 600mm",
                "Redistribute column sizes for uniform utilization",
                "Verify beam deflection at L/250 limit"
            ],
            "summary": "Design is adequate for preliminary stage. Core wall "
                       "stiffness should be verified against drift limits."
        }),
        model="deepseek-chat",
        provider=LLMProviderType.DEEPSEEK,
        usage=LLMUsage(prompt_tokens=500, completion_tokens=150, total_tokens=650),
    )


@pytest.fixture
def mock_llm_response_optimization():
    """Create a mock LLM response for optimization."""
    return LLMResponse(
        content=json.dumps({
            "material_savings": [
                "Reduce beam depth by 50mm in typical floors",
                "Use C35 concrete for non-critical elements"
            ],
            "system_improvements": [
                "Optimize grid spacing for 10m x 8m bays",
                "Consider outrigger system for additional stiffness"
            ],
            "constructability": [
                "Standardize column sizes to reduce formwork costs",
                "Use jump forms for core wall construction"
            ],
            "estimated_savings_percent": 15.5,
            "priority_action": "Standardize column sizes for 8-10% cost reduction"
        }),
        model="deepseek-chat",
        provider=LLMProviderType.DEEPSEEK,
        usage=LLMUsage(prompt_tokens=400, completion_tokens=180, total_tokens=580),
    )


@pytest.fixture
def mock_provider(mock_llm_response_design_review):
    """Create a mock LLM provider."""
    provider = Mock()  # Don't use spec to allow calculate_cost
    provider.chat.return_value = mock_llm_response_design_review
    provider.default_model = "deepseek-chat"
    provider.health_check.return_value = True
    provider.calculate_cost.return_value = 0.00065
    return provider


@pytest.fixture
def sample_project_params():
    """Sample project parameters for testing."""
    return {
        "height": 84.0,  # 28 floors * 3m
        "num_floors": 28,
        "grid_x": 9.0,
        "grid_y": 9.0,
        "total_area": 28 * 81,  # 28 floors * 9m * 9m
        "concrete_grade": "C40",
        "beam_sections": "400x700",
        "column_sections": "700x700",
        "core_wall_config": "I_SECTION",
        "lateral_system": "Core wall + Moment frames",
        "design_summary": "28-story residential tower with I-section core",
    }


@pytest.fixture
def sample_fem_results():
    """Sample FEM results for interpretation testing."""
    return FEMResultsSummary(
        max_beam_moment=(520.0, "Floor 15, Grid B-C"),
        max_beam_shear=(210.0, "Floor 15, Grid B-C"),
        max_column_axial=(9200.0, "Ground Floor, Grid B-2"),
        max_column_moment=(145.0, "Ground Floor, Grid B-2"),
        max_drift=(55.0, 420.0),  # 55mm, H/420
        max_stress=(24.0, "Column B-2, Ground Floor"),
        max_deflection=(38.0, "Floor 15, Grid B-C"),
        critical_load_case="ULS_WIND_3: 1.2Gk + 1.2Qk + 1.2Wk",
        element_count=1850,
        node_count=620,
    )


# ============================================================================
# TEST: CONFIG → PROVIDER → PROMPT → RESPONSE PIPELINE
# ============================================================================

class TestConfigToResponsePipeline:
    """Integration tests for the full AI pipeline."""

    def test_full_design_review_pipeline(
        self, mock_provider, sample_project_params
    ):
        """Test complete design review pipeline: config → provider → response."""
        # 1. Create config
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="test-key-12345678",
            track_costs=True,
        )

        # 2. Create service with mock provider
        service = AIService(config, provider=mock_provider)

        # 3. Get design review
        result = service.get_design_review(**sample_project_params)

        # 4. Verify result
        assert isinstance(result, DesignReviewResponse)
        assert 0 <= result.efficiency_score <= 100
        assert len(result.concerns) >= 1
        assert len(result.recommendations) >= 1
        assert result.summary is not None

        # 5. Verify provider was called correctly
        mock_provider.chat.assert_called_once()
        call_kwargs = mock_provider.chat.call_args.kwargs
        assert call_kwargs["json_mode"] is True
        assert call_kwargs["temperature"] == 0.7

    def test_prompt_generation_integration(self, sample_project_params):
        """Test prompt template → formatted prompt integration."""
        # 1. Get template
        template = get_template(PromptType.DESIGN_REVIEW)
        assert template is DESIGN_REVIEW_TEMPLATE

        # 2. Create design review prompt
        system_prompt, user_prompt = create_design_review_prompt(**sample_project_params)

        # 3. Verify system prompt
        assert "Senior Structural Engineer" in system_prompt
        assert "HK Code 2013" in system_prompt

        # 4. Verify user prompt contains project data
        assert "84m" in user_prompt or "84.0m" in user_prompt
        assert "28 floors" in user_prompt
        assert "C40" in user_prompt
        assert "I_SECTION" in user_prompt

    def test_response_parsing_integration(self, mock_llm_response_design_review):
        """Test LLM response → parsed response integration."""
        # 1. Parse response content
        parsed = safe_parse_design_review(mock_llm_response_design_review.content)

        # 2. Verify structured parsing
        assert isinstance(parsed, DesignReviewResponse)
        assert parsed.efficiency_score == 78
        assert len(parsed.concerns) == 2
        assert len(parsed.code_issues) == 1
        assert len(parsed.recommendations) == 3

    def test_optimization_pipeline(self, mock_provider, mock_llm_response_optimization):
        """Test optimization prompt → response pipeline."""
        mock_provider.chat.return_value = mock_llm_response_optimization

        # Parse response
        parsed = safe_parse_optimization(mock_llm_response_optimization.content)

        # Verify
        assert isinstance(parsed, OptimizationResponse)
        assert parsed.estimated_savings_percent == 15.5
        assert len(parsed.material_savings) >= 1
        assert parsed.priority_action != ""


# ============================================================================
# TEST: MESH GENERATION → QUALITY VALIDATION WORKFLOW
# ============================================================================

class TestMeshGenerationWorkflow:
    """Integration tests for mesh generation workflow."""

    def test_geometry_to_mesh_workflow(self):
        """Test geometry parameters → mesh config → mesh generation."""
        # 1. Create config from geometry
        config = MeshConfig.from_geometry(
            typical_beam_span=9000.0,
            floor_height=3200.0,
            density=MeshDensity.MEDIUM,
        )

        # 2. Create generator
        generator = MeshGenerator(config)

        # 3. Generate beam mesh (positional args)
        start = (0.0, 0.0, 3200.0)
        end = (9000.0, 0.0, 3200.0)
        section_depth = 700.0
        beam_mesh = generator.generate_beam_mesh(start, end, section_depth)

        # 4. Verify mesh
        assert beam_mesh.num_elements >= 4  # At least 4 elements
        assert beam_mesh.num_nodes == beam_mesh.num_elements + 1
        assert beam_mesh.quality.is_valid

    def test_mesh_quality_check_workflow(self):
        """Test mesh quality validation workflow."""
        config = MeshConfig(
            density=MeshDensity.FINE,
            beam_element_size=500.0,
            column_element_size=1000.0,
        )
        generator = MeshGenerator(config)

        # Generate meshes (positional args)
        start = (0.0, 0.0, 3000.0)
        end = (6000.0, 0.0, 3000.0)
        section_depth = 600.0
        beam_mesh = generator.generate_beam_mesh(start, end, section_depth)

        # Verify quality metrics
        assert beam_mesh.quality.aspect_ratio_max < 10.0
        assert beam_mesh.quality.skewness_max < 0.85
        assert beam_mesh.quality.is_valid

    def test_refinement_detection_workflow(self):
        """Test stress concentration → refinement detection workflow."""
        config = MeshConfig.from_geometry(
            typical_beam_span=9000.0,
            floor_height=3000.0,
            density=MeshDensity.MEDIUM,
        )
        generator = MeshGenerator(config)

        # Add refinement zone to test detection
        generator.config.refinement_zones = [(5000.0, 5000.0, 10000.0, 2000.0)]

        # Point inside refinement zone should need refinement
        needs_refinement = generator.check_refinement_needed((5000.0, 5000.0, 10000.0))
        assert needs_refinement is True

        # Point outside zone should not need refinement
        no_refinement = generator.check_refinement_needed((0.0, 0.0, 0.0))
        assert no_refinement is False


# ============================================================================
# TEST: MODEL SETUP → BOUNDARY CONDITIONS → LOAD COMBINATIONS
# ============================================================================

class TestModelSetupWorkflow:
    """Integration tests for model setup workflow."""

    def test_column_support_detection_workflow(self):
        """Test column base → support detection → BC creation workflow."""
        config = ModelSetupConfig(
            base_elevation=0.0,
            support_type_default=SupportType.FIXED,
        )
        setup = ModelSetup(config)

        # Define column positions at base (x, y only, z is inferred from base_elevation)
        column_locations = [
            (0.0, 0.0),
            (9000.0, 0.0),
            (0.0, 9000.0),
            (9000.0, 9000.0),
        ]

        # Detect supports
        supports = setup.detect_column_base_supports(column_locations)

        # Verify all columns have supports
        assert len(supports) == 4
        assert supports[0] == (0.0, 0.0, 0.0)
        assert supports[-1] == (9000.0, 9000.0, 0.0)

    def test_load_combination_generation_workflow(self):
        """Test HK Code 2013 load combination generation workflow."""
        config = ModelSetupConfig(load_combinations_hk2013=True)
        setup = ModelSetup(config)

        # Generate load combinations
        combinations = setup.generate_hk2013_load_combinations()

        # Should have at least 5 standard combinations
        assert len(combinations) >= 5

        # Check ULS1: 1.4Gk + 1.6Qk
        uls1 = next(c for c in combinations if c["name"] == "ULS1")
        assert uls1["factors"]["dead"] == 1.4
        assert uls1["factors"]["live"] == 1.6

        # Check SLS1: 1.0Gk + 1.0Qk
        sls1 = next(c for c in combinations if c["name"] == "SLS1")
        assert sls1["factors"]["dead"] == 1.0
        assert sls1["factors"]["live"] == 1.0

    def test_model_validation_workflow(self):
        """Test model setup → validation workflow."""
        config = ModelSetupConfig()
        setup = ModelSetup(config)

        # Create boundary conditions
        locations = [(1000.0, 2000.0, 0.0)]
        setup.create_boundary_conditions(locations)

        # Validate model
        validation = setup.validate_model_setup()

        assert validation["is_valid"] is True
        assert validation["num_supports"] >= 1


# ============================================================================
# TEST: OPTIMIZATION → CONVERGENCE → AI SUGGESTIONS WORKFLOW
# ============================================================================

class TestOptimizationWorkflow:
    """Integration tests for optimization workflow."""

    def test_beam_optimization_workflow(self):
        """Test beam design → optimization → result workflow."""
        # 1. Create beam optimizer with HK Code constraints
        optimizer = create_beam_optimizer(
            initial_depth=700.0,
            initial_width=350.0,
            span=9000.0,
            max_stress=18.0,  # MPa
            max_deflection=36.0,  # mm (L/250)
        )

        # 2. Run optimization
        result = optimizer.optimize()

        # 3. Verify result
        assert result.status in [OptimizationStatus.CONVERGED, OptimizationStatus.MAX_ITERATIONS]
        assert "depth" in result.optimal_design
        assert "width" in result.optimal_design
        assert result.optimal_design["depth"] >= 300.0  # Minimum bound
        assert result.optimal_design["width"] >= 200.0  # Minimum bound

    def test_optimization_with_constraints_workflow(self):
        """Test constrained optimization workflow."""
        # 1. Create optimizer
        optimizer = DesignOptimizer(OptimizationConfig(max_iterations=50))
        optimizer.add_design_variable("depth", 600.0, 400.0, 1000.0)
        optimizer.add_design_variable("width", 300.0, 200.0, 500.0)

        # 2. Add constraint: depth >= 2 * width
        def aspect_constraint(design):
            return 2 * design["width"] - design["depth"]  # depth >= 2*width

        optimizer.add_constraint("aspect_ratio", aspect_constraint)

        # 3. Set objective: minimize volume
        def objective(design):
            return design["depth"] * design["width"]

        optimizer.set_objective(objective)

        # 4. Optimize
        result = optimizer.optimize()

        # 5. Verify constraints satisfied
        assert result.optimal_design["depth"] >= 2 * result.optimal_design["width"] - 10  # Allow small tolerance

    def test_ai_suggestions_workflow(self):
        """Test optimization result → AI suggestions workflow."""
        # 1. Create optimization result
        result = OptimizationResult(
            status=OptimizationStatus.CONVERGED,
            optimal_design={"depth": 580.0, "width": 290.0},
            objective_value=168200.0,
            iterations=35,
            constraint_violations=[],
            convergence_history=[200000, 180000, 170000, 168200],
            improvement_percent=15.9,
        )

        # 2. Get AI suggestions (rule-based, no actual AI call)
        suggestions = get_ai_optimization_suggestions(result, use_ai=False)

        # 3. Verify suggestions
        assert "Optimization Summary" in suggestions
        assert "15.9%" in suggestions
        assert "converged" in suggestions.lower()  # status.value is lowercase


# ============================================================================
# TEST: RESULTS INTERPRETATION → CODE COMPLIANCE → RECOMMENDATIONS
# ============================================================================

class TestResultsInterpretationWorkflow:
    """Integration tests for results interpretation workflow."""

    def test_full_interpretation_workflow(self, sample_fem_results):
        """Test FEM results → interpretation → recommendations workflow."""
        # 1. Create interpreter
        interpreter = ResultsInterpreter(design_code="HK2013")

        # 2. Create project params
        project_params = {
            "num_floors": 28,
            "f_cu": 40,  # MPa
            "height": 84000.0,  # mm
            "span": 9000.0,  # mm
        }

        # 3. Interpret results
        interpretation = interpreter.interpret_results(
            fem_results=sample_fem_results,
            project_params=project_params,
        )

        # 4. Verify interpretation
        assert interpretation is not None
        assert len(interpretation.summary) > 50
        assert len(interpretation.code_compliance) >= 3  # Drift, stress, deflection
        assert len(interpretation.recommendations) >= 1
        assert interpretation.overall_status in [
            "SATISFACTORY",
            "REQUIRES ATTENTION",
            "REQUIRES IMMEDIATE ACTION",
            "CODE COMPLIANCE ISSUE",
            "REVIEW RECOMMENDED",
        ]

    def test_code_compliance_checking_workflow(self, sample_fem_results):
        """Test FEM results → code compliance checks workflow."""
        interpreter = ResultsInterpreter()
        project_params = {
            "num_floors": 28,
            "f_cu": 40,
            "height": 84000.0,
            "span": 9000.0,
        }

        interpretation = interpreter.interpret_results(
            fem_results=sample_fem_results,
            project_params=project_params,
        )

        # Verify code compliance checks
        check_names = [c.check_name for c in interpretation.code_compliance]
        assert "Lateral Drift" in check_names
        assert "Concrete Stress" in check_names
        assert "Beam Deflection" in check_names

        # Verify each check has proper structure
        for check in interpretation.code_compliance:
            assert check.clause is not None  # Has code clause reference
            assert check.status in ["pass", "fail", "warning"]
            assert check.utilization >= 0

    def test_discrepancy_calculation_workflow(self, sample_fem_results):
        """Test FEM vs simplified comparison workflow."""
        interpreter = ResultsInterpreter()

        # Create simplified results (lower than FEM)
        simplified_results = SimplifiedResultsSummary(
            beam_moment=450.0,  # FEM: 520
            beam_shear=180.0,   # FEM: 210
            column_axial=8000.0,  # FEM: 9200
            column_moment=120.0,  # FEM: 145
            drift_estimate=45.0,  # FEM: 55
            beam_utilization=0.72,
            column_utilization=0.65,
        )

        project_params = {
            "num_floors": 28,
            "f_cu": 40,
            "height": 84000.0,
            "span": 9000.0,
        }

        interpretation = interpreter.interpret_results(
            fem_results=sample_fem_results,
            simplified_results=simplified_results,
            project_params=project_params,
        )

        # Verify discrepancies calculated
        assert len(interpretation.discrepancies) >= 1

        # Check if significant discrepancies flagged (>15%)
        moment_disc = next(
            (d for d in interpretation.discrepancies if d.parameter == "moment"),
            None
        )
        if moment_disc:
            expected_diff = abs(520 - 450) / 450 * 100  # ~15.5%
            assert moment_disc.is_significant  # >15% should be significant


# ============================================================================
# TEST: END-TO-END WORKFLOW
# ============================================================================

class TestEndToEndWorkflow:
    """End-to-end integration tests."""

    def test_full_ai_assisted_design_workflow(
        self, mock_provider, sample_project_params, sample_fem_results
    ):
        """Test complete AI-assisted design workflow."""
        # 1. CONFIG: Create AI configuration
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="test-key-12345678",
            track_costs=True,
        )

        # 2. SERVICE: Create AI service
        service = AIService(config, provider=mock_provider)

        # 3. DESIGN REVIEW: Get AI design review
        review = service.get_design_review(**sample_project_params)
        assert isinstance(review, (DesignReviewResponse, UnstructuredResponse))

        # 4. MESH: Generate mesh
        mesh_config = MeshConfig.from_geometry(
            typical_beam_span=9000.0,
            floor_height=3200.0,
            density=MeshDensity.MEDIUM,
        )
        generator = MeshGenerator(mesh_config)
        start = (0.0, 0.0, 3200.0)
        end = (9000.0, 0.0, 3200.0)
        beam_mesh = generator.generate_beam_mesh(start, end, 700.0)
        assert beam_mesh.quality.is_valid

        # 5. MODEL SETUP: Create boundary conditions and load combinations
        setup_config = ModelSetupConfig()
        setup = ModelSetup(setup_config)
        column_locations = [
            (0.0, 0.0), (9000.0, 0.0),
            (0.0, 9000.0), (9000.0, 9000.0),
        ]
        supports = setup.detect_column_base_supports(column_locations)
        load_combos = setup.generate_hk2013_load_combinations()
        assert len(supports) == 4
        assert len(load_combos) >= 5

        # 6. OPTIMIZATION: Optimize beam design
        optimizer = create_beam_optimizer(
            initial_depth=700.0,
            initial_width=350.0,
            span=9000.0,
            max_stress=18.0,
            max_deflection=36.0,
        )
        opt_result = optimizer.optimize()
        assert opt_result.status in [OptimizationStatus.CONVERGED, OptimizationStatus.MAX_ITERATIONS]

        # 7. INTERPRETATION: Interpret FEM results
        interpreter = ResultsInterpreter()
        project_params = {
            "num_floors": 28,
            "f_cu": 40,
            "height": 84000.0,
            "span": 9000.0,
        }
        interpretation = interpreter.interpret_results(
            fem_results=sample_fem_results,
            project_params=project_params,
        )
        assert interpretation is not None
        assert len(interpretation.code_compliance) >= 3

    def test_error_recovery_workflow(self, mock_provider):
        """Test error handling and recovery in workflows."""
        # Setup provider to fail
        mock_provider.chat.side_effect = Exception("API timeout")

        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="test-key-12345678",
        )
        service = AIService(config, provider=mock_provider)

        # Design review should return UnstructuredResponse on error
        result = service.get_design_review(
            height=84.0, num_floors=28, grid_x=9.0, grid_y=9.0,
            total_area=2268.0, concrete_grade="C40", beam_sections="400x700",
            column_sections="700x700", core_wall_config="I_SECTION",
            lateral_system="Core wall", design_summary="Test",
        )

        assert isinstance(result, UnstructuredResponse)
        assert "Error:" in result.content

        # Interpretation should still work without AI
        interpreter = ResultsInterpreter()
        fem_results = FEMResultsSummary(
            max_drift=(50.0, 500.0),
            max_stress=(20.0, "Test"),
        )
        interpretation = interpreter.interpret_results(
            fem_results=fem_results,
            project_params={"num_floors": 28, "f_cu": 40, "height": 84000.0, "span": 9000.0},
        )

        # Should still produce rule-based interpretation
        assert interpretation is not None
        assert interpretation.confidence_score > 0


# ============================================================================
# TEST: PERFORMANCE BENCHMARKS (Optional)
# ============================================================================

class TestPerformanceBenchmarks:
    """Performance benchmark tests (markers for optional execution)."""

    @pytest.mark.slow
    def test_mesh_generation_performance(self):
        """Benchmark mesh generation for large structures."""
        config = MeshConfig.from_geometry(
            typical_beam_span=9000.0,
            floor_height=3000.0,
            density=MeshDensity.FINE,
        )
        generator = MeshGenerator(config)

        # Generate multiple beams
        import time
        start_time = time.time()

        for i in range(100):
            start = (0.0, i * 9000.0, 3000.0)
            end = (9000.0, i * 9000.0, 3000.0)
            generator.generate_beam_mesh(start, end, 600.0)

        elapsed = time.time() - start_time

        # Should complete in reasonable time (< 5 seconds for 100 beams)
        assert elapsed < 5.0, f"Mesh generation too slow: {elapsed:.2f}s for 100 beams"

    @pytest.mark.slow
    def test_optimization_convergence_performance(self):
        """Benchmark optimization convergence."""
        import time

        optimizer = create_beam_optimizer(
            initial_depth=800.0,
            initial_width=400.0,
            span=9000.0,
            max_stress=18.0,
            max_deflection=36.0,
        )

        start_time = time.time()
        result = optimizer.optimize()
        elapsed = time.time() - start_time

        # Should converge in reasonable time (< 2 seconds)
        assert elapsed < 2.0, f"Optimization too slow: {elapsed:.2f}s"
        assert result.iterations < 100, f"Too many iterations: {result.iterations}"
