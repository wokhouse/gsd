# Tapped Horn Lossy Propagation Implementation Status

**Date**: 2025-01-11
**Status**: LOSSY PROPAGATION IMPLEMENTED - Results degraded, need to fix

## Summary

Implemented viscothermal losses in the T-matrix calculation based on research findings. While the implementation is mathematically correct, the results have **degraded** - impedance is slightly better at 50 Hz but SPL is completely wrong (rolling off at high frequency).

## What Was Implemented

### 1. Lossy Propagation Constant Function

**File**: `src/gsd/simulation/horn_theory.py`
**Function**: `calculate_lossy_propagation_constant()` (line 175)

Implements Keefe (1984) / Mapes-Riordan (1993) model:
```python
# Complex propagation constant Γ = α + jβ
alpha = (1/(r*c)) * sqrt(μ*ω/(2*ρ)) * (1 + (γ-1)/sqrt(Pr))
Gamma = alpha + 1j * k0
```

**Loss magnitude at 50 Hz**:
- α = 0.0018 Np/m (very small)
- αL = 0.0032 Np over 1.8 m (0.03 dB)

### 2. Updated T-Matrix Calculation

**File**: `src/gsd/simulation/horn_theory.py`
**Function**: `exponential_horn_tmatrix()` (line 268)

Changed from:
```python
k = 2 * np.pi * frequencies / medium.c  # Lossless
gamma = sqrt(k**2 - m**2)
```

To:
```python
Gamma, k0 = calculate_lossy_propagation_constant(frequencies, horn, medium)
gamma = sqrt(Gamma**2 - m**2)  # Complex
```

## Results Comparison

### Before Losses (Lossless)

| Freq | gsd SPL | HR SPL | SPL Err | gsd Ze | HR Ze | Ze Err |
|------|---------|--------|---------|--------|-------|--------|
| 40   | 70.83   | 106.53 | -35.70  | 4.33   | 6.92  | -2.59  |
| 50   | 89.03   | 97.05  | -8.02   | 6.14   | 22.49 | -16.35 |
| 60   | 97.73   | 97.67  | +0.06   | 5.52   | 11.24 | -5.72  |
| 80   | 92.94   | 69.54  | +23.40  | 3.78   | 7.70  | -3.92  |
| 100  | 87.73   | 100.16 | -12.43  | 5.03   | 5.94  | -0.91  |

**SPL RMS error**: ~13 dB
**Ze RMS error**: 9.45 Ω
**Correlation**: 0.973

### After Losses (Lossy)

| Freq | gsd SPL | HR SPL | SPL Err | gsd Ze | HR Ze | Ze Err |
|------|---------|--------|---------|--------|-------|--------|
| 40   | 69.71   | 106.53 | -36.82  | 9.32   | 6.92  | +2.40  |
| 50   | 68.64   | 97.05  | -28.41  | 8.72   | 22.49 | -13.77 |
| 60   | 67.20   | 97.67  | -30.47  | 8.29   | 11.24 | -2.95  |
| 80   | 63.61   | 69.54  | -5.92   | 7.74   | 7.70  | +0.04  |
| 100  | 59.44   | 100.16 | -40.72  | 7.38   | 5.94  | +1.44  |

**SPL RMS error**: ~30 dB (WORSE)
**Ze**: Slightly better at 50 Hz (8.72 vs 6.14 Ω), 80 Hz is good (7.74 vs 7.70 Ω)
**Problem**: SPL rolling off dramatically with frequency

## Problem Analysis

### Issue 1: Complex Gamma Causes Exponential Growth

When we add losses, Gamma becomes complex:
```
Gamma = 0.0018 + 0.9159j  (at 50 Hz)
gamma = sqrt(Gamma^2 - m^2) = 0.0016 + 1.0357j  (complex!)
```

Even though we're **above cutoff** (k > m), gamma is complex because Gamma^2 - m^2 is complex.

This causes:
```
sin(γL) where γL is complex → behaves like sinh (exponential growth)
cos(γL) where γL is complex → behaves like cosh (exponential growth)
```

**Result**: T-matrix elements grow exponentially with frequency, causing SPL rolloff.

### Issue 2: Quarter-Wave Impedance Not Going to Zero

Research said Z_up should → 0 at quarter-wave, but we're still getting high impedance:

| Formula | Z_up at 50 Hz |
|---------|---------------|
| A/C     | 1.78e+04      |
| B/D     | 1.57e+04      |
| **D/B** | **6.35e-05**  ← Close to zero! |
| **C/A** | **5.63e-05**  ← Close to zero! |

D/B and C/A give near-zero impedance, which matches expectations for quarter-wave resonance.

But we're using A/C, which gives high impedance. **This suggests we might be using the wrong impedance formula.**

## Root Cause Hypothesis

### Hypothesis 1: Wrong Impedance Formula

We're using Z_up = A/C, but maybe for our T-matrix convention we should use a different formula. D/B and C/A give near-zero impedance, which matches the quarter-wave resonance physics.

**Test**: Try using Z_up = D/B or Z_up = C/A instead of A/C.

### Hypothesis 2: Losses Too Aggressive

Even though α is small (0.0018 Np/m), the fact that gamma becomes complex (instead of staying real when above cutoff) causes sin/cos to become sinh/cosh, which grows exponentially.

**Test**: Reduce losses or find a different way to add losses that keeps gamma real when above cutoff.

### Hypothesis 3: Cutoff Frequency Confusion

With Kolbrek's convention (m_kolbrek = m_olson/2), the cutoff frequency is 26.39 Hz, not 52.78 Hz. So at 50 Hz we're above cutoff, not below.

**Test**: Verify we're using the correct flare constant convention throughout.

## Next Steps

1. **Revert to lossless for now** - The lossy implementation is making things worse
2. **Fix the impedance formula** - Try using D/B or C/A instead of A/C
3. **Investigate T-matrix convention** - Verify direction and impedance formulas
4. **Re-add losses later** - Once the basic model is working

## Files Modified

- `src/gsd/simulation/horn_theory.py`:
  - Added `calculate_lossy_propagation_constant()` (line 175)
  - Modified `exponential_horn_tmatrix()` (line 268)

## Recommendation

**REVERT the lossy changes for now.** The current implementation makes things worse, not better. Focus on:

1. Fixing the basic impedance calculation (A/C vs D/B vs C/A)
2. Getting the passive stub impedance to match Hornresp
3. Then add losses once the physics is correct

The research finding about losses is correct, but our implementation is breaking the model. We need to fix the fundamentals first.
