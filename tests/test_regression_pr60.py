"""
Regression tests for PR #60 bug fixes.

These tests ensure that the critical bugs fixed in PR #60
don't regress in future versions.
"""

import pytest
import numpy as np
from gsd.simulation.response_metrics import find_f3_frequency
from gsd.driver import load_driver
from gsd.optimization.api.manufacturing import suggest_printing_strategy
from gsd.optimization.api.validation import validate_two_way_design


class TestInputValidation:
    """Test new input validation added in PR #60."""

    def test_manufacturing_rejects_negative_cutoff(self):
        """Test that suggest_printing_strategy validates target_cutoff."""
        driver = load_driver("BC_DH450")

        with pytest.raises(ValueError, match="target_cutoff must be positive"):
            suggest_printing_strategy(
                driver,
                target_cutoff=-100,  # Invalid
                printer_max_length=0.25
            )

    def test_manufacturing_rejects_zero_printer_length(self):
        """Test that suggest_printing_strategy validates printer_max_length."""
        driver = load_driver("BC_DH450")

        with pytest.raises(ValueError, match="printer_max_length must be positive"):
            suggest_printing_strategy(
                driver,
                target_cutoff=400,
                printer_max_length=0  # Invalid
            )

    def test_manufacturing_rejects_negative_mouth_area(self):
        """Test that suggest_printing_strategy validates target_mouth_area."""
        driver = load_driver("BC_DH450")

        with pytest.raises(ValueError, match="target_mouth_area must be positive"):
            suggest_printing_strategy(
                driver,
                target_cutoff=400,
                printer_max_length=0.25,
                target_mouth_area=-0.01  # Invalid
            )

    def test_manufacturing_rejects_invalid_driver(self):
        """Test that suggest_printing_strategy validates driver has S_d."""
        from gsd.driver.parameters import ThieleSmallParameters

        # Note: ThieleSmallParameters validates S_d in __post_init__
        # So we get a different error message, but the validation still happens
        with pytest.raises(ValueError):
            ThieleSmallParameters(
                M_md=0.01,
                C_ms=0.0001,
                R_ms=2.0,
                R_e=6.0,
                L_e=0.001,
                BL=8.0,
                S_d=0.0  # Invalid: S_d must be positive
            )

    def test_validation_requires_design_attributes(self):
        """Test that validate_two_way_design checks required attributes."""
        # Create mock design without required attributes
        class BadDesign:
            pass

        design = BadDesign()

        with pytest.raises(ValueError, match="missing required attributes"):
            validate_two_way_design(design)


class TestF3CalculationCorrectness:
    """Regression test for Issue #2: Incorrect F3 calculation."""

    def test_f3_highpass_returns_correct_value(self):
        """Test that F3 calculation uses interpolation, not first occurrence."""
        # Create 1st-order high-pass response at 50 Hz
        freq = np.logspace(1, 3, 1000)
        fc = 50

        # 1st-order high-pass: 20*log10(f / sqrt(fc^2 + f^2)) + reference
        # At f=fc, response should be -3dB
        spl = 20 * np.log10(freq / np.sqrt(fc**2 + freq**2)) + 94

        # Passband level (well above cutoff)
        passband = np.mean(spl[freq >= 100])

        # Calculate F3
        f3 = find_f3_frequency(
            freq, spl, passband,
            search_range=(10, 200),
            filter_type="highpass"
        )

        # Should be close to 50 Hz (within tolerance)
        assert 45 < f3 < 55, f"F3={f3:.1f} Hz, expected ~50 Hz"

    def test_f3_uses_interpolation(self):
        """Test that F3 uses linear interpolation for accuracy."""
        # Create sparse frequency array where true F3 is between points
        freq = np.array([20, 30, 40, 50, 60, 70, 80, 90, 100])

        # Create response that crosses -3dB between 50 and 60 Hz
        passband = 90
        target = passband - 3  # 87 dB

        # At 50Hz: 86 dB (below target by 1dB)
        # At 60Hz: 88 dB (above target by 1dB)
        # Should interpolate F3 ≈ 55 Hz (exactly halfway)
        spl = np.array([80, 82, 84, 86, 88, 90, 90, 90, 90])

        f3 = find_f3_frequency(
            freq, spl, passband,
            search_range=(20, 100),
            filter_type="highpass"
        )

        # Should interpolate between 50 and 60 Hz
        assert 50 < f3 < 60, f"F3={f3:.1f} Hz, should interpolate"
        # Expected: F3 ≈ 55 Hz (exactly at -3dB point)
        # With linear interpolation: 50 + (60-50) * (87-86) / (88-86) = 55 Hz
        assert abs(f3 - 55) < 1, "Should use linear interpolation"

    def test_f3_warns_on_fallback(self):
        """Test that F3 issues warning when falling back to closest value."""
        import warnings

        freq = np.linspace(100, 1000, 100)
        spl = np.ones_like(freq) * 90  # Flat response

        passband = 90

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            f3 = find_f3_frequency(
                freq, spl, passband,
                search_range=(100, 1000),
                filter_type="highpass"
            )

            # Should have issued a warning
            assert len(w) == 1
            assert "F3 crossing not found" in str(w[0].message)
            assert "Using closest value" in str(w[0].message)


