from __future__ import annotations

import pytest

plotly = pytest.importorskip("plotly")

from plotly.graph_objects import Figure

from src.fem.fem_engine import Element, ElementType, FEMModel, Load, Node, UniformLoad
from src.fem.visualization import VisualizationConfig, create_plan_view


def _build_plan_model() -> FEMModel:
    model = FEMModel()
    # Base nodes
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=2, x=4.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=3, x=0.0, y=4.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=4, x=4.0, y=4.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))

    # Top nodes
    model.add_node(Node(tag=5, x=0.0, y=0.0, z=3.0))
    model.add_node(Node(tag=6, x=4.0, y=0.0, z=3.0))
    model.add_node(Node(tag=7, x=0.0, y=4.0, z=3.0))
    model.add_node(Node(tag=8, x=4.0, y=4.0, z=3.0))

    # Columns
    model.add_element(Element(tag=1, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[1, 5], material_tag=1))
    model.add_element(Element(tag=2, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[2, 6], material_tag=1))
    model.add_element(Element(tag=3, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[3, 7], material_tag=1))
    model.add_element(Element(tag=4, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[4, 8], material_tag=1))

    # Beams at top
    model.add_element(Element(tag=5, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[5, 6], material_tag=1))
    model.add_element(Element(tag=6, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[6, 8], material_tag=1))
    model.add_element(Element(tag=7, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[8, 7], material_tag=1))
    model.add_element(Element(tag=8, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[7, 5], material_tag=1))

    # Loads
    model.add_load(Load(node_tag=6, load_values=[100.0, 0.0, -50.0, 0.0, 0.0, 0.0]))
    model.add_uniform_load(UniformLoad(element_tag=5, load_type="Gravity", magnitude=2.0))

    return model


def test_plan_view_with_utilization_and_labels() -> None:
    model = _build_plan_model()
    utilization = {1: 0.4, 2: 0.5, 3: 0.6, 4: 0.7, 5: 0.9, 6: 0.3, 7: 1.1, 8: 0.2}
    config = VisualizationConfig(show_labels=True, show_loads=True)

    fig = create_plan_view(model, config=config, floor_elevation=3.0, utilization=utilization)

    assert isinstance(fig, Figure)
    trace_names = [trace.name for trace in fig.data]
    # Implementation uses "Primary Beams" for main beams
    assert "Primary Beams" in trace_names or "Beams" in trace_names
    assert "Columns" in trace_names
    assert "Point Loads" in trace_names
    assert "Uniform Loads" in trace_names
    assert "Beam Labels" in trace_names
    assert "Column Labels" in trace_names


def test_plan_view_without_utilization_uses_default_beam_color() -> None:
    model = _build_plan_model()
    config = VisualizationConfig(show_labels=False, show_loads=False)

    fig = create_plan_view(model, config=config, floor_elevation=3.0, utilization=None)

    beam_traces = [trace for trace in fig.data if trace.name in ("Beams", "Primary Beams")]
    assert beam_traces, "Expected at least one beam trace"
    assert beam_traces[0].line.color == "#3B82F6"


def test_plan_view_shows_supports() -> None:
    """Test that plan view shows support nodes at floor level."""
    model = _build_plan_model()
    config = VisualizationConfig(show_supports=True, show_nodes=True)

    fig = create_plan_view(model, config=config, floor_elevation=0.0)

    trace_names = [trace.name for trace in fig.data]
    assert "Supports" in trace_names


def test_plan_view_shows_nodes() -> None:
    """Test that plan view displays node markers."""
    model = _build_plan_model()
    config = VisualizationConfig(show_nodes=True, show_labels=False)

    fig = create_plan_view(model, config=config, floor_elevation=3.0)

    trace_names = [trace.name for trace in fig.data]
    assert "Nodes" in trace_names


def test_plan_view_auto_selects_top_floor() -> None:
    """Test that plan view auto-selects top floor when not specified."""
    model = _build_plan_model()
    config = VisualizationConfig()

    fig = create_plan_view(model, config=config, floor_elevation=None)

    # Title should show floor z=3.0 (top floor)
    assert "3.0" in fig.layout.title.text or "3.00" in fig.layout.title.text


def test_plan_view_coupling_beams() -> None:
    """Test that plan view displays coupling beams with correct style."""
    model = FEMModel()
    # Add nodes
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=3.0))
    model.add_node(Node(tag=2, x=2.0, y=0.0, z=3.0))
    model.add_node(Node(tag=3, x=0.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))

    # Add coupling beam
    model.add_element(Element(tag=1, element_type=ElementType.COUPLING_BEAM,
                              node_tags=[1, 2], material_tag=1))

    config = VisualizationConfig()
    fig = create_plan_view(model, config=config, floor_elevation=3.0)

    trace_names = [trace.name for trace in fig.data]
    assert "Coupling Beams" in trace_names


