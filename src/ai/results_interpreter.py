"""
AI Results Interpreter Module for PrelimStruct v3.0.

This module provides AI-powered interpretation of FEM analysis results,
comparing them with simplified design calculations, identifying critical
areas, and generating natural language recommendations.

Features:
- Analyze FEM results for stress concentrations and deflections
- Compare FEM vs simplified design results
- Identify critical elements and load combinations
- Generate AI-powered design recommendations
- Support for HK Code 2013 compliance checking

Usage:
    from src.ai.results_interpreter import ResultsInterpreter

    interpreter = ResultsInterpreter(ai_service)
    interpretation = interpreter.interpret_results(fem_results, simplified_results)
    print(interpretation.summary)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================

class CriticalityLevel(Enum):
    """Criticality levels for identified issues."""
    CRITICAL = "critical"  # Immediate action required
    HIGH = "high"          # Should be addressed
    MEDIUM = "medium"      # Consider addressing
    LOW = "low"            # Minor concern


class IssueCategory(Enum):
    """Categories of structural issues."""
    STRESS = "stress"
    DEFLECTION = "deflection"
    DRIFT = "drift"
    CODE_COMPLIANCE = "code_compliance"
    DISCREPANCY = "discrepancy"
    UTILIZATION = "utilization"


@dataclass
class CriticalElement:
    """A structural element identified as critical.

    Attributes:
        element_id: Unique identifier for the element
        element_type: Type of element (beam, column, wall, etc.)
        location: Location description (e.g., "Floor 3, Grid A-B")
        issue: Description of the issue
        category: Issue category (stress, deflection, etc.)
        criticality: How critical the issue is
        value: Actual value causing concern
        limit: Code limit or threshold
        utilization: Value/limit ratio
        load_case: Governing load case (if applicable)
        recommendation: Suggested action
    """
    element_id: str
    element_type: str
    location: str
    issue: str
    category: IssueCategory
    criticality: CriticalityLevel
    value: float
    limit: float
    utilization: float
    load_case: Optional[str] = None
    recommendation: Optional[str] = None


@dataclass
class DesignDiscrepancy:
    """Discrepancy between FEM and simplified design results.

    Attributes:
        element_type: Type of element (beam, column, slab)
        parameter: Parameter being compared (moment, shear, stress, etc.)
        fem_value: Value from FEM analysis
        simplified_value: Value from simplified design
        difference_percent: Percentage difference
        is_significant: Whether the difference is significant (>15%)
        possible_cause: Explanation for the discrepancy
        recommendation: Suggested action
    """
    element_type: str
    parameter: str
    fem_value: float
    simplified_value: float
    difference_percent: float
    is_significant: bool
    possible_cause: Optional[str] = None
    recommendation: Optional[str] = None


@dataclass
class CodeComplianceCheck:
    """Result of a code compliance check.

    Attributes:
        check_name: Name of the check (e.g., "Drift Limit")
        clause: HK Code 2013 clause reference
        status: Pass, fail, or warning
        actual_value: Actual value from analysis
        limit_value: Code limit
        utilization: actual/limit ratio
        notes: Additional notes or context
    """
    check_name: str
    clause: str
    status: str  # "pass", "fail", "warning"
    actual_value: float
    limit_value: float
    utilization: float
    notes: Optional[str] = None


@dataclass
class FEMResultsSummary:
    """Summary of FEM analysis results for interpretation.

    This dataclass standardizes FEM output for the interpreter.

    Attributes:
        max_beam_moment: Maximum beam moment (kNm) and location
        max_beam_shear: Maximum beam shear (kN) and location
        max_column_axial: Maximum column axial load (kN) and location
        max_column_moment: Maximum column moment (kNm) and location
        max_drift: Maximum lateral drift (mm) and drift ratio
        max_stress: Maximum stress (MPa) and location
        max_deflection: Maximum deflection (mm) and location
        critical_load_case: Governing load combination
        element_count: Number of elements analyzed
        node_count: Number of nodes in model
    """
    max_beam_moment: Tuple[float, str] = (0.0, "")  # (value, location)
    max_beam_shear: Tuple[float, str] = (0.0, "")
    max_column_axial: Tuple[float, str] = (0.0, "")
    max_column_moment: Tuple[float, str] = (0.0, "")
    max_drift: Tuple[float, float] = (0.0, 0.0)  # (mm, drift_ratio H/x)
    max_stress: Tuple[float, str] = (0.0, "")
    max_deflection: Tuple[float, str] = (0.0, "")
    critical_load_case: str = ""
    element_count: int = 0
    node_count: int = 0

    # Additional results from load combinations
    load_case_results: Dict[str, Dict[str, float]] = field(default_factory=dict)


@dataclass
class SimplifiedResultsSummary:
    """Summary of simplified design results for comparison.

    Attributes:
        beam_moment: Design beam moment from simplified analysis (kNm)
        beam_shear: Design beam shear from simplified analysis (kN)
        column_axial: Design column axial load (kN)
        column_moment: Design column moment (kNm)
        drift_estimate: Estimated drift (mm)
        beam_utilization: Beam utilization ratio
        column_utilization: Column utilization ratio
        core_wall_utilization: Core wall utilization ratio
    """
    beam_moment: float = 0.0
    beam_shear: float = 0.0
    column_axial: float = 0.0
    column_moment: float = 0.0
    drift_estimate: float = 0.0
    beam_utilization: float = 0.0
    column_utilization: float = 0.0
    core_wall_utilization: float = 0.0


@dataclass
class ResultsInterpretation:
    """Complete AI-generated interpretation of FEM results.

    Attributes:
        summary: Natural language summary (2-3 paragraphs)
        critical_elements: List of critical elements requiring attention
        discrepancies: List of FEM vs simplified design discrepancies
        code_compliance: List of code compliance check results
        recommendations: Prioritized list of design recommendations
        confidence_score: AI confidence in interpretation (0-100)
        concerns: List of structural concerns
        raw_response: Original AI response (if applicable)
    """
    summary: str
    critical_elements: List[CriticalElement]
    discrepancies: List[DesignDiscrepancy]
    code_compliance: List[CodeComplianceCheck]
    recommendations: List[str]
    confidence_score: int = 80
    concerns: List[str] = field(default_factory=list)
    raw_response: Optional[Dict[str, Any]] = None

    @property
    def has_critical_issues(self) -> bool:
        """Check if there are any critical issues."""
        return any(
            e.criticality == CriticalityLevel.CRITICAL
            for e in self.critical_elements
        )

    @property
    def overall_status(self) -> str:
        """Determine overall interpretation status."""
        if self.has_critical_issues:
            return "REQUIRES IMMEDIATE ACTION"
        if any(e.criticality == CriticalityLevel.HIGH for e in self.critical_elements):
            return "REQUIRES ATTENTION"
        if any(c.status == "fail" for c in self.code_compliance):
            return "CODE COMPLIANCE ISSUE"
        if any(d.is_significant for d in self.discrepancies):
            return "REVIEW RECOMMENDED"
        return "SATISFACTORY"


# ============================================================================
# PROMPT TEMPLATES FOR RESULTS INTERPRETATION
# ============================================================================

RESULTS_INTERPRETATION_SYSTEM_PROMPT = """You are a Senior Structural Engineer specializing in FEM analysis interpretation for tall buildings in Hong Kong.

