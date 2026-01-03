# Critical Finding: Ported Box SPL Transfer Function Investigation

**Date:** 2025-12-29
**Branch:** `fix/ported-box-spl-transfer-function`
**Status:** **CRITICAL ISSUE** - All approaches produce inverted response shape

## Problem Statement

The ported box SPL transfer function produces a **fundamentally inverted** response compared to Hornresp validation data.

### Hornresp Results (VERIFIED)
- **Peak**: +6.40 dB at **52.5 Hz**
- 53 Hz: +6.23 dB
- 60 Hz: +2.49 dB
- **Behavior**: 53 Hz > 60 Hz by **+3.75 dB** (PEAK then decreases)

### GSD Results (ALL APPROACHES)
- **Peak**: +14 to +29 dB at **60-61 Hz** (wrong frequency!)
- 53 Hz: +0.4 to +21 dB
- 60 Hz: +14 to +29 dB
- **Behavior**: 53 Hz < 60 Hz by **-4 to -8 dB** (monotonic increase)

**Conclusion**: The response shapes are **FUNDAMENTALLY INVERTED**. All approaches produce
monotonic increase from 53→60 Hz, while Hornresp shows a peak at 52.5 Hz then decreases.

## All Approaches Tested

### 1. Original Transfer Function (Small 1973, Eq. 20)
**Form**: `G(s) = s⁴T_B²T_S² / D(s)` where D(s) is 4th-order denominator

**Variations Tested**:
- Q_T = Qts vs Qts/h (2 values)
- s³ coefficient order: T_B²T_S/Q_B + T_BT_S²/Q_T vs swapped (2 arrangements)
- Q_L = 7, 100, 1000, infinity (4 values)

**Result**: ALL 16+ combinations → Peak at 66-73 Hz, monotonic increase 53→60 Hz ✗

### 2. Normalized Transfer Function (Small 1973, Eq. 20-24)
**Form**: `G(s) = s⁴ / (s⁴ + a₁s³ + a₂s² + a₃s + 1)` where s = j·f/f₀

**Coefficients**:
- a₁ = (Q_L + h·Q_T) / (√h · Q_L · Q_T)
- a₂ = (h + (α+1+h²)·Q_L·Q_T) / (h · Q_L · Q_T)
- a₃ = (h·Q_L + Q_T) / (√h · Q_L · Q_T)

**Result**: Peak at 70 Hz, monotonic increase 53→60 Hz by -6.03 dB ✗

### 3. Vector Summation - Impedance Method (Hypothesis 7)
**Form**: P ∝ jω(Ud + Up) where Ud and Up are calculated from impedances

**Driver Impedance**: `Z_driver = s·Mmd + (w0·Mmd)/Qts + 1/(s·Cms) + (BL²/Re)`
**Box Impedance**: `Z_box = 1 / (s·Cab + 1/Z_box_branch)`
**Port Impedance**: `Z_box_branch = s·Map + Ral`

**Variations**:
- Using Qts vs Qms in driver impedance
- Summing (Ud + Up) vs subtracting (Ud - Up)
- Using mechanical vs acoustic impedance formulations

**Result**:
- Sum (Ud + Up): Peak at 59.79 Hz, monotonic increase ✗
- Difference (Ud - Up): Peak at 60.89 Hz, monotonic increase ✗
- Acoustic circuit model: Peak at 60.28 Hz, monotonic increase ✗

### 4. Phase Analysis

**Phase relationships show CORRECT pattern**:
- 52.5 Hz: Phase(Ud) = 13.2°, Phase(Up) = -14.0°, Diff = 27.2° (Constructive)
- 60.0 Hz: Phase(Ud) = 8.4°, Phase(Up) = -77.6°, Diff = 86.0° (Constructive)
- 62.5 Hz: Phase(Ud) = 6.9°, Phase(Up) = -109.7°, Diff = 116.6° (Destructive)

**Issue**: Despite correct phase patterns, magnitudes don't create peak at 52.5 Hz.
The port volume velocity |Up| increases dramatically as we approach Fb (60.3 Hz),
dominating the sum.

