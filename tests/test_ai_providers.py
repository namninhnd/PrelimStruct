"""
Unit tests for AI Provider Interface and Factory.

Tests cover:
- LLMProviderType enum
- LLMMessage model validation and serialization
- LLMResponse model properties
- LLMProvider abstract interface
- LLMProviderFactory creation and configuration
- Error classes
"""

import pytest

from src.ai.providers import (
    LLMProviderType,
    MessageRole,
    LLMMessage,
    LLMUsage,
    LLMResponse,
    LLMProvider,
    LLMProviderFactory,
    LLMProviderError,
    RateLimitError,
    AuthenticationError,
    ProviderUnavailableError,
)


class TestLLMProviderType:
    """Tests for LLMProviderType enum."""

    def test_provider_types_exist(self):
        """Test all expected provider types are defined."""
        assert LLMProviderType.DEEPSEEK.value == "deepseek"
        assert LLMProviderType.GROK.value == "grok"
        assert LLMProviderType.OPENROUTER.value == "openrouter"

    def test_provider_type_count(self):
        """Test exactly 3 provider types are defined."""
        assert len(LLMProviderType) == 3


class TestMessageRole:
    """Tests for MessageRole enum."""

    def test_message_roles_exist(self):
        """Test all expected message roles are defined."""
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"


class TestLLMMessage:
    """Tests for LLMMessage dataclass."""

    def test_create_user_message(self):
        """Test creating a basic user message."""
        msg = LLMMessage(role="user", content="Hello, world!")
        assert msg.role == "user"
        assert msg.content == "Hello, world!"
        assert msg.name is None

    def test_create_system_message(self):
        """Test creating a system message."""
        msg = LLMMessage(role="system", content="You are a helpful assistant.")
        assert msg.role == "system"
        assert msg.content == "You are a helpful assistant."

    def test_create_assistant_message(self):
        """Test creating an assistant message."""
        msg = LLMMessage(role="assistant", content="How can I help you?")
        assert msg.role == "assistant"
        assert msg.content == "How can I help you?"

    def test_create_message_with_name(self):
        """Test creating a message with optional name."""
        msg = LLMMessage(role="user", content="Hello", name="John")
        assert msg.name == "John"

    def test_invalid_role_raises_error(self):
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            LLMMessage(role="invalid", content="Test")
        assert "Invalid role" in str(exc_info.value)

    def test_to_dict_basic(self):
        """Test converting message to dictionary."""
        msg = LLMMessage(role="user", content="Test message")
        d = msg.to_dict()
        assert d == {"role": "user", "content": "Test message"}

    def test_to_dict_with_name(self):
        """Test converting message with name to dictionary."""
        msg = LLMMessage(role="user", content="Test", name="John")
        d = msg.to_dict()
        assert d == {"role": "user", "content": "Test", "name": "John"}

    def test_empty_content_allowed(self):
        """Test that empty content is allowed."""
        msg = LLMMessage(role="user", content="")
        assert msg.content == ""


class TestLLMUsage:
    """Tests for LLMUsage dataclass."""

    def test_create_usage(self):
        """Test creating token usage statistics."""
        usage = LLMUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_create_response(self):
        """Test creating a basic response."""
        response = LLMResponse(
            content="Hello!",
            model="deepseek-chat",
            provider=LLMProviderType.DEEPSEEK,
        )
        assert response.content == "Hello!"
        assert response.model == "deepseek-chat"
        assert response.provider == LLMProviderType.DEEPSEEK

    def test_response_with_usage(self):
        """Test response with token usage."""
        usage = LLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        response = LLMResponse(
            content="Hi",
            model="deepseek-chat",
            provider=LLMProviderType.DEEPSEEK,
            usage=usage,
        )
        assert response.usage is not None
        assert response.usage.total_tokens == 15

    def test_total_tokens_property_with_usage(self):
        """Test total_tokens property when usage is available."""
        usage = LLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        response = LLMResponse(
            content="Hi",
            model="deepseek-chat",
            provider=LLMProviderType.DEEPSEEK,
            usage=usage,
        )
        assert response.total_tokens == 15

    def test_total_tokens_property_without_usage(self):
        """Test total_tokens returns 0 when usage is None."""
        response = LLMResponse(
            content="Hi",
            model="deepseek-chat",
            provider=LLMProviderType.DEEPSEEK,
        )
        assert response.total_tokens == 0

    def test_response_with_finish_reason(self):
        """Test response with finish reason."""
        response = LLMResponse(
            content="Done",
            model="deepseek-chat",
            provider=LLMProviderType.DEEPSEEK,
            finish_reason="stop",
        )
        assert response.finish_reason == "stop"


