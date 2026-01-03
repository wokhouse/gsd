#!/usr/bin/env python3
"""
Quick test to verify the optimizer is using transfer function with default parameters.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
from gsd.driver.bc_drivers import get_bc_15ds115
from gsd.optimization.objectives.response_metrics import (
    objective_response_flatness,
    sealed_box_electrical_impedance,
    ported_box_electrical_impedance
)

def test_default_uses_tf():
    """Test that default parameters use transfer function."""
    print("=" * 70)
    print("TEST: Verify Optimizer Uses Calibrated Transfer Function")
    print("=" * 70)

    driver = get_bc_15ds115()

    # Test ported box
    Vb, Fb = 0.100, 30.0
    from gsd.enclosure.ported_box import calculate_optimal_port_dimensions
    port_area, port_length, _ = calculate_optimal_port_dimensions(driver, Vb, Fb)

    # Call the wrapper function with default parameters
    print("\nTesting wrapper function with DEFAULT parameters...")
    result_default = ported_box_electrical_impedance(
        100, driver, Vb, Fb, port_area, port_length, voltage=2.83
    )
    print(f"  100 Hz (default): {result_default['SPL']:.1f} dB")

    # Explicitly pass use_transfer_function_spl=True
    print("\nTesting with explicit use_transfer_function_spl=True...")
    result_tf_true = ported_box_electrical_impedance(
        100, driver, Vb, Fb, port_area, port_length, voltage=2.83,
        use_transfer_function_spl=True
    )
    print(f"  100 Hz (TF=True): {result_tf_true['SPL']:.1f} dB")

    # Explicitly pass use_transfer_function_spl=False
    print("\nTesting with explicit use_transfer_function_spl=False...")
    result_tf_false = ported_box_electrical_impedance(
        100, driver, Vb, Fb, port_area, port_length, voltage=2.83,
        use_transfer_function_spl=False
    )
    print(f"  100 Hz (TF=False): {result_tf_false['SPL']:.1f} dB")

    # Compare
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)

    if result_default['SPL'] == result_tf_true['SPL']:
        print("  PASS: Default uses transfer function (same as explicit True)")
    else:
        print("  FAIL: Default does NOT use transfer function!")
        print(f"        Default: {result_default['SPL']:.1f} dB")
        print(f"        TF=True: {result_tf_true['SPL']:.1f} dB")
        print(f"        TF=False: {result_tf_false['SPL']:.1f} dB")

    if result_default['SPL'] != result_tf_false['SPL']:
        print("  PASS: Transfer function differs from impedance coupling")
    else:
        print("  FAIL: Transfer function same as impedance coupling!")

    # Check frequency response shape
    print("\n" + "=" * 70)
    print("FREQUENCY RESPONSE TEST")
    print("=" * 70)

    test_freqs = [50, 100, 200]
    print(f"{'Freq':>10} | {'SPL (dB)':>10}")
    print("-" * 70)

    for freq in test_freqs:
        result = ported_box_electrical_impedance(
            freq, driver, Vb, Fb, port_area, port_length, voltage=2.83
        )
        print(f"{freq:>10} | {result['SPL']:>10.1f}")

    # Verify roll-off
    result_50 = ported_box_electrical_impedance(50, driver, Vb, Fb, port_area, port_length, voltage=2.83)
    result_200 = ported_box_electrical_impedance(200, driver, Vb, Fb, port_area, port_length, voltage=2.83)

    print("\n" + "=" * 70)
    if result_50['SPL'] > result_200['SPL']:
        print("  PASS: Response rolls off at high frequencies (correct)")
        print(f"        {result_50['SPL']:.1f} dB @ 50 Hz → {result_200['SPL']:.1f} dB @ 200 Hz")
    else:
        print("  FAIL: Response rises with frequency (incorrect)")
        print(f"        {result_50['SPL']:.1f} dB @ 50 Hz → {result_200['SPL']:.1f} dB @ 200 Hz")

    print()


if __name__ == "__main__":
    test_default_uses_tf()
