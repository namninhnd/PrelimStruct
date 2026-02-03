import pytest

from src.core.data_models import (
    FEMAnalysisSettings,
    FEMElementType,
    FEMModelInput,
    FEMResult,
    EnvelopedResult,
    EnvelopeValue,
    LoadCaseResult,
    LoadCombination,
    MeshData,
    MeshElement,
    NodalLoad,
    ProjectData,
    SupportCondition,
)


def test_support_condition_validation() -> None:
    """SupportCondition should validate restraint length and values."""
    with pytest.raises(ValueError):
        SupportCondition(node_tag=1, restraints=[1, 1, 1, 1, 1])  # missing one DOF

    with pytest.raises(ValueError):
        SupportCondition(node_tag=1, restraints=[1, 1, 1, 1, 1, -1])  # invalid flag

    support = SupportCondition(node_tag=2, restraints=[1, 1, 1, 1, 1, 1])
    assert support.is_fully_fixed


def test_nodal_load_validation() -> None:
    """NodalLoad should enforce 6-component vectors."""
    with pytest.raises(ValueError):
        NodalLoad(node_tag=1, load_values=[0.0, 0.0, 0.0])

    load = NodalLoad(node_tag=1, load_values=[100.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    assert load.load_pattern == "DEFAULT"


def test_mesh_data_summary_counts() -> None:
    """MeshData summary should reflect nodes, elements, supports, and loads."""
    mesh = MeshData(
        node_coordinates={1: (0.0, 0.0, 0.0), 2: (4.0, 0.0, 3.0)},
        elements=[
            MeshElement(
                element_id=1,
                element_type=FEMElementType.BEAM,
                node_tags=[1, 2],
                section_id="beam_section",
                material_id="concrete_c40",
            )
        ],
        supports=[SupportCondition(node_tag=1, restraints=[1, 1, 1, 1, 1, 1])],
        loads=[NodalLoad(node_tag=2, load_values=[0.0, 0.0, -25.0, 0.0, 0.0, 0.0])],
    )

    summary = mesh.get_summary()
    assert summary["n_nodes"] == 2
    assert summary["n_elements"] == 1
    assert summary["n_supports"] == 1
    assert summary["n_loads"] == 1
    assert mesh.get_fixed_nodes() == [1]


def test_fem_analysis_settings_defaults() -> None:
    """Default FEMAnalysisSettings should include standard combinations."""
    settings = FEMAnalysisSettings()
    assert settings.analysis_type == "linear_static"
    assert settings.n_dimensions == 3
    assert settings.dof_per_node == 6
    assert LoadCombination.ULS_GRAVITY_1 in settings.load_combinations
    assert LoadCombination.SLS_CHARACTERISTIC in settings.load_combinations


def test_fem_model_input_summary() -> None:
    """FEMModelInput should summarize mesh and element types."""
    mesh = MeshData(
        node_coordinates={1: (0.0, 0.0, 0.0), 2: (6.0, 0.0, 3.0)},
        elements=[
            MeshElement(
                element_id=1,
                element_type=FEMElementType.BEAM,
                node_tags=[1, 2],
            )
        ],
    )
    model_input = FEMModelInput(mesh=mesh)

    summary = model_input.get_summary()
    assert summary["n_nodes"] == 2
    assert summary["element_types"] == [FEMElementType.BEAM.value]
    assert summary["analysis_type"] == "linear_static"
    assert summary["dof_per_node"] == 6


def test_fem_result_summary_and_project_data_export() -> None:
    """FEMResult summary should propagate through ProjectData serialization."""
    load_case = LoadCaseResult(
        combination=LoadCombination.ULS_WIND_1,
        node_displacements={1: [0.0, 0.0, 0.012, 0.0, 0.0, 0.0]},
        reactions={1: [0.0, 0.0, -120.0, 0.0, 0.0, 15.0]},
    )
    envelope = EnvelopedResult(
        displacements=EnvelopeValue(
            max_value=0.012,
            min_value=0.0,
            governing_max_case=LoadCombination.ULS_WIND_1,
            governing_min_case=LoadCombination.ULS_GRAVITY_1,
        ),
        reactions=EnvelopeValue(max_value=120.0, min_value=0.0),
        stresses=EnvelopeValue(max_value=5.0, min_value=-5.0),
        strains=EnvelopeValue(max_value=0.0004, min_value=-0.0001),
    )
    fem_result = FEMResult(load_case_results=[load_case], enveloped_results=envelope)

    mesh = MeshData(node_coordinates={1: (0.0, 0.0, 0.0)})
    fem_model = FEMModelInput(mesh=mesh)
    project = ProjectData(fem_model=fem_model, fem_result=fem_result)

    summary = fem_result.get_summary()
    assert summary["n_load_cases"] == 1
    assert summary["enveloped"]["max_displacement"] == pytest.approx(0.012)
    assert summary["enveloped"]["max_reaction"] == pytest.approx(120.0)

    serialized = project.to_dict()
    assert serialized["fem_model"]["n_nodes"] == 1
    assert serialized["fem_result"]["n_load_cases"] == 1


# ============================================================================
# Edge Case Tests (Task 8.5 - Further Testing/Improvement)
# ============================================================================


def test_mesh_element_minimum_valid_two_nodes() -> None:
    """Test MeshElement with exactly 2 node_tags (minimum valid beam)."""
    # A beam element requires exactly 2 nodes minimum
    element = MeshElement(
        element_id=101,
        element_type=FEMElementType.BEAM,
        node_tags=[1, 2],
        section_id="beam_300x600",
        material_id="concrete_c40",
    )
    assert element.element_id == 101
    assert element.element_type == FEMElementType.BEAM
    assert len(element.node_tags) == 2
    assert element.node_tags == [1, 2]
    assert element.section_id == "beam_300x600"
    assert element.material_id == "concrete_c40"


def test_mesh_element_one_node_raises_error() -> None:
    """Test MeshElement with 1 node raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        MeshElement(
            element_id=102,
            element_type=FEMElementType.BEAM,
            node_tags=[1],  # Only 1 node - invalid
        )
    assert "at least two node tags" in str(exc_info.value)


def test_mesh_element_empty_nodes_raises_error() -> None:
    """Test MeshElement with empty node_tags raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        MeshElement(
            element_id=103,
            element_type=FEMElementType.PLATE,
            node_tags=[],  # Empty - invalid
        )
    assert "at least two node tags" in str(exc_info.value)


def test_mesh_element_plate_with_four_nodes() -> None:
    """Test MeshElement for plate with 4 nodes (quadrilateral element)."""
    element = MeshElement(
        element_id=201,
        element_type=FEMElementType.PLATE,
        node_tags=[1, 2, 3, 4],  # Quad element
        section_id="slab_200mm",
        material_id="concrete_c35",
    )
    assert len(element.node_tags) == 4
    assert element.element_type == FEMElementType.PLATE


def test_empty_mesh_data() -> None:
    """Test empty MeshData with n_nodes=0, n_elements=0."""
    # Empty mesh should be valid but have zero counts
    mesh = MeshData()
    
    summary = mesh.get_summary()
    assert summary["n_nodes"] == 0
    assert summary["n_elements"] == 0
    assert summary["n_supports"] == 0
    assert summary["n_loads"] == 0
    
    # Fixed nodes should be empty list
    assert mesh.get_fixed_nodes() == []


def test_mesh_data_with_nodes_only() -> None:
    """Test MeshData with nodes but no elements, supports, or loads."""
    mesh = MeshData(
        node_coordinates={
            1: (0.0, 0.0, 0.0),
            2: (4.0, 0.0, 0.0),
            3: (4.0, 4.0, 0.0),
        }
    )
    
    summary = mesh.get_summary()
    assert summary["n_nodes"] == 3
    assert summary["n_elements"] == 0
    assert summary["n_supports"] == 0
    assert summary["n_loads"] == 0


def test_support_condition_all_free() -> None:
    """Test SupportCondition with restraints=[0,0,0,0,0,0] (all DOFs free)."""
    # All DOFs free - valid configuration (e.g., for a node that's not a support)
    support = SupportCondition(
        node_tag=99,
        restraints=[0, 0, 0, 0, 0, 0],
        label="all_free_node",
    )
    
    assert support.node_tag == 99
    assert support.restraints == [0, 0, 0, 0, 0, 0]
    assert support.label == "all_free_node"
    # is_fully_fixed should be False
    assert support.is_fully_fixed is False


def test_support_condition_partial_restraints() -> None:
    """Test SupportCondition with partial restraints (e.g., pinned support)."""
    # Pinned support: translations fixed, rotations free
    pinned = SupportCondition(
        node_tag=10,
        restraints=[1, 1, 1, 0, 0, 0],
        label="pinned_support",
    )
    
    assert pinned.restraints == [1, 1, 1, 0, 0, 0]
    assert pinned.is_fully_fixed is False
    
    # Roller support: only vertical (uz) fixed
    roller = SupportCondition(
        node_tag=11,
        restraints=[0, 0, 1, 0, 0, 0],
        label="roller_support",
    )
    
    assert roller.is_fully_fixed is False
    assert roller.restraints[2] == 1  # uz fixed


def test_mesh_data_get_fixed_nodes_empty_when_no_fully_fixed() -> None:
    """Test MeshData.get_fixed_nodes() returns empty list when no fully-fixed supports."""
    mesh = MeshData(
        node_coordinates={
            1: (0.0, 0.0, 0.0),
            2: (4.0, 0.0, 0.0),
        },
        elements=[
            MeshElement(
                element_id=1,
                element_type=FEMElementType.BEAM,
                node_tags=[1, 2],
            )
        ],
        supports=[
            # Pinned support (translations fixed only)
            SupportCondition(node_tag=1, restraints=[1, 1, 1, 0, 0, 0], label="pinned"),
            # Roller support (vertical only)
            SupportCondition(node_tag=2, restraints=[0, 0, 1, 0, 0, 0], label="roller"),
        ],
    )
    
    # Neither support is fully fixed
    fixed_nodes = mesh.get_fixed_nodes()
    assert fixed_nodes == []


def test_mesh_data_get_fixed_nodes_mixed_supports() -> None:
    """Test MeshData.get_fixed_nodes() with mix of fully-fixed and partial supports."""
    mesh = MeshData(
        node_coordinates={
            1: (0.0, 0.0, 0.0),
            2: (4.0, 0.0, 0.0),
            3: (8.0, 0.0, 0.0),
        },
        supports=[
            SupportCondition(node_tag=1, restraints=[1, 1, 1, 1, 1, 1]),  # Fully fixed
            SupportCondition(node_tag=2, restraints=[1, 1, 1, 0, 0, 0]),  # Pinned
            SupportCondition(node_tag=3, restraints=[1, 1, 1, 1, 1, 1]),  # Fully fixed
        ],
    )
    
    fixed_nodes = mesh.get_fixed_nodes()
    assert fixed_nodes == [1, 3]  # Only nodes 1 and 3 are fully fixed


def test_mesh_data_get_fixed_nodes_all_free_supports() -> None:
    """Test get_fixed_nodes when all supports have all DOFs free."""
    mesh = MeshData(
        node_coordinates={1: (0.0, 0.0, 0.0)},
        supports=[
            SupportCondition(node_tag=1, restraints=[0, 0, 0, 0, 0, 0]),
        ],
    )
    
    assert mesh.get_fixed_nodes() == []


def test_envelope_value_defaults() -> None:
    """Test EnvelopeValue default values."""
    envelope = EnvelopeValue()
    
    assert envelope.max_value == 0.0
    assert envelope.min_value == 0.0
    assert envelope.governing_max_case is None
    assert envelope.governing_min_case is None


def test_envelope_value_with_all_fields() -> None:
    """Test EnvelopeValue with all fields populated."""
    envelope = EnvelopeValue(
        max_value=25.5,
        min_value=-10.2,
        governing_max_case=LoadCombination.ULS_WIND_1,
        governing_min_case=LoadCombination.ULS_GRAVITY_1,
    )

    assert envelope.max_value == pytest.approx(25.5)
    assert envelope.min_value == pytest.approx(-10.2)
    assert envelope.governing_max_case == LoadCombination.ULS_WIND_1
    assert envelope.governing_min_case == LoadCombination.ULS_GRAVITY_1


def test_load_combination_enum_values() -> None:
    """Test LoadCombination enum has expected values for HK Code 2013."""
    # Ensure primary combinations are present per HK Code 2013 Table 2.1
    assert LoadCombination.ULS_GRAVITY_1.value == "uls_gravity_1"
    assert LoadCombination.ULS_WIND_1.value == "uls_wind_1"
    assert LoadCombination.SLS_CHARACTERISTIC.value == "sls_characteristic"

    # Test all enum members are accessible (HK Code + Seismic)
    all_combos = list(LoadCombination)
    assert len(all_combos) >= 10  # Multiple ULS + SLS combinations


# ============================================================================
# Enhancement Tests (Task 8.5 - validate_connectivity & governing_location)
# ============================================================================


def test_mesh_data_validate_connectivity_valid() -> None:
    """Test validate_connectivity() returns True for valid mesh."""
    mesh = MeshData(
        node_coordinates={
            1: (0.0, 0.0, 0.0),
            2: (4.0, 0.0, 0.0),
            3: (4.0, 4.0, 0.0),
        },
        elements=[
            MeshElement(
                element_id=1,
                element_type=FEMElementType.BEAM,
                node_tags=[1, 2],
            ),
            MeshElement(
                element_id=2,
                element_type=FEMElementType.BEAM,
                node_tags=[2, 3],
            ),
        ],
        supports=[
            SupportCondition(node_tag=1, restraints=[1, 1, 1, 1, 1, 1]),
        ],
        loads=[
            NodalLoad(node_tag=3, load_values=[0.0, 0.0, -10.0, 0.0, 0.0, 0.0]),
        ],
    )

    is_valid, errors = mesh.validate_connectivity()
    assert is_valid is True
    assert errors == []


def test_mesh_data_validate_connectivity_invalid_element_nodes() -> None:
    """Test validate_connectivity() detects invalid element node references."""
    mesh = MeshData(
        node_coordinates={
            1: (0.0, 0.0, 0.0),
            2: (4.0, 0.0, 0.0),
        },
        elements=[
            MeshElement(
                element_id=1,
                element_type=FEMElementType.BEAM,
                node_tags=[1, 99],  # Node 99 doesn't exist
            ),
        ],
    )

    is_valid, errors = mesh.validate_connectivity()
    assert is_valid is False
    assert len(errors) == 1
    assert "Element 1" in errors[0]
    assert "node 99" in errors[0]


def test_mesh_data_validate_connectivity_invalid_support_node() -> None:
    """Test validate_connectivity() detects invalid support node references."""
    mesh = MeshData(
        node_coordinates={
            1: (0.0, 0.0, 0.0),
        },
        supports=[
            SupportCondition(node_tag=999, restraints=[1, 1, 1, 1, 1, 1]),  # Invalid
        ],
    )

    is_valid, errors = mesh.validate_connectivity()
    assert is_valid is False
    assert len(errors) == 1
    assert "Support at node 999" in errors[0]


def test_mesh_data_validate_connectivity_invalid_load_node() -> None:
    """Test validate_connectivity() detects invalid load node references."""
    mesh = MeshData(
        node_coordinates={
            1: (0.0, 0.0, 0.0),
        },
        loads=[
            NodalLoad(node_tag=888, load_values=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0]),  # Invalid
        ],
    )

    is_valid, errors = mesh.validate_connectivity()
    assert is_valid is False
    assert len(errors) == 1
    assert "Load at node 888" in errors[0]


def test_mesh_data_validate_connectivity_multiple_errors() -> None:
    """Test validate_connectivity() collects all errors."""
    mesh = MeshData(
        node_coordinates={
            1: (0.0, 0.0, 0.0),
        },
        elements=[
            MeshElement(element_id=1, element_type=FEMElementType.BEAM, node_tags=[1, 50]),
            MeshElement(element_id=2, element_type=FEMElementType.BEAM, node_tags=[60, 70]),
        ],
        supports=[
            SupportCondition(node_tag=100, restraints=[1, 1, 1, 1, 1, 1]),
        ],
        loads=[
            NodalLoad(node_tag=200, load_values=[0.0, 0.0, -10.0, 0.0, 0.0, 0.0]),
        ],
    )

    is_valid, errors = mesh.validate_connectivity()
    assert is_valid is False
    # Should have errors for: node 50, node 60, node 70, support 100, load 200
    assert len(errors) == 5


def test_mesh_data_validate_connectivity_empty_mesh() -> None:
    """Test validate_connectivity() on empty mesh returns valid."""
    mesh = MeshData()

    is_valid, errors = mesh.validate_connectivity()
    assert is_valid is True
    assert errors == []


def test_envelope_value_with_location_fields() -> None:
    """Test EnvelopeValue with governing_max_location and governing_min_location."""
    envelope = EnvelopeValue(
        max_value=150.5,
        min_value=-75.2,
        governing_max_case=LoadCombination.ULS_WIND_1,
        governing_min_case=LoadCombination.ULS_GRAVITY_1,
        governing_max_location=42,  # Node/element where max occurs
        governing_min_location=17,  # Node/element where min occurs
    )

    assert envelope.max_value == pytest.approx(150.5)
    assert envelope.min_value == pytest.approx(-75.2)
    assert envelope.governing_max_case == LoadCombination.ULS_WIND_1
    assert envelope.governing_min_case == LoadCombination.ULS_GRAVITY_1
    assert envelope.governing_max_location == 42
    assert envelope.governing_min_location == 17


def test_envelope_value_location_defaults_to_none() -> None:
    """Test EnvelopeValue location fields default to None."""
    envelope = EnvelopeValue(max_value=10.0, min_value=-5.0)

    assert envelope.governing_max_location is None
    assert envelope.governing_min_location is None


def test_enveloped_result_with_locations() -> None:
    """Test EnvelopedResult can store location info for all metrics."""
    envelope_disp = EnvelopeValue(
        max_value=0.025,
        min_value=0.0,
        governing_max_case=LoadCombination.SLS_CHARACTERISTIC,
        governing_max_location=15,  # Top floor node
    )
    envelope_stress = EnvelopeValue(
        max_value=25.0,
        min_value=-15.0,
        governing_max_location=7,  # Critical column
        governing_min_location=3,  # Compression zone
    )

    result = EnvelopedResult(
        displacements=envelope_disp,
        stresses=envelope_stress,
    )

    assert result.displacements.governing_max_location == 15
    assert result.stresses.governing_max_location == 7
    assert result.stresses.governing_min_location == 3
