import pytest

from src.fem.fem_engine import (
    Element,
    ElementType,
    FEMModel,
    Load,
    Node,
    RigidDiaphragm,
    UniformLoad,
)
from src.fem.materials import (
    ConcreteGrade,
    create_concrete_material,
    get_elastic_beam_section,
    get_next_material_tag,
    get_next_section_tag,
    get_openseespy_concrete_material,
    reset_material_tags,
)


def test_node_restraints_validation() -> None:
    with pytest.raises(ValueError):
        Node(tag=1, x=0, y=0, z=0, restraints=[1, 1])  # wrong length
    with pytest.raises(ValueError):
        Node(tag=1, x=0, y=0, z=0, restraints=[2, 0, 0, 0, 0, 0])  # invalid flag


def test_element_requires_existing_nodes() -> None:
    model = FEMModel()
    model.add_node(Node(tag=1, x=0, y=0, z=0))
    with pytest.raises(ValueError):
        model.add_element(
            Element(
                tag=1,
                element_type=ElementType.ELASTIC_BEAM,
                node_tags=[1, 2],
                material_tag=1,
                section_tag=1,
            )
        )


def test_validate_model_reports_missing_items() -> None:
    model = FEMModel()
    is_valid, errors = model.validate_model()
    assert not is_valid
    assert any("no nodes" in err.lower() for err in errors)

    # Add free nodes and an element referencing a missing section
    model.add_node(Node(tag=1, x=0, y=0, z=0))
    model.add_node(Node(tag=2, x=0, y=0, z=3))
    model.add_element(
        Element(
            tag=1,
            element_type=ElementType.ELASTIC_BEAM,
            node_tags=[1, 2],
            material_tag=1,
            section_tag=1,
        )
    )
    is_valid, errors = model.validate_model()
    assert not is_valid
    assert any("unstable" in err.lower() for err in errors)
    assert any("non-existent section 1" in err for err in errors)


def test_build_openseespy_model_with_loads(ops_monkeypatch) -> None:
    reset_material_tags()
    model = FEMModel()
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=2, x=0.0, y=0.0, z=3.0, restraints=[0, 0, 0, 0, 0, 0]))

    concrete = create_concrete_material(ConcreteGrade.C40)
    mat_tag = get_next_material_tag()
    model.add_material(mat_tag, get_openseespy_concrete_material(concrete, mat_tag))

    section_tag = get_next_section_tag()
    section = get_elastic_beam_section(concrete, width=300, height=500,
                                       section_tag=section_tag)
    model.add_section(section_tag, section)

    model.add_element(
        Element(
            tag=1,
            element_type=ElementType.ELASTIC_BEAM,
            node_tags=[1, 2],
            material_tag=mat_tag,
            section_tag=section_tag,
        )
    )
    model.add_load(
        Load(node_tag=2, load_values=[0, 0, -1000, 0, 0, 0], load_pattern=1)
    )
    model.add_uniform_load(
        UniformLoad(element_tag=1, load_type="Gravity", magnitude=5.0, load_pattern=1)
    )

    model.build_openseespy_model(ndm=3, ndf=6)

    assert ops_monkeypatch.nodes[1] == (0.0, 0.0, 0.0)
    assert ops_monkeypatch.fixes[1] == (1, 1, 1, 1, 1, 1)
    assert ops_monkeypatch.materials[mat_tag][0] == "Concrete01"
    assert ops_monkeypatch.sections[section_tag][0] == "Elastic"

    elem_type, elem_args = ops_monkeypatch.elements[1]
    assert elem_type == "elasticBeamColumn"
    assert elem_args[0:2] == (1, 2)  # connectivity
    assert elem_args[-1] == 1  # geom transformation tag

    assert ops_monkeypatch.time_series == [("Linear", 1)]
    assert ("Plain", 1, 1) in ops_monkeypatch.patterns
    assert ops_monkeypatch.loads == [(2, (0, 0, -1000, 0, 0, 0))]
    assert ops_monkeypatch.uniform_loads[-1] == ("-ele", 1, "-type", "beamUniform", -5.0, 0.0)


