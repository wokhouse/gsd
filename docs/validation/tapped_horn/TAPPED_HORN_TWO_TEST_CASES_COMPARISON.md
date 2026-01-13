# Tapped Horn Two-Test Case Comparison

## Purpose

Compare GSD simulation results across two different tapped horn configurations to identify error patterns and validate whether the baseline implementation (Kolbrek T-matrix + parallel impedance) behaves consistently.

## Test Case 1: BC_15PS100 (Baseline)

### Driver Parameters
- **Model**: B&C 15PS100
- **Size**: 15" woofer
- **S_d**: 855 cm²
- **F_s**: 37.3 Hz
- **BL**: 18.6 T·m
- **R_e**: 6.18 Ω
- **M_md**: 43.0 g

### Tapped Horn Geometry
- **Throat area**: 246 cm² (closed)
- **Tap area**: 855 cm² (driver location)
- **Intermediate area**: 2337 cm²
- **Mouth area**: 4536 cm² (open)
- **Upstream length**: 138.5 cm
- **Downstream length**: 186.5 cm
- **Profile**: Exponential

### Theoretical Quarter-Wave Resonance
- Physical length: L = 1.385 m
- Expected f_qw = c / (4L) = 344 / (4 × 1.385) = **62.1 Hz**

### GSD Simulation Results
- **Notch frequency**: 78.6 Hz
- **Notch depth**: 88.35 dB (minimum SPL)
- **SPL range**: 75.7 - 102.0 dB (20-200 Hz)
- **Frequency ratio**: 78.6 / 62.1 = **1.27** (notch is 27% HIGHER than theoretical)

### Hornresp Validation Results
- **Notch frequency**: 80.0 Hz
- **Notch depth**: 55.14 dB (45 dB dip!)
- **RMS error**: 10.80 dB
- **Peak error**: 33.21 dB at notch

## Test Case 2: BC_12NDL76 (New)

### Driver Parameters
- **Model**: B&C 12NDL76
- **Size**: 12" mid-woofer
- **S_d**: 522 cm²
- **F_s**: 48.7 Hz
- **BL**: 20.1 T·m
- **R_e**: 5.30 Ω
- **M_md**: 39.9 g

### Tapped Horn Geometry
- **Throat area**: 180 cm² (closed)
- **Tap area**: 550 cm² (driver location)
- **Intermediate area**: 1500 cm²
- **Mouth area**: 2800 cm² (open)
- **Upstream length**: 120.0 cm
- **Downstream length**: 160.0 cm
- **Profile**: Exponential

### Theoretical Quarter-Wave Resonance
- Physical length: L = 1.20 m
- Expected f_qw = c / (4L) = 343 / (4 × 1.20) = **71.5 Hz**

### GSD Simulation Results
- **Notch frequency**: 56.0 Hz
- **Notch depth**: 54.1 dB (minimum SPL)
- **SPL range**: 54.1 - 114.7 dB (20-200 Hz)
- **Frequency ratio**: 56.0 / 71.5 = **0.78** (notch is 22% LOWER than theoretical)

### Hornresp Validation Status
⚠️ **PENDING**: Need to create Hornresp input and run validation

## Key Observations

### 1. Notch Frequency Pattern

| Test Case | Physical Length (m) | Theoretical f_qw (Hz) | GSD Notch (Hz) | Ratio | Pattern |
|-----------|---------------------|----------------------|----------------|-------|---------|
| 1 (15PS100) | 1.385 | 62.1 | 78.6 | 1.27 | Notch HIGHER |
| 2 (12NDL76) | 1.20 | 71.5 | 56.0 | 0.78 | Notch LOWER |

**Critical Finding**: The notch frequency relationship to theoretical quarter-wave is **inverted** between the two test cases!

- Test case 1: Notch 27% HIGHER than expected
- Test case 2: Notch 22% LOWER than expected

This suggests that:
1. The notch frequency is NOT simply determined by upstream physical length
2. Other factors (driver parameters, area ratios, downstream length) significantly affect the notch
3. The simple formula f_qw = c/(4L) is insufficient for tapped horns

### 2. Notch Depth Pattern

