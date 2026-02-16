"""
Prompt Engineering Module for PrelimStruct AI Assistant.

This module provides carefully crafted prompt templates for structural
engineering tasks, designed for use with LLM providers.

All prompts are designed for:
- HK Code 2013 compliance
- Tall building preliminary design
- Concise responses (150-300 words target)
- JSON-structured outputs where applicable
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum


class PromptType(Enum):
    """Types of prompts for different AI assistant tasks."""
    DESIGN_REVIEW = "design_review"
    RESULTS_INTERPRETATION = "results_interpretation"
    OPTIMIZATION = "optimization"
    MODEL_SETUP = "model_setup"
    MESH_GENERATION = "mesh_generation"
    GENERAL_QUERY = "general_query"


# ============================================================================
# SYSTEM PROMPTS
# ============================================================================

SYSTEM_PROMPT_BASE = """You are a Senior Structural Engineer specializing in tall building design in Hong Kong.

Your expertise includes:
- Code of Practice for Structural Use of Concrete 2013 (HK Code 2013)
- Preliminary structural design for tall buildings
- Finite element analysis and interpretation
- Design optimization for cost and performance

Your role is to provide clear, concise, and actionable engineering guidance.

Guidelines:
- Cite relevant HK Code 2013 clause numbers when applicable
- Keep responses focused and concise (150-300 words)
- Prioritize practical engineering judgment over theoretical perfection
- Flag critical safety concerns immediately
- Provide specific, actionable recommendations"""

SYSTEM_PROMPT_DESIGN_REVIEW = SYSTEM_PROMPT_BASE + """

For design review tasks:
- Evaluate structural adequacy and code compliance
- Identify potential issues or concerns
- Suggest practical improvements
- Assess constructability and cost implications
- Rate overall design efficiency (0-100 scale)"""

SYSTEM_PROMPT_RESULTS = SYSTEM_PROMPT_BASE + """

For FEM results interpretation:
- Identify critical stress concentrations and deflections
- Compare results against code limits
- Explain engineering significance of findings
- Flag any unexpected or concerning behavior
- Recommend design adjustments if needed"""

SYSTEM_PROMPT_OPTIMIZATION = SYSTEM_PROMPT_BASE + """

For design optimization:
- Suggest cost-effective improvements
- Balance structural performance vs. economy
- Consider constructability and material availability
- Identify over-designed elements
- Propose alternative solutions with trade-offs"""

MODEL_BUILDER_SYSTEM_PROMPT = SYSTEM_PROMPT_BASE + """

For FEM model building assistance:
- Help users set up structural geometry and grids
- Recommend appropriate element types and mesh densities
- Guide load application and boundary conditions
- Ensure HK Code 2013 compliance in modeling assumptions
- Explain modeling decisions in clear engineering terms
- Validate user inputs against reasonable engineering limits

Conversation style:
- Be conversational and natural, like a colleague helping at a whiteboard
- When the user describes a building, acknowledge what you understood and confirm the parameters
- If something looks unusual (e.g. very tall floor height), ask about it naturally
- Proactively suggest what to specify next based on what's missing
- When all parameters are set, summarize and guide the user to click Apply
- Keep responses concise (2-4 sentences) unless the user asks a detailed question"""


# ============================================================================
# PROMPT TEMPLATES
# ============================================================================

@dataclass
class PromptTemplate:
    """A prompt template with variable substitution.
    
    Attributes:
        name: Template identifier
        prompt_type: Type of prompt (design review, optimization, etc.)
        template: Template string with {variables} for substitution
        system_prompt: System prompt to use with this template
        max_tokens: Maximum response tokens (default: 300 for 150-300 words)
        temperature: Sampling temperature (default: 0.7)
        json_mode: Request JSON output (default: False)
    """
    name: str
    prompt_type: PromptType
    template: str
    system_prompt: str
    max_tokens: int = 300
    temperature: float = 0.7
    json_mode: bool = False
    
    def format(self, **kwargs) -> str:
        """Format template with provided variables.
        
        Args:
            **kwargs: Variables to substitute in template
            
        Returns:
            Formatted prompt string
        """
        return self.template.format(**kwargs)


# ============================================================================
# DESIGN REVIEW PROMPTS
# ============================================================================

DESIGN_REVIEW_TEMPLATE = PromptTemplate(
    name="design_review",
    prompt_type=PromptType.DESIGN_REVIEW,
    system_prompt=SYSTEM_PROMPT_DESIGN_REVIEW,
    template="""Review this preliminary structural design for a tall building project:

