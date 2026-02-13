"""
Gate G: UI Defaults + I-Section Semantics Tests

Verifies:
1. I-section defaults: flange_width=3.0m, web_length=3.0m (changed from 6.0m/8.0m)
2. Tube defaults: length_x=3.0m, length_y=3.0m (changed from 6.0m/6.0m)
3. Both runtime paths (sidebar.py and app.py) use consistent defaults
4. Labels and help text are semantically aligned

Phase 13A Gate G Acceptance Criteria (from plan):
- I-section defaults changed to 3.0m × 3.0m
- Tube defaults changed to 3.0m × 3.0m
- Both sidebar.py and app.py have matching defaults
- No semantic inversions in labels/help text
"""

import pytest
from unittest.mock import patch, MagicMock
import importlib
import sys


class TestGateGISectionDefaults:
    """Test I-section default values in both runtime paths."""

    def test_sidebar_i_section_defaults_are_3m_by_3m(self):
        """
        Verify sidebar.py I-section defaults are 3.0m × 3.0m.
        
        Gate G Requirement: I-section defaults changed from 6.0m/8.0m to 3.0m/3.0m
        """
        # Mock streamlit to extract default values without UI rendering
        with patch.dict(sys.modules, {'streamlit': MagicMock()}):
            st_mock = sys.modules['streamlit']
            
            # Configure number_input mock to return calls with parameters
            call_params = []
            def capture_number_input(*args, **kwargs):
                call_params.append((args, kwargs))
                return kwargs.get('value', 0.0)
            
            st_mock.number_input = capture_number_input
            st_mock.columns = lambda n: [MagicMock(), MagicMock()]
            st_mock.caption = MagicMock()
            st_mock.selectbox = lambda *args, **kwargs: None
            st_mock.expander = lambda *args, **kwargs: MagicMock(__enter__=lambda self: self, __exit__=lambda *args: None)
            
            import src.ui.sidebar
            
            # Read the source file to extract default values
            import inspect
            source = inspect.getsource(src.ui.sidebar)
            
            # Verify I-section flange_width default is 3.0
            assert 'value=3.0' in source, "I-section flange_width default should be 3.0m"
            
            # Verify I-section web_length default is 3.0
            # Count occurrences to ensure both flange and web are 3.0
            value_3_0_count = source.count('value=3.0')
            assert value_3_0_count >= 4, f"Expected at least 4 'value=3.0' entries (I-section: 2, Tube: 2), found {value_3_0_count}"

    def test_app_i_section_defaults_are_3m_by_3m(self):
        """
        Verify app.py I-section defaults are 3.0m × 3.0m.
        
        Gate G Requirement: app.py must match sidebar.py defaults
        """
        # Read app.py source to extract default values
        with open('app.py', 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Find I-section section (between "I-Section Dimensions" and "TUBE_WITH_OPENINGS")
        i_section_start = source.find('st.caption("I-Section Dimensions")')
        i_section_end = source.find('else:  # TUBE_WITH_OPENINGS', i_section_start)
        
        assert i_section_start != -1, "Could not find I-section section in app.py"
        assert i_section_end != -1, "Could not find TUBE section marker in app.py"
        
        i_section_code = source[i_section_start:i_section_end]
        
        # Verify both flange_width and web_length have value=3.0
        assert 'value=3.0' in i_section_code, "I-section should have value=3.0 defaults"
        assert i_section_code.count('value=3.0') == 2, "I-section should have exactly 2 value=3.0 entries (flange + web)"
        
        # Verify old defaults (6.0, 8.0) are gone
        assert 'value=6.0' not in i_section_code, "Old flange_width default 6.0 should be removed"
        assert 'value=8.0' not in i_section_code, "Old web_length default 8.0 should be removed"

    def test_i_section_semantic_alignment(self):
        """
        Verify I-section labels semantically match behavior.
        
        Gate G Requirement: No flange/web inversions or semantic misalignment
        """
        with open('app.py', 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Find I-section section
        i_section_start = source.find('st.caption("I-Section Dimensions")')
        i_section_end = source.find('else:  # TUBE_WITH_OPENINGS', i_section_start)
        i_section_code = source[i_section_start:i_section_end]
        
        # Verify flange and web labels exist and are semantically correct
        assert '"Flange Width (m)"' in i_section_code, "Flange Width label missing"
        assert '"Web Length (m)"' in i_section_code, "Web Length label missing"
        
        # Verify help text is semantically aligned
        assert 'Width of horizontal flange' in i_section_code, "Flange help text should reference 'horizontal'"
        assert 'Length of vertical web' in i_section_code, "Web help text should reference 'vertical'"
        
        # Verify variable names match semantics (flange_width, web_length)
        assert 'flange_width = st.number_input' in i_section_code, "flange_width variable should exist"
        assert 'web_length = st.number_input' in i_section_code, "web_length variable should exist"


class TestGateGTubeDefaults:
    """Test Tube configuration default values in both runtime paths."""

    def test_sidebar_tube_defaults_are_3m_by_3m(self):
        """
        Verify sidebar.py tube defaults are 3.0m × 3.0m.
        
        Gate G Requirement: Tube defaults changed from 6.0m × 6.0m to 3.0m × 3.0m
        """
        import inspect
        import src.ui.sidebar
        
        source = inspect.getsource(src.ui.sidebar)
        
        # Find Tube section
        tube_start = source.find('st.caption("Tube Dimensions")')
        assert tube_start != -1, "Could not find Tube Dimensions section"
        
        # Extract substring around Tube section
        tube_section = source[tube_start:tube_start + 1000]
        
        # Verify both length_x and length_y have value=3.0
        assert 'value=3.0' in tube_section, "Tube dimensions should have value=3.0 defaults"
        assert tube_section.count('value=3.0') == 2, "Tube should have exactly 2 value=3.0 entries (length_x + length_y)"
        
        # Verify old defaults (6.0) are gone from tube section
        assert 'value=6.0' not in tube_section, "Old tube default 6.0 should be removed"

    def test_app_tube_defaults_are_3m_by_3m(self):
        """
        Verify app.py tube defaults are 3.0m × 3.0m.
        
        Gate G Requirement: app.py must match sidebar.py defaults
        """
        with open('app.py', 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Find Tube section (after "else:  # TUBE_WITH_OPENINGS")
        tube_start = source.find('st.caption("Tube Dimensions")')
        
        assert tube_start != -1, "Could not find Tube Dimensions section in app.py"
        
        # Extract substring around Tube section (before Opening Dimensions)
        tube_end = source.find('st.caption("Opening Dimensions")', tube_start)
        tube_code = source[tube_start:tube_end]
        
        # Verify both length_x and length_y have value=3.0
        assert 'value=3.0' in tube_code, "Tube should have value=3.0 defaults"
        assert tube_code.count('value=3.0') == 2, "Tube should have exactly 2 value=3.0 entries (length_x + length_y)"
        
        # Verify old defaults (6.0) are gone
        assert 'value=6.0' not in tube_code, "Old tube default 6.0 should be removed"

    def test_tube_semantic_alignment(self):
        """
        Verify tube labels semantically match behavior.
        
        Gate G Requirement: Directional naming (X, Y) is consistent
        """
        with open('app.py', 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Find Tube section
        tube_start = source.find('st.caption("Tube Dimensions")')
        tube_end = source.find('st.caption("Opening Dimensions")', tube_start)
        tube_code = source[tube_start:tube_end]
        
        # Verify X and Y labels exist
        assert '"Length X (m)"' in tube_code, "Length X label missing"
        assert '"Length Y (m)"' in tube_code, "Length Y label missing"
        
        # Verify help text references correct directions
        assert 'Outer dimension in X direction' in tube_code, "Length X help text should reference X direction"
        assert 'Outer dimension in Y direction' in tube_code, "Length Y help text should reference Y direction"
        
        # Verify variable names match semantics (length_x, length_y)
        assert 'length_x = st.number_input' in tube_code, "length_x variable should exist"
        assert 'length_y = st.number_input' in tube_code, "length_y variable should exist"


class TestGateGConsistency:
    """Test consistency between sidebar.py and app.py runtime paths."""

    def test_both_runtime_paths_have_same_i_section_defaults(self):
        """
        Verify sidebar.py and app.py have identical I-section defaults.
        
        Gate G Requirement: Both runtime paths must be consistent
        """
        import inspect
        import src.ui.sidebar
        
        sidebar_source = inspect.getsource(src.ui.sidebar)
        
        with open('app.py', 'r', encoding='utf-8') as f:
            app_source = f.read()
        
        # Both should have I-Section section with value=3.0 defaults
        assert 'st.caption("I-Section Dimensions")' in sidebar_source, "sidebar missing I-Section section"
        assert 'st.caption("I-Section Dimensions")' in app_source, "app.py missing I-Section section"
        
        # Extract I-section code blocks (extend window to capture both inputs)
        sidebar_i_start = sidebar_source.find('st.caption("I-Section Dimensions")')
        sidebar_i_section = sidebar_source[sidebar_i_start:sidebar_i_start + 700]
        
        app_i_start = app_source.find('st.caption("I-Section Dimensions")')
        app_i_section = app_source[app_i_start:app_i_start + 700]
        
        # Both should have 2 occurrences of value=3.0 in I-section
        assert sidebar_i_section.count('value=3.0') == 2, f"sidebar I-section should have 2 value=3.0, found {sidebar_i_section.count('value=3.0')}"
        assert app_i_section.count('value=3.0') == 2, f"app.py I-section should have 2 value=3.0, found {app_i_section.count('value=3.0')}"

    def test_both_runtime_paths_have_same_tube_defaults(self):
        """
        Verify sidebar.py and app.py have identical tube defaults.
        
        Gate G Requirement: Both runtime paths must be consistent
        """
        import inspect
        import src.ui.sidebar
        
        sidebar_source = inspect.getsource(src.ui.sidebar)
        
        with open('app.py', 'r', encoding='utf-8') as f:
            app_source = f.read()
        
        # Both should have Tube section with value=3.0 defaults
        assert 'st.caption("Tube Dimensions")' in sidebar_source, "sidebar missing Tube section"
        assert 'st.caption("Tube Dimensions")' in app_source, "app.py missing Tube section"
        
        # Extract Tube code blocks (extend window to capture both inputs)
        sidebar_tube_start = sidebar_source.find('st.caption("Tube Dimensions")')
        sidebar_tube_section = sidebar_source[sidebar_tube_start:sidebar_tube_start + 700]
        
        app_tube_start = app_source.find('st.caption("Tube Dimensions")')
        app_tube_section = app_source[app_tube_start:app_tube_start + 700]
        
        # Both should have 2 occurrences of value=3.0 in Tube section
        assert sidebar_tube_section.count('value=3.0') == 2, f"sidebar Tube should have 2 value=3.0, found {sidebar_tube_section.count('value=3.0')}"
        assert app_tube_section.count('value=3.0') == 2, f"app.py Tube should have 2 value=3.0, found {app_tube_section.count('value=3.0')}"


class TestGateGDocumentedBehavior:
    """
    Test documented behavior change from Gate G specification.
    
    Before Gate G:
    - I-section: flange_width=6.0m, web_length=8.0m
    - Tube: length_x=6.0m, length_y=6.0m
    
    After Gate G:
    - I-section: flange_width=3.0m, web_length=3.0m  (more realistic for typical cores)
    - Tube: length_x=3.0m, length_y=3.0m  (more realistic for typical cores)
    """

    def test_gate_g_defaults_are_more_realistic_than_old_defaults(self):
        """
        Verify new 3.0m × 3.0m defaults are more realistic than old 6.0m/8.0m.
        
        Design Rationale:
        - Typical HK residential core walls: 2.5m to 4.0m dimensions
        - Old defaults (6m × 8m I-section, 6m × 6m tube) were oversized for most projects
        - New 3.0m × 3.0m defaults are closer to typical preliminary design starting point
        """
        with open('app.py', 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Verify new defaults are present
        assert source.count('value=3.0') >= 4, "Should have at least 4 value=3.0 entries (I-section: 2, Tube: 2)"
        
        # Verify old oversized defaults are gone
        i_section_start = source.find('st.caption("I-Section Dimensions")')
        i_section_end = source.find('else:  # TUBE_WITH_OPENINGS', i_section_start)
        i_section_code = source[i_section_start:i_section_end]
        
        assert 'value=6.0' not in i_section_code, "Old I-section flange default 6.0 should be removed"
        assert 'value=8.0' not in i_section_code, "Old I-section web default 8.0 should be removed"
        
        # Verify tube section
        tube_start = source.find('st.caption("Tube Dimensions")')
        tube_end = source.find('st.caption("Opening Dimensions")', tube_start)
        tube_code = source[tube_start:tube_end]
        
        assert 'value=6.0' not in tube_code, "Old tube default 6.0 should be removed"
