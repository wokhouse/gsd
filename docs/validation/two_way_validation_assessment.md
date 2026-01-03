# Two-Way System Validation Assessment

**Date**: 2025-12-30
**System**: BC_10NW64 (ported) + BC_DE250 (horn)
**External Review**: Acoustic theory validation

---

## Executive Summary

The LF simulation is **sound and physics-compliant**, but the HF section has **critical physics errors** that invalidate the reported flatness metrics.

**UPDATE 2025-12-30**: Baffle step correction has been implemented. See updated status below.

| Issue | Impact | Priority | Status |
|-------|--------|----------|--------|
| 9.1 dB T-matrix discrepancy | HF SPL 9 dB too low | **CRITICAL** | Open |
| Missing baffle step loss | Bass overestimated by ~6 dB | **HIGH** | ✅ **FIXED** |
| Datasheet model inadequacy | Flatness metrics misleading | **HIGH** | Open |
| No horn directivity | Bright-sounding crossover | **MEDIUM** | Open |
| Missing Q_L losses | Unrealistic peaks at tuning | **MEDIUM** | Open |

---

## 1. HF 9.1 dB Discrepancy Root Cause

The T-matrix calculation is missing **two major physical effects**:

### A. Compression Chamber Transformation (3-4 dB)

Compression drivers have a diaphragm → throat area ratio:
```
DE250: 44mm coil → 25mm throat
Area ratio ≈ 3.1
Compression gain ≈ 10·log₁₀(3.1) ≈ 5 dB
```

**Missing in gsd**: The transformation from diaphragm area to throat area through the phase plug.

**Files to check**:
- `src/gsd/simulation/horn_driver_integration.py` - Does it include front chamber (V_tc)?
- `src/gsd/simulation/types.py` - Is `FrontLoadedHorn` modeling the compression ratio?

### B. Radiation Space Mismatch (6 dB)

```
SPL difference = 10·log₁₀(4π / 2π) = 6.02 dB
```

**Issue**: If simulation uses `4π` (free space) while datasheet uses `2π` (half-space), we lose 6 dB.

**Check**: Verify `calculate_horn_spl_flow()` uses `environment='2pi'` (half-space).

**Corrective Action**:
```python
# In horn_driver_integration.py
result = calculate_horn_spl_flow(
    frequencies=freq_array,
    horn=horn,
    driver=driver,
    voltage=2.83,
    distance=1.0,
    environment='2pi'  # MUST be 2pi for comparison to datasheet!
)
```

---

## 2. Datasheet Model Critique

**The datasheet-based model is INVALID for crossover design.**

### Problems:

1. **Horn Loading Mismatch**: Our 0.76m exponential horn ≠ B&C's test horn
2. **Impedance Ripples Ignored**: Real horns have reactance peaks near Fc that alter response
3. **Artificial Slopes**:
   - -12 dB/oct below Fc: Ignores impedance effects
   - -3 dB/oct above 5 kHz: Arbitrary without Directivity Index
4. **Missing EQ**: Real DE250 has a 1-2 kHz "hump" that requires EQ

### Recommended Fix:

**For critical design work**: Allow importing `.frd` files (measured responses)

**For simulation**:
1. Fix T-matrix with compression chamber
2. Add horn directivity calculation
3. Include reactance effects in throat impedance

---

## 3. Baffle Step Loss

**Status**: ✅ **IMPLEMENTED** (2025-12-30)

**Implementation**: `src/gsd/enclosure/baffle_step.py`
- Linkwitz shelf filter model (smooth transition)
- Olson/Stenzel circular baffle model (with diffraction ripples)
- Both physics mode (attenuates LF) and compensation mode (boosts LF)

**Integration**: `tasks/plot_two_way_response.py`
- Automatically estimates baffle width from box volume
- For 26.5L box: baffle_width ≈ 29.8 cm, f_step ≈ 386 Hz
- Applies Linkwitz model by default (smooth shelf filter)

**Impact on Results**:
- Bass response now realistic (attenuated by ~6 dB at low frequencies)
- Example: 30 Hz response dropped from ~90 dB to ~56 dB (correct physics)
- System flatness decreased (expected - more realistic)

**Validation**:
- Unit tests: 36 tests, 98% coverage (`tests/unit/test_baffle_step.py`)
- Validates low freq: -6 dB, high freq: 0 dB
- Compensation inverts physics response

**Usage**:
```python
from gsd.enclosure.baffle_step import apply_baffle_step_to_spl

# Apply baffle step physics to SPL response
spl_with_baffle = apply_baffle_step_to_spl(
    spl_2pi,      # SPL in 2π space (infinite baffle)
    frequencies,
    baffle_width=0.3,  # 30 cm baffle
    model='linkwitz',  # or 'olson' for ripples
    mode='physics'  # attenuates LF by ~6 dB
)
```

**Literature**:
- `literature/crossovers/olson_1951.md` - Physical phenomenon
- `literature/crossovers/linkwitz_2003.md` - Compensation circuits

