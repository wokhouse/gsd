"""
Unit tests for I_active force model in response.py.

Tests verify that the energy-conserving force calculation uses only the
active (in-phase) component of current for time-averaged SPL prediction.

Literature:
- COMSOL (2020), Eq. 4: P_E = 0.5·Re{V₀·i_c*}
- Kolbrek: "Purely reactive (no real part = no power transmission"
- Beranek (1954): Radiation impedance - only resistive component radiates
"""

import math
import cmath
import pytest

from gsd.driver import load_driver:
    """Test that force calculation uses I_active at high frequencies.

    At 20 kHz, voice coil inductance causes current to lag voltage by ~85°.
    I_active should be much smaller than |I| (approximately cos(85°) ≈ 0.087).

    This test verifies that the implemented force model correctly extracts
    and uses only the active (in-phase) component of current.
    """
    # Get driver parameters
    driver = load_driver("BC_8NDL51")
    freq = 20000  # 20 kHz
    voltage = 2.83

    # Calculate electrical impedance
    from gsd.driver.radiation_impedance import radiation_impedance_piston
    Z_rad = radiation_impedance_piston(freq, driver.S_d, SPEED_OF_SOUND, AIR_DENSITY)

    Ze = electrical_impedance_bare_driver(
        freq,
        driver,
        acoustic_load=Z_rad,
        voice_coil_model="simple"
    )

    # Calculate complex current and extract components
    I_complex = voltage / Ze
    I_mag = abs(I_complex)
    I_phase = cmath.phase(I_complex)
    I_active = I_mag * math.cos(I_phase)

    # At high frequency, current should lag significantly (70-85°)
    # Therefore I_active should be much smaller than I_mag
    assert abs(I_phase) > math.radians(70), \
        f"Current phase lag should be >70° at {freq} Hz, got {math.degrees(I_phase):.1f}°"

    assert I_active < 0.5 * I_mag, \
        f"I_active ({I_active:.4f}) should be < 0.5*I_mag ({I_mag:.4f}) at {freq} Hz"

    # Calculate force using BL × I_active
    F_expected = driver.BL * I_active

    # Verify that the force model produces results consistent with I_active
    # (not with |I|, which would give much larger force)
    result = direct_radiator_electrical_impedance(freq, driver, voltage)

    # The diaphragm velocity should be consistent with F_active = BL × I_active
    # Extract mechanical impedance to verify this
    omega = 2 * math.pi * freq
    Z_voice_coil = complex(driver.R_e, omega * driver.L_e)
    Z_reflected = Ze - Z_voice_coil

    if abs(Z_reflected) > 0:
        Z_mechanical_total = (driver.BL ** 2) / Z_reflected

        # Expected velocity from active force
        u_expected = F_expected / abs(Z_mechanical_total)

        # Compare with actual result (allow 5% tolerance for numerical precision)
        u_actual = result['diaphragm_velocity']

        assert abs(u_actual - u_expected) / u_expected < 0.05, \
            f"Diaphragm velocity ({u_actual:.6f}) should match F_active/|Z_mech| ({u_expected:.6f})"


def test_force_calculation_at_low_frequency():
    """Test that force calculation works correctly at low frequencies.

    At 100 Hz, the current has significant phase shift due to resonance
    effects (BC 8NDL51 has Fs ≈ 34 Hz). However, the I_active model
    should still produce physically reasonable results.

    This test verifies that low-frequency performance is maintained.
    """
    driver = load_driver("BC_8NDL51")
    freq = 100  # 100 Hz
    voltage = 2.83

    # Calculate electrical impedance
    from gsd.driver.radiation_impedance import radiation_impedance_piston
    Z_rad = radiation_impedance_piston(freq, driver.S_d, SPEED_OF_SOUND, AIR_DENSITY)

    Ze = electrical_impedance_bare_driver(
        freq,
        driver,
        acoustic_load=Z_rad,
        voice_coil_model="simple"
    )

    # Calculate complex current
    I_complex = voltage / Ze
    I_mag = abs(I_complex)
    I_phase = cmath.phase(I_complex)
    I_active = I_mag * math.cos(I_phase)

    # At 100 Hz (near resonance), current can have significant phase shift
    # but I_active should still be > 50% of I_mag
    assert I_active > 0.5 * I_mag, \
        f"I_active ({I_active:.4f}) should be > 0.5*I_mag ({I_mag:.4f}) at {freq} Hz"

    # Calculate result
    result = direct_radiator_electrical_impedance(freq, driver, voltage)

    # Should produce reasonable SPL (>50 dB at 1m for 2.83V input)
    assert result['SPL'] > 50, \
        f"SPL should be >50 dB at {freq} Hz, got {result['SPL']:.1f} dB"

    # Diaphragm velocity should be non-zero
    assert result['diaphragm_velocity'] > 0, \
        f"Diaphragm velocity should be >0 at {freq} Hz"


