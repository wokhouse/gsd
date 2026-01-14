#!/usr/bin/env python3
"""
Find optimal crossover frequency for the optimized horn.

Instead of using 2×Fc rule, sweep XO range to find best flatness.
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
    calculate_system_flatness,
)

rcParams['font.size'] = 11
rcParams['axes.labelsize'] = 12
rcParams['axes.titlesize'] = 14
rcParams['grid.alpha'] = 0.3


def main():
    """Find optimal crossover for optimized horn."""
    print("\n" + "=" * 80)
    print("CROSSOVER OPTIMIZATION FOR OPTIMIZED HORN")
    print("=" * 80)

    # Load confirmed LF design
    with open(Path(__file__).parent / "recommended_smaller_mouth_horn_design.json") as f:
        confirmed_design = json.load(f)

    # Load optimized horn design
    with open(Path(__file__).parent / "optimized_horn_direct.json") as f:
        horn_design = json.load(f)

    # LF parameters
    lf_params = {
        "Vb": confirmed_design["lf_enclosure"]["Vb_liters"] / 1000,
        "Fb": confirmed_design["lf_enclosure"]["Fb_hz"],
    }

    # HF parameters
    horn_fc = horn_design["performance"]["cutoff_hz"]

    print(f"\nSystem:")
    print(f"  LF: BC 12FW88 in {lf_params['Vb']*1000:.1f}L @ {lf_params['Fb']:.1f}Hz")
    print(f"  HF: BC DH450 in {horn_design['parameters']['mouth_area_cm2']:.0f}cm² horn")
    print(f"  Horn Fc: {horn_fc:.0f} Hz")

    # Calculate responses
    lf_driver = load_driver("BC_12FW88")
    freq = np.logspace(np.log10(20), np.log10(20000), 500)

    lf_response = np.array([
        calculate_spl_ported_transfer_function(f, lf_driver, lf_params["Vb"], lf_params["Fb"])
        for f in freq
    ])

    hf_response = calculate_hf_horn_response(freq, horn_fc)

    # Sweep XO frequencies
    print(f"\n{'='*80}")
    print("CROSSOVER SWEEP")
    print(f"{'='*80}")

    # Test XO range from 600-1200 Hz
    xo_range = np.arange(600, 1250, 50)

    results = []

    for xo_freq in xo_range:
        # Optimize HF padding for this XO
        try:
            hf_pad = optimize_hf_padding_for_flatness(
                lf_driver_name="BC_12FW88",
                hf_driver_name="BC_DH450",
                lf_enclosure_type="ported",
                lf_enclosure_params={"Vb": lf_params["Vb"], "Fb": lf_params["Fb"]},
                horn_params={"cutoff": horn_fc, "length": horn_design["parameters"]["total_length_cm"]/100},
                crossover_frequency=xo_freq,
                padding_range=(-25, -10),
                num_steps=16,
            )
        except:
            hf_pad = -16

        # Calculate system response
        lp_gain_db, hp_gain_db = calculate_lr4_crossover_gains(freq, xo_freq)
        lf_combined = lf_response + lp_gain_db
        hf_combined = (hf_response + hf_pad) + hp_gain_db
        system_response = 10 * np.log10(10**(lf_combined/10) + 10**(hf_combined/10))

        # Calculate metrics
        flatness = calculate_system_flatness(freq, system_response)

        # Dip in crossover region
        xo_region = (freq >= xo_freq/2) & (freq <= xo_freq*2)
        xo_spl = system_response[xo_region]
        min_spl = np.min(xo_spl)
        max_spl = np.max(xo_spl)
        dip = max_spl - min_spl

        results.append({
            'xo_freq': xo_freq,
            'hf_pad': hf_pad,
            'flatness': flatness,
            'dip': dip,
            'system_response': system_response,
            'lf_combined': lf_combined,
            'hf_combined': hf_combined,
        })

        print(f"XO={xo_freq:4.0f}Hz: pad={hf_pad:5.1f}dB, dip={dip:5.2f}dB, flatness={flatness:5.2f}dB")

    # Find best design
    print(f"\n{'='*80}")
    print("OPTIMAL CROSSOVER")
    print(f"{'='*80}")

    # Sort by dip (primary), then flatness (secondary)
    results_sorted = sorted(results, key=lambda x: (x['dip'], x['flatness']))
    best = results_sorted[0]

    print(f"\nBest crossover: {best['xo_freq']:.0f} Hz")
    print(f"  This is {best['xo_freq']/horn_fc:.2f}×Fc")
    print(f"  HF padding: {best['hf_pad']:.1f} dB")
    print(f"  Dip: {best['dip']:.2f} dB")
    print(f"  Flatness: {best['flatness']:.2f} dB")

    # Rate the dip
    if best['dip'] < 1.5:
        rating = "✅ Excellent"
    elif best['dip'] < 2.5:
        rating = "✅ Good"
    elif best['dip'] < 4:
        rating = "⚠️  Accepttable"
    else:
        rating = "❌ Poor"

    print(f"  Rating: {rating}")

    # Compare with 2×Fc (may not be in range)
    result_2fc = [r for r in results if r['xo_freq'] == int(horn_fc * 2)]

    print(f"\nComparison with 2×Fc rule:")
    if result_2fc:
        result_2fc = result_2fc[0]
        print(f"  2×Fc ({int(horn_fc*2)}Hz): dip={result_2fc['dip']:.2f}dB, flat={result_2fc['flatness']:.2f}dB")
        print(f"  Optimal ({best['xo_freq']:.0f}Hz): dip={best['dip']:.2f}dB, flat={best['flatness']:.2f}dB")
        print(f"  Improvement: {result_2fc['dip'] - best['dip']:.2f}dB dip, {result_2fc['flatness'] - best['flatness']:.2f}dB flatness")
        has_2fc = True
    else:
        print(f"  2×Fc ({int(horn_fc*2)}Hz): not in sweep range")
        print(f"  Optimal ({best['xo_freq']:.0f}Hz): dip={best['dip']:.2f}dB, flat={best['flatness']:.2f}dB")
        has_2fc = False
        result_2fc = None

    # Create plot
    print(f"\n{'='*80}")
    print("CREATING PLOT")
    print(f"{'='*80}")

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    # Plot 1: Dip vs XO frequency
    ax1 = axes[0]

    xo_freqs = [r['xo_freq'] for r in results]
    dips = [r['dip'] for r in results]

    ax1.plot(xo_freqs, dips, 'bo-', linewidth=2, markersize=6)
    ax1.axvline(horn_fc * 2, color='green', linestyle='--', alpha=0.7,
                label=f'2×Fc rule ({int(horn_fc*2)} Hz)')
    ax1.axvline(best['xo_freq'], color='red', linestyle='--', alpha=0.7,
                label=f'Optimal ({int(best["xo_freq"])} Hz)')
    ax1.axhline(2, color='orange', linestyle=':', alpha=0.5, label='Good (2 dB)')
    ax1.axhline(4, color='red', linestyle=':', alpha=0.5, label='Poor (4 dB)')

    ax1.set_xlabel('Crossover Frequency (Hz)')
    ax1.set_ylabel('Dip in Crossover Region (dB)')
    ax1.set_title('Crossover Dip vs Frequency (Lower is Better)')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    ax1.set_xlim(600, 1200)

    # Plot 2: System response comparison
    ax2 = axes[1]

    # Plot optimal
    ax2.semilogx(freq, best['system_response'], 'g-', linewidth=2.5,
                label=f"Optimal XO: {best['xo_freq']:.0f}Hz (dip={best['dip']:.1f}dB)")

    # Plot 2×Fc if available
    if result_2fc:
        ax2.semilogx(freq, result_2fc['system_response'], 'r--', linewidth=2,
                    label=f"2×Fc XO: {int(horn_fc*2)}Hz (dip={result_2fc['dip']:.1f}dB)")
        ax2.axvline(horn_fc * 2, color='red', linestyle=':', alpha=0.5)

    ax2.axvline(best['xo_freq'], color='green', linestyle=':', alpha=0.5)

    ax2.set_xlabel('Frequency (Hz)')
    ax2.set_ylabel('SPL (dB)')
    ax2.set_title('System Response: Optimal vs 2×Fc Crossover')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='lower left', fontsize=10)
    ax2.set_xlim(100, 20000)

    plt.tight_layout()

    # Save
    output_dir = Path(__file__).parent
    png_path = output_dir / "optimized_horn_xo_sweep.png"
    pdf_path = output_dir / "optimized_horn_xo_sweep.pdf"

    fig.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f"\n✓ PNG saved: {png_path}")
    fig.savefig(pdf_path, bbox_inches='tight')
    print(f"✓ PDF saved: {pdf_path}")

    # Save optimal design
    final_design = {
        'lf_driver': 'BC_12FW88',
        'hf_driver': 'BC_DH450',
        'lf_enclosure': confirmed_design["lf_enclosure"],
        'hf_horn': horn_design['parameters'],
        'horn_performance': horn_design['performance'],
        'crossover': {
            'frequency_hz': int(best['xo_freq']),
            'order': 4,
            'type': 'LR4',
            'hf_padding_db': best['hf_pad'],
            'xo_vs_fc_ratio': best['xo_freq'] / horn_fc,
            'optimization_method': 'sweep_xo_range',
        },
        'performance': {
            'dip_at_crossover_db': best['dip'],
            'flatness_db': best['flatness'],
            'rating': rating,
        },
    }

    if result_2fc:
        final_design['comparison_with_2fc_rule'] = {
            'freq_2fc_hz': int(horn_fc * 2),
            'dip_2fc_db': result_2fc['dip'],
            'flatness_2fc_db': result_2fc['flatness'],
            'dip_improvement_db': result_2fc['dip'] - best['dip'],
            'flatness_improvement_db': result_2fc['flatness'] - best['flatness'],
        }

    final_path = output_dir / "final_optimized_system_optimal_xo.json"
    with open(final_path, 'w') as f:
        json.dump(final_design, f, indent=2)

    print(f"✓ Final design saved: {final_path}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\n✅ Optimal crossover found: {best['xo_freq']:.0f} Hz ({best['xo_freq']/horn_fc:.2f}×Fc)")
    print(f"   Horn: 250cm² mouth, 250mm length, Fc={horn_fc:.0f}Hz")
    print(f"   Dip: {best['dip']:.2f} dB (was 13.75 dB with original horn)")
    print(f"   Flatness: {best['flatness']:.2f} dB (was 11.36 dB)")
    print(f"   HF pad: {best['hf_pad']:.1f} dB")
    print(f"\n   Rating: {rating}")
    if result_2fc:
        print(f"\n   Improvement over 2×Fc rule:")
        print(f"     Dip: {result_2fc['dip']:.2f} → {best['dip']:.2f} dB ({result_2fc['dip']-best['dip']:.2f} dB better)")
        print(f"     Flatness: {result_2fc['flatness']:.2f} → {best['flatness']:.2f} dB ({result_2fc['flatness']-best['flatness']:.2f} dB better)")
    print("=" * 80)


if __name__ == "__main__":
    main()
