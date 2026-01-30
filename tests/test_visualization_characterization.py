"""Characterization tests for visualization functions before v3.6 refactoring.

These tests capture the current behavior of create_plan_view(), create_elevation_view(),
and create_3d_view() to ensure refactoring preserves functionality.
"""
from __future__ import annotations

import pytest

plotly = pytest.importorskip("plotly")

from plotly.graph_objects import Figure

from src.fem.fem_engine import Element, ElementType, FEMModel, Load, Node, UniformLoad
from src.fem.visualization import (
    VisualizationConfig,
    create_plan_view,
    create_elevation_view,
    create_3d_view,
)


@pytest.fixture
def simple_fem_model() -> FEMModel:
    """Create a simple FEM model for characterization tests."""
    model = FEMModel()
    
    # Base nodes (fixed)
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=2, x=6.0, y=0.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=3, x=0.0, y=5.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    model.add_node(Node(tag=4, x=6.0, y=5.0, z=0.0, restraints=[1, 1, 1, 1, 1, 1]))
    
    # Top nodes (free)
    model.add_node(Node(tag=5, x=0.0, y=0.0, z=3.0))
    model.add_node(Node(tag=6, x=6.0, y=0.0, z=3.0))
    model.add_node(Node(tag=7, x=0.0, y=5.0, z=3.0))
    model.add_node(Node(tag=8, x=6.0, y=5.0, z=3.0))
    
    # Columns
    model.add_element(Element(tag=1, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[1, 5], material_tag=1))
    model.add_element(Element(tag=2, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[2, 6], material_tag=1))
    model.add_element(Element(tag=3, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[3, 7], material_tag=1))
    model.add_element(Element(tag=4, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[4, 8], material_tag=1))
    
    # Beams (X-direction)
    model.add_element(Element(tag=5, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[5, 6], material_tag=2))
    model.add_element(Element(tag=6, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[7, 8], material_tag=2))
    
    # Beams (Y-direction)
    model.add_element(Element(tag=7, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[5, 7], material_tag=2))
    model.add_element(Element(tag=8, element_type=ElementType.ELASTIC_BEAM,
                              node_tags=[6, 8], material_tag=2))
    
    # Add loads
    model.add_load(Load(node_tag=5, load_values=[0.0, 0.0, -10.0, 0.0, 0.0, 0.0]))
    model.add_load(Load(node_tag=6, load_values=[0.0, 0.0, -10.0, 0.0, 0.0, 0.0]))
    
    return model


class TestPlanViewCharacterization:
    """Characterization tests for create_plan_view()."""
    
    def test_returns_valid_plotly_figure(self, simple_fem_model):
        """Test that create_plan_view returns a valid Plotly Figure."""
        config = VisualizationConfig()
        fig = create_plan_view(simple_fem_model, config, floor_elevation=0.0)
        
        assert fig is not None
        assert isinstance(fig, Figure)
        assert hasattr(fig, 'data')
        assert hasattr(fig, 'layout')
        assert len(fig.data) > 0  # Should have at least some traces
    
    def test_show_nodes_config(self, simple_fem_model):
        """Test show_nodes configuration option."""
        config_with_nodes = VisualizationConfig(show_nodes=True)
        config_without_nodes = VisualizationConfig(show_nodes=False)
        
        fig_with = create_plan_view(simple_fem_model, config_with_nodes, floor_elevation=3.0)
        fig_without = create_plan_view(simple_fem_model, config_without_nodes, floor_elevation=3.0)
        
        # With nodes should have more traces than without
        assert len(fig_with.data) >= len(fig_without.data)
    
    def test_show_supports_config(self, simple_fem_model):
        """Test show_supports configuration option."""
        config = VisualizationConfig(show_supports=True)
        fig = create_plan_view(simple_fem_model, config, floor_elevation=0.0)
        
        # Should render without errors when supports shown
        assert isinstance(fig, Figure)
    
    def test_show_loads_config(self, simple_fem_model):
        """Test show_loads configuration option."""
        config_with_loads = VisualizationConfig(show_loads=True)
        config_without_loads = VisualizationConfig(show_loads=False)
        
        fig_with = create_plan_view(simple_fem_model, config_with_loads, floor_elevation=3.0)
        fig_without = create_plan_view(simple_fem_model, config_without_loads, floor_elevation=3.0)
        
        # Both should render successfully
        assert isinstance(fig_with, Figure)
        assert isinstance(fig_without, Figure)
    
    def test_show_labels_config(self, simple_fem_model):
        """Test show_labels configuration option."""
        config = VisualizationConfig(show_labels=True)
        fig = create_plan_view(simple_fem_model, config, floor_elevation=3.0)
        
        assert isinstance(fig, Figure)
    
    def test_grid_spacing_config(self, simple_fem_model):
        """Test grid_spacing configuration option."""
        config = VisualizationConfig(grid_spacing=2.0)
        fig = create_plan_view(simple_fem_model, config, floor_elevation=3.0)
        
        assert isinstance(fig, Figure)
        assert fig.layout.xaxis.dtick == 2.0
        assert fig.layout.yaxis.dtick == 2.0


