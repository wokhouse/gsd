#!/usr/bin/env python3
"""
Validate conical horn implementation against Hornresp simulation results.

Uses Hornresp simulation files from imports/ directory:
- case 1: S1=150cm², S2=1500cm², L12=120cm (Con = 120)
- case 2: S1=200cm², S2=800cm², L12=50cm (Con = 50)

Driver: BC 8NDL51

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
from gsd.driver.parameters import ThieleSmallParameters


def load_hornresp_sim(filepath):
    """Load Hornresp simulation results from tab-separated file.

    Args:
        filepath: Path to Hornresp .txt file

    Returns:
        dict with keys: freq, Ra, Xa, Za, SPL, Ze, Xd, etc.
    """
    data = np.loadtxt(filepath, skiprows=1, delimiter='\t')
    return {
        'freq': data[:, 0],
        'Ra': data[:, 1],  # Acoustic resistance (normalized)
        'Xa': data[:, 2],  # Acoustic reactance (normalized)
        'Za': data[:, 3],  # Acoustic impedance magnitude (normalized)
        'SPL': data[:, 4],  # SPL (dB)
        'Ze': data[:, 5],  # Electrical impedance (ohms)
    }


def bc_8ndl51_parameters():
    """Return BC 8NDL51 Thiele-Small parameters."""
    # From Hornresp export
    return ThieleSmallParameters(
        M_md=0.02629,  # 26.29g
        C_ms=1.50e-4,  # m/N
        R_ms=2.44,     # N·s/m
        R_e=2.60,      # ohms
        L_e=0.15e-3,   # H (0.15mH)
        BL=7.30,       # T·m
        S_d=0.0220,    # m² (220cm²)
    )


def validate_case_1():
    """Validate Case 1: S1=150cm², S2=1500cm², L12=120cm"""
    print("=" * 60)
    print("CASE 1: Conical Horn Validation")
    print("=" * 60)

    # Horn parameters (Con = 120 means L12 = 120cm)
    S1 = 150.0   # cm²
    S2 = 1500.0  # cm²
    L12 = 120.0  # cm (from Con = 120)

    print(f"\nHorn Parameters:")
    print(f"  S1 (throat): {S1} cm²")
    print(f"  S2 (mouth): {S2} cm²")
    print(f"  L12 (length): {L12} cm")
    print(f"  Expansion ratio: {S2/S1:.1f}:1")

    # Load Hornresp results
    # Path to imports directory (from project root)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    hornresp_path = os.path.join(project_root, "imports/case_1_sim.txt")

    if not os.path.exists(hornresp_path):
        print(f"\n❌ Hornresp file not found: {hornresp_path}")
        print("   Please ensure the file is in the imports/ directory")
        return None

    hornresp_data = load_hornresp_sim(hornresp_path)
    freq_hr = hornresp_data['freq']
    Ra_hr = hornresp_data['Ra']
    Xa_hr = hornresp_data['Xa']
    Za_hr = hornresp_data['Za']

    # Create conical horn
    horn = ConicalHorn(
        throat_area=S1 / 10000,  # cm² → m²
        mouth_area=S2 / 10000,   # cm² → m²
        length=L12 / 100         # cm → m
    )

    # Calculate viberesp throat impedance
    z_throat_vb = conical_horn_throat_impedance(freq_hr, horn)

    # Hornresp normalizes by (ρc/S1), not just ρc
    # Za_hornresp = Z_throat / (ρc/S1) = Z_throat * S1 / (ρc)
    Z0 = 1.205 * 344.0  # ρc
    S1_m2 = S1 / 10000  # throat area in m²

    Za_vb = np.abs(z_throat_vb) * S1_m2 / Z0
    Ra_vb = np.real(z_throat_vb) * S1_m2 / Z0
    Xa_vb = np.imag(z_throat_vb) * S1_m2 / Z0

    # Calculate deviations
    Za_dev = np.abs((Za_vb - Za_hr) / Za_hr) * 100
    Ra_dev = np.abs((Ra_vb - Ra_hr) / (Ra_hr + 1e-12)) * 100
    Xa_dev = np.abs((Xa_vb - Xa_hr) / (Xa_hr + 1e-12)) * 100

    print(f"\nValidation Results (vs Hornresp):")
    print(f"  Frequency Range: {freq_hr[0]:.1f} - {freq_hr[-1]:.1f} Hz")
    print(f"  Number of points: {len(freq_hr)}")

    # Statistics
    print(f"\nMagnitude (Za) Deviation:")
    print(f"  Max: {np.max(Za_dev):.2f}%")
    print(f"  Mean: {np.mean(Za_dev):.2f}%")
    print(f"  Median: {np.median(Za_dev):.2f}%")

    print(f"\nResistance (Ra) Deviation:")
    print(f"  Max: {np.max(Ra_dev):.2f}%")
    print(f"  Mean: {np.mean(Ra_dev):.2f}%")

    print(f"\nReactance (Xa) Deviation:")
    print(f"  Max: {np.max(Xa_dev):.2f}%")
    print(f"  Mean: {np.mean(Xa_dev):.2f}%")

    # Check tolerance thresholds
    Za_pass = np.max(Za_dev) < 2.0
    Ra_pass = np.max(Ra_dev) < 2.0
    Xa_pass = np.max(Xa_dev) < 2.0

    print(f"\nValidation Status:")
    print(f"  Za (<2%): {'✓ PASS' if Za_pass else '✗ FAIL'}")
    print(f"  Ra (<2%): {'✓ PASS' if Ra_pass else '✗ FAIL'}")
    print(f"  Xa (<2%): {'✓ PASS' if Xa_pass else '✗ FAIL'}")

    all_pass = Za_pass and Ra_pass and Xa_pass
    print(f"\n  Overall: {'✓ ALL TESTS PASSED' if all_pass else '✗ SOME TESTS FAILED'}")

    return {
        'case': 1,
        'Za_dev_max': np.max(Za_dev),
        'Za_dev_mean': np.mean(Za_dev),
        'pass': all_pass,
    }


def validate_case_2():
    """Validate Case 2: S1=200cm², S2=800cm², L12=50cm"""
    print("\n" + "=" * 60)
    print("CASE 2: Conical Horn Validation")
    print("=" * 60)

    # Horn parameters (Con = 50 means L12 = 50cm)
    S1 = 200.0   # cm²
    S2 = 800.0   # cm²
    L12 = 50.0   # cm (from Con = 50)

    print(f"\nHorn Parameters:")
    print(f"  S1 (throat): {S1} cm²")
    print(f"  S2 (mouth): {S2} cm²")
    print(f"  L12 (length): {L12} cm")
    print(f"  Expansion ratio: {S2/S1:.1f}:1")

    # Load Hornresp results
    # Path to imports directory (from project root)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    hornresp_path = os.path.join(project_root, "imports/case_2_sim.txt")

    if not os.path.exists(hornresp_path):
        print(f"\n❌ Hornresp file not found: {hornresp_path}")
        print("   Please ensure the file is in the imports/ directory")
        return None

    hornresp_data = load_hornresp_sim(hornresp_path)
    freq_hr = hornresp_data['freq']
    Ra_hr = hornresp_data['Ra']
    Xa_hr = hornresp_data['Xa']
    Za_hr = hornresp_data['Za']

    # Create conical horn
    horn = ConicalHorn(
        throat_area=S1 / 10000,  # cm² → m²
        mouth_area=S2 / 10000,   # cm² → m²
        length=L12 / 100         # cm → m
    )

    # Calculate viberesp throat impedance
    z_throat_vb = conical_horn_throat_impedance(freq_hr, horn)

    # Hornresp normalizes by (ρc/S1), not just ρc
    # Za_hornresp = Z_throat / (ρc/S1) = Z_throat * S1 / (ρc)
    Z0 = 1.205 * 344.0  # ρc
    S1_m2 = S1 / 10000  # throat area in m²

    Za_vb = np.abs(z_throat_vb) * S1_m2 / Z0
    Ra_vb = np.real(z_throat_vb) * S1_m2 / Z0
    Xa_vb = np.imag(z_throat_vb) * S1_m2 / Z0

    # Calculate deviations
    Za_dev = np.abs((Za_vb - Za_hr) / Za_hr) * 100
    Ra_dev = np.abs((Ra_vb - Ra_hr) / (Ra_hr + 1e-12)) * 100
    Xa_dev = np.abs((Xa_vb - Xa_hr) / (Xa_hr + 1e-12)) * 100

    print(f"\nValidation Results (vs Hornresp):")
    print(f"  Frequency Range: {freq_hr[0]:.1f} - {freq_hr[-1]:.1f} Hz")
    print(f"  Number of points: {len(freq_hr)}")

    # Statistics
    print(f"\nMagnitude (Za) Deviation:")
    print(f"  Max: {np.max(Za_dev):.2f}%")
    print(f"  Mean: {np.mean(Za_dev):.2f}%")
    print(f"  Median: {np.median(Za_dev):.2f}%")

    print(f"\nResistance (Ra) Deviation:")
    print(f"  Max: {np.max(Ra_dev):.2f}%")
    print(f"  Mean: {np.mean(Ra_dev):.2f}%")

    print(f"\nReactance (Xa) Deviation:")
    print(f"  Max: {np.max(Xa_dev):.2f}%")
    print(f"  Mean: {np.mean(Xa_dev):.2f}%")

    # Check tolerance thresholds
    Za_pass = np.max(Za_dev) < 2.0
    Ra_pass = np.max(Ra_dev) < 2.0
    Xa_pass = np.max(Xa_dev) < 2.0

    print(f"\nValidation Status:")
    print(f"  Za (<2%): {'✓ PASS' if Za_pass else '✗ FAIL'}")
    print(f"  Ra (<2%): {'✓ PASS' if Ra_pass else '✗ FAIL'}")
    print(f"  Xa (<2%): {'✓ PASS' if Xa_pass else '✗ FAIL'}")

    all_pass = Za_pass and Ra_pass and Xa_pass
    print(f"\n  Overall: {'✓ ALL TESTS PASSED' if all_pass else '✗ SOME TESTS FAILED'}")

    return {
        'case': 2,
        'Za_dev_max': np.max(Za_dev),
        'Za_dev_mean': np.mean(Za_dev),
        'pass': all_pass,
    }


def main():
    """Run all validation cases."""
    print("\n" + "=" * 60)
    print("CONICAL HORN VALIDATION vs HORNRESP")
    print("=" * 60)
    print("\nUsing Hornresp simulation files from imports/ directory")
    print("Note: 'Con = 120' means conical horn with L12 = 120cm")

    results = []

    # Validate both cases
    result1 = validate_case_1()
    if result1:
        results.append(result1)

    result2 = validate_case_2()
    if result2:
        results.append(result2)

    # Summary
    if results:
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        for r in results:
            status = "✓ PASS" if r['pass'] else "✗ FAIL"
            print(f"  Case {r['case']}: Max deviation = {r['Za_dev_max']:.2f}% [{status}]")

        all_pass = all(r['pass'] for r in results)
        print(f"\n  Overall Result: {'✓ ALL TESTS PASSED' if all_pass else '✗ SOME TESTS FAILED'}")

        if all_pass:
            print("\n  ✅ Conical horn implementation validated against Hornresp")
            print("     Deviation < 2% across all test cases")
        else:
            print("\n  ⚠️  Some tests exceeded 2% tolerance")
            print("     Review implementation for discrepancies")


if __name__ == "__main__":
    main()
