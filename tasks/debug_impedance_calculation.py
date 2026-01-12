"""Detailed debug of impedance calculation at 50 Hz."""
import sys
sys.path.insert(0, 'src')

import numpy as np
from gsd.simulation.types import TappedHorn
from gsd.simulation.horn_theory import MediumProperties
from gsd.simulation.tapped_horn_theory import (
    upstream_section_impedance,
    downstream_section_impedance,
    tapped_horn_tap_impedance,
)
from gsd.driver.parameters import ThieleSmallParameters

MEDIUM = MediumProperties(rho=1.18, c=343.0)
FREQ = 50.0

DRIVER = ThieleSmallParameters(
    S_d=855e-4, BL=21.2, M_md=0.147, R_ms=6.80, R_e=5.20, L_e=1.40e-3, C_ms=1.04e-4,
)

HORN = TappedHorn(
    upstream_throat_area=150.0, tap_area=855.0, downstream_mouth_area=6000.0,
    upstream_length=180.0, downstream_length=200.0,
    upstream_profile='exponential', downstream_profile='exponential',
    intermediate_area=2265.0,
)

print(f"=== Impedance Calculation Debug at {FREQ} Hz ===\n")

# Get impedances
z_up = upstream_section_impedance(np.array([FREQ]), HORN, MEDIUM)[0]
z_down = downstream_section_impedance(np.array([FREQ]), HORN, MEDIUM)[0]
z_tap = tapped_horn_tap_impedance(np.array([FREQ]), HORN, MEDIUM)[0]

print("Upstream impedance:")
print(f"  Z_up = {z_up:.6e}  |{np.abs(z_up):.6e}|")

print("\nDownstream impedance:")
print(f"  Z_down = {z_down:.6e}  |{np.abs(z_down):.6e}|")

print("\nTap impedance (parallel combination):")
print(f"  Z_tap = (Z_up × Z_down) / (Z_up + Z_down)")
print(f"  Z_tap = {z_tap:.6e}  |{np.abs(z_tap):.6e}|")

# Verify parallel combination
z_tap_check = (z_up * z_down) / (z_up + z_down)
print(f"  Z_tap (direct calc) = {z_tap_check:.6e}  |{np.abs(z_tap_check):.6e}|")
print(f"  Match: {np.allclose(z_tap, z_tap_check)}")

# Convert to mechanical impedance
z_mech_acoustic = z_tap * (DRIVER.S_d ** 2)
print(f"\nMechanical acoustic impedance:")
print(f"  Z_mech_acoustic = Z_tap × S_d²")
print(f"  S_d = {DRIVER.S_d:.6e} m²")
print(f"  Z_mech_acoustic = {z_mech_acoustic:.6e}  |{np.abs(z_mech_acoustic):.6e}|")

# Driver mechanical impedance
omega = 2 * np.pi * FREQ
z_mech_driver = DRIVER.R_ms + 1j * omega * DRIVER.M_md + 1 / (1j * omega * DRIVER.C_ms)
print(f"\nDriver mechanical impedance:")
print(f"  Z_mech_driver = {z_mech_driver:.6e}  |{np.abs(z_mech_driver):.6e}|")

# Total mechanical impedance
z_mech_total = z_mech_driver + z_mech_acoustic
print(f"\nTotal mechanical impedance:")
print(f"  Z_mech_total = {z_mech_total:.6e}  |{np.abs(z_mech_total):.6e}|")

# Motional impedance
z_motional = (DRIVER.BL ** 2) / z_mech_total
print(f"\nMotional impedance:")
print(f"  Z_motional = (BL)² / Z_mech_total")
print(f"  BL = {DRIVER.BL:.3f} T·m")
print(f"  Z_motional = {z_motional:.6e}  |{np.abs(z_motional):.6e}|")

# Voice coil impedance
z_vc = DRIVER.R_e + 1j * omega * DRIVER.L_e
print(f"\nVoice coil impedance:")
print(f"  Z_vc = {z_vc:.6e}  |{np.abs(z_vc):.6e}|")

# Total electrical impedance
z_e = z_vc + z_motional
print(f"\nTotal electrical impedance:")
print(f"  Z_e = Z_vc + Z_motional")
print(f"  Z_e = {z_e:.6e}  |{np.abs(z_e):.6e}| Ω")

# Target
target_ze = 22.49
print(f"\nTarget Ze = {target_ze:.3f} Ω")
print(f"Calculated Ze = {np.abs(z_e):.3f} Ω")
print(f"Error = {(np.abs(z_e) - target_ze) / target_ze * 100:+.1f}%")