class TestElevationViewCharacterization:
    """Characterization tests for create_elevation_view()."""
    
    def test_returns_valid_plotly_figure(self, simple_fem_model):
        """Test that create_elevation_view returns a valid Plotly Figure."""
        config = VisualizationConfig()
        fig = create_elevation_view(simple_fem_model, config, view_direction="X")
        
        assert fig is not None
        assert isinstance(fig, Figure)
        assert hasattr(fig, 'data')
        assert hasattr(fig, 'layout')
        assert len(fig.data) > 0
    
    def test_view_direction_x(self, simple_fem_model):
        """Test elevation view with X direction."""
        config = VisualizationConfig()
        fig = create_elevation_view(simple_fem_model, config, view_direction="X")
        
        assert isinstance(fig, Figure)
    
    def test_view_direction_y(self, simple_fem_model):
        """Test elevation view with Y direction."""
        config = VisualizationConfig()
        fig = create_elevation_view(simple_fem_model, config, view_direction="Y")
        
        assert isinstance(fig, Figure)
    
    def test_show_nodes_config(self, simple_fem_model):
        """Test show_nodes configuration option."""
        config = VisualizationConfig(show_nodes=True)
        fig = create_elevation_view(simple_fem_model, config, view_direction="X")
        
        assert isinstance(fig, Figure)
    
    def test_show_supports_config(self, simple_fem_model):
        """Test show_supports configuration option."""
        config = VisualizationConfig(show_supports=True)
        fig = create_elevation_view(simple_fem_model, config, view_direction="X")
        
        assert isinstance(fig, Figure)
    
    def test_show_loads_config(self, simple_fem_model):
        """Test show_loads configuration option."""
        config = VisualizationConfig(show_loads=True)
        fig = create_elevation_view(simple_fem_model, config, view_direction="X")
        
        assert isinstance(fig, Figure)
    
    def test_show_labels_config(self, simple_fem_model):
        """Test show_labels configuration option."""
        config = VisualizationConfig(show_labels=True)
        fig = create_elevation_view(simple_fem_model, config, view_direction="X")
        
        assert isinstance(fig, Figure)


class TestThreeDViewCharacterization:
    """Characterization tests for create_3d_view()."""
    
    def test_returns_valid_plotly_figure(self, simple_fem_model):
        """Test that create_3d_view returns a valid Plotly Figure."""
        config = VisualizationConfig()
        fig = create_3d_view(simple_fem_model, config)
        
        assert fig is not None
        assert isinstance(fig, Figure)
        assert hasattr(fig, 'data')
        assert hasattr(fig, 'layout')
        assert len(fig.data) > 0
    
    def test_show_nodes_config(self, simple_fem_model):
        """Test show_nodes configuration option."""
        config_with_nodes = VisualizationConfig(show_nodes=True)
        config_without_nodes = VisualizationConfig(show_nodes=False)
        
        fig_with = create_3d_view(simple_fem_model, config_with_nodes)
        fig_without = create_3d_view(simple_fem_model, config_without_nodes)
        
        assert isinstance(fig_with, Figure)
        assert isinstance(fig_without, Figure)
        assert len(fig_with.data) >= len(fig_without.data)
    
    def test_show_supports_config(self, simple_fem_model):
        """Test show_supports configuration option."""
        config = VisualizationConfig(show_supports=True)
        fig = create_3d_view(simple_fem_model, config)
        
        assert isinstance(fig, Figure)
    
    def test_show_loads_config(self, simple_fem_model):
        """Test show_loads configuration option."""
        config = VisualizationConfig(show_loads=True)
        fig = create_3d_view(simple_fem_model, config)
        
        assert isinstance(fig, Figure)
    
    def test_show_labels_config(self, simple_fem_model):
        """Test show_labels configuration option."""
        config = VisualizationConfig(show_labels=True)
        fig = create_3d_view(simple_fem_model, config)
        
        assert isinstance(fig, Figure)
    
    def test_camera_perspective(self, simple_fem_model):
        """Test that 3D view has proper camera setup."""
        config = VisualizationConfig()
        fig = create_3d_view(simple_fem_model, config)
        
        # Should have scene layout with camera
        assert hasattr(fig.layout, 'scene')
        assert isinstance(fig, Figure)
