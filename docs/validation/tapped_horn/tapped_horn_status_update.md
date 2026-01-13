# Tapped Horn Implementation Status - Research Handoff Update

**Date**: 2025-01-11
**Status**: ADMITTANCE METHOD IMPLEMENTED BUT STILL INCORRECT
**Issue**: Root cause identified - impedance calculation is fundamentally wrong

## Summary

After implementing the admittance method based on the provided research, the tapped horn simulation **still produces incorrect results**:
- SPL errors: -22.69 to +25.03 dB (should be < 3 dB)
- Electrical impedance errors: **26.58 Ω vs 6.92 Ω** at 40 Hz
- Systematic error across all frequencies

## Critical Finding: The Problem is NOT the SPL Calculation

The electrical impedance is wrong, which means the problem is **earlier in the chain**, not in the mouth pressure calculation:

```python
# Step 1-6: Calculate driver impedance and velocity
z_acoustic = tapped_horn_tap_impedance(...)  # ← WRONG
z_mechanical_acoustic = z_acoustic * (driver.S_d ** 2)  # ← PROPAGATES ERROR
z_mechanical_total = z_mechanical_driver + z_mechanical_acoustic  # ← WRONG
z_electrical = ...  # ← WRONG (26.58 Ω vs 6.92 Ω expected)
```

Both the original simple implementation AND the new admittance method produce the same wrong impedance values, which suggests the error is in:
1. `tapped_horn_tap_impedance()` function
2. OR the T-matrix calculation functions it calls
3. OR the acoustic-to-mechanical impedance conversion

## Detailed Comparison

### Original Simple Implementation
```
SPL errors: -15.73 to +25.17 dB (RMS: 12.00 dB)
Ze errors: 26.58 Ω vs 6.92 Ω at 40 Hz (RMS: 9.05 Ω)
```

### Admittance Method Implementation
```
SPL errors: -22.69 to +25.03 dB (RMS: 13.31 dB)
Ze errors: 26.58 Ω vs 6.92 Ω at 40 Hz (same as above!)
```

**Key observation**: Both implementations give the SAME wrong impedance values, which confirms the problem is in the impedance calculation, not the SPL calculation.

## Debug Data Analysis

At 40 Hz (quarter-wave resonance should be near 47.6 Hz):
```
|Z_up|   = 4.53e+03 Pa·s/m³
|Z_down| = 5.57e+03 Pa·s/m³
|Z_tap|  = 2.50e+03 Pa·s/m³ (parallel combination)
```

Expected behavior at quarter-wave:
- Upstream stub should have **very high impedance** (approaching infinity)
- This should dominate the parallel combination
- Driver should see very high load → very low velocity

What we're actually getting:
- Moderate upstream impedance (4530)
- No sign of quarter-wave resonance behavior

## Possible Root Causes

1. **T-matrix calculation is wrong**: `exponential_horn_tmatrix()` might be calculating incorrect T-matrix elements

2. **Upstream impedance calculation is wrong**: `Z_up = A_up / C_up` might not be correct for exponential horns

3. **Units mismatch**: The T-matrix or impedance functions might be using wrong units (cm vs m, etc.)

4. **Hornresp compatibility issue**: Hornresp might use different formulas than standard transmission line theory

5. **Driver parameters mismatch**: The driver parameters from Hornresp might not match our ThieleSmallParameters model

## Next Steps for Research

The admittance method implementation appears correct based on the research provided, but the **underlying T-matrix or impedance calculations are wrong**.

### Questions for Further Research

1. **How does Hornresp calculate tapped horn impedance?**
   - Does Hornresp use T-matrices or a different method?
   - Can we find Hornresp's algorithm documentation or source code?

2. **Is our T-matrix calculation correct?**
   - Check `exponential_horn_tmatrix()` against known results
   - Verify the formulas against Kolbrek's MMM_toolbox

3. **Is the upstream impedance formula correct?**
   - For exponential horn with closed end: Z = A/C?
   - Should this be different for exponential vs conical?

4. **Are there unit conversion issues?**
   - TappedHorn uses cm² for areas, cm for lengths
   - T-matrix functions expect m² and m
   - Verify all conversions are correct

5. **What does Hornresp show for the impedances?**
   - Can we export impedance data from Hornresp?
   - Compare Z_up, Z_down, Z_tap values directly

## Files Created

- `tasks/tapped_horn_phase_research_handoff.md` - Original handoff document
- `tasks/debug_tapped_horn_comparison.py` - Debug output showing errors
- `tasks/test_original_implementation.py` - Test of original simple method
- `tasks/tapped_horn_status_update.md` - This file

## Recommendation

**STOP** trying to fix the SPL calculation until the impedance calculation is correct. The wrong impedance means the driver loading is wrong, which means the diaphragm velocity is wrong, which means the SPL will be wrong no matter how we calculate it.

**Focus research on**:
1. How Hornresp calculates tapped horn impedance
2. Whether our T-matrix functions are correct
3. Whether the impedance formulas are correct for tapped horns

The admittance method for SPL calculation appears to be correctly implemented, but it's using wrong input values (wrong impedance, wrong driver velocity).
