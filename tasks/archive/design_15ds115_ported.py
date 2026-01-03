#!/usr/bin/env python3
"""
Design a ported subwoofer enclosure for the BC_15DS115 driver.

This script calculates optimal box parameters using Thiele-Small alignment
theory and exports the design to Hornresp format for validation.

Driver: B&C 15DS115-8 15" Subwoofer
- Fs: 33 Hz
- Qts: 0.17
- Vas: 94 L
- Xmax: 16.5 mm

Literature:
- Thiele (1971) - Vented box alignments
- Small (1973) - Optimum ported box systems
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from gsd.driver.bc_drivers import get_bc_15ds115
from gsd.enclosure.ported_box import (
    calculate_ported_box_system_parameters,
    calculate_optimal_port_dimensions,
    calculate_port_length_for_area,
    helmholtz_resonance_frequency,
)
from gsd.hornresp.export import export_to_hornresp


def main():
    """Design and analyze ported box for BC_15DS115."""
    print("=" * 70)
    print("PORTED SUBWOOFER DESIGN: B&C 15DS115-8")
    print("=" * 70)

    # Step 1: Get driver parameters
    print("\n[1] DRIVER PARAMETERS")
    print("-" * 70)
    driver = get_bc_15ds115()

    print(f"Driver: B&C 15DS115-8 15\" Subwoofer")
    print(f"  Resonance (Fs):    {driver.F_s:.2f} Hz")
    print(f"  Total Q (Qts):     {driver.Q_ts:.3f}")
    print(f"  Electrical Q (Qes): {driver.Q_es:.3f}")
    print(f"  Mechanical Q (Qms): {driver.Q_ms:.2f}")
    print(f"  Vas:               {driver.V_as * 1000:.2f} L")
    print(f"  Sd:                {driver.S_d * 10000:.1f} cm²")
    print(f"  Xmax:              {driver.X_max * 1000:.2f} mm")
    print(f"  BL:                {driver.BL:.2f} T·m")

    # Step 2: Determine alignment
    print("\n[2] ALIGNMENT SELECTION")
    print("-" * 70)

    # For subwoofer with Qts=0.17, we want extended bass response
    # B4 alignment requires Qts = 0.707 / sqrt(alpha+1)
    # For Qts=0.17, we can use a larger box for deeper bass

    # Option 1: B4 alignment (maximally flat)
    # B4: h = 1, alpha = (0.707/Qts)² - 1 = (0.707/0.17)² - 1 ≈ 16.3
    # This requires very large box

    # Option 2: Extended bass (larger box, lower F3)
    # Use practical box size for home theater

    # Let's design for home theater subwoofer
    # Target F3 around 28-30 Hz for deep bass
    # Use box volume around 150-200 L (practical size)

    print(f"Driver Qts = {driver.Q_ts:.3f}")
    print(f"  -> Suitable for ported enclosure (Qts < 0.3)")
    print(f"  -> Extended bass response with large box")
    print()

    # Design option: Extended bass alignment
    # Use larger box for deeper response
    Vb_liters = 180.0  # 180 L box (large but practical)
    Fb = 28.0          # Tune to 28 Hz for deep bass

    print(f"Selected design:")
    print(f"  Box volume (Vb):   {Vb_liters:.1f} L")
    print(f"  Tuning (Fb):       {Fb:.2f} Hz")

    # Step 3: Calculate system parameters
    print("\n[3] SYSTEM PARAMETERS")
    print("-" * 70)

    Vb = Vb_liters / 1000.0  # Convert to m³
    params = calculate_ported_box_system_parameters(
        driver, Vb, Fb, alignment="custom"
    )

    print(f"Compliance ratio (α = Vas/Vb): {params.alpha:.2f}")
    print(f"Tuning ratio (h = Fb/Fs):      {params.h:.2f}")
    print(f"-3dB frequency (F3):           {params.F3:.2f} Hz")

    # Calculate expected peak locations
    # For ported box: F_low ≈ Fb/√2, F_high ≈ Fb×√2
    import math
    F_low = Fb / math.sqrt(2)
    F_high = Fb * math.sqrt(2)
    print(f"Expected impedance peaks:")
    print(f"  Lower peak:  ~{F_low:.1f} Hz")
    print(f"  Upper peak:  ~{F_high:.1f} Hz")

    # Step 4: Calculate port dimensions
    print("\n[4] PORT DESIGN")
    print("-" * 70)

    port_area_m2, port_length_m, v_max = calculate_optimal_port_dimensions(
        driver, Vb, Fb, max_port_velocity=0.05, safety_factor=1.5
    )

    print(f"Port area:     {port_area_m2 * 10000:.1f} cm²")
    print(f"Port diameter: {2 * (port_area_m2 / math.pi)**0.5 * 100:.1f} cm (circular)")

    # Try common port diameters
    diameters_cm = [10, 12, 15, 18, 20]  # Common pipe sizes
    print(f"\nRecommended port options:")
    for diam_cm in diameters_cm:
        area = math.pi * ((diam_cm / 100 / 2)**2)
        try:
            length = calculate_port_length_for_area(area, Vb, Fb, flanged=True)
            print(f"  {diam_cm:2d} cm diameter: {length * 100:.1f} cm long")
        except ValueError:
            continue

    print(f"\nOptimized port (auto-calculated):")
    print(f"  Area:   {port_area_m2 * 10000:.1f} cm²")
    print(f"  Length: {port_length_m * 100:.1f} cm")
    print(f"  Max air velocity at rated power: {v_max:.2f} m/s")
    print(f"  (Limit: 5% of c = {0.05 * 343:.1f} m/s to prevent chuffing)")

    # Step 5: Box dimensions (assuming rectangular prism)
    print("\n[5] BOX DIMENSIONS (approximate)")
    print("-" * 70)

    # Net volume already accounts for driver, port, bracing
    # Add ~20% for driver displacement, port, bracing
    gross_volume_liters = Vb_liters * 1.2

    # Assume depth = 0.6 × width, height = 1.2 × width
    # V = W × D × H = W × 0.6W × 1.2W = 0.72W³
    width_m = (gross_volume_liters / 1000 / 0.72) ** (1/3)
    depth_m = width_m * 0.6
    height_m = width_m * 1.2

    print(f"Gross volume: ~{gross_volume_liters:.1f} L (includes driver, port, bracing)")
    print(f"External dimensions (approximate):")
    print(f"  Width:  {width_m * 100:.1f} cm")
    print(f"  Depth:  {depth_m * 100:.1f} cm")
    print(f"  Height: {height_m * 100:.1f} cm")

    # Step 6: Export to Hornresp
    print("\n[6] EXPORT TO HORNRESP")
    print("-" * 70)

    output_path = "outputs/15ds115_ported_28hz.txt"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    export_to_hornresp(
        driver=driver,
        driver_name="B&C 15DS115-8",
        output_path=output_path,
        comment=f"Ported box: {Vb_liters:.1f}L @ {Fb:.1f}Hz - Extended bass",
        enclosure_type="ported_box",
        Vb_liters=Vb_liters,
        Fb_hz=Fb,
        port_area_cm2=port_area_m2 * 10000,
        port_length_cm=port_length_m * 100,
    )

    print(f"Exported to: {output_path}")
    print(f"Import this file into Hornresp to validate the design")

    # Step 7: Summary
    print("\n" + "=" * 70)
    print("DESIGN SUMMARY")
    print("=" * 70)
    print(f"Driver:        B&C 15DS115-8 15\" Subwoofer")
    print(f"Box volume:    {Vb_liters:.1f} L net")
    print(f"Port tuning:   {Fb:.1f} Hz")
    print(f"Port area:     {port_area_m2 * 10000:.1f} cm²")
    print(f"Port length:   {port_length_m * 100:.1f} cm")
    print(f"Expected F3:   ~{params.F3:.1f} Hz")
    print(f"External size: ~{width_m*100:.0f} × {depth_m*100:.0f} × {height_m*100:.0f} cm")
    print()
    print("Next steps:")
    print("  1. Import 'outputs/15ds115_ported_28hz.txt' into Hornresp")
    print("  2. Run impedance simulation to verify dual peaks")
    print("  3. Run SPL simulation to check frequency response")
    print("  4. Adjust box volume/tuning if needed")
    print("=" * 70)


if __name__ == "__main__":
    main()
