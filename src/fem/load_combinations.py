"""
Load Combination System for FEM Analysis - HK Code 2013 Compliant

This module implements the comprehensive load combination system per HK Code 2013
Table 2.1 and Eurocode 8 for both ULS and SLS design checks.

Design Code References:
- HK Code of Practice for Structural Use of Concrete 2013 (Cl 2.3, Table 2.1)
- Eurocode 8 (EN 1998-1) for seismic load combinations (Cl 4.2.4)
- HK Code 2013 Cl 7.2-7.3 for serviceability combinations
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from src.core.data_models import LoadCombination


class LoadComponentType(Enum):
    """Types of load components in combinations."""
    DL = "DL"                        # Self-weight (Dead Load)
    SDL = "SDL"                      # Superimposed Dead Load
    LL = "LL"                        # Live Load

    # Canonical wind component cases (bridge: WX1->Wx, WX2->Wy, WTZ->Wtz)
    WX = "Wx"
    WY = "Wy"
    WTZ = "Wtz"
    
    # HK Code 2019 Wind Cases (3 dominance groups x 8 sign permutations)
    # Group 1: WX1 dominant
    W1 = "W1"
    W2 = "W2"
    W3 = "W3"
    W4 = "W4"
    W5 = "W5"
    W6 = "W6"
    W7 = "W7"
    W8 = "W8"

    # Group 2: WX2 dominant
    W9 = "W9"
    W10 = "W10"
    W11 = "W11"
    W12 = "W12"
    W13 = "W13"
    W14 = "W14"
    W15 = "W15"
    W16 = "W16"

    # Group 3: WTZ dominant
    W17 = "W17"
    W18 = "W18"
    W19 = "W19"
    W20 = "W20"
    W21 = "W21"
    W22 = "W22"
    W23 = "W23"
    W24 = "W24"

    # Eurocode 8 Seismic Cases
    E1 = "E1"   # X + 0.3Y
    E2 = "E2"   # 0.3X + Y
    E3 = "E3"   # Vertical Z

    ACCIDENTAL = "Ad"                # Notional horizontal loads


class LoadCombinationCategory(Enum):
    """Load combination categories for grouping."""
    ULS_GRAVITY = "uls_gravity"
    ULS_WIND = "uls_wind"
    ULS_SEISMIC = "uls_seismic"
    ULS_ACCIDENTAL = "uls_accidental"
    SLS = "sls"


@dataclass
class LoadFactor:
    """Load factor definition for a load component.
    
    Attributes:
        component: Type of load component (dead, live, wind, seismic, etc.)
        factor: Partial safety factor (γ_f) applied to the load
        description: Brief description for reporting
    """
    component: LoadComponentType
    factor: float
    description: str = ""
    
    def apply(self, load_value: float) -> float:
        """Apply factor to load value.
        
        Args:
            load_value: Unfactored load value
            
        Returns:
            Factored load value
        """
        return self.factor * load_value


@dataclass
class LoadCombinationDefinition:
    """Definition of a single load combination.
    
    Attributes:
        name: Load combination identifier (e.g., "LC1")
        combination_type: LoadCombination enum value
        category: Combination category for grouping
        load_factors: Dictionary mapping load components to their factors
        description: Full description with HK Code clause reference
        code_clause: HK Code or Eurocode clause reference
    """
    name: str
    combination_type: LoadCombination
    category: LoadCombinationCategory
    load_factors: Dict[LoadComponentType, float]
    description: str
    code_clause: str
    
    def get_factor(self, component: LoadComponentType) -> float:
        """Get load factor for a specific component.
        
        Args:
            component: Load component type
            
        Returns:
            Factor value (0.0 if component not in combination)
        """
        return self.load_factors.get(component, 0.0)
    
    def get_factored_load(self, loads: Dict[LoadComponentType, float]) -> float:
        """Calculate total factored load for this combination.
        
        Args:
            loads: Dictionary of unfactored load values
            
        Returns:
            Sum of factored loads
        """
        total = 0.0
        for component, factor in self.load_factors.items():
            load_value = loads.get(component, 0.0)
            total += factor * load_value
        return total
    
    def to_equation(self) -> str:
        """Generate load combination equation string for reporting.
        
        Returns:
            Equation string (e.g., "1.4Gk + 1.6Qk")
        """
        terms = []
        
        # Helper to format term
        def format_term(factor: float, symbol: str) -> str:
            if factor == 1.0:
                return f"{symbol}"
            elif factor == -1.0:
                return f"-{symbol}"
            elif factor > 0:
                return f"{factor:.2g}{symbol}"
            else:
                return f"{factor:.2g}{symbol}"

        # Order: DL, SDL, LL, Wind, Seismic, Accidental
        for comp in [LoadComponentType.DL, LoadComponentType.SDL, LoadComponentType.LL]:
            if comp in self.load_factors and self.load_factors[comp] != 0:
                terms.append(format_term(self.load_factors[comp], comp.value))

        # Canonical wind components
        for comp in [LoadComponentType.WX, LoadComponentType.WY, LoadComponentType.WTZ]:
            if comp in self.load_factors and self.load_factors[comp] != 0:
                terms.append(format_term(self.load_factors[comp], comp.value))

        # Wind
        for i in range(1, 25):
            w_comp = getattr(LoadComponentType, f"W{i}")
            if w_comp in self.load_factors and self.load_factors[w_comp] != 0:
                terms.append(format_term(self.load_factors[w_comp], w_comp.value))
        
        # Seismic
        for e_comp in [LoadComponentType.E1, LoadComponentType.E2, LoadComponentType.E3]:
             if e_comp in self.load_factors and self.load_factors[e_comp] != 0:
                terms.append(format_term(self.load_factors[e_comp], e_comp.value))

        # Accidental
        if LoadComponentType.ACCIDENTAL in self.load_factors and self.load_factors[LoadComponentType.ACCIDENTAL] != 0:
             terms.append(format_term(self.load_factors[LoadComponentType.ACCIDENTAL], LoadComponentType.ACCIDENTAL.value))
        
        return " + ".join(terms).replace(" + -", " - ")


class LoadCombinationLibrary:
    """Library of standard load combinations per HK Code 2013 and Eurocode 8."""
    
    @staticmethod
    def get_uls_gravity_combinations() -> List[LoadCombinationDefinition]:
        """Get ULS gravity-dominant combinations.
        
        HK Code 2013 Table 2.1, Case 1:
        - Maximum dead load case for design
        - Minimum dead load case for checking uplift/tension
        
        Returns:
            List of gravity load combination definitions
        """
        return [
            LoadCombinationDefinition(
                name="LC1",
                combination_type=LoadCombination.ULS_GRAVITY_1,
                category=LoadCombinationCategory.ULS_GRAVITY,
                load_factors={
                    LoadComponentType.DL: 1.4,
                    LoadComponentType.SDL: 1.4,
                    LoadComponentType.LL: 1.6,
                },
                description="ULS Gravity (max dead + live) - HK Code Table 2.1 Case 1",
                code_clause="HK Code 2013 Table 2.1, Case 1"
            ),
            LoadCombinationDefinition(
                name="LC2",
                combination_type=LoadCombination.ULS_GRAVITY_2,
                category=LoadCombinationCategory.ULS_GRAVITY,
                load_factors={
                    LoadComponentType.DL: 1.0,
                    LoadComponentType.SDL: 1.0,
                    LoadComponentType.LL: 1.6,
                },
                description="ULS Gravity (min dead + live) - Check uplift/tension",
                code_clause="HK Code 2013 Table 2.1, Case 1 (minimum dead)"
            ),
        ]
    
    @staticmethod
    def get_uls_wind_combinations() -> List[LoadCombinationDefinition]:
        """Get ULS wind load combinations.
        
        HK Code 2013 Table 2.1, Case 2:
        - 1.4Gk + 1.4Wk (Max Gravity)
        - 1.0Gk + 1.4Wk (Min Gravity - Uplift)
        
        Generates 48 combinations (24 Wind Cases x 2 Gravity variations).
        
        Returns:
            List of wind load combination definitions
        """
        combinations = []
        
        # Loop through all 24 wind cases
        for i in range(1, 25):
            w_comp = getattr(LoadComponentType, f"W{i}")
            
            # Case 2a: Max Gravity + Wind (1.4G + 1.4W)
            combinations.append(LoadCombinationDefinition(
                name=f"LC_W{i}_MAX",
                combination_type=LoadCombination.ULS_WIND_1,
                category=LoadCombinationCategory.ULS_WIND,
                load_factors={
                    LoadComponentType.DL: 1.4,
                    LoadComponentType.SDL: 1.4,
                    w_comp: 1.4,
                },
                description=f"ULS Wind (Max G) - {w_comp.value}",
                code_clause="HK Code 2013 Table 2.1, Case 2"
            ))
            
            # Case 2b: Min Gravity + Wind (1.0G + 1.4W)
            combinations.append(LoadCombinationDefinition(
                name=f"LC_W{i}_MIN",
                combination_type=LoadCombination.ULS_WIND_2,
                category=LoadCombinationCategory.ULS_WIND,
                load_factors={
                    LoadComponentType.DL: 1.0,
                    LoadComponentType.SDL: 1.0,
                    w_comp: 1.4,
                },
                description=f"ULS Wind (Min G) - {w_comp.value}",
                code_clause="HK Code 2013 Table 2.1, Case 2 (min dead)"
            ))
            
        return combinations

    @staticmethod
    def get_uls_seismic_combinations() -> List[LoadCombinationDefinition]:
        """Get ULS seismic load combinations per Eurocode 8.
        
        Eurocode 8 (EN 1998-1) Cl 4.2.4:
        - 1.0Gk + 0.3Qk + 1.0Ed
        - Reversal included (+/- Ed)
        
        Returns:
            List of seismic load combination definitions
        """
        combinations = []
        seismic_cases = [LoadComponentType.E1, LoadComponentType.E2, LoadComponentType.E3]
        
        for i, comp in enumerate(seismic_cases):
            # Positive Direction
            combinations.append(LoadCombinationDefinition(
                name=f"LC_SEISMIC_{comp.value}_POS",
                combination_type=getattr(LoadCombination, f"ULS_SEISMIC_{'XY'[i] if i<2 else 'Y'}_POS", LoadCombination.ULS_SEISMIC_X_POS), # Fallback mapping
                category=LoadCombinationCategory.ULS_SEISMIC,
                load_factors={
                    LoadComponentType.DL: 1.0,
                    LoadComponentType.SDL: 1.0,
                    LoadComponentType.LL: 0.3, # psi_2
                    comp: 1.0,
                },
                description=f"ULS Seismic (+{comp.value})",
                code_clause="Eurocode 8 EN 1998-1 Cl 4.2.4"
            ))
            
            # Negative Direction (Reversal)
            combinations.append(LoadCombinationDefinition(
                name=f"LC_SEISMIC_{comp.value}_NEG",
                combination_type=getattr(LoadCombination, f"ULS_SEISMIC_{'XY'[i] if i<2 else 'Y'}_NEG", LoadCombination.ULS_SEISMIC_X_NEG),
                category=LoadCombinationCategory.ULS_SEISMIC,
                load_factors={
                    LoadComponentType.DL: 1.0,
                    LoadComponentType.SDL: 1.0,
                    LoadComponentType.LL: 0.3,
                    comp: -1.0,
                },
                description=f"ULS Seismic (-{comp.value})",
                code_clause="Eurocode 8 EN 1998-1 Cl 4.2.4"
            ))
            
        return combinations
    
    @staticmethod
    def get_uls_accidental_combinations() -> List[LoadCombinationDefinition]:
        """Get ULS accidental load combinations.
        
        HK Code 2013 Table 2.1, Case 3:
        - 1.0Gk + 0.5Qk + 1.0Ad
        
        Returns:
            List of accidental load combination definitions
        """
        return [
            LoadCombinationDefinition(
                name="LC_ACC",
                combination_type=LoadCombination.ULS_ACCIDENTAL,
                category=LoadCombinationCategory.ULS_ACCIDENTAL,
                load_factors={
                    LoadComponentType.DL: 1.0,
                    LoadComponentType.SDL: 1.0,
                    LoadComponentType.LL: 0.5,
                    LoadComponentType.ACCIDENTAL: 1.0,
                },
                description="ULS Accidental - HK Code Table 2.1 Case 3",
                code_clause="HK Code 2013 Table 2.1, Case 3"
            ),
        ]
    
    @staticmethod
    def get_sls_combinations() -> List[LoadCombinationDefinition]:
        """Get SLS serviceability load combinations.
        
        Returns:
            List of SLS load combination definitions
        """
        return [
            LoadCombinationDefinition(
                name="SLS1",
                combination_type=LoadCombination.SLS_CHARACTERISTIC,
                category=LoadCombinationCategory.SLS,
                load_factors={
                    LoadComponentType.DL: 1.0,
                    LoadComponentType.SDL: 1.0,
                    LoadComponentType.LL: 1.0,
                },
                description="SLS Characteristic (deflection check) - HK Code Cl 7.3.2",
                code_clause="HK Code 2013 Cl 7.3.2"
            ),
            LoadCombinationDefinition(
                name="SLS2",
                combination_type=LoadCombination.SLS_FREQUENT,
                category=LoadCombinationCategory.SLS,
                load_factors={
                    LoadComponentType.DL: 1.0,
                    LoadComponentType.SDL: 1.0,
                    LoadComponentType.LL: 0.5,  # psi_1 factor
                },
                description="SLS Frequent (crack width check) - HK Code Cl 7.2.3",
                code_clause="HK Code 2013 Cl 7.2.3"
            ),
            LoadCombinationDefinition(
                name="SLS3",
                combination_type=LoadCombination.SLS_QUASI_PERMANENT,
                category=LoadCombinationCategory.SLS,
                load_factors={
                    LoadComponentType.DL: 1.0,
                    LoadComponentType.SDL: 1.0,
                    LoadComponentType.LL: 0.3,  # psi_2 factor
                },
                description="SLS Quasi-Permanent (long-term deflection) - HK Code Cl 7.3.3",
                code_clause="HK Code 2013 Cl 7.3.3"
            ),
        ]
    
    @staticmethod
    def get_all_combinations() -> List[LoadCombinationDefinition]:
        """Get all standard load combinations.
        
        Returns:
            Complete list of all ULS and SLS combinations
        """
        combinations = []
        combinations.extend(LoadCombinationLibrary.get_uls_gravity_combinations())
        combinations.extend(LoadCombinationLibrary.get_uls_wind_combinations())
        combinations.extend(LoadCombinationLibrary.get_uls_seismic_combinations())
        combinations.extend(LoadCombinationLibrary.get_uls_accidental_combinations())
        combinations.extend(LoadCombinationLibrary.get_sls_combinations())
        return combinations
    
    @staticmethod
    def get_combinations_by_category(
        category: LoadCombinationCategory
    ) -> List[LoadCombinationDefinition]:
        """Get combinations filtered by category.
        
        Args:
            category: Category to filter by
            
        Returns:
            List of combinations matching the category
        """
        all_combs = LoadCombinationLibrary.get_all_combinations()
        return [c for c in all_combs if c.category == category]


class PatternLoadingMode(Enum):
    """Pattern loading modes per HK Code 2013 Cl 2.3.2.1."""
    FULL = "full"                      # All spans loaded simultaneously
    CHECKERBOARD_MAX_POS = "checkerboard_max_pos"  # Alternate spans for +ve moment
    CHECKERBOARD_MAX_NEG = "checkerboard_max_neg"  # Alternate spans for -ve moment
    ADJACENT_MAX_SHEAR = "adjacent_max_shear"      # Adjacent spans for max shear
    USER_DEFINED = "user_defined"      # Custom pattern


@dataclass
class PatternLoadCase:
    """Pattern loading case definition.
    
    Attributes:
        mode: Pattern loading mode
        loaded_spans: List of span indices that are loaded (0-indexed)
        factor: Load factor applied to loaded spans (default 1.0)
        description: Description of pattern
    """
    mode: PatternLoadingMode
    loaded_spans: List[int]
    factor: float = 1.0
    description: str = ""
    
    def is_span_loaded(self, span_index: int) -> bool:
        """Check if a span is loaded in this pattern.
        
        Args:
            span_index: 0-indexed span number
            
        Returns:
            True if span is loaded
        """
        return span_index in self.loaded_spans


class PatternLoadingGenerator:
    """Generate pattern loading cases per HK Code 2013 Cl 2.3.2.1.
    
    For continuous beams and slabs, pattern loading considers:
    - Full loading: all spans loaded (conservative, always analyzed)
    - Checkerboard: alternate spans to maximize +ve/-ve moments
    - Adjacent loading: adjacent spans for maximum shear
    """
    
    @staticmethod
    def generate_patterns(n_spans: int, mode: str = "all") -> List[PatternLoadCase]:
        """Generate pattern loading cases for continuous member.
        
        HK Code 2013 Cl 2.3.2.1 requires pattern loading for continuous
        members to maximize design moments and shears.
        
        Args:
            n_spans: Number of continuous spans
            mode: "all", "checkerboard", "shear", or "full"
            
        Returns:
            List of pattern loading cases
        """
        patterns = []
        
        # Always include full loading case
        patterns.append(PatternLoadCase(
            mode=PatternLoadingMode.FULL,
            loaded_spans=list(range(n_spans)),
            factor=1.0,
            description="Full loading - all spans loaded"
        ))
        
        if mode in ("all", "checkerboard"):
            # Checkerboard pattern 1: odd spans loaded (maximize +ve moment at loaded spans)
            odd_spans = [i for i in range(n_spans) if i % 2 == 0]  # 0, 2, 4, ...
            patterns.append(PatternLoadCase(
                mode=PatternLoadingMode.CHECKERBOARD_MAX_POS,
                loaded_spans=odd_spans,
                factor=1.0,
                description=f"Checkerboard 1 - spans {odd_spans} loaded (max +ve moment)"
            ))
            
            # Checkerboard pattern 2: even spans loaded (maximize -ve moment at supports)
            even_spans = [i for i in range(n_spans) if i % 2 == 1]  # 1, 3, 5, ...
            if even_spans:  # Only if we have even spans
                patterns.append(PatternLoadCase(
                    mode=PatternLoadingMode.CHECKERBOARD_MAX_NEG,
                    loaded_spans=even_spans,
                    factor=1.0,
                    description=f"Checkerboard 2 - spans {even_spans} loaded (max -ve moment)"
                ))
        
        if mode in ("all", "shear") and n_spans >= 2:
            # Adjacent span loading for maximum shear
            # Load adjacent pairs of spans
            for i in range(n_spans - 1):
                patterns.append(PatternLoadCase(
                    mode=PatternLoadingMode.ADJACENT_MAX_SHEAR,
                    loaded_spans=[i, i + 1],
                    factor=1.0,
                    description=f"Adjacent spans {i},{i+1} loaded (max shear)"
                ))
        
        return patterns
    
    @staticmethod
    def create_user_defined_pattern(
        loaded_spans: List[int], 
        description: str = ""
    ) -> PatternLoadCase:
        """Create user-defined pattern loading case.
        
        Args:
            loaded_spans: List of span indices to load (0-indexed)
            description: Description of the pattern
            
        Returns:
            User-defined pattern load case
        """
        return PatternLoadCase(
            mode=PatternLoadingMode.USER_DEFINED,
            loaded_spans=loaded_spans,
            factor=1.0,
            description=description or f"User-defined - spans {loaded_spans} loaded"
        )


@dataclass
class LoadCombinationOptions:
    """Configuration options for load combination generation.
    
    Attributes:
        include_wind: Include wind load combinations
        include_seismic: Include seismic load combinations
        include_accidental: Include accidental load combinations
        include_pattern_loading: Enable pattern loading for continuous members
        pattern_loading_mode: Pattern loading mode ("all", "checkerboard", "shear", "full")
        n_continuous_spans: Number of continuous spans for pattern loading
        custom_combinations: User-defined custom combinations
    """
    include_wind: bool = True
    include_seismic: bool = False  # Seismic typically not required in HK for low seismicity
    include_accidental: bool = True
    include_pattern_loading: bool = False
    pattern_loading_mode: str = "checkerboard"
    n_continuous_spans: int = 0
    custom_combinations: List[LoadCombinationDefinition] = field(default_factory=list)


class LoadCombinationManager:
    """Manager for load combinations with validation and export capabilities.
    
    This class orchestrates the generation, validation, and application of
    load combinations per HK Code 2013 and Eurocode 8.
    """
    
    def __init__(self, options: Optional[LoadCombinationOptions] = None):
        """Initialize load combination manager.
        
        Args:
            options: Configuration options (uses defaults if None)
        """
        self.options = options or LoadCombinationOptions()
        self.combinations: List[LoadCombinationDefinition] = []
        self.pattern_cases: List[PatternLoadCase] = []
        self._generate_combinations()
    
    def _generate_combinations(self) -> None:
        """Generate load combinations based on configuration options."""
        # Always include gravity combinations
        self.combinations.extend(LoadCombinationLibrary.get_uls_gravity_combinations())
        
        # Add wind combinations if requested
        if self.options.include_wind:
            self.combinations.extend(LoadCombinationLibrary.get_uls_wind_combinations())
        
        # Add seismic combinations if requested
        if self.options.include_seismic:
            self.combinations.extend(LoadCombinationLibrary.get_uls_seismic_combinations())
        
        # Add accidental combinations if requested
        if self.options.include_accidental:
            self.combinations.extend(LoadCombinationLibrary.get_uls_accidental_combinations())
        
        # Always include SLS combinations
        self.combinations.extend(LoadCombinationLibrary.get_sls_combinations())
        
        # Add custom combinations
        if self.options.custom_combinations:
            self.combinations.extend(self.options.custom_combinations)
        
        # Generate pattern loading cases if requested
        if self.options.include_pattern_loading and self.options.n_continuous_spans > 0:
            self.pattern_cases = PatternLoadingGenerator.generate_patterns(
                self.options.n_continuous_spans,
                self.options.pattern_loading_mode
            )
    
    def get_all_combinations(self) -> List[LoadCombinationDefinition]:
        """Get all active load combinations.
        
        Returns:
            List of all load combination definitions
        """
        return self.combinations
    
    def get_uls_combinations(self) -> List[LoadCombinationDefinition]:
        """Get ULS load combinations only.
        
        Returns:
            List of ULS combinations
        """
        return [c for c in self.combinations 
                if c.category != LoadCombinationCategory.SLS]
    
    def get_sls_combinations(self) -> List[LoadCombinationDefinition]:
        """Get SLS load combinations only.
        
        Returns:
            List of SLS combinations
        """
        return [c for c in self.combinations 
                if c.category == LoadCombinationCategory.SLS]
    
    def get_combination_by_name(self, name: str) -> Optional[LoadCombinationDefinition]:
        """Get combination by name.
        
        Args:
            name: Combination name (e.g., "LC1")
            
        Returns:
            Combination definition or None if not found
        """
        for comb in self.combinations:
            if comb.name == name:
                return comb
        return None
    
    def validate_combination(
        self, combination: LoadCombinationDefinition
    ) -> Tuple[bool, List[str]]:
        """Validate a load combination definition.
        
        Checks:
        - Load factors are non-negative (except for reversal cases)
        - At least one load component is present
        - Factors are within reasonable limits (0.0 to 2.0)
        
        Args:
            combination: Combination to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check if combination has load factors
        if not combination.load_factors:
            errors.append(f"{combination.name}: No load factors defined")
        
        # Validate load factor ranges
        for component, factor in combination.load_factors.items():
            if abs(factor) > 2.0:
                errors.append(
                    f"{combination.name}: Factor {factor} for {component.value} "
                    f"exceeds typical range [-2.0, 2.0]"
                )
        
        # Check for dead load presence in ULS combinations
        if combination.category != LoadCombinationCategory.SLS:
            if LoadComponentType.DL not in combination.load_factors:
                errors.append(
                    f"{combination.name}: ULS combination should include dead load (DL)"
                )
        
        return (len(errors) == 0, errors)
    
    def validate_all_combinations(self) -> Tuple[bool, List[str]]:
        """Validate all load combinations.
        
        Returns:
            Tuple of (all_valid, error_messages)
        """
        all_errors = []
        for comb in self.combinations:
            is_valid, errors = self.validate_combination(comb)
            if not is_valid:
                all_errors.extend(errors)
        
        return (len(all_errors) == 0, all_errors)
    
    def export_combination_table(self, format: str = "text") -> str:
        """Export load combination table for reporting.
        
        Args:
            format: Export format ("text", "markdown", "latex")
            
        Returns:
            Formatted table string
        """
        if format == "markdown":
            return self._export_markdown_table()
        elif format == "latex":
            return self._export_latex_table()
        else:
            return self._export_text_table()
    
    def _export_text_table(self) -> str:
        """Export as plain text table."""
        lines = []
        lines.append("=" * 100)
        lines.append("LOAD COMBINATIONS SUMMARY")
        lines.append("=" * 100)
        lines.append(f"{'Name':<8} {'Equation':<40} {'Code Clause':<30} {'Category':<20}")
        lines.append("-" * 100)
        
        for comb in self.combinations:
            equation = comb.to_equation()
            lines.append(
                f"{comb.name:<8} {equation:<40} {comb.code_clause:<30} "
                f"{comb.category.value:<20}"
            )
        
        lines.append("=" * 100)
        lines.append(f"Total combinations: {len(self.combinations)}")
        
        if self.pattern_cases:
            lines.append(f"\nPattern loading cases: {len(self.pattern_cases)}")
            for pattern in self.pattern_cases:
                lines.append(f"  - {pattern.description}")
        
        lines.append("")
        return "\n".join(lines)
    
    def _export_markdown_table(self) -> str:
        """Export as markdown table."""
        lines = []
        lines.append("## Load Combinations Summary")
        lines.append("")
        lines.append("| Name | Equation | Code Clause | Category |")
        lines.append("|------|----------|-------------|----------|")
        
        for comb in self.combinations:
            equation = comb.to_equation()
            lines.append(
                f"| {comb.name} | {equation} | {comb.code_clause} | "
                f"{comb.category.value} |"
            )
        
        lines.append("")
        lines.append(f"**Total combinations:** {len(self.combinations)}")
        
        if self.pattern_cases:
            lines.append("")
            lines.append("### Pattern Loading Cases")
            lines.append("")
            for pattern in self.pattern_cases:
                lines.append(f"- {pattern.description}")
        
        return "\n".join(lines)
    
    def _export_latex_table(self) -> str:
        """Export as LaTeX table."""
        lines = []
        lines.append(r"\begin{table}[h]")
        lines.append(r"\centering")
        lines.append(r"\caption{Load Combinations per HK Code 2013}")
        lines.append(r"\begin{tabular}{llll}")
        lines.append(r"\hline")
        lines.append(r"Name & Equation & Code Clause & Category \\")
        lines.append(r"\hline")
        
        for comb in self.combinations:
            equation = comb.to_equation().replace("_", r"\_")
            clause = comb.code_clause.replace("_", r"\_")
            category = comb.category.value.replace("_", r"\_")
            lines.append(f"{comb.name} & {equation} & {clause} & {category} \\\\")
        
        lines.append(r"\hline")
        lines.append(r"\end{tabular}")
        lines.append(r"\end{table}")
        
        return "\n".join(lines)
    
    def get_summary(self) -> Dict[str, int]:
        """Get summary statistics.
        
        Returns:
            Dictionary with combination counts by category
        """
        summary = {
            "total": len(self.combinations),
            "uls_gravity": len([c for c in self.combinations 
                               if c.category == LoadCombinationCategory.ULS_GRAVITY]),
            "uls_wind": len([c for c in self.combinations 
                            if c.category == LoadCombinationCategory.ULS_WIND]),
            "uls_seismic": len([c for c in self.combinations 
                               if c.category == LoadCombinationCategory.ULS_SEISMIC]),
            "uls_accidental": len([c for c in self.combinations 
                                  if c.category == LoadCombinationCategory.ULS_ACCIDENTAL]),
            "sls": len([c for c in self.combinations 
                       if c.category == LoadCombinationCategory.SLS]),
            "pattern_cases": len(self.pattern_cases),
        }
        return summary
