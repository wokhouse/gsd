# Ported Box Denominator Coefficients Analysis

**Date:** 2025-12-28
**Status:** ✅ Current implementation is CORRECT per Small (1973)
**Critical Finding:** Docstring contains incorrect transfer function form

---

## Executive Summary

The current denominator coefficient implementation in `ported_box.py` is **mathematically correct** per Small (1973), Equation 13 (time-constant form). However, **the docstring incorrectly describes the transfer function**, contributing to the confusion about the numerator.

---

## Current Implementation vs Small (1973)

### Current Code (ported_box.py:760-773)

```python
# Small (1973), Eq. 13: Denominator polynomial D(s)
# D(s) = s⁴T_B²T_S² + s³(T_B²T_S/Q_B + T_BT_S²/Q_T) +
#        s²[(α+1)T_B² + T_BT_S/(Q_B×Q_T) + T_S²] +
#        s(T_B/Q_B + T_S/Q_T) + 1

# 4th order coefficient: s⁴
a4 = (Ts ** 2) * (Tb ** 2)

# 3rd order coefficient: s³
a3 = (Tb ** 2 * Ts / QB) + (Tb * Ts ** 2 / Qt)

# 2nd order coefficient: s² (CRITICAL: (α+1) term!)
a2 = (alpha + 1) * (Tb ** 2) + (Tb * Ts / (QB * Qt)) + (Ts ** 2)

# 1st order coefficient: s
a1 = Tb / QB + Ts / Qt

# 0th order coefficient: constant
a0 = 1
```

**Status:** ✅ CORRECT - Matches Small (1973), Eq. 13

### Small (1973), Equation 13 (Time-Constant Form)

```
D(s) = s⁴T_B²T_S² + s³(T_B²T_S/Q_B + T_BT_S²/Q_T) +
       s²[(α+1)T_B² + T_BT_S/(Q_B×Q_T) + T_S²] +
       s(T_B/Q_B + T_S/Q_T) + 1
```

Where:
- T_S = 1/ω_S = 1/(2πF_S) - driver time constant
- T_B = 1/ω_B = 1/(2πF_B) - box (port) time constant
- α = V_as/V_B - compliance ratio
- Q_T = Qts - driver total Q factor
- Q_B = combined box losses

**Status:** ✅ Current implementation matches exactly

---

## CRITICAL BUG FOUND: Incorrect Docstring

### Location
File: `src/gsd/enclosure/ported_box.py`
Lines: 654-664 (docstring)

### Current (Incorrect) Docstring

```python
Transfer Function Form:
    The normalized pressure response for a vented box is a 4th-order
    high-pass filter with the form:

    G(s) = K × (s²T_B² + sT_B/Q_B + 1) / D'(s)  # ❌ WRONG!

    where D'(s) is the 4th-order denominator polynomial (same as impedance):

    D'(s) = s⁴T_B²T_S² + s³(T_B²T_S/Q_B + T_BT_S²/Q_T) +
            s²[(α+1)T_B² + T_BT_S/(Q_B×Q_T) + T_S²] +
            s(T_B/Q_B + T_S/Q_T) + 1
```

### Problem

The docstring claims the numerator is `(s²T_B² + sT_B/Q_B + 1)`, which is:
- The **port resonance term** from Small's Eq. 16 (voice coil impedance)
- NOT the SPL transfer function numerator
- Exactly the incorrect form that was tested and failed (error 4.38 → 13.54 dB)

### Actual Implementation (Line 780)

```python
# Numerator (Small 1973, Eq. 13): N(s) = s⁴T_B²T_S²
# This matches the denominator's leading term to ensure G(s) → 1 as s → ∞
numerator = (s ** 4) * a4  # ✅ CORRECT
```

### Impact

This incorrect docstring:
1. **Confuses readers** about what the correct transfer function is
2. **May have led to the incorrect "port resonance numerator" test**
3. **Contradicts the actual code implementation**
4. **Contributes to the documentation inconsistency** identified in PR #27 code review

---

## Box Losses Implementation (Small Eq. 19)

### Current Implementation (ported_box.py:742-749)

```python
# Small (1973), Eq. 19: Combined box losses
# 1/QB = 1/QL + 1/QA + 1/QP
# QB represents the total losses from leakage, absorption, and port

if QL == float('inf') and QA == float('inf') and Qp == float('inf'):
    QB = float('inf')
else:
    QB = 1.0 / (1.0/QL + 1.0/QA + 1.0/Qp)
```

