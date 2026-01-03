# Test Case 2: Driver + Horn (No Chambers)

## Purpose
Validate horn driver integration without throat or rear chambers.

## System Configuration
- **Driver**: Compression driver (B&C DE10-style)
  - S_d: 8 cm²
  - M_md: 8g
  - BL: 12 T·m
  - R_e: 6.5 Ω
  - F_s: ~1.2 kHz

- **Horn**: Exponential
  - Throat area (S1): 5 cm²
  - Mouth area (S2): 200 cm²
  - Length (L12): 50 cm
  - Expansion ratio: 40:1
  - Flare constant: ~11.5 1/m
  - Cutoff frequency: ~630 Hz

- **Chambers**: None
  - Vtc = 0 (no throat chamber)
  - Vrc = 0 (no rear chamber, open back)

## Validation Goals
1. Electrical impedance matches Hornresp (<2% magnitude, <5° phase)
2. Diaphragm velocity is physically realistic
3. Horn loading effect is visible in impedance
4. Cutoff frequency behavior matches theory

## Expected Results
- Impedance peak near driver resonance (~1.2 kHz)
- Horn loading reduces impedance above cutoff (~630 Hz)
- No chamber-related resonances
- Smooth impedance curve above cutoff

## Files
- `horn_params.txt` - Hornresp input file (import this)
- `sim.txt` - Hornresp simulation results (run Hornresp to generate)
- `README.md` - This file

## Hornresp Setup
1. Import `horn_params.txt` into Hornresp
2. Set frequency range: 10 Hz - 10 kHz, 10 points/octave
3. Export Electrical Impedance
4. Export Acoustical Impedance
5. Save as `sim.txt`

## GSD Validation
Run:
```python
from gsd.simulation import ExponentialHorn
from gsd.enclosure.front_loaded_horn import FrontLoadedHorn
from gsd.driver.parameters import ThieleSmallParameters

driver = ThieleSmallParameters(
    M_md=0.008, C_ms=5e-5, R_ms=3.0,
    R_e=6.5, L_e=0.1e-3, BL=12.0, S_d=0.0008,
)

horn = ExponentialHorn(throat_area=0.0005, mouth_area=0.02, length=0.5)
flh = FrontLoadedHorn(driver, horn)

result = flh.electrical_impedance(1000)  # Test at 1 kHz
```
