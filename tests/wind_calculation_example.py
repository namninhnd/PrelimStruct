"""
WIND LOAD CALCULATION - DETAILED EXAMPLE WITH FLOWCHART
Complete worked example showing all formulas and calculations step-by-step
"""

import sys
import os
import math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.data_models import (
    ProjectData,
    GeometryInput,
    LoadInput,
    MaterialInput,
    LateralInput,
    TerrainCategory,
)
from src.engines.wind_engine import WindEngine, CoreWallEngine, DriftEngine


def print_section(title):
    """Print section header"""
    print(f"\n{'='*80}")
    print(f"{title:^80}")
    print(f"{'='*80}\n")


def print_flowchart():
    """Display wind load calculation flowchart"""
    flowchart = """
┌─────────────────────────────────────────────────────────────────────────────┐
│                    WIND LOAD CALCULATION FLOWCHART                          │
│                         (HK Wind Code 2019)                                 │
└─────────────────────────────────────────────────────────────────────────────┘

    START
      │
      ▼
┌──────────────────────┐
│  INPUT PARAMETERS    │
│  - Building Height   │
│  - Building Width    │
│  - Building Depth    │
│  - Terrain Category  │
│  - Core Dimensions   │
│  - Material (fcu)    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│  STEP 1: Reference Wind Pressure                     │
│                                                       │
│  V_ref = 55 m/s (HK 50-year return period)          │
│  ρ_air = 1.2 kg/m³                                   │
│                                                       │
│  q_ref = 0.5 × ρ × V_ref²                           │
│        = 0.5 × 1.2 × 55²                            │
│        = 1.815 kPa                                   │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│  STEP 2: Topography Factor                           │
│                                                       │
│  Sa = 1.0 (flat terrain assumed)                     │
│                                                       │
│  Note: Sa > 1.0 for hills/escarpments                │
│        (requires site-specific assessment)           │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│  STEP 3: Exposure Factor at Height z                 │
│                                                       │
│  Sd(z) = (z / z_ref)^(2α)                            │
│                                                       │
│  where: z_ref = 10 m                                 │
│         α = terrain-dependent exponent:              │
│           • Open Sea (A):     α = 0.11               │
│           • Open Country (B): α = 0.15               │
│           • Urban (C):        α = 0.22               │
│           • City Centre (D):  α = 0.30               │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│  STEP 4: Design Wind Pressure                        │
│                                                       │
│  q_design = q_ref × Sa × Sd                          │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│  STEP 5: Force Coefficient                           │
│                                                       │
│  Cf = force coefficient (building shape)             │
│     = 1.2 (H/W < 1)  - Low rise                     │
│     = 1.3 (1 < H/W < 4) - Medium rise               │
│     = 1.4 (H/W > 4)  - High rise/slender            │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│  STEP 6: Base Shear                                  │
│                                                       │
│  A_exposed = Height × Width                          │
│  V_wind = q_design × Cf × A_exposed                  │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│  STEP 7: Overturning Moment                          │
│                                                       │
│  Moment_arm = 0.6 × Height                           │
│  M_wind = V_wind × Moment_arm                        │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│  STEP 8: Core Wall Stress Check                      │
│                                                       │
│  • Compression: σ = P/A + My/I < 0.45fcu            │
│  • Tension: σ_min = P/A - My/I (check uplift)       │
│  • Shear: v = 1.5V/A < 0.8√fcu                      │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│  STEP 9: Drift Check                                 │
│                                                       │
│  E_c = 4700√fcu                                      │
│  I = (Lx × Ly³) / 12                                │
│  V_SLS = V_wind / 1.4                                │
│                                                       │
│  Δ = (V_SLS × H³) / (3 × E × I)                     │
│                                                       │
│  Drift Index = Δ/H < 1/500 ✓                        │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
                  END
                (Results)
"""
    print(flowchart)


