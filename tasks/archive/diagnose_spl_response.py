#!/usr/bin/env python3
"""
Diagnostic script to check ported box SPL response for BC_15DS115.

This script simulates the response at key frequencies and compares
with expected behavior to identify issues.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
from gsd.driver.bc_drivers import get_bc_15ds115
from gsd.enclosure.ported_box import ported_box_electrical_impedance


def main():
    """Test SPL response at key frequencies."""
    print("=" * 70)
    print("PORTED BOX SPL DIAGNOSTIC: BC_15DS115")
    print("=" * 70)

    # Load driver
    driver = get_bc_15ds115()

    # Design parameters (from the 28 Hz tuning design)
    Vb = 180.0 / 1000.0  # 180 L -> m³
    Fb = 28.0  # Hz
    port_area = 217.1 / 10000.0  # cm² -> m²
    port_length = 38.8 / 100.0  # cm -> m

    print(f"\nDesign Parameters:")
    print(f"  Vb: {Vb*1000:.1f} L")
    print(f"  Fb: {Fb:.1f} Hz")
    print(f"  Port area: {port_area*10000:.1f} cm²")
    print(f"  Port length: {port_length*100:.1f} cm")

    # Test frequencies
    test_frequencies = [
        10,    # Well below tuning
        20,    # Below tuning
        28,    # AT tuning (Fb)
        40,    # Above tuning
        50,    # Above tuning
        70,    # Above tuning
        100,   # Mid-bass
        200,   # Upper bass
        500,   # Midrange (should be low for subwoofer)
        1000,  # High (should be very low)
    ]

    print("\n" + "=" * 70)
    print("SPL RESPONSE VS FREQUENCY")
    print("=" * 70)
    print(f"{'Freq (Hz)':>10} | {'SPL (dB)':>10} | {'Impedance (Ω)':>15} | {'Notes'}")
    print("-" * 70)

    results = []
    for freq in test_frequencies:
        result = ported_box_electrical_impedance(
            freq,
            driver,
            Vb,
            Fb,
            port_area,
            port_length,
            voltage=2.83,
            impedance_model="small"
        )

        spl = result['SPL']
        z_mag = result['Ze_magnitude']

        # Add notes
        note = ""
        if freq < Fb / np.sqrt(2):
            note = "Below tuning (rolloff region)"
        elif abs(freq - Fb) < 2:
            note = "AT TUNING (Fb)"
        elif freq < Fb * np.sqrt(2):
            note = "Between peaks"
        elif freq < 200:
            note = "Above tuning (passband)"
        else:
            note = "High freq (should roll off)"

        print(f"{freq:>10.1f} | {spl:>10.1f} | {z_mag:>15.1f} | {note}")
        results.append((freq, spl, z_mag))

    # Check for anomalies
    print("\n" + "=" * 70)
    print("ANOMALY DETECTION")
    print("=" * 70)

    # Convert to numpy arrays
    freqs = np.array([r[0] for r in results])
    spls = np.array([r[1] for r in results])

    # Find peak SPL
    peak_idx = np.argmax(spls)
    peak_freq = freqs[peak_idx]
    peak_spl = spls[peak_idx]

    print(f"\nPeak SPL: {peak_spl:.1f} dB at {peak_freq:.1f} Hz")

    # Check if there's a midrange peak (problematic)
    midrange_mask = freqs > 200
    if np.any(midrange_mask):
        midrange_spl_max = np.max(spls[midrange_mask])
        midrange_freq_max = freqs[midrange_mask][np.argmax(spls[midrange_mask])]

        print(f"Midrange SPL: {midrange_spl_max:.1f} dB at {midrange_freq_max:.1f} Hz")

        if midrange_spl_max > peak_spl - 10:
            print("  ⚠️  WARNING: Midrange is within 10 dB of peak!")
            print("     This suggests issues with high-frequency modeling")

    # Check for dip (problematic if near tuning)
    for i in range(1, len(spls) - 1):
        if spls[i] < spls[i-1] - 5 and spls[i] < spls[i+1] - 5:
            print(f"\n  ⚠️  DIP detected at {freqs[i]:.1f} Hz: {spls[i]:.1f} dB")
            print(f"     (surrounded by {spls[i-1]:.1f} and {spls[i+1]:.1f} dB)")

    # Check response shape
    print("\n" + "=" * 70)
    print("RESPONSE SHAPE ANALYSIS")
    print("=" * 70)

    # Low frequency rolloff
    below_tuning = spls[freqs < Fb]
    above_tuning = spls[freqs >= Fb]

    if len(below_tuning) > 0 and len(above_tuning) > 0:
        avg_below = np.mean(below_tuning)
        avg_above = np.mean(above_tuning)

        print(f"\nAverage SPL below {Fb:.1f} Hz: {avg_below:.1f} dB")
        print(f"Average SPL above {Fb:.1f} Hz: {avg_above:.1f} dB")
        print(f"Difference: {avg_above - avg_below:.1f} dB")

        if avg_below > avg_above:
            print("  ⚠️  WARNING: Response increases with frequency!")
            print("     This is backwards - should roll off below tuning")

    # Expected behavior checklist
    print("\n" + "=" * 70)
    print("EXPECTED BEHAVIOR CHECKLIST")
    print("=" * 70)

    checks = []

    # Check 1: Rolloff below tuning
    low_freq_spl = spls[freqs < Fb]
    mid_freq_spl = spls[(freqs >= Fb) & (freqs < 200)]

    if len(low_freq_spl) > 0 and len(mid_freq_spl) > 0:
        if np.mean(mid_freq_spl) > np.mean(low_freq_spl):
            checks.append(("✓", "Higher SPL above tuning than below"))
        else:
            checks.append(("✗", "Higher SPL above tuning than below"))

    # Check 2: Dip at tuning (port and driver out of phase)
    fb_result = ported_box_electrical_impedance(Fb, driver, Vb, Fb, port_area, port_length, impedance_model="small")
    fb_spl = fb_result['SPL']

    # Get SPL at frequencies around Fb
    below_fb = ported_box_electrical_impedance(Fb * 0.8, driver, Vb, Fb, port_area, port_length, impedance_model="small")
    above_fb = ported_box_electrical_impedance(Fb * 1.2, driver, Vb, Fb, port_area, port_length, impedance_model="small")

    if fb_spl < below_fb['SPL'] and fb_spl < above_fb['SPL']:
        checks.append(("✓", f"DIP at tuning frequency ({Fb:.1f} Hz)"))
    else:
        checks.append(("✗", f"DIP at tuning frequency ({Fb:.1f} Hz)"))

    # Check 3: Low SPL at high frequencies
    if len(spls[freqs > 200]) > 0:
        high_freq_spl = np.mean(spls[freqs > 200])
        if high_freq_spl < peak_spl - 20:
            checks.append(("✓", f"High frequencies (>200 Hz) are {peak_spl - high_freq_spl:.1f} dB below peak"))
        else:
            checks.append(("✗", f"High frequencies (>200 Hz) should be lower"))

    for status, check in checks:
        print(f"  {status} {check}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