def test_uniform_load_mapping_ndm2(ops_monkeypatch) -> None:
    reset_material_tags()
    model = FEMModel()
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=2, x=4.0, y=0.0, z=0.0, restraints=[0, 0, 0, 0, 0, 0]))

    concrete = create_concrete_material(ConcreteGrade.C30)
    mat_tag = get_next_material_tag()
    model.add_material(mat_tag, get_openseespy_concrete_material(concrete, mat_tag))
    section_tag = get_next_section_tag()
    model.add_section(
        section_tag,
        get_elastic_beam_section(concrete, width=250, height=500, section_tag=section_tag),
    )
    model.add_element(
        Element(
            tag=1,
            element_type=ElementType.ELASTIC_BEAM,
            node_tags=[1, 2],
            material_tag=mat_tag,
            section_tag=section_tag,
        )
    )
    model.add_uniform_load(
        UniformLoad(element_tag=1, load_type="Gravity", magnitude=8.0, load_pattern=2)
    )

    model.build_openseespy_model(ndm=2, ndf=3)

    # Expect gravity applied in local y for 2D
    assert ops_monkeypatch.uniform_loads[-1] == ("-ele", 1, "-type", "beamUniform", -8.0)


def test_invalid_uniform_load_type_raises(ops_monkeypatch) -> None:
    reset_material_tags()
    model = FEMModel()
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=2, x=3.0, y=0.0, z=0.0, restraints=[0, 0, 0, 0, 0, 0]))

    concrete = create_concrete_material(ConcreteGrade.C25)
    mat_tag = get_next_material_tag()
    model.add_material(mat_tag, get_openseespy_concrete_material(concrete, mat_tag))
    section_tag = get_next_section_tag()
    model.add_section(
        section_tag,
        get_elastic_beam_section(concrete, width=200, height=450, section_tag=section_tag),
    )
    model.add_element(
        Element(
            tag=1,
            element_type=ElementType.ELASTIC_BEAM,
            node_tags=[1, 2],
            material_tag=mat_tag,
            section_tag=section_tag,
        )
    )
    model.add_uniform_load(
        UniformLoad(element_tag=1, load_type="InvalidType", magnitude=5.0, load_pattern=1)
    )

    with pytest.raises(ValueError):
        model.build_openseespy_model(ndm=3, ndf=6)


def test_rigid_diaphragm_constraints_applied(ops_monkeypatch) -> None:
    reset_material_tags()
    model = FEMModel()
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=3.0))
    model.add_node(Node(tag=2, x=4.0, y=0.0, z=3.0))
    model.add_node(Node(tag=3, x=8.0, y=0.0, z=3.0))
    model.add_node(Node(tag=10, x=0.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))

    concrete = create_concrete_material(ConcreteGrade.C30)
    mat_tag = get_next_material_tag()
    model.add_material(mat_tag, get_openseespy_concrete_material(concrete, mat_tag))
    section_tag = get_next_section_tag()
    model.add_section(
        section_tag,
        get_elastic_beam_section(concrete, width=300, height=500, section_tag=section_tag),
    )
    model.add_element(
        Element(
            tag=1,
            element_type=ElementType.ELASTIC_BEAM,
            node_tags=[1, 2],
            material_tag=mat_tag,
            section_tag=section_tag,
        )
    )
    model.add_element(
        Element(
            tag=2,
            element_type=ElementType.ELASTIC_BEAM,
            node_tags=[2, 3],
            material_tag=mat_tag,
            section_tag=section_tag,
        )
    )

    model.add_rigid_diaphragm(RigidDiaphragm(master_node=1, slave_nodes=[2, 3]))
    model.build_openseespy_model(ndm=3, ndf=6)

    assert ops_monkeypatch.rigid_diaphragms[-1] == (3, 1, 2, 3)


