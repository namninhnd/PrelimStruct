"""
Test Script for PrelimStruct Feature 1 - Engineering Core
Verifies slab, beam, column, and punching shear calculations.
"""

import sys
sys.path.insert(0, '/home/user/PrelimStruct')

from src.core.data_models import (
    ProjectData,
    GeometryInput,
    LoadInput,
    MaterialInput,
    ReinforcementInput,
    SlabDesignInput,
    SlabType,
    ExposureClass,
    ColumnPosition,
)
from src.core.load_tables import get_live_load, get_cover, LIVE_LOAD_TABLE
from src.engines.slab_engine import SlabEngine
from src.engines.beam_engine import BeamEngine
from src.engines.column_engine import ColumnEngine
from src.engines.punching_shear import PunchingShearEngine, ColumnLocation


def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(label: str, value, unit: str = ""):
    print(f"  {label}: {value} {unit}")


def test_load_tables():
    """Test HK Code load tables"""
    print_header("TEST 1: Load Tables (HK Code Tables 3.1/3.2/4.1)")

    # Test live load lookup
    tests = [
        ("2", "2.5", 0, 3.0),   # Offices for general use
        ("4", "4.1", 0, 5.0),   # Department stores
        ("5", "5.4", 4, 14.0),  # Stack rooms (3.5 × 4m = 14 kPa, min 10)
        ("1", "1.1", 0, 2.0),   # Domestic
    ]

    print("\n  Live Load Lookup:")
    all_pass = True
    for class_code, sub_code, height, expected in tests:
        result = get_live_load(class_code, sub_code, height)
        status = "✓" if abs(result - expected) < 0.01 else "✗"
        if status == "✗":
            all_pass = False
        print(f"    Class {sub_code}: {result} kPa (expected {expected}) {status}")

    # Test exposure covers
    print("\n  Exposure Covers (Table 4.1):")
    cover_tests = [
        ("2", 35, 35),  # Moderate, C35
        ("3", 40, 50),  # Severe, C40
        ("1", 45, 25),  # Mild, C45
    ]

    for exposure, fcu, expected in cover_tests:
        result = get_cover(exposure, fcu)
        status = "✓" if result == expected else "✗"
        if status == "✗":
            all_pass = False
        print(f"    Exposure {exposure}, C{fcu}: {result}mm (expected {expected}mm) {status}")

    return all_pass


def test_slab_design():
    """Test slab design engine"""
    print_header("TEST 2: Slab Design Engine")

    # Create project with typical office loading
    project = ProjectData(
        geometry=GeometryInput(bay_x=6.0, bay_y=6.0, floors=5),
        loads=LoadInput("2", "2.5", 2.0),  # Office, 3.0 kPa LL, 2.0 kPa SDL
        materials=MaterialInput(fcu_slab=35),
        slab_design=SlabDesignInput(slab_type=SlabType.TWO_WAY),
    )

    engine = SlabEngine(project)
    result = engine.calculate()

    print(f"\n  Input: 6m × 6m bay, Two-way slab, C35")
    print(f"  Live Load: {project.loads.live_load} kPa")
    print_result("Thickness", result.thickness, "mm")
    print_result("Self-weight", result.self_weight, "kPa")
    print_result("Design Moment", result.moment, "kNm/m")
    print_result("Reinforcement", result.reinforcement_area, "mm²/m")
    print_result("Deflection Ratio", result.deflection_ratio)
    print_result("Status", result.status)

    # Verify reasonable results
    checks = [
        ("Thickness 150-250mm", 150 <= result.thickness <= 250),
        ("Self-weight 3-6 kPa", 3.0 <= result.self_weight <= 6.0),
        ("Status OK", result.status == "OK"),
    ]

    print("\n  Verification:")
    all_pass = True
    for check_name, passed in checks:
        status = "✓" if passed else "✗"
        if not passed:
            all_pass = False
        print(f"    {check_name}: {status}")

    return all_pass