class TestLLMProviderErrors:
    """Tests for LLM provider error classes."""

    def test_base_error(self):
        """Test base LLMProviderError."""
        error = LLMProviderError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"

    def test_error_with_provider(self):
        """Test error with provider info."""
        error = LLMProviderError(
            "Connection failed",
            provider=LLMProviderType.DEEPSEEK,
        )
        assert "[deepseek]" in str(error)
        assert error.provider == LLMProviderType.DEEPSEEK

    def test_error_with_status_code(self):
        """Test error with HTTP status code."""
        error = LLMProviderError(
            "Rate limited",
            status_code=429,
        )
        assert "(HTTP 429)" in str(error)

    def test_error_with_all_fields(self):
        """Test error with all fields."""
        error = LLMProviderError(
            "Server error",
            provider=LLMProviderType.GROK,
            status_code=500,
            response={"error": "internal"},
        )
        assert "[grok]" in str(error)
        assert "(HTTP 500)" in str(error)
        assert error.response == {"error": "internal"}

    def test_rate_limit_error(self):
        """Test RateLimitError subclass."""
        error = RateLimitError("Too many requests", status_code=429)
        assert isinstance(error, LLMProviderError)
        assert error.status_code == 429

    def test_authentication_error(self):
        """Test AuthenticationError subclass."""
        error = AuthenticationError("Invalid API key", status_code=401)
        assert isinstance(error, LLMProviderError)
        assert error.status_code == 401

    def test_provider_unavailable_error(self):
        """Test ProviderUnavailableError subclass."""
        error = ProviderUnavailableError("Service down", status_code=503)
        assert isinstance(error, LLMProviderError)
        assert error.status_code == 503


class TestLLMProviderFactory:
    """Tests for LLMProviderFactory."""

    def test_create_deepseek_provider(self):
        """Test creating DeepSeek provider."""
        provider = LLMProviderFactory.create(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="test-key",
        )
        assert provider.provider_type == LLMProviderType.DEEPSEEK
        assert "deepseek" in provider.base_url
        assert provider.default_model == "deepseek-chat"

    def test_create_grok_provider(self):
        """Test creating Grok provider."""
        provider = LLMProviderFactory.create(
            provider_type=LLMProviderType.GROK,
            api_key="test-key",
        )
        assert provider.provider_type == LLMProviderType.GROK
        assert "x.ai" in provider.base_url
        assert provider.default_model == "grok-4-fast"

    def test_create_openrouter_provider(self):
        """Test creating OpenRouter provider."""
        provider = LLMProviderFactory.create(
            provider_type=LLMProviderType.OPENROUTER,
            api_key="test-key",
        )
        assert provider.provider_type == LLMProviderType.OPENROUTER
        assert "openrouter" in provider.base_url
        assert provider.default_model == "auto"

    def test_create_with_custom_base_url(self):
        """Test creating provider with custom base URL."""
        provider = LLMProviderFactory.create(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="test-key",
            base_url="https://custom.api.com/v1",
        )
        assert provider.base_url == "https://custom.api.com/v1"

    def test_create_with_custom_model(self):
        """Test creating provider with custom model."""
        provider = LLMProviderFactory.create(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="test-key",
            model="deepseek-coder",
        )
        assert provider.default_model == "deepseek-coder"

    def test_create_requires_api_key(self):
        """Test that API key is required."""
        with pytest.raises(ValueError) as exc_info:
            LLMProviderFactory.create(
                provider_type=LLMProviderType.DEEPSEEK,
                api_key="",
            )
        assert "API key is required" in str(exc_info.value)

    def test_get_provider_config_deepseek(self):
        """Test getting DeepSeek provider config."""
        config = LLMProviderFactory.get_provider_config(LLMProviderType.DEEPSEEK)
        assert "base_url" in config
        assert "default_model" in config
        assert config["default_model"] == "deepseek-chat"

    def test_get_provider_config_invalid(self):
        """Test getting config for invalid provider raises error."""
        # Create a mock invalid type by using a non-existent value
        with pytest.raises(ValueError):
            LLMProviderFactory.get_provider_config("invalid")  # type: ignore

    def test_list_providers(self):
        """Test listing all supported providers."""
        providers = LLMProviderFactory.list_providers()
        assert LLMProviderType.DEEPSEEK in providers
        assert LLMProviderType.GROK in providers
        assert LLMProviderType.OPENROUTER in providers
        assert len(providers) == 3