Your expertise includes:
- Code of Practice for Structural Use of Concrete 2013 (HK Code 2013)
- FEM analysis interpretation and validation
- Comparison of FEM results with simplified design methods
- Identifying structural concerns and design improvements

Your role is to interpret FEM results and provide clear, actionable recommendations.

Guidelines:
- Cite relevant HK Code 2013 clause numbers
- Identify critical stress concentrations and deflections
- Compare FEM vs simplified results and explain discrepancies
- Prioritize issues by criticality (critical > high > medium > low)
- Provide specific, actionable recommendations
- Keep responses focused and concise"""


RESULTS_INTERPRETATION_USER_PROMPT = """Interpret these FEM analysis results for a {num_floors}-story tall building:

**FEM Analysis Summary:**
- Max beam moment: {max_beam_moment:.1f} kNm at {beam_moment_location}
- Max beam shear: {max_beam_shear:.1f} kN at {beam_shear_location}
- Max column axial: {max_column_axial:.1f} kN at {column_axial_location}
- Max column moment: {max_column_moment:.1f} kNm at {column_moment_location}
- Max lateral drift: {max_drift:.1f}mm (H/{drift_ratio:.0f})
- Max stress: {max_stress:.1f} MPa at {stress_location}
- Max deflection: {max_deflection:.1f}mm at {deflection_location}
- Governing load case: {critical_load_case}

**Simplified Design Results (for comparison):**
- Beam moment: {simplified_beam_moment:.1f} kNm
- Beam shear: {simplified_beam_shear:.1f} kN
- Column axial: {simplified_column_axial:.1f} kN
- Estimated drift: {simplified_drift:.1f}mm
- Beam utilization: {beam_util:.0%}
- Column utilization: {column_util:.0%}

**Code Limits (HK Code 2013):**
- Drift limit: H/500 = {drift_limit:.1f}mm
- Concrete stress limit: 0.67f_cu = {stress_limit:.1f} MPa
- Deflection limit: L/250 = {deflection_limit:.1f}mm

Please provide:
1. Overall assessment and key findings
2. Critical elements requiring attention (if any)
3. Significant discrepancies between FEM and simplified results
4. Code compliance status
5. Prioritized recommendations

