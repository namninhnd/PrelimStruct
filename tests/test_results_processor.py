"""
Tests for results_processor.py dataclasses and ResultsProcessor class.

This module tests the three envelope dataclasses:
- ElementForceEnvelope
- DisplacementEnvelope
- ReactionEnvelope

And the ResultsProcessor class methods:
- process_load_case_results()
- _update_element_force_envelope()
"""

import pytest
from src.fem.results_processor import (
    ElementForceEnvelope,
    DisplacementEnvelope,
    ReactionEnvelope,
    ResultsProcessor,
)
from src.core.data_models import EnvelopeValue, LoadCombination, LoadCaseResult


class TestElementForceEnvelope:
    """Tests for ElementForceEnvelope dataclass."""

    def test_element_force_envelope_creation(self):
        """Test default values for ElementForceEnvelope."""
        envelope = ElementForceEnvelope(element_id=100)

        assert envelope.element_id == 100
        assert isinstance(envelope.N_max, EnvelopeValue)
        assert isinstance(envelope.N_min, EnvelopeValue)
        assert isinstance(envelope.V_max, EnvelopeValue)
        assert isinstance(envelope.V_min, EnvelopeValue)
        assert isinstance(envelope.M_max, EnvelopeValue)
        assert isinstance(envelope.M_min, EnvelopeValue)

        # Check default EnvelopeValue fields
        assert envelope.N_max.max_value == 0.0
        assert envelope.N_max.min_value == 0.0
        assert envelope.N_max.governing_max_case is None
        assert envelope.N_max.governing_min_case is None

    def test_element_force_envelope_with_values(self):
        """Test ElementForceEnvelope with custom EnvelopeValue."""
        custom_n_max = EnvelopeValue(
            max_value=1500.0,
            min_value=-500.0,
            governing_max_case=LoadCombination.ULS_GRAVITY_1,
            governing_min_case=LoadCombination.ULS_WIND_1,
            governing_max_location=100,
            governing_min_location=100,
        )

        envelope = ElementForceEnvelope(element_id=200, N_max=custom_n_max)

        assert envelope.element_id == 200
        assert envelope.N_max.max_value == 1500.0
        assert envelope.N_max.min_value == -500.0
        assert envelope.N_max.governing_max_case == LoadCombination.ULS_GRAVITY_1
        assert envelope.N_max.governing_min_case == LoadCombination.ULS_WIND_1
        assert envelope.N_max.governing_max_location == 100
        assert envelope.N_max.governing_min_location == 100

        # Other fields should still have defaults
        assert envelope.V_max.max_value == 0.0
        assert envelope.M_min.max_value == 0.0


class TestDisplacementEnvelope:
    """Tests for DisplacementEnvelope dataclass."""

    def test_displacement_envelope_creation(self):
        """Test default values for DisplacementEnvelope."""
        envelope = DisplacementEnvelope(node_id=500)

        assert envelope.node_id == 500
        assert isinstance(envelope.ux_max, EnvelopeValue)
        assert isinstance(envelope.uy_max, EnvelopeValue)
        assert isinstance(envelope.uz_max, EnvelopeValue)
        assert isinstance(envelope.drift_max, EnvelopeValue)

        # Check default EnvelopeValue fields
        assert envelope.ux_max.max_value == 0.0
        assert envelope.uy_max.max_value == 0.0
        assert envelope.uz_max.governing_max_case is None
        assert envelope.drift_max.governing_min_location is None

    def test_displacement_envelope_with_values(self):
        """Test DisplacementEnvelope with custom values."""
        custom_ux_max = EnvelopeValue(
            max_value=0.025,
            min_value=0.0,
            governing_max_case=LoadCombination.ULS_WIND_3,
            governing_max_location=500,
        )

        custom_drift_max = EnvelopeValue(
            max_value=0.002,
            governing_max_case=LoadCombination.SLS_CHARACTERISTIC,
            governing_max_location=500,
        )

        envelope = DisplacementEnvelope(
            node_id=600, ux_max=custom_ux_max, drift_max=custom_drift_max
        )

        assert envelope.node_id == 600
        assert envelope.ux_max.max_value == 0.025
        assert envelope.ux_max.governing_max_case == LoadCombination.ULS_WIND_3
        assert envelope.drift_max.max_value == 0.002
        assert envelope.drift_max.governing_max_case == LoadCombination.SLS_CHARACTERISTIC

        # Other fields should still have defaults
        assert envelope.uy_max.max_value == 0.0
        assert envelope.uz_max.max_value == 0.0


