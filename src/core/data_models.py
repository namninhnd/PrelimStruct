"""
Data Models for PrelimStruct - Preliminary Structural Design Platform
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple

from .constants import (
    GAMMA_G, GAMMA_Q, GAMMA_W,
    GAMMA_G_SLS, GAMMA_Q_SLS,
    CONCRETE_DENSITY,
)
from .load_tables import get_cover, get_live_load


class ExposureClass(Enum):
    """Exposure condition per HK Code Table 4.1"""
    MILD = "1"
    MODERATE = "2"
    SEVERE = "3"
    VERY_SEVERE = "4"
    ABRASIVE = "5"


class TerrainCategory(Enum):
    """Terrain category for wind load calculation (HK Wind Code 2019)"""
    OPEN_SEA = "A"          # Open sea, coastal areas
    OPEN_COUNTRY = "B"      # Open country with scattered obstructions
    URBAN = "C"             # Urban and suburban areas
    CITY_CENTRE = "D"       # City centre with tall buildings


class CoreWallConfig(Enum):
    """Core wall configuration types for FEM modeling.
    
    Simplified model for Phase 12A:
    - I_SECTION: Two walls blended into I-section shape
    - TUBE_WITH_OPENINGS: Tube/box core with configurable opening placement
    """
    I_SECTION = "i_section"
    TUBE_WITH_OPENINGS = "tube_with_openings"


class TubeOpeningPlacement(Enum):
    """Opening placement options for tube core walls.
    
    Primary UI options:
    - TOP_BOT: Openings at both top and bottom faces
    - NONE: No opening

    Backward-compatibility aliases are retained for persisted legacy values.
    """
    TOP_BOT = "top_bot"
    NONE = "none"

    TOP = "top"
    BOTTOM = "bottom"
    BOTH = "both"


class CoreLocationPreset(Enum):
    """Preset locations for core wall placement in floor plan.
    
    9 standard positions:
    - CENTER: Center of floor plan
    - NORTH/SOUTH/EAST/WEST: Side-middle positions
    - NORTHEAST/NORTHWEST/SOUTHEAST/SOUTHWEST: Corner positions
    
    All presets enforce bounding-box clearance from floor edges.
    """
    CENTER = "center"
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    NORTHEAST = "northeast"
    NORTHWEST = "northwest"
    SOUTHEAST = "southeast"
    SOUTHWEST = "southwest"


class WindLoadCase(Enum):
    """HK Wind Effects 2019 canonical wind load cases (24 total).

    Semantics:
    - 3 dominance groups (WX1-dominant, WX2-dominant, WTZ-dominant)
    - 8 sign permutations per group
    """
    # Group 1: WX1 dominant
    W1 = "W1"
    W2 = "W2"
    W3 = "W3"
    W4 = "W4"
    W5 = "W5"
    W6 = "W6"
    W7 = "W7"
    W8 = "W8"

    # Group 2: WX2 dominant
    W9 = "W9"
    W10 = "W10"
    W11 = "W11"
    W12 = "W12"
    W13 = "W13"
    W14 = "W14"
    W15 = "W15"
    W16 = "W16"

    # Group 3: WTZ dominant
    W17 = "W17"
    W18 = "W18"
    W19 = "W19"
    W20 = "W20"
    W21 = "W21"
    W22 = "W22"
    W23 = "W23"
    W24 = "W24"


class SeismicLoadCase(Enum):
    """Eurocode 8 Seismic Load Cases."""
    E1_X_POS = "E1"  # X Direction
    E2_Y_POS = "E2"  # Y Direction
    E3_Z_POS = "E3"  # Vertical (Optional)


class LoadCaseCategory(Enum):
    """Load case categories for organization."""
    GRAVITY = "GRAVITY"
    WIND = "WIND"
    SEISMIC = "SEISMIC"


class ColumnPosition(Enum):
    """Column position for eccentricity calculation"""
    INTERIOR = "interior"
    EDGE = "edge"
    CORNER = "corner"


class LoadCombination(Enum):
    """Load combination types per HK Code 2013 Table 2.1 and Eurocode 8."""
    # ULS Gravity-Dominant Combinations (HK Code 2013 Table 2.1, Case 1)
    ULS_GRAVITY_1 = "uls_gravity_1"  # 1.4Gk + 1.6Qk
    ULS_GRAVITY_2 = "uls_gravity_2"  # 1.0Gk + 1.6Qk (min dead load)
    
    # ULS Wind Combinations (HK Code 2013 Table 2.1, Case 2)
    ULS_WIND_1 = "uls_wind_1"        # 1.4Gk + 1.4Wk (dead + wind, no live)
    ULS_WIND_2 = "uls_wind_2"        # 1.0Gk + 1.4Wk (min dead + wind)
    ULS_WIND_3 = "uls_wind_3"        # 1.2Gk + 1.2Qk + 1.2Wk (combined action)
    ULS_WIND_4 = "uls_wind_4"        # 1.2Gk + 1.2Qk - 1.2Wk (wind reversal)
    
    # ULS Seismic Combinations (Eurocode 8, EN 1998-1 Cl 4.2.4)
    ULS_SEISMIC_X_POS = "uls_seismic_x_pos"  # 1.0Gk + 0.3Qk + 1.0Ed_x
    ULS_SEISMIC_X_NEG = "uls_seismic_x_neg"  # 1.0Gk + 0.3Qk - 1.0Ed_x
    ULS_SEISMIC_Y_POS = "uls_seismic_y_pos"  # 1.0Gk + 0.3Qk + 1.0Ed_y
    ULS_SEISMIC_Y_NEG = "uls_seismic_y_neg"  # 1.0Gk + 0.3Qk - 1.0Ed_y
    ULS_SEISMIC_XY_1 = "uls_seismic_xy_1"    # 1.0Gk + 0.3Qk + 0.3Ed_x + 1.0Ed_y
    ULS_SEISMIC_XY_2 = "uls_seismic_xy_2"    # 1.0Gk + 0.3Qk + 1.0Ed_x + 0.3Ed_y
    
    # ULS Accidental Combinations (HK Code 2013 Table 2.1, Case 3)
    ULS_ACCIDENTAL = "uls_accidental"  # 1.0Gk + 0.5Qk + 1.0Ad (notional loads)
    
    # SLS Combinations (HK Code 2013 Cl 3.4, 7.2-7.3)
    SLS_CHARACTERISTIC = "sls_characteristic"  # 1.0Gk + 1.0Qk (deflection check)
    SLS_FREQUENT = "sls_frequent"              # 1.0Gk + 0.5Qk (crack width check)
    SLS_QUASI_PERMANENT = "sls_quasi_permanent"  # 1.0Gk + 0.3Qk (long-term deflection)


class FEMElementType(Enum):
    """FEM element types for mesh generation."""
    BEAM = "beam"
    PLATE = "plate"
    SOLID = "solid"
    COUPLING_BEAM = "coupling_beam"


@dataclass
class SupportCondition:
    """Boundary condition definition for FEM supports.

    Attributes:
        node_tag: Node identifier matching mesh nodes
        restraints: Fixity flags [ux, uy, uz, rx, ry, rz] (1=fixed, 0=free)
        label: Optional description (e.g., "base_fixity")
    """
    node_tag: int
    restraints: List[int] = field(default_factory=lambda: [0, 0, 0, 0, 0, 0])
    label: str = ""

    def __post_init__(self):
        """Validate restraint definition."""
        if len(self.restraints) != 6:
            raise ValueError(
                "SupportCondition.restraints must have 6 components [ux, uy, uz, rx, ry, rz]"
            )
        if not all(value in (0, 1) for value in self.restraints):
            raise ValueError(
                "SupportCondition.restraints must use 0 (free) or 1 (fixed) values"
            )

    @property
    def is_fully_fixed(self) -> bool:
        """Check if all translational and rotational DOFs are fixed."""
        return all(value == 1 for value in self.restraints)


@dataclass
class NodalLoad:
    """Nodal load definition for FEM analysis.

    Attributes:
        node_tag: Node identifier matching mesh nodes
        load_values: Load vector [Fx, Fy, Fz, Mx, My, Mz] in N and N-m
        load_pattern: Load pattern identifier (e.g., combination name)
    """
    node_tag: int
    load_values: List[float]
    load_pattern: str = "DEFAULT"

    def __post_init__(self):
        """Validate load definition."""
        if len(self.load_values) != 6:
            raise ValueError(
                "NodalLoad.load_values must have 6 components [Fx, Fy, Fz, Mx, My, Mz]"
            )


@dataclass
class MeshElement:
    """Mesh element connectivity for FEM model.

    Attributes:
        element_id: Unique element identifier
        element_type: Element formulation type (beam, plate, solid, coupling_beam)
        node_tags: Node tags defining connectivity
        section_id: Optional section identifier for property mapping
        material_id: Optional material identifier for property mapping
    """
    element_id: int
    element_type: FEMElementType
    node_tags: List[int]
    section_id: Optional[str] = None
    material_id: Optional[str] = None

    def __post_init__(self):
        """Validate element connectivity."""
        if len(self.node_tags) < 2:
            raise ValueError("MeshElement requires at least two node tags for connectivity")


@dataclass
class MeshData:
    """Mesh data container for FEM model generation.

    Attributes:
        node_coordinates: Mapping of node tag to (x, y, z) coordinates in meters
        elements: List of mesh elements with connectivity and property references
        supports: Boundary condition definitions for supports
        loads: Nodal loads applied to the mesh
    """
    node_coordinates: Dict[int, Tuple[float, float, float]] = field(default_factory=dict)
    elements: List[MeshElement] = field(default_factory=list)
    supports: List[SupportCondition] = field(default_factory=list)
    loads: List[NodalLoad] = field(default_factory=list)

    def get_summary(self) -> Dict[str, Any]:
        """Summarize mesh contents for reporting."""
        return {
            "n_nodes": len(self.node_coordinates),
            "n_elements": len(self.elements),
            "n_supports": len(self.supports),
            "n_loads": len(self.loads),
        }

    def get_fixed_nodes(self) -> List[int]:
        """Return node tags that are fully fixed."""
        return [support.node_tag for support in self.supports if support.is_fully_fixed]

    def validate_connectivity(self) -> Tuple[bool, List[str]]:
        """Validate that all element node_tags reference existing nodes.

        Returns:
            Tuple of (is_valid, error_messages):
                - is_valid: True if all node references are valid
                - error_messages: List of error descriptions for invalid references
        """
        errors: List[str] = []
        valid_node_tags = set(self.node_coordinates.keys())

        for element in self.elements:
            for node_tag in element.node_tags:
                if node_tag not in valid_node_tags:
                    errors.append(
                        f"Element {element.element_id} references non-existent node {node_tag}"
                    )

        # Also validate support node references
        for support in self.supports:
            if support.node_tag not in valid_node_tags:
                errors.append(
                    f"Support at node {support.node_tag} references non-existent node"
                )

        # Also validate load node references
        for load in self.loads:
            if load.node_tag not in valid_node_tags:
                errors.append(
                    f"Load at node {load.node_tag} references non-existent node"
                )

        return (len(errors) == 0, errors)


@dataclass
class FEMAnalysisSettings:
    """Analysis configuration for FEM runs."""
    analysis_type: str = "linear_static"
    n_dimensions: int = 3
    dof_per_node: int = 6
    include_p_delta: bool = False
    apply_rigid_diaphragms: bool = True
    load_combinations: List[LoadCombination] = field(
        default_factory=lambda: [
            LoadCombination.ULS_GRAVITY_1,
            LoadCombination.ULS_WIND_1,
            LoadCombination.SLS_CHARACTERISTIC,
        ]
    )
    solver: str = "openseespy"


@dataclass
class FEMModelInput:
    """Input schema for FEM model generation."""
    mesh: MeshData = field(default_factory=MeshData)
    element_types: List[FEMElementType] = field(
        default_factory=lambda: [FEMElementType.BEAM]
    )
    analysis_settings: FEMAnalysisSettings = field(default_factory=FEMAnalysisSettings)
    description: str = ""

    def get_summary(self) -> Dict[str, Any]:
        """Provide lightweight summary for reporting or serialization."""
        mesh_summary = self.mesh.get_summary()
        mesh_summary.update({
            "element_types": [etype.value for etype in self.element_types],
            "analysis_type": self.analysis_settings.analysis_type,
            "n_dimensions": self.analysis_settings.n_dimensions,
            "dof_per_node": self.analysis_settings.dof_per_node,
        })
        return mesh_summary


@dataclass
class LoadCaseResult:
    """Result container for a single load combination."""
    combination: LoadCombination
    case_name: str = "DEFAULT"  # Specific combination name (e.g., "LC1", "W1_MAX")
    node_displacements: Dict[int, List[float]] = field(default_factory=dict)
    element_forces: Dict[int, Dict[str, float]] = field(default_factory=dict)
    reactions: Dict[int, List[float]] = field(default_factory=dict)
    stresses: Dict[int, float] = field(default_factory=dict)
    strains: Dict[int, float] = field(default_factory=dict)


@dataclass
class EnvelopeValue:
    """Envelope metrics across load combinations.

    Attributes:
        max_value: Maximum value across all load combinations
        min_value: Minimum value across all load combinations
        governing_max_case: Load combination that governs the maximum value
        governing_min_case: Load combination that governs the minimum value
        governing_max_case_name: Load combination name that governs the maximum value
        governing_min_case_name: Load combination name that governs the minimum value
        governing_max_location: Node/element tag where max occurs (for post-processing)
        governing_min_location: Node/element tag where min occurs (for post-processing)
    """
    max_value: float = 0.0
    min_value: float = 0.0
    governing_max_case: Optional[LoadCombination] = None
    governing_min_case: Optional[LoadCombination] = None
    governing_max_case_name: Optional[str] = None
    governing_min_case_name: Optional[str] = None
    governing_max_location: Optional[int] = None
    governing_min_location: Optional[int] = None


@dataclass
class EnvelopedResult:
    """Enveloped FEM results (max/min across combinations)."""
    displacements: EnvelopeValue = field(default_factory=EnvelopeValue)
    reactions: EnvelopeValue = field(default_factory=EnvelopeValue)
    stresses: EnvelopeValue = field(default_factory=EnvelopeValue)
    strains: EnvelopeValue = field(default_factory=EnvelopeValue)


@dataclass
class FEMResult:
    """FEM analysis results with load case breakdown and envelope."""
    load_case_results: List[LoadCaseResult] = field(default_factory=list)
    enveloped_results: EnvelopedResult = field(default_factory=EnvelopedResult)

    def get_summary(self) -> Dict[str, Any]:
        """Provide summary of FEM results for reporting."""
        return {
            "n_load_cases": len(self.load_case_results),
            "enveloped": {
                "max_displacement": self.enveloped_results.displacements.max_value,
                "min_displacement": self.enveloped_results.displacements.min_value,
                "max_stress": self.enveloped_results.stresses.max_value,
                "min_stress": self.enveloped_results.stresses.min_value,
                "max_reaction": self.enveloped_results.reactions.max_value,
                "min_reaction": self.enveloped_results.reactions.min_value,
            },
        }


@dataclass
class GeometryInput:
    """Structural geometry inputs"""
    bay_x: float            # Bay size in X direction (m)
    bay_y: float            # Bay size in Y direction (m)
    floors: int             # Number of floors
    story_height: float = 3.0  # Story height (m)
    num_bays_x: int = 1     # Number of bays in X direction
    num_bays_y: int = 1     # Number of bays in Y direction
    max_slab_span: Optional[float] = None  # Maximum slab span (m)

    def __post_init__(self):
        if self.max_slab_span is None:
            self.max_slab_span = min(self.bay_x, self.bay_y)

    @property
    def total_width_x(self) -> float:
        """Total building width in X direction"""
        return self.bay_x * self.num_bays_x

    @property
    def total_width_y(self) -> float:
        """Total building width in Y direction"""
        return self.bay_y * self.num_bays_y
    
    @property
    def x_gridlines(self) -> List[float]:
        """X-coordinate gridline positions."""
        return [i * self.bay_x for i in range(self.num_bays_x + 1)]
    
    @property
    def y_gridlines(self) -> List[float]:
        """Y-coordinate gridline positions."""
        return [i * self.bay_y for i in range(self.num_bays_y + 1)]



@dataclass
class LoadInput:
    """Loading inputs"""
    live_load_class: str        # HK Code Table 3.1 class (e.g., "2") or "9" for custom
    live_load_sub: str          # HK Code Table 3.2 subdivision (e.g., "2.5")
    dead_load: float            # Superimposed dead load (kPa)
    storage_height: float = 0   # For height-dependent storage loads (m)
    custom_live_load: Optional[float] = None  # Custom LL value in kPa (Class 9)

    @property
    def live_load(self) -> float:
        """Get live load value from code tables or custom input.
        
        If live_load_class is "9" (Other/Custom), returns the custom_live_load value.
        Otherwise, looks up the value from HK Code Tables 3.1/3.2.
        """
        if self.live_load_class == "9" and self.custom_live_load is not None:
            return self.custom_live_load
        return get_live_load(self.live_load_class, self.live_load_sub, self.storage_height)


@dataclass
class MaterialInput:
    """Material property inputs"""
    fcu_slab: int = 35      # Slab concrete grade (MPa)
    fcu_beam: int = 40      # Beam concrete grade (MPa)
    fcu_column: int = 45    # Column concrete grade (MPa)
    fy: int = 500           # Main reinforcement yield strength (MPa)
    fyv: int = 250          # Link yield strength (MPa)
    exposure: ExposureClass = ExposureClass.MODERATE

    @property
    def cover_slab(self) -> int:
        """Get slab cover from exposure table"""
        return get_cover(self.exposure.value, self.fcu_slab)

    @property
    def cover_beam(self) -> int:
        """Get beam cover from exposure table"""
        return get_cover(self.exposure.value, self.fcu_beam)

    @property
    def cover_column(self) -> int:
        """Get column cover from exposure table"""
        return get_cover(self.exposure.value, self.fcu_column)


@dataclass
class ReinforcementInput:
    """Reinforcement ratio inputs (%)"""
    min_rho_slab: float = 0.13
    max_rho_slab: float = 4.0
    min_rho_beam: float = 0.13
    max_rho_beam: float = 2.5
    min_rho_column: float = 2.0
    max_rho_column: float = 6.0


@dataclass
class CoreWallGeometry:
    """Core wall geometry parameters for FEM modeling.
    
    Attributes:
        config: Core wall configuration type
        wall_thickness: Wall thickness in mm (default 500mm per HK practice)
        length_x: Core wall outer dimension in X direction (mm)
        length_y: Core wall outer dimension in Y direction (mm)
        opening_width: Opening size in core wall (mm), if applicable
        opening_height: Optional legacy opening height (mm). If omitted,
            opening_width is reused for height-dependent calculations.
        flange_width: Flange width for I-section or C-section configurations (mm)
        web_length: Web length for I-section or C-section configurations (mm)
        opening_placement: Opening placement for TUBE_WITH_OPENINGS (Phase 12A)
    """
    config: CoreWallConfig
    wall_thickness: float = 500.0  # mm
    length_x: float = 6000.0       # mm
    length_y: float = 6000.0       # mm
    opening_width: Optional[float] = None   # mm
    opening_height: Optional[float] = None  # mm
    flange_width: Optional[float] = None    # mm
    web_length: Optional[float] = None      # mm
    opening_placement: TubeOpeningPlacement = TubeOpeningPlacement.TOP_BOT


@dataclass
class CoreWallSectionProperties:
    """Section properties for core wall structural analysis.

    These properties are used for FEM analysis and lateral stability calculations.
    All properties are calculated about the centroidal axis.

    Attributes:
        I_xx: Second moment of area about X-X axis (mm⁴)
        I_yy: Second moment of area about Y-Y axis (mm⁴)
        I_xy: Product of inertia (mm⁴)
        A: Cross-sectional area (mm²)
        J: Torsional constant (mm⁴)
        centroid_x: X-coordinate of centroid from reference point (mm)
        centroid_y: Y-coordinate of centroid from reference point (mm)
        shear_center_x: X-coordinate of shear center (mm)
        shear_center_y: Y-coordinate of shear center (mm)
    """
    I_xx: float = 0.0
    I_yy: float = 0.0
    I_xy: float = 0.0
    A: float = 0.0
    J: float = 0.0
    centroid_x: float = 0.0
    centroid_y: float = 0.0
    shear_center_x: float = 0.0
    shear_center_y: float = 0.0


@dataclass
class CouplingBeam:
    """Coupling beam spanning core wall openings.

    Coupling beams are deep beams that connect core wall segments across
    openings (e.g., door openings, elevator/stair openings). They provide
    critical coupling action for lateral load resistance in tall buildings.

    Per HK Code 2013, coupling beams typically have:
    - Width equal to wall thickness (for compatibility)
    - Depth constrained by opening height minus clearances
    - High shear forces requiring diagonal reinforcement

    Attributes:
        clear_span: Clear span between core wall faces (mm)
        depth: Beam depth constrained by opening height (mm)
        width: Beam width, typically equal to wall thickness (mm)
        location_x: X-coordinate of beam centerline (mm)
        location_y: Y-coordinate of beam centerline (mm)
        floor_level: Floor level where beam is located (0-indexed)
        opening_height: Full height of opening in core wall (mm)
        top_rebar_area: Top reinforcement area (mm²)
        bottom_rebar_area: Bottom reinforcement area (mm²)
        diagonal_rebar_area: Diagonal reinforcement area per leg (mm²)
        link_area: Shear link area (mm²/m)
        link_spacing: Shear link spacing (mm)
    """
    clear_span: float
    depth: float
    width: float
    location_x: float = 0.0
    location_y: float = 0.0
    floor_level: int = 0
    opening_height: Optional[float] = None
    top_rebar_area: float = 0.0
    bottom_rebar_area: float = 0.0
    diagonal_rebar_area: float = 0.0
    link_area: float = 0.0
    link_spacing: int = 0

    @property
    def span_to_depth_ratio(self) -> float:
        """Calculate span-to-depth ratio (L/h).

        HK Code 2013 Cl 6.1.1.2: Deep beam when L/h < 2.0
        """
        # Guard against None or zero values for defensive coding
        if self.clear_span is None or self.depth is None:
            return float('inf')
        if self.depth == 0:
            return float('inf')
        return self.clear_span / self.depth

    @property
    def is_deep_beam(self) -> bool:
        """Check if beam qualifies as deep beam per HK Code 2013.

        HK Code 2013 Cl 6.1.1.2: Deep beam when clear span ≤ 2 × overall depth
        """
        # Guard against None values
        if self.clear_span is None or self.depth is None:
            return False
        return self.span_to_depth_ratio < 2.0


@dataclass
class SlabDesignInput:
    """Slab-specific design inputs"""
    pass


@dataclass
class BeamDesignInput:
    """Beam-specific design inputs"""
    pattern_load_factor: float = 1.1  # Magnification for alternate span loading (user input)


@dataclass
class LateralInput:
    """Lateral stability inputs"""
    # v3.0 FEM fields
    core_wall_config: Optional[CoreWallConfig] = None  # Core wall configuration type
    wall_thickness: float = 500.0  # Wall thickness (mm) for FEM modeling
    core_geometry: Optional[CoreWallGeometry] = None   # Detailed geometry for FEM
    section_properties: Optional[CoreWallSectionProperties] = None  # Calculated properties
    
    # Wind load parameters
    terrain: TerrainCategory = TerrainCategory.URBAN
    building_width: float = 0   # Total building width (m)
    building_depth: float = 0   # Total building depth (m)

    # Core Wall Location (Phase 12A)
    location_preset: CoreLocationPreset = CoreLocationPreset.CENTER
    custom_center_x: Optional[float] = None  # Hidden compatibility field
    custom_center_y: Optional[float] = None  # Hidden compatibility field


@dataclass
class DesignResult:
    """Base class for design results"""
    element_type: str
    size: str
    utilization: float = 0.0
    status: str = "OK"
    warnings: List[str] = field(default_factory=list)
    calculations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SlabResult(DesignResult):
    """Slab design results"""
    thickness: int = 0          # mm
    moment: float = 0.0         # kNm/m
    reinforcement_area: float = 0.0  # mm²/m
    deflection_ratio: float = 0.0
    self_weight: float = 0.0    # kPa


@dataclass
class BeamResult(DesignResult):
    """Beam design results"""
    width: int = 0              # mm
    depth: int = 0              # mm
    moment: float = 0.0         # kNm
    shear: float = 0.0          # kN
    shear_capacity: float = 0.0 # kN
    shear_reinforcement_required: bool = False
    shear_reinforcement_area: float = 0.0  # mm²/m
    link_spacing: int = 0       # mm
    is_deep_beam: bool = False
    iteration_count: int = 0
    # Beam trimming fields (v3.0 FEM)
    is_trimmed: bool = False                    # True if beam was trimmed at core wall
    original_span: Optional[float] = None       # Original span before trimming (m)
    trimmed_span: Optional[float] = None        # Trimmed span after trimming (m)
    start_connection: Optional[str] = None      # Connection at start ("moment"/"pinned"/"fixed")
    end_connection: Optional[str] = None        # Connection at end ("moment"/"pinned"/"fixed")


@dataclass
class CouplingBeamResult(DesignResult):
    """Coupling beam design results.

    Coupling beams require special design considerations per HK Code 2013:
    - High shear forces requiring diagonal reinforcement
    - Deep beam provisions for L/h < 2.0
    - Ductility requirements for seismic regions
    """
    width: int = 0              # mm
    depth: int = 0              # mm
    clear_span: float = 0.0     # mm
    moment: float = 0.0         # kNm (from wind/seismic coupling action)
    shear: float = 0.0          # kN (dominant action in coupling beams)
    shear_capacity: float = 0.0 # kN
    top_rebar: float = 0.0      # mm² (top reinforcement)
    bottom_rebar: float = 0.0   # mm² (bottom reinforcement)
    diagonal_rebar: float = 0.0 # mm² per leg (diagonal reinforcement)
    link_spacing: int = 0       # mm (shear link spacing)
    is_deep_beam: bool = True   # Typically true for coupling beams
    span_to_depth_ratio: float = 0.0


@dataclass
class ColumnResult(DesignResult):
    """Column design results"""
    dimension: int = 0          # mm (legacy square column)
    width: int = 0              # mm (column width)
    depth: int = 0              # mm (column depth)
    axial_load: float = 0.0     # kN
    moment: float = 0.0         # kNm (gravity moment if any)
    is_slender: bool = False
    slenderness: float = 0.0
    # Lateral load fields (for moment frame system)
    lateral_shear: float = 0.0  # kN (wind shear at column)
    lateral_moment: float = 0.0 # kNm (moment at column base from wind)
    has_lateral_loads: bool = False  # True if moment frame system
    combined_utilization: float = 0.0  # P/A + M×y/I utilization


@dataclass
class CoreWallResult(DesignResult):
    """Core wall design results"""
    compression_check: float = 0.0  # Utilization ratio
    tension_check: float = 0.0      # Negative = tension
    shear_check: float = 0.0        # Utilization ratio
    requires_tension_piles: bool = False


@dataclass
class WindResult:
    """Wind load calculation results
    
    Gate H Extension (Phase 13A):
    Added traceability and per-floor wind loads for read-only detail expansion.
    Fields enable UI to show calculation breakdown without editable inputs.
    """
    # Legacy aggregate fields (backward compatibility)
    base_shear: float = 0.0          # kN (legacy aggregate for backward compatibility)
    base_shear_x: float = 0.0        # kN (wind in X direction)
    base_shear_y: float = 0.0        # kN (wind in Y direction)
    overturning_moment: float = 0.0  # kNm
    reference_pressure: float = 0.0  # kPa
    drift_mm: float = 0.0            # mm (lateral drift at top)
    drift_index: float = 0.0         # Drift ratio (Δ/H)
    drift_ok: bool = True
    lateral_system: str = "CORE_WALL"  # "CORE_WALL" or "MOMENT_FRAME"
    
    # Gate H: Traceability (wind code reference)
    code_reference: str = "HK Wind Code 2019 - Simplified Analysis"
    terrain_factor: float = 0.0      # Sz terrain coefficient
    force_coefficient: float = 0.0   # Cf aerodynamic coefficient
    design_pressure: float = 0.0     # kPa (reference_pressure * terrain_factor)
    
    # Gate H: Per-floor wind loads (empty lists if not calculated)
    floor_elevations: List[float] = field(default_factory=list)  # m (from base)
    floor_wind_x: List[float] = field(default_factory=list)      # kN per floor (X direction)
    floor_wind_y: List[float] = field(default_factory=list)      # kN per floor (Y direction)
    floor_torsion_z: List[float] = field(default_factory=list)   # kNm per floor (torsional)


@dataclass
class ProjectData:
    """
    Central data class for all project inputs and results.
    This is the main interface for the PrelimStruct platform.
    """
    # Project metadata
    project_name: str = "Untitled Project"
    project_number: str = ""
    engineer: str = ""
    date: str = ""

    # Input data
    geometry: GeometryInput = field(default_factory=lambda: GeometryInput(6.0, 6.0, 5))
    loads: LoadInput = field(default_factory=lambda: LoadInput("2", "2.5", 2.0))
    materials: MaterialInput = field(default_factory=MaterialInput)
    reinforcement: ReinforcementInput = field(default_factory=ReinforcementInput)
    slab_design: SlabDesignInput = field(default_factory=SlabDesignInput)
    beam_design: BeamDesignInput = field(default_factory=BeamDesignInput)
    lateral: LateralInput = field(default_factory=LateralInput)

    # Design settings
    load_combination: LoadCombination = LoadCombination.ULS_GRAVITY_1

    # Results (populated after calculation)
    slab_result: Optional[SlabResult] = None
    primary_beam_result: Optional[BeamResult] = None
    secondary_beam_result: Optional[BeamResult] = None
    column_result: Optional[ColumnResult] = None
    core_wall_result: Optional[CoreWallResult] = None
    wind_result: Optional[WindResult] = None
    fem_model: Optional[FEMModelInput] = None
    fem_result: Optional[FEMResult] = None

    # Summary metrics
    concrete_volume: float = 0.0    # m³
    carbon_emission: float = 0.0    # kgCO2e

    @property
    def tributary_area(self) -> float:
        """Calculate tributary area for column load"""
        return self.geometry.bay_x * self.geometry.bay_y

    @property
    def total_dead_load(self) -> float:
        """Total characteristic dead load (kPa)"""
        slab_self_weight = 0.0
        if self.slab_result:
            slab_self_weight = self.slab_result.self_weight
        else:
            # Estimate based on typical 200mm slab
            slab_self_weight = 0.2 * CONCRETE_DENSITY
        return self.loads.dead_load + slab_self_weight

    @property
    def total_live_load(self) -> float:
        """Total characteristic live load (kPa)"""
        return self.loads.live_load

    def get_design_load(self) -> float:
        """Get factored design load based on load combination (kPa)"""
        gk = self.total_dead_load
        qk = self.total_live_load

        if self.load_combination == LoadCombination.ULS_GRAVITY_1:
            return GAMMA_G * gk + GAMMA_Q * qk
        elif self.load_combination == LoadCombination.SLS_CHARACTERISTIC:
            return GAMMA_G_SLS * gk + GAMMA_Q_SLS * qk
        else:
            # Wind combination - return gravity portion only
            return gk + 0.5 * qk  # Reduced live load for wind combination

    def to_dict(self) -> Dict[str, Any]:
        """Export project data as dictionary for JSON serialization"""
        return {
            "project_name": self.project_name,
            "project_number": self.project_number,
            "engineer": self.engineer,
            "date": self.date,
            "geometry": {
                "bay_x": self.geometry.bay_x,
                "bay_y": self.geometry.bay_y,
                "floors": self.geometry.floors,
                "story_height": self.geometry.story_height,
                "max_slab_span": self.geometry.max_slab_span,
            },
            "loads": {
                "live_load_class": self.loads.live_load_class,
                "live_load_sub": self.loads.live_load_sub,
                "live_load_value": self.loads.live_load,
                "dead_load": self.loads.dead_load,
            },
            "materials": {
                "fcu_slab": self.materials.fcu_slab,
                "fcu_beam": self.materials.fcu_beam,
                "fcu_column": self.materials.fcu_column,
                "fy": self.materials.fy,
                "fyv": self.materials.fyv,
                "exposure": self.materials.exposure.value,
            },
            "summary": {
                "concrete_volume": self.concrete_volume,
                "carbon_emission": self.carbon_emission,
            },
            "fem_model": self.fem_model.get_summary() if self.fem_model else None,
            "fem_result": self.fem_result.get_summary() if self.fem_result else None,
        }


# Preset configurations for common building types
PRESETS = {
    "residential": {
        "name": "Residential",
        "loads": LoadInput("1", "1.1", 1.5),
        "materials": MaterialInput(fcu_slab=35, fcu_beam=35, fcu_column=40),
    },
    "office": {
        "name": "Office",
        "loads": LoadInput("2", "2.5", 2.0),
        "materials": MaterialInput(fcu_slab=35, fcu_beam=40, fcu_column=45),
    },
    "retail": {
        "name": "Retail / Shopping",
        "loads": LoadInput("4", "4.1", 2.5),
        "materials": MaterialInput(fcu_slab=40, fcu_beam=40, fcu_column=50),
    },
    "carpark": {
        "name": "Car Park",
        "loads": LoadInput("6", "6.1", 2.0),
        "materials": MaterialInput(fcu_slab=40, fcu_beam=45, fcu_column=45),
    },
    "plant_room": {
        "name": "Plant Room",
        "loads": LoadInput("5", "5.9", 3.0),
        "materials": MaterialInput(fcu_slab=40, fcu_beam=45, fcu_column=50),
    },
}
