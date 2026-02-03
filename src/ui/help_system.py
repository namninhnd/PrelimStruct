"""
Interactive Help and Annotation System for PrelimStruct

Provides context-sensitive help, tooltips, and guided tutorials
similar to Agentation but built natively for Streamlit.
"""

import streamlit as st
from typing import Optional, Dict, List, Literal
from dataclasses import dataclass
from src.ui.theme import GEMINI_TOKENS


@dataclass
class HelpTopic:
    """Structured help topic with title, content, and context."""
    id: str
    title: str
    content: str
    context: str  # Section where this help applies
    references: List[str] = None  # HK Code clauses, etc.

    def __post_init__(self):
        if self.references is None:
            self.references = []


class HelpSystem:
    """Main help system manager for PrelimStruct."""

    def __init__(self):
        self.topics: Dict[str, HelpTopic] = {}
        self.current_context: Optional[str] = None
        self._load_help_content()

    def _load_help_content(self):
        """Load all help topics (populated from help_content.py)."""
        from src.ui.help_content import HELP_TOPICS
        self.topics = {topic.id: topic for topic in HELP_TOPICS}

    def set_context(self, context: str):
        """Set current UI context for contextual help."""
        self.current_context = context

    def get_context_topics(self) -> List[HelpTopic]:
        """Get help topics relevant to current context."""
        if not self.current_context:
            return []
        return [t for t in self.topics.values() if t.context == self.current_context]

    def render_floating_help_button(self):
        """Render floating help button (bottom-right corner)."""
        colors = GEMINI_TOKENS["colors"]

        # Custom CSS for floating button
        st.markdown(f"""
        <style>
            .help-float-container {{
                position: fixed;
                bottom: 24px;
                right: 24px;
                z-index: 9999;
            }}
            .help-float-button {{
                background: {colors["accent_blue"]};
                color: {colors["bg_base"]};
                border: none;
                border-radius: 50%;
                width: 56px;
                height: 56px;
                font-size: 24px;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s ease;
            }}
            .help-float-button:hover {{
                background: {colors["accent_purple"]};
                box-shadow: 0 6px 16px rgba(0,0,0,0.3);
                transform: scale(1.05);
            }}
        </style>
        """, unsafe_allow_html=True)

        # Initialize help state if not exists
        if "help_panel_open" not in st.session_state:
            st.session_state.help_panel_open = False

        # Create columns for button placement (right-aligned)
        col1, col2 = st.columns([10, 1])

        with col2:
            if st.button("❓", key="help_toggle", help="Toggle Help Panel"):
                st.session_state.help_panel_open = not st.session_state.help_panel_open

    def render_help_panel(self):
        """Render help panel sidebar when activated."""
        if not st.session_state.get("help_panel_open", False):
            return

        colors = GEMINI_TOKENS["colors"]

        with st.sidebar:
            st.markdown(f"""
            <div style="background:{colors['bg_elevated']};padding:16px;border-radius:8px;margin-bottom:16px;">
                <h2 style="color:{colors['accent_blue']};margin:0;font-size:20px;">
                    📚 Help & Documentation
                </h2>
            </div>
            """, unsafe_allow_html=True)

            # Context-specific help
            context_topics = self.get_context_topics()

            if context_topics:
                st.markdown(f"**Current Section: {self.current_context or 'General'}**")
                for topic in context_topics:
                    with st.expander(f"ℹ️ {topic.title}"):
                        st.markdown(topic.content)
                        if topic.references:
                            st.caption("**References:**")
                            for ref in topic.references:
                                st.caption(f"• {ref}")
            else:
                st.info("Navigate to a section to see contextual help")

            st.divider()

            # Quick reference links
            st.markdown("### 🔗 Quick References")
            st.markdown("""
            - [HK Code 2013](https://www.bd.gov.hk/en/resources/codes-and-references/code-and-design-manuals/index_code_structural.html)
            - [OpenSeesPy Docs](https://openseespydoc.readthedocs.io/)
            - [Project Documentation](CLAUDE.md)
            """)

            st.divider()

            # Tutorial mode toggle
            if st.checkbox("🎓 Tutorial Mode", key="tutorial_mode"):
                st.success("Tutorial mode activated! Extra guidance will be shown throughout the app.")

    def render_tooltip(self, term: str, definition: str,
                      icon: str = "ℹ️") -> str:
        """Generate inline tooltip HTML for technical terms.

        Args:
            term: Technical term to annotate
            definition: Tooltip explanation
            icon: Icon to show (default: info)

        Returns:
            HTML string with tooltip
        """
        colors = GEMINI_TOKENS["colors"]

        tooltip_html = f"""
        <span class="tooltip-container" style="position:relative;display:inline-block;">
            <span style="color:{colors['accent_blue']};cursor:help;border-bottom:1px dotted {colors['accent_blue']};">
                {term} {icon}
            </span>
            <span class="tooltip-text" style="
                visibility:hidden;
                width:250px;
                background-color:{colors['bg_elevated']};
                color:{colors['text_primary']};
                text-align:left;
                border-radius:6px;
                padding:8px;
                position:absolute;
                z-index:1000;
                bottom:125%;
                left:50%;
                margin-left:-125px;
                opacity:0;
                transition:opacity 0.3s;
                box-shadow:0 4px 12px rgba(0,0,0,0.2);
                font-size:13px;
                line-height:1.4;
            ">
                {definition}
            </span>
        </span>
        <style>
            .tooltip-container:hover .tooltip-text {{
                visibility: visible;
                opacity: 1;
            }}
        </style>
        """
        return tooltip_html

    def show_section_guide(self, section: Literal[
        "geometry", "loads", "materials", "fem", "design", "results"
    ]):
        """Show contextual guide for specific section.

        Args:
            section: Section identifier
        """
        if not st.session_state.get("tutorial_mode", False):
            return

        guides = {
            "geometry": """
            **📐 Geometry Input Guide:**
            1. Set building dimensions (width, depth, height)
            2. Define floor heights and number of stories
            3. Configure structural grid spacing
            4. Select core wall configuration (I-section, C-shaped, etc.)
            """,
            "loads": """
            **⚖️ Load Input Guide:**
            1. Select occupancy type (determines live loads per HK Code)
            2. Enter imposed loads (kPa)
            3. Define wind exposure and terrain category
            4. Review load combinations (ULS and SLS)
            """,
            "materials": """
            **🧱 Materials Guide:**
            1. Select concrete grade (C30-C60)
            2. Choose reinforcement grade (typically Grade 500)
            3. Set exposure class (affects cover requirements)
            4. Review material properties
            """,
            "fem": """
            **🔬 FEM Analysis Guide:**
            1. Build model from geometry inputs
            2. Apply loads and boundary conditions
            3. Run analysis (gravity + lateral)
            4. Review results (displacements, forces, reactions)
            5. Check serviceability limits (deflection, drift)
            """,
            "design": """
            **📝 Design Checks Guide:**
            1. Select member to design (slab, beam, column, wall)
            2. Review FEM forces for critical sections
            3. Check HK Code compliance
            4. Review reinforcement requirements
            5. Generate design summary
            """,
            "results": """
            **📊 Results Review Guide:**
            1. Check FEM analysis status
            2. Review member utilization ratios
            3. Identify critical locations
            4. Compare FEM vs. Simplified methods
            5. Export report or results data
            """
        }

        if section in guides:
            st.info(guides[section])

    def render_technical_annotation(self, label: str, value: any,
                                    tooltip: Optional[str] = None,
                                    hk_clause: Optional[str] = None):
        """Render annotated technical value with optional tooltip and code reference.

        Args:
            label: Parameter label
            value: Parameter value
            tooltip: Optional explanation
            hk_clause: Optional HK Code clause reference
        """
        colors = GEMINI_TOKENS["colors"]

        # Build label with tooltip if provided
        if tooltip:
            label_html = self.render_tooltip(label, tooltip)
        else:
            label_html = label

        # Add HK Code reference if provided
        if hk_clause:
            label_html += f' <span style="color:{colors["text_secondary"]};font-size:11px;">({hk_clause})</span>'

        # Render metric
        st.markdown(f"{label_html}: **{value}**", unsafe_allow_html=True)


# Singleton instance
_help_system: Optional[HelpSystem] = None


def get_help_system() -> HelpSystem:
    """Get or create singleton HelpSystem instance."""
    global _help_system
    if _help_system is None:
        _help_system = HelpSystem()
    return _help_system


# Convenience functions for quick access
def help_tooltip(term: str, definition: str) -> str:
    """Quick tooltip generation."""
    return get_help_system().render_tooltip(term, definition)


def set_help_context(context: str):
    """Set current help context."""
    get_help_system().set_context(context)


def show_help_button():
    """Show floating help button."""
    get_help_system().render_floating_help_button()


def show_help_panel():
    """Show help panel if activated."""
    get_help_system().render_help_panel()


def show_section_guide(section: str):
    """Show section guide if tutorial mode is on."""
    get_help_system().show_section_guide(section)


def annotate(label: str, value: any, tooltip: str = None, hk_clause: str = None):
    """Quick annotation for technical values."""
    get_help_system().render_technical_annotation(label, value, tooltip, hk_clause)
