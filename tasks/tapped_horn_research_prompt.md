# Tapped Horn Simulation - Research Request for Clipboard Agent

**Date**: 2025-01-11
**Status**: Need research on Hornresp's throat boundary condition and impedance calculation

## Executive Summary

We have implemented a tapped horn simulation that validates against Hornresp (industry standard). Our current implementation achieves **0.973 correlation** and **9.45 Ω RMS error** in electrical impedance, but still has significant errors (up to 72%) at the quarter-wave resonance frequency (~50 Hz).

We need research to understand **how Hornresp models the throat boundary condition** and **what physics we're missing** that causes the impedance to be 3-7× higher than Hornresp's values.

## Current Implementation Assumptions

### 1. Throat Boundary Condition
**Assumption**: The throat (S1, upstream end) is a **rigid closed wall**
- Boundary condition: U_throat = 0 (zero volume velocity)
- Reflection coefficient: R = +1 for pressure
- Impedance calculation: Z_throat → ∞

**Evidence this might be wrong**:
- At 50 Hz, our Z_acoustic = 2.37e+04 Pa·s/m³
- Hornresp requires Z_acoustic ≈ 3.38e+03 Pa·s/m³ to get Ze = 22.49 Ω
- Our calculated impedance is **7× too high**

**Question**: Does Hornresp use a different throat boundary condition?
- Finite impedance instead of rigid wall?
- Radiation impedance at the throat?
- Losses in the throat section?
- Something else?

### 2. T-Matrix Formulation
**Assumption**: We use standard transmission line T-matrix for exponential horns
- Implementation: `exponential_horn_tmatrix()` in `src/gsd/simulation/horn_theory.py`
- Formulas: Based on wave equation solutions for exponential horns
- Literature: Olson (1947), Beranek (1954), Kolbrek's horn theory

**Evidence this might be wrong**:
- T-matrix elements are mostly real (A, D) or imaginary (B, C) at low frequencies
- Determinant AD - BC = 1 (lossless, reciprocal)
- Matches theory, but may not match Hornresp's implementation

**Question**: Does Hornresp use a different T-matrix formulation?
- Different coordinate system?
- Different sign conventions?
- Includes losses?
- Empirical corrections?

### 3. Driver Parameters
**Assumption**: We use the following Thiele-Small parameters from Hornresp:
```python
ThieleSmallParameters(
    S_d=855e-4,       # 855 cm²
    BL=21.2,          # T·m
    M_md=0.147,       # 147 g = 0.147 kg (driver mass only)
    R_ms=6.80,        # N·s/m
    R_e=5.20,         # Ω
    L_e=1.40e-3,      # 1.40 mH
    C_ms=1.04e-4,     # m/N
)
```

**Evidence this might be wrong**:
- Hornresp may use M_ms (total mass) instead of M_md (driver mass only)
- Parameter names/units may differ
- Need to verify all parameters match exactly

**Question**: Are we using the exact same parameters as Hornresp?

### 4. Radiation Impedance
**Assumption**: Mouth radiation uses circular piston in infinite baffle
- Implementation: `circular_piston_radiation_impedance()`
- Formula: Beranek (1954), Eq. 5.20
- Uses Struve H₁ function approximation

**Evidence this might be wrong**:
- Hornresp may use a different radiation model
- May include mouth diffraction effects
- May use empirical corrections

**Question**: Does Hornresp use the same radiation impedance formula?

### 5. Losses
**Assumption**: Lossless T-matrix propagation
- No wall losses
- No thermal/viscous losses in air
- No damping in horn sections

**Evidence this might be wrong**:
- Losses would reduce impedance at resonances
- Could explain why our Z is 3-7× too high
- Hornresp likely includes some loss mechanisms

**Question**: What losses does Hornresp include in its model?

## Current Impedance Calculation

### Active Loop Model (Currently Implemented)

**Derivation**:
```
Upstream segment (S1 → S2) with T-matrix [A_12, B_12; C_12, D_12]

Boundary conditions:
  U_1 = -U_sd (driver rear flow into throat)
  p_2 = Z_dn * U_2_out (tap pressure drives downstream)
  U_2_out = U_2_in + U_sd (flow conservation)

Solving:
  p_2 = U_sd * [Z_dn * (D_12 - 1)] / [C_12 * Z_dn + D_12]
  p_1 = A_12 * p_2 + B_12 * (p_2/Z_dn - U_sd)

  Z_acoustic = (p_1 - p_2) / U_sd
```

**Results**:
- 40 Hz: Z = 7.01e+04 → Ze = 6.08 Ω ✅ (close to HR 6.92 Ω)
- 50 Hz: Z = 2.37e+04 → Ze = 6.14 Ω ❌ (HR 22.49 Ω, error -72%)
- 60 Hz: Z = 4.37e+04 → Ze = 5.52 Ω ❌ (HR 11.24 Ω, error -51%)

### Passive Stub Model (Previously Implemented)

**Derivation**:
```
Z_up = A_up / C_up (closed throat)
Z_down = (A_dn * Z_rad + B_dn) / (C_dn * Z_rad + D_dn)
Z_tap = Z_up || Z_down (parallel combination)
```

