#!/usr/bin/env python3
"""
Validate transfer function SPL against Hornresp reference data.

This script compares viberesp SPL calculations using the transfer function
approach against Hornresp reference simulations to determine the calibration
offset needed for absolute accuracy.

Usage:
    PYTHONPATH=src python3 tasks/validate_transfer_function_calibration.py

Uses existing Hornresp simulation data from:
    tests/validation/drivers/bc_8ndl51/sealed_box/sim.txt (Vb=20L)
    tests/validation/drivers/bc_15ps100/sealed_box/sim.txt (Vb=50L)
"""

import sys
import os
import csv
from pathlib import Path
sys.path.insert(0, 'src')

from gsd.driver.bc_drivers import get_bc_8ndl51, get_bc_15ps100
from gsd.enclosure.sealed_box import sealed_box_electrical_impedance


# Test frequencies (Hz) - covering bass to midrange
TEST_FREQUENCIES = [20, 28, 40, 50, 70, 100, 150, 200, 300, 500]


def load_hornresp_spl(sim_txt_path, vb_liters):
    """
    Load Hornresp SPL data from sim.txt file.

    Args:
        sim_txt_path: Path to Hornresp sim.txt file
        vb_liters: Expected box volume in liters (for verification)

    Returns:
        Dictionary mapping frequency to SPL (dB)
    """
    if not os.path.exists(sim_txt_path):
        print(f"    ⚠ Hornresp data not found: {sim_txt_path}")
        return None

    try:
        frequencies = []
        spl_values = []

        with open(sim_txt_path, 'r') as f:
            # Read header
            header = f.readline().strip()
            # Expected format: Freq (hertz)  Ra (norm)  Xa (norm)  Za (norm)  SPL (dB)  ...
            columns = header.split('\t')

            # Find column indices
            freq_col = 0  # First column
            spl_col = 4   # SPL is 5th column (index 4)

            print(f"    Loading {sim_txt_path}...")
            print(f"    Box volume: {vb_liters}L")
            print(f"    Input voltage: 2.83V")

            # Read data lines
            for line in f:
                if line.strip():
                    parts = line.strip().split('\t')
                    if len(parts) > spl_col:
                        try:
                            freq = float(parts[freq_col])
                            spl = float(parts[spl_col])
                            frequencies.append(freq)
                            spl_values.append(spl)
                        except (ValueError, IndexError):
                            continue

        print(f"    ✓ Loaded {len(frequencies)} data points")
        print(f"    Frequency range: {min(frequencies):.1f} - {max(frequencies):.1f} Hz")

        return dict(zip(frequencies, spl_values))

    except Exception as e:
        print(f"    ✗ Error loading {sim_txt_path}: {e}")
        return None


def find_closest_frequency(target_freq, freq_dict):
    """Find the closest frequency in the Hornresp data."""
    if not freq_dict:
        return None

    closest_freq = min(freq_dict.keys(), key=lambda f: abs(f - target_freq))
    if abs(closest_freq - target_freq) < 5:  # Within 5 Hz
        return closest_freq, freq_dict[closest_freq]
    return None, None


def compare_sealed_box():
    """Compare sealed box SPL with Hornresp."""
    print("\n" + "=" * 70)
    print("SEALED BOX: BC_8NDL51 in 20L")
    print("=" * 70)

    driver = get_bc_8ndl51()
    Vb = 0.020  # 20L (matches existing Hornresp sim)

    # Load Hornresp data
    hornresp_path = "tests/validation/drivers/bc_8ndl51/sealed_box/sim.txt"
    hornresp_data = load_hornresp_spl(hornresp_path, Vb * 1000)

    if hornresp_data is None:
        print("\n⚠ No Hornresp data available - showing viberesp results only")
        print("\nFrequency (Hz) | Viberesp SPL (dB)")
        print("---------------|--------------------")

        for freq in TEST_FREQUENCIES:
            result = sealed_box_electrical_impedance(
                freq, driver, Vb, use_transfer_function_spl=True
            )
            viberesp_spl = result['SPL']
            print(f"{freq:14.0f} | {viberesp_spl:18.1f}")

        return None

    # We have Hornresp data - perform comparison
    print("\nFrequency (Hz) | Viberesp (dB) | Hornresp (dB) | Difference")
    print("---------------|---------------|---------------|------------")

    diffs = []
    for target_freq in TEST_FREQUENCIES:
        closest_freq, hornresp_spl = find_closest_frequency(target_freq, hornresp_data)

        if closest_freq is not None:
            result = sealed_box_electrical_impedance(
                closest_freq, driver, Vb, use_transfer_function_spl=True
            )
            viberesp_spl = result['SPL']
            diff = viberesp_spl - hornresp_spl
            diffs.append((closest_freq, diff, viberesp_spl, hornresp_spl))
            marker = f" ({target_freq}Hz)" if abs(closest_freq - target_freq) > 0.1 else ""
            print(f"{closest_freq:14.0f}{marker:13} | {viberesp_spl:13.1f} | {hornresp_spl:13.1f} | {diff:+10.1f}")

    # Calculate statistics
    diff_values = [d[1] for d in diffs]
    avg_offset = sum(diff_values) / len(diff_values)
    max_pos_diff = max(diff_values)
    max_neg_diff = min(diff_values)
    max_abs_diff = max(abs(d) for d in diff_values)

    print("\n" + "-" * 70)
    print("Statistics:")
    print(f"  Average offset:    {avg_offset:+.2f} dB")
    print(f"  Max positive diff: {max_pos_diff:+.2f} dB")
    print(f"  Max negative diff: {max_neg_diff:+.2f} dB")
    print(f"  Max absolute diff: {max_abs_diff:.2f} dB")
    if len(diff_values) > 1:
        std_dev = (sum((d - avg_offset)**2 for d in diff_values) / len(diff_values))**0.5
        print(f"  Std deviation:     {std_dev:.2f} dB")

    return avg_offset, diffs


