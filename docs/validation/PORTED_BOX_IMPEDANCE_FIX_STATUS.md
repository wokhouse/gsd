# Ported Box Impedance Fix - Implementation Summary

**Date:** 2025-12-27
**Component:** `src/gsd/enclosure/ported_box.py`
**Status:** Partial fix implemented - improved but not fully validated

## What Was Changed

### 1. Added Port Air Mass Impedance

```python
# Port air mass (acoustic impedance of air in port)
Z_a_port_mass = complex(0, omega * air_density * Lp_eff / port_area)
```

- Calculates effective port length with end correction: `Lp_eff = Lpt + 0.85 × √(S_p/π)`
- Models the air mass oscillating in the port as an inductive impedance
- Based on Helmholtz resonator theory (Thiele 1971)

### 2. Added Port Radiation Impedance

```python
Z_rad_port = radiation_impedance_piston(
    frequency, port_area,
    speed_of_sound=speed_of_sound,
    air_density=air_density
)
```

- Models port as a circular piston radiating into half-space
- Uses Beranek (1954) piston radiation impedance formulas
- Includes both resistive and reactive components

### 3. Implemented Parallel Impedance Combination

```python
# Driver acoustic impedance
Z_a_driver = Z_mechanical / (driver.S_d ** 2)

# Port acoustic impedance (mass + compliance + radiation)
Z_a_port = Z_a_port_mass + Z_a_port_compliance + Z_rad_port

# Parallel combination
Z_a_total = (Z_a_driver * Z_a_port) / (Z_a_driver + Z_a_port)

# Transform back to mechanical domain
Z_mechanical_total = Z_a_total * (driver.S_d ** 2)
```

- Driver and port impedances combine in parallel in acoustic domain
- Both share the same box pressure (Thiele 1971, Figure 3)
- Properly transforms between mechanical and acoustic domains using area ratios

### 4. Added Box Compliance to Port Branch

```python
Z_a_port_compliance = complex(0, -1 / (omega * C_mb)) * (port_area ** 2)
```

- Box compliance C_mb couples both driver and port
- Included in series with port mass and radiation impedance
- Ensures proper Helmholtz resonance behavior

## Current Results

### At Tuning Frequency (Fb = 37 Hz)

| Metric | gsd | Hornresp | Error | Status |
|--------|----------|----------|-------|--------|
| Ze     | 6.7 Ω    | 5.6 Ω    | 1.1 Ω (20%) | ✓ Good |

**Impedance dip behavior is now correct!**

### At Second Peak (~60 Hz)

| Metric | gsd | Hornresp | Error | Status |
|--------|----------|----------|-------|--------|
| Ze     | 46 Ω     | 65 Ω     | 19 Ω (29%) | ✗ Too low |

**Second peak magnitude is wrong but directionally correct (ported > sealed)**

### At First Peak (~20 Hz)

| Metric | gsd | Hornresp | Error | Status |
|--------|----------|----------|-------|--------|
| Ze     | 17.6 Ω   | 24.8 Ω   | 7.2 Ω (29%) | ✗ Too low |

### Overall Validation

```
Electrical Impedance Magnitude:
  Max error: 2412% @ 10 Hz (very low frequencies)
  RMS error: 15.55 Ω
  Mean error: 7.02 Ω
  Pass: ✗
```

## What's Working

1. ✓ Impedance dip at Fb is correct magnitude and location
2. ✓ Dual-peak characteristic is present (vs single peak before)
3. ✓ Ported impedance > sealed impedance (correct direction)
4. ✓ Basic coupled resonator behavior is implemented

## What's Still Wrong

1. ✗ Second peak magnitude is too low (~46 Ω vs ~65 Ω expected)
2. ✗ First peak magnitude is too low (~18 Ω vs ~25 Ω expected)
3. ✗ Very high errors at very low frequencies (<20 Hz)
4. ✗ Phase response has large errors (up to 132°)

## Possible Causes of Remaining Errors

### 1. Equivalent Circuit Topology

The current model may not match Thiele's exact circuit. Possible issues:
- Box compliance C_mb placement (series vs parallel)
- Driver compliance C_ms vs C_mb usage
- Missing series elements

### 2. Compliance Calculation

Currently using: `C_mb = C_ms / (1 + α)` where `α = Vas / Vb`

This is correct for sealed boxes, but ported boxes may need different treatment.

### 3. Missing Losses

Hornresp includes:
- Ql (box leakage losses)
- Qa (absorption losses)
- Port losses (viscous & thermal)

### 4. Mutual Coupling

Driver and port radiation may couple differently than modeled, especially at low frequencies.

### 5. Mass Loading

M_ms_enclosed calculation may not be correct for ported boxes (currently uses sealed box formula).

## Next Steps

### Immediate

1. **Verify equivalent circuit** - Compare with Thiele (1971) Figure 3 more carefully
2. **Check compliance calculation** - Should C_ms or C_mb be used in driver branch?
3. **Add simple losses** - Include R_ab (box absorption) to improve accuracy

### Future Work

1. **Port volume velocity calculation** - For accurate SPL (currently uses diaphragm only)
2. **Full Thiele transfer function** - Implement equations from Thiele (1971) Part 1, Section 5
3. **Leakage losses** - Add Ql parameter for box leakage
4. **Validation with multiple drivers** - Test with different drivers to ensure generality

## Literature References

- Thiele (1971), "Loudspeakers in Vented Boxes", Part 1, Sections 3-5
  - Figure 3: Equivalent circuit for vented box
  - Equation 9: Input impedance formula
- Beranek (1954), "Acoustics", Eq. 5.20: Piston radiation impedance
- `literature/thiele_small/thiele_1971_vented_boxes.md`
- `literature/horns/beranek_1954.md`

## Files Modified

- `src/gsd/enclosure/ported_box.py` - Main implementation (lines 505-636)

## Testing

Run validation:
```bash
PYTHONPATH=src python3 scripts/validate_ported_box.py imports/ported_sim.txt
```

Quick test at Fb:
```python
from gsd.driver.bc_drivers import get_bc_15ps100
from gsd.enclosure.ported_box import ported_box_electrical_impedance

driver = get_bc_15ps100()
result = ported_box_electrical_impedance(
    37.3, driver,
    Vb=0.10554,
    Fb=37.3,
    port_area=0.014017,
    port_length=0.2278,
    voltage=2.83
)
print(f"Ze at Fb: {result['Ze_magnitude']:.2f} Ω (expected ~5.5 Ω)")
```

## Notes

- The impedance dip at Fb is now correct, which validates the basic coupled resonator model
- The magnitude errors suggest the equivalent circuit needs refinement
- This is a significant improvement over the previous implementation (which didn't model the port at all)
- Further work should focus on verifying the exact equivalent circuit topology per Thiele (1971)
