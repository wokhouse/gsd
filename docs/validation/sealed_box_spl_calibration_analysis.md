# Sealed Box SPL Calibration Investigation - COMPLETE ANALYSIS

## Executive Summary

The +13.5 dB calibration offset was masking **two separate issues**:
1. **Hornresp configured for eighth-space (corner loading)** instead of half-space
2. **Unexplained ~8.5 dB gain** in Hornresp configuration

**Recommendation**: Remove the calibration offset and regenerate Hornresp validation files with standard half-space (2π) configuration.

---

## Investigation Results

### 1. Hornresp Configuration Discovery

**File**: `tests/validation/drivers/bc_8ndl51/sealed_box/results/bc_8ndl51_sealed_box_qtc0_707/input.txt`

**Critical Parameters**:
```
Line  7: Ang = 0.5 x Pi    ← Eighth-space (corner loading: π/2 steradians)
Line 40: Nd = 1            ← Single driver (correct)
Line  8: Eg = 2.83         ← 2.83V input (correct)
```

**This is NOT a standard half-space measurement!**

### 2. SPL Calculation Breakdown

At **500 Hz** with BC_8NDL51 driver (Fs=75Hz, Vas=10.1L, Qes=0.689, Re=2.6Ω):

| Component | Value | Notes |
|-----------|-------|-------|
| **Efficiency (η₀)** | 0.006051 (0.605%) | Small (1972), Eq. 24 ✓ |
| **Input power** | 3.08 W | 2.83V² / 2.6Ω |
| **Reference SPL (half-space 2π)** | 94.77 dB | Matches B&C datasheet (94 dB) ✓ |
| **Reference SPL (eighth-space π/2)** | 100.79 dB | +6.02 dB from half-space |
| **Mass roll-off at 500 Hz** | -3.49 dB | f_mass = 450 Hz |
| **Expected SPL (eighth-space)** | 97.30 dB | 100.79 - 3.49 |
| **Hornresp SPL** | 105.79 dB | From sim.txt |
| **Unexplained gain** | **+8.49 dB** | Difference not accounted for |

### 3. Radiation Space Comparison

| Radiation Space | Steradians | SPL @ 500 Hz | Difference from Hornresp |
|----------------|------------|--------------|--------------------------|
| Full space (4π) | 12.566 | 91.76 dB | -14.03 dB |
| **Half space (2π)** | **6.283** | **94.77 dB** | **-11.02 dB (correct)** ✓ |
| Quarter space (π) | 3.142 | 97.78 dB | -8.01 dB |
| Eighth space (π/2) | 1.571 | 100.79 dB | -5.00 dB |
| **Hornresp (Ang=0.5π)** | π/2 | **105.79 dB** | **0 dB (reference)** |

### 4. GSD Calibration Offset Decomposition

**Current implementation**: +13.5 dB offset

**What it's compensating for**:
- Half-space → eighth-space: +6.02 dB (10·log₁₀(2π/(π/2)))
- Unexplained Hornresp gain: ~+7.5 dB
- **Total**: +13.5 dB

**This is WRONG because**:
1. GSD should use **half-space (2π)** as standard (matches datasheet)
2. Hornresp validation file should be reconfigured for half-space
3. The +13.5 dB offset is empirically matching a non-standard configuration

---

## Ground Truth Verification

### B&C 8NDL51 Datasheet
- **Sensitivity**: 94 dB (2.83V @ 1m)
- **GSD half-space**: 94.77 dB ✓ MATCHES
- **Hornresp eighth-space**: 105.79 dB ✗ 11.8 dB too high

### Small's Theoretical Formula
```
SPL_1W/1m = 112.2 + 10·log₁₀(η₀)  (half-space)
         = 112.2 + 10·log₁₀(0.006051)
         = 112.2 - 22.18
         = 90.02 dB (at 1W)

At 3.08W:
SPL = 90.02 + 10·log₁₀(3.08)
    = 90.02 + 4.88
    = 94.90 dB  ✓ Matches gsd (94.77 dB)
```

---

## Root Cause Analysis

### The +13.5 dB Offset Problem

**Original issue**: GSD calculated 91.14 dB, Hornresp showed 105.79 dB

