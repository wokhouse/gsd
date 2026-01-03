#!/usr/bin/env python3
"""
Calculate sealed box volumes for target Qtc alignments.

This script calculates the required box volume Vb to achieve a target
system Q (Qtc) for a given driver, based on Small (1972) sealed box theory.

Formula derivation:
  Qtc = Qts × √(1 + Vas/Vb)
  Qtc²/Qts² = 1 + Vas/Vb
  Vb = Vas / (Qtc²/Qts² - 1)

Usage:
  PYTHONPATH=src python tasks/calculate_sealed_box_volumes.py

Literature:
- Small (1972) - Closed-Box Loudspeaker Systems Part I: Analysis
- literature/thiele_small/small_1972_closed_box.md
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gsd.driver.bc_drivers import get_bc_8ndl51, get_bc_15ps100
from gsd.enclosure.sealed_box import calculate_sealed_box_system_parameters


def calculate_vb_for_qtc(driver, target_qtc: float) -> tuple[float, float, float]:
    """
    Calculate required box volume for target Qtc alignment.

    Args:
        driver: ThieleSmallParameters instance
        target_qtc: Desired system Q factor

    Returns:
        (Vb_liters, Fc_hz, actual_qtc) - Box volume in liters, system resonance,
                                           and actual Qtc achieved
    """
    # Rearrange Qtc = Qts × √(1 + Vas/Vb) to solve for Vb
    # Vb = Vas / (Qtc²/Qts² - 1)

    ratio = (target_qtc ** 2) / (driver.Q_ts ** 2)
    Vb_m3 = driver.V_as / (ratio - 1)
    Vb_liters = Vb_m3 * 1000

    # Calculate actual system parameters
    params = calculate_sealed_box_system_parameters(driver, Vb_m3)

    return Vb_liters, params.Fc, params.Qtc


def print_driver_table(driver, driver_name: str, qtc_values: list[float]):
    """Print table of box volumes for different Qtc alignments."""
    print(f"\n{'=' * 80}")
    print(f"{driver_name} Sealed Box Volume Calculator")
    print(f"{'=' * 80}")
    print(f"\nDriver Parameters:")
    print(f"  Fs  = {driver.F_s:.2f} Hz")
    print(f"  Qts = {driver.Q_ts:.3f}")
    print(f"  Vas = {driver.V_as * 1000:.2f} L")
    print(f"\n{'Qtc':<6} {'Vb (L)':<10} {'Fc (Hz)':<10} {'Alignment Type':<20}")
    print("-" * 80)

    for qtc in qtc_values:
        Vb, Fc, actual_qtc = calculate_vb_for_qtc(driver, qtc)

        # Determine alignment type
        if qtc < 0.5:
            alignment = "Very underdamped"
        elif qtc < 0.65:
            alignment = "Underdamped"
        elif 0.65 <= qtc <= 0.75:
            alignment = "Butterworth (B4)"
        elif qtc < 0.9:
            alignment = "Slight overdamp"
        elif 0.9 <= qtc <= 1.1:
            alignment = "Critically damped"
        else:
            alignment = "Overdamped"

        print(f"{qtc:<6.2f} {Vb:<10.2f} {Fc:<10.2f} {alignment:<20}")

    print()


def main():
    """Calculate and display box volumes for test drivers."""
    # BC_8NDL51 has Qts=0.616, so Qtc must be >= 0.616
    qtc_values_8ndl51 = [0.65, 0.707, 0.8, 1.0, 1.1]

    # BC_15PS100 has Qts=0.441, so can use lower Qtc
    qtc_values_15ps100 = [0.5, 0.707, 1.0, 1.1]

    # BC_8NDL51
    driver_8ndl51 = get_bc_8ndl51()
    print_driver_table(driver_8ndl51, "BC_8NDL51 (8-inch driver)", qtc_values_8ndl51)

    # BC_15PS100
    driver_15ps100 = get_bc_15ps100()
    print_driver_table(driver_15ps100, "BC_15PS100 (15-inch driver)", qtc_values_15ps100)

    # Print summary for script generation
    print(f"\n{'=' * 80}")
    print("Summary for Hornresp Input File Generation")
    print(f"{'=' * 80}\n")

    print("BC_8NDL51:")
    for qtc in [0.65, 0.8, 1.0, 1.1]:
        Vb, Fc, _ = calculate_vb_for_qtc(driver_8ndl51, qtc)
        print(f"  Qtc={qtc:.2f}: Vb={Vb:.2f}L, Fc={Fc:.2f}Hz")

    print("\nBC_15PS100:")
    for qtc in [0.5, 1.0, 1.1]:
        Vb, Fc, _ = calculate_vb_for_qtc(driver_15ps100, qtc)
        print(f"  Qtc={qtc:.2f}: Vb={Vb:.2f}L, Fc={Fc:.2f}Hz")

    print("\nNon-optimal volumes:")
    # Recalculate for arbitrary volumes
    params_8 = calculate_sealed_box_system_parameters(driver_8ndl51, 0.020)
    params_15 = calculate_sealed_box_system_parameters(driver_15ps100, 0.050)
    print(f"  BC_8NDL51: Vb=20.0L → Qtc={params_8.Qtc:.3f}, Fc={params_8.Fc:.2f}Hz")
    print(f"  BC_15PS100: Vb=50.0L → Qtc={params_15.Qtc:.3f}, Fc={params_15.Fc:.2f}Hz")


if __name__ == "__main__":
    main()