def test_rigid_diaphragm_requires_3d(ops_monkeypatch) -> None:
    reset_material_tags()
    model = FEMModel()
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0))
    model.add_node(Node(tag=2, x=4.0, y=0.0, z=0.0))

    concrete = create_concrete_material(ConcreteGrade.C25)
    mat_tag = get_next_material_tag()
    model.add_material(mat_tag, get_openseespy_concrete_material(concrete, mat_tag))
    section_tag = get_next_section_tag()
    model.add_section(
        section_tag,
        get_elastic_beam_section(concrete, width=250, height=400, section_tag=section_tag),
    )
    model.add_element(
        Element(
            tag=1,
            element_type=ElementType.ELASTIC_BEAM,
            node_tags=[1, 2],
            material_tag=mat_tag,
            section_tag=section_tag,
        )
    )
    model.add_rigid_diaphragm(RigidDiaphragm(master_node=1, slave_nodes=[2]))

    with pytest.raises(ValueError):
        model.build_openseespy_model(ndm=2, ndf=3)


# ============================================================================
# Additional comprehensive tests for fem_engine.py
# ============================================================================


class TestNodeProperties:
    """Tests for Node dataclass properties and edge cases."""

    def test_node_is_fixed_property(self) -> None:
        """Test is_fixed property for fully fixed node."""
        fixed_node = Node(tag=1, x=0, y=0, z=0, restraints=[1, 1, 1, 1, 1, 1])
        assert fixed_node.is_fixed is True

        partially_fixed = Node(tag=2, x=0, y=0, z=0, restraints=[1, 1, 1, 0, 0, 0])
        assert partially_fixed.is_fixed is False

        free_node = Node(tag=3, x=0, y=0, z=0, restraints=[0, 0, 0, 0, 0, 0])
        assert free_node.is_fixed is False

    def test_node_is_pinned_property(self) -> None:
        """Test is_pinned property for pinned node."""
        pinned_node = Node(tag=1, x=0, y=0, z=0, restraints=[1, 1, 1, 0, 0, 0])
        assert pinned_node.is_pinned is True

        fixed_node = Node(tag=2, x=0, y=0, z=0, restraints=[1, 1, 1, 1, 1, 1])
        assert fixed_node.is_pinned is False

        free_node = Node(tag=3, x=0, y=0, z=0, restraints=[0, 0, 0, 0, 0, 0])
        assert free_node.is_pinned is False

    def test_node_default_restraints(self) -> None:
        """Test node with default restraints (free)."""
        node = Node(tag=1, x=1.0, y=2.0, z=3.0)
        assert node.restraints == [0, 0, 0, 0, 0, 0]
        assert node.is_fixed is False
        assert node.is_pinned is False

    def test_node_coordinates(self) -> None:
        """Test node coordinate storage."""
        node = Node(tag=100, x=10.5, y=-5.2, z=25.0)
        assert node.x == pytest.approx(10.5)
        assert node.y == pytest.approx(-5.2)
        assert node.z == pytest.approx(25.0)


class TestElementValidation:
    """Tests for Element dataclass validation."""

    def test_element_minimum_two_nodes(self) -> None:
        """Test that element requires at least 2 nodes."""
        with pytest.raises(ValueError, match="at least 2 nodes"):
            Element(
                tag=1,
                element_type=ElementType.ELASTIC_BEAM,
                node_tags=[1],  # Only one node
                material_tag=1,
            )

    def test_element_with_three_nodes(self) -> None:
        """Test element with 3 nodes (valid for shell elements)."""
        elem = Element(
            tag=1,
            element_type=ElementType.SHELL,
            node_tags=[1, 2, 3],
            material_tag=1,
        )
        assert len(elem.node_tags) == 3

    def test_element_geometry_defaults(self) -> None:
        """Test element geometry defaults to empty dict."""
        elem = Element(
            tag=1,
            element_type=ElementType.ELASTIC_BEAM,
            node_tags=[1, 2],
            material_tag=1,
        )
        assert elem.geometry == {}
        assert elem.section_tag is None


class TestLoadValidation:
    """Tests for Load dataclass validation."""

    def test_load_requires_six_components(self) -> None:
        """Test that load requires exactly 6 components."""
        with pytest.raises(ValueError, match="6 components"):
            Load(node_tag=1, load_values=[1000, 0, 0])  # Only 3 components

    def test_load_valid_six_components(self) -> None:
        """Test valid load with 6 components."""
        load = Load(
            node_tag=1,
            load_values=[1000, 2000, -5000, 100, 200, 50],
            load_pattern=2,
        )
        assert load.load_values == [1000, 2000, -5000, 100, 200, 50]
        assert load.load_pattern == 2


