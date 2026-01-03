#!/usr/bin/env python3
"""
Diagnostic script to investigate high-frequency SPL roll-off discrepancy.

This script breaks down the SPL calculation into intermediate steps
to identify where viberesp diverges from Hornresp at high frequencies.

Run: python tasks/diagnose_spl_rolloff.py
"""

import sys
sys.path.insert(0, 'src')

import numpy as np
import math
import cmath
from pathlib import Path

from gsd.hornresp.results_parser import load_hornresp_sim_file
from gsd.driver.bc_drivers import get_bc_8ndl51
from gsd.driver.radiation_impedance import radiation_impedance_piston
from gsd.simulation.constants import AIR_DENSITY, SPEED_OF_SOUND


def diagnose_spl_calculation(frequency, driver, voltage=2.83, measurement_distance=1.0):
    """
    Break down SPL calculation into intermediate steps.

    Returns dictionary with all intermediate values.
    """
    omega = 2 * math.pi * frequency
    k = omega / SPEED_OF_SOUND

    # 1. Voice coil impedance (simple model: Re + jωLe)
    Z_voice_coil = complex(driver.R_e, omega * driver.L_e)

    # 2. Radiation impedance
    Z_rad = radiation_impedance_piston(frequency, driver.S_d)

    # 3. Mechanical impedance (excluding radiation)
    # Z_mech = R_ms + j(ω*M_ms - 1/(ω*C_ms))
    Z_mech_proper = complex(driver.R_ms, omega * driver.M_ms - 1/(omega * driver.C_ms))

    # 4. Total mechanical impedance (including radiation)
    Z_mech_total = Z_mech_proper + Z_rad

    # 5. Motional impedance (referred to electrical side)
    # Z_mot = (BL)^2 / Z_mech_total
    Z_mot = (driver.BL ** 2) / Z_mech_total

    # 6. Total electrical impedance
    Z_e_total = Z_voice_coil + Z_mot

    # 7. Current
    I = voltage / Z_e_total

    # 8. Force on diaphragm
    F = driver.BL * I

    # 9. Diaphragm velocity
    u_diaphragm = F / Z_mech_total

    # 10. Volume velocity
    U = u_diaphragm * driver.S_d

    # 11. Pressure at measurement distance (on-axis)
    pressure_amplitude = (omega * AIR_DENSITY * abs(U)) / (2 * math.pi * measurement_distance)

    # 12. SPL
    p_ref = 20e-6  # 20 μPa
    spl = 20 * math.log10(pressure_amplitude / p_ref) if pressure_amplitude > 0 else -float('inf')

    return {
        'frequency': frequency,
        'omega': omega,
        'wavenumber': k,
        'Z_voice_coil': Z_voice_coil,
        'Z_voice_coil_mag': abs(Z_voice_coil),
        'Z_rad': Z_rad,
        'Z_rad_real': Z_rad.real,
        'Z_rad_imag': Z_rad.imag,
        'Z_mech_proper': Z_mech_proper,
        'Z_mech_total': Z_mech_total,
        'Z_mech_total_mag': abs(Z_mech_total),
        'Z_mot': Z_mot,
        'Z_e_total': Z_e_total,
        'Z_e_total_mag': abs(Z_e_total),
        'I': I,
        'I_mag': abs(I),
        'I_phase': cmath.phase(I),
        'F': F,
        'F_mag': abs(F),
        'u_diaphragm': u_diaphragm,
        'u_diaphragm_mag': abs(u_diaphragm),
        'U': U,
        'U_mag': abs(U),
        'pressure_amplitude': pressure_amplitude,
        'spl': spl,
    }