**Results**:
- 40 Hz: Z = 2.50e+03 → Ze = 4.33 Ω (HR 6.92 Ω, worse)
- 50 Hz: Z = 6.43e+03 → Ze = 6.14 Ω (same as active, still wrong)
- 60 Hz: Z = 1.75e+04 → Ze = 5.52 Ω (same as active, still wrong)

### Target Values (from Hornresp)

Working backwards from Hornresp's Ze at 50 Hz:
```
Target: Ze = 22.49 Ω

Required:
  Z_acoustic ≈ 3.38e+03 Pa·s/m³
  Z_mechanical_acoustic ≈ 24.74 N·s/m
  Z_mechanical_total ≈ 26.02 N·s/m
  Z_mot ≈ 17.27 Ω
```

**Comparison**:
- Target Z_acoustic: 3.38e+03
- Active loop Z: 2.37e+04 (7× too high)
- Passive stub Z: 6.43e+03 (2× too high)
- Closed throat Z_up: 1.03e+04 (3× too high)

**Neither model predicts the correct acoustic impedance.**

## Quarter-Wave Resonance Physics

### Theoretical Calculations

```
Upstream length: L_up = 180 cm = 1.8 m
Speed of sound: c = 343 m/s

Quarter-wave frequency:
  f_qw = c / (4 * L_up) = 343 / (4 * 1.8) = 47.6 Hz

Wavelength at f_qw:
  λ = c / f_qw = 343 / 47.6 = 7.2 m

Round trip to throat:
  2 * L_up = 3.6 m = λ/2 → 180° phase shift
```

### Expected Behavior

At quarter-wave resonance (47.6 Hz):
1. Wave travels from tap to throat (1.8 m)
2. Reflects at throat (R = +1 for rigid wall)
3. Travels back from throat to tap (1.8 m)
4. Total phase shift: 180° (round trip = λ/2)
5. Front path should self-cancel at mouth
6. Throat should act as pressure node (Z → 0)

### What We Observe

At 50 Hz (close to f_qw):
- Throat impedance (closed pipe): Z_up = 1.03e+04 Pa·s/m³ (high, not zero)
- Target Z_acoustic: 3.38e+03 Pa·s/m³ (3× lower than Z_up)
- No evidence of quarter-wave cancellation in impedance

**Question**: Why doesn't the throat impedance go to zero at quarter-wave?

## Horn Geometry

```
Upstream section:
  S1 (throat): 150 cm²
  S2 (tap): 855 cm²
  L12: 180 cm
  Profile: exponential

Downstream section:
  S2 (tap): 855 cm²
  S3 (intermediate): 2265 cm²
  S4 (mouth): 6000 cm²
  L23 + L34: 200 cm (total)
  Profile: exponential (3-segment)

Driver:
  S_d = 855 cm² (matches tap area S2)
  Mounted at tap point (S2)
```

## Validation Data

### Hornresp Simulation Results

File: `imports/th_sim.txt`
- 534 data points from 20 Hz to 500 Hz
- Columns: Freq, SPL, Phase, Ze, Xd, etc.
- Test frequencies: 40, 50, 60, 80, 100, 150, 200 Hz

### Key Validation Points

| Freq | HR SPL | HR Ze  | gsd SPL | gsd Ze | SPL Error | Ze Error |
|------|--------|--------|---------|--------|-----------|----------|
| 40   | 106.53 | 6.92   | 70.83   | 4.33   | -35.70    | -2.59    |
| 50   | 97.05  | 22.49  | 89.03   | 6.14   | -8.02     | -16.35   |
| 60   | 97.67  | 11.24  | 97.73   | 5.52   | +0.06     | -5.72    |
| 80   | 69.54  | 7.70   | 92.94   | 3.78   | +23.40    | -3.92    |
| 100  | 100.16 | 5.94   | 87.73   | 5.03   | -12.43    | -0.91    |
| 150  | 98.88  | 6.08   | 87.33   | 4.40   | -11.55    | -1.68    |
| 200  | 107.04 | 7.51   | 100.74  | 4.28   | -6.29     | -3.23    |

**Observations**:
- 60 Hz: SPL excellent (+0.06 dB), but Ze wrong (-5.72 Ω)
- 50 Hz: Both SPL and Ze significantly wrong
- Quarter-wave region (50-80 Hz) has largest errors

## Research Questions

### CRITICAL: Throat Boundary Condition

1. **What boundary condition does Hornresp use at the throat?**
   - Rigid wall (U = 0)?
   - Pressure release (p = 0)?
   - Finite impedance?
   - Radiation impedance?
   - Lossy termination?

2. **How does Hornresp calculate the throat impedance at quarter-wave?**
   - Should it be zero (pressure node)?
   - Should it be infinite (velocity node)?
   - Should it be somewhere in between?

3. **Why is our Z_acoustic 7× too high at 50 Hz?**
   - Is the throat boundary condition wrong?
   - Is the T-matrix calculation wrong?
   - Are we missing losses?
   - Is the driver excitation model wrong?

