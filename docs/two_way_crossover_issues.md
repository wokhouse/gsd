# Two-Way Crossover Design: Issues and Solutions

**Date:** 2026-01-13
**Session:** DH450 + 10MBX64 2-Way Design
**Status:** Resolved

## Overview

This document captures the issues encountered during the design and validation of a 2-way loudspeaker system using a BC DH450 compression driver on a horn-loaded enclosure and a BC 10MBX64 mid-bass driver in a ported enclosure.

## Critical Issues Found

### Issue 1: Incorrect Filter Application Domain (CRITICAL)

**Severity:** Critical - Made system response completely wrong

**Symptom:**
- Combined response showed ~20 dB dip at crossover frequency
- Filtered outputs were way too low (~66 dB instead of ~90 dB)
- LR4 crossover appeared to fail

**Root Cause:**
Filters were being applied in the **dB domain** instead of the **linear power domain**.

```python
# WRONG - multiplying dB by linear magnitude
hf_filtered = spl_hf * hp_filter  # spl_hf is in dB!

# CORRECT - work in linear domain
hf_linear = 10**(spl_hf/10)
hf_filtered_linear = hf_linear * hp_filter**2
hf_filtered = 10 * np.log10(hf_filtered_linear)
```

**Why This Matters:**
- dB is a logarithmic scale (10*log10(power))
- Filter magnitudes are linear ratios (0 to 1)
- Multiplying dB × linear is mathematically meaningless
- Must convert to linear, apply filter, convert back

**Impact:**
- LR4 filter with magnitude 0.5 should give -6 dB
- Wrong calculation gave -24 dB (0.004 in linear!)
- Combined response was completely invalid

**Resolution:**
- Convert driver responses from dB to linear power
- Apply filters in linear domain
- Convert back to dB for plotting
- See `tasks/25c_corrected_crossover.py` line 92-102

**Lessons Learned:**
1. ALWAYS work in linear domain when applying filters to dB data
2. Verify filter outputs at crossover (should be -6 dB from passband for LR4)
3. Test with known values before trusting complex simulations

---

### Issue 2: Incorrect HF Padding Calibration

**Severity:** High - Caused 3.5 dB error across HF passband

**Symptom:**
- HF response was 6-7 dB below LF passband maximum
- Entire HF region outside ±3 dB tolerance band
- Passband variation was 6.5 dB instead of 3.0 dB

**Root Cause:**
HF padding was calculated to match LF level **at crossover frequency**, not LF **passband maximum**.

```python
# WRONG - match at crossover
xo_range = (lf_sim.freq >= 1339*0.9) & (lf_sim.freq <= 1339*1.1)
spl_lf_xo = np.mean(lf_sim.spl_db[xo_range])  # 93 dB at 1339 Hz
padding = spl_hf_xo - spl_lf_xo  # 110 - 93 = 17 dB

# CORRECT - match to passband maximum
passband_mask = (lf_sim.freq >= 100) & (lf_sim.freq <= 10000)
lf_max_idx = np.argmax(lf_sim.spl_db[passband_mask])
spl_lf_max = lf_sim.spl_db[passband_mask][lf_max_idx]  # 96.5 dB @ 503 Hz
padding = spl_hf_pb - spl_lf_max  # 110 - 96.5 = 13.5 dB
```

**Why This Matters:**
- LF driver at crossover (1339 Hz) is already -3.5 dB below its maximum
- HF driver at crossover should also be at its maximum sensitivity
- Matching to crossover level penalizes HF driver across its entire passband

**Impact:**
- System sensitivity: 94.9 dB → 95.2 dB (0.3 dB improvement)
- Passband variation: 6.5 dB → 3.0 dB (major improvement!)
- Usable bandwidth: 61-1224 Hz → 61-10017 Hz (huge improvement!)
- HF region now within ±3 dB tolerance

**Resolution:**
- Calculate LF passband maximum (100 Hz - 10 kHz)
- Pad HF driver to match LF maximum, not crossover level
- See `tasks/25e_analyze_padding.py` for analysis

**Lessons Learned:**
1. Level matching should use **passband maximum**, not crossover level
2. LF drivers often peak below crossover frequency
3. Verify HF passband is within ±3 dB of system maximum
4. Always check both crossover region AND passband regions

---

### Issue 3: Hornresp Multi-Segment Horn Format Quirk

**Severity:** Medium - Documentation issue, caused confusion

**Symptom:**
- Initial confusion about Hornresp parameter format
- L12/L23 labels don't exist in Hornresp format

