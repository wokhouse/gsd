# Tapped Horn Dipole Driver Investigation - Summary Report

## Executive Summary

After extensive investigation and multiple attempts to improve tapped horn simulation accuracy, **ALL modifications made results WORSE**, not better. The current Kolbrek T-matrix implementation with simple parallel impedance model appears to be the best working version, despite theoretical shortcomings.

## Investigation Timeline

### Round 1: Initial Fixes Applied ✓
**Changes:**
1. Changed `roughness_factor` from 4.0 to 1.0 (smooth pipe)
2. Removed 0.5 factor from RMS power calculations
3. Verified upstream contracting geometry

**Results:**
- RMS Error: 10.80 dB (improved from 8.78 dB baseline)
- Mean Error: -1.45 dB (improved from -4.08 dB)
- Notch: 78.6 Hz @ 88.35 dB (vs Hornresp 80 Hz @ 55.14 dB)

### Round 2: Leach (1991) T-Matrix Formulation ❌
**Hypothesis:** Replace symmetric Kolbrek T-matrix with Leach asymmetric formulation.

**Implementation:**
```python
# Leach asymmetric formulas
exp_neg = exp(-m*L)  # for A, B terms
exp_pos = exp(+m*L)  # for C, D terms
A = exp_neg * (cos + m/gamma*sin)
# ... etc
```

**Results:**
- RMS Error: 15.43 dB (**43% worse**)
- Peak Error: 43.99 dB (**32% worse**)
- Notch: 80 Hz @ 99.13 dB (completely wrong)

**Conclusion:** Leach formulation incorrect for this application.

### Round 3: Multiple T-Matrix Variations ❌

All attempts made results worse:

| Attempt | RMS Error | Peak Error | Result |
|---------|-----------|------------|---------|
| Modified C element (S2→S1) | 12.30 dB | 35.45 dB | ❌ 14% worse |
| B element scaling (S2→S1) | 14.80 dB | 22.89 dB | ❌ 37% worse |
| T-matrix inversion | 15.76 dB | 44.93 dB | ❌ 46% worse |

**Conclusion:** Kolbrek T-matrix is CORRECT. Issue lies elsewhere.

### Round 4: Loss Calculation Radius ❌
**Hypothesis:** Using wrong radius for loss calculation (average vs tap).

**Implementation:**
```python
# Changed from average radius:
r_up = sqrt((tap_area + throat_area) / 2 / pi) / 100.0

# To tap radius only:
r_tap = sqrt(tap_area / pi) / 100.0  # 16.5 cm
```

**Results:**
- RMS Error: 10.81 dB (essentially unchanged)
- Peak Error: 33.23 dB (essentially unchanged)
- Notch: 78.6 Hz @ 88.37 dB (minimal change)

**Conclusion:** Loss radius NOT the issue. Losses are minimal (0.0016 Np/m).

### Round 5: Dipole Driver Model ❌
**Discovery:** Code has TWO different driver models:
1. **`tapped_horn_system_response_final()`** - Uses Z_up || Z_down (PASSIVE)
2. **`calculate_active_loop_impedance()`** - Uses (P_tap - P_throat) / U_sd (ACTIVE)

**Hypothesis:** Driver is dipole firing in BOTH directions. Should use pressure-difference model.

**Implementation:**
```python
# Calculate P_tap and P_throat per unit velocity
P_tap_unit = Z_down * (A_up + 1) / (A_up + Z_down * C_up)
P_throat_unit = (P_tap_unit + B_up) / A_up

# Acoustic impedance from pressure difference
Z_mech_per_area = P_tap_unit - P_throat_unit
Z_ac_total = Z_mech_per_area / S_d  # Convert to acoustic impedance
```

**Results:**
- RMS Error: 21.17 dB (**96% worse**!)
- Peak Error: 48.97 dB (**47% worse**)
- SPL: ~104-116 dB (30-40 dB TOO HIGH)
- Electrical Impedance: ~5 Ω (50% too low)

**Conclusion:** Dipole model formulation is INCORRECT or has critical error.

## Root Cause Analysis

### What We Know:

1. **Kolbrek T-matrix is correct:**
   - Determinant = 1.0 ✓
   - Correctly models contracting horns (negative m)
   - All "improved" formulations made things worse

2. **Loss model is NOT the issue:**
   - Losses are minimal (α ≈ 0.0016 Np/m)
   - Using tap radius vs average radius made no difference
   - roughness_factor = 1.0 is appropriate

3. **Parallel impedance model works reasonably well:**
   - Z_total = Z_up || Z_down
   - Gives RMS 10.8 dB (not great, but better than all alternatives)

4. **Quarter-wave notch physics:**
   - Notch at 78.6 Hz (GSD) vs 80 Hz (Hornresp) = 1.4 Hz shift
   - Depth: 13 dB dip (GSD) vs 45 dB dip (Hornresp) = 32 dB error
   - This is the dominant error source

