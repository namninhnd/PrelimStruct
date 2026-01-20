"""
FEM Engine abstraction layer for OpenSeesPy integration.

This module provides a high-level interface for structural finite element modeling
using OpenSeesPy, tailored for tall building structural analysis with HK Code 2013.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional
import numpy as np


class ElementType(Enum):
    """FEM element types for structural analysis."""
    BEAM_COLUMN = "beam_column"          # Frame element (beams and columns)
    ELASTIC_BEAM = "elastic_beam"        # Elastic beam element
    SHELL = "shell"                      # Shell element (walls, slabs)
    COUPLING_BEAM = "coupling_beam"      # Deep coupling beam


class BoundaryCondition(Enum):
    """Boundary condition types."""
    FREE = 0      # Free to move/rotate
    FIXED = 1     # Fixed (restrained)


class DOF(Enum):
    """Degrees of freedom in 3D structural analysis."""
    UX = 0  # Translation X
    UY = 1  # Translation Y
    UZ = 2  # Translation Z
    RX = 3  # Rotation about X
    RY = 4  # Rotation about Y
    RZ = 5  # Rotation about Z


@dataclass
class Node:
    """FEM node definition.
    
    Attributes:
        tag: Unique node identifier
        x: X-coordinate (m)
        y: Y-coordinate (m)
        z: Z-coordinate (m)
        restraints: Boundary conditions [ux, uy, uz, rx, ry, rz]
                   (1 = fixed, 0 = free)
    """
    tag: int
    x: float
    y: float
    z: float
    restraints: List[int] = field(default_factory=lambda: [0, 0, 0, 0, 0, 0])
    
    def __post_init__(self):
        """Validate node definition."""
        if len(self.restraints) != 6:
            raise ValueError("Restraints must have 6 DOFs [ux, uy, uz, rx, ry, rz]")
        if not all(r in [0, 1] for r in self.restraints):
            raise ValueError("Restraints must be 0 (free) or 1 (fixed)")
    
    @property
    def is_fixed(self) -> bool:
        """Check if node is fully fixed."""
        return all(r == 1 for r in self.restraints)
    
    @property
    def is_pinned(self) -> bool:
        """Check if node is pinned (translations fixed, rotations free)."""
        return (self.restraints[0:3] == [1, 1, 1] and 
                self.restraints[3:6] == [0, 0, 0])


@dataclass
class Element:
    """FEM element definition.
    
    Attributes:
        tag: Unique element identifier
        element_type: Type of element
        node_tags: List of node tags defining element connectivity
        material_tag: Material identifier
        section_tag: Section identifier
        geometry: Additional geometry parameters (dict)
    """
    tag: int
    element_type: ElementType
    node_tags: List[int]
    material_tag: int
    section_tag: Optional[int] = None
    geometry: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate element definition."""
        if len(self.node_tags) < 2:
            raise ValueError("Element must have at least 2 nodes")


@dataclass
class Load:
    """Load definition for FEM analysis.
    
    Attributes:
        node_tag: Node where load is applied
        load_values: Load values [Fx, Fy, Fz, Mx, My, Mz] in N and N·m
        load_pattern: Load pattern identifier
    """
    node_tag: int
    load_values: List[float]
    load_pattern: int = 1
    
    def __post_init__(self):
        """Validate load definition."""
        if len(self.load_values) != 6:
            raise ValueError("Load must have 6 components [Fx, Fy, Fz, Mx, My, Mz]")


@dataclass
class UniformLoad:
    """Uniform distributed load on element.
    
    Attributes:
        element_tag: Element where load is applied
        load_type: Load direction ('X', 'Y', 'Z', or 'Gravity')
        magnitude: Load magnitude (N/m for beams, Pa for shells)
        load_pattern: Load pattern identifier
    """
    element_tag: int
    load_type: str
    magnitude: float
    load_pattern: int = 1


