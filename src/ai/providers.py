"""
LLM Provider Interface and Factory for PrelimStruct AI Assistant.

This module provides a provider-agnostic interface for interacting with
various LLM APIs (DeepSeek, Grok, OpenRouter) using an OpenAI-compatible
API format for easy provider swapping.

Supported Providers:
- DeepSeek (PRIMARY): api.deepseek.com, deepseek-chat model, 128K context
- Grok (BACKUP): api.x.ai, grok-4-fast model, 2M context
- OpenRouter (FALLBACK): openrouter.ai, 300+ models

Usage:
    provider = LLMProviderFactory.create(
        provider_type=LLMProviderType.DEEPSEEK,
        api_key="your-api-key"
    )
    response = provider.chat([LLMMessage(role="user", content="Hello")])
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
import time
import logging

# Configure logging - avoid logging sensitive data (API keys)
logger = logging.getLogger(__name__)


class LLMProviderType(Enum):
    """Supported LLM provider types.

    Attributes:
        DEEPSEEK: DeepSeek API (api.deepseek.com) - PRIMARY for Hong Kong
        GROK: xAI Grok API (api.x.ai) - BACKUP with 2M context
        OPENROUTER: OpenRouter gateway (openrouter.ai) - Gateway to 300+ models
    """
    DEEPSEEK = "deepseek"
    GROK = "grok"
    OPENROUTER = "openrouter"


class MessageRole(Enum):
    """Message role types for chat completion.

    Follows OpenAI-compatible API format.
    """
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class LLMMessage:
    """A message in a chat conversation.

    Follows OpenAI-compatible message format for easy provider swapping.

    Attributes:
        role: The role of the message sender (system, user, or assistant)
        content: The text content of the message
        name: Optional name for the sender (used in multi-turn conversations)
    """
    role: str
    content: str
    name: Optional[str] = None

    def __post_init__(self):
        """Validate role is one of the allowed values."""
        valid_roles = {r.value for r in MessageRole}
        if self.role not in valid_roles:
            raise ValueError(
                f"Invalid role '{self.role}'. Must be one of: {valid_roles}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API request.

        Returns:
            Dictionary with role and content, plus name if provided.
        """
        result: Dict[str, Any] = {
            "role": self.role,
            "content": self.content,
        }
        if self.name:
            result["name"] = self.name
        return result


