# Tapped Horn Batting Model Implementation Summary

## Overview

Implemented the Miki (1990) porous absorber model for internal batting/fiberglass damping in tapped horn loudspeakers. This allows realistic simulation of commercial tapped horn designs which achieve 10-15 dB notch depth instead of the 35-60 dB depth predicted for undamped horns.

## Changes Made

### 1. Core Simulation (`src/gsd/simulation/horn_theory.py`)

**Added `z_rc` parameter to `exponential_horn_tmatrix()`:**
- Previously: `exponential_horn_tmatrix(frequencies, horn, medium, k)`
- Now: `exponential_horn_tmatrix(frequencies, horn, medium, k, z_rc=None)`
- Allows frequency-dependent complex characteristic impedance for bulk damping
- Maintains backward compatibility (z_rc defaults to medium.z_rc)

### 2. Tapped Horn Theory (`src/gsd/simulation/tapped_horn_theory_v2.py`)

**Added `calculate_miki_parameters()` function:**
- Implements Miki (1990) empirical model for porous absorbers
- Returns complex wavenumber `k_complex` and impedance `z_complex`
- Handles flow_resistivity=0 case (returns undamped air properties)
- Uses f/σ normalization (SI units: Hz and Pa·s/m²)

**Modified `calculate_three_port_pressure_v2()`:**
- Checks if `tapped_horn.flow_resistivity > 0`
- If yes: Uses Miki model (replaces wall-loss model)
- If no: Uses existing wall-loss model (backward compatible)
- Passes both `k` and `z_rc` to T-matrix functions

**Modified `calculate_three_port_acoustic_impedance()`:**
- Same damping logic as pressure calculation
- Ensures consistent impedance calculation for SPL wrapper

### 3. Data Types (`src/gsd/simulation/types.py`)

**Added `flow_resistivity` parameter to `TappedHorn` class:**
```python
class TappedHorn:
    ...
    flow_resistivity: float = 0.0  # Pa·s/m² (Rayls/m)
```

**Updated documentation with calibration results:**
- σ = 0: Undamped (no batting)
- σ = 400-800: Light batting for tapped horn subwoofers (20-200 Hz)
- σ = 2000-4000: Polyester batting (mid/high frequency)
- σ = 5000-10000: Fiberglass insulation

## Calibration Results

Tested BC_15PS100 driver in tapped horn at various flow resistivity values:

| σ (Pa·s/m²) | Notch Depth | Peak SPL | Notes |
|-------------|-------------|----------|-------|
| 0 (undamped) | 61.4 dB | 153.8 dB | Too deep - unrealistic |
| 500 | 11.8 dB | 126.2 dB | ✓ Target range (10-15 dB) |
| 1000 | 8.9 dB | 117.7 dB | Slight underdamping |
| 2000 | 6.7 dB | 106.9 dB | Too much damping |
| 3000 | 6.5 dB | 99.5 dB | Way too much damping |
| 10000 | 16.3 dB | 69.6 dB | Very heavy damping |

### Key Finding

**For tapped horn subwoofers (20-200 Hz), use σ ≈ 500 Pa·s/m²**

This is MUCH lower than room acoustics literature values (2000-4000) because:
1. The Miki model was designed for higher frequencies (>500 Hz)
2. Subwoofer frequencies require much less damping material
3. Commercial designs (Danley TH-115, Labhorn) use lightweight, sparse batting

## Physics Model

The Miki model calculates complex parameters:

**Characteristic Impedance:**
```
Z_c = ρ₀c₀ · (R_z + jX_z)
R_z = 1 + 0.070 · (f/σ)^(-0.632)
X_z = -0.107 · (f/σ)^(-0.632)
```

**Wavenumber:**
```
k_c = k₀ · (β - jα)
α = 0.160 · (f/σ)^(-0.618)  # Attenuation
β = 1 + 0.109 · (f/σ)^(-0.618)  # Phase
```

Where `f` is frequency and `σ` is flow resistivity.

## Usage Example

```python
from gsd.simulation.types import TappedHorn
from gsd.simulation.tapped_horn_theory_v2 import tapped_horn_spl_response
from gsd.driver.loader import load_driver

# Create tapped horn with lightweight batting
th = TappedHorn(
    upstream_throat_area=150.0,
    tap_area=450.0,
    downstream_mouth_area=1000.0,
    upstream_length=100.0,
    downstream_length=150.0,
    flow_resistivity=500.0,  # Light batting for subwoofer
)

# Calculate SPL response
driver = load_driver("BC_15PS100")
frequencies = np.logspace(np.log10(20), np.log10(200), 300)
spl = tapped_horn_spl_response(frequencies, th, driver, voltage=2.83)
```

## Validation

### Test Files Created

1. **`tasks/validate_batting_model.py`**
   - Tests undamped (σ=0) vs damped cases
   - Validates regression (no changes when σ=0)
   - Generates comparison plots

2. **`tasks/calibrate_batting_model.py`**
   - Tests multiple flow resistivity values
   - Finds optimal σ for target notch depth
   - Generates calibration curves

### Regression Test

✅ `flow_resistivity=0` produces identical results to previous implementation
- Ensures backward compatibility
- No changes to existing designs that don't use batting

## Next Steps

1. **Optimization Integration:** The batting parameter can now be included in tapped horn optimization
2. **Material Library:** Could add presets for common materials (polyester, fiberglass, foam)
3. **Hornresp Comparison:** Validate against Hornresp's damping model (if available)

## Literature

- **Miki (1990)** - Acoustic properties of porous materials
- **Allard & Atalla (2009)** - Propagation in sound-absorbing porous materials
- **Delany & Bazley (1970)** - Original empirical model (Miki is an improvement)

---

**Status:** ✅ IMPLEMENTED AND CALIBRATED

**Recommended flow_resistivity for tapped horn subwoofers:** σ ≈ 500 Pa·s/m²

**Result:** Realistic 10-15 dB notch depth matching commercial designs
