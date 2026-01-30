"""Reusable UI components for PrelimStruct."""

import streamlit as st
from typing import Literal, Union, Optional
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


def render_status_badge(status: str, utilization: float = 0.0) -> None:
    """Render status badge inline using st.markdown."""
    st.markdown(get_status_badge(status, utilization), unsafe_allow_html=True)


def metric_card(
    title: str,
    value: Union[str, float],
    unit: str = "",
    delta: Optional[float] = None,
    delta_color: Literal["normal", "inverse", "off"] = "normal"
) -> None:
    """Render themed metric card using Streamlit's st.metric.
    
    Args:
        title: Card title/label
        value: Main value to display
        unit: Unit suffix (e.g., "kN", "mm", "MPa")
        delta: Optional change value
        delta_color: "normal" (green up, red down), "inverse", or "off"
    """
    # Format value with unit
    if isinstance(value, (int, float)):
        if unit:
            value_str = f"{value:.2f}" if isinstance(value, float) else str(value)
        else:
            value_str = f"{value:.2f}" if isinstance(value, float) else str(value)
    else:
        value_str = str(value)
    
    if unit:
        value_str = f"{value_str} {unit}"
    
    st.metric(
        label=title,
        value=value_str,
        delta=delta,
        delta_color=delta_color
    )
