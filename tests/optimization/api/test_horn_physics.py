"""
Unit tests for horn physics module.

Tests cover:
- LF driver beaming frequency calculation
- Horn Fc calculation from crossover target
- Mouth area calculation from target Fc
- Fc calculation from mouth geometry (inverse function)
- Round-trip accuracy (forward and inverse functions)
- Mouth area feasibility assessment

Literature:
- Olson (1947) - Horn cutoff and flare theory
- Beranek (1954) - Directivity and radiation impedance
- literature/horns/olson_1947.md
- literature/horns/beranek_1954.md
"""

import pytest
import numpy as np
from numpy.testing import assert_allclose

from gsd.optimization.api.horn_physics import (
    calculate_lf_beaming_frequency,
    calculate_target_horn_fc,
    calculate_mouth_area_for_fc,
    calculate_fc_from_mouth,
    assess_mouth_area_feasibility,
    HornFeasibilityResult
)
from gsd.driver import load_driver


class TestLFBeamingFrequency:
    """Test LF driver beaming frequency calculation."""

    def test_bc_12fw88_beaming(self):
        """
        Test beaming frequency for BC 12FW88 driver.

        For 12" driver (S_d ≈ 530 cm²), expected beaming ~840 Hz.

        Literature: Beranek (1954), Chapter 5 - Directivity of circular pistons
        Expected: f_beam = 2c/(π×d) ≈ 840 Hz ± 50 Hz
        """
        driver = load_driver("BC_12FW88")
        f_beam = calculate_lf_beaming_frequency(driver)

        # Should be around 840 Hz for 12" driver
        assert 790 < f_beam < 890, f"Beaming {f_beam:.0f} Hz outside expected range"

    def test_bc_8ndl51_beaming(self):
        """
        Test beaming frequency for BC 8NDL51 driver.

        For 8" driver (S_d ≈ 215 cm²), expected beaming ~1300 Hz.

        Literature: Beranek (1954), Chapter 5 - Directivity of circular pistons
        Expected: f_beam = 2c/(π×d) ≈ 1305 Hz
        """
        driver = load_driver("BC_8NDL51")
        f_beam = calculate_lf_beaming_frequency(driver)

        # Should be around 1300 Hz for 8" driver
        assert 1200 < f_beam < 1400, f"Beaming {f_beam:.0f} Hz outside expected range"

    def test_beaming_scales_with_diameter(self):
        """
        Test that beaming frequency scales inversely with diameter.

        Larger drivers should beam at lower frequencies.
        f_beam ∝ 1/d
        """
        driver_12 = load_driver("BC_12FW88")
        driver_8 = load_driver("BC_8NDL51")

        f_beam_12 = calculate_lf_beaming_frequency(driver_12)
        f_beam_8 = calculate_lf_beaming_frequency(driver_8)

        # 12" driver should beam at lower frequency than 8"
        assert f_beam_12 < f_beam_8, \
            f"12\" driver ({f_beam_12:.0f} Hz) should beam lower than 8\" ({f_beam_8:.0f} Hz)"


