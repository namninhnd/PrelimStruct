"""
Unit tests for AI-Assisted Design Optimization module.

Tests cover:
- Design variable management
- Constraint handling
- Gradient-based optimization
- Convergence checking
- HK Code 2013 compliance

Author: PrelimStruct Development Team
Date: 2026-01-22
"""

import pytest
import math
from typing import Dict

from src.ai.optimizer import (
    DesignVariable,
    OptimizationConstraint,
    OptimizationResult,
    OptimizationConfig,
    OptimizationObjective,
    OptimizationStatus,
    DesignOptimizer,
    create_beam_optimizer,
    get_ai_optimization_suggestions
)


# ============================================================================
# Test DesignVariable
# ============================================================================

def test_design_variable_continuous():
    """Test continuous design variable."""
    var = DesignVariable("depth", 500.0, 300.0, 1200.0, step_size=None)
    
    assert var.name == "depth"
    assert var.value == 500.0
    assert var.is_continuous()
    assert var.is_within_bounds()


def test_design_variable_discrete():
    """Test discrete design variable with step size."""
    var = DesignVariable("depth", 505.0, 300.0, 1200.0, step_size=50.0)
    
    assert var.name == "depth"
    assert not var.is_continuous()
    
    # Round to nearest step
    var.round_to_step()
    assert var.value == 500.0  # Rounded to nearest 50mm


def test_design_variable_bounds_clipping():
    """Test bounds clipping."""
    var = DesignVariable("depth", 1500.0, 300.0, 1200.0)
    
    assert not var.is_within_bounds()
    
    var.clip_to_bounds()
    assert var.value == 1200.0  # Clipped to upper bound
    assert var.is_within_bounds()


def test_design_variable_discrete_rounding():
    """Test discrete variable rounding to step."""
    var = DesignVariable("width", 327.0, 200.0, 800.0, step_size=50.0)
    
    var.round_to_step()
    assert var.value == 350.0  # Nearest 50mm step


# ============================================================================
# Test OptimizationConstraint
# ============================================================================

def test_constraint_satisfied():
    """Test constraint satisfaction check."""
    def constraint_func(design: Dict[str, float]) -> float:
        return design["x"] - 10.0  # x <= 10
    
    constraint = OptimizationConstraint("max_x", constraint_func)
    
    # Satisfied
    assert constraint.is_satisfied({"x": 8.0})
    assert constraint.evaluate({"x": 8.0}) == -2.0
    
    # Violated
    assert not constraint.is_satisfied({"x": 12.0})
    assert constraint.evaluate({"x": 12.0}) == 2.0


def test_constraint_penalty():
    """Test constraint penalty calculation."""
    def constraint_func(design: Dict[str, float]) -> float:
        return design["x"] - 10.0  # x <= 10
    
    constraint = OptimizationConstraint("max_x", constraint_func, weight=1000.0)
    
    # No penalty if satisfied
    penalty_satisfied = constraint.penalty({"x": 8.0})
    assert penalty_satisfied == 0.0
    
    # Penalty if violated
    penalty_violated = constraint.penalty({"x": 12.0})
    assert penalty_violated > 0.0
    assert penalty_violated == 1000.0 * (2.0 ** 2)  # weight * violation^2


# ============================================================================
# Test DesignOptimizer - Basic Functionality
# ============================================================================

def test_optimizer_add_design_variable():
    """Test adding design variables."""
    optimizer = DesignOptimizer()
    
    optimizer.add_design_variable("depth", 500.0, 300.0, 1200.0)
    optimizer.add_design_variable("width", 300.0, 200.0, 800.0, step_size=50.0)
    
    assert len(optimizer.design_vars) == 2
    assert optimizer.design_vars[0].name == "depth"
    assert optimizer.design_vars[1].name == "width"


def test_optimizer_add_constraint():
    """Test adding constraints."""
    optimizer = DesignOptimizer()
    
    def constraint_func(design: Dict[str, float]) -> float:
        return design["x"] - 10.0
    
    optimizer.add_constraint("max_x", constraint_func)
    
    assert len(optimizer.constraints) == 1
    assert optimizer.constraints[0].name == "max_x"


def test_optimizer_set_objective():
    """Test setting objective function."""
    optimizer = DesignOptimizer()
    
    def objective_func(design: Dict[str, float]) -> float:
        return design["x"] ** 2
    
    optimizer.set_objective(objective_func)
    
    assert optimizer.objective_func is not None