def compare_bc_15ps100():
    """Compare BC_15PS100 sealed box with Hornresp."""
    print("\n" + "=" * 70)
    print("SEALED BOX: BC_15PS100 in 50L")
    print("=" * 70)

    driver = get_bc_15ps100()
    Vb = 0.050  # 50L (matches existing Hornresp sim)

    # Load Hornresp data
    hornresp_path = "tests/validation/drivers/bc_15ps100/sealed_box/sim.txt"
    hornresp_data = load_hornresp_spl(hornresp_path, Vb * 1000)

    if hornresp_data is None:
        print("\n⚠ No Hornresp data available - showing viberesp results only")
        print("\nFrequency (Hz) | Viberesp SPL (dB)")
        print("---------------|--------------------")

        for freq in TEST_FREQUENCIES:
            result = sealed_box_electrical_impedance(
                freq, driver, Vb, use_transfer_function_spl=True
            )
            viberesp_spl = result['SPL']
            print(f"{freq:14.0f} | {viberesp_spl:18.1f}")

        return None

    # We have Hornresp data - perform comparison
    print("\nFrequency (Hz) | Viberesp (dB) | Hornresp (dB) | Difference")
    print("---------------|---------------|---------------|------------")

    diffs = []
    for target_freq in TEST_FREQUENCIES:
        closest_freq, hornresp_spl = find_closest_frequency(target_freq, hornresp_data)

        if closest_freq is not None:
            result = sealed_box_electrical_impedance(
                closest_freq, driver, Vb, use_transfer_function_spl=True
            )
            viberesp_spl = result['SPL']
            diff = viberesp_spl - hornresp_spl
            diffs.append((closest_freq, diff, viberesp_spl, hornresp_spl))
            marker = f" ({target_freq}Hz)" if abs(closest_freq - target_freq) > 0.1 else ""
            print(f"{closest_freq:14.0f}{marker:13} | {viberesp_spl:13.1f} | {hornresp_spl:13.1f} | {diff:+10.1f}")

    # Calculate statistics
    diff_values = [d[1] for d in diffs]
    avg_offset = sum(diff_values) / len(diff_values)
    max_pos_diff = max(diff_values)
    max_neg_diff = min(diff_values)
    max_abs_diff = max(abs(d) for d in diff_values)

    print("\n" + "-" * 70)
    print("Statistics:")
    print(f"  Average offset:    {avg_offset:+.2f} dB")
    print(f"  Max positive diff: {max_pos_diff:+.2f} dB")
    print(f"  Max negative diff: {max_neg_diff:+.2f} dB")
    print(f"  Max absolute diff: {max_abs_diff:.2f} dB")
    if len(diff_values) > 1:
        std_dev = (sum((d - avg_offset)**2 for d in diff_values) / len(diff_values))**0.5
        print(f"  Std deviation:     {std_dev:.2f} dB")

    return avg_offset, diffs


def main():
    print("=" * 70)
    print("SPL Transfer Function Calibration Validation")
    print("=" * 70)
    print("\nThis script compares viberesp transfer function SPL against Hornresp")
    print("to determine the calibration offset needed for absolute accuracy.")
    print("\nUsing existing Hornresp simulation data:")
    print("  - BC_8NDL51: tests/validation/drivers/bc_8ndl51/sealed_box/sim.txt (Vb=20L)")
    print("  - BC_15PS100: tests/validation/drivers/bc_15ps100/sealed_box/sim.txt (Vb=50L)")

    # Run comparisons
    offset_8ndl51, diffs_8ndl51 = compare_sealed_box()
    offset_15ps100, diffs_15ps100 = compare_bc_15ps100()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if offset_8ndl51 is not None and offset_15ps100 is not None:
        print(f"\nCalibration Offset Required:")
        print(f"  BC_8NDL51 (20L): {offset_8ndl51:+.2f} dB")
        print(f"  BC_15PS100 (50L): {offset_15ps100:+.2f} dB")
        print(f"  Overall:          {(offset_8ndl51 + offset_15ps100)/2:+.2f} dB")

        print(f"\nRecommended Calibration Constant:")
        calibration_offset = (offset_8ndl51 + offset_15ps100) / 2
        print(f"  CALIBRATION_OFFSET_DB = {calibration_offset:+.2f}")

        # Check if calibration meets criteria
        print(f"\nValidation Criteria:")
        avg_offset = abs(calibration_offset)
        print(f"  ✓ Average offset < 0.5 dB: {'PASS' if avg_offset < 0.5 else 'FAIL'} ({avg_offset:.2f} dB)")

        max_deviation = max(
            max(abs(d[1]) for d in diffs_8ndl51),
            max(abs(d[1]) for d in diffs_15ps100)
        )
        print(f"  ✓ Max deviation < 2 dB: {'PASS' if max_deviation < 2.0 else 'FAIL'} ({max_deviation:.2f} dB)")

        if avg_offset < 0.5 and max_deviation < 2.0:
            print(f"\n✓ Calibration is VALID - ready to apply!")
            print(f"\nTo apply calibration:")
            print(f"  1. Edit tasks/apply_spl_calibration.py")
            print(f"  2. Update CALIBRATION_OFFSET_DB = {calibration_offset:+.2f}")
            print(f"  3. Run: PYTHONPATH=src python3 tasks/apply_spl_calibration.py")
            return 0
        else:
            print(f"\n✗ Calibration needs investigation")
            return 1

    else:
        print("\n⚠ Some Hornresp data missing")
        return 2


if __name__ == "__main__":
    sys.exit(main())
