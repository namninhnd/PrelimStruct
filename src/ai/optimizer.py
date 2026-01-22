"""
AI-Assisted Design Optimization Module

This module implements gradient-based design optimization for structural elements
with AI-guided optimization strategies using HK Code 2013 constraints.

Tasks:
- Task 13.1: Design Optimization Engine (gradient-based optimization)
- Task 13.2: AI-Guided Optimization (LLM integration for suggestions)

Author: PrelimStruct Development Team
Date: 2026-01-22
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Callable, Any
from enum import Enum
import math


class OptimizationObjective(Enum):
    """Optimization objective type."""
    MINIMIZE_COST = "minimize_cost"
    MINIMIZE_WEIGHT = "minimize_weight"
    MINIMIZE_DEFLECTION = "minimize_deflection"
    MULTI_OBJECTIVE = "multi_objective"


class OptimizationStatus(Enum):
    """Optimization convergence status."""
    CONVERGED = "converged"
    MAX_ITERATIONS = "max_iterations_reached"
    FAILED = "failed"
    CONSTRAINT_VIOLATION = "constraint_violation"


@dataclass
class DesignVariable:
    """
    Design variable for optimization.
    
    Attributes:
        name: Variable name (e.g., "beam_depth", "column_diameter")
        value: Current value
        lower_bound: Minimum allowed value
        upper_bound: Maximum allowed value
        step_size: Discretization step (for discrete variables)
    """
    name: str
    value: float
    lower_bound: float
    upper_bound: float
    step_size: Optional[float] = None  # None for continuous variables
    
    def is_continuous(self) -> bool:
        """Check if variable is continuous."""
        return self.step_size is None
    
    def is_within_bounds(self) -> bool:
        """Check if current value is within bounds."""
        return self.lower_bound <= self.value <= self.upper_bound
    
    def clip_to_bounds(self) -> None:
        """Clip value to bounds."""
        self.value = max(self.lower_bound, min(self.upper_bound, self.value))
    
    def round_to_step(self) -> None:
        """Round value to nearest step (for discrete variables)."""
        if self.step_size is not None:
            steps = round((self.value - self.lower_bound) / self.step_size)
            self.value = self.lower_bound + steps * self.step_size
            self.clip_to_bounds()


@dataclass
class OptimizationConstraint:
    """
    Optimization constraint (stress, deflection, code limits).
    
    Attributes:
        name: Constraint name (e.g., "max_stress", "deflection_limit")
        constraint_func: Function that returns constraint value (g(x) <= 0)
        tolerance: Constraint tolerance
        weight: Penalty weight for constraint violation
    """
    name: str
    constraint_func: Callable[[Dict[str, float]], float]
    tolerance: float = 1e-6
    weight: float = 1000.0  # High penalty for violations
    
    def is_satisfied(self, design_vars: Dict[str, float]) -> bool:
        """Check if constraint is satisfied."""
        return self.evaluate(design_vars) <= self.tolerance
    
    def evaluate(self, design_vars: Dict[str, float]) -> float:
        """Evaluate constraint value (g(x) <= 0)."""
        return self.constraint_func(design_vars)
    
    def penalty(self, design_vars: Dict[str, float]) -> float:
        """Calculate penalty for constraint violation."""
        violation = max(0.0, self.evaluate(design_vars))
        return self.weight * violation ** 2


@dataclass
class OptimizationResult:
    """
    Optimization result.
    
    Attributes:
        status: Convergence status
        optimal_design: Optimal design variables
        objective_value: Final objective function value
        iterations: Number of iterations
        constraint_violations: List of violated constraints
        convergence_history: Objective value history
        improvement_percent: Improvement over initial design (%)
        ai_suggestions: AI-generated optimization suggestions
    """
    status: OptimizationStatus
    optimal_design: Dict[str, float]
    objective_value: float
    iterations: int
    constraint_violations: List[str]
    convergence_history: List[float]
    improvement_percent: float
    ai_suggestions: Optional[str] = None


@dataclass
class OptimizationConfig:
    """
    Optimization configuration.
    
    Attributes:
        max_iterations: Maximum number of iterations
        tolerance: Convergence tolerance
        step_size_multiplier: Step size for gradient estimation
        learning_rate: Learning rate for gradient descent
        use_ai_suggestions: Enable AI-guided optimization
    """
    max_iterations: int = 100
    tolerance: float = 1e-4
    step_size_multiplier: float = 0.01  # 1% perturbation for gradient
    learning_rate: float = 0.1
    use_ai_suggestions: bool = True


class DesignOptimizer:
    """
    Gradient-based design optimizer with constraint handling.
    
    Supports:
    - Single and multi-objective optimization
    - Equality and inequality constraints
    - Discrete and continuous design variables
    - Penalty method for constraint handling
    - Gradient descent with adaptive learning rate
    
    HK Code 2013 Compliance:
    - All constraints based on HK Code 2013 stress/deflection limits
    - Material strength constraints per HK Code Cl 3.1.6
    - Deflection limits per HK Code Cl 3.2.1.2
    """
    
    def __init__(self, config: OptimizationConfig = OptimizationConfig()):
        """
        Initialize optimizer.
        
        Args:
            config: Optimization configuration
        """
        self.config = config
        self.design_vars: List[DesignVariable] = []
        self.constraints: List[OptimizationConstraint] = []
        self.objective_func: Optional[Callable[[Dict[str, float]], float]] = None
        self.convergence_history: List[float] = []
    
    def add_design_variable(
        self,
        name: str,
        initial_value: float,
        lower_bound: float,
        upper_bound: float,
        step_size: Optional[float] = None
    ) -> None:
        """
        Add design variable.
        
        Args:
            name: Variable name
            initial_value: Initial value
            lower_bound: Minimum allowed value
            upper_bound: Maximum allowed value
            step_size: Discretization step (None for continuous)
        """
        var = DesignVariable(
            name=name,
            value=initial_value,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            step_size=step_size
        )
        var.clip_to_bounds()
        if not var.is_continuous():
            var.round_to_step()
        self.design_vars.append(var)
    
    def add_constraint(
        self,
        name: str,
        constraint_func: Callable[[Dict[str, float]], float],
        tolerance: float = 1e-6,
        weight: float = 1000.0
    ) -> None:
        """
        Add optimization constraint.
        
        Args:
            name: Constraint name
            constraint_func: Function that returns g(x) <= 0
            tolerance: Constraint tolerance
            weight: Penalty weight
        """
        self.constraints.append(
            OptimizationConstraint(name, constraint_func, tolerance, weight)
        )
    
    def set_objective(
        self,
        objective_func: Callable[[Dict[str, float]], float]
    ) -> None:
        """
        Set objective function to minimize.
        
        Args:
            objective_func: Objective function f(x)
        """
        self.objective_func = objective_func
    
    def _get_design_dict(self) -> Dict[str, float]:
        """Get current design variables as dictionary."""
        return {var.name: var.value for var in self.design_vars}
    
    def _evaluate_objective(self, design_dict: Dict[str, float]) -> float:
        """
        Evaluate objective function with penalty for constraints.
        
        Args:
            design_dict: Design variables
            
        Returns:
            Objective value + constraint penalties
        """
        if self.objective_func is None:
            raise ValueError("Objective function not set")
        
        # Base objective
        obj = self.objective_func(design_dict)
        
        # Add constraint penalties
        for constraint in self.constraints:
            obj += constraint.penalty(design_dict)
        
        return obj
    
    def _estimate_gradient(self) -> Dict[str, float]:
        """
        Estimate gradient using finite differences.
        
        Returns:
            Gradient dict {var_name: df/dx}
        """
        gradient = {}
        base_design = self._get_design_dict()
        base_obj = self._evaluate_objective(base_design)
        
        for var in self.design_vars:
            # Perturb variable
            delta = self.config.step_size_multiplier * abs(var.value)
            if delta < 1e-8:
                delta = 1e-6  # Minimum perturbation
            
            perturbed_design = base_design.copy()
            perturbed_design[var.name] = var.value + delta
            
            # Evaluate perturbed objective
            perturbed_obj = self._evaluate_objective(perturbed_design)
            
            # Central difference gradient
            gradient[var.name] = (perturbed_obj - base_obj) / delta
        
        return gradient
    
    def _update_design_variables(self, gradient: Dict[str, float]) -> None:
        """
        Update design variables using gradient descent.
        
        Args:
            gradient: Gradient dictionary
        """
        for var in self.design_vars:
            # Gradient descent step
            var.value -= self.config.learning_rate * gradient[var.name]
            
            # Enforce bounds
            var.clip_to_bounds()
            
            # Round to step for discrete variables
            if not var.is_continuous():
                var.round_to_step()
    
    def _check_convergence(
        self,
        current_obj: float,
        previous_obj: Optional[float]
    ) -> bool:
        """
        Check convergence based on objective change.
        
        Args:
            current_obj: Current objective value
            previous_obj: Previous objective value
            
        Returns:
            True if converged
        """
        if previous_obj is None:
            return False
        
        relative_change = abs(current_obj - previous_obj) / max(abs(previous_obj), 1e-8)
        return relative_change < self.config.tolerance
    
    def _get_violated_constraints(self) -> List[str]:
        """
        Get list of violated constraints.
        
        Returns:
            List of violated constraint names
        """
        design_dict = self._get_design_dict()
        violations = []
        
        for constraint in self.constraints:
            if not constraint.is_satisfied(design_dict):
                violations.append(constraint.name)
        
        return violations
    
    def optimize(self) -> OptimizationResult:
        """
        Run gradient-based optimization.
        
        Returns:
            Optimization result with optimal design
        """
        if self.objective_func is None:
            raise ValueError("Objective function not set")
        
        if not self.design_vars:
            raise ValueError("No design variables defined")
        
        # Initialize
        self.convergence_history = []
        initial_design = self._get_design_dict()
        initial_obj = self._evaluate_objective(initial_design)
        self.convergence_history.append(initial_obj)
        
        previous_obj = None
        status = OptimizationStatus.MAX_ITERATIONS
        
        # Optimization loop
        for iteration in range(self.config.max_iterations):
            # Estimate gradient
            gradient = self._estimate_gradient()
            
            # Update design variables
            self._update_design_variables(gradient)
            
            # Evaluate new objective
            current_obj = self._evaluate_objective(self._get_design_dict())
            self.convergence_history.append(current_obj)
            
            # Check convergence
            if self._check_convergence(current_obj, previous_obj):
                status = OptimizationStatus.CONVERGED
                break
            
            previous_obj = current_obj
        
        # Final evaluation
        optimal_design = self._get_design_dict()
        final_obj = self._evaluate_objective(optimal_design)
        violations = self._get_violated_constraints()
        
        if violations:
            status = OptimizationStatus.CONSTRAINT_VIOLATION
        
        # Calculate improvement
        improvement = 100 * (initial_obj - final_obj) / max(abs(initial_obj), 1e-8)
        
        return OptimizationResult(
            status=status,
            optimal_design=optimal_design,
            objective_value=final_obj,
            iterations=len(self.convergence_history) - 1,
            constraint_violations=violations,
            convergence_history=self.convergence_history,
            improvement_percent=improvement
        )


# Example usage with HK Code 2013 constraints
def create_beam_optimizer(
    initial_depth: float,
    initial_width: float,
    span: float,
    max_stress: float,
    max_deflection: float
) -> DesignOptimizer:
    """
    Create beam section optimizer with HK Code 2013 constraints.
    
    Args:
        initial_depth: Initial beam depth (mm)
        initial_width: Initial beam width (mm)
        span: Beam span (mm)
        max_stress: Maximum allowable stress (MPa) per HK Code
        max_deflection: Maximum deflection (mm) per HK Code Cl 3.2.1.2
        
    Returns:
        Configured optimizer
    """
    optimizer = DesignOptimizer()
    
    # Design variables (discrete to match standard sizes)
    optimizer.add_design_variable("depth", initial_depth, 300, 1200, step_size=50)
    optimizer.add_design_variable("width", initial_width, 200, 800, step_size=50)
    
    # Objective: minimize cost (proportional to cross-sectional area)
    def cost_func(design: Dict[str, float]) -> float:
        """Cost proportional to volume."""
        area = design["depth"] * design["width"]  # mm²
        return area * span / 1e9  # Normalized volume (m³)
    
    optimizer.set_objective(cost_func)
    
    # Constraint 1: Stress limit (HK Code Cl 6.1.2.4)
    def stress_constraint(design: Dict[str, float]) -> float:
        """Stress constraint: σ <= σ_max (g(x) <= 0)."""
        # Simplified stress calculation (bending)
        moment = 100e6  # Example: 100 kNm = 100e6 Nmm
        section_modulus = (design["width"] * design["depth"]**2) / 6  # mm³
        stress = moment / section_modulus  # MPa
        return stress - max_stress  # g(x) <= 0
    
    optimizer.add_constraint("stress_limit", stress_constraint)
    
    # Constraint 2: Deflection limit (HK Code Cl 3.2.1.2: span/250)
    def deflection_constraint(design: Dict[str, float]) -> float:
        """Deflection constraint: δ <= δ_max (g(x) <= 0)."""
        # Simplified deflection (uniform load on simply supported beam)
        E_c = 30000  # MPa (C40 concrete)
        I = (design["width"] * design["depth"]**3) / 12  # mm⁴
        load = 10  # N/mm (example uniform load)
        deflection = (5 * load * span**4) / (384 * E_c * I)  # mm
        return deflection - max_deflection  # g(x) <= 0
    
    optimizer.add_constraint("deflection_limit", deflection_constraint)
    
    return optimizer


def get_ai_optimization_suggestions(
    result: OptimizationResult,
    project_context: Optional[str] = None,
    use_ai: bool = True
) -> str:
    """
    Get AI-guided optimization suggestions using LLM.
    
    Integrates with AIService (Task 13.2) to provide natural language
    optimization recommendations using DeepSeek/Grok/OpenRouter.
    
    Args:
        result: Optimization result
        project_context: Optional project context for AI
        use_ai: Enable AI suggestions (default True)
        
    Returns:
        AI-generated or rule-based optimization suggestions
    """
    # Rule-based summary (always generated)
    summary = f"""