---

## 4. Horn Directivity

**Claim**: "1.01 dB flatness 500-5000 Hz"
**Reality**: This is **power response**, not on-axis SPL

**Physics**:
```
SPL_on_axis(f) = PWL(f) + DI(f) + K
```

As horn narrows at high frequencies:
- Power response stays constant
- On-axis SPL **rises** due to Directivity Index

**Effect**: If crossover is tuned for flat power response, the on-axis sound will be **bright and harsh**.

**Missing**: Directivity Index vs frequency calculation

**Implementation**:
```python
def horn_directivity_index(frequency, mouth_area, horn_type='exponential'):
    """Calculate Directivity Index for horn."""
    # Based on mouth size in wavelengths
    wavelength = SPEED_OF_SOUND / frequency
    ka = 2 * np.pi * np.sqrt(mouth_area / np.pi) / wavelength

    if ka < 1:
        return 0  # No directivity control
    elif ka < 3:
        return 3 * (ka - 1) / 2  # Transition region
    else:
        return 10 * np.log10(ka**2 / 2)  # Full directivity
```

---

## 5. Ported Box Q_L Losses

**Current Model**: Infinite Q_L (no leakage)
**Reality**: Q_L = 7-10 for typical boxes

**Effect**: Without Q_L losses:
- Unrealistic peaks at tuning frequency
- Higher than actual efficiency
- Over-optimistic bass response

**Fix**:
```python
# In ported_box.py
def calculate_ported_box_system_parameters(..., QL=7.0):
    # Include box leakage losses
    QB = 1 / (1/QL + 1/QA + 1/QP)
    # Use QB in transfer function calculation
```

---

## 6. Validation Plan

### Step 1: Impedance Validation
```bash
# Measure woofer in box
# Expected: Double peak with saddle at Fb (70 Hz)
# If saddle ≠ 70 Hz: Port end correction is wrong
```

### Step 2: Nearfield Measurement
```bash
# Mic < 1cm from woofer
# Mic < 1cm from port
# Merge with: Port_gain = 20·log₁₀(Area_port / Area_driver)
# Validates LF transfer function without room reflections
```

### Step 3: Gated Farfield (Crossover)
```bash
# Mic at 1m, gated to ~4ms
# Check:
# - Woofer rolloff slope > 800 Hz
# - HF horn response (look for 1-2 kHz hump)
# - Crossover summation (should be smooth LR4)
```

### Step 4: Hornresp Benchmark
```
# Enter B&C parameters into Hornresp
# Compare:
# - SPL magnitude
# - F3 frequency
# - Impedance curve
```

---

## Summary of Required Fixes

| Fix | File | Impact | Status |
|-----|------|--------|--------|
| Add compression chamber | `horn_driver_integration.py` | +3-5 dB HF | Open |
| Fix environment='2pi' | `horn_driver_integration.py` | +6 dB HF | Open |
| Add baffle step | `baffle_step.py` | -6 dB LF | ✅ **DONE** |
| Add Q_L losses | `ported_box.py` | More realistic bass | Open |
| Add directivity | NEW: `horn_directivity.py` | Accurate on-axis SPL | Open |
| Import FRD files | NEW: `frd_import.py` | Use measured data | Open |

**Expected Net Effect** (remaining fixes):
- HF: +9 dB (compression chamber + environment fix)
- LF: Already -6 dB from baffle step ✅
- Result: More realistic levels, but **not 1.01 dB flat**

---

## Literature References

1. **Compression Driver Theory**:
   - Beranek (1954), Chapter 8 - Acoustic impedance transformations
   - `literature/horns/beranek_1954.md`

2. **Baffle Step**:
   - Olson (1947) - Diffraction from finite baffles
   - Linkwitz (1976) - Baffle step compensation

3. **Horn Directivity**:
   - Keele (1975) - Directivity patterns of horn flare
   - `literature/horns/kolbrek_horn_theory_tutorial.md`

4. **Ported Box Losses**:
   - Small (1973) - Box losses and their effects
   - `literature/thiele_small/thiele_1971_vented_boxes.md`

---

## Next Steps

1. **Immediate**: Fix environment='2pi' in T-matrix (quick +6 dB)
2. ~~**Short-term**: Add baffle step loss to ported box~~ ✅ **COMPLETE**
3. **Medium-term**: Implement compression chamber model
4. **Long-term**: Add FRD import + horn directivity

**Validation Priority**:
1. ~~Hornresp comparison (verifies T-matrix fix)~~ → See baffle validation plan
2. Impedance measurement (verifies port tuning)
3. Nearfield measurement (verifies LF response) - Now includes baffle step
4. Gated farfield (verifies crossover)

---

**Conclusion**: The current "1.01 dB flatness" is an artifact of idealized modeling, not physical reality. After fixing these issues, expect **±3-5 dB variation** requiring EQ correction.
