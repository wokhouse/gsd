"""Diagnostic script to find what Z_up value gives correct Ze at 50 Hz."""
import sys
sys.path.insert(0, 'src')

import numpy as np
from gsd.simulation.types import TappedHorn
from gsd.simulation.horn_theory import MediumProperties
from gsd.driver.parameters import ThieleSmallParameters

# Hornresp standard conditions
MEDIUM = MediumProperties(rho=1.18, c=343.0)

# Driver from Hornresp parameters
DRIVER = ThieleSmallParameters(
    S_d=855e-4,       # 855 cm²
    BL=21.2,          # T·m
    M_md=0.147,       # 147 g
    R_ms=6.80,        # N·s/m
    R_e=5.20,         # Ω
    L_e=1.40e-3,      # 1.40 mH
    C_ms=1.04e-4,     # m/N
)

# Horn geometry
HORN = TappedHorn(
    upstream_throat_area=150.0,
    tap_area=855.0,
    downstream_mouth_area=6000.0,
    upstream_length=180.0,
    downstream_length=200.0,
    upstream_profile='exponential',
    downstream_profile='exponential',
    intermediate_area=2265.0,
)

# Target: Hornresp Ze at 50 Hz
TARGET_ZE = 22.49  # Ω
FREQ = 50.0  # Hz

print(f"=== Finding Z_up that gives Ze = {TARGET_ZE} Ω at {FREQ} Hz ===\n")

# Calculate what Z_acoustic would give this Ze
omega = 2 * np.pi * FREQ

# Driver mechanical impedance
z_mech_stiffness = 1.0 / (1j * omega * DRIVER.C_ms)
z_mech_mass = 1j * omega * DRIVER.M_md
z_mech_resistance = DRIVER.R_ms
z_mech_driver = z_mech_resistance + z_mech_mass + z_mech_stiffness

print(f"Driver mechanical impedance:")
print(f"  Z_mech_driver = {z_mech_driver:.3f} N·s/m")
print(f"  |Z_mech_driver| = {np.abs(z_mech_driver):.3f} N·s/m\n")

# Work backwards: Ze_target -> Z_motional -> Z_mech_total -> Z_mech_acoustic -> Z_acoustic
# Z_e = Z_vc + Z_mot
# Z_mot = (BL)² / Z_mech_total
# Z_mech_total = Z_mech_driver + Z_mech_acoustic
# Z_mech_acoustic = Z_acoustic × S_d²

z_voice_coil = DRIVER.R_e + 1j * omega * DRIVER.L_e
z_motional = TARGET_ZE - z_voice_coil
z_mech_total = (DRIVER.BL ** 2) / z_motional
z_mech_acoustic = z_mech_total - z_mech_driver
z_acoustic_target = z_mech_acoustic / (DRIVER.S_d ** 2)

print(f"Target electrical impedance breakdown:")
print(f"  Z_voice_coil = {z_voice_coil:.3f} Ω")
print(f"  Z_motional = {z_motional:.3f} Ω")
print(f"  Z_mech_total = {z_mech_total:.3f} N·s/m")
print(f"  Z_mech_acoustic = {z_mech_acoustic:.3f} N·s/m")
print(f"  Z_acoustic_target = {z_acoustic_target:.3f} Pa·s/m³")
print(f"  |Z_acoustic_target| = {np.abs(z_acoustic_target):.3e} Pa·s/m³\n")

# Get current Z_down from the code
from gsd.simulation.tapped_horn_theory import downstream_section_impedance

z_down = downstream_section_impedance(np.array([FREQ]), HORN, MEDIUM)[0]
print(f"Current downstream impedance:")
print(f"  Z_down = {z_down:.3f} Pa·s/m³")
print(f"  |Z_down| = {np.abs(z_down):.3e} Pa·s/m³\n")

# For parallel combination: Z_tap = (Z_up * Z_down) / (Z_up + Z_down)
# If Z_tap = Z_acoustic_target, solve for Z_up
# Z_acoustic * (Z_up + Z_down) = Z_up * Z_down
# Z_acoustic * Z_up + Z_acoustic * Z_down = Z_up * Z_down
# Z_acoustic * Z_down = Z_up * (Z_down - Z_acoustic)
# Z_up = (Z_acoustic * Z_down) / (Z_down - Z_acoustic)

z_up_needed = (z_acoustic_target * z_down) / (z_down - z_acoustic_target)

print(f"Required upstream impedance:")
print(f"  Z_up_needed = {z_up_needed:.3f} Pa·s/m³")
print(f"  |Z_up_needed| = {np.abs(z_up_needed):.3e} Pa·s/m³\n")

print("Comparison with current formulas:")
print(f"  Current Z_up (A/C) ≈ 1.03e+04 Pa·s/m³")
print(f"  Z_up needed ≈ {np.abs(z_up_needed):.3e} Pa·s/m³")
print(f"  Ratio: {np.abs(z_up_needed) / 1.03e+04:.3f}\n")

# Check if this would give the right Ze
z_tap_test = (z_up_needed * z_down) / (z_up_needed + z_down)
z_mech_acoustic_test = z_tap_test * (DRIVER.S_d ** 2)
z_mech_total_test = z_mech_driver + z_mech_acoustic_test
z_motional_test = (DRIVER.BL ** 2) / z_mech_total_test
z_e_test = z_voice_coil + z_motional_test

print("Validation:")
print(f"  Z_tap with Z_up_needed = {np.abs(z_tap_test):.3e} Pa·s/m³")
print(f"  Ze_calculated = {np.abs(z_e_test):.3f} Ω")
print(f"  Ze_target = {TARGET_ZE:.3f} Ω")
print(f"  Match: {np.abs(np.abs(z_e_test) - TARGET_ZE) < 0.01}")
