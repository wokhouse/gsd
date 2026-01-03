#!/usr/bin/env python3
"""
Plot SPL response comparison for TC2-4 test cases.

Compares:
- TC2: Driver + Horn (no chambers)
- TC3: + Throat Chamber
- TC4: + Both Chambers
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

import numpy as np
import matplotlib.pyplot as plt
from gsd.simulation import ExponentialHorn
from gsd.enclosure.front_loaded_horn import FrontLoadedHorn
from gsd.driver.parameters import ThieleSmallParameters


def create_systems():
    """Create TC2, TC3, TC4 systems."""
    # Common driver and horn
    driver = ThieleSmallParameters(
        M_md=0.008, C_ms=5.0e-5, R_ms=3.0,
        R_e=6.5, L_e=0.1e-3, BL=12.0, S_d=0.0008,
    )

    horn = ExponentialHorn(
        throat_area=0.0005,
        mouth_area=0.02,
        length=0.5,
    )

    # TC2: No chambers
    tc2 = FrontLoadedHorn(
        driver=driver, horn=horn,
        V_tc=0.0, V_rc=0.0,
    )

    # TC3: Throat chamber only
    tc3 = FrontLoadedHorn(
        driver=driver, horn=horn,
        V_tc=50e-6, A_tc=0.0005,
        V_rc=0.0,
    )

    # TC4: Both chambers
    tc4 = FrontLoadedHorn(
        driver=driver, horn=horn,
        V_tc=50e-6, A_tc=0.0005,
        V_rc=0.002,
    )

    return tc2, tc3, tc4, horn


def calculate_spl_responses(systems, frequencies):
    """Calculate SPL responses for all systems."""
    tc2, tc3, tc4, horn = systems

    # Calculate SPL at 1m, 2.83V using vectorized array method
    result_tc2 = tc2.spl_response_array(frequencies, voltage=2.83, measurement_distance=1.0)
    result_tc3 = tc3.spl_response_array(frequencies, voltage=2.83, measurement_distance=1.0)
    result_tc4 = tc4.spl_response_array(frequencies, voltage=2.83, measurement_distance=1.0)

    return result_tc2['SPL'], result_tc3['SPL'], result_tc4['SPL']


def plot_spl_comparison(frequencies, spl_tc2, spl_tc3, spl_tc4, system):
    """Create SPL comparison plot."""
    fig, ax = plt.subplots(figsize=(12, 7))

    # Plot SPL responses
    ax.semilogx(frequencies, spl_tc2, 'b-', linewidth=2, label='TC2: No Chambers')
    ax.semilogx(frequencies, spl_tc3, 'r--', linewidth=2, label='TC3: + Throat Chamber')
    ax.semilogx(frequencies, spl_tc4, 'g-.', linewidth=2, label='TC4: + Both Chambers')

    # Mark cutoff frequency
    fc = system.cutoff_frequency()
    ax.axvline(x=fc, color='k', linestyle=':', linewidth=1.5, label=f'Horn Cutoff: {fc:.0f} Hz')

    # Formatting
    ax.set_xlabel('Frequency (Hz)', fontsize=12, fontweight='bold')
    ax.set_ylabel('SPL at 1m (dB)', fontsize=12, fontweight='bold')
    ax.set_title('Horn-Loaded System SPL Comparison\n'
                 f'Driver: 8cm², Fs={251:.0f}Hz | Horn: 5→200cm², fc={fc:.0f}Hz',
                 fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='lower left', fontsize=11, framealpha=0.9)

    # Set reasonable axis limits
    ax.set_xlim(10, 20000)
    ax.set_ylim(40, 110)

    plt.tight_layout()

    # Save plot
    output_path = Path(__file__).parent / "spl_comparison_tc2_tc3_tc4.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✓ SPL plot saved to: {output_path}")

    # Also save PDF
    pdf_path = Path(__file__).parent / "spl_comparison_tc2_tc3_tc4.pdf"
    plt.savefig(pdf_path, bbox_inches='tight')
    print(f"✓ SPL plot saved to: {pdf_path}")

    plt.close()


def main():
    """Generate SPL comparison plot."""
    print("Generating SPL comparison plot for TC2-4...")
    print()

    # Create systems
    tc2, tc3, tc4, horn = create_systems()
    print("✓ Created TC2, TC3, TC4 systems")

    # Generate frequency range
    frequencies = np.logspace(np.log10(10), np.log10(20000), 500)
    print(f"✓ Generated frequency range: {frequencies[0]:.1f} - {frequencies[-1]:.1f} Hz")

    # Calculate SPL responses
    print("Calculating SPL responses...")
    spl_tc2, spl_tc3, spl_tc4 = calculate_spl_responses((tc2, tc3, tc4, horn), frequencies)
    print("✓ SPL calculations complete")
    print()

    # Print summary statistics
    print("SPL SUMMARY (at 1m, 2.83V):")
    print(f"  TC2 (No Chambers):")
    print(f"    Min SPL: {min(spl_tc2):.1f} dB")
    print(f"    Max SPL: {max(spl_tc2):.1f} dB")
    print(f"  TC3 (+ Throat):")
    print(f"    Min SPL: {min(spl_tc3):.1f} dB")
    print(f"    Max SPL: {max(spl_tc3):.1f} dB")
    print(f"  TC4 (+ Both):")
    print(f"    Min SPL: {min(spl_tc4):.1f} dB")
    print(f"    Max SPL: {max(spl_tc4):.1f} dB")
    print()

    # Create plot
    plot_spl_comparison(frequencies, spl_tc2, spl_tc3, spl_tc4, tc2)

    print("✓ Plot generation complete!")


if __name__ == "__main__":
    main()
