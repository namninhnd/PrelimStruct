"""
Beam Design Update After Trimming

This module provides functionality to recalculate beam design parameters
after trimming at core wall edges. When beams are trimmed, their effective
span changes, which affects moments, shears, and required reinforcement.
"""

from typing import Tuple
from dataclasses import replace

from src.core.data_models import BeamResult, ProjectData
from src.engines.beam_engine import BeamEngine
from src.fem.beam_trimmer import TrimmedBeam, BeamConnectionType


class BeamTrimUpdater:
    """Update beam design calculations after trimming.
    
    This class recalculates beam design parameters (moments, shears, reinforcement)
    for trimmed spans. The updated design accounts for:
    - Reduced span length after trimming
    - Updated tributary width if applicable
    - Modified end conditions (moment vs. pinned connections)
    - Recalculated load distribution
    """
    
    def __init__(self, project: ProjectData):
        """Initialize beam trim updater.
        
        Args:
            project: ProjectData containing design parameters
        """
        self.project = project
        self.beam_engine = BeamEngine(project)
    
    def update_beam_design(
        self,
        original_result: BeamResult,
        trimmed_beam: TrimmedBeam,
        tributary_width: float
    ) -> BeamResult:
        """Update beam design for trimmed span.
        
        This method:
        1. Calculates new span length from trimmed geometry
        2. Recalculates moments and shears for new span
        3. Re-runs beam sizing if necessary
        4. Updates connection type information
        5. Preserves calculation audit trail
        
        Args:
            original_result: Original BeamResult before trimming
            trimmed_beam: TrimmedBeam with updated geometry
            tributary_width: Tributary width for load calculation (m)
        
        Returns:
            Updated BeamResult with recalculated design parameters
        """
        # Extract trimmed span length
        original_span = original_result.size  # Original span from result
        trimmed_span = trimmed_beam.trimmed_length / 1000.0  # Convert mm to m
        
        # If no trimming occurred, return original result
        if not trimmed_beam.trimmed_start and not trimmed_beam.trimmed_end:
            return original_result
        
        # Recalculate design for new span
        # Use existing beam engine to calculate for trimmed span
        updated_result = self._recalculate_beam_design(
            trimmed_span,
            tributary_width,
            trimmed_beam
        )
        
        # Update trimming-related fields
        updated_result = replace(
            updated_result,
            is_trimmed=True,
            original_span=original_result.moment if hasattr(original_result, 'moment') else None,
            trimmed_span=trimmed_span,
            start_connection=trimmed_beam.start_connection.value,
            end_connection=trimmed_beam.end_connection.value
        )
        
        # Add trimming note to warnings
        trim_note = self._generate_trim_warning(trimmed_beam, original_span, trimmed_span)
        if trim_note:
            warnings = list(updated_result.warnings) if updated_result.warnings else []
            warnings.insert(0, trim_note)
            updated_result = replace(updated_result, warnings=warnings)
        
        return updated_result
    
    def _recalculate_beam_design(
        self,
        trimmed_span: float,
        tributary_width: float,
        trimmed_beam: TrimmedBeam
    ) -> BeamResult:
        """Recalculate beam design for trimmed span.
        
        Args:
            trimmed_span: New span length after trimming (m)
            tributary_width: Tributary width for load calculation (m)
            trimmed_beam: TrimmedBeam with connection information
        
        Returns:
            New BeamResult for trimmed span
        """
        # Get design load (same method as original beam engine)
        slab_load = self._get_slab_load()
        line_load = slab_load * tributary_width
        
        # Calculate beam self-weight (initial estimate)
        # Use typical beam dimensions as starting point
        materials = self.project.materials
        reinforcement = self.project.reinforcement
        
        # Use beam engine's internal design method
        # This will iterate to find appropriate size for trimmed span
        from src.core.constants import MIN_BEAM_DEPTH, MIN_BEAM_WIDTH
        import math
        
        h_initial = max(MIN_BEAM_DEPTH, math.ceil((trimmed_span * 1000) / 18))
        b_initial = max(MIN_BEAM_WIDTH, math.ceil(h_initial / 2 / 25) * 25)
        
        v_max = self.beam_engine._get_max_shear_stress(materials.fcu_beam)
        
        # Run iterative sizing for trimmed span
        result = self.beam_engine._iterate_beam_size(
            trimmed_span,
            line_load,
            b_initial,
            h_initial,
            materials.fcu_beam,
            materials.cover_beam,
            reinforcement.min_rho_beam,
            reinforcement.max_rho_beam,
            v_max,
            "Trimmed"
        )
        
        return result
    
    def _get_slab_load(self) -> float:
        """Get design load from slab (or estimate if not calculated yet).
        
        Returns:
            Design slab load in kPa
        """
        from src.core.constants import CONCRETE_DENSITY
        
        if self.project.slab_result:
            slab_self_weight = self.project.slab_result.self_weight
        else:
            # Estimate 200mm slab
            slab_self_weight = 0.2 * CONCRETE_DENSITY
        
        gk = slab_self_weight + self.project.loads.dead_load
        qk = self.project.loads.live_load
        
        # ULS factored load
        return 1.4 * gk + 1.6 * qk
    
    def _generate_trim_warning(
        self,
        trimmed_beam: TrimmedBeam,
        original_span: str,
        trimmed_span: float
    ) -> str:
        """Generate warning message about beam trimming.
        
        Args:
            trimmed_beam: TrimmedBeam information
            original_span: Original beam span description
            trimmed_span: Trimmed span length (m)
        
        Returns:
            Warning message string
        """
        if trimmed_beam.trimmed_start and trimmed_beam.trimmed_end:
            return (f"Beam trimmed at both ends due to core wall intersection. "
                   f"New span: {trimmed_span:.2f}m. "
                   f"Connections: START={trimmed_beam.start_connection.value}, "
                   f"END={trimmed_beam.end_connection.value}")
        elif trimmed_beam.trimmed_start:
            return (f"Beam trimmed at start due to core wall intersection. "
                   f"New span: {trimmed_span:.2f}m. "
                   f"Start connection: {trimmed_beam.start_connection.value}")
        elif trimmed_beam.trimmed_end:
            return (f"Beam trimmed at end due to core wall intersection. "
                   f"New span: {trimmed_span:.2f}m. "
                   f"End connection: {trimmed_beam.end_connection.value}")
        else:
            return ""
    
    def calculate_span_reduction_ratio(self, trimmed_beam: TrimmedBeam) -> float:
        """Calculate the ratio of span reduction due to trimming.
        
        Args:
            trimmed_beam: TrimmedBeam with original and trimmed geometry
        
        Returns:
            Span reduction ratio (trimmed_length / original_length)
        """
        if trimmed_beam.original_length == 0:
            return 1.0
        
        return trimmed_beam.trimmed_length / trimmed_beam.original_length
    
    def estimate_moment_reduction(
        self,
        original_moment: float,
        trimmed_beam: TrimmedBeam
    ) -> Tuple[float, str]:
        """Estimate moment reduction due to span change.
        
        For simply supported beams, moment is proportional to L².
        For continuous beams, reduction is less pronounced.
        
        Args:
            original_moment: Original design moment (kNm)
            trimmed_beam: TrimmedBeam information
        
        Returns:
            Tuple of (estimated_new_moment, explanation)
        """
        span_ratio = self.calculate_span_reduction_ratio(trimmed_beam)
        
        # Conservative estimate: assume simply supported (M ∝ L²)
        moment_ratio = span_ratio ** 2
        estimated_moment = original_moment * moment_ratio
        
        explanation = (
            f"Estimated moment reduction: {original_moment:.1f} kNm → "
            f"{estimated_moment:.1f} kNm (span ratio: {span_ratio:.3f})"
        )
        
        return estimated_moment, explanation


