#!/usr/bin/env python3
"""
Validate ported box SPL with end correction across multiple drivers.

This tests generalizability of the end_correction_factor=1.2 parameter
across different driver sizes and enclosure types.
"""

import sys
sys.path.insert(0, 'src')

import numpy as np
from gsd.driver import load_driver
from gsd.enclosure.ported_box_vector_sum import calculate_spl_ported_vector_sum_array
from gsd.simulation.constants import SPEED_OF_SOUND


def parse_hornresp_sim(filepath):
    """Parse Hornresp simulation output file."""
    try:
        data = np.loadtxt(filepath, skiprows=1)
        freq = data[:, 0]  # Column 0: Frequency
        spl = data[:, 4]   # Column 5: SPL (dB)
        return freq, spl
    except Exception as e:
        print(f"  Error parsing {filepath}: {e}")
        return None, None


def normalize_to_passband(freq, spl, f_min=80, f_max=100):
    """Normalize SPL to passband (same as our implementation)."""
    mask = (freq >= f_min) & (freq <= f_max)
    if np.any(mask):
        ref = np.mean(spl[mask])
        return spl - ref
    return spl


def find_peak(freq, spl):
    """Find peak frequency and magnitude."""
    idx = np.argmax(spl)
    return freq[idx], spl[idx]


def test_driver(driver_name, Vb, port_area_cm2, port_length_cm, hornresp, end_correction=1.2):
    """Test a single driver against Hornresp data."""
    print(f"\n{'='*80}")
    print(f"Testing: {driver_name}")
    print(f"{'='*80}")
    print(f"  Vb = {Vb} L")
    print(f"  Port = {port_area_cm2} cm² × {port_length_cm} cm")
    print(f"  End correction = {end_correction}×r")
    print(f"  Hornresp data: {hornresp}")

    # Load driver
    try:
        driver = load_driver(driver_name)
    except Exception as e:
        print(f"  ✗ Failed to load driver: {e}")
        return None

    # Load Hornresp data
    hr_freq, hr_spl = parse_hornresp_sim(hornresp)
    if hr_freq is None:
        return None

    # Normalize Hornresp to passband (80-100 Hz)
    hr_spl_norm = normalize_to_passband(hr_freq, hr_spl)
    hr_peak_freq, hr_peak_spl = find_peak(hr_freq, hr_spl_norm)

    # Calculate Fb from port dimensions
    port_area_m2 = port_area_cm2 * 1e-4
    port_length_m = port_length_cm / 100
    port_radius = np.sqrt(port_area_m2 / np.pi)
    L_eff = port_length_m + (0.732 * port_radius)
    Fb = (SPEED_OF_SOUND / (2 * np.pi)) * np.sqrt(port_area_m2 / ((Vb / 1000) * L_eff))

    # Calculate viberesp response (convert units: L→m³, cm²→m², cm→m)
    freqs = np.linspace(20, 200, 1000)
    vb_spl = calculate_spl_ported_vector_sum_array(
        freqs, driver, Vb / 1000, Fb, port_area_m2, port_length_m,
        end_correction_factor=end_correction, QL=7.0
    )

    # Find viberesp peak
    vb_peak_freq, vb_peak_spl = find_peak(freqs, vb_spl)

    # Calculate error metrics
    freq_error = vb_peak_freq - hr_peak_freq
    spl_error = vb_peak_spl - hr_peak_spl

    # Check specific frequencies
    hr_53 = np.interp(53, hr_freq, hr_spl_norm) if 53 >= hr_freq.min() else None
    hr_60 = np.interp(60, hr_freq, hr_spl_norm) if 60 >= hr_freq.min() else None
    vb_53 = np.interp(53, freqs, vb_spl)
    vb_60 = np.interp(60, freqs, vb_spl)

    print(f"\n  Hornresp Reference:")
    print(f"    Peak: {hr_peak_spl:+.2f} dB at {hr_peak_freq:.2f} Hz")
    if hr_53 and hr_60:
        print(f"    53 Hz: {hr_53:+.2f} dB")
        print(f"    60 Hz: {hr_60:+.2f} dB")
        print(f"    Shape (53-60 Hz): {hr_53 - hr_60:+.2f} dB")

    print(f"\n  Viberesp Result:")
    print(f"    Peak: {vb_peak_spl:+.2f} dB at {vb_peak_freq:.2f} Hz")
    print(f"    53 Hz: {vb_53:+.2f} dB")
    print(f"    60 Hz: {vb_60:+.2f} dB")
    print(f"    Shape (53-60 Hz): {vb_53 - vb_60:+.2f} dB")

    print(f"\n  Errors:")
    print(f"    Frequency: {freq_error:+.2f} Hz {'✓' if abs(freq_error) < 3 else '✗'}")
    print(f"    Magnitude: {spl_error:+.2f} dB {'✓' if abs(spl_error) < 2 else '✗'}")

    # Overall match (across full range)
    hr_interp = np.interp(freqs, hr_freq, hr_spl_norm)
    overall_error = np.mean(np.abs(vb_spl - hr_interp))
    print(f"    Overall RMS error: {overall_error:.2f} dB {'✓' if overall_error < 3 else '✗'}")

    return {
        'driver': driver_name,
        'freq_error': freq_error,
        'spl_error': spl_error,
        'overall_error': overall_error,
        'pass': abs(freq_error) < 3 and abs(spl_error) < 2 and overall_error < 3
    }


