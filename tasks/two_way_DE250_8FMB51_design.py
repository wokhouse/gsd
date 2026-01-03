#!/usr/bin/env python3
"""
Two-way speaker design: BC_DE250 (HF) + BC_8FMB51 (LF)

This script uses the DesignAssistant and CrossoverDesignAssistant to:
1. Design optimal enclosure for BC_8FMB51 LF driver
2. Design crossover between LF and HF drivers
3. Calculate and plot combined system response

Author: Claude Code
Date: 2025-12-31
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams

from gsd.driver import load_driver
from gsd.optimization.api.design_assistant import DesignAssistant
from gsd.optimization.api.crossover_assistant import CrossoverDesignAssistant
from gsd.enclosure.ported_box import (
    calculate_spl_ported_transfer_function,
    calculate_ported_box_system_parameters
)
from gsd.enclosure.sealed_box import (
    calculate_spl_from_transfer_function,
    calculate_sealed_box_system_parameters
)

# Configure plot for better appearance
rcParams['font.size'] = 10
rcParams['axes.labelsize'] = 11
rcParams['axes.titlesize'] = 12
rcParams['legend.fontsize'] = 9
rcParams['figure.titlesize'] = 13
rcParams['grid.alpha'] = 0.3


def calculate_lf_response_ported(driver, Vb, Fb, frequencies):
    """Calculate LF response (ported box)."""
    lf_response = np.array([
        calculate_spl_ported_transfer_function(f, driver, Vb, Fb)
        for f in frequencies
    ])
    return lf_response


def calculate_lf_response_sealed(driver, Vb, frequencies):
    """Calculate LF response (sealed box)."""
    lf_response = np.array([
        calculate_spl_from_transfer_function(f, driver, Vb)
        for f in frequencies
    ])
    return lf_response


def calculate_hf_response_datasheet_model(driver, horn_cutoff, frequencies):
    """
    Calculate HF response using datasheet sensitivity with modeled rolloff.

    DE250 datasheet: 108.5 dB @ 1m, 2.83V on horn
    """
    passband_sensitivity = 108.5  # dB @ 1m, 2.83V
    fc = horn_cutoff

    hf_response = np.zeros_like(frequencies)

    for i, f in enumerate(frequencies):
        if f > 5000:
            # HF beaming rolloff above 5 kHz (-3 dB/octave)
            hf_rolloff = 3 * np.log2(f / 5000)
            transition = 0.5 * (1 + np.tanh((f - 7000) / 1000))
            hf_response[i] = passband_sensitivity - hf_rolloff * transition
        elif f <= fc / 2:
            # Below cutoff: 12 dB/octave rolloff
            octaves_below = np.log2(max(f, 10) / fc)
            hf_response[i] = passband_sensitivity + octaves_below * 12
        elif f <= fc * 1.5:
            # Transition region (smooth rolloff from fc/2 to fc*1.5)
            # CORRECTED: blend goes from 0 to 1.0
            blend = (f - fc/2) / fc  # Was: (f - fc/2) / (fc/2)
            blend_smooth = blend * blend * (3 - 2 * blend)  # Smoothstep
            octaves_below = np.log2(max(f, 10) / fc)
            below_cutoff = passband_sensitivity + octaves_below * 12
            hf_response[i] = below_cutoff * (1 - blend_smooth) + passband_sensitivity * blend_smooth
        else:
            # Above cutoff (f > fc * 1.5): nominal sensitivity
            hf_response[i] = passband_sensitivity

    return hf_response


def apply_crossover_filters(lf_response, hf_response, frequencies, f_xo, lf_padding, hf_padding):
    """
    Apply Linkwitz-Riley 4th-order crossover filters (simplified model).
    """
    # Apply padding
    lf_padded = lf_response + lf_padding
    hf_padded = hf_response + hf_padding

    # Create smooth crossover blending using tanh
    xo_region_width = np.log10(f_xo * 2) - np.log10(f_xo / 2)
    log_freq = np.log10(frequencies)

    # Normalized position in crossover region (-1 to +1)
    normalized_pos = (log_freq - np.log10(f_xo)) / (xo_region_width / 2)

    # Smooth blend function (0 = LF only, 1 = HF only)
    blend = 0.5 * (1 + np.tanh(3 * normalized_pos))

    # Combine responses
    combined = (1 - blend) * lf_padded + blend * hf_padded

    return lf_padded, hf_padded, combined


def plot_two_way_response(frequencies, lf_response, hf_response, combined_response,
                           lf_driver, hf_driver, f_xo, f3_lf, design_params, enclosure_type):
    """Create the SPL plot."""
    fig, ax = plt.subplots(figsize=(12, 7))

    # Plot individual driver responses
    ax.semilogx(frequencies, lf_response, 'b-', linewidth=1.5, alpha=0.7,
                label=f'LF Driver ({lf_driver})')
    ax.semilogx(frequencies, hf_response, 'r-', linewidth=1.5, alpha=0.7,
                label=f'HF Driver ({hf_driver})')

    # Plot combined response
    ax.semilogx(frequencies, combined_response, 'k-', linewidth=2.5, label='Combined System')

    # Mark key frequencies
    passband_max = np.max(combined_response[frequencies > 100])

    # System F3 point
    f3_idx = np.where(combined_response < passband_max - 3)[0]
    if len(f3_idx) > 0:
        f3 = frequencies[f3_idx[0]]
        spl_f3 = combined_response[f3_idx[0]]
        ax.axvline(f3, color='gray', linestyle='--', alpha=0.5, linewidth=1)
        ax.text(f3*1.05, spl_f3, f'  System F3 = {f3:.1f} Hz', fontsize=9, color='gray')

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
    ax.set_title(f'Two-Way System SPL Response: {lf_driver} + {hf_driver}\n'
                 f'{enclosure_type}: Vb={design_params["Vb"]*1000:.1f}L, '
                 f'Fb={design_params["Fb"]:.1f}Hz, '
                 f'Horn fc={design_params["horn_fc"]:.0f}Hz')
    ax.grid(True, which='both', alpha=0.3)
    ax.legend(loc='lower left', framealpha=0.9)

    # Set axis limits
    ax.set_xlim(20, 20000)
    ax.set_ylim(40, 115)

    # Add frequency range markers
    ax.text(100, 110, 'Bass', fontsize=8, alpha=0.6)
    ax.text(500, 110, 'Mid-Bass', fontsize=8, alpha=0.6)
    ax.text(2000, 110, 'Midrange', fontsize=8, alpha=0.6)
    ax.text(8000, 110, 'Treble', fontsize=8, alpha=0.6)

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
    ranges = [(40, 200), (100, 500), (500, 5000), (100, 10000)]
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
    """Main design workflow."""
    print("=" * 80)
    print("TWO-WAY SPEAKER DESIGN: BC_DE250 + BC_8FMB51")
    print("=" * 80)
    print()

    # Driver names
    lf_driver_name = "BC_8FMB51"
    hf_driver_name = "BC_DE250"

    print("Step 1: Loading drivers...")
    lf_driver = load_driver(lf_driver_name)
    hf_driver = load_driver(hf_driver_name)

    print(f"\nLF Driver: {lf_driver_name}")
    print(f"  F_s: {lf_driver.F_s:.1f} Hz")
    print(f"  Q_ts: {lf_driver.Q_ts:.3f}")
    print(f"  V_as: {lf_driver.V_as*1000:.1f} L")
    print(f"  S_d: {lf_driver.S_d*10000:.0f} cm²")

    print(f"\nHF Driver: {hf_driver_name}")
    print(f"  F_s: {hf_driver.F_s:.1f} Hz")
    print(f"  Sensitivity (on horn): 108.5 dB")
    print()

    # Step 2: Design LF enclosure
    print("=" * 80)
    print("Step 2: LF Enclosure Design (using DesignAssistant)")
    print("=" * 80)

    design_assistant = DesignAssistant()

    # Get design recommendation
    # Note: BC_8FMB51 has Qts=0.275 which is very low, good for horns.
    # But for practical two-way, we'll use ported for better bass extension.
    rec = design_assistant.recommend_design(
        driver_name=lf_driver_name,
        objectives=["f3", "flatness", "size"],
        enclosure_preference="ported"  # Force ported for practical two-way design
    )

    print(f"\nRecommended enclosure type: {rec.enclosure_type}")
    print(f"Confidence: {rec.confidence:.2f}")
    print(f"\nReasoning:")
    print(rec.reasoning)
    print(f"\nSuggested parameters:")
    for param, value in rec.suggested_parameters.items():
        if param == "Vb":
            print(f"  Vb = {value*1000:.1f} L")
        elif param == "Fb":
            print(f"  Fb = {value:.1f} Hz")
        else:
            print(f"  {param} = {value}")

    print(f"\nExpected performance:")
    for key, value in rec.expected_performance.items():
        if key == "volume_liters":
            print(f"  {key}: {value:.1f} L")
        elif isinstance(value, float):
            print(f"  {key}: {value:.1f}")
        else:
            print(f"  {key}: {value}")

    # Use recommended parameters
    enclosure_type = rec.enclosure_type
    if enclosure_type == "ported":
        Vb = rec.suggested_parameters.get("Vb", lf_driver.V_as)
        Fb = rec.suggested_parameters.get("Fb", lf_driver.F_s)
        params = calculate_ported_box_system_parameters(lf_driver, Vb, Fb)
        f3_lf = params.F3
    else:  # sealed
        Vb = rec.suggested_parameters.get("Vb", lf_driver.V_as * 0.7)
        params = calculate_sealed_box_system_parameters(lf_driver, Vb)
        f3_lf = params.F3
        Fb = None

    print(f"\nLF F3: {f3_lf:.1f} Hz")
    print()

    # Step 3: Design crossover
    print("=" * 80)
    print("Step 3: Crossover Design (using CrossoverDesignAssistant)")
    print("=" * 80)

    xo_assistant = CrossoverDesignAssistant()

    # Build enclosure params dict
    lf_enclosure_params = {"Vb": Vb}
    if Fb:
        lf_enclosure_params["Fb"] = Fb

    # Design crossover
    xo_design = xo_assistant.design_crossover(
        lf_driver_name=lf_driver_name,
        hf_driver_name=hf_driver_name,
        lf_enclosure_type=enclosure_type,
        lf_enclosure_params=lf_enclosure_params,
        crossover_range=(500, 3000)
    )

    print(f"\nRecommended crossover frequency: {xo_design.crossover_frequency:.0f} Hz")
    print(f"Crossover order: {xo_design.crossover_order}th-order {xo_design.filter_type}")
    print(f"LF padding: {xo_design.lf_padding_db:.1f} dB")
    print(f"HF padding: {xo_design.hf_padding_db:.1f} dB")
    print(f"Estimated ripple: {xo_design.estimated_ripple:.1f} dB")

    if xo_design.horn_cutoff_fc:
        print(f"Horn cutoff frequency: {xo_design.horn_cutoff_fc:.0f} Hz")
    if xo_design.horn_length_m:
        print(f"Horn length: {xo_design.horn_length_m:.2f} m")

    print(f"\nAnalysis:")
    print(f"  Crossover points analyzed: {xo_design.analysis['crossover_points_analyzed']}")
    print(f"  Level mismatch at crossover: {xo_design.analysis['level_mismatch_at_xo']:.1f} dB")
    print(f"  Suitability score: {xo_design.analysis['suitability_score']:.1f}/100")
    print(f"  Reasoning: {xo_design.analysis['reasoning']}")

    print(f"\nTop 5 crossover candidates:")
    for i, candidate in enumerate(xo_design.analysis['all_candidates'][:5], 1):
        print(f"  {i}. {candidate['freq']:.0f} Hz - score: {candidate['score']:.1f}")
    print()

    # Extract design parameters
    f_xo = xo_design.crossover_frequency
    lf_padding = xo_design.lf_padding_db
    hf_padding = xo_design.hf_padding_db
    horn_fc = xo_design.horn_cutoff_fc if xo_design.horn_cutoff_fc else 800

    # Step 4: Calculate system response
    print("=" * 80)
    print("Step 4: Calculate System Response")
    print("=" * 80)

    # Generate frequency points
    frequencies = np.logspace(np.log10(20), np.log10(20000), 500)

    # Calculate LF response
    print(f"\nCalculating LF response ({enclosure_type})...")
    if enclosure_type == "ported":
        lf_response = calculate_lf_response_ported(lf_driver, Vb, Fb, frequencies)
    else:
        lf_response = calculate_lf_response_sealed(lf_driver, Vb, frequencies)

    # Calculate HF response
    print("Calculating HF response (using datasheet sensitivity)...")
    hf_response = calculate_hf_response_datasheet_model(hf_driver, horn_fc, frequencies)

    # Apply crossover
    print("Applying crossover filters...")
    lf_padded, hf_padded, combined = apply_crossover_filters(
        lf_response, hf_response, frequencies, f_xo, lf_padding, hf_padding
    )

    # Analyze metrics
    print("\nSystem Response Metrics:")
    metrics = analyze_response_metrics(frequencies, combined)
    print(f"  System F3: {metrics['f3']:.1f} Hz")
    print(f"  System F10: {metrics['f10']:.1f} Hz")
    print(f"  Max SPL: {metrics['max_spl']:.1f} dB")
    print(f"  Passband max: {metrics['passband_max']:.1f} dB")
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

    # Step 5: Create plot
    print("\n" + "=" * 80)
    print("Step 5: Generate Plots")
    print("=" * 80)

    design_params = {
        "Vb": Vb,
        "Fb": Fb if Fb else 0,
        "horn_fc": horn_fc
    }

    fig = plot_two_way_response(
        frequencies, lf_padded, hf_padded, combined,
        lf_driver_name, hf_driver_name, f_xo, f3_lf, design_params, enclosure_type
    )

    # Save plot
    output_path = "tasks/two_way_DE250_8FMB51_response.png"
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved to: {output_path}")

    pdf_path = "tasks/two_way_DE250_8FMB51_response.pdf"
    fig.savefig(pdf_path, bbox_inches='tight')
    print(f"PDF saved to: {pdf_path}")

    # Summary
    print("\n" + "=" * 80)
    print("DESIGN SUMMARY")
    print("=" * 80)
    print(f"\nLF Driver ({lf_driver_name}):")
    print(f"  Enclosure type: {enclosure_type}")
    print(f"  Vb: {Vb*1000:.1f} L")
    if Fb:
        print(f"  Fb: {Fb:.1f} Hz")
    print(f"  F3: {f3_lf:.1f} Hz")

    print(f"\nHF Driver ({hf_driver_name}):")
    print(f"  Horn cutoff: {horn_fc:.0f} Hz")
    if xo_design.horn_length_m:
        print(f"  Horn length: {xo_design.horn_length_m:.2f} m")

    print(f"\nCrossover:")
    print(f"  Frequency: {f_xo:.0f} Hz")
    print(f"  Type: {xo_design.crossover_order}th-order {xo_design.filter_type}")
    print(f"  LF padding: {lf_padding:.1f} dB")
    print(f"  HF padding: {hf_padding:.1f} dB")

    print(f"\nSystem Performance:")
    print(f"  F3: {metrics['f3']:.1f} Hz")
    print(f"  F10: {metrics['f10']:.1f} Hz")
    print(f"  Max SPL: {metrics['max_spl']:.1f} dB")
    print(f"  Flatness (100-10000 Hz): {metrics['flatness']['100-10000']:.2f} dB")

    print("\n" + "=" * 80)
    print("DESIGN COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
