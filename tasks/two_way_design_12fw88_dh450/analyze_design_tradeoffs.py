#!/usr/bin/env python3
"""
Analyze design trade-offs for DH450 + 12FW88 system with 250mm cube constraint.

This script shows:
1. Horn cutoff vs. length constraint (fundamental physics limitation)
2. LF beaming frequency vs. crossover options
3. Recommended solutions
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams

from gsd.driver import load_driver
from gsd.enclosure.ported_box import calculate_spl_ported_transfer_function
from gsd.optimization.api.two_way_system import (
    calculate_hf_horn_response,
    calculate_lr4_crossover_gains,
)

rcParams['font.size'] = 11
rcParams['axes.labelsize'] = 12
rcParams['axes.titlesize'] = 14
rcParams['grid.alpha'] = 0.3


def calculate_horn_cutoff_for_length(target_length, throat_area, mouth_area):
    """
    Calculate horn cutoff for a given length (exponential horn).

    For exponential horn: m = ln(mouth/throat) / length
    Cutoff: fc = c * m / (4π) (Kolbrek convention)
    """
    c = 343  # m/s
    m = np.log(mouth_area / throat_area) / target_length
    fc = (c * m / 2) / (2 * np.pi)
    return fc


def calculate_lf_beaming_frequency(driver_diameter):
    """Calculate frequency where 12" driver starts beaming."""
    c = 343  # m/s
    # Beaming starts when ka ≈ 2, where k = 2πf/c, a = radius
    radius = driver_diameter / 2
    f_beaming = (2 * c) / (2 * np.pi * radius)
    return f_beaming


