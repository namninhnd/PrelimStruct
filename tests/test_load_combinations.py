"""
Unit tests for Load Combinations module (Feature 9)

Tests cover:
- Load combination definitions (ULS and SLS)
- LoadCombinationManager functionality
- Pattern loading generation
- Load factor validation
"""

import pytest
from src.fem.load_combinations import (
    LoadComponentType,
    LoadCombinationCategory,
    LoadFactor,
    LoadCombinationDefinition,
    LoadCombinationLibrary,
    PatternLoadingMode,
    PatternLoadCase,
    PatternLoadingGenerator,
    LoadCombinationOptions,
    LoadCombinationManager,
)
from src.core.data_models import LoadCombination


class TestLoadCombinationDefinitions:
    """Tests for load combination definitions and library."""
    
    def test_uls_gravity_combinations(self):
        """Test ULS gravity combination definitions."""
        combs = LoadCombinationLibrary.get_uls_gravity_combinations()
        
        assert len(combs) == 2
        
        # LC1: 1.4DL + 1.4SDL + 1.6LL
        lc1 = combs[0]
        assert lc1.name == "LC1"
        assert lc1.combination_type == LoadCombination.ULS_GRAVITY_1
        assert lc1.get_factor(LoadComponentType.DL) == 1.4
        assert lc1.get_factor(LoadComponentType.LL) == 1.6
        
        # LC2: 1.0DL + 1.0SDL + 1.6LL (min dead)
        lc2 = combs[1]
        assert lc2.name == "LC2"
        assert lc2.get_factor(LoadComponentType.DL) == 1.0
        assert lc2.get_factor(LoadComponentType.LL) == 1.6
    
    def test_uls_wind_combinations(self):
        """Test ULS wind combination definitions."""
        combs = LoadCombinationLibrary.get_uls_wind_combinations()
        
        # 24 wind cases x 2 (MAX/MIN gravity) = 48 combinations
        assert len(combs) == 48
        
        # LC_W1_MAX: 1.4DL + 1.4SDL + 1.4W1
        lc_w1_max = combs[0]
        assert lc_w1_max.name == "LC_W1_MAX"
        assert lc_w1_max.get_factor(LoadComponentType.DL) == 1.4
        assert lc_w1_max.get_factor(LoadComponentType.W1) == 1.4
        
        # LC_W1_MIN: 1.0DL + 1.0SDL + 1.4W1
        lc_w1_min = combs[1]
        assert lc_w1_min.name == "LC_W1_MIN"
        assert lc_w1_min.get_factor(LoadComponentType.DL) == 1.0
        assert lc_w1_min.get_factor(LoadComponentType.W1) == 1.4
    
    def test_uls_seismic_combinations(self):
        """Test ULS seismic combination definitions per Eurocode 8."""
        combs = LoadCombinationLibrary.get_uls_seismic_combinations()
        
        assert len(combs) == 6
        
        # LC_SEISMIC_E1_POS: 1.0DL + 0.3LL + 1.0E1
        lc_seismic = combs[0]
        assert lc_seismic.name == "LC_SEISMIC_E1_POS"
        assert lc_seismic.get_factor(LoadComponentType.DL) == 1.0
        assert lc_seismic.get_factor(LoadComponentType.LL) == 0.3
        assert lc_seismic.get_factor(LoadComponentType.E1) == 1.0
        
        # Check we have both positive and negative directions
        names = [c.name for c in combs]
        assert "LC_SEISMIC_E1_POS" in names
        assert "LC_SEISMIC_E1_NEG" in names
    
    def test_sls_combinations(self):
        """Test SLS combination definitions."""
        combs = LoadCombinationLibrary.get_sls_combinations()
        
        assert len(combs) == 3
        
        # SLS1: Characteristic (1.0DL + 1.0LL)
        sls1 = combs[0]
        assert sls1.name == "SLS1"
        assert sls1.combination_type == LoadCombination.SLS_CHARACTERISTIC
        assert sls1.get_factor(LoadComponentType.DL) == 1.0
        assert sls1.get_factor(LoadComponentType.LL) == 1.0
        
        # SLS2: Frequent (1.0DL + 0.5LL)
        sls2 = combs[1]
        assert sls2.get_factor(LoadComponentType.LL) == 0.5
        
        # SLS3: Quasi-permanent (1.0DL + 0.3LL)
        sls3 = combs[2]
        assert sls3.get_factor(LoadComponentType.LL) == 0.3
    
    def test_get_all_combinations(self):
        """Test retrieving all standard combinations."""
        all_combs = LoadCombinationLibrary.get_all_combinations()
        
        # Should have: 2 gravity + 48 wind + 6 seismic + 1 accidental + 3 SLS = 60 total
        assert len(all_combs) == 60
    
    def test_combination_equation_generation(self):
        """Test load combination equation string generation."""
        combs = LoadCombinationLibrary.get_uls_gravity_combinations()
        lc1 = combs[0]
        
        equation = lc1.to_equation()
        assert "1.4DL" in equation
        assert "1.6LL" in equation
    
    def test_factored_load_calculation(self):
        """Test calculation of factored loads."""
        lc = LoadCombinationDefinition(
            name="TEST",
            combination_type=LoadCombination.ULS_GRAVITY_1,
            category=LoadCombinationCategory.ULS_GRAVITY,
            load_factors={
                LoadComponentType.DL: 1.4,
                LoadComponentType.LL: 1.6,
            },
            description="Test combination",
            code_clause="Test"
        )
        
        loads = {
            LoadComponentType.DL: 100.0,  # kN
            LoadComponentType.LL: 50.0,   # kN
        }
        
        factored_load = lc.get_factored_load(loads)
        expected = 1.4 * 100.0 + 1.6 * 50.0  # = 140 + 80 = 220 kN
        assert factored_load == pytest.approx(expected)


