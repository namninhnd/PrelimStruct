from __future__ import annotations

import pytest

plotly = pytest.importorskip("plotly")

from plotly.graph_objects import Figure

from src.fem.fem_engine import Element, ElementType, FEMModel, Node
from src.fem.visualization import VisualizationConfig, create_3d_view


def _build_3d_model() -> FEMModel:
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
    return model


def test_3d_view_with_utilization_deflection_reactions() -> None:
    model = _build_3d_model()
    utilization = {1: 0.4, 2: 0.6, 3: 0.9}
    displaced = {3: (0.02, 0.0, -0.01), 4: (0.03, 0.0, -0.02)}
    reactions = {
        1: [1200.0, 0.0, 5000.0, 0.0, 0.0, 0.0],
        2: [800.0, 0.0, 4500.0, 0.0, 0.0, 0.0],
    }
    config = VisualizationConfig(show_supports=True, show_deformed=True, show_reactions=True)

    fig = create_3d_view(
        model,
        config=config,
        utilization=utilization,
        displaced_nodes=displaced,
        reactions=reactions,
    )

    assert isinstance(fig, Figure)
    trace_names = [trace.name for trace in fig.data]
    assert "Columns" in trace_names
    # Check for beams - implementation may use "Beams" or "Primary Beams"
    assert "Beams" in trace_names or "Primary Beams" in trace_names
    assert "Deflected Shape" in trace_names
    assert "Reactions" in trace_names


def test_3d_view_without_utilization() -> None:
    """Test 3D view without utilization coloring."""
    model = _build_3d_model()
    config = VisualizationConfig()

    fig = create_3d_view(model, config=config, utilization=None)

    assert isinstance(fig, Figure)
    trace_names = [trace.name for trace in fig.data]
    assert "Columns" in trace_names
    # Check for beams - implementation may use "Beams" or "Primary Beams"
    assert "Beams" in trace_names or "Primary Beams" in trace_names


def test_3d_view_without_deflection() -> None:
    """Test 3D view without deflected shape overlay."""
    model = _build_3d_model()
    config = VisualizationConfig()

    fig = create_3d_view(model, config=config, displaced_nodes=None)

    trace_names = [trace.name for trace in fig.data]
    assert "Deflected Shape" not in trace_names


def test_3d_view_without_reactions() -> None:
    """Test 3D view without reaction forces."""
    model = _build_3d_model()
    config = VisualizationConfig(show_supports=True)

    fig = create_3d_view(model, config=config, reactions=None)

    trace_names = [trace.name for trace in fig.data]
    assert "Reactions" not in trace_names


def test_3d_view_shows_nodes() -> None:
    """Test that 3D view displays node markers."""
    model = _build_3d_model()
    config = VisualizationConfig(show_nodes=True)

    fig = create_3d_view(model, config=config)

    trace_names = [trace.name for trace in fig.data]
    assert "Nodes" in trace_names


def test_3d_view_shows_supports() -> None:
    """Test that 3D view displays support markers."""
    model = _build_3d_model()
    config = VisualizationConfig(show_supports=True)

    fig = create_3d_view(model, config=config)

    trace_names = [trace.name for trace in fig.data]
    assert "Supports" in trace_names


def test_3d_view_coupling_beams() -> None:
    """Test that 3D view displays coupling beams."""
    model = FEMModel()
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=2, x=2.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=3, x=0.0, y=0.0, z=3.0))
    model.add_node(Node(tag=4, x=2.0, y=0.0, z=3.0))

    # Columns
    model.add_element(Element(tag=1, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[1, 3], material_tag=1))
    model.add_element(Element(tag=2, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[2, 4], material_tag=1))
    # Coupling beam
    model.add_element(Element(tag=3, element_type=ElementType.COUPLING_BEAM,
                              node_tags=[3, 4], material_tag=1))

    config = VisualizationConfig()
    fig = create_3d_view(model, config=config)

    trace_names = [trace.name for trace in fig.data]
    assert "Coupling Beams" in trace_names


def test_3d_view_layout_properties() -> None:
    """Test that 3D view has correct layout properties."""
    model = _build_3d_model()
    config = VisualizationConfig()

    fig = create_3d_view(model, config=config)

    assert fig.layout.title.text == "3D Model View"
    assert fig.layout.showlegend is True
    assert fig.layout.scene.xaxis.title.text == "X (m)"
    assert fig.layout.scene.yaxis.title.text == "Y (m)"
    assert fig.layout.scene.zaxis.title.text == "Z (m)"


def test_3d_view_multi_story() -> None:
    """Test 3D view with multi-story frame."""
    model = FEMModel()
    # 2-story, 2-bay frame
    for i, z in enumerate([0.0, 3.0, 6.0]):
        base_tag = i * 4 + 1
        for j, (x, y) in enumerate([(0, 0), (4, 0), (0, 4), (4, 4)]):
            restraints = [1, 1, 1, 1, 1, 1] if z == 0.0 else [0, 0, 0, 0, 0, 0]
            model.add_node(Node(tag=base_tag + j, x=float(x), y=float(y),
                                z=z, restraints=restraints))

    # Columns (vertical)
    elem_tag = 1
    for col in range(4):
        for story in range(2):
            node_i = story * 4 + col + 1
            node_j = (story + 1) * 4 + col + 1
            model.add_element(Element(tag=elem_tag, element_type=ElementType.ELASTIC_BEAM,
                                      node_tags=[node_i, node_j], material_tag=1))
            elem_tag += 1

    # Beams (horizontal)
    for story in range(1, 3):
        base = story * 4 + 1
        model.add_element(Element(tag=elem_tag, element_type=ElementType.ELASTIC_BEAM,
                                  node_tags=[base, base + 1], material_tag=1))
        elem_tag += 1
        model.add_element(Element(tag=elem_tag, element_type=ElementType.ELASTIC_BEAM,
                                  node_tags=[base + 2, base + 3], material_tag=1))
        elem_tag += 1

    config = VisualizationConfig(show_nodes=True, show_supports=True)
    fig = create_3d_view(model, config=config)

    assert isinstance(fig, Figure)
    trace_names = [trace.name for trace in fig.data]
    assert "Columns" in trace_names
    # Check for beams - implementation may use "Beams" or "Primary Beams"
    assert "Beams" in trace_names or "Primary Beams" in trace_names
    assert "Nodes" in trace_names
    assert "Supports" in trace_names


def test_3d_view_exaggeration_factor() -> None:
    """Test that 3D view respects displacement exaggeration factor."""
    model = _build_3d_model()
    displaced = {3: (0.01, 0.0, -0.005), 4: (0.015, 0.0, -0.01)}
    config = VisualizationConfig(show_deformed=True, exaggeration=50.0)

    fig = create_3d_view(model, config=config, displaced_nodes=displaced)

    trace_names = [trace.name for trace in fig.data]
    assert "Deflected Shape" in trace_names