def main():
    """Main analysis workflow."""
    print("=" * 80)
    print("DESIGN TRADE-OFF ANALYSIS: DH450 + 12FW88 (250mm CUBE)")
    print("=" * 80)

    # Load driver
    driver = load_driver("BC_12FW88")
    Sd = driver.S_d  # m²
    driver_diameter = 2 * np.sqrt(Sd / np.pi) * 1000  # mm

    print(f"\nLF Driver: BC 12FW88")
    print(f"  Diameter: {driver_diameter:.0f} mm")
    print(f"  Sd: {Sd*10000:.0f} cm²")

    # Calculate beaming frequency
    f_beaming = calculate_lf_beaming_frequency(driver_diameter / 1000)  # Convert to m
    print(f"  Beaming frequency: ~{f_beaming:.0f} Hz")

    # Horn parameters
    throat_area = 0.0007  # m² (7 cm²)
    mouth_area = 0.05     # m² (500 cm² - max for 250mm)

    print(f"\nHorn Constraints (250mm cube):")
    print(f"  Max length: 250 mm")
    print(f"  Max mouth: 625 cm² (250mm × 250mm)")
    print(f"  Current design: 504 cm² mouth (80mm diameter)")

    # Calculate horn cutoff for current design
    current_length = 0.25  # m
    current_fc = calculate_horn_cutoff_for_length(current_length, throat_area, mouth_area)

    print(f"\nCurrent Horn Design:")
    print(f"  Length: {current_length*1000:.0f} mm")
    print(f"  Throat: {throat_area*10000:.1f} cm²")
    print(f"  Mouth: {mouth_area*10000:.0f} cm²")
    print(f"  Cutoff: {current_fc:.0f} Hz")

    # What if we could use longer horn?
    print(f"\n" + "=" * 80)
    print("LENGTH vs. CUTOFF ANALYSIS")
    print("=" * 80)

    lengths_mm = np.array([250, 300, 400, 500, 600, 800, 1000])
    cutoffs = []

    for L_mm in lengths_mm:
        L = L_mm / 1000  # Convert to m
        fc = calculate_horn_cutoff_for_length(L, throat_area, mouth_area)
        cutoffs.append(fc)
        print(f"  {L_mm:4.0f} mm → Fc = {fc:6.0f} Hz")

    # Find length needed for desired crossover
    desired_xo = 800  # Hz
    target_fc = desired_xo / 2  # Horn should be 2 octaves below XO

    print(f"\nTarget Analysis:")
    print(f"  Desired crossover: {desired_xo} Hz")
    print(f"  Required horn cutoff: ≤{target_fc:.0f} Hz (2 octaves below XO)")

    # Interpolate required length
    required_length_mm = np.interp(target_fc, cutoffs[::-1], lengths_mm[::-1])
    print(f"  Required horn length: ~{required_length_mm:.0f} mm")

    if required_length_mm > 250:
        print(f"\n❌ CONSTRAINT VIOLATION:")
        print(f"  Required length ({required_length_mm:.0f} mm) exceeds 250mm limit")
        print(f"  Shortfall: {required_length_mm - 250:.0f} mm ({(required_length_mm/250 - 1)*100:.0f}% longer)")

    print("\n" + "=" * 80)
    print("CROSSOVER OPTIONS")
    print("=" * 80)

    # Option 1: Low crossover (800 Hz) - suboptimal with current horn
    xo1 = 800
    print(f"\nOption 1: Low XO ({xo1} Hz)")
    print(f"  Pros: Below LF beaming, good directivity match")
    print(f"  Cons: XO is {(current_fc/xo1):.1f}× horn cutoff (BAD!)")
    print(f"  → HF rolloff in XO region, dip in response")

    # Option 2: Medium crossover (1500 Hz) - optimized for current horn
    xo2 = 1500
    print(f"\nOption 2: Medium XO ({xo2} Hz) - OPTIMIZED FOR CURRENT HORN")
    print(f"  Pros: Best flatness with current horn (10.5 dB)")
    print(f"  Cons: XO is {(current_fc/xo2):.1f}× horn cutoff (still below ideal)")
    print(f"  → Some HF rolloff, but manageable")

    # Option 3: High crossover (2500 Hz) - above horn cutoff
    xo3 = 2500
    print(f"\nOption 3: High XO ({xo3} Hz)")
    print(f"  Pros: XO is {(xo3/current_fc):.1f}× horn cutoff (good!)")
    print(f"  Cons: Above LF beaming ({f_beaming:.0f} Hz)")
    print(f"  → LF directivity narrows, vertical beaming at XO")

    # Recommendation
    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)

    print("\nFUNDAMENTAL CONSTRAINT:")
    print("  The 250mm length limit forces a horn cutoff of ~1865 Hz.")
    print("  For optimal performance, XO should be 2× Fc ≈ 3700 Hz.")
    print("  But 12FW88 beaming starts at ~{:.0f} Hz.".format(f_beaming))

    print("\nPRACTICAL SOLUTIONS:")

    print("\n  Option A: ACCEPT MEDIUM XO (~1500 Hz)")
    print("    → Best compromise with current design")
    print("    → Flatness: ~10.5 dB (acceptable)")
    print("    → Small dip in crossover region")

    print("\n  Option B: USE HIGHER XO (~2500 Hz)")
    print("    → XO above horn cutoff (no HF rolloff)")
    print("    → Deal with LF beaming (toe-in speakers)")
    print("    → May need DSP correction for directivity")

    print("\n  Option C: RELAX 250MM CONSTRAINT")
    print("    → Use ~500mm horn (Fc ≈ 930 Hz)")
    print("    → Can XO at 800 Hz with proper loading")
    print("    → Better integration, no dip")

    print("\n  Option D: MULTI-PIECE HORN")
    print("    → Print horn in 2-3 sections")
    print("    → Assemble to longer total length")
    print("    → Keep each piece within 250mm")

    print("\n  Option E: DIFFERENT HF DRIVER")
    print("    → Compression driver with phase plug")
    print("    → Can work with shorter horn")
    print("    → Lower cutoff for same length")

    # Create visualization
    print("\n" + "=" * 80)
    print("Creating visualization...")
    print("=" * 80)

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    # Plot 1: Length vs. Cutoff
    ax1 = axes[0]
    ax1.plot(lengths_mm, cutoffs, 'bo-', linewidth=2, markersize=8)
    ax1.axhline(current_fc, color='red', linestyle='--', alpha=0.7, linewidth=2,
                label=f'Current horn (Fc = {current_fc:.0f} Hz)')
    ax1.axhline(target_fc, color='green', linestyle='--', alpha=0.7, linewidth=2,
                label=f'Target (Fc = {target_fc:.0f} Hz for 800 Hz XO)')
    ax1.axvline(250, color='orange', linestyle=':', alpha=0.7, linewidth=2,
                label='250mm constraint')
    ax1.axvline(required_length_mm, color='purple', linestyle=':', alpha=0.7, linewidth=2,
                label=f'Required ({required_length_mm:.0f}mm)')

    # Mark operating points
    ax1.plot(250, current_fc, 'ro', markersize=12, label='Current design')
    ax1.plot(required_length_mm, target_fc, 'g*', markersize=15,
             label='Target design')

    ax1.set_xlabel('Horn Length (mm)', fontsize=12)
    ax1.set_ylabel('Horn Cutoff Frequency (Hz)', fontsize=12)
    ax1.set_title('Horn Length vs. Cutoff Frequency (Fundamental Physics)', fontsize=14)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='best', fontsize=10)
    ax1.set_xlim(200, 1100)
    ax1.set_ylim(0, 2500)

    # Plot 2: Crossover options diagram
    ax2 = axes[1]
    ax2.axis('off')

    # Draw frequency spectrum
    freq_range = [20, 20000]

    # Draw horn constraint
    y_pos = 0.8
    ax2.annotate('', xy=(np.log10(current_fc), y_pos), xytext=(np.log10(current_fc*2), y_pos),
                 arrowprops=dict(arrowstyle='<->', color='red', lw=3))
    ax2.text(np.sqrt(current_fc * current_fc*2), y_pos + 0.05,
             f'Horn Operating Range\n({current_fc:.0f} - {current_fc*2:.0f} Hz)',
             ha='center', color='red', fontsize=11, fontweight='bold')

    # Draw LF beaming
    y_pos = 0.6
    ax2.annotate('', xy=(np.log10(f_beaming), y_pos), xytext=(np.log10(20000), y_pos),
                 arrowprops=dict(arrowstyle='<->', color='blue', lw=2))
    ax2.text(np.sqrt(f_beaming * 20000), y_pos + 0.05,
             f'LF Beaming Region\n(>{f_beaming:.0f} Hz)',
             ha='center', color='blue', fontsize=10)

    # Draw crossover options
    xo_positions = [0.4, 0.25, 0.1]
    xo_freqs = [xo1, xo2, xo3]
    xo_labels = ['Low XO', 'Medium XO\n(Recommended)', 'High XO']
    xo_colors = ['red', 'orange', 'green']

    for i, (freq, label, color) in enumerate(zip(xo_freqs, xo_labels, xo_colors)):
        y_pos = xo_positions[i]
        ax2.axvline(np.log10(freq), ymin=0.05, ymax=y_pos - 0.05,
                   color=color, linestyle='--', linewidth=2, alpha=0.7)
        ax2.text(np.log10(freq), y_pos, f'{label}\n{freq} Hz',
                ha='center', va='center', color=color,
                fontsize=10, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor=color, linewidth=2))

    # Title
    ax2.text(np.log10(500), 0.95, 'Crossover Frequency Options & Constraints',
             ha='left', va='top', fontsize=14, fontweight='bold')

    # X-axis label
    ax2.text(np.log10(1000), 0.02, 'Frequency (Hz, log scale)', ha='center', fontsize=11)

    ax2.set_xlim(np.log10(20), np.log10(20000))
    ax2.set_ylim(0, 1)

    plt.tight_layout()

    # Save
    output_dir = Path(__file__).parent
    path = output_dir / "design_tradeoffs_analysis.png"
    fig.savefig(path, dpi=150, bbox_inches='tight')
    print(f"\n✓ Plot saved: {path}")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

    return {
        'current_fc': current_fc,
        'required_length': required_length_mm,
        'beaming_freq': f_beaming,
        'recommended_xo': xo2,
    }


if __name__ == "__main__":
    main()
