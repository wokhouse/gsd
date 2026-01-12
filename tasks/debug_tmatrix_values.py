"""Debug script to print T-matrix values with area scaling."""
import sys
sys.path.insert(0, 'src')

import numpy as np
from gsd.simulation.types import TappedHorn
from gsd.simulation.horn_theory import MediumProperties, exponential_horn_tmatrix

MEDIUM = MediumProperties(rho=1.18, c=343.0)
FREQ = 50.0
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

# Get upstream section
upstream = HORN.upstream_section()
print(f"Upstream horn:")
print(f"  Throat area: {upstream.throat_area*1e4} cm²")
print(f"  Mouth area: {upstream.mouth_area*1e4} cm²")
print(f"  Length: {upstream.length*100} cm")
print(f"  Flare constant: {upstream.flare_constant} m⁻¹\n")

# Calculate T-matrix
a, b, c, d = exponential_horn_tmatrix(np.array([FREQ]), upstream, MEDIUM)

print("T-matrix elements (dimensionless):")
print(f"  A = {a}")
print(f"  B = {b}")
print(f"  C = {c}")
print(f"  D = {d}")
print(f"  AD - BC = {(a*d - b*c)}\n")

# Calculate characteristic impedances
rho = MEDIUM.rho
c_sound = MEDIUM.c
S1 = upstream.throat_area  # Already in m²
S2 = upstream.mouth_area

Z0_throat = rho * c_sound / S1
Z0_mouth = rho * c_sound / S2

print(f"Characteristic impedances:")
print(f"  Z0_throat = ρc/S1 = {Z0_throat:.3f} Pa·s/m³")
print(f"  Z0_mouth = ρc/S2 = {Z0_mouth:.3f} Pa·s/m³\n")

# Try different impedance formulas
Z_A_over_C = a[0] / c[0]
Z_C_over_A = c[0] / a[0]
Z_B_over_D = b[0] / d[0]
Z_D_over_B = d[0] / b[0]

print("Impedance formulas (dimensionless T-matrix only):")
print(f"  A/C = {Z_A_over_C:.6e}  |{np.abs(Z_A_over_C):.6e}|")
print(f"  C/A = {Z_C_over_A:.6e}  |{np.abs(Z_C_over_A):.6e}|")
print(f"  B/D = {Z_B_over_D:.6e}  |{np.abs(Z_B_over_D):.6e}|")
print(f"  D/B = {Z_D_over_B:.6e}  |{np.abs(Z_D_over_B):.6e}|")

# Scale by characteristic impedance
print(f"\nScaled by throat characteristic impedance ({Z0_throat:.0f}):")
print(f"  (A/C) × Z0_throat = {Z_A_over_C * Z0_throat:.6e}  |{np.abs(Z_A_over_C * Z0_throat):.6e}|")
print(f"  (C/A) × Z0_throat = {Z_C_over_A * Z0_throat:.6e}  |{np.abs(Z_C_over_A * Z0_throat):.6e}|")

print(f"\nScaled by mouth characteristic impedance ({Z0_mouth:.0f}):")
print(f"  (A/C) × Z0_mouth = {Z_A_over_C * Z0_mouth:.6e}  |{np.abs(Z_A_over_C * Z0_mouth):.6e}|")
print(f"  (C/A) × Z0_mouth = {Z_C_over_A * Z0_mouth:.6e}  |{np.abs(Z_C_over_A * Z0_mouth):.6e}|")

# What about the actual upstream_section_impedance()?
from gsd.simulation.tapped_horn_theory import upstream_section_impedance

z_up_actual = upstream_section_impedance(np.array([FREQ]), HORN, MEDIUM)
print(f"\nActual upstream_section_impedance() result:")
print(f"  Z_up = {z_up_actual[0]:.6e}  |{np.abs(z_up_actual[0]):.6e}|")

# Check ratio
print(f"\nRatio check:")
print(f"  Z_up / [(A/C) × Z0_throat] = {z_up_actual[0] / (Z_A_over_C * Z0_throat):.6f}")
print(f"  Z_up / [(C/A) × Z0_throat] = {z_up_actual[0] / (Z_C_over_A * Z0_throat):.6f}")

# Target from diagnostic
target_z = 3.054e+03
print(f"\nTarget Z_up (from diagnostic): |Z| = {target_z:.6e}")
print(f"Need formula that gives ~{target_z / Z0_throat:.6f} × Z0_throat")
