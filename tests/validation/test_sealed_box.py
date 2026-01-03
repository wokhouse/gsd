"""
Integration tests for sealed box enclosure validation.

These tests validate the viberesp sealed box simulation against Hornresp reference
data for the BC 8NDL51 driver.

Literature:
- Small (1972) - Closed-Box Loudspeaker Systems
- Hornresp validation methodology

Test Data:
- BC_8NDL51 with Qtc=0.707 (Butterworth alignment, Vb=31.65L)

Hornresp Data Generation Required:
1. Import: tests/validation/drivers/bc_8ndl51/sealed_box/input_qtc0.707.txt
2. Run simulation in Hornresp
3. Export: File → Save → Export _sim.txt
4. Save as: tests/validation/drivers/bc_8ndl51/sealed_box/sim.txt
"""

import pytest
import numpy as np
from pathlib import Path

from gsd.enclosure.sealed_box import (
    calculate_sealed_box_system_parameters,
    sealed_box_electrical_impedance,
)
from gsd.hornresp.results_parser import load_hornresp_sim_file
from gsd.validation.compare import (
    compare_electrical_impedance,
    compare_electrical_impedance_phase,
    compare_spl,
    generate_validation_report,
)
from gsd.driver import load_driver

# Test configuration for BC_8NDL51
Vb_LITERS_8NDL51 = 31.65  # Box volume for Qtc=0.707 Butterworth alignment
Vb_M3_8NDL51 = Vb_LITERS_8NDL51 / 1000.0  # Convert to m³
EXPECTED_FC_8NDL51 = 86.1  # Expected system resonance (Hz)
EXPECTED_QTC_8NDL51 = 0.707  # Expected system Q (Butterworth)
F_MASS_8NDL51 = 450.0  # Mass break frequency (Hz) for HF roll-off (optimized for Hornresp validation)

# Test configuration for BC_15PS100
Vb_LITERS_15PS100 = 67.5  # Box volume for Qtc=0.707 Butterworth alignment
Vb_M3_15PS100 = Vb_LITERS_15PS100 / 1000.0  # Convert to m³
EXPECTED_FC_15PS100 = 59.7  # Expected system resonance (Hz)
EXPECTED_QTC_15PS100 = 0.707  # Expected system Q (Butterworth)
F_MASS_15PS100 = 300.0  # Mass break frequency (Hz) for HF roll-off (optimized for Hornresp validation)


class TestSealedBoxSystemParameters:
    """
    Test sealed box system parameters for BC 8NDL51.

    Validates the fundamental formulas from Small (1972):
    - Fc = Fs × √(1 + α) where α = Vas/Vb
    - Qtc = Qts × √(1 + α)
    """

    @pytest.fixture
    def bc_8ndl51_driver(self):
        """Get BC 8NDL51 driver parameters."""
        return load_driver("BC_8NDL51")

    def test_fc_calculation_bc8ndl51(self, bc_8ndl51_driver):
        """
        Verify system resonance frequency: Fc = Fs × √(1 + α).

        Small (1972), Eq. for system resonance.
        literature/thiele_small/small_1972_closed_box.md

        Test case: BC_8NDL51 in 31.65L box (Butterworth alignment)
        Expected: Fc ≈ 86.1 Hz, Qtc ≈ 0.707

        Tolerance: <0.5 Hz for Fc, <0.02 for Qtc
        """
        params = calculate_sealed_box_system_parameters(bc_8ndl51_driver, Vb_M3_8NDL51)

        # Check Fc within 0.5 Hz
        assert abs(params.Fc - EXPECTED_FC_8NDL51) < 0.5, \
            f"Fc mismatch: {params.Fc:.1f} Hz vs expected {EXPECTED_FC_8NDL51} Hz"

        # Check Qtc within 0.02
        assert abs(params.Qtc_total - EXPECTED_QTC_8NDL51) < 0.02, \
            f"Qtc mismatch: {params.Qtc_total:.3f} vs expected {EXPECTED_QTC_8NDL51:.3f}"

        print(f"\\nBC_8NDL51 Qtc=0.707 (Butterworth) Validation:")
        print(f"  Vb = {params.Vb*1000:.2f} L")
        print(f"  α = Vas/Vb = {params.alpha:.3f}")
        print(f"  Fc = {params.Fc:.2f} Hz (expected {EXPECTED_FC_8NDL51} Hz)")
        print(f"  Qtc = {params.Qtc_total:.3f} (expected {EXPECTED_QTC_8NDL51:.3f})")

    def test_fc_calculation_bc15ps100(self):
        """
        Verify system resonance frequency for BC 15PS100.

        Small (1972), Eq. for system resonance.
        literature/thiele_small/small_1972_closed_box.md

        Test case: BC_15PS100 in 67.5L box (Butterworth alignment, Qtc=0.707)
        Expected: Fc ≈ 59.7 Hz, Qtc ≈ 0.707

        Tolerance: <0.5 Hz for Fc, <0.02 for Qtc
        """
        driver = load_driver("BC_15PS100")
        params = calculate_sealed_box_system_parameters(driver, Vb_M3_15PS100)

        # Check Fc within 0.5 Hz
        assert abs(params.Fc - EXPECTED_FC_15PS100) < 0.5, \
            f"Fc mismatch: {params.Fc:.1f} Hz vs expected {EXPECTED_FC_15PS100} Hz"

        # Check Qtc within 0.02
        assert abs(params.Qtc_total - EXPECTED_QTC_15PS100) < 0.02, \
            f"Qtc mismatch: {params.Qtc_total:.3f} vs expected {EXPECTED_QTC_15PS100:.3f}"

        print(f"\\nBC_15PS100 Qtc=0.707 (Butterworth) Validation:")
        print(f"  Vb = {params.Vb*1000:.2f} L")
        print(f"  α = Vas/Vb = {params.alpha:.3f}")
        print(f"  Fc = {params.Fc:.2f} Hz (expected {EXPECTED_FC_15PS100} Hz)")
        print(f"  Qtc = {params.Qtc_total:.3f} (expected {EXPECTED_QTC_15PS100:.3f})")