class TestTargetHornFc:
    """Test target horn Fc calculation from crossover target."""

    def test_traditional_2x_ratio(self):
        """
        Test traditional 2×Fc rule.

        For XO=800Hz with 2×Fc rule, target Fc should be 400Hz.

        Literature: Olson (1947) - Horn should operate 2 octaves above cutoff
        """
        fc = calculate_target_horn_fc(800, xo_fc_ratio=2.0)
        assert_allclose(fc, 400, rtol=0.01)

    def test_optimized_13x_ratio(self):
        """
        Test optimized 1.3×Fc rule.

        For XO=800Hz with 1.3×Fc rule, target Fc should be ~615Hz.

        Literature: Case study shows 1.28×Fc works well
        """
        fc = calculate_target_horn_fc(800, xo_fc_ratio=1.3)
        assert_allclose(fc, 800/1.3, rtol=0.01)

    def test_capped_at_beaming(self):
        """
        Test that XO is capped at LF beaming frequency.

        When desired XO > 0.8×beaming, should cap at 0.8×beaming.
        """
        f_beam = 840  # Hz

        # Desired XO above 0.8×beaming
        desired_xo = 1000  # Hz
        expected_xo_cap = 0.8 * f_beam  # 672 Hz

        fc = calculate_target_horn_fc(
            desired_xo,
            lf_driver_beaming_hz=f_beam,
            xo_fc_ratio=2.0
        )

        # Fc should be based on capped XO
        expected_fc = expected_xo_cap / 2.0
        assert_allclose(fc, expected_fc, rtol=0.01)

    def test_no_cap_when_below_beaming(self):
        """
        Test that XO is not capped when below beaming.

        When desired XO < 0.8×beaming, should use desired XO directly.
        """
        f_beam = 840  # Hz

        # Desired XO below 0.8×beaming (672 Hz)
        desired_xo = 600  # Hz

        fc = calculate_target_horn_fc(
            desired_xo,
            lf_driver_beaming_hz=f_beam,
            xo_fc_ratio=2.0
        )

        # Fc should be based on desired XO (no cap)
        expected_fc = desired_xo / 2.0
        assert_allclose(fc, expected_fc, rtol=0.01)

    def test_no_beaming_constraint(self):
        """
        Test that function works without beaming constraint.

        When lf_driver_beaming_hz is None, should use desired XO directly.
        """
        fc = calculate_target_horn_fc(800, lf_driver_beaming_hz=None, xo_fc_ratio=2.0)
        assert_allclose(fc, 400, rtol=0.01)


class TestMouthAreaForFc:
    """Test mouth area calculation from target Fc."""

    def test_mouth_for_400hz_fc(self):
        """
        Test mouth area calculation for 400Hz Fc.

        For 250mm horn, 7cm² throat, 400Hz Fc:
        Expected mouth ~273 cm²

        Literature: Olson (1947), Eq. 5.18 - Horn cutoff frequency
        Calculation: mouth = throat × exp((4π × Fc × L) / c)
        """
        mouth = calculate_mouth_area_for_fc(7.0, 25.0, 400)

        # Should be around 273 cm²
        assert 270 < mouth < 280, f"Mouth {mouth:.0f} cm² outside expected range"

    def test_mouth_for_500hz_fc(self):
        """
        Test mouth area calculation for 500Hz Fc.

        Higher Fc requires larger mouth (for fixed length).
        """
        mouth_400 = calculate_mouth_area_for_fc(7.0, 25.0, 400)
        mouth_500 = calculate_mouth_area_for_fc(7.0, 25.0, 500)

        # Higher Fc should require larger mouth
        assert mouth_500 > mouth_400, \
            f"500Hz Fc ({mouth_500:.0f} cm²) should require larger mouth than 400Hz ({mouth_400:.0f} cm²)"

    def test_mouth_scales_with_length(self):
        """
        Test that required mouth scales with horn length.

        Longer horn requires larger mouth for same Fc (exponential growth).
        """
        mouth_short = calculate_mouth_area_for_fc(7.0, 15.0, 400)
        mouth_long = calculate_mouth_area_for_fc(7.0, 35.0, 400)

        # Longer horn should require much larger mouth (exponential)
        assert mouth_long > mouth_short * 2, \
            f"35cm horn ({mouth_long:.0f} cm²) should require >2× mouth of 15cm horn ({mouth_short:.0f} cm²)"

    def test_mouth_scales_with_throat(self):
        """
        Test that mouth area scales with throat area.

        Larger throat requires proportionally larger mouth for same Fc.
        """
        mouth_small_throat = calculate_mouth_area_for_fc(5.0, 25.0, 400)
        mouth_large_throat = calculate_mouth_area_for_fc(10.0, 25.0, 400)

        # Mouth should scale proportionally with throat
        ratio = mouth_large_throat / mouth_small_throat
        expected_ratio = 10.0 / 5.0  # 2.0

        assert_allclose(ratio, expected_ratio, rtol=0.1), \
            f"Mouth ratio {ratio:.2f} should match throat ratio {expected_ratio:.2f}"