### HIGH PRIORITY: T-Matrix Validation

4. **How can we validate our T-matrix calculation?**
   - Compare with known analytical solutions?
   - Compare with Kolbrek's MMM_toolbox?
   - Test with simple geometries?

5. **Does Hornresp use a different T-matrix formulation?**
   - Different sign conventions?
   - Different coordinate definitions?
   - Includes losses by default?

### MEDIUM PRIORITY: Losses and Corrections

6. **What losses does Hornresp include?**
   - Wall boundary layer losses?
   - Thermal/viscous losses in air?
   - Horn wall absorption?
   - How much do these affect impedance at resonance?

7. **Does Hornresp include any empirical corrections?**
   - Mouth diffraction effects?
   - Driver modeling corrections?
   - Frequency-dependent adjustments?

### LOWER PRIORITY: Driver Parameters

8. **Are our Thiele-Small parameters exactly matching Hornresp?**
   - M_md vs M_ms?
   - C_ms calculation?
   - BL product definition?

## Expected Deliverables

### SECTION 1: Research Findings (for human review)

1. **Throat Boundary Condition**
   - What boundary condition does Hornresp use?
   - Literature citations for tapped horn throat modeling
   - Explanation of why our assumption (rigid wall) is wrong

2. **Quarter-Wave Physics**
   - What happens to throat impedance at f_qw?
   - Should it be zero, infinite, or finite?
   - Explain the discrepancy with our calculations

3. **Impedance Calculation**
   - How does Hornresp calculate tapped horn impedance?
   - Does it use active loop model, passive stub, or something else?
   - Provide correct formulas with literature citations

4. **Validation Approach**
   - How to validate T-matrix calculations
   - Known test cases to check implementation
   - Comparison with MMM_toolbox or other references

### SECTION 2: Implementation Instructions (for Claude Code)

1. **File to modify**: `src/gsd/simulation/tapped_horn_theory.py`

2. **Function to fix**: `calculate_tapped_horn_impedance_active_loop()` or replace with new implementation

3. **Specific changes needed**:
   - Correct throat boundary condition implementation
   - Correct T-matrix calculation (if needed)
   - Add losses (if needed)
   - Any other corrections based on research

4. **Validation steps**:
   - Recalculate impedance at 50 Hz
   - Target: Z_acoustic ≈ 3.38e+03 Pa·s/m³ → Ze ≈ 22.49 Ω
   - Full frequency sweep: RMS error < 3 Ω, correlation > 0.98
   - SPL RMS error < 3 dB in passband

5. **Expected results after fix**:
   - 50 Hz: Ze ≈ 22.49 Ω (currently 6.14 Ω)
   - 60 Hz: Ze ≈ 11.24 Ω (currently 5.52 Ω)
   - Overall: RMS error < 3 Ω

## Context and References

### Literature We Have

1. **Olson (1947)**: `literature/horns/olson_1947.md`
   - Exponential horn theory
   - T-matrix methods

2. **Beranek (1954)**: `literature/horns/beranek_1954.md`
   - Radiation impedance
   - Horn theory

3. **Kolbrek**: `literature/horns/kolbrek_horn_theory_tutorial.md`
   - Modern horn theory
   - T-matrix methods

4. **Berzborn & Smithers (2018)**: AES Paper 10047
   - Tapped horn acoustic model
   - Referenced in code but not full text

5. **Chabassier (2018)**: `literature/transmission_lines/chabassier_tournemenne_2018_tmatrix.md`
   - T-matrix methods
   - Wave propagation

### Literature We May Need

1. **Hornresp documentation/algorithms**
   - How does Hornresp calculate impedance?
   - What boundary conditions does it use?

2. **MMM_toolbox by Bjørn Kolbrek**
   - Reference T-matrix implementation
   - Validation test cases

3. **Tapped horn specific papers**
   - Danley patents
   - Berzborn & Smithers full paper
   - Other tapped horn modeling approaches

## Success Criteria

After implementing research findings:

1. **Electrical Impedance**:
   - RMS error < 3 Ω (currently 9.45 Ω)
   - Correlation > 0.98 (currently 0.973)
   - 50 Hz: Ze ≈ 22.49 Ω (currently 6.14 Ω, error -72%)
   - 60 Hz: Ze ≈ 11.24 Ω (currently 5.52 Ω, error -51%)

2. **SPL**:
   - RMS error < 3 dB (currently ~14 dB)
   - Passband (40-200 Hz) error < 3 dB
   - Quarter-wave null at correct frequency

3. **Physical Correctness**:
   - Quarter-wave resonance behavior matches theory
   - Throat impedance matches Hornresp at f_qw
   - All boundary conditions documented and validated

## Ready for Research

This handoff document provides:
- ✅ Clear problem statement (impedance 3-7× too high)
- ✅ Current assumptions and why they might be wrong
- ✅ Specific research questions prioritized by importance
- ✅ Target values and validation criteria
- ✅ Expected deliverables format

**Please copy this prompt to the clipboard research agent.**
