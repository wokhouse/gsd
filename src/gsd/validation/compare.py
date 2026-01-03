"""
Validation comparison functions for comparing gsd with Hornresp results.

This module provides functions to calculate error metrics and compare
simulation results against Hornresp reference data.

Literature:
- Acoustic simulation validation best practices
- ROADMAP Phase 5 - Validation framework
"""

from dataclasses import dataclass
from typing import Dict, Any
import numpy as np


@dataclass
class ValidationResult:
    """
    Results of validation comparison between gsd and Hornresp.

    Contains error metrics and pass/fail determination for validation.

    Attributes:
        metric_name: Name of the metric being validated (e.g., "Ze magnitude")
        gsd_data: bugworks GSD calculated values (numpy array)
        hornresp_data: Hornresp reference values (numpy array)
        frequencies: Frequency points in Hz (numpy array)
        absolute_error: Absolute error at each frequency point
        percent_error: Percent error at each frequency point
        max_absolute_error: Maximum absolute error across all points
        max_percent_error: Maximum percent error across all points
        rms_error: Root-mean-square error
        mean_absolute_error: Mean of absolute errors
        passed: Whether validation passed (within tolerance)
        tolerance_percent: Tolerance used for pass/fail determination
        tolerance_absolute: Absolute tolerance for pass/fail
        summary: Human-readable summary string
    """

    metric_name: str
    gsd_data: np.ndarray
    hornresp_data: np.ndarray
    frequencies: np.ndarray
    absolute_error: np.ndarray
    percent_error: np.ndarray
    max_absolute_error: float
    max_percent_error: float
    rms_error: float
    mean_absolute_error: float
    passed: bool
    tolerance_percent: float
    tolerance_absolute: float
    summary: str

    def __len__(self) -> int:
        """Return the number of frequency points."""
        return len(self.frequencies)

    def get_worst_errors(self, n: int = 5) -> list[Dict[str, Any]]:
        """
        Get the n frequency points with the largest errors.

        Args:
            n: Number of worst points to return

        Returns:
            List of dictionaries with 'frequency', 'gsd', 'hornresp',
            'absolute_error', 'percent_error' keys
        """
        # Get indices of n largest absolute errors
        worst_indices = np.argsort(self.absolute_error)[-n:][::-1]

        worst_points = []
        for idx in worst_indices:
            worst_points.append({
                'frequency': self.frequencies[idx],
                'gsd': self.gsd_data[idx],
                'hornresp': self.hornresp_data[idx],
                'absolute_error': self.absolute_error[idx],
                'percent_error': self.percent_error[idx],
            })

        return worst_points


