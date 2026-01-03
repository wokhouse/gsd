#!/usr/bin/env python3
"""
Test ported box SPL generalizability across multiple drivers.

This validates that end_correction=1.2 works for different driver sizes
and enclosure volumes. Tests are run against Hornresp simulation data.
"""

import sys
sys.path.insert(0, 'src')

import numpy as np
from gsd.driver import load_driver
from gsd.enclosure.ported_box_vector_sum import calculate_spl_ported_vector_sum_array
from gsd.simulation.constants import SPEED_OF_SOUND


def parse_hornresp_sim(filepath):
    """Parse Hornresp simulation output."""
    data = np.loadtxt(filepath, skiprows=1)
    freq = data[:, 0]
    spl = data[:, 4]
    return freq, spl


def normalize_to_passband(freq, spl, f_min=80, f_max=100):
    """Normalize to passband."""
    mask = (freq >= f_min) & (freq <= f_max)
    if np.any(mask):
        return spl - np.mean(spl[mask])
    return spl


def find_peak(freq, spl):
    """Find peak in bass region (20-200 Hz)."""
    mask = (freq >= 20) & (freq <= 200)
    freq_bass = freq[mask]
    spl_bass = spl[mask]
    idx = np.argmax(spl_bass)
    return freq_bass[idx], spl_bass[idx]


def test_driver(driver_name, Vb, port_area_cm2, port_length_cm, hornresp_sim_file, end_correction=1.2):
    """Test a driver against Hornresp simulation."""
    print(f"\n{'='*80}")
    print(f"Testing: {driver_name}")
    print(f"{'='*80}")
    print(f"  Vb = {Vb} L")
    print(f"  Port = {port_area_cm2} cm² × {port_length_cm} cm")
    print(f"  end_correction = {end_correction}×r")
    print(f"  Hornresp data: {hornresp_sim_file}")

    # Load driver
    driver = load_driver(driver_name)
    print(f"  Driver Fs = {driver.F_s:.1f} Hz, Vas = {driver.V_as*1000:.1f} L")

    # Load Hornresp
    hr_freq, hr_spl = parse_hornresp_sim(hornresp_sim_file)
    hr_spl_norm = normalize_to_passband(hr_freq, hr_spl)
    hr_peak_freq, hr_peak_spl = find_peak(hr_freq, hr_spl_norm)

    # Calculate Fb from port dimensions
    port_area_m2 = port_area_cm2 * 1e-4
    port_length_m = port_length_cm / 100
    port_radius = np.sqrt(port_area_m2 / np.pi)
    L_eff = port_length_m + (0.732 * port_radius)
    Fb = (SPEED_OF_SOUND / (2 * np.pi)) * np.sqrt(port_area_m2 / ((Vb / 1000) * L_eff))

    # Calculate viberesp (convert units: L→m³, cm²→m², cm→m)
    freqs = np.linspace(20, 200, 1000)
    vb_spl = calculate_spl_ported_vector_sum_array(
        freqs, driver, Vb / 1000, Fb, port_area_m2, port_length_m,
        end_correction_factor=end_correction, QL=7.0
    )

    vb_peak_freq, vb_peak_spl = find_peak(freqs, vb_spl)

    # Errors
    freq_error = vb_peak_freq - hr_peak_freq
    spl_error = vb_peak_spl - hr_peak_spl

    # Overall RMS error
    hr_interp = np.interp(freqs, hr_freq, hr_spl_norm)
    rms_error = np.mean(np.abs(vb_spl - hr_interp))

    print(f"\n  Hornresp (normalized):")
    print(f"    Peak: {hr_peak_spl:+.2f} dB at {hr_peak_freq:.2f} Hz")

    print(f"\n  Viberesp:")
    print(f"    Peak: {vb_peak_spl:+.2f} dB at {vb_peak_freq:.2f} Hz")

    print(f"\n  Errors:")
    print(f"    Frequency: {freq_error:+.2f} Hz")
    print(f"    Magnitude: {spl_error:+.2f} dB")
    print(f"    RMS error: {rms_error:.2f} dB")

    pass_fail = abs(freq_error) < 5 and abs(spl_error) < 3 and rms_error < 5
    print(f"\n  Status: {'✓ PASS' if pass_fail else '✗ FAIL'}")

    return {
        'driver': driver_name,
        'freq_error': freq_error,
        'spl_error': spl_error,
        'rms_error': rms_error,
        'pass': pass_fail,
        'Vb': Vb,
        'port_area': port_area_cm2,
        'port_length': port_length_cm
    }


def main():
    """Test all drivers."""
    print("\n" + "="*80)
    print("MULTI-DRIVER GENERALIZABILITY TEST")
    print("="*80)
    print("\nTesting end_correction=1.2 across different driver sizes")
    print("Validating that the parameter generalizes beyond BC_8FMB51\n")

    test_cases = [
        {
            'driver': 'BC_8FMB51',
            'Vb': 20.7,
            'port_area_cm2': 41.34,
            'port_length_cm': 3.80,
            'hornresp_sim': 'exports/validation/bc_8fmb51_b4_sim.txt'
        },
        {
            'driver': 'BC_12NDL76',
            'Vb': 71.9,
            'port_area_cm2': 200.0,
            'port_length_cm': 20.0,
            'hornresp_sim': 'exports/validation/bc_12ndl76_b4_sim.txt'
        },
        {
            'driver': 'BC_15PS100',
            'Vb': 105.5,
            'port_area_cm2': 300.0,
            'port_length_cm': 15.0,
            'hornresp_sim': 'exports/validation/bc_15ps100_b4_sim.txt'
        },
    ]

    results = []
    for tc in test_cases:
        import os
        if not os.path.exists(tc['hornresp_sim']):
            print(f"\n⚠ Skipping {tc['driver']}: Simulation file not found")
            print(f"  Run: {tc['hornresp_sim']}")
            continue

        result = test_driver(**tc)
        if result:
            results.append(result)

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")

    for r in results:
        status = "✓ PASS" if r['pass'] else "✗ FAIL"
        print(f"{r['driver']:15s}: {status}")
        print(f"  Vb={r['Vb']:.1f}L, Port={r['port_area']:.0f}cm²×{r['port_length']:.1f}cm")
        print(f"  Errors: freq={r['freq_error']:+.1f}Hz, spl={r['spl_error']:+.1f}dB, rms={r['rms_error']:.1f}dB")
        print()

    pass_count = sum(1 for r in results if r['pass'])
    total = len(results)

    print(f"Overall: {pass_count}/{total} drivers passed")
    if pass_count == total:
        print("\n✓✓✓ SUCCESS! end_correction=1.2 generalizes to all tested drivers!")
    else:
        print("\n⚠ Some drivers failed. Consider tuning end_correction per driver.")


if __name__ == "__main__":
    main()
