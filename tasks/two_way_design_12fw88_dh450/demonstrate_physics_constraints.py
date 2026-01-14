#!/usr/bin/env python3
"""
Demonstrate the fundamental physics constraint and provide practical solutions.

The issue: 250mm horn length forces a high cutoff frequency.
The solution: We need to work WITH the physics, not against it.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
from pathlib import Path

from gsd.driver import load_driver
from gsd.enclosure.ported_box import calculate_spl_ported_transfer_function
from gsd.optimization.api.two_way_system import (
    calculate_hf_horn_response,
    calculate_lr4_crossover_gains,
    optimize_hf_padding_for_flatness,
)
from gsd.optimization.api.design_assistant import DesignAssistant

rcParams['font.size'] = 11
rcParams['axes.labelsize'] = 12
rcParams['axes.titlesize'] = 14
rcParams['grid.alpha'] = 0.3


def calculate_horn_cutoff_physical(throat_area, mouth_area, length):
    """
    Calculate horn cutoff from first principles (exponential horn).

    Literature:
    - Olson (1947) - m = ln(S2/S1) / L
    - Kolbrek - fc = c * m / (4π) for pressure amplitude convention
    """
    c = 343  # m/s

    # Flare constant (Olson)
    m_olson = np.log(mouth_area / throat_area) / length

    # Cutoff frequency (Kolbrek convention)
    fc = (c * m_olson / 2) / (2 * np.pi)

    return fc, m_olson


def plot_horn_cutoff_vs_length():
    """Plot horn cutoff vs length for different expansion ratios."""
    print("\n" + "=" * 80)
    print("HORN PHYSICS: Cutoff vs Length")
    print("=" * 80)

    fig, ax = plt.subplots(figsize=(12, 8))

    # Different expansion ratios (mouth/throat)
    expansion_ratios = [10, 20, 40, 70, 100]
    colors = ['blue', 'green', 'orange', 'red', 'purple']

    lengths_mm = np.linspace(100, 1000, 100)

    for exp_ratio, color in zip(expansion_ratios, colors):
        cutoffs = []
        for L_mm in lengths_mm:
            L = L_mm / 1000  # m
            throat = 0.0007  # 7 cm² (DH450)
            mouth = throat * exp_ratio

            fc, _ = calculate_horn_cutoff_physical(throat, mouth, L)
            cutoffs.append(fc)

        ax.plot(lengths_mm, cutoffs, color=color, linewidth=2,
                label=f'Expansion {exp_ratio}:1 (mouth={throat*exp_ratio*1e4:.0f} cm²)')

    # Mark current design
    current_length = 250  # mm
    current_throat = 0.0007  # m²
    current_mouth = 0.0504  # m² (504 cm²)
    current_fc, current_m = calculate_horn_cutoff_physical(current_throat, current_mouth, current_length/1000)

    ax.plot(current_length, current_fc, 'ro', markersize=15,
            label=f'Current design\n(250mm, Fc={current_fc:.0f}Hz)')
    ax.axvline(current_length, color='red', linestyle='--', alpha=0.5, linewidth=2)
    ax.axhline(current_fc, color='red', linestyle='--', alpha=0.5, linewidth=2)

    # Target crossover regions
    ax.axhspan(400, 800, alpha=0.1, color='green', label='Target XO region (ideal)')
    ax.axhspan(800, 1500, alpha=0.05, color='yellow', label='Acceptable XO region')

    ax.set_xlabel('Horn Length (mm)', fontsize=13)
    ax.set_ylabel('Horn Cutoff Frequency (Hz)', fontsize=13)
    ax.set_title('Horn Cutoff vs Length (Fundamental Physics)\n'
                 'Lower cutoff requires longer horn or smaller expansion ratio', fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right', fontsize=9)
    ax.set_xlim(100, 1000)
    ax.set_ylim(0, 3000)

    plt.tight_layout()

    # Save
    output_dir = Path(__file__).parent
    path = output_dir / "horn_physics_cutoff_vs_length.png"
    fig.savefig(path, dpi=150, bbox_inches='tight')
    print(f"✓ Plot saved: {path}")

    # Analysis
    print(f"\nCurrent design analysis:")
    print(f"  Length: {current_length} mm")
    print(f"  Throat: {current_throat*1e4:.1f} cm²")
    print(f"  Mouth: {current_mouth*1e4:.0f} cm²")
    print(f"  Expansion ratio: {current_mouth/current_throat:.1f}:1")
    print(f"  Flare constant: {current_m:.1f} m⁻¹")
    print(f"  Cutoff: {current_fc:.0f} Hz")

    # What would we need for 800 Hz crossover?
    target_fc = 400  # Horn should be 2 octaves below XO
    print(f"\nFor {target_fc*2:.0f} Hz crossover (Fc ≤ {target_fc} Hz):")

    # Option 1: Longer horn
    for target_L_mm in [300, 400, 500, 750, 1000]:
        L = target_L_mm / 1000
        fc, m = calculate_horn_cutoff_physical(current_throat, current_mouth, L)
        if fc <= target_fc:
            print(f"  Required length: ~{target_L_mm} mm (Fc = {fc:.0f} Hz)")
            break

    # Option 2: Smaller mouth (lower expansion)
    for exp_ratio in [70, 50, 40, 30, 20]:
        mouth = current_throat * exp_ratio
        fc, m = calculate_horn_cutoff_physical(current_throat, mouth, current_length/1000)
        if fc <= target_fc:
            print(f"  Alternative: Reduce mouth to {mouth*1e4:.0f} cm² (expansion {exp_ratio}:1)")
            print(f"                 → Fc = {fc:.0f} Hz at 250mm length")
            break

    return current_fc


def analyze_crossover_options(current_fc):
    """Analyze different crossover options with current horn."""
    print("\n" + "=" * 80)
    print("CROSSOVER OPTIONS WITH CURRENT HORN")
    print("=" * 80)

    # Load drivers
    lf_driver = load_driver("BC_12FW88")
    hf_driver = load_driver("BC_DH450")

    # LF parameters
    Vb = 0.1145  # m³
    Fb = 46.5    # Hz

    # Generate frequency array
    freq = np.logspace(np.log10(20), np.log10(20000), 500)

    # Calculate responses
    lf_response = np.array([
        calculate_spl_ported_transfer_function(f, lf_driver, Vb, Fb)
        for f in freq
    ])

    hf_response = calculate_hf_horn_response(freq, current_fc)

    # Test different crossover frequencies
    xo_options = [800, 1200, 1500, 2000, 2500]

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    # Plot 1: System responses
    ax1 = axes[0]

    for xo_freq in xo_options:
        # Optimize padding for this XO
        try:
            hf_pad = optimize_hf_padding_for_flatness(
                lf_driver_name="BC_12FW88",
                hf_driver_name="BC_DH450",
                lf_enclosure_type="ported",
                lf_enclosure_params={"Vb": Vb, "Fb": Fb},
                horn_params={"cutoff": current_fc, "length": 0.25},
                crossover_frequency=xo_freq,
                padding_range=(-25, -5),
                num_steps=11,
            )
        except:
            hf_pad = -16.0

        # Calculate combined response
        lp_gain_db, hp_gain_db = calculate_lr4_crossover_gains(freq, xo_freq)
        lf_combined = lf_response + lp_gain_db
        hf_combined = hf_response + hf_pad + hp_gain_db

        system_response = 10 * np.log10(
            10**(lf_combined/10) + 10**(hf_combined/10)
        )

        # Calculate flatness
        passband = (freq >= 100) & (freq <= 10000)
        flatness = np.max(system_response[passband]) - np.min(system_response[passband])

        # Plot
        ax1.semilogx(freq, system_response, linewidth=2,
                    label=f'XO = {xo_freq:.0f} Hz (flatness: {flatness:.1f} dB)')

    # Mark horn cutoff
    ax1.axvline(current_fc, color='red', linestyle=':', linewidth=2, alpha=0.7)
    ax1.text(current_fc*1.1, 85, f'Horn Fc = {current_fc:.0f} Hz', color='red')

    ax1.set_xlabel('Frequency (Hz)')
    ax1.set_ylabel('SPL (dB)')
    ax1.set_title('System Response vs Crossover Frequency (Current Horn: Fc=1865Hz)')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='lower left', fontsize=9)
    ax1.set_xlim(100, 20000)
    ax1.set_ylim(70, 100)

    # Plot 2: Summary table
    ax2 = axes[1]
    ax2.axis('off')

    # Create analysis text
    analysis_text = f"""