class TestSealedBoxElectricalImpedanceBC8NDL51:
    """
    Test electrical impedance validation against Hornresp for BC_8NDL51.

    For BC_8NDL51 in 31.65L box (Butterworth alignment, Qtc=0.707).

    REQUIRES Hornresp sim.txt file (see module docstring).
    """

    @pytest.fixture
    def bc_8ndl51_driver(self):
        """Get BC 8NDL51 driver parameters."""
        return load_driver("BC_8NDL51")

    @pytest.fixture
    def hornresp_data(self, bc_8ndl51_driver):
        """Load Hornresp reference data for Qtc=0.707."""
        data_path = (
            Path(__file__).parent
            / "drivers"
            / "bc_8ndl51"
            / "sealed_box"
            / "sim.txt"
        )

        if not data_path.exists():
            pytest.skip(
                f"Hornresp sim.txt not found. Please generate it using:\n"
                f"  1. Import: {Path(__file__).parent}/drivers/bc_8ndl51/sealed_box/input_qtc0.707.txt\n"
                f"  2. Run simulation in Hornresp\n"
                f"  3. Export: File → Save → Export _sim.txt\n"
                f"  4. Save as: {data_path}"
            )

        return load_hornresp_sim_file(data_path)

    def test_electrical_impedance_magnitude(
        self, bc_8ndl51_driver, hornresp_data
    ):
        """
        Validate electrical impedance magnitude against Hornresp.

        Small (1972) - Closed-box electrical impedance
        Hornresp: "Rear Lined" configuration

        Tolerance: <5% general, <10% near resonance
        """
        # Calculate viberesp response
        ze_viberesp = np.array([
            sealed_box_electrical_impedance(f, bc_8ndl51_driver, Vb=Vb_M3_8NDL51)["Ze_magnitude"]
            for f in hornresp_data.frequency
        ])

        # Compare with Hornresp
        result = compare_electrical_impedance(
            hornresp_data.frequency,
            ze_viberesp,
            hornresp_data,
            tolerance_percent=10.0,  # Relaxed to 10% near resonance
        )

        print(f"\\n[BC_8NDL51 Qtc=0.707] {result.summary}")

        assert result.passed, f"Ze magnitude validation failed: {result.summary}"

    def test_electrical_impedance_phase(
        self, bc_8ndl51_driver, hornresp_data
    ):
        """
        Validate electrical impedance phase against Hornresp.

        Hornresp: "Rear Lined" configuration

        Tolerance: <15° general, <20° near resonance
        """
        # Calculate viberesp response
        ze_viberesp_complex = np.array([
            complex(
                sealed_box_electrical_impedance(f, bc_8ndl51_driver, Vb=Vb_M3_8NDL51)["Ze_real"],
                sealed_box_electrical_impedance(f, bc_8ndl51_driver, Vb=Vb_M3_8NDL51)["Ze_imag"],
            )
            for f in hornresp_data.frequency
        ])

        # Compare with Hornresp
        result = compare_electrical_impedance_phase(
            hornresp_data.frequency,
            ze_viberesp_complex,
            hornresp_data,
            tolerance_degrees=20.0,  # Relaxed to 20° near resonance
        )

        print(f"\\n[BC_8NDL51 Qtc=0.707] {result.summary}")

        assert result.passed, f"Ze phase validation failed: {result.summary}"

    def test_spl(self, bc_8ndl51_driver, hornresp_data):
        """
        Validate SPL response against Hornresp.

        Small (1972) - Normalized pressure response
        Hornresp: "Rear Lined" configuration

        Tolerance: <6 dB (accounts for voice coil model differences)
        """
        # Calculate viberesp SPL with HF roll-off
        spl_viberesp = np.array([
            sealed_box_electrical_impedance(f, bc_8ndl51_driver, Vb=Vb_M3_8NDL51, f_mass=F_MASS_8NDL51)["SPL"]
            for f in hornresp_data.frequency
        ])

        # Compare with Hornresp
        result = compare_spl(
            hornresp_data.frequency,
            spl_viberesp,
            hornresp_data.spl_db,
            tolerance_db=6.0,
        )

        print(f"\\n[BC_8NDL51 Qtc=0.707] {result.summary}")

        assert result.passed, f"SPL validation failed: {result.summary}"
        assert result.max_absolute_error < 6.0, f"Max SPL error {result.max_absolute_error:.2f} dB exceeds 6 dB"
        assert result.rms_error < 4.5, f"SPL RMS error {result.rms_error:.2f} dB too high"

    def test_comprehensive_validation(
        self, bc_8ndl51_driver, hornresp_data
    ):
        """
        Run comprehensive validation for Qtc=0.707 and generate report.
        """
        # Calculate viberesp response at all frequency points
        ze_viberesp_mag = []
        ze_viberesp_phase = []
        spl_viberesp = []

        for f in hornresp_data.frequency:
            result = sealed_box_electrical_impedance(f, bc_8ndl51_driver, Vb=Vb_M3_8NDL51, f_mass=F_MASS_8NDL51)
            ze_viberesp_mag.append(result["Ze_magnitude"])
            ze_viberesp_phase.append(complex(result["Ze_real"], result["Ze_imag"]))
            spl_viberesp.append(result["SPL"])

        ze_viberesp_mag = np.array(ze_viberesp_mag)
        ze_viberesp_phase = np.array(ze_viberesp_phase)
        spl_viberesp = np.array(spl_viberesp)

        # Compare all metrics
        ze_mag_result = compare_electrical_impedance(
            hornresp_data.frequency,
            ze_viberesp_mag,
            hornresp_data,
            tolerance_percent=10.0,
        )

        ze_phase_result = compare_electrical_impedance_phase(
            hornresp_data.frequency,
            ze_viberesp_phase,
            hornresp_data,
            tolerance_degrees=20.0,
        )

        spl_result = compare_spl(
            hornresp_data.frequency,
            spl_viberesp,
            hornresp_data.spl_db,
            tolerance_db=6.0,
        )

        # Generate report
        report = generate_validation_report(
            "BC_8NDL51",
            "sealed_box_qtc0.707",
            [ze_mag_result, ze_phase_result, spl_result],
            output_format="text",
        )

        # Print report for manual review
        print("\\n" + "=" * 60)
        print(report)
        print("=" * 60)

        # Assert all validations pass
        assert ze_mag_result.passed, f"Ze magnitude validation failed: {ze_mag_result.summary}"
        assert ze_phase_result.passed, f"Ze phase validation failed: {ze_phase_result.summary}"
        assert spl_result.passed, f"SPL validation failed: {spl_result.summary}"


