"""
Unit tests for validation comparison functions.

Tests the compare functions for correct error metric calculation.
"""

import pytest
import numpy as np

from gsd.validation.compare import (
    ValidationResult,
    compare_electrical_impedance,
    compare_spl,
    compare_electrical_impedance_phase,
    generate_validation_report,
)


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_create_validation_result(self):
        """Test creating a ValidationResult."""
        frequencies = np.array([10, 20, 30])
        viberesp_data = np.array([1.0, 2.0, 3.0])
        hornresp_data = np.array([1.1, 2.1, 3.1])

        result = ValidationResult(
            metric_name="Test metric",
            viberesp_data=viberesp_data,
            hornresp_data=hornresp_data,
            frequencies=frequencies,
            absolute_error=np.array([0.1, 0.1, 0.1]),
            percent_error=np.array([10.0, 9.09, 9.09]),
            max_absolute_error=0.1,
            max_percent_error=10.0,
            rms_error=0.1,
            mean_absolute_error=0.1,
            passed=True,
            tolerance_percent=2.0,
            tolerance_absolute=0.0,
            summary="Test summary",
        )

        assert result.metric_name == "Test metric"
        assert result.passed == True
        assert len(result) == 3

    def test_get_worst_errors(self):
        """Test getting worst error points."""
        frequencies = np.array([10, 20, 30, 40, 50])
        viberesp_data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        hornresp_data = np.array([1.01, 2.02, 3.15, 4.05, 5.01])  # Largest error at 30 Hz

        abs_error = np.abs(viberesp_data - hornresp_data)
        pct_error = 100 * abs_error / hornresp_data

        result = ValidationResult(
            metric_name="Test",
            viberesp_data=viberesp_data,
            hornresp_data=hornresp_data,
            frequencies=frequencies,
            absolute_error=abs_error,
            percent_error=pct_error,
            max_absolute_error=0.15,
            max_percent_error=5.0,
            rms_error=0.1,
            mean_absolute_error=0.1,
            passed=True,
            tolerance_percent=10.0,
            tolerance_absolute=0.0,
            summary="Test",
        )

        worst = result.get_worst_errors(n=2)

        assert len(worst) == 2
        assert worst[0]['frequency'] == 30.0  # Worst error
        assert worst[0]['absolute_error'] == pytest.approx(0.15)


class TestCompareElectricalImpedance:
    """Test electrical impedance comparison function."""

    def test_compare_impedance_magnitude(self):
        """Test comparing impedance magnitude."""
        frequencies = np.array([10, 20, 30])
        ze_viberesp = np.array([5.0 + 1j, 6.0 + 2j, 7.0 + 3j])

        # Mock Hornresp data
        class MockHornrespData:
            ze_ohms = np.array([5.1, 6.1, 7.1])
            zephase_deg = np.array([10, 15, 20])

        hornresp_data = MockHornrespData()

        result = compare_electrical_impedance(frequencies, ze_viberesp, hornresp_data)

        assert result.metric_name == "Ze magnitude"
        assert isinstance(result, ValidationResult)
        assert len(result) == 3
        assert result.max_percent_error > 0

    def test_perfect_match_passes(self):
        """Test that perfect match passes validation."""
        frequencies = np.array([10, 20, 30])
        ze_viberesp = np.array([5.0, 6.0, 7.0])

        class MockHornrespData:
            ze_ohms = np.array([5.0, 6.0, 7.0])
            zephase_deg = np.array([0, 0, 0])

        hornresp_data = MockHornrespData()

        result = compare_electrical_impedance(frequencies, ze_viberesp, hornresp_data, tolerance_percent=1.0)

        assert result.passed == True
        assert result.max_percent_error == 0.0


class TestCompareSPL:
    """Test SPL comparison function."""

    def test_compare_spl(self):
        """Test comparing SPL values."""
        frequencies = np.array([100, 200, 300])
        spl_viberesp = np.array([80, 85, 90])
        spl_hornresp = np.array([81, 86, 91])

        result = compare_spl(frequencies, spl_viberesp, spl_hornresp, tolerance_db=3.0)

        assert result.metric_name == "SPL"
        assert isinstance(result, ValidationResult)
        assert result.max_absolute_error == pytest.approx(1.0)

    def test_spl_within_tolerance(self):
        """Test that SPL within tolerance passes."""
        frequencies = np.array([100])
        spl_viberesp = np.array([80.0])
        spl_hornresp = np.array([82.0])  # 2 dB difference

        result = compare_spl(frequencies, spl_viberesp, spl_hornresp, tolerance_db=3.0)

        assert result.passed == True
        assert result.max_absolute_error == 2.0

    def test_spl_outside_tolerance(self):
        """Test that SPL outside tolerance fails."""
        frequencies = np.array([100])
        spl_viberesp = np.array([80.0])
        spl_hornresp = np.array([84.0])  # 4 dB difference

        result = compare_spl(frequencies, spl_viberesp, spl_hornresp, tolerance_db=3.0)

        assert result.passed == False
        assert result.max_absolute_error == 4.0


