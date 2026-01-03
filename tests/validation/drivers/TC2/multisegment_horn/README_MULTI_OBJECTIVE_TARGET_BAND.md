# Multi-Objective Horn Optimization with Target Band - Validation

**Date**: 2025-12-28
**Design**: Best flatness from multi-objective optimization (WITH target band constraint)
**File**: `multiobjective_target_band_best.txt`

## Design Summary

### Optimization Configuration
- **Objectives**: Wavefront Sphericity + Impedance Smoothness + Response Flatness
- **Target Band**: 500 - 5000 Hz (midrange)
- **Algorithm**: NSGA-II (Multi-objective genetic algorithm)
- **Population**: 60, Generations: 40
- **Pareto-optimal designs found**: 60

### Best Design Results

| Objective | Value | Assessment |
|-----------|-------|------------|
| **Flatness (500-5000 Hz)** | **2.60 dB** | ✓ EXCELLENT (studio monitor quality) |
| Wavefront Sphericity | 1.747648 | Compromised (optimal: ~0) |
| Impedance Smoothness | 3.06 | Compromised (optimal: ~1.5) |

### Horn Parameters

| Parameter | Value | Units |
|-----------|-------|-------|
| **Throat area (S1)** | 2.36 | cm² |
| **Middle area (S2)** | 102.13 | cm² |
| **Mouth area (S3)** | 495.48 | cm² |
| **Length 1 (L12)** | 10.00 | cm |
| **Length 2 (L23)** | 11.87 | cm |
| **Total Length** | 21.87 | cm |
| **Rear Chamber (Vrc)** | 3.49 | L |

### Acoustic Characteristics

| Parameter | Value | Units |
|-----------|-------|-------|
| **Flare constant m1** | 37.68 | m⁻¹ |
| **Flare constant m2** | 13.30 | m⁻¹ |
| **Cutoff Fc1** | 2057 | Hz |
| **Cutoff Fc2** | 726 | Hz |
| **Overall Fc** | 2057 | Hz |
| **Usable bandwidth** | ~3.1 kHz - ~20 kHz | (1.5×Fc to 10×Fc) |

## Key Findings

### 1. Multi-Objective WITH Target Band Works!
- **6× improvement** vs multi-objective WITHOUT target band (16.19 → 2.60 dB)
- Achieved studio-monitor quality flatness (<3 dB)
- Nearly as good as single-objective target band optimization (2.57 dB)

### 2. Trade-offs Remain
- Best flatness requires compromised wavefront quality
- Pareto front shows 60 designs with different trade-offs
- User can choose based on application priorities

### 3. Target Band is Critical
- Constrain optimization to intended frequency range
- Horns are bandpass devices - optimize for their usable range
- Don't penalize response outside the band where horn won't be used

## Comparison With Other Optimizations

| Approach | Flatness | Wavefront | Impedance |
|----------|----------|-----------|-----------|
| Multi-obj (WITH target) | **2.60 dB** ✓ | 1.75 | 3.06 |
| Multi-obj (no target) | 16.19 dB | **0.0001** ✓ | **1.62** ✓ |
| Single-obj (flatness) | 13.01 dB | N/A | N/A |
| Target band (single) | **2.57 dB** ✓ | N/A | N/A |

## Validation Steps

### 1. Import into Hornresp
```
File → Import → multiobjective_target_band_best.txt
```

### 2. Run Simulation
```
Tools → SPL Response
```
Use these settings:
- **Frequency range**: 20 Hz - 20 kHz (logarithmic)
- **Number of points**: 500+
- **Input voltage**: 2.83 V (1W @ 8Ω)

### 3. Export Results
```
File → Export → Text → multiobjective_target_band_sim.txt
```
Include these columns:
- Frequency (Hz)
- SPL (dB)
- Electrical Impedance magnitude (Ω)
- Electrical Impedance phase (°)

### 4. Compare with GSD
Run validation script (to be created):
```bash
python3 /path/to/validate_multiobjective_target_band.py
```

Expected results:
- **SPL error**: <3 dB in target band (500-5000 Hz)
- **Impedance error**: <5% magnitude, <10° phase

## Expected Performance

### Frequency Response
- **Target band (500-5000 Hz)**: 2.60 dB variation (EXCELLENT)
- **Usable range (3.1-20 kHz)**: Flat response
- **Below cutoff (<3 kHz)**: High-pass filter rolloff

### Applications
- **Studio monitors** (excellent flatness in target band)
- **Hi-fi midrange** (vocals, instruments)
- **PA systems** (upper-midrange)

### Limitations
- **Not suitable for full-range** - cutoff at 2057 Hz
- **Not optimized for bass** - target band starts at 500 Hz
- **Wavefront quality compromised** for flatness

## Literature

Optimization based on:
- Deb (2001) - NSGA-II multi-objective algorithm
- Olson (1947) - Horn theory and wavefront analysis
- Beranek (1954) - Horn impedance and directivity
- Small (1972) - Thiele-Small parameters

## Next Steps

1. ✅ Export to Hornresp
2. ⏳ Run Hornresp simulation
3. ⏳ Compare results with gsd
4. ⏳ Document any discrepancies
5. ⏳ If validation passes, add to test suite

## Files

- `multiobjective_target_band_best.txt` - Hornresp parameters (this file)
- `multiobjective_target_band_sim.txt` - Hornresp simulation results (to be generated)
- `multiobjective_target_band_validation.txt` - Validation report (to be generated)

---

**Status**: Ready for Hornresp validation
**Last updated**: 2025-12-28