class TestRigidDiaphragmValidation:
    """Tests for RigidDiaphragm dataclass validation."""

    def test_diaphragm_requires_slave_nodes(self) -> None:
        """Test that diaphragm requires at least one slave node."""
        with pytest.raises(ValueError, match="at least one slave node"):
            RigidDiaphragm(master_node=1, slave_nodes=[])

    def test_diaphragm_master_not_slave(self) -> None:
        """Test that master node cannot be a slave node."""
        with pytest.raises(ValueError, match="Master node cannot also be a slave"):
            RigidDiaphragm(master_node=1, slave_nodes=[1, 2, 3])

    def test_diaphragm_valid(self) -> None:
        """Test valid diaphragm creation."""
        diaphragm = RigidDiaphragm(master_node=1, slave_nodes=[2, 3, 4], perp_dirn=3)
        assert diaphragm.master_node == 1
        assert diaphragm.slave_nodes == [2, 3, 4]
        assert diaphragm.perp_dirn == 3


class TestFEMModelOperations:
    """Tests for FEMModel class operations."""

    def test_add_duplicate_node_raises(self) -> None:
        """Test that adding duplicate node tag raises error."""
        model = FEMModel()
        model.add_node(Node(tag=1, x=0, y=0, z=0))
        with pytest.raises(ValueError, match="Node tag 1 already exists"):
            model.add_node(Node(tag=1, x=1, y=0, z=0))

    def test_add_duplicate_element_raises(self) -> None:
        """Test that adding duplicate element tag raises error."""
        model = FEMModel()
        model.add_node(Node(tag=1, x=0, y=0, z=0))
        model.add_node(Node(tag=2, x=5, y=0, z=0))
        model.add_element(
            Element(
                tag=1,
                element_type=ElementType.ELASTIC_BEAM,
                node_tags=[1, 2],
                material_tag=1,
            )
        )
        with pytest.raises(ValueError, match="Element tag 1 already exists"):
            model.add_element(
                Element(
                    tag=1,
                    element_type=ElementType.ELASTIC_BEAM,
                    node_tags=[1, 2],
                    material_tag=1,
                )
            )

    def test_add_duplicate_material_raises(self) -> None:
        """Test that adding duplicate material tag raises error."""
        model = FEMModel()
        model.add_material(1, {"material_type": "Concrete01"})
        with pytest.raises(ValueError, match="Material tag 1 already exists"):
            model.add_material(1, {"material_type": "Steel01"})

    def test_add_duplicate_section_raises(self) -> None:
        """Test that adding duplicate section tag raises error."""
        model = FEMModel()
        model.add_section(1, {"section_type": "ElasticBeamSection"})
        with pytest.raises(ValueError, match="Section tag 1 already exists"):
            model.add_section(1, {"section_type": "FiberSection"})

    def test_add_load_to_nonexistent_node_raises(self) -> None:
        """Test that adding load to nonexistent node raises error."""
        model = FEMModel()
        model.add_node(Node(tag=1, x=0, y=0, z=0))
        with pytest.raises(ValueError, match="Node 99 does not exist"):
            model.add_load(Load(node_tag=99, load_values=[0, 0, -1000, 0, 0, 0]))

    def test_add_uniform_load_to_nonexistent_element_raises(self) -> None:
        """Test that adding uniform load to nonexistent element raises error."""
        model = FEMModel()
        with pytest.raises(ValueError, match="Element 99 does not exist"):
            model.add_uniform_load(
                UniformLoad(element_tag=99, load_type="Gravity", magnitude=10.0)
            )

    def test_add_diaphragm_to_nonexistent_master_raises(self) -> None:
        """Test that adding diaphragm with nonexistent master raises error."""
        model = FEMModel()
        model.add_node(Node(tag=1, x=0, y=0, z=0))
        model.add_node(Node(tag=2, x=5, y=0, z=0))
        with pytest.raises(ValueError, match="Master node 99 does not exist"):
            model.add_rigid_diaphragm(RigidDiaphragm(master_node=99, slave_nodes=[1, 2]))

    def test_add_diaphragm_to_nonexistent_slave_raises(self) -> None:
        """Test that adding diaphragm with nonexistent slave raises error."""
        model = FEMModel()
        model.add_node(Node(tag=1, x=0, y=0, z=0))
        model.add_node(Node(tag=2, x=5, y=0, z=0))
        with pytest.raises(ValueError, match="Slave node 99 does not exist"):
            model.add_rigid_diaphragm(RigidDiaphragm(master_node=1, slave_nodes=[2, 99]))

    def test_get_node_coordinates(self) -> None:
        """Test get_node_coordinates returns correct numpy array."""
        model = FEMModel()
        model.add_node(Node(tag=1, x=0, y=0, z=0))
        model.add_node(Node(tag=2, x=5, y=0, z=3))
        model.add_node(Node(tag=3, x=10, y=0, z=6))

        coords = model.get_node_coordinates()
        assert coords.shape == (3, 3)
        assert coords[0].tolist() == pytest.approx([0, 0, 0])
        assert coords[1].tolist() == pytest.approx([5, 0, 3])
        assert coords[2].tolist() == pytest.approx([10, 0, 6])

    def test_get_element_connectivity(self) -> None:
        """Test get_element_connectivity returns correct list."""
        model = FEMModel()
        model.add_node(Node(tag=1, x=0, y=0, z=0))
        model.add_node(Node(tag=2, x=5, y=0, z=0))
        model.add_node(Node(tag=3, x=10, y=0, z=0))

        model.add_element(
            Element(tag=1, element_type=ElementType.ELASTIC_BEAM,
                    node_tags=[1, 2], material_tag=1)
        )
        model.add_element(
            Element(tag=2, element_type=ElementType.ELASTIC_BEAM,
                    node_tags=[2, 3], material_tag=1)
        )

        connectivity = model.get_element_connectivity()
        assert len(connectivity) == 2
        assert connectivity[0] == (1, 2)
        assert connectivity[1] == (2, 3)

    def test_get_fixed_nodes(self) -> None:
        """Test get_fixed_nodes returns correct list."""
        model = FEMModel()
        model.add_node(Node(tag=1, x=0, y=0, z=0, restraints=[1, 1, 1, 1, 1, 1]))
        model.add_node(Node(tag=2, x=5, y=0, z=0, restraints=[0, 0, 0, 0, 0, 0]))
        model.add_node(Node(tag=3, x=10, y=0, z=0, restraints=[1, 1, 1, 1, 1, 1]))

        fixed_nodes = model.get_fixed_nodes()
        assert sorted(fixed_nodes) == [1, 3]

    def test_get_summary(self) -> None:
        """Test get_summary returns correct statistics."""
        model = FEMModel()
        model.add_node(Node(tag=1, x=0, y=0, z=0, restraints=[1, 1, 1, 1, 1, 1]))
        model.add_node(Node(tag=2, x=5, y=0, z=0))

        model.add_material(1, {"material_type": "Concrete01"})
        model.add_section(1, {"section_type": "ElasticBeamSection"})

        model.add_element(
            Element(tag=1, element_type=ElementType.ELASTIC_BEAM,
                    node_tags=[1, 2], material_tag=1, section_tag=1)
        )
        model.add_load(Load(node_tag=2, load_values=[0, 0, -1000, 0, 0, 0]))
        model.add_uniform_load(
            UniformLoad(element_tag=1, load_type="Gravity", magnitude=5.0)
        )

        summary = model.get_summary()
        assert summary["n_nodes"] == 2
        assert summary["n_elements"] == 1
        assert summary["n_materials"] == 1
        assert summary["n_sections"] == 1
        assert summary["n_loads"] == 1
        assert summary["n_uniform_loads"] == 1
        assert summary["n_fixed_nodes"] == 1
        assert summary["is_built"] is False