def test_optimizer_get_design_dict():
    """Test getting design variables as dictionary."""
    optimizer = DesignOptimizer()
    optimizer.add_design_variable("depth", 500.0, 300.0, 1200.0)
    optimizer.add_design_variable("width", 300.0, 200.0, 800.0)
    
    design_dict = optimizer._get_design_dict()
    
    assert design_dict == {"depth": 500.0, "width": 300.0}


# ============================================================================
# Test DesignOptimizer - Gradient Estimation
# ============================================================================

def test_optimizer_gradient_estimation():
    """Test gradient estimation using finite differences."""
    optimizer = DesignOptimizer()
    optimizer.add_design_variable("x", 5.0, 0.0, 10.0)
    
    # Objective: f(x) = x^2, gradient = 2x
    def objective_func(design: Dict[str, float]) -> float:
        return design["x"] ** 2
    
    optimizer.set_objective(objective_func)
    
    gradient = optimizer._estimate_gradient()
    
    # Gradient should be approximately 2*5 = 10
    assert "x" in gradient
    assert abs(gradient["x"] - 10.0) < 1.0  # Finite difference approximation


def test_optimizer_update_design_variables():
    """Test design variable update using gradient descent."""
    optimizer = DesignOptimizer(OptimizationConfig(learning_rate=0.1))
    optimizer.add_design_variable("x", 5.0, 0.0, 10.0)
    
    # Gradient indicates x should decrease (minimize x^2)
    gradient = {"x": 10.0}
    
    initial_value = optimizer.design_vars[0].value
    optimizer._update_design_variables(gradient)
    
    # x should decrease by learning_rate * gradient = 0.1 * 10 = 1.0
    assert optimizer.design_vars[0].value < initial_value
    assert abs(optimizer.design_vars[0].value - 4.0) < 0.1


# ============================================================================
# Test DesignOptimizer - Convergence
# ============================================================================

def test_optimizer_convergence_check():
    """Test convergence checking."""
    optimizer = DesignOptimizer(OptimizationConfig(tolerance=1e-4))
    
    # Not converged (large change)
    assert not optimizer._check_convergence(10.0, 5.0)
    
    # Converged (small change)
    assert optimizer._check_convergence(10.0, 10.00005)


def test_optimizer_violated_constraints():
    """Test getting violated constraints."""
    optimizer = DesignOptimizer()
    optimizer.add_design_variable("x", 12.0, 0.0, 20.0)
    
    def constraint_func(design: Dict[str, float]) -> float:
        return design["x"] - 10.0  # x <= 10
    
    optimizer.add_constraint("max_x", constraint_func)
    
    violations = optimizer._get_violated_constraints()
    
    assert "max_x" in violations


# ============================================================================
# Test DesignOptimizer - Simple Optimization
# ============================================================================

def test_optimizer_simple_unconstrained():
    """Test simple unconstrained optimization: minimize x^2."""
    optimizer = DesignOptimizer(OptimizationConfig(max_iterations=50, tolerance=1e-3))
    optimizer.add_design_variable("x", 5.0, 0.0, 10.0)
    
    # Objective: minimize x^2 (optimal x = 0)
    def objective_func(design: Dict[str, float]) -> float:
        return design["x"] ** 2
    
    optimizer.set_objective(objective_func)
    
    result = optimizer.optimize()
    
    assert result.status in [OptimizationStatus.CONVERGED, OptimizationStatus.MAX_ITERATIONS]
    assert result.optimal_design["x"] < 1.0  # Should be close to 0
    assert result.improvement_percent > 0  # Should improve


def test_optimizer_simple_constrained():
    """Test simple constrained optimization: minimize x^2 subject to x >= 3."""
    optimizer = DesignOptimizer(OptimizationConfig(max_iterations=50))
    optimizer.add_design_variable("x", 5.0, 3.0, 10.0)  # Lower bound = 3
    
    # Objective: minimize x^2 (optimal x = 3 due to constraint)
    def objective_func(design: Dict[str, float]) -> float:
        return design["x"] ** 2
    
    optimizer.set_objective(objective_func)
    
    result = optimizer.optimize()
    
    assert result.status in [OptimizationStatus.CONVERGED, OptimizationStatus.MAX_ITERATIONS]
    assert result.optimal_design["x"] >= 3.0  # Respects lower bound
    assert result.optimal_design["x"] <= 3.5  # Should be near lower bound


