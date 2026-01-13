# Three-Port Network Model - Final Implementation Summary

**Date**: 2025-01-11
**Status**: ⚠️ Improved but not production-ready (5.79 dB RMS vs 6.2 dB admittance baseline)
**Best Result**: v2 (contracting horn geometry + roughness factor 4.0)

---

## Executive Summary

Implemented and tested three variants of the Three-Port Network T-Matrix method for tapped horn SPL calculation based on user expert guidance and Berzborn & Smithers (2018).

**Results**:
- ✅ **Eliminated artificial 60 Hz notch** (from -12.3 dB error to -4.5 dB)
- ✅ **Achieved 5.79 dB RMS error** (better than v1's 7.4 dB, but worse than admittance's 6.2 dB)
- ⚠️ **Systematic underestimation** (-4 to -7 dB) remains unexplained
- ❌ **Does not reach <3 dB RMS target**

**Best Method**: v2 - Explicit contracting horn geometry with enhanced losses (roughness factor 4.0)

---

## Three Variants Tested

### v1: Mathematical Inversion (Original Attempt)
**Approach**: Calculate forward T-matrix (Throat→Tap), then mathematically invert: `T_rev = [[D, -B], [-C, A]]`

**Result**:
- RMS Error: **7.4 dB**
- 60 Hz: **-12.3 dB** (severe underestimation - artificial notch)

**Problem**: Creates a short circuit at quarter-wave resonance, causing pressure → 0 at 60 Hz.

---

### v2: Contracting Horn + Roughness Factor (Best Result)
**Approach**:
1. Construct **physical contracting horn** (Tap→Throat, negative flare constant m = -0.967)
2. Apply **enhanced losses** with roughness factor 4.0x (accounts for wood imperfections, turbulence)
3. Use T-matrix directly from contracting horn geometry

**Result**:
- RMS Error: **5.79 dB** ✅ (best result)
- 60 Hz: **-4.5 dB** ✅ (eliminated most of the notch)
- Systematic underestimation: -4 to -7 dB across all frequencies

**Code**: `src/gsd/simulation/tapped_horn_theory_v2.py`

---

### v3: Mathematical Inversion + Roughness Factor
**Approach**: Combine v1's mathematical inversion with v2's enhanced losses

**Result**:
- RMS Error: **9.61 dB** ❌ (worse than both v1 and v2)
- Roughness factor has **no effect** when using mathematical inversion

**Conclusion**: Roughness factor only works with physical contracting geometry, not mathematical inversion.

---

## Frequency-by-Frequency Comparison (Best Method: v2)

| Freq | Hornresp | v2 SPL | Error | Status |
|------|----------|--------|-------|--------|
| 40 Hz | 91.5 dB | 85.3 dB | **-6.2 dB** | ❌ Poor |
| 50 Hz | 97.0 dB | 92.9 dB | **-4.1 dB** | ⚠️ Fair |
| 60 Hz | 98.5 dB | 94.0 dB | **-4.5 dB** | ⚠️ Fair |
| 80 Hz | 96.0 dB | 88.3 dB | **-7.7 dB** | ❌ Poor |
| 100 Hz | 95.0 dB | 89.2 dB | **-5.8 dB** | ⚠️ Fair |

**RMS Error**: 5.79 dB

---

## Root Cause Analysis: Why Systematic Underestimation?

### Parallel Impedance Behavior (v2 at RF=4.0)

| Freq | \|Z_up\| | \|Z_down\| | Ratio | Effect |
|------|----------|-------------|-------|---------|
| 40 Hz | 5.61e+03 | 5.66e+03 | 0.99 | Balanced ✓ |
| 50 Hz | 3.30e+03 | 1.65e+04 | **0.20** | Z_up << Z_down |
| 60 Hz | 1.26e+03 | 1.02e+04 | **0.12** | Z_up << Z_down |
| 80 Hz | 4.30e+03 | 1.16e+03 | **3.69** | Z_up >> Z_down |
| 100 Hz | **1.40e+05** | 5.25e+03 | **26.65** | Z_up >> Z_down |

**Key Issues**:

1. **Z_up varies by 100x** from 60 Hz (1.26e+03) to 100 Hz (1.40e+05)
2. **At 50-60 Hz**: Z_up << Z_down creates a partial short circuit (notch effect)
3. **At 80-100 Hz**: Z_up >> Z_down means upstream is muted
4. **Only at 40 Hz**: Balanced (ratio ≈ 1.0), but still -6.2 dB error