class TestModelValidation:
    """Tests for FEMModel.validate_model method."""

    def test_validate_empty_model(self) -> None:
        """Test validation of empty model."""
        model = FEMModel()
        is_valid, errors = model.validate_model()
        assert is_valid is False
        assert any("no nodes" in err.lower() for err in errors)
        assert any("no elements" in err.lower() for err in errors)

    def test_validate_model_without_supports(self) -> None:
        """Test validation detects missing supports."""
        model = FEMModel()
        model.add_node(Node(tag=1, x=0, y=0, z=0))  # Free node
        model.add_node(Node(tag=2, x=5, y=0, z=0))  # Free node
        model.add_material(1, {"material_type": "Concrete01"})
        model.add_section(1, {"section_type": "ElasticBeamSection"})
        model.add_element(
            Element(tag=1, element_type=ElementType.ELASTIC_BEAM,
                    node_tags=[1, 2], material_tag=1, section_tag=1)
        )

        is_valid, errors = model.validate_model()
        assert is_valid is False
        assert any("unstable" in err.lower() for err in errors)

    def test_validate_model_missing_material(self) -> None:
        """Test validation detects missing material reference."""
        model = FEMModel()
        model.add_node(Node(tag=1, x=0, y=0, z=0, restraints=[1, 1, 1, 1, 1, 1]))
        model.add_node(Node(tag=2, x=5, y=0, z=0))
        model.add_section(1, {"section_type": "ElasticBeamSection"})
        model.add_element(
            Element(tag=1, element_type=ElementType.ELASTIC_BEAM,
                    node_tags=[1, 2], material_tag=99, section_tag=1)  # material_tag=99 doesn't exist
        )

        is_valid, errors = model.validate_model()
        assert is_valid is False
        assert any("non-existent material 99" in err for err in errors)

    def test_validate_model_missing_section_for_beam(self) -> None:
        """Test validation detects missing section for beam element."""
        model = FEMModel()
        model.add_node(Node(tag=1, x=0, y=0, z=0, restraints=[1, 1, 1, 1, 1, 1]))
        model.add_node(Node(tag=2, x=5, y=0, z=0))
        model.add_material(1, {"material_type": "Concrete01"})
        model.add_element(
            Element(tag=1, element_type=ElementType.ELASTIC_BEAM,
                    node_tags=[1, 2], material_tag=1, section_tag=None)  # No section
        )

        is_valid, errors = model.validate_model()
        assert is_valid is False
        assert any("missing section_tag" in err for err in errors)

    def test_validate_valid_model(self) -> None:
        """Test validation passes for valid model."""
        model = FEMModel()
        model.add_node(Node(tag=1, x=0, y=0, z=0, restraints=[1, 1, 1, 1, 1, 1]))
        model.add_node(Node(tag=2, x=5, y=0, z=0))
        model.add_material(1, {"material_type": "Concrete01"})
        model.add_section(1, {"section_type": "ElasticBeamSection"})
        model.add_element(
            Element(tag=1, element_type=ElementType.ELASTIC_BEAM,
                    node_tags=[1, 2], material_tag=1, section_tag=1)
        )

        is_valid, errors = model.validate_model()
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_diaphragm_missing_nodes(self) -> None:
        """Test validation detects diaphragm with missing nodes."""
        model = FEMModel()
        model.add_node(Node(tag=1, x=0, y=0, z=0, restraints=[1, 1, 1, 1, 1, 1]))
        model.add_node(Node(tag=2, x=5, y=0, z=0))
        model.add_material(1, {"material_type": "Concrete01"})
        model.add_section(1, {"section_type": "ElasticBeamSection"})
        model.add_element(
            Element(tag=1, element_type=ElementType.ELASTIC_BEAM,
                    node_tags=[1, 2], material_tag=1, section_tag=1)
        )

        # Force-add a diaphragm referencing nonexistent nodes
        model.diaphragms.append(RigidDiaphragm(master_node=99, slave_nodes=[2]))

        is_valid, errors = model.validate_model()
        assert is_valid is False
        assert any("master node 99 missing" in err.lower() for err in errors)


