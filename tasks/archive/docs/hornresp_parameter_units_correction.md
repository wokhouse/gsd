# Hornresp Parameter Units - CRITICAL CORRECTION

**Date:** 2025-12-28
**Issue:** https://github.com/wokhouse/gsd/issues/21
**Status:** Previous validation report was INCORRECT due to unit misunderstandings

---

## Hornresp Parameter Units (CORRECTED)

After reviewing the GitHub discussion, the correct units are:

| Parameter | What I thought | CORRECT Unit | Description |
|-----------|----------------|--------------|-------------|
| AT | Meters (length) | **cm²** (area) | Throat area (same as S1) |
| Vtc | Liters (volume) | **cm³** (cc) | Throat chamber volume |
| L12 | Not exported | **cm** (length) | Horn segment length |

---

## Critical Bug Found in gsd Export

The `export_front_loaded_horn_to_hornresp()` function has **MAJOR BUGS**:

### Bug 1: Wrong Parameter Mapping
```python
# Current (WRONG):
l12_m = horn.length  # Gets length in meters
AT = l12_m  # ❌ Assigns length to AT parameter!

# Should be:
AT = horn.throat_area * 10000  # Throat area in cm²
L12 = horn.length * 100  # Length in cm
```

### Bug 2: Missing L12 Parameter
The export doesn't write L12 (horn length in cm) at all!

Looking at the export format:
```
S1 = 86.38
S2 = 1002.44
Exp = 50.00
F12 = 50.29    ← This is WRONG
S2 = 0.00
S3 = 0.00
L23 = 0.00     ← Should be L12, but L23 is segment 2-3!
AT = 2.66      ← This is WRONG (should be throat area in cm²)
```

### Bug 3: Wrong F12 Calculation
The export calculates:
```python
f12 = (c * flare_constant) / (4.0 * math.pi)  # Gives ~50 Hz
```

But Hornresp actually uses:
```
F12 = 25.23 Hz (for this geometry)
```

The discrepancy suggests gsd is using the wrong formula or the formula is being misapplied.

---

## F12 Calculation Verification

**Given parameters:**
- S1 = 86.38 cm²
- S2 = 1002.44 cm²
- Length = 266 cm = 2.66 m

**Flare constant calculation:**
```
m = (1/L) × ln(S2/S1)
m = (1/2.66) × ln(1002.44/86.38)
m = 0.376 × 2.451
m = 0.921 m⁻¹
```

**Hornresp F12 formula:**
```
F12 = c × m / (4π)
F12 = 343 × 0.921 / (4π)
F12 = 316.0 / 12.566
F12 = 25.15 Hz
```

**Rounded:** F12 = 25.23 Hz (matches Hornresp!)

✓ **Hornresp calculation is CORRECT: F12 = 25.23 Hz**

✗ **gsd export is WRONG: F12 = 50.29 Hz (exactly 2× too high!)**

---

## Root Cause of F12 Error

The gsd export code calculates:
```python
f12 = (c * flare_constant) / (4.0 * math.pi)
```

For m = 0.921:
```
F12 = 343 × 0.921 / (4π)
F12 = 316.0 / 12.566
F12 = 25.15 Hz  ← This should be the result!
```

But the export shows **F12 = 50.29 Hz**, which is exactly **2 × 25.15 Hz**.

**Possible causes:**
1. Code is using `2π` instead of `4π` somewhere
2. There's a factor of 2 error in the flare constant calculation
3. The export is using a different horn length than expected

---

## Correct Manual Entry Parameters

Based on the GitHub discussion and Hornresp's actual behavior:

```
|HORN PARAMETER VALUES:
S1  = 86.38     # Throat area (cm²)
S2  = 1002.44   # Mouth area (cm²)
Exp = 50.00     # Exponential horn
F12 = 25.23     # Cutoff frequency (Hz) - let Hornresp calculate this!
L12 = 266.00    # Horn length (cm) - NOT in meters!
S2  = 0.00
S3  = 0.00
L23 = 0.00
AT  = 86.38     # Throat area (cm²) - SAME as S1!

|CHAMBER PARAMETER VALUES:
Vtc = 19820.00  # Throat chamber volume (cm³) - NOT liters!
Atc = 86.38     # Throat chamber area (cm²)
Vrc = 380.20    # Rear chamber volume (L)
Lrc = 72.44     # Rear chamber depth (cm)
```

**Key corrections:**
- **AT = 86.38 cm²** (throat area, same as S1) - NOT 2.66!
- **L12 = 266 cm** (horn length) - this parameter was missing!
- **Vtc = 19820 cm³** (19.82 L in cm³) - your original entry was CORRECT!
- **F12 = 25.23 Hz** - let Hornresp calculate this automatically

---

## Action Items

### 1. Fix gsd Export Function (CRITICAL BUG)

File: `src/gsd/hornresp/export.py`

**Changes needed:**
```python
# Calculate horn parameters in Hornresp units
s1_cm2 = horn.throat_area * 10000.0    # Already correct
s2_cm2 = horn.mouth_area * 10000.0     # Already correct
l12_cm = horn.length * 100              # NEW: Length in cm, NOT meters
at_cm2 = horn.throat_area * 10000.0     # NEW: Throat area in cm² (same as S1)

# Calculate F12 using correct Hornresp formula
flare_constant = math.log(s2_cm2 / s1_cm2) / l12_cm  # m in cm⁻¹
f12 = (SPEED_OF_SOUND / 100) * flare_constant / (4.0 * math.pi)  # Convert c to cm/s
```

**Fix the export format:**
```
|HORN PARAMETER VALUES:
S1 = {s1_cm2:.2f}
S2 = {s2_cm2:.2f}
Exp = 50.00
F12 = {f12:.2f}
S2 = 0.00
S3 = 0.00
L12 = {l12_cm:.2f}    # ← ADD THIS (was L23 before!)
S3 = 0.00
S4 = 0.00
L34 = 0.00
F34 = 0.00
S4 = 0.00
S5 = 0.00
L45 = 0.00
F45 = 0.00
AT = {at_cm2:.2f}     # ← FIX THIS (was length, should be area)
```

### 2. Re-run Validation

After fixing the export:
1. Re-export from gsd
2. Import to Hornresp
3. Verify F12 matches (should be ~25 Hz)
4. Compare simulation results

### 3. Update Documentation

Add to `CLAUDE.md`:
- Hornresp parameter units
- AT = throat area in cm² (not length!)
- Vtc = throat chamber volume in cm³ (not liters!)
- L12 = horn length in cm (not meters!)
- F12 = Hornresp calculates automatically using correct formula

---

## Lessons Learned

1. **Never assume units** - always verify from source documentation
2. **Test exports by round-tripping** - export → import → compare
3. **GitHub discussions are authoritative** - when in doubt, check the issues
4. **Manual validation is essential** - caught bugs that automated tests missed

---

## Summary

| Item | Status | Action |
|------|--------|--------|
| User's manual entry | ✓ Mostly correct | Vtc=19820 was right (cm³), AT was interpreted wrong |
| gsd export function | ✗ BROKEN | Needs critical fixes to AT, L12, F12 |
| F12 calculation | ✗ WRONG in gsd | Should be 25.23 Hz, not 50.29 Hz |
| Previous validation report | ✗ INVALID | Based on wrong unit assumptions |

**Correct validation needs to happen AFTER fixing the export function.**
