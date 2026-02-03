"""Tests for FEM visualization module."""
import pytest

from src.fem.fem_engine import FEMModel, Node, Element, ElementType, SurfaceLoad
from src.fem.visualization import _classify_elements


def test_classify_elements_separates_secondary_beams() -> None:
    """Test that _classify_elements differentiates primary vs secondary beams."""
    model = FEMModel()
    
    # Create nodes for horizontal beams at same elevation
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=3.0))
    model.add_node(Node(tag=2, x=6.0, y=0.0, z=3.0))
    model.add_node(Node(tag=3, x=0.0, y=5.0, z=3.0))
    model.add_node(Node(tag=4, x=6.0, y=5.0, z=3.0))
    
    # Add primary beam (section_tag=1)
    model.add_element(Element(
        tag=1,
        element_type=ElementType.ELASTIC_BEAM,
        node_tags=[1, 2],
        material_tag=1,
        section_tag=1,  # Primary beam
    ))
    
    # Add secondary beam (section_tag=2)
    model.add_element(Element(
        tag=2,
        element_type=ElementType.ELASTIC_BEAM,
        node_tags=[3, 4],
        material_tag=1,
        section_tag=2,  # Secondary beam
    ))
    
    # Classify elements
    classification = _classify_elements(model)
    
    # Verify primary beam is in "beams" category
    assert 1 in classification["beams"], "Primary beam should be in 'beams' category"
    assert 1 not in classification["beams_secondary"], "Primary beam should NOT be in 'beams_secondary'"
    
    # Verify secondary beam is in "beams_secondary" category
    assert 2 in classification["beams_secondary"], "Secondary beam should be in 'beams_secondary' category"
    assert 2 not in classification["beams"], "Secondary beam should NOT be in 'beams' category"


def test_classify_elements_handles_columns() -> None:
    """Test that vertical elements are classified as columns."""
    model = FEMModel()
    
    # Create nodes for vertical column
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=0.0))
    model.add_node(Node(tag=2, x=0.0, y=0.0, z=3.0))
    
    # Add column element
    model.add_element(Element(
        tag=1,
        element_type=ElementType.ELASTIC_BEAM,
        node_tags=[1, 2],
        material_tag=1,
        section_tag=3,
    ))
    
    classification = _classify_elements(model)
    
    assert 1 in classification["columns"], "Vertical element should be classified as column"
    assert 1 not in classification["beams"], "Column should not be in beams"
    assert 1 not in classification["beams_secondary"], "Column should not be in secondary beams"


def test_classify_elements_handles_coupling_beams() -> None:
    """Test that coupling beams are classified separately."""
    model = FEMModel()
    
    # Create nodes
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=3.0))
    model.add_node(Node(tag=2, x=2.0, y=0.0, z=3.0))
    
    # Add coupling beam
    model.add_element(Element(
        tag=1,
        element_type=ElementType.COUPLING_BEAM,
        node_tags=[1, 2],
        material_tag=1,
        section_tag=None,
    ))
    
    classification = _classify_elements(model)
    
    assert 1 in classification["coupling_beams"], "Coupling beam should be in 'coupling_beams'"
    assert 1 not in classification["beams"], "Coupling beam should not be in 'beams'"
    assert 1 not in classification["beams_secondary"], "Coupling beam should not be in 'beams_secondary'"


def test_classify_elements_separates_slabs_from_core_walls() -> None:
    """Test that SHELL_MITC4 elements are classified into slabs vs core walls by section_tag."""
    model = FEMModel()
    
    # Create nodes for a simple slab quad and core wall quad
    # Slab quad nodes (horizontal at z=3.0)
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=3.0))
    model.add_node(Node(tag=2, x=6.0, y=0.0, z=3.0))
    model.add_node(Node(tag=3, x=6.0, y=5.0, z=3.0))
    model.add_node(Node(tag=4, x=0.0, y=5.0, z=3.0))
    
    # Core wall quad nodes (different location)
    model.add_node(Node(tag=5, x=10.0, y=0.0, z=3.0))
    model.add_node(Node(tag=6, x=12.0, y=0.0, z=3.0))
    model.add_node(Node(tag=7, x=12.0, y=2.0, z=3.0))
    model.add_node(Node(tag=8, x=10.0, y=2.0, z=3.0))
    
    # Add slab element (section_tag=5)
    model.add_element(Element(
        tag=1,
        element_type=ElementType.SHELL_MITC4,
        node_tags=[1, 2, 3, 4],
        material_tag=1,
        section_tag=5,  # Slab section tag
    ))
    
    # Add core wall element (section_tag=4)
    model.add_element(Element(
        tag=2,
        element_type=ElementType.SHELL_MITC4,
        node_tags=[5, 6, 7, 8],
        material_tag=1,
        section_tag=4,  # Core wall section tag
    ))
    
    # Classify elements
    classification = _classify_elements(model)
    
    # Verify slab element is in "slabs" category
    assert 1 in classification["slabs"], "Slab element (section_tag=5) should be in 'slabs' category"
    assert 1 not in classification["core_walls"], "Slab element should NOT be in 'core_walls'"
    
    # Verify core wall element is in "core_walls" category
    assert 2 in classification["core_walls"], "Core wall element (section_tag=4) should be in 'core_walls' category"
    assert 2 not in classification["slabs"], "Core wall element should NOT be in 'slabs'"


