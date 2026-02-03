"""
Unit tests for AI configuration module.

Tests cover:
- AIConfig initialization and validation
- Environment variable loading
- Provider creation
- Health checks
- API key masking for security
- Configuration validation
"""

import pytest
import os
from unittest.mock import Mock, patch

from src.ai.config import AIConfig
from src.ai.providers import LLMProviderType, LLMProvider, LLMProviderError


class TestAIConfigInitialization:
    """Tests for AIConfig initialization and validation."""

    def test_create_valid_config(self):
        """Test creating a valid configuration."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="test-key-12345678",
        )
        
        assert config.provider_type == LLMProviderType.DEEPSEEK
        assert config.api_key == "test-key-12345678"
        assert config.timeout == 60.0
        assert config.max_retries == 3
        assert config.track_costs is True

    def test_create_config_with_all_parameters(self):
        """Test creating config with all optional parameters."""
        config = AIConfig(
            provider_type=LLMProviderType.GROK,
            api_key="grok-key-12345678",
            base_url="https://custom.api.endpoint",
            model="grok-4-fast",
            timeout=120.0,
            max_retries=5,
            track_costs=False,
            monthly_budget=100.0,
            site_url="https://mysite.com",
            site_name="MyApp",
        )
        
        assert config.provider_type == LLMProviderType.GROK
        assert config.base_url == "https://custom.api.endpoint"
        assert config.model == "grok-4-fast"
        assert config.timeout == 120.0
        assert config.max_retries == 5
        assert config.track_costs is False
        assert config.monthly_budget == 100.0
        assert config.site_url == "https://mysite.com"
        assert config.site_name == "MyApp"

    def test_missing_api_key_raises_error(self):
        """Test that missing API key raises ValueError."""
        with pytest.raises(ValueError, match="API key is required"):
            AIConfig(
                provider_type=LLMProviderType.DEEPSEEK,
                api_key="",
            )

    def test_empty_api_key_raises_error(self):
        """Test that empty API key raises ValueError."""
        with pytest.raises(ValueError, match="API key is required"):
            AIConfig(
                provider_type=LLMProviderType.DEEPSEEK,
                api_key="",
            )

    def test_negative_timeout_raises_error(self):
        """Test that negative timeout raises ValueError."""
        with pytest.raises(ValueError, match="Timeout must be positive"):
            AIConfig(
                provider_type=LLMProviderType.DEEPSEEK,
                api_key="test-key",
                timeout=-10.0,
            )

    def test_zero_timeout_raises_error(self):
        """Test that zero timeout raises ValueError."""
        with pytest.raises(ValueError, match="Timeout must be positive"):
            AIConfig(
                provider_type=LLMProviderType.DEEPSEEK,
                api_key="test-key",
                timeout=0.0,
            )

    def test_negative_max_retries_raises_error(self):
        """Test that negative max_retries raises ValueError."""
        with pytest.raises(ValueError, match="Max retries cannot be negative"):
            AIConfig(
                provider_type=LLMProviderType.DEEPSEEK,
                api_key="test-key",
                max_retries=-1,
            )

    def test_zero_max_retries_allowed(self):
        """Test that zero max_retries is allowed (no retries)."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="test-key",
            max_retries=0,
        )
        assert config.max_retries == 0

    def test_negative_monthly_budget_raises_error(self):
        """Test that negative monthly budget raises ValueError."""
        with pytest.raises(ValueError, match="Monthly budget cannot be negative"):
            AIConfig(
                provider_type=LLMProviderType.DEEPSEEK,
                api_key="test-key",
                monthly_budget=-50.0,
            )

    def test_zero_monthly_budget_allowed(self):
        """Test that zero monthly budget is allowed (unlimited)."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="test-key",
            monthly_budget=0.0,
        )
        assert config.monthly_budget == 0.0


class TestAIConfigFromEnv:
    """Tests for loading configuration from environment variables."""

    def test_from_env_deepseek(self):
        """Test loading DeepSeek config from environment."""
        env_vars = {
            "LLM_PROVIDER": "deepseek",
            "DEEPSEEK_API_KEY": "sk-test-12345678",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = AIConfig.from_env()
            
            assert config.provider_type == LLMProviderType.DEEPSEEK
            assert config.api_key == "sk-test-12345678"

    def test_from_env_grok(self):
        """Test loading Grok config from environment."""
        env_vars = {
            "LLM_PROVIDER": "grok",
            "GROK_API_KEY": "grok-key-12345678",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = AIConfig.from_env()
            
            assert config.provider_type == LLMProviderType.GROK
            assert config.api_key == "grok-key-12345678"

    def test_from_env_openrouter(self):
        """Test loading OpenRouter config from environment."""
        env_vars = {
            "LLM_PROVIDER": "openrouter",
            "OPENROUTER_API_KEY": "or-key-12345678",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = AIConfig.from_env()
            
            assert config.provider_type == LLMProviderType.OPENROUTER
            assert config.api_key == "or-key-12345678"

    def test_from_env_with_base_url(self):
        """Test loading config with custom base URL."""
        env_vars = {
            "LLM_PROVIDER": "deepseek",
            "DEEPSEEK_API_KEY": "sk-test",
            "DEEPSEEK_BASE_URL": "https://mkeai.com/v1",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = AIConfig.from_env()
            
            assert config.base_url == "https://mkeai.com/v1"

    def test_from_env_with_all_options(self):
        """Test loading config with all environment options."""
        env_vars = {
            "LLM_PROVIDER": "deepseek",
            "DEEPSEEK_API_KEY": "sk-test",
            "LLM_MODEL": "deepseek-chat",
            "LLM_TIMEOUT": "90",
            "LLM_MAX_RETRIES": "5",
            "LLM_TRACK_COSTS": "false",
            "LLM_MONTHLY_BUDGET": "200",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = AIConfig.from_env()
            
            assert config.model == "deepseek-chat"
            assert config.timeout == 90.0
            assert config.max_retries == 5
            assert config.track_costs is False
            assert config.monthly_budget == 200.0

    def test_from_env_missing_api_key_raises_error(self):
        """Test that missing API key raises ValueError."""
        env_vars = {
            "LLM_PROVIDER": "deepseek",
            # Missing DEEPSEEK_API_KEY
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="Missing API key"):
                AIConfig.from_env()

    def test_from_env_invalid_provider_raises_error(self):
        """Test that invalid provider type raises ValueError."""
        env_vars = {
            "LLM_PROVIDER": "invalid_provider",
            "INVALID_PROVIDER_API_KEY": "test-key",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="Invalid LLM_PROVIDER"):
                AIConfig.from_env()

    def test_from_env_default_provider_deepseek(self):
        """Test that default provider is DeepSeek if not specified."""
        env_vars = {
            # LLM_PROVIDER not specified
            "DEEPSEEK_API_KEY": "sk-test",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = AIConfig.from_env()
            assert config.provider_type == LLMProviderType.DEEPSEEK

    def test_from_env_openrouter_with_site_info(self):
        """Test OpenRouter config with site URL and name."""
        env_vars = {
            "LLM_PROVIDER": "openrouter",
            "OPENROUTER_API_KEY": "or-key",
            "OPENROUTER_SITE_URL": "https://myapp.com",
            "OPENROUTER_SITE_NAME": "MyApp",
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            config = AIConfig.from_env()
            
            assert config.site_url == "https://myapp.com"
            assert config.site_name == "MyApp"

    def test_from_env_track_costs_parsing(self):
        """Test track_costs boolean parsing from string."""
        # Test "true"
        with patch.dict(os.environ, {"LLM_PROVIDER": "deepseek", "DEEPSEEK_API_KEY": "sk-test", "LLM_TRACK_COSTS": "true"}):
            config = AIConfig.from_env()
            assert config.track_costs is True
        
        # Test "false"
        with patch.dict(os.environ, {"LLM_PROVIDER": "deepseek", "DEEPSEEK_API_KEY": "sk-test", "LLM_TRACK_COSTS": "false"}):
            config = AIConfig.from_env()
            assert config.track_costs is False
        
        # Test default (true)
        with patch.dict(os.environ, {"LLM_PROVIDER": "deepseek", "DEEPSEEK_API_KEY": "sk-test"}):
            config = AIConfig.from_env()
            assert config.track_costs is True


class TestAIConfigProviderCreation:
    """Tests for creating LLM providers from config."""

    def test_create_provider_deepseek(self):
        """Test creating DeepSeek provider."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="sk-test-12345678",
        )
        
        provider = config.create_provider()
        
        assert provider is not None
        assert hasattr(provider, "chat")
        assert provider.default_model == "deepseek-v3.2"

    def test_create_provider_grok(self):
        """Test creating Grok provider."""
        config = AIConfig(
            provider_type=LLMProviderType.GROK,
            api_key="grok-test-12345678",
        )
        
        provider = config.create_provider()
        
        assert provider is not None
        assert hasattr(provider, "chat")
        assert provider.default_model == "grok-4-fast"

    def test_create_provider_openrouter(self):
        """Test creating OpenRouter provider."""
        config = AIConfig(
            provider_type=LLMProviderType.OPENROUTER,
            api_key="or-test-12345678",
        )
        
        provider = config.create_provider()
        
        assert provider is not None
        assert hasattr(provider, "chat")

    def test_create_provider_with_custom_model(self):
        """Test creating provider with custom model."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="sk-test",
            model="deepseek-coder",
        )
        
        provider = config.create_provider()
        
        assert provider.default_model == "deepseek-coder"

    def test_create_provider_with_site_info(self):
        """Test creating OpenRouter provider with site info."""
        config = AIConfig(
            provider_type=LLMProviderType.OPENROUTER,
            api_key="or-test",
            site_url="https://myapp.com",
            site_name="MyApp",
        )
        
        # Should not raise error
        provider = config.create_provider()
        assert provider is not None


class TestAIConfigHealthCheck:
    """Tests for health check functionality."""

    def test_health_check_success(self):
        """Test successful health check."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="sk-test-12345678",
        )
        
        # Mock provider health check
        with patch.object(config, 'create_provider') as mock_create:
            mock_provider = Mock()
            mock_provider.health_check.return_value = True
            mock_create.return_value = mock_provider
            
            result = config.health_check()
            
            assert result is True
            mock_provider.health_check.assert_called_once()

    def test_health_check_failure(self):
        """Test failed health check."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="sk-test-12345678",
        )
        
        # Mock provider health check failure
        with patch.object(config, 'create_provider') as mock_create:
            mock_provider = Mock()
            mock_provider.health_check.return_value = False
            mock_create.return_value = mock_provider
            
            result = config.health_check()
            
            assert result is False

    def test_health_check_exception(self):
        """Test health check handles exceptions gracefully."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="sk-test-12345678",
        )
        
        # Mock provider creation exception
        with patch.object(config, 'create_provider') as mock_create:
            mock_create.side_effect = Exception("Connection failed")
            
            result = config.health_check()
            
            assert result is False