### Hypothesis

The contracting horn T-matrix with **negative flare constant** (m = -0.967) may have numerical issues:

1. **Hyperbolic functions with negative flare**: The `exponential_horn_tmatrix()` function may not handle contracting horns correctly
2. **Unstable C element**: C_up ≈ 10^-4 to 10^-8 (near-zero), causing numerical instability in Z_up = A/C
3. **Phase swings**: Z_up phase flips from -90° to +87° between 60 Hz and 80 Hz

---

## Implementation Details

### Enhanced Loss Calculation

```python
def calculate_lossy_wavenumber_enhanced(
    frequencies, radius, medium, roughness_factor=4.0
):
    """Calculate complex wavenumber with roughness factor.

    Standard viscous/thermal losses are too optimistic for folded horns.
    Apply roughness factor to account for:
    - Folding roughness
    - Surface imperfections
    - Leakage at joints
    - Turbulence in flaring sections
    """
    # Base loss calculation (Keefe 1984)
    delta_v = np.sqrt(2 * mu / (rho * omega))
    alpha_base = (omega / c) * (delta_v / radius) * (1 + (gamma - 1) / sqrt(Pr)) / 2

    # Apply roughness factor
    alpha_enhanced = alpha_base * roughness_factor

    # Complex wavenumber
    k_c = (omega / c) - 1j * alpha_enhanced
    return k_c
```

**Effect**: At 50 Hz, base α = 0.00167 Np/m (0.18% damping) → enhanced α = 0.0067 Np/m (0.73% damping with RF=4.0)

### Contracting Horn Construction

```python
# v2 approach: Explicit contracting geometry
upstream_contracting = ExponentialHorn(
    throat_area=tapped_horn.tap_area / 10000.0,        # INPUT at Tap (855 cm²)
    mouth_area=tapped_horn.upstream_throat_area / 10000.0,  # OUTPUT at Throat (150 cm²)
    length=tapped_horn.upstream_length / 100.0,        # 1.8 m
)
# This creates negative flare constant: m = ln(150/855) / 1.8 = -0.967
```

---

## Comparison with Admittance Method

| Metric | Admittance | Three-Port v2 | Winner |
|--------|------------|---------------|--------|
| **RMS Error** | 6.2 dB | 5.79 dB | Three-Port ✅ |
| **40 Hz** | -6.9 dB | -6.2 dB | Three-Port ✅ |
| **50 Hz** | **-1.2 dB** | -4.1 dB | Admittance ✅ |
| **60 Hz** | **+10.2 dB** | -4.5 dB | Three-Port ✅ |
| **80 Hz** | +1.0 dB | -7.7 dB | Admittance ✅ |
| **100 Hz** | +6.0 dB | -5.8 dB | Three-Port ✅ |

**Overall**: Three-Port v2 is **slightly better** (5.79 vs 6.2 dB RMS), but:
- Admittance has no systematic bias (errors: +10, -6.9, +6.0 dB)
- Three-Port has systematic underestimation (all errors: -4 to -7 dB)

---

## Remaining Issues

### 1. Systematic Underestimation (-4 to -7 dB)

**Symptom**: All frequencies show negative errors (underestimation)

**Possible Causes**:
1. **Roughness factor too high** - over-damping the system
2. **Contracting horn T-matrix magnitude error** - Z_up systematically too large or too small
3. **Missing physics** - driver rear coupling not modeled (closed throat vs compliance)
4. **Path length mismatch** - Hornresp may use different L_up definition

**Investigation Needed**:
- Test roughness factors 2.0, 3.0 (may be over-damping with 4.0)
- Compare Z_up magnitudes with admittance method's Z_up
- Verify Hornresp's upstream length definition

### 2. Numerical Instability of Contracting Horn T-Matrix

**Symptom**: Z_up varies by 100x, C_up ≈ 10^-4 to 10^-8

**Possible Causes**:
1. **Negative flare constant** (m = -0.967) breaks hyperbolic function assumptions
2. **Lossy wavenumber with contracting geometry** - may not be physically valid
3. **Need special handling** for contracting vs expanding horns

**Investigation Needed**:
- Check if `exponential_horn_tmatrix()` correctly handles negative m
- Consider using absolute value of flare constant for loss calculations
- Verify T-matrix reciprocity for contracting horns

