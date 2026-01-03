# Ported Box Impedance Calculation Bug Fixes

## Date
2025-12-27

## Issue
Validation against Hornresp simulation data for BC_15DS115 ported box revealed significant discrepancies in electrical impedance and SPL calculations.

## Validation Results

### Before Fixes
- **Electrical impedance peaks**: ~30 Ω (gsd) vs 143-151 Ω (Hornresp) - **4-5× error**
- **SPL error**: 6-16 dB too low across frequency range
- **Overall assessment**: POOR - significant differences

### After Fixes
- **Peak 1 impedance**: 128 Ω vs 151 Ω (15% error)
- **Peak 2 impedance**: 137 Ω vs 143 Ω (4% error)
- **SPL (30-1000 Hz)**: ±1-2 dB error
- **SPL (<30 Hz)**: 7-13 dB error (port contribution not included)

## Root Causes

### Bug 1: Incorrect R_es Calculation (Line 607)

**Location**: `src/gsd/enclosure/ported_box.py:607`

**Problem**:
```python
# WRONG - Extra R_e in denominator
R_es = (driver.BL ** 2) / (driver.R_e * R_ms)
```

The formula incorrectly included R_e in the denominator, which divided the motional impedance by an extra factor of R_e (typically 4-8 Ω), causing a 4-5× underestimate of impedance peaks.

**Correct Formula**:
```python
# CORRECT - Reflected mechanical impedance: Z_m → Z_e
R_es = (driver.BL ** 2) / R_ms
```

**Literature**:
- COMSOL (2020), Figure 2 - Reflected impedance: Z_reflected = (BL)² / Z_m
- Small (1973) - Motional impedance in electrical domain

**Impact**:
- Peak impedance underestimated by factor of 4.4×
- Expected peak at resonance: Z_max = R_e + (BL)²/R_ms = 4.9 + 1497.7/10.15 = 152.5 Ω
- Calculated with bug: Z_max = R_e + R_es_wrong = 4.9 + 30.1 = 35.0 Ω

### Bug 2: Incorrect Diaphragm Velocity Calculation (Lines 963, 1109)

**Location**: `src/gsd/enclosure/ported_box.py:963, 1109`

**Problem**:
```python
# WRONG - Using only in-phase current component
I_complex = voltage / Ze
I_phase = cmath.phase(I_complex)
I_active = abs(I_complex) * math.cos(I_phase)
F_active = driver.BL * I_active
u_diaphragm_mag = F_active / abs(Z_mechanical_total)
```

The code used only the in-phase component of the current (I_active), which underestimated the force when the current had significant phase angle (common away from resonance).

**Correct Formula**:
```python
# CORRECT - Use current magnitude
I_complex = voltage / Ze
I_mag = abs(I_complex)
F_mag = driver.BL * I_mag
u_diaphragm_mag = F_mag / abs(Z_mechanical_total)
```

**Literature**:
- COMSOL (2020), Figure 2 - Force and velocity relationship
- F = BL × I (use magnitude, not just in-phase component)

**Impact**:
- Diaphragm velocity underestimated by 2.6× at 100 Hz
- SPL underestimated by 6-16 dB across frequency range
- Error was worst away from resonance where current phase angle is largest

## Validation Test Case

**Driver**: BC_15DS115 (15" subwoofer)
**Design**: Vb=126.9L, Fb=23Hz, Ap=178.3cm², Lpt=72.8cm
**Reference**: Hornresp simulation exports/15ds115_sim.txt

### Key Results at 100 Hz

| Parameter | Hornresp | GSD (Fixed) | Error |
|-----------|----------|------------------|-------|
| Impedance | 45.8 Ω | 36.3 Ω | 21% |
| SPL | 92.2 dB | 91.6 dB | 0.6 dB |

### Impedance Peaks

| Peak | Hornresp | GSD (Fixed) | Error |
|------|----------|------------------|-------|
| Lower (12.2 Hz) | 151.4 Ω | 127.9 Ω | 15% |
| Upper (64.2 Hz) | 143.3 Ω | 137.3 Ω | 4% |

## Known Limitations

1. **Port contribution to SPL**: Current implementation calculates diaphragm SPL only. The port's contribution to total acoustic output is not included, causing 7-13 dB error at very low frequencies (<30 Hz). This is documented in the code as a Phase 2 feature.

2. **BC_15DS115 datasheet inconsistency**: The driver's datasheet contains incompatible T/S parameters:
   - Mms=254g, Fs=33Hz, Cms=0.25mm/N cannot all be true simultaneously
   - Current implementation prioritizes Fs and Cms, giving M_ms=93g and Vas=254L
   - This affects Q values: Qts=0.061 (calculated) vs 0.17 (datasheet)

3. **Mean impedance error**: While peak errors are good (4-15%), the mean error across all frequencies (16.3%) is higher. This is likely due to differences in impedance away from resonance peaks.

## Testing

Run validation:
```bash
PYTHONPATH=src python3 validate_hornresp_15ds115.py
```

Expected results:
- F3: 10.0 Hz (matches Hornresp exactly)
- Impedance peaks within 15% of Hornresp
- SPL within ±2 dB for 30-1000 Hz
- SPL error 7-13 dB for <30 Hz (known limitation)

## Files Modified

- `src/gsd/enclosure/ported_box.py`:
  - Line 607: Fixed R_es calculation
  - Lines 958-966: Fixed diaphragm velocity (Small model)
  - Lines 1105-1112: Fixed diaphragm velocity (circuit model)

## References

- Hornresp: http://www.hornresp.net/
- Small, R. H. (1973). "Vented-Box Loudspeaker Systems Part I", JAES
- Thiele, A. N. (1971). "Loudspeakers in Vented Boxes", JAES
- COMSOL (2020). "Lumped Loudspeaker Driver Model"
- Kinsler et al. (1982). "Fundamentals of Acoustics"
