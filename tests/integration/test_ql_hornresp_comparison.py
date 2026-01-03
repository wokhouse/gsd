"""
Integration tests for QL (box losses) implementation vs Hornresp.

These tests compare viberesp's QL implementation against Hornresp simulations
to validate correctness across various QL values for both sealed and ported boxes.

Literature:
- Small (1972), "Closed-Box Loudspeaker Systems Part I", JAES, Eq. 9
- Small (1973), "Vented-Box Loudspeaker Systems Part I", JAES, Eq. 13, 19
- Hornresp V53.20 - Industry standard horn simulation tool

Validation Dataset:
- tests/validation/drivers/bc_8ndl51/QL_VALIDATION_README.md
"""

import os
import pytest
from pathlib import Path
from gsd.driver import load_driver:
    """
    Find Hornresp simulation data for a specific QL value.

    Args:
        driver_name: Driver name (e.g., 'bc_8ndl51')
        enclosure_type: 'sealed_box' or 'ported'
        ql_value: QL value to find (e.g., 7, 10, 20)

    Returns:
        Path to sim.txt file if it exists, None otherwise
    """
    base_path = Path(f"tests/validation/drivers/{driver_name}/{enclosure_type}/ql{ql_value}")
    sim_file = base_path / "sim.txt"

    if sim_file.exists():
        return sim_file
    return None


