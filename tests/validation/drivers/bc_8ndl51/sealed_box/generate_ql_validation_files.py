#!/usr/bin/env python3
"""
Generate Hornresp input files for BC 8NDL51 sealed box QL validation.

This script creates Hornresp input files for various QL (box losses) values
to validate viberesp's Quc implementation.

Usage:
    PYTHONPATH=src python generate_ql_validation_files.py
"""

from pathlib import Path
from gsd.driver import load_driver

# Sealed box design (fixed)
Vb_liters = 10.0  # 10L box

# QL variations to test
ql_values = [5, 7, 10, 20, 100]

# Base directory
base_dir = Path("tests/validation/drivers/bc_8ndl51/sealed_box")

# Generate input files for each QL value
for ql in ql_values:
    ql_dir = base_dir / f"ql{ql}"
    ql_dir.mkdir(exist_ok=True)

    # Create Hornresp input file
    input_file = ql_dir / "input.txt"

    export_to_hornresp(
        driver=driver,
        driver_name=f"BC 8NDL51 Sealed Box QL={ql}",
        output_path=str(input_file),
        comment=f"QL={ql} validation - Vb={Vb_liters}L sealed box. "
                f"IMPORTANT: Double-click QL label in Hornresp and set to {ql}",
        enclosure_type="sealed_box",
        Vb_liters=Vb_liters,
    )

    print(f"✅ Created: {input_file}")
    print(f"   → QL={ql}, Vb={Vb_liters}L")

print("\n" + "="*60)
print("Next steps:")
print("="*60)
print("1. For each QL directory:")
print("   a. Open Hornresp")
print("   b. File → Import → Select input.txt")
print("   c. Double-click 'QL' label and set to the directory's QL value")
print("   d. Tools → Loudspeaker Wizard → Calculate")
print("   e. Tools → Export → Angular Frequency")
print("   f. Save as sim.txt in the same directory")
print()
print("2. Run validation tests:")
print("   PYTHONPATH=src pytest tests/validation/test_ql_box_losses.py -v")
print()
