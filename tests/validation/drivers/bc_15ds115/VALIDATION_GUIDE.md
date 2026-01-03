# BC_15DS115 Hornresp Validation Guide

**Date:** 2025-12-27
**Purpose:** Validate improved simulation model against Hornresp

---

## Overview

This document provides a step-by-step guide for validating the gsd simulation improvements using Hornresp as the reference standard.

**Three designs spanning the design space:**
1. **Compact (60L, 34Hz)** - Old model approach, space-saving
2. **Classic B4 (254L, 33Hz)** - Traditional Butterworth alignment
3. **Optimal (300L, 27Hz)** - Improved model, best overall flatness

---

## Files

All validation files are in `tasks/validation/`:

| File | Design | Purpose |
|------|--------|---------|
| `BC15DS115_compact_60L_34Hz.txt` | 60L @ 34Hz | Old model, small enclosure |
| `BC15DS115_B4_254L_33Hz.txt` | 254L @ 33Hz | Classic B4, literature standard |
| `BC15DS115_optimal_300L_27Hz.txt` | 300L @ 27Hz | Improved model, optimal |

---

## Validation Procedure

### Step 1: Import into Hornresp

1. Open Hornresp
2. File → Import → select the .txt file
3. Verify parameters loaded correctly:
   - **Vrc** (rear chamber volume) = Vb in liters
   - **Ap** (port area) in cm²
   - **Lpt** (port length) in cm
   - **Sd** = 855 cm² (driver area)
   - **Mmd** = 64.86 g (driver mass only, NOT M_ms!)
   - **Cms** = 2.50E-04 m/N

### Step 2: Run Simulation

**Settings:**
- Frequency range: 20 - 500 Hz
- Input voltage: 2.83 V (1W into 8Ω nominal)
- Measurement distance: 1 m
- Number of points: 200 (log-spaced)

**In Hornresp:**
1. Tools → Response Wizard
2. Set: 20-500 Hz, 2.83V, 1m
3. Click "Calculate"
4. Export results: File → Export → save as .csv

### Step 3: Key Comparison Points

#### A. Frequency Response (SPL)

Compare at these frequencies:

| Frequency | Compact (60L) | B4 (254L) | Optimal (300L) |
|-----------|---------------|-----------|----------------|
| 20 Hz | ~73 dB | ~82 dB | **~83 dB** ⭐ |
| 30 Hz | ~89 dB | ~99 dB | **~101 dB** |
| 40 Hz | ~90 dB | ~95 dB | **~96 dB** |
| 60 Hz | ~90 dB | ~94 dB | **~95 dB** |
| 100 Hz | ~91 dB | ~94 dB | **~96 dB** |
| 200 Hz | ~93 dB | ~97 dB | **~98 dB** |
| 500 Hz | ~94 dB | ~98 dB | **~98 dB** |

**Expected patterns:**
- Compact: ~10 dB less at 20 Hz (stiff box reduces bass)
- B4: Bass boost around 30-40 Hz (tuning frequency)
- Optimal: Highest deep bass, flattest overall

#### B. High-Frequency Roll-off

**Critical validation point for improved model:**

At 200 Hz:
- **GSD predicts:** -7.77 dB roll-off from mass + inductance
- **Hornresp should show:** Similar roll-off (check SPL slope 150-300 Hz)

At 500 Hz:
- **GSD predicts:** Additional -1-2 dB roll-off
- **Hornresp should show:** Continued roll-off

**What to look for:**
- Plot SPL from 100-500 Hz
- Slope should be ~6-12 dB/octave above 150 Hz
- This validates the HF roll-off implementation

#### C. Impedance Curve

Ported boxes show **dual impedance peaks**:

**Expected frequencies:**
- Lower peak: ~0.7 × Fb (driver resonance with port loading)
- Dip: At Fb (minimum impedance ≈ Re)
- Upper peak: ~1.4 × Fb (Helmholtz resonance)

| Design | Fb | Lower Peak | Impedance Dip | Upper Peak |
|--------|----|------------|---------------|------------|
| Compact (60L) | 34 Hz | ~24 Hz | 34 Hz | ~48 Hz |
| B4 (254L) | 33 Hz | ~23 Hz | 33 Hz | ~46 Hz |
| Optimal (300L) | 27 Hz | ~19 Hz | 27 Hz | ~38 Hz |

**What to check:**
- Impedance at tuning = ~5 Ω (close to Re = 4.9 Ω)
- Peak heights: 20-50 Ω depending on Qts
- Two distinct peaks visible

#### D. Flatness Metrics

Calculate standard deviation in different ranges:

**Method:**
1. Export SPL data from Hornresp
2. Calculate σ = std(SPL) for frequency range
3. Compare with gsd predictions

**Expected results:**