Optimization Summary:
- Status: {result.status.value}
- Improvement: {result.improvement_percent:.1f}%
- Iterations: {result.iterations}

Optimal Design:
"""
    for var, value in result.optimal_design.items():
        summary += f"- {var}: {value:.0f} mm\n"
    
    if result.constraint_violations:
        summary += f"\nConstraint Violations: {', '.join(result.constraint_violations)}\n"
    
    # AI-guided suggestions (if enabled)
    if use_ai:
        try:
            from .llm_service import AIService
            from .config import AIConfig
            from .prompts import OPTIMIZATION_TEMPLATE
            
            # Create AI service with default config from environment
            ai_service = AIService.from_env()
            
            # Prepare optimization context
            opt_context = f"""
Design Variables:
{chr(10).join(f'- {var}: {value:.1f} mm' for var, value in result.optimal_design.items())}

Optimization Result:
- Status: {result.status.value}
- Improvement: {result.improvement_percent:.1f}%
- Iterations: {result.iterations}
- Constraint Violations: {', '.join(result.constraint_violations) if result.constraint_violations else 'None'}

Convergence History:
- Initial Objective: {result.convergence_history[0]:.4f}
- Final Objective: {result.convergence_history[-1]:.4f}
"""
            
            if project_context:
                opt_context += f"\n\nProject Context:\n{project_context}"
            
            # Get AI suggestions using optimization prompt
            prompt = OPTIMIZATION_TEMPLATE.format(optimization_summary=opt_context)
            
            ai_response = ai_service.chat(
                user_message=prompt,
                temperature=0.7,  # Slightly creative for suggestions
                max_tokens=400
            )
            
            # Combine rule-based summary with AI suggestions (chat returns str)
            summary += f"\n\nAI Recommendations:\n{ai_response}"
            
        except ImportError:
            # AIService not available, use rule-based
            summary += _get_rule_based_suggestions(result)
        except Exception as e:
            # AI failed, use rule-based fallback
            summary += f"\n\n(AI suggestions unavailable: {str(e)})\n"
            summary += _get_rule_based_suggestions(result)
    else:
        # Use rule-based suggestions only
        summary += _get_rule_based_suggestions(result)
    
    return summary


def _get_rule_based_suggestions(result: OptimizationResult) -> str:
    """
    Get rule-based optimization suggestions (fallback).
    
    Args:
        result: Optimization result
        
    Returns:
        Rule-based recommendations
    """
    suggestions = "\n\nRecommendations:\n"
    
    # Status-specific recommendations
    if result.status == OptimizationStatus.CONVERGED:
        suggestions += "- Optimization converged successfully\n"
    elif result.status == OptimizationStatus.MAX_ITERATIONS:
        suggestions += "- Optimization stopped at max iterations (consider increasing limit)\n"
    elif result.status == OptimizationStatus.CONSTRAINT_VIOLATION:
        suggestions += "- Constraint violations detected (review design or relax constraints)\n"
    
    # Improvement-based recommendations
    if result.improvement_percent > 20:
        suggestions += "- Significant improvement achieved (>20%)\n"
    elif result.improvement_percent < 5:
        suggestions += "- Limited improvement (<5%), initial design may be near optimal\n"
    
    # Constraint violation recommendations
    if result.constraint_violations:
        suggestions += f"- Address constraint violations: {', '.join(result.constraint_violations)}\n"
    
    # General recommendations
    suggestions += "- Verify constructability and material availability\n"
    suggestions += "- Check code compliance per HK Code 2013\n"
    suggestions += "- Consider cost-performance trade-offs\n"
    
    return suggestions
