#!/usr/bin/env python3
"""
Compare mechanical impedance calculations between viberesp and Hornresp.

This script investigates why mechanical impedance differs significantly at high frequencies,
causing a 21.2× volume velocity difference at 20 kHz.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import math
import cmath
from gsd.driver.parameters import ThieleSmallParameters
from gsd.driver.electrical_impedance import electrical_impedance_bare_driver
from gsd.driver.radiation_impedance import radiation_impedance_piston

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

# Hornresp data
hornresp_data = {
    100.0: {'spl': 88.26, 'iin': 0.187227},
    503.3: {'spl': 92.81, 'iin': 0.519865},
    1000.0: {'spl': 91.18, 'iin': 0.483546},
    1986.7: {'spl': 84.55, 'iin': 0.359654},
    5033.4: {'spl': 69.64, 'iin': 0.171436},
    10000.0: {'spl': 58.15, 'iin': 0.089077},
    20000.0: {'spl': 46.15, 'iin': 0.044914},
}

freqs_of_interest = [100, 500, 1000, 2000, 5000, 10000, 20000]
voltage = 2.83  # Input voltage (V)
air_density = 1.18  # kg/m³
measurement_distance = 1.0  # m

print("=" * 130)
print("Mechanical Impedance Analysis: Viberesp vs Reverse-Engineered Hornresp")
print("=" * 130)

for freq in freqs_of_interest:
    # Find closest Hornresp data
    closest_freq = min(hornresp_data.keys(), key=lambda f: abs(f - freq))
    hr_data = hornresp_data[closest_freq]

    # Calculate viberesp values
    omega = 2 * math.pi * freq

    # Electrical impedance
    Ze = electrical_impedance_bare_driver(freq, driver, voice_coil_model="simple")

    # Voice coil impedance
    Z_voice_coil = complex(driver.R_e, omega * driver.L_e)

    # Reflected mechanical impedance
    Z_reflected = Ze - Z_voice_coil

    # Total mechanical impedance
    if abs(Z_reflected) == 0:
        Z_mechanical_total = complex(float('inf'), 0)
    else:
        Z_mechanical_total = (driver.BL ** 2) / Z_reflected

    # Driver mechanical impedance (without radiation)
    Z_mechanical_driver = complex(
        driver.R_ms,
        omega * driver.M_ms - 1 / (omega * driver.C_ms)
    )

    # Radiation impedance
    Z_rad = radiation_impedance_piston(freq, driver.S_d, air_density)

    # Acoustic impedance reflected to mechanical side
    Z_acoustic_reflected = Z_rad * (driver.S_d ** 2)

    # Current
    I = voltage / Ze
    I_mag = abs(I)

    # Viberesp diaphragm velocity
    if driver.BL == 0 or abs(Ze) == 0:
        u_diaphragm = complex(0, 0)
    else:
        u_diaphragm = (voltage * Z_reflected) / (driver.BL * Ze)

    # Viberesp volume velocity
    U_viberesp = u_diaphragm * driver.S_d
    U_viberesp_mag = abs(U_viberesp)

    # Viberesp SPL
    p_viberesp = (omega * air_density * U_viberesp_mag) / (2 * math.pi * measurement_distance)
    spl_viberesp = 20 * math.log10(p_viberesp / 20e-6) if p_viberesp > 0 else -float('inf')

    # Reverse-engineer Hornresp mechanical impedance
    # From SPL: U_HR = (2πr × p) / (ω × ρ₀)
    p_hr = 20e-6 * (10 ** (hr_data['spl'] / 20))
    U_hr_mag = (2 * math.pi * measurement_distance * p_hr) / (omega * air_density)

    # From force: F = BL × I (same for both)
    F_hr = driver.BL * hr_data['iin']

    # Hornresp mechanical impedance: Z_mech_HR = F / u = F / (U / S_d)
    if U_hr_mag > 0:
        Z_mech_hr_mag = F_hr / (U_hr_mag / driver.S_d)
    else:
        Z_mech_hr_mag = float('inf')

    # Calculate Hornresp mechanical impedance components
    # Z_mech_HR = Z_mech_driver + Z_acoustic_reflected + Z_extra
    # where Z_extra is any additional impedance not in viberesp
    Z_mech_viberesp_mag = abs(Z_mechanical_total)

    # Ratio of mechanical impedances
    Z_ratio = Z_mech_hr_mag / Z_mech_viberesp_mag if Z_mech_viberesp_mag > 0 else 0

    # Volume velocity ratio
    U_ratio = U_viberesp_mag / U_hr_mag if U_hr_mag > 0 else 0

    print(f"\n{'=' * 130}")
    print(f"Frequency: {freq} Hz")
    print(f"{'=' * 130}")
    print(f"Hornresp:    SPL={hr_data['spl']:6.2f} dB, Iin={hr_data['iin']:8.6f} A")
    print(f"Viberesp:    SPL={spl_viberesp:6.2f} dB, |I|={I_mag:8.6f} A")
    print(f"             Error={spl_viberesp - hr_data['spl']:6.2f} dB")
    print()
    print(f"Mechanical Impedance:")
    print(f"  Z_mech_driver (R_ms + jωM_ms + 1/jωC_ms): {abs(Z_mechanical_driver):12.2f} Ω_mech")
    print(f"    → {Z_mechanical_driver}")
    print(f"  Z_acoustic_reflected (Z_rad × S_d²):        {abs(Z_acoustic_reflected):12.2f} Ω_mech")
    print(f"    → {Z_acoustic_reflected}")
    print(f"  Z_mechanical_total (viberesp):             {Z_mech_viberesp_mag:12.2f} Ω_mech")
    print(f"    → {Z_mechanical_total}")
    print(f"  Z_mechanical_HR (reverse-engineered):      {Z_mech_hr_mag:12.2f} Ω_mech")
    print(f"  Ratio HR/Viberesp:                         {Z_ratio:12.2f}×")
    print()
    print(f"Volume Velocity:")
    print(f"  U_viberesp: {U_viberesp_mag*1e6:10.2f} cm³/s")
    print(f"  U_Hornresp: {U_hr_mag*1e6:10.2f} cm³/s")
    print(f"  Ratio:      {U_ratio:10.2f}× (= {20*math.log10(U_ratio) if U_ratio > 0 else 0:.2f} dB)")
    print()
    print(f"Force: F = BL × I = {driver.BL * I_mag:.6f} N")

print("\n" + "=" * 130)
print("Key Findings:")
print("=" * 130)
print("1. Current (I) matches perfectly between Hornresp and viberesp")
print("2. Force (F = BL × I) should be the same")
print("3. Volume velocity ratio = mechanical impedance ratio")
print("4. If Z_mech_HR > Z_mech_viberesp, Hornresp has additional impedance not in viberesp")
print("=" * 130)