def test_optimizer_rosenbrock_2d():
    """Test 2D Rosenbrock function optimization."""
    optimizer = DesignOptimizer(
        OptimizationConfig(max_iterations=200, learning_rate=0.01, tolerance=1e-2)
    )
    optimizer.add_design_variable("x", 0.0, -5.0, 5.0)
    optimizer.add_design_variable("y", 0.0, -5.0, 5.0)
    
    # Rosenbrock function: (1-x)^2 + 100*(y-x^2)^2 (optimal: x=1, y=1)
    def objective_func(design: Dict[str, float]) -> float:
        x, y = design["x"], design["y"]
        return (1 - x) ** 2 + 100 * (y - x ** 2) ** 2
    
    optimizer.set_objective(objective_func)
    
    result = optimizer.optimize()
    
    # Rosenbrock is hard to optimize, just check improvement
    assert result.improvement_percent > 0
    assert len(result.convergence_history) > 0


# ============================================================================
# Test Beam Optimizer (HK Code 2013)
# ============================================================================

def test_create_beam_optimizer():
    """Test beam optimizer factory function."""
    optimizer = create_beam_optimizer(
        initial_depth=600.0,
        initial_width=300.0,
        span=9000.0,
        max_stress=15.0,  # MPa
        max_deflection=36.0  # mm (span/250)
    )
    
    assert len(optimizer.design_vars) == 2
    assert len(optimizer.constraints) == 2
    assert optimizer.objective_func is not None


def test_beam_optimization():
    """Test beam section optimization with HK Code constraints."""
    optimizer = create_beam_optimizer(
        initial_depth=800.0,  # Over-designed initial
        initial_width=400.0,
        span=9000.0,
        max_stress=15.0,
        max_deflection=36.0
    )
    
    result = optimizer.optimize()
    
    # Should reduce section size while satisfying constraints
    assert result.optimal_design["depth"] <= 800.0
    assert result.optimal_design["width"] <= 400.0
    assert result.optimal_design["depth"] >= 300.0  # Reasonable minimum
    assert result.optimal_design["width"] >= 200.0


# ============================================================================
# Test AI Suggestions
# ============================================================================

def test_ai_optimization_suggestions():
    """Test AI optimization suggestions placeholder."""
    result = OptimizationResult(
        status=OptimizationStatus.CONVERGED,
        optimal_design={"depth": 550.0, "width": 300.0},
        objective_value=0.15,
        iterations=25,
        constraint_violations=[],
        convergence_history=[0.20, 0.18, 0.16, 0.15],
        improvement_percent=25.0
    )
    
    suggestions = get_ai_optimization_suggestions(result)
    
    assert "Optimization Summary" in suggestions
    assert "25.0%" in suggestions
    assert "depth: 550" in suggestions
    assert "width: 300" in suggestions


# ============================================================================
# Test OptimizationResult
# ============================================================================

def test_optimization_result_creation():
    """Test optimization result dataclass."""
    result = OptimizationResult(
        status=OptimizationStatus.CONVERGED,
        optimal_design={"x": 3.5},
        objective_value=12.25,
        iterations=30,
        constraint_violations=[],
        convergence_history=[100.0, 50.0, 25.0, 12.25],
        improvement_percent=87.75,
        ai_suggestions="Test suggestions"
    )
    
    assert result.status == OptimizationStatus.CONVERGED
    assert result.optimal_design == {"x": 3.5}
    assert result.iterations == 30
    assert result.improvement_percent == 87.75


# ============================================================================
# Test OptimizationConfig
# ============================================================================

def test_optimization_config_defaults():
    """Test optimization configuration defaults."""
    config = OptimizationConfig()
    
    assert config.max_iterations == 100
    assert config.tolerance == 1e-4
    assert config.step_size_multiplier == 0.01
    assert config.learning_rate == 0.1
    assert config.use_ai_suggestions == True


def test_optimization_config_custom():
    """Test custom optimization configuration."""
    config = OptimizationConfig(
        max_iterations=200,
        tolerance=1e-6,
        learning_rate=0.05
    )
    
    assert config.max_iterations == 200
    assert config.tolerance == 1e-6
    assert config.learning_rate == 0.05
