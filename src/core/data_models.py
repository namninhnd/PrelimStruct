"""
Data Models for PrelimStruct - Preliminary Structural Design Platform
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any

from .constants import (
    GAMMA_G, GAMMA_Q, GAMMA_W,
    GAMMA_G_SLS, GAMMA_Q_SLS,
    CONCRETE_DENSITY,
)
from .load_tables import get_cover, get_live_load


class SlabType(Enum):
    """Slab spanning type"""
    ONE_WAY = "one-way"
    TWO_WAY = "two-way"


class SpanDirection(Enum):
    """Main span direction for one-way slabs"""
    ALONG_X = "alongX"
    ALONG_Y = "alongY"


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


class CoreLocation(Enum):
    """Core wall location in building plan"""
    CENTER = "center"       # Core at building center (symmetric)
    SIDE = "side"           # Core at building side (one-way eccentricity)
    CORNER = "corner"       # Core at building corner (two-way eccentricity)


class CoreWallConfig(Enum):
    """Core wall configuration types for FEM modeling.
    
    These configurations represent typical tall building core wall arrangements
    commonly used in Hong Kong structural design practice.
    """
    I_SECTION = "i_section"                     # 2 walls blended into I-section
    TWO_C_FACING = "two_c_facing"               # 2 C-shaped walls facing each other
    TWO_C_BACK_TO_BACK = "two_c_back_to_back"   # 2 C-shaped walls back to back
    TUBE_CENTER_OPENING = "tube_center_opening" # Tube/box with center opening
    TUBE_SIDE_OPENING = "tube_side_opening"     # Tube/box with side flange opening


class ColumnPosition(Enum):
    """Column position for eccentricity calculation"""
    INTERIOR = "interior"
    EDGE = "edge"
    CORNER = "corner"


class LoadCombination(Enum):
    """Load combination types"""
    ULS_GRAVITY = "uls_gravity"      # 1.4Gk + 1.6Qk
    ULS_WIND = "uls_wind"            # 1.0Gk + 1.4Wk
    SLS_DEFLECTION = "sls_deflection"  # 1.0Gk + 1.0Qk


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


@dataclass
class LoadInput:
    """Loading inputs"""
    live_load_class: str        # HK Code Table 3.1 class (e.g., "2")
    live_load_sub: str          # HK Code Table 3.2 subdivision (e.g., "2.5")
    dead_load: float            # Superimposed dead load (kPa)
    storage_height: float = 0   # For height-dependent storage loads (m)

    @property
    def live_load(self) -> float:
        """Get live load value from code tables"""
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
        opening_width: Width of opening in core wall (mm), if applicable
        opening_height: Height of opening in core wall (mm), if applicable
        flange_width: Flange width for I-section or C-section configurations (mm)
        web_length: Web length for I-section or C-section configurations (mm)
    """
    config: CoreWallConfig
    wall_thickness: float = 500.0  # mm
    length_x: float = 6000.0       # mm
    length_y: float = 6000.0       # mm
    opening_width: Optional[float] = None   # mm
    opening_height: Optional[float] = None  # mm
    flange_width: Optional[float] = None    # mm
    web_length: Optional[float] = None      # mm


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
        if self.depth == 0:
            return float('inf')
        return self.clear_span / self.depth

    @property
    def is_deep_beam(self) -> bool:
        """Check if beam qualifies as deep beam per HK Code 2013.

        HK Code 2013 Cl 6.1.1.2: Deep beam when clear span ≤ 2 × overall depth
        """
        return self.span_to_depth_ratio < 2.0


@dataclass
class SlabDesignInput:
    """Slab-specific design inputs"""
    slab_type: SlabType = SlabType.TWO_WAY
    span_direction: SpanDirection = SpanDirection.ALONG_X


@dataclass
class BeamDesignInput:
    """Beam-specific design inputs"""
    pattern_load_factor: float = 1.1  # Magnification for alternate span loading (user input)


@dataclass
class LateralInput:
    """Lateral stability inputs"""
    # Legacy fields (for backward compatibility with v2.1)
    core_dim_x: float = 0       # Core wall outer dimension in X (m)
    core_dim_y: float = 0       # Core wall outer dimension in Y (m)
    core_thickness: float = 0.5  # Core wall thickness (m), default 500mm
    core_location: CoreLocation = CoreLocation.CENTER  # Core location in plan
    
    # v3.0 FEM fields
    core_wall_config: Optional[CoreWallConfig] = None  # Core wall configuration type
    wall_thickness: float = 500.0  # Wall thickness (mm) for FEM modeling
    core_geometry: Optional[CoreWallGeometry] = None   # Detailed geometry for FEM
    section_properties: Optional[CoreWallSectionProperties] = None  # Calculated properties
    
    # Wind load parameters
    terrain: TerrainCategory = TerrainCategory.URBAN
    building_width: float = 0   # Total building width (m)
    building_depth: float = 0   # Total building depth (m)


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
    start_connection: Optional[str] = None      # Connection type at start ("moment", "pinned", "fixed")
    end_connection: Optional[str] = None        # Connection type at end ("moment", "pinned", "fixed")


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
    dimension: int = 0          # mm (square column)
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
    """Wind load calculation results"""
    base_shear: float = 0.0         # kN
    overturning_moment: float = 0.0  # kNm
    reference_pressure: float = 0.0  # kPa
    drift_mm: float = 0.0            # mm (lateral drift at top)
    drift_index: float = 0.0         # Drift ratio (Δ/H)
    drift_ok: bool = True
    lateral_system: str = "CORE_WALL"  # "CORE_WALL" or "MOMENT_FRAME"


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
    load_combination: LoadCombination = LoadCombination.ULS_GRAVITY

    # Results (populated after calculation)
    slab_result: Optional[SlabResult] = None
    primary_beam_result: Optional[BeamResult] = None
    secondary_beam_result: Optional[BeamResult] = None
    column_result: Optional[ColumnResult] = None
    core_wall_result: Optional[CoreWallResult] = None
    wind_result: Optional[WindResult] = None

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

        if self.load_combination == LoadCombination.ULS_GRAVITY:
            return GAMMA_G * gk + GAMMA_Q * qk
        elif self.load_combination == LoadCombination.SLS_DEFLECTION:
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
            }
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