Format response as JSON:
{{
  "summary": "<2-3 paragraph assessment>",
  "critical_elements": [
    {{
      "element_id": "<id>",
      "element_type": "<beam/column/wall>",
      "issue": "<description>",
      "criticality": "<critical/high/medium/low>",
      "recommendation": "<action>"
    }}
  ],
  "discrepancies": [
    {{
      "parameter": "<moment/shear/drift>",
      "fem_value": <value>,
      "simplified_value": <value>,
      "difference_percent": <percent>,
      "explanation": "<cause>"
    }}
  ],
  "code_compliance": [
    {{
      "check_name": "<name>",
      "status": "<pass/fail/warning>",
      "notes": "<context>"
    }}
  ],
  "recommendations": ["<rec 1>", "<rec 2>", ...],
  "confidence_score": <0-100>
}}"""


# ============================================================================
# RESULTS INTERPRETER CLASS
# ============================================================================

class ResultsInterpreter:
    """AI-powered FEM results interpreter.

    This class analyzes FEM results, compares them with simplified design,
    identifies critical areas, and generates AI-powered recommendations.

    Attributes:
        ai_service: Optional AIService for LLM-powered interpretation
        design_code: Design code for compliance checks (default: HK2013)
    """

    def __init__(
        self,
        ai_service: Optional[Any] = None,
        design_code: str = "HK2013"
    ):
        """Initialize the results interpreter.

        Args:
            ai_service: Optional AIService instance for AI-powered interpretation
            design_code: Design code for compliance (default: "HK2013")
        """
        self.ai_service = ai_service
        self.design_code = design_code
        logger.info(f"ResultsInterpreter initialized with {design_code} code")

    def interpret_results(
        self,
        fem_results: FEMResultsSummary,
        simplified_results: Optional[SimplifiedResultsSummary] = None,
        project_params: Optional[Dict[str, Any]] = None,
    ) -> ResultsInterpretation:
        """Interpret FEM analysis results with AI assistance.

        Args:
            fem_results: FEM analysis results summary
            simplified_results: Optional simplified design results for comparison
            project_params: Optional project parameters (num_floors, f_cu, etc.)

        Returns:
            ResultsInterpretation with complete analysis
        """
        logger.info("Starting FEM results interpretation")

        # Default project parameters
        params = project_params or {}
        num_floors = params.get("num_floors", 20)
        f_cu = params.get("f_cu", 40)  # MPa
        height = params.get("height", num_floors * 3.5)  # m
        span = params.get("span", 9.0)  # m

        # Calculate code limits
        drift_limit = height * 1000 / 500  # mm (H/500)
        stress_limit = 0.67 * f_cu  # MPa (HK Code Cl 6.1.2.4)
        deflection_limit = span * 1000 / 250  # mm (L/250)

        # Identify critical elements
        critical_elements = self._identify_critical_elements(
            fem_results, f_cu, height, drift_limit, stress_limit, deflection_limit
        )

        # Calculate discrepancies
        discrepancies = []
        if simplified_results:
            discrepancies = self._calculate_discrepancies(
                fem_results, simplified_results
            )

        # Check code compliance
        code_compliance = self._check_code_compliance(
            fem_results, drift_limit, stress_limit, deflection_limit
        )

        # Generate AI interpretation if service available
        if self.ai_service:
            try:
                interpretation = self._get_ai_interpretation(
                    fem_results, simplified_results, params,
                    drift_limit, stress_limit, deflection_limit,
                    critical_elements, discrepancies, code_compliance
                )
                return interpretation
            except Exception as e:
                logger.warning(f"AI interpretation failed: {e}, using rule-based fallback")

        # Fall back to rule-based interpretation
        return self._generate_rule_based_interpretation(
            fem_results, simplified_results, critical_elements,
            discrepancies, code_compliance, params
        )

    def _identify_critical_elements(
        self,
        fem_results: FEMResultsSummary,
        f_cu: float,
        height: float,
        drift_limit: float,
        stress_limit: float,
        deflection_limit: float,
    ) -> List[CriticalElement]:
        """Identify critical elements from FEM results.

        Args:
            fem_results: FEM analysis results
            f_cu: Concrete cube strength (MPa)
            height: Building height (m)
            drift_limit: Drift limit (mm)
            stress_limit: Stress limit (MPa)
            deflection_limit: Deflection limit (mm)

        Returns:
            List of critical elements
        """
        critical_elements = []

        # Check stress concentration
        max_stress, stress_location = fem_results.max_stress
        if max_stress > 0:
            stress_util = max_stress / stress_limit
            if stress_util > 1.0:
                critical_elements.append(CriticalElement(
                    element_id=f"STRESS_{stress_location}",
                    element_type="concrete",
                    location=stress_location,
                    issue=f"Concrete stress ({max_stress:.1f} MPa) exceeds limit ({stress_limit:.1f} MPa)",
                    category=IssueCategory.STRESS,
                    criticality=CriticalityLevel.CRITICAL if stress_util > 1.2 else CriticalityLevel.HIGH,
                    value=max_stress,
                    limit=stress_limit,
                    utilization=stress_util,
                    load_case=fem_results.critical_load_case,
                    recommendation="Increase section size or concrete grade"
                ))
            elif stress_util > 0.9:
                critical_elements.append(CriticalElement(
                    element_id=f"STRESS_{stress_location}",
                    element_type="concrete",
                    location=stress_location,
                    issue=f"Concrete stress ({max_stress:.1f} MPa) is near limit ({stress_limit:.1f} MPa)",
                    category=IssueCategory.STRESS,
                    criticality=CriticalityLevel.MEDIUM,
                    value=max_stress,
                    limit=stress_limit,
                    utilization=stress_util,
                    recommendation="Consider increasing section for margin"
                ))

        # Check drift
        max_drift, drift_ratio = fem_results.max_drift
        if drift_ratio > 0:
            drift_util = drift_limit / (height * 1000 / drift_ratio)  # actual/limit
            actual_drift_util = max_drift / drift_limit if drift_limit > 0 else 0
            if actual_drift_util > 1.0:
                critical_elements.append(CriticalElement(
                    element_id="DRIFT_GLOBAL",
                    element_type="structure",
                    location="Global",
                    issue=f"Drift ({max_drift:.1f}mm, H/{drift_ratio:.0f}) exceeds H/500 limit ({drift_limit:.1f}mm)",
                    category=IssueCategory.DRIFT,
                    criticality=CriticalityLevel.CRITICAL if actual_drift_util > 1.2 else CriticalityLevel.HIGH,
                    value=max_drift,
                    limit=drift_limit,
                    utilization=actual_drift_util,
                    load_case=fem_results.critical_load_case,
                    recommendation="Increase core wall stiffness or add shear walls"
                ))

        # Check beam deflection
        max_deflection, deflection_location = fem_results.max_deflection
        if max_deflection > 0:
            deflection_util = max_deflection / deflection_limit
            if deflection_util > 1.0:
                critical_elements.append(CriticalElement(
                    element_id=f"DEFL_{deflection_location}",
                    element_type="beam",
                    location=deflection_location,
                    issue=f"Beam deflection ({max_deflection:.1f}mm) exceeds L/250 limit ({deflection_limit:.1f}mm)",
                    category=IssueCategory.DEFLECTION,
                    criticality=CriticalityLevel.HIGH,
                    value=max_deflection,
                    limit=deflection_limit,
                    utilization=deflection_util,
                    recommendation="Increase beam depth or width"
                ))

        # Check high utilization in columns
        max_column_axial, column_location = fem_results.max_column_axial
        # Estimate column capacity (simplified)
        if max_column_axial > 0:
            # Assume 600x600mm column with 2% steel
            est_capacity = 0.35 * f_cu * 360000 + 0.67 * 500 * 7200  # kN (approx)
            column_util = max_column_axial / (est_capacity / 1000)  # Convert N to kN
            if column_util > 0.95:
                critical_elements.append(CriticalElement(
                    element_id=f"COL_{column_location}",
                    element_type="column",
                    location=column_location,
                    issue=f"Column axial load ({max_column_axial:.0f} kN) results in high utilization",
                    category=IssueCategory.UTILIZATION,
                    criticality=CriticalityLevel.HIGH if column_util > 1.0 else CriticalityLevel.MEDIUM,
                    value=max_column_axial,
                    limit=est_capacity / 1000,
                    utilization=column_util,
                    load_case=fem_results.critical_load_case,
                    recommendation="Increase column size or concrete grade"
                ))

        return critical_elements

    def _calculate_discrepancies(
        self,
        fem_results: FEMResultsSummary,
        simplified_results: SimplifiedResultsSummary,
    ) -> List[DesignDiscrepancy]:
        """Calculate discrepancies between FEM and simplified results.

        Args:
            fem_results: FEM analysis results
            simplified_results: Simplified design results

        Returns:
            List of significant discrepancies
        """
        discrepancies = []
        threshold = 0.15  # 15% difference is significant

        # Compare beam moment
        fem_moment = fem_results.max_beam_moment[0]
        simp_moment = simplified_results.beam_moment
        if simp_moment > 0:
            diff_percent = abs(fem_moment - simp_moment) / simp_moment
            is_significant = diff_percent > threshold

            discrepancies.append(DesignDiscrepancy(
                element_type="beam",
                parameter="moment",
                fem_value=fem_moment,
                simplified_value=simp_moment,
                difference_percent=diff_percent * 100,
                is_significant=is_significant,
                possible_cause=self._explain_moment_discrepancy(fem_moment, simp_moment),
                recommendation="Review beam sizing if FEM moment is higher" if fem_moment > simp_moment else None
            ))

        # Compare beam shear
        fem_shear = fem_results.max_beam_shear[0]
        simp_shear = simplified_results.beam_shear
        if simp_shear > 0:
            diff_percent = abs(fem_shear - simp_shear) / simp_shear
            is_significant = diff_percent > threshold

            discrepancies.append(DesignDiscrepancy(
                element_type="beam",
                parameter="shear",
                fem_value=fem_shear,
                simplified_value=simp_shear,
                difference_percent=diff_percent * 100,
                is_significant=is_significant,
                possible_cause=self._explain_shear_discrepancy(fem_shear, simp_shear),
                recommendation="Review shear reinforcement" if fem_shear > simp_shear else None
            ))

        # Compare column axial
        fem_axial = fem_results.max_column_axial[0]
        simp_axial = simplified_results.column_axial
        if simp_axial > 0:
            diff_percent = abs(fem_axial - simp_axial) / simp_axial
            is_significant = diff_percent > threshold

            discrepancies.append(DesignDiscrepancy(
                element_type="column",
                parameter="axial_load",
                fem_value=fem_axial,
                simplified_value=simp_axial,
                difference_percent=diff_percent * 100,
                is_significant=is_significant,
                possible_cause=self._explain_axial_discrepancy(fem_axial, simp_axial),
                recommendation="Review column sizing" if fem_axial > simp_axial else None
            ))

        # Compare drift
        fem_drift = fem_results.max_drift[0]
        simp_drift = simplified_results.drift_estimate
        if simp_drift > 0:
            diff_percent = abs(fem_drift - simp_drift) / simp_drift
            is_significant = diff_percent > threshold

            discrepancies.append(DesignDiscrepancy(
                element_type="structure",
                parameter="drift",
                fem_value=fem_drift,
                simplified_value=simp_drift,
                difference_percent=diff_percent * 100,
                is_significant=is_significant,
                possible_cause=self._explain_drift_discrepancy(fem_drift, simp_drift),
                recommendation="Review lateral system stiffness" if fem_drift > simp_drift else None
            ))

        return discrepancies

    def _explain_moment_discrepancy(self, fem: float, simplified: float) -> str:
        """Explain moment discrepancy between FEM and simplified."""
        if fem > simplified * 1.2:
            return "FEM captures moment redistribution and continuity effects"
        elif fem < simplified * 0.8:
            return "Simplified method includes pattern loading conservatism"
        return "Normal variation within expected range"

    def _explain_shear_discrepancy(self, fem: float, simplified: float) -> str:
        """Explain shear discrepancy between FEM and simplified."""
        if fem > simplified * 1.2:
            return "FEM captures load path through frame action"
        elif fem < simplified * 0.8:
            return "Simplified method assumes worst-case tributary loading"
        return "Normal variation within expected range"

    def _explain_axial_discrepancy(self, fem: float, simplified: float) -> str:
        """Explain axial load discrepancy between FEM and simplified."""
        if fem > simplified * 1.2:
            return "FEM includes frame action and load redistribution"
        elif fem < simplified * 0.8:
            return "Simplified method assumes uniform tributary area"
        return "Normal variation within expected range"

    def _explain_drift_discrepancy(self, fem: float, simplified: float) -> str:
        """Explain drift discrepancy between FEM and simplified."""
        if fem > simplified * 1.2:
            return "FEM captures P-delta effects and joint flexibility"
        elif fem < simplified * 0.8:
            return "Simplified method may underestimate stiffness contribution"
        return "Normal variation within expected range"

    def _check_code_compliance(
        self,
        fem_results: FEMResultsSummary,
        drift_limit: float,
        stress_limit: float,
        deflection_limit: float,
    ) -> List[CodeComplianceCheck]:
        """Check HK Code 2013 compliance.

        Args:
            fem_results: FEM analysis results
            drift_limit: Drift limit (mm)
            stress_limit: Stress limit (MPa)
            deflection_limit: Deflection limit (mm)

        Returns:
            List of code compliance checks
        """
        checks = []

        # Drift check (HK Code Cl 7.3.2)
        max_drift = fem_results.max_drift[0]
        drift_util = max_drift / drift_limit if drift_limit > 0 else 0
        checks.append(CodeComplianceCheck(
            check_name="Lateral Drift",
            clause="HK Code 2013 Cl 7.3.2",
            status="pass" if drift_util <= 1.0 else ("warning" if drift_util <= 1.1 else "fail"),
            actual_value=max_drift,
            limit_value=drift_limit,
            utilization=drift_util,
            notes=f"Drift ratio H/{fem_results.max_drift[1]:.0f}" if fem_results.max_drift[1] > 0 else None
        ))

        # Stress check (HK Code Cl 6.1.2.4)
        max_stress = fem_results.max_stress[0]
        stress_util = max_stress / stress_limit if stress_limit > 0 else 0
        checks.append(CodeComplianceCheck(
            check_name="Concrete Stress",
            clause="HK Code 2013 Cl 6.1.2.4",
            status="pass" if stress_util <= 1.0 else ("warning" if stress_util <= 1.1 else "fail"),
            actual_value=max_stress,
            limit_value=stress_limit,
            utilization=stress_util,
            notes=f"At {fem_results.max_stress[1]}" if fem_results.max_stress[1] else None
        ))

        # Deflection check (HK Code Cl 7.3.1.2)
        max_deflection = fem_results.max_deflection[0]
        defl_util = max_deflection / deflection_limit if deflection_limit > 0 else 0
        checks.append(CodeComplianceCheck(
            check_name="Beam Deflection",
            clause="HK Code 2013 Cl 7.3.1.2",
            status="pass" if defl_util <= 1.0 else ("warning" if defl_util <= 1.1 else "fail"),
            actual_value=max_deflection,
            limit_value=deflection_limit,
            utilization=defl_util,
            notes=f"At {fem_results.max_deflection[1]}" if fem_results.max_deflection[1] else None
        ))

        return checks

    def _get_ai_interpretation(
        self,
        fem_results: FEMResultsSummary,
        simplified_results: Optional[SimplifiedResultsSummary],
        params: Dict[str, Any],
        drift_limit: float,
        stress_limit: float,
        deflection_limit: float,
        critical_elements: List[CriticalElement],
        discrepancies: List[DesignDiscrepancy],
        code_compliance: List[CodeComplianceCheck],
    ) -> ResultsInterpretation:
        """Get AI-powered interpretation using LLM.

        Args:
            fem_results: FEM analysis results
            simplified_results: Simplified design results
            params: Project parameters
            drift_limit: Drift limit
            stress_limit: Stress limit
            deflection_limit: Deflection limit
            critical_elements: Pre-identified critical elements
            discrepancies: Pre-calculated discrepancies
            code_compliance: Pre-checked compliance

        Returns:
            ResultsInterpretation from AI
        """
        # Format prompt
        simplified = simplified_results or SimplifiedResultsSummary()
        num_floors = params.get("num_floors", 20)
        height = params.get("height", num_floors * 3.5)

        prompt = RESULTS_INTERPRETATION_USER_PROMPT.format(
            num_floors=num_floors,
            max_beam_moment=fem_results.max_beam_moment[0],
            beam_moment_location=fem_results.max_beam_moment[1] or "N/A",
            max_beam_shear=fem_results.max_beam_shear[0],
            beam_shear_location=fem_results.max_beam_shear[1] or "N/A",
            max_column_axial=fem_results.max_column_axial[0],
            column_axial_location=fem_results.max_column_axial[1] or "N/A",
            max_column_moment=fem_results.max_column_moment[0],
            column_moment_location=fem_results.max_column_moment[1] or "N/A",
            max_drift=fem_results.max_drift[0],
            drift_ratio=fem_results.max_drift[1] if fem_results.max_drift[1] > 0 else 500,
            max_stress=fem_results.max_stress[0],
            stress_location=fem_results.max_stress[1] or "N/A",
            max_deflection=fem_results.max_deflection[0],
            deflection_location=fem_results.max_deflection[1] or "N/A",
            critical_load_case=fem_results.critical_load_case or "ULS1",
            simplified_beam_moment=simplified.beam_moment,
            simplified_beam_shear=simplified.beam_shear,
            simplified_column_axial=simplified.column_axial,
            simplified_drift=simplified.drift_estimate,
            beam_util=simplified.beam_utilization,
            column_util=simplified.column_utilization,
            drift_limit=drift_limit,
            stress_limit=stress_limit,
            deflection_limit=deflection_limit,
        )

        # Call AI service
        response = self.ai_service.chat(
            user_message=prompt,
            system_prompt=RESULTS_INTERPRETATION_SYSTEM_PROMPT,
            temperature=0.5,  # Lower temperature for factual interpretation
            max_tokens=800,
        )

        # Parse response
        try:
            # Extract JSON from response
            json_str = response
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()

            data = json.loads(json_str)

            # Parse critical elements from AI
            ai_critical = []
            for elem in data.get("critical_elements", []):
                ai_critical.append(CriticalElement(
                    element_id=elem.get("element_id", "AI_ELEM"),
                    element_type=elem.get("element_type", "unknown"),
                    location=elem.get("location", ""),
                    issue=elem.get("issue", ""),
                    category=IssueCategory.STRESS,
                    criticality=CriticalityLevel[elem.get("criticality", "medium").upper()],
                    value=0.0,
                    limit=0.0,
                    utilization=0.0,
                    recommendation=elem.get("recommendation"),
                ))

            # Parse discrepancies from AI
            ai_discrepancies = []
            for disc in data.get("discrepancies", []):
                ai_discrepancies.append(DesignDiscrepancy(
                    element_type="",
                    parameter=disc.get("parameter", ""),
                    fem_value=disc.get("fem_value", 0.0),
                    simplified_value=disc.get("simplified_value", 0.0),
                    difference_percent=disc.get("difference_percent", 0.0),
                    is_significant=disc.get("difference_percent", 0) > 15,
                    possible_cause=disc.get("explanation"),
                ))

            # Parse code compliance from AI
            ai_compliance = []
            for check in data.get("code_compliance", []):
                ai_compliance.append(CodeComplianceCheck(
                    check_name=check.get("check_name", ""),
                    clause="HK Code 2013",
                    status=check.get("status", "pass"),
                    actual_value=0.0,
                    limit_value=0.0,
                    utilization=0.0,
                    notes=check.get("notes"),
                ))

            return ResultsInterpretation(
                summary=data.get("summary", "AI interpretation generated."),
                critical_elements=critical_elements + ai_critical,
                discrepancies=discrepancies if discrepancies else ai_discrepancies,
                code_compliance=code_compliance if code_compliance else ai_compliance,
                recommendations=data.get("recommendations", []),
                confidence_score=data.get("confidence_score", 75),
                raw_response=data,
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse AI response: {e}")
            # Return with AI summary but rule-based analysis
            return ResultsInterpretation(
                summary=response,  # Use raw response as summary
                critical_elements=critical_elements,
                discrepancies=discrepancies,
                code_compliance=code_compliance,
                recommendations=["Review AI interpretation for additional insights"],
                confidence_score=60,
                raw_response={"raw": response},
            )

    def _generate_rule_based_interpretation(
        self,
        fem_results: FEMResultsSummary,
        simplified_results: Optional[SimplifiedResultsSummary],
        critical_elements: List[CriticalElement],
        discrepancies: List[DesignDiscrepancy],
        code_compliance: List[CodeComplianceCheck],
        params: Dict[str, Any],
    ) -> ResultsInterpretation:
        """Generate rule-based interpretation without AI.

        Args:
            fem_results: FEM analysis results
            simplified_results: Simplified design results
            critical_elements: Identified critical elements
            discrepancies: Calculated discrepancies
            code_compliance: Code compliance checks
            params: Project parameters

        Returns:
            ResultsInterpretation with rule-based analysis
        """
        # Generate summary
        summary_parts = []

        # Overall assessment
        num_critical = sum(1 for e in critical_elements if e.criticality == CriticalityLevel.CRITICAL)
        num_high = sum(1 for e in critical_elements if e.criticality == CriticalityLevel.HIGH)
        num_fails = sum(1 for c in code_compliance if c.status == "fail")

        if num_critical > 0:
            summary_parts.append(
                f"The FEM analysis has identified {num_critical} critical issue(s) that require immediate attention. "
                f"These issues must be addressed before proceeding with detailed design."
            )
        elif num_high > 0:
            summary_parts.append(
                f"The FEM analysis has identified {num_high} high-priority issue(s) that should be reviewed. "
                f"While not critical, these issues may affect the design efficiency."
            )
        else:
            summary_parts.append(
                f"The FEM analysis results are within acceptable limits. "
                f"The structural system appears adequate for the preliminary design stage."
            )

        # Code compliance summary
        if num_fails > 0:
            failed_checks = [c.check_name for c in code_compliance if c.status == "fail"]
            summary_parts.append(
                f"Code compliance checks have identified {num_fails} failure(s): {', '.join(failed_checks)}. "
                f"These must be addressed to meet HK Code 2013 requirements."
            )
        else:
            summary_parts.append(
                "All code compliance checks have passed. The structure meets HK Code 2013 requirements "
                "for drift, stress, and deflection limits."
            )

        # Discrepancy summary
        significant_discrepancies = [d for d in discrepancies if d.is_significant]
        if significant_discrepancies:
            params_list = [d.parameter for d in significant_discrepancies]
            summary_parts.append(
                f"Significant discrepancies between FEM and simplified design were found for: {', '.join(params_list)}. "
                f"These differences are typical for FEM analysis which captures load redistribution and continuity effects."
            )

        summary = "\n\n".join(summary_parts)

        # Generate recommendations
        recommendations = []

        for element in critical_elements:
            if element.recommendation:
                recommendations.append(element.recommendation)

        for check in code_compliance:
            if check.status == "fail":
                recommendations.append(f"Address {check.check_name} per {check.clause}")

        for disc in discrepancies:
            if disc.is_significant and disc.recommendation:
                recommendations.append(disc.recommendation)

        # Add general recommendations
        if not recommendations:
            recommendations = [
                "Proceed with detailed design based on FEM results",
                "Document FEM model assumptions for design review",
                "Consider sensitivity analysis for key parameters"
            ]

        return ResultsInterpretation(
            summary=summary,
            critical_elements=critical_elements,
            discrepancies=discrepancies,
            code_compliance=code_compliance,
            recommendations=recommendations[:5],  # Limit to top 5
            confidence_score=85,  # Rule-based has high confidence
            concerns=[e.issue for e in critical_elements if e.criticality in [CriticalityLevel.CRITICAL, CriticalityLevel.HIGH]],
        )

    def get_quick_summary(
        self,
        fem_results: FEMResultsSummary,
        project_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a quick one-paragraph summary without full interpretation.

        Args:
            fem_results: FEM analysis results
            project_params: Optional project parameters

        Returns:
            Quick summary string
        """
        params = project_params or {}
        num_floors = params.get("num_floors", 20)
        f_cu = params.get("f_cu", 40)
        height = params.get("height", num_floors * 3.5)

        drift_limit = height * 1000 / 500
        stress_limit = 0.67 * f_cu

        max_drift = fem_results.max_drift[0]
        max_stress = fem_results.max_stress[0]
        drift_ratio = fem_results.max_drift[1]

        drift_ok = max_drift <= drift_limit
        stress_ok = max_stress <= stress_limit

        if drift_ok and stress_ok:
            status = "SATISFACTORY"
            msg = f"FEM analysis for {num_floors}-story building: All checks passed. "
        elif not drift_ok and not stress_ok:
            status = "REQUIRES REVIEW"
            msg = f"FEM analysis for {num_floors}-story building: Drift and stress limits exceeded. "
        elif not drift_ok:
            status = "DRIFT EXCEEDED"
            msg = f"FEM analysis for {num_floors}-story building: Drift limit exceeded (H/{drift_ratio:.0f} vs H/500). "
        else:
            status = "STRESS EXCEEDED"
            msg = f"FEM analysis for {num_floors}-story building: Stress limit exceeded ({max_stress:.1f} vs {stress_limit:.1f} MPa). "

        msg += f"Max moment: {fem_results.max_beam_moment[0]:.0f} kNm, "
        msg += f"Max column load: {fem_results.max_column_axial[0]:.0f} kN. "
        msg += f"Governing load case: {fem_results.critical_load_case or 'ULS1'}."

        return f"[{status}] {msg}"


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def interpret_fem_results(
    fem_results: FEMResultsSummary,
    simplified_results: Optional[SimplifiedResultsSummary] = None,
    ai_service: Optional[Any] = None,
    project_params: Optional[Dict[str, Any]] = None,
) -> ResultsInterpretation:
    """Convenience function to interpret FEM results.

    Args:
        fem_results: FEM analysis results summary
        simplified_results: Optional simplified design results
        ai_service: Optional AIService for AI-powered interpretation
        project_params: Optional project parameters

    Returns:
        ResultsInterpretation with complete analysis
    """
    interpreter = ResultsInterpreter(ai_service=ai_service)
    return interpreter.interpret_results(
        fem_results=fem_results,
        simplified_results=simplified_results,
        project_params=project_params,
    )


