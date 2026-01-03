# Horn Theory Validation

This directory contains validation data for horn theory simulations, validating the T-matrix implementation and horn-driver integration against Hornresp.

## Purpose

Validates the complete horn system model:
- **TC1**: Pure horn theory (T-matrix, throat impedance transformation)
- **TC2-4**: Horn-driver integration (driver + horn + chambers)

## Test Cases

### TC1: Pure Horn Theory (No Driver)

**Directory:** `exp_midrange_tc1/`

Validates core acoustic horn theory independently of driver coupling.

**Parameters:**
- Throat area (S1): 50 cm²
- Mouth area (S2): 500 cm²
- Length (L12): 30 cm
- Flare type: Exponential
- Cutoff frequency (fc): 210.11 Hz
- Expansion ratio: 10:1
- No driver, no chambers

**Status:** ⏳ Pending Hornresp validation

---

### TC2: Driver + Horn (No Chambers)

**Directory:** `exp_midrange_tc2/`

Validates horn-loaded driver without chambers.

**System Configuration:**
- **Driver**: Compression driver (B&C DE10-style)
  - S_d: 8 cm²
  - M_md: 8g
  - BL: 12 T·m
  - R_e: 6.5 Ω

- **Horn**: Exponential
  - Throat area (S1): 5 cm²
  - Mouth area (S2): 200 cm²
  - Length (L12): 50 cm
  - Cutoff frequency: ~630 Hz

- **Chambers**: None (Vtc=0, Vrc=0)

**Validation Goals:**
- Electrical impedance matches Hornresp (<2% magnitude, <5° phase)
- Horn loading effect visible in impedance
- Cutoff frequency behavior matches theory

**Status:** ⏳ Pending Hornresp simulation

---

### TC3: Driver + Horn + Throat Chamber

**Directory:** `exp_midrange_tc3/`

Validates throat chamber compliance effect.

**System Configuration:**
- Same driver and horn as TC2
- **Throat Chamber**: 0.5 liters (Vtc=0.5L, Atc=5cm²)
- **Rear Chamber**: None (Vrc=0)

**Validation Goals:**
- Throat chamber adds series compliance to horn impedance
- Comparison with TC2 shows throat chamber impact
- Compliance resonance is visible

**Status:** ⏳ Pending Hornresp simulation

---

### TC4: Driver + Horn + Both Chambers

**Directory:** `exp_midrange_tc4/`

Validates complete front-loaded horn system.

**System Configuration:**
- Same driver and horn as TC2
- **Throat Chamber**: 0.5 liters (Vtc=0.5L)
- **Rear Chamber**: 2.0 liters (Vrc=2.0L)

**Validation Goals:**
- Complete system with both chambers
- Throat chamber compliance (series element)
- Rear chamber compliance (shunt element)
- Full electromechanical chain validation

**Status:** ⏳ Pending Hornresp simulation

## Validation Criteria

| Test Case | Frequency Range | Magnitude Tolerance | Phase Tolerance |
|---|---|---|---|
| TC1 | f > 2×fc | < 1% | < 2° |
| TC1 | fc < f ≤ 2×fc | < 3% | < 5° |
| TC2-4 | f > F_s/2 | < 2% | < 5° |
| TC2-4 | All frequencies | SPL < 3 dB | - |

## Usage

### Running Hornresp Simulations

1. Import `horn_params.txt` into Hornresp (File → Import)
2. Set frequency range: 10 Hz - 10 kHz, 10 points/octave
3. Export results:
   - Electrical Impedance
   - Acoustical Impedance
   - SPL (for TC4)
4. Save as `sim.txt` in the test case directory

### Running GSD Validation

```python
import sys
sys.path.insert(0, 'src')

import numpy as np
from gsd.simulation import ExponentialHorn
from gsd.enclosure.front_loaded_horn import FrontLoadedHorn
from gsd.driver.parameters import ThieleSmallParameters

# TC2: Driver + Horn (no chambers)
driver = ThieleSmallParameters(
    M_md=0.008, C_ms=5e-5, R_ms=3.0,
    R_e=6.5, L_e=0.1e-3, BL=12.0, S_d=0.0008,
)

horn = ExponentialHorn(throat_area=0.0005, mouth_area=0.02, length=0.5)
flh = FrontLoadedHorn(driver, horn)

# Calculate frequency response
freqs = np.logspace(1, 4, 100)
result = flh.electrical_impedance_array(freqs)

print(f"Electrical impedance at 1 kHz: {result['Ze_magnitude'][50]:.2f} Ω")
```

## Literature

- Kolbrek, B. "Horn Loudspeaker Simulation Part 1: Radiation and T-Matrix"
- Beranek (1954), Eq. 5.20 - Piston radiation impedance
- Olson (1947), Eq. 5.18 - Exponential horn cutoff frequency
- Olson (1947), Chapter 8 - Horn driver systems

## Status

- ✅ TC1: Implementation complete (horn_theory.py)
- ✅ TC1: Unit tests passing (22/22)
- ✅ TC2-4: Implementation complete (horn_driver_integration.py, front_loaded_horn.py)
- ✅ TC2-4: Unit tests passing (39/39)
- ⏳ TC1: Hornresp validation pending
- ⏳ TC2-4: Hornresp simulation pending
- ⏳ TC2-4: Validation comparison pending
