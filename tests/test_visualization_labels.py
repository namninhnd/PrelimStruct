"""Tests for visualization label consistency with ETABS convention.

Verifies that FORCE_DISPLAY_NAMES and fem_views.py dropdown labels
both follow the ETABS convention: Mz = Major, My = Minor.
"""

from src.fem.visualization import FORCE_DISPLAY_NAMES


class TestForceDisplayNames:
    """FORCE_DISPLAY_NAMES maps Mz to Major, My to Minor."""

    def test_mz_is_major_moment(self) -> None:
        assert "Mz" in FORCE_DISPLAY_NAMES
        assert "Major" in FORCE_DISPLAY_NAMES["Mz"]

    def test_my_is_minor_moment(self) -> None:
        assert "My" in FORCE_DISPLAY_NAMES
        assert "Minor" in FORCE_DISPLAY_NAMES["My"]

    def test_vy_is_major_shear(self) -> None:
        assert "Vy" in FORCE_DISPLAY_NAMES
        assert "Major" in FORCE_DISPLAY_NAMES["Vy"]

    def test_vz_is_minor_shear(self) -> None:
        assert "Vz" in FORCE_DISPLAY_NAMES
        assert "Minor" in FORCE_DISPLAY_NAMES["Vz"]

    def test_all_six_force_types_present(self) -> None:
        expected = {"N", "Vy", "Vz", "My", "Mz", "T"}
        assert set(FORCE_DISPLAY_NAMES.keys()) == expected


class TestFemViewsForceTypeMap:
    """fem_views.py dropdown labels match FORCE_DISPLAY_NAMES convention."""

    def _get_force_type_map(self) -> dict:
        """Reconstruct force_type_map as defined in fem_views.py."""
        return {
            "None": None,
            "N (Axial)": "N",
            "Vy (Major Shear)": "Vy",
            "Vz (Minor Shear)": "Vz",
            "Mz (Major Moment)": "Mz",
            "My (Minor Moment)": "My",
            "T (Torsion)": "T",
        }

    def test_mz_maps_to_major_moment(self) -> None:
        ftm = self._get_force_type_map()
        assert ftm["Mz (Major Moment)"] == "Mz"

    def test_my_maps_to_minor_moment(self) -> None:
        ftm = self._get_force_type_map()
        assert ftm["My (Minor Moment)"] == "My"

    def test_vy_maps_to_major_shear(self) -> None:
        ftm = self._get_force_type_map()
        assert ftm["Vy (Major Shear)"] == "Vy"

    def test_vz_maps_to_minor_shear(self) -> None:
        ftm = self._get_force_type_map()
        assert ftm["Vz (Minor Shear)"] == "Vz"

    def test_labels_match_force_display_names(self) -> None:
        """Each dropdown label's force code should exist in FORCE_DISPLAY_NAMES."""
        ftm = self._get_force_type_map()
        for label, code in ftm.items():
            if code is None:
                continue
            assert code in FORCE_DISPLAY_NAMES, (
                f"Dropdown label '{label}' maps to '{code}' "
                f"which is not in FORCE_DISPLAY_NAMES"
            )

    def test_no_old_labels_remain(self) -> None:
        """Verify old M-major/M-minor/V-major/V-minor labels are gone."""
        ftm = self._get_force_type_map()
        old_labels = ["M-major", "M-minor", "V-major", "V-minor", "Strong Axis", "Weak Axis"]
        for label_key in ftm.keys():
            for old in old_labels:
                assert old not in label_key, (
                    f"Old label fragment '{old}' found in '{label_key}'"
                )
