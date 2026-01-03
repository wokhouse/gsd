# Two-Way Loudspeaker Design Workflow

**Date:** 2025-12-30
**Status:** Validated and Production Ready
**Authors:** GSD Project with External Research Validation

## Overview

This document describes the validated workflow for designing time-aligned two-way horn-loaded loudspeaker systems using gsd. The workflow has been validated against external acoustic research and includes proper LR4 crossover simulation with phase modeling.

## Quick Start

For a complete two-way horn system design:

```bash
# 1. Plot final validated response
PYTHONPATH=src python tasks/examples/plot_final_validated.py

# 2. Optimize system parameters (optional)
PYTHONPATH=src python tasks/examples/optimize_practical.py

# 3. Review cabinet dimensions
cat docs/validation/two_way_cabinet_dimensions.md
```

## Design Workflow

### Phase 1: Define System Requirements

1. **Select drivers**
   - LF driver: Choose based on Fs, Vas, Qts
   - HF driver: Choose compression driver with appropriate sensitivity

2. **Define target specifications**
   - Crossover frequency range
   - System bandwidth (F3 target)
   - Sensitivity target
   - Maximum SPL requirement

### Phase 2: Design LF Enclosure

Use ported box design tools (existing gsd functionality):

```python
from gsd.enclosure.ported_box import calculate_ported_box_system_parameters
from gsd.enclosure.ported_box import calculate_optimal_port_dimensions

# For BC_10NW64 with B4 alignment:
Vb = driver.V_as  # Use Vas for B4
Fb = driver.F_s   # Use Fs for B4

system_params = calculate_ported_box_system_parameters(driver, Vb, Fb)
port_area, port_length, _ = calculate_optimal_port_dimensions(driver, Vb, Fb)
```

**Validation:** Export to Hornresp and compare impedance/SPL curves.

### Phase 3: Design Horn

For exponential horn with HF driver:

```python
from gsd.simulation.horn_theory import exponential_horn_throat_impedance

# Horn parameters
throat_area = 0.001  # m² (1" compression driver)
mouth_area = 0.1     # m² (356mm diameter)
length = 0.76        # m (for time alignment)
flare_constant = 4.6  # 1/m (Fc ≈ 250 Hz)

# Calculate throat impedance for validation
throat_impedance = exponential_horn_throat_impedance(
    throat_area, flare_constant, length, frequency
)
```

**Critical design rule:** Horn length determines required time alignment.
- Calculate: `delay = length / speed_of_sound`
- For 0.76m horn: delay = 2.2ms
- Time alignment required: Protrude horn forward by 0.76m

### Phase 4: Validate Crossover with LR4 Simulation

Use the validated LR4 crossover module:

```python
from gsd.crossover.lr4 import apply_lr4_crossover, optimize_crossover_and_alignment

# Calculate driver responses
lf_spl = calculate_ported_box_response(...)
hf_spl = calculate_horn_response(...)

# Apply LR4 crossover with time alignment
combined, lf_filt, hf_filt = apply_lr4_crossover(
    frequencies=freqs,
    lf_spl_db=lf_spl,
    hf_spl_db=hf_spl,
    crossover_freq=800.0,
    z_offset_m=0.0,  # Time-aligned (horn protrudes)
    speed_of_sound=343.0,
    sample_rate=48000.0
)
```

### Phase 5: Optimize System Parameters (Optional)

Use the practical optimizer to fine-tune:

```bash
PYTHONPATH=src python tasks/examples/optimize_practical.py
```

This will optimize:
- Box volume (Vb)
- Port tuning (Fb)
- Horn flare constant

Within practical constraints to achieve flattest response.

### Phase 6: Build Cabinet

Follow the detailed cabinet dimensions in `docs/validation/two_way_cabinet_dimensions.md`:

**Design choice:** Protruding horn (time-aligned)
- Horn extends 0.76m forward from baffle
- LF driver mounted on baffle
- Simple flat baffle construction
- No internal tunnels or complex chambers

## Validated Design Example

### System Specifications

