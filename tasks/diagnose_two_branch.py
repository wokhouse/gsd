#!/usr/bin/env python3
"""
Detailed diagnostic of two-branch impedance calculation.

Goal: Understand why Ze = 6.14 Ω instead of 22.49 Ω at 50 Hz.
"""

import sys
sys.path.insert(0, 'src')

import numpy as np
from gsd.simulation.tapped_horn_theory import (
    upstream_section_impedance,
    downstream_section_impedance,
    calculate_mutual_coupling,
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
    upstream_throat_area=150.0,      # S1 (cm²)
    tap_area=855.0,                   # S2 (cm²)
    downstream_mouth_area=6000.0,    # S4 (cm²)
    upstream_length=180.0,            # L12 (cm)
    downstream_length=200.0,          # L23 (cm)
    upstream_profile='exponential',
    downstream_profile='exponential',
    intermediate_area=2265.0,
)

# Hornresp standard conditions
medium = MediumProperties(rho=1.18, c=343.0)

# Test frequency
freq = 50.0
freqs = np.array([freq])

# Driver properties
BL = driver.BL
R_e = driver.R_e
S_d = driver.S_d  # m²

print(f"{'=== Two-Branch Impedance Diagnostic ===':^80}")
print(f"\nFrequency: {freq} Hz")
print(f"Driver: BC 15PS100")
print(f"  BL = {BL} T·m")
print(f"  R_e = {R_e} Ω")
print(f"  S_d = {S_d*10000:.1f} cm² = {S_d:.6f} m²")
print()

# Calculate branch impedances
print("Step 1: Calculate Acoustic Impedances")
print("-" * 80)

z_throat_ac = upstream_section_impedance(freqs, th, medium)[0]
z_mouth_ac = downstream_section_impedance(freqs, th, medium)[0]

print(f"Throat branch (upstream):")
print(f"  Z_throat_ac = {z_throat_ac:.2e} Pa·s/m³")
print(f"  Magnitude: {np.abs(z_throat_ac):.2e} Pa·s/m³")
print(f"  Phase: {np.angle(z_throat_ac, deg=True):.1f}°")
print()

print(f"Mouth branch (downstream):")
print(f"  Z_mouth_ac = {z_mouth_ac:.2e} Pa·s/m³")
print(f"  Magnitude: {np.abs(z_mouth_ac):.2e} Pa·s/m³")
print(f"  Phase: {np.angle(z_mouth_ac, deg=True):.1f}°")
print()

# Calculate mutual coupling
print("Step 2: Calculate Mutual Coupling")
print("-" * 80)

z_mutual_ac = calculate_mutual_coupling(freqs, th, medium)[0]

print(f"Mutual coupling:")
print(f"  Z_mutual_ac = {z_mutual_ac:.2e} Pa·s/m³")
print(f"  Magnitude: {np.abs(z_mutual_ac):.2e} Pa·s/m³")
print(f"  Phase: {np.angle(z_mutual_ac, deg=True):.1f}°")
print()

# Parallel combination
print("Step 3: Parallel Combination (Acoustic)")
print("-" * 80)

z_parallel_ac = (z_throat_ac * z_mouth_ac) / (z_throat_ac + z_mouth_ac)
print(f"Parallel combination:")
print(f"  Z_parallel_ac = (Z_throat * Z_mouth) / (Z_throat + Z_mouth)")
print(f"  Z_parallel_ac = {z_parallel_ac:.2e} Pa·s/m³")
print(f"  Magnitude: {np.abs(z_parallel_ac):.2e} Pa·s/m³")
print(f"  Phase: {np.angle(z_parallel_ac, deg=True):.1f}°")
print()

# Total with mutual coupling
print("Step 4: Total Acoustic Impedance")
print("-" * 80)

z_total_ac = z_parallel_ac + 2 * z_mutual_ac
print(f"Total (with mutual coupling):")
print(f"  Z_total_ac = Z_parallel_ac + 2*Z_mutual_ac")
print(f"  Z_total_ac = {z_total_ac:.2e} Pa·s/m³")
print(f"  Magnitude: {np.abs(z_total_ac):.2e} Pa·s/m³")
print(f"  Phase: {np.angle(z_total_ac, deg=True):.1f}°")
print()

# Convert to mechanical
print("Step 5: Convert to Mechanical Impedance")
print("-" * 80)

z_throat_mech = z_throat_ac * (S_d ** 2)
z_mouth_mech = z_mouth_ac * (S_d ** 2)
z_mutual_mech = z_mutual_ac * (S_d ** 2)
z_parallel_mech = z_parallel_ac * (S_d ** 2)
z_total_mech = z_total_ac * (S_d ** 2)

print(f"Throat branch mechanical: {np.abs(z_throat_mech):.2e} N·s/m")
print(f"Mouth branch mechanical: {np.abs(z_mouth_mech):.2e} N·s/m")
print(f"Mutual coupling mechanical: {np.abs(z_mutual_mech):.2e} N·s/m")
print(f"Parallel combination mechanical: {np.abs(z_parallel_mech):.2e} N·s/m")
print(f"Total mechanical: {np.abs(z_total_mech):.2e} N·s/m")
print()

