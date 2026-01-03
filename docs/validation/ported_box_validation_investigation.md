# Ported Box Validation Investigation - Summary

**Date:** 2025-12-28
**Branch:** `fix/ported-box-transfer-function-numerator`
**Status:** Investigation complete - Qts mismatch identified as primary issue

---

## Executive Summary

Validation against Hornresp revealed a **Qts parameter mismatch** as the primary cause of SPL errors at low frequencies. The gsd driver definition has **Qts = 0.0611**, while Hornresp uses **Qts = 0.0510** (calculated from physical parameters).

**Impact:**
- With correct Qts: Mean error improves from 6.09 dB → 5.36 dB (at 4 test frequencies)
- Optimal calibration offset: **+3 dB** (not +6 dB as currently used)
- Remaining error at 20 Hz: **-10.84 dB** (shape issue, not just level)

---

## Root Cause Analysis

### 1. Qts Parameter Mismatch

**GSD driver:**
```
Qes = 0.0631
Qms = 1.9006
Qts = 0.0611
```

**Hornresp (calculated from physical):**
```
Qes = 0.0527
Qms = 1.5869
Qts = 0.0510
```

**Difference:** 0.0101 (16.5% relative error)

**Source:** Discrepancy in how Q parameters are calculated or defined. Hornresp likely calculates Q directly from M_ms, C_ms, R_ms, while gsd uses Thiele-Small parameter values.

### 2. Calibration Offset

**Current:** +6 dB (tuned for BC_18RBX100)
**Optimal for BC_15DS115:** +3 dB
**Impact:** 3 dB constant offset error

**Finding:** Calibration offset is **driver-specific**, not universal. Different drivers may need different offsets.

### 3. Bass Response Shape Issue

**Hornresp response:**
```
20 Hz:  92.8 dB  ← PEAK at tuning
30 Hz:  84.9 dB  ← DIP
40 Hz:  85.4 dB
100 Hz: 92.0 dB
```

**GSD response (with corrected Qts):**
```
20 Hz:  81.97 dB  ← TOO LOW (should be peak!)
30 Hz:  90.38 dB  ← TOO HIGH
40 Hz:  89.93 dB  ← TOO HIGH
100 Hz: 92.53 dB  ← GOOD (only +0.54 dB error)
```

**Observation:** GSD doesn't show the characteristic **peak at Fb**. The bass shape is fundamentally different.

---

## Transfer Function Investigation

### Coefficient Verification

The denominator coefficients match Thiele (1971):

```
a4 = T_S² × T_B²  ✓
a3 = T_B²T_S/Q_B + T_BT_S²/Q_T  ✓
a2 = (α+1)T_B² + T_BT_S/(Q_B×Q_T) + T_S²  ✓
a1 = T_B/Q_B + T_S/Q_T  ✓
a0 = 1  ✓
```

**Finding:** Coefficients are correctly implemented.

### Numerator Investigation

**Current implementation:**
```python
numerator = (s ** 4) * a4  # s⁴T_B²T_S²
```

This ensures G(s) → 1 as s → ∞ (flat HF response), which is correct.

**Alternative tested:**
```python
numerator = (s ** 2) * (Tb ** 2) + s * (Tb / QB) + 1  # Port resonance term
```

**Result:** Made things **much worse** (error: 4.38 dB → 13.54 dB mean)
**Reason:** Causes excessive HF roll-off (G → 0 as s → ∞ instead of G → constant)

**Conclusion:** The current numerator `s⁴T_B²T_S²` is **correct** for ensuring proper HF response.

---

## Alignment Analysis

**Driver:** BC_15DS115 with **Qts = 0.051** (extremely low!)

**B4 Butterworth requirements:**
- Qts: 0.38-0.45
- α: ~1.2 (for Qts=0.40)
- h: ~0.69

**Current design (400L @ 20Hz):**
- Qts: 0.051 ✗ (far from B4 range)
- α: 0.634
- h: 0.606

**Implication:** This is **NOT a B4 alignment**. With Qts=0.051, the system has:
- Very weak damping
- Significant peaking at Fb
- F3 very close to Fb (~20 Hz)

**Hornresp correctly shows:** 92.8 dB peak @ 20 Hz (tuning frequency)
**GSD incorrectly shows:** 81.97 dB @ 20 Hz (no peak)

---

## Findings Summary

### What's Correct

1. ✓ Denominator coefficients match Thiele (1971)
2. ✓ Numerator form `s⁴T_B²T_S²` is correct for HF behavior
3. ✓ Port dimensions match Hornresp (155.06cm² × 22.91cm)
4. ✓ HF roll-off implementation is correct

