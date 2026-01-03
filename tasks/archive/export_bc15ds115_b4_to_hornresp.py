#!/usr/bin/env python3
"""
Export BC_15DS115 B4 alignment to Hornresp format.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from gsd.driver.bc_drivers import get_bc_15ds115
from gsd.hornresp.export import export_to_hornresp
from gsd.enclosure.ported_box import calculate_optimal_port_dimensions


def main():
    """Export B4 alignment to Hornresp."""
    # Get driver
    driver = get_bc_15ds115()

    # B4 Alignment parameters
    Vb = driver.V_as  # Vb = Vas for B4
    Fb = driver.F_s   # Fb = Fs for B4

    # Calculate optimal port dimensions
    port_area, port_length, port_velocity_max = calculate_optimal_port_dimensions(
        driver, Vb, Fb
    )

    print("=" * 70)
    print("BC_15DS115 B4 ALIGNMENT - HORNRESP EXPORT")
    print("=" * 70)
    print(f"Driver: B&C 15DS115")
    print(f"Design: B4 Butterworth Alignment")
    print()
    print(f"Enclosure Parameters:")
    print(f"  Vb = {Vb*1000:.1f} L (Vas)")
    print(f"  Fb = {Fb:.1f} Hz (Fs)")
    print(f"  Port Area = {port_area*10000:.1f} cm²")
    print(f"  Port Length = {port_length*100:.1f} cm")
    print()

    # Export to Hornresp format
    output_path = "tasks/bc15ds115_b4_alignment.txt"

    export_to_hornresp(
        driver=driver,
        driver_name="BC_15DS115",
        output_path=output_path,
        comment="B4 Butterworth Alignment: Vb=Vas=254L, Fb=Fs=33Hz",
        enclosure_type="ported_box",
        Vb_liters=Vb * 1000,
        Fb_hz=Fb,
        port_area_cm2=port_area * 10000,
        port_length_cm=port_length * 100
    )

    print("=" * 70)
    print(f"✅ Exported to: {output_path}")
    print("=" * 70)
    print()
    print("To import into Hornresp:")
    print("1. Open Hornresp")
    print("2. File → Import...")
    print(f"3. Select: {output_path}")
    print("4. Run simulation (Tools → Loudspeaker Wizard or F10)")
    print()
    print("Expected validation:")
    print("  - F3: ~33 Hz")
    print("  - Flat response in bass region (20-80 Hz)")
    print("  - Bass flatness σ ≈ 2.48 dB")
    print()


if __name__ == "__main__":
    main()