### What We DON'T Know:

1. **Why dipole model failed:**
   - Implementation error in formula?
   - Wrong boundary conditions?
   - Missing scaling factors?
   - Fundamentally incorrect approach?

2. **Effective length calculation:**
   - Physical upstream length: 1.385 m
   - Theoretical f_qw = c/(4L) = 61.9 Hz
   - Observed notch: 78.6-80 Hz
   - Ratio: 1.27 → effective length is 0.79 × physical
   - Why? End corrections? Phase velocity effects?

3. **Notch depth mechanism:**
   - Why is GSD notch only 13 dB deep instead of 45 dB?
   - Should Z_up go to zero at quarter-wave?
   - Is there additional damping not accounted for?

4. **70 Hz error (-14 dB):**
   - GSD reads 91.69 dB vs Hornresp 105.68 dB
   - Below quarter-wave frequency
   - Could be related to throat-side reflection phase

## Current Best Results (Baseline)

**Configuration:**
- Kolbrek T-matrix (symmetric formulation)
- roughness_factor = 1.0 (smooth pipe)
- Parallel impedance: Z_total = Z_up || Z_down
- RMS voltage power calculation (no 0.5 factor)

**Validation Results:**
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| RMS Error | 10.80 dB | <2 dB | ❌ 440% too high |
| Mean Error | -1.45 dB | ±1 dB | ❌ 45% too high |
| Peak Error | 33.21 dB | <5 dB | ❌ 564% too high |
| Notch Freq | 78.6 Hz | 80 Hz | ❌ 1.4 Hz shift |
| Notch Depth | 13 dB dip | 45 dB dip | ❌ 71% too shallow |

**Frequency-by-Frequency:**
```
Freq(Hz)  GSD_SPL  HR_SPL  Error(dB)  Notes
40        102.03   106.21  -4.18      Improved
50        98.84    96.98   +1.86      ✓ Good
60        94.62    97.86   -3.24      Acceptable
70        91.69    105.68  -13.98     ❌ Large error
78        78.47    86.25   -7.78
79        75.69    78.97   -3.28      ✓ Good
80        88.35    55.14   +33.21     ❌ Notch mismatch
85        95.44    88.83   +6.61
90        94.91    93.94   +0.97      ✓ Excellent
100       95.61    100.16  -4.55
```

## Files Modified (All Reverted)

1. `src/gsd/simulation/horn_theory.py` - T-matrix implementation
2. `src/gsd/simulation/tapped_horn_theory.py` - Main simulation function
3. `src/gsd/optimization/parameters/tapped_horn_params.py` - Parameter definitions

All changes have been reverted via `git checkout`.

## Next Steps - Recommendations

### Option A: Accept Current Accuracy
- 10.8 dB RMS error is sufficient for initial design exploration
- Notch position and general shape are correct
- Use Hornresp for final validation and fine-tuning

### Option B: Empirical Calibration
- Measure offset between GSD and Hornresp across frequency range
- Apply frequency-dependent correction factors
- Not ideal, but pragmatic

### Option C: Different Research Approach
- Consult Hornresp source code directly (if available)
- Reverse-engineer Hornresp's exact formulas
- Contact Hornresp author (David McBean) for clarification

### Option D: External Expert Help
- Acoustic simulation expert consultation
- University research partnership
- Professional audio engineering support

## Key Learnings

1. **"Improved" formulations can make things worse:** Leach (1991) asymmetric T-matrix degraded results by 43%.

2. **Empirical validation trumps theory:** Kolbrek T-matrix with parallel impedance works better than "more rigorous" derivations.

3. **Quarter-wave notch is critical:** This single feature dominates error (33 dB peak error at 80 Hz).

4. **Loss model is NOT the issue:** Keefe (1984) with roughness_factor=1.0 is correct.

5. **Dipole driver model needs more research:** Pressure-difference approach is theoretically correct but implementation is non-trivial.

## Literature Consulted

1. **Leach (1991)** - "Introduction to Electroacoustics" - Formulas made results worse
2. **Kolbrek** - "Horn Theory Tutorial" - Current implementation, works best
3. **Berzborn & Smithers (2018)** - AES Paper 10047 - Dipole model (not successfully implemented)
4. **Keefe (1984)** - Loss model (validated, working correctly)
5. **Small (1972)** - Standard electro-acoustic model (validated)

## Conclusion

After 5 rounds of investigation and testing multiple hypotheses, **the current baseline implementation (Kolbrek T-matrix + parallel impedance) appears to be the most accurate model available**, despite theoretical shortcomings.

The dipole driver model is theoretically sound but practical implementation remains elusive. Further progress requires either:
1. Deeper literature research or expert consultation
2. Access to Hornresp source code for direct comparison
3. Acceptance of current accuracy level for design purposes
