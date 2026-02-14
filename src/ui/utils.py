"""Utility functions for PrelimStruct dashboard."""

from typing import Tuple, List

from src.core.data_models import ProjectData
from src.core.constants import CARBON_FACTORS
from src.fem.beam_trimmer import BeamGeometry


def format_column_size_mm(project: ProjectData) -> str:
    column_result = project.column_result
    if column_result is None:
        return "N/A"

    width = int(column_result.width) if column_result.width > 0 else 0
    depth = int(column_result.depth) if column_result.depth > 0 else 0
    dimension = int(column_result.dimension) if column_result.dimension > 0 else 0

    if width == 0 and depth == 0:
        if dimension == 0:
            return "N/A"
        width = dimension
        depth = dimension
    else:
        if width == 0:
            width = dimension if dimension > 0 else depth
        if depth == 0:
            depth = dimension if dimension > 0 else width

    return f"{width} x {depth} mm"


def get_status_badge(status: str, utilization: float = 0.0) -> str:
    """Generate HTML status badge based on status and utilization."""
    if status == "FAIL" or utilization > 1.0:
        return '<span class="status-fail">FAIL</span>'
    elif status == "WARNING" or utilization > 0.85:
        return '<span class="status-warning">WARN</span>'
    elif status == "PENDING":
        return '<span class="status-pending">--</span>'
    else:
        return '<span class="status-pass">OK</span>'


def calculate_carbon_emission(project: ProjectData) -> Tuple[float, float]:
    """Calculate concrete volume and carbon emission.
    
    Args:
        project: ProjectData with geometry and results
        
    Returns:
        Tuple of (total_volume_m3, carbon_emission_kg)
    """
    # Estimate concrete volumes (simplified)
    floor_area = project.geometry.bay_x * project.geometry.bay_y
    floors = project.geometry.floors

    # Slab volume
    slab_thickness = 0.2  # default 200mm
    if project.slab_result:
        slab_thickness = project.slab_result.thickness / 1000
    slab_volume = floor_area * slab_thickness * floors

    # Beam volumes (approximate)
    beam_depth = 0.5
    beam_width = 0.3
    if project.primary_beam_result:
        beam_depth = project.primary_beam_result.depth / 1000
        beam_width = project.primary_beam_result.width / 1000

    # Primary beams (along X direction)
    primary_beam_length = project.geometry.bay_x
    primary_beam_volume = beam_width * beam_depth * primary_beam_length * floors

    # Secondary beams (along Y direction)
    secondary_beam_volume = beam_width * beam_depth * project.geometry.bay_y * floors

    # Column volume
    col_width = 0.4  # default 400mm
    col_depth = 0.4
    if project.column_result:
        if project.column_result.width > 0:
            col_width = project.column_result.width / 1000
        if project.column_result.depth > 0:
            col_depth = project.column_result.depth / 1000
        if project.column_result.dimension > 0:
            col_width = max(col_width, project.column_result.dimension / 1000)
            col_depth = max(col_depth, project.column_result.dimension / 1000)
    col_height = project.geometry.story_height * floors
    col_volume = col_width * col_depth * col_height

    # Total volume
    total_volume = slab_volume + primary_beam_volume + secondary_beam_volume + col_volume

    # Carbon emission (weighted average of grades)
    avg_fcu = (project.materials.fcu_slab + project.materials.fcu_beam + project.materials.fcu_column) / 3
    carbon_factor = CARBON_FACTORS.get(int(avg_fcu), 340)  # default to C40 factor
    carbon_emission = total_volume * carbon_factor

    return total_volume, carbon_emission


def create_beam_geometries_from_project(
    project: ProjectData, 
    core_offset_x: float, 
    core_offset_y: float
) -> List[BeamGeometry]:
    """Create BeamGeometry objects from project framing layout.

    Args:
        project: ProjectData with geometry configuration
        core_offset_x: Core wall X offset in meters
        core_offset_y: Core wall Y offset in meters

    Returns:
        List of BeamGeometry objects representing all beams in plan
    """
    bay_x = project.geometry.bay_x
    bay_y = project.geometry.bay_y
    num_bays_x = project.geometry.num_bays_x
    num_bays_y = project.geometry.num_bays_y
    total_x = bay_x * num_bays_x
    total_y = bay_y * num_bays_y

    beams = []

    # Horizontal beams (along X direction)
    for iy in range(num_bays_y + 1):
        y_pos = iy * bay_y * 1000  # Convert to mm
        beam = BeamGeometry(
            start_x=0,
            start_y=y_pos,
            end_x=total_x * 1000,
            end_y=y_pos,
            width=300.0,
            beam_id=f"H{iy}"
        )
        beams.append(beam)

    # Vertical beams (along Y direction)
    for ix in range(num_bays_x + 1):
        x_pos = ix * bay_x * 1000  # Convert to mm
        beam = BeamGeometry(
            start_x=x_pos,
            start_y=0,
            end_x=x_pos,
            end_y=total_y * 1000,
            width=300.0,
            beam_id=f"V{ix}"
        )
        beams.append(beam)

    return beams
