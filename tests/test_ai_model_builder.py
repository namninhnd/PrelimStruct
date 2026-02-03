"""
Unit tests for Model Builder Assistant.

Tests cover:
- Parameter extraction from natural language
- BuildingParameters dataclass
- Intent detection
- Parameter validation
- Conversation flow
"""

import pytest

from src.ai.model_builder_assistant import (
    ModelBuilderAssistant,
    BuildingParameters,
    Intent,
    extract_building_params,
)


class TestBuildingParameters:
    """Tests for BuildingParameters dataclass."""
    
    def test_empty_params(self):
        """Test creating empty parameters."""
        params = BuildingParameters()
        assert params.num_floors is None
        assert params.floor_height is None
        assert params.bay_x is None
        assert params.bay_y is None
    
    def test_to_dict_excludes_none(self):
        """Test to_dict only includes non-None values."""
        params = BuildingParameters(num_floors=30, floor_height=3.5)
        result = params.to_dict()
        assert result == {"num_floors": 30, "floor_height": 3.5}
        assert "bay_x" not in result
    
    def test_get_missing_required(self):
        """Test getting list of missing required parameters."""
        params = BuildingParameters(num_floors=30)
        missing = params.get_missing_required()
        assert "floor_height" in missing
        assert "bay_x" in missing
        assert "bay_y" in missing
        assert "num_floors" not in missing
    
    def test_all_required_present(self):
        """Test when all required parameters are set."""
        params = BuildingParameters(
            num_floors=30,
            floor_height=3.5,
            bay_x=8.0,
            bay_y=10.0
        )
        missing = params.get_missing_required()
        assert len(missing) == 0


class TestParameterExtraction:
    """Tests for extract_parameters method."""
    
    def test_extract_floors_story(self):
        """Test extracting floor count with 'story' keyword."""
        assistant = ModelBuilderAssistant()
        result = assistant.extract_parameters("30 story building")
        assert result["num_floors"] == 30
    
    def test_extract_floors_storey(self):
        """Test extracting floor count with 'storey' (British) spelling."""
        assistant = ModelBuilderAssistant()
        result = assistant.extract_parameters("25 storey tower")
        assert result["num_floors"] == 25
    
    def test_extract_floors_floor(self):
        """Test extracting floor count with 'floor' keyword."""
        assistant = ModelBuilderAssistant()
        result = assistant.extract_parameters("a 40 floor residential tower")
        assert result["num_floors"] == 40
    
    def test_extract_bay_dimensions(self):
        """Test extracting bay dimensions X x Y."""
        assistant = ModelBuilderAssistant()
        result = assistant.extract_parameters("with 8m x 10m bays")
        assert result["bay_x"] == 8.0
        assert result["bay_y"] == 10.0
    
    def test_extract_bay_dimensions_by(self):
        """Test extracting bay dimensions with 'by' keyword."""
        assistant = ModelBuilderAssistant()
        result = assistant.extract_parameters("grid 9m by 12m span")
        assert result["bay_x"] == 9.0
        assert result["bay_y"] == 12.0
    
    def test_extract_floor_height_meters(self):
        """Test extracting floor height in meters."""
        assistant = ModelBuilderAssistant()
        result = assistant.extract_parameters("residential tower, 3.5m floor height")
        assert result["floor_height"] == 3.5
    
    def test_extract_floor_height_mm(self):
        """Test extracting floor height in millimeters (converts to m)."""
        assistant = ModelBuilderAssistant()
        result = assistant.extract_parameters("4000mm floor height")
        assert result["floor_height"] == 4.0
    
    def test_extract_building_type_residential(self):
        """Test extracting residential building type."""
        assistant = ModelBuilderAssistant()
        result = assistant.extract_parameters("residential tower")
        assert result["building_type"] == "residential"
    
    def test_extract_building_type_office(self):
        """Test extracting office building type."""
        assistant = ModelBuilderAssistant()
        result = assistant.extract_parameters("modern office building")
        assert result["building_type"] == "office"
    
    def test_extract_concrete_grade(self):
        """Test extracting concrete grade."""
        assistant = ModelBuilderAssistant()
        result = assistant.extract_parameters("using C50 concrete")
        assert result["concrete_grade"] == "C50"
    
    def test_extract_combined_description(self):
        """Test extracting multiple parameters from one description."""
        assistant = ModelBuilderAssistant()
        result = assistant.extract_parameters(
            "30 story residential building with 8m x 10m bays"
        )
        assert result["num_floors"] == 30
        assert result["building_type"] == "residential"
        assert result["bay_x"] == 8.0
        assert result["bay_y"] == 10.0
    
    def test_extract_full_description(self):
        """Test extracting from a comprehensive building description."""
        assistant = ModelBuilderAssistant()
        result = assistant.extract_parameters(
            "45 storey office tower with 9m x 12m grid, "
            "3.2m floor height, using C60 concrete"
        )
        assert result["num_floors"] == 45
        assert result["building_type"] == "office"
        assert result["bay_x"] == 9.0
        assert result["bay_y"] == 12.0
        assert result["floor_height"] == 3.2
        assert result["concrete_grade"] == "C60"