class TestDeepSeekProvider:
    """Tests for DeepSeekProvider implementation."""

    def test_deepseek_provider_creation(self):
        """Test DeepSeekProvider can be created."""
        from src.ai.providers import DeepSeekProvider
        provider = DeepSeekProvider(api_key="test-key")
        assert provider.provider_type == LLMProviderType.DEEPSEEK
        assert provider.default_model == "deepseek-chat"
        assert "deepseek" in provider.base_url

    def test_deepseek_provider_from_factory(self):
        """Test DeepSeekProvider creation via factory."""
        from src.ai.providers import DeepSeekProvider
        provider = LLMProviderFactory.create(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="test-key",
        )
        assert isinstance(provider, DeepSeekProvider)
        assert provider.provider_type == LLMProviderType.DEEPSEEK

    def test_deepseek_estimate_tokens(self):
        """Test token estimation."""
        from src.ai.providers import DeepSeekProvider
        provider = DeepSeekProvider(api_key="test-key")
        # ~4 chars per token
        assert provider.estimate_tokens("Hello World!") == 3  # 12 chars / 4

    def test_deepseek_calculate_cost(self):
        """Test cost calculation."""
        from src.ai.providers import DeepSeekProvider
        provider = DeepSeekProvider(api_key="test-key")
        usage = LLMUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
        )
        cost = provider.calculate_cost(usage)
        # Input: 1000 / 1M * $0.14 = $0.00014
        # Output: 500 / 1M * $0.28 = $0.00014
        # Total: $0.00028
        assert cost == pytest.approx(0.00028, rel=0.01)

    def test_deepseek_calculate_cost_with_cache(self):
        """Test cost calculation with cache hits."""
        from src.ai.providers import DeepSeekProvider
        provider = DeepSeekProvider(api_key="test-key")
        usage = LLMUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
        )
        cost = provider.calculate_cost(usage, cache_hit_tokens=800)
        # Cache miss: 200 / 1M * $0.14 = $0.000028
        # Cache hit: 800 / 1M * $0.014 = $0.0000112
        # Output: 500 / 1M * $0.28 = $0.00014
        # Total: ~$0.000179
        assert cost == pytest.approx(0.000179, rel=0.01)

    def test_deepseek_backoff_delay(self):
        """Test exponential backoff calculation."""
        from src.ai.providers import DeepSeekProvider
        import random
        random.seed(42)  # For reproducible test
        provider = DeepSeekProvider(api_key="test-key", retry_base_delay=1.0)

        # Attempt 0: 1 * 2^0 = 1s + jitter
        delay0 = provider._calculate_backoff_delay(0)
        assert 1.0 <= delay0 <= 1.25

        # Attempt 1: 1 * 2^1 = 2s + jitter
        delay1 = provider._calculate_backoff_delay(1)
        assert 2.0 <= delay1 <= 2.5

        # Attempt 2: 1 * 2^2 = 4s + jitter
        delay2 = provider._calculate_backoff_delay(2)
        assert 4.0 <= delay2 <= 5.0


