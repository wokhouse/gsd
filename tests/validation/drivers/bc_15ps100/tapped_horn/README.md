# Tapped Horn Validation Data

## Design

**Driver:** BC 15PS100

**Horn Geometry:**
- Type: Tapped horn (TH mode)
- S1 (throat): 150.0 cm²
- S2 (tap point): 855.0 cm² (at driver)
- S3 (intermediate): 2265.0 cm²
- S4 (mouth): 6000.0 cm²
- L12 (throat→driver): 180.0 cm
- L23 (driver→intermediate): 100.0 cm
- L34 (intermediate→mouth): 100.0 cm
- Total length: 380.0 cm
- Profile: Exponential (all segments)

**Quarter-wave resonance:** ~48 Hz (from upstream length)

## Files

- `params.txt` - Hornresp parameter file (import format)
- `simulation.txt` - Hornresp simulation results

## Simulation Results (Hornresp)

Key characteristics from `simulation.txt`:

- **Passband:** 40-200 Hz
- **Peak SPL:** ~103 dB at 150-200 Hz
- **Electrical impedance peak:** 34.76 Ω at 40 Hz
- **-3 dB points:** ~30 Hz and ~200 Hz (estimated)

## Validation Status

✓ Horn geometry parameters match between gsd and Hornresp
✓ Driver TS parameters match
✓ Acoustic impedance at tap point implemented in gsd

⏳ **NOT YET IMPLEMENTED:**
- Full system response coupling
- Electrical impedance calculation
- SPL output calculation
- Cone excursion calculation

## Next Steps

To complete validation, implement the following in gsd:

1. `tapped_horn_system_response()` function in `tapped_horn_theory.py`
2. Integrate with `horn_driver_integration.py` for electrical impedance
3. Add SPL and excursion calculations
4. Compare results with Hornresp simulation.txt

## References

- `literature/horns/tapped_horn_theory.md` - Theory documentation
- `src/gsd/simulation/tapped_horn_theory.py` - Current implementation
- Hornresp manual: TH (tapped horn) option
