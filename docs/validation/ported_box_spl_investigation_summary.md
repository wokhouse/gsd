# Ported Box SPL Transfer Function Investigation Summary

**Date:** 2025-12-29
**Branch:** `fix/ported-box-spl-transfer-function`
**Status:** **INCOMPLETE** - Transfer function equation incorrect, needs correct equation from literature

## Problem Statement

The ported box SPL transfer function in `src/gsd/enclosure/ported_box.py` does **NOT** match Hornresp validation data. The response shape is fundamentally wrong regardless of parameter values.

## Validation Data

### Test Case: BC_8FMB51

**Driver Parameters:**
- Fs = 67.1 Hz
- Qts = 0.275
- Vas = 20.7 L

**Box Parameters:**
- Vb = 49.3 L
- Fb = 60.3 Hz
- Port: 41.3 cm² × 3.8 cm

### Hornresp Results (Normalized to Passband)

| Frequency | SPL (dB) | Behavior |
|-----------|----------|----------|
| 52.5 Hz | **+6.40** | **PEAK** |
| 53 Hz | +6.23 dB | |
| 60 Hz | +2.49 dB | |
| **Difference** | **53 Hz > 60 Hz by +3.75 dB** | **Shows peak, then decreases** |

### GSD Results (Normalized to Passband)

| Frequency | SPL (dB) | Behavior |
|-----------|----------|----------|
| 52.5 Hz | -4.36 dB | |
| 53 Hz | -3.80 dB | |
| 60 Hz | -0.32 dB | |
| **Difference** | **53 Hz < 60 Hz by -3.47 dB** | **Monotonic increase** |

**Conclusion:** The response shapes are **INVERTED** and **completely different**.

## Comprehensive Testing Results

### 1. Q_T Definition (2 values tested)

| Q_T Definition | Peak Location | 53-60 Hz Diff | Result |
|----------------|---------------|---------------|---------|
| Qts = 0.275 | 66.5 Hz | -3.47 dB | ✗ Wrong shape |
| Qts/h = 0.306 | 72.9 Hz | -4.04 dB | ✗ Wrong shape |

### 2. s³ Coefficient Order (2 arrangements tested)

| s³ Term Order | Peak Location | 53-60 Hz Diff | Result |
|---------------|---------------|---------------|---------|
| T_B²T_S/Q_B + T_BT_S²/Q_T | 71.8 Hz | -4.18 dB | ✗ Wrong shape |
| T_B²T_S/Q_T + T_BT_S²/Q_B | 66.5 Hz | -3.52 dB | ✗ Wrong shape |

### 3. Q_L Values (4 settings tested)

| Q_L Value | QA Value | Peak Magnitude | Peak Location | Result |
|-----------|----------|----------------|---------------|---------|
| 7.0 (Hornresp default) | 100.0 | +0.48 dB | 66.5 Hz | ✗ Wrong shape |
| infinity (lossless) | infinity | +7.47 dB | 61.1 Hz | ✗ Wrong shape |
| 100.0 | 100.0 | +3.51 dB | 62.5 Hz | ✗ Wrong shape |
| 1000.0 | 100.0 | +3.79 dB | 62.0 Hz | ✗ Wrong shape |

### 4. All 4 Combinations of Q_T × s³ Order

| Q_T | s³ Order | Peak Location | 53-60 Hz Diff | Result |
|-----|---------|---------------|---------------|---------|
| Qts/h | T_B²T_S/Q_B + T_BT_S²/Q_T | 72.9 Hz | -4.04 dB | ✗ |
| Qts | T_B²T_S/Q_B + T_BT_S²/Q_T | 71.8 Hz | -4.18 dB | ✗ |
| Qts/h | T_B²T_S/Q_T + T_BT_S²/Q_B | 67.5 Hz | -3.41 dB | ✗ |
| Qts | T_B²T_S/Q_T + T_BT_S²/Q_B | 66.5 Hz | -3.52 dB | ✗ |

**NONE of the 4 combinations produce the correct peaked response!**

## Current Transfer Function (Per Small Eq. 20)

```
G(s) = s⁴T_B²T_S² / D(s)

D(s) = s⁴T_B²T_S² + s³(T_B²T_S/Q_T + T_BT_S²/Q_L) +
       s²[(α+1)T_B² + T_BT_S/(Q_L×Q_T) + T_S²] +
       s(T_B/Q_L + T_S/Q_T) + 1
```

This produces:
- Monotonic increase from 53 Hz to 60 Hz (wrong: should decrease)
- Peak at 66-73 Hz (wrong: should be at 52.5 Hz)
- NO +6 dB peak like Hornresp (wrong: should have +6.4 dB peak)

## Root Cause Analysis

