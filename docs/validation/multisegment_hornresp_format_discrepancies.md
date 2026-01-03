# Hornresp Multi-Segment Export Format Analysis

## Critical Discrepancy Found

### ❌ OUR EXPORT (Invalid Format)
```
|HORN PARAMETER VALUES:

S1 = 1.79
S2 = 327.58
L12 = 28.86         ← WRONG: Hornresp doesn't use L12 for multi-segment!
F12 = 984.9457
S2 = 327.68
S3 = 541.78
L23 = 59.84         ← WRONG: Hornresp doesn't use L23!
F23 = 45.9018
```

### ✅ CORRECT FORMAT (User's Manual File)
```
|HORN PARAMETER VALUES:

S1 = 1.64
S2 = 277.68
Exp = 39.00         ← CORRECT: Exp = Length in cm!
F12 = 360.21
S2 = 277.68
S3 = 464.62
Exp = 59.53         ← CORRECT: Exp = Length in cm!
F23 = 23.67
```

## Key Finding

**Hornresp uses `Exp` parameter for LENGTH in multi-segment horns!**

Not `L12`, `L23` - those are for single-segment exponential horns!

For multi-segment horns:
```
Segment 1: S1, S2, Exp, F12
Segment 2: S2, S3, Exp, F23
Segment 3: S3, S4, Exp, F34
Segment 4: S4, S5, Exp, F45
```

Where:
- `Exp` = **Length in cm** (not flare constant!)
- `F12`, `F23`, etc. = Flare frequency in Hz

## All Discrepancies

### 1. Horn Parameter Format (CRITICAL)
| Parameter | Our Export | Correct Format | Issue |
|-----------|------------|----------------|-------|
| Segment 1 length | `L12 = 28.86` | `Exp = 39.00` | Wrong parameter name |
| Segment 2 length | `L23 = 59.84` | `Exp = 59.53` | Wrong parameter name |
| F12 calculation | 984.95 Hz | 360.21 Hz | Wrong formula/interpretation |
| F23 calculation | 45.90 Hz | 23.67 Hz | Wrong formula/interpretation |

### 2. Cir Parameter (Minor)
| File | Value |
|------|-------|
| Our export | 0.42 |
| Manual file | 0.07 |

This is a mouth correction factor - may vary by design.

### 3. Parameter Values (Different optimization runs)
| Parameter | Our Export | Manual File |
|-----------|------------|-------------|
| S1 | 1.79 cm² | 1.64 cm² |
| S2 | 327.58 cm² | 277.68 cm² |
| S3 | 541.78 cm² | 464.62 cm² |
| Vtc | 13.67 cm³ | 13.52 cm³ |
| Atc | 1.79 cm² | 1.64 cm² |

These are different because each optimization run finds different solutions (stochastic algorithm).

## Root Cause

The `export_multisegment_horn_to_hornresp()` function is using the **wrong format**:

```python
# WRONG - We're outputting single-segment format:
horn_section = f"""S1 = {s1:.2f}
S2 = {s2:.2f}
L12 = {l12:.2f}      ← Wrong for multi-segment!
F12 = {f12:.4f}
...
L23 = {l23:.2f}      ← Wrong for multi-segment!
F23 = {f23:.4f}
```

**Should be:**
```python
# CORRECT - Multi-segment format:
horn_section = f"""S1 = {s1:.2f}
S2 = {s2:.2f}
Exp = {length1_cm:.2f}   ← Length in cm!
F12 = {f12:.2f}
S2 = {s2:.2f}
S3 = {s3:.2f}
Exp = {length2_cm:.2f}   ← Length in cm!
F23 = {f23:.2f}
```

## Fix Required

In `src/gsd/hornresp/export.py`, function `export_multisegment_horn_to_hornresp()`:

Replace lines 1098-1115 (horn_section format) with multi-segment format using `Exp` instead of `L12`, `L23`, etc.

## Additional Notes

1. **F12/F23 values**: The manual file has much lower values. This suggests Hornresp may calculate flare frequency differently than our formula: `F = c * m / (2π)`. Need to verify Hornresp's actual formula.

2. **Cir parameter**: Value of 0.07 vs 0.42 - this is mouth correction and may be design-dependent.

3. **Exp parameter name confusion**:
   - For single-segment exponential: `Exp = 50.00` is a flare constant (unitless?)
   - For multi-segment: `Exp = 39.00` is the LENGTH in cm

   Hornresp reuses `Exp` for different purposes in different contexts!

## Files to Reference

- **Correct format**: `/Users/fungj/vscode/gsd/imports/tc2_multiseg.txt`
- **Our export**: `/Users/fungj/vscode/gsd/exports/tc2_optimized_multisegment_horn.txt`

## Next Steps

1. ✅ Document discrepancies (this file)
2. ❌ Fix `export_multisegment_horn_to_hornresp()` to use `Exp` for lengths
3. ❌ Verify F12/F23 calculation formula with Hornresp documentation
4. ❌ Re-test export after fix
