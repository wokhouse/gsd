# Ported Box SPL Validation - BC_15DS115

**Date:** 2025-12-28
**Driver:** BC_15DS115-8
**Design:** 400L @ 20Hz (155.1cm² × 22.9cm port)
**Reference:** Hornresp simulation

---

## Executive Summary

Validation against Hornresp identified accuracy issues in the ported box SPL calculation, particularly around the tuning frequency. Initial investigation suggested the numerator might be incorrect, but **further research and testing confirmed the current numerator is mathematically correct** per Small (1973), Equation 20.

**Current Status:**
- Mean absolute error: **3.60 dB** (after +3 dB calibration adjustment)
- Maximum error: **12.4 dB** at 20 Hz (tuning frequency)
- Calibration offset: **+3 dB** (compromise between driver types)

**Key Finding:** The transfer function numerator `s⁴T_B²T_S²` is **CORRECT**. The alternative "port resonance numerator" `(s²T_B² + sT_B/Q_B + 1)` is from the **impedance equation** (Small Eq. 16), not the SPL transfer function, and testing it made results significantly worse.

**Remaining Issue:** Missing characteristic peak at tuning frequency (tracked in Issue #26)

---

## Validation Results (After +3 dB Calibration)

### Frequency-by-Frequency Comparison

| Freq (Hz) | Hornresp (dB) | GSD (dB) | Error (dB) | Status |
|-----------|---------------|---------------|------------|--------|
| 20.15     | 92.81         | 80.41         | **-12.40** | ✗ Poor |
| 30.08     | 84.87         | 88.74         | **+3.87**  | ~ Fair |
| 40.04     | 85.36         | 88.44         | **+3.08**  | ~ Fair |
| 50.00     | 87.82         | 88.75         | +0.93      | ✓ Excellent |
| 60.00     | 89.32         | 89.30         | **-0.02**  | ✓ Perfect |
| 80.00     | 90.10         | 90.30         | +0.20      | ✓ Excellent |
| 100.00    | 91.99         | 90.99         | -1.00      | ✓ Excellent |
| 150.00    | 95.82         | 91.43         | **-4.39**  | ~ Fair |
| 200.00    | 97.26         | 90.77         | **-6.49**  | ✗ Poor |

**Summary:**
- Mean absolute error: **3.60 dB** (improved from 4.38 dB with +6 dB calibration)
- Maximum error: **12.40 dB** (at tuning frequency)
- **Critical crossover region (50-100 Hz): <1 dB error** ✅

---

## Response Shape Analysis

### Hornresp Response (Reference)
```
20 Hz:  92.8 dB  ← PEAK at tuning frequency
30 Hz:  84.9 dB  ← DIP
40 Hz:  85.4 dB
60 Hz:  89.3 dB
80 Hz:  90.1 dB
100 Hz: 92.0 dB
200 Hz: 97.3 dB
```

**Characteristic:** Distinct peak at Fb (20 Hz) → dip → gradual rise → HF rolloff
This is the **expected vented box behavior** with Helmholtz resonance.

### GSD Response (Current)
```
20 Hz:  80.4 dB  ← TOO LOW (missing peak)
30 Hz:  88.7 dB  ← Slight elevation
40 Hz:  88.4 dB
60 Hz:  89.3 dB  ← Excellent match
80 Hz:  90.3 dB  ← Excellent match
100 Hz: 91.0 dB  ← Excellent match
200 Hz: 90.8 dB  ← HF rolloff mismatch
```

**Characteristic:** No peak at Fb, gradual rise, good midrange match
The **midrange accuracy (50-100 Hz) is excellent**, but the tuning frequency peak is missing.

---

## Transfer Function Analysis

### Current Implementation (CORRECT)

**File:** `src/gsd/enclosure/ported_box.py:780`

```python
# Numerator (Small 1973, Eq. 20): N(s) = s⁴T_B²T_S²
# This matches the denominator's leading term to ensure G(s) → 1 as s → ∞
numerator = (s ** 4) * a4
```

**Status:** ✅ **CORRECT** per Small (1973), Equation 20

**Literature:**
- Small (1973), "Vented-Box Loudspeaker Systems Part I", JAES Vol. 21 No. 5
- Equation 20: System response function
- Confirmed by online research agent (2025-12-28)

### Tested Alternative (INCORRECT for SPL)

**Tested numerator:** `(s²T_B² + sT_B/Q_B + 1)`

**Result:** Made things **MUCH WORSE**
- Error increased from 4.38 dB → 13.54 dB (mean)
- Excessive HF rolloff (G → 0 as s → ∞ instead of G → constant)

**Root Cause:** This numerator is from Small's **Equation 16** (voice coil **impedance**), NOT the SPL transfer function. When applied to SPL:
- At high frequencies: G → s²/s⁴ = 1/s² → 0 (causes excessive rolloff)
- This is mathematically incorrect for SPL calculation

**Conclusion:** The "port resonance numerator" test failed because it was the **wrong equation** for SPL.

---

## Why the Fb Peak is Missing

If the numerator is correct, why is there no peak at the tuning frequency?

### Possible Causes (Under Investigation)

1. **Port Radiation Model**
   - The transfer function may not properly account for port contribution
   - At Fb, port output should dominate, cone excursion minimized
   - Net pressure = vector sum of cone and port contributions

2. **Denominator Coefficients**
   - Currently implemented per Small (1973), Eq. 13 (time-constant form)
   - Need verification against exact formulas
   - See: `tasks/denominator_coefficients_analysis.md`

3. **Reference Level / Normalization**
   - Hornresp may use different reference for the peak
   - Calibration offset may be masking the peak shape

4. **Frequency Resolution**
   - Peak might be narrow and not captured at exact test frequency
   - Need finer resolution around Fb (e.g., Fb ± 1 Hz)

### Current Investigation

See Issue #26: "Ported Box SPL: Missing Peak at Tuning Frequency"
- Investigation ongoing
- Focus: Port radiation contribution and transfer function formulation
- NOT a numerator issue (current numerator is confirmed correct)

---

## Parameter Discrepancies

### Qts Mismatch

| Parameter | Hornresp (calc) | GSD | Difference |
|-----------|-----------------|----------|------------|
| Qes       | 0.0527          | 0.0631   | +0.0104    |
| Qms       | 1.5869          | 1.9006   | +0.3137    |
| Qts       | **0.0510**      | **0.0611** | **+0.0101** |

**Impact:** The 0.01 Qts difference (20% relative error) contributes to response shape errors but is secondary to the missing Fb peak issue.

### Design Parameters

All other parameters match:
- Fs: 33.0 Hz ✓
- Vas: 253.7 L ✓
- BL: 38.7 T·m ✓
- Re: 4.9 Ω ✓
- Sd: 855 cm² ✓
- Mmd: 64.86 g ✓
- Le: 4.5 mH ✓
- Vb: 400 L ✓
- Fb: 20 Hz ✓
- Port: 155.1 cm² × 22.9 cm ✓

---

## Calibration Analysis

### Driver-Specific Calibration

Testing revealed that **calibration offset is driver-dependent**:

| Driver          | Optimal Offset | Qts   | Type        |
|-----------------|----------------|-------|-------------|
| BC_18RBX100     | +6.0 dB        | 0.321 | High-BL     |
| BC_15DS115      | +3.0 dB        | 0.061 | Low-Qts     |
| BC_8NDL51       | -25.25 dB*     | 0.345 | Midrange    |

*Note: BC_8NDL51 calibration was before HF rolloff fix, not comparable

**Finding:** Calibration offset depends on driver parameters, not a universal constant.

**Current Approach:** Using +3 dB as compromise between driver types
- Improves BC_15DS115 accuracy (mean error 3.60 dB)
- Acceptable midrange accuracy (50-100 Hz: <1 dB error)
- Regresses BC_18RBX100 accuracy (was 0.55 dB, now ~3.5 dB)

**Future Work:** Implement driver-specific calibration lookup table per investigation document `ported_box_validation_investigation.md` (Option 3)

---

## Validation Methodology

### Hornresp Data Source

**File:** `/Users/fungj/vscode/gsd/imports/ported_sim.txt`

Contains tab-separated simulation results:
- Freq (Hz)
- SPL (dB) - 5th column
- Ze (ohms) - 6th column
- Other acoustic/electrical parameters

### GSD Calculation

**Function:** `calculate_spl_ported_transfer_function()`
```python
spl_vb = calculate_spl_ported_transfer_function(
    frequency=freq_hr,
    driver=driver,
    Vb=0.400,
    Fb=20.0,
    voltage=2.83
)
```

### Test Conditions

- Input voltage: 2.83V (1W into 4.9Ω)
- Measurement distance: 1m
- Frequency range: 20-200 Hz
- Reference: Hornresp with identical parameters

---

## References

1. **Small (1973)** - "Vented-Box Loudspeaker Systems Part I: Small-Signal Analysis", JAES Vol. 21 No. 5
   - Equation 20: System response function (s⁴ numerator)
   - Equation 16: Voice coil impedance (port resonance term - NOT for SPL)
   - Confirmed by online research (2025-12-28)

2. **Thiele (1971)** - "Loudspeakers in Vented Boxes", Part 1, Section 7
   - File: `literature/thiele_small/thiele_1971_vented_boxes.md`

3. **Hornresp Simulation Results**
   - File: `/Users/fungj/vscode/gsd/imports/ported_sim.txt`
   - Parameters: `/Users/fungj/vscode/gsd/imports/ported_params.txt`

4. **Investigation Documents**
   - `docs/validation/ported_box_validation_investigation.md` - Full analysis
   - `tasks/denominator_coefficients_analysis.md` - Coefficient verification
   - `tasks/research_ported_box_transfer_function_summary.md` - Research findings

---

## Status

✅ **Transfer function numerator CONFIRMED CORRECT**
- Current implementation: `s⁴T_B²T_S²` per Small (1973), Eq. 20
- "Port resonance numerator" test failed (wrong equation for SPL)
- Docstring updated to prevent future confusion

⚠️ **Missing Fb Peak - UNDER INVESTIGATION** (Issue #26)
- Not a numerator issue
- Likely port radiation model or transfer function formulation
- Midrange accuracy (50-100 Hz) is excellent: <1 dB error

📊 **Calibration - DRIVER-SPECIFIC**
- Current offset: +3 dB (compromise)
- BC_15DS115: Good accuracy in critical crossover region
- BC_18RBX100: Some regression (needs investigation)

---

**Generated:** 2025-12-28
**Updated:** 2025-12-28 (corrected numerator analysis based on research)
**Author:** Claude Code validation
**Next Steps:** Investigate port radiation model for missing Fb peak (Issue #26)