class TestFcFromMouth:
    """Test Fc calculation from mouth geometry."""

    def test_fc_from_mouth_250cm2(self):
        """
        Test Fc calculation for 250cm² mouth.

        For 7cm² throat, 25cm length, 250cm² mouth:
        Expected Fc ~390 Hz

        Literature: Olson (1947), Eq. 5.18
        Inverse of calculate_mouth_area_for_fc
        """
        fc = calculate_fc_from_mouth(7.0, 250.0, 25.0)

        # Should be around 390 Hz
        assert 380 < fc < 400, f"Fc {fc:.0f} Hz outside expected range"

    def test_fc_from_mouth_504cm2(self):
        """
        Test Fc calculation for 504cm² mouth.

        For 7cm² throat, 25cm length, 504cm² mouth:
        Expected Fc ~467 Hz

        Literature: Olson (1947), Eq. 5.18
        Note: Case study document has error - claims 1865 Hz but correct value is 467 Hz
        """
        fc = calculate_fc_from_mouth(7.0, 504.0, 25.0)

        # Should be around 467 Hz (correct physics calculation)
        assert 450 < fc < 500, f"Fc {fc:.0f} Hz outside expected range"

    def test_fc_increases_with_mouth(self):
        """
        Test that Fc increases with mouth area.

        Larger mouth → higher flare constant → higher cutoff frequency.
        """
        fc_small_mouth = calculate_fc_from_mouth(7.0, 200.0, 25.0)
        fc_large_mouth = calculate_fc_from_mouth(7.0, 400.0, 25.0)

        # Larger mouth should give higher Fc
        assert fc_large_mouth > fc_small_mouth, \
            f"400cm² mouth (Fc={fc_large_mouth:.0f} Hz) should give higher Fc than 200cm² (Fc={fc_small_mouth:.0f} Hz)"


class TestRoundTripAccuracy:
    """Test round-trip accuracy of inverse functions."""

    def test_round_trip_400hz(self):
        """
        Test forward and inverse functions agree.

        Calculate mouth from Fc, then Fc from mouth - should get same Fc.

        Literature: Inverse functions should be accurate within 1 Hz
        """
        fc_original = 400.0

        # Forward: mouth = f(fc)
        mouth = calculate_mouth_area_for_fc(7.0, 25.0, fc_original)

        # Inverse: fc = f(mouth)
        fc_recovered = calculate_fc_from_mouth(7.0, mouth, 25.0)

        # Should agree within 1 Hz
        assert abs(fc_original - fc_recovered) < 1.0, \
            f"Round-trip error: {fc_original} Hz → {mouth:.0f} cm² → {fc_recovered:.2f} Hz"

    def test_round_trip_multiple_frequencies(self):
        """
        Test round-trip accuracy across multiple frequencies.

        Test range: 200 - 1000 Hz
        """
        test_frequencies = [200, 300, 400, 500, 600, 800, 1000]

        for fc_original in test_frequencies:
            mouth = calculate_mouth_area_for_fc(7.0, 25.0, fc_original)
            fc_recovered = calculate_fc_from_mouth(7.0, mouth, 25.0)

            error = abs(fc_original - fc_recovered)
            assert error < 1.0, \
                f"Round-trip error at {fc_original} Hz: {error:.2f} Hz"

    def test_round_trip_multiple_lengths(self):
        """
        Test round-trip accuracy across multiple horn lengths.

        Test range: 10 - 40 cm
        """
        test_lengths = [10, 15, 20, 25, 30, 35, 40]

        for length_cm in test_lengths:
            fc_original = 400.0
            mouth = calculate_mouth_area_for_fc(7.0, length_cm, fc_original)
            fc_recovered = calculate_fc_from_mouth(7.0, mouth, length_cm)

            error = abs(fc_original - fc_recovered)
            assert error < 1.0, \
                f"Round-trip error at {length_cm} cm: {error:.2f} Hz"