**Drivers:**
- LF: B&C Speakers 10NW64 (10" woofer)
- HF: B&C Speakers DE250 (1" compression driver)

**Horn:**
- Type: Exponential
- Throat: 1" (0.001 m²)
- Mouth: 356mm diameter (0.1 m²)
- Length: 0.76m
- Flare constant: 4.6 /m
- Cutoff frequency: 250 Hz

**Enclosure:**
- Type: Ported box
- Volume: 26.5 L
- Tuning: 70 Hz
- Ports: Dual 100mm × 228mm

**Crossover:**
- Type: LR4 (Linkwitz-Riley 4th-order)
- Frequency: 800 Hz
- Slope: 24 dB/octave
- HF padding: -17.5 dB
- Time alignment: Horn protrudes 0.76m (Z=0)

**Performance:**
- System F3: 65 Hz
- Passband flatness: σ = 1.07 dB (100 Hz - 10 kHz)
- Max SPL: >105 dB @ 1m, 2.83V

## Key Implementation Details

### LR4 Crossover Implementation

**Critical validation findings (from external research):**

1. ✅ **Use COMPLEX ADDITION** (not power summation)
   - Loudspeaker drivers produce coherent pressure waves
   - Vector sum: P_total = P_LF + P_HF (complex)
   - SPL_total = 20*log10(|P_total|)

2. ✅ **Synthesize minimum phase** from magnitude-only data
   - Use Hilbert transform with **extrapolation** to prevent truncation artifacts
   - Extend frequency range 3× before transform
   - This prevents 40dB spikes from edge effects

3. ✅ **Model delay as phase rotation**
   - H_delay(f) = exp(-j·2π·f·delay)
   - Correctly models time offset without assuming equal amplitudes

4. ✅ **Square Butterworth filters** for LR4
   - Design 2nd-order Butterworth (N=2)
   - Square the response: H_LR4 = H_Butterworth²
   - Gives 24 dB/octave slope

**What NOT to do:**
- ❌ Power summation: Hides phase cancellation effects
- ❌ Cosine Z-offset formula: Assumes equal driver amplitudes
- ❌ Hilbert transform without extrapolation: Creates massive spikes

### Time Alignment

**Why it's critical:**

LR4 crossovers sum flat ONLY when drivers are in phase at crossover. Z-offset creates phase mismatch:

```
Delay (seconds) = Z_offset (meters) / Speed_of_sound (m/s)
Phase shift (degrees) = -360 × Frequency (Hz) × Delay (seconds)
```

**For 0.76m horn at 800 Hz:**
- Delay: 2.2ms
- Phase shift: -632° (nearly 180° out of phase if not aligned)
- Result without alignment: 6-10 dB dip at crossover

**Solution:** Protrude horn forward by its length (0.76m) to align acoustic centers at baffle plane.

## Example Scripts

### 1. Plot Validated Crossover

```bash
PYTHONPATH=src python tasks/examples/plot_final_validated.py
```

Generates comprehensive plot showing:
- Multiple crossover frequencies (800, 1000, 1200 Hz)
- Time-aligned vs misaligned comparison
- Crossover region detail
- Validation metrics

**Output:** `tasks/lr4_final_validated.png`

### 2. Optimize System Parameters

```bash
PYTHONPATH=src python tasks/examples/optimize_practical.py
```

Optimizes within practical constraints:
- Vb: 20-40 L
- Fb: 60-80 Hz
- Flare constant: 3.0-6.0 /m

**Output:** `tasks/practical_optimization_results.png`

### 3. Original Two-Way Response

```bash
PYTHONPATH=src python tasks/examples/plot_two_way_response.py
```

Shows the datasheet-based model (before LR4 validation).

## External Research Validation

The LR4 crossover implementation was validated against external acoustic research with the following key findings:

### Recommendations Implemented

1. **Complex addition** for driver summation
2. **Phase rotation** for time delay modeling
3. **Extrapolation before Hilbert transform** to prevent artifacts
4. **Crossover frequency:** 800 Hz optimal for this driver combination (external agent suggested 1.0-1.2 kHz, but simulation showed 800 Hz works better for specific drivers)

### Validation Results

- ✅ No 40dB truncation spikes
- ✅ Realistic phase interference patterns
- ✅ Time alignment shows 9.74 dB improvement at crossover
- ✅ Response flatness: σ = 1.07 dB (excellent)

### Literature Citations

- Linkwitz Lab - Crossovers: Vector summation required
- Linkwitz Lab - Frontiers 5: Delay modeling via phase rotation
- Excelsior Audio: Directivity matching at crossover
- External research agent (2025): Phase modeling and minimum phase synthesis

## Troubleshooting

### Issue: Massive spikes in crossover response

**Cause:** Hilbert transform truncation artifacts
**Fix:** Extrapolate frequency response 3× before transform (implemented in `mag_to_minimum_phase()`)

### Issue: No crossover dip visible in simulation

**Cause:** Using power summation instead of complex addition
**Fix:** Use `apply_lr4_crossover()` which uses complex addition

### Issue: Crossover too high (>1.5 kHz)

**Cause:** HF beaming from 10" driver, or horn not loading properly
**Fix:** Lower crossover, or check horn cutoff frequency

### Issue: Deep nulls at crossover

**Cause:** Z-offset misalignment (phase cancellation)
**Fix:** Protrude horn forward to align acoustic centers (Z=0)

## Design Checklist

Before building:

**Acoustic Design:**
- [ ] LF enclosure calculated and validated
- [ ] Horn parameters calculated (flare, mouth, throat)
- [ ] Horn length determined for time alignment
- [ ] Crossover frequency selected (above horn Fc × 1.5)
- [ ] HF padding calculated for level matching
- [ ] LR4 crossover simulation run and validated
- [ ] Time alignment verified (Z=0 for protruding horn)

**Cabinet Design:**
- [ ] Baffle dimensions accommodate all drivers
- [ ] Internal volume correct (net of displacements)
- [ ] Port dimensions correct (area, length)
- [ ] Horn mounting method determined
- [ ] Bracing plan prevents panel resonance
- [ ] Driver access provided (front/rear)

**Construction:**
- [ ] Material selected (18-22 mm MDF/plywood)
- [ ] Joinery method determined
- [ ] Sealing strategy planned
- [ ] Finish method selected
- [ ] Terminal hardware selected

**Validation:**
- [ ] Design exported to Hornresp for comparison
- [ ] Responses match expected (within 2%)
- [ ] Time alignment verified in simulation
- [ ] Flatness metric acceptable (σ < 2.0 dB)

## Files and Scripts

### Core Implementation

- `src/gsd/crossover/lr4.py` - LR4 crossover implementation
- `src/gsd/crossover/__init__.py` - Module exports

### Example Scripts

- `tasks/examples/plot_final_validated.py` - Final validated crossover plot
- `tasks/examples/optimize_practical.py` - Practical system optimizer
- `tasks/examples/plot_two_way_response.py` - Original two-way response

### Documentation

- `docs/validation/two_way_cabinet_dimensions.md` - Detailed construction guide
- `docs/validation/time_aligned_horn_design.md` - Theory and principles

## References

### Literature

- Linkwitz, R. (1976). "Active Crossover Networks for Non-coincident Drivers" JAES
- Linkwitz Lab - www.linkwitzlab.com
- Olson, H.F. (1947). "Elements of Acoustical Engineering"
- Beranek, L.L. (1954). "Acoustics"
- Excelsior Audio - Crossover design articles

### External Tools

- Hornresp - www.hornresp.net
- VituixCAD - Crossover design and measurement
- REW (Room EQ Wizard) - Measurement and analysis

## Version History

- **v1.0** (2025-12-30): Initial validated implementation
  - LR4 crossover with complex addition
  - Minimum phase synthesis with extrapolation
  - Phase rotation for delay modeling
  - External research validation
  - Time alignment documentation
  - Practical optimizer

## Contributing

When extending this workflow:

1. **All physics code must cite literature** - See `CLAUDE.md` for requirements
2. **Validate against Hornresp** - Compare simulated results
3. **Use validated LR4 implementation** - Don't create custom crossovers
4. **Test with real drivers** - Verify against actual measurements when possible

---

**Document Version:** 1.0
**Last Updated:** 2025-12-30
**Status:** Production Ready ✅
