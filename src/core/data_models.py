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
    max_slab_span: Optional[float] = None  # Maximum slab span (m)

    def __post_init__(self):
        if self.max_slab_span is None:
            self.max_slab_span = min(self.bay_x, self.bay_y)


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
    core_dim_x: float = 0       # Core wall dimension in X (m)
    core_dim_y: float = 0       # Core wall dimension in Y (m)
    core_thickness: float = 0.3  # Core wall thickness (m)
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


@dataclass
class ColumnResult(DesignResult):
    """Column design results"""
    dimension: int = 0          # mm (square column)
    axial_load: float = 0.0     # kN
    moment: float = 0.0         # kNm
    is_slender: bool = False
    slenderness: float = 0.0


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
