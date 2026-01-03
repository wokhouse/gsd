# Multi-Segment Horn Export Comparison: GSD vs Hornresp

## Test Design

**2-Segment Horn for TC2 Compression Driver**
- Throat: 1.67 cm²
- Middle: 305.44 cm²
- Mouth: 505.74 cm²
- Length 1: 32.90 cm
- Length 2: 59.87 cm
- V_tc: 12.89 cm³
- V_rc: ~0 (Hornresp shows 0.00)

## Critical Discrepancies Found

### 1. **F12 and F23 Values - WAY OFF!**

| Parameter | GSD Export | Hornresp Output | Difference |
|-----------|----------------|-----------------|------------|
| F12 | 864.38 Hz | 433.41 Hz | **2× error!** |
| F23 | 45.98 Hz | 23.06 Hz | **2× error!** |

**Pattern**: Our values are almost exactly **double** what Hornresp calculates!

864.38 / 433.41 = 1.994 ≈ 2.0
45.98 / 23.06 = 1.994 ≈ 2.0

**Root Cause**: Our flare constant → F conversion formula is wrong!

Current code (export.py):
```python
# Convert dimensionless flare constant m (m^-1) to Hornresp F12 (Hz)
# F(Hz) = c * m / (2π)
f12 = (c * segments[0].flare_constant) / (2.0 * math.pi)
```

**Correct Formula Should Be**:
```python
# F(Hz) = c * m / (4π)  ← Note: 4π, not 2π!
f12 = (c * segments[0].flare_constant) / (4.0 * math.pi)
```

**Why the factor of 2?**
- Hornresp's F12 parameter represents the **cutoff frequency** of the segment
- Cutoff frequency formula: **f_c = c * m / (2π)** for exponential horns
- But Hornresp appears to use: **f_c = c * m / (4π)**

This might be because:
1. Hornresp uses a different definition of flare constant
2. Hornresp's F parameter is 1/2 of the theoretical cutoff
3. There's a factor of 2π vs 4π confusion in the literature

### 2. **Cir Parameter (Mouth Correction)**

| File | Value |
|------|-------|
| GSD export | 0.42 |
| Hornresp output | 0.08 |

This is a mouth correction factor. Hornresp adjusted it from 0.42 to 0.08 when importing. This appears to be an auto-calculated parameter based on mouth size and radiation angle.

**Not a critical issue** - Hornresp can calculate this automatically.

### 3. **V_rc Parameter Display**

Our export script shows:
```
V_rc: 3.66 cm³ (0.0037 L)
```

But Hornresp shows:
```
Vrc = 0.00
```

This is because 0.0037 L rounds to 0.00 with 2 decimal places, which Hornresp treats as "no rear chamber".

**Not an issue** - expected behavior for very small V_rc values.

## All Parameter Comparison

### Horn Parameters (MATCH ✓)

| Parameter | GSD | Hornresp | Status |
|-----------|----------|----------|--------|
| S1 (throat) | 1.67 | 1.67 | ✓ |
| S2 (middle) | 305.44 | 305.44 | ✓ |
| S3 (mouth) | 505.74 | 505.74 | ✓ |
| Exp (length 1) | 32.90 | 32.90 | ✓ |
| Exp (length 2) | 59.87 | 59.87 | ✓ |

### Flare Frequencies (WRONG ✗)

| Parameter | GSD | Hornresp | Error |
|-----------|----------|----------|-------|
| F12 | 864.38 Hz | 433.41 Hz | **2× too high** |
| F23 | 45.98 Hz | 23.06 Hz | **2× too high** |

### Radiation Parameters (OK)

| Parameter | GSD | Hornresp | Status |
|-----------|----------|----------|--------|
| Ang | 2.0 x Pi | 2.0 x Pi | ✓ |
| Eg | 2.83 | 2.83 | ✓ |
| Rg | 0.00 | 0.00 | ✓ |
| Cir | 0.42 | 0.08 | Auto-adjusted |

### Chamber Parameters (MATCH ✓)

| Parameter | GSD | Hornresp | Status |
|-----------|----------|----------|--------|
| Vtc | 12.89 | 12.89 | ✓ |
| Atc | 1.67 | 1.67 | ✓ |
| Vrc | 0.00 | 0.00 | ✓ (rounds to zero) |

## Fix Required

### File: `src/gsd/hornresp/export.py`

**Lines 1071 and 1077**: Change flare constant conversion

```python
# BEFORE (WRONG):
f12 = (c * segments[0].flare_constant) / (2.0 * math.pi)
f23 = (c * segments[1].flare_constant) / (2.0 * math.pi)

# AFTER (CORRECT):
f12 = (c * segments[0].flare_constant) / (4.0 * math.pi)
f23 = (c * segments[1].flare_constant) / (4.0 * math.pi)
```

Also update lines 1083 and 1089 (F34, F45) if those segments exist.

## Verification

After fix, re-export and compare:
- F12 should be ~433 Hz (not 864 Hz)
- F23 should be ~23 Hz (not 46 Hz)

**Expected Result**: Exact match with Hornresp's F12 and F23 values.

## Literature Reference

The factor of 2 discrepancy needs investigation:

**Possibilities:**
1. Olson (1947) uses **f_c = c·m/(2π)** for exponential horn cutoff
2. Hornresp might use **F = f_c / 2** for the F12/F23 parameters
3. Or Hornresp's flare constant definition differs from Olson's by factor of 2

**Action Required**: Check Hornresp documentation for F12 parameter definition.

## Summary

✅ **Horn geometry**: Perfect match (S1, S2, S3, Exp values)
✅ **Chamber parameters**: Perfect match (Vtc, Atc, Vrc)
✅ **Format**: Valid Hornresp multi-segment format

✗ **F12/F23 values**: Wrong by factor of 2 - **CRITICAL FIX NEEDED**
- Export is using 2π in denominator
- Should use 4π in denominator
- Or divide final result by 2

**Impact**: F12/F23 values are wrong, but Hornresp appears to recalculate them internally based on the segment geometry, so the import still works. However, for accuracy, we should fix this.
