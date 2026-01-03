#!/usr/bin/env python3
"""
Generate conical horn validation test case.

This script creates a Hornresp export file and calculates viberesp
results for the same conical horn configuration.

Test Case: CON Midrange TC1 - Pure Conical Horn Theory

Parameters:
- Throat area (S1): 50 cm² = 0.005 m²
- Mouth area (S2): 500 cm² = 0.05 m²
- Length (L12): 50 cm = 0.5 m
- Flare type: Conical (CON in Hornresp)
- No driver, no chambers (pure horn theory)

This validates:
- Spherical wave T-matrix calculation
- Throat impedance transformation
- Mouth radiation impedance
- No sharp cutoff behavior (conical horns don't have exponential-like cutoff)

Literature:
- Olson (1947), Section 5.15 - Conical horn geometry
- Olson (1947), Eq. 5.16 - Infinite conical horn impedance
- J.O. Smith, "Conical Acoustic Tubes" - Spherical wave theory
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

import numpy as np
from gsd.simulation.types import ConicalHorn
from gsd.simulation.horn_theory import conical_horn_throat_impedance
from gsd.hornresp.export import export_to_hornresp


def main():
    """Generate validation data for conical horn TC1."""

    # Conical horn parameters (matching exponential TC1 for comparison)
    S1 = 0.005  # Throat area [m²] (50 cm²)
    S2 = 0.05   # Mouth area [m²] (500 cm²)
    L12 = 0.5   # Length [m] (50 cm)

    # Create conical horn
    horn = ConicalHorn(throat_area=S1, mouth_area=S2, length=L12)

    # Calculate x0 (distance from apex to throat)
    x0 = horn.x0

    print(f"Conical Horn TC1 - Pure Horn Theory")
    print(f"=" * 50)
    print(f"Throat area (S1): {S1*10000:.1f} cm²")
    print(f"Mouth area (S2): {S2*10000:.1f} cm²")
    print(f"Length (L12): {L12*100:.1f} cm")
    print(f"Apex distance (x0): {x0*100:.2f} cm")
    print(f"Expansion ratio: {S2/S1:.1f}:1")
    print()

    # Export to Hornresp format
    # Note: Hornresp doesn't have a native "conical horn" export type that
    # matches our spherical wave implementation exactly. We export as CON type.
    output_path = "tests/validation/horn_theory/con_midrange_tc1/horn_params.txt"

    # Create a dummy driver for Hornresp export (we'll ignore driver effects)
    # Use a very light driver with minimal influence on horn impedance
    class DummyDriver:
        def __init__(self):
            self.M_md = 0.001  # Very light (1g)
            self.C_ms = 1e-3   # Very stiff
            self.R_ms = 1.0    # Minimal damping
            self.R_e = 8.0     # 8 ohm
            self.L_e = 0       # No inductance
            self.BL = 1.0      # Weak motor
            self.S_d = S1      # Same as throat area

    driver = DummyDriver()

    # Export using Hornresp format
    # For conical horns, Hornresp uses CON type
    with open(output_path, 'w') as f:
        f.write("Viberesp Conical Horn TC1 - Pure Horn Theory Validation\n")
        f.write("|\n")
        f.write("|\n")
        f.write(" hornresp -file -\n")
        f.write("CON\n")
        f.write(f"{S1*10000:.2f}\n")  # S1 in cm²
        f.write(f"{S2*10000:.2f}\n")  # S2 in cm²
        f.write(f"{L12*100:.2f}\n")   # L12 in cm
        f.write("0.0\n")   # Ang (default)
        f.write("0.0\n")   # Fc (N/A for conical)
        f.write("0.0\n")   # Tc (N/A for conical)

    print(f"Exported Hornresp parameters to: {output_path}")
    print()

    # Calculate viberesp results
    print("Calculating viberesp results...")
    frequencies = np.logspace(1, 4, 100)  # 10 Hz to 10 kHz

    z_throat = conical_horn_throat_impedance(frequencies, horn)

    # Save viberesp results
    viberesp_path = "tests/validation/horn_theory/con_midrange_tc1/viberesp_results.txt"

    with open(viberesp_path, 'w') as f:
        f.write("# Viberesp Conical Horn TC1 - Throat Impedance\n")
        f.write("# Frequency [Hz], Re(Z) [Pa·s/m³], Im(Z) [Pa·s/m³], |Z| [Pa·s/m³]\n")
        for freq, z in zip(frequencies, z_throat):
            f.write(f"{freq:.3f}\t{z.real:.6e}\t{z.imag:.6e}\t{np.abs(z):.6e}\n")

    print(f"Saved viberesp results to: {viberesp_path}")
    print()

    # Print key characteristics
    print("Key Characteristics:")
    print(f"  Low frequency (20 Hz): Re={np.real(z_throat[0]):.3e}, Im={np.imag(z_throat[0]):.3e}")
    print(f"  Mid frequency (500 Hz): Re={np.real(z_throat[49]):.3e}, Im={np.imag(z_throat[49]):.3e}")
    print(f"  High frequency (10 kHz): Re={np.real(z_throat[-1]):.3e}, Im={np.imag(z_throat[-1]):.3e}")
    print()

    # Check that resistance rises smoothly (no sharp cutoff)
    resistance = np.real(z_throat)
    monotonic_check = np.all(np.diff(resistance[10:-10]) >= -np.max(resistance) * 0.01)

    print("Validation Checks:")
    print(f"  Resistance rises smoothly: {'✓' if monotonic_check else '✗'}")
    print(f"  (Conical horns have NO sharp cutoff like exponential horns)")
    print()

    print("Next Steps:")
    print("1. Import horn_params.txt into Hornresp")
    print("2. Calculate Acoustical Impedance at throat")
    print("3. Export results to sim.txt")
    print("4. Compare with viberesp_results.txt")


if __name__ == "__main__":
    main()
