"""State-management tests for FEM view helpers."""

import streamlit as st

from src.ui.views.fem_views import _clear_analysis_state


def test_clear_analysis_state_removes_combination_cache():
    st.session_state["fem_preview_analysis_result"] = object()
    st.session_state["fem_analysis_results_dict"] = {"DL": object()}
    st.session_state["fem_combined_results_cache"] = {"LC1": object()}
    st.session_state["fem_analysis_status"] = "success"
    st.session_state["fem_analysis_message"] = "done"
    st.session_state["fem_inputs_locked"] = True

    _clear_analysis_state()

    assert "fem_preview_analysis_result" not in st.session_state
    assert "fem_analysis_results_dict" not in st.session_state
    assert "fem_combined_results_cache" not in st.session_state
    assert "fem_analysis_status" not in st.session_state
    assert "fem_analysis_message" not in st.session_state
    assert st.session_state["fem_inputs_locked"] is False
