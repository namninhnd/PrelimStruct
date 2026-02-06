import pytest

from src.fem.fem_engine import Load, create_simple_frame_model
from src.fem.materials import ConcreteGrade, reset_material_tags
from src.fem.solver import analyze_model


def test_reaction_extraction_requires_reactions_call(ops_monkeypatch) -> None:
    """
    GIVEN a minimal FEM model with DL load and fixed supports
    WHEN analyzing the model with strict_reaction_mode enabled
    THEN node_reactions should be non-empty (proving ops.reactions() was called)
    AND at least one node should have non-zero vertical reaction (Fz at index 2)
    """
    reset_material_tags()
    model = create_simple_frame_model(
        bay_width=4.0,
        bay_height=3.0,
        n_bays=1,
        n_stories=1,
        concrete_grade=ConcreteGrade.C30,
        beam_width=300,
        beam_height=500,
        column_width=400,
        column_height=400,
    )

    model.add_load(Load(node_tag=4, load_values=[0, 0, -10000, 0, 0, 0], load_pattern=1))

    ops_monkeypatch.displacements = {
        1: [0, 0, 0, 0, 0, 0],
        2: [0, 0, 0, 0, 0, 0],
        3: [0, 0, -0.004, 0, 0, 0],
        4: [0, 0, -0.006, 0, 0, 0],
    }
    ops_monkeypatch._reaction_data = {
        1: [0, 0, 6000, 0, 0, 0],
        2: [0, 0, 4000, 0, 0, 0],
    }
    ops_monkeypatch.element_forces = {
        1: [0.0] * 12,
        2: [0.0] * 12,
        3: [0.0] * 12,
    }

    ops_monkeypatch.strict_reaction_mode = True

    results = analyze_model(model)
    result = results["combined"]

    assert result.success
    assert len(result.node_reactions) > 0, "Reactions should be extracted after analysis"

    has_non_zero_vertical = False
    for node_tag, reaction in result.node_reactions.items():
        if abs(reaction[2]) > 1e-10:
            has_non_zero_vertical = True
            break
    assert has_non_zero_vertical, "At least one node should have non-zero vertical reaction"


def test_reactions_method_is_called_before_extraction(ops_monkeypatch) -> None:
    """
    GIVEN a minimal FEM model with loads
    WHEN analyzing the model
    THEN ops.reactions() method should have been called
    """
    reset_material_tags()
    model = create_simple_frame_model(
        bay_width=4.0,
        bay_height=3.0,
        n_bays=1,
        n_stories=1,
        concrete_grade=ConcreteGrade.C30,
        beam_width=300,
        beam_height=500,
        column_width=400,
        column_height=400,
    )

    model.add_load(Load(node_tag=4, load_values=[0, 0, -10000, 0, 0, 0], load_pattern=1))

    ops_monkeypatch.displacements = {1: [0] * 6, 2: [0] * 6, 3: [0] * 6, 4: [0] * 6}
    ops_monkeypatch._reaction_data = {1: [0, 0, 5000, 0, 0, 0], 2: [0, 0, 5000, 0, 0, 0]}
    ops_monkeypatch.element_forces = {1: [0.0] * 12, 2: [0.0] * 12, 3: [0.0] * 12}

    ops_monkeypatch.reactions_called = False

    analyze_model(model)

    assert ops_monkeypatch.reactions_called, "ops.reactions() must be called before reading nodeReaction"