# Calculate electrical impedance
print("Step 6: Calculate Electrical Impedance")
print("-" * 80)

# Mechanical impedance (from driver parameters)
M_ms = driver.M_ms  # Total moving mass (kg)
C_ms = driver.C_ms  # Mechanical compliance (m/N)
R_ms = driver.R_ms  # Mechanical resistance (N·s/m)
omega = 2 * np.pi * freq

Z_m_ms = 1j * omega * M_ms
Z_c_ms = 1 / (1j * omega * driver.C_ms)
Z_r_ms = driver.R_ms

Z_mech_driver = Z_m_ms + Z_c_ms + Z_r_ms

print(f"Driver mechanical impedance:")
print(f"  Mass term (j·ω·M_ms): {Z_m_ms:.2e} N·s/m")
print(f"  Compliance term (1/j·ω·C_ms): {Z_c_ms:.2e} N·s/m")
print(f"  Resistance term (R_ms): {Z_r_ms:.2e} N·s/m")
print(f"  Total driver mechanical: {Z_mech_driver:.2e} N·s/m")
print(f"  |Z_mech_driver|: {np.abs(Z_mech_driver):.2e} N·s/m")
print()

# Total mechanical impedance
Z_mech_total = Z_mech_driver + z_total_mech
print(f"Total mechanical impedance (driver + acoustic load):")
print(f"  Z_mech_total = Z_mech_driver + Z_acoustic_mech")
print(f"  Z_mech_total = {Z_mech_driver:.2e} + {z_total_mech:.2e}")
print(f"  Z_mech_total = {Z_mech_total:.2e} N·s/m")
print(f"  |Z_mech_total|: {np.abs(Z_mech_total):.2e} N·s/m")
print()

# Motional impedance
Z_motional = (BL ** 2) / Z_mech_total
print(f"Motional impedance:")
print(f"  Z_motional = (BL²) / Z_mech_total")
print(f"  Z_motional = {BL**2:.2e} / {Z_mech_total:.2e}")
print(f"  Z_motional = {Z_motional:.2e} Ω")
print(f"  |Z_motional|: {np.abs(Z_motional):.2e} Ω")
print()

# Total electrical impedance
Z_e_total = R_e + Z_motional
print(f"Total electrical impedance:")
print(f"  Z_e = R_e + Z_motional")
print(f"  Z_e = {R_e:.2f} + {Z_motional:.2f}")
print(f"  Z_e = {Z_e_total:.2e} Ω")
print(f"  |Z_e|: {np.abs(Z_e_total):.2f} Ω")
print()

# Compare to Hornresp
print("Step 7: Comparison with Hornresp")
print("-" * 80)

Ze_hornresp = 22.49
Ze_calculated = np.abs(Z_e_total)
error_pct = (Ze_calculated - Ze_hornresp) / Ze_hornresp * 100

print(f"Hornresp Ze: {Ze_hornresp:.2f} Ω")
print(f"Calculated Ze: {Ze_calculated:.2f} Ω")
print(f"Error: {error_pct:+.1f}%")
print()

if abs(error_pct) > 5:
    print("❌ ERROR TOO LARGE - Analysis needed:")
    print()
    print("Working backwards from target Ze = 22.49 Ω:")
    print("-" * 80)

    # Required motional impedance
    Z_motional_required = Ze_hornresp - R_e
    print(f"Required Z_motional: {Z_motional_required:.2f} Ω")

    # Required total mechanical
    Z_mech_total_required = (BL ** 2) / Z_motional_required
    print(f"Required Z_mech_total: {Z_mech_total_required:.2e} N·s/m")

    # Required acoustic mechanical impedance
    Z_acoustic_mech_required = Z_mech_total_required - Z_mech_driver
    print(f"Required Z_acoustic_mech: {Z_acoustic_mech_required:.2e} N·s/m")

    # Required acoustic impedance
    Z_acoustic_required = Z_acoustic_mech_required / (S_d ** 2)
    print(f"Required Z_acoustic: {Z_acoustic_required:.2e} Pa·s/m³")

    # Compare to calculated
    print()
    print(f"Calculated Z_acoustic: {np.abs(z_total_ac):.2e} Pa·s/m³")
    print(f"Ratio (required/calculated): {np.abs(Z_acoustic_required)/np.abs(z_total_ac):.2f}x")

    if np.abs(Z_acoustic_required) > np.abs(z_total_ac):
        mutual_deficit = (np.abs(Z_acoustic_required) - np.abs(z_parallel_ac)) / 2
        print()
        print(f"Required Z_mutual (acoustic): ±{mutual_deficit:.2e} Pa·s/m³")
        print(f"Current Z_mutual (acoustic): {np.abs(z_mutual_ac):.2e} Pa·s/m³")
        print(f"Multiplier needed: {mutual_deficit/np.abs(z_mutual_ac):.2f}x")

print()
print("=" * 80)