class TestReactionEnvelope:
    """Tests for ReactionEnvelope dataclass."""

    def test_reaction_envelope_creation(self):
        """Test default values for ReactionEnvelope."""
        envelope = ReactionEnvelope(node_id=1000)

        assert envelope.node_id == 1000
        assert isinstance(envelope.Fx_max, EnvelopeValue)
        assert isinstance(envelope.Fy_max, EnvelopeValue)
        assert isinstance(envelope.Fz_max, EnvelopeValue)
        assert isinstance(envelope.Fz_min, EnvelopeValue)
        assert isinstance(envelope.Mx_max, EnvelopeValue)
        assert isinstance(envelope.My_max, EnvelopeValue)

        # Check default EnvelopeValue fields
        assert envelope.Fx_max.max_value == 0.0
        assert envelope.Fz_min.min_value == 0.0
        assert envelope.Mx_max.governing_max_case is None

    def test_reaction_envelope_with_values(self):
        """Test ReactionEnvelope with custom values."""
        custom_fz_max = EnvelopeValue(
            max_value=25000.0,
            governing_max_case=LoadCombination.ULS_GRAVITY_1,
            governing_max_location=1000,
        )

        custom_fz_min = EnvelopeValue(
            min_value=-1500.0,
            governing_min_case=LoadCombination.ULS_WIND_2,
            governing_min_location=1000,
        )

        custom_mx_max = EnvelopeValue(
            max_value=5000.0,
            governing_max_case=LoadCombination.ULS_WIND_3,
            governing_max_location=1000,
        )

        envelope = ReactionEnvelope(
            node_id=1100,
            Fz_max=custom_fz_max,
            Fz_min=custom_fz_min,
            Mx_max=custom_mx_max,
        )

        assert envelope.node_id == 1100
        assert envelope.Fz_max.max_value == 25000.0
        assert envelope.Fz_max.governing_max_case == LoadCombination.ULS_GRAVITY_1
        assert envelope.Fz_min.min_value == -1500.0
        assert envelope.Fz_min.governing_min_case == LoadCombination.ULS_WIND_2
        assert envelope.Mx_max.max_value == 5000.0
        assert envelope.Mx_max.governing_max_case == LoadCombination.ULS_WIND_3

        # Other fields should still have defaults
        assert envelope.Fx_max.max_value == 0.0
        assert envelope.Fy_max.max_value == 0.0
        assert envelope.My_max.max_value == 0.0


# Fixtures for ResultsProcessor tests
@pytest.fixture
def sample_load_case_3d():
    """Create sample LoadCaseResult with 3D element forces."""
    return LoadCaseResult(
        combination=LoadCombination.ULS_GRAVITY_1,
        element_forces={
            1: {
                'N_i': 100.0, 'N_j': 100.0,
                'Vy_i': 50.0, 'Vy_j': 50.0,
                'Vz_i': 0.0, 'Vz_j': 0.0,
                'My_i': 200.0, 'My_j': 200.0,
                'Mz_i': 0.0, 'Mz_j': 0.0
            },
        },
        node_displacements={},
        reactions={},
    )


@pytest.fixture
def sample_load_case_2d():
    """Create sample LoadCaseResult with 2D element forces.
    
    Note: The implementation currently matches 3D format first if 'N_i' exists.
    So for 2D, we need to ensure it doesn't have 'N_i' to reach the 2D branch,
    OR we provide a force dict without N forces to test the 'V_i' branch.
    """
    return LoadCaseResult(
        combination=LoadCombination.ULS_WIND_1,
        element_forces={
            2: {
                'V_i': 75.0, 'V_j': 75.0,
                'M_i': 300.0, 'M_j': 300.0
            },
        },
        node_displacements={},
        reactions={},
    )