class TestDeepSeekProviderMocked:
    """Tests for DeepSeekProvider with mocked HTTP responses."""

    @pytest.fixture
    def mock_success_response(self):
        """Mock successful API response."""
        return {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1705395200,
            "model": "deepseek-chat",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help you today?"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 8,
                "total_tokens": 18
            }
        }

    @pytest.fixture
    def mock_json_response(self):
        """Mock JSON mode API response."""
        return {
            "id": "chatcmpl-456",
            "object": "chat.completion",
            "created": 1705395201,
            "model": "deepseek-chat",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": '{"status": "ok", "message": "Hello"}'
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 15,
                "completion_tokens": 12,
                "total_tokens": 27
            }
        }

    def test_chat_success(self, mock_success_response, monkeypatch):
        """Test successful chat completion."""
        from src.ai.providers import DeepSeekProvider

        class MockResponse:
            status_code = 200
            def json(self):
                return mock_success_response

        class MockClient:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def post(self, url, json, headers):
                return MockResponse()

        monkeypatch.setattr("httpx.Client", MockClient)

        provider = DeepSeekProvider(api_key="test-key")
        messages = [LLMMessage(role="user", content="Hello")]
        response = provider.chat(messages)

        assert response.content == "Hello! How can I help you today?"
        assert response.model == "deepseek-chat"
        assert response.provider == LLMProviderType.DEEPSEEK
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 8
        assert response.finish_reason == "stop"

    def test_chat_json_mode(self, mock_json_response, monkeypatch):
        """Test JSON mode chat completion."""
        from src.ai.providers import DeepSeekProvider

        class MockResponse:
            status_code = 200
            def json(self):
                return mock_json_response

        class MockClient:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def post(self, url, json, headers):
                # Verify json_mode is in request
                assert json.get("response_format") == {"type": "json_object"}
                return MockResponse()

        monkeypatch.setattr("httpx.Client", MockClient)

        provider = DeepSeekProvider(api_key="test-key")
        messages = [LLMMessage(role="user", content="Give me JSON")]
        response = provider.chat(messages, json_mode=True)

        assert '{"status": "ok"' in response.content
        assert response.usage.total_tokens == 27

    def test_chat_auth_error(self, monkeypatch):
        """Test authentication error handling."""
        from src.ai.providers import DeepSeekProvider

        class MockResponse:
            status_code = 401
            text = "Unauthorized"
            def json(self):
                return {"error": {"message": "Invalid API key"}}

        class MockClient:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def post(self, url, json, headers):
                return MockResponse()

        monkeypatch.setattr("httpx.Client", MockClient)

        provider = DeepSeekProvider(api_key="invalid-key")
        messages = [LLMMessage(role="user", content="Hello")]

        with pytest.raises(AuthenticationError) as exc_info:
            provider.chat(messages)

        assert exc_info.value.status_code == 401
        assert "Authentication failed" in str(exc_info.value)

    def test_chat_rate_limit_retry(self, mock_success_response, monkeypatch):
        """Test rate limit error triggers retry."""
        from src.ai.providers import DeepSeekProvider

        call_count = 0

        class MockRateLimitResponse:
            status_code = 429
            text = "Rate limited"
            def json(self):
                return {"error": {"message": "Too many requests"}}

        class MockSuccessResponse:
            status_code = 200
            def json(self):
                return mock_success_response

        class MockClient:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def post(self, url, json, headers):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return MockRateLimitResponse()
                return MockSuccessResponse()

        monkeypatch.setattr("httpx.Client", MockClient)
        monkeypatch.setattr("time.sleep", lambda x: None)  # Skip actual delay

        provider = DeepSeekProvider(api_key="test-key", max_retries=2)
        messages = [LLMMessage(role="user", content="Hello")]
        response = provider.chat(messages)

        assert call_count == 2  # First failed, second succeeded
        assert response.content == "Hello! How can I help you today?"

    def test_chat_server_error_retry(self, mock_success_response, monkeypatch):
        """Test server error triggers retry."""
        from src.ai.providers import DeepSeekProvider

        call_count = 0

        class MockServerErrorResponse:
            status_code = 503
            text = "Service Unavailable"
            def json(self):
                return {"error": {"message": "Server overloaded"}}

        class MockSuccessResponse:
            status_code = 200
            def json(self):
                return mock_success_response

        class MockClient:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def post(self, url, json, headers):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    return MockServerErrorResponse()
                return MockSuccessResponse()

        monkeypatch.setattr("httpx.Client", MockClient)
        monkeypatch.setattr("time.sleep", lambda x: None)

        provider = DeepSeekProvider(api_key="test-key", max_retries=3)
        messages = [LLMMessage(role="user", content="Hello")]
        response = provider.chat(messages)

        assert call_count == 3
        assert response.content == "Hello! How can I help you today?"

    def test_chat_max_retries_exceeded(self, monkeypatch):
        """Test max retries exceeded raises error."""
        from src.ai.providers import DeepSeekProvider

        class MockServerErrorResponse:
            status_code = 503
            text = "Service Unavailable"
            def json(self):
                return {"error": {"message": "Server overloaded"}}

        class MockClient:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def post(self, url, json, headers):
                return MockServerErrorResponse()

        monkeypatch.setattr("httpx.Client", MockClient)
        monkeypatch.setattr("time.sleep", lambda x: None)

        provider = DeepSeekProvider(api_key="test-key", max_retries=2)
        messages = [LLMMessage(role="user", content="Hello")]

        with pytest.raises(ProviderUnavailableError):
            provider.chat(messages)


