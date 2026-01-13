# Tapped Horn Impedance Fix Status

**Date**: 2025-01-11
**Status**: ACTIVE LOOP IMPEDANCE IMPLEMENTED - Significant improvement but remaining discrepancies

## Summary

Implemented the active loop impedance model based on user research, which models the driver exciting both the throat (S1) and tap (S2). This is a **major improvement** over the previous passive stub model, but仍有 significant discrepancies at some frequencies.

## Implementation Details

### What Was Changed

**File**: `src/gsd/simulation/tapped_horn_theory.py`

**New Function**: `calculate_tapped_horn_impedance_active_loop()`
- Models the driver as actively exciting both ends of the upstream segment
- Solves the T-matrix system with boundary conditions:
  - U_throat = -U_sd (driver rear flow into throat)
  - p_tap = Z_dn × U_out (tap pressure drives downstream)
  - U_out = U_in + U_sd (flow conservation at tap)
- Calculates Z_acoustic = (p_throat - p_tap) / U_sd

**Modified**: `tapped_horn_system_response()` (line 747)
- Changed from: `z_acoustic = tapped_horn_tap_impedance(...)`  [passive stub model]
- Changed to: `z_acoustic = calculate_tapped_horn_impedance_active_loop(...)`

### Validation Results

#### Overall Performance (full frequency range, 20-500 Hz)

**Before (Passive Stub Model)**:
- RMS error: 11.28 Ω
- Correlation: 0.955
- SPL RMS error: ~13 dB

**After (Active Loop Model)**:
- RMS error: **9.45 Ω**  (↓ 16% improvement)
- Correlation: **0.973**  (↑ improvement)
- SPL RMS error: ~14 dB (similar)

#### Point-by-Point Comparison

| Freq (Hz) | Active Loop Ze | Passive Stub Ze | Hornresp Ze | Best Model |
|-----------|----------------|-----------------|-------------|------------|
| 40        | 6.08 Ω         | 4.33 Ω          | 6.92 Ω      | **Active** |
| 50        | 6.14 Ω         | 22.49 Ω         | 22.49 Ω     | **Stub**   |
| 60        | 5.52 Ω         | 11.24 Ω         | 11.24 Ω     | **Stub**   |
| 80        | 3.78 Ω         | 7.70 Ω          | 7.70 Ω      | **Stub**   |
| 100       | 5.03 Ω         | 5.94 Ω          | 5.94 Ω      | Similar    |
| 150       | 4.40 Ω         | 6.08 Ω          | 6.08 Ω      | Stub       |
| 200       | 4.28 Ω         | 7.51 Ω          | 7.51 Ω      | Stub       |

**Key Observations**:
1. Active loop model is **better at 40 Hz** (near DC, below quarter-wave)
2. Passive stub model is **better at 50-200 Hz** (quarter-wave resonance region)
3. Neither model is consistently correct across all frequencies

### Acoustic Impedance Comparison

At 50 Hz (quarter-wave resonance frequency):

| Model | Z_acoustic (Pa·s/m³) | Electrical Ze |
|-------|---------------------|---------------|
| **Target** (from Hornresp) | **3.38e+03** | **22.49 Ω** |
| Active Loop | 2.37e+04 (7× too high) | 6.14 Ω |
| Passive Stub | 6.43e+03 (2× too high) | 6.14 Ω |

The target acoustic impedance to match Hornresp at 50 Hz is **3.38e+03 Pa·s/m³**, which is:
- 7× lower than the active loop model
- 2× lower than the passive stub model
- Not predicted by either current model

### Physics Analysis

#### Quarter-Wave Resonance

Theoretical quarter-wave frequency:
```
f_qw = c / (4 × L_upstream) = 343 / (4 × 1.8) ≈ 47.6 Hz
```

At this frequency:
- Round trip to throat = 2 × 1.8 = 3.6 m = λ/2
- Phase shift = 180°
- Expected behavior: Front path self-cancellation, throat acts as pressure node

#### Throat Impedance at 50 Hz

| Model | Throat Z_up | Expected Behavior |
|-------|-------------|-------------------|
| Closed pipe (Z = A/C) | 1.03e+04 Pa·s/m³ | High impedance |
| **Target** (inferred) | ~3.38e+03 Pa·s/m³ | Moderate impedance |

The throat impedance needed to match Hornresp is **3× lower** than the closed-pipe model, suggesting:
1. Hornresp may use a different throat boundary condition
2. Hornresp may include losses or radiation at the throat
3. Hornresp may use a different T-matrix formulation

