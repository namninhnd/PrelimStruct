"""
Solver interface for linear static FEM analysis using OpenSeesPy.

This module provides analysis and solution extraction capabilities for
structural finite element models.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass
class AnalysisResult:
    """Results from FEM analysis.
    
    Attributes:
        success: Whether analysis completed successfully
        message: Status or error message
        converged: Whether solution converged
        iterations: Number of iterations (if applicable)
        node_displacements: Node displacements {node_tag: [ux, uy, uz, rx, ry, rz]}
        node_reactions: Reaction forces {node_tag: [Fx, Fy, Fz, Mx, My, Mz]}
        element_forces: Element forces {element_tag: force_dict}
    """
    success: bool
    message: str
    converged: bool = True
    iterations: int = 0
    node_displacements: Dict[int, List[float]] = field(default_factory=dict)
    node_reactions: Dict[int, List[float]] = field(default_factory=dict)
    element_forces: Dict[int, Dict[str, float]] = field(default_factory=dict)
    
    def get_max_displacement(self, dof: int = 2) -> Tuple[int, float]:
        """Get maximum displacement and node tag.
        
        Args:
            dof: Degree of freedom index (0=ux, 1=uy, 2=uz, 3=rx, 4=ry, 5=rz)
        
        Returns:
            Tuple of (node_tag, max_displacement)
        """
        if not self.node_displacements:
            return (0, 0.0)
        
        max_disp = 0.0
        max_node = 0
        for node_tag, disps in self.node_displacements.items():
            if abs(disps[dof]) > abs(max_disp):
                max_disp = disps[dof]
                max_node = node_tag
        
        return (max_node, max_disp)
    
    def get_total_reaction(self, dof: int = 2) -> float:
        """Get total reaction force/moment.
        
        Args:
            dof: Degree of freedom index (0=Fx, 1=Fy, 2=Fz, 3=Mx, 4=My, 5=Mz)
        
        Returns:
            Sum of all reactions in specified DOF
        """
        if not self.node_reactions:
            return 0.0
        
        total = sum(reactions[dof] for reactions in self.node_reactions.values())
        return total


class FEMSolver:
    """OpenSeesPy linear static solver.
    
    This class handles analysis setup, solution, and result extraction
    for linear static structural analysis.
    """
    
    def __init__(self):
        """Initialize solver."""
        self._ops_available = False
        try:
            import openseespy.opensees as ops
            self.ops = ops
            self._ops_available = True
        except ImportError:
            self.ops = None
    
    def check_availability(self) -> bool:
        """Check if OpenSeesPy is available.
        
        Returns:
            True if OpenSeesPy is installed and imported
        """
        return self._ops_available
    
    def run_linear_static_analysis(self,
                                   load_pattern: int = 1,
                                   max_iterations: int = 100,
                                   tolerance: float = 1e-6) -> AnalysisResult:
        """Run linear static analysis.
        
        This performs a linear static analysis on the current OpenSeesPy model.
        The model must be built before calling this method.
        
        Args:
            load_pattern: Load pattern identifier to analyze
            max_iterations: Maximum iterations for nonlinear solver (if needed)
            tolerance: Convergence tolerance
        
        Returns:
            AnalysisResult with displacements, reactions, and element forces
            
        Raises:
            RuntimeError: If OpenSeesPy is not available or model not built
        """
        if not self._ops_available:
            raise RuntimeError(
                "OpenSeesPy is not available. Install with: pip install openseespy"
            )
        
        ops = self.ops
        
        # Create analysis
        # For linear static analysis, we use:
        # - constraints: Plain (or Transformation for MPCs)
        # - numberer: RCM (Reverse Cuthill-McKee for bandwidth optimization)
        # - system: BandGeneral (for general systems) or ProfileSPD (for symmetric)
        # - test: NormDispIncr (convergence test)
        # - algorithm: Linear (for linear analysis)
        # - integrator: LoadControl (static load)
        # - analysis: Static
        
        try:
            ops.constraints('Plain')
            ops.numberer('RCM')
            ops.system('BandGeneral')
            ops.test('NormDispIncr', tolerance, max_iterations)
            ops.algorithm('Linear')
            ops.integrator('LoadControl', 1.0)  # Apply full load in one step
            ops.analysis('Static')
            
            # Analyze
            result_code = ops.analyze(1)  # 1 step
            
            if result_code == 0:
                # Analysis successful - extract results
                results = self.extract_results()
                results.success = True
                results.converged = True
                results.message = "Analysis completed successfully"
                return results
            else:
                # Analysis failed
                return AnalysisResult(
                    success=False,
                    converged=False,
                    message=f"Analysis failed with code {result_code}"
                )
        
        except Exception as e:
            return AnalysisResult(
                success=False,
                converged=False,
                message=f"Analysis error: {str(e)}"
            )
    
    def extract_results(self) -> AnalysisResult:
        """Extract analysis results from OpenSeesPy model.
        
        Returns:
            AnalysisResult with current state of model
        """
        if not self._ops_available:
            raise RuntimeError("OpenSeesPy is not available")
        
        ops = self.ops
        
        result = AnalysisResult(success=True, message="Results extracted")
        
        # Get all node tags
        node_tags = ops.getNodeTags()
        
        # Extract displacements for all nodes
        for node_tag in node_tags:
            disp = ops.nodeDisp(node_tag)
            result.node_displacements[node_tag] = list(disp)
        
        # Extract reactions for fixed nodes
        for node_tag in node_tags:
            reaction = ops.nodeReaction(node_tag)
            # Only store if non-zero (i.e., node has restraints)
            if any(abs(r) > 1e-10 for r in reaction):
                result.node_reactions[node_tag] = list(reaction)
        
        # Extract element forces
        elem_tags = ops.getEleTags()
        for elem_tag in elem_tags:
            try:
                # Get element forces (returns different values for different element types)
                forces = ops.eleForce(elem_tag)
                
                # For beam-column elements in 3D, forces are typically:
                # [Fx_i, Fy_i, Fz_i, Mx_i, My_i, Mz_i, Fx_j, Fy_j, Fz_j, Mx_j, My_j, Mz_j]
                # where i is node 1, j is node 2
                
                if len(forces) == 12:  # 3D beam element
                    result.element_forces[elem_tag] = {
                        'N_i': forces[0],      # Axial force at i
                        'Vy_i': forces[1],     # Shear Y at i
                        'Vz_i': forces[2],     # Shear Z at i
                        'T_i': forces[3],      # Torque at i
                        'My_i': forces[4],     # Moment Y at i
                        'Mz_i': forces[5],     # Moment Z at i
                        'N_j': forces[6],      # Axial force at j
                        'Vy_j': forces[7],     # Shear Y at j
                        'Vz_j': forces[8],     # Shear Z at j
                        'T_j': forces[9],      # Torque at j
                        'My_j': forces[10],    # Moment Y at j
                        'Mz_j': forces[11],    # Moment Z at j
                    }
                elif len(forces) == 6:  # 2D beam element
                    result.element_forces[elem_tag] = {
                        'N_i': forces[0],      # Axial force at i
                        'V_i': forces[1],      # Shear at i
                        'M_i': forces[2],      # Moment at i
                        'N_j': forces[3],      # Axial force at j
                        'V_j': forces[4],      # Shear at j
                        'M_j': forces[5],      # Moment at j
                    }
                else:
                    # Store raw forces for other element types
                    result.element_forces[elem_tag] = {
                        f'force_{i}': f for i, f in enumerate(forces)
                    }
            except:
                # Skip elements that don't support force extraction
                pass
        
        return result
    
    def get_element_stress(self, element_tag: int) -> Optional[Dict[str, float]]:
        """Get element stresses (if available).
        
        Args:
            element_tag: Element identifier
        
        Returns:
            Dictionary of stresses or None if not available
        """
        if not self._ops_available:
            return None
        
        try:
            # This depends on element type - may not be available for all elements
            stresses = self.ops.eleResponse(element_tag, 'stresses')
            return {'stress': stresses}
        except:
            return None
    
    def get_natural_frequencies(self, n_modes: int = 5) -> Optional[np.ndarray]:
        """Get natural frequencies via eigenvalue analysis.
        
        Args:
            n_modes: Number of modes to extract
        
        Returns:
            Array of natural frequencies (Hz) or None if analysis fails
        """
        if not self._ops_available:
            return None
        
        try:
            # Eigenvalue analysis
            eigenvalues = self.ops.eigen(n_modes)
            
            # Convert eigenvalues to frequencies
            # omega = sqrt(lambda), f = omega / (2*pi)
            frequencies = np.sqrt(np.array(eigenvalues)) / (2 * np.pi)
            
            return frequencies
        except:
            return None
    
    def reset_model(self) -> None:
        """Reset/wipe OpenSeesPy model."""
        if self._ops_available:
            self.ops.wipe()


def analyze_model(model, load_pattern: int = 1) -> AnalysisResult:
    """Convenience function to build and analyze a FEMModel.
    
    Args:
        model: FEMModel instance
        load_pattern: Load pattern to analyze
    
    Returns:
        AnalysisResult with analysis outcomes
    """
    from src.fem.fem_engine import FEMModel
    
    if not isinstance(model, FEMModel):
        raise TypeError("model must be a FEMModel instance")
    
    # Validate model
    is_valid, errors = model.validate_model()
    if not is_valid:
        return AnalysisResult(
            success=False,
            converged=False,
            message=f"Model validation failed: {'; '.join(errors)}"
        )
    
    # Build OpenSeesPy model
    try:
        model.build_openseespy_model()
    except Exception as e:
        return AnalysisResult(
            success=False,
            converged=False,
            message=f"Model build failed: {str(e)}"
        )
    
    # Run analysis
    solver = FEMSolver()
    if not solver.check_availability():
        return AnalysisResult(
            success=False,
            converged=False,
            message="OpenSeesPy not available. Install with: pip install openseespy"
        )
    
    return solver.run_linear_static_analysis(load_pattern=load_pattern)


def print_analysis_summary(result: AnalysisResult) -> None:
    """Print formatted analysis summary.
    
    Args:
        result: AnalysisResult to summarize
    """
    print("\n" + "="*60)
    print("FEM ANALYSIS SUMMARY")
    print("="*60)
    print(f"Status: {'SUCCESS' if result.success else 'FAILED'}")
    print(f"Message: {result.message}")
    print(f"Converged: {result.converged}")
    
    if result.success:
        print(f"\nNodes analyzed: {len(result.node_displacements)}")
        print(f"Elements analyzed: {len(result.element_forces)}")
        print(f"Support reactions: {len(result.node_reactions)}")
        
        # Max displacements
        node_uz, max_uz = result.get_max_displacement(dof=2)
        print(f"\nMax vertical displacement: {max_uz*1000:.3f} mm at node {node_uz}")
        
        node_ux, max_ux = result.get_max_displacement(dof=0)
        print(f"Max horizontal displacement: {max_ux*1000:.3f} mm at node {node_ux}")
        
        # Total reactions
        total_fz = result.get_total_reaction(dof=2)
        print(f"\nTotal vertical reaction: {total_fz/1000:.2f} kN")
    
    print("="*60 + "\n")
