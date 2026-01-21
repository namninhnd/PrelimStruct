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

__all__ = [
    # Enums
    "LLMProviderType",
    "MessageRole",
    
    # Data models
    "LLMMessage",
    "LLMResponse",
    "LLMUsage",
    
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
    
    # Configuration
    "AIConfig",
]

