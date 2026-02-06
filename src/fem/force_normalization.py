"""Shared force normalization utilities for consistent table/overlay display.

Sign convention for beam elements in local coordinates:
- Positive N = tension
- Positive M = sagging (tension on bottom)
- For Vy, Vz, My, Mz, T at j-end: negate raw value for display consistency
- For N: use sign-based normalization (same sign -> keep, opposite sign -> negate)
"""

from typing import Dict, Set

NEGATED_J_END_TYPES: Set[str] = {"Vy", "Vz", "My", "Mz", "T"}


def _normalize_axial_force(force_i: float, force_j: float) -> float:
    if abs(force_i + force_j) < abs(force_i - force_j):
        return -force_j
    return force_j


def normalize_end_force(force_i: float, force_j: float, force_type: str) -> float:
    if force_type in NEGATED_J_END_TYPES:
        return -force_j
    return _normalize_axial_force(force_i, force_j)


def get_normalized_forces(forces: Dict[str, float]) -> Dict[str, float]:
    n_i = forces.get("N_i", 0.0)
    n_j = forces.get("N_j", 0.0)
    
    vy_i = forces.get("Vy_i", forces.get("V_i", 0.0))
    vy_j = forces.get("Vy_j", forces.get("V_j", 0.0))
    
    vz_i = forces.get("Vz_i", 0.0)
    vz_j = forces.get("Vz_j", 0.0)
    
    my_i = forces.get("My_i", 0.0)
    my_j = forces.get("My_j", 0.0)
    
    mz_i = forces.get("Mz_i", forces.get("M_i", 0.0))
    mz_j = forces.get("Mz_j", forces.get("M_j", 0.0))
    
    t_i = forces.get("T_i", 0.0)
    t_j = forces.get("T_j", 0.0)
    
    return {
        "N": normalize_end_force(n_i, n_j, "N"),
        "Vy": normalize_end_force(vy_i, vy_j, "Vy"),
        "Vz": normalize_end_force(vz_i, vz_j, "Vz"),
        "My": normalize_end_force(my_i, my_j, "My"),
        "Mz": normalize_end_force(mz_i, mz_j, "Mz"),
        "T": normalize_end_force(t_i, t_j, "T"),
    }
