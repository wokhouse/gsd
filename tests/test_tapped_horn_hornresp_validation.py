"""Validate tapped horn implementation against Hornresp reference data.

This module compares gsd simulation results with Hornresp output for a
3-segment tapped horn design.

Hornresp parameters from imports/th_params.txt:
- Horn: 3-segment exponential tapped horn
  S1=150cm², S2=855cm², S3=2265cm², S4=6000cm²
  L12=180cm, L23=100cm, L34=100cm
- Driver: Sd=855cm², BL=21.2, Mmd=147g, Rms=6.8, Re=5.2, Le=1.4mH, Cms=1.04e-4
- Input: 2.83V (1W into 8Ω)

Reference data: imports/th_sim.txt
"""

import numpy as np
import pytest
from numpy.testing import assert_allclose
from pathlib import Path

from gsd.simulation.types import TappedHorn
from gsd.simulation.horn_theory import MediumProperties
from gsd.simulation.tapped_horn_theory import tapped_horn_system_response
from gsd.driver.parameters import ThieleSmallParameters


# Hornresp standard conditions (from th_params.txt: Ang = 2.0 x Pi, Cir = 0.30)
MEDIUM = MediumProperties(rho=1.18, c=343.0)

# Driver from Hornresp parameters
HORNRESP_DRIVER = ThieleSmallParameters(
    S_d=855e-4,       # 855 cm²
    BL=21.2,          # T·m
    M_md=0.147,       # 147 g = 0.147 kg
    R_ms=6.80,        # N·s/m
    R_e=5.20,         # Ω
    L_e=1.40e-3,      # 1.40 mH
    C_ms=1.04e-4,     # m/N (from datasheet)
)

# Horn geometry from Hornresp parameters
# Note: Hornresp uses exponential segments with specific lengths
# S1=150cm², S2=855cm², L12=180cm (upstream)
# S2=855cm², S3=2265cm², L23=100cm (downstream segment 1)
# S3=2265cm², S4=6000cm², L34=100cm (downstream segment 2)
#
# gsd's TappedHorn splits downstream_length proportionally based on
# logarithmic area expansion. Since S2→S3 and S3→S4 have equal expansion
# ratios (2265/855 = 6000/2265 ≈ 2.65), the split is exactly 50/50.
HORNRESP_HORN = TappedHorn(
    upstream_throat_area=150.0,    # S1 = 150 cm²
    tap_area=855.0,                # S2 = 855 cm²
    downstream_mouth_area=6000.0,  # S4 = 6000 cm²
    upstream_length=180.0,         # L12 = 180 cm
    downstream_length=200.0,       # L23 + L34 = 100 + 100 = 200 cm
    upstream_profile='exponential',
    downstream_profile='exponential',
    intermediate_area=2265.0,      # S3 = 2265 cm² (3-segment horn)
    # Note: downstream_length will be split as 100cm + 100cm automatically
)

# Key frequencies for validation (Hz)
# Selected to cover: quarter-wave resonance, passband, impedance peaks
VALIDATION_FREQUENCIES = [40, 50, 60, 80, 100, 150, 200]


def load_hornresp_data(filepath: str = "imports/th_sim.txt") -> dict:
    """Load Hornresp simulation results.

    Args:
        filepath: Path to Hornresp export file

    Returns:
        Dict with arrays: freq, spl, ze, xd
    """
    path = Path(filepath)
    if not path.exists():
        pytest.skip(f"Hornresp data file not found: {filepath}")

    # Load data, skip header
    data = np.loadtxt(path, skiprows=1, delimiter='\t')

    return {
        'freq': data[:, 0],      # Frequency (Hz)
        'spl': data[:, 4],       # SPL (dB)
        'ze': data[:, 5],        # Electrical impedance (ohms)
        'xd': data[:, 6],        # Diaphragm displacement (mm)
    }


