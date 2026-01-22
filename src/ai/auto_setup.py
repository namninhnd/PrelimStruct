"""
Smart Model Setup for PrelimStruct FEM Analysis.

This module provides automated model setup with intelligent boundary
condition inference, support detection, and AI-powered recommendations.

Usage:
    from src.ai.auto_setup import ModelSetup, BoundaryCondition
    
    setup = ModelSetup.from_project_data(project_data)
    boundary_conditions = setup.infer_boundary_conditions()
    supports = setup.detect_support_locations()
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SupportType(Enum):
    """Types of structural supports."""
    FIXED = "fixed"        # All DOFs constrained
    PINNED = "pinned"      # Translations constrained, rotations free
    ROLLER = "roller"      # Vertical translation constrained only
    SPRING = "spring"      # Elastic support


class LoadType(Enum):
    """Types of loads for FEM analysis."""
    DEAD = "dead"
    LIVE = "live"
    WIND = "wind"
    SEISMIC = "seismic"
    SNOW = "snow"


@dataclass
class BoundaryCondition:
    """Boundary condition specification.
    
    Attributes:
        node_id: Node ID or coordinates
        support_type: Type of support
        dof_constraints: List of constrained DOFs (1=Fx, 2=Fy, 3=Fz, 4=Mx, 5=My, 6=Mz)
        location: (x, y, z) coordinates
        description: Human-readable description
    """
    node_id: int
    support_type: SupportType
    dof_constraints: List[int]
    location: Tuple[float, float, float]
    description: str = ""
    
    @classmethod
    def create_fixed(cls, node_id: int, location: Tuple[float, float, float]) -> "BoundaryCondition":
        """Create fixed support (all DOFs constrained)."""
        return cls(
            node_id=node_id,
            support_type=SupportType.FIXED,
            dof_constraints=[1, 2, 3, 4, 5, 6],
            location=location,
            description="Fixed support at base",
        )
    
    @classmethod
    def create_pinned(cls, node_id: int, location: Tuple[float, float, float]) -> "BoundaryCondition":
        """Create pinned support (translations constrained)."""
        return cls(
            node_id=node_id,
            support_type=SupportType.PINNED,
            dof_constraints=[1, 2, 3],  # Fx, Fy, Fz only
            location=location,
            description="Pinned support at base",
        )


@dataclass
class LoadCase:
    """Load case specification.
    
    Attributes:
        name: Load case name
        load_type: Type of load
        nodes: List of node IDs to apply load
        forces: List of (Fx, Fy, Fz, Mx, My, Mz) force vectors
        description: Human-readable description
    """
    name: str
    load_type: LoadType
    nodes: List[int]
    forces: List[Tuple[float, float, float, float, float, float]]
    description: str = ""


@dataclass
class ModelSetupConfig:
    """Configuration for automated model setup.
    
    Attributes:
        base_elevation: Elevation of structural base (mm)
        support_type_default: Default support type for base supports
        auto_detect_supports: Automatically detect support locations
        include_self_weight: Include self-weight in dead load
        load_combinations_hk2013: Use HK Code 2013 load combinations
    """
    base_elevation: float = 0.0
    support_type_default: SupportType = SupportType.FIXED
    auto_detect_supports: bool = True
    include_self_weight: bool = True
    load_combinations_hk2013: bool = True


class ModelSetup:
    """Smart model setup with automated boundary conditions and load detection.
    
    This class provides intelligent model setup features including:
    - Automatic support detection at column/wall bases
    - Boundary condition inference from structural type
    - Load application point detection
    - Material property assignment
    - Load combination generation
    
    Usage:
        setup = ModelSetup(config)
        supports = setup.detect_column_base_supports(column_locations)
        bcs = setup.create_boundary_conditions(supports)
    """
    
    def __init__(self, config: ModelSetupConfig):
        """Initialize model setup.
        
        Args:
            config: Model setup configuration
        """
        self.config = config
        self._support_locations: List[Tuple[float, float, float]] = []
        self._boundary_conditions: List[BoundaryCondition] = []
    
    @classmethod
    def from_project_data(cls, project_data: Dict[str, Any]) -> "ModelSetup":
        """Create model setup from project data.
        
        Args:
            project_data: Project data dictionary
            
        Returns:
            Initialized ModelSetup instance
        """
        config = ModelSetupConfig(
            base_elevation=project_data.get("base_elevation", 0.0),
        )
        return cls(config)
    
    def detect_column_base_supports(
        self,
        column_locations: List[Tuple[float, float]],
        base_elevation: Optional[float] = None,
    ) -> List[Tuple[float, float, float]]:
        """Detect support locations at column bases.
        
        Args:
            column_locations: List of (x, y) column grid locations
            base_elevation: Base elevation (defaults to config value)
            
        Returns:
            List of (x, y, z) support locations
        """
        z = base_elevation if base_elevation is not None else self.config.base_elevation
        
        supports = [(x, y, z) for x, y in column_locations]
        self._support_locations = supports
        
        logger.info(f"Detected {len(supports)} column base supports at z={z}mm")
        return supports
    
    def detect_core_wall_supports(
        self,
        core_wall_vertices: List[Tuple[float, float]],
        base_elevation: Optional[float] = None,
    ) -> List[Tuple[float, float, float]]:
        """Detect support locations at core wall base.
        
        Args:
            core_wall_vertices: List of (x, y) vertices of core wall outline
            base_elevation: Base elevation
            
        Returns:
            List of (x, y, z) support locations along wall base
        """
        z = base_elevation if base_elevation is not None else self.config.base_elevation
        
        supports = [(x, y, z) for x, y in core_wall_vertices]
        
        logger.info(f"Detected {len(supports)} core wall base supports")
        return supports
    
    def create_boundary_conditions(
        self,
        support_locations: List[Tuple[float, float, float]],
        support_type: Optional[SupportType] = None,
    ) -> List[BoundaryCondition]:
        """Create boundary conditions for support locations.
        
        Args:
            support_locations: List of (x, y, z) coordinates
            support_type: Type of support (defaults to config value)
            
        Returns:
            List of BoundaryCondition objects
        """
        support_type = support_type or self.config.support_type_default
        
        boundary_conditions = []
        for i, location in enumerate(support_locations):
            if support_type == SupportType.FIXED:
                bc = BoundaryCondition.create_fixed(node_id=i, location=location)
            elif support_type == SupportType.PINNED:
                bc = BoundaryCondition.create_pinned(node_id=i, location=location)
            else:
                # Default to fixed
                bc = BoundaryCondition.create_fixed(node_id=i, location=location)
            
            boundary_conditions.append(bc)
        
        self._boundary_conditions = boundary_conditions
        logger.info(f"Created {len(boundary_conditions)} boundary conditions")
        
        return boundary_conditions
    
    def infer_load_application_points(
        self,
        floor_levels: List[float],
        column_locations: List[Tuple[float, float]],
    ) -> Dict[str, List[Tuple[float, float, float]]]:
        """Infer load application points from geometry.
        
        Args:
            floor_levels: List of floor elevations
            column_locations: List of (x, y) column locations
            
        Returns:
            Dictionary mapping load type to list of application points
        """
        # Gravity loads applied at all floor-column intersections
        gravity_points = []
        for z in floor_levels:
            for x, y in column_locations:
                gravity_points.append((x, y, z))
        
        # Lateral loads applied at floor diaphragm centers
        lateral_points = []
        if column_locations:
            # Calculate centroid of floor plan
            cx = sum(x for x, y in column_locations) / len(column_locations)
            cy = sum(y for x, y in column_locations) / len(column_locations)
            
            for z in floor_levels:
                lateral_points.append((cx, cy, z))
        
        return {
            "gravity": gravity_points,
            "lateral": lateral_points,
        }
    
    def generate_hk2013_load_combinations(self) -> List[Dict[str, Any]]:
        """Generate HK Code 2013 load combinations.
        
        Returns:
            List of load combination specifications
        """
        # HK Code 2013 load combinations
        combinations = [
            {
                "name": "ULS1",
                "description": "1.4Gk + 1.6Qk (gravity dominant)",
                "factors": {"dead": 1.4, "live": 1.6, "wind": 0.0, "seismic": 0.0},
            },
            {
                "name": "ULS2",
                "description": "1.0Gk + 1.4Wk (wind dominant)",
                "factors": {"dead": 1.0, "live": 0.0, "wind": 1.4, "seismic": 0.0},
            },
            {
                "name": "ULS3",
                "description": "1.2Gk + 1.2Qk + 1.2Wk (combined)",
                "factors": {"dead": 1.2, "live": 1.2, "wind": 1.2, "seismic": 0.0},
            },
            {
                "name": "ULS4",
                "description": "1.4Gk + 1.6Qk + 0.6Wk (gravity + wind)",
                "factors": {"dead": 1.4, "live": 1.6, "wind": 0.6, "seismic": 0.0},
            },
            {
                "name": "SLS1",
                "description": "1.0Gk + 1.0Qk (serviceability)",
                "factors": {"dead": 1.0, "live": 1.0, "wind": 0.0, "seismic": 0.0},
            },
        ]
        
        logger.info(f"Generated {len(combinations)} HK Code 2013 load combinations")
        return combinations
    
    def validate_model_setup(self) -> Dict[str, Any]:
        """Validate model setup before analysis.
        
        Returns:
            Validation results with warnings and errors
        """
        errors = []
        warnings = []
        
        # Check if supports are defined
        if not self._boundary_conditions:
            errors.append("No boundary conditions defined")
        
        # Check if supports are at base elevation
        for bc in self._boundary_conditions:
            if abs(bc.location[2] - self.config.base_elevation) > 100:  # 100mm tolerance
                warnings.append(
                    f"Support at {bc.location} is not at base elevation {self.config.base_elevation}"
                )
        
        # Check for duplicate support locations
        locations = [bc.location for bc in self._boundary_conditions]
        if len(locations) != len(set(locations)):
            warnings.append("Duplicate support locations detected")
        
        is_valid = len(errors) == 0
        
        return {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "num_supports": len(self._boundary_conditions),
            "support_type": self.config.support_type_default.value,
        }
    
    def get_setup_summary(self) -> str:
        """Get human-readable setup summary.
        
        Returns:
            Summary string
        """
        summary_lines = [
            "FEM Model Setup Summary",
            "=" * 50,
            f"Base Elevation: {self.config.base_elevation} mm",
            f"Support Type: {self.config.support_type_default.value}",
            f"Number of Supports: {len(self._boundary_conditions)}",
            f"Auto-detect Supports: {self.config.auto_detect_supports}",
            f"Include Self-Weight: {self.config.include_self_weight}",
            f"HK2013 Load Combinations: {self.config.load_combinations_hk2013}",
        ]
        
        return "\n".join(summary_lines)
