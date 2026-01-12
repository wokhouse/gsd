# URGENT: Tapped Horn T-Matrix Impedance Formula Research

**Date**: 2025-01-11
**Status**: CRITICAL FINDING - Wrong impedance formula causing 73% error

## Executive Summary

We implemented the active loop impedance model for tapped horns based on previous research. This is working well (correlation 0.973), but we discovered a **critical issue**: we're using the wrong T-matrix impedance formula.

**Key Discovery**: At quarter-wave frequency (47.6 Hz), the throat impedance should be ~0 (pressure node), but:
- Our formula (A/C) = 1.03e+04 Pa·s/m³ (high, WRONG)
- Alternative (D/B) = 6.35e-05 Pa·s/m³ (near zero, CORRECT!)
- Alternative (C/A) = 5.63e-05 Pa·s/m³ (near zero, CORRECT!)

**This suggests we should be using D/B or C/A instead of A/C.**

## Current Implementation

### File: `src/gsd/simulation/horn_theory.py`

**Function**: `exponential_horn_tmatrix()`
- Returns T-matrix elements (a, b, c, d) for exponential horns
- Documentation says: `[p₁, U₁]ᵀ = [a b; c d][p₂, U₂]ᵀ`
- Maps FROM port 2 (mouth/tap) TO port 1 (throat)

**Function**: `upstream_section_impedance()` in `tapped_horn_theory.py`
- Calculates throat impedance for closed termination: `Z_up = A/C`
- Used in active loop model

### T-Matrix Convention

Our documentation states:
```
The T-matrix relates pressure and volume velocity at the throat (port 1) to the mouth (port 2):
    [p₁, U₁]ᵀ = [a b; c d][p₂, U₂]ᵀ
```

For a closed throat (U₁ = 0), the impedance looking from the tap is:
```
Z_up = A/C
```

**This gives high impedance (1.03e+04) at quarter-wave, which is WRONG.**

## The Problem

### At Quarter-Wave Frequency (47.6 Hz)

Expected physics:
- Upstream length L = 1.8 m
- Quarter-wave: L = λ/4, so round trip = λ/2
- Round trip phase shift = 180°
- Throat should be pressure node (Z → 0)
- Driver sees low impedance → high cone excursion → high electrical impedance

What we observe:
- Hornresp Ze at 50 Hz = 22.49 Ω (HIGH, correct)
- Our Ze at 50 Hz = 6.14 Ω (LOW, wrong)
- Our Z_up (A/C) = 1.03e+04 Pa·s/m³ (HIGH, blocking driver)
- Z_up (D/B) = 6.35e-05 Pa·s/m³ (LOW, would allow high Ze!)
- Z_up (C/A) = 5.63e-05 Pa·s/m³ (LOW, would allow high Ze!)

**The D/B and C/A formulas give near-zero impedance, which matches the physics!**

### Validation Data

At 50 Hz (close to quarter-wave):

| Formula | Z_up | Expected | Correct? |
|---------|------|----------|----------|
| A/C | 1.03e+04 | ~0 | ❌ |
| D/B | 6.35e-05 | ~0 | ✅ |
| C/A | 5.63e-05 | ~0 | ✅ |
| B/D | 1.57e+04 | ~0 | ❌ |

## T-Matrix Elements at 50 Hz

```
A = (4.377382316108072-0.016372338921467607j)
B = (-31463.363935948364+108.0186876335037j)
C = (-0.0002463260103886807+8.45676019460253e-07j)
D = (1.9989641206013304-0.004680401479814429j)

Determinant (AD - BC): 0.9999999999999991+1.3877787807814457e-17j ≈ 1.0
```

The determinant is ~1.0, which confirms the T-matrix itself is correct.

## Research Questions

### CRITICAL: Which Impedance Formula Is Correct?