def apply_trimming_to_beam_results(
    project: ProjectData,
    primary_beam_result: BeamResult,
    secondary_beam_result: BeamResult,
    trimmed_primary_beams: list,
    trimmed_secondary_beams: list,
    primary_tributary: float,
    secondary_tributary: float
) -> Tuple[BeamResult, BeamResult]:
    """Apply trimming updates to beam results.
    
    Convenience function to update both primary and secondary beam results
    after trimming operations.
    
    Args:
        project: ProjectData with design parameters
        primary_beam_result: Original primary beam result
        secondary_beam_result: Original secondary beam result
        trimmed_primary_beams: List of TrimmedBeam for primary beams
        trimmed_secondary_beams: List of TrimmedBeam for secondary beams
        primary_tributary: Primary beam tributary width (m)
        secondary_tributary: Secondary beam tributary width (m)
    
    Returns:
        Tuple of (updated_primary_result, updated_secondary_result)
    """
    updater = BeamTrimUpdater(project)
    
    # Update primary beam if any were trimmed
    updated_primary = primary_beam_result
    if trimmed_primary_beams and any(b.trimmed_start or b.trimmed_end for b in trimmed_primary_beams):
        # Use first trimmed beam as representative (could be enhanced to handle multiple)
        representative_trimmed = next((b for b in trimmed_primary_beams if b.trimmed_start or b.trimmed_end), None)
        if representative_trimmed:
            updated_primary = updater.update_beam_design(
                primary_beam_result,
                representative_trimmed,
                primary_tributary
            )
    
    # Update secondary beam if any were trimmed
    updated_secondary = secondary_beam_result
    if trimmed_secondary_beams and any(b.trimmed_start or b.trimmed_end for b in trimmed_secondary_beams):
        representative_trimmed = next((b for b in trimmed_secondary_beams if b.trimmed_start or b.trimmed_end), None)
        if representative_trimmed:
            updated_secondary = updater.update_beam_design(
                secondary_beam_result,
                representative_trimmed,
                secondary_tributary
            )
    
    return updated_primary, updated_secondary
