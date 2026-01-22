"""
Structured Response Parsing Module for PrelimStruct AI Assistant.

This module provides Pydantic models for parsing and validating
JSON responses from LLM providers, ensuring type safety and
programmatic handling of AI outputs.

Usage:
    from src.ai.response_parser import parse_design_review_response
    
    response = provider.chat(messages, json_mode=True)
    parsed = parse_design_review_response(response.content)
    print(f"Efficiency Score: {parsed.efficiency_score}")
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class PriorityLevel(Enum):
    """Priority levels for issues and recommendations."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class DesignReviewResponse:
    """Structured response from design review AI prompt.
    
    Attributes:
        efficiency_score: Overall design efficiency (0-100)
        concerns: List of structural concerns or risks
        code_issues: List of HK Code 2013 compliance issues
        recommendations: List of recommended improvements
        summary: 2-3 sentence overall assessment
        raw_response: Original JSON response for debugging
    """
    efficiency_score: int
    concerns: List[str]
    code_issues: List[str]
    recommendations: List[str]
    summary: str
    raw_response: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate efficiency score range."""
        if not 0 <= self.efficiency_score <= 100:
            raise ValueError(f"Efficiency score must be 0-100, got {self.efficiency_score}")


@dataclass
class OptimizationResponse:
    """Structured response from optimization AI prompt.
    
    Attributes:
        material_savings: List of material savings opportunities
        system_improvements: List of system-level improvements
        constructability: List of constructability enhancements
        estimated_savings_percent: Estimated cost savings (0-30%)
        priority_action: Highest impact recommendation
        raw_response: Original JSON response for debugging
    """
    material_savings: List[str]
    system_improvements: List[str]
    constructability: List[str]
    estimated_savings_percent: float
    priority_action: str
    raw_response: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate savings percentage range."""
        if not 0 <= self.estimated_savings_percent <= 30:
            raise ValueError(
                f"Savings percent must be 0-30, got {self.estimated_savings_percent}"
            )


@dataclass
class UnstructuredResponse:
    """Fallback for unstructured AI responses.
    
    Attributes:
        content: Raw text content
        has_structure: Always False for this type
        parse_error: Optional error message if parsing failed
    """
    content: str
    has_structure: bool = False
    parse_error: Optional[str] = None


# ============================================================================
# PARSING FUNCTIONS
# ============================================================================

def parse_design_review_response(response_text: str) -> DesignReviewResponse:
    """Parse design review JSON response.
    
    Args:
        response_text: JSON string from LLM response
        
    Returns:
        DesignReviewResponse with validated fields
        
    Raises:
        ValueError: If JSON is invalid or required fields missing
        
    Example:
        >>> json_str = '{\"efficiency_score\": 75, \"concerns\": [...]}'
        >>> parsed = parse_design_review_response(json_str)
        >>> print(parsed.efficiency_score)
        75
    """
    try:
        # Parse JSON
        data = json.loads(response_text)
        
        # Extract required fields
        efficiency_score = int(data.get("efficiency_score", 0))
        concerns = data.get("concerns", [])
        code_issues = data.get("code_issues", [])
        recommendations = data.get("recommendations", [])
        summary = data.get("summary", "")
        
        # Validate required fields
        if not isinstance(concerns, list):
            raise ValueError("'concerns' must be a list")
        if not isinstance(code_issues, list):
            raise ValueError("'code_issues' must be a list")
        if not isinstance(recommendations, list):
            raise ValueError("'recommendations' must be a list")
        if not summary:
            raise ValueError("'summary' is required")
        
        return DesignReviewResponse(
            efficiency_score=efficiency_score,
            concerns=concerns,
            code_issues=code_issues,
            recommendations=recommendations,
            summary=summary,
            raw_response=data,
        )
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON response: {e}")
    except KeyError as e:
        raise ValueError(f"Missing required field: {e}")