class TestIntentDetection:
    """Tests for intent detection."""
    
    def test_detect_building_description(self):
        """Test detecting building description intent."""
        assistant = ModelBuilderAssistant()
        intent = assistant._detect_intent("30 story building with 8m bays")
        assert intent == Intent.DESCRIBE_BUILDING
    
    def test_detect_modification(self):
        """Test detecting modification intent."""
        assistant = ModelBuilderAssistant()
        intent = assistant._detect_intent("change the floor height to 4m")
        assert intent == Intent.MODIFY_PARAMETER
    
    def test_detect_question(self):
        """Test detecting question intent."""
        assistant = ModelBuilderAssistant()
        intent = assistant._detect_intent("what is the typical bay size?")
        assert intent == Intent.ASK_QUESTION
    
    def test_detect_confirmation(self):
        """Test detecting confirmation intent."""
        assistant = ModelBuilderAssistant()
        intent = assistant._detect_intent("ok, proceed with the model")
        assert intent == Intent.CONFIRM_MODEL
    
    def test_detect_unknown(self):
        """Test detecting unknown intent."""
        assistant = ModelBuilderAssistant()
        intent = assistant._detect_intent("hello there")
        assert intent == Intent.UNKNOWN


class TestParameterValidation:
    """Tests for parameter validation."""
    
    def test_validate_normal_values(self):
        """Test validation passes for normal values."""
        assistant = ModelBuilderAssistant()
        result = assistant.validate_parameters({
            "num_floors": 30,
            "floor_height": 3.5,
            "bay_x": 8.0,
            "bay_y": 10.0
        })
        assert result["valid"] is True
        assert len(result["issues"]) == 0
    
    def test_validate_floors_too_high(self):
        """Test validation flags excessive floor count."""
        assistant = ModelBuilderAssistant()
        result = assistant.validate_parameters({
            "num_floors": 150,
        })
        assert result["valid"] is False
        assert len(result["issues"]) > 0
        assert result["corrected"]["num_floors"] == 100
    
    def test_validate_floor_height_too_low(self):
        """Test validation flags floor height below minimum."""
        assistant = ModelBuilderAssistant()
        result = assistant.validate_parameters({
            "floor_height": 2.0,
        })
        assert result["valid"] is False
        assert result["corrected"]["floor_height"] == 2.5
    
    def test_validate_bay_too_large(self):
        """Test validation flags bay size above maximum."""
        assistant = ModelBuilderAssistant()
        result = assistant.validate_parameters({
            "bay_x": 20.0,
        })
        assert result["valid"] is False
        assert result["corrected"]["bay_x"] == 15.0


