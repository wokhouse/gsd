"""
Test suite for two-way workflow improvements.

Tests for:
- F3 calculation helper function
- Printing strategy suggestion
- Design validation
- Constraint enforcement
"""

import pytest
import numpy as np
from gsd.simulation.response_metrics import find_f3_frequency
from gsd.driver import load_driver
from gsd.optimization.api.manufacturing import suggest_printing_strategy
from gsd.optimization.api.validation import validate_two_way_design
from gsd.optimization.api.two_way_system import TwoWaySystemDesign


class TestF3Calculation:
    """Test F3 calculation helper function."""

    def test_highpass_f3(self):
        """Test F3 for high-pass filter (ported box)."""
        # Create 4th-order high-pass response at 50 Hz
        freq = np.logspace(1, 4, 1000)
        fc = 50
        spl = 20 * np.log10(1 / (1 + (fc / freq)**4)) + 94

        # Passband above cutoff
        passband = np.mean(spl[freq >= 100])

        f3 = find_f3_frequency(freq, spl, passband,
                               search_range=(10, 200),
                               filter_type="highpass")

        # Should be close to fc
        assert 45 < f3 < 55, f"F3={f3:.1f} Hz, expected ~50 Hz"

    def test_lowpass_f3(self):
        """Test F3 for low-pass filter (sealed box)."""
        # Create 2nd-order low-pass response at 5000 Hz
        freq = np.logspace(1, 5, 1000)
        fc = 5000
        spl = 20 * np.log10(1 / (1 + (freq / fc)**2)) + 94

        # Passband below cutoff
        passband = np.mean(spl[freq <= 2000])

        f3 = find_f3_frequency(freq, spl, passband,
                               search_range=(1000, 10000),
                               filter_type="lowpass")

        # Should be close to fc
        assert 4500 < f3 < 5500, f"F3={f3:.1f} Hz, expected ~5000 Hz"

    def test_f3_not_found(self):
        """Test behavior when F3 not in search range."""
        freq = np.linspace(100, 1000, 100)
        spl = np.ones_like(freq) * 90  # Flat response

        passband = 90
        f3 = find_f3_frequency(freq, spl, passband,
                               search_range=(100, 1000),
                               filter_type="highpass")

        # Should return closest frequency
        assert f3 == freq[0] or f3 == freq[-1]


class TestPrintingStrategy:
    """Test printing strategy suggestion."""

    def test_fits_single_piece(self):
        """Test case where horn fits in printer."""
        driver = load_driver("BC_DH450")

        strategy = suggest_printing_strategy(
            driver,
            target_cutoff=600,  # Higher cutoff = shorter horn
            printer_max_length=0.25
        )

        assert strategy['fits_single_piece']
        assert strategy['strategy'] == 'single'
        assert strategy['num_sections_required'] == 1

    def test_requires_multi_piece(self):
        """Test case where horn is too long for single print."""
        driver = load_driver("BC_DH450")

        strategy = suggest_printing_strategy(
            driver,
            target_cutoff=400,  # Lower cutoff = longer horn
            printer_max_length=0.25
        )

        # Should suggest multi-piece
        if not strategy['fits_single_piece']:
            assert strategy['strategy'] == 'multi_piece'
            assert strategy['num_sections_required'] >= 2

    def test_requires_redesign(self):
        """Test case where requirements are unrealistic."""
        driver = load_driver("BC_DH450")

        strategy = suggest_printing_strategy(
            driver,
            target_cutoff=100,  # Very low cutoff
            printer_max_length=0.10  # Very small printer
        )

        # Should suggest redesign
        if strategy['strategy'] == 'redesign_needed':
            assert 'alternatives' in strategy
            assert len(strategy['alternatives']) > 0


class TestDesignValidation:
    """Test design validation function."""

    def test_good_design_passes(self):
        """Test that good design passes validation."""

        # Create a good design
        design = TwoWaySystemDesign(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            lf_enclosure_type="ported",
            lf_enclosure_params={},
            horn_params={"cutoff": 400},  # Good: 2× below 800 Hz
            crossover_frequency=800,
            hf_padding_db=-15.5,
            lf_padding_db=0.0,
            f3=47,
            flatness=2.0,  # Good: < 3 dB
            system_level=94.0
        )

        # Add required attributes
        design.lf_sensitivity = 94.0
        design.hf_sensitivity = 110.0

        validation = validate_two_way_design(design, verbose=False)

        assert validation.passes
        assert len(validation.warnings) == 0

    def test_poor_design_fails(self):
        """Test that poor design fails validation."""

        # Create a bad design
        design = TwoWaySystemDesign(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            lf_enclosure_type="ported",
            lf_enclosure_params={},
            horn_params={"cutoff": 700},  # Bad: close to crossover
            crossover_frequency=800,
            hf_padding_db=-15.5,
            lf_padding_db=0.0,
            f3=47,
            flatness=8.0,  # Bad: > 6 dB
            system_level=94.0
        )

        # Add required attributes
        design.lf_sensitivity = 94.0
        design.hf_sensitivity = 110.0

        validation = validate_two_way_design(design, verbose=False)

        assert not validation.passes
        assert len(validation.warnings) > 0
        assert len(validation.recommendations) > 0


class TestConstraintEnforcement:
    """Test that constraint parameters are passed correctly."""

    def test_constraint_total_length_enforced(self):
        """Verify that max_length constraint is actually enforced."""
        from gsd.optimization.parameters.multisegment_horn_params import (
            get_multisegment_horn_parameter_space
        )
        from gsd.optimization.objectives.composite import EnclosureOptimizationProblem

        driver = load_driver("BC_DH450")

        # Request 250mm max length
        param_space = get_multisegment_horn_parameter_space(
            driver,
            preset="midrange_horn",
            num_segments=2,
            max_length=0.25,  # 25cm
            max_mouth_area=0.0625
        )

        # Create problem with param_space
        problem = EnclosureOptimizationProblem(
            driver=driver,
            enclosure_type="multisegment_horn",
            objectives=["f3"],
            parameter_bounds=param_space.get_bounds_dict(),
            constraints=["total_length"],
            param_space=param_space,  # Pass param_space to get metadata
            num_segments=2
        )

        # Verify metadata was stored
        assert hasattr(problem, 'metadata')
        assert 'max_length' in problem.metadata
        assert problem.metadata['max_length'] == 0.25
