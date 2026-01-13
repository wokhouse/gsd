# Tapped Horn Phase Interference Research Handoff

**Date**: 2025-01-11
**Status**: CRITICAL BUG FOUND - Phase-aware implementation incorrect
**Branch**: feature/tapped-horn

## Executive Summary

We implemented phase-aware front/rear path combination for tapped horn simulation based on research findings, but **validation against Hornresp shows the implementation is fundamentally incorrect**. The SPL, impedance, and excursion are all significantly wrong, with errors ranging from -22 dB to +22 dB.

## What Was Implemented

### New Functions Added to `src/gsd/simulation/tapped_horn_theory.py`

1. **`calculate_rigid_reflection_coefficient()`** (line 255)
   - Returns R = +1 for pressure at rigid wall (closed throat)

2. **`calculate_front_path_pressure_contribution()`** (line 271)
   - Calculates pressure at mouth from front radiation path
   - Path: driver front → upstream → throat (reflect) → back to tap → downstream → mouth
   - Uses transmission coefficient: `T_up = Z_down / (Z_up + Z_down)`
   - Uses T-matrix propagation for both upstream and downstream sections

3. **`calculate_rear_path_pressure_contribution()`** (line 390)
   - Calculates pressure at mouth from rear radiation path
   - Path: driver rear → tap → downstream → mouth
   - Uses transmission coefficient: `T_down = Z_up / (Z_up + Z_down)`

4. **Modified `tapped_horn_system_response()`** (line 532)
   - **OLD**: `u_mouth = u_tap / (c * z_rad + d)` (all volume velocity downstream)
   - **NEW**: Calculates front and rear paths separately, combines as `P_total = P_front - P_rear`

### Tests Created

1. **`tests/test_tapped_horn_path_interference.py`** - All 8 tests pass
   - Quarter-wave resonance calculation
   - Front path cancellation behavior
   - Phase relationships
   - Vector superposition
   - Impedance splitting
   - System integration

2. **`tests/test_tapped_horn_hornresp_validation.py`** - **FAILS**
   - Uses Hornresp data from `imports/th_sim.txt`
   - Driver: BC 15PS100 parameters (from Hornresp)
   - Horn: 3-segment exponential (S1=150, S2=855, S3=2265, S4=6000 cm²)

## Validation Results - CRITICAL ISSUES

### Hornresp Comparison Data

Test frequencies: 40, 50, 60, 80, 100, 150, 200 Hz
Input: 2.83V (1W into 8Ω)
Medium: ρ=1.18 kg/m³, c=343 m/s

| Freq (Hz) | gsd SPL (dB) | HR SPL (dB) | Error (dB) | gsd Ze (Ω) | HR Ze (Ω) |
|-----------|--------------|-------------|------------|------------|-----------|
| 40        | 83.66        | 106.53      | **-22.88** | 26.58      | 6.92      |
| 50        | 90.41        | 97.05       | **-6.65**  | 9.23       | 22.49     |
| 60        | 103.98       | 97.67       | **+6.31**  | 8.90       | 11.24     |
| 80        | 91.83        | 69.54       | **+22.30** | 9.38       | 7.70      |
| 100       | 89.88        | 100.16      | **-10.28** | 6.66       | 5.94      |
| 150       | 95.63        | 98.88       | **-3.25**  | 6.11       | 6.08      |
| 200       | 93.26        | 107.04      | **-13.78** | 6.15       | 7.51      |

**Expected accuracy**: <1-3 dB in passband
**Actual accuracy**: -22 to +22 dB (completely wrong)

**Correlation coefficient**: **-0.23** (negative correlation = wrong shape)

### Path Contribution Analysis

| Freq (Hz) | \|P_front\| | Phase  | \|P_rear\| | Phase  | \|P_total\| |
|-----------|-------------|--------|------------|--------|------------|
| 40        | 10.8        | -101.9° | 13.1       | -104.1° | 2.36       |
| 50        | 79.3        | -130.5° | 84.0       | -131.9° | 5.14       |
| 60        | 180         | +153.9° | 203        | +151.8° | 24.5       |
| 80        | 27.9        | -176.6° | 25.0       | +171.9° | 6.04       |

