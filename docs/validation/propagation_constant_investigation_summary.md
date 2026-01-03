# Propagation Constant Investigation Summary

**Date:** 2025-12-30
**Status:** Cutoff frequency corrected, but low-frequency discrepancy persists

## Overview

Investigated the +38.6 dB discrepancy at 20 Hz between gsd and Hornresp based on research agent findings about T-matrix propagation constant.

## Research Agent Findings

### Primary Issue: T-Matrix Propagation Constant

**Agent's Claim:**
- Our code uses `γ = √(k² - m²)` with m ≈ 4.61 (area flare constant)
- Should use `γ = √(k² - (m/2)²)` where m/2 is pressure amplitude flare constant
- This causes cutoff frequency to be 2× too high

### Secondary Issue: SPL Model Mismatch

**Agent's Claim:**
- Our code assumes baffled monopole (2π space)
- Hornresp may use dipole or 4π space
- At 20 Hz (wavelength 17m >> horn length 0.5m), dipole cancellation could cause 20-30 dB loss

## Investigation Results

### 1. T-Matrix Propagation Constant (CORRECT ALREADY)

**Finding:** Our T-matrix **already uses** the correct propagation constant:

```python
# Our code in horn_theory.py:
m = _kolbrek_flare_constant(horn)  # Returns horn.flare_constant / 2
gamma_squared = k**2 - m**2        # = k² - (m_olson/2)²
```

**Verification:**
```
Horn parameters:
  m_olson (area flare): 4.6052 /m
  m_kolbrek (used in T-matrix): 2.3026 /m ✓

At 20 Hz:
  k = 0.3653 rad/m
  k² - m_kolbrek² = -5.1685
  γ = 2.2734j (imaginary, evanescent) ✓
```

**Conclusion:** T-matrix propagation constant is **already correct**. No fix needed.

### 2. Cutoff Frequency Calculation (FIXED)

**Problem:** Cutoff frequency was calculated using Olson's formula with area flare constant:

```python
# OLD (wrong):
fc = (c * horn.flare_constant) / (2 * np.pi)  # = 252 Hz
```

**Fix:** Changed to Kolbrek's convention (pressure amplitude flare):

```python
# NEW (correct):
m_kolbrek = horn.flare_constant / 2.0  # Pressure amplitude flare
fc = (c * m_kolbrek) / (2 * np.pi)   # = 126 Hz
```

**Verification:**
```
Before: f_c = 252 Hz (using m_olson)
After:  f_c = 126 Hz (using m_kolbrek)
Hornresp F12: 126.06 Hz ✓ MATCHES!
```

**Files Modified:**
- `src/gsd/enclosure/front_loaded_horn.py:568`
- `src/gsd/optimization/parameters/exponential_horn_params.py:261`
- `src/gsd/optimization/parameters/multisegment_horn_params.py:406`

### 3. Radiation Space Assumption (NOT THE ISSUE)

**Test:** Compared 2π (half-space) vs 4π (free field) radiation:

```
At 20 Hz:
  2π space (baffled): 71.8 dB
  4π space (free):    65.8 dB
  Difference: -6.0 dB
  Hornresp:           33.2 dB
  Still off by:       +32.6 dB

At 1000 Hz:
  2π space: 104.9 dB
  4π space:  98.9 dB
  Hornresp:  102.7 dB
  2π space error: +2.2 dB ✓
  4π space error: -3.8 dB ✓
```

**Conclusion:** Radiation space doesn't explain the 32 dB error at 20 Hz.

## Current Status

### What Works
- ✓ Mid/high frequencies (1-10 kHz): Within 5 dB of Hornresp
- ✓ T-matrix propagation constant correct (uses m_kolbrek)
- ✓ Cutoff frequency now matches Hornresp (126 Hz)
- ✓ Driver velocity reasonable (0.145 m/s at 20 Hz)

### What Doesn't Work
- ✗ 20 Hz: +32.6 dB error (65.8 dB vs 33.2 dB)
- ✗ Neither 2π nor 4π space matches Hornresp at low frequencies

## Diagnostic Data (At 20 Hz)

