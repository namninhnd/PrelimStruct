"""
AI Assistant Module for PrelimStruct

This module provides AI-powered assistance for structural design using
multiple LLM providers (DeepSeek, Grok, OpenRouter) with a provider-agnostic
interface.

Supported Providers:
- DeepSeek (PRIMARY): api.deepseek.com, 128K context
- Grok (BACKUP): api.x.ai, 2M context
- OpenRouter (FALLBACK): openrouter.ai, 300+ models

Usage:
    from src.ai import LLMProviderFactory, LLMProviderType, LLMMessage

    # Create provider
    provider = LLMProviderFactory.create(
        provider_type=LLMProviderType.DEEPSEEK,
        api_key="your-api-key"
    )

    # Send message
    messages = [LLMMessage(role="user", content="Hello")]
    response = provider.chat(messages)
    print(response.content)
"""

from .providers import (
    LLMProviderType,
    LLMMessage,
    LLMResponse,
    LLMUsage,
    LLMProvider,
    LLMProviderFactory,
    DeepSeekProvider,
    LLMProviderError,
    RateLimitError,
    AuthenticationError,
    ProviderUnavailableError,
    DEEPSEEK_PRICING,
)

__all__ = [
    # Enums and data classes
    "LLMProviderType",
    "LLMMessage",
    "LLMResponse",
    "LLMUsage",
    # Base class and factory
    "LLMProvider",
    "LLMProviderFactory",
    # Concrete providers
    "DeepSeekProvider",
    # Errors
    "LLMProviderError",
    "RateLimitError",
    "AuthenticationError",
    "ProviderUnavailableError",
    # Pricing
    "DEEPSEEK_PRICING",
]
