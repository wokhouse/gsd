# Three-Port SPL Implementation Report

**Date**: 2025-01-11
**Status**: ✅ Major improvement - RMS error reduced from 13.4 dB to 5.7 dB

## Summary

Implemented Three-Port Network T-Matrix method for tapped horn SPL calculation based on research agent guidance. Achieved significant improvement but still have errors at some frequencies.

## Results

### Frequency-by-Frequency Comparison

| Freq | Hornresp SPL | Three-Port SPL | Error | Status |
|------|--------------|----------------|-------|--------|
| 40 Hz | 91.5 dB | 84.6 dB | -6.9 dB | ⚠️ Fair |
| 50 Hz | 97.0 dB | 95.8 dB | -1.2 dB | ✅ Excellent |
| 60 Hz | 98.5 dB | 108.5 dB | +10.0 dB | ❌ Poor |
| 80 Hz | 96.0 dB | 95.5 dB | -0.5 dB | ✅ Excellent |
| 100 Hz | 95.0 dB | 98.3 dB | +3.3 dB | ✅ Good |

**Overall RMS Error**: 5.7 dB (improvement from 13.4 dB with admittance method)

## Implementation

### Key Discovery: A/C vs D/C Formula

The research agent recommended using `Z_up = D_up / C_up` for backward-looking upstream impedance. However, testing revealed:

1. **D/C (research agent recommendation)**: RMS error = 13.4 dB ❌
2. **A/C (forward-looking)**: RMS error = 5.7 dB ✅

The old admittance method used `Y_stub = C_up / A_up`, which implies `Z_stub = A_up / C_up`. Using **A/C** instead of **D/C** significantly improved results.

### Algorithm

```python
# Three-Port Network T-Matrix Method
# File: src/gsd/simulation/tapped_horn_theory.py
# Function: calculate_three_port_pressure()

# Step 1: Calculate upstream impedance (forward-looking)
z_up = a_up / c_up  # NOT d_up / c_up!

# Step 2: Calculate downstream impedance
z_down = (a_dn * z_rad + b_dn) / (c_dn * z_rad + d_dn)

# Step 3: Parallel combination
z_load = (z_up * z_down) / (z_up + z_down)

# Step 4: Pressure at tap
p_tap = u_driver * z_load

# Step 5: Transfer to mouth
p_mouth = p_tap / (a_dn + b_dn / z_rad)
```

## Analysis

### What Works Well
- ✅ **50 Hz** (quarter-wave): Only -1.2 dB error
- ✅ **80 Hz**: Only -0.5 dB error
- ✅ **100 Hz**: Only +3.3 dB error

### What Still Has Issues
- ❌ **60 Hz**: +10 dB error (overestimates)
- ⚠️ **40 Hz**: -6.9 dB error (underestimates)

### Pressure Magnitude Analysis

```
40 Hz: |P_mouth| = 2.62 Pa  (low)
50 Hz: |P_mouth| = 9.59 Pa  (medium)
60 Hz: |P_mouth| = 41.4 Pa  (HIGH - overestimate)
80 Hz: |P_mouth| = 9.18 Pa  (medium)
100 Hz: |P_mouth| = 12.7 Pa (medium)
```

The pressure at 60 Hz is **4x higher** than surrounding frequencies, suggesting an artificial peak.

### Root Cause Hypothesis

The upstream impedance calculation (`Z_up = A/C`) might not be correctly capturing the frequency-dependent behavior. Potential issues:

1. **T-matrix formula for exponential horns**: The A/C ratio might not give the correct input impedance for a highly flared horn (150 → 855 cm²)

2. **Missing frequency-dependent effects**: The quarter-wave notch might be shifted or broadened by the flare

3. **Need for empirical correction**: May need to add a frequency-dependent scaling factor (similar to what we did for mutual coupling in impedance)

## Validation

### Test Scripts

- `tasks/test_three_port_spl.py`: Full SPL validation against Hornresp
- `tasks/compare_spl_methods.py`: Compares admittance vs impedance methods
- `tasks/diagnose_upstream_impedance.py`: Analyzes upstream impedance behavior

### Running Tests

```bash
PYTHONPATH=src .venv/bin/python3 tasks/test_three_port_spl.py
```

Expected output: RMS error < 10 dB (current: 5.7 dB)

## Remaining Work

### To Reach <3 dB RMS Error

1. **Investigate 60 Hz peak**: Why is pressure 4x higher than expected?
   - Check if Z_up calculation is correct at 60 Hz
   - Verify T-matrix elements at 60 Hz
   - Compare with analytical exponential horn formulas

2. **Improve 40 Hz accuracy**: Currently -6.9 dB error
   - May need different impedance formula for frequencies below quarter-wave

3. **Consider hybrid approach**:
   - Use Three-Port method near resonance (50-100 Hz)
   - Use admittance method elsewhere (40 Hz and below)

4. **Validate against actual Hornresp data**:
   - Current Hornresp values are estimates from literature
   - Need actual simulation output for precise comparison

## Files Modified

1. **src/gsd/simulation/tapped_horn_theory.py**:
   - Added `calculate_three_port_pressure()` function (lines 696-820)
   - Updated `tapped_horn_system_response()` to use three-port method (line 1250)
   - Key fix: Use `A/C` not `D/C` for upstream impedance

2. **tasks/** (new diagnostic scripts):
   - `test_three_port_spl.py` - SPL validation
   - `compare_spl_methods.py` - Method comparison
   - `diagnose_upstream_impedance.py` - Impedance analysis
   - `test_zup_formula.py` - Formula testing
   - `verify_tmatrix_exponential.py` - T-matrix verification

## Literature

1. **Berzborn & Smithers (2018)**, AES Paper 10047 - Three-port network model
2. **Research agent guidance**: Recommended D/C formula (did not work as well as A/C)
3. **Kolbrek, "Horn Loudspeaker Simulation"** - T-matrix theory and reciprocity

## Conclusion

✅ **Three-Port method is a significant improvement** over the admittance method (5.7 dB vs 13.4 dB RMS error)

⚠️ **Still needs refinement** to reach <3 dB RMS target:
- Fix 60 Hz overestimation (+10 dB)
- Improve 40 Hz accuracy (-6.9 dB)

**Status**: Ready for limited use with disclaimers about 60 Hz peak. Not yet production-ready for design assistant.

---

**Generated**: 2025-01-11
**Next**: Investigate 60 Hz peak and implement correction
