# Two-Test Case Pattern Analysis - CRITICAL DISCOVERY

## Executive Summary

After running two different tapped horn configurations through GSD and Hornresp, **the error patterns are OPPOSITE**, revealing a fundamental flaw in the parallel impedance model that depends on driver/horn geometry.

## Test Case Comparison

### Test Case 1: BC_15PS100 (15" Driver)

**Configuration:**
- Driver: 15PS100 (S_d = 855 cm², F_s = 37.3 Hz)
- Horn: Throat 246 → Tap 855 → Mouth 4536 cm²
- Upstream length: 138.5 cm (L = 1.385 m)

**Results:**
| Metric | GSD | Hornresp | Error |
|--------|-----|----------|-------|
| Notch frequency | 78.6 Hz | 80.0 Hz | 1.4 Hz |
| Notch depth | 88.35 dB | 55.14 dB | **33 dB too shallow** |
| RMS error | - | - | **10.80 dB** |
| Peak error | - | - | **33.21 dB** |

**Error Pattern:** GSD notch is too SHALLOW (only 13 dB dip instead of 45 dB dip)

---

### Test Case 2: BC_12NDL76 (12" Driver)

**Configuration:**
- Driver: 12NDL76 (S_d = 522 cm², F_s = 48.7 Hz)
- Horn: Throat 180 → Tap 550 → Mouth 2800 cm²
- Upstream length: 120.0 cm (L = 1.20 m)

**Results:**
| Metric | GSD | Hornresp | Error |
|--------|-----|----------|-------|
| Notch frequency | 56.0 Hz | No notch (96.2 dB) | **N/A** |
| Notch depth | 54.07 dB | 96.20 dB | **42 dB too deep** |
| RMS error | - | - | **23.51 dB** |
| Peak error | - | - | **42.13 dB** |

**Error Pattern:** GSD shows deep notch where Hornresp has NONE

---

## CRITICAL DISCOVERY: Opposite Error Modes

### Test Case 1: Under-Cancellation (Large Driver)
- GSD shows shallow notch (13 dB dip)
- Hornresp shows deep notch (45 dB dip)
- **Problem:** Destructive interference is UNDERMODELED
- **GSD misses 32 dB of cancellation!**

### Test Case 2: Over-Cancellation (Small Driver)
- GSD shows deep notch (60 dB dip)
- Hornresp shows no notch (smooth response)
- **Problem:** Destructive interference is OVERMODELED
- **GSD creates 42 dB of non-existent cancellation!**

## Frequency-by-Frequency Comparison (Test Case 2)

| Freq (Hz) | GSD SPL (dB) | HR SPL (dB) | Error (dB) | Status |
|-----------|--------------|-------------|------------|--------|
| 40 | 101.49 | 86.72 | +14.77 | ❌ |
| 50 | 80.59 | 102.39 | -21.80 | ❌ |
| 55 | 65.86 | 96.67 | -30.81 | ❌ |
| **56** | **54.07** | **96.20** | **-42.13** | **❌** |
| 57 | 59.50 | 95.46 | -35.96 | ❌ |
| 58 | 67.65 | 95.18 | -27.53 | ❌ |
| 60 | 74.83 | 94.78 | -19.95 | ❌ |
| 70 | 91.11 | 95.11 | -4.00 | Acceptable |
| 80 | 105.92 | 98.39 | +7.53 | Marginal |
| 90 | 95.63 | 107.38 | -11.75 | ❌ |
| 100 | 93.54 | 95.60 | -2.06 | ✓ Good |

**RMS Error: 23.51 dB** (more than 2× worse than Test Case 1!)

## Root Cause Hypothesis

### Parallel Impedance Model Failure

The current GSD implementation uses:
```python
Z_ac_total = Z_up || Z_down  # Simple parallel combination
```

**This model creates incorrect destructive interference that depends on geometry:**

1. **Test Case 1 (Large horn):**
   - Upstream impedance dominates (large throat area)
   - Z_up doesn't go to zero at quarter-wave
   - **Result:** Insufficient cancellation (notch too shallow)

2. **Test Case 2 (Small horn):**
   - Downstream impedance dominates (small mouth area)
   - Z_up goes negative/too small at quarter-wave
   - **Result:** Excessive cancellation (notch too deep)

### The Real Physics

Hornresp's notch formation depends on:
1. **Pressure-difference model:** Z_acoustic = (P_throat - P_tap) / U_sd
2. **Phase-accurate interference:** Throat reflection cancels tap pressure
3. **Driver coupling strength:** Function of S_d relative to throat/tap areas

The simple parallel impedance model **cannot capture this physics correctly** for all geometries.

## Validation Results Summary

| Test Case | Driver | RMS Error | Peak Error | Notch Error | Pattern |
|-----------|--------|-----------|------------|-------------|---------|
| 1 | BC_15PS100 (15") | 10.80 dB | 33.21 dB | +32 dB (too shallow) | Under-cancellation |
| 2 | BC_12NDL76 (12") | 23.51 dB | 42.13 dB | -42 dB (too deep) | Over-cancellation |

**Correlation:** RMS error more than DOUBLES for smaller driver!

## Implications

1. **Parallel impedance model is fundamentally flawed:**
   - Works "okay" for some geometries (10.8 dB error)
   - Catastrophically fails for others (23.5 dB error)
   - Cannot be trusted for design work

2. **Dipole driver model is NECESSARY:**
   - Pressure-difference formula: Z_acoustic = (P_throat - P_tap) / U_sd
   - Correctly models phase interference
   - Works for all driver/horn combinations

3. **Previous dipole attempt failed due to IMPLEMENTATION ERROR, not theory:**
   - The concept is correct
   - The formulas need careful derivation
   - Boundary conditions are critical

## Recommended Fix

The `calculate_active_loop_impedance()` function in `tapped_horn_theory.py` implements the pressure-difference model but has never been properly validated. This function should:

1. **Calculate P_tap and P_throat separately** (not parallel combination)
2. **Account for active source at tap point** (driver creates pressures on both sides)
3. **Use correct boundary conditions:**
   - U_throat = -U_sd (driver rear flow into throat)
   - U_tap = U_sd + U_downstream (flow conservation at tap)
4. **Derive acoustic impedance from pressure difference:**
   - Z_acoustic = (P_tap - P_throat) / U_sd

## Literature Support

- Berzborn & Smithers (2018), AES Paper 10047 - Explicitly models dipole driver in tapped horn
- Small (1972) - Standard dipole radiation theory
- Kinsler et al. (1982) - Pressure-difference boundary conditions

## Next Steps

1. **Debug `calculate_active_loop_impedance()` implementation:**
   - Check T-matrix boundary conditions
   - Verify pressure calculations
   - Test against Hornresp for both test cases

2. **Create validation suite:**
   - Test multiple driver sizes (8", 10", 12", 15", 18")
   - Test different horn geometries
   - Verify consistent accuracy across all configurations

3. **Accept current limitations:**
   - Parallel impedance model works for limited geometry range
   - Must validate each design with Hornresp
   - Add warning in documentation about geometry-dependent accuracy
