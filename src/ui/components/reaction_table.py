import pandas as pd
import streamlit as st
import io
from typing import Dict, Optional, Union
from src.fem.solver import AnalysisResult

class ReactionTable:
    """Component to display and export FEM reaction forces."""

    def __init__(self, results: Union[AnalysisResult, Dict[str, AnalysisResult]]):
        """
        Initialize with analysis results.
        
        Args:
            results: Single AnalysisResult or dict of {case_name: AnalysisResult}
        """
        if isinstance(results, AnalysisResult):
            self.results = {"Load Case 1": results}
        else:
            self.results = results

    def _get_dataframe(self, case_name: str) -> pd.DataFrame:
        """Convert results for a specific case to DataFrame."""
        result = self.results.get(case_name)
        if not result or not result.node_reactions:
            return pd.DataFrame()

        data = []
        # result.node_reactions is Dict[int, List[float]] -> [Fx, Fy, Fz, Mx, My, Mz]
        for node_id, forces in result.node_reactions.items():
            row = {
                "Node": node_id,
                "Fx (kN)": forces[0] / 1000.0,
                "Fy (kN)": forces[1] / 1000.0,
                "Fz (kN)": forces[2] / 1000.0,
                "Mx (kNm)": forces[3] / 1000.0,
                "My (kNm)": forces[4] / 1000.0,
                "Mz (kNm)": forces[5] / 1000.0,
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        if not df.empty:
            df = df.set_index("Node").sort_index()
            
            # Calculate totals
            totals = df.sum()
            totals.name = "TOTAL"
            # Append total row
            df.loc["TOTAL"] = totals
            
        return df

    def render(self):
        """Render the component in Streamlit."""
        st.markdown("### Reaction Forces")

        if not self.results:
            st.info("No analysis results available.")
            return

        # Load Case Selector
        case_options = list(self.results.keys())
        selected_case = st.selectbox(
            "Load Case", 
            options=case_options,
            key="reaction_table_case_selector"
        )

        if not selected_case:
            return

        df = self._get_dataframe(selected_case)
        
        if df.empty:
            st.info(f"No reaction forces found for {selected_case}.")
            return

        # Display table
        st.dataframe(df.style.format("{:.2f}"), use_container_width=True)
        
        # Export Buttons
        col1, col2 = st.columns(2)
        
        # CSV Export
        csv = df.to_csv().encode('utf-8')
        col1.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"reactions_{selected_case.replace(' ', '_')}.csv",
            mime="text/csv",
            key=f'download-csv-{selected_case}'
        )
        
        # Excel Export
        buffer = io.BytesIO()
        try:
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Reactions')
            
            col2.download_button(
                label="Download Excel",
                data=buffer.getvalue(),
                file_name=f"reactions_{selected_case.replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f'download-excel-{selected_case}'
            )
        except Exception as e:
            col2.error(f"Excel export failed: {str(e)}")