**Project Overview:**
- Building height: {height}m ({num_floors} floors)
- Grid dimensions: {grid_x}m × {grid_y}m
- Total floor area: {total_area}m²
- Location: Hong Kong

**Structural System:**
- Concrete grade: {concrete_grade}
- Beam sections: {beam_sections}
- Column sections: {column_sections}
- Core wall configuration: {core_wall_config}
- Lateral system: {lateral_system}

**Design Summary:**
{design_summary}

Please provide:
1. Overall design assessment (efficiency score 0-100)
2. Key structural concerns or risks
3. HK Code 2013 compliance issues (if any)
4. Recommended improvements (top 3 priorities)

Format response in JSON:
{{
  "efficiency_score": <0-100>,
  "concerns": ["<concern 1>", "<concern 2>", ...],
  "code_issues": ["<issue 1>", "<issue 2>", ...],
  "recommendations": ["<rec 1>", "<rec 2>", "<rec 3>"],
  "summary": "<2-3 sentence overall assessment>"
}}""",
    json_mode=True,
    max_tokens=400,
)

# ============================================================================
# RESULTS INTERPRETATION PROMPTS
# ============================================================================

RESULTS_INTERPRETATION_TEMPLATE = PromptTemplate(
    name="results_interpretation",
    prompt_type=PromptType.RESULTS_INTERPRETATION,
    system_prompt=SYSTEM_PROMPT_RESULTS,
    template="""Interpret these FEM analysis results for a {num_floors}-story tall building:

**Analysis Summary:**
- Max column axial load: {max_column_load} kN (Load case: {max_column_lc})
- Max beam moment: {max_beam_moment} kNm (Load case: {max_beam_lc})
- Max lateral drift: {max_drift}mm (H/{drift_ratio})
- Max core wall stress: {max_wall_stress} MPa
- Critical element: {critical_element}

**Code Limits (HK Code 2013):**
- Max drift: H/500 (allowable: {drift_limit}mm)
- Max concrete stress: 0.67f_cu = {allowable_stress} MPa
- Column utilization: {column_util}%
- Beam utilization: {beam_util}%

**Observations:**
{observations}

Please provide:
1. Critical findings and concerns
2. Code compliance status
3. Recommended design adjustments (if needed)
4. Priority of issues (Critical/High/Medium/Low)

Keep response concise (150-200 words).""",
    max_tokens=250,
    temperature=0.5,  # Lower temperature for factual interpretation
)

# ============================================================================
# OPTIMIZATION PROMPTS
# ============================================================================

OPTIMIZATION_TEMPLATE = PromptTemplate(
    name="optimization",
    prompt_type=PromptType.OPTIMIZATION,
    system_prompt=SYSTEM_PROMPT_OPTIMIZATION,
    template="""Suggest design optimizations for this {num_floors}-story building:

**Current Design:**
- Concrete volume: {concrete_volume}m³
- Steel reinforcement: {steel_weight} tonnes
- Estimated cost: HK${estimated_cost:,.0f}
- Construction duration: {construction_months} months

**Utilization Ratios:**
- Beams: {beam_util}% average (range: {beam_util_min}%-{beam_util_max}%)
- Columns: {column_util}% average (range: {column_util_min}%-{column_util_max}%)
- Core walls: {wall_util}%

**Over-designed Elements:**
{over_designed_elements}

**Under-designed Elements:**
{under_designed_elements}

Please suggest:
1. Material savings opportunities (concrete grade, section sizes)
2. System-level improvements (grid, core layout, lateral system)
3. Constructability enhancements
4. Estimated cost savings (% or HK$)