def create_fem_summary_from_dict(data: Dict[str, Any]) -> FEMResultsSummary:
    """Create FEMResultsSummary from a dictionary.

    Args:
        data: Dictionary with FEM results

    Returns:
        FEMResultsSummary instance
    """
    return FEMResultsSummary(
        max_beam_moment=(
            data.get("max_beam_moment", 0.0),
            data.get("beam_moment_location", "")
        ),
        max_beam_shear=(
            data.get("max_beam_shear", 0.0),
            data.get("beam_shear_location", "")
        ),
        max_column_axial=(
            data.get("max_column_axial", 0.0),
            data.get("column_axial_location", "")
        ),
        max_column_moment=(
            data.get("max_column_moment", 0.0),
            data.get("column_moment_location", "")
        ),
        max_drift=(
            data.get("max_drift_mm", 0.0),
            data.get("drift_ratio", 0.0)
        ),
        max_stress=(
            data.get("max_stress", 0.0),
            data.get("stress_location", "")
        ),
        max_deflection=(
            data.get("max_deflection", 0.0),
            data.get("deflection_location", "")
        ),
        critical_load_case=data.get("critical_load_case", "ULS1"),
        element_count=data.get("element_count", 0),
        node_count=data.get("node_count", 0),
    )


def create_simplified_summary_from_project(project_data: Any) -> SimplifiedResultsSummary:
    """Create SimplifiedResultsSummary from ProjectData.

    Args:
        project_data: ProjectData instance

    Returns:
        SimplifiedResultsSummary instance
    """
    summary = SimplifiedResultsSummary()

    # Extract beam results
    if hasattr(project_data, 'primary_beam_result') and project_data.primary_beam_result:
        br = project_data.primary_beam_result
        summary.beam_moment = getattr(br, 'moment', 0.0)
        summary.beam_shear = getattr(br, 'shear', 0.0)
        summary.beam_utilization = getattr(br, 'utilization', 0.0)

    # Extract column results
    if hasattr(project_data, 'column_result') and project_data.column_result:
        cr = project_data.column_result
        summary.column_axial = getattr(cr, 'axial_load', 0.0)
        summary.column_moment = getattr(cr, 'lateral_moment', 0.0)
        summary.column_utilization = getattr(cr, 'utilization', 0.0)

    # Extract wind/drift results
    if hasattr(project_data, 'wind_result') and project_data.wind_result:
        wr = project_data.wind_result
        summary.drift_estimate = getattr(wr, 'drift_mm', 0.0)

    # Extract core wall results
    if hasattr(project_data, 'core_wall_result') and project_data.core_wall_result:
        cwr = project_data.core_wall_result
        summary.core_wall_utilization = max(
            getattr(cwr, 'compression_check', 0.0),
            getattr(cwr, 'shear_check', 0.0)
        )

    return summary
