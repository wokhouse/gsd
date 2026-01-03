"""
Tests for Thiele-Small parameter data structures.

Literature:
- COMSOL (2020) - T/S parameter definitions and formulas
- Thiele (1971) - Original T/S parameter papers
- Small (1972) - System analysis
"""

import math
import pytest

from gsd.driver.parameters import ThieleSmallParameters
from gsd.simulation.constants import SPEED_OF_SOUND, AIR_DENSITY


class TestThieleSmallParameters:
    """Test ThieleSmallParameters dataclass."""

    def test_initialization_with_valid_parameters(self):
        """Test creating ThieleSmallParameters with valid values."""
        driver = ThieleSmallParameters(
            M_md=0.054,    # 54g moving mass
            C_ms=0.00019,  # Compliance (m/N)
            R_ms=5.2,      # Mechanical resistance (N·s/m)
            R_e=3.1,       # DC resistance (Ω)
            L_e=0.72e-3,   # 0.72 mH inductance
            BL=16.5,       # Force factor (T·m)
            S_d=0.0522     # 522 cm² effective area
        )

        assert driver.M_ms > driver.M_md  # M_ms includes radiation mass
        assert driver.C_ms == 0.00019
        assert driver.R_ms == 5.2
        assert driver.R_e == 3.1
        assert driver.L_e == 0.72e-3
        assert driver.BL == 16.5
        assert driver.S_d == 0.0522

    def test_derived_parameter_calculation(self):
        """Test calculation of derived T/S parameters."""
        # COMSOL example driver (Table 2)
        driver = ThieleSmallParameters(
            M_md=0.0334,   # 33.4g from COMSOL example
            C_ms=0.00118,  # 1.18e-3 from COMSOL example
            R_ms=1.85,     # N·s/m from COMSOL example
            R_e=6.4,       # Ω from COMSOL example
            L_e=6.89e-3,   # 6.89 mH from COMSOL example
            BL=11.4,       # T·m from COMSOL example
            S_d=0.0452     # m² (π × 0.12²)
        )

        # Check F_s calculation
        # COMSOL (2020), Table 3: F_s = 1/(2π√(M_md·C_ms))
        expected_fs = 1.0 / (2.0 * math.pi * math.sqrt(0.0334 * 0.00118))
        assert abs(driver.F_s - expected_fs) < 0.01

        # Check Q_es calculation
        # COMSOL (2020), Table 3: Q_es = 2πF_s·M_md / R_E
        omega_s = 2.0 * math.pi * driver.F_s
        expected_qes = (omega_s * driver.M_ms) / driver.R_e
        assert abs(driver.Q_es - expected_qes) < 0.001

        # Check Q_ms calculation
        # COMSOL (2020), Table 3: Q_ms = 2πF_s·M_md / R_ms
        expected_qms = (omega_s * driver.M_ms) / driver.R_ms
        assert abs(driver.Q_ms - expected_qms) < 0.001

        # Check Q_ts calculation
        # COMSOL (2020), Table 3: Q_ts = Q_es·Q_ms / (Q_es + Q_ms)
        expected_qts = (driver.Q_es * driver.Q_ms) / (driver.Q_es + driver.Q_ms)
        assert abs(driver.Q_ts - expected_qts) < 0.001

    def test_vas_calculation(self):
        """Test equivalent volume of compliance calculation."""
        driver = ThieleSmallParameters(
            M_md=0.054,
            C_ms=0.00019,
            R_ms=5.2,
            R_e=3.1,
            L_e=0.72e-3,
            BL=16.5,
            S_d=0.0522
        )

        # COMSOL (2020), Table 3: V_as = ρc²·S_D²·C_ms
        expected_vas = (
            AIR_DENSITY *
            (SPEED_OF_SOUND ** 2) *
            (driver.S_d ** 2) *
            driver.C_ms
        )
        assert abs(driver.V_as - expected_vas) < 1e-6

    def test_piston_radius_calculation(self):
        """Test piston radius calculation from effective area."""
        S_d = 0.05  # 50 cm²
        driver = ThieleSmallParameters(
            M_md=0.05,
            C_ms=0.0002,
            R_ms=5.0,
            R_e=8.0,
            L_e=0.001,
            BL=10.0,
            S_d=S_d
        )

        expected_radius = math.sqrt(S_d / math.pi)
        assert abs(driver.piston_radius() - expected_radius) < 1e-6

    def test_validation_rejects_negative_mass(self):
        """Test that negative moving mass raises ValueError."""
        with pytest.raises(ValueError, match="M_ms must be > 0"):
            ThieleSmallParameters(
                M_md=-0.05,
                C_ms=0.0002,
                R_ms=5.0,
                R_e=8.0,
                L_e=0.001,
                BL=10.0,
                S_d=0.05
            )

    def test_validation_rejects_zero_compliance(self):
        """Test that zero compliance raises ValueError."""
        with pytest.raises(ValueError, match="C_ms must be > 0"):
            ThieleSmallParameters(
                M_md=0.05,
                C_ms=0.0,
                R_ms=5.0,
                R_e=8.0,
                L_e=0.001,
                BL=10.0,
                S_d=0.05
            )

    def test_validation_rejects_negative_resistance(self):
        """Test that negative DC resistance raises ValueError."""
        with pytest.raises(ValueError, match="R_e must be > 0"):
            ThieleSmallParameters(
                M_md=0.05,
                C_ms=0.0002,
                R_ms=5.0,
                R_e=-8.0,
                L_e=0.001,
                BL=10.0,
                S_d=0.05
            )

    def test_validation_rejects_negative_force_factor(self):
        """Test that negative BL raises ValueError."""
        with pytest.raises(ValueError, match="BL must be > 0"):
            ThieleSmallParameters(
                M_md=0.05,
                C_ms=0.0002,
                R_ms=5.0,
                R_e=8.0,
                L_e=0.001,
                BL=-10.0,
                S_d=0.05
            )

    def test_validation_rejects_negative_area(self):
        """Test that negative effective area raises ValueError."""
        with pytest.raises(ValueError, match="S_d must be > 0"):
            ThieleSmallParameters(
                M_md=0.05,
                C_ms=0.0002,
                R_ms=5.0,
                R_e=8.0,
                L_e=0.001,
                BL=10.0,
                S_d=-0.05
            )

    def test_validation_allows_zero_mechanical_resistance(self):
        """Test that zero mechanical resistance is allowed (ideal driver)."""
        driver = ThieleSmallParameters(
            M_md=0.05,
            C_ms=0.0002,
            R_ms=0.0,  # No mechanical losses
            R_e=8.0,
            L_e=0.001,
            BL=10.0,
            S_d=0.05
        )
        assert driver.R_ms == 0.0
        # Q_ms should be infinite for R_ms = 0 (no mechanical damping)
        assert driver.Q_ms == float('inf')
        # Q_ts should equal Q_es when Q_ms is infinite
        assert driver.Q_ts == driver.Q_es

    def test_validation_allows_zero_inductance(self):
        """Test that zero inductance is allowed (resistive voice coil)."""
        driver = ThieleSmallParameters(
            M_md=0.05,
            C_ms=0.0002,
            R_ms=5.0,
            R_e=8.0,
            L_e=0.0,  # No inductance
            BL=10.0,
            S_d=0.05
        )
        assert driver.L_e == 0.0

    def test_repr_includes_key_parameters(self):
        """Test that __repr__ includes key parameters."""
        driver = ThieleSmallParameters(
            M_md=0.054,
            C_ms=0.00019,
            R_ms=5.2,
            R_e=3.1,
            L_e=0.72e-3,
            BL=16.5,
            S_d=0.0522
        )

        repr_str = repr(driver)
        assert "F_s=" in repr_str
        assert "Q_ts=" in repr_str
        assert "V_as=" in repr_str
        assert "R_e=" in repr_str
        assert "S_d=" in repr_str

    def test_q_factors_relationship(self):
        """Test that Q_ts < Q_es and Q_ts < Q_ms."""
        driver = ThieleSmallParameters(
            M_md=0.054,
            C_ms=0.00019,
            R_ms=5.2,
            R_e=3.1,
            L_e=0.72e-3,
            BL=16.5,
            S_d=0.0522
        )

        # Q_ts should always be less than both Q_es and Q_ms
        assert driver.Q_ts < driver.Q_es
        assert driver.Q_ts < driver.Q_ms

    def test_resonance_frequency_in_typical_range(self):
        """Test that F_s is in typical range for loudspeakers (10-200 Hz)."""
        # Typical 12" woofer parameters
        driver = ThieleSmallParameters(
            M_md=0.054,
            C_ms=0.00019,
            R_ms=5.2,
            R_e=3.1,
            L_e=0.72e-3,
            BL=16.5,
            S_d=0.0522
        )

        # F_s should be between 10 Hz and 200 Hz for typical drivers
        assert 10 < driver.F_s < 200

    def test_comsol_example_driver(self):
        """
        Test against COMSOL example driver from documentation.

        COMSOL (2020), Table 2 provides complete parameters for a reference driver.
        This test validates our calculations match the COMSOL formulas.
        """
        # COMSOL Lumped Loudspeaker Driver example
        driver = ThieleSmallParameters(
            M_md=0.0334,   # 33.4 g
            C_ms=0.00118,  # 1.18e-3 m/N
            R_ms=1.85,     # 1.85 N·s/m
            R_e=6.4,       # 6.4 Ω
            L_e=6.89e-3,   # 6.89 mH
            BL=11.4,       # 11.4 T·m
            S_d=0.0452     # π × 0.12² (12cm radius)
        )

        # Expected values from COMSOL (2020), Table 3
        # F_s = 1/(2π√(33.4g × 1.18e-3)) ≈ 25.3 Hz
        assert 25 < driver.F_s < 26  # ~25.3 Hz
        # Q_es = 2π×25.3×0.0334 / 6.4 ≈ 0.83
        assert 0.8 < driver.Q_es < 0.85  # ~0.83
        # Q_ms = 2π×25.3×0.0334 / 1.85 ≈ 2.9
        assert 2.8 < driver.Q_ms < 3.0  # ~2.9
        # Q_ts = (0.83 × 2.9) / (0.83 + 2.9) ≈ 0.64
        assert 0.62 < driver.Q_ts < 0.66  # ~0.64