def main():
    """Run detailed wind load calculation example"""

    print_section("WIND LOAD CALCULATION - WORKED EXAMPLE")
    print_flowchart()

    print_section("TEST CASE: 20-STORY OFFICE BUILDING")

    # Define test case
    project = ProjectData(
        project_name="20-Story Office Building - Urban Site",
        geometry=GeometryInput(
            bay_x=8.0,
            bay_y=8.0,
            floors=20,
            story_height=3.5
        ),
        loads=LoadInput("2", "2.5", 2.0),  # Office loading
        materials=MaterialInput(
            fcu_slab=35,
            fcu_beam=40,
            fcu_column=45,
            fy=500
        ),
        lateral=LateralInput(
            building_width=24.0,
            building_depth=24.0,
            terrain=TerrainCategory.URBAN,
            core_dim_x=8.0,
            core_dim_y=8.0,
            core_thickness=0.35
        )
    )

    # Display inputs
    print("INPUT PARAMETERS:")
    print(f"  Building Height: {project.geometry.floors} floors × {project.geometry.story_height} m = {project.geometry.floors * project.geometry.story_height} m")
    print(f"  Building Width: {project.lateral.building_width} m")
    print(f"  Building Depth: {project.lateral.building_depth} m")
    print(f"  Terrain: {project.lateral.terrain.value} (Urban)")
    print(f"  Core Dimensions: {project.lateral.core_dim_x} × {project.lateral.core_dim_y} m")
    print(f"  Core Thickness: {project.lateral.core_thickness * 1000} mm")
    print(f"  Concrete Grade: fcu = {project.materials.fcu_column} MPa")

    # Calculate wind loads
    print_section("STEP-BY-STEP CALCULATIONS")

    wind_engine = WindEngine(project)

    # Manual calculations for verification
    height = project.geometry.floors * project.geometry.story_height
    width = project.lateral.building_width
    depth = project.lateral.building_depth

    print("STEP 1: Reference Wind Pressure")
    print("─" * 80)
    V_ref = 55.0  # m/s
    rho = 1.2  # kg/m³
    q_ref = 0.5 * rho * (V_ref ** 2) / 1000  # kPa
    print(f"  V_ref = {V_ref} m/s (HK Wind Code 2019 - 50 year return)")
    print(f"  ρ_air = {rho} kg/m³")
    print(f"  q_ref = 0.5 × ρ × V_ref²")
    print(f"        = 0.5 × {rho} × {V_ref}²")
    print(f"        = {q_ref:.3f} kPa ✓")

    print("\nSTEP 2: Topography Factor")
    print("─" * 80)
    Sa = 1.0
    print(f"  Sa = {Sa} (flat terrain assumed)")
    print(f"  Note: For hills/escarpments, Sa > 1.0 (site-specific)")

    print("\nSTEP 3: Exposure Factor")
    print("─" * 80)
    alpha = 0.22  # Urban terrain
    z_ref = 10.0
    z_min = 5.0
    z_eff = max(height, z_min)
    Sd = (z_eff / z_ref) ** (2 * alpha)
    print(f"  Terrain: URBAN (Category C)")
    print(f"  α = {alpha} (terrain exponent)")
    print(f"  z_ref = {z_ref} m")
    print(f"  z_min = {z_min} m")
    print(f"  z_eff = max(H, z_min) = max({height}, {z_min}) = {z_eff} m")
    print(f"  Sd(z) = (z_eff / z_ref)^(2α)")
    print(f"        = ({z_eff} / {z_ref})^(2 × {alpha})")
    print(f"        = ({z_eff / z_ref})^{2*alpha}")
    print(f"        = {Sd:.3f} ✓")

    print("\nSTEP 4: Design Wind Pressure")
    print("─" * 80)
    q_design = q_ref * Sa * Sd
    print(f"  q_design = q_ref × Sa × Sd")
    print(f"           = {q_ref:.3f} × {Sa} × {Sd:.3f}")
    print(f"           = {q_design:.3f} kPa ✓")

    print("\nSTEP 5: Force Coefficient")
    print("─" * 80)
    aspect_ratio = height / width
    if aspect_ratio < 1.0:
        Cf = 1.2
    elif aspect_ratio < 4.0:
        Cf = 1.3
    else:
        Cf = 1.4
    print(f"  Aspect ratio = H/W = {height}/{width} = {aspect_ratio:.2f}")
    print(f"  Cf = {Cf} (medium-rise rectangular building) ✓")

    print("\nSTEP 6: Base Shear")
    print("─" * 80)
    A_exposed = height * width
    V_wind = q_design * Cf * A_exposed
    print(f"  A_exposed = H × W")
    print(f"            = {height} × {width}")
    print(f"            = {A_exposed} m²")
    print(f"  V_wind = q_design × Cf × A_exposed")
    print(f"         = {q_design:.3f} × {Cf} × {A_exposed}")
    print(f"         = {V_wind:.1f} kN ✓")

    print("\nSTEP 7: Overturning Moment")
    print("─" * 80)
    moment_arm = 0.6 * height
    M_wind = V_wind * moment_arm
    print(f"  Moment arm = 0.6 × H")
    print(f"             = 0.6 × {height}")
    print(f"             = {moment_arm} m")
    print(f"  M_wind = V_wind × moment_arm")
    print(f"         = {V_wind:.1f} × {moment_arm}")
    print(f"         = {M_wind:.1f} kNm ✓")

    # Run engine calculations
    wind_result = wind_engine.calculate_wind_loads()

    print_section("CORE WALL STRESS CHECK")

    core_engine = CoreWallEngine(project)
    core_result = core_engine.check_core_wall(wind_result)

    L_x = project.lateral.core_dim_x
    L_y = project.lateral.core_dim_y
    t = project.lateral.core_thickness
    fcu = project.materials.fcu_column

    print("CORE WALL PROPERTIES:")
    print(f"  Dimensions: {L_x} × {L_y} m")
    print(f"  Thickness: {t*1000} mm")
    print(f"  Concrete: fcu = {fcu} MPa")

    # Simplified calculation
    A_gross = L_x * L_y
    I_yy = (L_y * L_x ** 3) / 12
    y_max = L_y / 2

    # Axial load (simplified)
    tributary_area = project.tributary_area
    gk = project.total_dead_load
    qk = project.total_live_load
    load_per_floor = tributary_area * (1.4 * gk + 1.6 * qk)
    P = load_per_floor * project.geometry.floors * 0.2

    print(f"\nGEOMETRIC PROPERTIES:")
    print(f"  A_gross = L_x × L_y = {L_x} × {L_y} = {A_gross} m²")
    print(f"  I_yy = (L_y × L_x³) / 12 = ({L_y} × {L_x}³) / 12 = {I_yy:.3f} m⁴")
    print(f"  y_max = L_y / 2 = {L_y} / 2 = {y_max} m")

    print(f"\nAXIAL LOAD:")
    print(f"  P = {P:.0f} kN (gravity on core, ~20% of total)")

    print(f"\nSTRESS CHECKS:")

    # Compression
    sigma_comp = (P * 1000) / (A_gross * 1e6) + (M_wind * 1e6 * y_max) / (I_yy * 1e12)
    sigma_allow = 0.45 * fcu
    comp_util = sigma_comp / sigma_allow

    print(f"\n1. COMPRESSION CHECK:")
    print(f"   σ_max = P/A + My/I")
    print(f"         = {P}×10³ / ({A_gross}×10⁶) + {M_wind}×10⁶×{y_max} / ({I_yy:.3f}×10¹²)")
    print(f"         = {sigma_comp:.2f} MPa")
    print(f"   σ_allow = 0.45 × fcu = 0.45 × {fcu} = {sigma_allow:.2f} MPa")
    print(f"   Utilization = {sigma_comp:.2f} / {sigma_allow:.2f} = {comp_util:.3f}")
    print(f"   Status: {'✓ OK' if comp_util <= 1.0 else '✗ FAIL'}")

    # Tension
    sigma_tens = (P * 1000) / (A_gross * 1e6) - (M_wind * 1e6 * y_max) / (I_yy * 1e12)
    print(f"\n2. TENSION CHECK:")
    print(f"   σ_min = P/A - My/I")
    print(f"         = {P}×10³ / ({A_gross}×10⁶) - {M_wind}×10⁶×{y_max} / ({I_yy:.3f}×10¹²)")
    print(f"         = {sigma_tens:.2f} MPa")
    if sigma_tens < 0:
        print(f"   Status: ⚠ TENSION - Tension piles required")
    else:
        print(f"   Status: ✓ OK - No uplift")

    # Shear
    A_shear = 2 * L_y * t
    v_actual = (1.5 * V_wind * 1000) / (A_shear * 1e6)
    v_allow = 0.8 * math.sqrt(fcu)
    shear_util = v_actual / v_allow

    print(f"\n3. SHEAR CHECK:")
    print(f"   A_shear = 2 × L_y × t = 2 × {L_y} × {t} = {A_shear:.3f} m²")
    print(f"   v = 1.5 × V / A_shear")
    print(f"     = 1.5 × {V_wind:.1f}×10³ / ({A_shear:.3f}×10⁶)")
    print(f"     = {v_actual:.3f} MPa")
    print(f"   v_allow = 0.8 × √fcu = 0.8 × √{fcu} = {v_allow:.2f} MPa")
    print(f"   Utilization = {v_actual:.3f} / {v_allow:.2f} = {shear_util:.3f}")
    print(f"   Status: {'✓ OK' if shear_util <= 1.0 else '✗ FAIL'}")

    print_section("DRIFT CHECK")

    drift_engine = DriftEngine(project)
    final_wind_result = drift_engine.calculate_drift(wind_result)

    E_c = 4700 * math.sqrt(fcu)
    I = (L_x * L_y ** 3) / 12
    V_service = V_wind / 1.4

    print("DRIFT CALCULATION:")
    print(f"  Formula: Δ = (V × H³) / (3 × E × I)")
    print(f"  (Cantilever beam with point load at tip)\n")

    print(f"  E_c = 4700 × √fcu")
    print(f"      = 4700 × √{fcu}")
    print(f"      = {E_c:.0f} MPa\n")

    print(f"  I = (L_x × L_y³) / 12")
    print(f"    = ({L_x} × {L_y}³) / 12")
    print(f"    = {I:.3f} m⁴\n")

    print(f"  V_service = V_wind / 1.4 (SLS load factor)")
    print(f"            = {V_wind:.1f} / 1.4")
    print(f"            = {V_service:.1f} kN\n")

    delta_m = (V_service * 1000 * (height ** 3)) / (3 * E_c * 1e6 * I)
    delta_mm = delta_m * 1000
    drift_index = delta_m / height
    drift_limit = 1.0 / 500.0

    print(f"  UNIT CONVERSIONS:")
    print(f"    V_service: {V_service:.1f} kN × 1000 = {V_service*1000:.0f} N")
    print(f"    E_c: {E_c:.0f} MPa × 10⁶ = {E_c*1e6:.0f} Pa (N/m²)")
    print(f"    H³: {height}³ = {height**3} m³\n")

    numerator = V_service * 1000 * (height ** 3)
    denominator = 3 * E_c * 1e6 * I

    print(f"  CALCULATION:")
    print(f"    Numerator = {V_service*1000:.0f} N × {height**3} m³")
    print(f"              = {numerator:.2e} N·m³")
    print(f"    Denominator = 3 × {E_c*1e6:.0f} Pa × {I:.3f} m⁴")
    print(f"                = {denominator:.2e} N·m²\n")

    print(f"    Δ = {numerator:.2e} / {denominator:.2e}")
    print(f"      = {delta_m:.6f} m")
    print(f"      = {delta_mm:.1f} mm ✓\n")

    print(f"  DRIFT INDEX:")
    print(f"    Δ/H = {delta_mm:.1f}mm / {height*1000:.0f}mm")
    print(f"        = {drift_index:.5f}")
    print(f"    Limit = 1/500 = {drift_limit:.5f}")
    print(f"    Status: {'✓ OK' if drift_index <= drift_limit else '✗ FAIL - Increase core stiffness'}\n")

    print_section("FINAL RESULTS SUMMARY")

    print(f"WIND LOADS:")
    print(f"  Reference Pressure: {wind_result.reference_pressure:.3f} kPa")
    print(f"  Design Pressure: {q_design:.3f} kPa")
    print(f"  Base Shear: {wind_result.base_shear:.1f} kN")
    print(f"  Overturning Moment: {wind_result.overturning_moment:.1f} kNm\n")

    print(f"CORE WALL CAPACITY:")
    print(f"  Status: {core_result.status}")
    print(f"  Compression Utilization: {core_result.compression_check:.3f}")
    print(f"  Shear Utilization: {core_result.shear_check:.3f}")
    print(f"  Tension Check: {core_result.tension_check:.2f} MPa")
    print(f"  Tension Piles Required: {'Yes' if core_result.requires_tension_piles else 'No'}\n")

    print(f"DRIFT CHECK:")
    print(f"  Lateral Drift: {final_wind_result.drift_mm:.1f} mm")
    print(f"  Drift Index: {final_wind_result.drift_index:.5f}")
    print(f"  Limit: {drift_limit:.5f}")
    print(f"  Status: {'✓ OK' if final_wind_result.drift_ok else '✗ FAIL'}\n")

    overall_ok = (core_result.status == "OK" and final_wind_result.drift_ok)
    print(f"OVERALL DESIGN STATUS: {'✓✓✓ PASS ✓✓✓' if overall_ok else '✗✗✗ FAIL ✗✗✗'}")

    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