@dataclass
class LLMUsage:
    """Token usage statistics from LLM response.

    Attributes:
        prompt_tokens: Number of tokens in the input prompt
        completion_tokens: Number of tokens in the completion
        total_tokens: Total tokens used (prompt + completion)
    """
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class LLMResponse:
    """Response from an LLM chat completion.

    Attributes:
        content: The text content of the response
        model: The model used for generation
        provider: The provider type that generated this response
        usage: Token usage statistics (if available)
        finish_reason: Why the completion stopped (stop, length, etc.)
        raw_response: The raw response from the API (for debugging)
    """
    content: str
    model: str
    provider: LLMProviderType
    usage: Optional[LLMUsage] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = field(default=None, repr=False)

    @property
    def total_tokens(self) -> int:
        """Total tokens used in this response.

        Returns:
            Total token count, or 0 if usage not available.
        """
        return self.usage.total_tokens if self.usage else 0


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    All LLM providers must implement this interface to ensure
    consistent behavior across different APIs.

    The interface follows OpenAI-compatible API format for easy
    provider swapping without code changes.

    Attributes:
        provider_type: The type of provider (for identification)
        api_key: The API key for authentication
        base_url: The base URL for API requests
        default_model: The default model to use
        timeout: Request timeout in seconds
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        default_model: str,
        timeout: float = 60.0,
    ):
        """Initialize the LLM provider.

        Args:
            api_key: API key for authentication
            base_url: Base URL for API requests
            default_model: Default model to use for completions
            timeout: Request timeout in seconds (default 60)
        """
        if not api_key:
            raise ValueError("API key is required")

        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._timeout = timeout

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

    @abstractmethod
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

        Args:
            messages: List of messages in the conversation
            model: Model to use (defaults to provider's default)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate (None = no limit)
            json_mode: If True, enforce JSON output format
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse with the completion content and metadata

        Raises:
            LLMProviderError: If the API request fails
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the provider is available and responding.

        Returns:
            True if provider is healthy, False otherwise
        """
        pass

    def _build_headers(self) -> Dict[str, str]:
        """Build HTTP headers for API requests.

        Returns:
            Dictionary of HTTP headers
        """
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }


class LLMProviderError(Exception):
    """Base exception for LLM provider errors.

    Attributes:
        message: Error description
        provider: The provider that raised the error
        status_code: HTTP status code (if applicable)
        response: Raw response data (if available)
    """

    def __init__(
        self,
        message: str,
        provider: Optional[LLMProviderType] = None,
        status_code: Optional[int] = None,
        response: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.status_code = status_code
        self.response = response

    def __str__(self) -> str:
        parts = [self.message]
        if self.provider:
            parts.insert(0, f"[{self.provider.value}]")
        if self.status_code:
            parts.append(f"(HTTP {self.status_code})")
        return " ".join(parts)


class RateLimitError(LLMProviderError):
    """Raised when API rate limit is exceeded (HTTP 429)."""
    pass


class AuthenticationError(LLMProviderError):
    """Raised when API authentication fails (HTTP 401/403)."""
    pass


class ProviderUnavailableError(LLMProviderError):
    """Raised when provider is temporarily unavailable (HTTP 500/502/503)."""
    pass


# DeepSeek API pricing (as of 2026-01)
# https://api-docs.deepseek.com/quick_start/pricing
DEEPSEEK_PRICING = {
    "deepseek-chat": {
        "input_per_million": 0.14,   # $0.14 per 1M input tokens (cache miss)
        "output_per_million": 0.28,  # $0.28 per 1M output tokens
        "cache_hit_per_million": 0.014,  # $0.014 per 1M cached input tokens
    },
    "deepseek-reasoner": {
        "input_per_million": 0.55,
        "output_per_million": 2.19,
        "cache_hit_per_million": 0.055,
    },
}

# Grok API pricing (as of 2026-01)
# https://docs.x.ai/docs/pricing
GROK_PRICING = {
    "grok-4-fast": {
        "input_per_million": 1.00,   # $1.00 per 1M input tokens
        "output_per_million": 3.00,  # $3.00 per 1M output tokens
        "cache_hit_per_million": 0.10,  # $0.10 per 1M cached input tokens (estimated)
    },
    "grok-2": {
        "input_per_million": 2.00,
        "output_per_million": 10.00,
        "cache_hit_per_million": 0.20,
    },
}


class DeepSeekProvider(LLMProvider):
    """DeepSeek API provider implementation.

    DeepSeek is the PRIMARY provider for Hong Kong users due to:
    - No geo-restrictions in HK
    - Competitive pricing ($0.14-0.28 per 1M tokens)
    - 128K context window
    - OpenAI-compatible API format

    API Reference: https://api-docs.deepseek.com

    Features:
    - Chat completion with streaming support (optional)
    - JSON mode for structured outputs
    - Automatic retry with exponential backoff
    - Token counting and cost calculation
    - Health check endpoint

    Usage:
        provider = DeepSeekProvider(api_key="your-key")
        response = provider.chat([LLMMessage(role="user", content="Hello")])
        print(f"Cost: ${provider.calculate_cost(response.usage):.6f}")
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com/v1",
        default_model: str = "deepseek-chat",
        timeout: float = 60.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ):
        """Initialize DeepSeek provider.

        Args:
            api_key: DeepSeek API key
            base_url: API base URL (default: api.deepseek.com)
            default_model: Default model (default: deepseek-chat)
            timeout: Request timeout in seconds (default: 60)
            max_retries: Maximum retry attempts for failed requests (default: 3)
            retry_base_delay: Base delay for exponential backoff in seconds (default: 1.0)
        """
        super().__init__(api_key, base_url, default_model, timeout)
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.DEEPSEEK

    def chat(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a chat completion request to DeepSeek API.

        Args:
            messages: List of messages in the conversation
            model: Model to use (default: deepseek-chat)
            temperature: Sampling temperature 0.0-2.0 (default: 0.7)
            max_tokens: Maximum tokens to generate (default: None = no limit)
            json_mode: If True, enforce JSON output format
            **kwargs: Additional parameters passed to the API

        Returns:
            LLMResponse with completion content and metadata

        Raises:
            AuthenticationError: Invalid API key (401/403)
            RateLimitError: Rate limit exceeded (429)
            ProviderUnavailableError: Server error (500/502/503)
            LLMProviderError: Other API errors
        """
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx is required for DeepSeekProvider. "
                "Install with: pip install httpx"
            )

        actual_model = model or self._default_model

        # Build request payload (OpenAI-compatible format)
        payload: Dict[str, Any] = {
            "model": actual_model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature,
        }

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        # Enable JSON mode if requested
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        # Add any additional kwargs
        payload.update(kwargs)

        # Make request with retry logic
        response_data = self._make_request_with_retry(
            endpoint="/chat/completions",
            payload=payload,
        )

        # Parse response
        return self._parse_response(response_data, actual_model)

    def _make_request_with_retry(
        self,
        endpoint: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Make HTTP request with exponential backoff retry.

        Args:
            endpoint: API endpoint path
            payload: Request payload

        Returns:
            Parsed JSON response

        Raises:
            LLMProviderError: If all retries fail
        """
        import httpx

        url = f"{self._base_url}{endpoint}"
        headers = self._build_headers()

        last_error: Optional[Exception] = None

        for attempt in range(self._max_retries + 1):
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.post(url, json=payload, headers=headers)

                # Handle response based on status code
                if response.status_code == 200:
                    return response.json()

                # Handle specific error codes
                self._handle_error_response(response)

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(
                    f"DeepSeek request timeout (attempt {attempt + 1}/{self._max_retries + 1})"
                )

            except httpx.RequestError as e:
                last_error = e
                logger.warning(
                    f"DeepSeek request error (attempt {attempt + 1}/{self._max_retries + 1}): {e}"
                )

            except RateLimitError as e:
                # Retry rate limit errors with backoff
                last_error = e
                if attempt < self._max_retries:
                    delay = self._calculate_backoff_delay(attempt)
                    logger.info(f"Rate limited, retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                raise

            except ProviderUnavailableError as e:
                # Retry server errors with backoff
                last_error = e
                if attempt < self._max_retries:
                    delay = self._calculate_backoff_delay(attempt)
                    logger.info(f"Server error, retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                raise

            except (AuthenticationError, LLMProviderError):
                # Don't retry auth errors or other client errors
                raise

            # Calculate backoff delay for next attempt
            if attempt < self._max_retries:
                delay = self._calculate_backoff_delay(attempt)
                time.sleep(delay)

        # All retries exhausted
        raise LLMProviderError(
            f"Request failed after {self._max_retries + 1} attempts: {last_error}",
            provider=LLMProviderType.DEEPSEEK,
        )

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds with jitter
        """
        import random
        # Exponential backoff: base * 2^attempt with jitter
        delay = self._retry_base_delay * (2 ** attempt)
        # Add random jitter (0-25% of delay)
        jitter = delay * random.uniform(0, 0.25)
        return delay + jitter

    def _handle_error_response(self, response: "httpx.Response") -> None:
        """Handle error HTTP responses.

        Args:
            response: HTTP response object

        Raises:
            AuthenticationError: For 401/403
            RateLimitError: For 429
            ProviderUnavailableError: For 500/502/503
            LLMProviderError: For other errors
        """
        status_code = response.status_code

        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", response.text)
        except Exception:
            error_data = None
            error_message = response.text

        if status_code in (401, 403):
            raise AuthenticationError(
                f"Authentication failed: {error_message}",
                provider=LLMProviderType.DEEPSEEK,
                status_code=status_code,
                response=error_data,
            )
        elif status_code == 429:
            raise RateLimitError(
                f"Rate limit exceeded: {error_message}",
                provider=LLMProviderType.DEEPSEEK,
                status_code=status_code,
                response=error_data,
            )
        elif status_code in (500, 502, 503):
            raise ProviderUnavailableError(
                f"Server error: {error_message}",
                provider=LLMProviderType.DEEPSEEK,
                status_code=status_code,
                response=error_data,
            )
        else:
            raise LLMProviderError(
                f"API error: {error_message}",
                provider=LLMProviderType.DEEPSEEK,
                status_code=status_code,
                response=error_data,
            )

    def _parse_response(
        self,
        response_data: Dict[str, Any],
        model: str,
    ) -> LLMResponse:
        """Parse API response into LLMResponse.

        Args:
            response_data: Raw API response
            model: Model used for the request

        Returns:
            Parsed LLMResponse
        """
        # Extract content from first choice
        choices = response_data.get("choices", [])
        if not choices:
            raise LLMProviderError(
                "No choices in API response",
                provider=LLMProviderType.DEEPSEEK,
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
            provider=LLMProviderType.DEEPSEEK,
            usage=usage,
            finish_reason=finish_reason,
            raw_response=response_data,
        )

    def health_check(self) -> bool:
        """Check if DeepSeek API is available.

        Sends a minimal request to verify connectivity.

        Returns:
            True if API is responding, False otherwise
        """
        try:
            # Send minimal request
            response = self.chat(
                messages=[LLMMessage(role="user", content="ping")],
                max_tokens=1,
                temperature=0,
            )
            return len(response.content) > 0
        except Exception as e:
            logger.warning(f"DeepSeek health check failed: {e}")
            return False

    def calculate_cost(
        self,
        usage: LLMUsage,
        model: Optional[str] = None,
        cache_hit_tokens: int = 0,
    ) -> float:
        """Calculate cost for a request based on token usage.

        Args:
            usage: Token usage statistics
            model: Model used (default: provider's default model)
            cache_hit_tokens: Number of input tokens that hit cache

        Returns:
            Estimated cost in USD
        """
        actual_model = model or self._default_model

        # Get pricing for model (default to deepseek-chat pricing)
        pricing = DEEPSEEK_PRICING.get(
            actual_model,
            DEEPSEEK_PRICING["deepseek-chat"]
        )

        # Calculate input cost (split between cache hit and miss)
        cache_miss_tokens = max(0, usage.prompt_tokens - cache_hit_tokens)
        input_cost = (
            (cache_miss_tokens / 1_000_000) * pricing["input_per_million"] +
            (cache_hit_tokens / 1_000_000) * pricing["cache_hit_per_million"]
        )

        # Calculate output cost
        output_cost = (
            usage.completion_tokens / 1_000_000
        ) * pricing["output_per_million"]

        return input_cost + output_cost

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Uses a simple approximation (4 characters per token on average).
        For precise counting, use tiktoken with cl100k_base encoding.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        # Rough estimate: ~4 characters per token for English text
        # DeepSeek uses a similar tokenizer to GPT-4
        return len(text) // 4


class GrokProvider(LLMProvider):
    """xAI Grok API provider implementation.

    Grok is the BACKUP provider for when DeepSeek is unavailable:
    - OpenAI-compatible API format (api.x.ai/v1)
    - 2M context window (much larger than DeepSeek's 128K)
    - Support for structured outputs via Pydantic
    - Competitive pricing for long contexts

    API Reference: https://docs.x.ai

    Features:
    - Chat completion with JSON mode
    - Automatic retry with exponential backoff
    - Token counting and cost calculation
    - Health check endpoint
    - Support for Pydantic structured outputs

    Usage:
        provider = GrokProvider(api_key="your-key")
        response = provider.chat([LLMMessage(role="user", content="Hello")])
        print(f"Cost: ${provider.calculate_cost(response.usage):.6f}")
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.x.ai/v1",
        default_model: str = "grok-4-fast",
        timeout: float = 60.0,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ):
        """Initialize Grok provider.

        Args:
            api_key: xAI API key
            base_url: API base URL (default: api.x.ai)
            default_model: Default model (default: grok-4-fast)
            timeout: Request timeout in seconds (default: 60)
            max_retries: Maximum retry attempts for failed requests (default: 3)
            retry_base_delay: Base delay for exponential backoff in seconds (default: 1.0)
        """
        super().__init__(api_key, base_url, default_model, timeout)
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay

    @property
    def provider_type(self) -> LLMProviderType:
        return LLMProviderType.GROK

    def chat(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a chat completion request to Grok API.

        Args:
            messages: List of messages in the conversation
            model: Model to use (default: grok-4-fast)
            temperature: Sampling temperature 0.0-2.0 (default: 0.7)
            max_tokens: Maximum tokens to generate (default: None = no limit)
            json_mode: If True, enforce JSON output format
            **kwargs: Additional parameters passed to the API

        Returns:
            LLMResponse with completion content and metadata

        Raises:
            AuthenticationError: Invalid API key (401/403)
            RateLimitError: Rate limit exceeded (429)
            ProviderUnavailableError: Server error (500/502/503)
            LLMProviderError: Other API errors
        """
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx is required for GrokProvider. "
                "Install with: pip install httpx"
            )

        actual_model = model or self._default_model

        # Build request payload (OpenAI-compatible format)
        payload: Dict[str, Any] = {
            "model": actual_model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature,
        }

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        # Enable JSON mode if requested
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        # Add any additional kwargs
        payload.update(kwargs)

        # Make request with retry logic
        response_data = self._make_request_with_retry(
            endpoint="/chat/completions",
            payload=payload,
        )

        # Parse response
        return self._parse_response(response_data, actual_model)

    def _make_request_with_retry(
        self,
        endpoint: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Make HTTP request with exponential backoff retry.

        Args:
            endpoint: API endpoint path
            payload: Request payload

        Returns:
            Parsed JSON response

        Raises:
            LLMProviderError: If all retries fail
        """
        import httpx

        url = f"{self._base_url}{endpoint}"
        headers = self._build_headers()

        last_error: Optional[Exception] = None

        for attempt in range(self._max_retries + 1):
            try:
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.post(url, json=payload, headers=headers)

                # Handle response based on status code
                if response.status_code == 200:
                    return response.json()

                # Handle specific error codes
                self._handle_error_response(response)

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(
                    f"Grok request timeout (attempt {attempt + 1}/{self._max_retries + 1})"
                )

            except httpx.RequestError as e:
                last_error = e
                logger.warning(
                    f"Grok request error (attempt {attempt + 1}/{self._max_retries + 1}): {e}"
                )

            except RateLimitError as e:
                # Retry rate limit errors with backoff
                last_error = e
                if attempt < self._max_retries:
                    delay = self._calculate_backoff_delay(attempt)
                    logger.info(f"Rate limited, retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                raise

            except ProviderUnavailableError as e:
                # Retry server errors with backoff
                last_error = e
                if attempt < self._max_retries:
                    delay = self._calculate_backoff_delay(attempt)
                    logger.info(f"Server error, retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    continue
                raise

            except (AuthenticationError, LLMProviderError):
                # Don't retry auth errors or other client errors
                raise

            # Calculate backoff delay for next attempt
            if attempt < self._max_retries:
                delay = self._calculate_backoff_delay(attempt)
                time.sleep(delay)

        # All retries exhausted
        raise LLMProviderError(
            f"Request failed after {self._max_retries + 1} attempts: {last_error}",
            provider=LLMProviderType.GROK,
        )

    def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds with jitter
        """
        import random
        # Exponential backoff: base * 2^attempt with jitter
        delay = self._retry_base_delay * (2 ** attempt)
        # Add random jitter (0-25% of delay)
        jitter = delay * random.uniform(0, 0.25)
        return delay + jitter

    def _handle_error_response(self, response: "httpx.Response") -> None:
        """Handle error HTTP responses.

        Args:
            response: HTTP response object

        Raises:
            AuthenticationError: For 401/403
            RateLimitError: For 429
            ProviderUnavailableError: For 500/502/503
            LLMProviderError: For other errors
        """
        status_code = response.status_code

        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", response.text)
        except Exception:
            error_data = None
            error_message = response.text

        if status_code in (401, 403):
            raise AuthenticationError(
                f"Authentication failed: {error_message}",
                provider=LLMProviderType.GROK,
                status_code=status_code,
                response=error_data,
            )
        elif status_code == 429:
            raise RateLimitError(
                f"Rate limit exceeded: {error_message}",
                provider=LLMProviderType.GROK,
                status_code=status_code,
                response=error_data,
            )
        elif status_code in (500, 502, 503):
            raise ProviderUnavailableError(
                f"Server error: {error_message}",
                provider=LLMProviderType.GROK,
                status_code=status_code,
                response=error_data,
            )
        else:
            raise LLMProviderError(
                f"API error: {error_message}",
                provider=LLMProviderType.GROK,
                status_code=status_code,
                response=error_data,
            )

    def _parse_response(
        self,
        response_data: Dict[str, Any],
        model: str,
    ) -> LLMResponse:
        """Parse API response into LLMResponse.

        Args:
            response_data: Raw API response
            model: Model used for the request

        Returns:
            Parsed LLMResponse
        """
        # Extract content from first choice
        choices = response_data.get("choices", [])
        if not choices:
            raise LLMProviderError(
                "No choices in API response",
                provider=LLMProviderType.GROK,
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
            provider=LLMProviderType.GROK,
            usage=usage,
            finish_reason=finish_reason,
            raw_response=response_data,
        )

    def health_check(self) -> bool:
        """Check if Grok API is available.

        Sends a minimal request to verify connectivity.

        Returns:
            True if API is responding, False otherwise
        """
        try:
            # Send minimal request
            response = self.chat(
                messages=[LLMMessage(role="user", content="ping")],
                max_tokens=1,
                temperature=0,
            )
            return len(response.content) > 0
        except Exception as e:
            logger.warning(f"Grok health check failed: {e}")
            return False

    def calculate_cost(
        self,
        usage: LLMUsage,
        model: Optional[str] = None,
        cache_hit_tokens: int = 0,
    ) -> float:
        """Calculate cost for a request based on token usage.

        Args:
            usage: Token usage statistics
            model: Model used (default: provider's default model)
            cache_hit_tokens: Number of input tokens that hit cache

        Returns:
            Estimated cost in USD
        """
        actual_model = model or self._default_model

        # Get pricing for model (default to grok-4-fast pricing)
        pricing = GROK_PRICING.get(
            actual_model,
            GROK_PRICING["grok-4-fast"]
        )

        # Calculate input cost (split between cache hit and miss)
        cache_miss_tokens = max(0, usage.prompt_tokens - cache_hit_tokens)
        input_cost = (
            (cache_miss_tokens / 1_000_000) * pricing["input_per_million"] +
            (cache_hit_tokens / 1_000_000) * pricing["cache_hit_per_million"]
        )

        # Calculate output cost
        output_cost = (
            usage.completion_tokens / 1_000_000
        ) * pricing["output_per_million"]

        return input_cost + output_cost

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Uses a simple approximation (4 characters per token on average).
        For precise counting, use tiktoken with cl100k_base encoding.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        # Rough estimate: ~4 characters per token for English text
        # Grok uses a similar tokenizer to GPT-4
        return len(text) // 4


class LLMProviderFactory:
    """Factory for creating LLM provider instances.

    This factory creates provider instances based on the provider type,
    with sensible defaults for each provider.

    Default configurations:
    - DeepSeek: api.deepseek.com, deepseek-chat model
    - Grok: api.x.ai, grok-4-fast model
    - OpenRouter: openrouter.ai, auto model selection

    Usage:
        provider = LLMProviderFactory.create(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="your-api-key"
        )
    """

    # Provider configuration defaults
    _PROVIDER_CONFIGS: Dict[LLMProviderType, Dict[str, str]] = {
        LLMProviderType.DEEPSEEK: {
            "base_url": "https://api.deepseek.com/v1",
            "default_model": "deepseek-chat",
        },
        LLMProviderType.GROK: {
            "base_url": "https://api.x.ai/v1",
            "default_model": "grok-4-fast",
        },
        LLMProviderType.OPENROUTER: {
            "base_url": "https://openrouter.ai/api/v1",
            "default_model": "auto",  # Auto-select best model
        },
    }

    @classmethod
    def create(
        cls,
        provider_type: LLMProviderType,
        api_key: str,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
        **kwargs: Any,
    ) -> LLMProvider:
        """Create an LLM provider instance.

        Args:
            provider_type: The type of provider to create
            api_key: API key for authentication
            base_url: Override the default base URL (optional)
            model: Override the default model (optional)
            timeout: Request timeout in seconds (default 60)
            **kwargs: Additional provider-specific options

        Returns:
            An initialized LLMProvider instance

        Raises:
            ValueError: If provider_type is not supported
        """
        if provider_type not in cls._PROVIDER_CONFIGS:
            raise ValueError(f"Unsupported provider type: {provider_type}")

        config = cls._PROVIDER_CONFIGS[provider_type]

        # Use provided values or defaults
        actual_base_url = base_url or config["base_url"]
        actual_model = model or config["default_model"]

        # Create the appropriate provider
        if provider_type == LLMProviderType.DEEPSEEK:
            return DeepSeekProvider(
                api_key=api_key,
                base_url=actual_base_url,
                default_model=actual_model,
                timeout=timeout,
                max_retries=kwargs.get("max_retries", 3),
                retry_base_delay=kwargs.get("retry_base_delay", 1.0),
            )
        elif provider_type == LLMProviderType.GROK:
            return GrokProvider(
                api_key=api_key,
                base_url=actual_base_url,
                default_model=actual_model,
                timeout=timeout,
                max_retries=kwargs.get("max_retries", 3),
                retry_base_delay=kwargs.get("retry_base_delay", 1.0),
            )
        elif provider_type == LLMProviderType.OPENROUTER:
            return _StubProvider(
                api_key=api_key,
                base_url=actual_base_url,
                default_model=actual_model,
                timeout=timeout,
                provider_type=provider_type,
            )
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")

    @classmethod
    def get_provider_config(cls, provider_type: LLMProviderType) -> Dict[str, str]:
        """Get the default configuration for a provider.

        Args:
            provider_type: The provider type

        Returns:
            Dictionary with base_url and default_model
        """
        if provider_type not in cls._PROVIDER_CONFIGS:
            raise ValueError(f"Unsupported provider type: {provider_type}")
        return cls._PROVIDER_CONFIGS[provider_type].copy()

    @classmethod
    def list_providers(cls) -> List[LLMProviderType]:
        """List all supported provider types.

        Returns:
            List of supported LLMProviderType values
        """
        return list(cls._PROVIDER_CONFIGS.keys())


class _StubProvider(LLMProvider):
    """Stub provider for interface testing.

    This provider returns mock responses and is used for testing
    the interface before concrete implementations are added.

    Note: This will be replaced by actual providers in Tasks 11.1.2-11.1.4.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        default_model: str,
        timeout: float,
        provider_type: LLMProviderType,
    ):
        super().__init__(api_key, base_url, default_model, timeout)
        self._provider_type = provider_type

    @property
    def provider_type(self) -> LLMProviderType:
        return self._provider_type

    def chat(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        """Return a stub response for testing.

        Note: This will be replaced by actual API calls in Tasks 11.1.2-11.1.4.
        """
        actual_model = model or self._default_model

        # Create a stub response
        stub_content = (
            f"[STUB] This is a placeholder response from {self._provider_type.value}. "
            f"Actual implementation pending in Task 11.1.2-11.1.4."
        )

        if json_mode:
            stub_content = '{"message": "stub response", "provider": "' + self._provider_type.value + '"}'

        return LLMResponse(
            content=stub_content,
            model=actual_model,
            provider=self._provider_type,
            usage=LLMUsage(
                prompt_tokens=sum(len(m.content.split()) for m in messages) * 2,
                completion_tokens=len(stub_content.split()) * 2,
                total_tokens=0,  # Will be calculated
            ),
            finish_reason="stop",
            raw_response={"stub": True},
        )

    def health_check(self) -> bool:
        """Return True for stub provider (always healthy)."""
        return True
