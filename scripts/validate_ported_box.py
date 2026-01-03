#!/usr/bin/env python3
"""
Ported box validation script.

Compares viberesp ported box simulation against Hornresp reference data.

Usage:
    python scripts/validate_ported_box.py

Literature:
- Thiele (1971) - Loudspeakers in Vented Boxes
- Hornresp validation methodology
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
    compare_spl,
    generate_validation_report,
)


def validate_ported_box(
    sim_file: Path,
    driver_name: str = "BC_8NDL51",
    Vb_liters: float = 31.65,
    Fb_hz: float = 65.3,
    port_area_cm2: float = 31.67,
    port_length_cm: float = 4.29,
):
    """
    Validate ported box simulation against Hornresp.

    Args:
        sim_file: Path to Hornresp sim.txt file
        driver_name: Name of driver
        Vb_liters: Box volume in liters
        Fb_hz: Port tuning frequency in Hz
        port_area_cm2: Port cross-sectional area in cm²
        port_length_cm: Port physical length in cm
    """
    print(f"\n{'='*70}")
    print(f"VALIDATING: {driver_name} Ported Box")
    print(f"  Vb = {Vb_liters} L")
    print(f"  Fb = {Fb_hz} Hz")
    print(f"  Port area = {port_area_cm2} cm²")
    print(f"  Port length = {port_length_cm} cm")
    print(f"{'='*70}\n")

    # Load driver
    driver = get_bc_8ndl51()

    # Load Hornresp reference data
    print(f"Loading Hornresp data from: {sim_file}")
    hornresp_data = load_hornresp_sim_file(sim_file)
    print(f"  Loaded {len(hornresp_data)} frequency points")
    print(f"  Frequency range: {hornresp_data.metadata['freq_min']:.1f} - {hornresp_data.metadata['freq_max']:.1f} Hz")

    # Convert units to SI
    Vb = Vb_liters / 1000.0  # L to m³
    port_area = port_area_cm2 / 10000.0  # cm² to m²
    port_length = port_length_cm / 100.0  # cm to m

    # Calculate viberesp response at all frequency points
    print(f"\nCalculating viberesp response...")
    ze_viberesp = []
    spl_viberesp = []

    for i, f in enumerate(hornresp_data.frequency):
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(hornresp_data)}...")

        result = ported_box_electrical_impedance(
            frequency=f,
            driver=driver,
            Vb=Vb,
            Fb=Fb_hz,
            port_area=port_area,
            port_length=port_length,
            voltage=2.83,
        )

        ze_viberesp.append(complex(result["Ze_real"], result["Ze_imag"]))
        spl_viberesp.append(result["SPL"])

    ze_viberesp = np.array(ze_viberesp)
    spl_viberesp = np.array(spl_viberesp)

    print(f"  Calculation complete")

    # Run comparisons
    print(f"\n{'='*70}")
    print("VALIDATION RESULTS")
    print(f"{'='*70}\n")

    # Electrical impedance magnitude
    ze_mag_result = compare_electrical_impedance(
        hornresp_data.frequency,
        ze_viberesp,
        hornresp_data,
        tolerance_percent=5.0,  # 5% tolerance for ported box
    )
    print(ze_mag_result.summary)
    print()

    # Electrical impedance phase
    ze_phase_result = compare_electrical_impedance_phase(
        hornresp_data.frequency,
        ze_viberesp,
        hornresp_data,
        tolerance_degrees=10.0,  # 10° tolerance for ported box
    )
    print(ze_phase_result.summary)
    print()

    # SPL response
    spl_result = compare_spl(
        hornresp_data.frequency,
        spl_viberesp,
        hornresp_data.spl_db,
        tolerance_db=6.0,  # 6 dB tolerance for ported box
    )
    print(spl_result.summary)
    print()

    # Generate comprehensive report
    report = generate_validation_report(
        driver_name,
        f"ported_Vb{Vb_liters}L_Fb{Fb_hz}Hz",
        [ze_mag_result, ze_phase_result, spl_result],
    )

    print(f"\n{report}\n")

    # Show worst errors
    print(f"\n{'='*70}")
    print("WORST ERRORS - Ze Magnitude")
    print(f"{'='*70}")
    worst_ze_mag = ze_mag_result.get_worst_errors(n=5)
    for i, err in enumerate(worst_ze_mag, 1):
        print(f"  {i}. {err['frequency']:.1f} Hz: "
              f"{err['viberesp']:.2f} vs {err['hornresp']:.2f} Ω "
              f"({err['percent_error']:.2f}%)")

    print(f"\nWORST ERRORS - Ze Phase")
    print(f"{'='*70}")
    worst_ze_phase = ze_phase_result.get_worst_errors(n=5)
    for i, err in enumerate(worst_ze_phase, 1):
        print(f"  {i}. {err['frequency']:.1f} Hz: "
              f"{err['viberesp']:.1f} vs {err['hornresp']:.1f}° "
              f"({err['absolute_error']:.1f}°)")

    print(f"\nWORST ERRORS - SPL")
    print(f"{'='*70}")
    worst_spl = spl_result.get_worst_errors(n=5)
    for i, err in enumerate(worst_spl, 1):
        print(f"  {i}. {err['frequency']:.1f} Hz: "
              f"{err['viberesp']:.2f} vs {err['hornresp']:.2f} dB "
              f"({err['absolute_error']:.2f} dB)")

    # Return pass/fail
    return ze_mag_result.passed and ze_phase_result.passed and spl_result.passed


def main():
    """Run validation on all available ported box cases."""
    validation_data_dir = Path("tests/validation_data/ported_boxes/BC_8NDL51")

    # Test cases
    test_cases = [
        {
            "name": "2.5 inch port",
            "dir": validation_data_dir / "vb31.6L_fb65Hz_b4_2.5in_port",
            "Vb": 31.65,
            "Fb": 65.3,
            "port_area": 31.67,
            "port_length": 4.29,
        },
        {
            "name": "3 inch port",
            "dir": validation_data_dir / "vb31.6L_fb65Hz_b4_3in_port",
            "Vb": 31.65,
            "Fb": 65.3,
            "port_area": 45.60,
            "port_length": 6.83,
        },
    ]

    results = []

    for test_case in test_cases:
        sim_file = test_case["dir"] / "sim.txt"

        if not sim_file.exists():
            print(f"\n⚠ WARNING: Simulation file not found: {sim_file}")
            print(f"  Skipping {test_case['name']}")
            continue

        try:
            passed = validate_ported_box(
                sim_file=sim_file,
                Vb_liters=test_case["Vb"],
                Fb_hz=test_case["Fb"],
                port_area_cm2=test_case["port_area"],
                port_length_cm=test_case["port_length"],
            )
            results.append((test_case["name"], passed))

        except Exception as e:
            print(f"\n✗ ERROR: Validation failed for {test_case['name']}")
            print(f"  {e}")
            import traceback
            traceback.print_exc()
            results.append((test_case["name"], False))

    # Summary
    print(f"\n{'='*70}")
    print("OVERALL SUMMARY")
    print(f"{'='*70}")
    for name, passed in results:
        status = "PASS ✓" if passed else "FAIL ✗"
        print(f"  {name}: {status}")

    all_passed = all(passed for _, passed in results)
    print(f"\nOverall Result: {'ALL TESTS PASSED ✓' if all_passed else 'SOME TESTS FAILED ✗'}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
