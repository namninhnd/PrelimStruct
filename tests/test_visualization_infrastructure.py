from __future__ import annotations

import pytest

from src.fem.fem_engine import Element, ElementType, FEMModel, Load, Node, RigidDiaphragm, UniformLoad
from src.fem.materials import (
    ConcreteGrade,
    create_concrete_material,
    get_elastic_beam_section,
    get_next_material_tag,
    get_next_section_tag,
    get_openseespy_concrete_material,
    reset_material_tags,
)
from src.fem.visualization import (
    VisualizationBackend,
    VisualizationData,
    VisualizationExtractionConfig,
    build_visualization_data_from_fem_model,
    extract_visualization_data_from_opensees,
)


def _add_material_section(model: FEMModel) -> tuple[int, int]:
    reset_material_tags()
    concrete = create_concrete_material(ConcreteGrade.C30)
    mat_tag = get_next_material_tag()
    model.add_material(mat_tag, get_openseespy_concrete_material(concrete, mat_tag))
    section_tag = get_next_section_tag()
    model.add_section(
        section_tag,
        get_elastic_beam_section(concrete, width=300, height=500, section_tag=section_tag),
    )
    return mat_tag, section_tag


def _build_simple_model() -> FEMModel:
    model = FEMModel()
    mat_tag, section_tag = _add_material_section(model)
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=2, x=3.0, y=0.0, z=3.0))
    model.add_element(
        Element(
            tag=1,
            element_type=ElementType.ELASTIC_BEAM,
            node_tags=[1, 2],
            material_tag=mat_tag,
            section_tag=section_tag,
        )
    )
    model.add_load(Load(node_tag=2, load_values=[0, 0, -10.0, 0, 0, 0]))
    model.add_uniform_load(UniformLoad(element_tag=1, load_type="Gravity", magnitude=2.0))
    model.add_rigid_diaphragm(RigidDiaphragm(master_node=1, slave_nodes=[2]))
    return model


def test_build_visualization_data_from_fem_model_copies_counts() -> None:
    model = _build_simple_model()

    data = build_visualization_data_from_fem_model(model)

    assert isinstance(data, VisualizationData)
    assert data.source == "fem_model"
    assert len(data.nodes) == 2
    assert len(data.elements) == 1
    assert len(data.loads) == 1
    assert len(data.uniform_loads) == 1
    assert len(data.diaphragms) == 1

    summary = data.get_summary()
    assert summary["n_nodes"] == 2
    assert summary["n_elements"] == 1
    assert summary["n_loads"] == 1
    assert summary["n_uniform_loads"] == 1
    assert summary["n_fixed_nodes"] == 1


def test_extract_visualization_data_from_opensees_fixed_nodes(ops_monkeypatch) -> None:
    model = _build_simple_model()
    model.build_openseespy_model(ndm=3, ndf=6)

    data = extract_visualization_data_from_opensees(ops_module=ops_monkeypatch)

    assert data.source == "opensees"
    assert len(data.nodes) == 2
    assert data.nodes[1].is_fixed is True
    assert data.nodes[2].is_fixed is False
    assert len(data.elements) == 1
    assert data.elements[1].node_tags == [1, 2]


def test_extract_visualization_data_from_opensees_respects_pinned_override(ops_monkeypatch) -> None:
    model = FEMModel()
    mat_tag, section_tag = _add_material_section(model)
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0))
    model.add_node(Node(tag=2, x=4.0, y=0.0, z=3.0))
    model.add_element(
        Element(
            tag=1,
            element_type=ElementType.ELASTIC_BEAM,
            node_tags=[1, 2],
            material_tag=mat_tag,
            section_tag=section_tag,
        )
    )
    model.build_openseespy_model(ndm=3, ndf=6)

    config = VisualizationExtractionConfig(
        fixed_node_tags=[1],
        pinned_node_tags=[2],
    )
    data = extract_visualization_data_from_opensees(ops_module=ops_monkeypatch, config=config)

    assert data.nodes[1].is_fixed is True
    assert data.nodes[2].is_pinned is True


def test_extract_visualization_data_from_opensees_handles_2d_coords(ops_monkeypatch) -> None:
    model = FEMModel()
    mat_tag, section_tag = _add_material_section(model)
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=2, x=6.0, y=0.0, z=0.0))
    model.add_element(
        Element(
            tag=1,
            element_type=ElementType.ELASTIC_BEAM,
            node_tags=[1, 2],
            material_tag=mat_tag,
            section_tag=section_tag,
        )
    )
    model.build_openseespy_model(ndm=2, ndf=3)

    data = extract_visualization_data_from_opensees(ops_module=ops_monkeypatch)

    assert data.nodes[1].y == pytest.approx(0.0)
    assert data.nodes[1].z == pytest.approx(0.0)
    assert data.nodes[2].x == pytest.approx(6.0)
    assert data.nodes[2].y == pytest.approx(0.0)


def test_extract_visualization_data_falls_back_to_opensees(monkeypatch, ops_monkeypatch) -> None:
    import src.fem.visualization as visualization

    model = _build_simple_model()
    model.build_openseespy_model(ndm=3, ndf=6)

    monkeypatch.setattr(visualization, "OPSVIS_AVAILABLE", False)
    config = VisualizationExtractionConfig(
        backend=VisualizationBackend.OPSVIS,
        allow_fallback=True,
    )

    data = visualization.extract_visualization_data_from_opensees(
        ops_module=ops_monkeypatch,
        config=config,
    )

    assert data.source == "opensees"


