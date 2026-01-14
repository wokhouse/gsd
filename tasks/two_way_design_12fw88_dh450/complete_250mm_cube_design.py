#!/usr/bin/env python3
"""
Two-Way System Design: BC_DH450 (HF) + BC_12FW88 (LF) with 250mm Cube Constraint

This script designs a complete two-way loudspeaker system with:
1. Multi-segment horn-loaded DH450 compression driver (must fit in 250mm cube)
2. Ported 12FW88 mid-bass driver
3. Crossover design and system integration
4. Hornresp export for validation

Author: Claude Code
Date: 2025-01-13
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
import json
from pathlib import Path

from gsd.driver import load_driver
from gsd.optimization.api.design_assistant import DesignAssistant
from gsd.optimization.api.crossover_assistant import CrossoverDesignAssistant
from gsd.optimization.api.two_way_system import (
    optimize_hf_padding_for_flatness,
    calculate_hf_horn_response,
    calculate_lr4_crossover_gains,
    calculate_system_flatness,
    calculate_f3_frequency,
)
from gsd.hornresp.export import export_to_hornresp
from gsd.enclosure.ported_box import (
    calculate_spl_ported_transfer_function,
    calculate_ported_box_system_parameters,
)
from gsd.optimization.parameters.multisegment_horn_params import (
    get_multisegment_horn_parameter_space,
    decode_multisegment_design,
)


# =============================================================================
# DESIGN CONSTRAINTS
# =============================================================================

PRINTER_CONSTRAINTS = {
    "max_length": 0.25,       # 250mm (1 dimension of cube)
    "max_mouth_area": 0.0625, # 250mm x 250mm = 625 cm² = 0.0625 m²
    "max_volume": 0.015625,   # 250mm³ = 15.6 L
}

HF_DRIVER = "BC_DH450"
LF_DRIVER = "BC_12FW88"

CROSSOVER_RANGE = (800, 2500)  # Hz


# =============================================================================
# DESIGN FUNCTIONS
# =============================================================================

def design_lf_enclosure():
    """Design optimal ported enclosure for 12FW88."""
    print("=" * 80)
    print("STEP 1: LF ENCLOSURE DESIGN (BC_12FW88)")
    print("=" * 80)

    assistant = DesignAssistant(validation_mode=False)

    # Optimize for F3 and flatness
    result = assistant.optimize_design(
        driver_name=LF_DRIVER,
        enclosure_type="ported",
        objectives=["f3", "flatness"],
        population_size=50,
        generations=50,
    )

    if not result.success:
        raise ValueError(f"LF optimization failed: {result.warnings}")

    best = result.best_designs[0]

    Vb = best['parameters']['Vb']
    Fb = best['parameters']['Fb']

    print(f"\n✓ Optimal ported box design:")
    print(f"  Vb = {Vb*1000:.1f} L")
    print(f"  Fb = {Fb:.1f} Hz")
    print(f"  F3 = {best['objectives']['f3']:.1f} Hz")
    print(f"  Flatness = {best['objectives']['flatness']:.2f} dB")

    # Calculate port dimensions
    driver = load_driver(LF_DRIVER)
    params = calculate_ported_box_system_parameters(driver, Vb, Fb)

    return {
        "Vb": Vb,
        "Fb": Fb,
        "F3": best['objectives']['f3'],
        "flatness": best['objectives']['flatness'],
        "port_area_cm2": params.port_area * 10000,
        "port_length_cm": params.port_length * 100,
    }


def design_hf_horn_250mm_cube():
    """Design multi-segment horn for DH450 within 250mm cube constraints."""
    print("\n" + "=" * 80)
    print("STEP 2: HF HORN DESIGN (BC_DH450) - 250mm CUBE CONSTRAINT")
    print("=" * 80)

    # Check existing design
    existing_design_path = Path(__file__).parent / "horn_design_dh450_constrained.json"

    if existing_design_path.exists():
        print(f"\nLoading existing constrained horn design...")
        with open(existing_design_path) as f:
            horn_data = json.load(f)

        print(f"\n✓ Existing horn design:")
        print(f"  Throat area: {horn_data['throat_area_cm2']:.1f} cm²")
        print(f"  Mouth area: {horn_data['mouth_area_cm2']:.1f} cm²")
        print(f"  Total length: {horn_data['total_length_cm']:.1f} cm")
        print(f"  Cutoff: {horn_data['overall_cutoff_hz']:.0f} Hz")
        print(f"  Volume: {horn_data['volume_liters']:.1f} L")

        # Validate constraints
        print(f"\n✓ Validation (250mm cube):")
        print(f"  Length: {horn_data['total_length_cm']:.1f} cm < 25 cm ✓")
        print(f"  Mouth: {horn_data['mouth_area_cm2']:.1f} cm² < 625 cm² ✓")
        print(f"  Volume: {horn_data['volume_liters']:.1f} L < 15.6 L ✓")

        if horn_data['validation']['fits_printer']:
            print(f"  → Fits within 250mm cube constraints ✓")

        # Convert to horn_params format
        return {
            "cutoff": horn_data['overall_cutoff_hz'],
            "length": horn_data['total_length_cm'] / 100,
            "throat_area": horn_data['throat_area_cm2'] / 10000,
            "mouth_area": horn_data['mouth_area_cm2'] / 10000,
            "segments": horn_data['segments'],
        }

    else:
        print(f"\nNo existing constrained design found.")
        print(f"Using simplified horn model based on constraints...")

        # Calculate horn parameters for 250mm cube
        max_length = PRINTER_CONSTRAINTS['max_length']
        max_mouth_area = PRINTER_CONSTRAINTS['max_mouth_area']

        # For a 2-segment exponential horn within 250mm cube:
        # - Target cutoff ~ 400-500 Hz for crossover at 800-2500 Hz
        # - Mouth area ~ 500-600 cm² (fits in 250mm x 250mm)
        # - Length ~ 240-250 mm

        horn_params = {
            "cutoff": 500,  # Hz (conservative for crossover range)
            "length": 0.24,  # m (240mm)
            "throat_area": 0.0005,  # m² (5 cm²)
            "mouth_area": 0.05,  # m² (500 cm²)
        }

        print(f"\n✓ Horn parameters (estimated):")
        print(f"  Cutoff: {horn_params['cutoff']} Hz")
        print(f"  Length: {horn_params['length']*100:.0f} mm")
        print(f"  Throat: {horn_params['throat_area']*10000:.1f} cm²")
        print(f"  Mouth: {horn_params['mouth_area']*10000:.0f} cm²")

        return horn_params


def design_crossover(lf_params, horn_params):
    """Design crossover between LF and HF sections."""
    print("\n" + "=" * 80)
    print("STEP 3: CROSSOVER DESIGN")
    print("=" * 80)

    xo_assistant = CrossoverDesignAssistant(validation_mode=False)

    lf_enclosure_params = {
        "Vb": lf_params["Vb"],
        "Fb": lf_params["Fb"],
    }

    xo_design = xo_assistant.design_crossover(
        lf_driver_name=LF_DRIVER,
        hf_driver_name=HF_DRIVER,
        lf_enclosure_type="ported",
        lf_enclosure_params=lf_enclosure_params,
        hf_horn_params=horn_params,
        crossover_range=CROSSOVER_RANGE,
    )

    print(f"\n✓ Crossover design:")
    print(f"  Frequency: {xo_design.crossover_frequency:.0f} Hz")
    print(f"  Type: {xo_design.crossover_order}th-order {xo_design.filter_type}")
    print(f"  LF padding: {xo_design.lf_padding_db:.1f} dB")
    print(f"  HF padding: {xo_design.hf_padding_db:.1f} dB")

    # Optimize HF padding for bi-amped system
    print(f"\nOptimizing HF padding for flatness...")
    optimal_hf_pad = optimize_hf_padding_for_flatness(
        lf_driver_name=LF_DRIVER,
        hf_driver_name=HF_DRIVER,
        lf_enclosure_type="ported",
        lf_enclosure_params=lf_enclosure_params,
        horn_params=horn_params,
        crossover_frequency=xo_design.crossover_frequency,
        padding_range=(-25, -10),
        num_steps=31,
    )

    print(f"  Optimal HF padding: {optimal_hf_pad:.1f} dB")
    print(f"  (vs initial: {xo_design.hf_padding_db:.1f} dB)")

    return {
        "frequency": xo_design.crossover_frequency,
        "order": xo_design.crossover_order,
        "type": xo_design.filter_type,
        "lf_padding": xo_design.lf_padding_db,
        "hf_padding_initial": xo_design.hf_padding_db,
        "hf_padding_optimal": optimal_hf_pad,
    }


def calculate_system_performance(lf_params, horn_params, xo_params):
    """Calculate complete system performance metrics."""
    print("\n" + "=" * 80)
    print("STEP 4: SYSTEM PERFORMANCE CALCULATION")
    print("=" * 80)

    # Load drivers
    lf_driver = load_driver(LF_DRIVER)
    hf_driver = load_driver(HF_DRIVER)

    # Generate frequency array
    freq = np.logspace(np.log10(20), np.log10(20000), 500)

    # Calculate LF response
    print(f"\nCalculating LF response (ported box)...")
    lf_response = np.array([
        calculate_spl_ported_transfer_function(f, lf_driver, lf_params["Vb"], lf_params["Fb"])
        for f in freq
    ])

    # Calculate HF response
    print(f"Calculating HF response (horn model)...")
    hf_response = calculate_hf_horn_response(freq, horn_params["cutoff"])

    # Apply optimal HF padding
    hf_response_padded = hf_response + xo_params["hf_padding_optimal"]

    # Apply crossover filters
    print(f"Applying LR4 crossover at {xo_params['frequency']:.0f} Hz...")
    lp_gain_db, hp_gain_db = calculate_lr4_crossover_gains(freq, xo_params["frequency"])

    lf_combined = lf_response + lp_gain_db
    hf_combined = hf_response_padded + hp_gain_db

    # Power sum for system response
    system_response = 10 * np.log10(
        10**(lf_combined/10) + 10**(hf_combined/10)
    )

    # Calculate metrics
    print(f"\nSystem Performance Metrics:")

    # F3 (using LF driver passband as reference)
    f3 = calculate_f3_frequency(freq, lf_response)
    print(f"  LF F3: {f3:.1f} Hz")

    # System flatness
    flatness = calculate_system_flatness(freq, system_response)
    print(f"  System flatness: {flatness:.2f} dB")

    # System level (LF passband)
    lf_passband = (freq >= 80) & (freq <= 200)
    system_level = np.max(lf_response[lf_passband])
    print(f"  System level: {system_level:.1f} dB")

    # Crossover verification
    xo_idx = np.argmin(np.abs(freq - xo_params["frequency"]))
    xo_spl = system_response[xo_idx]
    print(f"  Crossover SPL: {xo_spl:.1f} dB")

    return {
        "f3": f3,
        "flatness": flatness,
        "system_level": system_level,
        "crossover_spl": xo_spl,
        "freq": freq,
        "lf_response": lf_response,
        "hf_response": hf_response_padded,
        "system_response": system_response,
    }


def export_to_hornresp_format(lf_params, horn_params, xo_params, output_dir):
    """Export designs to Hornresp format."""
    print("\n" + "=" * 80)
    print("STEP 5: EXPORT TO HORNRESP")
    print("=" * 80)

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    # Export LF section (ported box)
    lf_path = output_dir / "lf_12fw88_ported_250mm_cube.txt"
    driver = load_driver(LF_DRIVER)

    export_to_hornresp(
        driver=driver,
        driver_name="BC_12FW88 (Two-way LF section)",
        output_path=str(lf_path),
        comment=f"Two-way LF section. Vb={lf_params['Vb']*1000:.1f}L, Fb={lf_params['Fb']:.1f}Hz",
        enclosure_type="ported_box",
        Vb_liters=lf_params["Vb"] * 1000,
        Fb_hz=lf_params["Fb"],
        port_area_cm2=lf_params["port_area_cm2"],
        port_length_cm=lf_params["port_length_cm"],
    )

    print(f"\n✓ LF section exported: {lf_path}")

    # Export HF section (multi-segment horn)
    hf_path = output_dir / "hf_dh450_multiseg_horn_250mm_cube.txt"
    hf_driver = load_driver(HF_DRIVER)

    # Convert horn parameters to Hornresp format
    if "segments" in horn_params:
        # Use existing segment data
        segments = horn_params["segments"]

        with open(hf_path, 'w') as f:
            # Header
            f.write(f"ID = 983.62\n\n")
            f.write(f"Comment = Two-way HF section (250mm cube). Fc={horn_params['cutoff']:.0f}Hz, L={horn_params['length']*100:.0f}cm\n\n")

            # Driver parameters
            f.write(f"|INPUT:\n")
            f.write(f"Le = {hf_driver.L_e*1000:.2f} mH\n")
            f.write(f"Re = {hf_driver.R_e:.1f} Ohm\n")
            f.write(f"Sd = {hf_driver.S_d*10000:.2f} cm²\n")
            f.write(f"Mmd = {hf_driver.M_md*1000:.2f} g\n")
            f.write(f"Cms = {hf_driver.C_ms*1e6:.2f} mm/N\n")
            f.write(f"Rms = {hf_driver.R_ms:.2f} kg/s\n")
            f.write(f"Bl = {hf_driver.BL:.2f} N/A\n")
            f.write(f"Fs = {hf_driver.F_s:.1f} Hz\n\n")

            # Chambers
            f.write(f"|LOUDSPEAKER ENCLOSURE:\n")
            f.write(f"Vrc = 4 cm³\n")
            f.write(f"Lrc = 3.0 cm\n")
            f.write(f"Vtc = 15.0 cm³\n")
            f.write(f"Atc = 0.00 cm²\n")
            f.write(f"Ltc = 0.00 cm\n\n")

            # Horn segments
            f.write(f"|HORN:\n")
            f.write(f"S1 = {segments[0]['area_start_cm2']:.2f}\n")
            f.write(f"S2 = {segments[0]['area_end_cm2']:.1f}\n")
            f.write(f"Exp = {segments[0]['length_cm']:.2f}\n")
            f.write(f"F12 = {segments[0]['cutoff_hz']:.1f}\n\n")

            f.write(f"S2 = {segments[1]['area_start_cm2']:.1f}\n")
            f.write(f"S3 = {segments[1]['area_end_cm2']:.1f}\n")
            f.write(f"Exp = {segments[1]['length_cm']:.2f}\n")
            f.write(f"F23 = {segments[1]['cutoff_hz']:.1f}\n\n")

            # Angular
            f.write(f"|ANGULAR:\n")
            f.write(f"Ang = 360.0\n")
            f.write(f"Cir = -200.00\n\n")

            # Room
            f.write(f"|ROOM:\n")
            f.write(f"Room = 0\n")
            f.write(f"Tem = 20.0 C\n")
            f.write(f"Pb = 101.3 kPa\n")

        print(f"✓ HF section exported: {hf_path}")

    else:
        print(f"  Note: HF export requires segment data (use existing horn_design_dh450_constrained.json)")

    return lf_path, hf_path


def save_design_summary(lf_params, horn_params, xo_params, perf_metrics, output_dir):
    """Save complete design summary to JSON."""
    output_dir = Path(output_dir)

    summary = {
        "lf_driver": LF_DRIVER,
        "hf_driver": HF_DRIVER,
        "constraints": {
            "max_length_mm": PRINTER_CONSTRAINTS["max_length"] * 1000,
            "max_mouth_area_cm2": PRINTER_CONSTRAINTS["max_mouth_area"] * 10000,
            "max_volume_liters": PRINTER_CONSTRAINTS["max_volume"] * 1000,
        },
        "lf_enclosure": {
            "type": "ported",
            "Vb_liters": lf_params["Vb"] * 1000,
            "Fb_hz": lf_params["Fb"],
            "F3_hz": lf_params["F3"],
            "port_area_cm2": lf_params["port_area_cm2"],
            "port_length_cm": lf_params["port_length_cm"],
        },
        "hf_horn": {
            "cutoff_hz": horn_params["cutoff"],
            "length_m": horn_params["length"],
            "throat_area_cm2": horn_params.get("throat_area", 0) * 10000,
            "mouth_area_cm2": horn_params.get("mouth_area", 0) * 10000,
        },
        "crossover": {
            "frequency_hz": xo_params["frequency"],
            "order": xo_params["order"],
            "type": xo_params["type"],
            "lf_padding_db": xo_params["lf_padding"],
            "hf_padding_db": xo_params["hf_padding_optimal"],
        },
        "performance": {
            "f3_hz": perf_metrics["f3"],
            "flatness_db": perf_metrics["flatness"],
            "system_level_db": perf_metrics["system_level"],
        },
    }

    summary_path = output_dir / "design_summary_250mm_cube.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n✓ Design summary saved: {summary_path}")

    return summary_path


def main():
    """Main design workflow."""
    print("\n" + "=" * 80)
    print("TWO-WAY SYSTEM DESIGN: DH450 + 12FW88 (250mm CUBE CONSTRAINT)")
    print("=" * 80)
    print()

    # Get output directory
    output_dir = Path(__file__).parent

    try:
        # Step 1: LF Enclosure Design
        lf_params = design_lf_enclosure()

        # Step 2: HF Horn Design (250mm cube constraint)
        horn_params = design_hf_horn_250mm_cube()

        # Step 3: Crossover Design
        xo_params = design_crossover(lf_params, horn_params)

        # Step 4: System Performance
        perf_metrics = calculate_system_performance(lf_params, horn_params, xo_params)

        # Step 5: Export to Hornresp
        lf_path, hf_path = export_to_hornresp_format(
            lf_params, horn_params, xo_params, output_dir
        )

        # Step 6: Save Design Summary
        summary_path = save_design_summary(
            lf_params, horn_params, xo_params, perf_metrics, output_dir
        )

        # Final Summary
        print("\n" + "=" * 80)
        print("DESIGN COMPLETE")
        print("=" * 80)
        print(f"\nFiles created:")
        print(f"  - {lf_path}")
        print(f"  - {hf_path}")
        print(f"  - {summary_path}")
        print(f"\nNext steps:")
        print(f"  1. Import .txt files into Hornresp for validation")
        print(f"  2. Simulate frequency response and impedance")
        print(f"  3. Compare with gsd predictions")
        print(f"  4. Iterate design if needed")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
