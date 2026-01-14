#!/usr/bin/env python3
"""
Redesign multisegment horn using DesignAssistant with smaller mouth constraint.

Target:
- Mouth area: ~250-300 cm² (for lower Fc)
- Cutoff: ~400 Hz (for 800 Hz XO)
- Length: ≤250mm
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
import json
from pathlib import Path

from gsd.driver import load_driver
from gsd.optimization.api.design_assistant import DesignAssistant


def main():
    """Use DesignAssistant to optimize horn with constraints."""
    print("\n" + "=" * 80)
    print("MULTISEGMENT HORN OPTIMIZATION WITH DESIGNASSISTANT")
    print("Target: Smaller mouth for lower Fc and better crossover")
    print("=" * 80)

    # Initialize assistant
    assistant = DesignAssistant(validation_mode=False)

    # Run optimization with constraints
    print("\nRunning optimization...")

    result = assistant.optimize_design(
        driver_name="BC_DH450",
        enclosure_type="multisegment_horn",
        objectives=["flatness", "wavefront_sphericity"],
        constraints={
            "max_length": 0.25,        # 250mm = 0.25m total
            "max_mouth_area": 0.03,    # 300 cm² = 0.03 m² (smaller mouth)
        },
        population_size=50,
        generations=50,
        num_segments=2,
    )

    if not result.success:
        print(f"\n❌ Optimization failed: {result.warnings}")
        return 1

    print(f"\n✓ Optimization complete!")
    print(f"\nFound {len(result.best_designs)} designs")

    # Analyze best designs
    print(f"\n{'='*80}")
    print("TOP 3 DESIGNS")
    print(f"{'='*80}")

    from gsd.optimization.parameters.multisegment_horn_params import decode_multisegment_design
    driver = load_driver("BC_DH450")

    for i, design in enumerate(result.best_designs[:3]):
        params = design['parameters']
        objs = design['objectives']

        print(f"\nDesign {i+1}:")
        print(f"  Flatness: {objs.get('flatness', 'N/A')}")
        print(f"  Wavefront: {objs.get('wavefront_sphericity', 'N/A')}")

        # Decode design array to get horn geometry
        design_array = np.array([
            params['throat_area'],
            params['middle_area'],
            params['mouth_area'],
            params['length1'],
            params['length2'],
            params.get('V_tc', 0),
            params.get('V_rc', 0),
        ])

        decoded = decode_multisegment_design(design_array, driver, num_segments=2)

        # Calculate cutoff
        segments = decoded['segments']
        throat1 = segments[0][0]
        mouth1 = segments[0][1]
        length1 = segments[0][2]

        c = 343
        m1 = np.log(mouth1 / throat1) / length1
        fc = (c * m1 / 2) / (2 * np.pi)

        print(f"  Throat: {decoded['throat_area']*1e4:.2f} cm²")
        print(f"  Mouth: {decoded['mouth_area']*1e4:.1f} cm²")
        print(f"  Length: {decoded['total_length']*100:.1f} mm")
        print(f"  Fc: {fc:.0f} Hz")

    # Get best design
    best = result.best_designs[0]
    best_params = best['parameters']

    print(f"\n{'='*80}")
    print("BEST DESIGN")
    print(f"{'='*80}")

    print(f"\n  Throat: {best_params['throat_area']*1e4:.2f} cm²")
    print(f"  Middle: {best_params['middle_area']*1e4:.1f} cm²")
    print(f"  Mouth: {best_params['mouth_area']*1e4:.1f} cm²")
    print(f"  Length 1: {best_params['length1']*100:.1f} mm")
    print(f"  Length 2: {best_params['length2']*100:.1f} mm")
    print(f"  Total: {(best_params['length1'] + best_params['length2'])*100:.1f} mm")

    # Calculate Fc
    design_array = np.array([
        best_params['throat_area'],
        best_params['middle_area'],
        best_params['mouth_area'],
        best_params['length1'],
        best_params['length2'],
        best_params.get('V_tc', 0),
        best_params.get('V_rc', 0),
    ])

    decoded = decode_multisegment_design(design_array, driver, num_segments=2)
    segments = decoded['segments']

    throat1 = segments[0][0]
    mouth1 = segments[0][1]
    length1 = segments[0][2]

    m1 = np.log(mouth1 / throat1) / length1
    fc = (c * m1 / 2) / (2 * np.pi)

    print(f"\n  Horn Fc: {fc:.0f} Hz")
    print(f"  Target Fc: 400 Hz")
    print(f"  Error: {abs(fc - 400):.0f} Hz")

    print(f"\n  Crossover recommendation: ~{fc*2:.0f} Hz (2×Fc)")

    # Save design in Hornresp format
    create_hornresp_export(decoded, fc, driver)

    # Also save JSON
    design_json = {
        'driver': 'BC_DH450',
        'parameters': best_params,
        'objectives': best['objectives'],
        'calculated': {
            'cutoff_hz': fc,
            'recommended_xo_hz': fc * 2,
        },
    }

    output_dir = Path(__file__).parent
    json_path = output_dir / "optimized_horn_design_assistant.json"
    with open(json_path, 'w') as f:
        json.dump(design_json, f, indent=2)

    print(f"\n✓ JSON saved: {json_path}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\n✓ Horn optimized with DesignAssistant")
    print(f"  Fc = {fc:.0f} Hz (target was 400 Hz)")
    print(f"  Mouth = {best_params['mouth_area']*1e4:.0f} cm² (was 504 cm²)")
    print(f"  Can XO at ~{fc*2:.0f} Hz")
    print(f"\nNext: Integrate with LF enclosure and validate complete system")

    return 0


def create_hornresp_export(decoded, fc, driver):
    """Create Hornresp export file."""
    output_dir = Path(__file__).parent
    export_path = output_dir / "hf_horn_optimized_design_assistant.txt"

    segments = decoded['segments']

    with open(export_path, 'w') as f:
        # Header
        f.write("ID = 983.62\n\n")
        f.write(f"Comment = Optimized multisegment horn: Fc={fc:.0f}Hz, L={decoded['total_length']*100:.1f}cm\n\n")

        # Driver parameters
        f.write("|INPUT:\n")
        f.write(f"Le = {driver.L_e*1000:.2f} mH\n")
        f.write(f"Re = {driver.R_e:.1f} Ohm\n")
        f.write(f"Sd = {driver.S_d*10000:.2f} cm²\n")
        f.write(f"Mmd = {driver.M_md*1000:.2f} g\n")
        f.write(f"Cms = {driver.C_ms*1e6:.2f} mm/N\n")
        f.write(f"Rms = {driver.R_ms:.2f} kg/s\n")
        f.write(f"Bl = {driver.BL:.2f} N/A\n")
        f.write(f"Fs = {driver.F_s:.1f} Hz\n\n")

        # Chambers
        f.write("|LOUDSPEAKER ENCLOSURE:\n")
        f.write("Vrc = 4 cm³\n")
        f.write("Lrc = 3.0 cm\n")
        f.write("Vtc = 15.0 cm³\n")
        f.write("Atc = 0.00 cm²\n")
        f.write("Ltc = 0.00 cm\n\n")

        # Horn segments
        f.write("|HORN:\n")
        for i, seg in enumerate(segments):
            f.write(f"S{i+1} = {seg[0]*10000:.2f}\n")
            f.write(f"S{i+2} = {seg[1]*10000:.2f}\n")
            f.write(f"Exp = {seg[2]*100:.2f}\n")

            # Calculate segment cutoff
            c = 343
            m = np.log(seg[1] / seg[0]) / seg[2]
            fc_seg = (c * m / 2) / (2 * np.pi)
            f.write(f"F{i+1}{i+2} = {fc_seg:.1f}\n\n")

        # Angular
        f.write("|ANGULAR:\n")
        f.write("Ang = 360.0\n")
        f.write("Cir = -200.00\n\n")

        # Room
        f.write("|ROOM:\n")
        f.write("Room = 0\n")
        f.write("Tem = 20.0 C\n")
        f.write("Pb = 101.3 kPa\n")

    print(f"✓ Hornresp export saved: {export_path}")


if __name__ == "__main__":
    sys.exit(main())
