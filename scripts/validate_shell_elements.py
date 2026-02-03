#!/usr/bin/env python
"""
ETABS Validation Script for Shell Element Implementation

This script provides validation infrastructure for comparing PrelimStruct v3.5
FEM results against ETABS benchmark results for 5 test buildings.

Usage:
    python scripts/validate_shell_elements.py --list-cases
    python scripts/validate_shell_elements.py --validate building_01
    python scripts/validate_shell_elements.py --validate-all
    python scripts/validate_shell_elements.py --show-template building_01
    python scripts/validate_shell_elements.py --report

Design Code References:
    - HK Code 2013: Structural Use of Concrete
    - HK Wind Code 2019: Wind Effects on Buildings
    
Validation Target: >95% match with ETABS benchmark (per PRD.md Success Criteria)
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
VALIDATION_DIR = PROJECT_ROOT / ".sisyphus" / "validation"
ETABS_RESULTS_DIR = VALIDATION_DIR / "etabs_results"


@dataclass
class ValidationMetric:
    """Single validation metric with actual/expected values."""
    name: str
    unit: str
    prelimstruct_value: Optional[float]
    etabs_value: Optional[float]
    tolerance_percent: float = 10.0  # Default 10% tolerance per decisions.md
    
    @property
    def difference_percent(self) -> Optional[float]:
        """Calculate percentage difference if both values exist."""
        if self.prelimstruct_value is None or self.etabs_value is None:
            return None
        if self.etabs_value == 0:
            return 0.0 if self.prelimstruct_value == 0 else float('inf')
        return abs(self.prelimstruct_value - self.etabs_value) / abs(self.etabs_value) * 100
    
    @property
    def passes(self) -> Optional[bool]:
        """Check if metric passes tolerance."""
        diff = self.difference_percent
        if diff is None:
            return None
        return diff <= self.tolerance_percent
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "unit": self.unit,
            "prelimstruct": self.prelimstruct_value,
            "etabs": self.etabs_value,
            "difference_percent": self.difference_percent,
            "tolerance_percent": self.tolerance_percent,
            "passes": self.passes
        }


@dataclass
class BuildingValidationResult:
    """Validation results for a single building."""
    building_id: str
    building_name: str
    metrics: List[ValidationMetric]
    
    @property
    def all_pass(self) -> bool:
        """Check if all metrics pass."""
        return all(m.passes for m in self.metrics if m.passes is not None)
    
    @property
    def pass_count(self) -> int:
        """Count passing metrics."""
        return sum(1 for m in self.metrics if m.passes is True)
    
    @property
    def fail_count(self) -> int:
        """Count failing metrics."""
        return sum(1 for m in self.metrics if m.passes is False)
    
    @property
    def pending_count(self) -> int:
        """Count metrics with missing data."""
        return sum(1 for m in self.metrics if m.passes is None)


class ETABSValidationRunner:
    """Manages ETABS validation for all test buildings."""
    
    # Standard validation metrics to compare
    VALIDATION_METRICS = [
        ("max_lateral_drift_mm", "mm", 10.0),
        ("max_story_drift_ratio", "ratio", 10.0),
        ("base_shear_kN", "kN", 5.0),
        ("overturning_moment_kNm", "kNm", 5.0),
        ("max_column_axial_kN", "kN", 5.0),
        ("max_beam_moment_kNm", "kNm", 10.0),
        ("first_mode_period_s", "s", 10.0),
        ("total_weight_kN", "kN", 2.0),
    ]
    
    def __init__(self, validation_dir: Path = VALIDATION_DIR):
        self.validation_dir = validation_dir
        self.etabs_results_dir = validation_dir / "etabs_results"
        self.building_definitions = self._load_building_definitions()
    
    def _load_building_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Load all building definition JSON files."""
        buildings: Dict[str, Dict[str, Any]] = {}
        for json_file in self.validation_dir.glob("building_*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    buildings[data["id"]] = data
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Failed to load {json_file}: {e}")
        return buildings
    
    def list_cases(self) -> List[Dict[str, Any]]:
        """List all test cases with summary."""
        cases: List[Dict[str, Any]] = []
        for bld_id, data in sorted(self.building_definitions.items()):
            cases.append({
                "id": bld_id,
                "name": data.get("name", "Unknown"),
                "category": data.get("category", "unknown"),
                "complexity": data.get("complexity", "unknown"),
                "floors": data.get("geometry", {}).get("floors", 0),
                "core_config": data.get("lateral", {}).get("core_wall_config", "unknown"),
                "test_focus": data.get("test_focus", []),
            })
        return cases
    
    def show_template(self, building_id: str) -> Optional[Dict[str, Any]]:
        """Show ETABS results template for a building."""
        if building_id not in self.building_definitions:
            return None
        
        bld = self.building_definitions[building_id]
        template = {
            "building_id": building_id,
            "building_name": bld.get("name", "Unknown"),
            "etabs_version": "ETABS v21.x.x",
            "analysis_date": "YYYY-MM-DD",
            "analyst": "Engineer Name",
            "etabs_file": f"{building_id}.EDB",
            "notes": "Manual analysis using building definition from .sisyphus/validation/",
            "results": {
                "max_lateral_drift_mm": None,
                "max_story_drift_ratio": None,
                "base_shear_kN": None,
                "overturning_moment_kNm": None,
                "max_column_axial_kN": None,
                "max_beam_moment_kNm": None,
                "max_coupling_beam_shear_kN": None,
                "first_mode_period_s": None,
                "second_mode_period_s": None,
                "total_weight_kN": None,
                "analysis_time_s": None,
            },
            "load_cases_analyzed": [
                "ULS_GRAVITY_1",
                "ULS_WIND_1 (W1-W24 as applicable)",
                "SLS_CHARACTERISTIC",
            ],
            "model_info": {
                "element_type": "Shell-Thin (ShellMITC4 equivalent)",
                "mesh_size_m": 1.0,
                "total_nodes": None,
                "total_elements": None,
                "wall_section": "Plate Fiber Section",
                "slab_section": "Elastic Membrane Plate Section",
            },
            "verification_notes": [
                "1. Verify fixed base boundary conditions",
                "2. Confirm rigid diaphragm assignment at each floor",
                "3. Check load application matches building definition",
                "4. Review element local axes orientation",
            ]
        }
        return template
    
    def load_etabs_results(self, building_id: str) -> Optional[Dict[str, Any]]:
        """Load ETABS results for a building if available."""
        results_file = self.etabs_results_dir / f"{building_id}_etabs.json"
        if not results_file.exists():
            return None
        try:
            with open(results_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return None
    
    def load_prelimstruct_results(self, building_id: str) -> Optional[Dict[str, Any]]:
        """Load PrelimStruct results for a building (placeholder)."""
        # This will be populated once FEM analysis is implemented
        results_file = self.validation_dir / "prelimstruct_results" / f"{building_id}_results.json"
        if not results_file.exists():
            return None
        try:
            with open(results_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return None
    
    def validate_building(self, building_id: str) -> Optional[BuildingValidationResult]:
        """Validate a single building against ETABS results."""
        if building_id not in self.building_definitions:
            return None
        
        bld = self.building_definitions[building_id]
        etabs = self.load_etabs_results(building_id)
        prelim = self.load_prelimstruct_results(building_id)
        
        metrics = []
        for metric_name, unit, tolerance in self.VALIDATION_METRICS:
            etabs_val = None
            prelim_val = None
            
            if etabs and "results" in etabs:
                etabs_val = etabs["results"].get(metric_name)
            if prelim and "results" in prelim:
                prelim_val = prelim["results"].get(metric_name)
            
            metrics.append(ValidationMetric(
                name=metric_name,
                unit=unit,
                prelimstruct_value=prelim_val,
                etabs_value=etabs_val,
                tolerance_percent=tolerance
            ))
        
        return BuildingValidationResult(
            building_id=building_id,
            building_name=bld.get("name", "Unknown"),
            metrics=metrics
        )
    
    def validate_all(self) -> List[BuildingValidationResult]:
        """Validate all buildings."""
        results = []
        for building_id in sorted(self.building_definitions.keys()):
            result = self.validate_building(building_id)
            if result:
                results.append(result)
        return results
    
    def generate_report(self) -> str:
        """Generate validation report."""
        results = self.validate_all()
        
        lines = [
            "=" * 80,
            "ETABS VALIDATION REPORT - PrelimStruct v3.5",
            "=" * 80,
            f"Date: 2026-02-03",
            f"Target: >95% match with ETABS (per PRD.md)",
            f"Tolerance: 10% default (5% for base shear, 2% for weight)",
            "",
            "SUMMARY",
            "-" * 40,
        ]
        
        total_pass = 0
        total_fail = 0
        total_pending = 0
        
        for result in results:
            total_pass += result.pass_count
            total_fail += result.fail_count
            total_pending += result.pending_count
            
            status = "PASS" if result.all_pass else ("PENDING" if result.pending_count > 0 else "FAIL")
            lines.append(
                f"  {result.building_id}: {status} "
                f"({result.pass_count}P/{result.fail_count}F/{result.pending_count}?)"
            )
        
        lines.extend([
            "",
            f"Overall: {total_pass} Pass, {total_fail} Fail, {total_pending} Pending",
            "",
            "DETAILED RESULTS",
            "-" * 40,
        ])
        
        for result in results:
            lines.extend([
                "",
                f"Building: {result.building_id} - {result.building_name}",
                f"{'Metric':<30} {'ETABS':>12} {'PrelimStruct':>12} {'Diff%':>8} {'Status':>8}",
                "-" * 72,
            ])
            
            for m in result.metrics:
                etabs_str = f"{m.etabs_value:.2f}" if m.etabs_value else "N/A"
                prelim_str = f"{m.prelimstruct_value:.2f}" if m.prelimstruct_value else "N/A"
                diff_str = f"{m.difference_percent:.1f}%" if m.difference_percent is not None else "N/A"
                status = "PASS" if m.passes is True else ("FAIL" if m.passes is False else "PENDING")
                
                lines.append(
                    f"  {m.name:<28} {etabs_str:>12} {prelim_str:>12} {diff_str:>8} {status:>8}"
                )
        
        lines.extend([
            "",
            "=" * 80,
            "END OF REPORT",
            "=" * 80,
        ])
        
        return "\n".join(lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ETABS Validation Script for PrelimStruct v3.5 Shell Elements",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/validate_shell_elements.py --list-cases
    python scripts/validate_shell_elements.py --validate building_01
    python scripts/validate_shell_elements.py --validate-all
    python scripts/validate_shell_elements.py --show-template building_01
    python scripts/validate_shell_elements.py --report
    
ETABS Manual Analysis Process:
    1. Run --show-template to get ETABS input parameters
    2. Build ETABS model matching building definition
    3. Run analysis and record results
    4. Save results to .sisyphus/validation/etabs_results/{building_id}_etabs.json
    5. Run --validate to compare against PrelimStruct results
"""
    )
    
    parser.add_argument(
        "--list-cases", "-l",
        action="store_true",
        help="List all test cases"
    )
    parser.add_argument(
        "--validate", "-v",
        type=str,
        metavar="BUILDING_ID",
        help="Validate specific building (e.g., building_01)"
    )
    parser.add_argument(
        "--validate-all", "-a",
        action="store_true",
        help="Validate all buildings"
    )
    parser.add_argument(
        "--show-template", "-t",
        type=str,
        metavar="BUILDING_ID",
        help="Show ETABS results template for a building"
    )
    parser.add_argument(
        "--report", "-r",
        action="store_true",
        help="Generate full validation report"
    )
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output results as JSON"
    )
    
    args = parser.parse_args()
    
    # Ensure validation directory exists
    if not VALIDATION_DIR.exists():
        print(f"Error: Validation directory not found: {VALIDATION_DIR}")
        sys.exit(1)
    
    runner = ETABSValidationRunner()
    
    if args.list_cases:
        cases = runner.list_cases()
        if args.json:
            print(json.dumps(cases, indent=2))
        else:
            print("\n" + "=" * 80)
            print("ETABS VALIDATION TEST CASES")
            print("=" * 80)
            print(f"\nFound {len(cases)} test cases:\n")
            
            for case in cases:
                print(f"  {case['id']}: {case['name']}")
                print(f"    Category: {case['category']}, Complexity: {case['complexity']}")
                print(f"    Floors: {case['floors']}, Core: {case['core_config']}")
                print(f"    Focus: {', '.join(case['test_focus'][:2])}")
                print()
    
    elif args.show_template:
        template = runner.show_template(args.show_template)
        if template:
            print(json.dumps(template, indent=2))
        else:
            print(f"Error: Building not found: {args.show_template}")
            sys.exit(1)
    
    elif args.validate:
        result = runner.validate_building(args.validate)
        if result:
            if args.json:
                print(json.dumps({
                    "building_id": result.building_id,
                    "building_name": result.building_name,
                    "all_pass": result.all_pass,
                    "pass_count": result.pass_count,
                    "fail_count": result.fail_count,
                    "pending_count": result.pending_count,
                    "metrics": [m.to_dict() for m in result.metrics]
                }, indent=2))
            else:
                status = "PASS" if result.all_pass else ("PENDING" if result.pending_count > 0 else "FAIL")
                print(f"\nValidation Result: {result.building_id} - {status}")
                print(f"  {result.pass_count} Pass, {result.fail_count} Fail, {result.pending_count} Pending")
        else:
            print(f"Error: Building not found: {args.validate}")
            sys.exit(1)
    
    elif args.validate_all:
        results = runner.validate_all()
        if args.json:
            print(json.dumps([{
                "building_id": r.building_id,
                "all_pass": r.all_pass,
                "pass_count": r.pass_count,
                "fail_count": r.fail_count,
                "pending_count": r.pending_count,
            } for r in results], indent=2))
        else:
            print("\nValidation Summary:")
            for result in results:
                status = "PASS" if result.all_pass else ("PENDING" if result.pending_count > 0 else "FAIL")
                print(f"  {result.building_id}: {status} ({result.pass_count}P/{result.fail_count}F/{result.pending_count}?)")
    
    elif args.report:
        report = runner.generate_report()
        print(report)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
