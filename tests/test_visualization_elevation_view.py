from __future__ import annotations

import pytest

plotly = pytest.importorskip("plotly")

from plotly.graph_objects import Figure

from src.fem.fem_engine import Element, ElementType, FEMModel, Node
from src.fem.visualization import VisualizationConfig, create_elevation_view


def _build_elevation_model() -> FEMModel:
    model = FEMModel()
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=2, x=4.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=3, x=0.0, y=0.0, z=3.0))
    model.add_node(Node(tag=4, x=4.0, y=0.0, z=3.0))

    model.add_element(Element(tag=1, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[1, 3], material_tag=1))
    model.add_element(Element(tag=2, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[2, 4], material_tag=1))
    model.add_element(Element(tag=3, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[3, 4], material_tag=1))

    model.add_node(Node(tag=10, x=1.0, y=0.0, z=0.0))
    model.add_node(Node(tag=11, x=1.0, y=0.0, z=3.0))
    model.add_node(Node(tag=12, x=1.4, y=0.0, z=3.0))
    model.add_node(Node(tag=13, x=1.4, y=0.0, z=0.0))
    model.add_element(
        Element(
            tag=20,
            element_type=ElementType.SHELL_MITC4,
            node_tags=[10, 11, 12, 13],
            material_tag=1,
            section_tag=4,
        )
    )
    return model


def test_elevation_view_with_deflection_and_reactions() -> None:
    model = _build_elevation_model()
    utilization = {1: 0.4, 2: 0.6, 3: 0.9}
    displaced = {3: (0.02, 0.0, -0.01), 4: (0.03, 0.0, -0.02)}
    reactions = {
        1: [1200.0, 0.0, 5000.0, 0.0, 0.0, 0.0],
        2: [800.0, 0.0, 4500.0, 0.0, 0.0, 0.0],
    }
    config = VisualizationConfig(show_supports=True, show_deformed=True, show_reactions=True)

    fig = create_elevation_view(
        model,
        config=config,
        view_direction="X",
        utilization=utilization,
        displaced_nodes=displaced,
        reactions=reactions,
    )

    assert isinstance(fig, Figure)
    trace_names = [trace.name for trace in fig.data]
    assert "Columns" in trace_names
    assert "Beams" in trace_names
    assert "Deflected Shape" in trace_names
    assert "Reactions" in trace_names
    assert "Floor Utilization" in trace_names
    assert fig.layout.annotations


def test_elevation_view_y_direction() -> None:
    """Test elevation view along Y direction (YZ view)."""
    model = _build_elevation_model()
    config = VisualizationConfig()

    fig = create_elevation_view(model, config=config, view_direction="Y")

    assert isinstance(fig, Figure)
    assert "Y Direction" in fig.layout.title.text
    assert fig.layout.xaxis.title.text == "Y (m)"
    assert fig.layout.yaxis.title.text == "Z (m)"


def test_elevation_view_without_utilization() -> None:
    """Test elevation view without utilization coloring."""
    model = _build_elevation_model()
    config = VisualizationConfig()

    fig = create_elevation_view(model, config=config, view_direction="X", utilization=None)

    assert isinstance(fig, Figure)
    trace_names = [trace.name for trace in fig.data]
    assert "Columns" in trace_names
    # Without utilization, should use default colors
    col_traces = [t for t in fig.data if t.name == "Columns"]
    assert len(col_traces) > 0


def test_elevation_view_without_deflection() -> None:
    """Test elevation view without deflected shape overlay."""
    model = _build_elevation_model()
    config = VisualizationConfig()

    fig = create_elevation_view(
        model, config=config, view_direction="X",
        displaced_nodes=None
    )

    trace_names = [trace.name for trace in fig.data]
    assert "Deflected Shape" not in trace_names


def test_elevation_view_without_reactions() -> None:
    """Test elevation view without reaction force arrows."""
    model = _build_elevation_model()
    config = VisualizationConfig(show_supports=True)

    fig = create_elevation_view(
        model, config=config, view_direction="X",
        reactions=None
    )

    trace_names = [trace.name for trace in fig.data]
    assert "Reactions" not in trace_names


def test_elevation_view_shows_supports() -> None:
    """Test that elevation view displays support markers."""
    model = _build_elevation_model()
    config = VisualizationConfig(show_supports=True)

    fig = create_elevation_view(model, config=config, view_direction="X")

    trace_names = [trace.name for trace in fig.data]
    assert "Supports" in trace_names


def test_elevation_view_multi_story() -> None:
    """Test elevation view with multi-story structure."""
    model = FEMModel()
    # 3-story structure
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=2, x=0.0, y=0.0, z=3.0))
    model.add_node(Node(tag=3, x=0.0, y=0.0, z=6.0))
    model.add_node(Node(tag=4, x=0.0, y=0.0, z=9.0))

    model.add_element(Element(tag=1, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[1, 2], material_tag=1))
    model.add_element(Element(tag=2, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[2, 3], material_tag=1))
    model.add_element(Element(tag=3, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[3, 4], material_tag=1))

    config = VisualizationConfig()
    fig = create_elevation_view(model, config=config, view_direction="X")

    assert isinstance(fig, Figure)
    # Should show all floor levels
    assert len([t for t in fig.data if t.name == "Columns"]) > 0


def test_elevation_view_layout_properties() -> None:
    """Test that elevation view has correct layout properties."""
    model = _build_elevation_model()
    config = VisualizationConfig()

    fig = create_elevation_view(model, config=config, view_direction="X")

    assert "Elevation View" in fig.layout.title.text
    assert fig.layout.showlegend is True
    assert fig.layout.plot_bgcolor == "white"


def test_elevation_view_coupling_beams() -> None:
    """Test that elevation view displays coupling beams."""
    model = FEMModel()
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=2, x=2.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=3, x=0.0, y=0.0, z=3.0))
    model.add_node(Node(tag=4, x=2.0, y=0.0, z=3.0))

    # Column
    model.add_element(Element(tag=1, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[1, 3], material_tag=1))
    model.add_element(Element(tag=2, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[2, 4], material_tag=1))
    # Coupling beam
    model.add_element(Element(tag=3, element_type=ElementType.COUPLING_BEAM,
                              node_tags=[3, 4], material_tag=1))

    config = VisualizationConfig()
    fig = create_elevation_view(model, config=config, view_direction="X")

    trace_names = [trace.name for trace in fig.data]
    assert "Coupling Beams" in trace_names


def test_elevation_view_shows_core_walls_for_standard_and_custom_gridlines() -> None:
    model = _build_elevation_model()
    config = VisualizationConfig(show_walls=True)

    fig_standard = create_elevation_view(model, config=config, view_direction="X", gridline_coord=0.0)
    fig_custom = create_elevation_view(model, config=config, view_direction="X", gridline_coord=0.2)

    standard_names = [trace.name for trace in fig_standard.data]
    custom_names = [trace.name for trace in fig_custom.data]

    assert "Core Walls" in standard_names
    assert "Core Walls" in custom_names


def test_elevation_view_hides_core_walls_when_toggle_off() -> None:
    model = _build_elevation_model()
    config = VisualizationConfig(show_walls=False)

    fig = create_elevation_view(model, config=config, view_direction="X", gridline_coord=0.0)

    trace_names = [trace.name for trace in fig.data]
    assert "Core Walls" not in trace_names
