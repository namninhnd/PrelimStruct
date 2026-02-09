"""
FEM Results Processor - Enveloping and Post-Processing

This module implements result enveloping across multiple load combinations,
providing maximum/minimum values with governing load case tracking for
design optimization.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from src.core.data_models import (
    LoadCombination, LoadCaseResult, EnvelopeValue, EnvelopedResult
)
from src.fem.solver import AnalysisResult


class ForceType(str, Enum):
    """Force type enumeration for section force extraction."""
    N = "N"       # Axial force
    Vy = "Vy"     # Shear force Y
    Vz = "Vz"     # Shear force Z
    My = "My"     # Bending moment Y
    Mz = "Mz"     # Bending moment Z
    T = "T"       # Torsion


@dataclass
class ElementForce:
    """Individual element force data for visualization.
    
    Attributes:
        element_id: Element identifier
        node_i: Start node tag
        node_j: End node tag
        force_i: Force value at node i (kN or kNm)
        force_j: Force value at node j (kN or kNm)
    """
    element_id: int
    node_i: int
    node_j: int
    force_i: float  # Already converted to kN or kNm
    force_j: float  # Already converted to kN or kNm


@dataclass
class SectionForcesData:
    """Container for section force visualization data.
    
    Attributes:
        force_type: Type of force (N, Vy, Vz, My, Mz, T)
        elements: Dictionary mapping element_id → ElementForce
        unit: Display unit ('kN' or 'kNm')
        min_value: Minimum force value across all elements
        max_value: Maximum force value across all elements
    """
    force_type: str
    elements: Dict[int, ElementForce] = field(default_factory=dict)
    unit: str = "kN"
    min_value: float = 0.0
    max_value: float = 0.0
    
    def get_color_range(self) -> Tuple[float, float]:
        """Get symmetric color scale range for visualization."""
        abs_max = max(abs(self.min_value), abs(self.max_value))
        return (-abs_max, abs_max)


@dataclass
class ElementForceEnvelope:
    """Envelope of element forces across load combinations.
    
    Attributes:
        element_id: Element identifier
        N_max/N_min: Axial force envelope
        Vy_max/Vy_min: Major-axis shear envelope
        Vz_max/Vz_min: Minor-axis shear envelope
        Mz_max/Mz_min: Major-axis moment envelope (ETABS M33)
        My_max/My_min: Minor-axis moment envelope (ETABS M22)
    """
    element_id: int
    N_max: EnvelopeValue = field(default_factory=EnvelopeValue)
    N_min: EnvelopeValue = field(default_factory=EnvelopeValue)
    Vy_max: EnvelopeValue = field(default_factory=EnvelopeValue)
    Vy_min: EnvelopeValue = field(default_factory=EnvelopeValue)
    Vz_max: EnvelopeValue = field(default_factory=EnvelopeValue)
    Vz_min: EnvelopeValue = field(default_factory=EnvelopeValue)
    Mz_max: EnvelopeValue = field(default_factory=EnvelopeValue)
    Mz_min: EnvelopeValue = field(default_factory=EnvelopeValue)
    My_max: EnvelopeValue = field(default_factory=EnvelopeValue)
    My_min: EnvelopeValue = field(default_factory=EnvelopeValue)


@dataclass
class DisplacementEnvelope:
    """Envelope of displacements for serviceability checks.
    
    Attributes:
        node_id: Node identifier
        ux_max: Maximum X displacement envelope
        uy_max: Maximum Y displacement envelope
        uz_max: Maximum Z displacement envelope (vertical deflection)
        drift_max: Maximum inter-story drift envelope
    """
    node_id: int
    ux_max: EnvelopeValue = field(default_factory=EnvelopeValue)
    uy_max: EnvelopeValue = field(default_factory=EnvelopeValue)
    uz_max: EnvelopeValue = field(default_factory=EnvelopeValue)
    drift_max: EnvelopeValue = field(default_factory=EnvelopeValue)


@dataclass
class ReactionEnvelope:
    """Envelope of support reactions for foundation design.
    
    Attributes:
        node_id: Support node identifier
        Fx_max: Maximum horizontal reaction X envelope
        Fy_max: Maximum horizontal reaction Y envelope
        Fz_max: Maximum vertical reaction envelope
        Fz_min: Minimum vertical reaction envelope (uplift)
        Mx_max: Maximum overturning moment X envelope
        My_max: Maximum overturning moment Y envelope
    """
    node_id: int
    Fx_max: EnvelopeValue = field(default_factory=EnvelopeValue)
    Fy_max: EnvelopeValue = field(default_factory=EnvelopeValue)
    Fz_max: EnvelopeValue = field(default_factory=EnvelopeValue)
    Fz_min: EnvelopeValue = field(default_factory=EnvelopeValue)
    Mx_max: EnvelopeValue = field(default_factory=EnvelopeValue)
    My_max: EnvelopeValue = field(default_factory=EnvelopeValue)


class ResultsProcessor:
    """Process and envelope FEM results across load combinations."""
    
    def __init__(self):
        """Initialize results processor."""
        self.element_force_envelopes: Dict[int, ElementForceEnvelope] = {}
        self.displacement_envelopes: Dict[int, DisplacementEnvelope] = {}
        self.reaction_envelopes: Dict[int, ReactionEnvelope] = {}
    
    def process_load_case_results(
        self, 
        load_case_results: List[LoadCaseResult]
    ) -> None:
        """Process all load case results and generate envelopes.
        
        Args:
            load_case_results: List of analysis results for each load combination
        """
        # Clear existing envelopes
        self.element_force_envelopes.clear()
        self.displacement_envelopes.clear()
        self.reaction_envelopes.clear()
        
        # Process each load case
        for result in load_case_results:
            self._update_element_force_envelope(result)
            self._update_displacement_envelope(result)
            self._update_reaction_envelope(result)
    
    def _update_element_force_envelope(self, result: LoadCaseResult) -> None:
        """Update element force envelopes with new load case results.
        
        Args:
            result: Load case result to process
        """
        for elem_id, forces in result.element_forces.items():
            # Get or create envelope for this element
            if elem_id not in self.element_force_envelopes:
                self.element_force_envelopes[elem_id] = ElementForceEnvelope(elem_id)
            
            envelope = self.element_force_envelopes[elem_id]
            
            # Extract forces (handle both 2D and 3D elements)
            # For 3D beam elements
            if 'N_i' in forces:
                N = max(abs(forces.get('N_i', 0.0)), abs(forces.get('N_j', 0.0)))
                Vy = max(abs(forces.get('Vy_i', 0.0)), abs(forces.get('Vy_j', 0.0)))
                Vz = max(abs(forces.get('Vz_i', 0.0)), abs(forces.get('Vz_j', 0.0)))
                Mz = max(abs(forces.get('Mz_i', 0.0)), abs(forces.get('Mz_j', 0.0)))
                My = max(abs(forces.get('My_i', 0.0)), abs(forces.get('My_j', 0.0)))
                N_signed = (forces.get('N_i', 0.0) + forces.get('N_j', 0.0)) / 2
                Vy_signed = (forces.get('Vy_i', 0.0) + forces.get('Vy_j', 0.0)) / 2
                Vz_signed = (forces.get('Vz_i', 0.0) + forces.get('Vz_j', 0.0)) / 2
                Mz_signed = (forces.get('Mz_i', 0.0) + forces.get('Mz_j', 0.0)) / 2
                My_signed = (forces.get('My_i', 0.0) + forces.get('My_j', 0.0)) / 2
            # For 2D beam elements
            elif 'V_i' in forces:
                N = max(abs(forces.get('N_i', 0.0)), abs(forces.get('N_j', 0.0)))
                Vy = max(abs(forces.get('V_i', 0.0)), abs(forces.get('V_j', 0.0)))
                Vz = 0.0
                Mz = max(abs(forces.get('M_i', 0.0)), abs(forces.get('M_j', 0.0)))
                My = 0.0
                N_signed = (forces.get('N_i', 0.0) + forces.get('N_j', 0.0)) / 2
                Vy_signed = (forces.get('V_i', 0.0) + forces.get('V_j', 0.0)) / 2
                Vz_signed = 0.0
                Mz_signed = (forces.get('M_i', 0.0) + forces.get('M_j', 0.0)) / 2
                My_signed = 0.0
            else:
                continue  # Skip if force format not recognized
            
            # Update axial force envelope
            if N > envelope.N_max.max_value:
                envelope.N_max.max_value = N
                envelope.N_max.governing_max_case = result.combination
                envelope.N_max.governing_max_location = elem_id
            if N_signed < envelope.N_min.min_value or envelope.N_min.min_value == 0.0:
                envelope.N_min.min_value = N_signed
                envelope.N_min.governing_min_case = result.combination
                envelope.N_min.governing_min_location = elem_id
            
            # Update major-axis shear envelope
            if Vy > envelope.Vy_max.max_value:
                envelope.Vy_max.max_value = Vy
                envelope.Vy_max.governing_max_case = result.combination
                envelope.Vy_max.governing_max_location = elem_id
            if Vy_signed < envelope.Vy_min.min_value or envelope.Vy_min.min_value == 0.0:
                envelope.Vy_min.min_value = Vy_signed
                envelope.Vy_min.governing_min_case = result.combination
                envelope.Vy_min.governing_min_location = elem_id

            # Update minor-axis shear envelope
            if Vz > envelope.Vz_max.max_value:
                envelope.Vz_max.max_value = Vz
                envelope.Vz_max.governing_max_case = result.combination
                envelope.Vz_max.governing_max_location = elem_id
            if Vz_signed < envelope.Vz_min.min_value or envelope.Vz_min.min_value == 0.0:
                envelope.Vz_min.min_value = Vz_signed
                envelope.Vz_min.governing_min_case = result.combination
                envelope.Vz_min.governing_min_location = elem_id

            # Update major-axis moment envelope
            if Mz > envelope.Mz_max.max_value:
                envelope.Mz_max.max_value = Mz
                envelope.Mz_max.governing_max_case = result.combination
                envelope.Mz_max.governing_max_location = elem_id
            if Mz_signed < envelope.Mz_min.min_value or envelope.Mz_min.min_value == 0.0:
                envelope.Mz_min.min_value = Mz_signed
                envelope.Mz_min.governing_min_case = result.combination
                envelope.Mz_min.governing_min_location = elem_id

            # Update minor-axis moment envelope
            if My > envelope.My_max.max_value:
                envelope.My_max.max_value = My
                envelope.My_max.governing_max_case = result.combination
                envelope.My_max.governing_max_location = elem_id
            if My_signed < envelope.My_min.min_value or envelope.My_min.min_value == 0.0:
                envelope.My_min.min_value = My_signed
                envelope.My_min.governing_min_case = result.combination
                envelope.My_min.governing_min_location = elem_id
    
    def _update_displacement_envelope(self, result: LoadCaseResult) -> None:
        """Update displacement envelopes with new load case results.
        
        Args:
            result: Load case result to process
        """
        for node_id, displacements in result.node_displacements.items():
            # Get or create envelope for this node
            if node_id not in self.displacement_envelopes:
                self.displacement_envelopes[node_id] = DisplacementEnvelope(node_id)
            
            envelope = self.displacement_envelopes[node_id]
            
            # Extract displacements (handle both 2D and 3D)
            # Assuming displacements format: [ux, uy, uz, rx, ry, rz]
            if len(displacements) >= 3:
                ux = abs(displacements[0])
                uy = abs(displacements[1])
                uz = abs(displacements[2])
                
                # Update X displacement envelope
                if ux > envelope.ux_max.max_value:
                    envelope.ux_max.max_value = ux
                    envelope.ux_max.governing_max_case = result.combination
                    envelope.ux_max.governing_max_location = node_id
                
                # Update Y displacement envelope
                if uy > envelope.uy_max.max_value:
                    envelope.uy_max.max_value = uy
                    envelope.uy_max.governing_max_case = result.combination
                    envelope.uy_max.governing_max_location = node_id
                
                # Update Z displacement envelope (vertical deflection)
                if uz > envelope.uz_max.max_value:
                    envelope.uz_max.max_value = uz
                    envelope.uz_max.governing_max_case = result.combination
                    envelope.uz_max.governing_max_location = node_id
    
    def _update_reaction_envelope(self, result: LoadCaseResult) -> None:
        """Update reaction envelopes with new load case results.
        
        Args:
            result: Load case result to process
        """
        for node_id, reactions in result.reactions.items():
            # Get or create envelope for this support node
            if node_id not in self.reaction_envelopes:
                self.reaction_envelopes[node_id] = ReactionEnvelope(node_id)
            
            envelope = self.reaction_envelopes[node_id]
            
            # Extract reactions (handle both 2D and 3D)
            # Assuming reactions format: [Fx, Fy, Fz, Mx, My, Mz]
            if len(reactions) >= 3:
                Fx = abs(reactions[0])
                Fy = abs(reactions[1])
                Fz = reactions[2]  # Keep sign for uplift check
                
                # Update horizontal reactions
                if Fx > envelope.Fx_max.max_value:
                    envelope.Fx_max.max_value = Fx
                    envelope.Fx_max.governing_max_case = result.combination
                    envelope.Fx_max.governing_max_location = node_id
                
                if Fy > envelope.Fy_max.max_value:
                    envelope.Fy_max.max_value = Fy
                    envelope.Fy_max.governing_max_case = result.combination
                    envelope.Fy_max.governing_max_location = node_id
                
                # Update vertical reaction (max compression)
                if Fz > envelope.Fz_max.max_value:
                    envelope.Fz_max.max_value = Fz
                    envelope.Fz_max.governing_max_case = result.combination
                    envelope.Fz_max.governing_max_location = node_id
                
                # Update vertical reaction (min - uplift check)
                if Fz < envelope.Fz_min.min_value or envelope.Fz_min.min_value == 0.0:
                    envelope.Fz_min.min_value = Fz
                    envelope.Fz_min.governing_min_case = result.combination
                    envelope.Fz_min.governing_min_location = node_id
                
                # Update overturning moments if available
                if len(reactions) >= 5:
                    Mx = abs(reactions[3])
                    My = abs(reactions[4])
                    
                    if Mx > envelope.Mx_max.max_value:
                        envelope.Mx_max.max_value = Mx
                        envelope.Mx_max.governing_max_case = result.combination
                        envelope.Mx_max.governing_max_location = node_id
                    
                    if My > envelope.My_max.max_value:
                        envelope.My_max.max_value = My
                        envelope.My_max.governing_max_case = result.combination
                        envelope.My_max.governing_max_location = node_id
    
    def calculate_inter_story_drift(
        self,
        node_elevations: Dict[int, float],
        story_height: float
    ) -> None:
        """Calculate inter-story drift ratios from displacement envelopes.
        
        HK Code / Eurocode 8 inter-story drift check requires drift ratios
        to be calculated from nodal displacements at adjacent floor levels.
        
        Args:
            node_elevations: Dictionary mapping node ID to elevation (m)
            story_height: Typical story height (m)
        """
        # Group nodes by floor level
        floors: Dict[float, List[int]] = {}
        for node_id, elevation in node_elevations.items():
            if elevation not in floors:
                floors[elevation] = []
            floors[elevation].append(node_id)
        
        # Sort floor elevations
        sorted_elevations = sorted(floors.keys())
        
        # Calculate drift for each floor
        for i in range(len(sorted_elevations) - 1):
            lower_elevation = sorted_elevations[i]
            upper_elevation = sorted_elevations[i + 1]
            height = upper_elevation - lower_elevation
            
            if height == 0:
                continue
            
            # Get nodes at each level
            lower_nodes = floors[lower_elevation]
            upper_nodes = floors[upper_elevation]
            
            # Calculate drift for each node pair
            for upper_node in upper_nodes:
                if upper_node not in self.displacement_envelopes:
                    continue
                
                upper_disp_x = self.displacement_envelopes[upper_node].ux_max.max_value
                upper_disp_y = self.displacement_envelopes[upper_node].uy_max.max_value
                
                # Find corresponding lower node (simplified - same X-Y position)
                # In practice, should match by coordinates
                for lower_node in lower_nodes:
                    if lower_node not in self.displacement_envelopes:
                        continue
                    
                    lower_disp_x = self.displacement_envelopes[lower_node].ux_max.max_value
                    lower_disp_y = self.displacement_envelopes[lower_node].uy_max.max_value
                    
                    # Calculate inter-story drift
                    drift_x = abs(upper_disp_x - lower_disp_x)
                    drift_y = abs(upper_disp_y - lower_disp_y)
                    drift = max(drift_x, drift_y)
                    drift_ratio = drift / height
                    
                    # Update drift envelope
                    if drift_ratio > self.displacement_envelopes[upper_node].drift_max.max_value:
                        self.displacement_envelopes[upper_node].drift_max.max_value = drift_ratio
                        # Copy governing case from displacement
                        self.displacement_envelopes[upper_node].drift_max.governing_max_case = \
                            self.displacement_envelopes[upper_node].ux_max.governing_max_case
    
    def get_critical_elements(
        self,
        n_elements: int = 10,
        criterion: str = "moment"
    ) -> List[Tuple[int, float, Optional[LoadCombination]]]:
        """Get critical elements with highest demand.
        
        Args:
            n_elements: Number of critical elements to return
            criterion: Sort criterion ("moment", "shear", "axial")
            
        Returns:
            List of tuples (element_id, max_value, governing_case)
        """
        critical = []
        
        for elem_id, envelope in self.element_force_envelopes.items():
            if criterion == "moment":
                value = envelope.Mz_max.max_value
                case = envelope.Mz_max.governing_max_case
            elif criterion == "shear":
                value = envelope.Vy_max.max_value
                case = envelope.Vy_max.governing_max_case
            elif criterion == "axial":
                value = envelope.N_max.max_value
                case = envelope.N_max.governing_max_case
            else:
                continue
            
            critical.append((elem_id, value, case))
        
        # Sort by value (descending)
        critical.sort(key=lambda x: x[1], reverse=True)
        
        return critical[:n_elements]
    
    def export_envelope_summary(self) -> str:
        """Export envelope summary for reporting.
        
        Returns:
            Formatted text summary
        """
        lines = []
        lines.append("=" * 80)
        lines.append("FEM RESULTS ENVELOPE SUMMARY")
        lines.append("=" * 80)
        
        # Element forces
        lines.append("\nELEMENT FORCE ENVELOPES:")
        lines.append(f"  Total elements enveloped: {len(self.element_force_envelopes)}")
        
        if self.element_force_envelopes:
            max_Mz = max(env.Mz_max.max_value for env in self.element_force_envelopes.values())
            max_My = max(env.My_max.max_value for env in self.element_force_envelopes.values())
            max_Vy = max(env.Vy_max.max_value for env in self.element_force_envelopes.values())
            max_Vz = max(env.Vz_max.max_value for env in self.element_force_envelopes.values())
            max_N = max(env.N_max.max_value for env in self.element_force_envelopes.values())
            
            lines.append(f"  Maximum Mz (major): {max_Mz/1e6:.2f} kN-m")
            lines.append(f"  Maximum My (minor): {max_My/1e6:.2f} kN-m")
            lines.append(f"  Maximum Vy (major shear): {max_Vy/1e3:.2f} kN")
            lines.append(f"  Maximum Vz (minor shear): {max_Vz/1e3:.2f} kN")
            lines.append(f"  Maximum axial: {max_N/1e3:.2f} kN")
        
        # Displacements
        lines.append("\nDISPLACEMENT ENVELOPES:")
        lines.append(f"  Total nodes enveloped: {len(self.displacement_envelopes)}")
        
        if self.displacement_envelopes:
            max_ux = max(env.ux_max.max_value for env in self.displacement_envelopes.values())
            max_uy = max(env.uy_max.max_value for env in self.displacement_envelopes.values())
            max_uz = max(env.uz_max.max_value for env in self.displacement_envelopes.values())
            
            lines.append(f"  Maximum horizontal X: {max_ux*1000:.2f} mm")
            lines.append(f"  Maximum horizontal Y: {max_uy*1000:.2f} mm")
            lines.append(f"  Maximum vertical: {max_uz*1000:.2f} mm")
        
        # Reactions
        lines.append("\nREACTION ENVELOPES:")
        lines.append(f"  Total support nodes: {len(self.reaction_envelopes)}")
        
        if self.reaction_envelopes:
            max_Fz = max(env.Fz_max.max_value for env in self.reaction_envelopes.values())
            min_Fz = min(env.Fz_min.min_value for env in self.reaction_envelopes.values())
            
            lines.append(f"  Maximum vertical reaction: {max_Fz/1e3:.2f} kN")
            lines.append(f"  Minimum vertical reaction: {min_Fz/1e3:.2f} kN")
            if min_Fz < 0:
                lines.append(f"  WARNING: Uplift detected ({min_Fz/1e3:.2f} kN)")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    @staticmethod
    def extract_reactions_dataframe(analysis_result, fixed_nodes):
        """Extract reaction forces as pandas DataFrame."""
        import pandas as pd
        
        if not analysis_result.node_reactions:
            return pd.DataFrame()
        
        rows = []
        for node_tag in sorted(fixed_nodes):
            if node_tag in analysis_result.node_reactions:
                reactions = analysis_result.node_reactions[node_tag]
                rows.append({
                    'Node': node_tag,
                    'Fx (kN)': reactions[0] / 1000.0,
                    'Fy (kN)': reactions[1] / 1000.0,
                    'Fz (kN)': reactions[2] / 1000.0,
                    'Mx (kNm)': reactions[3] / 1000.0,
                    'My (kNm)': reactions[4] / 1000.0,
                    'Mz (kNm)': reactions[5] / 1000.0,
                })
        
        return pd.DataFrame(rows)
    
    @staticmethod
    def extract_section_forces(
        result,
        model,
        force_type: str
    ) -> 'SectionForcesData':
        """Extract section forces from analysis results for visualization.
        
        Converts forces from N → kN and moments from N·m → kN·m for display.
        
        Handles subdivided elements (beams/columns split into 6 sub-elements):
        - Each sub-element is included in the output with its own element_id
        - Sub-elements can be grouped by parent_beam_id or parent_column_id
          in the element geometry metadata for visualization purposes
        - Forces are extracted at all subdivision nodes, enabling accurate
          parabolic force diagram visualization
        
        Args:
            result: AnalysisResult containing element_forces dict
            model: FEMModel containing element metadata
            force_type: Force component to extract (N, Vy, Vz, My, Mz, T)
            
        Returns:
            SectionForcesData with extracted forces in kN/kNm units
            (includes all sub-elements for subdivided beams/columns)
            
        Example:
            forces = ResultsProcessor.extract_section_forces(
                result=analysis_result,
                model=fem_model,
                force_type="Mz"
            )
            print(f"{len(forces.elements)} elements, range: {forces.get_color_range()}")
        """
        # Force key mapping for both 3D and 2D beam elements
        # 3D elements: Vy_i/Vy_j, Mz_i/Mz_j etc.
        # 2D elements: V_i/V_j, M_i/M_j
        force_key_map_3d = {
            "N": ("N_i", "N_j"),
            "Vy": ("Vy_i", "Vy_j"),
            "Vz": ("Vz_i", "Vz_j"),
            "T": ("T_i", "T_j"),
            "My": ("My_i", "My_j"),
            "Mz": ("Mz_i", "Mz_j"),
        }
        
        force_key_map_2d = {
            "N": ("N_i", "N_j"),
            "Vy": ("V_i", "V_j"),
            "Vz": ("V_i", "V_j"),
            "T": (None, None),
            "My": ("M_i", "M_j"),
            "Mz": ("M_i", "M_j"),
        }

        if force_type not in force_key_map_3d:
            raise ValueError(f"Unknown force type: {force_type}. Use one of {list(force_key_map_3d.keys())}")

        key_i_3d, key_j_3d = force_key_map_3d[force_type]
        key_i_2d, key_j_2d = force_key_map_2d[force_type]
        unit = "kN" if force_type in ["N", "Vy", "Vz"] else "kNm"
        
        elements_dict = {}
        min_val = float('inf')
        max_val = float('-inf')
        
        if not result.element_forces:
            return SectionForcesData(
                force_type=force_type,
                elements={},
                unit=unit,
                min_value=0.0,
                max_value=0.0
            )
        
        for elem_tag, force_dict in result.element_forces.items():
            if elem_tag not in model.elements:
                continue

            elem_info = model.elements[elem_tag]

            if len(elem_info.node_tags) != 2:
                continue

            key_i, key_j = None, None
            if key_i_3d in force_dict:
                key_i, key_j = key_i_3d, key_j_3d
            elif key_i_2d and key_i_2d in force_dict:
                key_i, key_j = key_i_2d, key_j_2d
            
            if key_i is None:
                continue

            node_i = elem_info.node_tags[0]
            node_j = elem_info.node_tags[1]

            force_i = force_dict[key_i] / 1000.0
            force_j = force_dict[key_j] / 1000.0
            
            elem_force = ElementForce(
                element_id=elem_tag,
                node_i=node_i,
                node_j=node_j,
                force_i=force_i,
                force_j=force_j
            )
            
            elements_dict[elem_tag] = elem_force
            
            min_val = min(min_val, force_i, force_j)
            max_val = max(max_val, force_i, force_j)
        
        if not elements_dict:
            min_val = 0.0
            max_val = 0.0
        
        return SectionForcesData(
            force_type=force_type,
            elements=elements_dict,
            unit=unit,
            min_value=min_val,
            max_value=max_val
        )