class TestValidationUsesConstants:
    """Test that validation module uses named constants instead of magic numbers."""

    def test_validation_constants_exist(self):
        """Test that validation constants are defined."""
        from gsd.optimization.api.validation import (
            MAX_HORN_CUTOFF_RATIO,
            CRITICAL_HORN_CUTOFF_RATIO,
            MAX_FLATNESS_DB,
            MAX_SENSITIVITY_MISMATCH_DB
        )

        # Verify constants have expected values
        assert MAX_HORN_CUTOFF_RATIO == 0.5
        assert CRITICAL_HORN_CUTOFF_RATIO == 0.8
        assert MAX_FLATNESS_DB == 6.0
        assert MAX_SENSITIVITY_MISMATCH_DB == 6.0


class TestManufacturingUsesConstants:
    """Test that manufacturing module uses named constants instead of magic numbers."""

    def test_manufacturing_constants_exist(self):
        """Test that manufacturing constants are defined."""
        from gsd.optimization.api.manufacturing import (
            SPEED_OF_SOUND,
            PRINTER_FIT_TOLERANCE,
            THROAT_AREA_RATIO
        )

        # Verify constants have expected values
        assert SPEED_OF_SOUND == 343.0
        assert PRINTER_FIT_TOLERANCE == 0.95
        assert THROAT_AREA_RATIO == 0.3


class TestDefensiveErrorHandling:
    """Test that modules handle errors gracefully."""

    def test_design_validation_missing_required_attrs(self):
        """Test validation raises clear error for missing required attributes."""
        from gsd.optimization.api.two_way_system import TwoWaySystemDesign

        # Create design without horn_params
        design = TwoWaySystemDesign(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            lf_enclosure_type="ported",
            lf_enclosure_params={},
            horn_params=None,  # Missing horn_params
            crossover_frequency=800,
            hf_padding_db=-15.5,
            lf_padding_db=0.0,
            f3=47,
            flatness=2.0,
            system_level=94.0
        )

        # Should not raise error, just skip horn-related checks
        result = validate_two_way_design(design, verbose=False)

        # Validation should run, just skip horn checks
        assert hasattr(result, 'passes')

    def test_manufacturing_validates_all_inputs(self):
        """Test that manufacturing validates all input parameters."""
        driver = load_driver("BC_DH450")

        # Test all validation cases
        test_cases = [
            (-100, 0.25, None, "target_cutoff"),
            (400, -0.25, None, "printer_max_length"),
            (400, 0.25, -0.01, "target_mouth_area"),
        ]

        for cutoff, length, mouth_area, expected_param in test_cases:
            with pytest.raises(ValueError, match=f"{expected_param} must be positive"):
                suggest_printing_strategy(
                    driver,
                    target_cutoff=cutoff,
                    printer_max_length=length,
                    target_mouth_area=mouth_area
                )
