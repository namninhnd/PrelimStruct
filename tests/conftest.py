import sys
import types
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.fem.opensees_capabilities import get_shell_dkgt_support


class PatchedOps:
    """OpenSeesPy monkeypatch stub for unit tests."""

    def __init__(self):
        self.reset()
        self.analyze_result = 0
        self.displacements: Dict[int, List[float]] = {}
        self._reaction_data: Dict[int, List[float]] = {}
        self.element_forces: Dict[int, List[float]] = {}
        self.element_responses: Dict[Tuple[int, str], Any] = {}
        self.eigenvalues: List[float] = []
        self.reactions_called = False
        self.strict_reaction_mode = False

    def reset(self) -> None:
        self.nodes: Dict[int, Tuple[float, ...]] = {}
        self.fixes: Dict[int, Tuple[int, ...]] = {}
        self.materials: Dict[int, Tuple[str, Tuple[Any, ...]]] = {}
        self.sections: Dict[int, Tuple[str, Tuple[Any, ...]]] = {}
        self.geom_transforms: Dict[int, Tuple[str, Tuple[Any, ...]]] = {}
        self.elements: Dict[int, Tuple[str, Tuple[Any, ...]]] = {}
        self.rigid_diaphragms: List[Tuple[Any, ...]] = []
        self.time_series: List[Tuple[str, int]] = []
        self.patterns: List[Tuple[str, int, int]] = []
        self.loads: List[Tuple[int, Tuple[float, ...]]] = []
        self.uniform_loads: List[Tuple[int, Tuple[Any, ...]]] = []
        self.constraint_args: List[Tuple[Any, ...]] = []
        self.numberer_args: List[Tuple[Any, ...]] = []
        self.system_args: List[Tuple[Any, ...]] = []
        self.test_args: List[Tuple[Any, ...]] = []
        self.algorithm_args: List[Tuple[Any, ...]] = []
        self.integrator_args: List[Tuple[Any, ...]] = []
        self.analysis_args: List[Tuple[Any, ...]] = []
        self.wiped = False
        self.reactions_called = False

    # Model level commands
    def wipe(self) -> None:
        self.wiped = True

    def model(self, *args: Any) -> None:
        self.analysis_args.append(("model", args))

    # Geometry
    def node(self, tag: int, *coords: float) -> None:
        self.nodes[tag] = tuple(coords)

    def nodeCoord(self, tag: int) -> Tuple[float, ...]:
        return self.nodes[tag]

    def fix(self, tag: int, *restraints: int) -> None:
        self.fixes[tag] = tuple(restraints)

    # Materials and sections
    def uniaxialMaterial(self, material_type: str, tag: int, *params: Any) -> None:
        self.materials[tag] = (material_type, params)

    def nDMaterial(self, material_type: str, tag: int, *params: Any) -> None:
        self.materials[tag] = (material_type, params)

    def section(self, section_type: str, tag: int, *params: Any) -> None:
        self.sections[tag] = (section_type, params)

    # Transformations and elements
    def geomTransf(self, transf_type: str, tag: int, *params: Any) -> None:
        self.geom_transforms[tag] = (transf_type, params)

    def element(self, elem_type: str, tag: int, *params: Any) -> None:
        self.elements[tag] = (elem_type, params)

    def rigidDiaphragm(self, perp_dirn: int, master: int, *slaves: Any) -> None:
        self.rigid_diaphragms.append((perp_dirn, master, *slaves))

    # Loading
    def timeSeries(self, ts_type: str, tag: int) -> None:
        self.time_series.append((ts_type, tag))

    def pattern(self, pattern_type: str, pattern_tag: int, ts_tag: int) -> None:
        self.patterns.append((pattern_type, pattern_tag, ts_tag))

    def load(self, node_tag: int, *load_values: float) -> None:
        self.loads.append((node_tag, tuple(load_values)))

    def eleLoad(self, *args: Any) -> None:
        # args e.g. ('-ele', tag, '-type', 'beamUniform', wy, wz)
        self.uniform_loads.append(args)

    # Analysis setup
    def constraints(self, *args: Any) -> None:
        self.constraint_args.append(args)

    def numberer(self, *args: Any) -> None:
        self.numberer_args.append(args)

    def system(self, *args: Any) -> None:
        self.system_args.append(args)

    def test(self, *args: Any) -> None:
        self.test_args.append(args)

    def algorithm(self, *args: Any) -> None:
        self.algorithm_args.append(args)

    def integrator(self, *args: Any) -> None:
        self.integrator_args.append(args)

    def analysis(self, *args: Any) -> None:
        self.analysis_args.append(args)

    def analyze(self, *args: Any) -> int:
        self.analysis_args.append(("analyze", args))
        return self.analyze_result

    def reactions(self) -> None:
        self.reactions_called = True

    def getNodeTags(self) -> List[int]:
        return sorted(self.nodes.keys())

    def getFixedNodes(self) -> List[int]:
        return sorted([tag for tag, restraints in self.fixes.items()
                       if all(r == 1 for r in restraints)])

    def nodeDisp(self, node_tag: int) -> List[float]:
        return self.displacements.get(node_tag, [0.0] * 6)

    def nodeReaction(self, node_tag: int) -> List[float]:
        if self.strict_reaction_mode and not self.reactions_called:
            return [0.0] * 6
        return self._reaction_data.get(node_tag, [0.0] * 6)

    def getEleTags(self) -> List[int]:
        return sorted(self.elements.keys())

    def eleNodes(self, elem_tag: int) -> List[int]:
        _, params = self.elements[elem_tag]
        return [int(params[0]), int(params[1])]

    def eleForce(self, elem_tag: int) -> List[float]:
        return self.element_forces.get(elem_tag, [0.0] * 12)

    def eleResponse(self, elem_tag: int, query: str):
        return self.element_responses.get((elem_tag, query))

    def eigen(self, n_modes: int) -> List[float]:
        return self.eigenvalues[:n_modes]


@pytest.fixture
def ops_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> PatchedOps:
    ops = PatchedOps()
    opensees_module = types.ModuleType("opensees")
    setattr(opensees_module, "opensees", ops)
    monkeypatch.setitem(sys.modules, "openseespy", opensees_module)
    monkeypatch.setitem(sys.modules, "openseespy.opensees", ops)
    return ops


# Only load playwright plugin if installed
try:
    import pytest_playwright
    pytest_plugins = ["pytest_playwright"]
except ImportError:
    pass


@pytest.fixture
def require_shell_dkgt() -> str:
    supported, detail = get_shell_dkgt_support()
    if not supported:
        pytest.skip(f"ShellDKGT unavailable: {detail}")
    return detail
