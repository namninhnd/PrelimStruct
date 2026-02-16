"""
Beam Forces Table Component.

Displays beam forces at all 5 subdivision nodes (4 sub-elements per beam).
Shows forces for all beams on a selected floor with export capability.
"""

import pandas as pd
import streamlit as st
import io
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from src.fem.force_normalization import normalize_end_force
from src.ui.floor_labels import format_floor_label_from_floor_number


@dataclass
class BeamForceRow:
    """Force values at a single subdivision node."""
    beam_id: int
    floor: int
    node_index: int
    position: float
    x: float
    y: float
    N: float
    Vy: float
    Vz: float
    My: float
    Mz: float
    T: float


class BeamForcesTable:
    """Component to display beam forces at subdivision nodes."""

    @staticmethod
    def _display_end_force(force_i: float, force_j: float, force_type: str) -> float:
        return normalize_end_force(force_i, force_j, force_type)

    def __init__(
        self,
        model: Any,
        analysis_result: Any,
        force_type: str = "Mz",
        story_height: float = 3.0,
        load_case: str = "DL"
    ):
        self.model = model
        self.result = analysis_result
        self.force_type = force_type
        self.story_height = story_height
        self.load_case = load_case
        self._beam_data: Optional[pd.DataFrame] = None
        
    def _extract_beam_forces(self) -> pd.DataFrame:
        """Extract forces at all subdivision nodes for all beams."""
        if self._beam_data is not None:
            return self._beam_data
            
        if not self.result or not self.result.element_forces:
            return pd.DataFrame()
        
        parent_groups: Dict[int, List[Tuple[int, int]]] = {}
        
        for elem_id, elem_info in self.model.elements.items():
            geom = elem_info.geometry or {}
            parent_id = geom.get("parent_beam_id")
            if parent_id is not None:
                sub_index = geom.get("sub_element_index", 0)
                if parent_id not in parent_groups:
                    parent_groups[parent_id] = []
                parent_groups[parent_id].append((sub_index, elem_id))
        
        for parent_id in parent_groups:
            parent_groups[parent_id].sort(key=lambda x: x[0])
        
        rows = []
        
        for parent_id, sub_elements in parent_groups.items():
            if len(sub_elements) < 2:
                continue
            
            first_elem = self.model.elements.get(sub_elements[0][1])
            if not first_elem or len(first_elem.node_tags) < 2:
                continue
            
            first_node = self.model.nodes.get(first_elem.node_tags[0])
            if not first_node:
                continue
            
            floor = int(round(first_node.z / self.story_height)) if hasattr(first_node, 'z') else 0
            
            node_positions = []
            force_values = []
            
            for sub_idx, sub_elem_id in sub_elements:
                sub_elem = self.model.elements.get(sub_elem_id)
                if not sub_elem or len(sub_elem.node_tags) < 2:
                    continue
                    
                node_i_tag = sub_elem.node_tags[0]
                node_i = self.model.nodes.get(node_i_tag)
                
                forces = self.result.element_forces.get(sub_elem_id, {})
                
                if node_i and forces:
                    node_positions.append((node_i.x, node_i.y, node_i.z))
                    n_i = forces.get('N_i', 0) / 1000.0
                    force_values.append({
                        'N_i': n_i,
                        'Vy_i': forces.get('Vy_i', forces.get('V_i', 0)) / 1000.0,
                        'Vz_i': forces.get('Vz_i', 0) / 1000.0,
                        'My_i': -forces.get('My_i', forces.get('M_i', 0)) / 1000.0,
                        'Mz_i': -forces.get('Mz_i', 0) / 1000.0,
                        'T_i': -forces.get('T_i', 0) / 1000.0,
                    })
            
            if sub_elements:
                last_elem_id = sub_elements[-1][1]
                last_elem = self.model.elements.get(last_elem_id)
                if last_elem and len(last_elem.node_tags) >= 2:
                    node_j_tag = last_elem.node_tags[1]
                    node_j = self.model.nodes.get(node_j_tag)
                    forces = self.result.element_forces.get(last_elem_id, {})
                    
                    if node_j and forces:
                        node_positions.append((node_j.x, node_j.y, node_j.z))
                        n_i = forces.get('N_i', 0) / 1000.0
                        n_j = forces.get('N_j', 0) / 1000.0
                        vy_i = forces.get('Vy_i', forces.get('V_i', 0)) / 1000.0
                        vy_j = forces.get('Vy_j', forces.get('V_j', 0)) / 1000.0
                        vz_i = forces.get('Vz_i', 0) / 1000.0
                        vz_j = forces.get('Vz_j', 0) / 1000.0
                        my_i = forces.get('My_i', forces.get('M_i', 0)) / 1000.0
                        my_j = forces.get('My_j', forces.get('M_j', 0)) / 1000.0
                        mz_i = forces.get('Mz_i', 0) / 1000.0
                        mz_j = forces.get('Mz_j', 0) / 1000.0
                        t_i = forces.get('T_i', 0) / 1000.0
                        t_j = forces.get('T_j', 0) / 1000.0

                        normalized_n = self._display_end_force(n_i, n_j, "N")
                        normalized_vy = self._display_end_force(vy_i, vy_j, "Vy")
                        normalized_vz = self._display_end_force(vz_i, vz_j, "Vz")
                        normalized_my = self._display_end_force(my_i, my_j, "My")
                        normalized_mz = self._display_end_force(mz_i, mz_j, "Mz")
                        normalized_t = self._display_end_force(t_i, t_j, "T")
                        force_values.append({
                            'N_i': normalized_n,
                            'Vy_i': normalized_vy,
                            'Vz_i': normalized_vz,
                            'My_i': normalized_my,
                            'Mz_i': normalized_mz,
                            'T_i': normalized_t,
                        })
            
            if len(node_positions) >= 2:
                start_pos = node_positions[0]
                end_pos = node_positions[-1]
                total_length = ((end_pos[0] - start_pos[0])**2 + 
                               (end_pos[1] - start_pos[1])**2)**0.5
                
                for i, (pos, forces) in enumerate(zip(node_positions, force_values)):
                    if total_length > 0:
                        dist_from_start = ((pos[0] - start_pos[0])**2 + 
                                          (pos[1] - start_pos[1])**2)**0.5
                        position_ratio = dist_from_start / total_length
                    else:
                        position_ratio = i / max(len(node_positions) - 1, 1)
                    
                    rows.append({
                        'Load Case': self.load_case,
                        'Beam ID': parent_id,
                        'Floor': floor,
                        'Node': i + 1,
                        'Position': f"{position_ratio:.2f}L",
                        'X (m)': pos[0],
                        'Y (m)': pos[1],
                        'N (kN)': forces['N_i'],
                        'Vy (kN)': forces['Vy_i'],
                        'Vz (kN)': forces['Vz_i'],
                        'My-minor (kNm)': forces['My_i'],
                        'Mz-major (kNm)': forces['Mz_i'],
                        'T (kNm)': forces['T_i'],
                    })
        
        self._beam_data = pd.DataFrame(rows)
        return self._beam_data
    
    def get_floors(self) -> List[int]:
        """Get list of available floor levels."""
        df = self._extract_beam_forces()
        if df.empty:
            return []
        return sorted(df['Floor'].unique().tolist())
    
    def get_beams_on_floor(self, floor: int) -> List[int]:
        """Get list of beam IDs on a specific floor."""
        df = self._extract_beam_forces()
        if df.empty:
            return []
        floor_df = df[df['Floor'] == floor]
        return sorted(floor_df['Beam ID'].unique().tolist())
    
    def get_beam_forces(self, beam_id: int) -> pd.DataFrame:
        """Get forces for a specific beam (5 nodes)."""
        df = self._extract_beam_forces()
        if df.empty:
            return pd.DataFrame()
        return df[df['Beam ID'] == beam_id].copy()
    
    def get_floor_forces(self, floor: int) -> pd.DataFrame:
        """Get forces for all beams on a floor."""
        df = self._extract_beam_forces()
        if df.empty:
            return pd.DataFrame()
        return df[df['Floor'] == floor].copy()
    
    def render(self, floor_filter: Optional[int] = None):
        """Render the component in Streamlit."""
        st.markdown("### Beam Section Forces")
        
        df = self._extract_beam_forces()
        
        if df.empty:
            st.info("No beam force data available. Run FEM analysis first.")
            return
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            floors = self.get_floors()
            if floor_filter is not None and floor_filter in floors:
                default_idx = floors.index(floor_filter)
            else:
                default_idx = len(floors) - 1 if floors else 0
                
            selected_floor = st.selectbox(
                "Floor Level",
                options=floors,
                index=default_idx,
                format_func=lambda floor: format_floor_label_from_floor_number(floor, self.story_height),
                key="beam_forces_floor_selector"
            )
        
        with col2:
            beams = self.get_beams_on_floor(selected_floor) if selected_floor is not None else []
            beam_options = ["All Beams"] + [f"Beam {b}" for b in beams]
            selected_beam_str = st.selectbox(
                "Beam",
                options=beam_options,
                key="beam_forces_beam_selector"
            )
        
        if selected_beam_str == "All Beams":
            display_df = self.get_floor_forces(selected_floor)
        else:
            beam_id = int(selected_beam_str.replace("Beam ", ""))
            display_df = self.get_beam_forces(beam_id)
        
        if display_df.empty:
            st.info("No forces found for selection.")
            return
        
        force_columns = ['N (kN)', 'Vy (kN)', 'Vz (kN)', 'My-minor (kNm)', 'Mz-major (kNm)', 'T (kNm)']
        highlight_col = {
            'N': 'N (kN)',
            'Vy': 'Vy (kN)',
            'Vz': 'Vz (kN)',
            'My': 'My-minor (kNm)',
            'Mz': 'Mz-major (kNm)',
            'T': 'T (kNm)',
        }.get(self.force_type, 'Mz-major (kNm)')
        
        def highlight_column(s):
            return ['background-color: #fffacd' if s.name == highlight_col else '' for _ in s]
        
        styled_df = display_df.style.apply(highlight_column).format({
            'X (m)': '{:.2f}',
            'Y (m)': '{:.2f}',
            'N (kN)': '{:.1f}',
            'Vy (kN)': '{:.1f}',
            'Vz (kN)': '{:.1f}',
            'My-minor (kNm)': '{:.1f}',
            'Mz-major (kNm)': '{:.1f}',
            'T (kNm)': '{:.1f}',
        })
        
        st.dataframe(styled_df, width="stretch", hide_index=True)
        
        st.caption(f"📊 {len(display_df)} rows")
        
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            csv = display_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"beam_forces_floor_{selected_floor}.csv",
                mime="text/csv",
                key="beam_forces_csv_download"
            )
        
        with col_exp2:
            buffer = io.BytesIO()
            try:
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    display_df.to_excel(writer, index=False, sheet_name='Beam Forces')
                buffer.seek(0)
                st.download_button(
                    label="📥 Download Excel",
                    data=buffer,
                    file_name=f"beam_forces_floor_{selected_floor}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="beam_forces_excel_download"
                )
            except ImportError:
                st.info("Install openpyxl for Excel export: pip install openpyxl")


def extract_beam_subdivision_forces(
    model: Any,
    result: Any,
    floor: Optional[int] = None
) -> pd.DataFrame:
    """
    Extract beam forces at subdivision nodes.
    
    Args:
        model: FEMModel
        result: AnalysisResult
        floor: Optional floor filter
        
    Returns:
        DataFrame with columns: Beam ID, Floor, Node, Position, X, Y, N, Vy, Vz, My, Mz, T
    """
    table = BeamForcesTable(model, result)
    if floor is not None:
        return table.get_floor_forces(floor)
    return table._extract_beam_forces()