class TestConvenienceFunction:
    """Tests for the extract_building_params convenience function."""
    
    def test_quick_extraction(self):
        """Test quick parameter extraction utility."""
        result = extract_building_params("30 story building with 8m x 10m bays")
        assert result["num_floors"] == 30
        assert result["bay_x"] == 8.0
        assert result["bay_y"] == 10.0


class TestApplyDefaults:
    """Tests for applying default values."""
    
    def test_apply_defaults_to_empty(self):
        """Test applying defaults to empty parameters."""
        assistant = ModelBuilderAssistant()
        applied = assistant.apply_defaults()
        
        assert "floor_height" in applied
        assert assistant.parameters.floor_height == 3.5
        assert assistant.parameters.bay_x == 8.0
        assert assistant.parameters.concrete_grade == "C40"
    
    def test_apply_defaults_preserves_existing(self):
        """Test that defaults don't overwrite existing values."""
        assistant = ModelBuilderAssistant()
        assistant.parameters.floor_height = 4.0
        assistant.parameters.bay_x = 9.0
        
        applied = assistant.apply_defaults()
        
        # These should NOT be in applied since they had values
        assert "floor_height" not in applied
        assert "bay_x" not in applied
        
        # Original values should be preserved
        assert assistant.parameters.floor_height == 4.0
        assert assistant.parameters.bay_x == 9.0


class TestReset:
    """Tests for resetting assistant state."""
    
    def test_reset_clears_parameters(self):
        """Test that reset clears all parameters."""
        assistant = ModelBuilderAssistant()
        assistant.parameters.num_floors = 30
        assistant.parameters.floor_height = 3.5
        assistant.conversation_history.append({"role": "user", "content": "test"})
        
        assistant.reset()
        
        assert assistant.parameters.num_floors is None
        assert assistant.parameters.floor_height is None
        assert len(assistant.conversation_history) == 0


class TestLocalResponseGeneration:
    """Tests for local response generation (no AI)."""

    def test_local_response_with_extracted(self):
        """Test local response when parameters are extracted."""
        assistant = ModelBuilderAssistant()  # No AI service
        extracted = {"num_floors": 30, "bay_x": 8.0}
        validation = {"valid": True, "issues": []}

        response = assistant._generate_local_response(extracted, validation)

        assert "Extracted" in response
        assert "30" in response

    def test_local_response_with_validation_issues(self):
        """Test local response includes validation issues."""
        assistant = ModelBuilderAssistant()
        extracted = {}
        validation = {"valid": False, "issues": ["floor_height too low"]}

        response = assistant._generate_local_response(extracted, validation)

        assert "Validation" in response
        assert "floor_height" in response

    def test_local_response_shows_missing(self):
        """Test local response shows missing parameters."""
        assistant = ModelBuilderAssistant()
        extracted = {"num_floors": 30}
        assistant.parameters.num_floors = 30
        validation = {"valid": True, "issues": []}

        response = assistant._generate_local_response(extracted, validation)

        assert "Still need" in response or "Ready" not in response