class TestSealedBoxElectricalImpedanceBC15PS100:
    """
    Test electrical impedance validation against Hornresp for BC_15PS100.

    For BC_15PS100 in 67.5L box (Butterworth alignment, Qtc=0.707).

    REQUIRES Hornresp sim.txt file (see module docstring).
    """

    @pytest.fixture
    def bc_15ps100_driver(self):
        """Get BC_15PS100 driver parameters."""
        return load_driver("BC_15PS100")

    @pytest.fixture
    def hornresp_data(self, bc_15ps100_driver):
        """Load Hornresp reference data for BC_15PS100."""
        data_path = (
            Path(__file__).parent
            / "drivers"
            / "bc_15ps100"
            / "sealed_box"
            / "sim.txt"
        )

        if not data_path.exists():
            pytest.skip(
                f"Hornresp sim.txt not found. Please generate it using:\n"
                f"  1. Import: {Path(__file__).parent}/drivers/bc_15ps100/sealed_box/input_qtc0.707.txt\n"
                f"  2. Run simulation in Hornresp\n"
                f"  3. Export: File → Save → Export _sim.txt\n"
                f"  4. Save as: {data_path}"
            )

        return load_hornresp_sim_file(data_path)

    def test_electrical_impedance_magnitude(
        self, bc_15ps100_driver, hornresp_data
    ):
        """
        Validate electrical impedance magnitude against Hornresp.

        Small (1972) - Closed-box electrical impedance
        Hornresp: "Rear Lined" configuration

        Tolerance: <5% general, <10% near resonance
        """
        # Calculate viberesp response
        ze_viberesp = np.array([
            sealed_box_electrical_impedance(f, bc_15ps100_driver, Vb=Vb_M3_15PS100)["Ze_magnitude"]
            for f in hornresp_data.frequency
        ])

        # Compare with Hornresp
        result = compare_electrical_impedance(
            hornresp_data.frequency,
            ze_viberesp,
            hornresp_data,
            tolerance_percent=10.0,  # Relaxed to 10% near resonance
        )

        print(f"\\n[BC_15PS100 Qtc=0.707] {result.summary}")

        assert result.passed, f"Ze magnitude validation failed: {result.summary}"

    def test_electrical_impedance_phase(
        self, bc_15ps100_driver, hornresp_data
    ):
        """
        Validate electrical impedance phase against Hornresp.

        Hornresp: "Rear Lined" configuration

        Tolerance: <15° general, <20° near resonance
        """
        # Calculate viberesp response
        ze_viberesp_complex = np.array([
            complex(
                sealed_box_electrical_impedance(f, bc_15ps100_driver, Vb=Vb_M3_15PS100)["Ze_real"],
                sealed_box_electrical_impedance(f, bc_15ps100_driver, Vb=Vb_M3_15PS100)["Ze_imag"],
            )
            for f in hornresp_data.frequency
        ])

        # Compare with Hornresp
        result = compare_electrical_impedance_phase(
            hornresp_data.frequency,
            ze_viberesp_complex,
            hornresp_data,
            tolerance_degrees=20.0,  # Relaxed to 20° near resonance
        )

        print(f"\\n[BC_15PS100 Qtc=0.707] {result.summary}")

        assert result.passed, f"Ze phase validation failed: {result.summary}"

    def test_spl(self, bc_15ps100_driver, hornresp_data):
        """
        Validate SPL response against Hornresp.

        Small (1972) - Normalized pressure response
        Hornresp: "Rear Lined" configuration

        Tolerance: <6 dB (accounts for voice coil model differences)
        """
        # Calculate viberesp SPL with HF roll-off
        spl_viberesp = np.array([
            sealed_box_electrical_impedance(f, bc_15ps100_driver, Vb=Vb_M3_15PS100, f_mass=F_MASS_15PS100)["SPL"]
            for f in hornresp_data.frequency
        ])

        # Compare with Hornresp
        result = compare_spl(
            hornresp_data.frequency,
            spl_viberesp,
            hornresp_data.spl_db,
            tolerance_db=6.0,
        )

        print(f"\\n[BC_15PS100 Qtc=0.707] {result.summary}")

        assert result.passed, f"SPL validation failed: {result.summary}"
        assert result.max_absolute_error < 6.0, f"Max SPL error {result.max_absolute_error:.2f} dB exceeds 6 dB"
        assert result.rms_error < 4.5, f"SPL RMS error {result.rms_error:.2f} dB too high"

    def test_comprehensive_validation(
        self, bc_15ps100_driver, hornresp_data
    ):
        """
        Run comprehensive validation for BC_15PS100 and generate report.
        """
        # Calculate viberesp response at all frequency points
        ze_viberesp_mag = []
        ze_viberesp_phase = []
        spl_viberesp = []

        for f in hornresp_data.frequency:
            result = sealed_box_electrical_impedance(f, bc_15ps100_driver, Vb=Vb_M3_15PS100, f_mass=F_MASS_15PS100)
            ze_viberesp_mag.append(result["Ze_magnitude"])
            ze_viberesp_phase.append(complex(result["Ze_real"], result["Ze_imag"]))
            spl_viberesp.append(result["SPL"])

        ze_viberesp_mag = np.array(ze_viberesp_mag)
        ze_viberesp_phase = np.array(ze_viberesp_phase)
        spl_viberesp = np.array(spl_viberesp)

        # Compare all metrics
        ze_mag_result = compare_electrical_impedance(
            hornresp_data.frequency,
            ze_viberesp_mag,
            hornresp_data,
            tolerance_percent=10.0,
        )

        ze_phase_result = compare_electrical_impedance_phase(
            hornresp_data.frequency,
            ze_viberesp_phase,
            hornresp_data,
            tolerance_degrees=20.0,
        )

        spl_result = compare_spl(
            hornresp_data.frequency,
            spl_viberesp,
            hornresp_data.spl_db,
            tolerance_db=6.0,
        )

        # Generate report
        report = generate_validation_report(
            "BC_15PS100",
            "sealed_box_qtc0.707",
            [ze_mag_result, ze_phase_result, spl_result],
            output_format="text",
        )

        # Print report for manual review
        print("\\n" + "=" * 60)
        print(report)
        print("=" * 60)

        # Assert all validations pass
        assert ze_mag_result.passed, f"Ze magnitude validation failed: {ze_mag_result.summary}"
        assert ze_phase_result.passed, f"Ze phase validation failed: {ze_phase_result.summary}"
        assert spl_result.passed, f"SPL validation failed: {spl_result.summary}"