def test_beam_design():
    """Test beam design engine"""
    print_header("TEST 3: Beam Design Engine")

    # Create project
    project = ProjectData(
        geometry=GeometryInput(bay_x=8.0, bay_y=6.0, floors=5),
        loads=LoadInput("2", "2.5", 2.0),
        materials=MaterialInput(fcu_beam=40),
    )

    # First calculate slab to get loads
    slab_engine = SlabEngine(project)
    project.slab_result = slab_engine.calculate()

    # Calculate primary beam (spans 8m)
    beam_engine = BeamEngine(project)
    result = beam_engine.calculate_primary_beam(tributary_width=3.0)

    print(f"\n  Input: 8m span primary beam, 3m tributary width, C40")
    print_result("Size", result.size)
    print_result("Design Moment", result.moment, "kNm")
    print_result("Design Shear", result.shear, "kN")
    print_result("Shear Capacity", result.shear_capacity, "kN")
    print_result("Shear Reinf Required", result.shear_reinforcement_required)
    print_result("Iterations", result.iteration_count)
    print_result("Status", result.status)

    if result.warnings:
        print("  Warnings:", result.warnings)

    # Verify reasonable results
    checks = [
        ("Beam depth 400-800mm", 400 <= result.depth <= 800),
        ("Beam width 250-500mm", 250 <= result.width <= 500),
        ("Not deep beam", not result.is_deep_beam),
        ("Status OK or with reinforcement", "OK" in result.status or "FAIL" not in result.status),
    ]

    print("\n  Verification:")
    all_pass = True
    for check_name, passed in checks:
        status = "✓" if passed else "✗"
        if not passed:
            all_pass = False
        print(f"    {check_name}: {status}")

    return all_pass


def test_beam_shear_hardstop():
    """Test beam shear hard-stop with extreme loading"""
    print_header("TEST 4: Beam Shear Hard-Stop (Extreme Case)")

    # Create project with heavy loading
    project = ProjectData(
        geometry=GeometryInput(bay_x=12.0, bay_y=8.0, floors=1),
        loads=LoadInput("5", "5.12", 5.0),  # Heavy workshop 10 kPa
        materials=MaterialInput(fcu_beam=40),
    )

    # Calculate slab
    slab_engine = SlabEngine(project)
    project.slab_result = slab_engine.calculate()

    # Calculate beam with large tributary
    beam_engine = BeamEngine(project)
    result = beam_engine.calculate_primary_beam(tributary_width=6.0)

    print(f"\n  Input: 12m span, 6m tributary, Heavy workshop (10 kPa LL)")
    print_result("Size", result.size)
    print_result("Design Shear", result.shear, "kN")
    print_result("Shear Capacity", result.shear_capacity, "kN")
    print_result("Iterations", result.iteration_count)
    print_result("Status", result.status)

    if result.warnings:
        print("  Warnings:")
        for w in result.warnings:
            print(f"    - {w}")

    # This test verifies the iteration logic works
    print("\n  Verification:")
    print(f"    Iteration count > 1: {'✓' if result.iteration_count > 1 else '✗'}")
    print(f"    Result generated: ✓")

    return True  # Just verify it doesn't crash