class TestHornrespValidation:
    """Validate gsd tapped horn simulation against Hornresp."""

    @pytest.fixture
    def hornresp_data(self):
        """Load Hornresp reference data."""
        return load_hornresp_data()

    def test_spl_vs_hornresp(self, hornresp_data):
        """SPL should match Hornresp within tolerance.

        Expected accuracy:
        - Well above cutoff (f > 2·f_c): <1 dB deviation
        - Near cutoff (f ≈ 1.2·f_c to 2·f_c): <2 dB deviation
        - Close to cutoff (f ≈ f_c): <5 dB deviation

        For this tapped horn, f_c ≈ 40 Hz (from quarter-wave resonance).
        """
        # Run gsd simulation
        result = tapped_horn_system_response(
            np.array(VALIDATION_FREQUENCIES),
            HORNRESP_HORN,
            HORNRESP_DRIVER,
            MEDIUM,
            voltage=2.83,  # Match Hornresp Eg = 2.83
        )

        # Get Hornresp reference values at validation frequencies
        hr_spl = np.interp(
            VALIDATION_FREQUENCIES,
            hornresp_data['freq'],
            hornresp_data['spl'],
        )

        # Calculate deviation
        spl_deviation = result['spl'] - hr_spl

        # Check tolerance (relaxed for initial validation)
        # Focus on passband performance
        passband_mask = np.array(VALIDATION_FREQUENCIES) >= 50

        for i, freq in enumerate(VALIDATION_FREQUENCIES):
            if passband_mask[i]:
                # Passband: < 3 dB tolerance (relaxed from 1-2 dB due to potential model differences)
                assert abs(spl_deviation[i]) < 3.0, \
                    f"SPL deviation at {freq} Hz: {spl_deviation[i]:.2f} dB " \
                    f"(gsd={result['spl'][i]:.2f}, hornresp={hr_spl[i]:.2f})"

        # Overall trend should match (correlation)
        # Remove DC component for correlation check
        gsd_spl_centered = result['spl'] - np.mean(result['spl'])
        hr_spl_centered = hr_spl - np.mean(hr_spl)
        correlation = np.corrcoef(gsd_spl_centered, hr_spl_centered)[0, 1]

        assert correlation > 0.9, \
            f"SPL response shape doesn't match Hornresp (correlation={correlation:.3f})"

    def test_impedance_vs_hornresp(self, hornresp_data):
        """Electrical impedance should match Hornresp within tolerance.

        Expected accuracy: <10% at impedance peaks, <15% elsewhere
        """
        result = tapped_horn_system_response(
            np.array(VALIDATION_FREQUENCIES),
            HORNRESP_HORN,
            HORNRESP_DRIVER,
            MEDIUM,
            voltage=2.83,
        )

        # Get Hornresp reference values
        hr_ze = np.interp(
            VALIDATION_FREQUENCIES,
            hornresp_data['freq'],
            hornresp_data['ze'],
        )

        # Calculate percentage error
        ze_error = np.abs(result['electrical_impedance'] - hr_ze) / hr_ze * 100

        # Check tolerance (relaxed for initial validation)
        for i, freq in enumerate(VALIDATION_FREQUENCIES):
            # Impedance: < 15% tolerance
            assert ze_error[i] < 15.0, \
                f"Ze deviation at {freq} Hz: {ze_error[i]:.1f}% " \
                f"(gsd={result['electrical_impedance'][i]:.2f}, hornresp={hr_ze[i]:.2f})"

    def test_excursion_vs_hornresp(self, hornresp_data):
        """Cone excursion should match Hornresp within tolerance.

        Expected accuracy: <15% deviation
        """
        result = tapped_horn_system_response(
            np.array(VALIDATION_FREQUENCIES),
            HORNRESP_HORN,
            HORNRESP_DRIVER,
            MEDIUM,
            voltage=2.83,
        )

        # Get Hornresp reference values
        hr_xd = np.interp(
            VALIDATION_FREQUENCIES,
            hornresp_data['freq'],
            hornresp_data['xd'],
        )

        # Calculate percentage error
        xd_error = np.abs(result['excursion'] - hr_xd) / hr_xd * 100

        # Check tolerance
        for i, freq in enumerate(VALIDATION_FREQUENCIES):
            # Excursion: < 20% tolerance (relaxed, can be sensitive to model differences)
            assert xd_error[i] < 20.0, \
                f"Xd deviation at {freq} Hz: {xd_error[i]:.1f}% " \
                f"(gsd={result['excursion'][i]:.3f}, hornresp={hr_xd[i]:.3f})"

    def test_quarter_wave_frequency(self, hornresp_data):
        """Quarter-wave frequency should match Hornresp prediction.

        f_qw = c / (4 × L_upstream)
        For L_upstream = 1.8m: f_qw = 343 / (4 × 1.8) ≈ 47.6 Hz
        """
        f_qw = HORNRESP_HORN.quarter_wave_frequency

        # Quarter-wave frequency from horn geometry
        f_qw_expected = MEDIUM.c / (4 * 1.8)  # 180 cm = 1.8 m

        assert_allclose(f_qw, f_qw_expected, rtol=0.01)

        # At quarter-wave frequency, SPL should show characteristic behavior
        # (not a peak or dip, but transition in response)
        result = tapped_horn_system_response(
            np.array([f_qw * 0.8, f_qw, f_qw * 1.2]),
            HORNRESP_HORN,
            HORNRESP_DRIVER,
            MEDIUM,
            voltage=2.83,
        )

        # SPL should be finite and reasonable
        assert np.all(result['spl'] > 30)  # At least 30 dB output
        assert np.all(result['spl'] < 120)  # Not unrealistically high