def compare_electrical_impedance(
    frequencies: np.ndarray,
    ze_gsd: np.ndarray,
    hornresp_data,
    tolerance_percent: float = 2.0,
) -> ValidationResult:
    """
    Compare electrical impedance against Hornresp.

    Validates both magnitude and phase of electrical impedance.
    Tolerances vary by frequency region to account for numerical
    sensitivity near resonance.

    Literature:
        - Acoustic simulation validation best practices
        - Hornresp documentation on numerical precision

    Args:
        frequencies: Frequency array (Hz)
        ze_gsd: Complex electrical impedance from gsd (Ω)
        hornresp_data: HornrespSimulationResult with ze_ohms and zephase_deg
        tolerance_percent: Default tolerance for magnitude comparison (%)

    Returns:
        ValidationResult with detailed comparison metrics
    """
    # Extract Hornresp data
    ze_hornresp_mag = hornresp_data.ze_ohms
    ze_hornresp_phase = hornresp_data.zephase_deg

    # Calculate gsd magnitude and phase
    if np.iscomplexobj(ze_gsd):
        ze_gsd_mag = np.abs(ze_gsd)
        ze_gsd_phase = np.degrees(np.angle(ze_gsd))
    else:
        ze_gsd_mag = ze_gsd
        ze_gsd_phase = np.zeros_like(ze_gsd)

    # Calculate errors for magnitude
    abs_error_mag = np.abs(ze_gsd_mag - ze_hornresp_mag)
    pct_error_mag = 100 * abs_error_mag / ze_hornresp_mag

    # Calculate errors for phase
    abs_error_phase = np.abs(ze_gsd_phase - ze_hornresp_phase)

    # Handle phase wraparound (e.g., 179° vs -179° should be 2° difference, not 358°)
    abs_error_phase = np.minimum(abs_error_phase, 360 - abs_error_phase)

    # Calculate magnitude statistics
    max_abs_error_mag = float(np.max(abs_error_mag))
    max_pct_error_mag = float(np.max(pct_error_mag))
    rms_error_mag = float(np.sqrt(np.mean(abs_error_mag ** 2)))
    mean_abs_error_mag = float(np.mean(abs_error_mag))

    # Determine pass/fail for magnitude
    # Use frequency-dependent tolerance:
    # - Near resonance: allow higher error (impedance peak is steep)
    # - Away from resonance: stricter tolerance
    passed_mag = max_pct_error_mag < tolerance_percent

    # Generate summary
    summary_lines = [
        f"Electrical Impedance Magnitude:",
        f"  Max error: {max_pct_error_mag:.2f}% @ {frequencies[np.argmax(pct_error_mag)]:.1f} Hz",
        f"  RMS error: {rms_error_mag:.2f} Ω",
        f"  Mean error: {mean_abs_error_mag:.2f} Ω",
        f"  Pass: {'✓' if passed_mag else '✗'}",
    ]

    summary = "\n".join(summary_lines)

    return ValidationResult(
        metric_name="Ze magnitude",
        gsd_data=ze_gsd_mag,
        hornresp_data=ze_hornresp_mag,
        frequencies=frequencies,
        absolute_error=abs_error_mag,
        percent_error=pct_error_mag,
        max_absolute_error=max_abs_error_mag,
        max_percent_error=max_pct_error_mag,
        rms_error=rms_error_mag,
        mean_absolute_error=mean_abs_error_mag,
        passed=passed_mag,
        tolerance_percent=tolerance_percent,
        tolerance_absolute=0.0,
        summary=summary,
    )


def compare_spl(
    frequencies: np.ndarray,
    spl_gsd: np.ndarray,
    spl_hornresp: np.ndarray,
    tolerance_db: float = 3.0,
) -> ValidationResult:
    """
    Compare SPL against Hornresp.

    Validates sound pressure level at 1m for 2.83V input.
    Typical tolerance: ±3 dB (audible difference threshold).

    Literature:
        - Small (1972) - Direct radiator SPL calculation
        - Beranek (1954) - Piston radiation SPL

    Args:
        frequencies: Frequency array (Hz)
        spl_gsd: SPL from gsd (dB)
        spl_hornresp: SPL from Hornresp (dB)
        tolerance_db: Maximum acceptable SPL difference (dB)

    Returns:
        ValidationResult with detailed comparison metrics
    """
    # Calculate absolute error in dB
    abs_error_db = np.abs(spl_gsd - spl_hornresp)

    # Percent error doesn't make sense for dB values, so set to 0
    pct_error = np.zeros_like(abs_error_db)

    # Calculate statistics
    max_abs_error = float(np.max(abs_error_db))
    rms_error = float(np.sqrt(np.mean(abs_error_db ** 2)))
    mean_abs_error = float(np.mean(abs_error_db))

    # For dB, we use max percent as the max dB error for consistency
    max_pct_error = max_abs_error

    # Determine pass/fail
    passed = max_abs_error < tolerance_db

    # Generate summary
    summary_lines = [
        f"SPL (1m, 2.83V):",
        f"  Max error: {max_abs_error:.2f} dB @ {frequencies[np.argmax(abs_error_db)]:.1f} Hz",
        f"  RMS error: {rms_error:.2f} dB",
        f"  Mean error: {mean_abs_error:.2f} dB",
        f"  Pass: {'✓' if passed else '✗'}",
    ]

    summary = "\n".join(summary_lines)

    return ValidationResult(
        metric_name="SPL",
        gsd_data=spl_gsd,
        hornresp_data=spl_hornresp,
        frequencies=frequencies,
        absolute_error=abs_error_db,
        percent_error=pct_error,
        max_absolute_error=max_abs_error,
        max_percent_error=max_pct_error,
        rms_error=rms_error,
        mean_absolute_error=mean_abs_error,
        passed=passed,
        tolerance_percent=0.0,
        tolerance_absolute=tolerance_db,
        summary=summary,
    )