**Root Cause:**
Hornresp uses **position-based format** with **segment type labels**, not dimension labels.

**Correct Format:**
```
S1 = 3.56        (throat area in cm²)
S2 = 101.50      (middle/junction area in cm²)
Exp = 15.00      ← "Exponential segment, 15.00 cm long"
F12 = 611.42     (flare frequency for segment 1)

S2 = 101.50      (middle area repeated)
S3 = 401.10      (mouth area in cm²)
Exp = 15.00      ← "Exponential segment, 15.00 cm long"
F23 = 250.78     (flare frequency for segment 2)
```

**All Segment Type Labels:**
- `Exp = <length>` → Exponential segment
- `Con = <length>` → Conical segment
- `Trx = <length>` → Tractrix segment
- `Obi = <length>` → Oblate spheroidal segment
- `Hyp = <length>` → Hyperbolic (catenoidal) segment

**Key Points:**
- LABEL indicates profile type (Exp/Con/etc.)
- VALUE following label is segment length in cm
- Do NOT use `L12 =` or `L23 =` - use profile type labels
- Format is position-based: 4 lines per segment

**Resolution:**
- Documented in `CLAUDE.md` section 4
- All future exports will use correct format

**Lessons Learned:**
1. Hornresp format is quirky and position-based
2. Read documentation carefully before export
3. Validate format with actual Hornresp imports

---

### Issue 4: Compression Driver Hornresp Limitations

**Severity:** Low - Known limitation, documented

**Symptom:**
- Hornresp shows 2-3 dB ripple artifacts for compression driver
- GSD calculation shows smooth response

**Root Cause:**
Hornresp doesn't understand compression drivers with phase plugs.

**The Problem:**
- Hornresp models driver diaphragm (Sd) directly coupled to horn throat (S1)
- For DH450: Sd=140 cm², S1=3.56 cm² → 40:1 impedance mismatch
- In reality, phase plug provides smooth impedance transformation
- Hornresp sees reflections that don't exist

**Validation Finding:**
- GSD datasheet model: smooth response, < 1 dB mean error in crossover band
- Hornresp simulation: ripple artifacts from incorrect physics
- Datasheet model is **more accurate** for compression drivers

**Resolution:**
- Use datasheet sensitivity model for compression drivers
- Don't rely on Hornresp for HF driver response
- Documented in `docs/validation/compression_driver_validation_findings.md`

**Lessons Learned:**
1. Hornresp can't model phase plugs
2. Datasheet sensitivity models are valid for compression drivers
3. Validate LF section with Hornresp, HF section with datasheet

---

### Issue 5: SPL Validation Range Too Restrictive

**Severity:** Low - Validation code fix

**Symptom:**
- Horn response validation failed with "SPL out of range"
- Horns below cutoff have extreme attenuation (< -40 dB)

**Root Cause:**
Validation range was [0, 150] dB, too restrictive for horns.

```python
# WRONG
if np.any(spl_db < 0) or np.any(spl_db > 150):
    raise ValueError("SPL out of range")

# CORRECT
if np.any(spl_db < -100) or np.any(spl_db > 150):
    raise ValueError("SPL out of range")
```

**Resolution:**
- Updated validation range to [-100, 150] dB
- See `src/gsd/hornresp/results_parser.py`

**Lessons Learned:**
1. Horns have extreme attenuation below cutoff
2. Validation ranges must accommodate physics
3. Test with real data before setting limits

---

## Updated Crossover Design Procedure

Based on these issues, the correct procedure is:

### Step 1: Calculate Driver Responses
```python
# LF: Use Hornresp simulation data
lf_sim = load_hornresp_sim_file("imports/ported_sim.txt")
spl_lf = lf_sim.spl_db

# HF: Use datasheet model (validated)
spl_hf = calculate_horn_response(freq, fc=607, sensitivity=110.0)
```

### Step 2: Calibrate HF Padding (CRITICAL)
```python
# Find LF passband MAXIMUM (not crossover level)
passband_mask = (freq >= 100) & (freq <= 10000)
lf_max_idx = np.argmax(spl_lf[passband_mask])
spl_lf_max = spl_lf[passband_mask][lf_max_idx]

# Pad HF to match LF maximum
spl_hf_pb = calculate_horn_response([1000], fc=607, sensitivity=110.0)[0]
padding_db = spl_hf_pb - spl_lf_max

# Apply padding
spl_hf_padded = calculate_horn_response(freq, fc=607, sensitivity=110.0,
                                        padding_db=padding_db)
```

