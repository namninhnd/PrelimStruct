
import pytest
from src.fem.load_combinations import (
    LoadCombinationManager, 
    LoadCombinationCategory,
    LoadCombinationOptions,
    LoadComponentType
)

def test_load_combination_generation():
    options = LoadCombinationOptions(
        include_wind=True,
        include_seismic=True,
        include_accidental=True
    )
    manager = LoadCombinationManager(options)
    
    combinations = manager.get_all_combinations()
    
    # Check counts
    gravity = [c for c in combinations if c.category == LoadCombinationCategory.ULS_GRAVITY]
    wind = [c for c in combinations if c.category == LoadCombinationCategory.ULS_WIND]
    seismic = [c for c in combinations if c.category == LoadCombinationCategory.ULS_SEISMIC]
    accidental = [c for c in combinations if c.category == LoadCombinationCategory.ULS_ACCIDENTAL]
    sls = [c for c in combinations if c.category == LoadCombinationCategory.SLS]
    
    assert len(gravity) == 2
    assert len(wind) == 48  # 24 directions * 2 variants
    assert len(seismic) == 6 # 3 directions * 2 variants (+/-)
    assert len(accidental) == 1
    assert len(sls) == 3
    
    print("\nLoad Combinations Table:")
    print(manager.export_combination_table())

def test_wind_combination_naming():
    options = LoadCombinationOptions(include_wind=True)
    manager = LoadCombinationManager(options)
    
    # Check W1 Max and Min
    w1_max = manager.get_combination_by_name("LC_W1_MAX")
    assert w1_max is not None
    assert w1_max.load_factors[LoadComponentType.W1] == 1.4
    assert w1_max.load_factors[LoadComponentType.DL] == 1.4
    
    w1_min = manager.get_combination_by_name("LC_W1_MIN")
    assert w1_min is not None
    assert w1_min.load_factors[LoadComponentType.W1] == 1.4
    assert w1_min.load_factors[LoadComponentType.DL] == 1.0

if __name__ == "__main__":
    test_load_combination_generation()
    test_wind_combination_naming()