**Breakdown of the 14.65 dB difference**:
1. **Mass roll-off**: -3.49 dB (f_mass=450 Hz @ 500 Hz)
2. **Half-space calculation**: 94.77 dB (correct theoretical value)
3. **With mass roll-off**: 91.28 dB (matches gsd's 91.14 dB) ✓
4. **Hornresp eighth-space**: Should be 97.30 dB
5. **Actual Hornresp**: 105.79 dB
6. **Unexplained gain**: +8.49 dB

**The +13.5 dB calibration was wrong** because:
- It forced gsd to match a non-standard Hornresp configuration
- It masked the fact that Hornresp was using eighth-space radiation
- It didn't address the unexplained ~8.5 dB gain in Hornresp

---

## Correct Implementation

### What GSD Should Do

```python
# 1. Calculate efficiency (Small 1972, Eq. 24) - CORRECT ✓
k = (4 * π²) / (c³)
eta_0 = k * (fs³ * Vas / Qes)

# 2. System efficiency (sealed box) - CORRECT ✓
eta = eta_0

# 3. Reference power
P_ref = V² / Re

# 4. Pressure calculation (HALF-SPACE - STANDARD)
# Use 2π steradians (infinite baffle, standard test condition)
pressure_rms = √(eta * P_ref * ρ₀ * c / (2π * r²))

# 5. SPL (NO CALIBRATION OFFSET)
spl = 20 * log₁₀(pressure_rms / 20μPa)

# 6. Apply transfer function and HF roll-off
spl += 20*log₁₀(|G(s)|)  # Box transfer function
spl += hf_rolloff         # Mass and inductance roll-off
```

### Expected Result

At 500 Hz, BC_8NDL51 in 31.65L sealed box:
- **GSD SPL**: ~91.1 dB (half-space + mass roll-off)
- **Matches B&C datasheet**: 94 dB ✓ (when referenced to half-space, no mass roll-off)

---

## Hornresp Validation File Fix

### Current (WRONG)
```
Ang = 0.5 x Pi    ← Eighth-space (corner loading)
Nd = 1
Eg = 2.83
```

### Should Be (CORRECT)
```
Ang = 2.0 x Pi    ← Half-space (infinite baffle, standard)
Nd = 1
Eg = 2.83
```

**Expected change**: Hornresp SPL should decrease by ~6 dB
- Current: 105.79 dB
- Corrected: ~99.8 dB (still ~4 dB higher than theory, but closer)

---

## Remaining Questions

### Why is Hornresp still ~8.5 dB higher than expected?

Even with eighth-space configuration accounted for:
- Expected (eighth-space + mass roll-off): 97.30 dB
- Hornresp actual: 105.79 dB
- **Difference: 8.49 dB UNEXPLAINED**

**Possible explanations**:
1. Hornresp uses different physical constants (c, ρ₀)
2. Hornresp has additional boundary gain model
3. Hornresp calculates efficiency differently
4. Hornresp includes radiation impedance effects
5. Different f_mass or inductance model in Hornresp

**Action**: Regenerate Hornresp file with Ang=2.0×π and re-evaluate

---

## Validation Test Results

### Current (with +13.5 dB offset)
```
Max error: 1.84 dB
RMS error: 1.01 dB
Mean error: 0.85 dB
```

**This "good" validation is misleading** because it's matching a non-standard configuration!

### After Fix (expected)
With corrected Hornresp file (Ang=2.0×π):
- GSD (no offset) should match within ±2 dB
- Both should match B&C datasheet (94 dB)

---

## Recommendations

### Immediate Actions

1. **Remove the +13.5 dB calibration offset** from gsd
   - File: `src/gsd/enclosure/sealed_box.py:429`
   - Change: `CALIBRATION_OFFSET_DB = 0.0`

2. **Regenerate Hornresp validation files**
   - Change all files from `Ang = 0.5 x Pi` to `Ang = 2.0 x Pi`
   - Keep `Nd = 1` (single driver)
   - Keep `Eg = 2.83` (standard voltage)

3. **Update validation tests**
   - Expected SPL should be ~91 dB at 500 Hz (with mass roll-off)
   - Expected sensitivity should be ~94 dB (matches datasheet)

4. **Document the standard**
   - GSD uses **half-space (2π steradians)** as standard
   - This matches B&C datasheet and IEEE/IEC standards
   - Infinite baffle mounting is the reference condition

### Future Investigation

1. **Understand the remaining ~8.5 dB in Hornresp**
   - Check if Hornresp uses different efficiency calculation
   - Verify physical constants (c, ρ₀) in Hornresp
   - Investigate radiation impedance model differences

2. **Mass roll-off parameter**
   - Current: f_mass = 450 Hz (empirical)
   - Should be calculated from driver parameters
   - Literature: Small (1973) mass roll-off formula

---

## References

- Small, R.H. (1972) "Closed-Box Loudspeaker Systems Part I: Analysis", JAES
- Small, R.H. (1973) "Closed-Box Loudspeaker Systems Part II: Synthesis", JAES
- Beranek, L.L. (1954) "Acoustics", McGraw-Hill
- B&C Speakers 8NDL51 Datasheet
- Hornresp User Manual (radiation space parameters)

---

## Test Commands

```bash
# Verify efficiency calculation
PYTHONPATH=src python -c "
from gsd.driver import load_driver
driver = load_driver('BC_8NDL51')
import math
k = (4 * math.pi ** 2) / (343 ** 3)
eta_0 = k * (driver.F_s ** 3 * driver.V_as) / driver.Q_es
print(f'Efficiency: {eta_0:.6f} ({eta_0*100:.3f}%)')
"

# Test radiation space comparison
PYTHONPATH=src python tasks/test_radiation_space_hypothesis.py

# Compare with Hornresp
PYTHONPATH=src python -c "
from gsd.driver import load_driver
from gsd.enclosure.sealed_box import calculate_spl_from_transfer_function
driver = load_driver('BC_8NDL51')
spl = calculate_spl_from_transfer_function(500, driver, 0.03165, f_mass=450)
print(f'GSD SPL at 500 Hz: {spl:.2f} dB (with +13.5 dB offset)')
print(f'GSD SPL at 500 Hz: {spl-13.5:.2f} dB (without offset)')
"
```

---

**Status**: Analysis complete, awaiting implementation of fix and regeneration of Hornresp validation files.

**Date**: 2025-01-29
**Author**: Generated from investigation of sealed_box.py calibration offset issue
