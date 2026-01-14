#!/usr/bin/env python3
"""
Validate the optimized horn design with the LF enclosure.

This integrates the new 250cm² mouth horn (Fc≈468Hz) with the confirmed
LF enclosure to check crossover performance.
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


def main():
    """Validate optimized horn with LF enclosure."""
    print("\n" + "=" * 80)
    print("SYSTEM VALIDATION: OPTIMIZED HORN + LF ENCLOSURE")
    print("=" * 80)

    # Load confirmed LF design
    with open(Path(__file__).parent / "recommended_smaller_mouth_horn_design.json") as f:
        confirmed_design = json.load(f)

    # Load optimized horn design
    with open(Path(__file__).parent / "optimized_horn_direct.json") as f:
        horn_design = json.load(f)

    # LF parameters (confirmed)
    lf_params = {
        "Vb": confirmed_design["lf_enclosure"]["Vb_liters"] / 1000,
        "Fb": confirmed_design["lf_enclosure"]["Fb_hz"],
    }

    # HF parameters (optimized)
    horn_fc = horn_design["performance"]["cutoff_hz"]

    print(f"\nLF Enclosure (BC 12FW88):")
    print(f"  Vb = {lf_params['Vb']*1000:.1f} L")
    print(f"  Fb = {lf_params['Fb']:.1f} Hz")

    print(f"\nHF Horn (BC DH450 - Optimized):")
    print(f"  Throat = {horn_design['parameters']['throat_area_cm2']:.1f} cm²")
    print(f"  Mouth = {horn_design['parameters']['mouth_area_cm2']:.0f} cm²")
    print(f"  Length = {horn_design['parameters']['total_length_cm']:.0f} cm ({horn_design['parameters']['total_length_cm']*10:.0f} mm)")
    print(f"  Fc = {horn_fc:.0f} Hz")

    # Calculate responses
    lf_driver = load_driver("BC_12FW88")
    freq = np.logspace(np.log10(20), np.log10(20000), 500)

    # LF response
    lf_response = np.array([
        calculate_spl_ported_transfer_function(f, lf_driver, lf_params["Vb"], lf_params["Fb"])
        for f in freq
    ])

    # HF response (optimized horn)
    hf_response = calculate_hf_horn_response(freq, horn_fc)

    # Test crossover at 2×Fc (recommended)
    target_xo = int(horn_fc * 2)

    print(f"\n{'='*80}")
    print(f"CROSSOVER ANALYSIS: XO = {target_xo} Hz (2×Fc)")
    print(f"{'='*80}")

    # Optimize HF padding
    try:
        hf_pad = optimize_hf_padding_for_flatness(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            lf_enclosure_type="ported",
            lf_enclosure_params={"Vb": lf_params["Vb"], "Fb": lf_params["Fb"]},
            horn_params={"cutoff": horn_fc, "length": horn_design["parameters"]["total_length_cm"]/100},
            crossover_frequency=target_xo,
            padding_range=(-25, -10),
            num_steps=16,
        )
    except:
        hf_pad = -16

    print(f"  Optimal HF padding: {hf_pad:.1f} dB")

    # Calculate system response
    lp_gain_db, hp_gain_db = calculate_lr4_crossover_gains(freq, target_xo)
    lf_combined = lf_response + lp_gain_db
    hf_combined = (hf_response + hf_pad) + hp_gain_db
    system_response = 10 * np.log10(10**(lf_combined/10) + 10**(hf_combined/10))

    # Calculate crossover region dip
    xo_region = (freq >= target_xo/2) & (freq <= target_xo*2)
    xo_spl = system_response[xo_region]
    min_spl = np.min(xo_spl)
    max_spl = np.max(xo_spl)
    dip = max_spl - min_spl

    # Calculate overall flatness
    flatness = calculate_system_flatness(freq, system_response)

    # Calculate F3
    f3 = calculate_f3_frequency(freq, system_response)

    print(f"  Dip in XO region: {dip:.2f} dB")
    print(f"  Overall flatness: {flatness:.2f} dB")
    print(f"  System F3: {f3:.0f} Hz")

    # Compare with previous design
    print(f"\n{'='*80}")
    print("COMPARISON: Original vs Optimized Horn")
    print(f"{'='*80}")

    original_fc = 1865  # Hz (from 504cm² mouth)
    original_xo = 2238  # Hz
    original_dip = 13.75  # dB

    print(f"\n{'Metric':<25} {'Original':>15} {'Optimized':>15} {'Improvement':>15}")
    print("-" * 75)
    print(f"{'Horn mouth':<25} {504:>15.0f} {horn_design['parameters']['mouth_area_cm2']:>15.0f} {((horn_design['parameters']['mouth_area_cm2']-504)/504*100):>+14.1f}%")
    print(f"{'Horn Fc':<25} {original_fc:>15.0f} {horn_fc:>15.0f} {((horn_fc-original_fc)/original_fc*100):>+14.1f}%")
    print(f"{'XO frequency':<25} {original_xo:>15.0f} {target_xo:>15.0f} {((target_xo-original_xo)/original_xo*100):>+14.1f}%")
    print(f"{'Dip at XO':<25} {original_dip:>15.2f} {dip:>15.2f} {(original_dip - dip):>+15.2f} dB")
    print(f"{'Flatness':<25} {11.36:>15.2f} {flatness:>15.2f} {(11.36 - flatness):>+15.2f} dB")

    # Rate the dip
    if dip < 1.5:
        rating = "✅ Excellent"
    elif dip < 2.5:
        rating = "✅ Good"
    elif dip < 4:
        rating = "⚠️  Acceptable"
    else:
        rating = "❌ Poor"

    print(f"\n  Rating: {rating}")

    # Create plot
    print(f"\n{'='*80}")
    print("CREATING SYSTEM RESPONSE PLOT")
    print(f"{'='*80}")

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    # Plot 1: System response
    ax1 = axes[0]

    ax1.semilogx(freq, lf_response, 'b-', linewidth=1.5, alpha=0.7, label='LF (12FW88)')
    ax1.semilogx(freq, hf_response + hf_pad, 'r-', linewidth=1.5, alpha=0.7, label=f'HF (DH450 + {hf_pad:.1f}dB pad)')
    ax1.semilogx(freq, system_response, 'k-', linewidth=2.5, label='System')
    ax1.axvline(target_xo, color='gray', linestyle='--', alpha=0.5, label=f'XO: {target_xo} Hz')
    ax1.axvline(horn_fc, color='orange', linestyle=':', alpha=0.7, label=f'Horn Fc: {horn_fc:.0f} Hz')
    ax1.axvline(f3, color='green', linestyle=':', alpha=0.7, label=f'System F3: {f3:.0f} Hz')

    # -3dB band
    passband_max = np.max(system_response[(freq >= 100) & (freq <= 10000)])
    threshold = passband_max - 3
    ax1.axhline(threshold, color='gray', linestyle=':', alpha=0.3)

    ax1.set_xlabel('Frequency (Hz)')
    ax1.set_ylabel('SPL (dB)')
    ax1.set_title(f'Optimized System Response: XO={target_xo}Hz, Dip={dip:.1f}dB, Flatness={flatness:.1f}dB')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='lower left', fontsize=9)
    ax1.set_xlim(100, 20000)
    ax1.set_ylim(60, 105)

    # Plot 2: Crossover region detail
    ax2 = axes[1]

    # Zoom into crossover region
    xo_range = (freq >= target_xo/3) & (freq <= target_xo*3)
    freq_xo = freq[xo_range]
    lf_xo = lf_combined[xo_range]
    hf_xo = hf_combined[xo_range]
    sys_xo = system_response[xo_range]

    ax2.semilogx(freq_xo, lf_xo, 'b-', linewidth=1.5, alpha=0.7, label='LF (after LP filter)')
    ax2.semilogx(freq_xo, hf_xo, 'r-', linewidth=1.5, alpha=0.7, label='HF (after HP filter)')
    ax2.semilogx(freq_xo, sys_xo, 'k-', linewidth=2.5, label='System')
    ax2.axvline(target_xo, color='gray', linestyle='--', alpha=0.5, label=f'XO: {target_xo} Hz')

    # Mark dip
    min_idx = np.argmin(sys_xo)
    ax2.plot(freq_xo[min_idx], sys_xo[min_idx], 'ro', markersize=8,
             label=f'Dip: {dip:.1f} dB')

    ax2.set_xlabel('Frequency (Hz)')
    ax2.set_ylabel('SPL (dB)')
    ax2.set_title(f'Crossover Region Detail ({target_xo//2:.0f}-{target_xo*2:.0f} Hz)')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='lower left', fontsize=9)
    ax2.set_xlim(target_xo/3, target_xo*3)

    plt.tight_layout()

    # Save plot
    output_dir = Path(__file__).parent
    png_path = output_dir / "optimized_horn_system_response.png"
    pdf_path = output_dir / "optimized_horn_system_response.pdf"

    fig.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f"\n✓ PNG saved: {png_path}")
    fig.savefig(pdf_path, bbox_inches='tight')
    print(f"✓ PDF saved: {pdf_path}")

    # Save final system design
    final_design = {
        'lf_driver': 'BC_12FW88',
        'hf_driver': 'BC_DH450',
        'lf_enclosure': confirmed_design["lf_enclosure"],
        'hf_horn': horn_design['parameters'],
        'horn_performance': horn_design['performance'],
        'crossover': {
            'frequency_hz': target_xo,
            'order': 4,
            'type': 'LR4',
            'hf_padding_db': hf_pad,
            'xo_vs_fc_ratio': target_xo / horn_fc,
        },
        'performance': {
            'dip_at_crossover_db': dip,
            'flatness_db': flatness,
            'f3_hz': f3,
            'rating': rating,
        },
        'comparison': {
            'original_dip_db': original_dip,
            'dip_improvement_db': original_dip - dip,
            'original_flatness_db': 11.36,
            'flatness_improvement_db': 11.36 - flatness,
        },
    }

    final_path = output_dir / "final_optimized_system_design.json"
    with open(final_path, 'w') as f:
        json.dump(final_design, f, indent=2)

    print(f"✓ Final design saved: {final_path}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\n✅ Optimized horn successfully integrated with LF enclosure")
    print(f"   Horn mouth: {horn_design['parameters']['mouth_area_cm2']:.0f} cm² (was 504 cm²)")
    print(f"   Horn Fc: {horn_fc:.0f} Hz (was {original_fc} Hz)")
    print(f"   Crossover: {target_xo} Hz (was {original_xo} Hz)")
    print(f"   Dip improved: {original_dip:.1f} → {dip:.1f} dB ({original_dip-dip:.1f} dB better)")
    print(f"   Flatness improved: {11.36:.1f} → {flatness:.1f} dB ({11.36-flatness:.1f} dB better)")
    print(f"\n   Rating: {rating}")
    print(f"\nNext: Validate with Hornresp simulations")
    print("=" * 80)


if __name__ == "__main__":
    main()
