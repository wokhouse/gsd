#!/usr/bin/env python3
"""
Interactive two-way system design workflow with user confirmation checkpoints.

Workflow:
1. Design LF enclosure → PAUSE for user confirmation
2. Design HF horn (with crossover-aware objective)
3. Design crossover for the system
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
from gsd.enclosure.ported_box import (
    calculate_spl_ported_transfer_function,
    calculate_ported_box_system_parameters,
)


def design_lf_enclosure_with_confirmation():
    """Design LF enclosure and pause for user confirmation."""
    print("=" * 80)
    print("STEP 1: LF ENCLOSURE DESIGN (BC_12FW88)")
    print("=" * 80)

    assistant = DesignAssistant(validation_mode=False)

    # Optimize for F3 and flatness
    print("\nRunning optimization...")
    result = assistant.optimize_design(
        driver_name="BC_12FW88",
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

    # Calculate port dimensions
    driver = load_driver("BC_12FW88")
    params = calculate_ported_box_system_parameters(driver, Vb, Fb)

    # Calculate box dimensions (assuming cube-ish shape)
    # Add 10% for bracing, driver, port, etc.
    internal_volume_liters = Vb * 1000
    total_volume_liters = internal_volume_liters * 1.1

    # Assuming depth ≈ width, calculate rough external dimensions
    # For a rectangular box: V = W × D × H
    # Let's assume H = 1.2 × W for typical speaker proportions
    # And D = 0.9 × W
    # V_external = W × 0.9W × 1.2W = 1.08 W³
    # W = (V / 1.08)^(1/3)

    import math
    width_m = (total_volume_liters / 1000 / 1.08) ** (1/3)
    depth_m = width_m * 0.9
    height_m = width_m * 1.2

    # Convert to mm
    width_mm = width_m * 1000
    depth_mm = depth_m * 1000
    height_mm = height_m * 1000

    # Display results
    print("\n" + "=" * 80)
    print("LF ENCLOSURE DESIGN RESULTS")
    print("=" * 80)

    print(f"\nAcoustic Design:")
    print(f"  Box volume (Vb): {Vb*1000:.1f} L")
    print(f"  Tuning frequency (Fb): {Fb:.1f} Hz")
    print(f"  F3: {best['objectives']['f3']:.1f} Hz")
    print(f"  Flatness: {best['objectives']['flatness']:.2f} dB")

    print(f"\nPort Design:")
    print(f"  Port area: {params.port_area*10000:.1f} cm²")
    print(f"  Port length: {params.port_length*100:.1f} cm")

    # Calculate round port equivalent
    port_diameter_mm = 2 * math.sqrt((params.port_area * 1e6) / math.pi)
    print(f"  Equivalent round port: {port_diameter_mm:.1f} mm diameter")

    print(f"\nEstimated External Dimensions:")
    print(f"  Width:  {width_mm:.0f} mm")
    print(f"  Depth:  {depth_mm:.0f} mm")
    print(f"  Height: {height_mm:.0f} mm")
    print(f"  (Assuming 18mm MDF, ~10% extra for bracing/driver/port)")

    print(f"\nPanel Sizes (18mm MDF):")
    print(f"  Front baffle: {width_mm:.0f} × {height_mm:.0f} mm")
    print(f"  Side panels: 2 × {depth_mm:.0f} × {height_mm:.0f} mm")
    print(f"  Top/bottom: 2 × {width_mm:.0f} × {depth_mm:.0f} mm")
    print(f"  Back panel: {width_mm:.0f} × {height_mm:.0f} mm")

    # Material estimate
    panel_area_m2 = (
        2 * (width_mm * depth_mm) +
        2 * (width_mm * height_mm) +
        2 * (depth_mm * height_mm)
    ) / 1e6  # Convert mm² to m²

    # Add 15% for saw kerf and mistakes
    panel_area_m2 *= 1.15

    sheets_needed = panel_area_m2 / (1.22 * 2.44)  # Standard 4×8' sheet

    print(f"\nMaterial Requirements:")
    print(f"  Total panel area: {panel_area_m2:.2f} m²")
    print(f"  18mm MDF sheets (4×8'): {sheets_needed:.1f} sheets")

    # Check practicality
    print(f"\nPracticality Check:")

    warnings = []

    if Vb * 1000 > 150:
        warnings.append("⚠️  Large box (>150L) - consider if space allows")

    if Vb * 1000 > 200:
        warnings.append("⚠️  Very large box (>200L) - significant construction challenge")

    if params.port_length * 100 > 30:
        warnings.append(f"⚠️  Long port ({params.port_length*100:.1f} cm) - may need internal elbow")

    if port_diameter_mm > 120:
        warnings.append(f"⚠️  Large port ({port_diameter_mm:.0f} mm) - consider multiple smaller ports")

    if width_mm > 600 or depth_mm > 600 or height_mm > 1000:
        warnings.append("⚠️  Large dimensions - may require internal bracing")

    if warnings:
        for warning in warnings:
            print(f"  {warning}")
    else:
        print(f"  ✓ Design looks practical for home construction")

    # Alternative sizes
    print(f"\nAlternative Size Options:")
    print(f"  If this is too large, consider:")
    print(f"    • Smaller box (higher F3, less bass extension)")
    print(f"    • Sealed box (smaller, tighter bass, higher F3)")
    print(f"    • Different driver (smaller Vas)")

    print("\n" + "=" * 80)
    print("USER CONFIRMATION REQUIRED")
    print("=" * 80)

    while True:
        print("\nOptions:")
        print("  1. Accept this design and continue")
        print("  2. Try a smaller box (trade-off: higher F3)")
        print("  3. Try sealed box (trade-off: higher F3, smaller size)")
        print("  4. Cancel and review manually")

        choice = input("\nEnter choice (1-4): ").strip()

        if choice == "1":
            print("\n✓ Design accepted. Continuing to HF horn design...")
            return {
                "Vb": Vb,
                "Fb": Fb,
                "F3": best['objectives']['f3'],
                "flatness": best['objectives']['flatness'],
                "port_area_cm2": params.port_area * 10000,
                "port_length_cm": params.port_length * 100,
                "external_dims_mm": {
                    "width": width_mm,
                    "depth": depth_mm,
                    "height": height_mm,
                },
            }

        elif choice == "2":
            print("\nRedesigning with smaller box target...")
            # Modify optimization to prefer smaller boxes
            # Use size constraint
            result_smaller = assistant.optimize_design(
                driver_name="BC_12FW88",
                enclosure_type="ported",
                objectives=["f3", "flatness"],
                population_size=50,
                generations=50,
                # TODO: Add size constraint
            )
            # Would need to implement this properly
            print("\n⚠️  Size-constrained optimization not yet implemented.")
            print("   Please accept current design or choose option 3.")
            continue

        elif choice == "3":
            print("\nRedesigning as sealed box...")
            result_sealed = assistant.optimize_design(
                driver_name="BC_12FW88",
                enclosure_type="sealed",
                objectives=["f3", "flatness"],
                population_size=50,
                generations=50,
            )

            if not result_sealed.success:
                print(f"❌ Sealed optimization failed: {result_sealed.warnings}")
                continue

            best_sealed = result_sealed.best_designs[0]
            Vb_sealed = best_sealed['parameters']['Vb']

            # Recalculate dimensions
            total_volume_liters_sealed = Vb_sealed * 1000 * 1.1
            width_m_sealed = (total_volume_liters_sealed / 1000 / 1.08) ** (1/3)
            width_mm_sealed = width_m_sealed * 1000
            depth_mm_sealed = width_mm_sealed * 0.9
            height_mm_sealed = width_mm_sealed * 1.2

            print(f"\nSealed Box Design:")
            print(f"  Vb: {Vb_sealed*1000:.1f} L (vs {Vb*1000:.1f} L ported)")
            print(f"  F3: {best_sealed['objectives']['f3']:.1f} Hz (vs {best['objectives']['f3']:.1f} Hz ported)")
            print(f"  Size: {width_mm_sealed:.0f} × {depth_mm_sealed:.0f} × {height_mm_sealed:.0f} mm")

            choice_sealed = input("\nUse sealed box design? (y/n): ").strip().lower()
            if choice_sealed == 'y':
                return {
                    "Vb": Vb_sealed,
                    "F3": best_sealed['objectives']['f3'],
                    "flatness": best_sealed['objectives']['flatness'],
                    "type": "sealed",
                }
            else:
                continue

        elif choice == "4":
            print("\nCancelling. Design results saved for manual review.")
            # Save results to JSON
            design = {
                "ported_design": {
                    "Vb_liters": Vb * 1000,
                    "Fb_hz": Fb,
                    "F3_hz": best['objectives']['f3'],
                    "flatness_db": best['objectives']['flatness'],
                    "port_area_cm2": params.port_area * 10000,
                    "port_length_cm": params.port_length * 100,
                    "external_dims_mm": {
                        "width": width_mm,
                        "depth": depth_mm,
                        "height": height_mm,
                    },
                },
            }

            output_dir = Path(__file__).parent
            design_path = output_dir / "lf_design_for_review.json"
            with open(design_path, 'w') as f:
                json.dump(design, f, indent=2)

            print(f"Design saved to: {design_path}")
            return None

        else:
            print("\nInvalid choice. Please enter 1, 2, 3, or 4.")


def main():
    """Main workflow with user checkpoints."""
    print("\n" + "=" * 80)
    print("INTERACTIVE TWO-WAY SYSTEM DESIGN")
    print("DH450 (HF) + 12FW88 (LF) - 250mm Cube Constraint")
    print("=" * 80)

    try:
        # Step 1: LF enclosure with confirmation
        lf_params = design_lf_enclosure_with_confirmation()

        if lf_params is None:
            print("\nWorkflow cancelled by user.")
            return 1

        # Step 2: HF horn design
        print("\n" + "=" * 80)
        print("STEP 2: HF HORN DESIGN (with crossover constraints)")
        print("=" * 80)

        print("\n⚠️  DESIGN TRADE-OFF:")
        print("  • 250mm horn length forces Fc ≈ 1865 Hz")
        print("  • Optimal XO should be ~2×Fc ≈ 3700 Hz")
        print("  • But 12FW88 beaming starts ~800 Hz")

        print("\nOptions:")
        print("  1. Use current 250mm horn, XO at ~1500 Hz (compromise)")
        print("  2. Design multi-piece horn (2 sections, total ~500mm)")
        print("  3. Accept higher XO (~2000-2500 Hz)")

        print("\nFor now, using existing 250mm horn design...")
        print("(See horn_design_dh450_constrained.json for details)")

        hf_params = {
            "cutoff_hz": 1865,
            "throat_area_cm2": 7.0,
            "mouth_area_cm2": 504.4,
            "length_cm": 25.0,
        }

        # Step 3: Crossover design
        print("\nProceeding to crossover design...")
        print("(This will be implemented in next step)")

    except KeyboardInterrupt:
        print("\n\nWorkflow cancelled by user.")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
