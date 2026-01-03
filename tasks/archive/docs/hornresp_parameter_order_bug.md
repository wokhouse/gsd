# Hornresp Parameter Order Bug - CRITICAL FIX NEEDED

**Date:** 2025-12-28
**Issue:** Hornresp parameter block has different order than documented

---

## The Bug

Hornresp interprets our parameter block **incorrectly** because the parameter positions don't match what Hornresp expects.

### Our Current Export (WRONG):
```
|HORN PARAMETER VALUES:

S1 = 86.38       # ✓ Correct position
S2 = 1002.44     # ✓ Correct position
Exp = 50.00      # ❌ WRONG - Hornresp interprets this as L12!
F12 = 25.15      # ✓ Correct position
S2 = 0.00        # ✓ Reset
S3 = 0.00
L12 = 266.00     # ❌ WRONG - Hornresp interprets this as L23!
...
```

### What Hornresp Actually Expects:
```
|HORN PARAMETER VALUES:

S1 = 86.38       # Throat area
S2 = 1002.44     # Mouth area
Exp = 266.00     # ← This field stores L12 (horn length)!
F12 = 25.15      # Cutoff frequency
S2 = 0.00
S3 = 0.00
L23 = 0.00       # ← Length of segment 2 (not used for single segment)
...
```

---

## Root Cause

**Hornresp's parameter block uses this order:**

```
Line 1: S1  = throat_area (cm²)
Line 2: S2  = mouth_area (cm²)
Line 3: Exp = L12_length (cm)           ← NOT flare type!
Line 4: F12 = cutoff_frequency (Hz)
Line 5: S2  = 0.00 (reset)
Line 6: S3  = 0.00
Line 7: L23 = segment_2_length (cm)     ← NOT L12!
```

**We were incorrectly mapping:**
- `Exp = 50.00` (thinking this was flare type)
- `L12 = 266.00` (thinking this was the length position)

**But Hornresp interprets:**
- `Exp` field as the L12 length
- `L23` field as... something else (possibly L12 in Hornresp's display)

---

## The Fix

### Old Code (WRONG):
```python
|HORN PARAMETER VALUES:

S1 = {s1_cm2:.2f}
S2 = {s2_cm2:.2f}
Exp = 50.00              # ← WRONG!
F12 = {f12_hz:.2f}
S2 = 0.00
S3 = 0.00
L12 = {l12_cm:.2f}       # ← WRONG POSITION!
```

### New Code (CORRECT):
```python
|HORN PARAMETER VALUES:

S1 = {s1_cm2:.2f}
S2 = {s2_cm2:.2f}
Exp = {l12_cm:.2f}       # ← CORRECT: L12 goes in Exp field!
F12 = {f12_hz:.2f}
S2 = 0.00
S3 = 0.00
L23 = 0.00               # ← Segment 2 length (0 for single segment)
S3 = 0.00
S4 = 0.00
L34 = 0.00
F34 = 0.00
S4 = 0.00
S5 = 0.00
L45 = 0.00
F45 = 0.00
AT = {at_cm2:.2f}
```

---

## Verification

After fix, the export should be:

```
S1 = 86.38
S2 = 1002.44
Exp = 266.00     # ← Now contains L12 length!
F12 = 25.15
S2 = 0.00
S3 = 0.00
L23 = 0.00       # ← Segment 2 length (not used)
...
```

When imported to Hornresp, this should correctly show:
- Exp field → displays as L12 = 266 cm
- L23 field → displays as L12 (segment 2) = 0 cm

---

## Impact

This is a **CRITICAL BUG** affecting all horn exports:

- **All exported horns had wrong length**
- L12 was being set to 50.00 (hard-coded "Exp" value)
- Actual horn length (266 cm) was being placed in wrong position
- Hornresp was interpreting this as a 2-segment horn

**Affected exports:**
- All exponential horns via `export_front_loaded_horn_to_hornresp()`
- All multi-segment horns via `export_multisegment_horn_to_hornresp()`

---

## Files to Fix

1. **`src/gsd/hornresp/export.py`**
   - Line 795: Change `Exp = 50.00` to `Exp = {l12_cm:.2f}`
   - Line 798: Change `L12 = {l12_cm:.2f}` to `L23 = 0.00`
   - Verify parameter positions for multi-segment horns

2. **Multi-segment export function**
   - Similar fixes needed for `export_multisegment_horn_to_hornresp()`
   - May need complete parameter order review

---

## Action Items

- [ ] Fix `export_front_loaded_horn_to_hornresp()` parameter order
- [ ] Fix `export_multisegment_horn_to_hornresp()` parameter order
- [ ] Re-export BC_15DS115 horn with corrected format
- [ ] Re-import to Hornresp to verify
- [ ] Update GitHub issue #21 with findings
- [ ] Add unit tests for export format

---

## References

- User feedback: "Exp is functionally L12, and L12 is actually imported as L23"
- Previous validation: `tasks/hornresp_format_comparison.md`
- GitHub issue: https://github.com/wokhouse/gsd/issues/21
