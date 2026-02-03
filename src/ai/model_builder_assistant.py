"""
Model Builder Assistant for PrelimStruct AI Chat.

This module provides a conversational AI assistant for extracting building
parameters from natural language descriptions and guiding FEM model setup.

Features:
- Intent detection for building descriptions
- Parameter extraction from text (floors, bay size, heights, etc.)
- Parameter validation with reasonable defaults
- Conversation context management

Usage:
    from src.ai import AIService
    from src.ai.model_builder_assistant import ModelBuilderAssistant

    ai_service = AIService.from_env()
    assistant = ModelBuilderAssistant(ai_service)
    
    result = await assistant.process_message("30 story building with 8m x 10m bays")
    print(result["extracted_params"])
"""

import re
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

from .llm_service import AIService
from .prompts import MODEL_BUILDER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class Intent(Enum):
    """User intent classification for model builder chat."""
    
    DESCRIBE_BUILDING = "describe_building"
    MODIFY_PARAMETER = "modify_parameter"
    ASK_QUESTION = "ask_question"
    CONFIRM_MODEL = "confirm_model"
    UNKNOWN = "unknown"


@dataclass
class BuildingParameters:
    """Extracted building parameters from user description.
    
    Attributes:
        num_floors: Number of floors/stories
        floor_height: Floor-to-floor height in meters
        bay_x: Bay dimension in X direction (meters)
        bay_y: Bay dimension in Y direction (meters)
        num_bays_x: Number of bays in X direction
        num_bays_y: Number of bays in Y direction
        building_type: Building use type (residential, office, etc.)
        concrete_grade: Concrete grade (e.g., "C40")
        core_wall_config: Core wall configuration type
    """
    num_floors: Optional[int] = None
    floor_height: Optional[float] = None
    bay_x: Optional[float] = None
    bay_y: Optional[float] = None
    num_bays_x: Optional[int] = None
    num_bays_y: Optional[int] = None
    building_type: Optional[str] = None
    concrete_grade: Optional[str] = None
    core_wall_config: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in self.__dict__.items() if v is not None}
    
    def get_missing_required(self) -> List[str]:
        """Get list of required parameters that are still missing."""
        required = ["num_floors", "floor_height", "bay_x", "bay_y"]
        return [p for p in required if getattr(self, p) is None]


