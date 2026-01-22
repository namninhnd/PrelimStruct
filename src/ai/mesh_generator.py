"""
Automated Mesh Generation for PrelimStruct FEM Analysis.

This module provides rule-based mesh generation with automatic element sizing,
quality checks, and refinement strategies for tall building structures.

Usage:
    from src.ai.mesh_generator import MeshGenerator, MeshConfig
    
    config = MeshConfig.from_geometry(project_data)
    generator = MeshGenerator(config)
    mesh = generator.generate_mesh()
    
    if mesh.is_valid():
        print(f"Generated {mesh.num_elements} elements")
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from enum import Enum
import logging
import math

logger = logging.getLogger(__name__)


class MeshDensity(Enum):
    """Mesh density levels for different analysis requirements."""
    COARSE = "coarse"      # Fast preliminary analysis
    MEDIUM = "medium"      # Standard analysis
    FINE = "fine"          # Detailed analysis
    VERY_FINE = "very_fine"  # High-accuracy analysis


class ElementType(Enum):
    """FEM element types supported."""
    BEAM = "beam"
    COLUMN = "column"
    WALL = "wall"
    SLAB = "slab"


@dataclass
class MeshQuality:
    """Mesh quality metrics.
    
    Attributes:
        aspect_ratio_max: Maximum aspect ratio (should be < 10)
        aspect_ratio_avg: Average aspect ratio
        skewness_max: Maximum skewness (should be < 0.85)
        skewness_avg: Average skewness
        num_poor_elements: Number of poor quality elements
        is_valid: Overall mesh validity
    """
    aspect_ratio_max: float
    aspect_ratio_avg: float
    skewness_max: float
    skewness_avg: float
    num_poor_elements: int
    is_valid: bool = True
    
    def __post_init__(self):
        """Validate mesh quality."""
        # Aspect ratio should be < 10 for good quality
        if self.aspect_ratio_max > 10:
            self.is_valid = False
            logger.warning(f"Max aspect ratio {self.aspect_ratio_max:.2f} exceeds 10")
        
        # Skewness should be < 0.85 for good quality
        if self.skewness_max > 0.85:
            self.is_valid = False
            logger.warning(f"Max skewness {self.skewness_max:.3f} exceeds 0.85")


@dataclass
class MeshConfig:
    """Configuration for mesh generation.
    
    Attributes:
        density: Overall mesh density level
        beam_element_size: Maximum beam element length (mm)
        column_element_size: Maximum column element length (mm)
        wall_element_size: Maximum wall element size (mm)
        refinement_zones: List of (x, y, z, radius) tuples for local refinement
        max_aspect_ratio: Maximum allowed aspect ratio
        target_aspect_ratio: Target aspect ratio for good quality
    """
    density: MeshDensity = MeshDensity.MEDIUM
    beam_element_size: float = 1000.0  # mm
    column_element_size: float = 3000.0  # mm (floor-to-floor height)
    wall_element_size: float = 1000.0  # mm
    refinement_zones: List[Tuple[float, float, float, float]] = field(default_factory=list)
    max_aspect_ratio: float = 10.0
    target_aspect_ratio: float = 3.0
    
    @classmethod
    def from_geometry(
        cls,
        typical_beam_span: float,
        floor_height: float,
        density: MeshDensity = MeshDensity.MEDIUM,
    ) -> "MeshConfig":
        """Create mesh config from geometry parameters.
        
        Args:
            typical_beam_span: Typical beam span in mm
            floor_height: Floor-to-floor height in mm
            density: Mesh density level
            
        Returns:
            MeshConfig with appropriate element sizes
        """
        # Element sizing based on density and geometry
        density_factors = {
            MeshDensity.COARSE: 0.25,      # 4 elements per span
            MeshDensity.MEDIUM: 0.125,     # 8 elements per span
            MeshDensity.FINE: 0.0625,      # 16 elements per span
            MeshDensity.VERY_FINE: 0.03125  # 32 elements per span
        }
        
        factor = density_factors[density]
        
        return cls(
            density=density,
            beam_element_size=typical_beam_span * factor,
            column_element_size=floor_height,  # One element per floor
            wall_element_size=floor_height * factor,
        )


@dataclass
class MeshElement:
    """A single mesh element.
    
    Attributes:
        id: Element ID
        element_type: Type of element (beam, column, wall, slab)
        nodes: List of node IDs
        length: Element length (for 1D elements)
        area: Element area (for 2D elements)
        aspect_ratio: Length/width ratio
    """
    id: int
    element_type: ElementType
    nodes: List[int]
    length: Optional[float] = None
    area: Optional[float] = None
    aspect_ratio: float = 1.0


@dataclass
class Mesh:
    """Complete FEM mesh.
    
    Attributes:
        nodes: List of (x, y, z) node coordinates
        elements: List of MeshElement objects
        quality: Mesh quality metrics
        metadata: Additional mesh information
    """
    nodes: List[Tuple[float, float, float]]
    elements: List[MeshElement]
    quality: Optional[MeshQuality] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def num_nodes(self) -> int:
        """Number of nodes in mesh."""
        return len(self.nodes)
    
    @property
    def num_elements(self) -> int:
        """Number of elements in mesh."""
        return len(self.elements)
    
    def is_valid(self) -> bool:
        """Check if mesh is valid for analysis."""
        if self.quality is None:
            return False
        return self.quality.is_valid


class MeshGenerator:
    """Rule-based mesh generator for structural FEM analysis.
    
    This generator creates finite element meshes from structural geometry
    with automatic element sizing, quality checks, and refinement.
    
    Usage:
        config = MeshConfig.from_geometry(9000, 3000, MeshDensity.MEDIUM)
        generator = MeshGenerator(config)
        mesh = generator.generate_beam_mesh(start, end, section_depth)
    """
    
    def __init__(self, config: MeshConfig):
        """Initialize mesh generator.
        
        Args:
            config: Mesh generation configuration
        """
        self.config = config
        self._node_counter = 0
        self._element_counter = 0
    
    def generate_beam_mesh(
        self,
        start_point: Tuple[float, float, float],
        end_point: Tuple[float, float, float],
        section_depth: float,
    ) -> Mesh:
        """Generate mesh for a beam element.
        
        Args:
            start_point: (x, y, z) coordinates of beam start
            end_point: (x, y, z) coordinates of beam end
            section_depth: Beam depth for aspect ratio calculation
            
        Returns:
            Mesh with beam elements
        """
        # Calculate beam length
        dx = end_point[0] - start_point[0]
        dy = end_point[1] - start_point[1]
        dz = end_point[2] - start_point[2]
        length = math.sqrt(dx**2 + dy**2 + dz**2)
        
        # Determine number of elements based on config
        num_elements = max(1, int(length / self.config.beam_element_size))
        
        # Generate nodes along beam
        nodes = []
        for i in range(num_elements + 1):
            t = i / num_elements
            x = start_point[0] + t * dx
            y = start_point[1] + t * dy
            z = start_point[2] + t * dz
            nodes.append((x, y, z))
        
        # Generate elements
        elements = []
        for i in range(num_elements):
            element_length = length / num_elements
            aspect_ratio = element_length / section_depth if section_depth > 0 else 1.0
            
            element = MeshElement(
                id=self._element_counter,
                element_type=ElementType.BEAM,
                nodes=[self._node_counter + i, self._node_counter + i + 1],
                length=element_length,
                aspect_ratio=aspect_ratio,
            )
            elements.append(element)
            self._element_counter += 1
        
        self._node_counter += len(nodes)
        
        # Calculate mesh quality
        aspect_ratios = [e.aspect_ratio for e in elements]
        quality = MeshQuality(
            aspect_ratio_max=max(aspect_ratios),
            aspect_ratio_avg=sum(aspect_ratios) / len(aspect_ratios),
            skewness_max=0.0,  # Beams are 1D, no skewness
            skewness_avg=0.0,
            num_poor_elements=sum(1 for ar in aspect_ratios if ar > self.config.max_aspect_ratio),
        )
        
        return Mesh(
            nodes=nodes,
            elements=elements,
            quality=quality,
            metadata={
                "element_type": "beam",
                "length": length,
                "num_elements": num_elements,
            }
        )
    
    def generate_column_mesh(
        self,
        base_point: Tuple[float, float, float],
        height: float,
        section_size: float,
    ) -> Mesh:
        """Generate mesh for a column element.
        
        Args:
            base_point: (x, y, z) coordinates of column base
            height: Column height
            section_size: Column section dimension for aspect ratio
            
        Returns:
            Mesh with column elements
        """
        # Determine number of elements (typically one per floor)
        num_elements = max(1, int(height / self.config.column_element_size))
        
        # Generate nodes along column height
        nodes = []
        for i in range(num_elements + 1):
            z = base_point[2] + (i / num_elements) * height
            nodes.append((base_point[0], base_point[1], z))
        
        # Generate elements
        elements = []
        for i in range(num_elements):
            element_height = height / num_elements
            aspect_ratio = element_height / section_size if section_size > 0 else 1.0
            
            element = MeshElement(
                id=self._element_counter,
                element_type=ElementType.COLUMN,
                nodes=[self._node_counter + i, self._node_counter + i + 1],
                length=element_height,
                aspect_ratio=aspect_ratio,
            )
            elements.append(element)
            self._element_counter += 1
        
        self._node_counter += len(nodes)
        
        # Calculate quality
        aspect_ratios = [e.aspect_ratio for e in elements]
        quality = MeshQuality(
            aspect_ratio_max=max(aspect_ratios),
            aspect_ratio_avg=sum(aspect_ratios) / len(aspect_ratios),
            skewness_max=0.0,
            skewness_avg=0.0,
            num_poor_elements=sum(1 for ar in aspect_ratios if ar > self.config.max_aspect_ratio),
        )
        
        return Mesh(
            nodes=nodes,
            elements=elements,
            quality=quality,
            metadata={
                "element_type": "column",
                "height": height,
                "num_elements": num_elements,
            }
        )
    
    def check_refinement_needed(
        self,
        point: Tuple[float, float, float],
    ) -> bool:
        """Check if point is in a refinement zone.
        
        Args:
            point: (x, y, z) coordinates
            
        Returns:
            True if point needs refinement
        """
        for zone_x, zone_y, zone_z, radius in self.config.refinement_zones:
            distance = math.sqrt(
                (point[0] - zone_x)**2 +
                (point[1] - zone_y)**2 +
                (point[2] - zone_z)**2
            )
            if distance <= radius:
                return True
        return False
    
    def reset_counters(self):
        """Reset node and element counters for new mesh generation."""
        self._node_counter = 0
        self._element_counter = 0