**KEY PROBLEM**: Front and rear path phases are nearly **identical** (within 2-3°), when they should differ significantly due to round-trip path length difference.

At quarter-wave frequency (47.6 Hz), the round trip to throat (2 × 1.8m = 3.6m = λ/2) should cause 180° phase shift, making front path **self-cancel**. Our implementation shows no such cancellation.

### Impedance Split Analysis

| Freq (Hz) | \|Z_up\|   | \|Z_down\| | T_up   | T_down  |
|-----------|------------|-------------|--------|---------|
| 40        | 4.53e+03   | 5.57e+03    | 0.552  | 0.449   |
| 60        | 1.69e+04   | 9.69e+03    | **1.035** | **1.809** |
| 100       | 6.63e+05   | 5.22e+03    | 0.008  | 1.007   |

**PROBLEM**: Transmission coefficients > 1.0 and not summing to 1.0 at 60 Hz.

## Root Cause Analysis

### The Physics Should Be

From Danley's patent and research:
- Quarter-wave frequency: f_qw = c / (4 × L_upstream) = 343 / (4 × 1.8) ≈ 47.6 Hz
- At f_qw: Round trip = 2 × L_upstream = λ/2 = **180° phase shift**
- Front path should **self-cancel** at mouth
- Only rear path should contribute significantly
- Front and rear driver are 180° out of phase (opposite diaphragm sides)

### What Our Implementation Does

```python
# Current approach in calculate_front_path_pressure_contribution():

# 1. Calculate transmission coefficient
tau_up = z_down / (z_up + z_down)
u_upstream = u_driver * tau_up

# 2. Propagate to throat using T-matrix
p_at_tap_upstream = u_upstream * z_up
p_throat = p_at_tap_upstream / a_up

# 3. Reflect at throat
p_throat_reflected = p_throat * calculate_rigid_reflection_coefficient()  # R = +1

# 4. Propagate back to tap
p_at_tap_reflected = p_throat_reflected * a_up  # <-- PROBLEM: a_up is real, no phase info

# 5. Propagate downstream to mouth
p_mouth_front = a_down * p_at_tap_reflected + b_down * u_at_tap_reflected
```

**THE ISSUE**: The T-matrix element `a_up` is **not capturing the round-trip phase shift**. We're using it bidirectionally, but:
- Forward direction (tap → throat): `p_throat = p_tap / a_up`
- Reverse direction (throat → tap): `p_tap = p_throat × a_up`

This assumes `a_up` is its own inverse, which is **only true if a_up is real**. For exponential horns, `a_up` is **complex** and frequency-dependent, containing phase information. The inverse operation for reverse propagation should use the **inverse T-matrix**, not the forward `a_up` element.

### Additional Issues

1. **Transmission coefficients > 1**: The calculation `tau_up = z_down / (z_up + z_down)` can exceed 1 when impedances are complex with opposite phase angles. We should use magnitude ratios or ensure proper normalization.

2. **Missing round-trip phase factor**: We're not explicitly adding the phase shift `exp(-2j × k × L_upstream)` for the round trip.

3. **Front/rear combination**: Using `P_total = P_front - P_rear` assumes the driver front/rear are 180° out of phase, but this might not be the right way to combine the paths at the mouth.

## What Needs Research

### Critical Questions for Research Agent

1. **T-Matrix Bidirectional Propagation**
   - How to correctly use T-matrix for reverse propagation (mouth → throat vs throat → mouth)?
   - Is the inverse T-matrix different from the transpose?
   - Reference: Check MMM_toolbox by Bjørn Kolbrek (GitHub)

2. **Phase Accumulation in Horns**
   - How does phase accumulate in exponential horns?
   - What's the correct way to calculate round-trip phase shift?
   - Does the T-matrix `a` element contain phase, or is it purely real?

3. **Volume Velocity Splitting at Junction**
   - How does volume velocity split at the tap point between upstream and downstream?
   - Should transmission coefficients use impedance magnitudes or complex values?
   - Reference: Berzborn & Smithers (2018), AES Paper 10047

