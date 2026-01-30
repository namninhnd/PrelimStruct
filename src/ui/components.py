"""Reusable UI components for PrelimStruct."""

from src.ui.theme import GEMINI_TOKENS


def get_status_badge(status: str, utilization: float = 0.0) -> str:
    """Generate HTML status badge based on status and utilization.
    
    Args:
        status: Status string - "FAIL", "WARNING", "PENDING", or other (OK)
        utilization: Utilization ratio (0.0 to 1.0+)
        
    Returns:
        HTML span with styled badge
    """
    colors = GEMINI_TOKENS["colors"]
    
    # Determine label and background color
    if status == "FAIL" or utilization > 1.0:
        label = "FAIL"
        bg = colors["error"]  # #f28b82
    elif status == "WARNING" or utilization > 0.85:
        label = "WARN"
        bg = colors["warning"]  # #fdd663
    elif status == "PENDING":
        label = "--"
        bg = colors["text_secondary"]  # #9aa0a6
    else:
        label = "OK"
        bg = colors["success"]  # #81c995
    
    return f'<span style="background-color:{bg};color:{colors["bg_base"]};padding:4px 12px;border-radius:12px;font-size:12px;font-weight:600;">{label}</span>'
