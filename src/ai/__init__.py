"""
AI Assistant Module for PrelimStruct v3.0

This module provides AI-powered features for structural design automation,
including LLM providers, prompt engineering, response parsing, mesh generation,
model setup, design optimization, and results interpretation.

Features:
- Feature 11: AI Assistant Core Infrastructure (DeepSeek, Grok, OpenRouter)
- Feature 12: AI-Assisted Mesh Generation & Model Setup
- Feature 13: AI-Assisted Design Optimization
- Feature 14: AI Results Interpretation & Recommendations (NEW)

Components:
- LLM Providers: DeepSeekProvider, GrokProvider, OpenRouterProvider
- Configuration: AIConfig
- Prompt Templates: System prompts and templates for HK Code 2013
- Response Parsing: Structured JSON response parsing
- AI Service: High-level service interface
- Mesh Generation: Automated mesh generation with quality checks
- Model Setup: Smart boundary condition and load application detection
- Design Optimization: Gradient-based optimization with AI guidance
- Results Interpreter: FEM results analysis and recommendations (NEW)

Usage:
    from src.ai import AIService, DesignOptimizer, ResultsInterpreter

    # AI Assistant
    service = AIService.from_env()
    review = service.get_design_review(...)

    # Design Optimization
    optimizer = DesignOptimizer()
    optimizer.add_design_variable("depth", 600, 300, 1200)
    optimizer.set_objective(cost_func)
    result = optimizer.optimize()

    # Results Interpretation
    interpreter = ResultsInterpreter(ai_service=service)
    interpretation = interpreter.interpret_results(fem_results, simplified_results)
    print(interpretation.summary)
"""

# Provider Infrastructure
from .providers import (
    LLMProvider,
    LLMProviderType,
    LLMMessage,
    LLMResponse,
    LLMUsage,
    MessageRole,
    DeepSeekProvider,
    GrokProvider,
    OpenRouterProvider,
    LLMProviderError,
    RateLimitError,
    AuthenticationError,
    ProviderUnavailableError,
    DEEPSEEK_PRICING,
    GROK_PRICING,
    OPENROUTER_PRICING,
)

# Configuration
from .config import AIConfig

# Prompts
from .prompts import (
    PromptTemplate,
    PromptType,
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
    create_design_review_prompt,
    inject_project_context,
)

# Response Parsing
from .response_parser import (
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

# AI Service
from .llm_service import AIService

# Mesh Generation (Feature 12)
from .mesh_generator import (
    MeshDensity,
    ElementType,
    MeshConfig,
    MeshQuality,
    MeshElement,
    Mesh,
    MeshGenerator,
)

# Model Setup (Feature 12)
from .auto_setup import (
    SupportType,
    LoadType,
    BoundaryCondition,
    LoadCase,
    ModelSetupConfig,
    ModelSetup,
)

# Design Optimization (Feature 13)
from .optimizer import (
    OptimizationObjective,
    OptimizationStatus,
    DesignVariable,
    OptimizationConstraint,
    OptimizationResult,
    OptimizationConfig,
    DesignOptimizer,
    create_beam_optimizer,
    get_ai_optimization_suggestions,
)

# Results Interpretation (Feature 14 - NEW)
from .results_interpreter import (
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

__all__ = [
    # Providers
    "LLMProvider",
    "LLMProviderType",
    "LLMMessage",
    "LLMResponse",
    "LLMUsage",
    "MessageRole",
    "DeepSeekProvider",
    "GrokProvider",
    "OpenRouterProvider",
    "LLMProviderError",
    "RateLimitError",
    "AuthenticationError",
    "ProviderUnavailableError",
    "DEEPSEEK_PRICING",
    "GROK_PRICING",
    "OPENROUTER_PRICING",
    # Configuration
    "AIConfig",
    # Prompts
    "PromptTemplate",
    "PromptType",
    "SYSTEM_PROMPT_BASE",
    "SYSTEM_PROMPT_DESIGN_REVIEW",
    "SYSTEM_PROMPT_RESULTS",
    "SYSTEM_PROMPT_OPTIMIZATION",
    "DESIGN_REVIEW_TEMPLATE",
    "RESULTS_INTERPRETATION_TEMPLATE",
    "OPTIMIZATION_TEMPLATE",
    "MODEL_SETUP_TEMPLATE",
    "MESH_GENERATION_TEMPLATE",
    "get_template",
    "create_design_review_prompt",
    "inject_project_context",
    # Response Parsing
    "DesignReviewResponse",
    "OptimizationResponse",
    "UnstructuredResponse",
    "PriorityLevel",
    "parse_design_review_response",
    "parse_optimization_response",
    "safe_parse_design_review",
    "safe_parse_optimization",
    "extract_json_from_markdown",
    # AI Service
    "AIService",
    # Mesh Generation
    "MeshDensity",
    "ElementType",
    "MeshConfig",
    "MeshQuality",
    "MeshElement",
    "Mesh",
    "MeshGenerator",
    # Model Setup
    "SupportType",
    "LoadType",
    "BoundaryCondition",
    "LoadCase",
    "ModelSetupConfig",
    "ModelSetup",
    # Design Optimization
    "OptimizationObjective",
    "OptimizationStatus",
    "DesignVariable",
    "OptimizationConstraint",
    "OptimizationResult",
    "OptimizationConfig",
    "DesignOptimizer",
    "create_beam_optimizer",
    "get_ai_optimization_suggestions",
    # Results Interpretation (NEW)
    "ResultsInterpreter",
    "ResultsInterpretation",
    "FEMResultsSummary",
    "SimplifiedResultsSummary",
    "CriticalElement",
    "DesignDiscrepancy",
    "CodeComplianceCheck",
    "CriticalityLevel",
    "IssueCategory",
    "interpret_fem_results",
    "create_fem_summary_from_dict",
    "create_simplified_summary_from_project",
]