**Volume Velocities at 53 Hz**:
- |Ud| = 9.8e-02 (relatively constant with frequency)
- |Up| = 3.77e-01 (increasing toward Fb)
- |Ud + Up| = 4.65e-01

**Volume Velocities at 60 Hz**:
- |Ud| = 9.9e-02
- |Up| = 6.97e-01 (much larger at tuning!)
- |Ud + Up| = 7.11e-01 (maximum at Fb, not at 52.5 Hz)

## Root Cause Analysis

### What We've Ruled Out:
- ✗ Q_T definition (both Qts and Qts/h tested)
- ✗ s³ coefficient order (both arrangements tested)
- ✗ Q_L value (tested from 7 to infinity)
- ✗ Transfer function form (4 different forms tested)
- ✗ Normalization approach (3 different methods)
- ✗ Vector summation approach (sum, difference, impedance-based, transfer function-based)
- ✗ Driver impedance formula (Qts vs Qms, with/without electrical damping)
- ✗ Domain (mechanical vs acoustic impedances)

### What Works:
✓ Phase relationships are correct (constructive below Fb, destructive above)
✓ Diaphragm acceleration peaks at Fs (~70 Hz), as expected
✓ Port volume velocity peaks at Fb (60.3 Hz), as expected

### What Doesn't Work:
✗ **Creating a peak at 52.5 Hz** (all approaches peak at 60-70 Hz)
✗ **Making 53 Hz > 60 Hz** (all approaches show 53 Hz < 60 Hz)
✗ Matching Hornresp's +6.4 dB peak magnitude

## Possible Explanations

### Hypothesis 1: Wrong Transfer Function
Small's Eq. 20 might be for **driver diaphragm acceleration/displacement**, not total SPL.
The port contribution might need to be added differently.

**Evidence against**: Vector summation approach also fails.

### Hypothesis 2: Hornresp Uses Different Model
Hornresp might not use Small/Thiele equations at all. It could use:
- Transmission line model
- T-matrix method
- Numerical simulation of wave equation
- Proprietary algorithm

**Evidence against**: Hornresp documentation cites Small/Thiele.

### Hypothesis 3: Missing Physical Effect
Our model might be missing:
- **Port radiation impedance**: Port radiating into half-space vs free space
- **Driver-port coupling**: Mutual impedance between driver and port
- **Box standing waves**: Internal resonances affecting output
- **Diffraction effects**: Edge diffraction at port and box edges
- **End corrections**: Proper end corrections for port radiation

**Evidence for**: Port impedance models are simplified.

### Hypothesis 4: Parameter Derivation Error
One of our derived parameters might be wrong:
- Cms, Cab, Map calculations
- Qms, Qes, Qts relationships
- Time constant definitions (T_S, T_B)
- Normalization frequency (f₀ = F_S/√h)

**Evidence against**: All parameters verified against Hornresp export file.

### Hypothesis 5: Sign or Convention Error
Possible sign errors in:
- Port velocity direction (inward vs outward)
- Pressure summation (add vs subtract vs different weighting)
- Phase reference (0° vs 180° reference)

**Evidence against**: Tested both addition and subtraction of port velocity.

### Hypothesis 6: Frequency-Dependent Effects
Hornresp might include frequency-dependent effects we're not modeling:
- Voice coil inductance (Le) and its losses
- Semi-inductance (skin effect, proximity effect)
- Frequency-dependent damping
- Thermal compression

**Evidence for**: Hornresp has "Semi-Inductance Model" and "Damping Model" flags.

## Test Case Parameters (BC_8FMB51)

### Driver Parameters
- Fs = 67.12 Hz
- Qts = 0.27497
- Qms = 3.07288
- Qes = 0.30199
- Vas = 20.67 L
- Sd = 227.00 cm²
- BL = 11.30 Tm
- Re = 4.70 Ω
- Mmd = 15.60 g

### Box Parameters
- Vb = 49.3 L
- Fb = 60.3 Hz
- Port: 41.34 cm² × 3.80 cm
- α = 0.4193 (compliance ratio)
- h = 0.8984 (tuning ratio)
- Qp = 9.168 (port Q)