### Ruled Out:
- ✗ Q_T definition (both Qts and Qts/h tested)
- ✗ s³ coefficient order (both arrangements tested)
- ✗ Q_L value (tested from 7 to infinity)
- ✗ Parameter values (verified against Hornresp export)
- ✗ Reference level normalization (both normalized correctly)
- ✗ Port contribution (Small's G(s) should already include driver + port)

### Likely Causes:
1. **OCR/translation error in Small's equations**
   - Wrong signs in denominator?
   - Wrong coefficient positions?
   - Using wrong equation entirely?

2. **Wrong equation for SPL**
   - Eq. 20 might be for impedance, not SPL
   - Different equation for "acoustic output" vs "transfer function"
   - Should use Thiele (1971) instead of Small (1973)?

3. **Fundamental form error**
   - Numerator might be wrong (not s⁴T_B²T_S²?)
   - Denominator might have different form
   - Missing critical terms

## Changes Made (Do NOT Fix the Issue)

### File: `src/gsd/enclosure/ported_box.py`

**Change 1 (Line 840-848): Q_T Definition**
```python
# OLD:
Qt = driver.Q_ts / h  # Q_T = Qts / h

# NEW (per research agent recommendation):
Qt = driver.Q_ts  # Q_T = Qts (NOT Qts/h!)
```

**Change 2 (Line 859-880): s³ Coefficient Order**
```python
# OLD:
a3 = (Tb ** 2 * Ts / QB) + (Tb * Ts ** 2 / Qt)

# NEW (per research agent recommendation):
a3 = (Tb ** 2 * Ts / Qt) + (Tb * Ts ** 2 / QB)  # Terms swapped!
```

**Result:** These changes do NOT fix the response shape. The transfer function
still produces monotonic increase (53 Hz < 60 Hz) instead of the characteristic
peaked response (53 Hz > 60 Hz) shown by Hornresp.

## Test Scripts Created

All test scripts in `tasks/` directory:

1. `diagnose_bc8fmb51_spike.py` - Original diagnostic showing the issue
2. `debug_transfer_function.py` - Transfer function coefficient analysis
3. `verify_shape_match.py` - Proper comparison normalized to passband
4. `test_lossless_ql.py` - Testing different Q_L values
5. `test_all_tf_combinations.py` - Testing all Q_T × s³ order combinations
6. `transfer_function_coefs_check.py` - Checking coefficient interpretation
7. `compare_qt_definitions.py` - Comparing Qts vs Qts/h
8. `test_normalized_tf.py` - Testing normalized form of transfer function

## Validation Files

- Hornresp export: `tasks/BC8FMB51_ported_design.txt`
- Hornresp sim data: `imports/bookshelf_sim.txt`

## Research Agent Tasks Created

1. **Initial research:** Asked for Small (1973) Eq. 20 transfer function
   - Agent provided equation and claimed current implementation was correct
   - Agent claimed monotonically increasing response is "correct high-pass behavior"

2. **Follow-up 1:** Pointed out response shapes don't match Hornresp
   - Agent clarified that G(s) is normalized high-pass filter
   - Suggested normalizing both to passband for comparison
   - Claimed shapes should match

3. **Follow-up 2:** Showed definitive proof that shapes DON'T match
   - Provided normalized comparison showing Hornresp has +6.4 dB peak at 52.5 Hz
   - GSD shows monotonic increase with no peak
   - Agent still claimed transfer function is correct

4. **Follow-up 3 (FINAL):** Requested OCR verification from PDF
   - Asked agent to access Small (1973) PDF directly
   - Request screenshots of actual equations
   - Asked for verification that equation produces peaked response
   - Prompt copied to clipboard, awaiting results

## Next Steps

1. **✓ RESEARCH AGENT TASK:** Prompt already copied to clipboard
   - Paste to https://claude.ai/code
   - Agent will verify Small (1973) equations directly from PDF
   - Check for OCR errors in equation transcription
   - Provide correct equation that produces +6 dB peak at ~52 Hz

2. **Alternative approach if research fails:**
   - Check Thiele (1971) for different transfer function form
   - Consider using impedance-based SPL calculation
   - May need to contact Hornresp author for clarification

3. **Documentation:**
   - Keep this investigation summary updated
   - Document correct equation when found
   - Create unit tests to prevent regression

## References

- Small, R.H. (1973). "Vented-Box Loudspeaker Systems Part I", JAES
  - PDF: https://sdlabo.jp/archives/Vented_Box_Loudspeaker%20Systems_Part_1-4.pdf
- Thiele, A.N. (1971). "Loudspeakers in Vented Boxes", JAES
- Hornresp: http://www.hornresp.net/

## Status

**INCOMPLETE** - The transfer function equation from Small (1973) Eq. 20 does not
produce response matching Hornresp. Likely cause is OCR/transcription error in
the equation or using wrong equation entirely.

**Action required:** Get verified correct equation from Small (1973) PDF (with
screenshots to verify no OCR errors) that produces peaked vented box response
matching Hornresp (+6.4 dB peak at 52.5 Hz, then decreases to tuning frequency).
