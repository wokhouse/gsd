"""Find T-matrix impedance formula that gives Z_up = 3.054e+03 at 50 Hz."""
import sys
sys.path.insert(0, 'src')

import numpy as np
from gsd.simulation.types import TappedHorn, ExponentialHorn
from gsd.simulation.horn_theory import MediumProperties, exponential_horn_tmatrix

MEDIUM = MediumProperties(rho=1.18, c=343.0)
FREQ = 50.0

# Upstream horn geometry
upstream_horn = ExponentialHorn(
    throat_area=150.0,
    mouth_area=855.0,
    length=180.0,
)

# Get T-matrix elements
a, b, c, d = exponential_horn_tmatrix(np.array([FREQ]), upstream_horn, MEDIUM)

print("=== T-Matrix Elements at 50 Hz ===")
print(f"A = {a[0]:.6f}")
print(f"B = {b[0]:.6f}")
print(f"C = {c[0]:.6f}")
print(f"D = {d[0]:.6f}")
print(f"\nDeterminant (AD - BC) = {(a[0]*d[0] - b[0]*c[0]):.15f}")
print(f"Should be ≈ 1.0 for reciprocal network\n")

# Target Z_up
target_z = 3.054e+03
print(f"Target |Z_up| = {target_z:.3e}\n")

# Try different formulas
formulas = {
    "A/C": a/c,
    "C/A": c/a,
    "B/D": b/d,
    "D/B": d/b,
    "A*D/B*C": (a*d)/(b*c),
    "sqrt(A/B*C/D)": np.sqrt((a/c)*(b/d)),
    "sqrt(B/A*D/C)": np.sqrt((b/a)*(d/c)),
    "A*D": a*d,
    "B*C": b*c,
}

print("=== Testing Different Formulas ===")
for name, result in formulas.items():
    print(f"{name:20s} = {result[0]:.6e}  |{np.abs(result[0]):.6e}|")

# Check if any formula magnitude matches
print(f"\n=== Looking for formula with |Z| ≈ {target_z:.3e} ===")

# Try combinations with coefficients
for coeff_a in [1, 2, 0.5, 1/3]:
    for coeff_b in [1, 2, 0.5]:
        test = (coeff_a * a) / (coeff_b * c)
        if abs(np.abs(test[0]) - target_z) / target_z < 0.1:  # Within 10%
            print(f"  ({coeff_a}A)/({coeff_b}C) = {test[0]:.6e}  |{np.abs(test[0]):.6e}| ✓")

# Check throat impedance directly from transmission line theory
print(f"\n=== Transmission Line Theory ===")
print("For exponential horn with closed throat:")
print(f"  Standard formula: Z_up = A/C = {np.abs(a/c)[0]:.6e}")
print(f"  Target: Z_up = {target_z:.6e}")
print(f"  Ratio: {target_z / np.abs(a/c)[0]:.3f}")

# Maybe the throat isn't perfectly closed?
print(f"\n=== If throat has finite radiation impedance ===")
# For a closed throat with small opening, Z_throat is large but finite
# Z_load = Z_rad (at throat)
# Z_up = (A*Z_rad + B) / (C*Z_rad + D)

# Circular piston radiation at throat (150 cm²)
from gsd.simulation.horn_theory import circular_piston_radiation_impedance
z_rad_throat = circular_piston_radiation_impedance(np.array([FREQ]), upstream_horn.throat_area, MEDIUM)[0]

print(f"Z_rad at throat (150 cm²) = {z_rad_throat:.6e}  |{np.abs(z_rad_throat):.6e}|")

z_up_with_rad = (a[0]*z_rad_throat + b[0]) / (c[0]*z_rad_throat + d[0])
print(f"Z_up with throat radiation = {z_up_with_rad:.6e}  |{np.abs(z_up_with_rad):.6e}|")
print(f"Ratio to target: {np.abs(z_up_with_rad)/target_z:.3f}")