### Hornresp Results (from imports/bookshelf_sim.txt)
```
Freq (Hz)    SPL (dB)
52.540826    100.307587  ← PEAK (MAXIMUM)
53.297652    100.142958
60.618990     96.005538
```

Normalized to passband (~94 dB):
- Peak: +6.40 dB at 52.5 Hz
- 53 Hz: +6.23 dB
- 60 Hz: +2.49 dB
- Difference: +3.75 dB (53 > 60)

## Files Created During Investigation

All test scripts in `tasks/` directory:

1. `diagnose_bc8fmb51_spike.py` - Initial diagnostic confirming 10.1 dB error
2. `debug_transfer_function.py` - Transfer function coefficient analysis
3. `verify_shape_match.py` - Proper comparison with Hornresp normalized
4. `test_lossless_ql.py` - Testing QL = infinity
5. `test_all_tf_combinations.py` - Testing all 16 coefficient combinations
6. `test_verified_equations.py` - Testing "verified" normalized form
7. `complete_equation_chain.py` - Comprehensive documentation of all tests
8. `analyze_phase_relationship.py` - Phase analysis showing correct pattern
9. `debug_vector_sum.py` - Vector summation debug at 53 Hz
10. `test_vector_summation.py` - Full vector summation test
11. `test_corrected_vector_sum.py` - Using Qms instead of Qts
12. `test_subtract_port.py` - Testing (Ud - Up) instead of (Ud + Up)
13. `test_acceleration_transfer_function.py` - Testing diaphragm acceleration only
14. `test_ported_vector_sum_tf.py` - Vector sum with transfer functions
15. `test_acoustic_circuit_model.py` - Pure acoustic circuit model

## Next Steps Required

### Immediate Actions Needed:
1. **Get Small (1973) PDF directly** - Verify equations from original source
2. **Compare with Thiele (1971)** - Thiele might have different/better equations
3. **Check Hornresp source code** - If available, see what algorithm it actually uses
4. **Consult with acoustics expert** - This might require domain expert knowledge
5. **Consider alternative approaches**:
   - Transmission line model
   - T-matrix method
   - Numerical simulation

### Questions for Research:
1. Is Small's Eq. 20 actually the **SPL** transfer function, or is it for something else?
2. How does Hornresp actually calculate ported box SPL? (Not just what it claims)
3. What is the role of port radiation impedance in the total SPL?
4. Are there frequency-dependent effects we're not accounting for?
5. Could there be a sign convention or coordinate system issue?

## Deliverable Needed

We need a Python function that produces:

```python
def ported_box_spl_correct(f, fs, Qts, Vas, Vb, fb, QL=7.0):
    '''
    Calculate ported box SPL using CORRECT equation.

    Parameters (BC_8FMB51 test case):
    - fs = 67.12 Hz, Qts = 0.275, Vas = 20.67 L
    - Vb = 49.3 L, fb = 60.3 Hz

    Expected output (normalized to passband):
    - Peak at ~52-53 Hz
    - Peak level: +6 to +7 dB
    - 53 Hz: +6.23 dB
    - 60 Hz: +2.49 dB
    - Difference: 53 Hz > 60 Hz by +3.75 dB

    Returns:
    - spl_db: SPL in dB (normalized to passband = 0 dB)
    '''
    # TODO: Fill in correct equations
    pass
```

That produces the **CORRECT peaked response** matching Hornresp, not the inverted
monotonic increase we've been getting.

## Conclusion

After exhaustive testing of 15+ approaches across:
- 4 transfer function forms
- 16+ parameter combinations
- 3 impedance formulations
- 2 summation methods (add/subtract)
- Multiple normalization approaches

**ALL PRODUCE THE SAME WRONG RESULT**: Inverted response shape with peak at 60-61 Hz
instead of 52.5 Hz.

This strongly suggests we're either:
1. Using the wrong fundamental equation
2. Missing a critical physical effect
3. Misunderstanding how Hornresp actually works

**This requires deeper investigation beyond standard Small/Thiele equations.**
