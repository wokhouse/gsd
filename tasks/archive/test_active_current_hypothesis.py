#!/usr/bin/env python3
"""
Test the hypothesis: Hornresp uses F = BL × I_active instead of F = BL × |I|.

This script calculates SPL using different force models to see which one
matches Hornresp's behavior.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import math
import cmath
from gsd.driver.parameters import ThieleSmallParameters
from gsd.driver.electrical_impedance import electrical_impedance_bare_driver
from gsd.driver.radiation_impedance import radiation_impedance_piston

# BC 8NDL51 driver parameters
driver = ThieleSmallParameters(
    M_ms=0.0268, C_ms=0.000354, R_ms=3.3,
    R_e=5.9, L_e=0.0005, BL=12.39, S_d=0.0220, F_s=54.0,
)

# Hornresp data
hornresp_data = {
    100.0: {'spl': 88.26},
    503.3: {'spl': 92.81},
    1000.0: {'spl': 91.18},
    1986.7: {'spl': 84.55},
    5033.4: {'spl': 69.64},
    10000.0: {'spl': 58.15},
    20000.0: {'spl': 46.15},
}

freqs_of_interest = [100, 500, 1000, 2000, 5000, 10000, 20000]
voltage = 2.83
air_density = 1.18
measurement_distance = 1.0

print("=" * 130)
print("Testing Force Calculation Models: |I| vs I_active")
print("=" * 130)
print()
print("Hypothesis: Hornresp uses F = BL × I_active (energy-conserving)")
print("            Viberesp uses F = BL × |I| (magnitude-based)")
print()
print("At high frequencies, current lags voltage by ~90° due to inductance.")
print("I_active = |I| × cos(phase_I) is the component in phase with voltage.")
print("Only I_active contributes to REAL power transfer.")
print("=" * 130)
print()

def calculate_spl_from_force_model(freq, driver, voltage, force_model):
    """Calculate SPL using different force models."""
    omega = 2 * math.pi * freq

    # Calculate electrical quantities
    Ze = electrical_impedance_bare_driver(freq, driver, voice_coil_model="simple")
    Z_voice_coil = complex(driver.R_e, omega * driver.L_e)
    Z_reflected = Ze - Z_voice_coil

    # Complex current
    I_complex = voltage / Ze
    I_mag = abs(I_complex)
    I_phase = cmath.phase(I_complex)

    # Calculate force based on model
    if force_model == "magnitude":
        # Viberesp model: F = BL × |I|
        F_mag = driver.BL * I_mag
    elif force_model == "active":
        # Hornresp hypothesis: F = BL × I_active
        # I_active is the component in phase with voltage
        # Since voltage has phase 0°, I_active = |I| × cos(phase_I)
        I_active = I_mag * math.cos(I_phase)
        F_mag = driver.BL * I_active
    else:
        raise ValueError(f"Unknown force model: {force_model}")

    # Mechanical impedance (without radiation, for manual calculation)
    Z_mechanical = complex(
        driver.R_ms,
        omega * driver.M_ms - 1 / (omega * driver.C_ms)
    )

    # Add radiation impedance
    Z_rad = radiation_impedance_piston(freq, driver.S_d)
    Z_acoustic_reflected = Z_rad * (driver.S_d ** 2)
    Z_mechanical_total = Z_mechanical + Z_acoustic_reflected

    # Diaphragm velocity: u = F / Z_mechanical
    u_diaphragm_mag = F_mag / abs(Z_mechanical_total)

    # Volume velocity: U = u × S_d
    U_mag = u_diaphragm_mag * driver.S_d

    # SPL: p = (ω × ρ₀ × U) / (2πr)
    p_mag = (omega * air_density * U_mag) / (2 * math.pi * measurement_distance)
    spl = 20 * math.log10(p_mag / 20e-6) if p_mag > 0 else -float('inf')

    return {
        'spl': spl,
        'I_mag': I_mag,
        'I_phase_deg': math.degrees(I_phase),
        'I_active': I_mag * math.cos(I_phase) if force_model == "active" else None,
        'F_mag': F_mag,
        'u_mag': u_diaphragm_mag,
        'U_mag': U_mag,
    }

print(f"{'Freq':>8} {'HR SPL':>8} {'|I| Model':>10} ['I| Error'] {'I_active Model':>14} [I_active Error] {'I_phase':>10}")
print("-" * 130)

for freq in freqs_of_interest:
    # Find closest Hornresp data
    closest_freq = min(hornresp_data.keys(), key=lambda f: abs(f - freq))
    hr_spl = hornresp_data[closest_freq]['spl']

    # Calculate SPL using both force models
    result_mag = calculate_spl_from_force_model(freq, driver, voltage, "magnitude")
    result_active = calculate_spl_from_force_model(freq, driver, voltage, "active")

    error_mag = result_mag['spl'] - hr_spl
    error_active = result_active['spl'] - hr_spl

    print(f"{freq:8.0f} {hr_spl:8.2f} {result_mag['spl']:10.2f} [{error_mag:+7.2f}] {result_active['spl']:14.2f} [{error_active:+7.2f}] {result_mag['I_phase_deg']:10.2f}°")

print()
print("=" * 130)
print("Analysis:")
print("- If |I| model matches Hornresp: Viberesp implementation is correct → investigate elsewhere")
print("- If I_active model matches Hornresp: Need to change force calculation to use active current")
print("=" * 130)
print()
print("Expected pattern:")
print("- At low f (phase_I ~ 0°): Both models should match (I_active ≈ |I|)")
print("- At high f (phase_I ~ -90°): I_active model should have lower SPL (I_active << |I|)")
print("=" * 130)