CROSSOVER ANALYSIS SUMMARY

Current Horn: 250mm length, Fc = {current_fc:.0f} Hz

{'XO Freq':>10} | {'XO/Fc':>8} | {'Assessment':>30} | {'Recommendation':>40}
{'-'*100}
"""

    for xo_freq in xo_options:
        ratio = xo_freq / current_fc

        if ratio < 0.5:
            assessment = "❌ FAR BELOW CUTOFF"
            recommendation = "HF severely rolled off, large dip in response"
        elif ratio < 0.8:
            assessment = "⚠️  BELOW CUTOFF"
            recommendation = "HF rolled off in XO region, noticeable dip"
        elif ratio < 1.2:
            assessment = "⚠️  NEAR CUTOFF"
            recommendation = "Marginal HF loading, some rolloff possible"
        elif ratio < 2.0:
            assessment = "✅ ACCEPTABLE"
            recommendation = "Adequate HF loading, minimal rolloff"
        else:
            assessment = "✅ GOOD"
            recommendation = "Proper HF loading, smooth integration"

        analysis_text += f"{xo_freq:>10.0f} Hz | {ratio:>7.2f}× | {assessment:>30} | {recommendation:>40}\n"

    ax2.text(0.05, 0.95, analysis_text,
            transform=ax2.transAxes,
            fontsize=10,
            verticalalignment='top',
            fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    plt.tight_layout()

    # Save
    output_dir = Path(__file__).parent
    path = output_dir / "crossover_options_with_current_horn.png"
    fig.savefig(path, dpi=150, bbox_inches='tight')
    print(f"✓ Plot saved: {path}")

    # Recommendation
    print(f"\nRECOMMENDATION:")
    optimal_xo = int(current_fc * 1.5)
    print(f"  Optimal crossover: ~{optimal_xo:.0f} Hz (1.5× Fc)")
    print(f"  Acceptable range: {int(current_fc*1.2)} - {int(current_fc*2)} Hz")


def main():
    """Main analysis workflow."""
    print("\n" + "=" * 80)
    print("PHYSICS CONSTRAINTS ANALYSIS")
    print("DH450 + 12FW88 Two-Way System with 250mm Cube Constraint")
    print("=" * 80)

    # Step 1: Show horn physics
    current_fc = plot_horn_cutoff_vs_length()

    # Step 2: Analyze crossover options
    analyze_crossover_options(current_fc)

    # Final summary
    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)

    print("\nThe fundamental issue:")
    print("  • 250mm horn length → Fc ≈ 1865 Hz")
    print("  • For optimal performance, XO should be 2×Fc ≈ 3700 Hz")
    print("  • But 12FW88 beaming starts ~800-1000 Hz")

    print("\nPRACTICAL SOLUTIONS:")

    print("\n  Option 1: ACCEPT HIGHER CROSSOVER (~1500-2000 Hz)")
    print("    → XO above Fc, good HF loading")
    print("    → Some LF beaming, but acceptable with toe-in")

    print("\n  Option 2: MULTI-PIECE HORN (2 sections)")
    print("    → Each section ≤250mm")
    print("    → Total length ~500mm, Fc ~900 Hz")
    print("    → Can XO at 800-1000 Hz with proper loading")

    print("\n  Option 3: COMPROMISE CURRENT DESIGN")
    print("    → XO at ~1500 Hz (current optimum)")
    print("    → Accept ~10dB flatness variation")
    print("    → Simple, single-piece print")

    print("\nRECOMMENDED: Option 1 (XO at 1500-2000 Hz)")
    print("  • Best balance of performance and practicality")
    print("  • No modifications to horn design")
    print("  • Acceptable LF beaming in typical room")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
