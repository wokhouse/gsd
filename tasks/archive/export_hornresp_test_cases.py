#!/usr/bin/env python3
"""
Export test driver designs to Hornresp format for SPL calibration validation.

This script creates Hornresp input files for the test cases that will be used
to calibrate the SPL transfer function against Hornresp reference simulations.
"""

import sys
sys.path.insert(0, 'src')

from gsd.hornresp.export import export_to_hornresp
from gsd.driver.bc_drivers import get_bc_8ndl51, get_bc_15ds115
from gsd.enclosure.ported_box import calculate_optimal_port_dimensions


def main():
    print("=" * 70)
    print("Exporting Test Designs to Hornresp Format")
    print("=" * 70)

    # Test 1: BC_8NDL51 sealed box (10L)
    print("\n[1/2] Exporting BC_8NDL51 Sealed Box (10L)...")
    driver_8ndl51 = get_bc_8ndl51()
    Vb_sealed = 0.010  # 10L

    export_to_hornresp(
        driver=driver_8ndl51,
        driver_name="BC_8NDL51_Sealed_10L",
        output_path="tests/validation/drivers/bc_8ndl51/sealed/bc_8ndl51_sealed_10l.txt",
        comment="10L sealed box for SPL calibration. Fs=64Hz, Qts=0.37, Vas=14L",
        enclosure_type="sealed_box",
        Vb_liters=Vb_sealed * 1000
    )
    print(f"  ✓ Exported to: tests/validation/drivers/bc_8ndl51/sealed/bc_8ndl51_sealed_10l.txt")
    print(f"    Driver: BC_8NDL51")
    print(f"    Fs: {driver_8ndl51.F_s} Hz")
    print(f"    Box volume: {Vb_sealed * 1000}L")
    print(f"    Expected Fc: {driver_8ndl51.F_s * ((1 + driver_8ndl51.V_as / Vb_sealed) ** 0.5):.1f} Hz")

    # Test 2: BC_15DS115 ported box (180L, B4 alignment)
    print("\n[2/2] Exporting BC_15DS115 Ported Box (180L, B4 alignment)...")
    driver_15ds115 = get_bc_15ds115()
    Vb_ported = 0.180  # 180L
    Fb = driver_15ds115.F_s  # B4 alignment: Fb = Fs

    # Calculate optimal port dimensions
    port_area, port_length, v_max = calculate_optimal_port_dimensions(
        driver_15ds115, Vb_ported, Fb
    )

    export_to_hornresp(
        driver=driver_15ds115,
        driver_name="BC_15DS115_Ported_180L_B4",
        output_path="tests/validation/drivers/bc_15ds115/ported/bc_15ds115_ported_180l.txt",
        comment=f"180L ported box B4 alignment for SPL calibration. Fs={Fb}Hz, Fb={Fb}Hz. "
                f"Port: {port_area*10000:.1f}cm² x {port_length*100:.1f}cm",
        enclosure_type="ported_box",
        Vb_liters=Vb_ported * 1000,
        Fb_hz=Fb,
        port_area_cm2=port_area * 10000,
        port_length_cm=port_length * 100
    )
    print(f"  ✓ Exported to: tests/validation/drivers/bc_15ds115/ported/bc_15ds115_ported_180l.txt")
    print(f"    Driver: BC_15DS115")
    print(f"    Fs: {driver_15ds115.F_s} Hz")
    print(f"    Box volume: {Vb_ported * 1000}L")
    print(f"    Tuning: Fb = {Fb} Hz (B4 alignment)")
    print(f"    Port: {port_area * 10000:.1f} cm² x {port_length * 100:.1f} cm")
    print(f"    Max port velocity: {v_max:.3f} m/s")

    print("\n" + "=" * 70)
    print("Export Complete!")
    print("=" * 70)
    print("\nNext Steps:")
    print("1. Open Hornresp")
    print("2. For each exported file:")
    print("   - File → Import → Select the .txt file")
    print("   - Tools → Loudspeaker Wizard (or press F10)")
    print("   - Export SPL: File → Export → SPL Response")
    print("   - Save as 'spl_hornresp.csv' in the same directory")
    print("\n3. Run the validation script:")
    print("   PYTHONPATH=src python3 tasks/validate_transfer_function_calibration.py")
    print("\nFrequencies to simulate in Hornresp:")
    print("  20, 28, 40, 50, 70, 100, 150, 200, 300, 500 Hz")
    print("  Input: 2.83V (1W into 8Ω)")
    print("  Distance: 1m")


if __name__ == "__main__":
    main()
