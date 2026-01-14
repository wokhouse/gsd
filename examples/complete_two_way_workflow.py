"""
Complete Two-Way System Design Workflow

This example shows the complete workflow for designing a two-way system.

IMPORTANT: Use the integrated approach for one-shot design success!

The NEW integrated workflow:
1. Calculates horn requirements BEFORE optimization
2. Works backwards from target XO to required Fc
3. Checks feasibility against printer constraints
4. Optimizes crossover by sweep (doesn't assume 2×Fc)
5. Returns validated design in ONE function call

The old sequential workflow is still supported but requires manual iteration.

Literature:
- Olson (1947) - Horn cutoff and operating range
- Beranek (1954) - Directivity and beaming
- Case study: docs/two_way_design_review_12fw88_dh450.md
"""

from gsd.optimization.api.two_way_system import (
    design_two_way_system_complete,
    design_two_way_system_integrated
)
from gsd.hornresp.export import export_to_hornresp
from gsd.driver import load_driver
import matplotlib.pyplot as plt


# =============================================================================
# EXAMPLE 1: INTEGRATED DESIGN (RECOMMENDED)
# =============================================================================

def example_integrated_design():
    """
    NEW: One-shot design with integrated horn/crossover optimization.

    This is the recommended approach that considers horn geometry and
    crossover as an integrated system, ensuring success on the first try.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 1: INTEGRATED TWO-WAY DESIGN (RECOMMENDED)")
    print("=" * 70)

    # Printer constraints (250mm cube)
    PRINTER = {
        "max_length": 0.25,      # 250mm build height
        "max_mouth_area": 0.0625,  # 250mm × 250mm bed
    }

    # Target crossover frequency
    TARGET_XO = 800  # Hz

    print(f"\nRunning integrated design...")
    print(f"  LF driver: BC 12FW88")
    print(f"  HF driver: BC DH450")
    print(f"  Target XO: {TARGET_XO} Hz")
    print(f"  Printer: {PRINTER['max_length']*1000:.0f}mm cube")

    design = design_two_way_system_integrated(
        lf_driver_name="BC_12FW88",
        hf_driver_name="BC_DH450",
        target_crossover_hz=TARGET_XO,
        printer_constraints=PRINTER,
        enclosure_type="ported",
        xo_fc_ratio=2.0,  # Traditional 2×Fc rule
        accept_sensitivity_loss=True,  # Allow smaller mouth for better integration
        verbose=True
    )

    # Review results
    print("\n" + "=" * 70)
    print("DESIGN RESULTS")
    print("=" * 70)

    print(f"\nHorn Parameters:")
    print(f"  Throat: {design.horn_params['throat_area']*10000:.1f} cm²")
    print(f"  Mouth: {design.horn_params['mouth_area']*10000:.0f} cm²")
    print(f"  Length: {design.horn_params['length']*100:.0f} cm")
    print(f"  Fc: {design.horn_fc_hz:.0f} Hz")

    print(f"\nCrossover:")
    print(f"  Frequency: {design.crossover_frequency:.0f} Hz")
    print(f"  XO/Fc ratio: {design.crossover_frequency/design.horn_fc_hz:.2f}")
    print(f"  HF padding: {design.hf_padding_db:.1f} dB")

    print(f"\nPerformance:")
    print(f"  F3: {design.f3:.1f} Hz")
    print(f"  Dip: {design.dip_db:.2f} dB")
    print(f"  Flatness: {design.flatness:.2f} dB")

    print(f"\nValidation:")
    print(f"  Rating: {design.validation['rating']}")
    print(f"  Passes: {design.validation['passes']}")

    return design


# =============================================================================
# EXAMPLE 2: PHYSICS-FIRST APPROACH
# =============================================================================

def example_physics_first_approach():
    """
    Calculate requirements BEFORE optimizing.

    This shows how to use the horn_physics module to understand
    requirements before running the optimizer.
    """
    from gsd.optimization.api.horn_physics import (
        calculate_lf_beaming_frequency,
        calculate_target_horn_fc,
        calculate_mouth_area_for_fc,
        assess_mouth_area_feasibility
    )

    print("\n" + "=" * 70)
    print("EXAMPLE 2: PHYSICS-FIRST APPROACH")
    print("=" * 70)

    # Load drivers
    lf_driver = load_driver("BC_12FW88")
    hf_driver = load_driver("BC_DH450")

    # Step 1: Calculate LF beaming frequency
    f_beam = calculate_lf_beaming_frequency(lf_driver)
    print(f"\nLF Driver Analysis:")
    print(f"  Beaming frequency: {f_beam:.0f} Hz")

    # Step 2: Calculate target horn Fc from XO target
    target_xo = 800  # Hz
    target_fc = calculate_target_horn_fc(target_xo, f_beam, xo_fc_ratio=2.0)
    print(f"\nHorn Requirements:")
    print(f"  Target XO: {target_xo} Hz")
    print(f"  Target Fc: {target_fc:.0f} Hz (XO/Fc = {target_xo/target_fc:.2f})")

    # Step 3: Calculate required mouth area
    horn_length = 25.0  # cm (250mm)
    throat_area = hf_driver.S_d * 10000  # m² to cm²
    required_mouth = calculate_mouth_area_for_fc(
        throat_area, horn_length, target_fc
    )
    print(f"  Required mouth: {required_mouth:.0f} cm²")

    # Step 4: Check feasibility
    max_mouth = 625  # cm² (250mm × 250mm)
    feasibility = assess_mouth_area_feasibility(
        required_mouth, max_mouth, target_fc, throat_area, horn_length
    )

    print(f"\nFeasibility Check:")
    print(f"  Available mouth: {max_mouth:.0f} cm²")
    if feasibility['feasible']:
        print(f"  ✓ {feasibility['recommendation']}")
    else:
        print(f"  ✗ {feasibility['recommendation']}")
        print(f"    Resulting Fc: {feasibility['resulting_fc_hz']:.0f} Hz")
        print(f"    Sensitivity penalty: {feasibility['sensitivity_penalty_db']:+.1f} dB")


# =============================================================================
# EXAMPLE 3: OLD SEQUENTIAL WORKFLOW (STILL SUPPORTED)
# =============================================================================

def example_sequential_workflow():
    """
    Original sequential workflow (still supported).

    This approach designs LF and HF independently, then attempts to make
    the crossover work. May require iteration for acceptable results.
    """

def example_sequential_workflow():
    """
    Original sequential workflow (still supported).

    This approach designs LF and HF independently, then attempts to make
    the crossover work. May require iteration for acceptable results.
    """
    # Printer constraints (250mm cube)
    PRINTER = {
        "max_length": 0.25,      # 250mm build height
        "max_mouth_area": 0.0625,  # 250mm × 250mm bed
        "max_volume": 0.015625,   # 15.6 L
    }

    # Target crossover frequency range
    CROSSOVER_RANGE = (800, 2500)  # Hz

    print("\nRunning sequential design workflow...")
    print(f"  LF driver: BC 12FW88")
    print(f"  HF driver: BC DH450")
    print(f"  Crossover range: {CROSSOVER_RANGE[0]}-{CROSSOVER_RANGE[1]} Hz")
    print(f"  Printer: {PRINTER['max_length']*1000:.0f}mm cube")

    design = design_two_way_system_complete(
        lf_driver_name="BC_12FW88",
        hf_driver_name="BC_DH450",
        crossover_range=CROSSOVER_RANGE,
        printer_constraints=PRINTER,
        allow_multi_piece=True,
        verbose=False  # Less verbose for this example
    )

    print(f"\nResults:")
    print(f"  F3: {design.f3:.1f} Hz")
    print(f"  Flatness: {design.flatness:.2f} dB")

    return design


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import sys

    print("\n" + "=" * 70)
    print("TWO-WAY SYSTEM DESIGN WORKFLOW EXAMPLES")
    print("=" * 70)

    # Run integrated design (recommended)
    print("\n" + "=" * 70)
    print("Running: Integrated Design (Recommended)")
    print("=" * 70)

    design = example_integrated_design()

    # Optionally run other examples
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        print("\n\nRunning additional examples...")

        # Physics-first approach
        example_physics_first_approach()

        # Sequential workflow (for comparison)
        example_sequential_workflow()

    print("\n" + "=" * 70)
    print("EXAMPLES COMPLETE")
    print("=" * 70)

    print("\nRecommendation:")
    print("  Use design_two_way_system_integrated() for one-shot design success.")
    print("  See docs/two_way_design_review_12fw88_dh450.md for case study.")

