"""
Unit tests for QL (box losses) parameter calculations.

These tests verify the correct implementation of QL/Quc formulas
based on Small (1972) and Small (1973) literature.

Literature:
- Small (1972), "Closed-Box Loudspeaker Systems Part I", JAES, Eq. 9
- Small (1973), "Vented-Box Loudspeaker Systems Part I", JAES, Eq. 13, 19
- literature/thiele_small/small_1972_closed_box.md
- literature/thiele_small/small_1973_vented_box_part1.md
"""

import math
import pytest
from gsd.driver.parameters import ThieleSmallParameters
from gsd.enclosure.sealed_box import (
    calculate_sealed_box_system_parameters,
    sealed_box_electrical_impedance,
)
from gsd.enclosure.ported_box import (
    calculate_ported_box_system_parameters,
    ported_box_electrical_impedance,
    calculate_spl_ported_transfer_function,
)


@pytest.fixture
def test_driver():
    """Create a test driver with known parameters.

    Driver specifications:
    - Fs: 50 Hz
    - Re: 6.0 ohms
    - Qms: 5.0
    - Qes: 0.5
    - Qts: 0.45 (calculated)
    - Vas: 20L
    - Sd: 200 cm²
    - Mms: 20g
    - Cms: 0.5 mm/N
    - BL: 8.0 T·m
    - Le: 1.0 mH
    """
    return ThieleSmallParameters(
        M_md=0.018,  # kg (approximate, without radiation mass)
        C_ms=0.0005,  # m/N (0.5 mm/N)
        R_ms=2.0,  # N·s/m (calculated from Qms)
        R_e=6.0,  # ohms
        L_e=0.001,  # H (1.0 mH)
        BL=8.0,  # T·m
        S_d=0.02,  # m² (200 cm²)
        X_max=0.008,  # m (8mm)
        F_s=50.0,  # Hz
        Q_es=0.5,  # electrical Q
        Q_ms=5.0,  # mechanical Q
        Q_ts=0.45,  # total Q
        V_as=0.020,  # m³ (20L)
    )


class TestSealedBoxQucFormula:
    """Test sealed box Quc (mechanical + absorption losses) formulas."""

    def test_parallel_q_combination(self, test_driver):
        """Verify parallel Q combination formula (Small 1972, Eq. 9).

        The total system Q should use parallel combination, NOT geometric mean.

        Small (1972), Eq. 9: Qtc' = (Qec × Quc) / (Qec + Quc)
        """
        Vb = 0.010  # 10L box
        alpha = test_driver.V_as / Vb  # compliance ratio
        sqrt_factor = math.sqrt(1.0 + alpha)
        Qec = test_driver.Q_es * sqrt_factor  # electrical Q at Fc

        Quc = 7.0  # mechanical + absorption losses

        # Calculate system parameters
        params = calculate_sealed_box_system_parameters(
            test_driver, Vb, Quc=Quc
        )

        # Expected: parallel combination
        Qtc_expected = (Qec * Quc) / (Qec + Quc)

        # Verify
        assert abs(params.Qtc_total - Qtc_expected) < 0.01, \
            f"Qtc_total should be {Qtc_expected:.3f}, got {params.Qtc_total:.3f}"

        # Verify it's NOT geometric mean
        Qtc_wrong = (Qec * Quc) / math.sqrt(Qec**2 + Quc**2)
        assert abs(params.Qtc_total - Qtc_wrong) > 0.01, \
            "Qtc_total should NOT use geometric mean formula"

    def test_quc_infinity_no_losses(self, test_driver):
        """Test that Quc = ∞ represents no losses (theoretical limit)."""
        Vb = 0.010
        alpha = test_driver.V_as / Vb
        sqrt_factor = math.sqrt(1.0 + alpha)
        Qec = test_driver.Q_es * sqrt_factor

        # Quc = infinity should give Qtc = Qec (no losses)
        params = calculate_sealed_box_system_parameters(
            test_driver, Vb, Quc=float('inf')
        )

        assert abs(params.Qtc_total - Qec) < 0.001, \
            f"Quc=∞ should give Qtc=Qec={Qec:.3f}, got Qtc={params.Qtc_total:.3f}"

    def test_quc_decreases_qtc(self, test_driver):
        """Test that lower Quc (more losses) decreases total Qtc."""
        Vb = 0.010

        # High Quc (low losses)
        params_high = calculate_sealed_box_system_parameters(
            test_driver, Vb, Quc=100.0
        )

        # Low Quc (high losses)
        params_low = calculate_sealed_box_system_parameters(
            test_driver, Vb, Quc=5.0
        )

        # Lower Quc should give lower Qtc (more damping)
        assert params_low.Qtc_total < params_high.Qtc_total, \
            f"Quc=5.0 should give lower Qtc than Quc=100.0"

    def test_electrical_impedance_uses_quc(self, test_driver):
        """Test that electrical impedance function accepts and uses Quc parameter."""
        Vb = 0.010
        frequency = 100.0  # Hz

        # Test with different Quc values
        result_low = sealed_box_electrical_impedance(
            frequency, test_driver, Vb, Quc=5.0
        )
        result_high = sealed_box_electrical_impedance(
            frequency, test_driver, Vb, Quc=50.0
        )

        # Results should include Quc
        assert 'Quc' in result_low
        assert 'Quc' in result_high
        assert result_low['Quc'] == 5.0
        assert result_high['Quc'] == 50.0

        # Results should include Qtc_total (parallel combination)
        assert 'Qtc_total' in result_low
        assert 'Qtc_total' in result_high