def main():
    """Run diagnostic analysis at key frequencies."""

    # Load Hornresp reference data
    data_path = Path("tests/validation/drivers/bc_8ndl51/infinite_baffle/8ndl51_sim.txt")
    hr_data = load_hornresp_sim_file(data_path)
    driver = get_bc_8ndl51()

    # Test frequencies
    test_frequencies = [100, 500, 1000, 2000, 5000, 10000, 20000]

    print("=" * 100)
    print("SPL CALCULATION DIAGNOSTIC - BC 8NDL51 Infinite Baffle")
    print("=" * 100)

    print("\nDRIVER PARAMETERS:")
    print("-" * 100)
    print(f"Re = {driver.R_e:.6f} Ω")
    print(f"Le = {driver.L_e*1000:.6f} mH")
    print(f"BL = {driver.BL:.6f} T·m")
    print(f"Mms = {driver.M_ms*1000:.6f} g")
    print(f"Cms = {driver.C_ms*1e6:.6f} µm/N")
    print(f"Rms = {driver.R_ms:.6f} N·s/m")
    print(f"Sd = {driver.S_d*1e4:.6f} cm²")
    print(f"Fs = {driver.F_s:.3f} Hz")

    print("\n" + "=" * 100)
    print("INTERMEDIATE CALCULATIONS")
    print("=" * 100)

    results = []

    for freq in test_frequencies:
        diag = diagnose_spl_calculation(freq, driver)
        results.append(diag)

        # Get Hornresp reference
        idx = np.argmin(np.abs(hr_data.frequency - freq))
        hr_freq = hr_data.frequency[idx]
        hr_ze = hr_data.ze_ohms[idx]
        hr_spl = hr_data.spl_db[idx]

        print(f"\n{'Frequency:':<25} {hr_freq:10.1f} Hz")
        print("-" * 100)

        print(f"\nELECTRICAL:")
        z_vc_str = f"{diag['Z_voice_coil'].real:.3f}{diag['Z_voice_coil'].imag:+.3f}j"
        z_mot_str = f"{diag['Z_mot'].real:.3f}{diag['Z_mot'].imag:+.3f}j"
        z_e_str = f"{diag['Z_e_total'].real:.3f}{diag['Z_e_total'].imag:+.3f}j"
        print(f"  {'Z_voice_coil (Re + jωLe)':<30} {z_vc_str:>20s}  (|Z| = {diag['Z_voice_coil_mag']:8.3f} Ω)")
        print(f"  {'Z_motional (BL²/Z_mech)':<30} {z_mot_str:>20s}  (|Z| = {abs(diag['Z_mot']):8.3f} Ω)")
        print(f"  {'Z_e_total':<30} {z_e_str:>20s}  (|Z| = {diag['Z_e_total_mag']:8.3f} Ω)")
        print(f"  {'Hornresp Ze':<30} {'':>20s}  (|Z| = {hr_ze:8.3f} Ω)")
        print(f"  {'Ze error':<30} {'':>20s}  (diff = {abs(diag['Z_e_total_mag'] - hr_ze):8.3f} Ω, {abs(diag['Z_e_total_mag'] - hr_ze)/hr_ze*100:6.2f}%)")

        print(f"\nCURRENT & FORCE:")
        i_str = f"{diag['I'].real:.6f}{diag['I'].imag:+.6f}j"
        f_str = f"{diag['F'].real:.6f}{diag['F'].imag:+.6f}j"
        print(f"  {'Current I = V / Ze':<30} {i_str:>20s}  (|I| = {diag['I_mag']*1000:8.3f} mA)")
        print(f"  {'Force F = BL * I':<30} {f_str:>20s}  (|F| = {diag['F_mag']:8.6f} N)")

        print(f"\nMECHANICAL:")
        z_mech_p_str = f"{diag['Z_mech_proper'].real:.3f}{diag['Z_mech_proper'].imag:+.3f}j"
        z_rad_str = f"{diag['Z_rad'].real:.3f}{diag['Z_rad'].imag:+.3f}j"
        z_mech_t_str = f"{diag['Z_mech_total'].real:.3f}{diag['Z_mech_total'].imag:+.3f}j"
        print(f"  {'Z_mech_proper (Rms + jωM - j/ωC)':<30} {z_mech_p_str:>20s}  (|Z| = {abs(diag['Z_mech_proper']):8.3f} N·s/m)")
        print(f"  {'Z_radiation':<30} {z_rad_str:>20s}  (|Z| = {abs(diag['Z_rad']):8.3f} N·s/m)")
        print(f"  {'Z_mech_total':<30} {z_mech_t_str:>20s}  (|Z| = {diag['Z_mech_total_mag']:8.3f} N·s/m)")

        print(f"\nMOTION:")
        u_str = f"{diag['u_diaphragm'].real:.6e}{diag['u_diaphragm'].imag:+.6e}j"
        u_str = f"{diag['u_diaphragm'].real:.6f}{diag['u_diaphragm'].imag:+.6f}j"
        print(f"  {'Diaphragm velocity u = F/Z':<30} {u_str:>20s}  (|u| = {diag['u_diaphragm_mag']*1000:8.3f} mm/s)")
        print(f"  {'Volume velocity U = u·Sd':<30} {diag['U_mag']*1e6:8.3f} cm³/s")

        print(f"\nACOUSTIC OUTPUT:")
        print(f"  {'Pressure amplitude p':<30} {diag['pressure_amplitude']:>20.3e} Pa")
        print(f"  {'Viberesp SPL':<30} {diag['spl']:20.3f} dB")
        print(f"  {'Hornresp SPL':<30} {hr_spl:20.3f} dB")
        print(f"  {'SPL error':<30} {abs(diag['spl'] - hr_spl):20.3f} dB")

    # Summary analysis
    print("\n" + "=" * 100)
    print("SUMMARY ANALYSIS")
    print("=" * 100)

    print("\nImpedance comparison:")
    print(f"{'Freq':<12} {'Vib Ze (Ω)':<15} {'HR Ze (Ω)':<15} {'Error %':<12} {'I_mag (mA)':<15}")
    print("-" * 100)
    for r, freq in zip(results, test_frequencies):
        idx = np.argmin(np.abs(hr_data.frequency - freq))
        hr_ze = hr_data.ze_ohms[idx]
        err = abs(r['Z_e_total_mag'] - hr_ze) / hr_ze * 100
        print(f"{freq:<12.1f} {r['Z_e_total_mag']:<15.3f} {hr_ze:<15.3f} {err:<12.2f} {r['I_mag']*1000:<15.3f}")

    print("\nSPL comparison:")
    print(f"{'Freq':<12} {'Vib SPL (dB)':<18} {'HR SPL (dB)':<18} {'Error (dB)':<15}")
    print("-" * 100)
    for r, freq in zip(results, test_frequencies):
        idx = np.argmin(np.abs(hr_data.frequency - freq))
        hr_spl = hr_data.spl_db[idx]
        err = abs(r['spl'] - hr_spl)
        print(f"{freq:<12.1f} {r['spl']:<18.3f} {hr_spl:<18.3f} {err:<15.3f}")

    print("\nVolume velocity comparison:")
    print(f"{'Freq':<12} {'|U| (cm³/s)':<18} {'SPL (dB)':<18} {'HR SPL (dB)':<18}")
    print("-" * 100)
    for r, freq in zip(results, test_frequencies):
        idx = np.argmin(np.abs(hr_data.frequency - freq))
        hr_spl = hr_data.spl_db[idx]
        print(f"{freq:<12.1f} {r['U_mag']*1e6:<18.3f} {r['spl']:<18.3f} {hr_spl:<18.3f}")

    print("\nKey observations:")
    print("-" * 100)
    print("1. Check if current decreases correctly at high frequencies (should drop as inductance increases)")
    print("2. Check if volume velocity decreases at high frequencies")
    print("3. Check if mechanical impedance increases correctly with frequency")
    print("4. Identify which step shows divergence from expected behavior")

    print("\n" + "=" * 100)
    print("Next steps:")
    print("=" * 100)
    print("- Compare these calculations with Hornresp's intermediate values (if available)")
    print("- Check literature for correct SPL calculation formula")
    print("- Verify radiation impedance effects at high frequencies")
    print("- Investigate if additional damping or mass loading is needed")


if __name__ == "__main__":
    main()