class ModelBuilderAssistant:
    """AI-powered assistant for building model setup.
    
    Extracts building parameters from natural language and guides
    users through FEM model configuration.
    
    Attributes:
        ai_service: AIService instance for LLM interactions
        parameters: Currently extracted building parameters
        conversation_history: List of previous messages
    """
    
    # Regex patterns for parameter extraction
    PATTERNS = {
        # "30 story", "30 floors", "30-storey"
        "num_floors": [
            r"(\d+)\s*(?:stor(?:e?y|ies)|floors?)",
            r"(\d+)\s*(?:-)?stor(?:e?y|ies)",
        ],
        # "3.5m floor height", "floor height 3.5m", "3500mm floor height"
        "floor_height": [
            r"(\d+(?:\.\d+)?)\s*m\s*(?:floor|storey|story)\s*height",
            r"(?:floor|storey|story)\s*height[:\s]*(\d+(?:\.\d+)?)\s*m",
            r"(\d+(?:\.\d+)?)\s*m\s*(?:floor-to-floor|f2f)",
            r"(\d{4})\s*mm\s*(?:floor|storey|story)\s*height",
        ],
        # "8m x 10m bays", "8x10m bay", "8m by 10m grid"
        "bay_dimensions": [
            r"(\d+(?:\.\d+)?)\s*m?\s*[xX×]\s*(\d+(?:\.\d+)?)\s*m?\s*(?:bay|grid|span)",
            r"(\d+(?:\.\d+)?)\s*m\s*(?:by|x|×)\s*(\d+(?:\.\d+)?)\s*m\s*(?:bay|grid|span)?",
            r"bay[s]?\s*(?:of|:)?\s*(\d+(?:\.\d+)?)\s*m?\s*[xX×]\s*(\d+(?:\.\d+)?)\s*m?",
        ],
        # "5 bays", "5x6 bays", "5 bays x 6 bays"
        "num_bays": [
            r"(\d+)\s*[xX×]\s*(\d+)\s*bays?",
            r"(\d+)\s*bays?\s*(?:in\s*)?(?:x|×|by)\s*(\d+)\s*bays?",
        ],
        # "residential", "office", "commercial"
        "building_type": [
            r"\b(residential|office|commercial|retail|hotel|mixed[- ]?use|car\s*park|plant\s*room)\b",
        ],
        # "C40", "C50", "grade 40"
        "concrete_grade": [
            r"\b[Cc](\d{2,3})\b",
            r"grade\s*(\d{2,3})",
            r"(\d{2,3})\s*(?:MPa|mpa)\s*concrete",
        ],
    }
    
    # Default values for Hong Kong practice
    DEFAULTS = {
        "floor_height": 3.5,  # meters
        "bay_x": 8.0,  # meters
        "bay_y": 8.0,  # meters
        "num_bays_x": 3,
        "num_bays_y": 3,
        "concrete_grade": "C40",
        "building_type": "residential",
    }
    
    # Validation limits
    LIMITS = {
        "num_floors": (1, 100),
        "floor_height": (2.5, 6.0),
        "bay_x": (4.0, 15.0),
        "bay_y": (4.0, 15.0),
        "num_bays_x": (1, 20),
        "num_bays_y": (1, 20),
    }
    
    def __init__(self, ai_service: Optional[AIService] = None):
        """Initialize the model builder assistant.
        
        Args:
            ai_service: Optional AIService instance. If None, AI features
                       will be disabled and only regex extraction used.
        """
        self.ai_service = ai_service
        self.parameters = BuildingParameters()
        self.conversation_history: List[Dict[str, str]] = []
    
    async def process_message(self, user_message: str) -> Dict[str, Any]:
        """Process a user message and extract building parameters.
        
        Args:
            user_message: Natural language input from user
            
        Returns:
            Dictionary containing:
            - intent: Detected user intent
            - extracted_params: Newly extracted parameters
            - current_params: All parameters extracted so far
            - missing_params: Required parameters still missing
            - response: AI-generated response (if ai_service available)
            - validation_issues: Any validation problems found
        """
        # Store in conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Detect intent
        intent = self._detect_intent(user_message)
        
        # Extract parameters from text
        extracted = self.extract_parameters(user_message)
        
        # Merge with existing parameters
        for key, value in extracted.items():
            if value is not None:
                setattr(self.parameters, key, value)
        
        # Validate parameters
        validation = self.validate_parameters(self.parameters.to_dict())
        
        # Generate AI response if service available
        response = ""
        if self.ai_service:
            response = await self._generate_response(user_message, extracted, validation)
            self.conversation_history.append({
                "role": "assistant",
                "content": response
            })
        else:
            response = self._generate_local_response(extracted, validation)
        
        return {
            "intent": intent.value,
            "extracted_params": extracted,
            "current_params": self.parameters.to_dict(),
            "missing_params": self.parameters.get_missing_required(),
            "response": response,
            "validation_issues": validation.get("issues", []),
        }
    
    def extract_parameters(self, text: str) -> Dict[str, Any]:
        """Extract building parameters from text using regex patterns.
        
        Args:
            text: Natural language text to parse
            
        Returns:
            Dictionary of extracted parameter values
        """
        text_lower = text.lower()
        extracted: Dict[str, Any] = {}
        
        # Extract number of floors
        for pattern in self.PATTERNS["num_floors"]:
            match = re.search(pattern, text_lower)
            if match:
                extracted["num_floors"] = int(match.group(1))
                break
        
        # Extract floor height
        for pattern in self.PATTERNS["floor_height"]:
            match = re.search(pattern, text_lower)
            if match:
                value = float(match.group(1))
                # Convert mm to m if needed
                if value > 100:
                    value = value / 1000
                extracted["floor_height"] = value
                break
        
        # Extract bay dimensions (X x Y)
        for pattern in self.PATTERNS["bay_dimensions"]:
            match = re.search(pattern, text_lower)
            if match:
                extracted["bay_x"] = float(match.group(1))
                extracted["bay_y"] = float(match.group(2))
                break
        
        # Extract number of bays
        for pattern in self.PATTERNS["num_bays"]:
            match = re.search(pattern, text_lower)
            if match:
                extracted["num_bays_x"] = int(match.group(1))
                extracted["num_bays_y"] = int(match.group(2))
                break
        
        # Extract building type
        for pattern in self.PATTERNS["building_type"]:
            match = re.search(pattern, text_lower)
            if match:
                building_type = match.group(1).replace(" ", "_").replace("-", "_")
                extracted["building_type"] = building_type
                break
        
        # Extract concrete grade
        for pattern in self.PATTERNS["concrete_grade"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                grade = int(match.group(1))
                extracted["concrete_grade"] = f"C{grade}"
                break
        
        return extracted
    
    def validate_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate extracted parameters against limits.
        
        Args:
            params: Dictionary of parameter values
            
        Returns:
            Dictionary with:
            - valid: Boolean indicating if all params are valid
            - issues: List of validation issue descriptions
            - corrected: Dictionary of corrected values (clamped to limits)
        """
        issues: List[str] = []
        corrected: Dict[str, Any] = {}
        
        for param_name, (min_val, max_val) in self.LIMITS.items():
            if param_name in params and params[param_name] is not None:
                value = params[param_name]
                if value < min_val:
                    issues.append(
                        f"{param_name}={value} is below minimum ({min_val}). "
                        f"Using {min_val}."
                    )
                    corrected[param_name] = min_val
                elif value > max_val:
                    issues.append(
                        f"{param_name}={value} exceeds maximum ({max_val}). "
                        f"Using {max_val}."
                    )
                    corrected[param_name] = max_val
        
        # Apply corrections
        for key, value in corrected.items():
            if hasattr(self.parameters, key):
                setattr(self.parameters, key, value)
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "corrected": corrected,
        }
    
    def apply_defaults(self) -> Dict[str, Any]:
        """Apply default values to missing parameters.
        
        Returns:
            Dictionary of parameters with defaults applied
        """
        applied_defaults: Dict[str, Any] = {}
        
        for param_name, default_value in self.DEFAULTS.items():
            if getattr(self.parameters, param_name, None) is None:
                setattr(self.parameters, param_name, default_value)
                applied_defaults[param_name] = default_value
        
        return applied_defaults
    
    def reset(self) -> None:
        """Reset assistant state for a new conversation."""
        self.parameters = BuildingParameters()
        self.conversation_history.clear()

    def to_project_config(self) -> Dict[str, Any]:
        """Convert extracted parameters to ProjectData configuration.

        Maps BuildingParameters to dictionary format that can update ProjectData
        fields via Streamlit session state. Handles partial configurations by
        only returning fields that were explicitly extracted.

        Returns:
            Dictionary with keys matching ProjectData structure:
            - geometry: Dict with bay_x, bay_y, floors, story_height
            - materials: Dict with concrete grades if specified
            - lateral: Dict with core wall config if specified
        """
        config: Dict[str, Any] = {}

        # Geometry mapping
        geometry = {}
        if self.parameters.num_floors is not None:
            geometry["floors"] = self.parameters.num_floors
        if self.parameters.floor_height is not None:
            geometry["story_height"] = self.parameters.floor_height
        if self.parameters.bay_x is not None:
            geometry["bay_x"] = self.parameters.bay_x
        if self.parameters.bay_y is not None:
            geometry["bay_y"] = self.parameters.bay_y
        if self.parameters.num_bays_x is not None:
            geometry["num_bays_x"] = self.parameters.num_bays_x
        if self.parameters.num_bays_y is not None:
            geometry["num_bays_y"] = self.parameters.num_bays_y

        if geometry:
            config["geometry"] = geometry

        # Materials mapping (concrete grade)
        if self.parameters.concrete_grade is not None:
            grade_value = int(self.parameters.concrete_grade.replace("C", ""))
            config["materials"] = {
                "fcu_slab": grade_value,
                "fcu_beam": grade_value,
                "fcu_column": grade_value,
            }

        # Lateral/Core wall configuration
        if self.parameters.core_wall_config is not None:
            config["lateral"] = {
                "core_wall_config": self.parameters.core_wall_config,
            }

        # Building type mapping to load presets (if needed)
        if self.parameters.building_type is not None:
            config["building_type"] = self.parameters.building_type

        return config

    def get_config_preview(self) -> str:
        """Generate human-readable preview of configuration to be applied.

        Returns:
            Markdown-formatted preview string showing what will change
        """
        config = self.to_project_config()

        if not config:
            return "No configuration extracted yet. Describe your building to get started."

        lines = ["**Configuration to Apply:**\n"]

        # Geometry section
        if "geometry" in config:
            lines.append("**Geometry:**")
            geom = config["geometry"]
            if "floors" in geom:
                lines.append(f"- Floors: {geom['floors']}")
            if "story_height" in geom:
                lines.append(f"- Floor Height: {geom['story_height']:.2f}m")
            if "bay_x" in geom and "bay_y" in geom:
                lines.append(f"- Bay Size: {geom['bay_x']:.1f}m × {geom['bay_y']:.1f}m")
            elif "bay_x" in geom:
                lines.append(f"- Bay X: {geom['bay_x']:.1f}m")
            elif "bay_y" in geom:
                lines.append(f"- Bay Y: {geom['bay_y']:.1f}m")
            if "num_bays_x" in geom and "num_bays_y" in geom:
                lines.append(f"- Grid: {geom['num_bays_x']} × {geom['num_bays_y']} bays")
            lines.append("")

        # Materials section
        if "materials" in config:
            mat = config["materials"]
            if "fcu_slab" in mat:
                lines.append("**Materials:**")
                lines.append(f"- Concrete Grade: C{mat['fcu_slab']}")
                lines.append("")

        # Lateral system section
        if "lateral" in config:
            lat = config["lateral"]
            if "core_wall_config" in lat:
                lines.append("**Lateral System:**")
                lines.append(f"- Core Wall: {lat['core_wall_config'].replace('_', ' ').title()}")
                lines.append("")

        # Building type
        if "building_type" in config:
            lines.append("**Building Type:**")
            lines.append(f"- {config['building_type'].replace('_', ' ').title()}")
            lines.append("")

        # Missing parameters warning
        missing = self.parameters.get_missing_required()
        if missing:
            lines.append("**⚠️ Missing Required:**")
            lines.append(f"- {', '.join(missing)}")
            lines.append("- These will use default values")

        return "\n".join(lines)
    
    def _detect_intent(self, text: str) -> Intent:
        """Detect user intent from message text.
        
        Args:
            text: User message text
            
        Returns:
            Detected Intent enum value
        """
        text_lower = text.lower()
        
        # Check for questions FIRST (most specific)
        if "?" in text or text_lower.startswith(("what", "how", "why", "can", "is there")):
            return Intent.ASK_QUESTION
        
        # Check for modification intent (before building keywords)
        modify_keywords = ["change", "modify", "update", "set", "make it", "adjust"]
        if any(kw in text_lower for kw in modify_keywords):
            return Intent.MODIFY_PARAMETER
        
        # Check for confirmation
        confirm_keywords = ["ok", "confirm", "yes", "proceed", "looks good", "create", "build it"]
        if any(kw in text_lower for kw in confirm_keywords):
            return Intent.CONFIRM_MODEL
        
        # Check for building description keywords (least specific)
        building_keywords = [
            "building", "tower", "story", "storey", "floor", "bay", 
            "grid", "span", "residential", "office", "commercial"
        ]
        if any(kw in text_lower for kw in building_keywords):
            return Intent.DESCRIBE_BUILDING
        
        return Intent.UNKNOWN
    
    async def _generate_response(
        self, 
        user_message: str, 
        extracted: Dict[str, Any],
        validation: Dict[str, Any]
    ) -> str:
        """Generate AI response using LLM service.
        
        Args:
            user_message: Original user message
            extracted: Extracted parameters
            validation: Validation results
            
        Returns:
            AI-generated response string
        """
        if not self.ai_service:
            return self._generate_local_response(extracted, validation)
        
        # Build context for AI
        context = f"""
Current extracted parameters:
{self.parameters.to_dict()}

Newly extracted from this message:
{extracted}

Missing required parameters:
{self.parameters.get_missing_required()}

Validation issues:
{validation.get('issues', [])}
"""
        
        try:
            response = self.ai_service.chat(
                user_message=user_message,
                system_prompt=MODEL_BUILDER_SYSTEM_PROMPT + "\n\nContext:\n" + context,
                conversation_history=[
                    {"role": m["role"], "content": m["content"]} 
                    for m in self.conversation_history[:-1]
                ],
                temperature=0.7,
                max_tokens=200,
            )
            return response
        except Exception as e:
            logger.warning(f"AI response generation failed: {e}")
            return self._generate_local_response(extracted, validation)
    
    def _generate_local_response(
        self, 
        extracted: Dict[str, Any],
        validation: Dict[str, Any]
    ) -> str:
        """Generate a local response without AI.
        
        Args:
            extracted: Extracted parameters
            validation: Validation results
            
        Returns:
            Generated response string
        """
        parts = []
        
        if extracted:
            param_str = ", ".join(f"{k}={v}" for k, v in extracted.items())
            parts.append(f"Extracted: {param_str}")
        
        if validation.get("issues"):
            parts.append("Validation: " + "; ".join(validation["issues"]))
        
        missing = self.parameters.get_missing_required()
        if missing:
            parts.append(f"Still need: {', '.join(missing)}")
        else:
            parts.append("All required parameters set. Ready to create model.")
        
        return " | ".join(parts) if parts else "I didn't extract any parameters."


# Convenience function for quick parameter extraction
def extract_building_params(text: str) -> Dict[str, Any]:
    """Quick utility to extract building parameters from text.
    
    Args:
        text: Natural language building description
        
    Returns:
        Dictionary of extracted parameters
    """
    assistant = ModelBuilderAssistant()
    return assistant.extract_parameters(text)
