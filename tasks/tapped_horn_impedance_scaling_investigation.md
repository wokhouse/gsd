# Tapped Horn Impedance Scaling Investigation

**Date**: 2025-01-11
**Status**: EMPIRICAL SCALING TESTED - Not viable, different errors at different frequencies

## Executive Summary

Tested empirical scaling factors on the Z = A/C formula to match Hornresp's quarter-wave impedance. While scaling fixes the 50 Hz impedance, it breaks other frequencies, indicating this is **not the correct approach**.

## Investigation Summary

### Problem Statement

Original issue: At 50 Hz (quarter-wave frequency), Ze = 6.14 Ω vs Hornresp 22.49 Ω (-73% error).

The upstream impedance Z_up = A/C = 1.03e+04 Pa·s/m³ gives Ze = 6.14 Ω, which is too low.

### Diagnostic Findings

Working backwards from Hornresp Ze = 22.49 Ω at 50 Hz:
- Target Z_acoustic = 3.323e+03 Pa·s/m³
- Required Z_up = 3.054e+03 Pa·s/m³
- Current Z_up (A/C) = 1.03e+04 Pa·s/m³
- Ratio: target/current ≈ 0.3

### Scaling Tests

Tested different scaling factors on Z_up = scaling × (A/C):

| Scaling | 40 Hz Ze | 50 Hz Ze | 60 Hz Ze | 40 Hz Err | 50 Hz Err | 60 Hz Err | Notes |
|---------|----------|----------|----------|-----------|-----------|-----------|-------|
| 1.0× (no scaling) | 9.23 Ω | 9.23 Ω | 8.90 Ω | +33% | -59% | -21% | Original |
| 0.5× | 38.63 Ω | 11.70 Ω | 7.53 Ω | +458% | -48% | -33% | Worse |
| 0.3× | 50.55 Ω | 14.30 Ω | 7.92 Ω | +630% | -36% | -30% | Worse |
| 0.1× | 68.88 Ω | 20.69 Ω | 11.60 Ω | +895% | -8% | +3% | 50-60 Hz good! |
| 0.09× | 69.56 Ω | 21.24 Ω | 11.95 Ω | +905% | -6% | +6% | Balanced |
| 0.085× | 69.86 Ω | 21.54 Ω | 12.13 Ω | **+909%** | **-4%** | **+8%** | Best compromise |
| 0.08× | 70.14 Ω | 21.84 Ω | 12.32 Ω | +914% | -3% | +10% | 50 Hz best |

### Full Frequency Range (0.085× scaling)

```
Freq (Hz) | gsd Ze  | HR Ze   | Err %
---------------------------------------------
40       |  69.86  |   6.92  | +909.0  ← TERRIBLE
50       |  21.54  |  22.49  |   -4.2  ← GOOD
60       |  12.13  |  11.24  |   +7.9  ← GOOD
80       |   9.28  |   7.70  |  +20.5  ← OK
100      |   6.66  |   5.94  |  +12.1  ← OK
150      |   5.79  |   6.08  |   -4.8  ← GOOD
200      |   5.96  |   7.51  |  -20.6  ← OK
300      |   5.42  |   5.35  |   +1.4  ← EXCELLENT
400      |   5.73  |   5.80  |   -1.3  ← EXCELLENT
500      |   6.23  |   6.34  |   -1.7  ← EXCELLENT

RMS error: 19.92 Ω (vs 9.45 Ω original)
Correlation: 0.138 (vs 0.973 original)
```

## Key Finding

**Empirical scaling is NOT the solution.** While 0.085× scaling improves the quarter-wave region (50-100 Hz), it catastrophically breaks 40 Hz (+909% error).

### Why Scaling Fails

The scaling factor needs to be **frequency-dependent**:
- At 40 Hz (below quarter-wave): Need Z_up HIGH (closed pipe behavior)
- At 50 Hz (quarter-wave): Need Z_up LOW (pressure node)
- At higher frequencies: Scaling works reasonably

A constant scaling factor cannot handle these different physical regimes.

### Physics Interpretation

The counterintuitive result (lower Z_up → higher Ze) is due to the inverse relationship:

```
Z_mech_total = Z_mech_driver + Z_mech_acoustic
Z_motional = (BL)² / Z_mech_total  ← Inverse!
Z_e = Z_vc + Z_motional
```

**Lower** acoustic impedance → **lower** Z_mech_total → **higher** Z_motional → **higher** Ze

This is why scaling down Z_up by 0.085× increases Ze from 9.23 Ω to 21.54 Ω.

## Root Cause Analysis

The fundamental issue is **NOT** the impedance formula itself, but rather:

1. **Quarter-wave physics is different than expected**
   - For a tapped horn, the quarter-wave resonance does NOT create a simple pressure node
   - The driver excites BOTH ends of the upstream section
   - Standard transmission line formulas don't directly apply

2. **The active loop model may be more correct than passive stub**
   - Passive stub (Z = A/C) treats upstream as a simple impedance
   - Active loop models the driver exciting both throat and tap
   - But active loop gives Ze = 6.14 Ω, which is also wrong

3. **We may be missing key physics**
   - Hornresp uses losses (we've tried, made it worse)
   - Hornresp may use different T-matrix formulation
   - Throat boundary condition may not be "closed" as we assumed

## Recommendations

### Immediate Actions

1. **Revert to baseline (Z = A/C)** - Empirical scaling is a dead end
2. **Accept 50 Hz error for now** - 59% error at one frequency is better than breaking the whole model
3. **Focus on SPL calculation** - Impedance is "good enough" for design work

### Research Needed

1. **How does Hornresp calculate tapped horn impedance?**
   - Does it use T-matrices at all?
   - What formula does it use for the upstream section?
   - Can we find Hornresp source code or detailed documentation?

2. **What is the correct physics model?**
   - Active loop vs passive stub - which is really correct?
   - Why does neither match Hornresp at 50 Hz?
   - Is there a third model we're missing?

3. **Validate T-matrix implementation**
   - Are our T-matrix elements correct?
   - Do they match Kolbrek's MMM_toolbox?
   - Test with known analytical solutions

4. **Quarter-wave resonance in tapped horns**
   - Is it really a pressure node?
   - How does the driver excitation affect this?
   - What does Hornresp show for throat impedance at 50 Hz?

## Conclusion

The empirical scaling approach successfully improved the quarter-wave impedance (50 Hz: 4% error vs 59% original), but at the cost of breaking 40 Hz (+909% error vs 33% original).

**This indicates the impedance formula Z = A/C is fundamentally correct for most frequencies, but something special happens at quarter-wave that we don't yet understand.**

The way forward is NOT to add empirical corrections, but to understand the underlying physics better through research and validation.

## Next Steps

1. Revert to Z = A/C (no scaling)
2. Document current model as "validated except near quarter-wave resonance"
3. Add warning in code about 50 Hz limitation
4. Focus on improving SPL calculation
5. Conduct deeper research into Hornresp's methods

---

**Status**: Investigation complete - empirical scaling rejected as viable approach
**Recommendation**: Return to passive stub baseline (Z = A/C) and document limitations
