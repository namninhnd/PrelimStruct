from __future__ import annotations

import pytest

plotly = pytest.importorskip("plotly")

from plotly.graph_objects import Figure

from src.fem.fem_engine import Element, ElementType, FEMModel, Load, Node, UniformLoad
from src.fem.visualization import COLORS, VisualizationConfig, create_plan_view


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

    # Check for beam traces (could be "Beams" or "Primary Beams")
    beam_traces = [trace for trace in fig.data if trace.name in ("Beams", "Primary Beams")]
    assert beam_traces, "Expected at least one beam trace"
    assert beam_traces[0].line.color == COLORS["beam"]


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


def test_plan_view_no_loads_hides_load_traces() -> None:
    """Test that plan view hides load traces when show_loads is False."""
    model = _build_plan_model()
    config = VisualizationConfig(show_loads=False)

    fig = create_plan_view(model, config=config, floor_elevation=3.0)

    trace_names = [trace.name for trace in fig.data]
    assert "Point Loads" not in trace_names
    assert "Uniform Loads" not in trace_names


def test_plan_view_layout_properties() -> None:
    """Test that plan view has correct layout properties."""
    model = _build_plan_model()
    config = VisualizationConfig()

    fig = create_plan_view(model, config=config, floor_elevation=3.0)

    assert fig.layout.xaxis.title.text == "X (m)"
    assert fig.layout.yaxis.title.text == "Y (m)"
    assert fig.layout.showlegend is True
    assert fig.layout.plot_bgcolor == "white"


def test_plan_view_empty_floor() -> None:
    """Test plan view with floor that has no elements."""
    model = FEMModel()
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=2, x=4.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))

    config = VisualizationConfig()
    fig = create_plan_view(model, config=config, floor_elevation=0.0)

    # Should still create a figure without errors
    assert isinstance(fig, Figure)