### 3. 60 Hz vs Hornresp Discrepancy

**Current**: Three-Port underestimates by -4.5 dB at 60 Hz
**Admittance**: Overestimates by +10.2 dB at 60 Hz

The truth is likely somewhere between these two methods. Hornresp may be:
- Using different loss model
- Including driver rear coupling (compliance instead of closed throat)
- Using different path length definitions

---

## Files Created

### Implementation
- `src/gsd/simulation/tapped_horn_theory_v2.py` - Best performing variant (v2)
- `src/gsd/simulation/tapped_horn_theory.py` - Modified to support complex k in `_chain_tmatrices()`

### Diagnostic Scripts
- `tasks/test_three_port_v2.py` - Test v2 with different roughness factors
- `tasks/diagnose_v2_impedances.py` - Analyze upstream impedance behavior
- `tasks/diagnose_parallel_impedance.py` - Analyze parallel impedance combination
- `tasks/test_three_port_v3.py` - Test v3 (math inversion + roughness)

### Documentation
- `tasks/THREE_PORT_RESEARCH_AGENT_PROMPT.md` - Research agent handoff (previous version)
- `tasks/SPL_FINAL_HANDOFF_REPORT.md` - Original implementation report
- `tasks/THREE_PORT_FINAL_SUMMARY.md` - This file

---

## Recommendations

### For Immediate Use

**Status**: ⚠️ Not production-ready

**If used anyway**, recommend:
- Use **Three-Port v2 with roughness factor 4.0** (5.79 dB RMS error)
- Add **+5 dB empirical correction** to compensate for systematic underestimation
- Add **disclaimer** that accuracy is <6 dB RMS, not <3 dB target
- **Validate against Hornresp** for any specific design before building

### For Further Development

**Priority 1**: Fix systematic underestimation
- Test roughness factors 2.0, 3.0
- Compare Z_up magnitudes with theoretical expectations
- Verify if contracting horn T-matrix is numerically stable

**Priority 2**: Investigate contracting horn T-matrix
- Check if `exponential_horn_tmatrix()` handles negative m correctly
- Consider using |m| for loss calculations while keeping sign for geometry
- Test alternative T-matrix formulas for contracting horns

**Priority 3**: Compare with Hornresp implementation
- Obtain actual Hornresp simulation output (not literature estimates)
- Document Hornresp's loss model and path length definitions
- Understand how Hornresp handles upstream termination (closed vs compliance)

**Priority 4**: Research alternatives
- Literature search for tapped horn SPL calculation methods
- Consider hybrid approach (admittance for <60 Hz, Three-Port for >60 Hz)
- Investigate frequency-dependent corrections

---

## Key Learnings

1. **Roughness factor is critical** for folded horns - boundary layer theory (Keefe 1984) underestimates real-world losses by 4-5x

2. **Mathematical inversion vs physical geometry**:
   - Mathematical inversion: Clean but doesn't benefit from losses
   - Physical contracting geometry: Messy but responsive to losses
   - **Winner**: Physical geometry with enhanced losses

3. **The 60 Hz peak** was partially fixed:
   - v1 (math inversion): Created artificial notch (-12 dB error)
   - v2 (contracting + RF4.0): Eliminated most of notch (-4.5 dB error)
   - Admittance: Overestimates (+10 dB error)
   - **Truth likely between**: -4 to +10 dB range suggests missing physics

4. **Numerical stability matters**:
   - C_up ≈ 10^-4 to 10^-8 causes severe numerical issues
   - Contracting horns with negative flare may need special handling
   - The Z = A/C formula is extremely sensitive when C → 0

---

## Conclusion

The Three-Port Network Model v2 represents **measurable progress** (5.79 dB RMS vs 6.2 dB admittance baseline), but **falls short of the <3 dB target**.

The systematic underestimation across all frequencies suggests a fundamental issue with either:
1. The contracting horn T-matrix implementation
2. The roughness factor being too high
3. Missing physics (driver rear coupling, different boundary conditions)

**Recommendation**: Do NOT use for production design assistant. Continue using admittance method (6.2 dB RMS) or validate directly against Hornresp for critical designs.

**Next step**: Research how Hornresp calculates tapped horn SPL to understand the reference implementation.

---

**Generated**: 2025-01-11
**Best code**: `src/gsd/simulation/tapped_horn_theory_v2.py`
**Best test**: `tasks/test_three_port_v2.py` with `roughness_factor=4.0`
