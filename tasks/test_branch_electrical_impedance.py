#!/usr/bin/env python3
"""
Test: Calculate electrical impedance contribution of each branch separately.

Hypothesis: Maybe we should calculate Ze for each branch separately, then combine.
"""

import sys
sys.path.insert(0, 'src')

import numpy as np
from gsd.simulation.tapped_horn_theory import (
    upstream_section_impedance,
    downstream_section_impedance,
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

print(f"{'=== Branch Electrical Impedance Test ===':^80}\n")
print(f"Frequency: {freq} Hz\n")

# Driver properties
BL = driver.BL
R_e = driver.R_e
S_d = driver.S_d  # m²
M_ms = driver.M_ms  # Total moving mass (kg)
C_ms = driver.C_ms  # Mechanical compliance (m/N)
R_ms = driver.R_ms  # Mechanical resistance (N·s/m)
omega = 2 * np.pi * freq

# Driver mechanical impedance
Z_m_ms = 1j * omega * M_ms
Z_c_ms = 1 / (1j * omega * C_ms)
Z_mech_driver = Z_m_ms + Z_c_ms + R_ms

print(f"Driver mechanical impedance: {Z_mech_driver:.2e} N·s/m")
print(f"|Z_mech_driver|: {np.abs(Z_mech_driver):.2e} N·s/m\n")

# Calculate branch impedances
z_throat_ac = upstream_section_impedance(freqs, th, medium)[0]
z_mouth_ac = downstream_section_impedance(freqs, th, medium)[0]

print("Step 1: Branch Acoustic Impedances")
print("-" * 80)
print(f"Throat branch (acoustic): {z_throat_ac:.2e} Pa·s/m³")
print(f"  |Z_throat_ac|: {np.abs(z_throat_ac):.2e} Pa·s/m³")
print(f"  Phase: {np.angle(z_throat_ac, deg=True):.1f}°")
print()
print(f"Mouth branch (acoustic): {z_mouth_ac:.2e} Pa·s/m³")
print(f"  |Z_mouth_ac|: {np.abs(z_mouth_ac):.2e} Pa·s/m³")
print(f"  Phase: {np.angle(z_mouth_ac, deg=True):.1f}°")
print()

# Convert to mechanical
z_throat_mech = z_throat_ac * (S_d ** 2)
z_mouth_mech = z_mouth_ac * (S_d ** 2)

print("Step 2: Branch Mechanical Impedances")
print("-" * 80)
print(f"Throat branch (mechanical): {z_throat_mech:.2e} N·s/m")
print(f"  |Z_throat_mech|: {np.abs(z_throat_mech):.2e} N·s/m")
print()
print(f"Mouth branch (mechanical): {z_mouth_mech:.2e} N·s/m")
print(f"  |Z_mouth_mech|: {np.abs(z_mouth_mech):.2e} N·s/m")
print()

# Calculate electrical impedance if ONLY throat branch were present
print("Step 3: Electrical Impedance if Only Throat Branch")
print("-" * 80)
Z_mech_total_throat = Z_mech_driver + z_throat_mech
Z_motional_throat = (BL ** 2) / Z_mech_total_throat
Ze_throat = R_e + Z_motional_throat
print(f"Total mechanical (driver + throat): {Z_mech_total_throat:.2e} N·s/m")
print(f"Motional impedance: {Z_motional_throat:.2e} Ω")
print(f"Electrical impedance (throat only): {Ze_throat:.2e} Ω")
print(f"|Ze_throat|: {np.abs(Ze_throat):.2f} Ω")
print()

# Calculate electrical impedance if ONLY mouth branch were present
print("Step 4: Electrical Impedance if Only Mouth Branch")
print("-" * 80)
Z_mech_total_mouth = Z_mech_driver + z_mouth_mech
Z_motional_mouth = (BL ** 2) / Z_mech_total_mouth
Ze_mouth = R_e + Z_motional_mouth
print(f"Total mechanical (driver + mouth): {Z_mech_total_mouth:.2e} N·s/m")
print(f"Motional impedance: {Z_motional_mouth:.2e} Ω")
print(f"Electrical impedance (mouth only): {Ze_mouth:.2e} Ω")
print(f"|Ze_mouth|: {np.abs(Ze_mouth):.2f} Ω")
print()

# Now try combining them in electrical domain (parallel)
print("Step 5: Parallel Combination in Electrical Domain")
print("-" * 80)
print("Treating Ze_throat and Ze_mouth as parallel impedances:")
print(f"  Ze_throat = {np.abs(Ze_throat):.2f} Ω")
print(f"  Ze_mouth = {np.abs(Ze_mouth):.2f} Ω")

# Calculate parallel combination (complex)
Z_sum_e = Ze_throat + Ze_mouth
epsilon = 1e-12
if np.abs(Z_sum_e) < epsilon:
    Z_sum_e += epsilon
Ze_parallel = (Ze_throat * Ze_mouth) / Z_sum_e

print(f"  Ze_parallel = (Ze_throat * Ze_mouth) / (Ze_throat + Ze_mouth)")
print(f"  Ze_parallel = {Ze_parallel:.2e} Ω")
print(f"  |Ze_parallel|: {np.abs(Ze_parallel):.2f} Ω")
print()

# Try adding mutual coupling
print("Step 6: Add Mutual Coupling (estimate)")
print("-" * 80)
# From research: mutual coupling should be ~15 Ω at 50 Hz
# Calculate this from driver mass
M_mutual = driver.M_md  # Use full driver mass
Z_mutual_mech = 1j * omega * M_mutual
Z_mutual_ac = Z_mutual_mech / (S_d ** 2)
Z_mutual_mech_total = Z_mutual_ac * (S_d ** 2)
Z_mutual_e = (BL ** 2) / Z_mutual_mech_total

print(f"Mutual coupling (mechanical): {Z_mutual_mech:.2e} N·s/m")
print(f"Mutual coupling (electrical): {Z_mutual_e:.2e} Ω")
print(f"|Z_mutual_e|: {np.abs(Z_mutual_e):.2f} Ω")
print()

# Total with mutual coupling
Ze_total_with_mutual = Ze_parallel + 2 * Z_mutual_e
print(f"Total (parallel + 2*mutual): {Ze_total_with_mutual:.2e} Ω")
print(f"|Ze_total|: {np.abs(Ze_total_with_mutual):.2f} Ω")
print()

# Compare to Hornresp
print("Step 7: Comparison with Hornresp")
print("-" * 80)
Ze_hornresp = 22.49
Ze_calculated = np.abs(Ze_total_with_mutual)
error_pct = (Ze_calculated - Ze_hornresp) / Ze_hornresp * 100

print(f"Hornresp Ze: {Ze_hornresp:.2f} Ω")
print(f"Calculated Ze: {Ze_calculated:.2f} Ω")
print(f"Error: {error_pct:+.1f}%")
print()

if abs(error_pct) < 5:
    print("✅ SUCCESS! The model matches Hornresp!")
else:
    print("❌ Still not matching. Need to investigate further.")

print()
print("=" * 80)
