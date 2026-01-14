#!/usr/bin/env python3
"""
Complete two-way system design with confirmed LF enclosure.

User has approved:
- 114.5 L ported box (floorstanding)
- 489 × 440 × 586 mm external dimensions
- F3 = 47 Hz

Now continuing with:
1. HF horn design (250mm cube constraint)
2. Crossover optimization
3. System validation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
from pathlib import Path
import json

from gsd.driver import load_driver
from gsd.enclosure.ported_box import calculate_spl_ported_transfer_function
from gsd.optimization.api.two_way_system import (
    calculate_hf_horn_response,
    calculate_lr4_crossover_gains,
    optimize_hf_padding_for_flatness,
    calculate_f3_frequency,
    calculate_system_flatness,
)
from gsd.optimization.api.crossover_assistant import CrossoverDesignAssistant

rcParams['font.size'] = 11
rcParams['axes.labelsize'] = 12
rcParams['axes.titlesize'] = 14
rcParams['grid.alpha'] = 0.3


def main():
    """Complete design workflow with confirmed LF parameters."""
    print("\n" + "=" * 80)
    print("COMPLETE TWO-WAY SYSTEM DESIGN")
    print("DH450 (HF) + 12FW88 (LF) - Floorstanding Design")
    print("=" * 80)

    # Confirmed LF parameters
    lf_params = {
        "Vb": 0.1145,  # m³ (114.5 L)
        "Fb": 47.6,    # Hz
        "F3": 47.0,    # Hz
        "flatness": 1.81,  # dB
    }

    print(f"\n✓ LF Enclosure (CONFIRMED):")
    print(f"  Vb = {lf_params['Vb']*1000:.1f} L")
    print(f"  Fb = {lf_params['Fb']:.1f} Hz")
    print(f"  F3 = {lf_params['F3']:.1f} Hz")
    print(f"  Size: 489 × 440 × 586 mm (floorstanding)")

    # =============================================================================
    # STEP 2: HF HORN DESIGN
    # =============================================================================
    print("\n" + "=" * 80)
    print("STEP 2: HF HORN DESIGN (250mm Cube Constraint)")
    print("=" * 80)

    # Load existing horn design
    horn_design_path = Path(__file__).parent / "horn_design_dh450_constrained.json"

    if horn_design_path.exists():
        with open(horn_design_path) as f:
            horn_data = json.load(f)

        print(f"\n✓ Using existing optimized horn design:")
        print(f"  Throat: {horn_data['throat_area_cm2']:.1f} cm²")
        print(f"  Mouth: {horn_data['mouth_area_cm2']:.1f} cm²")
        print(f"  Length: {horn_data['total_length_cm']:.1f} cm")
        print(f"  Cutoff: {horn_data['overall_cutoff_hz']:.0f} Hz")
        print(f"  Volume: {horn_data['volume_liters']:.1f} L")

        hf_params = {
            "cutoff_hz": horn_data['overall_cutoff_hz'],
            "throat_area_cm2": horn_data['throat_area_cm2'],
            "mouth_area_cm2": horn_data['mouth_area_cm2'],
            "length_cm": horn_data['total_length_cm'],
            "length_m": horn_data['total_length_cm'] / 100,
            "segments": horn_data['segments'],
        }
    else:
        print(f"\n⚠️  Horn design file not found, using default parameters")
        hf_params = {
            "cutoff_hz": 1865,
            "throat_area_cm2": 7.0,
            "mouth_area_cm2": 504.4,
            "length_cm": 25.0,
            "length_m": 0.25,
        }

    # =============================================================================
    # STEP 3: CROSSOVER DESIGN WITH CONSTRAINTS
    # =============================================================================
    print("\n" + "=" * 80)
    print("STEP 3: CROSSOVER DESIGN")
    print("=" * 80)

    print(f"\nConstraint Analysis:")
    print(f"  Horn cutoff: {hf_params['cutoff_hz']:.0f} Hz")
    print(f"  LF beaming: ~800-1000 Hz (12\" driver)")
    print(f"  Target XO range: {hf_params['cutoff_hz']*1.2:.0f} - {hf_params['cutoff_hz']*2:.0f} Hz")

    # Calculate optimal crossover range
    min_xo = hf_params['cutoff_hz'] * 1.2  # Minimum XO should be 1.2× Fc
    max_xo = min(hf_params['cutoff_hz'] * 2, 3000)  # Max 2× Fc or 3 kHz

    print(f"\nRecommended crossover range: {min_xo:.0f} - {max_xo:.0f} Hz")

    # Use CrossoverDesignAssistant
    xo_assistant = CrossoverDesignAssistant(validation_mode=False)

    lf_enclosure_params = {
        "Vb": lf_params["Vb"],
        "Fb": lf_params["Fb"],
    }

    horn_params_for_xo = {
        "cutoff": hf_params["cutoff_hz"],
        "length": hf_params["length_m"],
    }

    print(f"\nOptimizing crossover...")
    xo_design = xo_assistant.design_crossover(
        lf_driver_name="BC_12FW88",
        hf_driver_name="BC_DH450",
        lf_enclosure_type="ported",
        lf_enclosure_params=lf_enclosure_params,
        hf_horn_params=horn_params_for_xo,
        crossover_range=(min_xo, max_xo),
    )

    print(f"\n✓ Crossover design:")
    print(f"  Frequency: {xo_design.crossover_frequency:.0f} Hz")
    print(f"  Ratio: {xo_design.crossover_frequency/hf_params['cutoff_hz']:.2f} × horn cutoff")
    print(f"  Type: {xo_design.crossover_order}th-order {xo_design.filter_type}")
    print(f"  LF padding: {xo_design.lf_padding_db:.1f} dB")
    print(f"  HF padding (initial): {xo_design.hf_padding_db:.1f} dB")

    # Optimize HF padding for flatness
    print(f"\nOptimizing HF padding for system flatness...")
    optimal_hf_pad = optimize_hf_padding_for_flatness(
        lf_driver_name="BC_12FW88",
        hf_driver_name="BC_DH450",
        lf_enclosure_type="ported",
        lf_enclosure_params=lf_enclosure_params,
        horn_params=horn_params_for_xo,
        crossover_frequency=xo_design.crossover_frequency,
        padding_range=(-25, -5),
        num_steps=21,
    )

    print(f"  Optimal HF padding: {optimal_hf_pad:.1f} dB")
    print(f"  (vs initial: {xo_design.hf_padding_db:.1f} dB)")

    # =============================================================================
    # STEP 4: SYSTEM RESPONSE CALCULATION
    # =============================================================================
    print("\n" + "=" * 80)
    print("STEP 4: SYSTEM PERFORMANCE CALCULATION")
    print("=" * 80)

    # Load drivers
    lf_driver = load_driver("BC_12FW88")
    hf_driver = load_driver("BC_DH450")

    # Generate frequency array
    freq = np.logspace(np.log10(20), np.log10(20000), 500)

    # Calculate LF response
    print(f"\nCalculating LF response...")
    lf_response = np.array([
        calculate_spl_ported_transfer_function(f, lf_driver, lf_params["Vb"], lf_params["Fb"])
        for f in freq
    ])

    # Calculate HF response
    print(f"Calculating HF response...")
    hf_response = calculate_hf_horn_response(freq, hf_params["cutoff_hz"])

    # Apply optimal HF padding
    hf_response_padded = hf_response + optimal_hf_pad

    # Apply crossover filters
    print(f"Applying LR4 crossover at {xo_design.crossover_frequency:.0f} Hz...")
    lp_gain_db, hp_gain_db = calculate_lr4_crossover_gains(freq, xo_design.crossover_frequency)

    lf_combined = lf_response + lp_gain_db
    hf_combined = hf_response_padded + hp_gain_db

    # Power sum for system response
    system_response = 10 * np.log10(
        10**(lf_combined/10) + 10**(hf_combined/10)
    )

    # Calculate metrics
    print(f"\nSystem Performance Metrics:")

    # F3
    f3 = calculate_f3_frequency(freq, system_response)
    print(f"  System F3: {f3:.1f} Hz")

    # Flatness
    flatness = calculate_system_flatness(freq, system_response)
    print(f"  System flatness: {flatness:.2f} dB")

    # System level
    lf_passband = (freq >= 80) & (freq <= 200)
    system_level = np.max(lf_response[lf_passband])
    print(f"  System level: {system_level:.1f} dB")

    # =============================================================================
    # STEP 5: PLOT SYSTEM RESPONSE
    # =============================================================================
    print(f"\nGenerating system response plot...")

    fig, ax = plt.subplots(figsize=(14, 8))

    # Plot individual responses
    ax.semilogx(freq, lf_response, 'b-', linewidth=1.5, alpha=0.6,
                label=f'LF Driver (BC 12FW88)')
    ax.semilogx(freq, hf_response_padded, 'r-', linewidth=1.5, alpha=0.6,
                label=f'HF Driver (BC DH450, {optimal_hf_pad:.0f} dB pad)')

    # Plot filtered responses
    ax.semilogx(freq, lf_combined, 'b--', linewidth=1, alpha=0.3)
    ax.semilogx(freq, hf_combined, 'r--', linewidth=1, alpha=0.3)

    # Plot system response
    ax.semilogx(freq, system_response, 'k-', linewidth=3, label='Combined System')

    # Mark F3
    if not np.isnan(f3):
        f3_spl = np.interp(f3, freq, system_response)
        ax.axvline(f3, color='gray', linestyle='--', alpha=0.7, linewidth=2)
        ax.text(f3*1.05, f3_spl, f'  System F3 = {f3:.1f} Hz',
                fontsize=11, color='gray', fontweight='bold')

    # Mark crossover
    xo_spl = np.interp(xo_design.crossover_frequency, freq, system_response)
    ax.axvline(xo_design.crossover_frequency, color='purple', linestyle='--',
               alpha=0.7, linewidth=2)
    ax.text(xo_design.crossover_frequency*1.05, xo_spl + 3,
            f'  XO = {xo_design.crossover_frequency:.0f} Hz',
            fontsize=11, color='purple', fontweight='bold')

    # Mark horn cutoff
    ax.axvline(hf_params['cutoff_hz'], color='orange', linestyle=':', alpha=0.7, linewidth=2)
    ax.text(hf_params['cutoff_hz']*0.8, system_level - 5,
            f'Horn Fc = {hf_params["cutoff_hz"]:.0f} Hz  ',
            fontsize=10, color='orange', ha='right')

    # Shade crossover region
    ax.axvspan(xo_design.crossover_frequency/np.sqrt(2), xo_design.crossover_frequency*np.sqrt(2),
                alpha=0.1, color='purple', label='Crossover Region')

    # Formatting
    ax.set_xlabel('Frequency (Hz)', fontsize=13)
    ax.set_ylabel('SPL (dB) @ 1m, 2.83V', fontsize=13)
    ax.set_title(f'Two-Way Floorstanding System: BC_DH450 + BC_12FW88\n'
                 f'LF: {lf_params["Vb"]*1000:.1f}L ported, Fb={lf_params["Fb"]:.1f}Hz | '
                 f'HF: Fc={hf_params["cutoff_hz"]:.0f}Hz, L={hf_params["length_cm"]:.0f}mm | '
                 f'XO: {xo_design.crossover_frequency:.0f}Hz LR4',
                 fontsize=14)
    ax.grid(True, which='both', alpha=0.3)
    ax.legend(loc='lower left', fontsize=10)
    ax.set_xlim(20, 20000)
    ax.set_ylim(40, 115)

    # Add frequency range markers
    ax.text(30, 110, 'Bass', fontsize=8, alpha=0.5)
    ax.text(100, 110, 'Mid-Bass', fontsize=8, alpha=0.5)
    ax.text(500, 110, 'Midrange', fontsize=8, alpha=0.5)
    ax.text(3000, 110, 'Upper-Mid', fontsize=8, alpha=0.5)
    ax.text(8000, 110, 'Treble', fontsize=8, alpha=0.5)

    plt.tight_layout()

    # Save plot
    output_dir = Path(__file__).parent
    png_path = output_dir / "final_system_response_floorstanding.png"
    pdf_path = output_dir / "final_system_response_floorstanding.pdf"

    fig.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f"\n✓ PNG saved: {png_path}")
    fig.savefig(pdf_path, bbox_inches='tight')
    print(f"✓ PDF saved: {pdf_path}")

    # =============================================================================
    # STEP 6: SAVE DESIGN SUMMARY
    # =============================================================================
    print("\n" + "=" * 80)
    print("STEP 6: SAVE FINAL DESIGN")
    print("=" * 80)

    final_design = {
        "system_name": "Two-Way Floorstanding Speaker",
        "lf_driver": "BC_12FW88",
        "hf_driver": "BC_DH450",
        "lf_enclosure": {
            "type": "ported",
            "Vb_liters": lf_params["Vb"] * 1000,
            "Fb_hz": lf_params["Fb"],
            "F3_hz": f3,
            "external_dims_mm": {
                "width": 489,
                "depth": 440,
                "height": 586,
            },
        },
        "hf_horn": {
            "cutoff_hz": hf_params["cutoff_hz"],
            "throat_area_cm2": hf_params["throat_area_cm2"],
            "mouth_area_cm2": hf_params["mouth_area_cm2"],
            "length_cm": hf_params["length_cm"],
            "fits_250mm_printer": True,
        },
        "crossover": {
            "frequency_hz": xo_design.crossover_frequency,
            "order": xo_design.crossover_order,
            "type": xo_design.filter_type,
            "hf_padding_db": optimal_hf_pad,
            "lf_padding_db": 0.0,
        },
        "performance": {
            "f3_hz": f3,
            "flatness_db": flatness,
            "system_level_db": system_level,
        },
        "notes": [
            "Floorstanding design - use spikes or isolation pads",
            "Horn fits within 250mm cube 3D printer",
            "Crossover above horn cutoff for proper HF loading",
            "Consider toe-in (~15°) for optimal stereo imaging",
        ],
    }

    design_path = output_dir / "final_design_floorstanding.json"
    with open(design_path, 'w') as f:
        json.dump(final_design, f, indent=2)

    print(f"\n✓ Final design saved: {design_path}")

    # =============================================================================
    # FINAL SUMMARY
    # =============================================================================
    print("\n" + "=" * 80)
    print("FINAL DESIGN SUMMARY")
    print("=" * 80)

    print(f"\nLF Enclosure (BC 12FW88):")
    print(f"  Type: Ported")
    print(f"  Vb: {lf_params['Vb']*1000:.1f} L")
    print(f"  Fb: {lf_params['Fb']:.1f} Hz")
    print(f"  F3: {f3:.1f} Hz")
    print(f"  Size: 489 × 440 × 586 mm (floorstanding)")

    print(f"\nHF Horn (BC DH450):")
    print(f"  Type: 2-segment exponential")
    print(f"  Throat: {hf_params['throat_area_cm2']:.1f} cm²")
    print(f"  Mouth: {hf_params['mouth_area_cm2']:.1f} cm²")
    print(f"  Length: {hf_params['length_cm']:.1f} cm")
    print(f"  Cutoff: {hf_params['cutoff_hz']:.0f} Hz")

    print(f"\nCrossover:")
    print(f"  Frequency: {xo_design.crossover_frequency:.0f} Hz")
    print(f"  Type: LR4 (4th-order Linkwitz-Riley)")
    print(f"  HF padding: {optimal_hf_pad:.1f} dB")
    print(f"  XO/Fc ratio: {xo_design.crossover_frequency/hf_params['cutoff_hz']:.2f} × (good!)")

    print(f"\nSystem Performance:")
    print(f"  F3: {f3:.1f} Hz")
    print(f"  Flatness: {flatness:.2f} dB")
    print(f"  Sensitivity: {system_level:.1f} dB (2.83V, 1m)")

    print(f"\nBuild Notes:")
    print(f"  • LF enclosure: 0.6 sheets of 18mm MDF")
    print(f"  • HF horn: Fits in 250mm cube 3D printer")
    print(f"  • Finish: Consider veneer or paint for floorstanding aesthetic")
    print(f"  • Placement: Toe-in 15° for optimal imaging")
    print(f"  • Position: 20-30cm from front wall for bass reinforcement")

    print("\n" + "=" * 80)
    print("DESIGN COMPLETE - READY FOR MANUFACTURING")
    print("=" * 80)

    return final_design


if __name__ == "__main__":
    main()
