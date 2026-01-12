#!/usr/bin/env python3
"""Debug the system response function to find the impedance bug."""

import sys
sys.path.insert(0, 'src')

import numpy as np
from gsd.simulation.tapped_horn_theory import (
    calculate_tapped_horn_impedance_two_branch,
    tapped_horn_system_response,
)
from gsd.simulation.types import TappedHorn
from gsd.simulation.horn_theory import MediumProperties
from gsd.driver.parameters import ThieleSmallParameters

# Driver parameters (from Hornresp th_sim.txt)
driver = ThieleSmallParameters(
    S_d=855e-4,       # 855 cm²
    BL=21.2,          # T·m
    M_md=0.147,       # 147 g = 0.147 kg
    R_ms=6.80,        # N·s/m
    R_e=5.20,         # Ω
    L_e=1.40e-3,      # 1.40 mH
    C_ms=1.04e-4,     # m/N
)

# Tapped horn geometry (from th_sim.txt)
th = TappedHorn(
    upstream_throat_area=150.0,
    tap_area=855.0,
    downstream_mouth_area=6000.0,
    upstream_length=180.0,
    downstream_length=200.0,
    upstream_profile='exponential',
    downstream_profile='exponential',
    intermediate_area=2265.0,
)

# Hornresp standard conditions
medium = MediumProperties(rho=1.18, c=343.0)

# Test frequency
freq = 50.0
freqs = np.array([freq])

print(f"{'=== System Response Debug ===':^80}\n")
print(f"Frequency: {freq} Hz\n")

# Test 1: Call two-branch function directly
print("Test 1: Two-branch function directly")
print("-" * 80)
z_acoustic_tb = calculate_tapped_horn_impedance_two_branch(freqs, th, driver, medium)[0]
print(f"Acoustic impedance: {z_acoustic_tb:.2e} Pa·s/m³")
print(f"|z_acoustic|: {np.abs(z_acoustic_tb):.2e} Pa·s/m³")

# Convert to electrical
BL = driver.BL
R_e = driver.R_e
S_d = driver.S_d
M_ms = driver.M_ms
C_ms = driver.C_ms
R_ms = driver.R_ms
L_e = driver.L_e
omega = 2 * np.pi * freq

# Driver mechanical
Z_m_ms = 1j * omega * M_ms
Z_c_ms = 1 / (1j * omega * C_ms)
Z_mech_driver = Z_m_ms + Z_c_ms + R_ms

# Convert acoustic to mechanical
z_mech_acoustic = z_acoustic_tb * (S_d ** 2)

# Total mechanical
Z_mech_total = Z_mech_driver + z_mech_acoustic

# Motional
Z_motional = (BL ** 2) / Z_mech_total

# Voice coil
Z_voice_coil = R_e + 1j * omega * L_e

# Total electrical
Ze_total = Z_voice_coil + Z_motional

print(f"Electrical impedance: {Ze_total:.2e} Ω")
print(f"|Ze|: {np.abs(Ze_total):.2f} Ω")
print()

# Test 2: Call system response function
print("Test 2: System response function")
print("-" * 80)
result = tapped_horn_system_response(freqs, th, driver, medium, voltage=2.83)
Ze_from_result = result['electrical_impedance'][0]
Ze_complex = result['z_electrical_complex'][0]
Z_mech_from_result = result['z_mechanical_total'][0]
print(f"Mechanical impedance: {Z_mech_from_result:.2e} N·s/m")
print(f"|Z_mechanical|: {np.abs(Z_mech_from_result):.2e} N·s/m")
print(f"Electrical impedance (complex): {Ze_complex:.2e} Ω")
print(f"Electrical impedance (magnitude): {Ze_from_result:.2f} Ω")
print(f"Voice coil impedance (R_e + jωL_e): {R_e + 1j*omega*L_e:.2e} Ω")
print()

# Compare
print("Comparison")
print("-" * 80)
Ze_target = 22.49
print(f"Two-branch direct: {np.abs(Ze_total):.2f} Ω")
print(f"System response: {Ze_from_result:.2f} Ω")
print(f"Hornresp target: {Ze_target:.2f} Ω")
print()

error_direct = (np.abs(Ze_total) - Ze_target) / Ze_target * 100
error_system = (Ze_from_result - Ze_target) / Ze_target * 100
print(f"Error (direct): {error_direct:+.1f}%")
print(f"Error (system): {error_system:+.1f}%")
print()

if abs(error_direct - error_system) < 1:
    print("✅ Both methods agree!")
elif abs(error_direct) < 5:
    print("✅ Direct method is correct, system response has bug")
else:
    print("❌ Both methods have issues")

print()
print("=" * 80)
