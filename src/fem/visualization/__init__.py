"""
FEM Visualization Package.

This package provides modular visualization components for FEM models:
- Projections: Coordinate transformations for different views
- Element Rendering: Beams, columns, shells
- Overlays: Supports, loads, labels
- Specialized Renderers: Slabs, ghost columns

Usage:
    from src.fem.visualization import create_plan_view, create_elevation_view, create_3d_view
    from src.fem.visualization.element_renderer import render_beams, render_columns
    from src.fem.visualization.projections import get_floor_elevations

Note: The main visualization functions (create_plan_view, etc.) are imported from
the parent visualization module for backward compatibility. The modular components
are defined in the subpackage modules.
"""

import importlib.util
import os

_viz_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "visualization.py")
_spec = importlib.util.spec_from_file_location("visualization_module", _viz_file)
_viz_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_viz_module)

VisualizationConfig = _viz_module.VisualizationConfig
VisualizationData = _viz_module.VisualizationData
VisualizationExtractionConfig = _viz_module.VisualizationExtractionConfig
VisualizationBackend = _viz_module.VisualizationBackend
ModelLike = _viz_module.ModelLike
create_plan_view = _viz_module.create_plan_view
create_elevation_view = _viz_module.create_elevation_view
create_3d_view = _viz_module.create_3d_view
extract_visualization_data_from_opensees = _viz_module.extract_visualization_data_from_opensees
build_visualization_data_from_fem_model = _viz_module.build_visualization_data_from_fem_model
get_model_statistics = _viz_module.get_model_statistics
export_plotly_figure_image = _viz_module.export_plotly_figure_image
_classify_elements = _viz_module._classify_elements
_get_support_symbol = _viz_module._get_support_symbol
_get_floor_elevations = _viz_module._get_floor_elevations
calculate_auto_scale_factor = _viz_module.calculate_auto_scale_factor
render_section_forces = _viz_module.render_section_forces
render_section_forces_plan = _viz_module.render_section_forces_plan
PLOTLY_AVAILABLE = _viz_module.PLOTLY_AVAILABLE
OPSVIS_AVAILABLE = _viz_module.OPSVIS_AVAILABLE
LEGACY_COLORS = _viz_module.COLORS

# Re-export modular components from subpackage modules
from src.fem.visualization.element_renderer import (
    COLORS,
    RenderConfig,
    classify_elements,
    render_beams,
    render_columns,
    render_core_walls,
)
from src.fem.visualization.overlays import (
    render_ghost_columns,
    render_loads,
    render_nodes,
    render_slabs,
    render_supports,
)
from src.fem.visualization.projections import (
    calculate_camera_position,
    filter_nodes_at_elevation,
    get_bounding_box_2d,
    get_bounding_box_3d,
    get_floor_elevations,
    project_element_to_elevation,
    project_element_to_plan,
    project_to_elevation_xz,
    project_to_elevation_yz,
    project_to_plan,
)
from src.fem.visualization.specialized_renderers import (
    render_ghost_column_3d,
    render_slab_grid_lines,
    render_slab_mesh,
    render_slabs as render_slabs_detailed,
)

__all__ = [
    "OPSVIS_AVAILABLE",
    "VisualizationBackend",
    "ModelLike",
    "create_plan_view",
    "create_elevation_view",
    "create_3d_view",
    "extract_visualization_data_from_opensees",
    "build_visualization_data_from_fem_model",
    "get_model_statistics",
    "export_plotly_figure_image",
    "_classify_elements",
    "_get_support_symbol",
    "_get_floor_elevations",
    "PLOTLY_AVAILABLE",
    "OPSVIS_AVAILABLE",
    "LEGACY_COLORS",
    "calculate_auto_scale_factor",
    "render_section_forces",
    "render_section_forces_plan",
    "get_floor_elevations",
    "filter_nodes_at_elevation",
    "project_to_plan",
    "project_element_to_plan",
    "project_to_elevation_xz",
    "project_to_elevation_yz",
    "project_element_to_elevation",
    "get_bounding_box_2d",
    "get_bounding_box_3d",
    "calculate_camera_position",
    "COLORS",
    "RenderConfig",
    "classify_elements",
    "render_beams",
    "render_columns",
    "render_core_walls",
    "render_supports",
    "render_nodes",
    "render_loads",
    "render_ghost_columns",
    "render_slabs",
    "render_slab_mesh",
    "render_slab_grid_lines",
    "render_slabs_detailed",
    "render_ghost_column_3d",
]
