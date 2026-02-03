"""
Base LLM Provider with Shared Utilities.

This module provides the BaseLLMProvider class with common utilities
that were previously duplicated across DeepSeekProvider, GrokProvider,
and OpenRouterProvider.

Track 8 Refactoring:
- Moved _parse_response to base class (parameterized by provider_type)
- Added _make_request with retry logic
- Added shared chat() template method
- Providers override _format_request() and _get_endpoint()
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import time
import logging

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from src.ai.providers import (
    LLMProviderType,
    LLMMessage,
    LLMResponse,
    LLMUsage,
    MessageRole,
    AuthenticationError,
    RateLimitError,
    ProviderUnavailableError,
    LLMProviderError,
)

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Base class for LLM providers with shared utilities.
    
    This class implements the Template Method pattern for chat() and
    provides common utilities that were previously duplicated across
    all provider implementations.
    
    Attributes:
        provider_type: The type of provider (must be set by subclasses)
        api_key: The API key for authentication
        base_url: The base URL for API requests
        default_model: The default model to use
        timeout: Request timeout in seconds
        max_retries: Maximum number of retries for failed requests
        retry_base_delay: Base delay for exponential backoff
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        default_model: str,
        timeout: float = 60.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ):
        """Initialize the base LLM provider.
        
        Args:
            api_key: API key for authentication
            base_url: Base URL for API requests
            default_model: Default model to use for completions
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
            retry_base_delay: Base delay for exponential backoff in seconds
        """
        if not api_key:
            raise ValueError("API key is required")

        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._timeout = timeout
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay

    @property
    @abstractmethod
    def provider_type(self) -> LLMProviderType:
        """Return the provider type identifier."""
        pass

    @property
    def default_model(self) -> str:
        """Return the default model name."""
        return self._default_model

    @property
    def base_url(self) -> str:
        """Return the base URL for API requests."""
        return self._base_url

    def _build_headers(self) -> Dict[str, str]:
        """Build HTTP headers for API requests.
        
        Returns:
            Dictionary of HTTP headers
        """
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    @abstractmethod
    def _get_endpoint(self) -> str:
        """Return the API endpoint path for chat completions.
        
        Returns:
            Endpoint path (e.g., "/chat/completions")
        """
        pass

    @abstractmethod
    def _format_request(
        self,
        messages: List[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        json_mode: bool,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Format the request payload for the API.
        
        Args:
            messages: List of messages
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            json_mode: Whether to enforce JSON output
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Formatted request payload dictionary
        """
        pass

    def _make_request(
        self,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request with automatic retry logic.
        
        This method implements the retry loop that was previously
        duplicated in each provider's chat() method.
        
        Args:
            payload: Request payload
            headers: Optional custom headers
            
        Returns:
            Parsed JSON response
            
        Raises:
            ImportError: If httpx is not available
            AuthenticationError: For 401/403 errors
            RateLimitError: For 429 errors
            ProviderUnavailableError: For 5xx errors
            LLMProviderError: For other errors
        """
        if not HTTPX_AVAILABLE:
            raise ImportError(
                "httpx is required for LLM providers. "
                "Install with: pip install httpx"
            )

        url = f"{self._base_url}{self._get_endpoint()}"
        request_headers = headers or self._build_headers()

        last_error: Optional[Exception] = None

        for attempt in range(self._max_retries):
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.post(
                        url,
                        json=payload,
                        headers=request_headers,
                    )

                # Handle specific HTTP status codes
                if response.status_code in (401, 403):
                    raise AuthenticationError(
                        f"Invalid API key for {self.provider_type.value}",
                        provider=self.provider_type,
                        status_code=response.status_code,
                    )
                elif response.status_code == 429:
                    raise RateLimitError(
                        f"Rate limit exceeded for {self.provider_type.value}",
                        provider=self.provider_type,
                        status_code=response.status_code,
                    )
                elif response.status_code >= 500:
                    raise ProviderUnavailableError(
                        f"{self.provider_type.value} server error: {response.status_code}",
                        provider=self.provider_type,
                        status_code=response.status_code,
                    )
                elif response.status_code != 200:
                    error_data = response.json() if response.text else None
                    error_message = (
                        error_data.get("error", {}).get("message", "Unknown error")
                        if error_data else f"HTTP {response.status_code}"
                    )
                    raise LLMProviderError(
                        f"API error: {error_message}",
                        provider=self.provider_type,
                        status_code=response.status_code,
                        response=error_data,
                    )

                return response.json()

            except (AuthenticationError, RateLimitError):
                # Don't retry auth or rate limit errors
                raise
            except ProviderUnavailableError as e:
                last_error = e
                # Exponential backoff
                delay = self._retry_base_delay * (2 ** attempt)
                logger.warning(
                    f"{self.provider_type.value} unavailable (attempt {attempt + 1}), "
                    f"retrying in {delay}s: {e}"
                )
                time.sleep(delay)
            except Exception as e:
                last_error = e
                delay = self._retry_base_delay * (2 ** attempt)
                logger.warning(
                    f"{self.provider_type.value} request failed (attempt {attempt + 1}), "
                    f"retrying in {delay}s: {e}"
                )
                time.sleep(delay)

        # All retries exhausted
        raise ProviderUnavailableError(
            f"{self.provider_type.value} unavailable after {self._max_retries} attempts: {last_error}",
            provider=self.provider_type,
        ) from last_error

    def _parse_response(
        self,
        response_data: Dict[str, Any],
        model: str,
    ) -> LLMResponse:
        """Parse API response into LLMResponse.
        
        This method is now shared across all providers. The only
        difference is the provider_type which is determined by the
        concrete subclass.
        
        Args:
            response_data: Raw API response
            model: Model used for the request
            
        Returns:
            Parsed LLMResponse
            
        Raises:
            LLMProviderError: If response is invalid
        """
        # Extract content from first choice
        choices = response_data.get("choices", [])
        if not choices:
            raise LLMProviderError(
                "No choices in API response",
                provider=self.provider_type,
            )

        choice = choices[0]
        content = choice.get("message", {}).get("content", "")
        finish_reason = choice.get("finish_reason")

        # Extract usage statistics
        usage_data = response_data.get("usage", {})
        usage = LLMUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        return LLMResponse(
            content=content,
            model=response_data.get("model", model),
            provider=self.provider_type,
            usage=usage,
            finish_reason=finish_reason,
            raw_response=response_data,
        )

    def chat(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a chat completion request.
        
        This is the Template Method - it orchestrates the request
        by calling abstract methods that subclasses must implement.
        
        Args:
            messages: List of messages in the conversation
            model: Model to use (defaults to provider's default)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate (None = no limit)
            json_mode: If True, enforce JSON output format
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMResponse with the completion content and metadata
        """
        actual_model = model or self._default_model

        # Format the request (provider-specific)
        payload = self._format_request(
            messages=messages,
            model=actual_model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
            **kwargs,
        )

        # Make the request with retry logic (shared)
        response_data = self._make_request(payload)

        # Parse the response (shared)
        return self._parse_response(response_data, actual_model)

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the provider is available and responding.
        
        Returns:
            True if provider is healthy, False otherwise
        """
        pass

    @abstractmethod
    def calculate_cost(
        self,
        usage: LLMUsage,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> float:
        """Calculate cost for a request based on token usage.
        
        Args:
            usage: Token usage statistics
            model: Model used (default: provider's default model)
            **kwargs: Provider-specific parameters (e.g., cache_hit_tokens)
            
        Returns:
            Estimated cost in USD
        """
        pass

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.
        
        Uses a simple approximation (4 characters per token on average).
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        # Rough estimate: ~4 characters per token for English text
        return len(text) // 4


__all__ = ["BaseLLMProvider"]