def test_plan_view_renders_slab_quads() -> None:
    """Test that create_plan_view renders slab quad elements."""
    from src.fem.visualization import create_plan_view
    
    model = FEMModel()
    
    # Create a simple slab quad at floor level z=3.0
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=3.0))
    model.add_node(Node(tag=2, x=6.0, y=0.0, z=3.0))
    model.add_node(Node(tag=3, x=6.0, y=5.0, z=3.0))
    model.add_node(Node(tag=4, x=0.0, y=5.0, z=3.0))
    
    # Add slab element
    model.add_element(Element(
        tag=1,
        element_type=ElementType.SHELL_MITC4,
        node_tags=[1, 2, 3, 4],
        material_tag=1,
        section_tag=5,
    ))
    
    # Add section definition (required for thickness extraction)
    model.add_section(5, {
        'section_type': 'ElasticMembranePlateSection',
        'tag': 5,
        'E': 25e9,  # ~40 MPa concrete
        'nu': 0.2,
        'h': 0.15,  # 150mm thickness
        'rho': 2500,
    })
    
    # Create plan view at this floor
    fig = create_plan_view(model, floor_elevation=3.0)
    
    # Verify that the figure contains slab-related traces
    trace_names = [trace.name for trace in fig.data]
    assert 'Slabs' in trace_names or any('Slab' in name for name in trace_names), \
        "Plan view should contain slab traces"
    
    # Check that at least one trace has slab data
    slab_traces = [t for t in fig.data if t.name and 'Slab' in t.name]
    assert len(slab_traces) > 0, "Should have at least one slab trace"


def test_slab_hover_tooltip_includes_thickness() -> None:
    """Test that slab hover tooltips include thickness information."""
    from src.fem.visualization import create_plan_view
    
    model = FEMModel()
    
    # Create slab quad
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=3.0))
    model.add_node(Node(tag=2, x=6.0, y=0.0, z=3.0))
    model.add_node(Node(tag=3, x=6.0, y=5.0, z=3.0))
    model.add_node(Node(tag=4, x=0.0, y=5.0, z=3.0))
    
    model.add_element(Element(
        tag=60001,
        element_type=ElementType.SHELL_MITC4,
        node_tags=[1, 2, 3, 4],
        material_tag=1,
        section_tag=5,
    ))
    
    # Add section with specific thickness
    thickness = 0.15  # 150mm
    model.add_section(5, {
        'section_type': 'ElasticMembranePlateSection',
        'tag': 5,
        'E': 25e9,
        'nu': 0.2,
        'h': thickness,
        'rho': 2500,
    })
    
    # Create plan view
    fig = create_plan_view(model, floor_elevation=3.0)
    
    # Find slab traces
    slab_traces = [t for t in fig.data if t.name and 'Slab' in t.name]
    assert len(slab_traces) > 0, "Should have slab traces"
    
    # Check that tooltip text includes thickness
    for trace in slab_traces:
        if hasattr(trace, 'text') and trace.text:
            # text can be a string or list of strings
            text_content = trace.text if isinstance(trace.text, str) else ' '.join(trace.text)
            assert 'Thickness' in text_content or '0.15' in text_content, \
                "Slab tooltip should include thickness information"
    
    
def test_slab_tooltip_shows_surface_load() -> None:
    """Test that slab hover tooltips include surface load in kPa."""
    from src.fem.visualization import create_plan_view
    
    model = FEMModel()
    
    # Create slab quad
    model.add_node(Node(tag=1, x=0.0, y=0.0, z=3.0))
    model.add_node(Node(tag=2, x=6.0, y=0.0, z=3.0))
    model.add_node(Node(tag=3, x=6.0, y=5.0, z=3.0))
    model.add_node(Node(tag=4, x=0.0, y=5.0, z=3.0))
    
    model.add_element(Element(
        tag=1,
        element_type=ElementType.SHELL_MITC4,
        node_tags=[1, 2, 3, 4],
        material_tag=1,
        section_tag=5,
    ))
    
    # Add section
    model.add_section(5, {
        'section_type': 'ElasticMembranePlateSection',
        'tag': 5,
        'E': 25e9,
        'nu': 0.2,
        'h': 0.2,
        'rho': 2500,
    })
    
    # Add surface load (6500 Pa = 6.5 kPa)
    model.add_surface_load(SurfaceLoad(
        element_tag=1,
        pressure=6500.0
    ))
    
    # Create plan view
    fig = create_plan_view(model, floor_elevation=3.0)
    
    # Verify tooltip contains "6.50 kPa"
    slab_traces = [t for t in fig.data if t.name and 'Slab' in t.name]
    assert len(slab_traces) > 0
    
    found_load = False
    for trace in slab_traces:
        if hasattr(trace, 'text') and trace.text:
            text = trace.text if isinstance(trace.text, str) else ' '.join(trace.text)
            if '6.50 kPa' in text and 'Surface Load' in text:
                found_load = True
                break
    
    assert found_load, "Tooltip should display 'Surface Load: 6.50 kPa'"


def test_model_statistics_includes_surface_loads() -> None:
    """Test that get_model_statistics counts surface loads."""
    from src.fem.visualization import get_model_statistics
    
    model = FEMModel()
    
    # Add dummy elements and loads
    model.add_node(Node(tag=1, x=0, y=0, z=0))
    model.add_node(Node(tag=2, x=1, y=0, z=0))
    model.add_element(Element(
        tag=1, element_type=ElementType.SHELL_MITC4,
        node_tags=[1, 2, 2, 1], material_tag=1, section_tag=5
    ))
    
    model.add_surface_load(SurfaceLoad(element_tag=1, pressure=1000.0))
    model.add_surface_load(SurfaceLoad(element_tag=1, pressure=2000.0))
    
    stats = get_model_statistics(model)
    
    assert stats['n_surface_loads'] == 2, "Should count 2 surface loads"
