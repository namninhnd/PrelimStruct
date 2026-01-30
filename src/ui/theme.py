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
    """Generate Streamlit custom CSS from tokens.
    
    Implementation in Task 3.2.
    """
    return ""

def apply_theme() -> None:
    """Inject theme CSS into Streamlit app.
    
    Implementation in Task 3.2.
    """
    pass
