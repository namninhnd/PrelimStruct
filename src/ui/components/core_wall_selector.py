import streamlit as st
from src.core.data_models import CoreWallConfig

def get_core_wall_svg(config: CoreWallConfig, selected: bool = False) -> str:
    """Generate SVG string for core wall configuration."""
    color = "#1E3A5F" if not selected else "#EF4444"
    stroke_width = "3"
    
    # Common SVG header
    svg_header = f'<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round">'
    svg_footer = '</svg>'
    
    path = ""
    
    if config == CoreWallConfig.I_SECTION:
        # I-Shape
        path = '<path d="M20,20 H80 V30 H60 V70 H80 V80 H20 V70 H40 V30 H20 Z" />'
        
    elif config == CoreWallConfig.TWO_C_FACING:
        # [ ]
        # Left C (facing right)
        path += '<path d="M45,20 H15 V80 H45" />'
        # Right C (facing left)
        path += '<path d="M55,20 H85 V80 H55" />'
        
    elif config == CoreWallConfig.TWO_C_BACK_TO_BACK:
        # ] [
        # Left C (facing left, web on right)
        path += '<path d="M15,20 H45 V80 H15" />'
        # Right C (facing right, web on left)
        path += '<path d="M85,20 H55 V80 H85" />'
        
    elif config == CoreWallConfig.TUBE_CENTER_OPENING:
        # Box with center opening
        # Outer box
        path += '<rect x="10" y="20" width="80" height="60" />'
        # Inner opening
        path += '<rect x="35" y="40" width="30" height="20" />'
        
    elif config == CoreWallConfig.TUBE_SIDE_OPENING:
        # Box with side opening (left side)
        # Outer C-shape forming box with opening
        path += '<path d="M10,20 H90 V80 H10 V60 H30 V40 H10 Z" />'
        
    return f'{svg_header}{path}{svg_footer}'

def render_core_wall_selector(current_config: CoreWallConfig) -> CoreWallConfig:
    """Render visual core wall selector using columns and cards."""
    
    st.markdown("""
    <style>
    .core-wall-card {
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
        transition: all 0.2s;
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: space-between;
    }
    .core-wall-card:hover {
        border-color: #2D5A87;
        background-color: #F8FAFC;
        transform: translateY(-2px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .core-wall-card.selected {
        border-color: #1E3A5F;
        background-color: #F1F5F9;
        border-width: 2px;
    }
    .core-wall-label {
        font-size: 12px;
        font-weight: 600;
        color: #1E3A5F;
        margin-top: 8px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.caption("Select Configuration")
    
    # Create 5 columns for the 5 configurations
    cols = st.columns(5)
    
    configs = [
        (CoreWallConfig.I_SECTION, "I-Section"),
        (CoreWallConfig.TWO_C_FACING, "Facing C"),
        (CoreWallConfig.TWO_C_BACK_TO_BACK, "Back-to-Back"),
        (CoreWallConfig.TUBE_CENTER_OPENING, "Tube Center"),
        (CoreWallConfig.TUBE_SIDE_OPENING, "Tube Side"),
    ]
    
    new_config = current_config
    
    for i, (config, label) in enumerate(configs):
        with cols[i]:
            is_selected = (config == current_config)
            
            # Use a container for visual grouping
            with st.container():
                svg = get_core_wall_svg(config, is_selected)
                
                # Render SVG using st.markdown with minimal margins
                st.markdown(f'<div style="text-align: center; margin-bottom: 5px;">{svg}</div>', unsafe_allow_html=True)
                
                # Use a button for selection
                # We use use_container_width to make it fill the column
                if st.button(label, key=f"core_select_{config.name}", use_container_width=True, 
                             type="primary" if is_selected else "secondary"):
                    new_config = config
                    # Force rerun happens automatically on button click
                    
    return new_config