class TestCompareImpedancePhase:
    """Test impedance phase comparison function."""

    def test_compare_phase(self):
        """Test comparing phase values."""
        frequencies = np.array([100, 200, 300])
        ze_viberesp = np.array([5.0 + 1j, 6.0 + 2j, 7.0 + 3j])

        class MockHornrespData:
            ze_ohms = np.array([5.0, 6.0, 7.0])
            zephase_deg = np.array([11, 18, 23])

        hornresp_data = MockHornrespData()

        result = compare_electrical_impedance_phase(frequencies, ze_viberesp, hornresp_data, tolerance_degrees=5.0)

        assert result.metric_name == "Ze phase"
        assert isinstance(result, ValidationResult)
        assert result.max_absolute_error > 0

    def test_phase_wraparound(self):
        """Test phase wraparound handling (179° vs -179°)."""
        frequencies = np.array([100])
        ze_viberesp = np.array([1.0 + 0j])  # 0° phase

        class MockHornrespData:
            ze_ohms = np.array([1.0])
            zephase_deg = np.array([359])  # -1° phase (stored as 359°)

        hornresp_data = MockHornrespData()

        result = compare_electrical_impedance_phase(frequencies, ze_viberesp, hornresp_data)

        # Should handle wraparound: difference should be 1°, not 359°
        assert result.max_absolute_error < 5.0


class TestGenerateValidationReport:
    """Test validation report generation."""

    def test_generate_report(self):
        """Test generating validation report."""
        # Create mock results
        result1 = ValidationResult(
            metric_name="Ze magnitude",
            viberesp_data=np.array([5.0]),
            hornresp_data=np.array([5.1]),
            frequencies=np.array([100]),
            absolute_error=np.array([0.1]),
            percent_error=np.array([2.0]),
            max_absolute_error=0.1,
            max_percent_error=2.0,
            rms_error=0.1,
            mean_absolute_error=0.1,
            passed=True,
            tolerance_percent=2.0,
            tolerance_absolute=0.0,
            summary="Ze: Max error: 2.0%\n  Pass: ✓",
        )

        result2 = ValidationResult(
            metric_name="SPL",
            viberesp_data=np.array([80.0]),
            hornresp_data=np.array([81.0]),
            frequencies=np.array([100]),
            absolute_error=np.array([1.0]),
            percent_error=np.array([0.0]),
            max_absolute_error=1.0,
            max_percent_error=1.0,
            rms_error=1.0,
            mean_absolute_error=1.0,
            passed=True,
            tolerance_percent=0.0,
            tolerance_absolute=3.0,
            summary="SPL: Max error: 1.0 dB\n  Pass: ✓",
        )

        report = generate_validation_report(
            "Test Driver",
            "infinite_baffle",
            [result1, result2],
            output_format="text"
        )

        assert "VALIDATION REPORT: Test Driver" in report
        assert "infinite_baffle" in report
        assert "Ze magnitude" in report
        assert "SPL" in report
        assert "Overall Result: PASS" in report
        assert "Worst Errors" in report

    def test_report_with_failure(self):
        """Test report shows failure when any result fails."""
        result = ValidationResult(
            metric_name="Test",
            viberesp_data=np.array([5.0]),
            hornresp_data=np.array([6.0]),
            frequencies=np.array([100]),
            absolute_error=np.array([1.0]),
            percent_error=np.array([20.0]),
            max_absolute_error=1.0,
            max_percent_error=20.0,
            rms_error=1.0,
            mean_absolute_error=1.0,
            passed=False,  # Failed
            tolerance_percent=5.0,
            tolerance_absolute=0.0,
            summary="Test: Max error: 20.0%\n  Pass: ✗",
        )

        report = generate_validation_report(
            "Test Driver",
            "test_config",
            [result],
            output_format="text"
        )

        assert "Overall Result: FAIL" in report