def main():
    """Test multiple drivers with default end_correction=1.2."""
    print("\n" + "="*80)
    print("MULTIPLE DRIVER VALIDATION: End Correction Generalizability")
    print("="*80)
    print("\nTesting end_correction_factor=1.2 across different drivers...")
    print("This validates that the parameter generalizes beyond BC_8FMB51.\n")

    # Test cases (using available Hornresp validation data)
    test_cases = [
        {
            'name': 'BC_8FMB51',
            'Vb': 49.3,
            'port_area_cm2': 41.34,
            'port_length_cm': 3.80,
            'hornresp': 'imports/bookshelf_sim.txt'
        },
        {
            'name': 'BC_8NDL51',
            'Vb': 10.1,
            'port_area_cm2': 30.0,  # Approximate from Hornresp
            'port_length_cm': 3.81,  # 1.5 inch
            'hornresp': 'tests/validation/drivers/bc_8ndl51/ported_box/sim_1_5in.txt'
        },
        {
            'name': 'BC_15DS115',
            'Vb': 180.0,
            'port_area_cm2': 84.0,  # Approximate (4 inch port)
            'port_length_cm': 10.16,  # 4 inch
            'hornresp': 'tests/validation/drivers/bc_15ds115/ported/bc_15ds115_ported_180l.txt'
        },
    ]

    results = []
    for tc in test_cases:
        driver_name = tc.pop('name')
        result = test_driver(driver_name, **tc, end_correction=1.2)
        tc['name'] = driver_name  # Restore for summary
        if result:
            results.append(result)

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")

    for r in results:
        status = "✓ PASS" if r['pass'] else "✗ FAIL"
        print(f"{r['driver']:15s}: {status} (freq_err={r['freq_error']:+.1f} Hz, "
              f"spl_err={r['spl_error']:+.1f} dB, rms_err={r['overall_error']:.1f} dB)")

    pass_count = sum(1 for r in results if r['pass'])
    print(f"\nOverall: {pass_count}/{len(results)} drivers passed with end_correction=1.2")

    if pass_count == len(results):
        print("\n✓✓✓ SUCCESS! end_correction=1.2 generalizes to all tested drivers!")
    else:
        print("\n⚠ Some drivers may need end_correction tuning for optimal accuracy.")
        print("  Consider making end_correction a driver-specific parameter.")


if __name__ == "__main__":
    main()
