"""Structural layout visualization functions for PrelimStruct dashboard.

This module contains visualization functions for displaying structural framing plans,
lateral load diagrams, and utilization maps using Plotly.
"""

from typing import Dict, Any, Tuple, Optional

import plotly.graph_objects as go
import numpy as np

from src.core.data_models import ProjectData, CoreWallConfig
from src.fem.fem_engine import FEMModel
from src.fem.core_wall_helpers import get_core_wall_outline, get_coupling_beams
from src.fem.beam_trimmer import BeamTrimmer
from src.ui.utils import create_beam_geometries_from_project


def build_preview_utilization_map(model: FEMModel, project: ProjectData) -> Dict[int, float]:
    """Build approximate utilization map for FEM preview using preliminary design results."""
    utilization_map: Dict[int, float] = {}
    tolerance = 0.01
    primary_along_x = project.geometry.bay_x >= project.geometry.bay_y

    pri_util = project.primary_beam_result.utilization if project.primary_beam_result else 0.0
    sec_util = project.secondary_beam_result.utilization if project.secondary_beam_result else 0.0
    col_util = project.column_result.utilization if project.column_result else 0.0

    for elem in model.elements.values():
        if len(elem.node_tags) < 2:
            continue
        node_i = model.nodes[elem.node_tags[0]]
        node_j = model.nodes[elem.node_tags[1]]

        is_vertical = (abs(node_i.z - node_j.z) > tolerance and
                       abs(node_i.x - node_j.x) < tolerance and
                       abs(node_i.y - node_j.y) < tolerance)
        if is_vertical:
            utilization_map[elem.tag] = col_util
            continue

        is_horizontal = abs(node_i.z - node_j.z) < tolerance
        if is_horizontal:
            along_x = abs(node_i.y - node_j.y) < tolerance
            if primary_along_x:
                utilization_map[elem.tag] = pri_util if along_x else sec_util
            else:
                utilization_map[elem.tag] = sec_util if along_x else pri_util

    return utilization_map


def _analysis_result_to_displacements(result) -> Dict[int, Tuple[float, float, float]]:
    """Extract translational displacements from AnalysisResult."""
    displaced: Dict[int, Tuple[float, float, float]] = {}
    for node_tag, values in result.node_displacements.items():
        if len(values) >= 3:
            displaced[node_tag] = (values[0], values[1], values[2])
    return displaced


