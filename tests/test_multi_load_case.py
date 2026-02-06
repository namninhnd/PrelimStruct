import pytest

from src.fem.fem_engine import Load, create_simple_frame_model
from src.fem.materials import ConcreteGrade, reset_material_tags
from src.fem.solver import (
    AnalysisResult,
    LOAD_CASE_PATTERN_MAP,
    analyze_model,
)


def test_analyze_model_returns_dict(ops_monkeypatch) -> None:
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
    
    results = analyze_model(model)
    
    assert isinstance(results, dict)
    assert "combined" in results
    assert results["combined"].success


def test_analyze_model_multiple_load_cases(ops_monkeypatch) -> None:
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
    model.add_load(Load(node_tag=4, load_values=[0, 0, -5000, 0, 0, 0], load_pattern=2))
    
    ops_monkeypatch.displacements = {
        1: [0, 0, 0, 0, 0, 0],
        2: [0, 0, 0, 0, 0, 0],
        3: [0, 0, -0.002, 0, 0, 0],
        4: [0, 0, -0.003, 0, 0, 0],
    }
    ops_monkeypatch._reaction_data = {1: [0, 0, 3000, 0, 0, 0], 2: [0, 0, 2000, 0, 0, 0]}
    ops_monkeypatch.element_forces = {1: [0.0] * 12, 2: [0.0] * 12, 3: [0.0] * 12}
    
    results = analyze_model(model, load_cases=["DL", "SDL"])
    
    assert isinstance(results, dict)
    assert len(results) == 2
    assert "DL" in results
    assert "SDL" in results
    for lc_name, result in results.items():
        assert isinstance(result, AnalysisResult)
        assert lc_name in result.message


def test_analyze_model_all_seven_load_cases(ops_monkeypatch) -> None:
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
    for pattern_id in range(1, 8):
        model.add_load(
            Load(node_tag=4, load_values=[0, 0, -1000 * pattern_id, 0, 0, 0], load_pattern=pattern_id)
        )
    
    ops_monkeypatch.displacements = {
        1: [0, 0, 0, 0, 0, 0],
        2: [0, 0, 0, 0, 0, 0],
        3: [0, 0, -0.001, 0, 0, 0],
        4: [0, 0, -0.002, 0, 0, 0],
    }
    ops_monkeypatch._reaction_data = {1: [0, 0, 1000, 0, 0, 0], 2: [0, 0, 1000, 0, 0, 0]}
    ops_monkeypatch.element_forces = {1: [0.0] * 12, 2: [0.0] * 12, 3: [0.0] * 12}
    
    all_load_cases = ["DL", "SDL", "LL", "Wx+", "Wx-", "Wy+", "Wy-"]
    results = analyze_model(model, load_cases=all_load_cases)
    
    assert len(results) == 7
    for lc in all_load_cases:
        assert lc in results
        assert results[lc].success


def test_load_case_pattern_map() -> None:
    assert LOAD_CASE_PATTERN_MAP["DL"] == 1
    assert LOAD_CASE_PATTERN_MAP["SDL"] == 2
    assert LOAD_CASE_PATTERN_MAP["LL"] == 3
    assert LOAD_CASE_PATTERN_MAP["Wx+"] == 4
    assert LOAD_CASE_PATTERN_MAP["Wx-"] == 5
    assert LOAD_CASE_PATTERN_MAP["Wy+"] == 6
    assert LOAD_CASE_PATTERN_MAP["Wy-"] == 7
    assert LOAD_CASE_PATTERN_MAP["combined"] == 0


def test_backward_compatibility_single_result(ops_monkeypatch) -> None:
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
    ops_monkeypatch._reaction_data = {}
    ops_monkeypatch.element_forces = {1: [0.0] * 12, 2: [0.0] * 12, 3: [0.0] * 12}
    
    results = analyze_model(model)
    
    assert isinstance(results, dict)
    assert "combined" in results
    result = results["combined"]
    assert isinstance(result, AnalysisResult)
