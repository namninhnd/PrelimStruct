"""
Wind Load Calculator - HK Wind Code 2019 Compliant
Calculates wind pressure, base shear, and overturning moment.
"""

import math
from typing import Dict, Any, List, Tuple

from ..core.data_models import (
    ProjectData,
    WindResult,
    TerrainCategory,
)


class WindEngine:
    """
    Wind load calculator per HK Wind Code 2019.
    Implements reference pressure, topography, and exposure factors.
    """

    # HK Wind Code 2019 - Basic wind speed (m/s) for Hong Kong
    V_REF = 55.0  # 3-second gust speed with 50-year return period

    # Terrain roughness parameters per HK Wind Code 2019
    TERRAIN_PARAMS = {
        TerrainCategory.OPEN_SEA: {"z0": 0.005, "z_min": 1.0, "alpha": 0.11},
        TerrainCategory.OPEN_COUNTRY: {"z0": 0.03, "z_min": 2.0, "alpha": 0.15},
        TerrainCategory.URBAN: {"z0": 0.3, "z_min": 5.0, "alpha": 0.22},
        TerrainCategory.CITY_CENTRE: {"z0": 1.0, "z_min": 10.0, "alpha": 0.30},
    }

    def __init__(self, project: ProjectData):
        self.project = project
        self.calculations: List[Dict[str, Any]] = []

    def _add_calc_step(self, description: str, calculation: str, reference: str = ""):
        """Add a calculation step to the audit trail"""
        self.calculations.append({
            "description": description,
            "calculation": calculation,
            "reference": reference
        })

    def calculate_wind_loads(self) -> WindResult:
        """
        Main calculation method for wind loads.
        Returns WindResult with base shear and overturning moment.
        """
        self.calculations = []

        geometry = self.project.geometry
        lateral = self.project.lateral

        # Building dimensions
        height = geometry.floors * geometry.story_height
        width = lateral.building_width if lateral.building_width > 0 else geometry.bay_x * 3
        depth = lateral.building_depth if lateral.building_depth > 0 else geometry.bay_y * 3

        self._add_calc_step(
            "WIND LOAD CALCULATION - HK Wind Code 2019",
            f"Building Height: {height:.1f} m\n"
            f"Building Width: {width:.1f} m\n"
            f"Building Depth: {depth:.1f} m\n"
            f"Terrain: {lateral.terrain.value}",
            "HK Wind Code 2019"
        )

        # Step 1: Calculate reference wind pressure
        q_ref = self._calculate_reference_pressure()

        # Step 2: Calculate topography factor (Sa)
        Sa = self._calculate_topography_factor()

        # Step 3: Calculate exposure factor at building height (Sd)
        Sd = self._calculate_exposure_factor(height, lateral.terrain)

        # Step 4: Calculate design wind pressure
        q_design = q_ref * Sa * Sd

        self._add_calc_step(
            "Design wind pressure",
            f"q_design = q_ref × Sa × Sd\n"
            f"q_design = {q_ref:.3f} × {Sa:.2f} × {Sd:.2f} = {q_design:.3f} kPa",
            "HK Wind Code 2019 - Clause 5.3"
        )

        # Step 5: Calculate force coefficient (Cf) for rectangular building
        # Assume along-wind direction (Cf ≈ 1.2-1.3 for rectangular buildings)
        Cf = self._calculate_force_coefficient(height, width, depth)

        # Step 6: Calculate base shear
        # V = q × Cf × A_exposed (where A_exposed = height × width)
        A_exposed = height * width
        V_wind = q_design * Cf * A_exposed

        self._add_calc_step(
            "Base shear calculation",
            f"A_exposed = H × W = {height:.1f} × {width:.1f} = {A_exposed:.1f} m²\n"
            f"Cf = {Cf:.2f} (force coefficient)\n"
            f"V_wind = q_design × Cf × A_exposed\n"
            f"V_wind = {q_design:.3f} × {Cf:.2f} × {A_exposed:.1f} = {V_wind:.1f} kN",
            "HK Wind Code 2019 - Clause 6.2"
        )

        # Step 7: Calculate overturning moment at base
        # Simplified approach: M = V × H/2 (assuming triangular distribution)
        # More accurate: M = V × 0.6H (considering actual pressure distribution)
        moment_arm = 0.6 * height  # Centroid of wind pressure
        M_wind = V_wind * moment_arm

        self._add_calc_step(
            "Overturning moment at base",
            f"Moment arm = 0.6 × H = 0.6 × {height:.1f} = {moment_arm:.1f} m\n"
            f"M_wind = V_wind × moment_arm\n"
            f"M_wind = {V_wind:.1f} × {moment_arm:.1f} = {M_wind:.1f} kNm",
            "HK Wind Code 2019 - Simplified method"
        )

        return WindResult(
            base_shear=round(V_wind, 1),
            overturning_moment=round(M_wind, 1),
            reference_pressure=round(q_ref, 3),
            drift_index=0.0,  # Will be calculated in drift check
            drift_ok=True,
        )

    def _calculate_reference_pressure(self) -> float:
        """
        Calculate reference wind pressure q_ref.
        q_ref = 0.5 × ρ × V_ref²
        where ρ = 1.2 kg/m³ (air density)
        """
        rho_air = 1.2  # kg/m³
        q_ref = 0.5 * rho_air * (self.V_REF ** 2) / 1000  # Convert to kPa

        self._add_calc_step(
            "Reference wind pressure",
            f"V_ref = {self.V_REF} m/s (50-year return period)\n"
            f"ρ_air = {rho_air} kg/m³\n"
            f"q_ref = 0.5 × ρ × V_ref²\n"
            f"q_ref = 0.5 × {rho_air} × {self.V_REF}² = {q_ref:.3f} kPa",
            "HK Wind Code 2019 - Clause 5.2"
        )

        return q_ref

    def _calculate_topography_factor(self) -> float:
        """
        Calculate topography factor Sa.
        For flat terrain or typical HK urban sites: Sa = 1.0
        For hills/cliffs: Sa can be > 1.0 (requires site-specific assessment)
        """
        Sa = 1.0  # Conservative assumption for typical sites

        self._add_calc_step(
            "Topography factor",
            f"Sa = {Sa:.2f} (flat terrain assumed)\n"
            f"Note: Site-specific assessment required for hills/escarpments",
            "HK Wind Code 2019 - Clause 5.4"
        )

        return Sa

    def _calculate_exposure_factor(self, height: float, terrain: TerrainCategory) -> float:
        """
        Calculate exposure factor Sd at height z.
        Sd(z) = (z / z_ref)^(2*alpha) for z ≥ z_min
        where z_ref = 10m, alpha depends on terrain category
        """
        params = self.TERRAIN_PARAMS[terrain]
        z_min = params["z_min"]
        alpha = params["alpha"]
        z_ref = 10.0  # Reference height

        # Use effective height (minimum z_min)
        z_eff = max(height, z_min)

        # Exposure factor
        Sd = (z_eff / z_ref) ** (2 * alpha)

        self._add_calc_step(
            "Exposure factor at building height",
            f"Terrain: {terrain.value} (alpha = {alpha:.2f})\n"
            f"z_eff = max(H, z_min) = max({height:.1f}, {z_min}) = {z_eff:.1f} m\n"
            f"Sd(z) = (z / z_ref)^(2α)\n"
            f"Sd = ({z_eff:.1f} / {z_ref})^(2 × {alpha:.2f}) = {Sd:.3f}",
            "HK Wind Code 2019 - Clause 5.5"
        )

        return Sd

    def _calculate_force_coefficient(
        self, height: float, width: float, depth: float
    ) -> float:
        """
        Calculate force coefficient Cf for rectangular building.
        Depends on aspect ratio and wind direction.
        Typical values: 1.2-1.4 for tall buildings.
        """
        # Aspect ratio (height to width)
        aspect_ratio = height / width

        # Base force coefficient
        if aspect_ratio < 1.0:
            Cf = 1.2  # Low-rise buildings
        elif aspect_ratio < 4.0:
            Cf = 1.3  # Medium-rise buildings
        else:
            Cf = 1.4  # Tall/slender buildings

        self._add_calc_step(
            "Force coefficient",
            f"Aspect ratio = H/W = {height:.1f}/{width:.1f} = {aspect_ratio:.2f}\n"
            f"Cf = {Cf:.2f} (rectangular building, along-wind)",
            "HK Wind Code 2019 - Clause 6.2"
        )

        return Cf