1. **For our T-matrix convention [p₁, U₁]ᵀ = [a b; c d][p₂, U₂]ᵀ, what is the correct formula for input impedance when port 1 is closed (U₁ = 0)?**

   - We're using Z = A/C (gives high impedance, wrong)
   - D/B gives near-zero impedance (matches physics!)
   - Which one is correct and why?

2. **Are we confusing the T-matrix direction?**

   - Our docs say: maps FROM port 2 TO port 1
   - But maybe the actual implementation maps FROM port 1 TO port 2?
   - If direction is reversed, the impedance formula changes

3. **What is the standard formula for input impedance from T-matrix?**

   Literature says:
   - For [p₁, U₁] = T * [p₂, U₂] with Z_load at port 1:
     - If U₁ = 0 (closed): Z_in_from_2 = A/C
     - If p₁ = 0 (open): Z_in_from_2 = B/D
     - If Z₁ is finite: Z_in_from_2 = (A*Z₁ + B) / (C*Z₁ + D)

   - But what if we have the REVERSE T-matrix?

### HIGH PRIORITY: T-Matrix Convention Verification

4. **How can we verify our T-matrix direction and convention?**

   - Test with known analytical solutions?
   - Check Kolbrek's MMM_toolbox conventions?
   - Verify with simple cylindrical pipe?

5. **What do other horn simulation tools use?**

   - Does Hornresp use T-matrices?
   - What impedance formula does Hornresp use?
   - Can we find Hornresp source code or documentation?

### MEDIUM PRIORITY: Active Loop Model

6. **Is our active loop impedance derivation correct?**

   We use: Z_acoustic = (p₁ - p₂) / U_sd
   - Is this the correct pressure difference?
   - Should it be (p₂ - p₁) instead?
   - Are we missing terms?

7. **Why does the active loop model give reasonable results (0.973 correlation) if the impedance formula is wrong?**

   - Maybe the error partially cancels out?
   - Maybe we're accidentally using a different formula somewhere?

## Context

### Horn Geometry

```
Upstream section:
  S1 (throat): 150 cm² → CLOSED (rigid wall)
  S2 (tap): 855 cm² → DRIVER FRONT
  L12: 180 cm
  Profile: exponential
  Flare constant: m = 0.4835 m⁻¹ (Kolbrek convention)

Driver:
  S_d = 855 cm² (matches tap area S2)
  Mounted at tap point (S2)
  Excites both throat (rear) and tap (front)
```

### Key Frequencies

```
Cutoff frequency (Kolbrek): f_c = 26.39 Hz
Quarter-wave frequency: f_qw = 47.6 Hz
Test frequency: f = 50 Hz (close to f_qw)

At 50 Hz:
  k = 0.9159 rad/m
  m = 0.4835 m⁻¹
  k > m → ABOVE CUTOFF → propagating waves
```

### Current Performance

**Electrical Impedance**:
- 40 Hz: 4.33 Ω vs 6.92 Ω (good)
- 50 Hz: 6.14 Ω vs 22.49 Ω (**-73% error**)
- 60 Hz: 5.52 Ω vs 11.24 Ω (**-51% error**)
- 100 Hz: 5.03 Ω vs 5.94 Ω (good)

**Overall**: RMS error = 9.45 Ω, Correlation = 0.973

## Expected Deliverables

### SECTION 1: Research Findings (for human review)

1. **Correct T-Matrix Impedance Formula**
   - For T-matrix [p₁, U₁] = [a b; c d][p₂, U₂]
   - With closed port 1 (U₁ = 0)
   - What is the input impedance Z_in seen from port 2?
   - Provide derivation with literature citations

2. **T-Matrix Direction Verification**
   - How to verify if our T-matrix maps 2→1 or 1→2
   - Test cases with known results
   - Comparison with Kolbrek's conventions

3. **Why D/B Gives Near-Zero at Quarter-Wave**
   - Explain the physics
   - Is D/B the correct formula for our case?
   - Or is there something else going on?

