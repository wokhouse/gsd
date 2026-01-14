#!/usr/bin/env python3
"""
Redo crossover optimization for DH450 + 12FW88 to fix dip in crossover region.

The issue: Horn cutoff (1865 Hz) > crossover (800 Hz), causing HF rolloff in XO region.

Solution: Find optimal crossover frequency that minimizes dip given horn characteristics.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
from pathlib import Path
import json

from gsd.driver import load_driver
from gsd.enclosure.ported_box import calculate_spl_ported_transfer_function
from gsd.optimization.api.two_way_system import (
    calculate_hf_horn_response,
    calculate_lr4_crossover_gains,
    optimize_hf_padding_for_flatness,
)
from gsd.optimization.api.crossover_assistant import CrossoverDesignAssistant

# Configure plot
rcParams['font.size'] = 11
rcParams['axes.labelsize'] = 12
rcParams['axes.titlesize'] = 14
rcParams['legend.fontsize'] = 10
rcParams['grid.alpha'] = 0.3


def calculate_system_response(freq, lf_response, hf_response, xo_freq, hf_pad):
    """Calculate combined system response for a given crossover frequency."""
    # Get crossover gains
    lp_gain_db, hp_gain_db = calculate_lr4_crossover_gains(freq, xo_freq)

    # Apply padding
    hf_padded = hf_response + hf_pad

    # Apply crossover
    lf_combined = lf_response + lp_gain_db
    hf_combined = hf_padded + hp_gain_db

    # Power sum
    system_response = 10 * np.log10(
        10**(lf_combined/10) + 10**(hf_combined/10)
    )

    return system_response


def calculate_dip_metric(freq, system_response, xo_freq, xo_bandwidth=0.5):
    """
    Calculate dip metric around crossover frequency.

    Returns the minimum SPL in the crossover region and its depth.
    """
    # Define crossover region (octave around XO)
    xo_region = (freq >= xo_freq / xo_bandwidth) & (freq <= xo_freq * xo_bandwidth)

    if not np.any(xo_region):
        return 0.0, 0.0

    # Find minimum in crossover region
    xo_spl = system_response[xo_region]
    min_spl = np.min(xo_spl)

    # Find reference level (away from crossover)
    ref_mask = (freq >= xo_freq * 2) & (freq <= xo_freq * 4)
    if np.any(ref_mask):
        ref_spl = np.mean(system_response[ref_mask])
    else:
        ref_spl = np.max(system_response)

    dip_depth = ref_spl - min_spl

    return min_spl, dip_depth


def sweep_crossover_frequencies(freq, lf_response, hf_response, crossover_range):
    """
    Sweep crossover frequencies and evaluate system flatness.

    Returns results sorted by flatness (best first).
    """
    print("\nSweeping crossover frequencies...")

    results = []
    xo_frequencies = np.linspace(crossover_range[0], crossover_range[1], 50)

    for xo_freq in xo_frequencies:
        # Optimize HF padding for this crossover
        try:
            hf_pad = optimize_hf_padding_for_flatness(
                lf_driver_name="BC_12FW88",
                hf_driver_name="BC_DH450",
                lf_enclosure_type="ported",
                lf_enclosure_params={"Vb": 0.1145, "Fb": 46.5},
                horn_params={"cutoff": 1865, "length": 0.25},
                crossover_frequency=xo_freq,
                padding_range=(-25, -5),
                num_steps=21,
            )
        except Exception as e:
            print(f"  Warning: Could not optimize padding for {xo_freq:.0f} Hz: {e}")
            hf_pad = -15.0  # Fallback

        # Calculate system response
        system_response = calculate_system_response(freq, lf_response, hf_response, xo_freq, hf_pad)

        # Calculate metrics
        # Passband flatness (100-10000 Hz)
        passband = (freq >= 100) & (freq <= 10000)
        flatness = np.max(system_response[passband]) - np.min(system_response[passband])

        # Dip metric
        min_spl, dip_depth = calculate_dip_metric(freq, system_response, xo_freq)

        # Store results
        results.append({
            'xo_freq': xo_freq,
            'hf_pad': hf_pad,
            'flatness': flatness,
            'dip_depth': dip_depth,
            'min_spl': min_spl,
            'system_response': system_response.copy(),
        })

    # Sort by flatness (lower is better)
    results.sort(key=lambda x: x['flatness'])

    return results


def main():
    """Main optimization workflow."""
    print("=" * 80)
    print("CROSSOVER OPTIMIZATION: DH450 + 12FW88")
    print("=" * 80)

    # Load drivers
    print("\nLoading drivers...")
    lf_driver = load_driver("BC_12FW88")
    hf_driver = load_driver("BC_DH450")

    # LF parameters
    Vb = 0.1145  # m³ (114.5 L)
    Fb = 46.5    # Hz
    horn_fc = 1865  # Hz

    print(f"  LF: Vb={Vb*1000:.1f}L, Fb={Fb:.1f}Hz")
    print(f"  HF: Horn Fc={horn_fc:.0f}Hz")

    # Generate frequency array
    freq = np.logspace(np.log10(20), np.log10(20000), 500)

    # Calculate responses
    print("\nCalculating driver responses...")
    lf_response = np.array([
        calculate_spl_ported_transfer_function(f, lf_driver, Vb, Fb)
        for f in freq
    ])

    hf_response = calculate_hf_horn_response(freq, horn_fc)

    # Sweep crossover frequencies
    print("\n" + "=" * 80)
    print("OPTIMIZATION: Finding best crossover frequency")
    print("=" * 80)

    # Define sweep range - must be above horn cutoff for best results
    # But 12FW88 has beaming above ~2kHz, so we need to balance
    crossover_range = (800, 2500)

    results = sweep_crossover_frequencies(freq, lf_response, hf_response, crossover_range)

    print(f"\n{'XO Freq':>10} {'HF Pad':>10} {'Flatness':>12} {'Dip Depth':>12}")
    print("-" * 50)
    for i, r in enumerate(results[:10]):
        print(f"{r['xo_freq']:>10.0f} {r['hf_pad']:>10.1f} {r['flatness']:>12.2f} {r['dip_depth']:>12.2f}")

    # Best result
    best = results[0]
    print("\n" + "=" * 80)
    print("OPTIMAL CROSSOVER FOUND")
    print("=" * 80)
    print(f"\nCrossover Frequency: {best['xo_freq']:.0f} Hz")
    print(f"HF Padding: {best['hf_pad']:.1f} dB")
    print(f"Flatness: {best['flatness']:.2f} dB")
    print(f"Dip Depth: {best['dip_depth']:.2f} dB")

    # Create comparison plot
    print("\nCreating comparison plot...")

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    # Plot 1: Best result
    ax1 = axes[0]

    ax1.semilogx(freq, lf_response, 'b-', linewidth=1.5, alpha=0.5, label='LF (BC 12FW88)')
    ax1.semilogx(freq, hf_response + best['hf_pad'], 'r-', linewidth=1.5, alpha=0.5, label='HF (BC DH450)')
    ax1.semilogx(freq, best['system_response'], 'k-', linewidth=2.5, label='System')

    # Mark crossover
    ax1.axvline(best['xo_freq'], color='purple', linestyle='--', alpha=0.7, linewidth=1.5)
    ax1.text(best['xo_freq']*1.05, np.max(best['system_response']) - 5,
             f"XO = {best['xo_freq']:.0f} Hz", color='purple', fontweight='bold')

    # Mark horn cutoff
    ax1.axvline(horn_fc, color='orange', linestyle=':', alpha=0.7, linewidth=1.5)
    ax1.text(horn_fc*1.05, np.max(best['system_response']) - 10,
             f"Horn Fc = {horn_fc:.0f} Hz", color='orange', fontsize=9)

    # Crossover region shading
    ax1.axvspan(best['xo_freq']/np.sqrt(2), best['xo_freq']*np.sqrt(2),
                alpha=0.1, color='purple', label='XO Region')

    ax1.set_xlabel('Frequency (Hz)')
    ax1.set_ylabel('SPL (dB)')
    ax1.set_title(f'Optimized Crossover: {best["xo_freq"]:.0f} Hz (Flatness: {best["flatness"]:.2f} dB)')
    ax1.grid(True, which='both', alpha=0.3)
    ax1.legend(loc='lower left')
    ax1.set_xlim(20, 20000)
    ax1.set_ylim(40, 115)

    # Plot 2: Comparison of top 3 options
    ax2 = axes[1]

    colors = ['black', 'blue', 'green']
    for i, result in enumerate(results[:3]):
        label = f"XO = {result['xo_freq']:.0f} Hz (Flatness: {result['flatness']:.2f} dB)"
        ax2.semilogx(freq, result['system_response'], color=colors[i], linewidth=2,
                    linestyle=['-', '--', ':'][i], label=label)

    ax2.axvline(horn_fc, color='orange', linestyle=':', alpha=0.7, linewidth=1.5)
    ax2.text(horn_fc*1.05, 85, f"Horn Fc = {horn_fc:.0f} Hz", color='orange')

    ax2.set_xlabel('Frequency (Hz)')
    ax2.set_ylabel('SPL (dB)')
    ax2.set_title('Crossover Frequency Comparison')
    ax2.grid(True, which='both', alpha=0.3)
    ax2.legend(loc='lower left')
    ax2.set_xlim(20, 20000)
    ax2.set_ylim(70, 100)

    plt.tight_layout()

    # Save plot
    output_dir = Path(__file__).parent
    png_path = output_dir / "crossover_optimization_comparison.png"
    pdf_path = output_dir / "crossover_optimization_comparison.pdf"

    fig.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f"\n✓ PNG saved: {png_path}")
    fig.savefig(pdf_path, bbox_inches='tight')
    print(f"✓ PDF saved: {pdf_path}")

    # Save best design
    design = {
        "lf_driver": "BC_12FW88",
        "hf_driver": "BC_DH450",
        "lf_enclosure": {
            "Vb_liters": Vb * 1000,
            "Fb_hz": Fb,
        },
        "hf_horn": {
            "cutoff_hz": horn_fc,
            "length_m": 0.25,
        },
        "crossover": {
            "frequency_hz": best['xo_freq'],
            "hf_padding_db": best['hf_pad'],
            "flatness_db": best['flatness'],
            "dip_depth_db": best['dip_depth'],
        },
    }

    design_path = output_dir / "optimized_crossover_design.json"
    with open(design_path, 'w') as f:
        json.dump(design, f, indent=2)
    print(f"✓ Design saved: {design_path}")

    # Summary
    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)
    print(f"\nOptimal crossover: {best['xo_freq']:.0f} Hz")
    print(f"  - This is {best['xo_freq']/horn_fc:.2f}× horn cutoff")
    print(f"  - HF padding: {best['hf_pad']:.1f} dB")
    print(f"  - Expected flatness: {best['flatness']:.2f} dB")
    print(f"  - Crossover dip: {best['dip_depth']:.2f} dB")

    if best['xo_freq'] < horn_fc:
        print(f"\n⚠️  WARNING: Crossover ({best['xo_freq']:.0f} Hz) is below horn cutoff ({horn_fc:.0f} Hz)")
        print(f"  This will cause some HF rolloff in crossover region.")
        print(f"  For better performance, consider:")
        print(f"  1. Longer horn (if possible)")
        print(f"  2. Higher crossover frequency")
        print(f"  3. Different HF driver with lower cutoff")
    else:
        print(f"\n✓ Crossover is safely above horn cutoff")

    print("\n" + "=" * 80)

    return best


if __name__ == "__main__":
    main()
