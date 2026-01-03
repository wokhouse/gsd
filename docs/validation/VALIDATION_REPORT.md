# Horn Optimization Validation Report

**Date:** 2025-12-28
**Design:** TC2 Optimized Horn #3
**Driver:** TC2 (compression driver, Fs=251 Hz)

---

## Design Parameters

| Parameter | Value |
|-----------|-------|
| Throat area | 3.23 mm² |
| Mouth area | 174.17 cm² |
| Length | 266 cm |
| Cutoff frequency (Fc) | 279.7 Hz |
| Optimized flatness | 0.81 dB |
| Volume | 3.34 L |

---

## Hornresp Validation Results

### Frequency Response Flatness

| Frequency Range | Hornresp Std Dev | Peak-to-Peak | Rating |
|-----------------|------------------|--------------|--------|
| 420-500 Hz (optimization range) | 1.48 dB | 4.70 dB | Fair |
| **500-5000 Hz (full passband)** | **5.81 dB** | **29.39 dB** | **Poor** |
| 500-1000 Hz | 3.66 dB | 12.41 dB | Fair |
| 1000-2000 Hz | 2.35 dB | 9.64 dB | Good |
| 2000-4000 Hz | 2.58 dB | 10.64 dB | Good |

### Critical Finding

**DISCREPANCY:** Optimization predicted 0.81 dB flatness, but Hornresp shows:
- 1.48 dB in optimization range (420-500 Hz) - 0.67 dB error
- **5.81 dB in full passband (500-5000 Hz) - 5.0 dB error**

### Root Cause Analysis

The optimization uses an **inappropriate frequency range** for midrange horns:

```python
# From objective_response_flatness() line 118-119:
frequency_range: Tuple[float, float] = (20.0, 500.0)  # Default

# For exponential horns (line 191):
f_min = max(frequency_range[0], fc * 1.5)
# For Fc = 279.7 Hz: f_min = max(20, 419.5) = 419.5 Hz
# Actual range: 419.5 - 500 Hz (only 80 Hz!)
```

**Problems:**
1. Range (20, 500) Hz designed for woofers, not midrange horns
2. `Fc * 1.5` constraint pushes start frequency to 420 Hz
3. **Only evaluates 80 Hz bandwidth**, missing 4500 Hz of actual passband
4. Cannot detect response variations above 500 Hz

---

## Design Performance Assessment

### Strengths
- Good flatness in 1-2 kHz range (2.35 dB)
- Acceptable flatness in 2-4 kHz range (2.58 dB)
- Cutoff frequency close to prediction (279.7 Hz → 305 Hz measured, 25 Hz error)

### Weaknesses
- **Poor overall passband flatness** (5.81 dB std dev, 29.4 dB p2p)
- Significant SPL rolloff above 2 kHz
- Large peak at ~1 kHz (100.2 dB)
- Optimization failed to evaluate critical frequency regions

---

## Recommendations

### 1. Fix Optimization Frequency Range

**Current (WRONG for midrange horns):**
```python
frequency_range=(20.0, 500.0)  # Only 80 Hz evaluated for Fc ≈ 280 Hz
```

**Proposed fix:**
```python
# For midrange horns (Fc ≈ 200-500 Hz):
frequency_range=(Fc * 2, Fc * 20)  # Wider range covering passband
# Or use frequency-specific ranges:
if fc < 100:      # Bass horn
    frequency_range=(20, 200)
elif fc < 400:    # Midrange horn
    frequency_range=(100, 5000)
else:             # Tweeter horn
    frequency_range=(500, 20000)
```

### 2. Add Multi-Band Flatness Metric

Evaluate flatness in multiple octave bands:
- Low-mid (Fc to 2×Fc)
- Mid (2×Fc to 10×Fc)
- High-mid (10×Fc to 20×Fc)

### 3. Validation Required

Before using optimization results:
1. Check optimization frequency range is appropriate for Fc
2. Run Hornresp validation over full operating range
3. Verify flatness across decade bands, not just optimization range

---

## Files Requiring Updates

1. **src/gsd/optimization/objectives/response_metrics.py**
   - Line 118: Change default `frequency_range` to be adaptive based on Fc
   - Lines 189-197: Adjust frequency range calculation for horns

2. **src/gsd/optimization/parameters/exponential_horn_params.py**
   - Consider adding frequency range presets based on horn type (bass/midrange/tweeter)

3. **tasks/validate_optimized_horn_designs.py**
   - Add warning if optimization frequency range is too narrow
   - Always validate over full operating range (Fc×2 to 20 kHz)

---

## Conclusion

The horn optimization feature has a **critical configuration issue** where the default frequency range (20-500 Hz) is inappropriate for midrange horns. This caused the optimizer to "miss" significant response variations, reporting 0.81 dB flatness when the actual passband has 5.81 dB variation.

**Status:** Optimization results are **NOT VALID** for midrange horns until frequency range is fixed.

**Next steps:**
1. Fix frequency range calculation in `objective_response_flatness()`
2. Re-run optimization with appropriate frequency range
3. Re-validate with Hornresp

---

## Appendix: Cutoff Frequency Validation

| Parameter | Predicted | Hornresp | Error |
|-----------|-----------|----------|-------|
| Fc (Olson formula) | 279.7 Hz | 305 Hz | 25.4 Hz (9.1%) |

Cutoff frequency prediction is within acceptable tolerance (<10%), confirming the horn theory implementation is correct. The issue is purely with the optimization objective configuration.
