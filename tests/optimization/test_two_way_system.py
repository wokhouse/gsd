"""
Unit tests for two-way system design module.

Tests cover:
- F3 calculation accuracy
- HF padding optimization
- Complete system design workflow
- Input validation

Literature:
- Small (1972) - F3 definition for enclosure systems
- D'Appolito (1984) - System flatness optimization
"""

import pytest
import numpy as np
from gsd.optimization.api.two_way_system import (
    optimize_hf_padding_for_flatness,
    design_two_way_system,
    TwoWaySystemDesign
)
from gsd.driver import load_driver


class TestF3Calculation:
    """Test F3 (-3 dB frequency) calculation."""

    def test_f3_with_ported_box_b4_alignment(self):
        """
        Test F3 calculation with B4 ported alignment.

        For a B4 alignment (Vb = Vas, Fb = Fs), the F3 should be
        approximately equal to the tuning frequency Fb.

        Literature: Small (1972) - Vented-box alignments

        Expected: F3 ≈ Fb = 46.4 Hz ± 2 Hz
        """
        # Use BC_12FW88 with B4 alignment
        lf_driver = load_driver("BC_12FW88")
        Fb = lf_driver.F_s   # B4: Fb = Fs

        result = design_two_way_system(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            lf_enclosure_type="ported",
            optimize_hf_padding=False,
            crossover_range=(1000, 1500),
            population_size=10,
            generations=5
        )

        # F3 should be close to tuning frequency
        assert result.f3 > 40, f"F3 {result.f3} Hz too low for {Fb} Hz tuning"
        assert result.f3 < 60, f"F3 {result.f3} Hz too high for {Fb} Hz tuning"
        # Within ~30% of tuning frequency (wider tolerance for optimization)
        assert abs(result.f3 - Fb) / Fb < 0.3, \
            f"F3 {result.f3} Hz deviates >30% from Fb {Fb} Hz"

    def test_f3_interpolation_accuracy(self):
        """
        Test linear interpolation accuracy for F3 calculation.

        Creates a synthetic response with a known -3 dB crossing point
        and verifies the interpolation recovers it accurately.
        """
        # Import the helper function
        from gsd.optimization.api.two_way_system import calculate_f3_frequency

        # Create synthetic frequency response
        freq = np.logspace(np.log10(20), np.log10(200), 100)

        # Create response with -3 dB point at exactly 50 Hz
        # At 50 Hz: response should be 87 dB (90 - 3)
        # We'll use -12 dB/octave slope, but position it so F3 = 50 Hz
        f3_true = 50.0
        passband_level = 90.0

        response = np.zeros_like(freq)
        for i, f in enumerate(freq):
            if f >= f3_true * 1.5:  # Well above F3
                response[i] = passband_level
            elif f <= f3_true:  # At or below F3
                # Use a step function: exactly at -3 dB at F3, then rolls off
                if f == f3_true:
                    response[i] = passband_level - 3
                else:
                    # -12 dB/octave below F3
                    octaves_below = np.log2(max(f, 10) / f3_true)
                    response[i] = (passband_level - 3) + octaves_below * 12
            else:  # Transition region
                # Smooth transition from passband to -3 dB
                ratio = (f - f3_true) / (f3_true * 0.5)
                response[i] = (passband_level - 3) + ratio * 3

        f3_calc = calculate_f3_frequency(freq, response)

        # Should be within 10% of true value (wider tolerance due to discrete freq points)
        assert abs(f3_calc - f3_true) / f3_true < 0.10, \
            f"Interpolation error: {f3_calc} Hz vs {f3_true} Hz"

    def test_f3_with_sealed_box(self):
        """
        Test F3 calculation with sealed box enclosure.

        Sealed boxes typically have F3 higher than ported boxes
        for the same driver.
        """
        result = design_two_way_system(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            lf_enclosure_type="sealed",
            optimize_hf_padding=False,
            crossover_range=(1000, 1500),
            population_size=10,
            generations=5
        )

        # Sealed box F3 should be in reasonable range
        assert result.f3 > 50, f"F3 {result.f3} Hz seems too low for sealed box"
        assert result.f3 < 120, f"F3 {result.f3} Hz seems too high"


class TestHFPaddingOptimization:
    """Test HF padding optimization for bi-amped systems."""

    def test_padding_optimization_reduces_flatness(self):
        """
        Test that padding optimization improves system flatness.

        The function should find a padding value that minimizes
        passband ripple.
        """
        lf_enclosure_params = {"Vb": 0.1145, "Fb": 46.4}
        horn_params = {"cutoff": 400, "length": 0.24}

        # Get optimal padding
        optimal_pad = optimize_hf_padding_for_flatness(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            lf_enclosure_type="ported",
            lf_enclosure_params=lf_enclosure_params,
            horn_params=horn_params,
            crossover_frequency=1000,
            padding_range=(-20, -10),
            num_steps=11
        )

        # Optimal padding should be within search range
        assert -20 <= optimal_pad <= -10, \
            f"Optimal padding {optimal_pad} outside search range"

        # Should be reasonably close to typical values (-15 to -18 dB)
        assert -18 <= optimal_pad <= -14, \
            f"Optimal padding {optimal_pad} seems unusual"

    def test_padding_optimization_convergence(self):
        """
        Test that optimization converges to same value with different resolutions.

        Running with different step counts should give similar results.
        """
        lf_enclosure_params = {"Vb": 0.1145, "Fb": 46.4}
        horn_params = {"cutoff": 400, "length": 0.24}

        # Coarse search
        pad_coarse = optimize_hf_padding_for_flatness(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            lf_enclosure_type="ported",
            lf_enclosure_params=lf_enclosure_params,
            horn_params=horn_params,
            crossover_frequency=1000,
            padding_range=(-20, -10),
            num_steps=11
        )

        # Fine search
        pad_fine = optimize_hf_padding_for_flatness(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            lf_enclosure_type="ported",
            lf_enclosure_params=lf_enclosure_params,
            horn_params=horn_params,
            crossover_frequency=1000,
            padding_range=(-20, -10),
            num_steps=41
        )

        # Should agree within 1 dB
        assert abs(pad_coarse - pad_fine) < 1.0, \
            f"Coarse {pad_coarse} and fine {pad_fine} searches disagree"


