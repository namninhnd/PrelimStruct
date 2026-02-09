"""
FEM Engine abstraction layer for OpenSeesPy integration.

This module provides a high-level interface for structural finite element modeling
using OpenSeesPy, tailored for tall building structural analysis with HK Code 2013.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional
import numpy as np

_logger = logging.getLogger(__name__)


class ElementType(Enum):
    """FEM element types for structural analysis."""
    BEAM_COLUMN = "beam_column"          # Frame element (beams and columns)
    ELASTIC_BEAM = "elastic_beam"        # Elastic beam element
    SECONDARY_BEAM = "secondary_beam"    # Secondary beam element
    SHELL = "shell"                      # Shell element (walls, slabs) - legacy
    SHELL_MITC4 = "shell_mitc4"          # ShellMITC4 4-node quad shell element
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
        visual_only: If True, used for visualization only (not applied in analysis)
    """
    element_tag: int
    load_type: str
    magnitude: float
    load_pattern: int = 1
    visual_only: bool = False


@dataclass
class SurfaceLoad:
    """Surface pressure load on shell/slab elements.
    
    Attributes:
        element_tag: Shell element where load is applied
        pressure: Load magnitude in Pa (N/m²) - positive = downward
        load_pattern: Load pattern identifier
    """
    element_tag: int
    pressure: float  # Pa (N/m²)
    load_pattern: int = 1


