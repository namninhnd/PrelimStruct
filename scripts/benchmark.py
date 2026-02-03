"""
Performance benchmarking for PrelimStruct v3.5 FEM Analysis.

Measures analysis time and memory usage for 10/20/30 floor buildings to verify
performance targets per PRD.md Success Criteria.

Target: <30 seconds for 30-story building (conservative limit: <60s)

Usage:
    python scripts/benchmark.py --floors 30 --timeout 60
    python scripts/benchmark.py --all
"""

import argparse
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Dict, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.data_models import (
    ProjectData,
    GeometryInput,
    LoadInput,
    MaterialInput,
    CoreWallConfig,
    CoreWallGeometry,
    TerrainCategory,
    ExposureClass,
    LateralInput,
)
from src.fem.model_builder import build_fem_model, ModelBuilderOptions
from src.fem.solver import analyze_model, AnalysisResult


def create_test_building(num_floors: int) -> ProjectData:
    """Create a test building configuration for benchmarking.
    
    Args:
        num_floors: Number of floors (10, 20, or 30)
    
    Returns:
        ProjectData with standard test configuration
    """
    return ProjectData(
        project_name=f"Benchmark {num_floors} Floors",
        project_number=f"BENCH-{num_floors}",
        engineer="Benchmark Test",
        geometry=GeometryInput(
            bay_x=8.0,
            bay_y=8.0,
            num_bays_x=3,
            num_bays_y=3,
            floors=num_floors,
            story_height=3.5,
        ),
        loads=LoadInput(
            live_load_class="2",
            live_load_sub="2.5",
            dead_load=1.5,
        ),
        materials=MaterialInput(
            fcu_slab=35,
            fcu_beam=35,
            fcu_column=45,
        ),
        lateral=LateralInput(
            core_wall_config=CoreWallConfig.I_SECTION,
            core_geometry=CoreWallGeometry(
                config=CoreWallConfig.I_SECTION,
                wall_thickness=300.0,
                length_x=6000.0,
                length_y=6000.0,
                flange_width=2000.0,
                web_length=4000.0,
            ),
            terrain=TerrainCategory.URBAN,
        ),
    )


def benchmark_analysis(num_floors: int) -> Tuple[float, float, bool, str]:
    """Benchmark FEM analysis for a building.
    
    Args:
        num_floors: Number of floors to test
    
    Returns:
        Tuple of (wall_time_seconds, peak_memory_mb, success, message)
    """
    print(f"\n{'='*60}")
    print(f"Benchmarking {num_floors}-floor building...")
    print(f"{'='*60}")
    
    project = create_test_building(num_floors)
    
    tracemalloc.start()
    
    start_time = time.time()
    
    try:
        print("  -> Building FEM model...")
        options = ModelBuilderOptions(
            apply_wind_loads=False,
            apply_gravity_loads=True,
        )
        model = build_fem_model(project, options=options)
        
        print("  -> Running linear static analysis...")
        result: AnalysisResult = analyze_model(model, load_pattern=1)
        
        end_time = time.time()
        wall_time = end_time - start_time
        
        current, peak = tracemalloc.get_traced_memory()
        peak_memory_mb = peak / (1024 * 1024)
        tracemalloc.stop()
        
        success = result.success and result.converged
        message = result.message
        
        print(f"\n  OK Analysis completed")
        print(f"    - Wall time: {wall_time:.2f}s")
        print(f"    - Peak memory: {peak_memory_mb:.2f} MB")
        print(f"    - Status: {message}")
        print(f"    - Nodes: {len(result.node_displacements)}")
        print(f"    - Elements: {len(result.element_forces)}")
        
        return wall_time, peak_memory_mb, success, message
        
    except Exception as e:
        end_time = time.time()
        wall_time = end_time - start_time
        tracemalloc.stop()
        
        error_msg = f"ERROR: {str(e)}"
        print(f"\n  FAIL Analysis failed: {error_msg}")
        
        return wall_time, 0.0, False, error_msg


def run_benchmarks(floor_counts: list[int]) -> Dict[int, dict]:
    """Run benchmarks for multiple building sizes.
    
    Args:
        floor_counts: List of floor counts to test
    
    Returns:
        Dictionary mapping floor count to results
    """
    results = {}
    
    for num_floors in floor_counts:
        wall_time, memory_mb, success, message = benchmark_analysis(num_floors)
        
        results[num_floors] = {
            'wall_time_s': wall_time,
            'peak_memory_mb': memory_mb,
            'success': success,
            'message': message,
        }
    
    return results


def print_summary(results: Dict[int, dict], timeout: float = 60.0):
    """Print formatted summary of benchmark results.
    
    Args:
        results: Benchmark results dictionary
        timeout: Target timeout in seconds for verification
    """
    print(f"\n{'='*60}")
    print("BENCHMARK SUMMARY")
    print(f"{'='*60}")
    print(f"{'Floors':<10} {'Time (s)':<15} {'Memory (MB)':<15} {'Status':<10}")
    print(f"{'-'*60}")
    
    for num_floors in sorted(results.keys()):
        res = results[num_floors]
        time_s = res['wall_time_s']
        memory = res['peak_memory_mb']
        status = 'OK PASS' if res['success'] else 'X FAIL'
        
        print(f"{num_floors:<10} {time_s:<15.2f} {memory:<15.2f} {status:<10}")
    
    print(f"{'='*60}")
    
    print("\nVERIFICATION:")
    
    if 30 in results:
        time_30 = results[30]['wall_time_s']
        success_30 = results[30]['success']
        
        if success_30 and time_30 <= timeout:
            print(f"  OK PASS: 30-floor building completed in {time_30:.2f}s (<{timeout}s target)")
        elif not success_30:
            print(f"  X FAIL: 30-floor building analysis failed")
        else:
            print(f"  ! WARNING: 30-floor building took {time_30:.2f}s (>{timeout}s target)")
    
    for num_floors, res in results.items():
        if res['wall_time_s'] > 30.0:
            print(f"  ! WARNING: {num_floors}-floor exceeded PRD target of 30s ({res['wall_time_s']:.2f}s)")
    
    print(f"{'='*60}\n")


def main():
    """Main entry point for benchmark script."""
    parser = argparse.ArgumentParser(
        description="Performance benchmarking for PrelimStruct v3.5"
    )
    parser.add_argument(
        '--floors',
        type=int,
        choices=[10, 20, 30],
        help='Number of floors to benchmark (10, 20, or 30)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Benchmark all building sizes (10, 20, 30 floors)'
    )
    parser.add_argument(
        '--timeout',
        type=float,
        default=60.0,
        help='Target timeout in seconds (default: 60s)'
    )
    
    args = parser.parse_args()
    
    # Determine which floor counts to test
    if args.all:
        floor_counts = [10, 20, 30]
    elif args.floors:
        floor_counts = [args.floors]
    else:
        # Default: test all
        floor_counts = [10, 20, 30]
    
    print("PrelimStruct v3.5 Performance Benchmark")
    print(f"Testing: {floor_counts} floors")
    print(f"Target: <{args.timeout}s for 30-floor building\n")
    
    # Run benchmarks
    results = run_benchmarks(floor_counts)
    
    # Print summary
    print_summary(results, timeout=args.timeout)
    
    # Exit code
    if 30 in results:
        success = results[30]['success']
        within_time = results[30]['wall_time_s'] <= args.timeout
        sys.exit(0 if (success and within_time) else 1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
