"""
FEM (Finite Element Method) module for PrelimStruct v3.0

This module provides finite element analysis capabilities using OpenSeesPy
and ConcreteProperties with HK Code 2013 integration.
"""

from src.fem.core_wall_geometry import (
    ISectionCoreWall,
    calculate_i_section_properties,
)

__all__ = [
    "ISectionCoreWall",
    "calculate_i_section_properties",
]