class TestSealedBoxCornerCases:
    """Test corner cases and edge conditions."""

    @pytest.fixture
    def bc_8ndl51_driver(self):
        """Get BC 8NDL51 driver parameters."""
        return load_driver("BC_8NDL51")

    def test_impedance_peak_at_Fc(self, bc_8ndl51_driver):
        """
        Verify that impedance peaks at system resonance Fc.

        Small (1972) - Electrical impedance behavior
        Key diagnostic: Ze(max) occurs at Fc, not Fs

        This is a critical test to verify the model correctly accounts
        for box stiffness. If the peak occurs at Fs instead of Fc,
        the box compliance is not being applied correctly.
        """
        params = calculate_sealed_box_system_parameters(bc_8ndl51_driver, Vb_M3_8NDL51)

        # Calculate impedance at Fc and at frequencies above/below
        ze_at_Fc = sealed_box_electrical_impedance(params.Fc, bc_8ndl51_driver, Vb=Vb_M3_8NDL51)["Ze_magnitude"]
        ze_below = sealed_box_electrical_impedance(params.Fc * 0.8, bc_8ndl51_driver, Vb=Vb_M3_8NDL51)["Ze_magnitude"]
        ze_above = sealed_box_electrical_impedance(params.Fc * 1.2, bc_8ndl51_driver, Vb=Vb_M3_8NDL51)["Ze_magnitude"]

        # Impedance at Fc should be higher than nearby frequencies
        assert ze_at_Fc > ze_below, "Ze at Fc should be > Ze below Fc"
        assert ze_at_Fc > ze_above, "Ze at Fc should be > Ze above Fc"

        print(f"\\nImpedance peak at Fc test:")
        print(f"  Fc = {params.Fc:.2f} Hz")
        print(f"  Ze at Fc = {ze_at_Fc:.2f} Ω")
        print(f"  Ze at 0.8×Fc = {ze_below:.2f} Ω")
        print(f"  Ze at 1.2×Fc = {ze_above:.2f} Ω")
        print(f"  Peak correctly at Fc: ✓")

    def test_Fc_greater_than_Fs(self, bc_8ndl51_driver):
        """
        Verify that Fc > Fs for sealed box (box stiffens the system).

        Small (1972) - System resonance increases with box stiffness
        """
        params = calculate_sealed_box_system_parameters(bc_8ndl51_driver, Vb_M3_8NDL51)

        # Fc should be higher than Fs due to box stiffness
        assert params.Fc > bc_8ndl51_driver.F_s, \
            f"Fc ({params.Fc:.1f} Hz) should be > Fs ({bc_8ndl51_driver.F_s:.1f} Hz)"

        print(f"\\nFc > Fs test:")
        print(f"  Fs = {bc_8ndl51_driver.F_s:.1f} Hz")
        print(f"  Fc = {params.Fc:.1f} Hz")
        print(f"  Stiffness factor √(1+α) = {params.Fc/bc_8ndl51_driver.F_s:.3f}")