4. **Hornresp's Implementation**
   - How does Hornresp calculate tapped horn response?
   - Does Hornresp explicitly model front/rear path interference?
   - Can we find Hornresp source code or detailed algorithm description?

5. **Alternative Approaches**
   - Should we use pressure wave decomposition (forward/backward waves)?
   - Would a transmission line matrix (TLM) approach be better?
   - Reference: Chabassier & Tournemenne (2018) on T-matrix methods

### Literature to Consult

1. **Kolbrek, B. "Horn Loudspeaker Simulation" series**
   - Part 1: Radiation and T-Matrix
   - Part 2: Conical horns
   - Part 3: Multi-segment horns
   - MMM_toolbox source code: https://github.com/bkolbrek/MMM_toolbox

2. **Berzborn, M. & Smithers, M. (2018)**. "An Acoustic Model of the Tapped Horn Loudspeaker." AES Convention Paper 10047.
   - Need to find full paper with equations
   - Check if they show the path interference calculation

3. **Chabassier & Tournemenne (2018)**. "T-matrix methods for wave propagation."
   - literature/transmission_lines/chabassier_tournemenne_2018_tmatrix.md

4. **Danley Patents**
   - US Patent 8,457,341 B2: Check for mathematical formulation
   - Look for equations describing the path combination

## Files to Examine

### GSD Codebase
- `src/gsd/simulation/tapped_horn_theory.py` - Our implementation
- `src/gsd/simulation/horn_theory.py` - T-matrix functions
- `src/gsd/simulation/types.py` - TappedHorn geometry
- `tasks/debug_tapped_horn_comparison.py` - Debug script

### Validation Data
- `imports/th_params.txt` - Hornresp parameters
- `imports/th_sim.txt` - Hornresp simulation results (534 data points)
- `tests/test_tapped_horn_hornresp_validation.py` - Validation tests

### Research Notes
- `TAPPED_HORN_RESEARCH_PLAN.md` - Original research (in root)
- `docs/validation/tapped_horn_phase_implementation.md` - Implementation notes

## Expected Deliverables

### For Research Agent

**SECTION 1: RESEARCH FINDINGS** (for human review)
- Explain correct T-matrix bidirectional propagation
- Show how to calculate round-trip phase shift in exponential horns
- Identify the exact error in our current implementation
- Provide corrected equations with literature citations

**SECTION 2: IMPLEMENTATION INSTRUCTIONS** (for Claude Code)
- File: `src/gsd/simulation/tapped_horn_theory.py`
- Function: `calculate_front_path_pressure_contribution()` (line 271)
- Provide corrected code with:
  - Proper inverse T-matrix for reverse propagation
  - Explicit round-trip phase factor: `exp(-2j × k × L_upstream)`
  - Fixed transmission coefficient calculation
  - Validation steps: Compare with Hornresp after fix

### Acceptance Criteria

After implementing the research agent's fix:
1. SPL deviation < 3 dB across passband (50-200 Hz)
2. Electrical impedance deviation < 15%
3. Correlation coefficient > 0.9 with Hornresp
4. Quarter-wave frequency shows front path cancellation (front contribution << rear)
5. All tests in `test_tapped_horn_hornresp_validation.py` pass

## Handoff Checklist

- [x] Problem clearly identified and documented
- [x] Validation data available (Hornresp exports in `imports/`)
- [x] Debug script created (`tasks/debug_tapped_horn_comparison.py`)
- [x] Research questions formulated
- [x] Literature sources identified
- [x] Expected deliverables specified
- [x] Acceptance criteria defined

## Next Steps

1. **Copy this prompt to clipboard** for research agent
2. **Research agent investigates** correct T-matrix bidirectional propagation and phase accumulation
3. **Research agent provides**:
   - Explanation of the error
   - Corrected equations with citations
   - Implementation instructions for Claude Code
4. **Claude Code implements** the fix
5. **Re-run validation** to confirm < 3 dB accuracy
6. **Document findings** in `docs/validation/`

---

**READY FOR RESEARCH AGENT HANDOFF**