class TestConfigurationMapping:
    """Tests for Task 22.3 - Configuration mapping to ProjectData."""

    def test_to_project_config_geometry(self):
        """Test mapping geometry parameters to config dict."""
        assistant = ModelBuilderAssistant()
        assistant.parameters.num_floors = 30
        assistant.parameters.floor_height = 3.5
        assistant.parameters.bay_x = 8.0
        assistant.parameters.bay_y = 10.0

        config = assistant.to_project_config()

        assert "geometry" in config
        assert config["geometry"]["floors"] == 30
        assert config["geometry"]["story_height"] == 3.5
        assert config["geometry"]["bay_x"] == 8.0
        assert config["geometry"]["bay_y"] == 10.0

    def test_to_project_config_materials(self):
        """Test mapping concrete grade to materials config."""
        assistant = ModelBuilderAssistant()
        assistant.parameters.concrete_grade = "C50"

        config = assistant.to_project_config()

        assert "materials" in config
        assert config["materials"]["fcu_slab"] == 50
        assert config["materials"]["fcu_beam"] == 50
        assert config["materials"]["fcu_column"] == 50

    def test_to_project_config_partial(self):
        """Test partial configuration only includes set values."""
        assistant = ModelBuilderAssistant()
        assistant.parameters.num_floors = 30
        # Other params remain None

        config = assistant.to_project_config()

        assert "geometry" in config
        assert "floors" in config["geometry"]
        # bay_x/bay_y should not be in config since they're None
        assert "bay_x" not in config["geometry"]
        assert "materials" not in config

    def test_to_project_config_building_type(self):
        """Test building type mapping."""
        assistant = ModelBuilderAssistant()
        assistant.parameters.building_type = "residential"

        config = assistant.to_project_config()

        assert "building_type" in config
        assert config["building_type"] == "residential"

    def test_to_project_config_empty(self):
        """Test empty config when no parameters extracted."""
        assistant = ModelBuilderAssistant()

        config = assistant.to_project_config()

        assert config == {}

    def test_get_config_preview_full(self):
        """Test configuration preview with full parameters."""
        assistant = ModelBuilderAssistant()
        assistant.parameters.num_floors = 30
        assistant.parameters.floor_height = 3.5
        assistant.parameters.bay_x = 8.0
        assistant.parameters.bay_y = 10.0
        assistant.parameters.concrete_grade = "C40"
        assistant.parameters.building_type = "residential"

        preview = assistant.get_config_preview()

        assert "Geometry:" in preview
        assert "30" in preview
        assert "3.50m" in preview
        assert "8.0m × 10.0m" in preview
        assert "C40" in preview
        assert "Residential" in preview

    def test_get_config_preview_empty(self):
        """Test preview message when no config extracted."""
        assistant = ModelBuilderAssistant()

        preview = assistant.get_config_preview()

        assert "No configuration" in preview or "Describe your building" in preview

    def test_get_config_preview_with_missing(self):
        """Test preview shows missing required parameters."""
        assistant = ModelBuilderAssistant()
        assistant.parameters.num_floors = 30
        # floor_height, bay_x, bay_y are missing

        preview = assistant.get_config_preview()

        assert "Missing Required" in preview or "⚠️" in preview
        assert "default" in preview.lower()


class TestConfigurationApplication:
    """Tests for applying configuration (integration with ProjectData)."""

    def test_apply_full_geometry(self):
        """Test applying full geometry configuration."""
        assistant = ModelBuilderAssistant()
        assistant.parameters.num_floors = 30
        assistant.parameters.floor_height = 3.5
        assistant.parameters.bay_x = 8.0
        assistant.parameters.bay_y = 10.0

        config = assistant.to_project_config()

        # Verify config structure matches ProjectData expectations
        assert "geometry" in config
        geom = config["geometry"]
        assert all(k in geom for k in ["floors", "story_height", "bay_x", "bay_y"])

    def test_apply_preserves_unset_fields(self):
        """Test that unset fields are not included in config."""
        assistant = ModelBuilderAssistant()
        assistant.parameters.num_floors = 30

        config = assistant.to_project_config()

        # Only floors should be set
        geom = config.get("geometry", {})
        assert "floors" in geom
        assert "bay_x" not in geom  # Shouldn't be in config if None

    def test_num_bays_extraction_and_mapping(self):
        """Test number of bays extraction and mapping."""
        assistant = ModelBuilderAssistant()
        result = assistant.extract_parameters("5 x 6 bays")

        assert result["num_bays_x"] == 5
        assert result["num_bays_y"] == 6

        # Apply to parameters
        for k, v in result.items():
            setattr(assistant.parameters, k, v)

        config = assistant.to_project_config()
        assert config["geometry"]["num_bays_x"] == 5
        assert config["geometry"]["num_bays_y"] == 6
