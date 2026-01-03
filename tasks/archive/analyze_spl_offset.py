#!/usr/bin/env python3
"""
Analyze the SPL offset between transfer function and impedance coupling methods.

This script helps identify the calibration offset needed by comparing the
transfer function approach (which has correct shape but wrong absolute level)
against the impedance coupling approach (which may have shape issues but
can be closer to correct level).
"""

import sys
sys.path.insert(0, 'src')

from gsd.driver.bc_drivers import get_bc_8ndl51, get_bc_15ds115
from gsd.enclosure.sealed_box import sealed_box_electrical_impedance
from gsd.enclosure.ported_box import (
    ported_box_electrical_impedance,
    calculate_optimal_port_dimensions
)


# Test frequencies (Hz)
TEST_FREQUENCIES = [20, 28, 40, 50, 70, 100, 150, 200, 300, 500]


def analyze_sealed_box():
    """Analyze sealed box SPL offset."""
    print("\n" + "=" * 80)
    print("SEALED BOX: BC_8NDL51 in 10L")
    print("=" * 80)

    driver = get_bc_8ndl51()
    Vb = 0.010  # 10L

    print("\nComparing transfer function vs impedance coupling:")
    print("\nFrequency (Hz) | Transfer Func | Impedance Coupling | Difference")
    print("---------------|---------------|---------------------|------------")

    diffs = []
    for freq in TEST_FREQUENCIES:
        # Transfer function method
        result_tf = sealed_box_electrical_impedance(
            freq, driver, Vb, use_transfer_function_spl=True
        )
        spl_tf = result_tf['SPL']

        # Impedance coupling method
        result_ic = sealed_box_electrical_impedance(
            freq, driver, Vb, use_transfer_function_spl=False
        )
        spl_ic = result_ic['SPL']

        diff = spl_tf - spl_ic
        diffs.append((freq, diff, spl_tf, spl_ic))
        print(f"{freq:14.0f} | {spl_tf:13.1f} | {spl_ic:19.1f} | {diff:+10.1f}")

    # Calculate statistics
    diff_values = [d[1] for d in diffs]
    avg_diff = sum(diff_values) / len(diff_values)

    print("\n" + "-" * 80)
    print("Offset Analysis:")
    print(f"  Average offset (transfer function - impedance coupling): {avg_diff:+.2f} dB")

    # Look at high-frequency range (200-500Hz) where response should be flat
    hf_diffs = [d[1] for d in diffs if d[0] >= 200]
    if hf_diffs:
        hf_avg = sum(hf_diffs) / len(hf_diffs)
        print(f"  High-freq offset (200-500Hz): {hf_avg:+.2f} dB")

    # The transfer function is the correct approach (Small 1972)
    # The impedance coupling may have shape issues
    # We need to calibrate the transfer function to match Hornresp
    # If Hornresp is closer to impedance coupling at low frequencies,
    # we might need a negative calibration offset

    return avg_diff


def analyze_ported_box():
    """Analyze ported box SPL offset."""
    print("\n" + "=" * 80)
    print("PORTED BOX: BC_15DS115 in 180L, Fb=33Hz (B4)")
    print("=" * 80)

    driver = get_bc_15ds115()
    Vb = 0.180  # 180L
    Fb = driver.F_s  # B4 alignment
    port_area, port_length, _ = calculate_optimal_port_dimensions(driver, Vb, Fb)

    print("\nComparing transfer function vs impedance coupling:")
    print("\nFrequency (Hz) | Transfer Func | Impedance Coupling | Difference")
    print("---------------|---------------|---------------------|------------")

    diffs = []
    for freq in TEST_FREQUENCIES:
        # Transfer function method
        result_tf = ported_box_electrical_impedance(
            freq, driver, Vb, Fb, port_area, port_length,
            use_transfer_function_spl=True
        )
        spl_tf = result_tf['SPL']

        # Impedance coupling method
        result_ic = ported_box_electrical_impedance(
            freq, driver, Vb, Fb, port_area, port_length,
            use_transfer_function_spl=False
        )
        spl_ic = result_ic['SPL']

        diff = spl_tf - spl_ic
        diffs.append((freq, diff, spl_tf, spl_ic))
        print(f"{freq:14.0f} | {spl_tf:13.1f} | {spl_ic:19.1f} | {diff:+10.1f}")

    # Calculate statistics
    diff_values = [d[1] for d in diffs]
    avg_diff = sum(diff_values) / len(diff_values)

    print("\n" + "-" * 80)
    print("Offset Analysis:")
    print(f"  Average offset (transfer function - impedance coupling): {avg_diff:+.2f} dB")

    # Look at high-frequency range (200-500Hz) where response should be rolling off
    hf_diffs = [d[1] for d in diffs if d[0] >= 200]
    if hf_diffs:
        hf_avg = sum(hf_diffs) / len(hf_diffs)
        print(f"  High-freq offset (200-500Hz): {hf_avg:+.2f} dB")

    return avg_diff


def main():
    print("=" * 80)
    print("SPL Offset Analysis: Transfer Function vs Impedance Coupling")
    print("=" * 80)
    print("\nThis analysis compares two SPL calculation methods:")
    print("  1. Transfer Function (Small 1972/1973) - CORRECT SHAPE")
    print("  2. Impedance Coupling - may have shape issues")
    print("\nThe transfer function has the correct frequency response shape,")
    print("but may need calibration for absolute SPL accuracy.")

    sealed_offset = analyze_sealed_box()
    ported_offset = analyze_ported_box()

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nAverage Transfer Function Offset (vs Impedance Coupling):")
    print(f"  Sealed box: {sealed_offset:+.2f} dB")
    print(f"  Ported box: {ported_offset:+.2f} dB")
    print(f"  Overall:    {(sealed_offset + ported_offset)/2:+.2f} dB")

    print("\n" + "-" * 80)
    print("RECOMMENDATION:")
    print("-" * 80)
    print("\nThe transfer function is the theoretically correct approach (Small 1972).")
    print("To calibrate against Hornresp:")
    print("\n1. Export designs to Hornresp (already done):")
    print("   - tasks/export_hornresp_test_cases.py")
    print("\n2. Run Hornresp simulations and export SPL data:")
    print("   - Import: tests/validation/drivers/bc_8ndl51/sealed/bc_8ndl51_sealed_10l.txt")
    print("   - Import: tests/validation/drivers/bc_15ds115/ported/bc_15ds115_ported_180l.txt")
    print("   - Export: File → Export → SPL Response → spl_hornresp.csv")
    print("\n3. Run validation script:")
    print("   PYTHONPATH=src python3 tasks/validate_transfer_function_calibration.py")
    print("\n4. Apply the recommended calibration offset to:")
    print("   - src/viberesp/enclosure/sealed_box.py (line ~270)")
    print("   - src/viberesp/enclosure/ported_box.py (line ~686)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
