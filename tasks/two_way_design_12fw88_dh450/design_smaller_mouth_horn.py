#!/usr/bin/env python3
"""
Optimize horn with smaller mouth constraint for better crossover integration.

Targets:
- Horn cutoff: 400-500 Hz (for 800-1000 Hz XO, 2×Fc rule)
- Mouth area: ≤350 cm² (sacrifice some HF sensitivity)
- Max length: 250mm
- Result: Smooth crossover with <2 dB dip
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
    calculate_f3_frequency,
    calculate_system_flatness,
)

rcParams['font.size'] = 11
rcParams['axes.labelsize'] = 12
rcParams['axes.titlesize'] = 14
rcParams['grid.alpha'] = 0.3


def main():
    """Design and test smaller-mouth horn for better crossover."""
    print("\n" + "=" * 80)
    print("SMALLER MOUTH HORN DESIGN")
    print("Sacrifice HF sensitivity for better crossover integration")
    print("=" * 80)

    # LF parameters (confirmed)
    lf_params = {
        "Vb": 0.1145,
        "Fb": 47.6,
    }

    print(f"\nLF Enclosure (confirmed):")
    print(f"  Vb = {lf_params['Vb']*1000:.1f} L")
    print(f"  Fb = {lf_params['Fb']:.1f} Hz")

    # Define alternative horn designs with smaller mouth
    print(f"\n{'='*80}")
    print("ALTERNATIVE HORN DESIGNS")
    print(f"{'='*80}")

    horn_options = [
        {
            'name': 'Current (504 cm² mouth)',
            'throat_cm2': 7.0,
            'mouth_cm2': 504.4,
            'length_cm': 25.0,
            'fc_hz': 1865,
        },
        {
            'name': 'Option A: 350 cm² mouth',
            'throat_cm2': 7.0,
            'mouth_cm2': 350.0,
            'length_cm': 25.0,
            'fc_hz': None,  # Will calculate
        },
        {
            'name': 'Option B: 300 cm² mouth',
            'throat_cm2': 7.0,
            'mouth_cm2': 300.0,
            'length_cm': 25.0,
            'fc_hz': None,
        },
        {
            'name': 'Option C: 250 cm² mouth',
            'throat_cm2': 7.0,
            'mouth_cm2': 250.0,
            'length_cm': 25.0,
            'fc_hz': None,
        },
    ]

    # Calculate cutoff for each option
    c = 343  # m/s
    for horn in horn_options:
        if horn['fc_hz'] is None:
            # For exponential horn with uniform expansion
            # m = ln(mouth/throat) / L
            # fc = c * m / (4π)
            throat_m2 = horn['throat_cm2'] / 10000
            mouth_m2 = horn['mouth_cm2'] / 10000
            length_m = horn['length_cm'] / 100

            m = np.log(mouth_m2 / throat_m2) / length_m
            fc = (c * m / 2) / (2 * np.pi)
            horn['fc_hz'] = fc

    # Display options
    print(f"\n{'Option':<30} {'Throat':>10} {'Mouth':>10} {'Fc':>10} {'XO @ 2×Fc':>12}")
    print("-" * 80)
    for horn in horn_options:
        xo_2fc = horn['fc_hz'] * 2
        print(f"{horn['name']:<30} {horn['throat_cm2']:>8.1f} cm² {horn['mouth_cm2']:>8.1f} cm² {horn['fc_hz']:>8.0f} Hz {xo_2fc:>10.0f} Hz")

    # Test each option
    print(f"\n{'='*80}")
    print("CROSSOVER INTEGRATION ANALYSIS")
    print(f"{'='*80}")

    lf_driver = load_driver("BC_12FW88")
    freq = np.logspace(np.log10(20), np.log10(20000), 500)

    # Calculate LF response
    lf_response = np.array([
        calculate_spl_ported_transfer_function(f, lf_driver, lf_params["Vb"], lf_params["Fb"])
        for f in freq
    ])

    results = []

    for horn in horn_options:
        print(f"\n{horn['name']}:")

        # Calculate HF response
        hf_response = calculate_hf_horn_response(freq, horn['fc_hz'])

        # Target XO range: 2×Fc to 2.5×Fc
        xo_min = int(horn['fc_hz'] * 2)
        xo_max = int(horn['fc_hz'] * 2.5)

        # Find best XO in range
        best_xo = None
        best_dip = 100
        best_pad = -16

        for xo_freq in range(xo_min, xo_max + 1, 50):
            try:
                hf_pad = optimize_hf_padding_for_flatness(
                    lf_driver_name="BC_12FW88",
                    hf_driver_name="BC_DH450",
                    lf_enclosure_type="ported",
                    lf_enclosure_params={"Vb": lf_params["Vb"], "Fb": lf_params["Fb"]},
                    horn_params={"cutoff": horn['fc_hz'], "length": horn['length_cm']/100},
                    crossover_frequency=xo_freq,
                    padding_range=(-25, -10),
                    num_steps=16,
                )
            except:
                hf_pad = -16

            # Calculate dip at XO
            lp_gain_db, hp_gain_db = calculate_lr4_crossover_gains(freq, xo_freq)
            lf_combined = lf_response + lp_gain_db
            hf_combined = (hf_response + hf_pad) + hp_gain_db
            system_response = 10 * np.log10(10**(lf_combined/10) + 10**(hf_combined/10))

            # Find dip in crossover region
            xo_region = (freq >= xo_freq/2) & (freq <= xo_freq*2)
            xo_spl = system_response[xo_region]
            min_spl = np.min(xo_spl)
            max_spl = np.max(xo_spl)
            dip = max_spl - min_spl

            if dip < best_dip:
                best_dip = dip
                best_xo = xo_freq
                best_pad = hf_pad

        # Calculate overall flatness
        lp_gain_db, hp_gain_db = calculate_lr4_crossover_gains(freq, best_xo)
        lf_combined = lf_response + lp_gain_db
        hf_combined = (hf_response + best_pad) + hp_gain_db
        system_response = 10 * np.log10(10**(lf_combined/10) + 10**(hf_combined/10))

        flatness = calculate_system_flatness(freq, system_response)

        # Calculate -3dB bandwidth
        passband_max = np.max(system_response[(freq >= 100) & (freq <= 10000)])
        threshold = passband_max - 3
        above_threshold = system_response > threshold
        above_idx = np.where(above_threshold)[0]

        if len(above_idx) > 0:
            f_low = freq[above_idx[0]]
            f_high = freq[above_idx[-1]]
            bandwidth_octaves = np.log2(f_high / f_low)
        else:
            f_low = f_high = bandwidth_octaves = np.nan

        results.append({
            'horn': horn,
            'xo_freq': best_xo,
            'hf_pad': best_pad,
            'dip': best_dip,
            'flatness': flatness,
            'bandwidth_octaves': bandwidth_octaves,
            'system_response': system_response,
            'hf_response': hf_response + best_pad,
        })

        print(f"  Best XO: {best_xo:.0f} Hz ({best_xo/horn['fc_hz']:.2f}×Fc)")
        print(f"  HF padding: {best_pad:.1f} dB")
        print(f"  Dip in XO region: {best_dip:.2f} dB")
        print(f"  Overall flatness: {flatness:.2f} dB")
        print(f"  -3dB bandwidth: {bandwidth_octaves:.1f} octaves ({f_low:.0f}-{f_high:.0f} Hz)")

        # Rate the dip
        if best_dip < 1.5:
            rating = "✅ Excellent"
        elif best_dip < 2.5:
            rating = "✅ Good"
        elif best_dip < 4:
            rating = "⚠️  Acceptable"
        else:
            rating = "❌ Poor"

        print(f"  Rating: {rating}")

    # Create comparison plot
    print(f"\n{'='*80}")
    print("CREATING COMPARISON PLOT")
    print(f"{'='*80}")

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    # Plot 1: System responses
    ax1 = axes[0]

    colors = ['red', 'blue', 'green', 'orange']
    linestyles = ['-', '--', ':', '-.']

    for i, result in enumerate(results):
        label = (f"{result['horn']['name']}\n"
                f"XO: {result['xo_freq']:.0f}Hz, Dip: {result['dip']:.1f}dB")
        ax1.semilogx(freq, result['system_response'], color=colors[i], linewidth=2,
                    linestyle=linestyles[i], label=label)

    ax1.set_xlabel('Frequency (Hz)')
    ax1.set_ylabel('SPL (dB)')
    ax1.set_title('System Response Comparison: Different Mouth Sizes')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='lower left', fontsize=9)
    ax1.set_xlim(100, 20000)
    ax1.set_ylim(70, 100)

    # Plot 2: Dip comparison
    ax2 = axes[1]

    options = [r['horn']['name'] for r in results]
    dips = [r['dip'] for r in results]
    mouth_areas = [r['horn']['mouth_cm2'] for r in results]
    fcs = [r['horn']['fc_hz'] for r in results]

    x_pos = np.arange(len(options))
    bars = ax2.bar(x_pos, dips, color=['red' if d > 4 else 'orange' if d > 2 else 'green' for d in dips],
                   alpha=0.7, edgecolor='black')

    ax2.set_xlabel('Horn Option')
    ax2.set_ylabel('Dip at Crossover (dB)')
    ax2.set_title('Crossover Dip vs Mouth Size (Lower is Better)')
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels([f"{mouth_areas[i]:.0f} cm²\nFc={fcs[i]:.0f}Hz" for i in range(len(options))],
                       fontsize=9)
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.axhline(2, color='orange', linestyle='--', alpha=0.7, label='Good (2 dB)')
    ax2.axhline(4, color='red', linestyle='--', alpha=0.7, label='Poor (4 dB)')
    ax2.legend()

    # Add value labels on bars
    for i, (bar, dip) in enumerate(zip(bars, dips)):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{dip:.1f} dB', ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()

    # Save plot
    output_dir = Path(__file__).parent
    png_path = output_dir / "smaller_mouth_horn_comparison.png"
    pdf_path = output_dir / "smaller_mouth_horn_comparison.pdf"

    fig.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f"\n✓ PNG saved: {png_path}")
    fig.savefig(pdf_path, bbox_inches='tight')
    print(f"✓ PDF saved: {pdf_path}")

    # Save best design
    print(f"\n{'='*80}")
    print("RECOMMENDATION")
    print(f"{'='*80}")

    # Find best option (minimize dip, then maximize bandwidth)
    best_result = min(results, key=lambda x: (x['dip'], -x['bandwidth_octaves']))

    print(f"\n✅ BEST OPTION: {best_result['horn']['name']}")
    print(f"   Mouth: {best_result['horn']['mouth_cm2']:.0f} cm²")
    print(f"   Fc: {best_result['horn']['fc_hz']:.0f} Hz")
    print(f"   XO: {best_result['xo_freq']:.0f} Hz ({best_result['xo_freq']/best_result['horn']['fc_hz']:.2f}×Fc)")
    print(f"   Dip: {best_result['dip']:.2f} dB")
    print(f"   HF pad: {best_result['hf_pad']:.1f} dB")
    print(f"   Flatness: {best_result['flatness']:.2f} dB")
    print(f"   Bandwidth: {best_result['bandwidth_octaves']:.1f} octaves")

    # Save design
    design = {
        'lf_driver': 'BC_12FW88',
        'hf_driver': 'BC_DH450',
        'lf_enclosure': {
            'Vb_liters': lf_params['Vb'] * 1000,
            'Fb_hz': lf_params['Fb'],
        },
        'hf_horn_recommended': {
            'throat_area_cm2': best_result['horn']['throat_cm2'],
            'mouth_area_cm2': best_result['horn']['mouth_cm2'],
            'length_cm': best_result['horn']['length_cm'],
            'cutoff_hz': best_result['horn']['fc_hz'],
            'note': 'Smaller mouth for better crossover integration',
        },
        'crossover': {
            'frequency_hz': best_result['xo_freq'],
            'order': 4,
            'type': 'LR4',
            'hf_padding_db': best_result['hf_pad'],
        },
        'performance': {
            'dip_at_crossover_db': best_result['dip'],
            'flatness_db': best_result['flatness'],
            'bandwidth_octaves': best_result['bandwidth_octaves'],
        },
    }

    design_path = output_dir / "recommended_smaller_mouth_horn_design.json"
    with open(design_path, 'w') as f:
        json.dump(design, f, indent=2)

    print(f"\n✓ Design saved: {design_path}")

    # Compare with current
    current_result = results[0]  # 504 cm² mouth
    print(f"\n{'='*80}")
    print("COMPARISON: Current vs Recommended")
    print(f"{'='*80}")

    print(f"\n{'Metric':<25} {'Current':>15} {'Recommended':>15} {'Improvement':>15}")
    print("-" * 75)
    print(f"{'Mouth area':<25} {current_result['horn']['mouth_cm2']:>15.1f} {best_result['horn']['mouth_cm2']:>15.1f} {-((current_result['horn']['mouth_cm2'] - best_result['horn']['mouth_cm2']) / current_result['horn']['mouth_cm2'] * 100):>+14.1f}%")
    print(f"{'Horn Fc':<25} {current_result['horn']['fc_hz']:>15.0f} {best_result['horn']['fc_hz']:>15.0f} {-((current_result['horn']['fc_hz'] - best_result['horn']['fc_hz']) / current_result['horn']['fc_hz'] * 100):>+14.1f}%")
    print(f"{'XO frequency':<25} {current_result['xo_freq']:>15.0f} {best_result['xo_freq']:>15.0f} {-((current_result['xo_freq'] - best_result['xo_freq']) / current_result['xo_freq'] * 100):>+14.1f}%")
    print(f"{'Dip at XO':<25} {current_result['dip']:>15.2f} {best_result['dip']:>15.2f} {(current_result['dip'] - best_result['dip']):>+15.2f} dB")
    print(f"{'Flatness':<25} {current_result['flatness']:>15.2f} {best_result['flatness']:>15.2f} {(current_result['flatness'] - best_result['flatness']):>+15.2f} dB")
    print(f"{'Bandwidth':<25} {current_result['bandwidth_octaves']:>15.2f} {best_result['bandwidth_octaves']:>15.2f} {-((current_result['bandwidth_octaves'] - best_result['bandwidth_octaves']) / current_result['bandwidth_octaves'] * 100):>+14.1f}%")

    print("\n" + "=" * 80)

    return design


if __name__ == "__main__":
    main()