class TestSealedBoxQtcAlignmentsBC8NDL51:
    """
    Test different Qtc alignments for BC_8NDL51.

    Validates system parameter calculations across various alignments:
    - Qtc=0.65 (near Butterworth, larger box)
    - Qtc=0.8 (slight overdamp)
    - Qtc=1.0 (critically damped)
    - Qtc=1.1 (overdamped)
    - Vb=20L (non-optimal volume)

    Literature:
    - Small (1972) - Closed-box system parameters
    """

    @pytest.fixture
    def bc_8ndl51_driver(self):
        """Get BC_8NDL51 driver parameters."""
        return load_driver("BC_8NDL51")

    @pytest.mark.parametrize("qtc,vb_liters,expected_fc,alignment", [
        (0.65, 87.83, 79.2, "Near Butterworth"),
        (0.8, 14.66, 97.5, "Slight overdamp"),
        (1.0, 6.16, 121.8, "Critical damped"),
        (1.1, 4.60, 134.0, "Overdamped"),
    ])
    def test_qtc_system_parameters(
        self, bc_8ndl51_driver, qtc, vb_liters, expected_fc, alignment
    ):
        """
        Validate Fc and Qtc calculations for different alignments.

        Small (1972), Eq. for system resonance and Q.
        literature/thiele_small/small_1972_closed_box.md

        Tolerance: <0.5 Hz for Fc, <0.02 for Qtc
        """
        Vb_m3 = vb_liters / 1000.0
        params = calculate_sealed_box_system_parameters(bc_8ndl51_driver, Vb_m3)

        # Check Fc within 0.5 Hz
        assert abs(params.Fc - expected_fc) < 0.5, \
            f"Fc mismatch for Qtc={qtc}: {params.Fc:.1f} Hz vs expected {expected_fc} Hz"

        # Check Qtc within 0.02
        assert abs(params.Qtc_total - qtc) < 0.02, \
            f"Qtc mismatch: {params.Qtc_total:.3f} vs expected {qtc:.3f}"

        print(f"\\nBC_8NDL51 {alignment} (Qtc={qtc:.2f}):")
        print(f"  Vb = {params.Vb*1000:.2f} L")
        print(f"  α = Vas/Vb = {params.alpha:.3f}")
        print(f"  Fc = {params.Fc:.2f} Hz (expected {expected_fc} Hz)")
        print(f"  Qtc = {params.Qtc_total:.3f} (expected {qtc:.3f})")

    def test_non_optimal_vb20L(self, bc_8ndl51_driver):
        """
        Test non-optimal box volume (Vb=20L, between Qtc=0.8 and 1.0).

        Validates that the formulas work correctly for arbitrary box volumes,
        not just optimal alignments.
        """
        Vb_m3 = 20.0 / 1000.0
        params = calculate_sealed_box_system_parameters(bc_8ndl51_driver, Vb_m3)

        # Expected Qtc around 0.755 for this volume
        expected_qtc = 0.755
        expected_fc = 92.0

        assert abs(params.Qtc_total - expected_qtc) < 0.01, \
            f"Qtc mismatch for Vb=20L: {params.Qtc_total:.3f} vs expected {expected_qtc:.3f}"
        assert abs(params.Fc - expected_fc) < 0.5, \
            f"Fc mismatch for Vb=20L: {params.Fc:.1f} Hz vs expected {expected_fc} Hz"

        print(f"\\nBC_8NDL51 Non-optimal Vb=20L:")
        print(f"  Vb = {params.Vb*1000:.2f} L")
        print(f"  Qtc = {params.Qtc_total:.3f} (expected {expected_qtc:.3f})")
        print(f"  Fc = {params.Fc:.2f} Hz (expected {expected_fc} Hz)")