class TestMouthAreaFeasibility:
    """Test mouth area feasibility assessment."""

    def test_feasible_design(self):
        """
        Test feasible design (required mouth <= available mouth).

        Should return feasible=True with no penalty.
        """
        result = assess_mouth_area_feasibility(
            required_mouth_cm2=273,
            available_mouth_cm2=625,
            target_fc_hz=400
        )

        assert result['feasible'] is True
        assert result['sensitivity_penalty_db'] == 0.0
        assert "fits constraint" in result['recommendation'].lower()

    def test_infeasible_design(self):
        """
        Test infeasible design (required mouth > available mouth).

        Should return feasible=False with recommendations.

        Note: Smaller mouth gives LOWER Fc, not higher.
        Fc = (c/4π) × (1/L) × ln(mouth/throat)
        """
        result = assess_mouth_area_feasibility(
            required_mouth_cm2=500,
            available_mouth_cm2=250,
            target_fc_hz=400,
            throat_area_cm2=7.0,
            length_cm=25.0
        )

        assert result['feasible'] is False
        assert 'resulting_fc_hz' in result
        assert 'sensitivity_penalty_db' in result
        assert result['sensitivity_penalty_db'] < 0  # Loss

        # Resulting Fc should be lower than target (smaller mouth → lower Fc)
        # 250cm² mouth → ~390 Hz, which is lower than 400 Hz target
        assert result['resulting_fc_hz'] < result['target_fc_hz']

    def test_sensitivity_penalty_estimate(self):
        """
        Test sensitivity penalty estimation.

        Penalty should follow 10×log10(available/required) approximation.
        """
        required = 500
        available = 250

        result = assess_mouth_area_feasibility(
            required_mouth_cm2=required,
            available_mouth_cm2=available,
            target_fc_hz=400
        )

        # Penalty should be approximately 10×log10(250/500) = -3 dB
        expected_penalty = 10 * np.log10(available / required)

        assert_allclose(
            result['sensitivity_penalty_db'],
            expected_penalty,
            rtol=0.01
        )

    def test_recommendation_format(self):
        """
        Test that recommendation is properly formatted.

        Recommendation should list alternatives.
        """
        result = assess_mouth_area_feasibility(
            required_mouth_cm2=500,
            available_mouth_cm2=250,
            target_fc_hz=400
        )

        rec = result['recommendation']

        # Should mention options
        assert "multi-piece" in rec.lower() or "options" in rec.lower()
        assert len(rec) > 50  # Should be detailed


class TestHornFeasibilityResult:
    """Test HornFeasibilityResult dataclass."""

    def test_feasible_result_str(self):
        """Test string representation of feasible result."""
        result = HornFeasibilityResult(
            feasible=True,
            target_fc_hz=400,
            required_mouth_cm2=273,
            available_mouth_cm2=625,
            recommendation="Design with 273cm² mouth (fits constraint)"
        )

        s = str(result)

        assert "FEASIBLE" in s
        assert "400 Hz" in s
        assert "273" in s

    def test_infeasible_result_str(self):
        """Test string representation of infeasible result."""
        result = HornFeasibilityResult(
            feasible=False,
            target_fc_hz=400,
            required_mouth_cm2=500,
            available_mouth_cm2=250,
            resulting_fc_hz=550,
            sensitivity_penalty_db=-3.0,
            recommendation="Use multi-piece horn"
        )

        s = str(result)

        assert "NOT FEASIBLE" in s
        assert "550 Hz" in s
        assert "-3.0 dB" in s