class TestAIConfigAPIKeyMasking:
    """Tests for API key masking for security."""

    def test_mask_api_key_standard(self):
        """Test masking standard length API key."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="sk-test-1234567890abcdef",
        )
        
        masked = config.mask_api_key()
        
        assert masked == "sk-test-...cdef"
        assert "1234567890" not in masked

    def test_mask_api_key_short(self):
        """Test masking short API key."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="short-key",
        )
        
        masked = config.mask_api_key()
        
        # Short keys should return "***"
        assert masked == "***"

    def test_repr_uses_masked_key(self):
        """Test that __repr__ uses masked API key."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="sk-test-1234567890abcdef",
        )
        
        repr_str = repr(config)
        
        assert "sk-test-...cdef" in repr_str
        assert "1234567890" not in repr_str
        assert "provider=deepseek" in repr_str

    def test_repr_with_model(self):
        """Test __repr__ with custom model."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="sk-test-12345678",
            model="deepseek-coder",
        )
        
        repr_str = repr(config)
        
        assert "model=deepseek-coder" in repr_str

    def test_repr_default_model(self):
        """Test __repr__ with default model."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="sk-test-12345678",
        )
        
        repr_str = repr(config)
        
        assert "model=default" in repr_str


class TestAIConfigEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_long_api_key(self):
        """Test handling very long API key."""
        long_key = "sk-" + "a" * 200
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key=long_key,
        )
        
        assert config.api_key == long_key
        masked = config.mask_api_key()
        assert len(masked) < len(long_key)

    def test_timeout_float_precision(self):
        """Test timeout with float precision."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="sk-test",
            timeout=45.5,
        )
        
        assert config.timeout == 45.5

    def test_very_high_max_retries(self):
        """Test very high max_retries value."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="sk-test",
            max_retries=100,
        )
        
        assert config.max_retries == 100

    def test_large_monthly_budget(self):
        """Test large monthly budget value."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="sk-test",
            monthly_budget=10000.0,
        )
        
        assert config.monthly_budget == 10000.0

    def test_none_optional_fields(self):
        """Test that None is acceptable for optional fields."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="sk-test",
            base_url=None,
            model=None,
            site_url=None,
            site_name=None,
        )
        
        assert config.base_url is None
        assert config.model is None
        assert config.site_url is None
        assert config.site_name is None
