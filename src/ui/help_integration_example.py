"""
PrelimStruct Help System - Integration Example

This file demonstrates how to integrate the help system into app.py
"""

import streamlit as st
from src.ui.help_system import (
    show_help_button,
    show_help_panel,
    set_help_context,
    show_section_guide,
    help_tooltip,
    annotate,
)
from src.ui.help_content import TOOLTIPS


# =============================================================================
# BASIC INTEGRATION (Minimal Changes to app.py)
# =============================================================================

def example_basic_integration():
    """Add to top of app.py main() function."""

    # 1. Add floating help button (renders in bottom-right corner)
    show_help_button()

    # 2. Add help panel (renders in sidebar when button clicked)
    show_help_panel()


# =============================================================================
# SECTION-SPECIFIC INTEGRATION
# =============================================================================

def example_geometry_section():
    """Example: Geometry Input Section with Help."""

    # Set context for contextual help
    set_help_context("geometry")

    # Show tutorial guide if enabled
    show_section_guide("geometry")

    st.header("📐 Building Geometry")

    # Basic inputs with tooltips
    st.markdown(
        help_tooltip("Building Width (X)", TOOLTIPS.get("effective_depth", "Building dimension in X-direction")),
        unsafe_allow_html=True
    )
    width = st.number_input("Width (m)", min_value=10.0, max_value=100.0, value=30.0)

    st.markdown(
        help_tooltip("Building Depth (Y)", "Building dimension in Y-direction"),
        unsafe_allow_html=True
    )
    depth = st.number_input("Depth (m)", min_value=10.0, max_value=100.0, value=25.0)


def example_materials_section():
    """Example: Materials Section with Annotations."""

    set_help_context("materials")
    show_section_guide("materials")

    st.header("🧱 Materials")

    # Annotated parameters with HK Code references
    fcu = st.selectbox("Concrete Grade", [30, 35, 40, 45, 50, 60], index=2)

    # Show annotated value with tooltip and code reference
    annotate(
        label="fcu",
        value=f"{fcu} MPa",
        tooltip=TOOLTIPS["fcu"],
        hk_clause="HK Code Cl 3.1.7"
    )

    # Calculate and annotate Ec
    Ec = 22 * (fcu / 20) ** 0.3
    annotate(
        label="Ec (Modulus of Elasticity)",
        value=f"{Ec:.1f} kN/mm²",
        tooltip=TOOLTIPS["Ec"],
        hk_clause="HK Code Cl 3.1.7"
    )


def example_loads_section():
    """Example: Loads Section with Contextual Help."""

    set_help_context("loads")
    show_section_guide("loads")

    st.header("⚖️ Loads")

    # Occupancy selection with inline help
    occupancy = st.selectbox(
        "Occupancy Type",
        ["Residential", "Office", "Retail", "Car Park"]
    )

    # Show tooltip for technical term
    st.markdown(
        help_tooltip("Pattern Loading Factor", TOOLTIPS.get("pattern_loading", "Reduction factor for non-simultaneous loading")),
        unsafe_allow_html=True
    )
    pattern_factor = st.slider("Pattern Factor", 0.0, 1.0, 0.5)


def example_fem_section():
    """Example: FEM Analysis Section with Help."""

    set_help_context("fem")
    show_section_guide("fem")

    st.header("🔬 FEM Analysis")

    # Analysis button with tooltip
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(
            help_tooltip("Run Analysis", "Builds FEM model and solves for displacements and forces"),
            unsafe_allow_html=True
        )
    with col2:
        if st.button("▶ Run Analysis"):
            st.success("Analysis complete!")


def example_results_section():
    """Example: Results Section with Annotated Values."""

    set_help_context("results")
    show_section_guide("results")

    st.header("📊 Results")

    # Display results with annotations
    st.subheader("Member Utilization")

    col1, col2, col3 = st.columns(3)

    with col1:
        annotate("Slab Util.", "0.72", tooltip="Demand/Capacity ratio for flexural design")

    with col2:
        annotate("Beam Util.", "0.89", tooltip="Demand/Capacity ratio for flexural design")

    with col3:
        annotate("Column Util.", "0.65", tooltip="Demand/Capacity ratio for axial + bending")

    # Drift check with annotation
    st.subheader("Serviceability Checks")
    drift = 0.0042  # Example: 4.2mm / 1000mm = 1/238
    drift_limit = 1/500

    annotate(
        label="Inter-story Drift",
        value=f"1/{int(1/drift)} {'✓' if drift < drift_limit else '✗'}",
        tooltip=TOOLTIPS.get("rigid_diaphragm", "Lateral displacement between floors"),
        hk_clause="HK Code Cl 7.3.2"
    )


# =============================================================================
# FULL EXAMPLE APP STRUCTURE
# =============================================================================

def example_full_app():
    """Complete example showing help system in full app."""

    st.set_page_config(page_title="PrelimStruct", layout="wide")

    # Initialize help system (add at top of main())
    show_help_button()
    show_help_panel()

    # Sidebar navigation
    with st.sidebar:
        st.title("PrelimStruct")
        section = st.radio(
            "Navigation",
            ["Geometry", "Loads", "Materials", "FEM Analysis", "Results"]
        )

    # Main content with section-specific help
    if section == "Geometry":
        example_geometry_section()
    elif section == "Loads":
        example_loads_section()
    elif section == "Materials":
        example_materials_section()
    elif section == "FEM Analysis":
        example_fem_section()
    elif section == "Results":
        example_results_section()


# =============================================================================
# INTEGRATION INSTRUCTIONS
# =============================================================================

"""
HOW TO INTEGRATE INTO app.py:

1. ADD IMPORTS (top of app.py):
   --------------------------------
   from src.ui.help_system import (
       show_help_button,
       show_help_panel,
       set_help_context,
       show_section_guide,
       help_tooltip,
       annotate,
   )
   from src.ui.help_content import TOOLTIPS


2. ADD HELP SYSTEM INITIALIZATION (in main() function, after st.set_page_config):
   -------------------------------------------------------------------------------
   def main():
       st.set_page_config(...)

       # Add help system
       show_help_button()
       show_help_panel()

       # ... rest of your app


3. ADD CONTEXTUAL HELP TO SECTIONS:
   ---------------------------------
   # Before each major section, set context:
   set_help_context("geometry")  # or "loads", "materials", "fem", "design", "results"
   show_section_guide("geometry")

   st.header("Your Section")
   # ... your section content


4. ADD TOOLTIPS TO TECHNICAL TERMS:
   ---------------------------------
   # Inline tooltip:
   st.markdown(
       help_tooltip("ULS", TOOLTIPS["ULS"]),
       unsafe_allow_html=True
   )

   # Or wrap input labels:
   st.markdown(help_tooltip("Concrete Grade (fcu)", TOOLTIPS["fcu"]), unsafe_allow_html=True)
   fcu = st.selectbox("", [30, 35, 40, 45, 50, 60])


5. ANNOTATE CALCULATED VALUES:
   ----------------------------
   # Show calculated values with tooltips and HK Code references:
   annotate(
       label="Ec",
       value=f"{Ec:.1f} kN/mm²",
       tooltip=TOOLTIPS["Ec"],
       hk_clause="HK Code Cl 3.1.7"
   )


6. TUTORIAL MODE:
   --------------
   # Tutorial mode is toggled by user in help panel
   # show_section_guide() automatically checks tutorial mode state
   # No additional code needed!


THAT'S IT! The help system is now fully integrated.
"""

if __name__ == "__main__":
    # Run example app
    example_full_app()
