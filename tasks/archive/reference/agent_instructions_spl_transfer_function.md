# Agent Task: Implement Transfer Function SPL Calculation

## Objective

Fix the SPL calculation bug by implementing Small's transfer function approach instead of impedance coupling. The current impedance-based approach causes SPL to rise +20 dB from 20-200 Hz for high-BL drivers.

## Problem Summary

**Current Bug:** SPL rises with frequency instead of rolling off at high frequencies.

**Root Cause:** Impedance coupling equation `v = (BL × V) / (Ze×Zm + BL²)` doesn't work for high-BL drivers because BL² dominates the denominator.

**Solution:** Use Small's transfer functions which directly give SPL vs frequency.

## What to Implement

### 1. Sealed Box Transfer Function

Create a new function in `src/gsd/enclosure/sealed_box.py`:

```python
def calculate_spl_from_transfer_function(
    frequency: float,
    driver: ThieleSmallParameters,
    Vb: float,
    voltage: float = 2.83,
    measurement_distance: float = 1.0,
    speed_of_sound: float = SPEED_OF_SOUND,
    air_density: float = AIR_DENSITY
) -> float:
    """
    Calculate SPL using Small's transfer function.

    Transfer function (Small 1972, Eq. 19):
    G(s) = s² / (s² + s·ωc/Qtc + ωc²)

    where:
    - s = jω
    - ωc = 2πfc (system cutoff frequency)
    - fc = Fs × sqrt(α + 1) (system resonance)
    - Qtc = Qts × sqrt(α + 1) (system Q)
    - α = Vas/Vb (compliance ratio)

    Returns:
        SPL in dB at measurement_distance
    """
    import math
    import cmath

    # Calculate system parameters
    alpha = driver.V_as / Vb
    Qtc = driver.Q_ts * math.sqrt(alpha + 1)
    fc = driver.F_s * math.sqrt(alpha + 1)
    wc = 2 * math.pi * fc

    # Complex frequency variable
    omega = 2 * math.pi * frequency
    s = complex(0, omega)

    # Transfer function magnitude
    numerator = s**2
    denominator = s**2 + s * (wc / Qtc) + wc**2
    G = numerator / denominator

    # Calculate reference sensitivity at 1W/1m
    # Use driver's efficiency or calculate from T/S parameters
    # For now: use calibrated reference from driver's nominal impedance
    # This needs to be calculated from first principles

    # Simplified: Use reference SPL at midband frequency
    # Full implementation should calculate from Bl, Sd, Re, etc.

    # TEMPORARY: Use current approach to get reference level
    # Calculate SPL at a reference frequency (well above Fc)
    # then apply transfer function shape

    # Better approach: Calculate from diaphragm velocity at reference
    # This is a placeholder - you'll need to implement properly

    # Convert transfer function magnitude to dB
    tf_dB = 20 * math.log10(abs(G))

    # Reference SPL (needs proper calculation)
    # For now, return relative response
    return tf_dB  # Placeholder!
```

**IMPORTANT:** The reference SPL calculation needs to be implemented correctly. Look at:
- Small (1972) for sensitivity calculation
- Beranek (1954) for radiation efficiency
- Current code in `sealed_box_electrical_impedance()` for reference

### 2. Ported Box Transfer Function

Create in `src/gsd/enclosure/ported_box.py`:

```python
def calculate_spl_ported_transfer_function(
    frequency: float,
    driver: ThieleSmallParameters,
    Vb: float,
    Fb: float,
    voltage: float = 2.83,
    measurement_distance: float = 1.0,
    speed_of_sound: float = SPEED_OF_SOUND,
    air_density: float = AIR_DENSITY
) -> float:
    """
    Calculate SPL using Small's 4th-order transfer function for ported box.

    Transfer function (Small 1973, Eq. 13):
    D'(s) = s⁴Tb²Ts² + s³(Tb²Ts/Qes + TbTs²/QL) +
            s²[(α+1)Tb² + TbTs/(QL×Qes) + Ts²] +
            s(Tb/QL + Ts/Qes) + 1

    where:
    - Ts = 1/ωs (driver time constant)
    - Tb = 1/ωb (box time constant)
    - α = Vas/Vb (compliance ratio)
    - Qes, Qms, Qts (driver Q factors)
    - QL (box losses, typically 7-10 for port)

    Returns:
        SPL in dB at measurement_distance
    """
    import math

    # Normalized parameters
    omega_s = 2 * math.pi * driver.F_s
    omega_b = 2 * math.pi * Fb
    Ts = 1.0 / omega_s
    Tb = 1.0 / omega_b
    alpha = driver.V_as / Vb
    Qp = 7.0  # Port Q factor

    # Complex frequency
    omega = 2 * math.pi * frequency
    s = complex(0, omega)

    # 4th-order denominator polynomial (Small 1973, Eq. 13)
    a4 = (Ts**2) * (Tb**2)
    a3 = (Tb**2 * Ts / Qp) + (Ts * Tb**2 / driver.Q_es)
    a2 = (alpha + 1) * (Tb**2) + (Ts * Tb / (Qp * driver.Q_es)) + (Ts**2)
    a1 = Tb / Qp + Ts / driver.Q_es
    a0 = 1

    # Numerator (for SPL, not impedance)
    # Need to check Small (1973) for correct numerator
    # This is a placeholder - you'll need to get the exact form

    denominator = (s**4) * a4 + (s**3) * a3 + (s**2) * a2 + s * a1 + a0

    # Calculate transfer function magnitude
    # ...

    return spl  # Placeholder!
```

