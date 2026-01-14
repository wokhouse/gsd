#!/usr/bin/env python3
"""
Optimize system for higher crossover frequency (2500-3000 Hz).

This should reduce the crossover dip by ensuring the XO is well above
the horn cutoff (1865 Hz), giving proper HF loading.
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
    calculate_f3_frequency,
)

rcParams['font.size'] = 11
rcParams['axes.labelsize'] = 12
rcParams['axes.titlesize'] = 14
rcParams['grid.alpha'] = 0.3


def sweep_xo_frequencies(freq, lf_response, hf_response, xo_range, lf_params):
    """Sweep crossover frequencies and find best flatness."""
    print(f"\nSweeping crossover frequencies from {xo_range[0]} to {xo_range[1]} Hz...")

    results = []
    xo_frequencies = np.linspace(xo_range[0], xo_range[1], 30)

    for xo_freq in xo_frequencies:
        try:
            # Optimize HF padding for this XO
            hf_pad = optimize_hf_padding_for_flatness(
                lf_driver_name="BC_12FW88",
                hf_driver_name="BC_DH450",
                lf_enclosure_type="ported",
                lf_enclosure_params={"Vb": lf_params["Vb"], "Fb": lf_params["Fb"]},
                horn_params={"cutoff": lf_params["horn_fc"], "length": lf_params["horn_length"]},
                crossover_frequency=xo_freq,
                padding_range=(-25, -5),
                num_steps=21,
            )
        except Exception as e:
            hf_pad = -16.0  # Fallback

        # Calculate system response
        lp_gain_db, hp_gain_db = calculate_lr4_crossover_gains(freq, xo_freq)
        lf_combined = lf_response + lp_gain_db
        hf_combined = (hf_response + hf_pad) + hp_gain_db

        system_response = 10 * np.log10(
            10**(lf_combined/10) + 10**(hf_combined/10)
        )

        # Calculate metrics
        # Overall flatness (100-10000 Hz)
        flatness = calculate_system_flatness(freq, system_response)

        # Crossover region flatness (±1 octave)
        xo_mask = (freq >= xo_freq/2) & (freq <= xo_freq*2)
        if np.any(xo_mask):
            xo_response = system_response[xo_mask]
            xo_flatness = np.max(xo_response) - np.min(xo_response)
        else:
            xo_flatness = 100

        # Dip at crossover
        xo_spl = np.interp(xo_freq, freq, system_response)
        peak_spl = np.max(system_response[(freq >= 100) & (freq <= 10000)])
        dip_at_xo = peak_spl - xo_spl

        results.append({
            'xo_freq': xo_freq,
            'hf_pad': hf_pad,
            'flatness': flatness,
            'xo_flatness': xo_flatness,
            'dip_at_xo': dip_at_xo,
            'system_response': system_response.copy(),
        })

    # Sort by dip_at_xo (lower is better)
    results.sort(key=lambda x: x['dip_at_xo'])

    return results


def calculate_minus_3db_band(freq, response):
    """Calculate -3dB bandwidth."""
    mask = (freq >= 100) & (freq <= 10000)
    if not np.any(mask):
        return np.nan, np.nan, 0

    peak = np.max(response[mask])
    threshold = peak - 3

    above_threshold = response > threshold
    above_idx = np.where(above_threshold)[0]

    if len(above_idx) == 0:
        return np.nan, np.nan, 0

    f_low = freq[above_idx[0]]
    f_high = freq[above_idx[-1]]
    bandwidth = np.log2(f_high / f_low)

    return f_low, f_high, bandwidth


def main():
    """Main optimization workflow."""
    print("\n" + "=" * 80)
    print("HIGHER CROSSOVER OPTIMIZATION")
    print("Target: 2500-3000 Hz to reduce crossover dip")
    print("=" * 80)

    # LF parameters (confirmed)
    lf_params = {
        "Vb": 0.1145,
        "Fb": 47.6,
        "horn_fc": 1865,
        "horn_length": 0.25,
    }

    print(f"\nLF Enclosure:")
    print(f"  Vb = {lf_params['Vb']*1000:.1f} L")
    print(f"  Fb = {lf_params['Fb']:.1f} Hz")

    print(f"\nHF Horn:")
    print(f"  Fc = {lf_params['horn_fc']:.0f} Hz")
    print(f"  Length = {lf_params['horn_length']*1000:.0f} mm")

    # Calculate responses
    print("\nCalculating driver responses...")

    lf_driver = load_driver("BC_12FW88")
    freq = np.logspace(np.log10(20), np.log10(20000), 500)

    lf_response = np.array([
        calculate_spl_ported_transfer_function(f, lf_driver, lf_params["Vb"], lf_params["Fb"])
        for f in freq
    ])

    hf_response = calculate_hf_horn_response(freq, lf_params["horn_fc"])

    # Sweep XO frequencies
    print("\n" + "=" * 80)
    print("SWEEPING CROSSOVER FREQUENCIES")
    print("=" * 80)

    xo_range = (2500, 3000)
    results = sweep_xo_frequencies(freq, lf_response, hf_response, xo_range, lf_params)

    # Display top results
    print(f"\n{'XO Freq':>10} {'HF Pad':>9} {'Flatness':>10} {'XO Flat':>10} {'Dip @ XO':>11}")
    print("-" * 60)
    for i, r in enumerate(results[:10]):
        print(f"{r['xo_freq']:>10.0f} {r['hf_pad']:>9.1f} {r['flatness']:>10.2f} {r['xo_flatness']:>10.2f} {r['dip_at_xo']:>11.2f}")

    # Best result
    best = results[0]

    print("\n" + "=" * 80)
    print("OPTIMAL CROSSOVER FOUND")
    print("=" * 80)

    print(f"\nCrossover: {best['xo_freq']:.0f} Hz")
    print(f"  Ratio to horn cutoff: {best['xo_freq']/lf_params['horn_fc']:.2f}×")
    print(f"  HF padding: {best['hf_pad']:.1f} dB")
    print(f"  Overall flatness: {best['flatness']:.2f} dB")
    print(f"  XO region flatness: {best['xo_flatness']:.2f} dB")
    print(f"  Dip at crossover: {best['dip_at_xo']:.2f} dB")

    # Calculate -3dB band
    f_low, f_high, bandwidth = calculate_minus_3db_band(freq, best['system_response'])

    print(f"\n-3dB Band:")
    print(f"  Range: {f_low:.0f} - {f_high:.0f} Hz")
    print(f"  Bandwidth: {bandwidth:.2f} octaves")

    # Calculate F3
    f3 = calculate_f3_frequency(freq, best['system_response'])
    print(f"\nSystem F3: {f3:.1f} Hz")

    # Assessment
    print("\n" + "=" * 80)
    print("ASSESSMENT")
    print("=" * 80)

    if best['dip_at_xo'] < 2:
        print("✅ Excellent - Minimal dip at crossover")
    elif best['dip_at_xo'] < 3:
        print("✅ Good - Acceptable dip")
    elif best['dip_at_xo'] < 4:
        print("⚠️  Fair - Noticeable dip")
    else:
        print("❌ Poor - Significant dip")

    # Create comparison plot
    print("\nGenerating comparison plot...")

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    # Plot 1: Best result
    ax1 = axes[0]

    ax1.semilogx(freq, lf_response, 'b-', linewidth=1.5, alpha=0.5, label='LF (BC 12FW88)')
    ax1.semilogx(freq, hf_response + best['hf_pad'], 'r-', linewidth=1.5, alpha=0.5, label='HF (BC DH450)')
    ax1.semilogx(freq, best['system_response'], 'k-', linewidth=3, label='System')

    # Mark crossover
    ax1.axvline(best['xo_freq'], color='purple', linestyle='--', alpha=0.8, linewidth=2)
    ax1.text(best['xo_freq']*1.05, np.max(best['system_response']) - 5,
             f"XO = {best['xo_freq']:.0f} Hz\nDip = {best['dip_at_xo']:.2f} dB",
             color='purple', fontweight='bold')

    # Mark horn cutoff
    ax1.axvline(lf_params['horn_fc'], color='orange', linestyle=':', alpha=0.7, linewidth=2)
    ax1.text(lf_params['horn_fc']*1.05, np.max(best['system_response']) - 10,
             f"Horn Fc = {lf_params['horn_fc']:.0f} Hz", color='orange')

    # Shade crossover region
    ax1.axvspan(best['xo_freq']/np.sqrt(2), best['xo_freq']*np.sqrt(2),
                alpha=0.1, color='purple', label='XO Region (±½ octave)')

    # Shade -3dB band
    ax1.axhspan(91.36, 94.36, alpha=0.05, color='green', label='-3dB Band (old)')
    ax1.axhspan(np.max(best['system_response'])-3, np.max(best['system_response']),
                alpha=0.1, color='green', label='-3dB Band (new)')

    ax1.set_xlabel('Frequency (Hz)')
    ax1.set_ylabel('SPL (dB)')
    ax1.set_title(f'Optimized System: XO = {best["xo_freq"]:.0f} Hz ({best["xo_freq"]/lf_params["horn_fc"]:.2f}×Fc)')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='lower left', fontsize=9)
    ax1.set_xlim(100, 20000)
    ax1.set_ylim(70, 100)

    # Plot 2: Comparison of different XO frequencies
    ax2 = axes[1]

    # Show best 3 results
    colors = ['black', 'blue', 'green']
    linestyles = ['-', '--', ':']

    for i, result in enumerate(results[:3]):
        label = f"XO = {result['xo_freq']:.0f} Hz (Dip: {result['dip_at_xo']:.2f} dB, XO/Fc: {result['xo_freq']/lf_params['horn_fc']:.2f}×)"
        ax2.semilogx(freq, result['system_response'], color=colors[i], linewidth=2,
                    linestyle=linestyles[i], label=label)

    ax2.axvline(lf_params['horn_fc'], color='orange', linestyle=':', alpha=0.7, linewidth=2)
    ax2.text(lf_params['horn_fc']*1.05, 75, f"Horn Fc = {lf_params['horn_fc']:.0f} Hz", color='orange')

    ax2.set_xlabel('Frequency (Hz)')
    ax2.set_ylabel('SPL (dB)')
    ax2.set_title('Crossover Frequency Comparison')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='lower left', fontsize=9)
    ax2.set_xlim(100, 20000)
    ax2.set_ylim(75, 98)

    plt.tight_layout()

    # Save plot
    output_dir = Path(__file__).parent
    png_path = output_dir / "higher_xo_optimization_results.png"
    pdf_path = output_dir / "higher_xo_optimization_results.pdf"

    fig.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f"\n✓ PNG saved: {png_path}")
    fig.savefig(pdf_path, bbox_inches='tight')
    print(f"✓ PDF saved: {pdf_path}")

    # Save design
    print("\n" + "=" * 80)
    print("SAVING OPTIMIZED DESIGN")
    print("=" * 80)

    optimized_design = {
        "lf_driver": "BC_12FW88",
        "hf_driver": "BC_DH450",
        "lf_enclosure": {
            "Vb_liters": lf_params["Vb"] * 1000,
            "Fb_hz": lf_params["Fb"],
            "F3_hz": f3,
        },
        "hf_horn": {
            "cutoff_hz": lf_params["horn_fc"],
            "length_cm": lf_params["horn_length"] * 100,
        },
        "crossover": {
            "frequency_hz": best['xo_freq'],
            "order": 4,
            "type": "LR4",
            "hf_padding_db": best['hf_pad'],
            "lf_padding_db": 0.0,
        },
        "performance": {
            "flatness_db": best['flatness'],
            "xo_region_flatness_db": best['xo_flatness'],
            "dip_at_crossover_db": best['dip_at_xo'],
            "minus_3db_band_hz": (f_low, f_high),
            "bandwidth_octaves": bandwidth,
        },
    }

    design_path = output_dir / "optimized_design_higher_xo.json"
    with open(design_path, 'w') as f:
        json.dump(optimized_design, f, indent=2)
    print(f"✓ Design saved: {design_path}")

    # Summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)

    print(f"\n✅ OPTIMIZED DESIGN:")
    print(f"   Crossover: {best['xo_freq']:.0f} Hz (vs 2238 Hz before)")
    print(f"   XO/Fc ratio: {best['xo_freq']/lf_params['horn_fc']:.2f}× (vs 1.20× before)")
    print(f"   Dip at XO: {best['dip_at_xo']:.2f} dB (vs 4.70 dB before)")
    print(f"   Improvement: {4.70 - best['dip_at_xo']:.2f} dB less dip!")

    print(f"\nPerformance:")
    print(f"   -3dB bandwidth: {bandwidth:.2f} octaves ({f_low:.0f}-{f_high:.0f} Hz)")
    print(f"   Overall flatness: {best['flatness']:.2f} dB")
    print(f"   XO region flatness: {best['xo_flatness']:.2f} dB")

    print("\n" + "=" * 80)

    return optimized_design


if __name__ == "__main__":
    main()