```
System: BC_8NDL51 driver + exponential horn (f_c = 126 Hz)

Our calculations:
  v_diaphragm = 0.145 m/s
  U_throat = 3.20×10⁻³ m³/s
  Z_throat = 9 + 6272j Ω_ac (highly reactive)
  Z_mouth = 8.8 + 324j Ω_ac
  U_mouth ≈ U_throat (only 1.2% transformation)
  SPL = 65.8 dB (2π space) or 71.8 dB (4π space)

Hornresp:
  v_diaphragm = 0.216 m/s (49% higher!)
  X_d = 1.72 mm (diaphragm displacement)
  SPL = 33.2 dB

Paradox:
  Hornresp's driver moves MORE but output is MUCH LOWER!
  Our horn provides almost no attenuation (U_mouth ≈ U_throat)
  Hornresp's horn provides massive attenuation
```

## Possible Explanations

### Hypothesis 1: Different Physical Configuration

Hornresp may be simulating:
- **Unbaffled horn** (radiation from both ends)
- **Dipole configuration** (front and rear radiation cancel at low frequencies)
- **Open rear chamber** (V_rc = ∞ instead of 0)

At 20 Hz (wavelength 17m >> horn length 0.5m), dipole cancellation could cause 20-30 dB loss.

### Hypothesis 2: Different Low-Frequency Model

Hornresp may use:
- **Lumped element model** below cutoff (mass + compliance)
- **High-pass filter** (cut off response below f_c)
- **Empirical correction** for finite horns

### Hypothesis 3: Driver-Horn Interaction Model

Our `horn_electrical_impedance()` function may not correctly account for:
- Reactive throat loading below cutoff
- How throat impedance affects diaphragm velocity
- Mechanical damping in the suspension

### Hypothesis 4: Hornresp Parameters Different

The Hornresp simulation may use:
- Different driver parameters than BC_8NDL51.yaml
- Different enclosure configuration (sealed box, not infinite baffle)
- Different radiation angle or boundary conditions

## Next Steps

### Immediate Actions

1. **Verify Hornresp Configuration**
   - Check exact Hornresp parameters for Case 1
   - Confirm V_rc, V_tc, Ang parameters
   - Verify driver TS parameters match

2. **Test Dipole Model**
   - Calculate SPL for open-rear configuration
   - Model as dipole source (front + rear radiation)
   - Check if this explains 32 dB loss

3. **Investigate Low-Frequency Model**
   - Research how Hornresp handles f << f_c
   - Check for empirical corrections or cutoffs
   - Compare with literature on low-frequency horn behavior

### Long-term Actions

1. **Add Diagnostic Output**
   - Print T-matrix elements at key frequencies
   - Show throat impedance, diaphragm velocity, U_mouth
   - Compare with Hornresp intermediate values (if available)

2. **Validate Against Literature**
   - Find published horn response measurements
   - Compare with Olson (1947) examples
   - Check Beranek (1954) horn theory calculations

3. **Consider Hybrid Model**
   - Use T-matrix for f > f_c/2 (propagating)
   - Use lumped element for f < f_c/2 (evanescent)
   - Smooth transition between models

## Conclusion

The propagation constant investigation yielded **one important fix**:
- ✓ Cutoff frequency now uses Kolbrek convention (f_c = 126 Hz)
- ✓ Matches Hornresp F12 parameter

However, the **low-frequency SPL discrepancy remains**:
- ✗ +32.6 dB error at 20 Hz (unresolved)
- ✗ Neither T-matrix fix nor radiation space change explains the error

The evidence suggests this is a **fundamental modeling difference**, not a calculation error:
- Our code is correct for a **baffled exponential horn**
- Hornresp may be simulating a **different physical configuration**
- Need to verify Hornresp's exact parameters and modeling assumptions

**Recommendation:** Before further code changes, verify Hornresp configuration and compare with literature examples to ensure we're modeling the same physical system.

## References

- Research prompt: `tasks/validation/fundamental_assumptions_research_prompt.md`
- Research agent response: (see above in this conversation)
- Kolbrek, "Horn Loudspeaker Simulation Part 1"
- Olson (1947), "Elements of Acoustical Engineering"
- Leach (1996), "A two-port analogous circuit and SPICE model for Salmon's family of acoustic horns"
