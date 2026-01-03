#!/usr/bin/env python3
"""
Validate BC_15DS115 B4 alignment results against Hornresp simulation.

Compares viberesp predictions with Hornresp reference data to verify
the accuracy of the calibrated transfer function SPL calculation.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
from gsd.driver.bc_drivers import get_bc_15ds115
from gsd.enclosure.ported_box import (
    ported_box_electrical_impedance,
    calculate_optimal_port_dimensions
)


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


def get_viberesp_prediction(driver, Vb, Fb, port_area, port_length, frequencies):
    """Get viberesp predictions at specified frequencies."""
    spl_values = []
    impedances = []

    for freq in frequencies:
        result = ported_box_electrical_impedance(
            freq, driver, Vb, Fb, port_area, port_length,
            voltage=2.83, impedance_model="circuit",  # Use circuit model for impedance
            use_transfer_function_spl=True  # CRITICAL: Use calibrated TF for SPL
        )
        spl_values.append(result['SPL'])
        impedances.append(result['Ze_magnitude'])

    return np.array(spl_values), np.array(impedances)


def interpolate_hornresp(hornresp_freqs, hornresp_spl, target_freqs):
    """Interpolate Hornresp data to match target frequencies."""
    spl_interpolated = np.interp(target_freqs, hornresp_freqs, hornresp_spl)
    return spl_interpolated


def compare_results():
    """Compare viberesp predictions with Hornresp reference."""
    print("=" * 70)
    print("BC_15DS115 B4 ALIGNMENT - VALIDATION vs HORNRESP")
    print("=" * 70)

    # Get driver parameters
    driver = get_bc_15ds115()
    Vb = driver.V_as  # B4 alignment
    Fb = driver.F_s

    # Calculate port dimensions
    port_area, port_length, _ = calculate_optimal_port_dimensions(driver, Vb, Fb)

    print(f"\nDesign Parameters:")
    print(f"  Vb = {Vb*1000:.1f} L")
    print(f"  Fb = {Fb:.1f} Hz")
    print(f"  Port Area = {port_area*10000:.1f} cm²")
    print(f"  Port Length = {port_length*100:.1f} cm")
    print()

    # Load Hornresp data
    hornresp_file = "imports/bc15ds115_b4_alignment_sim.txt"
    hornresp_freq, hornresp_spl, hornresp_ze = load_hornresp_data(hornresp_file)

    print(f"Hornresp Data Loaded: {len(hornresp_freq)} frequency points")
    print(f"  Frequency range: {hornresp_freq[0]:.1f} - {hornresp_freq[-1]:.1f} Hz")
    print(f"  SPL range: {np.min(hornresp_spl):.1f} - {np.max(hornresp_spl):.1f} dB")
    print(f"  Impedance range: {np.min(hornresp_ze):.1f} - {np.max(hornresp_ze):.1f} Ω")
    print()

    # Select comparison frequencies (log-spaced)
    compare_freqs = np.logspace(np.log10(20), np.log10(200), 30)

    # Get viberesp predictions
    viberesp_spl, viberesp_ze = get_viberesp_prediction(
        driver, Vb, Fb, port_area, port_length, compare_freqs
    )

    # Interpolate Hornresp data to comparison frequencies
    hornresp_spl_interp = interpolate_hornresp(hornresp_freq, hornresp_spl, compare_freqs)
    hornresp_ze_interp = interpolate_hornresp(hornresp_freq, hornresp_ze, compare_freqs)

    # Calculate differences
    spl_diff = viberesp_spl - hornresp_spl_interp
    ze_diff = viberesp_ze - hornresp_ze_interp

    # Overall statistics
    spl_diff_mean = np.mean(spl_diff)
    spl_diff_std = np.std(spl_diff)
    spl_diff_max = np.max(np.abs(spl_diff))

    print("=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)
    print(f"SPL Difference Statistics:")
    print(f"  Mean difference:   {spl_diff_mean:+.2f} dB")
    print(f"  Std deviation:     {spl_diff_std:.2f} dB")
    print(f"  Max absolute:     {spl_diff_max:.2f} dB")
    print()

    # Check calibration status
    if abs(spl_diff_mean) < 1.0:
        print("  ✅ PASS: Mean offset < 1 dB (excellent calibration)")
    elif abs(spl_diff_mean) < 2.0:
        print("  ✅ PASS: Mean offset < 2 dB (good calibration)")
    elif abs(spl_diff_mean) < 5.0:
        print("  ⚠️  WARNING: Mean offset > 2 dB (calibration may need adjustment)")
    else:
        print("  ❌ FAIL: Mean offset > 5 dB (calibration issue)")
    print()

    if spl_diff_max < 2.0:
        print("  ✅ PASS: Max deviation < 2 dB")
    elif spl_diff_max < 5.0:
        print("  ⚠️  WARNING: Max deviation > 2 dB")
    else:
        print("  ❌ FAIL: Max deviation > 5 dB")
    print()

    # Frequency-by-frequency comparison table
    print("=" * 70)
    print("DETAILED COMPARISON (Selected Frequencies)")
    print("=" * 70)
    print(f"{'Freq (Hz)':>10} | {'Hornresp SPL':>13} | {'Viberesp SPL':>13} | {'Diff':>7} | {'Viberesp Ze':>12} | {'Hornresp Ze':>12}")
    print("-" * 70)

    # Show every 3rd frequency to keep table readable
    for i in range(0, len(compare_freqs), 3):
        print(f"{compare_freqs[i]:>10.1f} | {hornresp_spl_interp[i]:>13.1f} | {viberesp_spl[i]:>13.1f} | {spl_diff[i]:>+7.2f} | {viberesp_ze[i]:>12.1f} | {hornresp_ze_interp[i]:>12.1f}")

    print()
    print("=" * 70)
    print("KEY FREQUENCIES COMPARISON")
    print("=" * 70)

    key_freqs = [20, 30, 40, 50, 70, 100, 150, 200]
    for freq in key_freqs:
        # Find closest frequency in arrays
        idx = np.argmin(np.abs(compare_freqs - freq))
        f_actual = compare_freqs[idx]

        print(f"\n{f_actual:.1f} Hz:")
        print(f"  Hornresp: {hornresp_spl_interp[idx]:.1f} dB")
        print(f"  Viberesp: {viberesp_spl[idx]:.1f} dB")
        print(f"  Difference: {spl_diff[idx]:+.1f} dB")
        print(f"  Hornresp Ze: {hornresp_ze_interp[idx]:.1f} Ω")
        print(f"  Viberesp Ze: {viberesp_ze[idx]:.1f} Ω")

    print()
    print("=" * 70)
    print("VALIDATION CONCLUSION")
    print("=" * 70)

    # Determine overall validation status
    if abs(spl_diff_mean) < 2.0 and spl_diff_max < 5.0:
        status = "✅ PASS - Excellent agreement with Hornresp"
    elif abs(spl_diff_mean) < 5.0 and spl_diff_max < 10.0:
        status = "⚠️  ACCEPTABLE - Good agreement with some deviations"
    else:
        status = "❌ FAIL - Significant deviations from Hornresp"

    print(status)
    print()
    print(f"Calibration offset used: -25.25 dB")
    print(f"Actual mean offset observed: {spl_diff_mean:+.2f} dB")
    print(f"Max deviation observed: {spl_diff_max:.2f} dB")
    print()
    print("=" * 70)


if __name__ == "__main__":
    compare_results()