| Range | Compact (60L) | B4 (254L) | Optimal (300L) |
|-------|---------------|-----------|----------------|
| 20-40 Hz | σ ≈ 5.9 dB | σ ≈ 7.3 dB | σ ≈ **5.4 dB** ⭐ |
| 20-80 Hz | σ ≈ 4.9 dB | σ ≈ 5.4 dB | σ ≈ **3.9 dB** ⭐ |
| 40-120 Hz | σ ≈ 0.5 dB | σ ≈ 0.7 dB | σ ≈ **0.5 dB** ⭐ |
| 20-200 Hz | σ ≈ 4.2 dB | σ ≈ 4.3 dB | σ ≈ **3.1 dB** ⭐ |

**Key validation:** Optimal (300L) should be flattest overall (20-200 Hz)

---

## Expected Differences Between Designs

### Compact (60L, 34Hz)

**Characteristics:**
- High α = 4.23 (very stiff box)
- Reduced deep bass output
- Best midbass flatness (40-120 Hz)
- Less variation overall

**Hornresp should show:**
- Lowest output at 20-30 Hz
- Flattest response 40-200 Hz
- Higher tuning frequency shifts response up

**Use case:** Space-constrained, music-focused

### Classic B4 (254L, 33Hz)

**Characteristics:**
- α = 1.00 (by definition)
- h = 1.00 (by definition)
- Bass boost around tuning (30-40 Hz)
- More variation in deep bass

**Hornresp should show:**
- Visible peak at ~30-40 Hz (bass boost)
- Higher output at 20 Hz than compact
- More variation overall

**Use case:** Traditional design, well-documented

### Optimal (300L, 27Hz)

**Characteristics:**
- α = 0.85 (box softer than driver suspension)
- h = 0.82 (tuning below Fs)
- Best overall flatness (20-200 Hz)
- Deep bass extension (F3 ≈ 10 Hz)

**Hornresp should show:**
- Highest output at 20 Hz
- Flattest response overall
- Bass boost balances HF roll-off

**Use case:** Maximum performance, home theater

---

## Quantitative Validation Checklist

### Frequency Response

- [ ] Deep bass (20-40 Hz): Optimal > B4 > Compact by ~8-10 dB
- [ ] Tuning frequency (30-34 Hz): All show different response shapes
- [ ] Midbass (40-120 Hz): All similar (σ ≈ 0.5-0.7 dB)
- [ ] HF roll-off (200 Hz): -7 to -8 dB from peak
- [ ] HF roll-off (500 Hz): Additional -1 to -2 dB

### Impedance

- [ ] Dual peaks visible in all designs
- [ ] Impedance dip at Fb ≈ Re (4.9 Ω)
- [ ] Lower peak ~0.7 × Fb
- [ ] Upper peak ~1.4 × Fb

### Flatness

- [ ] Optimal (300L) flattest overall (20-200 Hz)
- [ ] Compact (60L) best midbass (40-120 Hz)
- [ ] B4 (254L) intermediate performance

### Driver Parameters Verification

- [ ] Mmd = 64.86 g (NOT M_ms = 93 g!)
- [ ] Hornresp calculates its own radiation mass
- [ ] Cms = 2.50E-04 m/N (scientific notation)
- [ ] Re = 4.9 Ω, Le = 4.5 mH

---

## Troubleshooting

### Issue: SPL levels don't match

**Check:**
- Input voltage = 2.83 V
- Measurement distance = 1 m
- Driver parameters match (especially Mmd)

**Expected offset:** ±3 dB is acceptable

### Issue: No HF roll-off visible

**Check:**
- Frequency range extends to 500 Hz
- Le = 4.5 mH (inductance matters!)
- BL = 38.7 T·m (high BL = strong motor)

**Expected:** -7.77 dB at 200 Hz relative to peak

### Issue: Impedance peaks missing

**Check:**
- Port parameters correct (Ap, Lpt)
- Vrc = box volume
- End correction enabled (End Correction Flag = 1)

**Expected:** Two clear peaks with dip at Fb

---

## Success Criteria

**Validation successful if:**

1. **Frequency response shapes match** within ±3 dB
2. **HF roll-off visible** at 200 Hz (-7 to -8 dB)
3. **Dual impedance peaks** present
4. **Flatness ranking correct:** Optimal > B4 > Compact (overall)
5. **Deep bass output ranking:** Optimal > B4 > Compact

**Expected deviation from Hornresp:**
- SPL: ±3 dB (calibration offset)
- Impedance magnitude: ±10% near peaks
- F3: ±2 Hz
- Flatness: ±0.5 dB

---

## Next Steps

After validation:

1. **Document results** in `tasks/validation/RESULTS.md`
2. **Update calibration** if needed (currently +13 dB)
3. **Refine HF roll-off model** if Hornresp shows different slope
4. **Add port noise validation** (chuffing at high power)
5. **Validate against other drivers** (BC_8NDL51, BC_15PS100)

---

## References

**Hornresp:**
- http://www.hornresp.net/
- User manual: File format specification

**GSD:**
- `src/gsd/enclosure/ported_box.py` - Simulation model
- `src/gsd/hornresp/export.py` - Export function
- `tasks/optimized_bc15ds115_study.py` - Study script

**Literature:**
- Small (1973) - Vented-box systems
- Thiele (1971) - Loudspeakers in vented boxes

---

**Generated:** 2025-12-27
**Status:** Ready for validation