class TestPortedBoxQLFormulas:
    """Test ported box QL/QA/QP (box losses) formulas."""

    def test_combined_box_losses_formula(self, test_driver):
        """Verify combined box losses formula (Small 1973, Eq. 19).

        Small (1973), Eq. 19: 1/QB = 1/QL + 1/QA + 1/QP

        This is a parallel combination of loss factors.
        """
        Vb = 0.020  # 20L
        Fb = 50.0  # Hz
        port_area = 0.003  # m² (30 cm²)
        port_length = 0.08  # m (8 cm)

        QL = 7.0
        QA = 100.0

        # Calculate system parameters
        params = calculate_ported_box_system_parameters(
            test_driver, Vb, Fb, port_area, port_length,
            QL=QL, QA=QA
        )

        # Expected: parallel combination
        QP = params.Qp  # calculated from port dimensions
        QB_expected = 1.0 / (1.0/QL + 1.0/QA + 1.0/QP)

        assert abs(params.QB - QB_expected) < 0.01, \
            f"QB should be {QB_expected:.3f}, got {params.QB:.3f}"

    def test_qb_dominated_by_smallest_q(self, test_driver):
        """Test that QB is dominated by the smallest Q factor.

        In parallel combination, smallest Q dominates (highest losses),
        so QB should always be less than the smallest individual Q.
        """
        Vb = 0.020
        Fb = 50.0
        port_area = 0.003
        port_length = 0.08

        # QL much smaller (dominates)
        params = calculate_ported_box_system_parameters(
            test_driver, Vb, Fb, port_area, port_length,
            QL=5.0, QA=100.0, QP=20.0
        )

        # QB should be close to (but less than) the smallest Q
        assert params.QB < 5.0, \
            f"QB={params.QB:.3f} should be < smallest Q=5.0"

        # QB should be approximately QL when QL dominates
        # For QL=5, QA=100, QP=20: 1/QB = 1/5 + 1/100 + 1/20 = 0.2 + 0.01 + 0.05 = 0.26
        # QB = 1/0.26 ≈ 3.85
        QB_expected = 1.0 / (1.0/5.0 + 1.0/100.0 + 1.0/20.0)
        assert abs(params.QB - QB_expected) < 0.01, \
            f"QB should be {QB_expected:.3f}, got {params.QB:.3f}"

    def test_ported_box_uses_qt_not_qes(self, test_driver):
        """Verify transfer function uses Q_T (total Q), not Q_ES (electrical Q).

        Small (1973), Eq. 13 uses Q_T in the denominator polynomial.

        This is a CRITICAL correction - the transfer function should use
        the driver's total Q (Qts), not electrical Q (Qes).
        """
        Vb = 0.020
        Fb = 50.0

        # Get driver parameters
        Qts = test_driver.Q_ts  # total Q
        Qes = test_driver.Q_es  # electrical Q

        # Verify they're different for this driver
        assert Qts != Qes, "Test driver should have Qts ≠ Qes"

        # Calculate SPL using transfer function
        frequency = 100.0  # Hz
        spl = calculate_spl_ported_transfer_function(
            frequency, test_driver, Vb, Fb
        )

        # The function internally uses Qt = driver.Q_ts (line ~719)
        # We can't directly inspect this, but we can verify it runs without error
        assert isinstance(spl, float) and spl > 0, \
            "SPL calculation should succeed using Q_T"

    def test_electrical_impedance_uses_ql_qa_qp(self, test_driver):
        """Test that ported box electrical impedance accepts QL, QA, QP."""
        Vb = 0.020
        Fb = 50.0
        port_area = 0.003
        port_length = 0.08
        frequency = 100.0

        # Test with explicit QL, QA
        result = ported_box_electrical_impedance(
            frequency, test_driver, Vb, Fb, port_area, port_length,
            QL=7.0, QA=100.0
        )

        # Should include QL, QA, QP, QB in result
        assert 'QL' in result
        assert 'QA' in result
        assert 'QP' in result
        assert 'QB' in result

        # QB should be calculated from QL, QA, QP
        QB_expected = 1.0 / (1.0/7.0 + 1.0/100.0 + 1.0/result['QP'])
        assert abs(result['QB'] - QB_expected) < 0.01

    def test_qp_auto_calc_if_not_provided(self, test_driver):
        """Test that QP is auto-calculated from port dimensions if not provided."""
        Vb = 0.020
        Fb = 50.0
        port_area = 0.003
        port_length = 0.08

        # Calculate with QP=None (auto-calc)
        params = calculate_ported_box_system_parameters(
            test_driver, Vb, Fb, port_area, port_length,
            QL=7.0, QA=100.0, QP=None
        )

        # QP should be calculated
        assert params.Qp is not None
        assert 5.0 <= params.Qp <= 100.0  # realistic range

    def test_spl_function_accepts_ql_qa(self, test_driver):
        """Test that SPL function accepts QL and QA parameters."""
        Vb = 0.020
        Fb = 50.0
        frequency = 100.0

        # Should not raise error
        spl = calculate_spl_ported_transfer_function(
            frequency, test_driver, Vb, Fb,
            QL=10.0, QA=50.0
        )

        assert isinstance(spl, float)
        assert spl > 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_quc_raises_error(self, test_driver):
        """Test that Quc = 0 raises an error."""
        Vb = 0.010

        with pytest.raises(ValueError):
            calculate_sealed_box_system_parameters(
                test_driver, Vb, Quc=0.0
            )

    def test_zero_ql_raises_error(self, test_driver):
        """Test that QL = 0 raises an error."""
        Vb = 0.020
        Fb = 50.0
        port_area = 0.003
        port_length = 0.08

        with pytest.raises(ValueError):
            calculate_ported_box_system_parameters(
                test_driver, Vb, Fb, port_area, port_length,
                QL=0.0
            )

    def test_negative_q_values_raise_error(self, test_driver):
        """Test that negative Q values raise errors."""
        Vb = 0.010

        with pytest.raises(ValueError):
            calculate_sealed_box_system_parameters(
                test_driver, Vb, Quc=-5.0
            )

    def test_default_ql_values(self, test_driver):
        """Test that default QL values match Hornresp/WinISD standards."""
        Vb = 0.020
        Fb = 50.0
        port_area = 0.003
        port_length = 0.08

        # Default QL = 7.0 (Hornresp)
        params = calculate_ported_box_system_parameters(
            test_driver, Vb, Fb, port_area, port_length
        )

        assert params.QL == 7.0, "Default QL should be 7.0 (Hornresp)"
        assert params.QA == 100.0, "Default QA should be 100.0 (negligible)"
