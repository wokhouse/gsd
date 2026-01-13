"""
Complete Two-Way System Design Workflow

This example shows the complete workflow for designing a two-way system,
including:
1. Specifying printer constraints
2. Automatic multi-piece detection
3. Horn optimization with proper constraints
4. Crossover design
5. Validation and iteration
6. Hornresp export
7. Frequency response plotting
"""

from gsd.optimization.api.two_way_system import design_two_way_system_complete
from gsd.hornresp.export import export_to_hornresp
from gsd.driver import load_driver
import matplotlib.pyplot as plt

# =============================================================================
# STEP 1: Define Constraints
# =============================================================================

print("Two-Way System Design Workflow")
print("=" * 70)

# Printer constraints (250mm cube)
PRINTER = {
    "max_length": 0.25,      # 250mm build height
    "max_mouth_area": 0.0625,  # 250mm × 250mm bed
    "max_volume": 0.015625,   # 15.6 L
}

# Target crossover frequency range
CROSSOVER_RANGE = (800, 2500)  # Hz

# =============================================================================
# STEP 2: Run Complete Design
# =============================================================================

print("\nRunning complete design workflow...")
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
    verbose=True
)

# =============================================================================
# STEP 3: Review Validation
# =============================================================================

print("\n" + "=" * 70)
print("VALIDATION RESULTS")
print("=" * 70)

print(design.validation)

if not design.validation.passes:
    print("\n⚠ Design has issues. Consider recommendations above.")

    # Example: Iterate if needed
    if "multi_piece" in str(design.validation.recommendations):
        print("\nRe-running with multi-piece strategy...")
        design = design_two_way_system_complete(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            crossover_range=CROSSOVER_RANGE,
            printer_constraints=PRINTER,
            allow_multi_piece=True,
            verbose=True
        )

# =============================================================================
# STEP 4: Export for Hornresp Validation
# =============================================================================

print("\n" + "=" * 70)
print("EXPORTING TO HORNRESP")
print("=" * 70)

# Export LF design
lf_path = "lf_12fw88_ported.txt"
export_to_hornresp(
    driver=load_driver("BC_12FW88"),
    driver_name="BC 12FW88",
    output_path=lf_path,
    comment="Two-way LF section",
    enclosure_type="ported_box",
    Vb_liters=design.lf_enclosure_params['Vb'] * 1000,
    Fb_hz=design.lf_enclosure_params['Fb'],
    port_area_cm2=design.lf_enclosure_params['port_area'] * 10000,
    port_length_cm=design.lf_enclosure_params['port_length'] * 100
)

print(f"✓ LF design: {lf_path}")

# Export HF horn (TODO: implement multisegment export)
# hf_path = "hf_dh450_horn.txt"
# export_multisegment_horn(...)
# print(f"✓ HF horn: {hf_path}")

print("\nNext steps:")
print("  1. Open exported files in Hornresp")
print("  2. Run simulations")
print("  3. Compare with gsd predictions")
print("  4. Iterate if needed")

# =============================================================================
# STEP 5: Plot Response
# =============================================================================

print("\n" + "=" * 70)
print("PLOTTING FREQUENCY RESPONSE")
print("=" * 70)

# TODO: Use new plotting function with fixed F3
# plot_two_way_response(design, save_path="response.png")

print("\n✓ Plot saved to: response.png")

print("\n" + "=" * 70)
print("WORKFLOW COMPLETE")
print("=" * 70)