class CoreWallEngine:
    """
    Core wall stress checker.
    Verifies compression, tension, and shear capacity.
    """

    def __init__(self, project: ProjectData):
        self.project = project
        self.calculations: List[Dict[str, Any]] = []

    def _add_calc_step(self, description: str, calculation: str, reference: str = ""):
        """Add a calculation step to the audit trail"""
        self.calculations.append({
            "description": description,
            "calculation": calculation,
            "reference": reference
        })

    def check_core_wall(self, wind_result: WindResult):
        """
        Check core wall capacity under wind loads.
        Returns CoreWallResult with compression, tension, and shear checks.
        """
        from ..core.data_models import CoreWallResult

        self.calculations = []

        lateral = self.project.lateral
        geometry = self.project.geometry
        materials = self.project.materials

        # Core wall dimensions
        L_x = lateral.core_dim_x
        L_y = lateral.core_dim_y
        t = lateral.core_thickness

        if L_x <= 0 or L_y <= 0 or t <= 0:
            return CoreWallResult(
                element_type="Core Wall",
                size="NOT DEFINED",
                utilization=0.0,
                status="NOT DEFINED",
                warnings=["Core wall dimensions not specified"],
                calculations=self.calculations,
            )

        self._add_calc_step(
            "CORE WALL STRESS CHECK",
            f"Core dimensions: {L_x:.2f} × {L_y:.2f} m\n"
            f"Wall thickness: {t:.3f} m\n"
            f"Concrete grade: fcu = {materials.fcu_column} MPa",
            "HK Code 2013 - Clause 6.2"
        )

        # Calculate core wall properties
        # Simplified as rectangular hollow section
        A_gross = L_x * L_y  # Gross area (conservative, doesn't subtract opening)

        # Second moment of area (assuming symmetric core)
        I_xx = (L_x * L_y ** 3) / 12  # Bending about X-axis (wind in Y direction)
        I_yy = (L_y * L_x ** 3) / 12  # Bending about Y-axis (wind in X direction)

        # Distance to extreme fiber
        y_max = L_y / 2
        x_max = L_x / 2

        # Axial load (gravity load on core)
        # Simplified: assume core carries 20% of building gravity load
        tributary_area = self.project.tributary_area
        gk = self.project.total_dead_load
        qk = self.project.total_live_load

        # ULS gravity load per floor
        load_per_floor = tributary_area * (1.4 * gk + 1.6 * qk)
        P = load_per_floor * geometry.floors * 0.2  # Core carries 20%

        self._add_calc_step(
            "Axial load on core wall",
            f"Tributary area = {tributary_area:.1f} m²\n"
            f"Load per floor = {load_per_floor:.1f} kN\n"
            f"P = {load_per_floor:.1f} × {geometry.floors} floors × 0.20 = {P:.1f} kN\n"
            f"(Assuming core carries 20% of gravity load)",
            "Simplified approach"
        )

        # Overturning moment from wind
        M_wind = wind_result.overturning_moment

        # === COMPRESSION CHECK ===
        # Maximum compressive stress: σ_max = P/A + M*y/I
        sigma_compression = (P * 1000) / (A_gross * 1e6) + (M_wind * 1e6 * y_max) / (I_yy * 1e12)

        # Allowable stress: 0.45 × fcu (simplified)
        sigma_allow = 0.45 * materials.fcu_column
        compression_util = sigma_compression / sigma_allow

        self._add_calc_step(
            "Maximum compression check",
            f"A_gross = {A_gross:.2f} m²\n"
            f"I_yy = {I_yy:.3f} m⁴\n"
            f"σ_max = P/A + M×y/I\n"
            f"σ_max = {P:.0f}×10³/({A_gross:.2f}×10⁶) + {M_wind:.0f}×10⁶×{y_max:.2f}/({I_yy:.3f}×10¹²)\n"
            f"σ_max = {sigma_compression:.2f} MPa\n"
            f"σ_allow = 0.45 × fcu = 0.45 × {materials.fcu_column} = {sigma_allow:.2f} MPa\n"
            f"Utilization = {compression_util:.3f}",
            "HK Code 2013 - Clause 6.2.4"
        )

        # === TENSION CHECK ===
        # Minimum stress (tension): σ_min = P/A - M*y/I
        sigma_tension = (P * 1000) / (A_gross * 1e6) - (M_wind * 1e6 * y_max) / (I_yy * 1e12)
        requires_tension_piles = sigma_tension < 0

        self._add_calc_step(
            "Tension/uplift check",
            f"σ_min = P/A - M×y/I\n"
            f"σ_min = {P:.0f}×10³/({A_gross:.2f}×10⁶) - {M_wind:.0f}×10⁶×{y_max:.2f}/({I_yy:.3f}×10¹²)\n"
            f"σ_min = {sigma_tension:.2f} MPa\n"
            f"{'TENSION - Tension piles required' if requires_tension_piles else 'OK - No uplift'}",
            "Foundation design consideration"
        )

        # === SHEAR CHECK ===
        # Base shear from wind
        V_wind = wind_result.base_shear

        # Shear area (approximate as web area)
        A_shear = 2 * L_y * t  # Two webs perpendicular to wind

        # Shear stress
        v_actual = (1.5 * V_wind * 1000) / (A_shear * 1e6)  # 1.5 factor for rectangular section

        # Allowable shear stress: 0.8 × sqrt(fcu)
        v_allow = 0.8 * math.sqrt(materials.fcu_column)
        shear_util = v_actual / v_allow

        self._add_calc_step(
            "Shear capacity check",
            f"V_wind = {V_wind:.1f} kN\n"
            f"A_shear = 2 × {L_y:.2f} × {t:.3f} = {A_shear:.3f} m²\n"
            f"v = 1.5 × V / A_shear\n"
            f"v = 1.5 × {V_wind:.1f} × 10³ / ({A_shear:.3f} × 10⁶) = {v_actual:.3f} MPa\n"
            f"v_allow = 0.8 × √fcu = 0.8 × √{materials.fcu_column} = {v_allow:.2f} MPa\n"
            f"Utilization = {shear_util:.3f}",
            "HK Code 2013 - Clause 6.1.2"
        )

        # Determine overall status
        max_util = max(compression_util, shear_util)
        status = "OK"
        warnings = []

        if compression_util > 1.0:
            status = "FAIL"
            warnings.append(f"Compression stress exceeds limit (util={compression_util:.2f})")
            warnings.append("Increase core dimensions or use higher grade concrete")

        if shear_util > 1.0:
            status = "FAIL"
            warnings.append(f"Shear stress exceeds limit (util={shear_util:.2f})")
            warnings.append("Increase core wall thickness")

        if requires_tension_piles:
            warnings.append("Tension piles required to resist uplift forces")

        if compression_util < 0.5 and shear_util < 0.5:
            warnings.append("Core wall appears oversized - consider optimization")

        return CoreWallResult(
            element_type="Core Wall",
            size=f"{L_x:.2f} × {L_y:.2f} m, t={int(t*1000)}mm",
            utilization=round(max_util, 3),
            status=status,
            warnings=warnings,
            calculations=self.calculations,
            compression_check=round(compression_util, 3),
            tension_check=round(sigma_tension, 2),
            shear_check=round(shear_util, 3),
            requires_tension_piles=requires_tension_piles,
        )