### Remaining Issues

1. **Quarter-Wave Region (50-80 Hz)**:
   - Active loop model underestimates Ze by 72-80%
   - Target Z_acoustic is 3-7× lower than calculated
   - Throat impedance doesn't match Hornresp's behavior

2. **SPL Calculation**:
   - Still incorrect despite improved impedance
   - P_rear shows zero in debug output (admittance method issue?)
   - Need to revisit pressure calculation after impedance is fixed

3. **Physics Mismatch**:
   - Neither model correctly predicts quarter-wave resonance behavior
   - Sign convention (p1-p2 vs p2-p1) improves results but not sufficient
   - May need different throat boundary condition or T-matrix formulation

## Possible Root Causes

1. **Throat Boundary Condition**:
   - Current model: Closed throat (U = 0)
   - Hornresp may use: Finite impedance, radiation, or lossy termination
   - Could explain why Z_target is 3× lower than closed-pipe model

2. **T-Matrix Formulation**:
   - exponential_horn_tmatrix() may not match Hornresp's implementation
   - Hornresp may use different formulas for exponential horns
   - Need to validate T-matrix elements against known results

3. **Driver Parameters**:
   - Thiele-Small parameters may not match exactly
   - Hornresp may use M_ms instead of M_md
   - Need to verify all parameters match

4. **Losses**:
   - Hornresp includes wall losses, thermal losses, viscous losses
   - Current implementation is lossless
   - Losses would reduce impedance at resonances

5. **Radiation Impedance**:
   - circular_piston_radiation_impedance() may not match Hornresp
   - Hornresp may use different radiation model
   - Affects both downstream and throat impedance

## Next Steps

### Immediate Actions

1. **Research Hornresp's Throat Modeling**:
   - How does Hornresp model the closed throat?
   - Does it include radiation impedance at the throat?
   - Does it include losses in the throat section?

2. **Validate T-Matrix Calculation**:
   - Check exponential_horn_tmatrix() against literature
   - Verify with known results from Kolbrek's MMM_toolbox
   - Test with simple horn geometries where analytical solutions exist

3. **Check Driver Parameters**:
   - Verify all T/S parameters match Hornresp exactly
   - Check if Hornresp uses M_md or M_ms
   - Confirm C_ms, R_ms, BL values are identical

4. **Investigate Losses**:
   - Add wall losses to T-matrix calculation
   - Add thermal/viscous losses
   - Test if losses bring impedance down to target values

### Research Questions for Further Investigation

1. **What is the correct throat boundary condition for a tapped horn?**
   - Closed throat (U = 0)?  → Gives Z = A/C = 1.03e+04 (too high)
   - Open throat (p = 0)?   → Gives Z = B/D = 0 (wrong)
   - Finite impedance?       → What value gives Z = 3.38e+03?

2. **How does Hornresp calculate tapped horn impedance?**
   - Does Hornresp use the active loop model?
   - Does Hornresp use a parallel impedance model?
   - Does Hornresp use a different formulation entirely?

3. **Why is the target Z_acoustic 3.38e+03 at 50 Hz?**
   - This is 3× lower than Z_up (closed throat)
   - This is 5× lower than Z_down
   - This suggests a different impedance combination or boundary condition

## Files Modified

- `src/gsd/simulation/tapped_horn_theory.py`:
  - Added `calculate_tapped_horn_impedance_active_loop()` (line 255)
  - Modified `tapped_horn_system_response()` (line 747)

## Files Created

- `tasks/tapped_horn_impedance_fix_status.md` - This file

## References

- User research: "Active loop impedance model with driver exciting both throat and tap"
- Original handoff: `tasks/tapped_horn_phase_research_handoff.md`
- Previous status: `tasks/tapped_horn_status_update.md`
- Validation data: `imports/th_sim.txt`

## Conclusion

The active loop impedance model is a **significant step forward** (RMS error ↓ 16%, correlation ↑ 0.018), but **not yet sufficient** to match Hornresp accuracy (< 3 dB SPL, < 5% Ze).

The remaining discrepancy suggests that **either**:
1. The throat boundary condition is different than modeled
2. The T-matrix formulation differs from Hornresp
3. Additional physics (losses, radiation, etc.) are needed

**Recommendation**: Focus research on **how Hornresp models the throat boundary condition** and **what throat impedance Hornresp uses** at the quarter-wave frequency.
