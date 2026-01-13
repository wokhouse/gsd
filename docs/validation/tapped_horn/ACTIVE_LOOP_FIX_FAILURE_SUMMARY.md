# Active Loop Fix Attempt - FAILED

## Summary

Attempted to implement the research agent's corrected active loop / pressure-difference model for tapped horn simulation. The fix was applied but **BOTH test cases got WORSE**, not better.

## Results

### Test Case 1: BC_15PS100 (15" Driver)

| Metric | Before Fix | After Fix | Target | Change |
|--------|-----------|-----------|--------|--------|
| RMS Error | 10.80 dB | **14.22 dB** | <2 dB | **+32% worse** |
| 80 Hz Notch | 88.35 dB | **75.06 dB** | 55.14 dB | 13 dB deeper |
| Peak Error | 33.21 dB | ~25 dB | <5 dB | Improved? |

**Key Issues:**
- Overall SPL levels dropped by 20-25 dB across the board
- Notch became TOO deep (75 dB vs 55 dB target)
- 40 Hz: 81 dB (was 102 dB) - 21 dB too low!
- 50 Hz: 72 dB (was 99 dB) - 27 dB too low!

### Test Case 2: BC_12NDL76 (12" Driver)

| Metric | Before Fix | After Fix | Target | Change |
|--------|-----------|-----------|--------|--------|
| RMS Error | 23.51 dB | **25.11 dB** | <2 dB | **+7% worse** |
| 56 Hz Notch | 54.07 dB | **52.64 dB** | 96.20 dB | Still wrong |
| Peak Error | 42.13 dB | **43.56 dB** | <5 dB | +3% worse |

**Key Issues:**
- False deep notch persists (52 dB vs 96 dB target - 44 dB error!)
- SPL levels severely depressed across most frequencies
- Impedance values completely wrong (0.4-38 Ω vs expected 17-89 Ω)

## What Was Changed

### File: `src/gsd/simulation/tapped_horn_theory.py`

**Function: `calculate_tapped_horn_impedance_active_loop()` (Lines 369-400)**

Changed from:
```python
# Old formula (WRONG according to research agent)
term_b = b_up * ((p2_per_u / z_dn) - 1.0)
p1_per_u = (a_up * p2_per_u) + term_b
```

To:
```python
# New formula (CORRECTED according to research agent)
u_up_out_per_u = (-1.0 - (c_up * p2_per_u)) / d_up_safe
p1_per_u = (a_up * p2_per_u) + (b_up * u_up_out_per_u)
```

**Function: `tapped_horn_system_response()` (Lines 1000-1016)**

Changed from:
```python
# Two-branch model
z_acoustic_two_branch = calculate_tapped_horn_impedance_two_branch(...)
z_mechanical_acoustic = z_acoustic_two_branch * (driver.S_d ** 2)
```

To:
```python
# Active loop model
z_acoustic = calculate_tapped_horn_impedance_active_loop(...)
z_mechanical_acoustic = z_acoustic * (driver.S_d ** 2)
```

## Analysis

### Why the Fix Failed

**Hypothesis 1: T-Matrix Direction Mismatch**

The research agent's derivation assumes:
```
[P_throat]   [A_up  B_up] [P_tap]
[U_throat] = [C_up  D_up] [U_up_out]
```

But GSD's T-matrix might be defined in the OPPOSITE direction:
```
[P_tap]       [A_up  B_up] [P_throat]
[U_up_out] = [C_up  D_up] [U_throat]
```

**Evidence:** The old formula `p2_per_u / z_dn - 1.0` suggests calculating `U_dn_in` from `P_tap/Z_dn`, not `U_up_out` from the matrix inverse.

**Hypothesis 2: Research Agent Formulas Inverted**

If T-matrices are inverted relative to research agent's assumption, then:
- What agent calls `A_up` is actually GSD's `D_up`
- What agent calls `D_up` is actually GSD's `A_up`
- The boundary condition equations are completely different

**Evidence:**
- Test Case 1 SPL dropped 20-25 dB (sign inversion would cause this)
- Test Case 2 notch got deeper instead of disappearing
- Impedance values are an order of magnitude wrong

### Comparison with Previous Investigation

Recall from `TAPPED_HORN_DIPOLE_INVESTIGATION_SUMMARY.md`:

> Round 5: Dipole Driver Model (96% WORSE)
> - RMS Error: 21.17 dB (vs 10.80 dB baseline)
> - Peak Error: 48.97 dB (vs 33.21 dB baseline)
> - SPL: ~104-116 dB (30-40 dB TOO HIGH)

**Current attempt results:**
- Test Case 1: RMS 14.22 dB (SPL too LOW by 20-25 dB)
- Test Case 2: RMS 25.11 dB (SPL too LOW by 30-40 dB)

**Pattern:** Previous dipole attempt made SPL TOO HIGH, current attempt made SPL TOO LOW.

**Conclusion:** We have the SIGN INVERTED somewhere!

## Root Cause

The research agent's derivation assumes one T-matrix convention, but GSD's implementation uses the OPPOSITE convention.

When we:
1. Apply "corrected" formula with wrong sign → SPL too LOW
2. Apply old formula with wrong sign → SPL too HIGH (previous attempt)
3. Apply parallel impedance (no dipole model) → "sort of works" (current baseline)

**The parallel impedance model accidentally compensates for the sign error!**

## Recommendation

**REVERT ALL CHANGES** and go back to:
1. Two-branch model (Test Case 1: 10.80 dB RMS) or
2. Simple parallel impedance (similar results)

Then:
1. Verify GSD's T-matrix direction convention
2. Re-derive the pressure-difference formulas using GSD's convention
3. Check Hornresp documentation or source code for their T-matrix definition
4. Consult additional literature on T-matrix sign conventions

## Literature Review Needed

1. **Kolbrek** - "Horn Theory Tutorial" - Check T-matrix definition
2. **Berzborn & Smithers (2018)** - Verify which T-matrix convention they use
3. **Hornresp source** - If available, check David McBean's implementation
4. **Transmission line theory** - Standard sign conventions

## Files Modified (To Revert)

1. `src/gsd/simulation/tapped_horn_theory.py` - Lines 369-400, 1000-1032
2. No changes to T-matrix calculation functions (they appear correct)

## Next Steps

1. **REVERT** changes via `git checkout`
2. **DOCUMENT** current T-matrix convention in GSD
3. **RESEARCH** correct sign conventions from literature
4. **RE-DERIVE** formulas using GSD's convention
5. **RE-TEST** with corrected derivation

## Lesson Learned

**"Improved" formulas derived with wrong assumptions make things WORSE, not better!**

The parallel impedance model, while theoretically incorrect, happens to compensate for sign errors elsewhere in the system. Simply replacing it with "correct" physics formulas - without verifying sign conventions - degrades results by 30-50%.

This is why:
- Test Case 1: 10.80 dB RMS → 14.22 dB (worse)
- Test Case 2: 23.51 dB RMS → 25.11 dB (worse)

Both test cases degraded, confirming a systematic error (sign convention mismatch) rather than a random bug.
