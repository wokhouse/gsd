#!/usr/bin/env python3
"""
Example: Design a Two-Way Loudspeaker System

This example demonstrates the complete workflow for designing a two-way
loudspeaker system using the GSD optimization tools.

The example uses a generic approach that can be adapted to any driver
combination by changing the driver names and constraints.
"""

from gsd.optimization.api.two_way_system import (
    design_two_way_system,
    optimize_hf_padding_for_flatness,
)
from gsd.optimization.api.design_assistant import DesignAssistant
from gsd.optimization.api.crossover_assistant import CrossoverDesignAssistant


def example_basic_two_way():
    """
    Example 1: Basic two-way system design.

    This designs a ported box for the LF driver and uses a compression
    driver with horn for HF, then optimizes the crossover and HF padding.
    """
    print("=" * 70)
    print("EXAMPLE 1: Basic Two-Way System Design")
    print("=" * 70)

    # Define your drivers
    lf_driver = "BC_12FW88"   # 12" mid-bass
    hf_driver = "BC_DH450"    # 1" compression driver

    # Design complete system
    design = design_two_way_system(
        lf_driver_name=lf_driver,
        hf_driver_name=hf_driver,
        lf_enclosure_type="ported",
        crossover_range=(800, 2500),
        optimize_hf_padding=True,
        horn_constraints={
            "max_length": 0.25,      # 250mm max (for 3D printing)
            "max_mouth_area": 0.0625, # 250mm x 250mm
            "max_volume": 0.015625,   # 15.6 L
            "target_cutoff": 400,     # Hz
        },
        population_size=50,
        generations=50,
    )

    print("\n" + str(design))


def example_manual_workflow():
    """
    Example 2: Manual step-by-step workflow.

    This shows each step of the design process separately, giving you
    more control over individual parameters.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Manual Step-by-Step Workflow")
    print("=" * 70)

    # Step 1: Optimize LF enclosure
    print("\n--- Step 1: LF Enclosure Optimization ---")
    assistant = DesignAssistant()

    lf_result = assistant.optimize_design(
        driver_name="BC_12FW88",
        enclosure_type="ported",
        objectives=["f3", "flatness"],
        population_size=50,
        generations=50,
    )

    if not lf_result.success:
        print(f"Optimization failed: {lf_result.warnings}")
        return

    best_lf = lf_result.best_designs[0]
    lf_params = {
        "Vb": best_lf['parameters']['Vb'],
        "Fb": best_lf['parameters']['Fb'],
    }

    print(f"LF enclosure: Vb = {lf_params['Vb']*1000:.1f} L, "
          f"Fb = {lf_params['Fb']:.1f} Hz")
    print(f"Performance: F3 = {best_lf['objectives']['f3']:.1f} Hz, "
          f"Flatness = {best_lf['objectives']['flatness']:.2f} dB")

    # Step 2: Define HF horn parameters
    print("\n--- Step 2: HF Horn Parameters ---")
    horn_params = {
        "cutoff": 400,      # Hz (target)
        "length": 0.24,     # m (240mm)
        "throat_area": 0.00045,  # m² (4.5 cm²)
        "mouth_area": 0.015,     # m² (150 cm²)
    }

    print(f"Horn: Fc = {horn_params['cutoff']} Hz, "
          f"L = {horn_params['length']*100:.0f} mm")

    # Step 3: Design crossover
    print("\n--- Step 3: Crossover Design ---")
    xo_assistant = CrossoverDesignAssistant()

    xo_design = xo_assistant.design_crossover(
        lf_driver_name="BC_12FW88",
        hf_driver_name="BC_DH450",
        lf_enclosure_type="ported",
        lf_enclosure_params=lf_params,
        hf_horn_params=horn_params,
        crossover_range=(800, 2500),
    )

    print(f"Crossover: {xo_design.crossover_frequency:.0f} Hz")
    print(f"Filter: {xo_design.filter_type} {xo_design.crossover_order//2}th order")
    print(f"HF padding: {xo_design.hf_padding_db:.2f} dB")

    # Step 4: Optimize HF padding (bi-amped)
    print("\n--- Step 4: HF Padding Optimization (Bi-amped) ---")
    optimal_pad = optimize_hf_padding_for_flatness(
        lf_driver_name="BC_12FW88",
        hf_driver_name="BC_DH450",
        lf_enclosure_type="ported",
        lf_enclosure_params=lf_params,
        horn_params=horn_params,
        crossover_frequency=xo_design.crossover_frequency,
        padding_range=(-25, -10),
        num_steps=31,
    )

    print(f"Optimal HF padding: {optimal_pad:.2f} dB")
    print(f"  (vs. initial suggestion: {xo_design.hf_padding_db:.2f} dB)")


def example_custom_constraints():
    """
    Example 3: Custom horn size constraints.

    This shows how to design a horn that must fit within specific
    physical constraints (e.g., for 3D printing).
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Custom Horn Size Constraints")
    print("=" * 70)

    # Define physical constraints
    constraints = {
        # Maximum dimensions (for your enclosure/printer)
        "max_length": 0.30,      # 300mm length
        "max_mouth_area": 0.09,  # 300mm x 300mm mouth
        "max_volume": 0.027,     # 27 L total volume

        # Acoustic target
        "target_cutoff": 350,    # 350 Hz cutoff (lower = more bass)
    }

    print(f"Horn Constraints:")
    print(f"  Max length: {constraints['max_length']*100:.0f} mm")
    print(f"  Max mouth: {constraints['max_mouth_area']*1e4:.0f} cm²")
    print(f"  Max volume: {constraints['max_volume']*1000:.1f} L")
    print(f"  Target Fc: {constraints['target_cutoff']} Hz")

    # Design system with constraints
    design = design_two_way_system(
        lf_driver_name="BC_12FW88",
        hf_driver_name="BC_DH450",
        lf_enclosure_type="ported",
        horn_constraints=constraints,
        optimize_hf_padding=True,
    )

    print("\n" + str(design))


def example_sealed_box_two_way():
    """
    Example 4: Two-way system with sealed box LF.

    Sealed boxes have different characteristics than ported boxes
    (typically higher F3, better transient response, smaller size).
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Sealed Box Two-Way System")
    print("=" * 70)

    # Design with sealed LF enclosure
    design = design_two_way_system(
        lf_driver_name="BC_8NDL51",   # 8" woofer (good for sealed)
        hf_driver_name="BC_DE250",    # 1" compression driver
        lf_enclosure_type="sealed",
        crossover_range=(1500, 3500),  # Higher for 8" woofer
        optimize_hf_padding=True,
        horn_constraints={
            "max_length": 0.20,      # More compact for smaller system
            "target_cutoff": 600,     # Higher Fc for smaller horn
        },
        population_size=40,
        generations=40,
    )

    print("\n" + str(design))


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("TWO-WAY LOUDSPEAKER SYSTEM DESIGN EXAMPLES")
    print("=" * 70)

    # Run examples
    example_basic_two_way()
    example_manual_workflow()
    example_custom_constraints()
    example_sealed_box_two_way()

    print("\n" + "=" * 70)
    print("Examples complete!")
    print("=" * 70)
    print("\nTo adapt these examples for your design:")
    print("1. Change driver names to your chosen drivers")
    print("2. Adjust constraints (max_length, target_cutoff, etc.)")
    print("3. Modify crossover_range based on driver capabilities")
    print("4. Tune optimization parameters (population_size, generations)")
    print("\nFor more information, see: docs/two_way_system_workflow.md")


if __name__ == "__main__":
    main()