### What's Wrong

1. ✗ **Qts parameter mismatch** (0.0611 vs 0.0510) → 16.5% error
2. ✗ **Calibration offset** (+6 dB vs optimal +3 dB) → 3 dB error
3. ✗ **Missing peak at Fb** → Shape is wrong in bass region

### Impact of Issues

| Issue | Impact | Fix Difficulty |
|-------|--------|---------------|
| Qts mismatch | Affects bass shape, 20 Hz error | Medium - need to correct driver definition |
| Calibration offset | 3 dB constant error | Easy - change from 6 dB to 3 dB |
| Missing peak at Fb | 10-14 dB error at 20 Hz | Unknown - requires deeper investigation |

---

## Recommendations

### Immediate (Easy Fixes)

1. **Update calibration offset to +3 dB**
   - File: `src/gsd/enclosure/ported_box.py:846`
   - Change: `CALIBRATION_OFFSET_DB = 6.0` → `CALIBRATION_OFFSET_DB = 3.0`
   - Expected improvement: ~1 dB (mean error)

2. **Correct Qts in driver definition**
   - File: `src/gsd/driver/bc_drivers.py`
   - Investigate source of Qts discrepancy
   - Recalculate from physical parameters if needed
   - Expected improvement: ~0.7 dB (mean error)

### Investigation Required

3. **Investigate missing peak at Fb**
   - Review Thiele (1971) transfer function formulation
   - Check if transfer function should be product of two 2nd-order sections
   - Compare with Hornresp implementation details
   - May require literature review of Small (1973)

4. **Driver-specific calibration**
   - Current calibration is tuned for BC_18RBX100
   - May need driver-specific calibration factors
   - Consider auto-calibration against Hornresp reference

---

## Validation Data

### Test Conditions

- Driver: BC_15DS115-8
- Design: 400L @ 20Hz
- Port: 155.06cm² × 22.91cm
- Input: 2.83V (1W into 4.9Ω)
- Reference: Hornresp simulation

### Comparison Summary (Best Case)

**With Qts = 0.0510 and +3 dB calibration:**

| Freq (Hz) | Hornresp | GSD | Error | Status |
|-----------|----------|----------|-------|--------|
| 20.15     | 92.81    | ~82      | -10.8 | ✗ Poor |
| 30.08     | 84.87    | ~90      | +5.5  | ✗ Poor |
| 40.04     | 85.36    | ~90      | +4.6  | ✗ Poor |
| 100.00    | 91.99    | ~92.5    | +0.5  | ✓ Excellent |

**Mean error (20-100 Hz):** ~5.3 dB
**Main issue:** Bass response shape wrong below 40 Hz

---

## Next Steps

### Option 1: Accept Current Accuracy

If 5 dB mean error is acceptable:
- Apply Qts correction
- Update calibration offset
- Document known limitations
- Focus on relative flatness (not absolute SPL)

### Option 2: Deep Investigation

If better accuracy is required:
- Literature review: Small (1973) complete paper
- Transfer function reformulation investigation
- Possible Hornresp algorithm reverse-engineering
- Multi-driver validation study

### Option 3: Empirical Calibration

Create Hornresp-based calibration:
- Run Hornresp simulations for multiple drivers
- Build calibration lookup table
- Apply corrections based on driver parameters
- Less theoretically pure, but practically accurate

---

## Files Modified

1. `docs/validation/ported_box_spl_validation_bc15ds115.md` - Initial validation report
2. `docs/validation/ported_box_validation_investigation.md` - This investigation summary
3. `src/gsd/driver/bc_drivers.py` - **NOT YET MODIFIED** (Qts correction pending)
4. `src/gsd/enclosure/ported_box.py` - **NOT YET MODIFIED** (calibration pending)

---

## References

1. **Hornresp simulation:**
   - `/Users/fungj/vscode/gsd/imports/ported_sim.txt`
   - `/Users/fungj/vscode/gsd/imports/ported_params.txt`

2. **Literature:**
   - Thiele (1971) - "Loudspeakers in Vented Boxes"
   - `literature/thiele_small/thiele_1971_vented_boxes.md`

3. **Previous validation work:**
   - `docs/validation/transfer_function_spl_implementation.md`
   - `docs/validation/PORTED_BOX_IMPEDANCE_FIX_STATUS.md`

---

**Status:** Investigation complete, awaiting decision on fix approach
**Branch:** `fix/ported-box-transfer-function-numerator`
**Generated:** 2025-12-28
