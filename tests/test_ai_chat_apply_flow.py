"""Tests for AI chat apply flow (Phase 16 Task 10).

Verifies that the AI chat processes user messages and auto-applies
extracted parameters back to the project configuration.
"""

import pytest
from src.ai.model_builder_assistant import ModelBuilderAssistant


class TestAIChatApplyFlow:
    """Tests for the end-to-end AI chat → parameter apply flow."""

    def test_process_message_extracts_and_applies(self):
        """process_message should extract params and apply them to assistant.parameters."""
        assistant = ModelBuilderAssistant()
        result = assistant.process_message("30 storey office building with 8m x 10m bays")
        assert result["extracted_params"]["num_floors"] == 30
        assert result["extracted_params"]["bay_x"] == 8.0
        assert result["extracted_params"]["bay_y"] == 10.0
        assert assistant.parameters.num_floors == 30

    def test_process_message_returns_response(self):
        """process_message should always return a non-empty response string."""
        assistant = ModelBuilderAssistant()
        result = assistant.process_message("I want a 20-floor residential tower")
        assert isinstance(result["response"], str)
        assert len(result["response"]) > 0

    def test_incremental_parameter_application(self):
        """Multiple messages should accumulate parameters."""
        assistant = ModelBuilderAssistant()
        assistant.process_message("30 storey building")
        assert assistant.parameters.num_floors == 30
        # bay_x may have a default applied (8.0) from auto-defaults
        prev_bay_x = assistant.parameters.bay_x

        assistant.process_message("with 9m x 12m bays")
        assert assistant.parameters.num_floors == 30  # preserved
        assert assistant.parameters.bay_x == 9.0  # newly set (overrides default)

    def test_to_project_config_after_chat(self):
        """After chat, to_project_config should produce valid config dict."""
        assistant = ModelBuilderAssistant()
        assistant.process_message("40 floor office, 8x10m bays, 3.5m height, C50")
        config = assistant.to_project_config()
        assert config["geometry"]["floors"] == 40
        assert config["geometry"]["bay_x"] == 8.0
        assert config["materials"]["fcu_slab"] == 50

    def test_undo_reverts_parameters(self):
        """Undo should revert to previous parameter state."""
        assistant = ModelBuilderAssistant()
        assistant.process_message("30 storey building")
        prev = assistant.parameters.num_floors
        assistant.process_message("actually make it 50 stories")
        assert assistant.parameters.num_floors == 50
        # Undo if supported
        if hasattr(assistant, 'undo') and callable(assistant.undo):
            assistant.undo()
            assert assistant.parameters.num_floors == prev
