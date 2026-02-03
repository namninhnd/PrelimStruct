import pytest
import pandas as pd
from src.ui.components.reaction_table import ReactionTable
from src.fem.solver import AnalysisResult

def test_reaction_table_dataframe_generation():
    """Test DataFrame generation from AnalysisResult."""
    # Mock data
    result = AnalysisResult(success=True, message='Test')
    result.node_reactions = {
        1: [1000.0, 2000.0, 5000.0, 100.0, 200.0, 300.0],
        2: [-1000.0, -2000.0, 5000.0, -100.0, -200.0, -300.0]
    }
    
    table = ReactionTable(result)
    df = table._get_dataframe("Load Case 1")
    
    # Check dimensions: 2 nodes + 1 total = 3 rows
    assert len(df) == 3
    
    # Check columns (using kN-m for moments per SI convention)
    expected_cols = ["Fx (kN)", "Fy (kN)", "Fz (kN)", "Mx (kN-m)", "My (kN-m)", "Mz (kN-m)"]
    for col in expected_cols:
        assert col in df.columns
        
    # Check values (kN conversion /1000)
    assert df.loc[1, "Fx (kN)"] == 1.0
    assert df.loc[1, "Fz (kN)"] == 5.0
    
    # Check totals
    assert df.loc["TOTAL", "Fx (kN)"] == 0.0  # 1.0 + (-1.0)
    assert df.loc["TOTAL", "Fz (kN)"] == 10.0 # 5.0 + 5.0

def test_reaction_table_empty_results():
    """Test handling of empty results."""
    result = AnalysisResult(success=True, message='Test')
    table = ReactionTable(result)
    df = table._get_dataframe("Load Case 1")
    assert df.empty

def test_reaction_table_dict_input():
    """Test initialization with dictionary of results."""
    result1 = AnalysisResult(success=True, message='Test')
    result1.node_reactions = {1: [1000.0, 0, 0, 0, 0, 0]}
    
    results = {"Case A": result1}
    table = ReactionTable(results)
    
    df = table._get_dataframe("Case A")
    assert not df.empty
    assert df.loc[1, "Fx (kN)"] == 1.0
