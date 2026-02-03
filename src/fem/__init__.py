"""
FEM (Finite Element Method) module for PrelimStruct v3.0

This module provides finite element analysis capabilities using OpenSeesPy
and ConcreteProperties with HK Code 2013 integration.
"""

from src.fem.core_wall_geometry import ISectionCoreWall, calculate_i_section_properties
from src.fem.fem_engine import (
    FEMModel,
    Element,
    ElementType,
    BoundaryCondition,
    DOF,
    Load,
    Node,
    UniformLoad,
    RigidDiaphragm,
    create_simple_frame_model,
)
from src.fem.materials import (
    ConcreteGrade,
    SteelGrade,
    ConcreteProperties,
    SteelProperties,
    create_concrete_material,
    create_steel_material,
    get_elastic_beam_section,
)
from src.fem.model_builder import (
    apply_lateral_loads_to_diaphragms,
    create_floor_rigid_diaphragms,
    build_fem_model,
    ModelBuilderOptions,
    BeamSegment,
    trim_beam_segment_against_polygon,
)
from src.fem.solver import FEMSolver, AnalysisResult, analyze_model

__all__ = [
    "ISectionCoreWall",
    "calculate_i_section_properties",
    "FEMModel",
    "Element",
    "ElementType",
    "BoundaryCondition",
    "DOF",
    "Load",
    "Node",
    "UniformLoad",
    "RigidDiaphragm",
    "create_simple_frame_model",
    "ConcreteGrade",
    "SteelGrade",
    "ConcreteProperties",
    "SteelProperties",
    "create_concrete_material",
    "create_steel_material",
    "get_elastic_beam_section",
    "FEMSolver",
    "AnalysisResult",
    "analyze_model",
    "create_floor_rigid_diaphragms",
    "apply_lateral_loads_to_diaphragms",
    "build_fem_model",
    "ModelBuilderOptions",
    "BeamSegment",
    "trim_beam_segment_against_polygon",
]
