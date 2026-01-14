#!/usr/bin/env python3
"""
Plot system response for DH450 + 12FW88 two-way system.

Shows LF response, HF response, combined system response,
F3 markers, and -3dB flatness band from system peak.
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
    calculate_f3_frequency,
)

# Configure plot for better appearance
rcParams['font.size'] = 11
rcParams['axes.labelsize'] = 12
rcParams['axes.titlesize'] = 14
rcParams['legend.fontsize'] = 10
rcParams['figure.titlesize'] = 16
rcParams['grid.alpha'] = 0.3
rcParams['lines.linewidth'] = 2


def load_design_params():
    """Load design parameters from JSON file."""
    design_path = Path(__file__).parent / "design_summary_250mm_cube.json"

    if not design_path.exists():
        raise FileNotFoundError(f"Design file not found: {design_path}")

    with open(design_path) as f:
        design = json.load(f)

    return design


def calculate_f3_for_response(freq, response, passband_range=(80, 200)):
    """
    Calculate F3 (-3dB frequency) for a response.

    Finds frequency where response drops 3dB below passband maximum.
    """
    # Define passband
    passband = (freq >= passband_range[0]) & (freq <= passband_range[1])

    if not np.any(passband):
        return np.nan

    # Find passband maximum
    passband_max = np.max(response[passband])
    threshold = passband_max - 3

    # Find F3 crossing (linear interpolation)
    below_threshold = response < threshold

    if not np.any(below_threshold):
        return np.nan

    for i in range(len(freq) - 1):
        if response[i] < threshold and response[i + 1] >= threshold:
            f1, f2 = freq[i], freq[i + 1]
            r1, r2 = response[i], response[i + 1]
            # Linear interpolation
            f3 = f1 + (threshold - r1) * (f2 - f1) / (r2 - r1)
            return f3

    return np.nan


def calculate_system_flatness_region(freq, system_response, peak_db=-3):
    """
    Calculate the frequency range where response is within peak_db of system peak.

    Returns (f_low, f_high) defining the flatness band.
    """
    # Find system maximum (in relevant range 100-10000 Hz)
    mask = (freq >= 100) & (freq <= 10000)
    system_max = np.max(system_response[mask])
    threshold = system_max + peak_db  # -3 dB means 3 dB below max

    # Find lower frequency bound (below max)
    above_threshold = system_response > threshold
    above_idx = np.where(above_threshold)[0]

    if len(above_idx) == 0:
        return np.nan, np.nan

    f_low = freq[above_idx[0]]
    f_high = freq[above_idx[-1]]

    return f_low, f_high, system_max, threshold


def main():
    """Main plotting workflow."""
    print("=" * 80)
    print("PLOTTING SYSTEM RESPONSE: DH450 + 12FW88")
    print("=" * 80)

    # Load design parameters
    print("\nLoading design parameters...")
    design = load_design_params()

    lf_driver_name = design["lf_driver"]
    hf_driver_name = design["hf_driver"]

    # Extract parameters
    Vb = design["lf_enclosure"]["Vb_liters"] / 1000  # Convert L to m³
    Fb = design["lf_enclosure"]["Fb_hz"]
    horn_fc = design["hf_horn"]["cutoff_hz"]
    xo_freq = design["crossover"]["frequency_hz"]
    hf_pad = design["crossover"]["hf_padding_db"]

    print(f"  LF: {lf_driver_name}, Vb={Vb*1000:.1f}L, Fb={Fb:.1f}Hz")
    print(f"  HF: {hf_driver_name}, Fc={horn_fc:.0f}Hz")
    print(f"  XO: {xo_freq:.0f}Hz, HF pad={hf_pad:.1f}dB")

    # Load drivers
    print("\nLoading drivers...")
    lf_driver = load_driver(lf_driver_name)
    hf_driver = load_driver(hf_driver_name)

    # Generate frequency array
    freq = np.logspace(np.log10(20), np.log10(20000), 500)

    # Calculate LF response (ported box)
    print("\nCalculating LF response...")
    lf_response = np.array([
        calculate_spl_ported_transfer_function(f, lf_driver, Vb, Fb)
        for f in freq
    ])

    # Calculate HF response (horn model)
    print("Calculating HF response...")
    hf_response_raw = calculate_hf_horn_response(freq, horn_fc)
    hf_response = hf_response_raw + hf_pad  # Apply HF padding

    # Calculate crossover gains
    print("Calculating crossover filters...")
    lp_gain_db, hp_gain_db = calculate_lr4_crossover_gains(freq, xo_freq)

    # Apply crossover
    lf_filtered = lf_response + lp_gain_db
    hf_filtered = hf_response + hp_gain_db

    # Combine (power sum)
    print("Calculating combined response...")
    system_response = 10 * np.log10(
        10**(lf_filtered/10) + 10**(hf_filtered/10)
    )

    # Calculate F3 frequencies
    print("\nCalculating F3 frequencies...")

    # LF F3 (using LF passband as reference)
    lf_f3 = calculate_f3_for_response(freq, lf_response, passband_range=(80, 200))
    print(f"  LF F3: {lf_f3:.1f} Hz")

    # HF F3 (using HF passband as reference)
    hf_f3 = calculate_f3_for_response(freq, hf_response, passband_range=(2000, 10000))
    print(f"  HF F3 (upper): {hf_f3:.1f} Hz")

    # System F3
    system_f3 = calculate_f3_for_response(freq, system_response, passband_range=(80, 200))
    print(f"  System F3: {system_f3:.1f} Hz")

    # Calculate flatness band
    print("\nCalculating -3dB flatness band...")
    f_low, f_high, system_max, threshold = calculate_system_flatness_region(
        freq, system_response, peak_db=-3
    )
    print(f"  System max: {system_max:.1f} dB")
    print(f"  -3dB threshold: {threshold:.1f} dB")
    print(f"  Flatness band: {f_low:.0f} - {f_high:.0f} Hz")
    print(f"  Bandwidth: {np.log2(f_high/f_low):.1f} octaves")

    # Create plot
    print("\nCreating plot...")
    fig, ax = plt.subplots(figsize=(14, 8))

    # Plot individual responses
    ax.semilogx(freq, lf_response, 'b-', linewidth=1.5, alpha=0.6,
                label=f'LF Driver ({lf_driver_name})')
    ax.semilogx(freq, hf_response, 'r-', linewidth=1.5, alpha=0.6,
                label=f'HF Driver ({hf_driver_name})')

    # Plot filtered responses
    ax.semilogx(freq, lf_filtered, 'b--', linewidth=1, alpha=0.4)
    ax.semilogx(freq, hf_filtered, 'r--', linewidth=1, alpha=0.4)

    # Plot combined system response
    ax.semilogx(freq, system_response, 'k-', linewidth=3, label='Combined System')

    # Mark F3 frequencies
    # LF F3
    if not np.isnan(lf_f3):
        f3_spl_lf = np.interp(lf_f3, freq, lf_response)
        ax.axvline(lf_f3, color='blue', linestyle=':', alpha=0.6, linewidth=1.5)
        ax.text(lf_f3*1.05, f3_spl_lf, f'  LF F3 = {lf_f3:.1f} Hz',
                fontsize=10, color='blue', fontweight='bold')

    # HF F3 (upper rolloff)
    if not np.isnan(hf_f3):
        f3_spl_hf = np.interp(hf_f3, freq, hf_response)
        ax.axvline(hf_f3, color='red', linestyle=':', alpha=0.6, linewidth=1.5)
        ax.text(hf_f3*0.85, f3_spl_hf + 2, f'HF F3 = {hf_f3:.0f} Hz  ',
                fontsize=10, color='red', fontweight='bold', ha='right')

    # System F3
    if not np.isnan(system_f3):
        f3_spl_sys = np.interp(system_f3, freq, system_response)
        ax.axvline(system_f3, color='gray', linestyle='--', alpha=0.7, linewidth=2)
        ax.text(system_f3*1.05, f3_spl_sys, f'  System F3 = {system_f3:.1f} Hz',
                fontsize=11, color='gray', fontweight='bold')

    # Crossover frequency
    xo_spl = np.interp(xo_freq, freq, system_response)
    ax.axvline(xo_freq, color='purple', linestyle='--', alpha=0.7, linewidth=1.5)
    ax.text(xo_freq*1.05, xo_spl + 3, f'  XO = {xo_freq:.0f} Hz',
            fontsize=10, color='purple')

    # Flatness band (shade region within -3dB of peak)
    if not np.isnan(f_low) and not np.isnan(f_high):
        # Find indices for shading
        idx_low = np.argmin(np.abs(freq - f_low))
        idx_high = np.argmin(np.abs(freq - f_high))

        # Shade the -3dB band
        ax.axvspan(f_low, f_high, alpha=0.15, color='green', label=f'-3dB Band ({f_low:.0f}-{f_high:.0f} Hz)')

        # Add text for flatness
        mid_freq = np.sqrt(f_low * f_high)  # Geometric mean
        ax.text(mid_freq, system_max - 1, f'-3dB Flatness Band\n({np.log2(f_high/f_low):.1f} octaves)',
                fontsize=9, color='green', ha='center',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.7))

    # System max line
    ax.axhline(system_max, color='green', linestyle='-', alpha=0.3, linewidth=1)
    ax.axhline(threshold, color='green', linestyle='--', alpha=0.3, linewidth=1,
               label=f'-3dB Threshold ({threshold:.1f} dB)')

    # Formatting
    ax.set_xlabel('Frequency (Hz)', fontsize=13)
    ax.set_ylabel('SPL (dB) @ 1m, 2.83V', fontsize=13)
    ax.set_title(f'Two-Way System Response: {lf_driver_name} + {hf_driver_name}\n'
                 f'Ported: Vb={Vb*1000:.1f}L, Fb={Fb:.1f}Hz | Horn: Fc={horn_fc:.0f}Hz | '
                 f'XO: {xo_freq:.0f}Hz (LR4)', fontsize=14)
    ax.grid(True, which='both', alpha=0.3)
    ax.legend(loc='lower left', framealpha=0.9, fontsize=10)

    # Set axis limits
    ax.set_xlim(20, 20000)
    ax.set_ylim(30, 115)

    # Add frequency range markers
    ax.text(30, 110, 'Bass', fontsize=8, alpha=0.5)
    ax.text(100, 110, 'Mid-Bass', fontsize=8, alpha=0.5)
    ax.text(500, 110, 'Midrange', fontsize=8, alpha=0.5)
    ax.text(3000, 110, 'Upper-Mid', fontsize=8, alpha=0.5)
    ax.text(8000, 110, 'Treble', fontsize=8, alpha=0.5)

    plt.tight_layout()

    # Save plot
    output_dir = Path(__file__).parent
    png_path = output_dir / "system_response_complete_with_f3_and_flatness.png"
    pdf_path = output_dir / "system_response_complete_with_f3_and_flatness.pdf"

    fig.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f"\n✓ PNG saved: {png_path}")

    fig.savefig(pdf_path, bbox_inches='tight')
    print(f"✓ PDF saved: {pdf_path}")

    # Print summary
    print("\n" + "=" * 80)
    print("PLOT SUMMARY")
    print("=" * 80)
    print(f"\nF3 Frequencies:")
    print(f"  LF Driver: {lf_f3:.1f} Hz")
    print(f"  HF Driver: {hf_f3:.0f} Hz (upper rolloff)")
    print(f"  System: {system_f3:.1f} Hz")
    print(f"\nFlatness:")
    print(f"  System Maximum: {system_max:.1f} dB")
    print(f"  -3dB Threshold: {threshold:.1f} dB")
    print(f"  Flatness Band: {f_low:.0f} - {f_high:.0f} Hz")
    print(f"  Bandwidth: {np.log2(f_high/f_low):.1f} octaves")
    print(f"\nCrossover:")
    print(f"  Frequency: {xo_freq:.0f} Hz")
    print(f"  Type: LR4 (4th-order Linkwitz-Riley)")
    print(f"  HF Padding: {hf_pad:.1f} dB")
    print("\n" + "=" * 80)

    return fig


if __name__ == "__main__":
    main()
