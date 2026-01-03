#!/usr/bin/env python3
"""
Quick validation script for ported box enclosures.

This script validates viberesp ported box simulations against Hornresp
reference data for BC_8NDL51 driver.

Usage:
    python scripts/validate_ported_box_quick.py
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
from gsd.driver.bc_drivers import get_bc_8ndl51
from gsd.enclosure.ported_box import (
    calculate_ported_box_system_parameters,
    ported_box_electrical_impedance,
)
from gsd.hornresp.results_parser import load_hornresp_sim_file
from gsd.validation.compare import (
    compare_electrical_impedance,
    compare_electrical_impedance_phase,
)


def validate_ported_box_case(
    driver,
    sim_file_path,
    vb_liters,
    fb_hz,
    port_area_cm2,
    port_length_cm,
    test_name,
):
    """
    Validate a single ported box test case.

    Args:
        driver: ThieleSmallParameters
        sim_file_path: Path to Hornresp sim.txt file
        vb_liters: Box volume in liters
        fb_hz: Target tuning frequency in Hz
        port_area_cm2: Port area in cm²
        port_length_cm: Port length in cm
        test_name: Name of the test case

    Returns:
        dict with validation results
    """
    print(f"\n{'='*70}")
    print(f"Validating: {test_name}")
    print(f"{'='*70}")
    print(f"  Vb = {vb_liters:.2f} L")
    print(f"  Fb = {fb_hz:.2f} Hz")
    print(f"  Port area = {port_area_cm2:.2f} cm²")
    print(f"  Port length = {port_length_cm:.2f} cm")

    # Load Hornresp data
    print(f"\nLoading Hornresp data: {sim_file_path}")
    hornresp_data = load_hornresp_sim_file(sim_file_path)

    # Convert parameters to SI units
    vb_m3 = vb_liters / 1000.0
    port_area_m2 = port_area_cm2 / 10000.0
    port_length_m = port_length_cm / 100.0

    # Calculate system parameters
    print(f"\nCalculating system parameters...")
    sys_params = calculate_ported_box_system_parameters(driver, vb_m3, fb_hz)
    print(f"  α (compliance ratio) = {sys_params.alpha:.3f}")
    print(f"  h (tuning ratio) = {sys_params.h:.3f}")
    print(f"  F3 (-3dB) = {sys_params.F3:.2f} Hz")

    # Get frequencies from Hornresp data
    frequencies = hornresp_data.frequency

    # Calculate electrical impedance using viberesp
    print(f"\nCalculating viberesp electrical impedance...")
    print(f"  Computing {len(frequencies)} frequency points...")

    # Ported box function takes single frequency, need to loop
    ze_viberesp = np.zeros_like(frequencies)
    ze_phase_viberesp = np.zeros_like(frequencies)

    for i, freq in enumerate(frequencies):
        result = ported_box_electrical_impedance(
            frequency=freq,
            driver=driver,
            Vb=vb_m3,
            Fb=fb_hz,
            port_area=port_area_m2,
            port_length=port_length_m,
            impedance_model="small",  # Use Small's transfer function model
        )
        ze_viberesp[i] = result['Ze_magnitude']
        ze_phase_viberesp[i] = result['Ze_phase']

    model_used = "small"

    # Compare electrical impedance magnitude
    print(f"\nComparing electrical impedance magnitude...")
    result_mag = compare_electrical_impedance(
        frequencies,
        ze_viberesp,
        hornresp_data,
        tolerance_percent=15.0,  # Relaxed tolerance for dual peaks
    )

    # Compare electrical impedance phase
    print(f"\nComparing electrical impedance phase...")
    result_phase = compare_electrical_impedance_phase(
        frequencies,
        ze_phase_viberesp,
        hornresp_data,
        tolerance_degrees=25.0,  # Relaxed tolerance
    )

    # Print results
    print(f"\n{'='*70}")
    print(f"RESULTS: {test_name}")
    print(f"{'='*70}")

    print(f"\nElectrical Impedance Magnitude:")
    print(f"  Max error: {result_mag.max_percent_error:.2f}%")
    print(f"  RMS error: {result_mag.rms_error:.2f} Ω")
    print(f"  Pass: {result_mag.passed} (tolerance: 15%)")

    print(f"\nElectrical Impedance Phase:")
    print(f"  Max error: {result_phase.max_percent_error:.2f}%")
    print(f"  RMS error: {result_phase.rms_error:.2f}°")
    print(f"  Pass: {result_phase.passed} (tolerance: 25°)")

    # Find impedance peaks
    print(f"\nImpedance Peaks:")
    from scipy.signal import find_peaks

    # Hornresp peaks
    peaks_hr, _ = find_peaks(hornresp_data.ze_ohms, prominence=5.0)
    if len(peaks_hr) > 0:
        peak_freqs_hr = frequencies[peaks_hr]
        peak_vals_hr = hornresp_data.ze_ohms[peaks_hr]
        print(f"  Hornresp peaks:")
        for i, (freq, val) in enumerate(zip(peak_freqs_hr, peak_vals_hr)):
            print(f"    Peak {i+1}: {freq:.1f} Hz @ {val:.2f} Ω")

    # Viberesp peaks
    peaks_vb, _ = find_peaks(ze_viberesp, prominence=5.0)
    if len(peaks_vb) > 0:
        peak_freqs_vb = frequencies[peaks_vb]
        peak_vals_vb = ze_viberesp[peaks_vb]
        print(f"  Viberesp peaks:")
        for i, (freq, val) in enumerate(zip(peak_freqs_vb, peak_vals_vb)):
            print(f"    Peak {i+1}: {freq:.1f} Hz @ {val:.2f} Ω")

    return {
        "test_name": test_name,
        "impedance_mag": result_mag,
        "impedance_phase": result_phase,
        "model_used": model_used,
        "passes": result_mag.passed and result_phase.passed,
    }


def main():
    """Run validation on BC_8NDL51 ported box test cases."""
    print("=" * 70)
    print("Ported Box Validation - BC_8NDL51")
    print("=" * 70)

    # Get driver
    driver = get_bc_8ndl51()
    print(f"\nDriver: BC_8NDL51")
    print(f"  Fs = {driver.F_s:.2f} Hz")
    print(f"  Vas = {driver.V_as * 1000:.2f} L")
    print(f"  Qts = {driver.Q_ts:.3f}")

    # Validation data directory
    validation_dir = Path("tests/validation/drivers/bc_8ndl51/ported_box")

    # Define test cases
    # Note: Port parameters extracted from input_*.txt files
    test_cases = [
        {
            "name": "B4 Alignment",
            "sim_file": validation_dir / "sim_b4.txt",
            "vb_liters": 10.10,
            "fb_hz": 75.0,
            "port_area_cm2": 63.47,
            "port_length_cm": 29.48,
        },
        {
            "name": "1 inch port",
            "sim_file": validation_dir / "sim_1in.txt",
            "vb_liters": 10.10,
            "fb_hz": 75.0,
            "port_area_cm2": 5.1,
            "port_length_cm": 1.6,
        },
        {
            "name": "1.5 inch port",
            "sim_file": validation_dir / "sim_1_5in.txt",
            "vb_liters": 10.10,
            "fb_hz": 75.0,
            "port_area_cm2": 11.4,
            "port_length_cm": 4.4,
        },
        {
            "name": "2 inch port",
            "sim_file": validation_dir / "sim_2in.txt",
            "vb_liters": 10.10,
            "fb_hz": 75.0,
            "port_area_cm2": 20.3,
            "port_length_cm": 8.5,
        },
    ]

    # Run validation
    results = []
    for tc in test_cases:
        if not tc["sim_file"].exists():
            print(f"\n⚠️  SKIPPED: {tc['name']} - sim file not found: {tc['sim_file']}")
            continue

        result = validate_ported_box_case(
            driver=driver,
            sim_file_path=tc["sim_file"],
            vb_liters=tc["vb_liters"],
            fb_hz=tc["fb_hz"],
            port_area_cm2=tc["port_area_cm2"],
            port_length_cm=tc["port_length_cm"],
            test_name=tc["name"],
        )

        if result:
            results.append(result)

    # Summary
    print(f"\n{'='*70}")
    print(f"VALIDATION SUMMARY")
    print(f"{'='*70}")

    passed = sum(1 for r in results if r["passes"])
    total = len(results)

    print(f"\nTotal tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")

    print(f"\nDetailed Results:")
    for r in results:
        status = "✅ PASS" if r["passes"] else "❌ FAIL"
        print(f"  {status}: {r['test_name']}")
        print(f"    Impedance mag: {r['impedance_mag'].max_percent_error:.2f}% max error")
        print(f"    Impedance phase: {r['impedance_phase'].max_percent_error:.2f}% max error")
        print(f"    Model: {r['model_used']}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