| Test Case | GSD Notch Depth (dB) | Hornresp Notch (dB) | Error |
|-----------|---------------------|---------------------|-------|
| 1 (15PS100) | 88.35 (13 dB dip) | 55.14 (45 dB dip) | 32 dB too shallow |
| 2 (12NDL76) | 54.1 (60 dB dip?) | PENDING | ? |

Test case 2 shows a MUCH deeper notch (54.1 dB SPL) compared to test case 1 (88.35 dB SPL). This is a ~34 dB difference!

### 3. Driver Size Impact

| Parameter | Test 1 (15PS100) | Test 2 (12NDL76) | Ratio |
|-----------|------------------|------------------|-------|
| S_d (cm²) | 855 | 522 | 1.64× |
| F_s (Hz) | 37.3 | 48.7 | 0.77× |
| Upstream length (cm) | 138.5 | 120.0 | 1.15× |
| Throat area (cm²) | 246 | 180 | 1.37× |
| Tap area (cm²) | 855 | 550 | 1.55× |

The smaller driver (12NDL76) has:
- Smaller S_d (less acoustic coupling)
- Higher F_s (stiffer suspension)
- Shorter upstream length
- Much deeper notch (60 dB vs 13 dB dip)

### 4. Hornresp Comparison Needed

For test case 2, we need to:
1. Create Hornresp input file with parameters above
2. Run simulation at 20-200 Hz, 1 Hz steps
3. Extract SPL and impedance data
4. Calculate RMS error and compare with test case 1

## Hypotheses to Test

### Hypothesis 1: Notch Frequency Depends on Area Ratio
The quarter-wave notch might be determined by an **effective acoustic length** rather than physical length:
- L_eff = L_physical × sqrt(S_throat / S_tap)
- Test case 1: L_eff = 1.385 × sqrt(246/855) = 1.385 × 0.537 = 0.744 m → f_qw = 115 Hz (too high)
- Test case 2: L_eff = 1.20 × sqrt(180/550) = 1.20 × 0.572 = 0.686 m → f_qw = 125 Hz (too high)

This doesn't match either test case. ❌

### Hypothesis 2: Notch Frequency from Combined Upstream + Downstream
The notch might involve the **entire horn length**, not just upstream:
- L_total = L_upstream + L_downstream
- Test case 1: L_total = 1.385 + 1.865 = 3.25 m → f_qw = 26.5 Hz (too low)
- Test case 2: L_total = 1.20 + 1.60 = 2.80 m → f_qw = 30.6 Hz (too low)

This also doesn't match. ❌

### Hypothesis 3: Notch from Impedance Minima at Tap Point
The notch occurs when Z_up || Z_down is minimized, which depends on:
- Upstream quarter-wave resonance (closed-closed pipe)
- Downstream impedance transformation
- Driver coupling at tap point

This requires analyzing the **complex impedance interaction**, not simple length formulas.

### Hypothesis 4: Different Error Modes for Different Geometries

**Test case 1** (larger driver, longer horn):
- Notch too SHALLOW (13 dB dip vs 45 dB expected)
- Notch frequency HIGHER than theoretical

**Test case 2** (smaller driver, shorter horn):
- Notch appears MUCH DEEPER (60 dB dip?)
- Notch frequency LOWER than theoretical

**Possible explanation**: The parallel impedance model (Z_up || Z_down) might be:
- Underestimating destructive interference in large horns
- Overestimating notch frequency shift in small horns
- Missing driver-size-dependent effects

## Next Steps

1. **Run Hornresp for test case 2** - Critical for comparison
2. **Compare error patterns** - Are errors consistent across drivers?
3. **Analyze impedance curves** - Look at Z_up, Z_down, Z_total separately
4. **Calculate effective acoustic length** - Derive from actual notch frequency
5. **Investigate area ratio effects** - Does throat/tap ratio dominate?

## Files Generated

- `tasks/test_case_2_12ndl76.py` - Test case 2 generation script
- `tasks/test_case_2_12ndl76_gsd_results.txt` - GSD simulation results (ready for Hornresp comparison)

## Literature References

- Berzborn & Smithers (2018), AES Paper 10047 - Quarter-wave resonance in tapped horns
- Danley (2013), US Patent 8,457,341 B2 - Tapped horn design criteria
- `literature/horns/tapped_horn_theory.md` - Background theory
