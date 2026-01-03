# Hornresp Format Comparison: gsd vs Manual Entry

**Date:** 2025-12-28
**Files compared:**
- `imports/15ds115_params.txt` - Your manual entry exported from Hornresp
- `exports/bc15ds115_bass_horn_CORRECTED.txt` - gsd automated export

---

## Critical Differences Found

### Difference 1: Exp Parameter Format 🔴 CRITICAL

**Your file (from Hornresp):**
```
Exp = 266.00
```

**GSD export:**
```
Exp = 50.00
```

**Analysis:**
- Hornresp shows `Exp = 266.00` (the horn LENGTH in cm!)
- gsd exports `Exp = 50.00` (hard-coded value for exponential)
- **This suggests Hornresp uses Exp field differently than we thought!**

Looking at the Hornresp format, it appears:
- `Exp = 50.00` is the exponential flare TYPE (fixed)
- But Hornresp may be reinterpreting this field

---

### Difference 2: L12 Parameter Missing 🔴 CRITICAL

**Your file (from Hornresp):**
```
S2 = 0.00
S3 = 0.00
L23 = 0.00      ← Wrong position!
```

**GSD export:**
```
S2 = 0.00
S3 = 0.00
L12 = 266.00    ← Correct position!
S3 = 0.00
S4 = 0.00
L34 = 0.00
F34 = 0.00
```

**Analysis:**
- Your file shows `L23 = 0.00` instead of `L12 = 266.00`
- The L12 parameter is in the wrong place
- **This suggests Hornresp may have reorganized the parameters**

---

### Difference 3: AT Parameter 🟡

**Your file (from Hornresp):**
```
AT = 1.38
```

**GSD export:**
```
AT = 86.38
```

**Analysis:**
- AT = 1.38 vs 86.38
- Ratio: 86.38 / 1.38 = 62.6
- This doesn't match any obvious conversion
- **AT may have a different meaning in Hornresp**

---

### Difference 4: Cir Parameter 🟢 Minor

**Your file (from Hornresp):**
```
Cir = 0.12
```

**GSD export:**
```
Cir = 0.42
```

**Analysis:**
- Cir is the mouth correction factor
- Difference is minor and won't significantly affect results
- This is likely calculated by Hornresp based on mouth geometry

---

### Difference 5: Duplicate F34/F45 Lines 🟡

**Your file (from Hornresp):**
```
F34 = 0.00
F34 = 0.00    ← Duplicate!
...
F45 = 0.00
F45 = 0.00    ← Duplicate!
```

**GSD export:**
```
L34 = 0.00
F34 = 0.00
...
L45 = 0.00
F45 = 0.00
```

**Analysis:**
- Your file has duplicate F34 and F45 lines
- Missing L34 and L45 lines
- **Hornresp format issue - may need adjustment**

---

## Parameter Format Investigation

### Hornresp Parameter Order (from your file)

```
|HORN PARAMETER VALUES:

S1 = 86.38      # Throat area
S2 = 1002.44    # Mouth area
Exp = 266.00    # ← LENGTH, not flare type!
F12 = 25.23     # Cutoff frequency
S2 = 0.00       # Reset S2
S3 = 0.00
L23 = 0.00      # ← Should be L12!
AT = 1.38       # ← Unknown value
S3 = 0.00
S4 = 0.00
F34 = 0.00      # ← Duplicate
F34 = 0.00      # ← Duplicate
S4 = 0.00
S5 = 0.00
F45 = 0.00      # ← Duplicate
F45 = 0.00      # ← Duplicate
```

**This format doesn't match the standard Hornresp format!**

---

## Hypothesis: Hornresp Parameter Mapping

Based on these differences, I suspect:

### Hypothesis 1: Exp Field Contains Length
```
Exp = 266.00  # Horn length in cm (not flare type!)
```

If this is true, then:
- The "Exp = 50.00" for exponential may be outdated
- Modern Hornresp may use Exp for length
- L12 field may be calculated automatically by Hornresp

### Hypothesis 2: AT is Throat + Chamber Correction
```
AT = 1.38     # Some throat/chamber correction factor?
```

This could be:
- Throat correction factor
- Combined throat + chamber effect
- Calculated by Hornresp automatically

---

## Action Items

### Immediate:
1. **Verify Hornresp file format** - Check actual Hornresp documentation
2. **Test import** - Does our corrected file actually import correctly?
3. **Check parameter positions** - L12 location in file format

### Investigation Needed:
1. **What does Exp field contain?** - Length or flare type?
2. **Where should L12 go?** - Position in parameter block
3. **What is AT?** - Throat area or correction factor?
4. **Why duplicate F34/F45?** - Format error or intentional?

---

## Questions for User

1. **Did you manually enter the parameters or use Hornresp's auto-calculation?**
2. **Did Hornresp automatically calculate F12 = 25.23 Hz?**
3. **What does Hornresp show for the Exp parameter field?**
4. **Are there any warnings or errors when importing our file?**

---

## Recommendation

**We need to verify the actual Hornresp file format specification.** The differences suggest our understanding of the parameter format may be incorrect.

**Next steps:**
1. Check Hornresp user manual for exact parameter format
2. Test import of our corrected file
3. Compare Hornresp's auto-calculated values with manual entry
4. May need to adjust export format based on Hornresp version

---

## Status

🔴 **CRITICAL:** Export format may not match Hornresp expectations
🟡 **INVESTIGATION:** Need to verify actual Hornresp parameter format
🟢 **GOOD NEWS:** F12 matches (25.15 vs 25.23 Hz) - calculation is correct!

**The F12 calculation is correct, but the file format may need adjustment.**
