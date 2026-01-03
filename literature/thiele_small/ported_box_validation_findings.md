# Ported Box Validation Findings - BC_15DS115 B4 Alignment

**Date:** 2025-12-27
**Driver:** B&C 15DS115
**Alignment:** B4 (Vb=Vas=253.7L, Fb=Fs=33Hz)

## Validation Results

### Impedance Comparison

| Frequency (Hz) | Hornresp Ze (Ω) | GSD Circuit (Ω) | GSD Small (Ω) | Error (Circuit) |
|----------------|-----------------|---------------------|--------------------|------------------|
| 20             | 139.0           | 100.3               | 151.3              | -28%            |
| 30             | 5.5             | 43.2                | 130.2              | +686%           |
| 33 (Fb)        | 14.1            | 41.9                | 107.2              | +197%           |
| 40             | 46.0            | 90.5                | 144.1              | +97%            |
| 50             | 119.2           | 154.1               | 150.7              | +29%            |
| 100            | 38.6            | 54.8                | 150.7              | +42%            |

**Observations:**
- **Circuit model**: Better qualitative behavior (shows dip at Fb), but quantitative errors are large
- **Small model**: Completely broken - flat ~150 Ω across frequency
- **Root cause**: `ported_box_impedance_small()` transfer function doesn't work for this driver

### SPL Comparison

| Frequency (Hz) | Hornresp SPL (dB) | GSD SPL (dB) | Difference (dB) |
|----------------|-------------------|-------------------|-----------------|
| 20             | 75.3              | 98.2              | +22.9           |
| 30             | 103.2             | 93.7              | -9.5            |
| 33 (Fb)        | 96.2              | 90.7              | -5.5            |
| 40             | 90.3              | 91.7              | +1.4            |
| 50             | 89.1              | 90.2              | +1.1            |
| 70             | 90.0              | 87.3              | -2.7            |
| 100            | 92.3              | 84.3              | -8.0            |
| 150            | 95.9              | 80.7              | -15.2           |
| 200            | 99.5              | 77.7              | -21.8           |

**Statistics:**
- Mean difference: -3.84 dB
- Standard deviation: 10.50 dB
- Max absolute error: 22.87 dB

**Overall status: ❌ FAIL** - Significant deviations from Hornresp

## Root Cause Analysis

### Issue 1: Efficiency Formula is Fundamentally Broken

**Location:** `src/gsd/enclosure/ported_box.py:664`

```python
eta_0 = (air_density / (2 * math.pi * speed_of_sound)) * \
        ((4 * math.pi ** 2 * driver.F_s ** 3 * driver.V_as) / driver.Q_es)
```

**Problem:** This formula gives η₀ = 3122 (312,255% efficiency), which is physically impossible!

**Expected:** Efficiency should be 0.001-0.1 (0.1-10%) for typical drivers.

**Why it still gives reasonable SPL:**
There's a compensating error in the SPL calculation formula that happens to cancel out the wrong efficiency value. But the underlying physics is wrong.

### Issue 2: Transfer Function Roll-off at High Frequencies

**Location:** `src/gsd/enclosure/ported_box.py:509` (`calculate_spl_ported_transfer_function`)

**Transfer function values observed:**
- 20 Hz: -19.72 dB (too high)
- 33 Hz (Fb): -27.18 dB
- 40 Hz: -26.17 dB
- 100 Hz: -33.73 dB
- 200 Hz: -39.69 dB (too low!)

**Expected behavior:**
The transfer function should approach 0 dB at high frequencies (well above Fb), not continue rolling off.

**Root cause:** The denominator polynomial D'(s) is not correctly normalized, causing excessive roll-off.

### Issue 3: Small's Impedance Model Doesn't Work for High-BL Drivers

**Location:** `src/gsd/enclosure/ported_box.py:704` (`ported_box_impedance_small`)

**Problem:** For the BC_15DS115 driver (Qes=0.06, BL=38.7 T·m), the impedance model produces a flat ~150 Ω across frequency, completely missing the dual-peak pattern.

**Possible causes:**
1. Extreme driver parameters (Qes=0.06 is very low)
2. Numerical precision issues in polynomial coefficients
3. Transfer function formulation doesn't account for high-BL effects

**Workaround:** Use circuit model (`impedance_model="circuit"`) which shows better qualitative behavior.

## Driver-Specific Issues

The BC_15DS115 is an **extreme driver** with:
- Qes = 0.06 (very low electrical Q)
- BL = 38.7 T·m (very high force factor)
- Vas = 253.7 L (very large compliance)
- Designed for large ported boxes (B4 alignment: 254L)

These extreme parameters may be outside the valid range of Small's transfer function assumptions. The theory was developed for typical drivers with Qes > 0.2.

## Recommendations

### Immediate Actions

1. **Fix efficiency formula**:
   - Research correct Small (1972) efficiency formula
   - Add proper unit conversions
   - Validate that η₀ < 1 for all drivers

2. **Debug transfer function**:
   - Check denominator polynomial normalization
   - Verify transfer function approaches 0 dB at high frequencies
   - May need to reformulate for extreme Qes values

3. **For this specific driver**:
   - Use circuit model for impedance (not Small's transfer function)
   - Add validation warning for drivers with Qes < 0.1
   - Consider empirical correction for high-BL drivers

### Long-term Fixes

1. **Reimplement Small's transfer function**:
   - Start from Small (1973) original equations
   - Verify with typical drivers first (Qes > 0.2)
   - Then extend to extreme drivers

2. **Add parameter range validation**:
   - Warn users when driver parameters are outside validated range
   - Provide alternative models for extreme drivers

3. **Improve calibration**:
   - Current -25.25 dB offset was calibrated for BC_8NDL51 (Qes=0.39)
   - May need driver-specific calibration offsets
   - Or implement physics-based correction

## Validation Status

- **Impedance (Circuit model)**: ⚠️ PARTIAL - Qualitatively correct, quantitatively poor
- **Impedance (Small model)**: ❌ FAIL - Completely broken for this driver
- **SPL (Transfer function)**: ❌ FAIL - Wrong frequency dependence
- **Overall**: ❌ FAIL - Not ready for production use

## Files Created During Investigation

- `tasks/validate_bc15ds115_b4_vs_hornresp.py` - Main validation script
- `tasks/diagnose_ported_impedance.py` - Impedance diagnostic
- `tasks/debug_transfer_function.py` - Transfer function debug
- `tasks/debug_spl_transfer_function.py` - SPL transfer function debug
- `tasks/debug_efficiency_calculation.py` - Efficiency calculation debug
- `tasks/ported_box_validation_findings.md` - This file

## Next Steps

1. Fix efficiency formula in `ported_box.py`
2. Debug and fix transfer function high-frequency roll-off
3. Re-validate after fixes
4. Consider adding empirical corrections for extreme drivers
