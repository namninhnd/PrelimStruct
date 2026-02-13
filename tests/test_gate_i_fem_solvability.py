import pytest

from src.core.data_models import (
    BeamResult,
    ColumnResult,
    CoreWallConfig,
    CoreWallGeometry,
    GeometryInput,
    LateralInput,
    LoadInput,
    MaterialInput,
    ProjectData,
    TubeOpeningPlacement,
    WindResult,
)
from src.fem.fem_engine import Element, ElementType, FEMModel, Node, RigidDiaphragm
from src.fem.model_builder import ModelBuilderOptions, build_fem_model
from src.fem.solver import analyze_model


def _make_project_for_gate_i(core_geometry: CoreWallGeometry) -> ProjectData:
    project = ProjectData(
        geometry=GeometryInput(
            bay_x=6.0,
            bay_y=6.0,
            floors=2,
            story_height=3.0,
            num_bays_x=2,
            num_bays_y=2,
        ),
        loads=LoadInput(live_load_class="2", live_load_sub="2.5", dead_load=2.0),
        materials=MaterialInput(fcu_slab=35, fcu_beam=40, fcu_column=45),
        lateral=LateralInput(
            core_wall_config=core_geometry.config,
            core_geometry=core_geometry,
            building_width=12.0,
            building_depth=12.0,
        ),
    )

    project.primary_beam_result = BeamResult(
        element_type="Primary Beam",
        size="300x600",
        width=300,
        depth=600,
    )
    project.secondary_beam_result = BeamResult(
        element_type="Secondary Beam",
        size="250x500",
        width=250,
        depth=500,
    )
    project.column_result = ColumnResult(
        element_type="Column",
        size="400",
        dimension=400,
    )

    return project


class TestGateIIntegration:
    @pytest.mark.parametrize(
        "core_geometry",
        [
            CoreWallGeometry(
                config=CoreWallConfig.I_SECTION,
                wall_thickness=500.0,
                flange_width=3000.0,
                web_length=6000.0,
                length_x=3000.0,
                length_y=6000.0,
            ),
            CoreWallGeometry(
                config=CoreWallConfig.TUBE_WITH_OPENINGS,
                wall_thickness=400.0,
                length_x=4000.0,
                length_y=4000.0,
                opening_width=2000.0,
                opening_height=None,
                opening_placement=TubeOpeningPlacement.TOP_BOT,
            ),
        ],
        ids=["i_section", "tube"],
    )
    def test_core_models_validate_without_orphan_or_zero_length_errors(
        self,
        core_geometry: CoreWallGeometry,
    ) -> None:
        project = _make_project_for_gate_i(core_geometry)
        model = build_fem_model(
            project,
            ModelBuilderOptions(
                include_core_wall=True,
                include_slabs=False,
                apply_wind_loads=False,
            ),
        )

        is_valid, errors = model.validate_model()
        assert is_valid, f"Validation failed: {errors}"
        assert not any("orphan" in err.lower() for err in errors)
        assert not any("zero" in err.lower() and "length" in err.lower() for err in errors)

    @pytest.mark.parametrize(
        "core_geometry",
        [
            CoreWallGeometry(
                config=CoreWallConfig.I_SECTION,
                wall_thickness=500.0,
                flange_width=3000.0,
                web_length=6000.0,
                length_x=3000.0,
                length_y=6000.0,
            ),
            CoreWallGeometry(
                config=CoreWallConfig.TUBE_WITH_OPENINGS,
                wall_thickness=400.0,
                length_x=4000.0,
                length_y=4000.0,
                opening_width=2000.0,
                opening_height=None,
                opening_placement=TubeOpeningPlacement.TOP_BOT,
            ),
        ],
        ids=["i_section", "tube"],
    )
    def test_core_models_analyze_without_singular_matrix(
        self,
        core_geometry: CoreWallGeometry,
    ) -> None:
        project = _make_project_for_gate_i(core_geometry)
        model = build_fem_model(
            project,
            ModelBuilderOptions(
                include_core_wall=True,
                include_slabs=False,
                apply_wind_loads=False,
            ),
        )

        result = analyze_model(model, load_cases=["DL"])["DL"]

        assert result.success, result.message
        assert result.converged, result.message
        assert "matrix singular" not in result.message.lower()

    @pytest.mark.parametrize(
        "opening_placement,opening_width",
        [
            (TubeOpeningPlacement.TOP_BOT, 1000.0),
            (TubeOpeningPlacement.NONE, None),
        ],
        ids=["top_bot_1m", "none"],
    )
    def test_tube_with_slabs_analyzes_without_singular_matrix(
        self,
        opening_placement: TubeOpeningPlacement,
        opening_width: float | None,
    ) -> None:
        project = _make_project_for_gate_i(
            CoreWallGeometry(
                config=CoreWallConfig.TUBE_WITH_OPENINGS,
                wall_thickness=500.0,
                length_x=3000.0,
                length_y=3000.0,
                opening_width=opening_width,
                opening_height=None,
                opening_placement=opening_placement,
            )
        )

        model = build_fem_model(
            project,
            ModelBuilderOptions(
                include_core_wall=True,
                include_slabs=True,
                apply_wind_loads=False,
            ),
        )

        connected_node_tags = set()
        for element in model.elements.values():
            connected_node_tags.update(element.node_tags)

        isolated_node_tags = [
            tag for tag in model.nodes
            if tag not in connected_node_tags
        ]
        diaphragm_master_tags = {diaphragm.master_node for diaphragm in model.diaphragms}
        assert all(tag in diaphragm_master_tags for tag in isolated_node_tags)

        result = analyze_model(model, load_cases=["DL"])["DL"]
        assert result.success, result.message
        assert result.converged, result.message
        assert "matrix singular" not in result.message.lower()

    def test_tube_with_slabs_and_wind_analyzes_without_singular_matrix(self) -> None:
        project = _make_project_for_gate_i(
            CoreWallGeometry(
                config=CoreWallConfig.TUBE_WITH_OPENINGS,
                wall_thickness=500.0,
                length_x=3000.0,
                length_y=3000.0,
                opening_width=1000.0,
                opening_height=None,
                opening_placement=TubeOpeningPlacement.TOP_BOT,
            )
        )
        project.wind_result = WindResult(
            base_shear=120.0,
            base_shear_x=120.0,
            base_shear_y=90.0,
        )

        model = build_fem_model(
            project,
            ModelBuilderOptions(
                include_core_wall=True,
                include_slabs=True,
                apply_wind_loads=True,
            ),
        )

        results = analyze_model(model, load_cases=["DL", "Wx", "Wy", "Wtz"])
        for case_name in ["DL", "Wx", "Wy", "Wtz"]:
            case_result = results[case_name]
            assert case_result.success, case_result.message
            assert case_result.converged, case_result.message
            assert "matrix singular" not in case_result.message.lower()

    def test_tube_with_omitted_columns_analyzes_without_singular_matrix(self) -> None:
        project = _make_project_for_gate_i(
            CoreWallGeometry(
                config=CoreWallConfig.TUBE_WITH_OPENINGS,
                wall_thickness=500.0,
                length_x=3000.0,
                length_y=3000.0,
                opening_width=1000.0,
                opening_height=None,
                opening_placement=TubeOpeningPlacement.TOP_BOT,
            )
        )
        project.wind_result = WindResult(
            base_shear=120.0,
            base_shear_x=120.0,
            base_shear_y=90.0,
        )

        model = build_fem_model(
            project,
            ModelBuilderOptions(
                include_core_wall=True,
                include_slabs=True,
                apply_wind_loads=True,
                suggested_omit_columns=("B-2", "B-3", "C-2", "C-3"),
            ),
        )

        results = analyze_model(model, load_cases=["DL", "Wx", "Wy", "Wtz"])
        for case_name in ["DL", "Wx", "Wy", "Wtz"]:
            case_result = results[case_name]
            assert case_result.success, case_result.message
            assert case_result.converged, case_result.message
            assert "matrix singular" not in case_result.message.lower()