def parse_optimization_response(response_text: str) -> OptimizationResponse:
    """Parse optimization JSON response.
    
    Args:
        response_text: JSON string from LLM response
        
    Returns:
        OptimizationResponse with validated fields
        
    Raises:
        ValueError: If JSON is invalid or required fields missing
    """
    try:
        # Parse JSON
        data = json.loads(response_text)
        
        # Extract required fields
        material_savings = data.get("material_savings", [])
        system_improvements = data.get("system_improvements", [])
        constructability = data.get("constructability", [])
        estimated_savings_percent = float(data.get("estimated_savings_percent", 0))
        priority_action = data.get("priority_action", "")
        
        # Validate required fields
        if not isinstance(material_savings, list):
            raise ValueError("'material_savings' must be a list")
        if not isinstance(system_improvements, list):
            raise ValueError("'system_improvements' must be a list")
        if not isinstance(constructability, list):
            raise ValueError("'constructability' must be a list")
        if not priority_action:
            raise ValueError("'priority_action' is required")
        
        return OptimizationResponse(
            material_savings=material_savings,
            system_improvements=system_improvements,
            constructability=constructability,
            estimated_savings_percent=estimated_savings_percent,
            priority_action=priority_action,
            raw_response=data,
        )
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON response: {e}")
    except KeyError as e:
        raise ValueError(f"Missing required field: {e}")


def parse_response_with_fallback(
    response_text: str,
    parser_func: callable,
) -> DesignReviewResponse | OptimizationResponse | UnstructuredResponse:
    """Parse response with fallback to unstructured.
    
    Attempts to parse structured JSON response. If parsing fails,
    returns UnstructuredResponse with the raw text.
    
    Args:
        response_text: Response text from LLM
        parser_func: Parser function (parse_design_review_response or parse_optimization_response)
        
    Returns:
        Parsed structured response or UnstructuredResponse fallback
        
    Example:
        >>> response = parse_response_with_fallback(
        ...     json_text,
        ...     parse_design_review_response
        ... )
        >>> if isinstance(response, UnstructuredResponse):
        ...     print(response.content)
    """
    try:
        return parser_func(response_text)
    except (ValueError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to parse structured response: {e}")
        logger.debug(f"Response text: {response_text[:200]}...")
        
        return UnstructuredResponse(
            content=response_text,
            has_structure=False,
            parse_error=str(e),
        )


def extract_json_from_markdown(response_text: str) -> str:
    """Extract JSON from markdown code blocks.
    
    Some LLMs wrap JSON in markdown code blocks like:
    ```json
    {"key": "value"}
    ```
    
    This function extracts the JSON content.
    
    Args:
        response_text: Response text that may contain markdown
        
    Returns:
        Extracted JSON string or original text if no code block found
    """
    # Check for JSON code block
    if "```json" in response_text:
        # Extract content between ```json and ```
        start = response_text.find("```json") + 7
        end = response_text.find("```", start)
        if end > start:
            return response_text[start:end].strip()
    
    # Check for generic code block
    if "```" in response_text:
        start = response_text.find("```") + 3
        end = response_text.find("```", start)
        if end > start:
            content = response_text[start:end].strip()
            # Only return if it looks like JSON
            if content.startswith("{") or content.startswith("["):
                return content
    
    # No code block found, return original
    return response_text.strip()


def safe_parse_design_review(response_text: str) -> DesignReviewResponse | UnstructuredResponse:
    """Safely parse design review response with markdown extraction.
    
    Args:
        response_text: Raw response text from LLM
        
    Returns:
        DesignReviewResponse or UnstructuredResponse fallback
    """
    # Extract JSON from markdown if present
    json_text = extract_json_from_markdown(response_text)
    
    # Parse with fallback
    return parse_response_with_fallback(json_text, parse_design_review_response)


def safe_parse_optimization(response_text: str) -> OptimizationResponse | UnstructuredResponse:
    """Safely parse optimization response with markdown extraction.
    
    Args:
        response_text: Raw response text from LLM
        
    Returns:
        OptimizationResponse or UnstructuredResponse fallback
    """
    # Extract JSON from markdown if present
    json_text = extract_json_from_markdown(response_text)
    
    # Parse with fallback
    return parse_response_with_fallback(json_text, parse_optimization_response)
