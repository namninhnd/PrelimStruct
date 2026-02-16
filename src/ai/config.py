"""
AI Assistant Configuration Module for PrelimStruct.

This module handles configuration management for the AI assistant,
including environment variable loading, provider selection, and
secure API key handling.

Usage:
    config = AIConfig.from_env()
    provider = config.create_provider()
    response = provider.chat([LLMMessage(role="user", content="Hello")])
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import os
import logging

from .providers import (
    LLMProvider,
    LLMProviderType,
    LLMProviderFactory,
    LLMProviderError,
)

logger = logging.getLogger(__name__)


@dataclass
class AIConfig:
    """AI Assistant configuration.

    This class manages all configuration for the AI assistant,
    including provider selection, API keys, and settings.

    Attributes:
        provider_type: The LLM provider to use (deepseek, grok, openrouter)
        api_key: API key for the selected provider
        base_url: Optional custom base URL (for resellers)
        model: Optional model override (uses provider default if None)
        timeout: Request timeout in seconds (default: 60)
        max_retries: Maximum retry attempts (default: 3)
        track_costs: Enable cost tracking and logging (default: True)
        monthly_budget: Monthly budget limit in USD (0 = unlimited)
        site_url: Optional site URL for OpenRouter rankings
        site_name: Optional site name for OpenRouter rankings
    """

    provider_type: LLMProviderType
    api_key: str
    base_url: Optional[str] = None
    model: Optional[str] = None
    timeout: float = 60.0
    max_retries: int = 3
    track_costs: bool = True
    monthly_budget: float = 0.0
    site_url: Optional[str] = None
    site_name: Optional[str] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.api_key:
            raise ValueError("API key is required")

        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")

        if self.max_retries < 0:
            raise ValueError("Max retries cannot be negative")

        if self.monthly_budget < 0:
            raise ValueError("Monthly budget cannot be negative")

    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "AIConfig":
        """Load configuration from environment variables.

        Args:
            env_file: Optional path to .env file (default: .env in project root)

        Returns:
            AIConfig instance with loaded configuration

        Raises:
            ValueError: If required environment variables are missing
            FileNotFoundError: If env_file is specified but doesn't exist

        Environment Variables:
            LLM_PROVIDER: Provider type (deepseek, grok, openrouter)
            {PROVIDER}_API_KEY: API key for the provider
            {PROVIDER}_BASE_URL: Optional custom base URL
            LLM_MODEL: Optional model override
            LLM_TIMEOUT: Request timeout in seconds
            LLM_MAX_RETRIES: Maximum retry attempts
            LLM_TRACK_COSTS: Enable cost tracking (true/false)
            LLM_MONTHLY_BUDGET: Monthly budget limit in USD
        """
        # Load .env file if specified
        if env_file:
            cls._load_env_file(env_file)

        # Get provider type
        provider_str = os.getenv("LLM_PROVIDER", "gemini").lower()
        try:
            provider_type = LLMProviderType(provider_str)
        except ValueError:
            raise ValueError(
                f"Invalid LLM_PROVIDER: {provider_str}. "
                f"Must be one of: gemini, deepseek, grok, openrouter"
            )

        # Get API key for the selected provider
        api_key_env = f"{provider_str.upper()}_API_KEY"
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(
                f"Missing API key: {api_key_env} environment variable is required"
            )

        # Get optional base URL override
        base_url_env = f"{provider_str.upper()}_BASE_URL"
        base_url = os.getenv(base_url_env) or None

        # Get other settings
        model = os.getenv("LLM_MODEL") or None
        timeout = float(os.getenv("LLM_TIMEOUT", "60"))
        max_retries = int(os.getenv("LLM_MAX_RETRIES", "3"))
        track_costs = os.getenv("LLM_TRACK_COSTS", "true").lower() == "true"
        monthly_budget = float(os.getenv("LLM_MONTHLY_BUDGET", "0"))

        # OpenRouter-specific settings
        site_url = os.getenv("OPENROUTER_SITE_URL") or None
        site_name = os.getenv("OPENROUTER_SITE_NAME") or None

        return cls(
            provider_type=provider_type,
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=timeout,
            max_retries=max_retries,
            track_costs=track_costs,
            monthly_budget=monthly_budget,
            site_url=site_url,
            site_name=site_name,
        )

    @staticmethod
    def _load_env_file(env_file: str) -> None:
        """Load environment variables from .env file.

        Args:
            env_file: Path to .env file

        Raises:
            FileNotFoundError: If env_file doesn't exist
        """
        try:
            from dotenv import load_dotenv
            if not load_dotenv(env_file):
                raise FileNotFoundError(f".env file not found: {env_file}")
        except ImportError:
            raise ImportError(
                "python-dotenv is required for .env file support. "
                "Install with: pip install python-dotenv"
            )

    def create_provider(self) -> LLMProvider:
        """Create an LLM provider instance from this configuration.

        Returns:
            Initialized LLMProvider instance

        Raises:
            LLMProviderError: If provider creation fails
        """
        kwargs: Dict[str, Any] = {
            "max_retries": self.max_retries,
        }

        # Add OpenRouter-specific kwargs
        if self.provider_type == LLMProviderType.OPENROUTER:
            if self.site_url:
                kwargs["site_url"] = self.site_url
            if self.site_name:
                kwargs["site_name"] = self.site_name

        provider = LLMProviderFactory.create(
            provider_type=self.provider_type,
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            timeout=self.timeout,
            **kwargs,
        )

        logger.info(
            f"Created {self.provider_type.value} provider "
            f"(model: {provider.default_model})"
        )

        return provider

    def health_check(self) -> bool:
        """Check if the configured provider is available.

        Returns:
            True if provider is healthy, False otherwise
        """
        try:
            provider = self.create_provider()
            return provider.health_check()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def mask_api_key(self) -> str:
        """Return masked API key for logging (shows only first 8 chars).

        Returns:
            Masked API key string
        """
        if len(self.api_key) <= 12:
            return "***"
        return f"{self.api_key[:8]}...{self.api_key[-4:]}"

    def __repr__(self) -> str:
        """String representation with masked API key."""
        return (
            f"AIConfig("
            f"provider={self.provider_type.value}, "
            f"model={self.model or 'default'}, "
            f"api_key={self.mask_api_key()})"
        )