class TestUniformLoadComponents:
    """Tests for uniform load component mapping."""

    def test_uniform_load_y_direction(self) -> None:
        """Test uniform load in Y direction mapping."""
        load = UniformLoad(element_tag=1, load_type="Y", magnitude=10.0)
        wy, wz = FEMModel._get_uniform_load_components(load, ndm=3)
        assert wy == pytest.approx(10.0)
        assert wz == pytest.approx(0.0)

    def test_uniform_load_z_direction(self) -> None:
        """Test uniform load in Z direction mapping."""
        load = UniformLoad(element_tag=1, load_type="Z", magnitude=15.0)
        wy, wz = FEMModel._get_uniform_load_components(load, ndm=3)
        assert wy == pytest.approx(0.0)
        assert wz == pytest.approx(15.0)

    def test_uniform_load_gravity_3d(self) -> None:
        """Test gravity load mapping in 3D.

        With ETABS vecxz convention, local_y is vertical for horizontal beams.
        Gravity = load in -local_y direction = wy = -magnitude.
        """
        load = UniformLoad(element_tag=1, load_type="Gravity", magnitude=8.0)
        wy, wz = FEMModel._get_uniform_load_components(load, ndm=3)
        assert wy == pytest.approx(-8.0)
        assert wz == pytest.approx(0.0)

    def test_uniform_load_gravity_2d(self) -> None:
        """Test gravity load mapping in 2D."""
        load = UniformLoad(element_tag=1, load_type="Gravity", magnitude=8.0)
        wy, wz = FEMModel._get_uniform_load_components(load, ndm=2)
        assert wy == pytest.approx(-8.0)
        assert wz == pytest.approx(0.0)

    def test_uniform_load_case_insensitive(self) -> None:
        """Test uniform load type is case insensitive."""
        load1 = UniformLoad(element_tag=1, load_type="gravity", magnitude=5.0)
        load2 = UniformLoad(element_tag=1, load_type="GRAVITY", magnitude=5.0)
        load3 = UniformLoad(element_tag=1, load_type="Gravity", magnitude=5.0)

        wy1, wz1 = FEMModel._get_uniform_load_components(load1, ndm=3)
        wy2, wz2 = FEMModel._get_uniform_load_components(load2, ndm=3)
        wy3, wz3 = FEMModel._get_uniform_load_components(load3, ndm=3)

        assert wy1 == wy2 == wy3 == pytest.approx(-5.0)