class TestPatternLoading:
    """Tests for pattern loading generation."""
    
    def test_full_loading_pattern(self):
        """Test full loading pattern generation."""
        patterns = PatternLoadingGenerator.generate_patterns(4, mode="full")
        
        assert len(patterns) == 1
        assert patterns[0].mode == PatternLoadingMode.FULL
        assert patterns[0].loaded_spans == [0, 1, 2, 3]
    
    def test_checkerboard_patterns(self):
        """Test checkerboard pattern generation."""
        patterns = PatternLoadingGenerator.generate_patterns(4, mode="checkerboard")
        
        # Should have: 1 full + 2 checkerboard = 3 patterns
        assert len(patterns) >= 2
        
        # Check odd spans pattern (0, 2)
        odd_pattern = [p for p in patterns if p.mode == PatternLoadingMode.CHECKERBOARD_MAX_POS][0]
        assert odd_pattern.loaded_spans == [0, 2]
        
        # Check even spans pattern (1, 3)
        even_pattern = [p for p in patterns if p.mode == PatternLoadingMode.CHECKERBOARD_MAX_NEG][0]
        assert even_pattern.loaded_spans == [1, 3]
    
    def test_adjacent_span_patterns(self):
        """Test adjacent span loading for maximum shear."""
        patterns = PatternLoadingGenerator.generate_patterns(4, mode="shear")
        
        # Should have: 1 full + 3 adjacent pairs (0-1, 1-2, 2-3) = 4 patterns
        assert len(patterns) >= 3
        
        adjacent_patterns = [p for p in patterns if p.mode == PatternLoadingMode.ADJACENT_MAX_SHEAR]
        assert len(adjacent_patterns) == 3
        
        # Check first adjacent pair
        assert [0, 1] in [p.loaded_spans for p in adjacent_patterns]
    
    def test_all_patterns(self):
        """Test generation of all pattern types."""
        patterns = PatternLoadingGenerator.generate_patterns(3, mode="all")
        
        # Should have: 1 full + 2 checkerboard + 2 adjacent = 5 patterns
        assert len(patterns) >= 4
    
    def test_user_defined_pattern(self):
        """Test user-defined pattern creation."""
        pattern = PatternLoadingGenerator.create_user_defined_pattern(
            loaded_spans=[0, 2, 4],
            description="Custom test pattern"
        )
        
        assert pattern.mode == PatternLoadingMode.USER_DEFINED
        assert pattern.loaded_spans == [0, 2, 4]
        assert pattern.is_span_loaded(0)
        assert not pattern.is_span_loaded(1)