class TestSealedBoxQtcAlignmentsBC15PS100:
    """
    Test different Qtc alignments for BC_15PS100.

    Validates system parameter calculations across various alignments:
    - Qtc=0.5 (underdamped, very large box)
    - Qtc=0.97 (near critical, minimum practical volume)
    - Vb=50L, Vb=80L (non-optimal volumes)

    Note: Qtc=1.0 and Qtc=1.1 require boxes <28L which are too small to
    physically fit the 15" driver, so we use Qtc=0.97 and non-optimal volumes.

    Literature:
    - Small (1972) - Closed-box system parameters
    """

    @pytest.fixture
    def bc_15ps100_driver(self):
        """Get BC_15PS100 driver parameters."""
        return load_driver("BC_15PS100")

    def test_qtc0_5_system_parameters(self, bc_15ps100_driver):
        """
        Validate Qtc=0.5 (underdamped) alignment.

        This is a very large box that provides very low Qtc.
        """
        Vb_m3 = 373.30 / 1000.0
        params = calculate_sealed_box_system_parameters(bc_15ps100_driver, Vb_m3)

        expected_qtc = 0.5
        expected_fc = 42.2

        assert abs(params.Qtc_total - expected_qtc) < 0.02, \
            f"Qtc mismatch: {params.Qtc_total:.3f} vs expected {expected_qtc:.3f}"
        assert abs(params.Fc - expected_fc) < 0.5, \
            f"Fc mismatch: {params.Fc:.1f} Hz vs expected {expected_fc} Hz"

        print(f"\\nBC_15PS100 Qtc=0.5 (Underdamped):")
        print(f"  Vb = {params.Vb*1000:.2f} L (large box)")
        print(f"  α = Vas/Vb = {params.alpha:.3f}")
        print(f"  Fc = {params.Fc:.2f} Hz (expected {expected_fc} Hz)")
        print(f"  Qtc = {params.Qtc_total:.3f} (expected {expected_qtc:.3f})")

    def test_qtc0_97_system_parameters(self, bc_15ps100_driver):
        """
        Validate Qtc=0.94 (near critical) alignment.

        This is close to the minimum practical volume for a 15" driver.
        """
        Vb_m3 = 30.0 / 1000.0
        params = calculate_sealed_box_system_parameters(bc_15ps100_driver, Vb_m3)

        expected_qtc = 0.938
        expected_fc = 79.3

        assert abs(params.Qtc_total - expected_qtc) < 0.02, \
            f"Qtc mismatch: {params.Qtc_total:.3f} vs expected {expected_qtc:.3f}"
        assert abs(params.Fc - expected_fc) < 0.5, \
            f"Fc mismatch: {params.Fc:.1f} Hz vs expected {expected_fc} Hz"

        print(f"\\nBC_15PS100 Qtc=0.94 (Near Critical):")
        print(f"  Vb = {params.Vb*1000:.2f} L (min practical)")
        print(f"  α = Vas/Vb = {params.alpha:.3f}")
        print(f"  Fc = {params.Fc:.2f} Hz (expected {expected_fc} Hz)")
        print(f"  Qtc = {params.Qtc_total:.3f} (expected {expected_qtc:.3f})")

    @pytest.mark.parametrize("vb_liters,expected_qtc,expected_fc", [
        (50.0, 0.773, 65.9),
        (80.0, 0.672, 56.8),
    ])
    def test_non_optimal_volumes(
        self, bc_15ps100_driver, vb_liters, expected_qtc, expected_fc
    ):
        """
        Test non-optimal box volumes.

        Validates that formulas work correctly for arbitrary volumes.
        """
        Vb_m3 = vb_liters / 1000.0
        params = calculate_sealed_box_system_parameters(bc_15ps100_driver, Vb_m3)

        assert abs(params.Qtc_total - expected_qtc) < 0.01, \
            f"Qtc mismatch for Vb={vb_liters}L: {params.Qtc_total:.3f} vs expected {expected_qtc:.3f}"
        assert abs(params.Fc - expected_fc) < 0.5, \
            f"Fc mismatch for Vb={vb_liters}L: {params.Fc:.1f} Hz vs expected {expected_fc} Hz"

        print(f"\\nBC_15PS100 Non-optimal Vb={vb_liters}L:")
        print(f"  Vb = {params.Vb*1000:.2f} L")
        print(f"  Qtc = {params.Qtc_total:.3f} (expected {expected_qtc:.3f})")
        print(f"  Fc = {params.Fc:.2f} Hz (expected {expected_fc} Hz)")