class TestBuildWithBeamColumn(object):
    """Tests for building model with BEAM_COLUMN element type."""

    def test_beam_column_element_builds(self, ops_monkeypatch) -> None:
        """Test that BEAM_COLUMN elements are built correctly."""
        reset_material_tags()
        model = FEMModel()
        model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
        model.add_node(Node(tag=2, x=0.0, y=0.0, z=3.0))

        concrete = create_concrete_material(ConcreteGrade.C40)
        mat_tag = get_next_material_tag()
        model.add_material(mat_tag, get_openseespy_concrete_material(concrete, mat_tag))

        section_tag = get_next_section_tag()
        section = get_elastic_beam_section(concrete, width=400, height=600,
                                           section_tag=section_tag)
        model.add_section(section_tag, section)

        model.add_element(
            Element(
                tag=1,
                element_type=ElementType.BEAM_COLUMN,  # Use BEAM_COLUMN type
                node_tags=[1, 2],
                material_tag=mat_tag,
                section_tag=section_tag,
            )
        )

        model.build_openseespy_model(ndm=3, ndf=6)

        elem_type, _ = ops_monkeypatch.elements[1]
        assert elem_type == "elasticBeamColumn"


class TestMultipleLoadPatterns:
    """Tests for models with multiple load patterns."""

    def test_multiple_load_patterns(self, ops_monkeypatch) -> None:
        """Test that multiple load patterns are applied correctly."""
        reset_material_tags()
        model = FEMModel()
        model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
        model.add_node(Node(tag=2, x=0.0, y=0.0, z=3.0))

        concrete = create_concrete_material(ConcreteGrade.C35)
        mat_tag = get_next_material_tag()
        model.add_material(mat_tag, get_openseespy_concrete_material(concrete, mat_tag))

        section_tag = get_next_section_tag()
        section = get_elastic_beam_section(concrete, width=300, height=500,
                                           section_tag=section_tag)
        model.add_section(section_tag, section)

        model.add_element(
            Element(
                tag=1,
                element_type=ElementType.ELASTIC_BEAM,
                node_tags=[1, 2],
                material_tag=mat_tag,
                section_tag=section_tag,
            )
        )

        # Add loads in different patterns
        model.add_load(
            Load(node_tag=2, load_values=[0, 0, -1000, 0, 0, 0], load_pattern=1)
        )
        model.add_load(
            Load(node_tag=2, load_values=[500, 0, 0, 0, 0, 0], load_pattern=2)
        )
        model.add_uniform_load(
            UniformLoad(element_tag=1, load_type="Gravity", magnitude=5.0, load_pattern=1)
        )
        model.add_uniform_load(
            UniformLoad(element_tag=1, load_type="Y", magnitude=2.0, load_pattern=2)
        )

        model.build_openseespy_model(ndm=3, ndf=6)

        # Check both patterns created
        pattern_ids = [p[1] for p in ops_monkeypatch.patterns]
        assert 1 in pattern_ids
        assert 2 in pattern_ids

        # Check time series created for each pattern
        ts_ids = [ts[1] for ts in ops_monkeypatch.time_series]
        assert 1 in ts_ids
        assert 2 in ts_ids


