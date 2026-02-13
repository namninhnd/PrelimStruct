import streamlit as st
from src.core.data_models import CoreWallConfig

def get_core_wall_svg(config: CoreWallConfig, selected: bool = False) -> str:
    """Generate SVG string for core wall configuration."""
    color = "#1E3A5F" if not selected else "#EF4444"
    stroke_width = "3"
    
    svg_header = f'<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round">'
    svg_footer = '</svg>'
    
    path = ""
    
    if config == CoreWallConfig.I_SECTION:
        path = '<path d="M20,20 H80 V30 H60 V70 H80 V80 H20 V70 H40 V30 H20 Z" />'
    elif config == CoreWallConfig.TUBE_WITH_OPENINGS:
        path += '<rect x="10" y="20" width="80" height="60" />'
        path += '<rect x="35" y="40" width="30" height="20" />'
        
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
    
    cols = st.columns(2)
    
    configs = [
        (CoreWallConfig.I_SECTION, "I-Section"),
        (CoreWallConfig.TUBE_WITH_OPENINGS, "Tube with Openings"),
    ]
    
    new_config = current_config
    
    for i, (config, label) in enumerate(configs):
        with cols[i]:
            is_selected = (config == current_config)
            
            with st.container():
                svg = get_core_wall_svg(config, is_selected)
                
                st.markdown(f'<div style="text-align: center; margin-bottom: 5px;">{svg}</div>', unsafe_allow_html=True)
                
                if st.button(label, key=f"core_select_{config.name}", use_container_width=True, 
                             type="primary" if is_selected else "secondary"):
                    new_config = config
                    
    return new_config