def test_plan_view_runtime_coupling_metadata_classification() -> None:
    model = FEMModel()
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=3.0))
    model.add_node(Node(tag=2, x=2.0, y=0.0, z=3.0))
    model.add_node(Node(tag=3, x=0.0, y=1.0, z=3.0))
    model.add_node(Node(tag=4, x=2.0, y=1.0, z=3.0))

    model.add_element(
        Element(
            tag=10,
            element_type=ElementType.ELASTIC_BEAM,
            node_tags=[1, 2],
            material_tag=1,
            section_tag=20,
            geometry={"coupling_beam": True, "parent_beam_id": 70000, "sub_element_index": 0},
        )
    )

    model.add_element(
        Element(
            tag=11,
            element_type=ElementType.ELASTIC_BEAM,
            node_tags=[3, 4],
            material_tag=1,
            section_tag=20,
            geometry={"parent_coupling_beam_id": 70001, "sub_element_index": 0},
        )
    )

    fig = create_plan_view(model, config=VisualizationConfig(), floor_elevation=3.0)

    trace_names = [trace.name for trace in fig.data]
    assert "Coupling Beams" in trace_names
    assert "Primary Beams" not in trace_names
    assert "Secondary Beams" not in trace_names


def test_plan_view_no_loads_hides_load_traces() -> None:
    """Test that plan view hides load traces when show_loads is False."""
    model = _build_plan_model()
    config = VisualizationConfig(show_loads=False)

    fig = create_plan_view(model, config=config, floor_elevation=3.0)

    trace_names = [trace.name for trace in fig.data]
    assert "Point Loads" not in trace_names
    assert "Uniform Loads" not in trace_names


def test_plan_view_hides_beams_when_toggle_off() -> None:
    model = _build_plan_model()
    config = VisualizationConfig(show_beams=False)

    fig = create_plan_view(model, config=config, floor_elevation=3.0)

    trace_names = [trace.name for trace in fig.data]
    assert "Primary Beams" not in trace_names
    assert "Secondary Beams" not in trace_names
    assert "Coupling Beams" not in trace_names


def test_plan_view_hides_columns_when_toggle_off() -> None:
    model = _build_plan_model()
    config = VisualizationConfig(show_columns=False)

    fig = create_plan_view(model, config=config, floor_elevation=3.0)

    trace_names = [trace.name for trace in fig.data]
    assert "Columns" not in trace_names


def test_plan_view_shows_reactions_with_reaction_toggle() -> None:
    model = _build_plan_model()
    reactions = {
        1: [1200.0, 0.0, 5000.0, 0.0, 0.0, 0.0],
        2: [800.0, 0.0, 4500.0, 0.0, 0.0, 0.0],
        3: [0.0, 700.0, 4200.0, 0.0, 0.0, 0.0],
        4: [0.0, 600.0, 4100.0, 0.0, 0.0, 0.0],
    }
    config = VisualizationConfig(show_reactions=True, show_supports=False)

    fig = create_plan_view(model, config=config, floor_elevation=3.0, reactions=reactions)

    trace_names = [trace.name for trace in fig.data]
    assert "Reactions" in trace_names


def test_plan_view_layout_properties() -> None:
    """Test that plan view has correct layout properties."""
    model = _build_plan_model()
    config = VisualizationConfig()

    fig = create_plan_view(model, config=config, floor_elevation=3.0)

    assert fig.layout.xaxis.title.text == "X (m)"
    assert fig.layout.yaxis.title.text == "Y (m)"
    assert fig.layout.showlegend is True
    assert fig.layout.plot_bgcolor == "white"


def test_plan_view_hides_omitted_columns_when_toggle_off() -> None:
    model = _build_plan_model()
    model.omitted_columns = [{"x": 1.0, "y": 1.0, "id": "C1"}]
    config = VisualizationConfig(show_ghost_columns=False)

    fig = create_plan_view(model, config=config, floor_elevation=3.0)

    omitted_traces = [trace for trace in fig.data if trace.name == "Omitted Columns"]
    assert not omitted_traces


def test_plan_view_omitted_columns_single_legend_trace() -> None:
    model = _build_plan_model()
    model.omitted_columns = [
        {"x": 1.0, "y": 1.0, "id": "C1"},
        {"x": 3.0, "y": 3.0, "id": "C2"},
    ]
    config = VisualizationConfig(show_ghost_columns=True)

    fig = create_plan_view(model, config=config, floor_elevation=3.0)

    omitted_traces = [trace for trace in fig.data if trace.name == "Omitted Columns"]
    assert len(omitted_traces) == 1


def test_plan_view_empty_floor() -> None:
    """Test plan view with floor that has no elements."""
    model = FEMModel()
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=2, x=4.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))

    config = VisualizationConfig()
    fig = create_plan_view(model, config=config, floor_elevation=0.0)

    # Should still create a figure without errors
    assert isinstance(fig, Figure)
