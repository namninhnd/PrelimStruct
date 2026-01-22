"""
Unit tests for AI service module.

Tests cover:
- AIService initialization
- Design review functionality
- Chat functionality
- Cost tracking
- Error handling
"""

import pytest
from unittest.mock import Mock, MagicMock

from src.ai.llm_service import AIService
from src.ai.config import AIConfig
from src.ai.providers import LLMMessage, LLMResponse, LLMUsage, LLMProviderType
from src.ai.response_parser import DesignReviewResponse, UnstructuredResponse


class TestAIServiceInitialization:
    """Tests for AIService initialization."""

    def test_init_with_config(self):
        """Test initializing service with config."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="test-key-12345678",
        )
        
        # Mock provider to avoid actual API calls
        mock_provider = Mock()
        service = AIService(config, provider=mock_provider)
        
        assert service.config == config
        assert service.provider == mock_provider

    def test_init_creates_provider_if_none(self):
        """Test that provider is created if not provided."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="test-key-12345678",
        )
        
        # This will create a real provider, but we won't call it
        service = AIService(config)
        
        assert service.provider is not None
        assert service.config == config


class TestAIServiceDesignReview:
    """Tests for design review functionality."""

    @pytest.fixture
    def mock_service(self):
        """Create mock service for testing."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="test-key-12345678",
            track_costs=False,  # Disable cost tracking for tests
        )
        mock_provider = Mock()
        service = AIService(config, provider=mock_provider)
        return service, mock_provider

    def test_get_design_review_success(self, mock_service):
        """Test successful design review."""
        service, mock_provider = mock_service
        
        # Mock successful response with valid JSON
        mock_response = LLMResponse(
            content='{"efficiency_score": 85, "concerns": ["High drift"], "code_issues": [], "recommendations": ["Add bracing"], "summary": "Good design"}',
            model="deepseek-chat",
            provider=LLMProviderType.DEEPSEEK,
            usage=LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        )
        mock_provider.chat.return_value = mock_response
        
        # Call design review
        result = service.get_design_review(
            height=120.0,
            num_floors=30,
            grid_x=9.0,
            grid_y=9.0,
            total_area=30000.0,
            concrete_grade="C40",
            beam_sections="600x300",
            column_sections="900x900",
            core_wall_config="I_SECTION",
            lateral_system="Core + frames",
            design_summary="Test building",
        )
        
        # Verify result
        assert isinstance(result, DesignReviewResponse)
        assert result.efficiency_score == 85
        assert len(result.concerns) == 1
        assert "High drift" in result.concerns
        
        # Verify provider was called
        mock_provider.chat.assert_called_once()
        call_args = mock_provider.chat.call_args
        assert call_args.kwargs["json_mode"] is True
        assert call_args.kwargs["temperature"] == 0.7

    def test_get_design_review_unstructured_fallback(self, mock_service):
        """Test design review with unstructured response fallback."""
        service, mock_provider = mock_service
        
        # Mock response with non-JSON content
        mock_response = LLMResponse(
            content="This is a plain text response without JSON structure.",
            model="deepseek-chat",
            provider=LLMProviderType.DEEPSEEK,
            usage=LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        )
        mock_provider.chat.return_value = mock_response
        
        result = service.get_design_review(
            height=120.0,
            num_floors=30,
            grid_x=9.0,
            grid_y=9.0,
            total_area=30000.0,
            concrete_grade="C40",
            beam_sections="600x300",
            column_sections="900x900",
            core_wall_config="I_SECTION",
            lateral_system="Core + frames",
            design_summary="Test",
        )
        
        # Should fallback to unstructured
        assert isinstance(result, UnstructuredResponse)
        assert result.has_structure is False
        assert "plain text" in result.content

    def test_get_design_review_provider_error(self, mock_service):
        """Test design review with provider error."""
        service, mock_provider = mock_service
        
        # Mock provider error
        mock_provider.chat.side_effect = Exception("API connection failed")
        
        result = service.get_design_review(
            height=120.0,
            num_floors=30,
            grid_x=9.0,
            grid_y=9.0,
            total_area=30000.0,
            concrete_grade="C40",
            beam_sections="600x300",
            column_sections="900x900",
            core_wall_config="I_SECTION",
            lateral_system="Core + frames",
            design_summary="Test",
        )
        
        # Should return unstructured error response
        assert isinstance(result, UnstructuredResponse)
        assert "Error:" in result.content
        assert "API connection failed" in result.content

    def test_get_design_review_with_cost_tracking(self):
        """Test design review with cost tracking enabled."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="test-key-12345678",
            track_costs=True,  # Enable cost tracking
        )
        mock_provider = Mock()
        mock_provider.calculate_cost = Mock(return_value=0.00042)  # Mock cost calculation
        
        service = AIService(config, provider=mock_provider)
        
        # Mock successful response
        mock_response = LLMResponse(
            content='{"efficiency_score": 80, "concerns": [], "code_issues": [], "recommendations": [], "summary": "OK"}',
            model="deepseek-chat",
            provider=LLMProviderType.DEEPSEEK,
            usage=LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        )
        mock_provider.chat.return_value = mock_response
        
        result = service.get_design_review(
            height=120.0, num_floors=30, grid_x=9.0, grid_y=9.0,
            total_area=30000.0, concrete_grade="C40", beam_sections="600x300",
            column_sections="900x900", core_wall_config="I_SECTION",
            lateral_system="Core", design_summary="Test",
        )
        
        # Cost calculation should have been called
        mock_provider.calculate_cost.assert_called_once()