class TestLLMProviderInterface:
    """Tests for LLMProvider abstract interface."""

    def test_provider_is_abstract(self):
        """Test that LLMProvider cannot be instantiated directly."""
        # Create a concrete subclass that doesn't implement abstract methods
        # This should fail when trying to instantiate
        with pytest.raises(TypeError):
            # Cannot instantiate abstract class
            LLMProvider("key", "url", "model")  # type: ignore


class TestGrokProvider:
    """Tests for GrokProvider implementation."""

    def test_grok_provider_creation(self):
        """Test GrokProvider can be created."""
        from src.ai.providers import GrokProvider
        provider = GrokProvider(api_key="test-key")
        assert provider.provider_type == LLMProviderType.GROK
        assert provider.default_model == "grok-4-fast"
        assert "x.ai" in provider.base_url

    def test_grok_provider_from_factory(self):
        """Test GrokProvider creation via factory."""
        from src.ai.providers import GrokProvider
        provider = LLMProviderFactory.create(
            provider_type=LLMProviderType.GROK,
            api_key="test-key",
        )
        assert isinstance(provider, GrokProvider)
        assert provider.provider_type == LLMProviderType.GROK

    def test_grok_estimate_tokens(self):
        """Test token estimation."""
        from src.ai.providers import GrokProvider
        provider = GrokProvider(api_key="test-key")
        # ~4 chars per token
        assert provider.estimate_tokens("Hello World!") == 3  # 12 chars / 4

    def test_grok_calculate_cost(self):
        """Test cost calculation."""
        from src.ai.providers import GrokProvider
        provider = GrokProvider(api_key="test-key")
        usage = LLMUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
        )
        cost = provider.calculate_cost(usage)
        # Input: 1000 / 1M * $1.00 = $0.001
        # Output: 500 / 1M * $3.00 = $0.0015
        # Total: $0.0025
        assert cost == pytest.approx(0.0025, rel=0.01)

    def test_grok_calculate_cost_with_cache(self):
        """Test cost calculation with cache hits."""
        from src.ai.providers import GrokProvider
        provider = GrokProvider(api_key="test-key")
        usage = LLMUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
        )
        cost = provider.calculate_cost(usage, cache_hit_tokens=800)
        # Cache miss: 200 / 1M * $1.00 = $0.0002
        # Cache hit: 800 / 1M * $0.10 = $0.00008
        # Output: 500 / 1M * $3.00 = $0.0015
        # Total: ~$0.00178
        assert cost == pytest.approx(0.00178, rel=0.01)

    def test_grok_backoff_delay(self):
        """Test exponential backoff calculation."""
        from src.ai.providers import GrokProvider
        import random
        random.seed(42)  # For reproducible test
        provider = GrokProvider(api_key="test-key", retry_base_delay=1.0)

        # Attempt 0: 1 * 2^0 = 1s + jitter
        delay0 = provider._calculate_backoff_delay(0)
        assert 1.0 <= delay0 <= 1.25

        # Attempt 1: 1 * 2^1 = 2s + jitter
        delay1 = provider._calculate_backoff_delay(1)
        assert 2.0 <= delay1 <= 2.5

        # Attempt 2: 1 * 2^2 = 4s + jitter
        delay2 = provider._calculate_backoff_delay(2)
        assert 4.0 <= delay2 <= 5.0


