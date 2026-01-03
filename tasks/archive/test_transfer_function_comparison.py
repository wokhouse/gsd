#!/usr/bin/env python3
"""
Compare optimizer output with and without transfer function SPL.

This verifies that the optimizer is actually using the calibrated
transfer function.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
from gsd.driver.bc_drivers import get_bc_8ndl51, get_bc_15ds115
from gsd.optimization.objectives.response_metrics import objective_response_flatness


def compare_transfer_function_usage():
    """Compare with and without transfer function for sealed box."""
    print("=" * 70)
    print("TRANSFER FUNCTION VERIFICATION TEST")
    print("=" * 70)

    driver = get_bc_8ndl51()
    Vb = 0.020  # 20L

    # Test WITH transfer function (default, should be calibrated)
    print("\nTesting with use_transfer_function_spl=True (calibrated)...")
    from gsd.enclosure.sealed_box import sealed_box_electrical_impedance

    test_freqs = [50, 100, 200]
    spl_with_tf = []
    for freq in test_freqs:
        result = sealed_box_electrical_impedance(
            freq, driver, Vb, voltage=2.83,
            use_transfer_function_spl=True
        )
        spl_with_tf.append(result['SPL'])
        print(f"  {freq} Hz: {result['SPL']:.1f} dB")

    # Test WITHOUT transfer function (old method, should be different)
    print("\nTesting with use_transfer_function_spl=False (uncalibrated)...")
    spl_without_tf = []
    for freq in test_freqs:
        result = sealed_box_electrical_impedance(
            freq, driver, Vb, voltage=2.83,
            use_transfer_function_spl=False
        )
        spl_without_tf.append(result['SPL'])
        print(f"  {freq} Hz: {result['SPL']:.1f} dB")

    # Compare
    print("\n" + "=" * 70)
    print("COMPARISON")
    print("=" * 70)
    print(f"{'Freq':>10} | {'With TF':>10} | {'Without TF':>12} | {'Delta':>10}")
    print("-" * 70)

    for i, freq in enumerate(test_freqs):
        delta = spl_without_tf[i] - spl_with_tf[i]
        print(f"{freq:>10} | {spl_with_tf[i]:>10.1f} | {spl_without_tf[i]:>12.1f} | {delta:>10.1f}")

    # Check if difference is ~25 dB (expected calibration offset)
    avg_delta = np.mean([spl_without_tf[i] - spl_with_tf[i] for i in range(len(test_freqs))])
    print(f"\nAverage difference: {avg_delta:.1f} dB")

    if 24 < avg_delta < 26:
        print("  PASS: Difference is ~25 dB (expected calibration offset)")
    elif abs(avg_delta) < 1:
        print("  WARNING: No difference - transfer function may not be working!")
    else:
        print(f"  INFO: Difference is {avg_delta:.1f} dB (expected ~25 dB)")

    print()


def compare_ported_box():
    """Compare with and without transfer function for ported box."""
    print("=" * 70)
    print("PORTED BOX TRANSFER FUNCTION VERIFICATION")
    print("=" * 70)

    driver = get_bc_15ds115()
    Vb, Fb = 0.100, 30.0

    from gsd.enclosure.ported_box import (
        ported_box_electrical_impedance,
        calculate_optimal_port_dimensions
    )

    port_area, port_length, _ = calculate_optimal_port_dimensions(driver, Vb, Fb)

    # Test WITH transfer function
    print("\nTesting with use_transfer_function_spl=True (calibrated)...")
    test_freqs = [50, 100, 200]
    spl_with_tf = []
    for freq in test_freqs:
        result = ported_box_electrical_impedance(
            freq, driver, Vb, Fb, port_area, port_length,
            voltage=2.83, impedance_model="small",
            use_transfer_function_spl=True
        )
        spl_with_tf.append(result['SPL'])
        print(f"  {freq} Hz: {result['SPL']:.1f} dB")

    # Test WITHOUT transfer function
    print("\nTesting with use_transfer_function_spl=False (uncalibrated)...")
    spl_without_tf = []
    for freq in test_freqs:
        result = ported_box_electrical_impedance(
            freq, driver, Vb, Fb, port_area, port_length,
            voltage=2.83, impedance_model="small",
            use_transfer_function_spl=False
        )
        spl_without_tf.append(result['SPL'])
        print(f"  {freq} Hz: {result['SPL']:.1f} dB")

    # Compare
    print("\n" + "=" * 70)
    print("COMPARISON")
    print("=" * 70)
    print(f"{'Freq':>10} | {'With TF':>10} | {'Without TF':>12} | {'Delta':>10}")
    print("-" * 70)

    for i, freq in enumerate(test_freqs):
        delta = spl_without_tf[i] - spl_with_tf[i]
        print(f"{freq:>10} | {spl_with_tf[i]:>10.1f} | {spl_without_tf[i]:>12.1f} | {delta:>10.1f}")

    avg_delta = np.mean([spl_without_tf[i] - spl_with_tf[i] for i in range(len(test_freqs))])
    print(f"\nAverage difference: {avg_delta:.1f} dB")

    if 24 < avg_delta < 26:
        print("  PASS: Difference is ~25 dB (expected calibration offset)")
    elif abs(avg_delta) < 1:
        print("  WARNING: No difference - transfer function may not be working!")
    else:
        print(f"  INFO: Difference is {avg_delta:.1f} dB (expected ~25 dB)")

    print()


if __name__ == "__main__":
    compare_transfer_function_usage()
    compare_ported_box()