### Step 3: Apply Crossover Filters (CRITICAL)
```python
# Design LR4 filters
hp_filter, lp_filter = design_lr4_crossover(freq, crossover_freq)

# Apply in LINEAR domain (not dB!)
hf_linear = 10**(spl_hf_padded/10)
lf_linear = 10**(spl_lf/10)

# Apply filters (squared for power)
hf_filtered_linear = hf_linear * hp_filter**2
lf_filtered_linear = lf_linear * lp_filter**2

# Combine (power sum)
combined_linear = hf_filtered_linear + lf_filtered_linear

# Convert back to dB
hf_filtered = 10 * np.log10(hf_filtered_linear)
lf_filtered = 10 * np.log10(lf_filtered_linear)
combined = 10 * np.log10(combined_linear)
```

### Step 4: Verify Results
```python
# At crossover, filtered outputs should be -6 dB from passband
idx_xo = np.argmin(np.abs(freq - crossover_freq))
print(f"HF filtered @ crossover: {hf_filtered[idx_xo]:.1f} dB")
print(f"LF filtered @ crossover: {lf_filtered[idx_xo]:.1f} dB")
print(f"Combined @ crossover: {combined[idx_xo]:.1f} dB")

# Check passband flatness
passband_mask = (freq >= 100) & (freq <= 10000)
variation = np.max(combined[passband_mask]) - np.min(combined[passband_mask])
print(f"Passband variation: {variation:.1f} dB")

# Should be < 4 dB for good design
```

---

## Final Validated Design (DH450 + 10MBX64)

### System Specifications

**Drivers:**
- LF: BC 10MBX64 (ported box, 31.1L, Fb=62.6Hz)
- HF: BC DH450 (2-segment horn, Fc=607Hz)

**Crossover:**
- Type: Linkwitz-Riley 4th order
- Frequency: 1339 Hz
- HF Padding: **-13.47 dB** (matched to LF passband max of 96.53 dB)

**Performance:**
- System sensitivity: 95.2 dB @ 1 kHz
- Passband variation: **3.0 dB** (100 Hz - 10 kHz) ✓ Excellent
- F3 Low: 61 Hz
- F3 High: 10017 Hz
- Usable bandwidth: 61 - 10017 Hz (within ±3 dB)

### Files Generated

**Design Scripts:**
- `tasks/25d_system_response.py` - Final system response plot
- `tasks/25e_analyze_padding.py` - Padding calibration analysis
- `tasks/25c_corrected_crossover.py` - Corrected crossover with linear filtering

**Validation Scripts:**
- `tasks/23_validate_multisegment_horn.py` - Horn validation
- `tasks/24_validate_10mbx64_ported.py` - Ported box validation

**Reference Data:**
- `imports/dh450_sim.txt` - Hornresp simulation for 2-segment horn
- `imports/ported_sim.txt` - Hornresp simulation for ported box

---

## Lessons Learned

### For Future 2-Way Designs

1. **Always verify filter outputs** - Check that LR4 gives -6 dB at crossover
2. **Work in linear domain** - Never multiply dB by linear magnitudes
3. **Match to passband maximum** - Not crossover level
4. **Validate both sections** - LF with Hornresp, HF with datasheet
5. **Check entire passband** - Not just crossover region
6. **Use F3/F10 markers** - Shows actual usable bandwidth
7. **Include ±3 dB tolerance** - Visual check for flatness

### Red Flags to Watch For

- ❌ Filtered outputs way below expected (-24 dB instead of -6 dB)
- ❌ HF passband > 3 dB below LF maximum
- ❌ Crossover dip > 3 dB
- ❌ Passband variation > 6 dB
- ❌ Massive spikes or dips in response

### Validation Checklist

- [ ] Filters give -6 dB at crossover (verify!)
- [ ] HF within ±3 dB of LF passband maximum
- [ ] Combined response at crossover = passband max
- [ ] Passband variation < 4 dB
- [ ] F3 points make sense for design
- [ ] No massive dips or spikes

---

## References

**Modified Files:**
- `src/gsd/hornresp/results_parser.py` - Updated SPL validation range
- `CLAUDE.md` - Added Hornresp format documentation

**New Documentation:**
- `docs/validation/compression_driver_validation_findings.md` - HF driver validation

**Literature:**
- Linkwitz-Riley crossover theory
- Hornresp user manual
- Compression driver datasheets

---

**Document Version:** 1.0
**Last Updated:** 2026-01-13
**Status:** Resolved ✅
