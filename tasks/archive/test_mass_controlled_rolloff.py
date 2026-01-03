#!/usr/bin/env python3
"""
Test script to validate mass-controlled roll-off implementation.

This script tests the implementation of high-frequency roll-off in
ported box SPL calculations, comparing against Hornresp reference data
for the B&C 15DS115 driver.

Research: docs/validation/mass_controlled_rolloff_research.md
"""

import sys
sys.path.insert(0, 'src')

import math
from gsd.driver.bc_drivers import get_bc_15ds115
from gsd.enclosure.ported_box import (
    calculate_spl_ported_transfer_function,
    calculate_mass_break_frequency,
    calculate_inductance_corner_frequency,
    calculate_hf_rolloff_db,
)


def test_corner_frequencies():
    """Test calculation of mass break point and inductance corner frequencies."""
    print("=" * 70)
    print("TEST 1: Corner Frequency Calculations")
    print("=" * 70)

    # Get B&C 15DS115 driver
    driver = get_bc_15ds115()

    print(f"\nDriver: B&C 15DS115 8Ω")
    print(f"  BL = {driver.BL} T·m")
    print(f"  Re = {driver.R_e} Ω")
    print(f"  Mms = {driver.M_ms * 1000} g")
    print(f"  Le = {driver.L_e * 1000} mH")

    # Calculate corner frequencies
    f_mass = calculate_mass_break_frequency(driver.BL, driver.R_e, driver.M_ms)
    f_le = calculate_inductance_corner_frequency(driver.R_e, driver.L_e)

    print(f"\nCorner Frequencies:")
    print(f"  Mass break point (f_mass): {f_mass:.1f} Hz")
    print(f"  Expected: ~383 Hz")
    print(f"  Error: {abs(f_mass - 383):.1f} Hz ({abs(f_mass - 383)/383*100:.1f}%)")

    print(f"\n  Inductance corner (f_le): {f_le:.1f} Hz")
    print(f"  Expected: ~173 Hz")
    print(f"  Error: {abs(f_le - 173):.1f} Hz ({abs(f_le - 173)/173*100:.1f}%)")

    # Validate
    assert abs(f_mass - 383) < 10, f"Mass break point error too large: {f_mass} Hz"
    assert abs(f_le - 173) < 5, f"Inductance corner error too large: {f_le} Hz"

    print("\n✓ Corner frequencies calculated correctly")
    return f_mass, f_le


def test_hf_rolloff_magnitude(f_mass, f_le):
    """Test high-frequency roll-off magnitude at key frequencies."""
    print("\n" + "=" * 70)
    print("TEST 2: High-Frequency Roll-off Magnitude")
    print("=" * 70)

    test_frequencies = [100, 500, 1000, 5000]
    expected_rolloff = {
        100: -1.0,   # ~-1 dB at 100 Hz
        500: -6.0,   # ~-6 dB at 500 Hz
        1000: -14.0, # ~-14 dB at 1000 Hz
        5000: -32.0, # ~-32 dB at 5000 Hz (matches observed error!)
    }

    print(f"\nCorner frequencies: f_mass = {f_mass:.1f} Hz, f_le = {f_le:.1f} Hz")
    print(f"\n{'Frequency':<12} {'Roll-off':<12} {'Expected':<12} {'Error':<12}")
    print("-" * 70)

    for freq in test_frequencies:
        rolloff = calculate_hf_rolloff_db(freq, f_mass, f_le)
        expected = expected_rolloff[freq]
        error = abs(rolloff - expected)

        print(f"{freq:<12} {rolloff:<12.2f} {expected:<12.1f} {error:<12.2f}")

        # Allow ±3 dB tolerance (this is an empirical model)
        assert error < 3.0, f"Roll-off error too large at {freq} Hz: {error:.2f} dB"

    print("\n✓ High-frequency roll-off magnitude correct")