@dataclass
class RigidDiaphragm:
    """Rigid diaphragm constraint tying slave nodes to a master node.
    
    Attributes:
        master_node: Master node tag for in-plane constraint
        slave_nodes: Slave node tags constrained to the master in plan
        perp_dirn: Perpendicular axis (OpenSeesPy uses 3 for XY plane)
    """
    master_node: int
    slave_nodes: List[int]
    perp_dirn: int = 3

    def __post_init__(self):
        if not self.slave_nodes:
            raise ValueError("RigidDiaphragm must have at least one slave node")
        if self.master_node in self.slave_nodes:
            raise ValueError("Master node cannot also be a slave node in the diaphragm")


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
        self.surface_loads: List[SurfaceLoad] = []
        self.materials: Dict[int, Dict] = {}
        self.sections: Dict[int, Dict] = {}
        self.diaphragms: List[RigidDiaphragm] = []
        self.omitted_columns: List[Dict] = []  # Ghost columns for visualization: [{"x": float, "y": float, "id": str}]
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
    
    def add_surface_load(self, surface_load: SurfaceLoad) -> None:
        """Add surface pressure load to model.
        
        Args:
            surface_load: SurfaceLoad object to add
        """
        if surface_load.element_tag not in self.elements:
            raise ValueError(f"Element {surface_load.element_tag} does not exist")
        self.surface_loads.append(surface_load)

    def add_rigid_diaphragm(self, diaphragm: RigidDiaphragm) -> None:
        """Add rigid diaphragm tying slave nodes to a master node.

        Args:
            diaphragm: RigidDiaphragm definition

        Raises:
            ValueError: If nodes do not exist in the model
        """
        if diaphragm.master_node not in self.nodes:
            raise ValueError(f"Master node {diaphragm.master_node} does not exist")
        for slave in diaphragm.slave_nodes:
            if slave not in self.nodes:
                raise ValueError(f"Slave node {slave} does not exist")
        self.diaphragms.append(diaphragm)

    @staticmethod
    def _get_uniform_load_components(uniform_load: UniformLoad,
                                     ndm: int) -> Tuple[float, float]:
        """Map uniform load to local y/z components for OpenSeesPy.

        Args:
            uniform_load: Load definition
            ndm: Number of model dimensions

        Returns:
            Tuple (wy, wz) to be passed to OpenSeesPy `eleLoad`.
        """
        wy = 0.0
        wz = 0.0
        load_type = uniform_load.load_type.lower()

        if load_type == "gravity":
            # Gravity = force in -local_y direction.
            # With ETABS vecxz convention, local_y is vertical for horizontal beams.
            wy = -uniform_load.magnitude
        elif load_type == "y":
            wy = uniform_load.magnitude
        elif load_type == "z":
            wz = uniform_load.magnitude
        else:
            raise ValueError(
                f"Unsupported uniform load type '{uniform_load.load_type}'. "
                "Use 'Gravity', 'Y', or 'Z'."
            )

        return wy, wz
    
    def build_openseespy_model(
        self, ndm: int = 3, ndf: int = 6, active_pattern: Optional[int] = None
    ) -> None:
        """Build OpenSeesPy model from definitions.
        
        Args:
            ndm: Number of dimensions (2 or 3)
            ndf: Number of degrees of freedom per node (3 or 6)
            active_pattern: If specified, only apply loads with this pattern ID.
                           If None, apply all load patterns.
            
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
            elif mat_type == 'ElasticIsotropic':
                # NDMaterial for shell elements (PlaneStress)
                ops.nDMaterial('ElasticIsotropic', tag,
                              params['E'], params['nu'], params['rho'])
        
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
            elif sec_type == 'PlateFiber':
                # PlateFiberSection for ShellMITC4 elements
                ops.section('PlateFiber', tag, params['matTag'], params['h'])
            elif sec_type == 'ElasticMembranePlateSection':
                # ElasticMembranePlateSection for slab shell elements
                ops.section('ElasticMembranePlateSection', tag,
                           params['E'], params['nu'], params['h'], params['rho'])
        
        # Create elements
        for elem in self.elements.values():
            if elem.element_type in [ElementType.ELASTIC_BEAM, ElementType.SECONDARY_BEAM]:
                # Elastic beam-column element (includes secondary beams)
                if elem.section_tag is None:
                    raise ValueError(f"Element {elem.tag} missing section_tag")
                if elem.section_tag not in self.sections:
                    raise ValueError(
                        f"Element {elem.tag} references unknown section {elem.section_tag}"
                    )

                section = self.sections[elem.section_tag]
                geom_transf_tag = elem.geometry.get('geom_transf_tag', elem.tag)
                vecxz = elem.geometry.get('vecxz', (0.0, 0.0, 1.0))

                if ndm == 3:
                    ops.geomTransf('Linear', geom_transf_tag, *vecxz)
                    ops.element(
                        'elasticBeamColumn',
                        elem.tag,
                        *elem.node_tags,
                        section['A'],
                        section['E'],
                        section['G'],
                        section['J'],
                        section['Iy'],
                        section['Iz'],
                        geom_transf_tag,
                    )
                else:
                    ops.geomTransf('Linear', geom_transf_tag)
                    ops.element(
                        'elasticBeamColumn',
                        elem.tag,
                        *elem.node_tags,
                        section['A'],
                        section['E'],
                        section['Iz'],
                        geom_transf_tag,
                    )
            elif elem.element_type == ElementType.BEAM_COLUMN:
                if elem.section_tag is None:
                    raise ValueError(f"Element {elem.tag} missing section_tag")
                if elem.section_tag not in self.sections:
                    raise ValueError(
                        f"Element {elem.tag} references unknown section {elem.section_tag}"
                    )

                section = self.sections[elem.section_tag]
                geom_transf_tag = elem.geometry.get('geom_transf_tag', elem.tag)
                vecxz = elem.geometry.get('vecxz', (0.0, 0.0, 1.0))

                if ndm == 3:
                    ops.geomTransf('Linear', geom_transf_tag, *vecxz)
                    ops.element(
                        'elasticBeamColumn',
                        elem.tag,
                        *elem.node_tags,
                        section['A'],
                        section['E'],
                        section['G'],
                        section['J'],
                        section['Iy'],
                        section['Iz'],
                        geom_transf_tag,
                    )
                else:
                    ops.geomTransf('Linear', geom_transf_tag)
                    ops.element(
                        'elasticBeamColumn',
                        elem.tag,
                        *elem.node_tags,
                        section['A'],
                        section['E'],
                        section['Iz'],
                        geom_transf_tag,
                    )
            elif elem.element_type in (ElementType.SHELL, ElementType.COUPLING_BEAM):
                # SHELL and COUPLING_BEAM elements are modeled as elastic beam-column
                # elements with equivalent section properties (for core walls and
                # deep coupling beams in preliminary analysis)
                if elem.section_tag is None:
                    raise ValueError(f"Element {elem.tag} missing section_tag")
                if elem.section_tag not in self.sections:
                    raise ValueError(
                        f"Element {elem.tag} references unknown section {elem.section_tag}"
                    )

                section = self.sections[elem.section_tag]
                geom_transf_tag = elem.geometry.get('geom_transf_tag', elem.tag)
                vecxz = elem.geometry.get('vecxz', (0.0, 0.0, 1.0))

                if ndm == 3:
                    ops.geomTransf('Linear', geom_transf_tag, *vecxz)
                    ops.element(
                        'elasticBeamColumn',
                        elem.tag,
                        *elem.node_tags,
                        section['A'],
                        section['E'],
                        section['G'],
                        section['J'],
                        section['Iy'],
                        section['Iz'],
                        geom_transf_tag,
                    )
                else:
                    ops.geomTransf('Linear', geom_transf_tag)
                    ops.element(
                        'elasticBeamColumn',
                        elem.tag,
                        *elem.node_tags,
                        section['A'],
                        section['E'],
                        section['Iz'],
                        geom_transf_tag,
                    )
            elif elem.element_type == ElementType.SHELL_MITC4:
                # ShellMITC4 4-node quad shell element
                if elem.section_tag is None:
                    raise ValueError(f"Element {elem.tag} missing section_tag")
                if len(elem.node_tags) != 4:
                    raise ValueError(
                        f"ShellMITC4 element {elem.tag} requires exactly 4 nodes, "
                        f"got {len(elem.node_tags)}"
                    )
                if ndm != 3:
                    raise ValueError("ShellMITC4 elements require ndm=3 (3D model)")
                
                # ShellMITC4 uses section tag directly, no geomTransf needed
                ops.element('ShellMITC4', elem.tag, *elem.node_tags, elem.section_tag)
            else:
                raise ValueError(
                    f"Element type {elem.element_type.value} not supported in builder"
                )

        # OpenSees SurfaceLoad works only with brick elements (SSPbrick, brickUP).
        # For ShellMITC4, convert pressure to equivalent nodal loads.
        surface_nodal_loads = []
        
        for surface_load in self.surface_loads:
            shell_elem_tag = surface_load.element_tag
            
            if shell_elem_tag not in self.elements:
                raise ValueError(
                    f"SurfaceLoad references non-existent element {shell_elem_tag}"
                )
            
            shell_elem = self.elements[shell_elem_tag]
            
            if shell_elem.element_type != ElementType.SHELL_MITC4:
                raise ValueError(
                    f"SurfaceLoad can only be applied to ShellMITC4 elements, "
                    f"got {shell_elem.element_type}"
                )
            
            if len(shell_elem.node_tags) != 4:
                raise ValueError(
                    f"SurfaceLoad requires 4 nodes, element {shell_elem_tag} has "
                    f"{len(shell_elem.node_tags)}"
                )
            
            n1, n2, n3, n4 = [self.nodes[tag] for tag in shell_elem.node_tags]
            area = 0.5 * abs((n1.x - n3.x) * (n2.y - n4.y) - (n2.x - n4.x) * (n1.y - n3.y))
            total_load = surface_load.pressure * area
            force_per_node = -total_load / 4.0
            
            for node_tag in shell_elem.node_tags:
                surface_nodal_loads.append((
                    node_tag,
                    surface_load.load_pattern,
                    force_per_node
                ))

        # Apply rigid diaphragms (planar constraints) for lateral patterns only
        apply_diaphragms = False
        if self.diaphragms:
            if active_pattern is None:
                apply_diaphragms = True
            else:
                apply_diaphragms = active_pattern in {4, 5, 6, 7}

        if apply_diaphragms:
            if ndm < 3:
                raise ValueError("Rigid diaphragms require ndm=3 (3D model)")
            for diaphragm in self.diaphragms:
                ops.rigidDiaphragm(
                    diaphragm.perp_dirn,
                    diaphragm.master_node,
                    *diaphragm.slave_nodes,
                )
        
        # Apply loads grouped by pattern
        patterns = {load.load_pattern for load in self.loads}
        patterns.update({u.load_pattern for u in self.uniform_loads})
        patterns.update({s.load_pattern for s in self.surface_loads})
        
        # Filter patterns if active_pattern is specified
        if active_pattern is not None:
            patterns = {p for p in patterns if p == active_pattern}

        _logger.info(f"Applying loads for pattern(s): {sorted(patterns)}")
        total_point_loads = 0
        total_uniform_loads = 0
        total_surface_loads = 0
        
        for pattern_id in sorted(patterns):
            ops.timeSeries('Linear', pattern_id)
            ops.pattern('Plain', pattern_id, pattern_id)

            # Point loads
            pattern_point_loads = 0
            for load in self.loads:
                if load.load_pattern != pattern_id:
                    continue

                if len(load.load_values) < ndf:
                    raise ValueError(
                        f"Load on node {load.node_tag} has insufficient DOFs "
                        f"(expected at least {ndf}, got {len(load.load_values)})"
                    )
                load_vector = load.load_values[:ndf]
                ops.load(load.node_tag, *load_vector)
                pattern_point_loads += 1

            # Uniform loads
            pattern_uniform_loads = 0
            for uniform_load in self.uniform_loads:
                if uniform_load.load_pattern != pattern_id:
                    continue
                if uniform_load.visual_only:
                    continue

                wy, wz = self._get_uniform_load_components(uniform_load, ndm)
                if ndm == 2:
                    ops.eleLoad('-ele', uniform_load.element_tag,
                                '-type', 'beamUniform', wy)
                else:
                    ops.eleLoad('-ele', uniform_load.element_tag,
                                '-type', 'beamUniform', wy, wz)
                pattern_uniform_loads += 1
            
            nodal_load_dict = {}
            for node_tag, load_pattern, force_z in surface_nodal_loads:
                if load_pattern != pattern_id:
                    continue
                if node_tag not in nodal_load_dict:
                    nodal_load_dict[node_tag] = 0.0
                nodal_load_dict[node_tag] += force_z
            
            for node_tag, force_z in nodal_load_dict.items():
                load_vector = [0.0, 0.0, force_z, 0.0, 0.0, 0.0]
                ops.load(node_tag, *load_vector[:ndf])
            
            pattern_surface_loads = len(nodal_load_dict)
            _logger.debug(f"Pattern {pattern_id}: {pattern_point_loads} point loads, "
                         f"{pattern_uniform_loads} uniform loads, {pattern_surface_loads} surface load nodes")
            total_point_loads += pattern_point_loads
            total_uniform_loads += pattern_uniform_loads
            total_surface_loads += pattern_surface_loads

        _logger.info(f"Total loads applied: {total_point_loads} point, {total_uniform_loads} uniform, {total_surface_loads} surface nodes")
        
        if total_point_loads + total_uniform_loads + total_surface_loads == 0:
            _logger.warning("WARNING: No loads were applied! Check load definitions and pattern IDs.")

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
            'n_surface_loads': len(self.surface_loads),
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

        # Validate diaphragms
        for diaphragm in self.diaphragms:
            if diaphragm.master_node not in self.nodes:
                errors.append(f"Diaphragm master node {diaphragm.master_node} missing")
            for slave in diaphragm.slave_nodes:
                if slave not in self.nodes:
                    errors.append(f"Diaphragm slave node {slave} missing")
                if slave == diaphragm.master_node:
                    errors.append("Diaphragm slave cannot equal master node")
        
        # Mesh quality checks for shell elements (warn only)
        max_aspect_ratio = 5.0
        for elem in self.elements.values():
            if elem.element_type == ElementType.SHELL_MITC4:
                if len(elem.node_tags) != 4:
                    errors.append(f"Shell element {elem.tag} has {len(elem.node_tags)} nodes (expected 4)")
                    continue

                n1 = self.nodes[elem.node_tags[0]]
                n2 = self.nodes[elem.node_tags[1]]
                n3 = self.nodes[elem.node_tags[2]]
                n4 = self.nodes[elem.node_tags[3]]

                edge1 = np.sqrt((n2.x - n1.x)**2 + (n2.y - n1.y)**2 + (n2.z - n1.z)**2)
                edge2 = np.sqrt((n3.x - n2.x)**2 + (n3.y - n2.y)**2 + (n3.z - n2.z)**2)
                edge3 = np.sqrt((n4.x - n3.x)**2 + (n4.y - n3.y)**2 + (n4.z - n3.z)**2)
                edge4 = np.sqrt((n1.x - n4.x)**2 + (n1.y - n4.y)**2 + (n1.z - n4.z)**2)

                max_edge = max(edge1, edge2, edge3, edge4)
                min_edge = min(edge1, edge2, edge3, edge4)

                if min_edge > 0:
                    aspect_ratio = max_edge / min_edge
                    if aspect_ratio > max_aspect_ratio:
                        _logger.warning(
                            "Shell element %s has excessive aspect ratio %.2f (max %.2f)",
                            elem.tag,
                            aspect_ratio,
                            max_aspect_ratio,
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
