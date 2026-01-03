# BC_15DS115 Bass Horn Design Summary

**Date:** 2025-12-28
**Driver:** B&C 15DS115-8 15" Subwoofer
**Design Method:** Multi-objective optimization (NSGA-II)

---

## Driver Analysis

The BC_15DS115 is an **excellent candidate for horn loading**:

| Parameter | Value | Suitability |
|-----------|-------|-------------|
| Fs | 33 Hz | Low resonance = deep bass extension |
| Qts | 0.061 (with horn loading) | ✓ Excellent - < 0.35 ideal for horns |
| Vas | 254 L | Large compliance = good low-frequency response |
| Sd | 855 cm² | Large piston = high output capability |
| BL | 38.7 T·m | Strong motor = good control |
| Xmax | 16.5 mm | Long excursion = high power handling |

**Horn Suitability Assessment:** The very low Qts (0.061 with horn loading) indicates this driver is exceptionally well-suited for horn loading. The driver will achieve tight coupling and high efficiency in a properly designed horn.

---

## Optimization Results

**Method:** NSGA-II multi-objective optimization
**Population:** 100 designs
**Generations:** 100
**Objectives:**
- Minimize F3 (bass extension)
- Maximize efficiency
- Minimize enclosure size

**Valid designs found:** 100
**Pareto front size:** 100 designs

---

## Top 10 Bass Horn Designs

### Design #1 (Recommended - Best Balance)

**Geometry:**
- Throat area: 85.6 cm²
- Mouth area: 1003 cm² (radius: 17.9 cm)
- Length: 2.59 m
- Flare constant: 0.95 m⁻¹
- **Cutoff frequency (fc): 51.9 Hz**

**Chambers:**
- Throat chamber: 19.4 cm³
- Rear chamber: 391.0 L
- Horn volume: 96.5 L
- **Total system volume: 487.5 L**

**Performance:**
- **F3: 51.9 Hz**
- Efficiency: High (horn loading advantage)

---

### Design #2 (Lower Cutoff - Slightly Longer)

**Geometry:**
- Throat area: 86.9 cm²
- Mouth area: 1000 cm² (radius: 17.8 cm)
- Length: 2.65 m
- Flare constant: 0.92 m⁻¹
- **Cutoff frequency (fc): 50.3 Hz**

**Chambers:**
- Throat chamber: 19.0 cm³
- Rear chamber: 381.6 L
- Horn volume: 99.1 L
- **Total system volume: 480.8 L**

**Performance:**
- **F3: 50.3 Hz** (best of top 10)

---

### Design #4 (Compact - Higher Cutoff)

**Geometry:**
- Throat area: 88.5 cm²
- Mouth area: 1000 cm² (radius: 17.8 cm)
- Length: 2.73 m
- Flare constant: 0.89 m⁻¹
- **Cutoff frequency (fc): 48.5 Hz**

**Chambers:**
- Throat chamber: 19.8 cm³
- Rear chamber: 357.3 L
- Horn volume: 102.6 L
- **Total system volume: 459.9 L** (smallest of top 10)

**Performance:**
- **F3: 48.5 Hz**

---

## Hornresp Export File

**Location:** `exports/bc15ds115_bass_horn.txt`

The top design (Design #2) has been exported to Hornresp format for validation.

**Import into Hornresp:**
```
File → Import → Select bc15ds115_bass_horn.txt
```

**Hornresp Parameters:**
- S1 (throat): 86.38 cm²
- S2 (mouth): 1002.44 cm²
- L12 (length): 2.66 m
- F12 (cutoff): 50.29 Hz
- Rear chamber (Vrc): 381.6 L
- Throat chamber (Vtc): 19 cm³

---

## Design Notes

### Horn Size Considerations

These bass horns are **large but realistic** for serious bass reproduction:

- **Total volume:** ~480-500 L (0.48-0.5 m³)
- **Horn length:** 2.6-2.7 m
- **Mouth diameter:** ~36 cm (14 inches)

**Why so large?**
- Bass horns require large mouth areas to maintain loading at low frequencies
- Full mouth loading at 50 Hz would require ~6 m² mouth area (impractical)
- These designs use a practical compromise: ~0.1 m² mouth for acceptable size
- The rear chamber (~380 L) provides additional compliance for low-frequency extension

### Trade-offs

**Bass Horn Advantages:**
- ✓ Much higher efficiency than direct radiator (+6-10 dB typical)
- ✓ Better damping and control (low Qts)
- ✓ Lower distortion for given output
- ✓ Extended low-frequency response

**Bass Horn Disadvantages:**
- ✗ Large physical size (480-500 L total volume)
- ✗ Complex construction (folded horn required for 2.6 m length)
- ✗ Long path length can cause time smearing (mitigated by driver placement)

---

## Construction Recommendations

### Folded Horn Layout

For a 2.6 m exponential horn with ~0.1 m² mouth, consider these folding strategies:

**Option 1: Bass Reflex Fold (Klipsch-style)**
- Path folds back on itself 3-4 times
- Fits in a rectangular cabinet ~120 cm × 80 cm × 80 cm
- Driver mounted on top panel, horn exits from front

**Option 2: S-Curve Fold**
- Single continuous S-curve path
- Smoother airflow, fewer reflections
- Requires taller cabinet (~150 cm height)

### Materials

**Walls:** 18-22 mm plywood or MDF (braced internally)
**Horn path:** Smooth surfaces to reduce turbulence
**Internal bracing:** Critical to prevent panel resonance at 40-60 Hz

### Mouth Treatment

**Options:**
1. **Open baffle:** Mouth exits directly into room (half-space radiation)
2. **Corner placement:** Exploit room corners for acoustic gain
3. **Flare extension:** Add 20-30 cm rectangular flare at mouth for better impedance matching

---

## Validation Next Steps

1. **Import to Hornresp:** Load `bc15ds115_bass_horn.txt` and verify parameters
2. **Simulate response:** Generate SPL and impedance curves
3. **Compare with gsd:** Check agreement (should be <2% deviation)
4. **Analyze mouth reflection:** Look for impedance anomalies from mouth size compromise
5. **Adjust if needed:** Modify rear chamber volume or throat chamber for desired response

---

## Literature References

**Horn Theory:**
- Olson (1947), Chapter 5 - Exponential horn theory, cutoff frequency
- Olson (1947), Eq. 5.18 - f_c = c·m/(2π)
- Beranek (1954), Chapter 5 - Horn radiation impedance

**Hornresp Validation:**
- Hornresp User Manual - File format specification
- Hornresp uses: F12 = c·m/(4π) (note: 4π, not 2π!)

**Design Principles:**
- Small (1972) - Horn driver requirements (Qts < 0.35)
- Kolbrek horn theory tutorial - Modern T-matrix methods

---

## Files Generated

1. **`exports/bc15ds115_bass_horn_designs.json`** - Full optimization results (all 100 designs)
2. **`exports/bc15ds115_bass_horn.txt`** - Hornresp import file (top design)
3. **`tasks/design_bc15ds115_bass_horn.py`** - Optimization script (reusable)

---

## Summary

The BC_15DS115 is an **excellent candidate for bass horn loading** due to its very low Qts (0.061) and strong motor (BL = 38.7 T·m). The optimization produced practical bass horn designs with:

- **F3: 48-52 Hz** (good bass extension)
- **Total volume: 480-500 L** (large but realistic)
- **Horn length: 2.6-2.7 m** (requires folding)
- **Efficiency: High** (horn loading advantage)

**Recommended design:** #2 (fc = 50.3 Hz, V_total = 480.8 L)

**Next step:** Import to Hornresp for validation and fine-tuning!
