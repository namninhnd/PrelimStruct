"""
AI Service Module for PrelimStruct.

This module provides a high-level service interface for AI assistant
features, integrating providers, prompts, and response parsing.

Usage:
    from src.ai import AIService
    
    # Initialize service
    service = AIService.from_env()
    
    # Get design review
    review = service.get_design_review(project_data)
    print(f"Efficiency Score: {review.efficiency_score}")
"""

from typing import Optional, Dict, Any
import logging

from .config import AIConfig
from .providers import LLMProvider, LLMMessage, LLMResponse
from .prompts import (
    PromptType,
    get_template,
    create_design_review_prompt,
)
from .response_parser import (
    DesignReviewResponse,
    OptimizationResponse,
    UnstructuredResponse,
    safe_parse_design_review,
    safe_parse_optimization,
)

logger = logging.getLogger(__name__)


class AIService:
    """High-level AI service for structural engineering tasks.
    
    This service manages the LLM provider, handles prompt formatting,
    and parses structured responses.
    
    Attributes:
        config: AI configuration
        provider: LLM provider instance
    """
    
    def __init__(self, config: AIConfig, provider: Optional[LLMProvider] = None):
        """Initialize AI service.
        
        Args:
            config: AI configuration
            provider: Optional pre-configured provider (creates new if None)
        """
        self.config = config
        self.provider = provider or config.create_provider()
        logger.info(f"AIService initialized with {config.provider_type.value} provider")
    
    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "AIService":
        """Create service from environment variables.
        
        Args:
            env_file: Optional .env file path
            
        Returns:
            Initialized AIService instance
        """
        config = AIConfig.from_env(env_file)
        return cls(config)
    
    def get_design_review(
        self,
        height: float,
        num_floors: int,
        grid_x: float,
        grid_y: float,
        total_area: float,
        concrete_grade: str,
        beam_sections: str,
        column_sections: str,
        core_wall_config: str,
        lateral_system: str,
        design_summary: str,
    ) -> DesignReviewResponse | UnstructuredResponse:
        """Get AI design review for a project.
        
        Args:
            height: Building height in meters
            num_floors: Number of floors
            grid_x: Grid dimension X in meters
            grid_y: Grid dimension Y in meters
            total_area: Total floor area in m²
            concrete_grade: Concrete grade (e.g., "C40")
            beam_sections: Beam section summary
            column_sections: Column section summary
            core_wall_config: Core wall configuration type
            lateral_system: Lateral system description
            design_summary: Overall design summary
            
        Returns:
            DesignReviewResponse with structured assessment or UnstructuredResponse fallback
        """
        # Create prompt
        system_prompt, user_prompt = create_design_review_prompt(
            height=height,
            num_floors=num_floors,
            grid_x=grid_x,
            grid_y=grid_y,
            total_area=total_area,
            concrete_grade=concrete_grade,
            beam_sections=beam_sections,
            column_sections=column_sections,
            core_wall_config=core_wall_config,
            lateral_system=lateral_system,
            design_summary=design_summary,
        )
        
        # Send request
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]
        
        template = get_template(PromptType.DESIGN_REVIEW)
        
        try:
            response = self.provider.chat(
                messages=messages,
                temperature=template.temperature,
                max_tokens=template.max_tokens,
                json_mode=template.json_mode,
            )
            
            # Parse response
            parsed = safe_parse_design_review(response.content)
            
            # Log usage
            if self.config.track_costs and response.usage:
                cost = getattr(self.provider, 'calculate_cost', lambda x: 0.0)(response.usage)
                logger.info(
                    f"Design review: {response.usage.total_tokens} tokens, "
                    f"${cost:.6f} cost"
                )
            
            return parsed
            
        except Exception as e:
            logger.error(f"Design review failed: {e}")
            return UnstructuredResponse(
                content=f"Error: {str(e)}",
                has_structure=False,
                parse_error=str(e),
            )
    
    def chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[list] = None,
        temperature: float = 0.7,
        max_tokens: int = 300,
    ) -> str:
        """General chat interface for custom queries.
        
        Args:
            user_message: User's question or request
            system_prompt: Optional custom system prompt
            conversation_history: Optional list of previous messages
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum response tokens
            
        Returns:
            AI response text
        """
        messages = []
        
        # Add system prompt
        if system_prompt:
            messages.append(LLMMessage(role="system", content=system_prompt))
        
        # Add conversation history (convert dicts to LLMMessage if needed)
        if conversation_history:
            for msg in conversation_history:
                if isinstance(msg, LLMMessage):
                    messages.append(msg)
                elif isinstance(msg, dict):
                    messages.append(LLMMessage(
                        role=msg.get("role", "user"),
                        content=msg.get("content", ""),
                    ))
                else:
                    messages.append(msg)
        
        # Add user message
        messages.append(LLMMessage(role="user", content=user_message))
        
        try:
            response = self.provider.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            # Log usage
            if self.config.track_costs and response.usage:
                cost = getattr(self.provider, 'calculate_cost', lambda x: 0.0)(response.usage)
                logger.info(
                    f"Chat: {response.usage.total_tokens} tokens, ${cost:.6f} cost"
                )
            
            return response.content
            
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            return f"Error: {str(e)}"
    
    def health_check(self) -> bool:
        """Check if AI service is operational.
        
        Returns:
            True if service is healthy, False otherwise
        """
        return self.provider.health_check()