class DriftEngine:
    """
    Building drift checker.
    Calculates lateral displacement and checks serviceability limits.
    """

    def __init__(self, project: ProjectData):
        self.project = project
        self.calculations: List[Dict[str, Any]] = []

    def _add_calc_step(self, description: str, calculation: str, reference: str = ""):
        """Add a calculation step to the audit trail"""
        self.calculations.append({
            "description": description,
            "calculation": calculation,
            "reference": reference
        })

    def calculate_drift(self, wind_result: WindResult) -> WindResult:
        """
        Calculate building drift index and check against limits.
        Updates and returns WindResult with drift information.
        """
        self.calculations = []

        geometry = self.project.geometry
        lateral = self.project.lateral
        materials = self.project.materials

        height = geometry.floors * geometry.story_height
        L_x = lateral.core_dim_x
        L_y = lateral.core_dim_y

        if L_x <= 0 or L_y <= 0:
            # Cannot calculate drift without core dimensions
            wind_result.drift_mm = 0.0
            wind_result.drift_index = 0.0
            wind_result.drift_ok = False
            return wind_result

        self._add_calc_step(
            "BUILDING DRIFT CHECK",
            f"Building height: {height:.1f} m\n"
            f"Core dimensions: {L_x:.2f} × {L_y:.2f} m\n"
            f"Base shear: {wind_result.base_shear:.1f} kN",
            "HK Code 2013 - Serviceability limit"
        )

        # Simplified drift calculation using cantilever beam theory
        # Δ = (V × H³) / (3 × E × I)

        # Modulus of elasticity
        E_c = 4700 * math.sqrt(materials.fcu_column)  # MPa

        # Second moment of area (bending about minor axis)
        I = (L_x * L_y ** 3) / 12  # m⁴

        # Use serviceability wind load (unfactored, reduced)
        V_service = wind_result.base_shear / 1.4  # Reduce from ULS to SLS

        # Top displacement (m)
        # Δ = (V × H³) / (3 × E × I)
        # Units: V in kN, H in m, E in MPa (= N/mm² = 10⁶ N/m²), I in m⁴
        delta = (V_service * 1000 * (height ** 3)) / (3 * E_c * 1e6 * I)

        # Convert to mm for output
        drift_mm = delta * 1000

        # Drift index (Δ/H)
        drift_index = delta / height

        # Limit: Δ/H < 1/500 (typical serviceability limit)
        drift_limit = 1.0 / 500.0
        drift_ok = drift_index <= drift_limit

        self._add_calc_step(
            "Cantilever deflection calculation",
            f"E_c = 4700√fcu = 4700√{materials.fcu_column} = {E_c:.0f} MPa\n"
            f"I = (L_x × L_y³) / 12 = ({L_x:.2f} × {L_y:.2f}³) / 12 = {I:.3f} m⁴\n"
            f"V_service = {V_service:.1f} kN (SLS wind load)\n"
            f"Δ = (V × H³) / (3 × E × I)\n"
            f"Δ = ({V_service:.1f}×10³ N × {height:.1f}³ m³) / (3 × {E_c:.0f}×10⁶ Pa × {I:.3f} m⁴)\n"
            f"Δ = {drift_mm:.1f} mm",
            "Simplified cantilever beam theory"
        )

        self._add_calc_step(
            "Drift index check",
            f"Drift index = Δ/H = {drift_mm:.1f}mm / {height*1000:.0f}mm = {drift_index:.5f}\n"
            f"Limit = H/500 = {drift_limit:.5f}\n"
            f"Status: {'OK' if drift_ok else 'FAIL - Increase core stiffness'}",
            "HK Code 2013 - Serviceability (Δ/H < 1/500)"
        )

        # Update wind result with drift information
        wind_result.drift_mm = round(drift_mm, 1)
        wind_result.drift_index = round(drift_index, 5)
        wind_result.drift_ok = drift_ok

        return wind_result
