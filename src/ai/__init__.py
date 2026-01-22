"""
AI Assistant Module for PrelimStruct.

This module provides AI-powered features for structural engineering:
- LLM provider abstraction (DeepSeek, Grok, OpenRouter)
- Configuration management
- Prompt engineering for structural engineering tasks
- Results interpretation and recommendations

Usage:
    from src.ai import AIConfig, LLMMessage
    
    # Load configuration from environment
    config = AIConfig.from_env()
    
    # Create provider and send request
    provider = config.create_provider()
    response = provider.chat([
        LLMMessage(role="system", content="You are a structural engineer."),
        LLMMessage(role="user", content="Explain moment redistribution.")
    ])
"""

from .providers import (
    LLMProviderType,
    MessageRole,
    LLMMessage,
    LLMResponse,
    LLMUsage,
    LLMProvider,
    LLMProviderFactory,
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

from .config import AIConfig

from .prompts import (
    PromptType,
    PromptTemplate,
    get_template,
    inject_project_context,
    create_design_review_prompt,
    SYSTEM_PROMPT_BASE,
    SYSTEM_PROMPT_DESIGN_REVIEW,
    SYSTEM_PROMPT_RESULTS,
    SYSTEM_PROMPT_OPTIMIZATION,
)

from .response_parser import (
    PriorityLevel,
    DesignReviewResponse,
    OptimizationResponse,
    UnstructuredResponse,
    parse_design_review_response,
    parse_optimization_response,
    safe_parse_design_review,
    safe_parse_optimization,
    extract_json_from_markdown,
)

from .llm_service import AIService

from .mesh_generator import (
    MeshDensity,
    ElementType,
    MeshQuality,
    MeshConfig,
    MeshElement,
    Mesh,
    MeshGenerator,
)

from .auto_setup import (
    SupportType,
    LoadType,
    BoundaryCondition,
    LoadCase,
    ModelSetupConfig,
    ModelSetup,
)

__all__ = [
    # Enums
    "LLMProviderType",
    "MessageRole",
    "PromptType",
    "PriorityLevel",
    "MeshDensity",
    "ElementType",
    "SupportType",
    "LoadType",
    
    # Data models
    "LLMMessage",
    "LLMResponse",
    "LLMUsage",
    "PromptTemplate",
    "DesignReviewResponse",
    "OptimizationResponse",
    "UnstructuredResponse",
    "MeshQuality",
    "MeshConfig",
    "MeshElement",
    "Mesh",
    "BoundaryCondition",
    "LoadCase",
    "ModelSetupConfig",
    
    # Base class and factory
    "LLMProvider",
    "LLMProviderFactory",
    
    # Concrete providers
    "DeepSeekProvider",
    "GrokProvider",
    "OpenRouterProvider",
    
    # Errors
    "LLMProviderError",
    "RateLimitError",
    "AuthenticationError",
    "ProviderUnavailableError",
    
    # Pricing constants
    "DEEPSEEK_PRICING",
    "GROK_PRICING",
    "OPENROUTER_PRICING",
    
    # Configuration and Service
    "AIConfig",
    "AIService",
    
    # Prompts
    "get_template",
    "inject_project_context",
    "create_design_review_prompt",
    "SYSTEM_PROMPT_BASE",
    "SYSTEM_PROMPT_DESIGN_REVIEW",
    "SYSTEM_PROMPT_RESULTS",
    "SYSTEM_PROMPT_OPTIMIZATION",
    
    # Response parsing
    "parse_design_review_response",
    "parse_optimization_response",
    "safe_parse_design_review",
    "safe_parse_optimization",
    "extract_json_from_markdown",
    
    # Mesh generation and model setup
    "MeshGenerator",
    "ModelSetup",
]

