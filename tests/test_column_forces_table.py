"""
Column Forces Table Component Tests.

TDD RED phase: These tests should FAIL initially since ColumnForcesTable doesn't exist.

Tests cover:
1. Column forces can be extracted and grouped by parent_column_id
2. Resulting DataFrame is non-empty after analysis
3. Force normalization uses the shared utility
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Dict, Any, Optional, List


# --- Fixtures for mocking FEM model and analysis result ---

@dataclass
class MockNode:
    """Mock node for testing."""
    x: float
    y: float
    z: float


@dataclass
class MockElement:
    """Mock element for testing."""
    node_tags: List[int]
    geometry: Optional[Dict[str, Any]] = None
    element_type: str = "elasticBeamColumn"


@pytest.fixture
def mock_column_model():
    """Create a mock FEM model with column elements.
    
    Simulates a single column with 4 sub-elements (parent_column_id=1001).
    """
    model = MagicMock()
    
    # Nodes: 5 nodes along a column at (0, 0, z) from z=0 to z=3.0
    model.nodes = {
        1: MockNode(0.0, 0.0, 0.0),    # Base
        2: MockNode(0.0, 0.0, 0.75),   # 0.25L
        3: MockNode(0.0, 0.0, 1.5),    # 0.5L
        4: MockNode(0.0, 0.0, 2.25),   # 0.75L
        5: MockNode(0.0, 0.0, 3.0),    # Top (1.0L)
    }
    
    # Elements: 4 sub-elements (1001-1004) with parent_column_id=1001
    model.elements = {
        1001: MockElement(
            node_tags=[1, 2],
            geometry={"parent_column_id": 1001, "sub_element_index": 0}
        ),
        1002: MockElement(
            node_tags=[2, 3],
            geometry={"parent_column_id": 1001, "sub_element_index": 1}
        ),
        1003: MockElement(
            node_tags=[3, 4],
            geometry={"parent_column_id": 1001, "sub_element_index": 2}
        ),
        1004: MockElement(
            node_tags=[4, 5],
            geometry={"parent_column_id": 1001, "sub_element_index": 3}
        ),
    }
    
    return model


@pytest.fixture
def mock_analysis_result():
    """Create a mock analysis result with element forces.
    
    Forces are in Newtons and N-m (OpenSeesPy output format).
    """
    result = MagicMock()
    result.success = True
    
    # Element forces for each sub-element
    # Format: N_i, Vy_i, Vz_i, T_i, My_i, Mz_i, N_j, Vy_j, Vz_j, T_j, My_j, Mz_j
    result.element_forces = {
        1001: {
            "N_i": -100000.0, "Vy_i": 1000.0, "Vz_i": 500.0,
            "T_i": 100.0, "My_i": 5000.0, "Mz_i": 2000.0,
            "N_j": -100000.0, "Vy_j": -1000.0, "Vz_j": -500.0,
            "T_j": -100.0, "My_j": -3000.0, "Mz_j": -1500.0,
        },
        1002: {
            "N_i": -98000.0, "Vy_i": 800.0, "Vz_i": 400.0,
            "T_i": 80.0, "My_i": 4000.0, "Mz_i": 1600.0,
            "N_j": -98000.0, "Vy_j": -800.0, "Vz_j": -400.0,
            "T_j": -80.0, "My_j": -2500.0, "Mz_j": -1200.0,
        },
        1003: {
            "N_i": -96000.0, "Vy_i": 600.0, "Vz_i": 300.0,
            "T_i": 60.0, "My_i": 3000.0, "Mz_i": 1200.0,
            "N_j": -96000.0, "Vy_j": -600.0, "Vz_j": -300.0,
            "T_j": -60.0, "My_j": -1500.0, "Mz_j": -800.0,
        },
        1004: {
            "N_i": -94000.0, "Vy_i": 400.0, "Vz_i": 200.0,
            "T_i": 40.0, "My_i": 2000.0, "Mz_i": 800.0,
            "N_j": -94000.0, "Vy_j": -400.0, "Vz_j": -200.0,
            "T_j": -40.0, "My_j": -500.0, "Mz_j": -400.0,
        },
    }
    
    return result


class TestColumnForcesTableExtraction:
    """Tests for column force extraction and grouping."""
    
    def test_can_import_column_forces_table(self):
        """GIVEN ColumnForcesTable component
        WHEN importing
        THEN should be importable from ui.components"""
        from src.ui.components.column_forces_table import ColumnForcesTable
        assert ColumnForcesTable is not None
    
    def test_column_forces_grouped_by_parent_column_id(self, mock_column_model, mock_analysis_result):
        """GIVEN model with column sub-elements
        WHEN extracting column forces
        THEN forces should be grouped by parent_column_id"""
        from src.ui.components.column_forces_table import ColumnForcesTable
        
        table = ColumnForcesTable(
            model=mock_column_model,
            analysis_result=mock_analysis_result,
            force_type="N",
            story_height=3.0,
            load_case="DL"
        )
        
        df = table._extract_column_forces()
        
        # Should have 5 rows (5 nodes for the parent column)
        assert len(df) == 5, f"Expected 5 rows, got {len(df)}"
        
        # All rows should belong to same Column ID
        assert df["Column ID"].nunique() == 1
        assert df["Column ID"].iloc[0] == 1001
    
    def test_dataframe_non_empty_after_analysis(self, mock_column_model, mock_analysis_result):
        """GIVEN model with analysis result
        WHEN extracting column forces
        THEN DataFrame should not be empty"""
        from src.ui.components.column_forces_table import ColumnForcesTable
        
        table = ColumnForcesTable(
            model=mock_column_model,
            analysis_result=mock_analysis_result,
            force_type="N",
            story_height=3.0,
            load_case="DL"
        )
        
        df = table._extract_column_forces()
        
        assert not df.empty, "DataFrame should not be empty after analysis"
        assert len(df) > 0
    
    def test_dataframe_has_expected_columns(self, mock_column_model, mock_analysis_result):
        """GIVEN model with analysis result
        WHEN extracting column forces
        THEN DataFrame should have expected columns"""
        from src.ui.components.column_forces_table import ColumnForcesTable
        
        table = ColumnForcesTable(
            model=mock_column_model,
            analysis_result=mock_analysis_result,
            force_type="N",
            story_height=3.0,
            load_case="DL"
        )
        
        df = table._extract_column_forces()
        
        expected_cols = [
            "Load Case", "Column ID", "Floor", "Node", "Position",
            "X (m)", "Y (m)", "Z (m)",
            "N (kN)", "Vy (kN)", "Vz (kN)", "My-minor (kNm)", "Mz-major (kNm)", "T (kNm)"
        ]
        
        for col in expected_cols:
            assert col in df.columns, f"Missing column: {col}"


class TestColumnForcesTableNormalization:
    """Tests for force normalization using shared utility."""
    
    def test_uses_shared_normalization(self, mock_column_model, mock_analysis_result):
        """GIVEN ColumnForcesTable
        WHEN normalizing forces
        THEN should use normalize_end_force from force_normalization module"""
        from src.ui.components.column_forces_table import ColumnForcesTable
        from src.fem.force_normalization import normalize_end_force
        
        # Verify the import exists in column_forces_table
        import src.ui.components.column_forces_table as module
        
        # The module should import normalize_end_force
        assert hasattr(module, "normalize_end_force") or "normalize_end_force" in dir(module), \
            "ColumnForcesTable should import normalize_end_force"
    
    def test_j_end_forces_normalized_correctly(self, mock_column_model, mock_analysis_result):
        """GIVEN column forces at j-end
        WHEN extracting forces
        THEN Vy, Vz should be negated and My, Mz, T should remain raw"""
        from src.ui.components.column_forces_table import ColumnForcesTable
        
        table = ColumnForcesTable(
            model=mock_column_model,
            analysis_result=mock_analysis_result,
            force_type="My",
            story_height=3.0,
            load_case="DL"
        )
        
        df = table._extract_column_forces()
        
        # Last row should be the j-end of the last sub-element (node 5)
        last_row = df.iloc[-1]
        
        assert abs(last_row["My-minor (kNm)"] - (-0.5)) < 0.01, \
            f"Expected My ~-0.5 kNm after normalization, got {last_row['My-minor (kNm)']}"


class TestColumnForcesTableFloorMethods:
    """Tests for floor-related methods."""
    
    def test_get_floors_returns_list(self, mock_column_model, mock_analysis_result):
        """GIVEN ColumnForcesTable
        WHEN calling get_floors
        THEN should return list of floor levels"""
        from src.ui.components.column_forces_table import ColumnForcesTable
        
        table = ColumnForcesTable(
            model=mock_column_model,
            analysis_result=mock_analysis_result,
            force_type="N",
            story_height=3.0,
            load_case="DL"
        )
        
        floors = table.get_floors()
        
        assert isinstance(floors, list)
        # With story_height=3.0 and column from z=0 to z=3, should have floor 0 and 1
        assert 0 in floors or 1 in floors
    
    def test_get_columns_on_floor_returns_list(self, mock_column_model, mock_analysis_result):
        """GIVEN ColumnForcesTable
        WHEN calling get_columns_on_floor
        THEN should return list of column IDs"""
        from src.ui.components.column_forces_table import ColumnForcesTable
        
        table = ColumnForcesTable(
            model=mock_column_model,
            analysis_result=mock_analysis_result,
            force_type="N",
            story_height=3.0,
            load_case="DL"
        )
        
        floors = table.get_floors()
        if floors:
            columns = table.get_columns_on_floor(floors[0])
            assert isinstance(columns, list)
            assert 1001 in columns


class TestColumnForcesTableEmptyResult:
    """Tests for empty/no analysis result scenarios."""
    
    def test_empty_result_returns_empty_dataframe(self, mock_column_model):
        """GIVEN no analysis result
        WHEN extracting column forces
        THEN should return empty DataFrame"""
        from src.ui.components.column_forces_table import ColumnForcesTable
        
        empty_result = MagicMock()
        empty_result.success = False
        empty_result.element_forces = {}
        
        table = ColumnForcesTable(
            model=mock_column_model,
            analysis_result=empty_result,
            force_type="N",
            story_height=3.0,
            load_case="DL"
        )
        
        df = table._extract_column_forces()
        
        assert df.empty, "DataFrame should be empty when no forces available"
    
    def test_none_result_returns_empty_dataframe(self, mock_column_model):
        """GIVEN None analysis result
        WHEN extracting column forces
        THEN should return empty DataFrame"""
        from src.ui.components.column_forces_table import ColumnForcesTable
        
        table = ColumnForcesTable(
            model=mock_column_model,
            analysis_result=None,
            force_type="N",
            story_height=3.0,
            load_case="DL"
        )
        
        df = table._extract_column_forces()
        
        assert df.empty, "DataFrame should be empty when result is None"
