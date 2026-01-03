#!/usr/bin/env python3
"""
Practical system optimization with realistic constraints.

Focuses on practical build parameters while still optimizing for
flattest crossover response.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.optimize import minimize

from gsd.driver.loader import load_driver
from gsd.crossover.lr4 import apply_lr4_crossover
from gsd.enclosure.ported_box import calculate_spl_ported_transfer_function


def calculate_hf_response_simple(hf_driver, flare_constant, frequencies, speed_of_sound=343.0):
    """Simplified HF response model focusing on cutoff frequency."""
    fc = (speed_of_sound * flare_constant) / (2 * np.pi)
    passband_sensitivity = 108.5  # DE250 datasheet

    hf_response = np.zeros_like(frequencies)
    for i, f in enumerate(frequencies):
        if f > 5000:
            hf_rolloff = 3 * np.log2(f / 5000)
            transition = 0.5 * (1 + np.tanh((f - 7000) / 1000))
            hf_response[i] = passband_sensitivity - hf_rolloff * transition
        elif f >= fc * 1.5:
            hf_response[i] = passband_sensitivity
        elif f >= fc / 2:
            blend = (f - fc/2) / (fc/2)
            blend_clamped = max(0.0, min(1.0, blend))
            blend_smooth = blend_clamped * blend_clamped * (3 - 2 * blend_clamped)
            octaves_below = np.log2(max(f, 10) / fc)
            below_cutoff = passband_sensitivity + octaves_below * 12
            hf_response[i] = below_cutoff * (1 - blend_smooth) + passband_sensitivity * blend_smooth
        else:
            octaves_below = np.log2(max(f, 10) / fc)
            hf_response[i] = passband_sensitivity + octaves_below * 12
    return hf_response


def objective_practical(params, lf_driver, hf_driver, freqs, xo_freq, z_offset, c, fs):
    """Objective with practical constraints."""
    Vb, Fb, flare_constant = params

    # Practical constraints
    penalty = 0.0

    # Box volume: 20L to 40L (practical range)
    if Vb < 0.020 or Vb > 0.040:
        penalty += 1000

    # Port tuning: 60Hz to 80Hz (common for 10" woofers)
    if Fb < 60 or Fb > 80:
        penalty += 1000

    # Horn cutoff: must be below crossover/2 for proper loading
    fc = (c * flare_constant) / (2 * np.pi)
    if fc > xo_freq * 0.5:
        penalty += 500
    if fc < 200:  # Don't go too low (impractical horns)
        penalty += 200

    # Flare constant: 3.0 to 6.0 (Fc = 163 to 326 Hz)
    if flare_constant < 3.0 or flare_constant > 6.0:
        penalty += 200

    if penalty > 0:
        return penalty

    # Calculate responses
    lf_spl = np.array([calculate_spl_ported_transfer_function(f, lf_driver, Vb, Fb) for f in freqs])
    hf_spl = calculate_hf_response_simple(hf_driver, flare_constant, freqs, c)

    # Level match
    lf_pb = np.mean(lf_spl[(freqs >= 200) & (freqs <= 500)])
    hf_pb = np.mean(hf_spl[(freqs >= 1000) & (freqs <= 5000)])
    hf_padded = hf_spl + (lf_pb - hf_pb)

    # Apply crossover
    combined, _, _ = apply_lr4_crossover(freqs, lf_spl, hf_padded, xo_freq, z_offset_m=z_offset, speed_of_sound=c, sample_rate=fs)

    # Calculate flatness with emphasis on crossover region
    mask_full = (freqs >= 100) & (freqs <= 10000)
    mask_xo = (freqs >= xo_freq/2) & (freqs <= xo_freq*2)

    flatness_full = np.std(combined[mask_full])
    flatness_xo = np.std(combined[mask_xo])

    # Weighted metric: 70% full range, 30% crossover region
    metric = 0.7 * flatness_full + 0.3 * flatness_xo

    return metric


def main():
    """Run practical optimization."""

    print("=" * 70)
    print("PRACTICAL SYSTEM OPTIMIZATION")
    print("=" * 70)
    print()

    lf_driver = load_driver("BC_10NW64")
    hf_driver = load_driver("BC_DE250")

    xo_freq = 800.0
    z_offset = 0.0
    freqs = np.logspace(np.log10(20), np.log10(20000), 1000)

    # Current design
    Vb_current = 26.5e-3
    Fb_current = 70.0
    flare_current = 4.6

    print("Current design:")
    print(f"  Vb: {Vb_current*1000:.1f} L")
    print(f"  Fb: {Fb_current:.1f} Hz")
    print(f"  Flare constant: {flare_current:.2f} /m → Fc = {343*flare_current/(2*np.pi):.0f} Hz")
    print()

    # Calculate current performance
    lf_current = np.array([calculate_spl_ported_transfer_function(f, lf_driver, Vb_current, Fb_current) for f in freqs])
    hf_current = calculate_hf_response_simple(hf_driver, flare_current, freqs)
    lf_pb = np.mean(lf_current[(freqs >= 200) & (freqs <= 500)])
    hf_pb = np.mean(hf_current[(freqs >= 1000) & (freqs <= 5000)])
    hf_padded_current = hf_current + (lf_pb - hf_pb)
    combined_current, _, _ = apply_lr4_crossover(freqs, lf_current, hf_padded_current, xo_freq, z_offset_m=z_offset, speed_of_sound=343.0, sample_rate=48000.0)
    flatness_current = np.std(combined_current[(freqs >= 100) & (freqs <= 10000)])

    print(f"Current flatness: σ = {flatness_current:.3f} dB")
    print()

    # Initial guess
    x0 = np.array([Vb_current, Fb_current, flare_current])

    # Practical bounds
    bounds = [
        (0.020, 0.040),  # Vb: 20L to 40L
        (60.0, 80.0),    # Fb: 60Hz to 80Hz
        (3.0, 6.0)       # Flare: 3.0 to 6.0 /m
    ]

    print("Optimizing with practical constraints...")
    print("  Vb: 20L - 40L")
    print("  Fb: 60Hz - 80Hz")
    print("  Flare: 3.0 - 6.0 /m (Fc: 163 - 326 Hz)")
    print()

    result = minimize(
        objective_practical,
        x0,
        args=(lf_driver, hf_driver, freqs, xo_freq, z_offset, 343.0, 48000.0),
        method='Nelder-Mead',
        bounds=bounds,
        options={'maxiter': 500, 'xatol': 1e-4, 'fatol': 1e-4, 'disp': True}
    )

    print()
    print("Optimization complete!")
    print(f"Success: {result.success}")
    print(f"Iterations: {result.nit}")
    print()

    Vb_opt, Fb_opt, flare_opt = result.x
    fc_opt = 343.0 * flare_opt / (2 * np.pi)

    # Calculate optimized performance
    lf_opt = np.array([calculate_spl_ported_transfer_function(f, lf_driver, Vb_opt, Fb_opt) for f in freqs])
    hf_opt = calculate_hf_response_simple(hf_driver, flare_opt, freqs)
    lf_pb_opt = np.mean(lf_opt[(freqs >= 200) & (freqs <= 500)])
    hf_pb_opt = np.mean(hf_opt[(freqs >= 1000) & (freqs <= 5000)])
    hf_padded_opt = hf_opt + (lf_pb_opt - hf_pb_opt)
    combined_opt, _, _ = apply_lr4_crossover(freqs, lf_opt, hf_padded_opt, xo_freq, z_offset_m=z_offset, speed_of_sound=343.0, sample_rate=48000.0)
    flatness_opt = np.std(combined_opt[(freqs >= 100) & (freqs <= 10000)])

    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()
    print("Optimized parameters:")
    print(f"  Vb: {Vb_opt*1000:.1f} L (was {Vb_current*1000:.1f} L)")
    print(f"  Fb: {Fb_opt:.1f} Hz (was {Fb_current:.1f} Hz)")
    print(f"  Flare constant: {flare_opt:.2f} /m (was {flare_current:.2f} /m)")
    print(f"  Horn Fc: {fc_opt:.0f} Hz (was {343*flare_current/(2*np.pi):.0f} Hz)")
    print()
    print(f"Flatness improvement:")
    print(f"  Current: σ = {flatness_current:.3f} dB")
    print(f"  Optimized: σ = {flatness_opt:.3f} dB")
    print(f"  Improvement: {(flatness_current - flatness_opt):.3f} dB")
    print()

    # Plot comparison
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))

    # Plot 1: Full range comparison
    ax1 = axes[0]
    ax1.semilogx(freqs, lf_current, 'b--', label='LF (current)', alpha=0.4, linewidth=1.5)
    ax1.semilogx(freqs, hf_padded_current, 'r--', label='HF (current)', alpha=0.4, linewidth=1.5)
    ax1.semilogx(freqs, combined_current, 'k-', label='Combined (current)', linewidth=2)

    ax1.semilogx(freqs, lf_opt, 'b:', label='LF (optimized)', alpha=0.6, linewidth=2)
    ax1.semilogx(freqs, hf_padded_opt, 'r:', label='HF (optimized)', alpha=0.6, linewidth=2)
    ax1.semilogx(freqs, combined_opt, 'g-', linewidth=2.5, label='Combined (optimized)')

    ax1.axvline(xo_freq, color='purple', linestyle=':', alpha=0.7, linewidth=1.5)
    ax1.set_xlabel('Frequency (Hz)', fontsize=11)
    ax1.set_ylabel('SPL (dB)', fontsize=11)
    ax1.set_title(f'Practical Optimization: {xo_freq:.0f} Hz Crossover\n'
                  f'Improvement: {(flatness_current - flatness_opt):.3f} dB | '
                  f'Vb: {Vb_current*1000:.0f}→{Vb_opt*1000:.0f}L, Fb: {Fb_current:.0f}→{Fb_opt:.0f}Hz',
                  fontsize=12, fontweight='bold')
    ax1.legend(loc='lower left', fontsize=9, framealpha=0.9)
    ax1.grid(True, which='both', alpha=0.3)
    ax1.set_xlim([20, 20000])
    ax1.set_ylim([70, 100])

    # Plot 2: Difference
    ax2 = axes[1]
    diff = combined_opt - combined_current
    ax2.semilogx(freqs, diff, 'purple', linewidth=2)
    ax2.axhline(0, color='gray', linestyle='-', alpha=0.5)
    ax2.axvline(xo_freq, color='purple', linestyle=':', alpha=0.7, linewidth=1.5)
    ax2.fill_between(freqs, 0, diff, where=(diff > 0), alpha=0.3, color='green', label='Improvement')
    ax2.fill_between(freqs, 0, diff, where=(diff < 0), alpha=0.3, color='red', label='Degradation')
    ax2.set_xlabel('Frequency (Hz)', fontsize=11)
    ax2.set_ylabel('Difference (dB)', fontsize=11)
    ax2.set_title('Optimized - Current Response', fontsize=12)
    ax2.legend(loc='best', fontsize=10)
    ax2.grid(True, which='both', alpha=0.3)
    ax2.set_xlim([20, 20000])
    ax2.set_ylim([-3, 3])

    plt.tight_layout()

    output_path = Path(__file__).parent / "practical_optimization_results.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Plot saved to: {output_path}")

    print()
    print("=" * 70)
    print("PRACTICAL RECOMMENDATIONS")
    print("=" * 70)
    print()
    print("For improved flatness with practical build constraints:")
    print(f"  • Increase box volume to: {Vb_opt*1000:.1f} L")
    print(f"  • Adjust port tuning to: {Fb_opt:.1f} Hz")
    print(f"  • Adjust horn flare to: {flare_opt:.2f} /m (Fc = {fc_opt:.0f} Hz)")
    print()
    print("These adjustments improve flatness while remaining practical to build.")
    print()


if __name__ == "__main__":
    main()
