# Baffle Step Validation - Hornresp Reference Data

This directory contains reference data from Hornresp for validating the baffle step implementation.

## Purpose

Validate the Olson/Stenzel circular baffle model (`gsd.enclosure.baffle_step.baffle_step_loss_olson()`) against Hornresp's baffle diffraction simulation.

## Status

**PENDING** - Hornresp simulation needs to be created.

## How to Create Reference Data

### Step 1: Install Hornresp

1. Download Hornresp from http://www.hornresp.net/
2. Install and launch the application
3. Familiarize yourself with the interface

### Step 2: Enter Driver Parameters

Use BC_8NDL51 driver parameters (from B&C datasheet):

```
|TRADITIONAL DRIVER PARAMETER VALUES:
Sd = 92.90        # cm² (piston area)
Bl = 12.40        # T·m (force factor)
Cms = 2.03E-04    # m/N (compliance)
Rms = 3.30        # N·s/m (mechanical resistance)
Mmd = 26.77       # g (moving mass, WITHOUT radiation mass)
Le = 0.00         # mH (inductance - use 0 for simple model)
Re = 5.30         # ohms (DC resistance)
Nd = 1            # (number of drivers)
```

### Step 3: Configure Enclosure

1. Select **Direct Radiator** as enclosure type
2. Specify baffle dimensions:
   - **Baffle width**: 30 cm (0.3 m)
   - **Baffle height**: 30 cm (0.3 m)
   - This creates a **square baffle** with `f_step ≈ 115/0.3 ≈ 383 Hz`

### Step 4: Configure Simulation

1. Set frequency range: **10 Hz to 10 kHz**
2. Use logarithmic frequency spacing
3. Enable all outputs:
   - SPL
   - Electrical impedance
   - Displacement
   - Phase

### Step 5: Export Results

1. Run the simulation
2. Export results to `.txt` file
3. Save as `sim.txt` in this directory

**File format should be:**
- Tab-separated values
- Include header row
- CRLF or LF line endings (both accepted)

### Step 6: Run Validation

Once `sim.txt` is in place, run:

```bash
PYTHONPATH=src pytest tests/validation/test_baffle_step_hornresp.py -v
```

## Expected Results

The Olson model should match Hornresp within **±2 dB** for:

- Overall step shape (-6 to 0 dB transition)
- Ripple frequencies in the transition region (300-500 Hz)
- Magnitude of diffraction ripples

### Known Differences

Small differences are expected due to:

1. **Baffle geometry**: Olson uses circular baffle, Hornresp may use rectangular
2. **Edge diffraction**: Hornresp may include more complex edge effects
3. **Numerical methods**: Different approximation methods

## Alternative: Compare Infinite vs Finite Baffle

If Hornresp doesn't directly output "baffle step contribution," you can:

1. Run **infinite baffle** simulation → `sim_infinite.txt`
2. Run **finite baffle** simulation (30×30cm) → `sim_finite.txt`
3. The difference is the baffle step effect:
   ```
   baffle_step_effect = SPL_finite - SPL_infinite
   ```

This isolates the baffle diffraction contribution for direct comparison.

## Validation Criteria

Tests check:

- [ ] Low frequency response (~-6 dB at 100 Hz)
- [ ] High frequency response (~0 dB at 5 kHz)
- [ ] Transition near f_step (383 Hz)
- [ ] Diffraction ripples present in transition region
- [ ] Overall shape matches Hornresp (visual inspection)

## Troubleshooting

### "No such file or directory: sim.txt"

The reference data doesn't exist yet. Follow the steps above to create it.

### Tests fail with "Hornresp simulation doesn't match"

1. Verify baffle dimensions are exactly 30×30 cm
2. Check that driver parameters match BC_8NDL51 datasheet
3. Ensure frequency range is 10 Hz - 10 kHz
4. Confirm simulation type is "Direct Radiator"

### Can't install Hornresp

The validation tests will skip gracefully if `sim.txt` is missing.
Unit tests in `tests/unit/test_baffle_step.py` don't require Hornresp.

## References

- Olson (1951) - "Direct Radiator Loudspeaker Enclosures", JAES 2(4)
- Stenzel (1930) - "Circular baffle diffraction theory"
- `literature/crossovers/olson_1951.md` - Olson reference in gsd
- `literature/crossovers/linkwitz_2003.md` - Linkwitz baffle step compensation
- Hornresp User Manual - http://www.hornresp.net/
