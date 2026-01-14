#!/usr/bin/env python3
"""
Plot the final optimized system response.

Shows:
- System response with optimized horn (250cm²) at 600 Hz crossover
- LF and HF individual responses
- Crossover region detail
- Comparison with original design
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
    calculate_system_flatness,
    calculate_f3_frequency,
)

rcParams['font.size'] = 11
rcParams['axes.labelsize'] = 12
rcParams['axes.titlesize'] = 14
rcParams['grid.alpha'] = 0.3


def main():
    """Plot final system response."""
    print("\n" + "=" * 80)
    print("FINAL SYSTEM RESPONSE PLOT")
    print("=" * 80)

    # Load optimized system design
    with open(Path(__file__).parent / "final_optimized_system_optimal_xo.json") as f:
        design = json.load(f)

    # Load original design for comparison
    with open(Path(__file__).parent / "recommended_smaller_mouth_horn_design.json") as f:
        original_design = json.load(f)

    # Extract parameters
    lf_vb = design['lf_enclosure']['Vb_liters'] / 1000
    lf_fb = design['lf_enclosure']['Fb_hz']
    horn_fc = design['horn_performance']['cutoff_hz']
    xo_freq = design['crossover']['frequency_hz']
    hf_pad = design['crossover']['hf_padding_db']

    print(f"\nOptimized system:")
    print(f"  LF: {lf_vb*1000:.1f}L @ {lf_fb:.1f}Hz")
    print(f"  HF horn: {design['hf_horn']['mouth_area_cm2']:.0f}cm², Fc={horn_fc:.0f}Hz")
    print(f"  Crossover: {xo_freq}Hz (LR4, HF pad={hf_pad}dB)")

    # Calculate responses
    lf_driver = load_driver("BC_12FW88")
    freq = np.logspace(np.log10(20), np.log10(20000), 1000)

    # LF response
    lf_response = np.array([
        calculate_spl_ported_transfer_function(f, lf_driver, lf_vb, lf_fb)
        for f in freq
    ])

    # HF response (optimized horn)
    hf_response_optimized = calculate_hf_horn_response(freq, horn_fc)

    # Original HF response for comparison
    horn_fc_original = 1865  # Hz (from original 504cm² mouth)
    hf_response_original = calculate_hf_horn_response(freq, horn_fc_original)

    # Calculate system responses
    lp_gain_db, hp_gain_db = calculate_lr4_crossover_gains(freq, xo_freq)

    # Optimized system
    lf_combined_opt = lf_response + lp_gain_db
    hf_combined_opt = (hf_response_optimized + hf_pad) + hp_gain_db
    system_response_opt = 10 * np.log10(10**(lf_combined_opt/10) + 10**(hf_combined_opt/10))

    # Original system (2238 Hz crossover with -16 dB pad)
    xo_freq_original = 2238
    lp_gain_orig, hp_gain_orig = calculate_lr4_crossover_gains(freq, xo_freq_original)
    lf_combined_orig = lf_response + lp_gain_orig
    hf_combined_orig = (hf_response_original - 16) + hp_gain_orig
    system_response_orig = 10 * np.log10(10**(lf_combined_orig/10) + 10**(hf_combined_orig/10))

    # Calculate metrics
    flatness_opt = calculate_system_flatness(freq, system_response_opt)
    f3_opt = calculate_f3_frequency(freq, system_response_opt)

    # Crossover region dip (optimized)
    xo_region = (freq >= xo_freq/2) & (freq <= xo_freq*2)
    xo_spl = system_response_opt[xo_region]
    dip_opt = np.max(xo_spl) - np.min(xo_spl)

    print(f"\nPerformance metrics:")
    print(f"  Flatness: {flatness_opt:.2f} dB")
    print(f"  F3: {f3_opt:.0f} Hz")
    print(f"  Dip at XO: {dip_opt:.2f} dB")

    # Create comprehensive plot
    print(f"\n{'='*80}")
    print("CREATING PLOT")
    print(f"{'='*80}")

    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 2, hspace=0.35, wspace=0.3)

    # Plot 1: Full system response comparison
    ax1 = fig.add_subplot(gs[0, :])

    ax1.semilogx(freq, system_response_orig, 'r--', linewidth=2, alpha=0.6,
                label=f'Original: XO={xo_freq_original}Hz, Dip=13.8dB')
    ax1.semilogx(freq, system_response_opt, 'g-', linewidth=2.5,
                label=f'Optimized: XO={xo_freq}Hz, Dip={dip_opt:.1f}dB')

    # F3 lines
    ax1.axvline(f3_opt, color='blue', linestyle=':', alpha=0.5, label=f'F3: {f3_opt:.0f} Hz')

    # -3dB band
    passband_max = np.max(system_response_opt[(freq >= 100) & (freq <= 10000)])
    threshold = passband_max - 3
    ax1.axhline(threshold, color='gray', linestyle=':', alpha=0.3, linewidth=1)
    ax1.text(freq[np.argmin(np.abs(system_response_opt - threshold))], threshold,
            f' -3dB', fontsize=9, alpha=0.7)

    # Crossover markers
    ax1.axvline(xo_freq_original, color='red', linestyle=':', alpha=0.4, linewidth=1)
    ax1.axvline(xo_freq, color='green', linestyle=':', alpha=0.6, linewidth=1)

    ax1.set_xlabel('Frequency (Hz)', fontsize=12)
    ax1.set_ylabel('SPL (dB)', fontsize=12)
    ax1.set_title('System Response Comparison: Original vs Optimized Horn', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='lower left', fontsize=10, framealpha=0.9)
    ax1.set_xlim(20, 20000)
    ax1.set_ylim(40, 105)

    # Plot 2: LF and HF individual responses (optimized)
    ax2 = fig.add_subplot(gs[1, 0])

    ax2.semilogx(freq, lf_response, 'b-', linewidth=1.5, alpha=0.7, label='LF raw (12FW88)')
    ax2.semilogx(freq, hf_response_optimized + hf_pad, 'r-', linewidth=1.5, alpha=0.7,
                label=f'HF raw (DH450 + {hf_pad}dB pad)')
    ax2.semilogx(freq, lf_combined_opt, 'b--', linewidth=2, alpha=0.5, label='LF filtered')
    ax2.semilogx(freq, hf_combined_opt, 'r--', linewidth=2, alpha=0.5, label='HF filtered')
    ax2.semilogx(freq, system_response_opt, 'g-', linewidth=2.5, label='System')

    ax2.axvline(xo_freq, color='gray', linestyle='--', alpha=0.5, label=f'XO: {xo_freq} Hz')
    ax2.axvline(horn_fc, color='orange', linestyle=':', alpha=0.5, label=f'Horn Fc: {horn_fc:.0f} Hz')

    ax2.set_xlabel('Frequency (Hz)', fontsize=11)
    ax2.set_ylabel('SPL (dB)', fontsize=11)
    ax2.set_title('Optimized System: Individual Driver Responses', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='lower left', fontsize=9)
    ax2.set_xlim(100, 20000)
    ax2.set_ylim(60, 105)

    # Plot 3: Crossover region detail (optimized)
    ax3 = fig.add_subplot(gs[1, 1])

    xo_zoom = (freq >= xo_freq/3) & (freq <= xo_freq*3)
    freq_xo = freq[xo_zoom]
    lf_xo = lf_combined_opt[xo_zoom]
    hf_xo = hf_combined_opt[xo_zoom]
    sys_xo = system_response_opt[xo_zoom]

    ax3.semilogx(freq_xo, lf_xo, 'b-', linewidth=2, alpha=0.6, label='LF (after LP)')
    ax3.semilogx(freq_xo, hf_xo, 'r-', linewidth=2, alpha=0.6, label='HF (after HP)')
    ax3.semilogx(freq_xo, sys_xo, 'g-', linewidth=3, label='System')

    ax3.axvline(xo_freq, color='gray', linestyle='--', alpha=0.7, linewidth=1.5, label=f'XO: {xo_freq} Hz')

    # Mark dip
    min_idx = np.argmin(sys_xo)
    ax3.plot(freq_xo[min_idx], sys_xo[min_idx], 'ro', markersize=10,
            label=f'Dip: {dip_opt:.1f} dB')

    ax3.fill_between(freq_xo, np.min(sys_xo), np.max(sys_xo),
                    where=(freq_xo >= xo_freq/2) & (freq_xo <= xo_freq*2),
                    alpha=0.2, color='gray', label='XO region (±1 oct)')

    ax3.set_xlabel('Frequency (Hz)', fontsize=11)
    ax3.set_ylabel('SPL (dB)', fontsize=11)
    ax3.set_title(f'Crossover Region Detail ({xo_freq//3:.0f}-{xo_freq*3:.0f} Hz)', fontsize=12)
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc='lower left', fontsize=9)

    # Plot 4: Horn comparison
    ax4 = fig.add_subplot(gs[2, 0])

    ax4.semilogx(freq, hf_response_original, 'r-', linewidth=2, alpha=0.7,
                label=f'Original horn: 504cm², Fc={horn_fc_original:.0f}Hz')
    ax4.semilogx(freq, hf_response_optimized, 'g-', linewidth=2, alpha=0.7,
                label=f'Optimized horn: 250cm², Fc={horn_fc:.0f}Hz')
    ax4.axvline(xo_freq_original, color='red', linestyle=':', alpha=0.5,
                label=f'Original XO: {xo_freq_original} Hz')
    ax4.axvline(xo_freq, color='green', linestyle=':', alpha=0.7,
                label=f'Optimized XO: {xo_freq} Hz')

    ax4.set_xlabel('Frequency (Hz)', fontsize=11)
    ax4.set_ylabel('HF SPL (dB)', fontsize=11)
    ax4.set_title('Horn Response Comparison (raw, before padding)', fontsize=12)
    ax4.grid(True, alpha=0.3)
    ax4.legend(loc='lower left', fontsize=9)
    ax4.set_xlim(100, 20000)

    # Plot 5: Performance metrics summary
    ax5 = fig.add_subplot(gs[2, 1])
    ax5.axis('off')

    # Metrics text
    metrics_text = f"""