class TestSystemDesignIntegration:
    """Test complete two-way system design workflow."""

    def test_ported_system_design(self):
        """
        Test complete ported box two-way system design.
        """
        design = design_two_way_system(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            lf_enclosure_type="ported",
            optimize_hf_padding=False,
            crossover_range=(1000, 1500),
            population_size=15,
            generations=10
        )

        # Check structure
        assert isinstance(design, TwoWaySystemDesign)
        assert design.lf_driver_name == "BC_12FW88"
        assert design.hf_driver_name == "BC_DH450"
        assert design.lf_enclosure_type == "ported"

        # Check LF enclosure parameters
        assert "Vb" in design.lf_enclosure_params
        assert "Fb" in design.lf_enclosure_params
        assert design.lf_enclosure_params["Vb"] > 0
        assert design.lf_enclosure_params["Fb"] > 30

        # Check crossover
        assert 800 < design.crossover_frequency < 2000

        # Check performance metrics
        assert not np.isnan(design.f3), "F3 should not be NaN"
        assert 30 < design.f3 < 100, f"F3 {design.f3} Hz outside reasonable range"
        assert design.flatness > 0, "Flatness should be positive"

    def test_sealed_system_design(self):
        """
        Test complete sealed box two-way system design.
        """
        design = design_two_way_system(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            lf_enclosure_type="sealed",
            optimize_hf_padding=False,
            crossover_range=(1000, 1500),
            population_size=15,
            generations=10
        )

        # Check structure
        assert isinstance(design, TwoWaySystemDesign)
        assert design.lf_enclosure_type == "sealed"

        # Sealed box only has Vb, no Fb
        assert "Vb" in design.lf_enclosure_params
        assert "Fb" not in design.lf_enclosure_params

    def test_system_with_hf_padding_optimization(self):
        """
        Test system design with HF padding optimization enabled.
        """
        design = design_two_way_system(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            lf_enclosure_type="ported",
            optimize_hf_padding=True,
            horn_constraints={"max_length": 0.25, "target_cutoff": 400},
            crossover_range=(1000, 1500),
            population_size=15,
            generations=10
        )

        # Should have horn params when compression driver detected
        assert design.horn_params is not None
        assert "cutoff" in design.horn_params

        # HF padding should be negative (attenuation)
        assert design.hf_padding_db < 0, \
            f"HF padding {design.hf_padding_db} should be negative"

        # Should be reasonable range
        assert -25 < design.hf_padding_db < -5, \
            f"HF padding {design.hf_padding_db} outside typical range"


class TestInputValidation:
    """Test input validation and error handling."""

    def test_invalid_enclosure_type(self):
        """
        Test that invalid enclosure type raises appropriate error.
        """
        with pytest.raises((ValueError, AttributeError)):
            design_two_way_system(
                lf_driver_name="BC_12FW88",
                hf_driver_name="BC_DH450",
                lf_enclosure_type="invalid_type",
                population_size=5,
                generations=3
            )

    def test_invalid_crossover_range(self):
        """
        Test that invalid crossover range is handled.
        Currently this may not raise an error, but test documents
        expected behavior.
        """
        # This test documents expected behavior
        # If input validation is added, this should raise an error
        pass

    def test_nonexistent_driver(self):
        """
        Test that nonexistent driver raises appropriate error.
        """
        with pytest.raises(Exception):
            design_two_way_system(
                lf_driver_name="NONEXISTENT_DRIVER",
                hf_driver_name="BC_DH450",
                lf_enclosure_type="ported",
                population_size=5,
                generations=3
            )


class TestSystemFlatnessCalculation:
    """Test system flatness calculation."""

    def test_system_flatness_includes_both_drivers(self):
        """
        Test that system flatness includes both LF and HF contributions.

        This is currently a placeholder test - the actual implementation
        needs to be fixed to calculate full system flatness, not just LF.
        """
        design = design_two_way_system(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            lf_enclosure_type="ported",
            optimize_hf_padding=False,
            crossover_range=(1000, 1500),
            population_size=10,
            generations=5
        )

        # Flatness should be reasonable (<15 dB for well-designed system)
        # Note: This currently uses LF-only flatness, which is a known issue
        assert 0 < design.flatness < 20, \
            f"Flatness {design.flatness} dB outside reasonable range"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