def test_spl_with_hf_rolloff():
    """Test ported box SPL with high-frequency roll-off enabled."""
    print("\n" + "=" * 70)
    print("TEST 3: Ported Box SPL with HF Roll-off")
    print("=" * 70)

    # Get B&C 15DS115 driver
    driver = get_bc_15ds115()

    # B4 alignment parameters (from previous optimization)
    Vb = driver.V_as  # B4 alignment
    Fb = driver.F_s   # B4 alignment

    print(f"\nDriver: B&C 15DS115 8Ω")
    print(f"  Box volume Vb = {Vb * 1000:.1f} L (Vas)")
    print(f"  Tuning frequency Fb = {Fb:.1f} Hz (Fs)")

    # Hornresp reference data (from previous validation)
    # Frequencies: 20, 100, 500, 1000, 5000 Hz
    hornresp_data = {
        20: 75.3,
        100: 92.5,
        500: 100.6,
        1000: 88.4,
        5000: 59.2,
    }

    print(f"\n{'Freq':<8} {'Hornresp':<12} {'With HF':<12} {'No HF':<12} {'Error (HF)':<12}")
    print("-" * 70)

    test_freqs = [20, 100, 500, 1000, 5000]

    for freq in test_freqs:
        # Calculate SPL with HF roll-off (default)
        spl_with_hf = calculate_spl_ported_transfer_function(
            frequency=freq,
            driver=driver,
            Vb=Vb,
            Fb=Fb,
            voltage=2.83,
            measurement_distance=1.0,
            Qp=7.0,
            include_hf_rolloff=True
        )

        # Calculate SPL without HF roll-off
        spl_no_hf = calculate_spl_ported_transfer_function(
            frequency=freq,
            driver=driver,
            Vb=Vb,
            Fb=Fb,
            voltage=2.83,
            measurement_distance=1.0,
            Qp=7.0,
            include_hf_rolloff=False
        )

        # Compare with Hornresp
        hornresp_spl = hornresp_data[freq]
        error_with_hf = abs(spl_with_hf - hornresp_spl)
        error_no_hf = abs(spl_no_hf - hornresp_spl)

        print(f"{freq:<8} {hornresp_spl:<12.1f} {spl_with_hf:<12.1f} {spl_no_hf:<12.1f} {error_with_hf:<12.2f}")

        # Check that HF roll-off improves high-frequency match
        if freq >= 1000:
            # At high frequencies, HF roll-off should significantly improve match
            assert error_with_hf < error_no_hf, \
                f"HF roll-off should improve match at {freq} Hz"

    print("\n✓ HF roll-off improves Hornresp agreement at high frequencies")


def test_5khz_discrepancy_fix():
    """Verify that the 5 kHz discrepancy is fixed."""
    print("\n" + "=" * 70)
    print("TEST 4: 5 kHz Discrepancy Fix")
    print("=" * 70)

    # Get B&C 15DS115 driver
    driver = get_bc_15ds115()
    Vb = driver.V_as
    Fb = driver.F_s

    # Hornresp reference at 5 kHz
    hornresp_5khz = 59.2  # dB

    # Calculate with HF roll-off
    spl_with_hf = calculate_spl_ported_transfer_function(
        frequency=5000,
        driver=driver,
        Vb=Vb,
        Fb=Fb,
        voltage=2.83,
        measurement_distance=1.0,
        Qp=7.0,
        include_hf_rolloff=True
    )

    # Calculate without HF roll-off
    spl_no_hf = calculate_spl_ported_transfer_function(
        frequency=5000,
        driver=driver,
        Vb=Vb,
        Fb=Fb,
        voltage=2.83,
        measurement_distance=1.0,
        Qp=7.0,
        include_hf_rolloff=False
    )

    print(f"\nHornresp SPL at 5 kHz: {hornresp_5khz:.1f} dB")
    print(f"Viberesp SPL (with HF roll-off): {spl_with_hf:.1f} dB")
    print(f"Viberesp SPL (without HF roll-off): {spl_no_hf:.1f} dB")
    print(f"\nError (with HF): {abs(spl_with_hf - hornresp_5khz):.2f} dB")
    print(f"Error (without HF): {abs(spl_no_hf - hornresp_5khz):.2f} dB")
    print(f"Improvement: {abs(spl_no_hf - hornresp_5khz) - abs(spl_with_hf - hornresp_5khz):.2f} dB")

    # The original discrepancy was +32 dB (without HF roll-off)
    # With HF roll-off, error should be much smaller
    original_error = spl_no_hf - hornresp_5khz
    new_error = spl_with_hf - hornresp_5khz

    print(f"\nOriginal discrepancy (without HF): {original_error:+.2f} dB")
    print(f"New discrepancy (with HF): {new_error:+.2f} dB")
    print(f"Reduction: {original_error - new_error:.2f} dB")

    # Check that HF roll-off significantly reduces the error
    assert abs(new_error) < 10.0, f"HF roll-off error still too large: {new_error:.2f} dB"
    assert abs(new_error) < abs(original_error), \
        f"HF roll-off should reduce error (original: {original_error:.2f}, new: {new_error:.2f})"

    print("\n✓ 5 kHz discrepancy fixed by HF roll-off")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("MASS-CONTROLLED ROLL-OFF VALIDATION TESTS")
    print("=" * 70)
    print("\nTesting implementation against Hornresp reference data")
    print("Driver: B&C 15DS115 8Ω")
    print("Research: docs/validation/mass_controlled_rolloff_research.md")

    try:
        # Test 1: Corner frequencies
        f_mass, f_le = test_corner_frequencies()

        # Test 2: HF roll-off magnitude
        test_hf_rolloff_magnitude(f_mass, f_le)

        # Test 3: SPL with HF roll-off
        test_spl_with_hf_rolloff()

        # Test 4: 5 kHz discrepancy fix
        test_5khz_discrepancy_fix()

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED ✓")
        print("=" * 70)
        print("\nMass-controlled roll-off implementation validated successfully!")
        print("High-frequency SPL now matches Hornresp within acceptable tolerances.")

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
