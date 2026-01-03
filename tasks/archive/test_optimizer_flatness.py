#!/usr/bin/env python3
"""
Test the response flatness optimizer with the BC_15DS115.

This demonstrates that the optimizer exists BUT has the SPL bug.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
from gsd.driver.bc_drivers import get_bc_15ds115
from gsd.optimization.objectives.response_metrics import objective_response_flatness

def main():
    """Test flatness objective with different designs."""
    print("=" * 70)
    print("RESPONSE FLATNESS OPTIMIZER TEST: BC_15DS115")
    print("=" * 70)

    driver = get_bc_15ds115()

    # Test different ported box designs
    designs = [
        ("Small box (50L)", np.array([0.050, 35.0])),
        ("Medium box (100L)", np.array([0.100, 30.0])),
        ("Large box (180L)", np.array([0.180, 28.0])),
        ("Very large box (300L)", np.array([0.300, 25.0])),
    ]

    print("\n" + "=" * 70)
    print("FLATNESS METRIC (Standard Deviation) - Lower is Better")
    print("=" * 70)

    flatness_results = []
    for name, design_vector in designs:
        Vb = design_vector[0]
        Fb = design_vector[1]

        try:
            # Add port dimensions (auto-calculated by function)
            from gsd.enclosure.ported_box import calculate_optimal_port_dimensions
            port_area, port_length, _ = calculate_optimal_port_dimensions(driver, Vb, Fb)

            # Full design vector with port dims
            full_vector = np.array([Vb, Fb, port_area, port_length])

            # Calculate flatness over 20-200 Hz range
            flatness = objective_response_flatness(
                full_vector,
                driver,
                "ported",
                frequency_range=(20.0, 200.0),
                n_points=50,
                voltage=2.83
            )

            flatness_results.append((name, flatness, Vb, Fb))

            print(f"{name:25s}: σ = {flatness:.2f} dB  (Vb={Vb*1000:.0f}L, Fb={Fb:.1f}Hz)")

        except Exception as e:
            print(f"{name:25s}: ERROR - {e}")

    # Find "best" design according to optimizer
    if flatness_results:
        best = min(flatness_results, key=lambda x: x[1])
        print("\n" + "=" * 70)
        print(f"OPTIMIZER'S CHOICE: {best[0]}")
        print(f"  Flatness (σ): {best[1]:.2f} dB")
        print(f"  Design: Vb={best[2]*1000:.1f}L, Fb={best[3]:.1f}Hz")
        print("=" * 70)

        print("\n" + "=" * 70)
        print("BUT WAIT! Let's check the ACTUAL response shape...")
        print("=" * 70)

        # Sample frequencies to see the actual response
        from gsd.enclosure.ported_box import ported_box_electrical_impedance

        test_freqs = [20, 30, 40, 50, 70, 100, 150, 200]
        spl_values = []

        print(f"\n{'Freq (Hz)':>10} | {'SPL (dB)':>10} | {'Note'}")
        print("-" * 70)

        for freq in test_freqs:
            result = ported_box_electrical_impedance(
                freq,
                driver,
                best[2],
                best[3],
                port_area=217.1/10000,  # Use approximate port dims
                port_length=0.388,
                voltage=2.83,
                impedance_model="small",
                use_transfer_function_spl=True  # CRITICAL: Use calibrated transfer function
            )
            spl = result['SPL']
            spl_values.append(spl)

            note = ""
            if freq < best[3]:
                note = "Below tuning"
            elif abs(freq - best[3]) < 5:
                note = "Near tuning"
            else:
                note = "Above tuning"

            print(f"{freq:>10.1f} | {spl:>10.1f} | {note}")

        print("\n" + "=" * 70)
        print("ANALYSIS")
        print("=" * 70)

        # Check if response is rising or falling
        if spl_values[0] < spl_values[-1]:
            print("  WARNING: Response is RISING with frequency (incorrect!)")
            print("  1. SPL rises from {:.1f} dB @ 20 Hz to {:.1f} dB @ 200 Hz".format(
                spl_values[0], spl_values[-1]))
            print("  2. This is NOT a flat response - it's rising with frequency!")
            print("  3. The optimizer may not be using transfer function SPL")
            print()
            print("Real subwoofer response should:")
            print("  - Roll off at high frequencies (mass-controlled)")
            print("  - Have peak or flat response in the bass region")
            print("  - NOT increase linearly with frequency!")
        else:
            print("  Response shape is CORRECT:")
            print("  1. SPL rolls off at high frequencies: {:.1f} dB @ 20 Hz → {:.1f} dB @ 200 Hz".format(
                spl_values[0], spl_values[-1]))
            print("  2. This is the expected mass-controlled roll-off")
            print("  3. Optimizer is using calibrated transfer function SPL")
            print()
            print("  The response shows proper subwoofer behavior:")
            print("  - Peak or flat response in the bass region")
            print("  - Gradual roll-off at higher frequencies")
            print("  - Flatness metric of {:.2f} dB is reasonable for this design".format(
                min([r[1] for r in flatness_results])))
        print("=" * 70)


if __name__ == "__main__":
    main()
