#!/usr/bin/env python3
"""
Extract port parameters from Hornresp input files and run validation.
"""

import sys
sys.path.insert(0, 'src')

import re
import numpy as np
from gsd.driver import load_driver
from gsd.enclosure.ported_box_vector_sum import calculate_spl_ported_vector_sum_array
from gsd.simulation.constants import SPEED_OF_SOUND


def parse_hornresp_input(filepath):
    """Extract Vb, port area, and port length from Hornresp input file."""
    params = {}
    with open(filepath, 'r') as f:
        for line in f:
            # Extract Vrc (Vb in liters)
            if line.startswith('Vrc ='):
                params['Vb'] = float(line.split('=')[1].strip())

            # Extract Ap (port area in cm²)
            if line.startswith('Ap ='):
                params['port_area_cm2'] = float(line.split('=')[1].strip())

            # Extract Lpt (port length in cm)
            if line.startswith('Lpt ='):
                params['port_length_cm'] = float(line.split('=')[1].strip())

    return params


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


def test_from_hornresp_input(driver_name, input_file, sim_file, end_correction=1.2):
    """Test a driver using parameters extracted from Hornresp input file."""
    print(f"\n{'='*80}")
    print(f"Testing: {driver_name}")
    print(f"{'='*80}")
    print(f"  Hornresp input: {input_file}")
    print(f"  Hornresp sim: {sim_file}")
    print(f"  End correction: {end_correction}×r")

    # Extract parameters
    params = parse_hornresp_input(input_file)
    if not params:
        print(f"  ✗ Failed to extract parameters from {input_file}")
        return None

    print(f"\n  Extracted Parameters:")
    print(f"    Vb = {params['Vb']} L")
    print(f"    Port area = {params['port_area_cm2']} cm²")
    print(f"    Port length = {params['port_length_cm']} cm")

    # Load driver
    try:
        driver = load_driver(driver_name)
    except Exception as e:
        print(f"  ✗ Failed to load driver: {e}")
        return None

    # Load Hornresp sim data
    hr_freq, hr_spl = parse_hornresp_sim(sim_file)
    if hr_freq is None:
        return None

    # Normalize Hornresp to passband
    hr_spl_norm = normalize_to_passband(hr_freq, hr_spl)
    hr_peak_freq, hr_peak_spl = find_peak(hr_freq, hr_spl_norm)

    # Calculate Fb from port dimensions
    port_area_m2 = params['port_area_cm2'] * 1e-4
    port_length_m = params['port_length_cm'] / 100
    port_radius = np.sqrt(port_area_m2 / np.pi)
    L_eff = port_length_m + (0.732 * port_radius)
    Fb = (SPEED_OF_SOUND / (2 * np.pi)) * np.sqrt(port_area_m2 / ((params['Vb'] / 1000) * L_eff))

    # Calculate viberesp response (convert units: L→m³, cm²→m², cm→m)
    freqs = np.linspace(20, 200, 1000)
    vb_spl = calculate_spl_ported_vector_sum_array(
        freqs, driver, params['Vb'] / 1000, Fb, port_area_m2, port_length_m,
        end_correction_factor=end_correction, QL=7.0
    )

    # Find viberesp peak
    vb_peak_freq, vb_peak_spl = find_peak(freqs, vb_spl)

    # Calculate errors
    freq_error = vb_peak_freq - hr_peak_freq
    spl_error = vb_peak_spl - hr_peak_spl

    # Overall match
    hr_interp = np.interp(freqs, hr_freq, hr_spl_norm)
    overall_error = np.mean(np.abs(vb_spl - hr_interp))

    print(f"\n  Hornresp Reference:")
    print(f"    Peak: {hr_peak_spl:+.2f} dB at {hr_peak_freq:.2f} Hz")

    print(f"\n  Viberesp Result:")
    print(f"    Peak: {vb_peak_spl:+.2f} dB at {vb_peak_freq:.2f} Hz")

    print(f"\n  Errors:")
    print(f"    Frequency: {freq_error:+.2f} Hz")
    print(f"    Magnitude: {spl_error:+.2f} dB")
    print(f"    Overall RMS: {overall_error:.2f} dB")

    pass_fail = abs(freq_error) < 3 and abs(spl_error) < 2 and overall_error < 3
    print(f"    Status: {'✓ PASS' if pass_fail else '✗ FAIL'}")

    return {
        'driver': driver_name,
        'freq_error': freq_error,
        'spl_error': spl_error,
        'overall_error': overall_error,
        'pass': pass_fail,
        'params': params
    }


def main():
    """Test multiple drivers with their actual Hornresp parameters."""
    print("\n" + "="*80)
    print("MULTIPLE DRIVER VALIDATION: Using Hornresp Input Parameters")
    print("="*80)
    print("\nTesting with actual port dimensions from Hornresp input files...\n")

    test_cases = [
        {
            'driver': 'BC_8FMB51',
            'input_file': 'imports/bookshelf_input.txt',  # Need to create this
            'sim_file': 'imports/bookshelf_sim.txt',
        },
        {
            'driver': 'BC_8NDL51',
            'input_file': 'tests/validation/drivers/bc_8ndl51/ported_box/input_b4.txt',
            'sim_file': 'tests/validation/drivers/bc_8ndl51/ported_box/sim_b4.txt',
        },
    ]

    results = []
    for tc in test_cases:
        # Check if input file exists
        import os
        if not os.path.exists(tc['input_file']):
            print(f"\n⚠ Skipping {tc['driver']}: input file not found ({tc['input_file']})")
            continue

        driver = tc.pop('driver')
        result = test_from_hornresp_input(driver, **tc)
        tc['driver'] = driver  # Restore
        if result:
            results.append(result)

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}\n")

    for r in results:
        status = "✓ PASS" if r['pass'] else "✗ FAIL"
        print(f"{r['driver']:15s}: {status}")
        print(f"  Parameters: Vb={r['params']['Vb']:.1f}L, "
              f"Port={r['params']['port_area_cm2']:.1f}cm² × {r['params']['port_length_cm']:.2f}cm")
        print(f"  Errors: freq={r['freq_error']:+.1f}Hz, spl={r['spl_error']:+.1f}dB, rms={r['overall_error']:.1f}dB")
        print()

    pass_count = sum(1 for r in results if r['pass'])
    print(f"Overall: {pass_count}/{len(results)} drivers passed")


if __name__ == "__main__":
    main()