class TestAIServiceChat:
    """Tests for general chat functionality."""

    @pytest.fixture
    def mock_service(self):
        """Create mock service for testing."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="test-key-12345678",
            track_costs=False,
        )
        mock_provider = Mock()
        service = AIService(config, provider=mock_provider)
        return service, mock_provider

    def test_chat_success(self, mock_service):
        """Test successful chat interaction."""
        service, mock_provider = mock_service
        
        # Mock response
        mock_response = LLMResponse(
            content="Moment redistribution allows...",
            model="deepseek-chat",
            provider=LLMProviderType.DEEPSEEK,
            usage=LLMUsage(prompt_tokens=20, completion_tokens=30, total_tokens=50),
        )
        mock_provider.chat.return_value = mock_response
        
        result = service.chat("Explain moment redistribution")
        
        assert result == "Moment redistribution allows..."
        mock_provider.chat.assert_called_once()

    def test_chat_with_system_prompt(self, mock_service):
        """Test chat with custom system prompt."""
        service, mock_provider = mock_service
        
        mock_response = LLMResponse(
            content="Response",
            model="deepseek-chat",
            provider=LLMProviderType.DEEPSEEK,
        )
        mock_provider.chat.return_value = mock_response
        
        service.chat(
            "Question",
            system_prompt="You are a helpful assistant.",
        )
        
        # Verify system prompt was included
        call_args = mock_provider.chat.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0].role == "system"
        assert "helpful assistant" in messages[0].content

    def test_chat_with_conversation_history(self, mock_service):
        """Test chat with conversation history."""
        service, mock_provider = mock_service
        
        mock_response = LLMResponse(
            content="Follow-up response",
            model="deepseek-chat",
            provider=LLMProviderType.DEEPSEEK,
        )
        mock_provider.chat.return_value = mock_response
        
        # Create conversation history
        history = [
            LLMMessage(role="user", content="First question"),
            LLMMessage(role="assistant", content="First answer"),
        ]
        
        service.chat("Second question", conversation_history=history)
        
        # Verify history was included
        call_args = mock_provider.chat.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) >= 3  # History + new message
        assert messages[0].content == "First question"
        assert messages[1].content == "First answer"

    def test_chat_with_custom_parameters(self, mock_service):
        """Test chat with custom temperature and max_tokens."""
        service, mock_provider = mock_service
        
        mock_response = LLMResponse(
            content="Response",
            model="deepseek-chat",
            provider=LLMProviderType.DEEPSEEK,
        )
        mock_provider.chat.return_value = mock_response
        
        service.chat(
            "Question",
            temperature=0.5,
            max_tokens=100,
        )
        
        # Verify parameters were passed
        call_args = mock_provider.chat.call_args
        assert call_args.kwargs["temperature"] == 0.5
        assert call_args.kwargs["max_tokens"] == 100

    def test_chat_provider_error(self, mock_service):
        """Test chat with provider error."""
        service, mock_provider = mock_service
        
        mock_provider.chat.side_effect = Exception("Connection timeout")
        
        result = service.chat("Question")
        
        assert "Error:" in result
        assert "Connection timeout" in result


class TestAIServiceHealthCheck:
    """Tests for health check functionality."""

    def test_health_check_success(self):
        """Test successful health check."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="test-key-12345678",
        )
        mock_provider = Mock()
        mock_provider.health_check.return_value = True
        
        service = AIService(config, provider=mock_provider)
        
        assert service.health_check() is True
        mock_provider.health_check.assert_called_once()

    def test_health_check_failure(self):
        """Test failed health check."""
        config = AIConfig(
            provider_type=LLMProviderType.DEEPSEEK,
            api_key="test-key-12345678",
        )
        mock_provider = Mock()
        mock_provider.health_check.return_value = False
        
        service = AIService(config, provider=mock_provider)
        
        assert service.health_check() is False
