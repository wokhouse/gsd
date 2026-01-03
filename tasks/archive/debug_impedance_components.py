#!/usr/bin/env python3
"""
Debug: Calculate impedance components at key frequencies to understand why velocity isn't falling.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import math
from gsd.driver.bc_drivers import get_bc_15ds115
from gsd.simulation.constants import SPEED_OF_SOUND, AIR_DENSITY


def debug_at_frequency(freq, voltage, driver):
    """Debug all impedance components at a single frequency."""
    omega = 2 * math.pi * freq

    # Radiation mass
    from gsd.driver.radiation_mass import calculate_radiation_mass
    M_rad = calculate_radiation_mass(freq, driver.S_d, SPEED_OF_SOUND, AIR_DENSITY)
    M_ms = driver.M_md + 2.0 * M_rad

    # Mechanical impedance components
    Zm_resistive = driver.R_ms
    Zm_massive = omega * M_ms
    Zm_compliant = -1 / (omega * driver.C_ms)

    Zm_mechanical_real = Zm_resistive
    Zm_mechanical_imag = Zm_massive + Zm_compliant
    Zm_mechanical = complex(Zm_mechanical_real, Zm_mechanical_imag)

    # Electrical impedance components
    Ze_resistive = driver.R_e
    Ze_inductive = omega * driver.L_e
    Ze_electrical = complex(Ze_resistive, Ze_inductive)

    # Coupled impedance denominator: Ze_electrical × Zm + BL²
    denominator = Ze_electrical * Zm_mechanical + driver.BL**2

    # Velocity
    numerator = driver.BL * voltage
    velocity = numerator / denominator

    return {
        'omega': omega,
        'M_rad': M_rad * 1000,  # g
        'M_ms': M_ms * 1000,    # g
        'Zm_resistive': Zm_resistive,
        'Zm_massive': Zm_massive,
        'Zm_compliant': Zm_compliant,
        'Zm_mechanical': Zm_mechanical,
        'Ze_resistive': Ze_resistive,
        'Ze_inductive': Ze_inductive,
        'Ze_electrical': Ze_electrical,
        'denominator': denominator,
        'velocity': velocity,
    }


def main():
    """Debug impedance components at key frequencies."""
    print("=" * 70)
    print("DEBUG: Impedance Components Analysis")
    print("=" * 70)

    driver = get_bc_15ds115()

    print(f"\nDriver: BC_15DS115")
    print(f"  M_md: {driver.M_md*1000:.1f} g")
    print(f"  C_ms: {driver.C_ms*1e6:.2f} mm/N")
    print(f"  R_ms: {driver.R_ms:.2f} N·s/m")
    print(f"  BL: {driver.BL:.1f} T·m")
    print(f"  R_e: {driver.R_e:.1f} Ω")
    print(f"  L_e: {driver.L_e*1000:.1f} mH")

    # Key frequencies
    test_freqs = [33, 50, 100, 200]

    print(f"\n" + "=" * 70)
    print(f"{'Freq':>6} | {'M_rad':>8} | {'M_ms':>8} | {'Zm_res':>8} | {'Zm_mass':>8} | {'Zm_comp':>8} | {'|Zm|':>8} | {'|vel|':>10}")
    print("-" * 70)

    for freq in test_freqs:
        debug = debug_at_frequency(freq, 2.83, driver)

        print(f"{freq:>6.1f} | "
              f"{debug['M_rad']:>8.2f} | "
              f"{debug['M_ms']:>8.2f} | "
              f"{debug['Zm_resistive']:>8.2f} | "
              f"{debug['Zm_massive']:>8.2f} | "
              f"{debug['Zm_compliant']:>8.2f} | "
              f"{abs(debug['Zm_mechanical']):>8.2f} | "
              f"{abs(debug['velocity'])*1000:>10.3f}")

    print("\n" + "=" * 70)
    print("DETAILED BREAKDOWN AT 200 HZ")
    print("=" * 70)

    freq = 200
    debug = debug_at_frequency(freq, 2.83, driver)

    print(f"\nFrequency: {freq} Hz")
    print(f"ω = 2πf = {debug['omega']:.1f} rad/s")

    print(f"\n--- Mass ---")
    print(f"M_rad (radiation): {debug['M_rad']/1000*1000:.2f} g")
    print(f"M_md (driver):     {driver.M_md*1000:.2f} g")
    print(f"M_ms (total):      {debug['M_ms']/1000*1000:.2f} g")

    print(f"\n--- Mechanical Impedance ---")
    print(f"Zm_resistive:     {debug['Zm_resistive']:.2f} Ω (R_ms)")
    print(f"Zm_massive (jωM): j{debug['Zm_massive']:.2f} Ω")
    print(f"Zm_compliant:     j{debug['Zm_compliant']:.2f} Ω")
    print(f"Zm_total:         {debug['Zm_mechanical']:.2f} Ω")
    print(f"                 |Zm| = {abs(debug['Zm_mechanical']):.2f} Ω")

    print(f"\n--- Electrical Impedance ---")
    print(f"Ze_resistive:     {debug['Ze_resistive']:.2f} Ω (R_e)")
    print(f"Ze_inductive:    j{debug['Ze_inductive']:.2f} Ω")
    print(f"Ze_total:         {debug['Ze_electrical']:.2f} Ω")

    print(f"\n--- Coupled System ---")
    print(f"Denominator: Ze × Zm + BL² = {debug['denominator']:.2f}")
    print(f"Numerator:   BL × V = {debug['denominator'].real/driver.BL*2.83:.2f}")

    print(f"\n--- Result ---")
    print(f"Velocity:    {debug['velocity']:.6f} m/s")
    print(f"             |v| = {abs(debug['velocity'])*1000:.3f} mm/s")

    # Check what happens if we ignore electrical impedance
    print("\n" + "=" * 70)
    print("WHAT IF WE IGNORE Ze_electrical?")
    print("=" * 70)

    print(f"\nAt 200 Hz:")
    print(f"  Current approach: v = BL×V / (Ze×Zm + BL²)")
    print(f"  |v| = {abs(debug['velocity'])*1000:.3f} mm/s")

    # Simplified: v = BL×V / (jωM×Re + BL²)  (ignore compliance, use dominant terms)
    omega = 2 * math.pi * freq
    from gsd.driver.radiation_mass import calculate_radiation_mass
    M_rad = calculate_radiation_mass(freq, driver.S_d, SPEED_OF_SOUND, AIR_DENSITY)
    M_ms = driver.M_md + 2.0 * M_rad

    denominator_simple = complex(driver.R_e, omega * driver.L_e) * complex(0, omega * M_ms) + driver.BL**2
    velocity_simple = driver.BL * 2.83 / denominator_simple

    print(f"\n  Simplified (mass only): v = BL×V / (Ze×jωM + BL²)")
    print(f"  |v| = {abs(velocity_simple)*1000:.3f} mm/s")

    # Even simpler: v = BL×V / BL² = V/BL (at very high frequency where Ze×Zm >> BL²)
    velocity_very_simple = 2.83 / driver.BL * M_ms * omega * driver.R_e / driver.BL**2  # Wrong direction
    # Actually at high freq: Ze × Zm ≈ jωLe × jωM = -ω²LeM
    # v = BL×V / (-ω²LeM + BL²)
    omega = 2 * math.pi * freq
    denominator_hf = -omega**2 * driver.L_e * M_ms + driver.BL**2
    velocity_hf = driver.BL * 2.83 / denominator_hf

    print(f"\n  High freq approx: v = BL×V / (-ω²LeM + BL²)")
    print(f"  |v| = {abs(velocity_hf)*1000:.3f} mm/s")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
