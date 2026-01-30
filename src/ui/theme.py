"""Gemini-style dark theme tokens for PrelimStruct v3.6."""

GEMINI_TOKENS = {
    "colors": {
        "bg_base": "#131314",        # Near-black background
        "bg_surface": "#1f1f1f",     # Elevated surface
        "bg_elevated": "#2d2e2f",    # Cards/panels
        "text_primary": "#e3e3e3",   # Main text
        "text_secondary": "#9aa0a6", # Secondary text
        "accent_blue": "#8ab4f8",    # Primary accent
        "accent_purple": "#c58af9",  # Secondary accent
        "success": "#81c995",        # Pass status
        "warning": "#fdd663",        # Warning status
        "error": "#f28b82",          # Error status
        "border_subtle": "rgba(255, 255, 255, 0.08)"
    },
    "typography": {
        "font_family": "'Inter', 'Segoe UI', system-ui, sans-serif",
        "font_mono": "'JetBrains Mono', 'Consolas', monospace",
        "size_xs": "12px",
        "size_sm": "14px",
        "size_base": "16px",
        "size_lg": "18px",
        "size_xl": "24px",
        "size_2xl": "32px",
        "weight_normal": 400,
        "weight_medium": 500,
        "weight_bold": 600
    },
    "spacing": {
        "xs": "4px",
        "sm": "8px",
        "md": "16px",
        "lg": "24px",
        "xl": "32px"
    },
    "radius": {
        "sm": "8px",
        "md": "12px",
        "lg": "16px",
        "xl": "20px"
    }
}

def get_streamlit_css() -> str:
    """Generate Streamlit custom CSS from tokens."""
    colors = GEMINI_TOKENS["colors"]
    typo = GEMINI_TOKENS["typography"]
    
    return f"""
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* Background */
    .stApp {{ background-color: {colors["bg_base"]}; }}
    .stSidebar {{ background-color: {colors["bg_surface"]}; }}
    
    /* Typography */
    .stApp {{ font-family: {typo["font_family"]}; color: {colors["text_primary"]}; }}
    h1, h2, h3 {{ color: {colors["text_primary"]}; font-weight: {typo["weight_medium"]}; }}
    
    /* Buttons */
    .stButton > button {{ 
        background-color: {colors["bg_elevated"]}; 
        border-radius: 12px;
        color: {colors["text_primary"]};
        border: 1px solid {colors["border_subtle"]};
    }}
    .stButton > button:hover {{ background-color: #3d3e3f; }}
    
    /* Cards/Metrics */
    div[data-testid="metric-container"] {{ 
        background-color: {colors["bg_elevated"]}; 
        border-radius: 12px; 
        padding: 16px; 
        border: 1px solid {colors["border_subtle"]};
    }}
    
    /* Inputs */
    .stTextInput input, .stNumberInput input, .stSelectbox select {{
        background-color: {colors["bg_elevated"]};
        border-color: {colors["border_subtle"]};
        color: {colors["text_primary"]};
    }}

    /* Custom Status Badges */
    .status-pass {{
        background-color: {colors["success"]};
        color: #000000;
        padding: 4px 12px;
        border-radius: 16px;
        font-weight: 600;
        font-size: 14px;
        display: inline-block;
    }}
    .status-fail {{
        background-color: {colors["error"]};
        color: #000000;
        padding: 4px 12px;
        border-radius: 16px;
        font-weight: 600;
        font-size: 14px;
        display: inline-block;
    }}
    .status-warning {{
        background-color: {colors["warning"]};
        color: #000000;
        padding: 4px 12px;
        border-radius: 16px;
        font-weight: 600;
        font-size: 14px;
        display: inline-block;
    }}
    .status-pending {{
        background-color: {colors["text_secondary"]};
        color: #000000;
        padding: 4px 12px;
        border-radius: 16px;
        font-weight: 600;
        font-size: 14px;
        display: inline-block;
    }}

    /* Custom Metric Card */
    .metric-card {{
        background-color: {colors["bg_elevated"]};
        border-radius: 12px;
        padding: 16px;
        color: {colors["text_primary"]};
        margin-bottom: 8px;
        border: 1px solid {colors["border_subtle"]};
    }}
    .metric-value {{
        font-size: 28px;
        font-weight: 700;
        margin: 0;
        color: {colors["accent_blue"]};
    }}
    .metric-label {{
        font-size: 14px;
        opacity: 0.8;
        margin: 0;
        color: {colors["text_secondary"]};
    }}

    /* Custom Section Headers */
    .section-header {{
        color: {colors["accent_blue"]};
        font-weight: 700;
        border-bottom: 2px solid {colors["border_subtle"]};
        padding-bottom: 8px;
        margin-bottom: 16px;
    }}

    /* Custom Element Summary Cards */
    .element-card {{
        background: {colors["bg_surface"]};
        border: 1px solid {colors["border_subtle"]};
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
    }}
    .element-card strong {{
        color: {colors["text_primary"]};
        font-size: 15px;
    }}
    .element-card small {{
        color: {colors["text_secondary"]};
    }}

    /* Hide Streamlit branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    """

def apply_theme() -> None:
    """Inject theme CSS into Streamlit app."""
    import streamlit as st
    st.markdown(f"<style>{get_streamlit_css()}</style>", unsafe_allow_html=True)
