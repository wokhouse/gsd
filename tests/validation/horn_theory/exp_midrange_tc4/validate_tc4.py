#!/usr/bin/env python3
"""
Validate TC4: Driver + Horn + Both Chambers against Hornresp.

This script reads the Hornresp simulation results and compares them
with viberesp calculations for the same system.

Usage:
    python validate_tc4.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

import numpy as np
from gsd.simulation import ExponentialHorn
from gsd.enclosure.front_loaded_horn import FrontLoadedHorn
from gsd.driver.parameters import ThieleSmallParameters


def parse_hornresp_sim(sim_path: str):
    """
    Parse Hornresp sim.txt file.

    Hornresp format (tab-separated):
    Freq    Ra    Xa    Za    SPL    Ze    Xd    WPhase    UPhase    CPhase    Delay    Eff    Ein    Pin    Iin    ZePhase
    where:
    - Column 1: Freq (hertz)
    - Column 6: Ze (ohms) - electrical impedance magnitude
    - Column 16: ZePhase (deg) - electrical impedance phase
    """
    data = {
        'frequency': [],
        'Ze_magnitude': [],
        'Ze_phase': [],
        'Ze_real': [],
        'Ze_imag': [],
    }

    with open(sim_path, 'r') as f:
        lines = f.readlines()

    # Skip header line
    for i, line in enumerate(lines):
        if i == 0:
            continue  # Skip header

        line = line.strip()
        if not line or line.startswith('*'):
            continue

        # Split by tab
        parts = line.split('\t')
        if len(parts) >= 16:
            try:
                freq = float(parts[0])
                ze_mag = float(parts[5])   # Column 6: Ze (ohms)
                ze_phase = float(parts[15])  # Column 16: ZePhase (deg)

                data['frequency'].append(freq)
                data['Ze_magnitude'].append(ze_mag)
                data['Ze_phase'].append(ze_phase)

                # Convert to rectangular
                ze_rad = np.deg2rad(ze_phase)
                data['Ze_real'].append(ze_mag * np.cos(ze_rad))
                data['Ze_imag'].append(ze_mag * np.sin(ze_rad))

            except (ValueError, IndexError) as e:
                print(f"Warning: Skipping line {i+1}: {e}")
                continue

    if not data['frequency']:
        raise ValueError(f"No data found in {sim_path}")

    # Convert to numpy arrays
    for key in data:
        data[key] = np.array(data[key])

    return data


def calculate_viberesp_response():
    """
    Calculate viberesp response for TC4 system.

    TC4 Parameters (from horn_params.txt):
    - Driver: Sd=8cm², Bl=12, Cms=5e-5, Rms=3, Mmd=8g, Le=0.1mH, Re=6.5Ω
    - Horn: S1=5cm², S2=200cm², L12=0.5m
    - Throat Chamber: Vtc=50cm³, Atc=5cm²
    - Rear Chamber: Vrc=2.0L, Lrc=12.6cm
    """
    # Create driver (match horn_params.txt)
    driver = ThieleSmallParameters(
        M_md=0.008,     # 8g -> 0.008 kg
        C_ms=5.0e-5,    # 5.00E-05 m/N
        R_ms=3.0,       # 3.00 N·s/m
        R_e=6.5,        # 6.50 Ω
        L_e=0.1e-3,     # 0.10 mH -> 0.0001 H
        BL=12.0,        # 12.00 T·m
        S_d=0.0008,     # 8.00 cm² -> 0.0008 m²
    )

    # Create horn (match horn_params.txt)
    horn = ExponentialHorn(
        throat_area=0.0005,  # 5.00 cm² -> 0.0005 m²
        mouth_area=0.02,      # 200.00 cm² -> 0.02 m²
        length=0.5,           # 0.500 m
    )

    # Create front-loaded horn system with both chambers
    flh = FrontLoadedHorn(
        driver=driver,
        horn=horn,
        V_tc=50e-6,   # 50.00 cm³ -> 0.00005 m³ (throat chamber)
        A_tc=0.0005,  # 5.00 cm² -> 0.0005 m² (throat chamber area)
        V_rc=0.002,   # 2.00 L -> 0.002 m³ (rear chamber)
    )

    # Get frequencies from Hornresp results
    sim_path = Path(__file__).parent / "sim.txt"
    hr_data = parse_hornresp_sim(sim_path)

    # Calculate viberesp response at same frequencies
    viberesp_result = flh.electrical_impedance_array(hr_data['frequency'])

    return viberesp_result, driver, horn, flh


def compare_results(hr_data, ve_result):
    """
    Compare Hornresp and viberesp results.

    Print comparison statistics and identify largest deviations.
    """
    print("=" * 70)
    print("TC4 VALIDATION: Driver + Horn + Both Chambers")
    print("=" * 70)
    print()

    # Print system info
    print(f"Number of frequency points: {len(hr_data['frequency'])}")
    print(f"Frequency range: {hr_data['frequency'][0]:.1f} - {hr_data['frequency'][-1]:.1f} Hz")
    print()

    # Calculate errors
    ze_mag_error = np.abs(ve_result['Ze_magnitude'] - hr_data['Ze_magnitude']) / hr_data['Ze_magnitude'] * 100
    ze_phase_error = np.abs(ve_result['Ze_phase'] - hr_data['Ze_phase'])

    # Overall statistics
    print("IMPEDANCE MAGNITUDE:")
    print(f"  Mean error: {np.mean(ze_mag_error):.2f}%")
    print(f"  Max error:  {np.max(ze_mag_error):.2f}%")
    print(f"  Median error: {np.median(ze_mag_error):.2f}%")
    print(f"  Std deviation: {np.std(ze_mag_error):.2f}%")
    print()

    print("IMPEDANCE PHASE:")
    print(f"  Mean error: {np.mean(ze_phase_error):.2f}°")
    print(f"  Max error:  {np.max(ze_phase_error):.2f}°")
    print(f"  Median error: {np.median(ze_phase_error):.2f}°")
    print(f"  Std deviation: {np.std(ze_phase_error):.2f}°")
    print()

    # Find worst offenders
    worst_mag_idx = np.argmax(ze_mag_error)
    worst_phase_idx = np.argmax(ze_phase_error)

    print("WORST CASES:")
    print(f"  Magnitude error: {ze_mag_error[worst_mag_idx]:.2f}% at {hr_data['frequency'][worst_mag_idx]:.1f} Hz")
    print(f"    Hornresp: {hr_data['Ze_magnitude'][worst_mag_idx]:.2f} Ω")
    print(f"    Viberesp:  {ve_result['Ze_magnitude'][worst_mag_idx]:.2f} Ω")
    print()
    print(f"  Phase error: {ze_phase_error[worst_phase_idx]:.2f}° at {hr_data['frequency'][worst_phase_idx]:.1f} Hz")
    print(f"    Hornresp: {hr_data['Ze_phase'][worst_phase_idx]:.2f}°")
    print(f"    Viberesp:  {ve_result['Ze_phase'][worst_phase_idx]:.2f}°")
    print()

    # Validation criteria
    mag_pass = np.mean(ze_mag_error) < 2.0
    phase_pass = np.mean(ze_phase_error) < 5.0

    print("VALIDATION CRITERIA:")
    print(f"  Magnitude < 2%: {'✓ PASS' if mag_pass else '✗ FAIL'}")
    print(f"  Phase < 5°:     {'✓ PASS' if phase_pass else '✗ FAIL'}")
    print()

    # Frequency bands
    print("FREQUENCY BAND ANALYSIS:")
    bands = [
        ("Low (10-100 Hz)", hr_data['frequency'] < 100),
        ("Mid (100-1k Hz)", (hr_data['frequency'] >= 100) & (hr_data['frequency'] < 1000)),
        ("High (1k-10k Hz)", hr_data['frequency'] >= 1000),
    ]

    for band_name, mask in bands:
        if np.any(mask):
            mag_err_band = ze_mag_error[mask]
            phase_err_band = ze_phase_error[mask]
            print(f"  {band_name}:")
            print(f"    Mag: {np.mean(mag_err_band):.2f}% (max {np.max(mag_err_band):.2f}%)")
            print(f"    Phase: {np.mean(phase_err_band):.2f}° (max {np.max(phase_err_band):.2f}°)")
    print()

    return mag_pass and phase_pass


def save_comparison_data(hr_data, ve_result):
    """Save comparison data for further analysis."""
    output_path = Path(__file__).parent / "comparison_results.txt"

    with open(output_path, 'w') as f:
        f.write("# TC4 Validation Results\n")
        f.write("# Frequency(Hz)\tHR_Ze_mag(ohm)\tVE_Ze_mag(ohm)\tHR_Ze_phase(deg)\tVE_Ze_phase(deg)\tMag_err(%)\tPhase_err(deg)\n")

        for i in range(len(hr_data['frequency'])):
            freq = hr_data['frequency'][i]
            hr_mag = hr_data['Ze_magnitude'][i]
            ve_mag = ve_result['Ze_magnitude'][i]
            hr_phase = hr_data['Ze_phase'][i]
            ve_phase = ve_result['Ze_phase'][i]

            mag_err = abs(ve_mag - hr_mag) / hr_mag * 100
            phase_err = abs(ve_phase - hr_phase)

            f.write(f"{freq:.2f}\t{hr_mag:.4f}\t{ve_mag:.4f}\t{hr_phase:.2f}\t{ve_phase:.2f}\t{mag_err:.2f}\t{phase_err:.2f}\n")

    print(f"✓ Comparison results saved to: {output_path}")


def main():
    """Run validation for TC4."""
    print("TC4 Validation: Driver + Horn + Both Chambers")
    print()

    # Parse Hornresp results
    sim_path = Path(__file__).parent / "sim.txt"
    if not sim_path.exists():
        print(f"ERROR: {sim_path} not found!")
        print("Please run Hornresp simulation first and save results as sim.txt")
        return 1

    print(f"Reading Hornresp results from: {sim_path}")
    hr_data = parse_hornresp_sim(str(sim_path))
    print(f"✓ Loaded {len(hr_data['frequency'])} data points")
    print()

    # Calculate viberesp response
    print("Calculating viberesp response...")
    ve_result, driver, horn, flh = calculate_viberesp_response()
    print("✓ Viberesp calculation complete")
    print()

    # Print system parameters
    print("SYSTEM PARAMETERS:")
    print(f"  Driver: Sd={driver.S_d*10000:.1f}cm², Mmd={driver.M_md*1000:.1f}g, BL={driver.BL:.1f}")
    print(f"  Horn: S1={horn.throat_area*10000:.1f}cm², S2={horn.mouth_area*10000:.1f}cm², L={horn.length:.2f}m")
    print(f"  Throat Chamber: Vtc={flh.V_tc*1e6:.1f}cm³, Atc={flh.A_tc*10000:.1f}cm²")
    print(f"  Rear Chamber: Vrc={flh.V_rc*1000:.1f}L")
    print(f"  Cutoff: {flh.cutoff_frequency():.1f} Hz")
    print(f"  Driver Fs: {driver.F_s:.1f} Hz")
    print()

    # Compare results
    try:
        passed = compare_results(hr_data, ve_result)

        # Save comparison data
        save_comparison_data(hr_data, ve_result)

        print("=" * 70)
        if passed:
            print("✓ VALIDATION PASSED")
        else:
            print("✗ VALIDATION FAILED - criteria not met")
        print("=" * 70)

        return 0 if passed else 1

    except Exception as e:
        print(f"ERROR during comparison: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