class TestShellAndCouplingBeamElements:
    """Tests for SHELL and COUPLING_BEAM element type support in builder."""

    def test_shell_element_builds_as_elastic_beam_column(self, ops_monkeypatch) -> None:
        """Test that SHELL elements (core walls) build as elasticBeamColumn."""
        reset_material_tags()
        model = FEMModel()

        # Create nodes for a vertical core wall element
        model.add_node(Node(tag=1, x=5.0, y=5.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
        model.add_node(Node(tag=2, x=5.0, y=5.0, z=3.0))

        concrete = create_concrete_material(ConcreteGrade.C40)
        mat_tag = get_next_material_tag()
        model.add_material(mat_tag, get_openseespy_concrete_material(concrete, mat_tag))

        # Section with core wall properties (A, I, J)
        section_tag = get_next_section_tag()
        model.add_section(section_tag, {
            'section_type': 'ElasticBeamSection',
            'tag': section_tag,
            'E': 25e9,
            'A': 2.0,      # 2 m² area
            'Iz': 10.0,    # 10 m⁴ I_xx
            'Iy': 5.0,     # 5 m⁴ I_yy
            'G': 10e9,
            'J': 2.5,      # 2.5 m⁴ torsional constant
        })

        # Create SHELL element (used for core walls)
        model.add_element(
            Element(
                tag=1,
                element_type=ElementType.SHELL,
                node_tags=[1, 2],
                material_tag=mat_tag,
                section_tag=section_tag,
                geometry={"vecxz": (0.0, 1.0, 0.0)},
            )
        )

        # Build model - should not raise
        model.build_openseespy_model(ndm=3, ndf=6)

        # Verify element was created as elasticBeamColumn
        elem_type, elem_args = ops_monkeypatch.elements[1]
        assert elem_type == "elasticBeamColumn"
        assert elem_args[0:2] == (1, 2)  # connectivity

    def test_coupling_beam_element_builds(self, ops_monkeypatch) -> None:
        """Test that COUPLING_BEAM elements build as elasticBeamColumn."""
        reset_material_tags()
        model = FEMModel()

        # Create nodes for a horizontal coupling beam
        model.add_node(Node(tag=1, x=0.0, y=5.0, z=3.0))
        model.add_node(Node(tag=2, x=3.0, y=5.0, z=3.0))
        model.add_node(Node(tag=10, x=0.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))

        concrete = create_concrete_material(ConcreteGrade.C40)
        mat_tag = get_next_material_tag()
        model.add_material(mat_tag, get_openseespy_concrete_material(concrete, mat_tag))

        section_tag = get_next_section_tag()
        model.add_section(
            section_tag,
            get_elastic_beam_section(concrete, width=500, height=1200, section_tag=section_tag),
        )

        # Create COUPLING_BEAM element
        model.add_element(
            Element(
                tag=1,
                element_type=ElementType.COUPLING_BEAM,
                node_tags=[1, 2],
                material_tag=mat_tag,
                section_tag=section_tag,
            )
        )

        # Build model - should not raise
        model.build_openseespy_model(ndm=3, ndf=6)

        # Verify element was created as elasticBeamColumn
        elem_type, elem_args = ops_monkeypatch.elements[1]
        assert elem_type == "elasticBeamColumn"