OPTIMIZED SYSTEM METRICS

Horn Design:
  • Mouth area: {design['hf_horn']['mouth_area_cm2']:.0f} cm² (-50.4% vs original)
  • Horn Fc: {horn_fc:.0f} Hz (-74.9% vs original)
  • Length: {design['hf_horn']['total_length_cm']:.0f} cm ({design['hf_horn']['total_length_cm']*10:.0f} mm)

Crossover:
  • Frequency: {xo_freq} Hz (1.28×Fc)
  • Type: LR4 (4th-order Linkwitz-Riley)
  • HF padding: {hf_pad} dB

Performance:
  • Crossover dip: {dip_opt:.2f} dB ✓ (was 13.75 dB)
  • Flatness: {flatness_opt:.2f} dB ✓ (was 11.36 dB)
  • System F3: {f3_opt:.0f} Hz (maintained)
  • Rating: ⚠️ Acceptable (borderline Good)

Improvement vs Original:
  • Dip reduced: 13.75 → {dip_opt:.1f} dB (+{13.75-dip_opt:.1f} dB)
  • Flatness: 11.36 → {flatness_opt:.1f} dB (+{11.36-flatness_opt:.1f} dB)
  • XO frequency: 2238 → {xo_freq} Hz (-{2238-xo_freq} Hz)
    """

    ax5.text(0.05, 0.95, metrics_text, transform=ax5.transAxes,
            fontsize=10, verticalalignment='top', family='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    # Save
    output_dir = Path(__file__).parent
    png_path = output_dir / "final_system_response.png"
    pdf_path = output_dir / "final_system_response.pdf"

    fig.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f"\n✓ PNG saved: {png_path}")
    fig.savefig(pdf_path, bbox_inches='tight')
    print(f"✓ PDF saved: {pdf_path}")

    print("\n" + "=" * 80)
    print("PLOT CREATED")
    print("=" * 80)
    print("\nThe plot shows:")
    print("  1. Overall system response (original vs optimized)")
    print("  2. Individual driver responses (optimized system)")
    print("  3. Crossover region detail")
    print("  4. Horn response comparison")
    print("  5. Performance metrics summary")
    print("=" * 80)


if __name__ == "__main__":
    main()