class FEMModel:
    """OpenSeesPy FEM model manager.
    
    This class provides a high-level interface for creating and managing
    OpenSeesPy finite element models for structural analysis.
    
    Attributes:
        nodes: Dictionary of nodes {tag: Node}
        elements: Dictionary of elements {tag: Element}
        loads: List of point loads
        uniform_loads: List of distributed loads
        materials: Dictionary of material parameters
        sections: Dictionary of section parameters
    """
    
    def __init__(self):
        """Initialize empty FEM model."""
        self.nodes: Dict[int, Node] = {}
        self.elements: Dict[int, Element] = {}
        self.loads: List[Load] = []
        self.uniform_loads: List[UniformLoad] = []
        self.materials: Dict[int, Dict] = {}
        self.sections: Dict[int, Dict] = {}
        self._is_built = False
        self._ops_initialized = False
    
    def add_node(self, node: Node) -> None:
        """Add node to model.
        
        Args:
            node: Node object to add
            
        Raises:
            ValueError: If node tag already exists
        """
        if node.tag in self.nodes:
            raise ValueError(f"Node tag {node.tag} already exists")
        self.nodes[node.tag] = node
    
    def add_element(self, element: Element) -> None:
        """Add element to model.
        
        Args:
            element: Element object to add
            
        Raises:
            ValueError: If element tag already exists or nodes don't exist
        """
        if element.tag in self.elements:
            raise ValueError(f"Element tag {element.tag} already exists")
        
        # Check that all nodes exist
        for node_tag in element.node_tags:
            if node_tag not in self.nodes:
                raise ValueError(f"Node {node_tag} does not exist")
        
        self.elements[element.tag] = element
    
    def add_material(self, tag: int, material_params: Dict) -> None:
        """Add material definition to model.
        
        Args:
            tag: Material tag
            material_params: Material parameters from materials.py
        """
        if tag in self.materials:
            raise ValueError(f"Material tag {tag} already exists")
        self.materials[tag] = material_params
    
    def add_section(self, tag: int, section_params: Dict) -> None:
        """Add section definition to model.
        
        Args:
            tag: Section tag
            section_params: Section parameters from materials.py
        """
        if tag in self.sections:
            raise ValueError(f"Section tag {tag} already exists")
        self.sections[tag] = section_params
    
    def add_load(self, load: Load) -> None:
        """Add point load to model.
        
        Args:
            load: Load object to add
        """
        if load.node_tag not in self.nodes:
            raise ValueError(f"Node {load.node_tag} does not exist")
        self.loads.append(load)
    
    def add_uniform_load(self, uniform_load: UniformLoad) -> None:
        """Add distributed load to model.
        
        Args:
            uniform_load: UniformLoad object to add
        """
        if uniform_load.element_tag not in self.elements:
            raise ValueError(f"Element {uniform_load.element_tag} does not exist")
        self.uniform_loads.append(uniform_load)
    
    def build_openseespy_model(self, ndm: int = 3, ndf: int = 6) -> None:
        """Build OpenSeesPy model from definitions.
        
        Args:
            ndm: Number of dimensions (2 or 3)
            ndf: Number of degrees of freedom per node (3 or 6)
            
        Raises:
            ImportError: If openseespy is not installed
        """
        try:
            import openseespy.opensees as ops
        except ImportError:
            raise ImportError(
                "openseespy is not installed. "
                "Install with: pip install openseespy>=3.5.0"
            )
        
        # Wipe existing model
        ops.wipe()
        
        # Create model
        ops.model('basic', '-ndm', ndm, '-ndf', ndf)
        
        # Create nodes
        for node in self.nodes.values():
            if ndm == 2:
                ops.node(node.tag, node.x, node.z)
            else:  # ndm == 3
                ops.node(node.tag, node.x, node.y, node.z)
            
            # Apply boundary conditions
            if any(r == 1 for r in node.restraints):
                ops.fix(node.tag, *node.restraints)
        
        # Create materials
        for tag, params in self.materials.items():
            mat_type = params['material_type']
            if mat_type == 'Concrete01':
                ops.uniaxialMaterial('Concrete01', tag, 
                                    params['fpc'], params['epsc0'],
                                    params['fpcu'], params['epsU'])
            elif mat_type == 'Steel01':
                ops.uniaxialMaterial('Steel01', tag,
                                    params['fy'], params['E0'], params['b'])
        
        # Create sections
        for tag, params in self.sections.items():
            sec_type = params['section_type']
            if sec_type == 'ElasticBeamSection':
                if ndm == 3:
                    # 3D elastic section
                    ops.section('Elastic', tag, params['E'], params['A'],
                               params['Iz'], params['Iy'], params['G'], params['J'])
                else:
                    # 2D elastic section
                    ops.section('Elastic', tag, params['E'], params['A'], params['Iz'])
        
        # Create elements
        for elem in self.elements.values():
            if elem.element_type == ElementType.ELASTIC_BEAM:
                # Elastic beam-column element
                if elem.section_tag is None:
                    raise ValueError(f"Element {elem.tag} missing section_tag")
                
                # Geometric transformation (1 = Linear, 2 = P-Delta, 3 = Corotational)
                geom_transf = elem.geometry.get('geom_transf', 1)
                
                if ndm == 3:
                    # Need to define geometric transformation for 3D
                    # Using Linear transformation by default
                    ops.geomTransf('Linear', elem.tag, 0, 0, 1)  # vertical axis
                    ops.element('elasticBeamColumn', elem.tag,
                               *elem.node_tags, elem.section_tag, elem.tag)
                else:
                    ops.geomTransf('Linear', elem.tag)
                    ops.element('elasticBeamColumn', elem.tag,
                               *elem.node_tags, elem.section_tag, elem.tag)
        
        self._is_built = True
        self._ops_initialized = True
    
    def get_node_coordinates(self) -> np.ndarray:
        """Get all node coordinates as numpy array.
        
        Returns:
            Array of shape (n_nodes, 3) with [x, y, z] coordinates
        """
        coords = []
        for node in sorted(self.nodes.values(), key=lambda n: n.tag):
            coords.append([node.x, node.y, node.z])
        return np.array(coords)
    
    def get_element_connectivity(self) -> List[Tuple[int, ...]]:
        """Get element connectivity as list of node tag tuples.
        
        Returns:
            List of tuples, each containing node tags for an element
        """
        connectivity = []
        for elem in sorted(self.elements.values(), key=lambda e: e.tag):
            connectivity.append(tuple(elem.node_tags))
        return connectivity
    
    def get_fixed_nodes(self) -> List[int]:
        """Get list of fully fixed node tags.
        
        Returns:
            List of node tags that are fully fixed
        """
        return [node.tag for node in self.nodes.values() if node.is_fixed]
    
    def get_summary(self) -> Dict:
        """Get model summary statistics.
        
        Returns:
            Dictionary with model statistics
        """
        return {
            'n_nodes': len(self.nodes),
            'n_elements': len(self.elements),
            'n_materials': len(self.materials),
            'n_sections': len(self.sections),
            'n_loads': len(self.loads),
            'n_uniform_loads': len(self.uniform_loads),
            'n_fixed_nodes': len(self.get_fixed_nodes()),
            'is_built': self._is_built,
        }
    
    def validate_model(self) -> Tuple[bool, List[str]]:
        """Validate model for common issues.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check for nodes
        if not self.nodes:
            errors.append("Model has no nodes")
        
        # Check for elements
        if not self.elements:
            errors.append("Model has no elements")
        
        # Check for boundary conditions
        if not any(node.is_fixed or node.is_pinned for node in self.nodes.values()):
            errors.append("Model has no fixed or pinned supports (unstable)")
        
        # Check material references
        for elem in self.elements.values():
            if elem.material_tag not in self.materials:
                errors.append(
                    f"Element {elem.tag} references non-existent material {elem.material_tag}"
                )
        
        # Check section references for beam elements
        for elem in self.elements.values():
            if elem.element_type in [ElementType.BEAM_COLUMN, ElementType.ELASTIC_BEAM]:
                if elem.section_tag is None:
                    errors.append(f"Beam element {elem.tag} missing section_tag")
                elif elem.section_tag not in self.sections:
                    errors.append(
                        f"Element {elem.tag} references non-existent section {elem.section_tag}"
                    )
        
        return (len(errors) == 0, errors)


def create_simple_frame_model(bay_width: float,
                              bay_height: float,
                              n_bays: int,
                              n_stories: int,
                              concrete_grade,
                              beam_width: float,
                              beam_height: float,
                              column_width: float,
                              column_height: float) -> FEMModel:
    """Create a simple 2D frame model for testing.
    
    Args:
        bay_width: Width of each bay (m)
        bay_height: Height of each story (m)
        n_bays: Number of bays
        n_stories: Number of stories
        concrete_grade: ConcreteGrade enum value
        beam_width: Beam width (mm)
        beam_height: Beam depth (mm)
        column_width: Column width (mm)
        column_height: Column depth (mm)
    
    Returns:
        FEMModel with frame elements and fixed base
    """
    from src.fem.materials import (
        create_concrete_material,
        get_openseespy_concrete_material,
        get_elastic_beam_section,
        get_next_material_tag,
        get_next_section_tag,
    )
    
    model = FEMModel()
    
    # Create material
    concrete = create_concrete_material(concrete_grade)
    mat_tag = get_next_material_tag()
    mat_params = get_openseespy_concrete_material(concrete, mat_tag)
    model.add_material(mat_tag, mat_params)
    
    # Create sections
    beam_section_tag = get_next_section_tag()
    beam_section = get_elastic_beam_section(concrete, beam_width, beam_height, 
                                            beam_section_tag)
    model.add_section(beam_section_tag, beam_section)
    
    col_section_tag = get_next_section_tag()
    col_section = get_elastic_beam_section(concrete, column_width, column_height,
                                           col_section_tag)
    model.add_section(col_section_tag, col_section)
    
    # Create nodes
    node_tag = 1
    node_map = {}  # (x_index, y_index) -> node_tag
    
    for story in range(n_stories + 1):
        z = story * bay_height
        for bay in range(n_bays + 1):
            x = bay * bay_width
            
            # Fixed base
            if story == 0:
                restraints = [1, 1, 1, 1, 1, 1]  # Fully fixed
            else:
                restraints = [0, 0, 0, 0, 0, 0]  # Free
            
            node = Node(tag=node_tag, x=x, y=0, z=z, restraints=restraints)
            model.add_node(node)
            node_map[(bay, story)] = node_tag
            node_tag += 1
    
    # Create column elements
    elem_tag = 1
    for story in range(n_stories):
        for bay in range(n_bays + 1):
            node_i = node_map[(bay, story)]
            node_j = node_map[(bay, story + 1)]
            elem = Element(
                tag=elem_tag,
                element_type=ElementType.ELASTIC_BEAM,
                node_tags=[node_i, node_j],
                material_tag=mat_tag,
                section_tag=col_section_tag,
            )
            model.add_element(elem)
            elem_tag += 1
    
    # Create beam elements
    for story in range(1, n_stories + 1):
        for bay in range(n_bays):
            node_i = node_map[(bay, story)]
            node_j = node_map[(bay + 1, story)]
            elem = Element(
                tag=elem_tag,
                element_type=ElementType.ELASTIC_BEAM,
                node_tags=[node_i, node_j],
                material_tag=mat_tag,
                section_tag=beam_section_tag,
            )
            model.add_element(elem)
            elem_tag += 1
    
    return model