class TestLoadCombinationManager:
    """Tests for LoadCombinationManager class."""
    
    def test_default_initialization(self):
        """Test manager initialization with default options."""
        manager = LoadCombinationManager()
        
        combs = manager.get_all_combinations()
        
        # Should include: gravity + wind + accidental + SLS (no seismic by default)
        assert len(combs) > 0
        
        # Check that wind is included
        wind_combs = [c for c in combs if c.category == LoadCombinationCategory.ULS_WIND]
        assert len(wind_combs) > 0
    
    def test_seismic_option(self):
        """Test enabling seismic combinations."""
        options = LoadCombinationOptions(include_seismic=True)
        manager = LoadCombinationManager(options)
        
        combs = manager.get_all_combinations()
        seismic_combs = [c for c in combs if c.category == LoadCombinationCategory.ULS_SEISMIC]
        assert len(seismic_combs) == 6
    
    def test_exclude_wind(self):
        """Test excluding wind combinations."""
        options = LoadCombinationOptions(include_wind=False)
        manager = LoadCombinationManager(options)
        
        combs = manager.get_all_combinations()
        wind_combs = [c for c in combs if c.category == LoadCombinationCategory.ULS_WIND]
        assert len(wind_combs) == 0
    
    def test_pattern_loading_option(self):
        """Test enabling pattern loading."""
        options = LoadCombinationOptions(
            include_pattern_loading=True,
            n_continuous_spans=3,
            pattern_loading_mode="all"
        )
        manager = LoadCombinationManager(options)
        
        assert len(manager.pattern_cases) > 0
        assert manager.get_summary()["pattern_cases"] > 0
    
    def test_get_uls_combinations(self):
        """Test filtering ULS combinations."""
        manager = LoadCombinationManager()
        
        uls_combs = manager.get_uls_combinations()
        
        # All should be ULS (not SLS)
        for comb in uls_combs:
            assert comb.category != LoadCombinationCategory.SLS
    
    def test_get_sls_combinations(self):
        """Test filtering SLS combinations."""
        manager = LoadCombinationManager()
        
        sls_combs = manager.get_sls_combinations()
        
        # All should be SLS
        for comb in sls_combs:
            assert comb.category == LoadCombinationCategory.SLS
    
    def test_get_combination_by_name(self):
        """Test retrieving combination by name."""
        manager = LoadCombinationManager()
        
        lc1 = manager.get_combination_by_name("LC1")
        assert lc1 is not None
        assert lc1.name == "LC1"
        
        # Non-existent combination
        lc_none = manager.get_combination_by_name("LC999")
        assert lc_none is None
    
    def test_combination_validation(self):
        """Test load combination validation."""
        manager = LoadCombinationManager()
        
        # Get a valid combination
        lc1 = manager.get_combination_by_name("LC1")
        is_valid, errors = manager.validate_combination(lc1)
        
        assert is_valid
        assert len(errors) == 0
    
    def test_invalid_combination_validation(self):
        """Test validation of invalid combination."""
        manager = LoadCombinationManager()
        
        # Create an invalid combination (excessive load factor)
        invalid_comb = LoadCombinationDefinition(
            name="INVALID",
            combination_type=LoadCombination.ULS_GRAVITY_1,
            category=LoadCombinationCategory.ULS_GRAVITY,
            load_factors={LoadComponentType.DL: 5.0},  # Excessive factor
            description="Invalid test",
            code_clause="Test"
        )
        
        is_valid, errors = manager.validate_combination(invalid_comb)
        
        assert not is_valid
        assert len(errors) > 0
    
    def test_validate_all_combinations(self):
        """Test validation of all combinations."""
        manager = LoadCombinationManager()
        
        is_valid, errors = manager.validate_all_combinations()
        
        # All standard combinations should be valid
        assert is_valid
        assert len(errors) == 0
    
    def test_export_text_table(self):
        """Test exporting combination table as text."""
        manager = LoadCombinationManager()
        
        table = manager.export_combination_table(format="text")
        
        assert "LOAD COMBINATIONS SUMMARY" in table
        assert "LC1" in table
        assert "Total combinations:" in table
    
    def test_export_markdown_table(self):
        """Test exporting combination table as markdown."""
        manager = LoadCombinationManager()
        
        table = manager.export_combination_table(format="markdown")
        
        assert "## Load Combinations Summary" in table
        assert "| Name |" in table
        assert "| LC1 |" in table
    
    def test_summary_statistics(self):
        """Test summary statistics generation."""
        manager = LoadCombinationManager()
        
        summary = manager.get_summary()
        
        assert "total" in summary
        assert "uls_gravity" in summary
        assert "sls" in summary
        assert summary["total"] > 0
        assert summary["uls_gravity"] == 2


class TestLoadFactor:
    """Tests for LoadFactor class."""
    
    def test_load_factor_creation(self):
        """Test creating a load factor."""
        factor = LoadFactor(
            component=LoadComponentType.DL,
            factor=1.4,
            description="Dead load factor"
        )
        
        assert factor.component == LoadComponentType.DL
        assert factor.factor == 1.4
    
    def test_apply_load_factor(self):
        """Test applying load factor to value."""
        factor = LoadFactor(
            component=LoadComponentType.LL,
            factor=1.6
        )
        
        factored = factor.apply(100.0)
        assert factored == pytest.approx(160.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