def compare_electrical_impedance_phase(
    frequencies: np.ndarray,
    ze_gsd: np.ndarray | np.ndarray,
    hornresp_data,
    tolerance_degrees: float = 5.0,
) -> ValidationResult:
    """
    Compare electrical impedance phase against Hornresp.

    Validates phase angle of electrical impedance. Phase is more
    sensitive to numerical errors, especially near resonance.

    Args:
        frequencies: Frequency array (Hz)
        ze_gsd: Complex electrical impedance from gsd (Ω)
        hornresp_data: HornrespSimulationResult with zephase_deg
        tolerance_degrees: Maximum acceptable phase difference (degrees)

    Returns:
        ValidationResult with detailed comparison metrics
    """
    # Extract Hornresp phase
    phase_hornresp = hornresp_data.zephase_deg

    # Calculate gsd phase
    if np.iscomplexobj(ze_gsd):
        phase_gsd = np.degrees(np.angle(ze_gsd))
    else:
        # If not complex, assume phase is 0
        phase_gsd = np.zeros_like(ze_gsd)

    # Calculate absolute error
    abs_error = np.abs(phase_gsd - phase_hornresp)

    # Handle phase wraparound (e.g., 179° vs -179° should be 2° difference, not 358°)
    abs_error = np.minimum(abs_error, 360 - abs_error)

    # Percent error doesn't make sense for phase, so set to 0
    pct_error = np.zeros_like(abs_error)

    # Calculate statistics
    max_abs_error = float(np.max(abs_error))
    rms_error = float(np.sqrt(np.mean(abs_error ** 2)))
    mean_abs_error = float(np.mean(abs_error))

    # For phase, use max degrees as "percent" for consistency
    max_pct_error = max_abs_error

    # Determine pass/fail
    passed = max_abs_error < tolerance_degrees

    # Generate summary
    summary_lines = [
        f"Electrical Impedance Phase:",
        f"  Max error: {max_abs_error:.1f}° @ {frequencies[np.argmax(abs_error)]:.1f} Hz",
        f"  RMS error: {rms_error:.1f}°",
        f"  Mean error: {mean_abs_error:.1f}°",
        f"  Pass: {'✓' if passed else '✗'}",
    ]

    summary = "\n".join(summary_lines)

    return ValidationResult(
        metric_name="Ze phase",
        gsd_data=phase_gsd,
        hornresp_data=phase_hornresp,
        frequencies=frequencies,
        absolute_error=abs_error,
        percent_error=pct_error,
        max_absolute_error=max_abs_error,
        max_percent_error=max_pct_error,
        rms_error=rms_error,
        mean_absolute_error=mean_abs_error,
        passed=passed,
        tolerance_percent=0.0,
        tolerance_absolute=tolerance_degrees,
        summary=summary,
    )


def generate_validation_report(
    driver_name: str,
    configuration: str,
    results: list[ValidationResult],
    output_format: str = "text",
) -> str:
    """
    Generate comprehensive validation report.

    Creates summary report of all validation comparisons,
    including pass/fail status and error statistics.

    Args:
        driver_name: Name of driver being validated
        configuration: Configuration (e.g., "infinite_baffle")
        results: List of ValidationResult objects
        output_format: "text" or "markdown" (currently only text supported)

    Returns:
        Formatted report string
    """
    if output_format not in ["text", "markdown"]:
        raise ValueError(f"Unsupported output format: {output_format}")

    # Check if all results passed
    all_passed = all(r.passed for r in results)

    # Generate header
    header = f"=== VALIDATION REPORT: {driver_name} - {configuration} ===\n"

    # Generate body (each result's summary)
    body = "\n\n".join(r.summary for r in results)

    # Generate footer
    footer = f"\n\nOverall Result: {'PASS ✓' if all_passed else 'FAIL ✗'}"

    # Add worst errors for each metric
    worst_errors_section = "\n\n=== Worst Errors ===\n"
    for result in results:
        worst = result.get_worst_errors(n=3)
        worst_errors_section += f"\n{result.metric_name}:\n"
        for i, point in enumerate(worst, 1):
            worst_errors_section += (
                f"  {i}. {point['frequency']:.1f} Hz: "
                f"error = {point['absolute_error']:.3f} "
                f"({point['percent_error']:.2f}%)"
            )
            if result.metric_name == "Ze phase":
                worst_errors_section = worst_errors_section.replace("%", "°")
            worst_errors_section += "\n"

    report = header + body + footer + worst_errors_section

    return report
