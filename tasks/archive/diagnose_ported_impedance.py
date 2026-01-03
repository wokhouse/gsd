#!/usr/bin/env python3
"""
Diagnose ported box impedance calculation issues.

This script helps identify why the impedance calculation is not matching Hornresp.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import math
from gsd.driver.bc_drivers import get_bc_15ds115
from gsd.enclosure.ported_box import (
    ported_box_electrical_impedance,
    ported_box_impedance_small,
    calculate_optimal_port_dimensions
)


def diagnose_impedance():
    """Diagnose impedance calculation issues."""
    print("=" * 70)
    print("PORTED BOX IMPEDANCE DIAGNOSTIC")
    print("=" * 70)

    # Get driver parameters
    driver = get_bc_15ds115()

    print(f"\nDriver Parameters:")
    print(f"  Re: {driver.R_e:.2f} Ω")
    print(f"  Fs: {driver.F_s:.1f} Hz")
    print(f"  Qes: {driver.Q_es:.2f}")
    print(f"  Qms: {driver.Q_ms:.2f}")
    print(f"  Qts: {driver.Q_ts:.2f}")
    print(f"  Vas: {driver.V_as*1000:.1f} L")
    print(f"  BL: {driver.BL:.1f} T·m")
    print(f"  Mmd: {driver.M_md*1000:.2f} g")
    print(f"  Cms: {driver.C_ms*1e6:.2f} mm/N")
    print(f"  Sd: {driver.S_d*1e4:.1f} cm²")
    print(f"  Le: {driver.L_e*1000:.1f} mH")

    # B4 alignment
    Vb = driver.V_as
    Fb = driver.F_s

    # Calculate port dimensions
    port_area, port_length, _ = calculate_optimal_port_dimensions(driver, Vb, Fb)

    print(f"\nBox Parameters:")
    print(f"  Vb: {Vb*1000:.1f} L")
    print(f"  Fb: {Fb:.1f} Hz")
    print(f"  Port Area: {port_area*10000:.1f} cm²")
    print(f"  Port Length: {port_length*100:.1f} cm")

    # Test at key frequencies
    test_freqs = [20, 25, 30, 33, 40, 50, 70, 100, 150, 200]

    print("\n" + "=" * 70)
    print("IMPEDANCE CALCULATION COMPARISON")
    print("=" * 70)
    print(f"{'Freq (Hz)':>10} | {'Small Model (Ω)':>16} | {'Circuit Model (Ω)':>17} | {'Hornresp (Ω)':>15}")
    print("-" * 70)

    # Load Hornresp reference data
    hornresp_file = "imports/bc15ds115_b4_alignment_sim.txt"
    hornresp_freq, hornresp_spl, hornresp_ze = load_hornresp_data(hornresp_file)

    for freq in test_freqs:
        # Small model
        Qp = 7.0  # Default port Q
        try:
            Z_small = ported_box_impedance_small(freq, driver, Vb, Fb, Qp)
            Z_small_mag = abs(Z_small)
        except Exception as e:
            Z_small_mag = float('nan')
            print(f"Error in Small model at {freq} Hz: {e}")

        # Circuit model (default in ported_box_electrical_impedance)
        try:
            result_circuit = ported_box_electrical_impedance(
                freq, driver, Vb, Fb, port_area, port_length,
                voltage=2.83, impedance_model="circuit"
            )
            Z_circuit_mag = result_circuit['Ze_magnitude']
        except Exception as e:
            Z_circuit_mag = float('nan')
            print(f"Error in circuit model at {freq} Hz: {e}")

        # Hornresp reference
        idx = np.argmin(np.abs(hornresp_freq - freq))
        hornresp_ze_at_freq = hornresp_ze[idx]

        print(f"{freq:>10.1f} | {Z_small_mag:>16.1f} | {Z_circuit_mag:>17.1f} | {hornresp_ze_at_freq:>15.1f}")

    print("\n" + "=" * 70)
    print("DIAGNOSTIC NOTES")
    print("=" * 70)

    print("\nExpected behavior (Hornresp):")
    print("  - Dual impedance peaks: ~23 Hz and ~47 Hz")
    print("  - Impedance dip at Fb (33 Hz): ~5-6 Ω (close to Re)")
    print("  - Low frequencies (20 Hz): ~140 Ω")
    print("  - High frequencies (200 Hz): ~13 Ω")

    print("\nIf Small model is flat (~150 Ω):")
    print("  - Transfer function implementation may have bug")
    print("  - Check denominator polynomial coefficients")
    print("  - Verify Q_ES value is correct")

    print("\nIf Circuit model shows peaks:")
    print("  - Coupled resonator model is working")
    print("  - Issue is with Small's transfer function")
    print("  - Use circuit model for now")

    print("\n" + "=" * 70)


def load_hornresp_data(filepath):
    """Load Hornresp simulation results from text file."""
    frequencies = []
    spl_values = []
    impedances = []

    with open(filepath, 'r') as f:
        lines = f.readlines()

    # Skip header line
    for line in lines[2:]:  # Skip header and column labels
        parts = line.split()
        if len(parts) >= 6:
            try:
                freq = float(parts[0])
                spl = float(parts[4])
                ze = float(parts[5])

                frequencies.append(freq)
                spl_values.append(spl)
                impedances.append(ze)
            except ValueError:
                continue

    return np.array(frequencies), np.array(spl_values), np.array(impedances)


if __name__ == "__main__":
    diagnose_impedance()