**Status:** ✅ CORRECT - Matches Small (1973), Eq. 19

### Default Values

- QL = 7.0 (Hornresp default for leakage losses)
- QA = 100.0 (absorption losses ≈ negligible)
- Qp = 7.0 (port losses)

Result: QB ≈ 3.5 (combined losses)

**Status:** ✅ Reasonable defaults

---

## Verification: Comparison with Research Formulas

### Research Form (Small Normalized Form)

From research agent (Small 1973, Eq. 20-24):
```
h = f_S/f_B
a₁ = (Q_L + h·Q_T) / (h·Q_L·Q_T)
a₂ = [h + (α + 1 + h²)·Q_L·Q_T] / (h·Q_L·Q_T)
a₃ = (h·Q_L + Q_T) / (h·Q_L·Q_T)
```

**Note:** This is a mathematically equivalent form using:
- Normalized coefficients relative to T₀ = T_B·T_S
- Single loss parameter Q_L (simplified from combined QB)

The current implementation uses the **time-constant form** (Small Eq. 13), which is more explicit and easier to verify.

**Conclusion:** Both forms are mathematically equivalent. The current implementation is correct.

---

## Root Cause of Missing Fb Peak

If the denominator coefficients are correct, why is there no peak at Fb?

### Possible Explanations

1. **Not a coefficient problem**
   - The transfer function form is correct
   - The coefficients are calculated correctly
   - The issue is elsewhere in the implementation

2. **Port radiation contribution**
   - The transfer function G(s) represents net volume velocity
   - At Fb, port output dominates
   - Implementation may not properly account for port phase relationship

3. **Reference level / normalization**
   - Hornresp may use different reference point
   - Calibration offset may be masking the peak
   - The "peak" might be relative to a different baseline

4. **Frequency resolution / evaluation**
   - The peak might be present but not captured at exact Fb
   - Need to evaluate at finer frequency resolution around Fb

### Recommendation

**DO NOT change denominator coefficients** - they are correct per Small (1973).

**INSTEAD investigate:**
- Port radiation model (net pressure calculation)
- Frequency evaluation at Fb ± 1 Hz to capture peak
- Comparison with Hornresp's exact transfer function implementation
- Whether the peak is in the cone response, port response, or combined response

---

## Action Items

### Priority 1: Fix Incorrect Docstring ✅ TODO

**File:** `src/gsd/enclosure/ported_box.py`
**Lines:** 654-664

Change from:
```python
G(s) = K × (s²T_B² + sT_B/Q_B + 1) / D'(s)
```

To:
```python
G(s) = s⁴T_B²T_S² / D(s)
```

This matches the actual implementation and Small (1973), Eq. 13.

### Priority 2: Update Validation Documentation ✅ TODO

**File:** `docs/validation/ported_box_spl_validation_bc15ds115.md`

**Remove:**
- Claim of "critical bug in numerator"
- Suggestion that (s²T_B² + sT_B/Q_B + 1) is the correct numerator

**Add:**
- Clarification that the "port resonance numerator" test failed because it's from impedance equation, not SPL
- Confirmation that s⁴T_B²T_S² is correct per Small (1973), Eq. 13

### Priority 3: Investigate Fb Peak (Separate from coefficient issue)

The missing peak is likely NOT due to denominator coefficients (which are correct). Investigation should focus on:
- Port radiation contribution
- Frequency resolution around Fb
- Reference level calculation

---

## Conclusion

✅ **Denominator coefficients are CORRECT** per Small (1973), Eq. 13
❌ **Docstring is INCORRECT** and contributes to confusion
✅ **Numerator (s⁴T_B²T_S²) is CORRECT** per Small (1973), Eq. 20

**The research agent's findings are confirmed:**
- Current transfer function form is mathematically correct
- "Port resonance numerator" test failed because it's the wrong equation (impedance, not SPL)
- The real issue (missing Fb peak) is elsewhere in the implementation

**Next steps:**
1. Fix docstring (immediate)
2. Update validation documentation (immediate)
3. Fix BC_18RBX100 regression (address calibration offset)
4. Investigate Fb peak separately (port radiation model, not coefficients)