4. **Hornresp's Method**
   - How does Hornresp calculate tapped horn impedance?
   - Does Hornresp use T-matrices?
   - What formulas does it use?

### SECTION 2: Implementation Instructions (for Claude Code)

1. **File to modify**: `src/gsd/simulation/tapped_horn_theory.py`

2. **Function to fix**: `upstream_section_impedance()` and/or `calculate_tapped_horn_impedance_active_loop()`

3. **Specific changes**:
   - Change impedance formula from A/C to correct formula
   -可能是 D/B, C/A, or something else based on research
   - Add comments explaining the correct formula with citations

4. **Validation**:
   - At 50 Hz: Z_up should be ~0 (not 1.03e+04)
   - At 50 Hz: Ze should be ~22.49 Ω (not 6.14 Ω)
   - Full frequency sweep: RMS error < 3 Ω

5. **Expected results**:
   - Quarter-wave impedance: Z_up ≈ 0 at 47.6 Hz
   - Electrical impedance peak at quarter-wave
   - Overall Ze RMS error < 3 Ω

## Literature to Consult

1. **Kolbrek, "Horn Loudspeaker Simulation Part 1"**
   - T-matrix input impedance formulas
   - https://kolbrek.hornspeakersystems.info/

2. **MMM_toolbox by Bjørn Kolbrek**
   - Reference implementation
   - https://github.com/bkolbrek/MMM_toolbox

3. **Berzborn & Smithers (2018), AES Paper 10047**
   - Tapped horn impedance model
   - T-matrix methods

4. **Hornresp Documentation**
   - How Hornresp calculates impedance
   - T-matrix or other methods?

5. **Transmission Line Theory**
   - Standard T-matrix impedance formulas
   - Input impedance for closed/open terminations

## Test Case for Validation

Upstream horn at 50 Hz:
```
Throat area: 150 cm² (closed)
Tap area: 855 cm²
Length: 1.8 m
Profile: exponential

T-matrix elements:
  A = 4.38 - 0.016j
  B = -31463 + 108j
  C = -0.000246 + 0.000000846j
  D = 2.00 - 0.0047j

Determinant: AD - BC ≈ 1.0

Question: What is the impedance Z_up seen at the tap looking into the closed throat?

Formulas to test:
  Z = A/C = 1.03e+04 (our current, WRONG)
  Z = D/B = 6.35e-05 (near zero, matches physics!)
  Z = C/A = 5.63e-05 (near zero, matches physics!)
  Z = B/D = 1.57e+04 (high, wrong)
```

## Success Criteria

After implementing the correct formula:

1. **Quarter-wave impedance**: Z_up ≈ 0 at 47.6 Hz
2. **Electrical impedance at 50 Hz**: Ze ≈ 22.49 Ω (currently 6.14 Ω)
3. **Overall Ze RMS error**: < 3 Ω (currently 9.45 Ω)
4. **Correlation**: > 0.98 (currently 0.973)
5. **SPL RMS error**: < 3 dB (currently ~13 dB)

## Urgency

**HIGH** - This is blocking all further progress. The impedance formula is fundamental to the model. Without fixing this, we cannot achieve accurate results regardless of other improvements.

## Files Referenced

- `src/gsd/simulation/horn_theory.py` - T-matrix calculation
- `src/gsd/simulation/tapped_horn_theory.py` - Impedance calculation
- `tasks/TAPPED_HORN_FINAL_STATUS.md` - Full status summary
- `imports/th_sim.txt` - Hornresp validation data

---

**READY FOR CLIPBOARD RESEARCH AGENT**

Please investigate:
1. The correct T-matrix impedance formula for our convention
2. Why D/B gives near-zero at quarter-wave
3. Whether we should use D/B, C/A, or another formula
4. How to verify our T-matrix direction and convention

Provide:
1. Explanation of the correct formula with derivation
2. Implementation instructions for fixing the code
3. Validation steps to confirm the fix