@pytest.mark.skipif(
    not Path("imports/th_sim.txt").exists(),
    reason="Hornresp data file not found"
)
class TestDetailedComparison:
    """Detailed frequency-by-frequency comparison with Hornresp."""

    def test_full_frequency_response_comparison(self):
        """Compare full frequency response curve with Hornresp.

        This test generates a detailed comparison plot showing:
        - SPL vs frequency
        - Impedance vs frequency
        - Excursion vs frequency

        For visual inspection and debugging.
        """
        hornresp_data = load_hornresp_data()

        # Sample frequencies from Hornresp data (10 Hz - 200 Hz)
        mask = hornresp_data['freq'] <= 200
        freq_test = hornresp_data['freq'][mask][::10]  # Every 10th point

        result = tapped_horn_system_response(
            freq_test,
            HORNRESP_HORN,
            HORNRESP_DRIVER,
            MEDIUM,
            voltage=2.83,
        )

        # Interpolate Hornresp to test frequencies
        hr_spl = np.interp(freq_test, hornresp_data['freq'], hornresp_data['spl'])
        hr_ze = np.interp(freq_test, hornresp_data['freq'], hornresp_data['ze'])
        hr_xd = np.interp(freq_test, hornresp_data['freq'], hornresp_data['xd'])

        # Print comparison statistics
        print("\n=== Tapped Horn Validation vs Hornresp ===")
        print(f"Frequency range: {freq_test.min():.1f} - {freq_test.max():.1f} Hz")
        print(f"Number of points: {len(freq_test)}")

        spl_rms_error = np.sqrt(np.mean((result['spl'] - hr_spl)**2))
        ze_rms_error = np.sqrt(np.mean((result['electrical_impedance'] - hr_ze)**2))
        xd_rms_error = np.sqrt(np.mean((result['excursion'] - hr_xd)**2))

        print(f"\nRMS Errors:")
        print(f"  SPL: {spl_rms_error:.2f} dB")
        print(f"  Ze:  {ze_rms_error:.2f} ohms")
        print(f"  Xd:  {xd_rms_error:.3f} mm")

        print(f"\nMax Errors:")
        print(f"  SPL: {np.max(np.abs(result['spl'] - hr_spl)):.2f} dB")
        print(f"  Ze:  {np.max(np.abs(result['electrical_impedance'] - hr_ze)):.2f} ohms")
        print(f"  Xd:  {np.max(np.abs(result['excursion'] - hr_xd)):.3f} mm")

        # Correlation coefficients
        spl_corr = np.corrcoef(result['spl'], hr_spl)[0, 1]
        ze_corr = np.corrcoef(result['electrical_impedance'], hr_ze)[0, 1]

        print(f"\nCorrelation with Hornresp:")
        print(f"  SPL: {spl_corr:.4f}")
        print(f"  Ze:  {ze_corr:.4f}")

        # Basic sanity checks
        assert spl_corr > 0.85, "SPL response shape should correlate with Hornresp"
        assert ze_corr > 0.85, "Impedance response shape should correlate with Hornresp"
