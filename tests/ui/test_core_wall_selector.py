import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.core.data_models import CoreWallConfig
from src.ui.components.core_wall_selector import get_core_wall_svg, render_core_wall_selector

class TestCoreWallSelector(unittest.TestCase):
    def test_get_core_wall_svg(self):
        """Test SVG generation for all configs."""
        for config in CoreWallConfig:
            svg = get_core_wall_svg(config)
            self.assertTrue(svg.startswith('<svg'))
            self.assertTrue(svg.endswith('</svg>'))
            self.assertIn('viewBox="0 0 100 100"', svg)
            
    def test_svg_selected_color(self):
        """Test selected state color change."""
        svg_normal = get_core_wall_svg(CoreWallConfig.I_SECTION, selected=False)
        svg_selected = get_core_wall_svg(CoreWallConfig.I_SECTION, selected=True)
        
        self.assertIn('stroke="#1E3A5F"', svg_normal)
        self.assertIn('stroke="#EF4444"', svg_selected)

    @patch('src.ui.components.core_wall_selector.st')
    def test_render_core_wall_selector(self, mock_st):
        """Test selector rendering logic."""
        # Mock streamlit columns (2 columns for 2 configs)
        mock_cols = [MagicMock() for _ in range(2)]
        mock_st.columns.return_value = mock_cols
        
        # Mock button return value (simulate no click)
        mock_st.button.return_value = False
        
        # Call function
        result = render_core_wall_selector(CoreWallConfig.I_SECTION)
        
        # Should return current config if no button clicked
        self.assertEqual(result, CoreWallConfig.I_SECTION)
        
        # Verify columns created (2 columns for 2 configs)
        mock_st.columns.assert_called_with(2)
        
        # Verify buttons created (2 buttons, one for each config)
        self.assertEqual(mock_st.button.call_count, 2)

    @patch('src.ui.components.core_wall_selector.st')
    def test_render_core_wall_selector_click(self, mock_st):
        """Test selector state update on click."""
        mock_cols = [MagicMock() for _ in range(2)]
        mock_st.columns.return_value = mock_cols
        mock_st.button.side_effect = [False, True]
        result = render_core_wall_selector(CoreWallConfig.I_SECTION)
        self.assertEqual(result, CoreWallConfig.TUBE_WITH_OPENINGS)

if __name__ == '__main__':
    unittest.main()
