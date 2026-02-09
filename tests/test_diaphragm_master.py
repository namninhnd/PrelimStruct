import pytest

from src.fem.fem_engine import FEMModel, Element, ElementType, Node
from src.fem.model_builder import create_floor_rigid_diaphragms


def _add_floor_nodes(model: FEMModel) -> None:
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=2, x=8.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=3, x=0.0, y=4.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=4, x=8.0, y=4.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))

    model.add_node(Node(tag=11, x=0.0, y=0.0, z=3.0))
    model.add_node(Node(tag=12, x=8.0, y=0.0, z=3.0))
    model.add_node(Node(tag=13, x=0.0, y=4.0, z=3.0))
    model.add_node(Node(tag=14, x=8.0, y=4.0, z=3.0))


def test_centroid_master_node() -> None:
    model = FEMModel()
    _add_floor_nodes(model)

    masters = create_floor_rigid_diaphragms(model, base_elevation=0.0, story_height=3.0)

    assert 3.0 in masters
    master = model.nodes[masters[3.0]]
    assert master.x == pytest.approx(4.0)
    assert master.y == pytest.approx(2.0)
    assert master.z == pytest.approx(3.0)


def test_master_node_tag_90000_range() -> None:
    model = FEMModel()
    _add_floor_nodes(model)

    masters = create_floor_rigid_diaphragms(model, base_elevation=0.0, story_height=3.0)

    assert masters[3.0] >= 90000


def test_all_structural_nodes_are_slaves() -> None:
    model = FEMModel()
    _add_floor_nodes(model)

    masters = create_floor_rigid_diaphragms(model, base_elevation=0.0, story_height=3.0)
    diaphragm = model.diaphragms[0]

    assert masters[3.0] == diaphragm.master_node
    assert set(diaphragm.slave_nodes) == {11, 12, 13, 14}


def test_master_has_no_element_connectivity() -> None:
    model = FEMModel()
    _add_floor_nodes(model)

    model.add_element(
        Element(
            tag=1,
            element_type=ElementType.BEAM_COLUMN,
            node_tags=[11, 12],
            material_tag=1,
            section_tag=1,
        )
    )

    masters = create_floor_rigid_diaphragms(model, base_elevation=0.0, story_height=3.0)
    master_tag = masters[3.0]

    assert all(master_tag not in elem.node_tags for elem in model.elements.values())


def test_centroid_for_asymmetric_plan() -> None:
    model = FEMModel()
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=2, x=10.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=11, x=0.0, y=0.0, z=3.0))
    model.add_node(Node(tag=12, x=10.0, y=0.0, z=3.0))
    model.add_node(Node(tag=13, x=4.0, y=6.0, z=3.0))

    masters = create_floor_rigid_diaphragms(model, base_elevation=0.0, story_height=3.0)
    master = model.nodes[masters[3.0]]

    assert master.x == pytest.approx((0.0 + 10.0 + 4.0) / 3.0)
    assert master.y == pytest.approx((0.0 + 0.0 + 6.0) / 3.0)
