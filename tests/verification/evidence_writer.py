"""Evidence JSON writer for benchmark verification outputs.

This module provides utilities to write deterministic JSON evidence files
after benchmark runs for debugging and verification purposes.

Evidence files are written to: .sisyphus/evidence/benchmarks/
Naming convention: {model}_{load_case}[_mesh{N}].json
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional
import json

EVIDENCE_DIR = Path(".sisyphus/evidence/benchmarks")


@dataclass
class ReactionRecord:
    """Record for a single base node reaction."""
    node_tag: int
    x: float
    y: float
    Fz_kN: float


@dataclass
class InputSpec:
    """Input specification for a benchmark run."""
    model: str
    load_case: str
    bay_x: float
    bay_y: float
    slab_elements_per_bay: int


@dataclass
class GroupAverages:
    """Tributary group average reactions."""
    corner_avg_kN: float
    edge_avg_kN: float
    interior_avg_kN: float


@dataclass
class EvidenceRecord:
    """Complete evidence record for a benchmark run."""
    input_spec: InputSpec
    load_case: str
    expected_sum_Fz_kN: float
    actual_sum_Fz_kN: float
    relative_error_percent: float
    reactions: List[ReactionRecord]
    group_averages: Optional[GroupAverages] = None


def _make_serializable(obj):
    """Convert dataclass objects to serializable dicts."""
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _make_serializable(v) for k, v in asdict(obj).items()}
    elif isinstance(obj, list):
        return [_make_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    else:
        return obj


def write_evidence(
    model_name: str,
    load_case: str,
    record: EvidenceRecord,
    mesh_level: Optional[int] = None,
) -> Path:
    """Write evidence JSON for a benchmark run.
    
    Args:
        model_name: Model identifier (e.g., "1x1", "2x3")
        load_case: Load case identifier (e.g., "SDL", "LL", "DL")
        record: EvidenceRecord with all verification data
        mesh_level: Optional mesh refinement level (for refinement tests)
    
    Returns:
        Path to the written evidence file
    """
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    
    if mesh_level is not None:
        filename = f"{model_name}_{load_case}_mesh{mesh_level}.json"
    else:
        filename = f"{model_name}_{load_case}.json"
    
    filepath = EVIDENCE_DIR / filename
    
    data = _make_serializable(record)
    
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    
    return filepath


def read_evidence(filepath: Path) -> Dict:
    """Read evidence JSON from file.
    
    Args:
        filepath: Path to the evidence file
    
    Returns:
        Parsed JSON data as dict
    """
    with open(filepath, "r") as f:
        return json.load(f)