@pytest.fixture
def sample_load_case_with_displacements():
    """Create sample LoadCaseResult with node displacements."""
    return LoadCaseResult(
        combination=LoadCombination.ULS_GRAVITY_1,
        element_forces={},
        node_displacements={
            1: [0.001, 0.002, 0.003, 0.0, 0.0, 0.0],  # ux, uy, uz, rx, ry, rz
            2: [0.002, 0.004, 0.001, 0.0, 0.0, 0.0],
        },
        reactions={
            100: [10.0, 20.0, 500.0, 5.0, 10.0, 0.0],  # Fx, Fy, Fz, Mx, My, Mz
        },
    )


@pytest.fixture
def sample_load_case_with_uplift():
    """Create sample LoadCaseResult with uplift (negative Fz) in reactions."""
    return LoadCaseResult(
        combination=LoadCombination.ULS_WIND_1,
        element_forces={},
        node_displacements={},
        reactions={
            100: [50.0, 30.0, -100.0, 15.0, 25.0, 0.0],  # Negative Fz = uplift
        },
    )


class TestResultsProcessor:
    """Tests for ResultsProcessor class."""

    def test_results_processor_init(self):
        """Test ResultsProcessor initialization with empty envelopes."""
        processor = ResultsProcessor()

        assert isinstance(processor.element_force_envelopes, dict)
        assert isinstance(processor.displacement_envelopes, dict)
        assert isinstance(processor.reaction_envelopes, dict)
        assert len(processor.element_force_envelopes) == 0
        assert len(processor.displacement_envelopes) == 0
        assert len(processor.reaction_envelopes) == 0

    def test_process_load_case_results_empty_list(self):
        """Test processing empty list of load case results."""
        processor = ResultsProcessor()
        processor.process_load_case_results([])

        assert len(processor.element_force_envelopes) == 0
        assert len(processor.displacement_envelopes) == 0
        assert len(processor.reaction_envelopes) == 0

    def test_process_load_case_results_clears_existing(self):
        """Test that processing clears existing envelopes."""
        processor = ResultsProcessor()

        # Add dummy envelope
        processor.element_force_envelopes[999] = ElementForceEnvelope(element_id=999)
        assert len(processor.element_force_envelopes) == 1

        # Process empty list should clear
        processor.process_load_case_results([])
        assert len(processor.element_force_envelopes) == 0

    def test_element_force_envelope_3d_format(self, sample_load_case_3d):
        """Test element force envelope with 3D force format."""
        processor = ResultsProcessor()
        processor.process_load_case_results([sample_load_case_3d])

        assert 1 in processor.element_force_envelopes
        envelope = processor.element_force_envelopes[1]

        assert envelope.element_id == 1
        # Axial force: max(abs(N_i), abs(N_j)) = max(100, 100) = 100
        assert envelope.N_max.max_value == 100.0
        # Shear force: max(abs(Vy_i), abs(Vy_j), abs(Vz_i), abs(Vz_j)) = 50
        assert envelope.V_max.max_value == 50.0
        # Moment: max(abs(My_i), abs(My_j), abs(Mz_i), abs(Mz_j)) = 200
        assert envelope.M_max.max_value == 200.0

    def test_element_force_envelope_2d_format(self, sample_load_case_2d):
        """Test element force envelope with 2D force format."""
        processor = ResultsProcessor()
        processor.process_load_case_results([sample_load_case_2d])

        assert 2 in processor.element_force_envelopes
        envelope = processor.element_force_envelopes[2]

        assert envelope.element_id == 2
        # No axial force in this test case (testing V_i branch)
        assert envelope.N_max.max_value == 0.0
        # Shear force: max(abs(V_i), abs(V_j)) = 75
        assert envelope.V_max.max_value == 75.0
        # Moment: max(abs(M_i), abs(M_j)) = 300
        assert envelope.M_max.max_value == 300.0

    def test_element_force_envelope_max_tracking(self):
        """Test that maximum values are tracked correctly across multiple load cases."""
        processor = ResultsProcessor()

        # First load case with smaller forces (3D format)
        lc1 = LoadCaseResult(
            combination=LoadCombination.ULS_GRAVITY_1,
            element_forces={
                1: {
                    'N_i': 100.0, 'N_j': 100.0,
                    'Vy_i': 50.0, 'Vy_j': 50.0,
                    'Vz_i': 0.0, 'Vz_j': 0.0,
                    'My_i': 200.0, 'My_j': 200.0,
                    'Mz_i': 0.0, 'Mz_j': 0.0
                },
            },
            node_displacements={},
            reactions={},
        )

        # Second load case with larger forces (3D format)
        lc2 = LoadCaseResult(
            combination=LoadCombination.ULS_WIND_1,
            element_forces={
                1: {
                    'N_i': 200.0, 'N_j': 200.0,
                    'Vy_i': 100.0, 'Vy_j': 100.0,
                    'Vz_i': 0.0, 'Vz_j': 0.0,
                    'My_i': 400.0, 'My_j': 400.0,
                    'Mz_i': 0.0, 'Mz_j': 0.0
                },
            },
            node_displacements={},
            reactions={},
        )

        processor.process_load_case_results([lc1, lc2])

        envelope = processor.element_force_envelopes[1]
        # Should track maximum from lc2
        assert envelope.N_max.max_value == 200.0
        assert envelope.V_max.max_value == 100.0
        assert envelope.M_max.max_value == 400.0

    def test_element_force_envelope_governing_case(self):
        """Test that governing load case is tracked correctly."""
        processor = ResultsProcessor()

        lc1 = LoadCaseResult(
            combination=LoadCombination.ULS_GRAVITY_1,
            element_forces={
                1: {
                    'N_i': 100.0, 'N_j': 100.0,
                    'Vy_i': 50.0, 'Vy_j': 50.0,
                    'Vz_i': 0.0, 'Vz_j': 0.0,
                    'My_i': 200.0, 'My_j': 200.0,
                    'Mz_i': 0.0, 'Mz_j': 0.0
                },
            },
            node_displacements={},
            reactions={},
        )

        lc2 = LoadCaseResult(
            combination=LoadCombination.ULS_WIND_1,
            element_forces={
                1: {
                    'N_i': 50.0, 'N_j': 50.0,
                    'Vy_i': 100.0, 'Vy_j': 100.0,
                    'Vz_i': 0.0, 'Vz_j': 0.0,
                    'My_i': 400.0, 'My_j': 400.0,
                    'Mz_i': 0.0, 'Mz_j': 0.0
                },
            },
            node_displacements={},
            reactions={},
        )

        processor.process_load_case_results([lc1, lc2])

        envelope = processor.element_force_envelopes[1]
        # N_max governed by ULS_GRAVITY_1
        assert envelope.N_max.governing_max_case == LoadCombination.ULS_GRAVITY_1
        # V_max governed by ULS_WIND_1
        assert envelope.V_max.governing_max_case == LoadCombination.ULS_WIND_1
        # M_max governed by ULS_WIND_1
        assert envelope.M_max.governing_max_case == LoadCombination.ULS_WIND_1

    def test_displacement_envelope_update(self, sample_load_case_with_displacements):
        """Test displacement envelope updates with ux, uy, uz tracking."""
        processor = ResultsProcessor()
        processor.process_load_case_results([sample_load_case_with_displacements])

        # Check node 1 displacements
        assert 1 in processor.displacement_envelopes
        env1 = processor.displacement_envelopes[1]
        assert env1.node_id == 1
        assert env1.ux_max.max_value == 0.001  # abs(0.001)
        assert env1.uy_max.max_value == 0.002  # abs(0.002)
        assert env1.uz_max.max_value == 0.003  # abs(0.003)
        assert env1.ux_max.governing_max_case == LoadCombination.ULS_GRAVITY_1

        # Check node 2 displacements
        assert 2 in processor.displacement_envelopes
        env2 = processor.displacement_envelopes[2]
        assert env2.node_id == 2
        assert env2.ux_max.max_value == 0.002  # abs(0.002)
        assert env2.uy_max.max_value == 0.004  # abs(0.004)
        assert env2.uz_max.max_value == 0.001  # abs(0.001)

    def test_displacement_envelope_max_across_cases(self):
        """Test displacement envelope max tracking across multiple load cases."""
        processor = ResultsProcessor()

        lc1 = LoadCaseResult(
            combination=LoadCombination.ULS_GRAVITY_1,
            element_forces={},
            node_displacements={
                1: [0.001, 0.002, 0.003, 0.0, 0.0, 0.0],
            },
            reactions={},
        )

        lc2 = LoadCaseResult(
            combination=LoadCombination.ULS_WIND_1,
            element_forces={},
            node_displacements={
                1: [0.005, 0.001, 0.002, 0.0, 0.0, 0.0],  # Higher ux, lower uy, uz
            },
            reactions={},
        )

        processor.process_load_case_results([lc1, lc2])

        env = processor.displacement_envelopes[1]
        # Should track max from each load case
        assert env.ux_max.max_value == 0.005  # From lc2
        assert env.ux_max.governing_max_case == LoadCombination.ULS_WIND_1
        assert env.uy_max.max_value == 0.002  # From lc1
        assert env.uy_max.governing_max_case == LoadCombination.ULS_GRAVITY_1
        assert env.uz_max.max_value == 0.003  # From lc1
        assert env.uz_max.governing_max_case == LoadCombination.ULS_GRAVITY_1

    def test_reaction_envelope_update(self, sample_load_case_with_displacements):
        """Test reaction envelope updates with Fx, Fy, Fz tracking."""
        processor = ResultsProcessor()
        processor.process_load_case_results([sample_load_case_with_displacements])

        assert 100 in processor.reaction_envelopes
        env = processor.reaction_envelopes[100]

        assert env.node_id == 100
        assert env.Fx_max.max_value == 10.0  # abs(10.0)
        assert env.Fy_max.max_value == 20.0  # abs(20.0)
        assert env.Fz_max.max_value == 500.0  # 500.0 (compression)
        assert env.Fz_min.min_value == 500.0  # 500.0 (no uplift in this case)
        assert env.Fx_max.governing_max_case == LoadCombination.ULS_GRAVITY_1

    def test_reaction_envelope_uplift_detection(self, sample_load_case_with_uplift):
        """Test reaction envelope tracks negative Fz (uplift)."""
        processor = ResultsProcessor()
        processor.process_load_case_results([sample_load_case_with_uplift])

        env = processor.reaction_envelopes[100]

        assert env.node_id == 100
        assert env.Fx_max.max_value == 50.0
        assert env.Fy_max.max_value == 30.0
        # Fz is negative (uplift)
        assert env.Fz_max.max_value == 0.0  # No compression
        assert env.Fz_min.min_value == -100.0  # Uplift
        assert env.Fz_min.governing_min_case == LoadCombination.ULS_WIND_1

    def test_reaction_envelope_moment_tracking(self):
        """Test reaction envelope tracks Mx, My for 6DOF reactions."""
        processor = ResultsProcessor()

        lc1 = LoadCaseResult(
            combination=LoadCombination.ULS_GRAVITY_1,
            element_forces={},
            node_displacements={},
            reactions={
                100: [10.0, 20.0, 500.0, 50.0, 100.0, 0.0],  # With moments
            },
        )

        lc2 = LoadCaseResult(
            combination=LoadCombination.ULS_WIND_1,
            element_forces={},
            node_displacements={},
            reactions={
                100: [30.0, 40.0, 300.0, 150.0, 80.0, 0.0],  # Different moments
            },
        )

        processor.process_load_case_results([lc1, lc2])

        env = processor.reaction_envelopes[100]

        # Mx_max should track max across cases
        assert env.Mx_max.max_value == 150.0  # From lc2
        assert env.Mx_max.governing_max_case == LoadCombination.ULS_WIND_1
        # My_max should track max across cases
        assert env.My_max.max_value == 100.0  # From lc1
        assert env.My_max.governing_max_case == LoadCombination.ULS_GRAVITY_1

    def test_calculate_drift_empty_elevations(self):
        """Test calculate_inter_story_drift handles empty node_elevations."""
        processor = ResultsProcessor()

        # Create some displacement envelopes
        processor.displacement_envelopes[1] = DisplacementEnvelope(node_id=1)
        processor.displacement_envelopes[1].ux_max.max_value = 0.005

        # Call with empty elevations - should not crash
        processor.calculate_inter_story_drift({}, story_height=3.5)

        # Drift should remain at default (0.0)
        assert processor.displacement_envelopes[1].drift_max.max_value == 0.0

    def test_calculate_drift_single_floor(self):
        """Test no drift calculated for single floor."""
        processor = ResultsProcessor()

        # Create displacement envelope for single node
        processor.displacement_envelopes[1] = DisplacementEnvelope(node_id=1)
        processor.displacement_envelopes[1].ux_max.max_value = 0.005

        # Single floor - no adjacent floor to compare
        node_elevations = {1: 0.0}
        processor.calculate_inter_story_drift(node_elevations, story_height=3.5)

        # No drift should be calculated
        assert processor.displacement_envelopes[1].drift_max.max_value == 0.0

    def test_calculate_drift_two_floors(self):
        """Test drift calculated correctly between two floors."""
        processor = ResultsProcessor()

        # Set up displacement envelopes
        # Ground floor node
        processor.displacement_envelopes[1] = DisplacementEnvelope(node_id=1)
        processor.displacement_envelopes[1].ux_max.max_value = 0.005  # 5mm
        processor.displacement_envelopes[1].uy_max.max_value = 0.003  # 3mm
        processor.displacement_envelopes[1].ux_max.governing_max_case = LoadCombination.ULS_WIND_1

        # First floor node
        processor.displacement_envelopes[2] = DisplacementEnvelope(node_id=2)
        processor.displacement_envelopes[2].ux_max.max_value = 0.015  # 15mm
        processor.displacement_envelopes[2].uy_max.max_value = 0.008  # 8mm
        processor.displacement_envelopes[2].ux_max.governing_max_case = LoadCombination.ULS_WIND_1

        node_elevations = {1: 0.0, 2: 3.5}  # Ground and first floor
        processor.calculate_inter_story_drift(node_elevations, story_height=3.5)

        # Drift_x = abs(15mm - 5mm) = 10mm = 0.010m
        # Drift_y = abs(8mm - 3mm) = 5mm = 0.005m
        # Drift = max(0.010, 0.005) = 0.010m
        # Drift_ratio = 0.010 / 3.5 = 0.002857...
        upper_drift = processor.displacement_envelopes[2].drift_max.max_value
        expected_drift_ratio = 0.010 / 3.5

        assert upper_drift > 0
        assert abs(upper_drift - expected_drift_ratio) < 1e-6
        # Governing case should be copied from ux_max
        assert processor.displacement_envelopes[2].drift_max.governing_max_case == LoadCombination.ULS_WIND_1

    def test_calculate_drift_ratio_calculation(self):
        """Test drift ratio calculation with different story heights."""
        processor = ResultsProcessor()

        # Set up nodes at different elevations
        processor.displacement_envelopes[1] = DisplacementEnvelope(node_id=1)
        processor.displacement_envelopes[1].ux_max.max_value = 0.0
        processor.displacement_envelopes[1].uy_max.max_value = 0.0

        processor.displacement_envelopes[2] = DisplacementEnvelope(node_id=2)
        processor.displacement_envelopes[2].ux_max.max_value = 0.012  # 12mm
        processor.displacement_envelopes[2].uy_max.max_value = 0.0

        processor.displacement_envelopes[3] = DisplacementEnvelope(node_id=3)
        processor.displacement_envelopes[3].ux_max.max_value = 0.028  # 28mm
        processor.displacement_envelopes[3].uy_max.max_value = 0.0

        # Three floors: ground (0m), first (4m), second (8m)
        node_elevations = {1: 0.0, 2: 4.0, 3: 8.0}
        processor.calculate_inter_story_drift(node_elevations, story_height=4.0)

        # First floor drift: (12mm - 0mm) / 4m = 0.012 / 4 = 0.003
        drift_1 = processor.displacement_envelopes[2].drift_max.max_value
        assert abs(drift_1 - 0.003) < 1e-6

        # Second floor drift: (28mm - 12mm) / 4m = 0.016 / 4 = 0.004
        drift_2 = processor.displacement_envelopes[3].drift_max.max_value
        assert abs(drift_2 - 0.004) < 1e-6

    def test_calculate_drift_zero_height_protection(self):
        """Test that zero height between floors is handled (skipped)."""
        processor = ResultsProcessor()

        processor.displacement_envelopes[1] = DisplacementEnvelope(node_id=1)
        processor.displacement_envelopes[1].ux_max.max_value = 0.005

        processor.displacement_envelopes[2] = DisplacementEnvelope(node_id=2)
        processor.displacement_envelopes[2].ux_max.max_value = 0.015

        # Same elevation - height = 0 - should be skipped
        node_elevations = {1: 3.5, 2: 3.5}
        processor.calculate_inter_story_drift(node_elevations, story_height=3.5)

        # Drift should remain 0 (not calculated due to zero height)
        assert processor.displacement_envelopes[2].drift_max.max_value == 0.0

    def test_calculate_drift_missing_envelope(self):
        """Test drift calculation when some nodes lack displacement envelopes."""
        processor = ResultsProcessor()

        # Only create envelope for upper node, not lower node
        processor.displacement_envelopes[2] = DisplacementEnvelope(node_id=2)
        processor.displacement_envelopes[2].ux_max.max_value = 0.015

        # Node 1 has no envelope
        node_elevations = {1: 0.0, 2: 3.5}
        processor.calculate_inter_story_drift(node_elevations, story_height=3.5)

        # Should not crash, drift remains 0 (no lower node to compare)
        assert processor.displacement_envelopes[2].drift_max.max_value == 0.0

    def test_get_critical_elements_empty(self):
        """Test get_critical_elements returns empty list when no elements."""
        processor = ResultsProcessor()

        critical = processor.get_critical_elements(n_elements=10, criterion="moment")

        assert critical == []
        assert isinstance(critical, list)

    def test_get_critical_elements_by_moment(self):
        """Test get_critical_elements sorts by moment (default criterion)."""
        processor = ResultsProcessor()

        # Add element force envelopes with different moments
        env1 = ElementForceEnvelope(element_id=1)
        env1.M_max.max_value = 100.0
        env1.M_max.governing_max_case = LoadCombination.ULS_GRAVITY_1

        env2 = ElementForceEnvelope(element_id=2)
        env2.M_max.max_value = 300.0  # Highest
        env2.M_max.governing_max_case = LoadCombination.ULS_WIND_1

        env3 = ElementForceEnvelope(element_id=3)
        env3.M_max.max_value = 200.0
        env3.M_max.governing_max_case = LoadCombination.ULS_GRAVITY_1

        processor.element_force_envelopes = {1: env1, 2: env2, 3: env3}

        critical = processor.get_critical_elements(n_elements=3, criterion="moment")

        # Should be sorted by moment descending
        assert len(critical) == 3
        assert critical[0] == (2, 300.0, LoadCombination.ULS_WIND_1)
        assert critical[1] == (3, 200.0, LoadCombination.ULS_GRAVITY_1)
        assert critical[2] == (1, 100.0, LoadCombination.ULS_GRAVITY_1)

    def test_get_critical_elements_by_shear(self):
        """Test get_critical_elements sorts by shear."""
        processor = ResultsProcessor()

        env1 = ElementForceEnvelope(element_id=1)
        env1.V_max.max_value = 150.0
        env1.V_max.governing_max_case = LoadCombination.ULS_GRAVITY_1

        env2 = ElementForceEnvelope(element_id=2)
        env2.V_max.max_value = 50.0
        env2.V_max.governing_max_case = LoadCombination.ULS_WIND_1

        env3 = ElementForceEnvelope(element_id=3)
        env3.V_max.max_value = 100.0
        env3.V_max.governing_max_case = LoadCombination.ULS_GRAVITY_1

        processor.element_force_envelopes = {1: env1, 2: env2, 3: env3}

        critical = processor.get_critical_elements(n_elements=3, criterion="shear")

        assert len(critical) == 3
        assert critical[0] == (1, 150.0, LoadCombination.ULS_GRAVITY_1)
        assert critical[1] == (3, 100.0, LoadCombination.ULS_GRAVITY_1)
        assert critical[2] == (2, 50.0, LoadCombination.ULS_WIND_1)

    def test_get_critical_elements_by_axial(self):
        """Test get_critical_elements sorts by axial force."""
        processor = ResultsProcessor()

        env1 = ElementForceEnvelope(element_id=1)
        env1.N_max.max_value = 500.0
        env1.N_max.governing_max_case = LoadCombination.ULS_GRAVITY_1

        env2 = ElementForceEnvelope(element_id=2)
        env2.N_max.max_value = 1000.0  # Highest
        env2.N_max.governing_max_case = LoadCombination.ULS_WIND_1

        env3 = ElementForceEnvelope(element_id=3)
        env3.N_max.max_value = 750.0
        env3.N_max.governing_max_case = LoadCombination.ULS_GRAVITY_1

        processor.element_force_envelopes = {1: env1, 2: env2, 3: env3}

        critical = processor.get_critical_elements(n_elements=3, criterion="axial")

        assert len(critical) == 3
        assert critical[0] == (2, 1000.0, LoadCombination.ULS_WIND_1)
        assert critical[1] == (3, 750.0, LoadCombination.ULS_GRAVITY_1)
        assert critical[2] == (1, 500.0, LoadCombination.ULS_GRAVITY_1)

    def test_get_critical_elements_limit(self):
        """Test get_critical_elements returns only n_elements."""
        processor = ResultsProcessor()

        # Create 5 elements
        for i in range(1, 6):
            env = ElementForceEnvelope(element_id=i)
            env.M_max.max_value = float(i * 100)
            processor.element_force_envelopes[i] = env

        # Request only 2 elements
        critical = processor.get_critical_elements(n_elements=2, criterion="moment")

        assert len(critical) == 2
        assert critical[0][0] == 5  # Element 5 has highest moment (500)
        assert critical[1][0] == 4  # Element 4 has second highest (400)

    def test_get_critical_elements_invalid_criterion(self):
        """Test get_critical_elements handles invalid criterion gracefully."""
        processor = ResultsProcessor()

        env1 = ElementForceEnvelope(element_id=1)
        env1.M_max.max_value = 100.0
        processor.element_force_envelopes[1] = env1

        # Invalid criterion should skip the element (returns empty list)
        critical = processor.get_critical_elements(n_elements=10, criterion="invalid")

        assert critical == []

    def test_export_envelope_summary_empty(self):
        """Test export_envelope_summary returns header with empty processor."""
        processor = ResultsProcessor()

        summary = processor.export_envelope_summary()

        # Check that header is present
        assert "FEM RESULTS ENVELOPE SUMMARY" in summary
        assert "=" * 80 in summary
        assert "ELEMENT FORCE ENVELOPES:" in summary
        assert "Total elements enveloped: 0" in summary
        assert "DISPLACEMENT ENVELOPES:" in summary
        assert "Total nodes enveloped: 0" in summary
        assert "REACTION ENVELOPES:" in summary
        assert "Total support nodes: 0" in summary

    def test_export_envelope_summary_with_data(self):
        """Test export_envelope_summary with proper formatting."""
        processor = ResultsProcessor()

        # Add element force envelope
        env1 = ElementForceEnvelope(element_id=1)
        env1.M_max.max_value = 200e6  # 200 kN-m (in N-mm)
        env1.V_max.max_value = 150e3  # 150 kN (in N)
        env1.N_max.max_value = 500e3  # 500 kN (in N)
        processor.element_force_envelopes[1] = env1

        # Add displacement envelope
        disp_env = DisplacementEnvelope(node_id=100)
        disp_env.ux_max.max_value = 0.025  # 25 mm (in m)
        disp_env.uy_max.max_value = 0.030  # 30 mm
        disp_env.uz_max.max_value = 0.015  # 15 mm
        processor.displacement_envelopes[100] = disp_env

        # Add reaction envelope
        react_env = ReactionEnvelope(node_id=200)
        react_env.Fz_max.max_value = 1000e3  # 1000 kN (in N)
        react_env.Fz_min.min_value = -50e3   # -50 kN (uplift, in N)
        processor.reaction_envelopes[200] = react_env

        summary = processor.export_envelope_summary()

        # Check element forces section
        assert "Total elements enveloped: 1" in summary
        assert "Maximum moment: 200.00 kN-m" in summary
        assert "Maximum shear: 150.00 kN" in summary
        assert "Maximum axial: 500.00 kN" in summary

        # Check displacement section
        assert "Total nodes enveloped: 1" in summary
        assert "Maximum horizontal X: 25.00 mm" in summary
        assert "Maximum horizontal Y: 30.00 mm" in summary
        assert "Maximum vertical: 15.00 mm" in summary

        # Check reaction section
        assert "Total support nodes: 1" in summary
        assert "Maximum vertical reaction: 1000.00 kN" in summary
        assert "Minimum vertical reaction: -50.00 kN" in summary
        assert "WARNING: Uplift detected (-50.00 kN)" in summary

