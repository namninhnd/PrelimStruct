"""
SLS (Serviceability Limit State) Checks per HK Code 2013

This module implements serviceability checks per HK Code 2013 Cl 7.2-7.3:
- Span/depth ratio checks (Table 7.3, Cl 7.3.4)
- Deflection checks (Cl 7.3.2-7.3.3)
- Crack width checks (Cl 7.2)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from src.core.constants import SPAN_DEPTH_RATIOS


class MemberType(Enum):
    """Member type for SLS checks."""
    CANTILEVER = "cantilever"
    SIMPLY_SUPPORTED_BEAM = "simply_supported"
    CONTINUOUS_BEAM = "continuous"
    RECTANGULAR_FLANGED_BEAM = "rectangular"
    T_BEAM = "flanged"
    ONE_WAY_SLAB = "one_way_slab"
    TWO_WAY_SLAB_RESTRAINED = "two_way_slab_restrained"
    TWO_WAY_SLAB_SIMPLE = "two_way_slab_simple"


class ExposureCondition(Enum):
    """Exposure condition for crack width limits per HK Code Table 7.1."""
    MILD = "mild"                    # w_max = 0.3mm
    MODERATE = "moderate"            # w_max = 0.3mm
    SEVERE = "severe"                # w_max = 0.1mm (prestressed)


@dataclass
class SpanDepthCheckResult:
    """Result of span/depth ratio check.
    
    Attributes:
        member_id: Member identifier
        actual_ratio: Actual L/d ratio
        allowable_ratio: Allowable L/d ratio per HK Code Table 7.3
        modification_factor: Total modification factor applied
        is_compliant: True if actual ≤ allowable
        note: Calculation notes
    """
    member_id: str
    actual_ratio: float
    allowable_ratio: float
    modification_factor: float = 1.0
    is_compliant: bool = False
    note: str = ""


@dataclass
class DeflectionCheckResult:
    """Result of deflection check.
    
    Attributes:
        member_id: Member identifier
        actual_deflection: Actual deflection (mm)
        allowable_deflection: Allowable deflection (mm) per HK Code Cl 7.3.2
        span_length: Span length (mm)
        deflection_limit_ratio: Allowable deflection ratio (e.g., L/500)
        is_compliant: True if actual ≤ allowable
        note: Calculation notes
    """
    member_id: str
    actual_deflection: float
    allowable_deflection: float
    span_length: float
    deflection_limit_ratio: str
    is_compliant: bool = False
    note: str = ""


@dataclass
class CrackWidthCheckResult:
    """Result of crack width check.
    
    Attributes:
        member_id: Member identifier
        calculated_crack_width: Calculated crack width w_k (mm)
        allowable_crack_width: Allowable crack width (mm) per HK Code Table 7.1
        exposure: Exposure condition
        is_compliant: True if w_k ≤ w_allowable
        note: Calculation notes
    """
    member_id: str
    calculated_crack_width: float
    allowable_crack_width: float
    exposure: ExposureCondition
    is_compliant: bool = False
    note: str = ""


class SLSChecker:
    """Serviceability limit state checker per HK Code 2013 Cl 7."""
    
    def __init__(self):
        """Initialize SLS checker."""
        self.span_depth_results: List[SpanDepthCheckResult] = []
        self.deflection_results: List[DeflectionCheckResult] = []
        self.crack_width_results: List[CrackWidthCheckResult] = []
    
    def check_span_depth_ratio(
        self,
        member_id: str,
        span_length: float,
        effective_depth: float,
        member_type: MemberType,
        steel_stress: float = 500.0,
        compression_reinf_ratio: float = 0.0,
        span_gt_10m: bool = False
    ) -> SpanDepthCheckResult:
        """Check span/depth ratio per HK Code 2013 Cl 7.3.4 and Table 7.3.
        
        HK Code 2013 Cl 7.3.4:
        - Basic span/depth ratios given in Table 7.3
        - Modification factors applied for tension reinforcement, compression
          reinforcement, and long spans (> 10m)
        
        Args:
            member_id: Member identifier
            span_length: Effective span (mm)
            effective_depth: Effective depth d (mm)
            member_type: Member type (beam, slab, cantilever, etc.)
            steel_stress: Design stress in tension reinforcement (MPa)
            compression_reinf_ratio: Compression reinforcement ratio A_sc/A_st
            span_gt_10m: True if span > 10m
            
        Returns:
            SpanDepthCheckResult with compliance status
        """
        # Calculate actual L/d ratio
        actual_ratio = span_length / effective_depth if effective_depth > 0 else 0.0
        
        # Get basic allowable ratio from Table 7.3
        basic_ratio = self._get_basic_span_depth_ratio(member_type)
        
        # Apply modification factors per HK Code Cl 7.3.4.2
        # (1) Tension reinforcement modification factor
        # Simplified: factor = 500 / steel_stress (conservative)
        tension_factor = 500.0 / steel_stress if steel_stress > 0 else 1.0
        
        # (2) Compression reinforcement modification factor
        # Simplified: factor = 1 + (compression_ratio / 3)
        compression_factor = 1.0 + (compression_reinf_ratio / 3.0)
        
        # (3) Long span modification factor (span > 10m)
        # HK Code Cl 7.3.4.2: reduce by 10/span
        long_span_factor = 10.0 / (span_length / 1000.0) if span_gt_10m else 1.0
        
        # Total modification factor
        total_factor = tension_factor * compression_factor * long_span_factor
        
        # Allowable ratio with modifications
        allowable_ratio = basic_ratio * total_factor
        
        # Check compliance
        is_compliant = actual_ratio <= allowable_ratio
        
        note = (
            f"Basic L/d = {basic_ratio}, "
            f"Tension factor = {tension_factor:.2f}, "
            f"Compression factor = {compression_factor:.2f}, "
            f"Long span factor = {long_span_factor:.2f}"
        )
        
        result = SpanDepthCheckResult(
            member_id=member_id,
            actual_ratio=actual_ratio,
            allowable_ratio=allowable_ratio,
            modification_factor=total_factor,
            is_compliant=is_compliant,
            note=note
        )
        
        self.span_depth_results.append(result)
        return result
    
    def _get_basic_span_depth_ratio(self, member_type: MemberType) -> float:
        """Get basic span/depth ratio from HK Code 2013 Table 7.3.
        
        Args:
            member_type: Type of structural member
            
        Returns:
            Basic allowable L/d ratio
        """
        # HK Code 2013 Table 7.3 (simplified values)
        ratios = {
            MemberType.CANTILEVER: 7.0,
            MemberType.SIMPLY_SUPPORTED_BEAM: 20.0,  # Rectangular section
            MemberType.CONTINUOUS_BEAM: 26.0,         # Rectangular section
            MemberType.RECTANGULAR_FLANGED_BEAM: 20.0,
            MemberType.T_BEAM: 26.0,                  # Flanged beam (simply supported)
            MemberType.ONE_WAY_SLAB: 30.0,            # Simply supported
            MemberType.TWO_WAY_SLAB_RESTRAINED: 48.0,
            MemberType.TWO_WAY_SLAB_SIMPLE: 40.0,
        }
        return ratios.get(member_type, 20.0)
    
    def check_deflection(
        self,
        member_id: str,
        actual_deflection: float,
        span_length: float,
        deflection_type: str = "total",
        creep_factor: float = 1.0
    ) -> DeflectionCheckResult:
        """Check deflection per HK Code 2013 Cl 7.3.2-7.3.3.
        
        HK Code 2013 Cl 7.3.2:
        - Deflection after construction: L/500 (or 20mm max)
        - Deflection affecting partitions: L/350
        - Total deflection: L/250
        
        HK Code 2013 Cl 7.3.3:
        - Long-term deflection includes creep effects (ϕ per Cl 3.1.8)
        
        Args:
            member_id: Member identifier
            actual_deflection: Actual calculated deflection (mm)
            span_length: Effective span (mm)
            deflection_type: Type of deflection ("total", "post_construction", "partition")
            creep_factor: Creep factor ϕ (typical 2.0-3.0 for long-term)
            
        Returns:
            DeflectionCheckResult with compliance status
        """
        # Apply creep factor for long-term deflection
        actual_deflection_with_creep = actual_deflection * creep_factor
        
        # Determine allowable deflection per HK Code Cl 7.3.2
        if deflection_type == "post_construction":
            limit_ratio = "L/500"
            allowable_deflection = min(span_length / 500.0, 20.0)
        elif deflection_type == "partition":
            limit_ratio = "L/350"
            allowable_deflection = span_length / 350.0
        else:  # total
            limit_ratio = "L/250"
            allowable_deflection = span_length / 250.0
        
        # Check compliance
        is_compliant = actual_deflection_with_creep <= allowable_deflection
        
        note = (
            f"Immediate deflection = {actual_deflection:.2f} mm, "
            f"Creep factor = {creep_factor:.2f}, "
            f"Long-term deflection = {actual_deflection_with_creep:.2f} mm"
        )
        
        result = DeflectionCheckResult(
            member_id=member_id,
            actual_deflection=actual_deflection_with_creep,
            allowable_deflection=allowable_deflection,
            span_length=span_length,
            deflection_limit_ratio=limit_ratio,
            is_compliant=is_compliant,
            note=note
        )
        
        self.deflection_results.append(result)
        return result
    
    def check_crack_width(
        self,
        member_id: str,
        steel_strain: float,
        bar_spacing: float,
        concrete_cover: float,
        exposure: ExposureCondition = ExposureCondition.MODERATE,
        bar_diameter: float = 16.0
    ) -> CrackWidthCheckResult:
        """Check crack width per HK Code 2013 Cl 7.2.
        
        HK Code 2013 Cl 7.2.4:
        - Design crack width: w_k = β × s_rm × ε_sm
        - Mean crack spacing: s_rm (Cl 7.2.4.2)
        - Mean strain: ε_sm (Cl 7.2.4.3)
        
        HK Code 2013 Table 7.1 - Allowable crack widths:
        - Mild exposure: w_max = 0.3mm
        - Moderate exposure: w_max = 0.3mm
        - Severe exposure: w_max = 0.1mm (for prestressed concrete)
        
        Args:
            member_id: Member identifier
            steel_strain: Strain in tension reinforcement ε_sm
            bar_spacing: Center-to-center spacing of bars (mm)
            concrete_cover: Concrete cover to reinforcement (mm)
            exposure: Exposure condition
            bar_diameter: Reinforcement bar diameter (mm)
            
        Returns:
            CrackWidthCheckResult with compliance status
        """
        # Calculate mean crack spacing s_rm per HK Code Cl 7.2.4.2
        # Simplified formula: s_rm = 50 + 0.25k1k2φ/ρ_eff
        # Conservative approximation: s_rm ≈ 3.4c + 0.425k1k2φ/ρ_eff
        # For simplicity, use approximate formula based on cover and spacing
        s_rm = 3.4 * concrete_cover + 0.17 * bar_spacing
        
        # Calculate crack width w_k
        # HK Code Cl 7.2.4: w_k = β × s_rm × ε_sm
        # β is a coefficient relating crack width to strain (typically 1.7 for short-term)
        beta = 1.7
        w_k = beta * s_rm * steel_strain  # Result in mm if s_rm in mm
        
        # Get allowable crack width from Table 7.1
        if exposure == ExposureCondition.SEVERE:
            w_allowable = 0.1  # mm (prestressed concrete)
        else:  # Mild or Moderate
            w_allowable = 0.3  # mm
        
        # Check compliance
        is_compliant = w_k <= w_allowable
        
        note = (
            f"Mean crack spacing s_rm = {s_rm:.2f} mm, "
            f"Steel strain ε_sm = {steel_strain:.6f}, "
            f"Calculated w_k = {w_k:.3f} mm"
        )
        
        result = CrackWidthCheckResult(
            member_id=member_id,
            calculated_crack_width=w_k,
            allowable_crack_width=w_allowable,
            exposure=exposure,
            is_compliant=is_compliant,
            note=note
        )
        
        self.crack_width_results.append(result)
        return result
    
    def get_summary_report(self) -> str:
        """Generate summary report of all SLS checks.
        
        Returns:
            Formatted text report
        """
        lines = []
        lines.append("=" * 80)
        lines.append("SERVICEABILITY LIMIT STATE (SLS) CHECKS SUMMARY")
        lines.append("=" * 80)
        
        # Span/depth ratio checks
        lines.append("\nSPAN/DEPTH RATIO CHECKS (HK Code Cl 7.3.4, Table 7.3):")
        lines.append(f"  Total members checked: {len(self.span_depth_results)}")
        if self.span_depth_results:
            compliant = sum(1 for r in self.span_depth_results if r.is_compliant)
            lines.append(f"  Compliant: {compliant}/{len(self.span_depth_results)}")
            lines.append("\n  Member ID | Actual L/d | Allowable L/d | Status")
            lines.append("  " + "-" * 55)
            for result in self.span_depth_results:
                status = "PASS" if result.is_compliant else "FAIL"
                lines.append(
                    f"  {result.member_id:<10} | {result.actual_ratio:>10.2f} | "
                    f"{result.allowable_ratio:>13.2f} | {status}"
                )
        
        # Deflection checks
        lines.append("\nDEFLECTION CHECKS (HK Code Cl 7.3.2-7.3.3):")
        lines.append(f"  Total members checked: {len(self.deflection_results)}")
        if self.deflection_results:
            compliant = sum(1 for r in self.deflection_results if r.is_compliant)
            lines.append(f"  Compliant: {compliant}/{len(self.deflection_results)}")
            lines.append("\n  Member ID | Actual (mm) | Allowable (mm) | Limit | Status")
            lines.append("  " + "-" * 65)
            for result in self.deflection_results:
                status = "PASS" if result.is_compliant else "FAIL"
                lines.append(
                    f"  {result.member_id:<10} | {result.actual_deflection:>11.2f} | "
                    f"{result.allowable_deflection:>14.2f} | {result.deflection_limit_ratio:<5} | {status}"
                )
        
        # Crack width checks
        lines.append("\nCRACK WIDTH CHECKS (HK Code Cl 7.2):")
        lines.append(f"  Total members checked: {len(self.crack_width_results)}")
        if self.crack_width_results:
            compliant = sum(1 for r in self.crack_width_results if r.is_compliant)
            lines.append(f"  Compliant: {compliant}/{len(self.crack_width_results)}")
            lines.append("\n  Member ID | w_k (mm) | w_allow (mm) | Exposure | Status")
            lines.append("  " + "-" * 65)
            for result in self.crack_width_results:
                status = "PASS" if result.is_compliant else "FAIL"
                lines.append(
                    f"  {result.member_id:<10} | {result.calculated_crack_width:>8.3f} | "
                    f"{result.allowable_crack_width:>12.3f} | {result.exposure.value:<8} | {status}"
                )
        
        lines.append("=" * 80)
        return "\n".join(lines)