# ============================================================================
# Additional tests for visualization infrastructure
# ============================================================================


class TestVisualizationData:
    """Tests for VisualizationData dataclass."""

    def test_visualization_data_empty(self) -> None:
        """Test empty VisualizationData."""
        data = VisualizationData()

        summary = data.get_summary()
        assert summary["n_nodes"] == 0
        assert summary["n_elements"] == 0
        assert summary["n_loads"] == 0
        assert summary["n_uniform_loads"] == 0
        assert summary["n_fixed_nodes"] == 0
        assert summary["is_built"] is True

    def test_visualization_data_source(self) -> None:
        """Test VisualizationData source tracking."""
        data = VisualizationData(source="test_source")
        assert data.source == "test_source"


class TestVisualizationExtractionConfig:
    """Tests for VisualizationExtractionConfig."""

    def test_default_config(self) -> None:
        """Test default extraction config values."""
        config = VisualizationExtractionConfig()

        assert config.backend == VisualizationBackend.AUTO
        assert config.default_element_type == ElementType.ELASTIC_BEAM
        assert config.fixed_node_tags is None
        assert config.pinned_node_tags is None
        assert config.allow_fallback is True

    def test_custom_config(self) -> None:
        """Test custom extraction config values."""
        config = VisualizationExtractionConfig(
            backend=VisualizationBackend.OPENSEES,
            fixed_node_tags=[1, 2, 3],
            pinned_node_tags=[4, 5],
            allow_fallback=False,
        )

        assert config.backend == VisualizationBackend.OPENSEES
        assert config.fixed_node_tags == [1, 2, 3]
        assert config.pinned_node_tags == [4, 5]
        assert config.allow_fallback is False


class TestGetModelStatistics:
    """Tests for get_model_statistics function."""

    def test_model_statistics_basic(self) -> None:
        """Test basic model statistics."""
        from src.fem.visualization import get_model_statistics

        model = _build_simple_model()
        stats = get_model_statistics(model)

        assert stats["n_nodes"] == 2
        assert stats["n_elements"] == 1
        assert stats["n_loads"] == 1
        assert stats["n_uniform_loads"] == 1
        assert stats["n_diaphragms"] == 1
        assert stats["n_floors"] >= 1
        assert "bounding_box" in stats

    def test_model_statistics_bounding_box(self) -> None:
        """Test model statistics bounding box calculation."""
        from src.fem.visualization import get_model_statistics

        model = FEMModel()
        model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0))
        model.add_node(Node(tag=2, x=10.0, y=5.0, z=15.0))
        model.add_element(Element(tag=1, element_type=ElementType.ELASTIC_BEAM,
                                  node_tags=[1, 2], material_tag=1))

        stats = get_model_statistics(model)

        bbox = stats["bounding_box"]
        assert bbox["x_min"] == 0.0
        assert bbox["x_max"] == 10.0
        assert bbox["y_min"] == 0.0
        assert bbox["y_max"] == 5.0
        assert bbox["z_min"] == 0.0
        assert bbox["z_max"] == 15.0

    def test_model_statistics_element_classification(self) -> None:
        """Test model statistics element classification."""
        from src.fem.visualization import get_model_statistics

        model = FEMModel()
        model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
        model.add_node(Node(tag=2, x=0.0, y=0.0, z=3.0))
        model.add_node(Node(tag=3, x=4.0, y=0.0, z=3.0))

        # Column (vertical)
        model.add_element(Element(tag=1, element_type=ElementType.ELASTIC_BEAM,
                                  node_tags=[1, 2], material_tag=1))
        # Beam (horizontal)
        model.add_element(Element(tag=2, element_type=ElementType.ELASTIC_BEAM,
                                  node_tags=[2, 3], material_tag=1))
        # Coupling beam
        model.add_element(Element(tag=3, element_type=ElementType.COUPLING_BEAM,
                                  node_tags=[2, 3], material_tag=1))

        stats = get_model_statistics(model)

        assert stats["n_columns"] >= 1
        assert stats["n_beams"] >= 1
        assert stats["n_coupling_beams"] >= 1


class TestVisualizationConfig:
    """Tests for VisualizationConfig dataclass."""

    def test_default_visualization_config(self) -> None:
        """Test default visualization config values."""
        from src.fem.visualization import VisualizationConfig

        config = VisualizationConfig()

        assert config.show_nodes is True
        assert config.show_elements is True
        assert config.show_supports is True
        assert config.show_loads is True
        assert config.show_labels is False
        assert config.node_size == 8
        assert config.element_width == 3
        assert config.support_size == 15
        assert config.load_scale == 1.0
        assert config.colorscale == "RdYlGn_r"
        assert config.floor_level is None
        assert config.exaggeration == 10.0

    def test_custom_visualization_config(self) -> None:
        """Test custom visualization config values."""
        from src.fem.visualization import VisualizationConfig

        config = VisualizationConfig(
            show_nodes=False,
            show_labels=True,
            node_size=12,
            colorscale="Viridis",
            floor_level=6.0,
            exaggeration=50.0,
        )

        assert config.show_nodes is False
        assert config.show_labels is True
        assert config.node_size == 12
        assert config.colorscale == "Viridis"
        assert config.floor_level == 6.0
        assert config.exaggeration == 50.0
