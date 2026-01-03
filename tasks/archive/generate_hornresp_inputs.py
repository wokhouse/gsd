#!/usr/bin/env python3
"""
Generate Hornresp input files for sealed box validation test cases.

This script creates Hornresp .txt input files for various Qtc alignments
and non-optimal box volumes for BC_8NDL51 and BC_15PS100 drivers.

Usage:
  PYTHONPATH=src python tasks/generate_hornresp_inputs.py

Output:
  Creates input files in tests/validation/drivers/{driver}/sealed_box/
  Files are named: input_qtc{value}.txt or input_vb{volume}L.txt

Literature:
- Small (1972) - Closed-Box Loudspeaker Systems
- Hornresp User Manual - File format specification
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gsd.driver.bc_drivers import get_bc_8ndl51, get_bc_15ps100
from gsd.hornresp.export import export_to_hornresp


def generate_bc_8ndl51_inputs():
    """Generate all input files for BC_8NDL51 driver."""
    driver = get_bc_8ndl51()
    base_dir = Path("tests/validation/drivers/bc_8ndl51/sealed_box")

    print(f"\nGenerating BC_8NDL51 input files...")
    print(f"  Driver: Fs={driver.F_s:.2f}Hz, Qts={driver.Q_ts:.3f}, Vas={driver.V_as*1000:.2f}L")

    test_cases = [
        # (filename, Vb_liters, comment)
        ("input_qtc0.65.txt", 87.83,
         "Qtc=0.65 (near Butterworth): Vb=87.83L, Fc=79.2Hz"),
        ("input_qtc0.8.txt", 14.66,
         "Qtc=0.8 (slight overdamp): Vb=14.66L, Fc=97.5Hz"),
        ("input_qtc1.0.txt", 6.16,
         "Qtc=1.0 (critically damped): Vb=6.16L, Fc=121.8Hz"),
        ("input_qtc1.1.txt", 4.60,
         "Qtc=1.1 (overdamped): Vb=4.60L, Fc=134.0Hz"),
        ("input_vb20L.txt", 20.0,
         "Non-optimal volume: Vb=20L, Qtc=0.755, Fc=92.0Hz"),
    ]

    for filename, Vb_liters, comment in test_cases:
        output_path = base_dir / filename

        export_to_hornresp(
            driver=driver,
            driver_name=f"BC_8NDL51 - {Path(filename).stem}",
            output_path=str(output_path),
            comment=comment,
            enclosure_type="sealed_box",
            Vb_liters=Vb_liters,
        )

        print(f"  ✓ Created: {filename}")

    print(f"  Generated {len(test_cases)} files for BC_8NDL51")


def generate_bc_15ps100_inputs():
    """Generate all input files for BC_15PS100 driver."""
    driver = get_bc_15ps100()
    base_dir = Path("tests/validation/drivers/bc_15ps100/sealed_box")

    print(f"\nGenerating BC_15PS100 input files...")
    print(f"  Driver: Fs={driver.F_s:.2f}Hz, Qts={driver.Q_ts:.3f}, Vas={driver.V_as*1000:.2f}L")

    test_cases = [
        # (filename, Vb_liters, comment)
        # Note: volumes must be >= 28.2L to physically fit the 15" driver
        ("input_qtc0.5.txt", 373.30,
         "Qtc=0.5 (underdamped): Vb=373.30L, Fc=42.2Hz"),
        ("input_qtc0.97.txt", 30.0,
         "Qtc=0.97 (near critical): Vb=30.0L, Fc=81.8Hz (min physical volume)"),
        ("input_vb50L.txt", 50.0,
         "Non-optimal volume: Vb=50L, Qtc=0.779, Fc=65.8Hz"),
        ("input_vb80L.txt", 80.0,
         "Non-optimal volume: Vb=80L, Qtc=0.688, Fc=56.7Hz"),
    ]

    for filename, Vb_liters, comment in test_cases:
        output_path = base_dir / filename

        export_to_hornresp(
            driver=driver,
            driver_name=f"BC_15PS100 - {Path(filename).stem}",
            output_path=str(output_path),
            comment=comment,
            enclosure_type="sealed_box",
            Vb_liters=Vb_liters,
        )

        print(f"  ✓ Created: {filename}")

    print(f"  Generated {len(test_cases)} files for BC_15PS100")


def main():
    """Generate all Hornresp input files."""
    print("=" * 80)
    print("Hornresp Input File Generator")
    print("=" * 80)
    print("\nThis script generates Hornresp input files for sealed box validation.")
    print("Files will be created in: tests/validation/drivers/{driver}/sealed_box/")

    # Create base directories if they don't exist
    Path("tests/validation/drivers/bc_8ndl51/sealed_box").mkdir(parents=True, exist_ok=True)
    Path("tests/validation/drivers/bc_15ps100/sealed_box").mkdir(parents=True, exist_ok=True)

    # Generate input files for both drivers
    generate_bc_8ndl51_inputs()
    generate_bc_15ps100_inputs()

    # Print summary
    print("\n" + "=" * 80)
    print("Generation Complete!")
    print("=" * 80)
    print(f"\nTotal files generated: 9 (5 for BC_8NDL51, 4 for BC_15PS100)")
    print("\nNext steps:")
    print("  1. Import each input file into Hornresp")
    print("  2. Run simulation (10-20000 Hz)")
    print("  3. Export results as sim.txt")
    print("  4. Place sim.txt in the same directory as the input file")
    print("\nExample workflow for one file:")
    print("  1. Open Hornresp")
    print("  2. File → Import → Select tests/validation/drivers/bc_8ndl51/sealed_box/input_qtc0.65.txt")
    print("  3. Calculate the simulation")
    print("  4. Tool → Save → Export _sim.txt")
    print("  5. Save as: tests/validation/drivers/bc_8ndl51/sealed_box/sim_qtc0.65.txt")
    print("=" * 80)


if __name__ == "__main__":
    main()