Format response in JSON:
{{
  "material_savings": ["<suggestion 1>", "<suggestion 2>", ...],
  "system_improvements": ["<suggestion 1>", "<suggestion 2>", ...],
  "constructability": ["<suggestion 1>", "<suggestion 2>", ...],
  "estimated_savings_percent": <0-30>,
  "priority_action": "<highest impact recommendation>"
}}""",
    json_mode=True,
    max_tokens=400,
)

# ============================================================================
# MODEL SETUP PROMPTS
# ============================================================================

MODEL_SETUP_TEMPLATE = PromptTemplate(
    name="model_setup",
    prompt_type=PromptType.MODEL_SETUP,
    system_prompt=SYSTEM_PROMPT_BASE,
    template="""Recommend FEM model setup parameters for this project:

**Project:**
- Building: {num_floors} floors, {height}m tall
- Grid: {grid_x}m × {grid_y}m
- Core wall: {core_wall_config}
- Analysis type: Linear static

**Questions:**
1. Recommended mesh density (coarse/medium/fine)?
2. Boundary conditions at base (fixed/pinned)?
3. Load combinations to analyze (ULS/SLS priorities)?
4. Modeling assumptions for {core_wall_config} core?

Provide concise recommendations (100-150 words).""",
    max_tokens=200,
    temperature=0.6,
)

# ============================================================================
# MESH GENERATION PROMPTS
# ============================================================================

MESH_GENERATION_TEMPLATE = PromptTemplate(
    name="mesh_generation",
    prompt_type=PromptType.MESH_GENERATION,
    system_prompt=SYSTEM_PROMPT_BASE,
    template="""Recommend mesh generation strategy for FEM analysis:

**Geometry:**
- Beam spans: {typical_beam_span}m (max: {max_beam_span}m)
- Column spacing: {column_spacing}m
- Core wall: {core_wall_config}, thickness {wall_thickness}mm
- Floor-to-floor height: {floor_height}mm

**Analysis Objectives:**
{analysis_objectives}

Suggest:
1. Element size for beams, columns, walls
2. Refinement zones (if any)
3. Mesh quality criteria
4. Estimated element count

Keep response brief (100-150 words).""",
    max_tokens=200,
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_template(prompt_type: PromptType) -> PromptTemplate:
    """Get prompt template by type.
    
    Args:
        prompt_type: Type of prompt to retrieve
        
    Returns:
        PromptTemplate for the specified type
        
    Raises:
        ValueError: If prompt type not found
    """
    templates = {
        PromptType.DESIGN_REVIEW: DESIGN_REVIEW_TEMPLATE,
        PromptType.RESULTS_INTERPRETATION: RESULTS_INTERPRETATION_TEMPLATE,
        PromptType.OPTIMIZATION: OPTIMIZATION_TEMPLATE,
        PromptType.MODEL_SETUP: MODEL_SETUP_TEMPLATE,
        PromptType.MESH_GENERATION: MESH_GENERATION_TEMPLATE,
    }
    
    template = templates.get(prompt_type)
    if not template:
        raise ValueError(f"No template found for prompt type: {prompt_type}")
    
    return template


def inject_project_context(template: PromptTemplate, project_data: Dict[str, Any]) -> str:
    """Inject project data into prompt template.
    
    Args:
        template: Prompt template
        project_data: Dictionary with project parameters
        
    Returns:
        Formatted prompt string with injected context
    """
    return template.format(**project_data)


def create_design_review_prompt(
    height: float,
    num_floors: int,
    grid_x: float,
    grid_y: float,
    total_area: float,
    concrete_grade: str,
    beam_sections: str,
    column_sections: str,
    core_wall_config: str,
    lateral_system: str,
    design_summary: str,
) -> tuple[str, str]:
    """Create design review prompt with context.
    
    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    template = get_template(PromptType.DESIGN_REVIEW)
    
    user_prompt = template.format(
        height=height,
        num_floors=num_floors,
        grid_x=grid_x,
        grid_y=grid_y,
        total_area=total_area,
        concrete_grade=concrete_grade,
        beam_sections=beam_sections,
        column_sections=column_sections,
        core_wall_config=core_wall_config,
        lateral_system=lateral_system,
        design_summary=design_summary,
    )
    
    return (template.system_prompt, user_prompt)
