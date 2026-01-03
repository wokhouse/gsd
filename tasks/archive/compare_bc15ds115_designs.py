#!/usr/bin/env python3
"""
Compare multiple ported box designs for BC_15DS115.

Shows how box volume affects frequency response and flatness.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
from gsd.driver.bc_drivers import get_bc_15ds115
from gsd.optimization.objectives.response_metrics import objective_response_flatness
from gsd.enclosure.ported_box import (
    calculate_optimal_port_dimensions,
    ported_box_electrical_impedance,
    calculate_ported_box_system_parameters
)


def evaluate_design(driver, Vb, Fb, name):
    """Evaluate a single design and return metrics."""
    port_area, port_length, _ = calculate_optimal_port_dimensions(driver, Vb, Fb)
    design_vector = np.array([Vb, Fb, port_area, port_length])

    # Calculate flatness
    flatness_full = objective_response_flatness(
        design_vector, driver, "ported",
        frequency_range=(20.0, 200.0),
        n_points=100,
        voltage=2.83
    )

    flatness_bass = objective_response_flatness(
        design_vector, driver, "ported",
        frequency_range=(20.0, 80.0),
        n_points=50,
        voltage=2.83
    )

    # Sample frequency response
    test_freqs = [20, 30, 40, 50, 70, 100, 150, 200]
    spl_response = {}
    for freq in test_freqs:
        result = ported_box_electrical_impedance(
            freq, driver, Vb, Fb, port_area, port_length,
            voltage=2.83, impedance_model="small",
            use_transfer_function_spl=True
        )
        spl_response[freq] = result['SPL']

    # Calculate system parameters
    sys_params = calculate_ported_box_system_parameters(driver, Vb, Fb)

    return {
        'name': name,
        'Vb': Vb,
        'Fb': Fb,
        'port_area': port_area,
        'port_length': port_length,
        'flatness_full': flatness_full,
        'flatness_bass': flatness_bass,
        'spl': spl_response,
        'F3': sys_params.F3,
        'alpha': sys_params.alpha,
        'h': sys_params.h
    }


def main():
    """Compare multiple designs."""
    driver = get_bc_15ds115()

    print("=" * 70)
    print("PORTED BOX DESIGN COMPARISON: BC_15DS115")
    print("=" * 70)
    print(f"Driver: Vas={driver.V_as*1000:.0f}L, Fs={driver.F_s:.1f}Hz, Qts={driver.Q_ts:.2f}")
    print()

    # Define designs to compare
    designs = [
        ("Very Small (50L, 35Hz)", 0.050, 35.0),
        ("Small (80L, 33Hz)", 0.080, 33.0),
        ("Medium (120L, 31Hz)", 0.120, 31.0),
        ("Large (180L, 28Hz)", 0.180, 28.0),
        ("B4 Alignment (254L, 33Hz)", driver.V_as, driver.F_s),
        ("Very Large (300L, 27Hz)", 0.300, 27.0),
    ]

    results = []
    for name, Vb, Fb in designs:
        result = evaluate_design(driver, Vb, Fb, name)
        results.append(result)

    # Sort by flatness
    results_sorted = sorted(results, key=lambda x: x['flatness_full'])

    # Print comparison table
    print("=" * 70)
    print("FLATNESS COMPARISON (20-200 Hz)")
    print("=" * 70)
    print(f"{'Design':<30} | {'Vb':>6} | {'Fb':>6} | {'σ Full':>8} | {'σ Bass':>8} | {'F3':>6}")
    print("-" * 70)

    for r in results_sorted:
        print(f"{r['name']:<30} | {r['Vb']*1000:>6.0f} | {r['Fb']:>6.1f} | {r['flatness_full']:>8.2f} | {r['flatness_bass']:>8.2f} | {r['F3']:>6.1f}")

    print()
    print("=" * 70)
    print("FREQUENCY RESPONSE COMPARISON")
    print("=" * 70)
    print(f"{'Freq (Hz)':>10} | ", end="")
    for r in results_sorted[:4]:  # Show top 4 designs
        print(f"{r['name'][:20]:>20} | ", end="")
    print()
    print("-" * 70)

    test_freqs = [20, 30, 40, 50, 70, 100, 150, 200]
    for freq in test_freqs:
        print(f"{freq:>10.1f} | ", end="")
        for r in results_sorted[:4]:
            spl = r['spl'][freq]
            print(f"{spl:>20.1f} | ", end="")
        print()

    print()
    print("=" * 70)
    print("ANALYSIS")
    print("=" * 70)

    best = results_sorted[0]
    print(f"\nFlattest Response (20-200Hz): {best['name']}")
    print(f"  Flatness: σ = {best['flatness_full']:.2f} dB")
    print(f"  Design: Vb={best['Vb']*1000:.0f}L, Fb={best['Fb']:.1f}Hz")
    print(f"  Alpha: {best['alpha']:.2f} (compliance ratio)")
    print(f"  F3: {best['F3']:.1f} Hz")

    # Compare with B4 alignment
    b4 = next(r for r in results if "B4" in r['name'])
    print(f"\nB4 Alignment Comparison:")
    print(f"  B4 flatness: σ = {b4['flatness_full']:.2f} dB")
    print(f"  Difference: Δσ = {best['flatness_full'] - b4['flatness_full']:+.2f} dB")

    # Trade-off analysis
    print(f"\nTrade-offs:")
    print(f"  Smaller boxes:")
    print(f"    - Better midbass flatness (less bass boost)")
    print(f"    - Higher F3 (less bass extension)")
    print(f"    - Higher tuning needed")
    print(f"  Larger boxes:")
    print(f"    - Deeper bass extension (lower F3)")
    print(f"    - More bass boost near tuning")
    print(f"    - Potentially less flat overall response")

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