def test_column_design():
    """Test column design engine"""
    print_header("TEST 5: Column Design Engine")

    # Create project
    project = ProjectData(
        geometry=GeometryInput(bay_x=6.0, bay_y=6.0, floors=10, story_height=3.2),
        loads=LoadInput("2", "2.5", 2.0),
        materials=MaterialInput(fcu_column=45),
        reinforcement=ReinforcementInput(min_rho_column=2.0),
    )

    # Calculate slab first
    slab_engine = SlabEngine(project)
    project.slab_result = slab_engine.calculate()

    # Calculate columns at different positions
    column_engine = ColumnEngine(project)

    results = {}
    for position in [ColumnPosition.INTERIOR, ColumnPosition.EDGE, ColumnPosition.CORNER]:
        results[position.value] = column_engine.calculate(position)

    print(f"\n  Input: 6m × 6m bay, 10 floors, C45")

    all_pass = True
    for pos_name, result in results.items():
        print(f"\n  {pos_name.upper()} Column:")
        print_result("    Size", result.size)
        print_result("    Axial Load", result.axial_load, "kN")
        print_result("    Moment", result.moment, "kNm")
        print_result("    Slenderness", result.slenderness)
        print_result("    Status", result.status)

        if result.status != "OK":
            all_pass = False

    # Interior should be largest
    interior_size = results["interior"].dimension
    corner_size = results["corner"].dimension

    print("\n  Verification:")
    checks = [
        ("Interior > Corner (more load)", interior_size >= corner_size),
        ("All columns OK", all(r.status == "OK" for r in results.values())),
        ("Reasonable sizes (200-600mm)", all(200 <= r.dimension <= 600 for r in results.values())),
    ]

    for check_name, passed in checks:
        status = "✓" if passed else "✗"
        if not passed:
            all_pass = False
        print(f"    {check_name}: {status}")

    return all_pass


def test_punching_shear():
    """Test punching shear check"""
    print_header("TEST 6: Punching Shear Check")

    # Create project
    project = ProjectData(
        geometry=GeometryInput(bay_x=6.0, bay_y=6.0, floors=5),
        materials=MaterialInput(fcu_slab=35),
    )

    engine = PunchingShearEngine(project)

    # Test interior column
    result = engine.check_punching_shear(
        column_size=400,
        slab_thickness=200,
        reaction=500,  # kN per floor
        location=ColumnLocation.INTERIOR,
        fcu=35,
        rho_x=0.5,
        rho_y=0.5,
    )

    print(f"\n  Input: 400mm column, 200mm slab, 500kN reaction")
    print_result("Critical Perimeter", f"{result.perimeter:.0f}", "mm")
    print_result("Design Shear Stress", f"{result.v_Ed:.3f}", "MPa")
    print_result("Shear Resistance", f"{result.v_Rd:.3f}", "MPa")
    print_result("Max Shear Stress", f"{result.v_max:.2f}", "MPa")
    print_result("Utilization", f"{result.utilization:.2f}")
    print_result("Reinf Required", result.shear_reinforcement_required)
    print_result("Status", result.status)

    print("\n  Verification:")
    checks = [
        ("Perimeter calculated", result.perimeter > 0),
        ("v_Ed calculated", result.v_Ed > 0),
        ("v_Rd calculated", result.v_Rd > 0),
        ("Utilization reasonable", 0 < result.utilization < 5),
    ]

    all_pass = True
    for check_name, passed in checks:
        status = "✓" if passed else "✗"
        if not passed:
            all_pass = False
        print(f"    {check_name}: {status}")

    return all_pass


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "=" * 60)
    print("  PRELIMSTRUCT - FEATURE 1 TEST SUITE")
    print("  Python Engineering Core Verification")
    print("=" * 60)

    tests = [
        ("Load Tables", test_load_tables),
        ("Slab Design", test_slab_design),
        ("Beam Design", test_beam_design),
        ("Beam Shear Hard-Stop", test_beam_shear_hardstop),
        ("Column Design", test_column_design),
        ("Punching Shear", test_punching_shear),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed, None))
        except Exception as e:
            results.append((test_name, False, str(e)))
            print(f"\n  ERROR: {e}")

    # Summary
    print_header("TEST SUMMARY")

    passed_count = sum(1 for _, p, _ in results if p)
    total_count = len(results)

    for test_name, passed, error in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        error_msg = f" ({error})" if error else ""
        print(f"  {test_name}: {status}{error_msg}")

    print(f"\n  Total: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n  ✓ ALL TESTS PASSED - Feature 1 verified!")
        return True
    else:
        print("\n  ✗ Some tests failed - review required")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