**CRITICAL:** You need to find the exact SPL transfer function from Small (1973), not the impedance transfer function.

### 3. Update Existing Functions

Modify `sealed_box_electrical_impedance()` and `ported_box_electrical_impedance()` to:
1. Keep impedance calculation as-is (it's accurate!)
2. Replace SPL calculation with transfer function approach
3. Maintain backward compatibility (same function signature)

## Key Literature References

1. **Small (1972)** - "Closed-Box Loudspeaker Systems Part I: Analysis"
   - JAES Vol. 20, No. 10
   - Equation 19: Transfer function for sealed box
   - File: `literature/thiele_small/small_1972_closed_box.md`

2. **Small (1973)** - "Vented-Box Loudspeaker Systems Part I"
   - JAES Vol. 21, No. 6
   - Equation 13: 4th-order transfer function for ported box
   - File: `literature/thiele_small/thiele_1971_vented_boxes.md`

3. **Thiele (1971)** - "Loudspeakers in Vented Boxes"
   - JAES Vol. 19, Parts 1 & 2
   - Transfer function tables for different alignments
   - File: `literature/thiele_small/thiele_1971_vented_boxes.md`

## Validation Requirements

After implementation, validate against Hornresp:

```python
# Test with BC_15DS115 (high-BL driver that currently fails)
driver = get_bc_15ds115()
Vb = 0.180  # 180L
Fb = 28.0   # 28Hz tuning

# Test frequencies
for freq in [20, 28, 40, 50, 70, 100, 150, 200]:
    spl_new = calculate_spl_ported_transfer_function(
        freq, driver, Vb, Fb, voltage=2.83
    )
    # Compare with Hornresp output
    # Expected: within ±2 dB
```

**Expected behavior:**
- Velocity/SPL should ROLL OFF at high frequencies
- 200 Hz should be 3-6 dB LOWER than 70 Hz
- 500 Hz should be 10-20 dB LOWER than 100 Hz
- Flat response in passband (Fb to ~200 Hz)

## Files to Modify

1. `src/gsd/enclosure/sealed_box.py`
   - Add `calculate_spl_from_transfer_function()`
   - Update `sealed_box_electrical_impedance()` to use it

2. `src/gsd/enclosure/ported_box.py`
   - Add `calculate_spl_ported_transfer_function()`
   - Update `ported_box_electrical_impedance()` to use it

3. `src/gsd/driver/response.py`
   - Update `direct_radiator_electrical_impedance()` to use transfer function

4. `tests/test_*.py`
   - Add validation tests comparing with Hornresp

## Important Notes

1. **DO NOT change impedance calculations** - they're accurate (3.9% error)
2. **ONLY replace SPL calculation** - keep the same API
3. **MUST cite literature** - every equation needs Small/Thiele reference
4. **Validate thoroughly** - test with both low-BL and high-BL drivers
5. **Reference SPL level** - needs proper calculation from T/S parameters

## Success Criteria

- [ ] SPL rolls off at high frequencies (not rising!)
- [ ] Matches Hornresp within ±2 dB for BC_15DS115
- [ ] Flatness optimizer finds truly flat responses
- [ ] Works for both sealed and ported boxes
- [ ] All code has literature citations

## Debugging Tips

If SPL still doesn't roll off:
1. Check transfer function coefficients (especially α+1 term)
2. Verify reference SPL calculation
3. Plot transfer function magnitude vs frequency
4. Compare with Small's paper examples
5. Test with simple driver (BC_8NDL51) first

## Estimated Complexity

- **Sealed box:** MEDIUM (2nd-order TF is straightforward)
- **Ported box:** HIGH (4th-order TF with many parameters)
- **Time estimate:** 4-8 hours implementation + 2-4 hours validation

## Next Steps After Implementation

1. Run `tasks/diagnose_spl_response.py` to verify fix
2. Run `tasks/test_optimizer_flatness.py` to verify optimizer works
3. Create validation plots comparing with Hornresp
4. Update documentation in `docs/validation/`
5. Mark existing SPL bug as resolved

---

**Priority:** CRITICAL - Blocks flatness optimization
**Dependencies:** None (standalone implementation)
**Testing:** Must validate against Hornresp for multiple drivers