class TestGrokProviderMocked:
    """Tests for GrokProvider with mocked HTTP responses."""

    @pytest.fixture
    def mock_success_response(self):
        """Mock successful API response."""
        return {
            "id": "chatcmpl-grok-123",
            "object": "chat.completion",
            "created": 1705395200,
            "model": "grok-4-fast",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I assist you today?"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 10,
                "total_tokens": 22
            }
        }

    @pytest.fixture
    def mock_json_response(self):
        """Mock JSON mode API response."""
        return {
            "id": "chatcmpl-grok-456",
            "object": "chat.completion",
            "created": 1705395201,
            "model": "grok-4-fast",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": '{"result": "success", "data": "structured output"}'
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 20,
                "completion_tokens": 15,
                "total_tokens": 35
            }
        }

    def test_chat_success(self, mock_success_response, monkeypatch):
        """Test successful chat completion."""
        from src.ai.providers import GrokProvider

        class MockResponse:
            status_code = 200
            def json(self):
                return mock_success_response

        class MockClient:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def post(self, url, json, headers):
                return MockResponse()

        monkeypatch.setattr("httpx.Client", MockClient)

        provider = GrokProvider(api_key="test-key")
        messages = [LLMMessage(role="user", content="Hello")]
        response = provider.chat(messages)

        assert response.content == "Hello! How can I assist you today?"
        assert response.model == "grok-4-fast"
        assert response.provider == LLMProviderType.GROK
        assert response.usage.prompt_tokens == 12
        assert response.usage.completion_tokens == 10
        assert response.finish_reason == "stop"

    def test_chat_json_mode(self, mock_json_response, monkeypatch):
        """Test JSON mode chat completion."""
        from src.ai.providers import GrokProvider

        class MockResponse:
            status_code = 200
            def json(self):
                return mock_json_response

        class MockClient:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def post(self, url, json, headers):
                # Verify json_mode is in request
                assert json.get("response_format") == {"type": "json_object"}
                return MockResponse()

        monkeypatch.setattr("httpx.Client", MockClient)

        provider = GrokProvider(api_key="test-key")
        messages = [LLMMessage(role="user", content="Give me JSON")]
        response = provider.chat(messages, json_mode=True)

        assert '{"result": "success"' in response.content
        assert response.usage.total_tokens == 35

    def test_chat_auth_error(self, monkeypatch):
        """Test authentication error handling."""
        from src.ai.providers import GrokProvider

        class MockResponse:
            status_code = 401
            text = "Unauthorized"
            def json(self):
                return {"error": {"message": "Invalid API key"}}

        class MockClient:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def post(self, url, json, headers):
                return MockResponse()

        monkeypatch.setattr("httpx.Client", MockClient)

        provider = GrokProvider(api_key="invalid-key")
        messages = [LLMMessage(role="user", content="Hello")]

        with pytest.raises(AuthenticationError) as exc_info:
            provider.chat(messages)

        assert exc_info.value.status_code == 401
        assert "Authentication failed" in str(exc_info.value)

    def test_chat_rate_limit_retry(self, mock_success_response, monkeypatch):
        """Test rate limit error triggers retry."""
        from src.ai.providers import GrokProvider

        call_count = 0

        class MockRateLimitResponse:
            status_code = 429
            text = "Rate limited"
            def json(self):
                return {"error": {"message": "Too many requests"}}

        class MockSuccessResponse:
            status_code = 200
            def json(self):
                return mock_success_response

        class MockClient:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def post(self, url, json, headers):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return MockRateLimitResponse()
                return MockSuccessResponse()

        monkeypatch.setattr("httpx.Client", MockClient)
        monkeypatch.setattr("time.sleep", lambda x: None)  # Skip actual delay

        provider = GrokProvider(api_key="test-key", max_retries=2)
        messages = [LLMMessage(role="user", content="Hello")]
        response = provider.chat(messages)

        assert call_count == 2  # First failed, second succeeded
        assert response.content == "Hello! How can I assist you today?"

    def test_chat_server_error_retry(self, mock_success_response, monkeypatch):
        """Test server error triggers retry."""
        from src.ai.providers import GrokProvider

        call_count = 0

        class MockServerErrorResponse:
            status_code = 503
            text = "Service Unavailable"
            def json(self):
                return {"error": {"message": "Server overloaded"}}

        class MockSuccessResponse:
            status_code = 200
            def json(self):
                return mock_success_response

        class MockClient:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def post(self, url, json, headers):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    return MockServerErrorResponse()
                return MockSuccessResponse()

        monkeypatch.setattr("httpx.Client", MockClient)
        monkeypatch.setattr("time.sleep", lambda x: None)

        provider = GrokProvider(api_key="test-key", max_retries=3)
        messages = [LLMMessage(role="user", content="Hello")]
        response = provider.chat(messages)

        assert call_count == 3
        assert response.content == "Hello! How can I assist you today?"

    def test_chat_max_retries_exceeded(self, monkeypatch):
        """Test max retries exceeded raises error."""
        from src.ai.providers import GrokProvider

        class MockServerErrorResponse:
            status_code = 503
            text = "Service Unavailable"
            def json(self):
                return {"error": {"message": "Server overloaded"}}

        class MockClient:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def post(self, url, json, headers):
                return MockServerErrorResponse()

        monkeypatch.setattr("httpx.Client", MockClient)
        monkeypatch.setattr("time.sleep", lambda x: None)

        provider = GrokProvider(api_key="test-key", max_retries=2)
        messages = [LLMMessage(role="user", content="Hello")]

        with pytest.raises(ProviderUnavailableError):
            provider.chat(messages)

    def test_chat_custom_model(self, mock_success_response, monkeypatch):
        """Test chat with custom model."""
        from src.ai.providers import GrokProvider

        class MockResponse:
            status_code = 200
            def json(self):
                # Modify response to reflect custom model
                response = mock_success_response.copy()
                response["model"] = "grok-2"
                return response

        class MockClient:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def post(self, url, json, headers):
                # Verify custom model in request
                assert json.get("model") == "grok-2"
                return MockResponse()

        monkeypatch.setattr("httpx.Client", MockClient)

        provider = GrokProvider(api_key="test-key")
        messages = [LLMMessage(role="user", content="Hello")]
        response = provider.chat(messages, model="grok-2")

        assert response.model == "grok-2"

    def test_health_check_success(self, monkeypatch):
        """Test health check returns True when API is available."""
        from src.ai.providers import GrokProvider

        mock_response = {
            "id": "health-check",
            "model": "grok-4-fast",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": "ok"},
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
        }

        class MockResponse:
            status_code = 200
            def json(self):
                return mock_response

        class MockClient:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def post(self, url, json, headers):
                return MockResponse()

        monkeypatch.setattr("httpx.Client", MockClient)

        provider = GrokProvider(api_key="test-key")
        assert provider.health_check() is True

    def test_health_check_failure(self, monkeypatch):
        """Test health check returns False on error."""
        from src.ai.providers import GrokProvider

        class MockClient:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def post(self, url, json, headers):
                raise Exception("Connection failed")

        monkeypatch.setattr("httpx.Client", MockClient)

        provider = GrokProvider(api_key="test-key")
        assert provider.health_check() is False


class TestStubProviderUpdated:
    """Tests for the stub provider implementation (OpenRouter only now)."""

    def test_stub_provider_chat(self):
        """Test stub provider chat method returns response."""
        # Use OpenRouter which still uses stub provider
        provider = LLMProviderFactory.create(
            provider_type=LLMProviderType.OPENROUTER,
            api_key="test-key",
        )
        messages = [LLMMessage(role="user", content="Hello")]
        response = provider.chat(messages)

        assert response.content is not None
        assert response.model == "auto"
        assert response.provider == LLMProviderType.OPENROUTER
        assert "STUB" in response.content

    def test_stub_provider_chat_json_mode(self):
        """Test stub provider returns JSON in json_mode."""
        provider = LLMProviderFactory.create(
            provider_type=LLMProviderType.OPENROUTER,
            api_key="test-key",
        )
        messages = [LLMMessage(role="user", content="Give me JSON")]
        response = provider.chat(messages, json_mode=True)

        assert response.content.startswith("{")
        assert "openrouter" in response.content

    def test_stub_provider_health_check(self):
        """Test stub provider health check returns True."""
        provider = LLMProviderFactory.create(
            provider_type=LLMProviderType.OPENROUTER,
            api_key="test-key",
        )
        assert provider.health_check() is True

