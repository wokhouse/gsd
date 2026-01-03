#!/usr/bin/env python3
"""
Test script for hornresp export functionality.

Generates Hornresp .txt files for TC2-4 test cases to verify
the export_front_loaded_horn_to_hornresp() function.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from gsd.simulation import ExponentialHorn
from gsd.hornresp import export_front_loaded_horn_to_hornresp
from gsd.driver.parameters import ThieleSmallParameters


def create_tc4_system():
    """Create the TC4 system (driver + horn + both chambers)."""
    # Create driver (TC4 parameters)
    driver = ThieleSmallParameters(
        M_md=0.008,     # 8g -> 0.008 kg
        C_ms=5.0e-5,    # 5.00E-05 m/N
        R_ms=3.0,       # 3.00 N·s/m
        R_e=6.5,        # 6.50 Ω
        L_e=0.1e-3,     # 0.10 mH -> 0.0001 H
        BL=12.0,        # 12.00 T·m
        S_d=0.0008,     # 8.00 cm² -> 0.0008 m²
    )

    # Create horn (TC4 parameters)
    horn = ExponentialHorn(
        throat_area=0.0005,  # 5.00 cm² -> 0.0005 m²
        mouth_area=0.02,      # 200.00 cm² -> 0.02 m²
        length=0.5,           # 0.500 m
    )

    return driver, horn


def main():
    """Generate Hornresp export files for TC2-4."""
    print("Testing Hornresp export functionality...")
    print()

    driver, horn = create_tc4_system()

    # Output directory
    output_dir = Path(__file__).parent / "hornresp_exports"
    output_dir.mkdir(exist_ok=True)

    # TC2: No chambers
    print("Exporting TC2 (no chambers)...")
    export_front_loaded_horn_to_hornresp(
        driver=driver,
        horn=horn,
        driver_name="TC2_Baseline",
        output_path=str(output_dir / "tc2_baseline.txt"),
        comment="TC2: Driver + Horn (no chambers) - Validation test case",
    )

    # TC3: Throat chamber only
    print("Exporting TC3 (+throat chamber)...")
    export_front_loaded_horn_to_hornresp(
        driver=driver,
        horn=horn,
        driver_name="TC3_ThroatChamber",
        output_path=str(output_dir / "tc3_throat_chamber.txt"),
        comment="TC3: Driver + Horn + Throat Chamber (50cm³) - Validation test case",
        V_tc_liters=0.05,  # 50 cm³
        A_tc_cm2=5.0,      # 5 cm² throat chamber area
    )

    # TC4: Both chambers
    print("Exporting TC4 (+both chambers)...")
    export_front_loaded_horn_to_hornresp(
        driver=driver,
        horn=horn,
        driver_name="TC4_BothChambers",
        output_path=str(output_dir / "tc4_both_chambers.txt"),
        comment="TC4: Driver + Horn + Throat Chamber (50cm³) + Rear Chamber (2.0L) - Validation test case",
        V_tc_liters=0.05,  # 50 cm³ throat chamber
        A_tc_cm2=5.0,      # 5 cm² throat chamber area
        V_rc_liters=2.0,   # 2.0 L rear chamber
        L_rc_cm=12.6,      # 12.6 cm rear chamber depth
    )

    print()
    print("=" * 70)
    print("✓ Export complete!")
    print()
    print(f"Generated files in: {output_dir}")
    print("  - tc2_baseline.txt")
    print("  - tc3_throat_chamber.txt")
    print("  - tc4_both_chambers.txt")
    print()
    print("You can now import these files into Hornresp to verify they match")
    print("the original TC2-4 test parameters.")
    print("=" * 70)


if __name__ == "__main__":
    main()
