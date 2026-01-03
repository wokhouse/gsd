#!/usr/bin/env python3
"""
Compare viberesp and Hornresp current calculations.

This script extracts Hornresp Iin values and compares them with viberesp
current calculations to determine if the discrepancy is in current or force.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import math
import cmath
from gsd.driver.parameters import ThieleSmallParameters
from gsd.driver.electrical_impedance import electrical_impedance_bare_driver

# BC 8NDL51 driver parameters
driver = ThieleSmallParameters(
    M_ms=0.0268,      # Moving mass (kg)
    C_ms=0.000354,    # Compliance (m/N)
    R_ms=3.3,         # Mechanical resistance (N·s/m)
    R_e=5.9,          # Voice coil DC resistance (ohms)
    L_e=0.0005,       # Voice coil inductance (H) - 0.5 mH
    BL=12.39,         # Force factor (T·m)
    S_d=0.0220,       # Diaphragm area (m²)
    F_s=54.0,         # Resonance frequency (Hz)
)

# Key frequencies
freqs_of_interest = [100, 500, 1000, 2000, 5000, 10000, 20000]

print("=" * 100)
print("Current Calculation Comparison: Viberesp vs Hornresp")
print("=" * 100)
print(f"{'Freq':>8} {'Hornresp SPL':>15} {'Hornresp Iin':>15} {'Viberesp |I|':>15} {'Viberesp I_real':>17} {'Viberesp I_active':>18}")
print("-" * 100)

# Hornresp data (extracted from 8ndl51_sim.txt)
hornresp_data = {
    100.0: {'spl': 88.26, 'iin': 0.187227, 'ze_phase': -52.84},
    503.3: {'spl': 92.81, 'iin': 0.519865, 'ze_phase': -0.55},
    1000.0: {'spl': 91.18, 'iin': 0.483546, 'ze_phase': 23.10},
    1986.7: {'spl': 84.55, 'iin': 0.359654, 'ze_phase': 47.35},
    5033.4: {'spl': 69.64, 'iin': 0.171436, 'ze_phase': 71.26},
    10000.0: {'spl': 58.15, 'iin': 0.089077, 'ze_phase': 80.39},
    20000.0: {'spl': 46.15, 'iin': 0.044914, 'ze_phase': 85.17},
}

voltage = 2.83  # Input voltage (V)

for freq in freqs_of_interest:
    # Find closest Hornresp data
    closest_freq = min(hornresp_data.keys(), key=lambda f: abs(f - freq))
    hr_data = hornresp_data[closest_freq]

    # Calculate viberesp electrical impedance
    omega = 2 * math.pi * freq
    Ze = electrical_impedance_bare_driver(freq, driver, voice_coil_model="simple")

    # Calculate current
    I_complex = voltage / Ze
    I_mag = abs(I_complex)
    I_real = I_complex.real
    I_phase = cmath.phase(I_complex)

    # Active current (component in phase with voltage)
    # Voltage has phase 0°, so I_active = |I| * cos(phase(I) - phase(V))
    # Since phase(V) = 0°, I_active = |I| * cos(phase(I))
    I_active = I_mag * math.cos(I_phase)

    # Print comparison
    print(f"{freq:8.1f} {hr_data['spl']:15.2f} {hr_data['iin']:15.6f} {I_mag:15.6f} {I_real:17.6f} {I_active:18.6f}")

    # Calculate ratios
    ratio_mag = hr_data['iin'] / I_mag if I_mag > 0 else 0
    ratio_real = hr_data['iin'] / I_real if abs(I_real) > 0 else 0
    ratio_active = hr_data['iin'] / I_active if abs(I_active) > 0 else 0

    print(f"        Ratios: Hornresp/|I|={ratio_mag:.4f}, Hornresp/I_real={ratio_real:.4f}, Hornresp/I_active={ratio_active:.4f}")
    print(f"        Viberesp: I_phase={math.degrees(I_phase):.2f}°, Ze_phase={math.degrees(cmath.phase(Ze)):.2f}°")
    print()

print("=" * 100)
print("Analysis:")
print("- If Hornresp/|I| ≈ 1.0: Hornresp uses current magnitude")
print("- If Hornresp/I_real ≈ 1.0: Hornresp uses real part of current")
print("- If Hornresp/I_active ≈ 1.0: Hornresp uses active (in-phase) component")
print("=" * 100)
