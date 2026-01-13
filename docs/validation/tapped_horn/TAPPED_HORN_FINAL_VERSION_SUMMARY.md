# Tapped Horn Final Version - Implementation Summary

## Overview

Implemented the **Final Version** of the tapped horn simulation based on literature validation by the research agent. This version uses a rigorous **One-Pass electro-mechanical-acoustic solver** that follows standard electro-acoustic theory (Leach, Small, Beranek).

## Implementation Location

- **File**: `src/gsd/simulation/tapped_horn_theory.py`
- **Function**: `tapped_horn_system_response_final()`
- **Helper**: `calculate_lossy_wavenumber_with_roughness()`

## Key Features

### 1. One-Pass Solver

Instead of calculating electrical impedance separately and then velocity, the Final Version solves for driver velocity U_D directly using:

```
U_D = (Bl × V_in) / (Z_e × Z_mech_total + Bl²)
```

Where:
- `Z_e = R_e + jωL_e` (voice coil impedance only)
- `Z_mech_total = Z_mech_driver + Z_acoustic × S_d²`
- `Z_acoustic = Z_up || Z_down` (parallel combination)

This eliminates circular dependencies and follows the standard Leach/Small topology.

### 2. Parameterizable Roughness Factor

Added `roughness_factor` parameter (default 4.0) to account for real-world folded horn imperfections:

- **1.0** = Smooth pipe (Keefe standard, laboratory)
- **4.0** = Folded wooden horn (typical)
- **2.0-5.0** = Practical range for folded horns

This is based on Holland & Fahy (AES) measurements showing folded horns have significantly higher losses than smooth waveguides.

### 3. Explicit Contracting Horn Geometry

The upstream section is modeled as a **physical contracting horn** (Tap → Throat), not a mathematically inverted expanding horn. This correctly captures the impedance transformation of waves traveling into a narrowing taper.

```python
upstream_contracting = ExponentialHorn(
    throat_area=tapped_horn.tap_area / 10000.0,              # INPUT at Tap (m²)
    mouth_area=tapped_horn.upstream_throat_area / 10000.0,    # OUTPUT at Throat (m²)
    length=tapped_horn.upstream_length / 100.0,               # Convert cm to m
)
```

### 4. Standard Electro-Acoustic Model

Removed heuristic "coupling factors" and used the standard Leach/Small formula:

```
Z_e_plot = Z_voice_coil + (Bl)² / Z_mech_total
```

This is the well-established electro-acoustic impedance model used throughout the literature.

### 5. 2π Half-Space Radiation

Default radiation is hardcoded to **half-space (2π)** to match Hornresp measurements. Free-field (4π) would be 6 dB lower.

## Validation Results

### Test Configuration

- **Driver**: BC_15PS100 (Fs=37.3 Hz, Vas=105.5 L, Qts=0.44)
- **Geometry**: 3-segment tapped horn
  - Throat area: 246 cm²
  - Tap area: 855 cm² (at 138.5 cm from throat)
  - Intermediate area: 2337 cm²
  - Mouth area: 4536 cm²
  - Total length: 325 cm (138.5 cm upstream + 186.5 cm downstream)

### Accuracy vs Hornresp (40-100 Hz Passband)

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| RMS Error | 8.78 dB | <2 dB | ✗ Not met |
| Mean Error | -4.08 dB | ±1 dB | ✗ Not met |
| Peak Error | 29.86 dB (at 80 Hz) | <5 dB | ✗ Not met |

### Detailed Frequency Analysis

| Freq (Hz) | GSD SPL (dB) | HR SPL (dB) | Error (dB) | Notes |
|-----------|--------------|--------------|------------|-------|
| 40 | 98.80 | 106.21 | -7.41 | Below passband |
| 50 | 95.74 | 96.98 | -1.24 | ✓ Good |
| 60 | 91.57 | 97.86 | -6.29 | Impedance error (+85%) |
| 70 | 88.64 | 105.68 | -17.03 | Large error |
| 79 | 75.63 | 78.97 | -3.34 | Quarter-wave notch (GSD) |
| 80 | 84.99 | 55.14 | +29.86 | Quarter-wave notch (HR) |
| 85 | 92.24 | 88.83 | +3.41 | ✓ Good |
| 90 | 91.83 | 93.94 | -2.11 | ✓ Good |
| 100 | 92.56 | 100.16 | -7.60 | |