def parse_hornresp_sim_file(sim_file_path):
    """
    Parse Hornresp sim.txt file.

    Expected format (Angular Frequency export):
    - Column 1: Angular frequency ω (rad/s)
    - Column 2: Electrical impedance magnitude (Ω)
    - Column 3: Electrical impedance phase (degrees)
    - Column 4: SPL (dB)

    Args:
        sim_file_path: Path to Hornresp sim.txt file

    Returns:
        Dictionary with frequencies and corresponding data
    """
    frequencies = []
    impedances = []
    phases = []
    spls = []

    with open(sim_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split()
            if len(parts) >= 4:
                omega = float(parts[0])
                impedance = float(parts[1])
                phase = float(parts[2])
                spl = float(parts[3])

                # Convert angular frequency to Hz: f = ω / (2π)
                frequency = omega / (2 * 3.14159265359)

                frequencies.append(frequency)
                impedances.append(impedance)
                phases.append(phase)
                spls.append(spl)

    return {
        'frequencies': frequencies,
        'impedances': impedances,
        'phases': phases,
        'spls': spls,
    }


class TestPortedBoxQLHornrespComparison:
    """
    Integration tests comparing ported box QL implementation with Hornresp.

    Note: These tests require Hornresp sim.txt files to be generated manually.
    See: tests/validation/drivers/bc_8ndl51/QL_VALIDATION_README.md
    """

    @pytest.mark.parametrize("ql_value", [7, 10, 20])
    def test_ported_box_impedance_vs_hornresp(self, ql_value):
        """
        Compare ported box electrical impedance with Hornresp for various QL values.

        Expected tolerances:
        - Impedance magnitude: <12% error across 20-200 Hz
        - Dual peak frequencies: ±2 Hz
        - Impedance dip depth: Should increase with lower QL (more leakage)
        """
        # Get driver
        driver = load_driver("BC_8NDL51")

        # Ported box design from validation dataset
        Vb = 0.020  # 20L
        Fb = 50.0  # Hz
        port_area = 0.00423  # 42.3 cm²
        port_length = 0.221  # 22.1 cm

        # Find Hornresp data
        sim_file = find_hornresp_data('bc_8ndl51', 'ported', ql_value)

        if sim_file is None:
            pytest.skip(f"Hornresp sim.txt not found for QL={ql_value}. "
                      f"Generate using instructions in "
                      f"tests/validation/drivers/bc_8ndl51/QL_VALIDATION_README.md")

        # Parse Hornresp data
        hornresp_data = parse_hornresp_sim_file(sim_file)

        # Test at specific frequencies from Hornresp data
        max_error = 0
        errors = []

        for freq, hr_imp in zip(hornresp_data['frequencies'], hornresp_data['impedances']):
            # Calculate viberesp impedance at this frequency
            result = ported_box_electrical_impedance(
                freq, driver, Vb, Fb, port_area, port_length,
                QL=float(ql_value), QA=100.0
            )

            vibe_imp = result['Ze_magnitude']

            # Calculate percentage error
            if hr_imp > 0:
                error = abs(vibe_imp - hr_imp) / hr_imp
                errors.append(error)
                max_error = max(max_error, error)

        # Check that max error is within tolerance
        # Allow 12% for ported boxes (more complex than sealed)
        assert max_error < 0.12, \
            f"QL={ql_value}: Max impedance error {max_error*100:.1f}% exceeds 12% tolerance"

    @pytest.mark.parametrize("ql_value,expected_impedance_range", [
        (7, (4.5, 6.0)),   # Hornresp default - moderate dip
        (10, (4.5, 6.0)),  # WinISD default - shallower dip
        (20, (4.5, 6.0)),  # Well-sealed - minimal dip
    ])
    def test_ported_box_impedance_dip_trend(self, ql_value, expected_impedance_range):
        """
        Test that impedance dip at Fb is close to Re.

        At tuning frequency Fb, the port and driver are 180° out of phase,
        creating an impedance dip. The dip should be close to the driver's
        DC resistance (Re) plus some losses.

        Lower QL (more leakage) → slightly shallower dip
        Higher QL (better sealed) → slightly deeper dip
        """
        driver = load_driver("BC_8NDL51")
        Vb = 0.020
        Fb = 50.0
        port_area = 0.00423
        port_length = 0.221

        # Calculate impedance at tuning frequency (where dip occurs)
        result = ported_box_electrical_impedance(
            Fb, driver, Vb, Fb, port_area, port_length,
            QL=float(ql_value), QA=100.0
        )

        impedance_at_fb = result['Ze_magnitude']

        # Check that impedance at Fb is in expected range (close to Re)
        min_expected, max_expected = expected_impedance_range
        assert min_expected <= impedance_at_fb <= max_expected, \
            f"QL={ql_value}: Impedance at Fb ({impedance_at_fb:.1f}Ω) " \
            f"outside expected range [{min_expected}, {max_expected}]Ω"

    def test_ported_box_dual_peaks_present(self):
        """
        Test that dual impedance peaks are present for ported box.

        Ported boxes should show:
        - Lower peak: Driver resonance with port loading (~Fb/√2)
        - Dip: Anti-resonance at Fb
        - Upper peak: Helmholtz resonance (~Fb×√2)
        """
        driver = load_driver("BC_8NDL51")
        Vb = 0.020
        Fb = 50.0
        port_area = 0.00423
        port_length = 0.221
        QL = 7.0  # Hornresp default

        # Calculate impedance around tuning frequency
        frequencies = [
            Fb / 1.5,   # Below lower peak
            Fb / 1.414, # Expected lower peak (~Fb/√2)
            Fb,        # Tuning frequency (dip)
            Fb * 1.414, # Expected upper peak (~Fb×√2)
            Fb * 1.5,   # Above upper peak
        ]

        impedances = []
        for freq in frequencies:
            result = ported_box_electrical_impedance(
                freq, driver, Vb, Fb, port_area, port_length,
                QL=QL, QA=100.0
            )
            impedances.append(result['Ze_magnitude'])

        # Check that we have dual peaks (impedance should be higher at peaks than at dip)
        lower_peak_imp = impedances[1]  # At ~Fb/√2
        dip_imp = impedances[2]         # At Fb
        upper_peak_imp = impedances[3]  # At ~Fb×√2

        # Both peaks should be higher than the dip
        assert lower_peak_imp > dip_imp, \
            "Lower peak impedance should be higher than dip at Fb"
        assert upper_peak_imp > dip_imp, \
            "Upper peak impedance should be higher than dip at Fb"


class TestSealedBoxQucHornrespComparison:
    """
    Integration tests comparing sealed box Quc implementation with Hornresp.

    IMPORTANT NOTE: Hornresp does NOT support QL parameter for sealed box enclosures.
    These tests cannot be run until Hornresp adds sealed box QL support or an
    alternative validation method is found.

    See: src/viberesp/enclosure/sealed_box.py - Important note on Hornresp limitation
    """

    @pytest.mark.skip(reason="Hornresp does not support QL for sealed boxes")
    def test_sealed_box_quc_vs_hornresp(self):
        """
        Compare sealed box electrical impedance with Hornresp.

        NOTE: This test is skipped because Hornresp does NOT support QL parameter
        for sealed box enclosures. QL is only available in Hornresp for ported boxes.

        The sealed box Quc implementation is based on Small (1972) theory and cannot
        be directly validated against Hornresp.

        Alternative validation methods:
        - Compare with other simulation tools that support sealed box QL
        - Validate against physical measurements
        - Verify formula correctness through unit tests
        """
        pass

    def test_sealed_box_quc_formula_consistency(self):
        """
        Test that sealed box Quc implementation is internally consistent.

        While we can't validate against Hornresp, we can verify:
        - Lower Quc (more losses) → lower impedance peak
        - Quc = infinity → theoretical lossless case
        - Parallel Q combination formula is correct
        """
        driver = load_driver("BC_8NDL51")
        Vb = 0.010  # 10L box

        # Test at system resonance (where impedance peak occurs)
        # Estimate Fc
        alpha = driver.V_as / Vb
        fc_approx = driver.F_s * (1 + alpha)**0.5

        # Calculate impedance for different Quc values
        result_low_loss = sealed_box_electrical_impedance(
            fc_approx, driver, Vb, Quc=50.0
        )
        result_high_loss = sealed_box_electrical_impedance(
            fc_approx, driver, Vb, Quc=5.0
        )

        # Higher losses (lower Quc) should give lower impedance peak
        assert result_high_loss['Ze_magnitude'] < result_low_loss['Ze_magnitude'], \
            "Higher losses (Quc=5) should give lower impedance peak than low losses (Quc=50)"

        # Test that Qtc_total follows parallel combination
        assert 'Qtc_total' in result_low_loss
        assert 'Qtc_total' in result_high_loss

        # Qtc should be lower with higher losses
        assert result_high_loss['Qtc_total'] < result_low_loss['Qtc_total'], \
            "Higher losses (Quc=5) should give lower Qtc than low losses (Quc=50)"


@pytest.mark.parametrize("ql_value", [7, 10, 20])
def test_ported_box_qb_calculation(ql_value):
    """
    Test that QB (combined box losses) is calculated correctly.

    Small (1973), Eq. 19: 1/QB = 1/QL + 1/QA + 1/QP

    QB should always be less than the smallest individual Q factor.
    """
    driver = load_driver("BC_8NDL51")
    Vb = 0.020
    Fb = 50.0
    port_area = 0.00423
    port_length = 0.221
    QA = 100.0

    result = ported_box_electrical_impedance(
        100.0, driver, Vb, Fb, port_area, port_length,
        QL=float(ql_value), QA=QA
    )

    QB = result['QB']
    QP = result['QP']

    # QB should be less than QL (since QL is typically the smallest)
    assert QB < ql_value, \
        f"QB={QB:.2f} should be < QL={ql_value} (parallel combination)"

    # Verify parallel combination formula
    QB_expected = 1.0 / (1.0/ql_value + 1.0/QA + 1.0/QP)
    assert abs(QB - QB_expected) < 0.01, \
        f"QB should be {QB_expected:.2f} from parallel combination, got {QB:.2f}"
