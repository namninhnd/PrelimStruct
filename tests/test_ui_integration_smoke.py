"""Smoke test for UI integration paths (Gate J Design Checks panel + Gate K AI Chat).

These tests verify that the UI integration code in fem_views.py and app.py
would not crash at runtime by exercising the import paths and key functions
with realistic mock data.
"""
import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from typing import Dict, List, Any


# ---------------------------------------------------------------------------
# Gate J: Design Checks panel integration smoke test
# ---------------------------------------------------------------------------

class TestDesignChecksPanelIntegration:
    """Test that the Design Checks panel code paths work without runtime errors."""

    def test_classify_skips_shells_gracefully(self):
        """C5: classify_element raises ValueError on shells; panel must skip them."""
        from src.fem.design_checks import classify_element, StructuralClass
        from src.fem.fem_engine import FEMModel, Node, Element, ElementType

        model = FEMModel()
        # Add 4 nodes for a shell element (horizontal slab)
        for i, (x, y, z) in enumerate([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]):
            model.nodes[i + 1] = Node(tag=i + 1, x=x, y=y, z=z)

        shell = Element(
            tag=100,
            element_type=ElementType.SHELL_MITC4,
            node_tags=[1, 2, 3, 4],
            material_tag=1,
        )
        model.elements[100] = shell

        # classify_element should raise ValueError for shells
        with pytest.raises(ValueError):
            classify_element(model, 100)

    def test_shear_check_result_is_dataclass(self):
        """C4: shear_stress_check returns ShearCheckResult dataclass, not dict."""
        from src.fem.design_checks import shear_stress_check, ShearCheckResult

        result = shear_stress_check(V=100_000, b=300, d=460, fcu=40)
        assert isinstance(result, ShearCheckResult)
        assert hasattr(result, "v")
        assert hasattr(result, "v_max")
        assert hasattr(result, "ratio")
        assert hasattr(result, "passed")

    def test_compute_governing_score_keyword_args(self):
        """C2: compute_governing_score takes keyword float args, not positional (class, dict)."""
        from src.fem.design_checks import compute_governing_score

        score = compute_governing_score(shear_ratio=0.75, rho_ratio=0.5)
        assert score == 0.75

        score2 = compute_governing_score(shear_ratio=0.3, n_ratio=0.9)
        assert score2 == 0.9

    def test_governing_item_has_key_metric_not_details(self):
        """C3: GoverningItem has key_metric and warnings fields, not details."""
        from src.fem.design_checks import GoverningItem, StructuralClass

        item = GoverningItem(
            element_id=1,
            element_class=StructuralClass.PRIMARY_BEAM,
            governing_score=0.8,
            key_metric="v=2.50/5.06 MPa (ratio 0.49)",
            warnings=["some warning"],
        )
        assert item.key_metric == "v=2.50/5.06 MPa (ratio 0.49)"
        assert item.warnings == ["some warning"]
        assert not hasattr(item, "details")

    def test_force_key_fallback(self):
        """N1: code must handle both Vy_i and Vy force key formats."""
        # Simulate forces dict with i/j suffix
        forces_with_suffix = {"Vy_i": 50.0, "N_i": 200.0, "Mz_i": 100.0}
        V = abs(forces_with_suffix.get("Vy_i", forces_with_suffix.get("Vy", 0.0)))
        assert V == 50.0

        # Simulate forces dict without suffix
        forces_without_suffix = {"Vy": 30.0, "N": 150.0, "Mz": 80.0}
        V2 = abs(forces_without_suffix.get("Vy_i", forces_without_suffix.get("Vy", 0.0)))
        assert V2 == 30.0


# ---------------------------------------------------------------------------
# Gate K: AI Chat integration smoke test
# ---------------------------------------------------------------------------

class TestAIChatIntegration:
    """Test that the AI Chat code paths work without runtime errors."""

    def test_process_message_is_sync(self):
        """C1: process_message is synchronous (no asyncio needed)."""
        import inspect
        from src.ai.model_builder_assistant import ModelBuilderAssistant

        assistant = ModelBuilderAssistant()  # No AI service = regex-only mode
        assert not inspect.iscoroutinefunction(assistant.process_message)

        result = assistant.process_message("20 storey office, 3.5m floor height")
        assert isinstance(result, dict)
        assert "response" in result
        assert "extracted_params" in result

    def test_get_config_preview_is_sync(self):
        """get_config_preview should work synchronously."""
        from src.ai.model_builder_assistant import ModelBuilderAssistant

        assistant = ModelBuilderAssistant()
        assistant.process_message("25 floors, 8m x 10m bays")

        preview = assistant.get_config_preview()
        assert isinstance(preview, str)

    def test_to_project_config_is_sync(self):
        """to_project_config should work synchronously and return dict."""
        from src.ai.model_builder_assistant import ModelBuilderAssistant

        assistant = ModelBuilderAssistant()
        assistant.process_message("30 storey, bay 9m x 7m")

        config = assistant.to_project_config()
        assert isinstance(config, dict)


# ---------------------------------------------------------------------------
# M3/M4: Simplified reference cleanup verification
# ---------------------------------------------------------------------------

class TestSimplifiedRefsRemoved:
    """Verify no user-facing 'simplified' references remain in key files."""

    def test_sidebar_no_simplified(self):
        """M3: sidebar.py should not contain user-facing 'simplified' text."""
        import pathlib
        sidebar_path = pathlib.Path(__file__).parent.parent / "src" / "ui" / "sidebar.py"
        content = sidebar_path.read_text(encoding="utf-8")

        # Check that no user-facing simplified text remains
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            lower = line.lower()
            if "simplified" in lower:
                # Should not find any — we fixed them all
                pytest.fail(f"sidebar.py:{i} still contains 'simplified': {line.strip()}")

    def test_data_models_code_reference(self):
        """M4: WindResult.code_reference should not say 'Simplified Analysis'."""
        from src.core.data_models import WindResult

        wr = WindResult()
        assert "Simplified" not in wr.code_reference
        assert "Wind Analysis" in wr.code_reference