class TestGateIOrphanDetection:
    def test_detects_structural_orphan_node(self) -> None:
        model = FEMModel()
        model.add_node(Node(tag=1, x=0, y=0, z=0, restraints=[1, 1, 1, 1, 1, 1]))
        model.add_node(Node(tag=2, x=3, y=0, z=0))
        model.add_node(Node(tag=3, x=3, y=3, z=0))
        model.add_material(1, {"material_type": "Concrete01"})
        model.add_section(1, {"section_type": "ElasticBeamSection"})
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
        assert any("orphan" in err.lower() and "3" in err for err in errors)

    def test_allows_fixed_orphan_node(self) -> None:
        model = FEMModel()
        model.add_node(Node(tag=1, x=0, y=0, z=0, restraints=[1, 1, 1, 1, 1, 1]))
        model.add_node(Node(tag=2, x=3, y=0, z=0))
        model.add_node(Node(tag=3, x=3, y=3, z=0, restraints=[1, 1, 1, 1, 1, 1]))
        model.add_material(1, {"material_type": "Concrete01"})
        model.add_section(1, {"section_type": "ElasticBeamSection"})
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
        assert is_valid, f"Fixed orphan should be allowed: {errors}"

    def test_diaphragm_slaves_not_orphans(self) -> None:
        model = FEMModel()
        model.add_node(Node(tag=1, x=0, y=0, z=0, restraints=[1, 1, 1, 1, 1, 1]))
        model.add_node(Node(tag=2, x=3, y=0, z=0))
        model.add_node(Node(tag=3, x=0, y=3, z=0))
        model.add_node(Node(tag=100, x=1.5, y=1.5, z=0))
        model.add_material(1, {"material_type": "Concrete01"})
        model.add_section(1, {"section_type": "ElasticBeamSection"})
        model.add_element(
            Element(
                tag=1,
                element_type=ElementType.ELASTIC_BEAM,
                node_tags=[1, 2],
                material_tag=1,
                section_tag=1,
            )
        )
        model.add_rigid_diaphragm(RigidDiaphragm(master_node=100, slave_nodes=[1, 2, 3]))
        is_valid, errors = model.validate_model()
        assert is_valid, f"Diaphragm slaves should not be orphans: {errors}"


class TestGateIZeroLengthDetection:
    def test_detects_zero_length_element(self) -> None:
        model = FEMModel()
        model.add_node(Node(tag=1, x=0, y=0, z=0, restraints=[1, 1, 1, 1, 1, 1]))
        model.add_node(Node(tag=2, x=0, y=0, z=0))
        model.add_material(1, {"material_type": "Concrete01"})
        model.add_section(1, {"section_type": "ElasticBeamSection"})
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
        assert any("zero" in err.lower() and "length" in err.lower() for err in errors)
