#!/usr/bin/env python3
"""
Create optimized horn design directly based on physics constraints.

Target:
- Horn cutoff: ~400 Hz (for 800 Hz crossover)
- Mouth area: 250-300 cm² (smaller for lower Fc)
- Length: 250mm (3D printer constraint)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
import json
from pathlib import Path

from gsd.driver import load_driver
from gsd.optimization.parameters.multisegment_horn_params import decode_multisegment_design


def create_optimized_horn_design():
    """
    Create horn design optimized for 800 Hz crossover.

    Physics approach:
    - Target Fc ≈ 400 Hz for XO at 2×Fc = 800 Hz
    - Length = 250mm (printer constraint)
    - Calculate required mouth area for target Fc

    Fc formula for exponential horn:
        fc = (c * m / 2) / (2π)
        where m = ln(mouth/throat) / L

    Solving for mouth area:
        m = 2π * fc * 2 / c
        ln(mouth/throat) = m * L
        mouth = throat * exp(m * L)
    """
    print("\n" + "=" * 80)
    print("OPTIMIZED HORN DESIGN FOR 800 HZ CROSSOVER")
    print("=" * 80)

    # Fixed parameters
    c = 343  # Speed of sound (m/s)
    target_fc = 400  # Target cutoff (Hz)
    L_total = 0.25  # Total horn length (m) - 250mm
    throat_area = 0.0007  # Throat area (m²) - 7 cm² (DH450)

    print(f"\nDesign targets:")
    print(f"  Cutoff: {target_fc} Hz")
    print(f"  Crossover: {target_fc*2} Hz (2×Fc)")
    print(f"  Length: {L_total*1000:.0f} mm")
    print(f"  Throat: {throat_area*1e4:.1f} cm²")

    # Calculate required flare constant
    m = 2 * np.pi * target_fc * 2 / c

    print(f"\nRequired flare constant: m = {m:.2f} m⁻¹")

    # Calculate required mouth area for uniform exponential horn
    mouth_area_uniform = throat_area * np.exp(m * L_total)

    print(f"\nFor uniform exponential horn ({L_total*1000:.0f}mm):")
    print(f"  Required mouth: {mouth_area_uniform*1e4:.0f} cm²")

    # Check if this fits within constraints
    max_mouth = 0.0625  # 625 cm² (250mm × 250mm)

    if mouth_area_uniform > max_mouth:
        print(f"  ❌ Exceeds maximum ({max_mouth*1e4:.0f} cm²)")
        print(f"\nSolution: Use smaller mouth with higher Fc")
    else:
        print(f"  ✓ Fits within constraint")

    # Calculate Fc for various mouth areas
    print(f"\n{'Mouth (cm²)':<15} {'Fc (Hz)':>12} {'XO @ 2×Fc (Hz)':>18} {'Assessment':<30}")
    print("-" * 80)

    mouth_options = [250, 300, 350, 400, 450, 500]

    for mouth_cm2 in mouth_options:
        mouth_m2 = mouth_cm2 / 10000

        # Calculate flare constant for this mouth
        m_calc = np.log(mouth_m2 / throat_area) / L_total

        # Calculate resulting cutoff
        fc = (c * m_calc / 2) / (2 * np.pi)
        xo_2fc = fc * 2

        # Assessment
        if fc <= target_fc:
            assessment = "✅ Excellent"
        elif fc <= target_fc * 1.2:
            assessment = "✅ Good"
        elif fc <= target_fc * 1.5:
            assessment = "⚠️  Acceptable"
        else:
            assessment = "❌ Poor"

        print(f"{mouth_cm2:<15.0f} {fc:>12.0f} {xo_2fc:>18.0f} {assessment:<30}")

    # Select optimal design
    print("\n" + "=" * 80)
    print("SELECTED DESIGN")
    print("=" * 80)

    # Based on analysis from design_smaller_mouth_horn.py:
    # - 250 cm² mouth gives Fc=390Hz, XO=780Hz, dip=3.99dB (best)
    # - This matches our target of 400Hz perfectly

    selected_mouth_cm2 = 250
    selected_mouth_m2 = selected_mouth_cm2 / 10000

    # Calculate 2-segment horn design
    # Segment 1: Most of the expansion
    # Segment 2: Final expansion to mouth

    length1 = 0.125  # 125mm
    length2 = 0.125  # 125mm

    # Calculate middle area (junction between segments)
    # For gradual expansion, use ~50% of total expansion in segment 1
    exp_total = np.log(selected_mouth_m2 / throat_area)
    exp1 = exp_total * 0.6  # 60% of expansion in segment 1
    middle_area = throat_area * np.exp(exp1)

    # Create design array for decode_multisegment_design
    # Format: [throat, middle, mouth, length1, length2, V_tc, V_rc]
    design_array = np.array([
        throat_area,
        middle_area,
        selected_mouth_m2,
        length1,
        length2,
        0,  # V_tc (rear chamber)
        0,  # V_rc (front chamber)
    ])

    driver = load_driver("BC_DH450")
    decoded = decode_multisegment_design(design_array, driver, num_segments=2)

    # Calculate actual cutoff
    segments = decoded['segments']
    throat1 = segments[0][0]
    mouth1 = segments[0][1]
    length1_act = segments[0][2]

    m1 = np.log(mouth1 / throat1) / length1_act
    fc = (c * m1 / 2) / (2 * np.pi)

    print(f"\nHorn geometry:")
    print(f"  Throat: {decoded['throat_area']*1e4:.2f} cm²")
    print(f"  Middle: {decoded['segments'][0][1]*1e4:.1f} cm²")
    print(f"  Mouth: {decoded['mouth_area']*1e4:.0f} cm²")
    print(f"  Length 1: {decoded['segments'][0][2]*100:.1f} cm ({decoded['segments'][0][2]*1000:.0f} mm)")
    print(f"  Length 2: {decoded['segments'][1][2]*100:.1f} cm ({decoded['segments'][1][2]*1000:.0f} mm)")
    print(f"  Total: {decoded['total_length']*100:.1f} cm ({decoded['total_length']*1000:.0f} mm)")

    print(f"\nPerformance:")
    print(f"  Horn Fc: {fc:.0f} Hz")
    print(f"  Target Fc: {target_fc} Hz")
    print(f"  Error: {abs(fc - target_fc):.0f} Hz")
    print(f"  Recommended XO: {fc*2:.0f} Hz ({fc*2/target_fc:.2f}×Fc)")

    if abs(fc - target_fc) / target_fc < 0.1:  # Within 10%
        print(f"  ✅ Excellent match!")
    elif abs(fc - target_fc) / target_fc < 0.2:  # Within 20%
        print(f"  ✅ Good match")
    else:
        print(f"  ⚠️  Outside target range")

    # Save design
    design = {
        'design_array': design_array.tolist(),
        'parameters': {
            'throat_area_cm2': decoded['throat_area'] * 10000,
            'middle_area_cm2': decoded['segments'][0][1] * 10000,
            'mouth_area_cm2': decoded['mouth_area'] * 10000,
            'length1_cm': decoded['segments'][0][2] * 100,
            'length2_cm': decoded['segments'][1][2] * 100,
            'total_length_cm': decoded['total_length'] * 100,
        },
        'performance': {
            'cutoff_hz': fc,
            'recommended_xo_hz': fc * 2,
            'target_fc_hz': target_fc,
            'error_hz': abs(fc - target_fc),
        },
        'design_method': 'Direct physics calculation',
    }

    output_dir = Path(__file__).parent
    design_path = output_dir / "optimized_horn_direct.json"

    with open(design_path, 'w') as f:
        json.dump(design, f, indent=2)

    print(f"\n✓ Design saved: {design_path}")

    # Create Hornresp export
    create_hornresp_export(decoded, fc, driver, design_path)

    return design


def create_hornresp_export(decoded, fc, driver, json_path):
    """Create Hornresp export file."""
    output_dir = Path(__file__).parent
    export_path = output_dir / "hf_horn_optimized_250cm.txt"

    segments = decoded['segments']

    with open(export_path, 'w') as f:
        # Header
        f.write("ID = 983.62\n\n")
        f.write(f"Comment = Optimized multisegment horn: Fc={fc:.0f}Hz, L={decoded['total_length']*100:.1f}cm, Mouth={decoded['mouth_area']*1e4:.0f}cm2\n\n")

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
        c = 343
        for i, seg in enumerate(segments):
            f.write(f"S{i+1} = {seg[0]*10000:.2f}\n")
            f.write(f"S{i+2} = {seg[1]*10000:.2f}\n")
            f.write(f"Exp = {seg[2]*100:.2f}\n")

            # Calculate segment cutoff
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
    design = create_optimized_horn_design()

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\n✅ Horn designed using physics-first approach")
    print(f"   Fc = {design['performance']['cutoff_hz']:.0f} Hz")
    print(f"   XO at = {design['performance']['recommended_xo_hz']:.0f} Hz")
    print(f"   Mouth = {design['parameters']['mouth_area_cm2']:.0f} cm²")
    print(f"   Length = {design['parameters']['total_length_cm']:.0f} cm ({design['parameters']['total_length_cm']*10:.0f} mm)")
    print(f"\nNext: Validate with Hornresp and integrate with LF enclosure")
    print("=" * 80)
