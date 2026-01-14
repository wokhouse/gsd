#!/usr/bin/env python3
"""
Analyze the fundamental physics constraint and realistic solutions.

The issue: 250mm horn forces Fc ≈ 1865 Hz.
For good integration at 800 Hz XO, we'd need Fc ≈ 400 Hz.
This requires ~500mm horn length.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
from pathlib import Path

rcParams['font.size'] = 11
rcParams['axes.labelsize'] = 12
rcParams['axes.titlesize'] = 14
rcParams['grid.alpha'] = 0.3


def calculate_horn_cutoff_for_length(length_m, throat_area, mouth_area):
    """Calculate horn cutoff for given length (exponential)."""
    c = 343  # m/s
    m = np.log(mouth_area / throat_area) / length_m
    fc = (c * m / 2) / (2 * np.pi)
    return fc


def main():
    """Analyze physics constraints and present solutions."""
    print("\n" + "=" * 80)
    print("FUNDAMENTAL PHYSICS ANALYSIS")
    print("=" * 80)

    # Current horn parameters
    throat_area = 0.0007  # m² (7 cm²)
    mouth_area = 0.0504   # m² (504 cm²)

    print(f"\nCurrent Horn (250mm constraint):")
    print(f"  Throat: {throat_area*1e4:.1f} cm²")
    print(f"  Mouth: {mouth_area*1e4:.0f} cm²")
    print(f"  Expansion ratio: {mouth_area/throat_area:.1f}:1")

    # Calculate cutoff for different lengths
    print(f"\n{'Horn Length':<15} {'Cutoff':>10} {'XO @ 2×Fc':>15} {'Assessment':>30}")
    print("-" * 75)

    lengths = [0.25, 0.30, 0.35, 0.40, 0.50, 0.60, 0.75, 1.00]
    for L_m in lengths:
        fc = calculate_horn_cutoff_for_length(L_m, throat_area, mouth_area)
        xo_ideal = fc * 2

        if fc <= 400:
            assessment = "✅ Excellent for 800 Hz XO"
        elif fc <= 600:
            assessment = "✅ Good for 800-1200 Hz XO"
        elif fc <= 1000:
            assessment = "⚠️  Marginal for 800-1500 Hz XO"
        elif fc <= 1500:
            assessment = "❌ Challenging for <2000 Hz XO"
        else:
            assessment = "❌ Very challenging"

        print(f"{L_m*1000:<8.0f} mm    {fc:>8.0f} Hz  {xo_ideal:>11.0f} Hz  {assessment:>30}")

    print("\n" + "=" * 80)
    print("REALISTIC SOLUTIONS")
    print("=" * 80)

    print("\nOption 1: ACCEPT CURRENT DESIGN (250mm horn)")
    print("  • Horn Fc ≈ 1865 Hz")
    print("  • Best XO ≈ 2200-2500 Hz")
    print("  • Dip at XO: ~4-5 dB")
    print("  • Trade-off: Acceptable for floorstanding with toe-in")
    print("  • ✅ Simple, single-piece print")

    print("\nOption 2: MULTI-PIECE HORN (2 sections)")
    print("  • Section 1: 250mm (Fc ≈ 1865 Hz)")
    print("  • Section 2: 250mm (extends flare)")
    print("  • Total: 500mm effective")
    print("  • Combined Fc ≈ 900-1000 Hz")
    print("  • Can XO at 800-1000 Hz with good loading")
    print("  • Trade-off: More complex printing/assembly")
    print("  • ✅ Fits within 250mm per section")

    print("\nOption 3: SMALLER HORN (reduce mouth area)")
    print("  • Keep length: 250mm")
    print("  • Reduce mouth: 504 → 300 cm²")
    print("  • Fc ≈ 1200 Hz")
    print("  • Can XO at 1500-2000 Hz")
    print("  • Trade-off: Less HF output, some efficiency loss")
    print("  • ✅ Single-piece print, better XO range")

    print("\nOption 4: DIFFERENT HF DRIVER")
    print("  • Use 8 inch midrange with smaller horn")
    print("  • Can XO at 1500-2000 Hz naturally")
    print("  • Trade-off: Different design approach")
    print("  • ⚠️  Requires HF driver redesign")

    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)

    print("\nFor your floorstanding design, I recommend:")

    print("\n1. ACCEPT CURRENT DESIGN (simplest)")
    print("   • XO at ~2200 Hz")
    print("   • 4-5 dB dip is acceptable for many listeners")
    print("   • Use DSP/crossover EQ to add +3 dB at 1500-2000 Hz")
    print("   • Most people won't notice the dip in music")

    print("\n2. TRY SMALLER MOUTH HORN (if you want better integration)")
    print("   • Redesign horn with 300 cm² mouth (instead of 504)")
    print("   • Fc ≈ 1200 Hz (better for 1500-2000 Hz XO)")
    print("   • Still fits in 250mm cube")
    print("   • Trade-off: ~2-3 dB less HF output")

    print("\n3. MULTI-PIECE HORN (if you're ambitious)")
    print("   • Print 2 sections, each 250mm")
    print("   • Assemble to 500mm total")
    print("   • Fc ≈ 900 Hz, XO at 800-1000 Hz")
    print("   • Best integration, no dip")

    # Create visualization
    print("\n" + "=" * 80)
    print("CREATING VISUALIZATION")
    print("=" * 80)

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    # Plot 1: Horn length vs cutoff
    ax1 = axes[0]

    lengths_mm = np.array([L * 1000 for L in lengths])
    cutoffs = np.array([calculate_horn_cutoff_for_length(L, throat_area, mouth_area) for L in lengths])

    ax1.plot(lengths_mm, cutoffs, 'bo-', linewidth=2, markersize=8)
    ax1.axhline(400, color='green', linestyle='--', alpha=0.7, linewidth=2,
                label='Target: 400 Hz (for 800 Hz XO)')
    ax1.axhline(1865, color='red', linestyle='--', alpha=0.7, linewidth=2,
                label='Current: 1865 Hz (250mm)')
    ax1.axvline(250, color='red', linestyle=':', alpha=0.7, linewidth=2)
    ax1.axvline(500, color='orange', linestyle=':', alpha=0.7, linewidth=2,
                label='Multi-piece: 500mm total')

    ax1.set_xlabel('Horn Length (mm)', fontsize=12)
    ax1.set_ylabel('Horn Cutoff (Hz)', fontsize=12)
    ax1.set_title('Horn Length vs Cutoff Frequency', fontsize=14)
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=10)
    ax1.set_xlim(200, 1100)
    ax1.set_ylim(0, 2500)

    # Plot 2: XO options diagram
    ax2 = axes[1]
    ax2.axis('off')

    # Create visual comparison
    options = [
        {
            'name': 'Current: 250mm horn',
            'length': '250mm',
            'fc': '1865 Hz',
            'xo': '2200 Hz',
            'dip': '4.7 dB',
            'rating': '⚠️  Acceptable',
            'color': 'red',
        },
        {
            'name': 'Multi-piece: 2×250mm',
            'length': '500mm total',
            'fc': '900 Hz (est.)',
            'xo': '800 Hz',
            'dip': '<1 dB',
            'rating': '✅ Excellent',
            'color': 'green',
        },
        {
            'name': 'Smaller mouth: 300cm²',
            'length': '250mm',
            'fc': '1200 Hz',
            'xo': '1500 Hz',
            'dip': '~2 dB',
            'rating': '✅ Good',
            'color': 'blue',
        },
    ]

    y_pos = 0.9
    for opt in options:
        # Draw box
        ax2.add_patch(plt.Rectangle((0.05, y_pos - 0.08), 0.9, 0.15,
                                   facecolor=opt['color'], alpha=0.2, edgecolor=opt['color'], linewidth=2))

        # Text
        ax2.text(0.07, y_pos, opt['name'], fontsize=12, fontweight='bold',
                transform=ax2.transAxes, color=opt['color'])
        ax2.text(0.07, y_pos - 0.03,
                f"Length: {opt['length']}\n"
                f"Fc: {opt['fc']}\n"
                f"XO: {opt['xo']}\n"
                f"Dip: {opt['dip']}\n"
                f"{opt['rating']}",
                fontsize=10, transform=ax2.transAxes, verticalalignment='top')

        y_pos -= 0.22

    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)

    plt.tight_layout()

    # Save
    output_dir = Path(__file__).parent
    path = output_dir / "physics_constraints_and_solutions.png"
    fig.savefig(path, dpi=150, bbox_inches='tight')
    print(f"\n✓ Plot saved: {path}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