## Known Issues

### 1. Quarter-Wave Notch Position Mismatch

- **GSD**: Notch at 79 Hz (75.63 dB)
- **Hornresp**: Notch at 80 Hz (55.14 dB)

The notch depth is very different (20 dB difference), suggesting that the parallel impedance `Z_up || Z_down` is not reaching zero as it should at quarter-wave resonance.

### 2. General SPL Level Offset

Consistent -4 to -10 dB offset across most frequencies suggests:
- Possible reference pressure issue
- Radiation impedance scaling problem
- Power calculation error

### 3. Electrical Impedance Errors

At 60 Hz resonance:
- **GSD**: 20.34 Ω
- **Hornresp**: 10.96 Ω
- **Error**: +85%

This suggests the impedance calculation needs refinement.

## Comparison with Previous Versions

| Feature | Production | v2 | Final Version |
|---------|-----------|-----|---------------|
| Upstream Geometry | Reversed T-matrix | Explicit contracting | Explicit contracting ✓ |
| Losses | Standard Keefe | Enhanced (4x) | Parameterizable (default 4x) ✓ |
| Electrical Model | Two-branch with heuristic | Two-branch with heuristic | Standard Leach/Small ✓ |
| Radiation | 4π (free-field) | 2π (half-space) | 2π (half-space) ✓ |
| Solver | Multi-pass | Multi-pass | One-Pass ✓ |

## Literature Citations

All implementation is based on established literature:

- **Berzborn & Smithers (2018), AES Paper 10047** - Three-port network model
- **Keefe (1984)** - Lossy wave propagation with roughness correction
- **Small (1972)** - Standard electro-acoustic impedance model
- **Leach (1989)** - Electro-mechanical-acoustic circuit topology
- **Beranek (1954)** - Acoustic impedance theory

## Next Steps

The Final Version implements the correct topology based on literature, but validation shows it needs tuning to match Hornresp exactly. Possible improvements:

1. **Investigate quarter-wave notch**: The parallel impedance calculation may need adjustment
2. **SPL level calibration**: Investigate the -4 to -10 dB systematic offset
3. **Impedance refinement**: The electrical impedance calculation needs work at resonance

## Usage Example

```python
from gsd.driver.loader import load_driver
from gsd.simulation.types import TappedHorn
from gsd.simulation.tapped_horn_theory import tapped_horn_system_response_final

driver = load_driver("BC_15PS100")

th = TappedHorn(
    upstream_throat_area=246.0,
    tap_area=855.0,
    upstream_length=138.5,
    upstream_profile='exponential',
    downstream_mouth_area=4536.0,
    downstream_length=186.5,
    downstream_profile='exponential',
    intermediate_area=2337.0,
)

result = tapped_horn_system_response_final(
    frequencies=np.linspace(20, 200, 361),
    driver=driver,
    tapped_horn=th,
    voltage=2.83,
    roughness_factor=4.0,
    radiation_space='halfspace',
)

print(f"SPL at 50 Hz: {result['spl'][60]:.2f} dB")  # Index 60 = 50 Hz
```

## Files Created

- `src/gsd/simulation/tapped_horn_theory.py` - Final Version implementation
- `tasks/validate_tapped_horn_final.py` - Validation script
- `tasks/detailed_comparison.py` - Frequency-by-frequency comparison
- `tasks/debug_final_version.py` - Debug output tool

## Summary

The Final Version successfully implements the literature-validated electro-acoustic topology with:
- ✅ One-Pass solver (no circular dependencies)
- ✅ Parameterizable losses (roughness_factor)
- ✅ Explicit contracting horn geometry
- ✅ Standard Leach/Small impedance model
- ✅ 2π half-space radiation

However, validation shows **8.78 dB RMS error** vs Hornresp, which does not meet the <2 dB target. Further investigation is needed to:
1. Correct the quarter-wave notch depth
2. Eliminate the -4 to -10 dB SPL offset
3. Fix electrical impedance errors at resonance
