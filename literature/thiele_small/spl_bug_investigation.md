# SPL Bug Investigation Summary

**Date:** 2025-12-27
**Status:** Root cause identified, solution known

## Problem Statement

SPL rises +20 dB from 20-200 Hz instead of rolling off at high frequencies.
Flatness optimization is blocked because it's optimizing a fundamentally wrong curve.

## Root Cause Analysis

### Initial Hypothesis (WRONG)
Thought the pressure formula `p = ωρU/(2πr)` was wrong due to the `omega` factor.

### Research Agent Response (PARTIALLY CORRECT)
Agent correctly identified that we might be double-counting mechanical impedance.
Suggested using: `v = (BL × V) / (Ze_electrical × Zm + BL²)`

### Testing Revealed (THE REAL ISSUE)

**The impedance coupling equation doesn't work for high-BL drivers!**

Test results:
- **BC_8NDL51 (BL=7.3, BL²=53)**: Velocity falls 3.2× over 6× frequency → ✓ WORKS
- **BC_15DS115 (BL=38.7, BL²=1498)**: Velocity doesn't fall → ✗ BROKEN

**Why?** For high-BL drivers, the BL² term dominates the denominator:
```
v = (BL × V) / (Ze×Zm + BL²)

For BC_15DS115 at 200 Hz:
  |Ze×Zm| = 583 Ω
  BL² = 1498 Ω
  → BL² dominates 2.6×, velocity stays constant!
```

### Current Code Status

The existing `direct_radiator_electrical_impedance()` in `src/gsd/driver/response.py`
uses the SAME impedance coupling approach (lines 210-226).

**Known limitation already documented:**
```python
# Lines 143-150
Known Limitations:
SPL validation fails for 3/4 tested drivers (BC_12NDL76, BC_15DS115, BC_18PZW100)
with errors up to 10 dB.
```

This is the SAME BUG we're seeing!

## The Correct Solution

### Use Small's Transfer Function (NOT impedance coupling)

For sealed boxes:
```
G(s) = s² / (s² + s·ωc/Qtc + ωc²)

where:
- s = jω (complex frequency)
- ωc = 2πfc (system cutoff frequency)
- Qtc = total system Q
- fc = F3 (-3dB point)
```

For ported boxes:
```
4th-order high-pass transfer function (Small 1973, Eq. 13)
```

**Key advantages:**
1. Direct SPL calculation from frequency (no velocity needed)
2. Proper high-frequency rolloff built-in
3. Validated by Hornresp
4. Works for ANY BL value

### Implementation Approach

```python
def calculate_spl_from_transfer_function(
    frequency: float,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    Vb: float,
    Fb: float = None  # For ported
) -> float:
    """Calculate SPL using Small's transfer function."""

    omega = 2 * math.pi * frequency
    s = complex(0, omega)

    if enclosure_type == "sealed":
        # Calculate system parameters
        alpha = driver.V_as / Vb
        Qtc = driver.Q_ts * math.sqrt(alpha + 1)
        fc = driver.F_s * math.sqrt(alpha + 1)
        wc = 2 * math.pi * fc

        # Transfer function magnitude
        # G(s) = s² / (s² + s·wc/Qtc + wc²)
        numerator = s**2
        denominator = s**2 + s * (wc / Qtc) + wc**2
        G = numerator / denominator

        # Convert to SPL (reference sensitivity at 1W/1m)
        # Use driver efficiency or reference SPL
        sensitivity = calculate_sensitivity(driver, voltage=2.83)
        spl = sensitivity + 20 * math.log10(abs(G))

        return spl

    elif enclosure_type == "ported":
        # 4th-order transfer function (Small 1973)
        # Implementation similar but with 4th-order polynomial
        ...
```

## Why This Works

1. **No velocity calculation** - Transfer function directly gives SPL vs frequency
2. **HF rolloff is built-in** - The transfer function naturally has proper rolloff
3. **BL-independent** - Works for any motor strength
4. **Validated** - This is what Hornresp uses internally

## Next Steps

1. Implement transfer function SPL calculation for sealed boxes
2. Implement for ported boxes (4th-order)
3. Validate against Hornresp (should match within ±2 dB)
4. Replace current impedance-based SPL calculation
5. Re-enable flatness optimization

## Literature

- Small (1972) - "Closed-Box Loudspeaker Systems Part I: Analysis", JAES Vol. 20
  - Equation 19: Second-order transfer function
- Small (1973) - "Vented-Box Loudspeaker Systems Part I", JAES Vol. 21
  - Equation 13: Fourth-order transfer function
- Thiele (1971) - "Loudspeakers in Vented Boxes", JAES Vol. 19
  - Transfer function tables for alignments

## Files to Modify

1. `src/gsd/enclosure/sealed_box.py` - Add transfer function SPL
2. `src/gsd/enclosure/ported_box.py` - Add transfer function SPL
3. `src/gsd/enclosure/sealed_box.py` - Update `sealed_box_electrical_impedance()`
4. `src/gsd/enclosure/ported_box.py` - Update `ported_box_electrical_impedance()`
5. `src/gsd/optimization/objectives/response_metrics.py` - Will work automatically once SPL is fixed

## Validation Plan

1. Test with BC_8NDL51 (low-BL driver) - should match current working behavior
2. Test with BC_15DS115 (high-BL driver) - should FIX the +20 dB rise
3. Compare with Hornresp at multiple frequencies
4. Verify impedance still matches (3.9% error - this is separate)
5. Enable flatness optimizer and verify it finds flat responses

## Impact

Once fixed:
- ✅ Flatness optimization will work correctly
- ✅ SPL will match Hornresp
- ✅ Max SPL calculations will be accurate
- ✅ Power handling estimates will be correct
- ✅ User confidence in the tool will increase

---

**Priority:** CRITICAL
**Complexity:** MEDIUM (transfer functions are well-documented)
**Estimated effort:** 4-8 hours implementation + testing
