#!/usr/bin/env python3
"""
Plot SPL response for the two-way system (flattest design option).

Author: Claude Code
Date: 2025-12-30
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams

from gsd.driver import load_driver
from gsd.enclosure.ported_box import calculate_spl_ported_transfer_function
from gsd.optimization.api.crossover_assistant import CrossoverDesignAssistant

# Configure plot for better appearance
rcParams['font.size'] = 10
rcParams['axes.labelsize'] = 11
rcParams['axes.titlesize'] = 12
rcParams['legend.fontsize'] = 9
rcParams['figure.titlesize'] = 13
rcParams['grid.alpha'] = 0.3


def calculate_lf_response(driver, Vb, Fb, frequencies):
    """Calculate LF response (ported box)."""
    lf_response = np.array([
        calculate_spl_ported_transfer_function(f, driver, Vb, Fb)
        for f in frequencies
    ])
    return lf_response


def calculate_hf_response_datasheet_model(driver, horn_cutoff, frequencies):
    """
    Calculate HF response using datasheet sensitivity with modeled rolloff.

    This is MORE ACCURATE than first-principles calculation when using
    approximate driver parameters, because it uses the manufacturer's
    measured sensitivity (108.5 dB for DE250).

    The physics-based T-matrix calculation is useful for horn profile
    optimization but not for absolute SPL prediction with estimated parameters.
    """
    # DE250 datasheet sensitivity
    passband_sensitivity = 108.5  # dB @ 1m, 2.83V
    fc = horn_cutoff

    hf_response = np.zeros_like(frequencies)

    for i, f in enumerate(frequencies):
        if f > 5000:
            # HF beaming rolloff above 5 kHz (-3 dB/octave)
            hf_rolloff = 3 * np.log2(f / 5000)
            # Smooth transition
            transition = 0.5 * (1 + np.tanh((f - 7000) / 1000))
            hf_response[i] = passband_sensitivity - hf_rolloff * transition

        elif f > fc * 1.5:
            # Above cutoff: nominal sensitivity
            hf_response[i] = passband_sensitivity

        elif f > fc / 2:
            # Transition region (smooth rolloff)
            blend = (f - fc/2) / (fc/2)
            blend_smooth = blend * blend * (3 - 2 * blend)  # Smoothstep

            # Below cutoff: 12 dB/octave rolloff
            octaves_below = np.log2(max(f, 10) / fc)
            below_cutoff = passband_sensitivity + octaves_below * 12

            # Blend smoothly
            hf_response[i] = below_cutoff * (1 - blend_smooth) + passband_sensitivity * blend_smooth

        else:
            # Below cutoff: 12 dB/octave rolloff
            octaves_below = np.log2(max(f, 10) / fc)
            hf_response[i] = passband_sensitivity + octaves_below * 12

    return hf_response


def apply_crossover_filters(lf_response, hf_response, frequencies, f_xo, lf_padding, hf_padding):
    """
    Apply Linkwitz-Riley 4th-order crossover filters.

    This is a simplified model - in practice, you'd use actual filter calculations.
    For visualization, we blend the responses smoothly around the crossover.
    """
    # Apply padding
    lf_padded = lf_response + lf_padding
    hf_padded = hf_response + hf_padding

    # Create smooth crossover blending
    # Use tanh for smooth transition (similar to LR4 summation)
    xo_region_width = np.log10(f_xo * 2) - np.log10(f_xo / 2)
    log_freq = np.log10(frequencies)

    # Normalized position in crossover region (-1 to +1)
    normalized_pos = (log_freq - np.log10(f_xo)) / (xo_region_width / 2)

    # Smooth blend function (0 = LF only, 1 = HF only)
    blend = 0.5 * (1 + np.tanh(3 * normalized_pos))

    # Combine responses
    combined = (1 - blend) * lf_padded + blend * hf_padded

    return lf_padded, hf_padded, combined


def plot_response(frequencies, lf_response, hf_response, combined_response,
                  f_xo, f3_lf, design_name):
    """Create the SPL plot."""
    fig, ax = plt.subplots(figsize=(12, 7))

    # Plot individual driver responses
    ax.semilogx(frequencies, lf_response, 'b-', linewidth=1.5, alpha=0.7, label='LF Driver (BC_10NW64)')
    ax.semilogx(frequencies, hf_response, 'r-', linewidth=1.5, alpha=0.7, label='HF Driver (BC_DE250)')

    # Plot combined response
    ax.semilogx(frequencies, combined_response, 'k-', linewidth=2.5, label='Combined System')

    # Mark key frequencies
    # F3 point
    passband_max = np.max(combined_response[frequencies > 100])
    f3_idx = np.where(combined_response < passband_max - 3)[0]
    if len(f3_idx) > 0:
        f3 = frequencies[f3_idx[0]]
        spl_f3 = combined_response[f3_idx[0]]
        ax.axvline(f3, color='gray', linestyle='--', alpha=0.5, linewidth=1)
        ax.text(f3*1.05, spl_f3, f'  F3 = {f3:.1f} Hz', fontsize=9, color='gray')

    # Crossover point
    xo_idx = np.argmin(np.abs(frequencies - f_xo))
    spl_xo = combined_response[xo_idx]
    ax.axvline(f_xo, color='purple', linestyle='--', alpha=0.5, linewidth=1.5)
    ax.text(f_xo*1.05, spl_xo + 2, f'  Crossover = {f_xo:.0f} Hz', fontsize=9, color='purple')

    # LF F3 point
    ax.axvline(f3_lf, color='blue', linestyle=':', alpha=0.5, linewidth=1)
    ax.text(f3_lf*1.05, passband_max - 5, f'  LF F3 = {f3_lf:.1f} Hz', fontsize=9, color='blue')

    # Formatting
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('SPL (dB) @ 1m, 2.83V')
    ax.set_title(f'Two-Way System SPL Response: {design_name}\n'
                 f'BC_10NW64 (Ported) + BC_DE250 (Horn)')
    ax.grid(True, which='both', alpha=0.3)
    ax.legend(loc='lower left', framealpha=0.9)

    # Set axis limits
    ax.set_xlim(20, 20000)
    ax.set_ylim(40, 110)

    # Add frequency range markers
    ax.text(100, 105, 'Bass', fontsize=8, alpha=0.6)
    ax.text(500, 105, 'Mid-Bass', fontsize=8, alpha=0.6)
    ax.text(2000, 105, 'Midrange', fontsize=8, alpha=0.6)
    ax.text(8000, 105, 'Treble', fontsize=8, alpha=0.6)

    plt.tight_layout()
    return fig


def analyze_response_metrics(frequencies, response):
    """Calculate response metrics."""
    # Find F3
    passband_max = np.max(response[frequencies > 100])
    f3_idx = np.where(response < passband_max - 3)[0]
    if len(f3_idx) > 0:
        f3 = frequencies[f3_idx[0]]
    else:
        f3 = frequencies[0]

    # Find F10
    f10_idx = np.where(response < passband_max - 10)[0]
    if len(f10_idx) > 0:
        f10 = frequencies[f10_idx[0]]
    else:
        f10 = frequencies[0]

    # Calculate flatness (std dev) over different ranges
    ranges = [(40, 200), (100, 500), (500, 5000)]
    flatness = {}
    for f_min, f_max in ranges:
        mask = (frequencies >= f_min) & (frequencies <= f_max)
        if np.sum(mask) > 0:
            flatness[f'{f_min}-{f_max}'] = np.std(response[mask])

    # Max SPL
    max_spl = np.max(response)

    return {
        'f3': f3,
        'f10': f10,
        'flatness': flatness,
        'max_spl': max_spl,
        'passband_max': passband_max
    }


def main():
    """Main plotting workflow."""
    print("=" * 70)
    print("PLOTTING TWO-WAY SYSTEM RESPONSE")
    print("Design: FLATTEST RESPONSE option")
    print("=" * 70)
    print()

    # Load drivers
    lf_driver = load_driver("BC_10NW64")
    hf_driver = load_driver("BC_DE250")

    # Flattest design parameters (from optimization results)
    Vb = 0.0265  # 26.5 L in m³
    Fb = 70.0    # Hz
    f3_lf = 64.9 # Hz

    # Horn parameters
    horn_cutoff = 480  # Hz (for DE250)

    # Crossover parameters
    f_xo = 800      # Hz
    lf_padding = 0.0  # dB
    # HF padding: DE250 is 108.5 dB, LF is ~91 dB → need ~17.5 dB attenuation
    hf_padding = -17.5 # dB (corrected from -4.3 dB)

    print(f"Design Parameters:")
    print(f"  Vb = {Vb*1000:.1f} L")
    print(f"  Fb = {Fb:.1f} Hz")
    print(f"  Horn cutoff = {horn_cutoff:.0f} Hz")
    print(f"  Crossover = {f_xo:.0f} Hz")
    print(f"  HF padding = {hf_padding:.1f} dB")
    print()

    # Generate frequency points
    frequencies = np.logspace(np.log10(20), np.log10(20000), 500)

    # Calculate LF response
    print("Calculating LF response...")
    lf_response = calculate_lf_response(lf_driver, Vb, Fb, frequencies)

    # Calculate HF response using datasheet model (more accurate!)
    print("Calculating HF response (using datasheet sensitivity)...")
    hf_response = calculate_hf_response_datasheet_model(hf_driver, horn_cutoff, frequencies)

    # Note: We're NOT using first-principles T-matrix calculation because:
    # - Driver parameters are approximate, not measured
    # - Results are 9.1 dB lower than datasheet
    # - Physics model is useful for horn optimization, not SPL prediction

    # Apply crossover
    print("Applying crossover filters...")
    lf_padded, hf_padded, combined = apply_crossover_filters(
        lf_response, hf_response, frequencies, f_xo, lf_padding, hf_padding
    )

    # Analyze metrics
    metrics = analyze_response_metrics(frequencies, combined)

    print("\nResponse Metrics:")
    print(f"  System F3: {metrics['f3']:.1f} Hz")
    print(f"  System F10: {metrics['f10']:.1f} Hz")
    print(f"  Max SPL: {metrics['max_spl']:.1f} dB")
    print("\n  Flatness (standard deviation):")
    for range_name, std_dev in metrics['flatness'].items():
        print(f"    {range_name} Hz: {std_dev:.2f} dB")

    # Sample key frequencies
    print("\n  Sample Response:")
    key_freqs = [30, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
    print(f"    {'Freq':>8} | {'LF':>6} | {'HF':>6} | {'Combined':>8}")
    print("    " + "-" * 38)
    for f in key_freqs:
        idx = np.argmin(np.abs(frequencies - f))
        lf = lf_padded[idx]
        hf = hf_padded[idx]
        comb = combined[idx]
        print(f"    {f:>8.0f} | {lf:>6.1f} | {hf:>6.1f} | {comb:>8.1f}")

    # Create plot
    print("\nCreating plot...")
    fig = plot_response(
        frequencies, lf_padded, hf_padded, combined,
        f_xo, f3_lf,
        design_name="Flattest Response (Vb=26.5L, Fb=70Hz) - CORRECTED"
    )

    # Save plot
    output_path = "tasks/two_way_flattest_response.png"
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Plot saved to: {output_path}")

    # Also save PDF for higher quality
    pdf_path = "tasks/two_way_flattest_response.pdf"
    fig.savefig(pdf_path, bbox_inches='tight')
    print(f"PDF saved to: {pdf_path}")

    print("\n" + "=" * 70)
    print("PLOTTING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