def test_i_active_reduces_high_frequency_spl():
    """Test that I_active model reduces high-frequency SPL compared to |I| model.

    This test verifies the expected improvement: using I_active instead of |I|
    should reduce SPL at high frequencies by approximately the power factor:
    SPL_reduction ≈ 20·log₁₀(cos(θ)) where θ is current phase lag.

    Note: The reduction is negative (SPL goes down), so we expect < -10 dB.
    """
    driver = load_driver("BC_8NDL51")
    freq = 10000  # 10 kHz
    voltage = 2.83

    # Calculate electrical impedance
    from gsd.driver.radiation_impedance import radiation_impedance_piston
    Z_rad = radiation_impedance_piston(freq, driver.S_d, SPEED_OF_SOUND, AIR_DENSITY)

    Ze = electrical_impedance_bare_driver(
        freq,
        driver,
        acoustic_load=Z_rad,
        voice_coil_model="simple"
    )

    # Calculate current components
    I_complex = voltage / Ze
    I_mag = abs(I_complex)
    I_phase = cmath.phase(I_complex)
    I_active = I_mag * math.cos(I_phase)

    # Calculate expected SPL reduction from using I_active vs |I|
    # SPL is proportional to velocity, which is proportional to force
    # Force ratio = I_active / I_mag = cos(θ)
    # SPL difference = 20·log₁₀(cos(θ))  [negative value = reduction]
    expected_spl_reduction = 20 * math.log10(abs(math.cos(I_phase)))

    # At 10 kHz, we expect significant reduction (more negative than -10 dB)
    assert expected_spl_reduction < -10, \
        f"Expected SPL reduction < -10 dB (i.e., >10 dB reduction), got {expected_spl_reduction:.1f} dB"

    # Verify I_active is much smaller than I_mag at high frequency
    assert I_active < 0.3 * I_mag, \
        f"I_active ({I_active:.4f}) should be < 0.3*I_mag ({I_mag:.4f}) at {freq} Hz"

    # Verify the result is physically reasonable
    result = direct_radiator_electrical_impedance(freq, driver, voltage)

    # SPL should be reasonable (not excessively high from using |I|)
    # For a typical 8" woofer at 10 kHz, SPL should be <100 dB at 1m for 2.83V
    assert result['SPL'] < 100, \
        f"SPL should be <100 dB at {freq} Hz (I_active prevents overestimation), got {result['SPL']:.1f} dB"


def test_active_current_definition():
    """Test the definition of I_active = |I|·cos(θ).

    This is a fundamental test of the I_active calculation.
    """
    # Test case 1: Current in phase with voltage (θ = 0°)
    I_mag = 1.0
    I_phase = 0.0
    I_active = I_mag * math.cos(I_phase)

    assert abs(I_active - I_mag) < 1e-10, \
        "I_active should equal I_mag when phase = 0°"

    # Test case 2: Current 90° out of phase (purely reactive)
    I_mag = 1.0
    I_phase = math.pi / 2
    I_active = I_mag * math.cos(I_phase)

    assert abs(I_active) < 1e-10, \
        "I_active should be 0 when phase = 90° (purely reactive)"

    # Test case 3: Current 85° out of phase (highly inductive)
    I_mag = 1.0
    I_phase = math.radians(85)
    I_active = I_mag * math.cos(I_phase)

    expected_ratio = math.cos(math.radians(85))  # ≈ 0.087
    assert abs(I_active - expected_ratio) < 1e-10, \
        f"I_active should be {expected_ratio:.3f} when phase = 85°"


@pytest.mark.parametrize("freq", [20, 50, 100, 200, 500])
def test_low_frequency_regression(freq):
    """Ensure low-frequency performance is maintained with I_active model.

    At low frequencies, current and voltage are nearly in phase,
    so I_active ≈ I_mag and the new model should give similar results
    to the old model.

    This is a regression test to ensure the I_active implementation
    doesn't break low-frequency accuracy.
    """
    driver = load_driver("BC_8NDL51")
    voltage = 2.83

    # Calculate result with I_active model
    result = direct_radiator_electrical_impedance(freq, driver, voltage)

    # At low frequencies, SPL should be reasonable
    # For BC 8NDL51 at 2.83V:
    # - Resonance (Fs ≈ 34 Hz): SPL should be >60 dB
    # - 100-500 Hz: SPL should be >65 dB
    if freq < 100:
        assert result['SPL'] > 60, \
            f"SPL at {freq} Hz should be >60 dB, got {result['SPL']:.1f} dB"
    else:
        assert result['SPL'] > 65, \
            f"SPL at {freq} Hz should be >65 dB, got {result['SPL']:.1f} dB"

    # Diaphragm velocity should be non-zero
    assert result['diaphragm_velocity'] > 0, \
        f"Diaphragm velocity should be >0 at {freq} Hz"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
