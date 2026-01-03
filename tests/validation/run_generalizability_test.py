#!/usr/bin/env python3
"""Run validation on existing Hornresp simulation files."""

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
    """Find peak in bass region."""
    mask = (freq >= 20) & (freq <= 200)
    freq_bass = freq[mask]
    spl_bass = spl[mask]
    idx = np.argmax(spl_bass)
    return freq_bass[idx], spl_bass[idx]


def test_driver(driver_name, sim_file, Vb, port_area, port_length, end_correction=1.2):
    """Test a driver against Hornresp simulation."""
    print(f"\n{'='*80}")
    print(f"Testing: {driver_name}")
    print(f"{'='*80}")
    print(f"  Hornresp data: {sim_file}")
    print(f"  Vb = {Vb} L, Port = {port_area} cm² × {port_length} cm")
    print(f"  end_correction = {end_correction}×r")

    # Load driver
    driver = load_driver(driver_name)
    print(f"  Driver: Fs={driver.F_s:.1f}Hz, Vas={driver.V_as*1000:.1f}L, Qts={driver.Q_ts:.3f}")

    # Load Hornresp
    hr_freq, hr_spl = parse_hornresp_sim(sim_file)
    hr_spl_norm = normalize_to_passband(hr_freq, hr_spl)
    hr_peak_freq, hr_peak_spl = find_peak(hr_freq, hr_spl_norm)

    # Calculate Fb from port dimensions
    port_area_m2 = port_area * 1e-4
    port_length_m = port_length / 100
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
    hr_interp = np.interp(freqs, hr_freq, hr_spl_norm)
    rms_error = np.mean(np.abs(vb_spl - hr_interp))

    print(f"\n  Hornresp (normalized to 80-100 Hz):")
    print(f"    Peak: {hr_peak_spl:+.2f} dB at {hr_peak_freq:.2f} Hz")

    print(f"\n  Viberesp (end_correction={end_correction}):")
    print(f"    Peak: {vb_peak_spl:+.2f} dB at {vb_peak_freq:.2f} Hz")

    print(f"\n  Errors:")
    print(f"    Frequency: {freq_error:+.2f} Hz {'✓' if abs(freq_error) < 5 else '✗'}")
    print(f"    Magnitude: {spl_error:+.2f} dB {'✓' if abs(spl_error) < 3 else '✗'}")
    print(f"    RMS error: {rms_error:.2f} dB {'✓' if rms_error < 5 else '✗'}")

    pass_fail = abs(freq_error) < 5 and abs(spl_error) < 3 and rms_error < 5
    print(f"\n  Status: {'✓✓✓ PASS' if pass_fail else '✗✗✗ FAIL'}")

    return {
        'driver': driver_name,
        'freq_error': freq_error,
        'spl_error': spl_error,
        'rms_error': rms_error,
        'pass': pass_fail
    }


print("\n" + "="*80)
print("MULTI-DRIVER GENERALIZABILITY VALIDATION")
print("="*80)
print("\nTesting end_correction=1.2 across different driver sizes\n")

# Test BC_8FMB51
result = test_driver(
    driver_name='BC_8FMB51',
    sim_file='imports/8fmb51_sim.txt',
    Vb=49.3,
    port_area=41.34,
    port_length=3.80
)

results = [result] if result else []

# Check other files
for sim_file in ['imports/12ndl76_sim.txt', 'imports/15ps100_sim.txt']:
    print(f"\n{'='*80}")
    print(f"Checking: {sim_file}")
    print(f"{'='*80}")

    import os
    if not os.path.exists(sim_file):
        print(f"  ✗ File not found")
        continue

    hr_freq, hr_spl = parse_hornresp_sim(sim_file)
    hr_spl_norm = normalize_to_passband(hr_freq, hr_spl)
    hr_peak_freq, hr_peak_spl = find_peak(hr_freq, hr_spl_norm)

    print(f"  Hornresp peak: {hr_peak_spl:+.2f} dB at {hr_peak_freq:.2f} Hz")
    print(f"  Frequency range: {hr_freq.min():.1f} - {hr_freq.max():.1f} Hz")
    print(f"  ⚠ Need port parameters to test viberesp")

# Summary
print(f"\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}\n")

for r in results:
    status = "✓ PASS" if r['pass'] else "✗ FAIL"
    print(f"{r['driver']:15s}: {status} (freq_err={r['freq_error']:+.1f}Hz, spl_err={r['spl_error']:+.1f}dB, rms={r['rms_error']:.1f}dB)")

if results:
    pass_count = sum(1 for r in results if r['pass'])
    total = len(results)
    print(f"\nTested: {pass_count}/{total} drivers passed")
