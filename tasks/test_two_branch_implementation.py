#!/usr/bin/env python3
"""Debug the two-branch implementation to find the bug."""

import sys
sys.path.insert(0, 'src')

import numpy as np
from gsd.simulation.tapped_horn_theory import (
    calculate_tapped_horn_impedance_two_branch,
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

print(f"{'=== Two-Branch Implementation Debug ===':^80}\n")
print(f"Frequency: {freq} Hz\n")

# Call the two-branch function
z_acoustic = calculate_tapped_horn_impedance_two_branch(freqs, th, driver, medium)[0]

print(f"Returned acoustic impedance: {z_acoustic:.2e} Pa·s/m³")
print(f"|z_acoustic|: {np.abs(z_acoustic):.2e} Pa·s/m³")
print()

# Now convert to electrical impedance to see what we get
BL = driver.BL
R_e = driver.R_e
S_d = driver.S_d
M_ms = driver.M_ms
C_ms = driver.C_ms
R_ms = driver.R_ms
omega = 2 * np.pi * freq

# Driver mechanical impedance
Z_m_ms = 1j * omega * M_ms
Z_c_ms = 1 / (1j * omega * C_ms)
Z_mech_driver = Z_m_ms + Z_c_ms + R_ms

# Convert acoustic to mechanical
z_mech_acoustic = z_acoustic * (S_d ** 2)

# Total mechanical
Z_mech_total = Z_mech_driver + z_mech_acoustic

# Motional impedance
Z_motional = (BL ** 2) / Z_mech_total

# Total electrical
Ze_total = R_e + Z_motional

print(f"Acoustic → Mechanical: {z_mech_acoustic:.2e} N·s/m")
print(f"Driver mechanical: {Z_mech_driver:.2e} N·s/m")
print(f"Total mechanical: {Z_mech_total:.2e} N·s/m")
print(f"Motional impedance: {Z_motional:.2e} Ω")
print(f"Total electrical: {Ze_total:.2e} Ω")
print(f"|Ze_total|: {np.abs(Ze_total):.2f} Ω")
print()

# Compare to target
Ze_target = 22.49
error = (np.abs(Ze_total) - Ze_target) / Ze_target * 100
print(f"Target Ze: {Ze_target:.2f} Ω")
print(f"Calculated Ze: {np.abs(Ze_total):.2f} Ω")
print(f"Error: {error:+.1f}%")
print()

if abs(error) < 5:
    print("✅ SUCCESS!")
else:
    print("❌ Still has issues. Need to debug further.")

print()
print("=" * 80)
