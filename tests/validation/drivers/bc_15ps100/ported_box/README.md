# Ported Box Validation - BC_15PS100

## Driver

- **Model**: BC_15PS100
- **Manufacturer**: B&C Speakers
- **Size**: 15"
- **Thiele-Small Parameters**:
  - F_s: 37.3 Hz
  - Q_ts: 0.441
  - V_as: 105.5 L
  - S_d: 855 cm²
  - BL: 21.2 T·m
  - R_e: 5.2 Ω
  - M_md: 147.0 g (driver mass only)

## Test Cases

### Standard Alignments

| Alignment | Vb (L) | Fb (Hz) | Description | Input File | Status |
|-----------|--------|---------|-------------|------------|--------|
| B4 | 105.5 | 37.3 | Butterworth maximally flat | input_b4.txt | Pending |
| QB3 | 84.4 | 29.8 | Quasi-Butterworth 3rd-order | input_qb3.txt | Pending |
| BB4 | 63.3 | 33.6 | Extended bass shelf | input_bb4.txt | Pending |


**Alignment formulas from Thiele (1971):**
- B4: Vb = Vas, Fb = Fs (maximally flat response)
- QB3: Vb ≈ 0.8×Vas, Fb ≈ 0.8×Fs (quasi-Butterworth 3rd-order)
- BB4: Vb ≈ 0.6×Vas, Fb ≈ 0.9×Fs (extended bass shelf)

### Port Dimension Sweeps (B4 Alignment)

| Port Dia | Port Area (cm²) | Port Length (cm) | Description | Input File | Status |
|----------|-----------------|------------------|-------------|------------|--------|
| 2.0" | 20.3 | 2.0 | 2.0″ port | input_port_2in.txt | Pending |
| 3.0" | 45.6 | 6.0 | 3.0″ port | input_port_3in.txt | Pending |
| 4.0" | 81.1 | 12.1 | 4.0″ port | input_port_4in.txt | Pending |


**Port length calculated using `calculate_port_length_for_area()` to achieve Fb tuning.**

## Files

### Hornresp Input Files (Generated)
- `input_b4.txt` - B4
- `input_qb3.txt` - Qb3
- `input_bb4.txt` - Bb4
- `input_port_2in.txt` - Port 2In
- `input_port_3in.txt` - Port 3In
- `input_port_4in.txt` - Port 4In

### Hornresp Simulation Results
- `sim_*.txt` - **YOU NEED TO GENERATE THESE** (one at a time per test case)

## How to Generate Hornresp Data

### For Each Test Case:

1. **Open Hornresp and Import**
   - Launch Hornresp
   - File → Open
   - Select the input file (e.g., `input_b4.txt`)

2. **Verify Parameters**
   Check that the following parameters match:
   - Driver parameters (Sd, Bl, Cms, Rms, Mmd, Le, Re)
   - Enclosure type: Vented Box
   - Box volume Vrc
   - Port tuning Fr (should be close to target Fb)
   - Port area Ap and length Lpt

3. **Run Simulation**
   - Click "Calculate" or press Ctrl+L
   - Accept defaults (frequency range 10-20000 Hz, 2.83V input)

4. **Export Results**
   - File → Save
   - Select "Export _sim.txt" format
   - Save as `sim_<test_case>.txt` in this directory
   - For example: `input_b4.txt` → `sim_b4.txt`

5. **Run Validation Tests** (once all sim.txt files are generated)
   ```bash
   PYTHONPATH=src pytest tests/validation/test_ported_box.py -v
   ```

## Expected Results

Based on sealed box validation results and ported box preliminary validation:

- **System parameters (α, h, F3)**: <1% error
- **Port tuning frequency**: <0.5 Hz deviation from target Fb
- **Electrical impedance magnitude**: <15% max error (dual peaks region)
- **Electrical impedance phase**: <25° max error
- **Impedance dual peaks**: Should show two peaks at driver Fs and port Fb
- **SPL**: Known limitation if port contribution not implemented (~7-13 dB error at low frequencies)

## Validation Status

- **Hornresp input files**: ✅ Generated
- **Hornresp simulations**: Pending (requires manual Hornresp execution)
- **Validation tests**: Pending (requires sim.txt files)

## Physical Constraints

The ported box design must satisfy:
1. **Port diameter**: Must be small enough to fit inside box (< ½ box dimension)
2. **Port length**: Must be physically realizable (typically 2-50 cm)
3. **Port velocity**: Should be < 5% of speed of sound to avoid chuffing (~17 m/s)
4. **Box volume**: Must be large enough for driver to physically fit

All test cases in this validation satisfy these constraints.

## Literature

- Thiele (1971) - Loudspeakers in Vented Boxes Parts 1 & 2
- Small (1973) - Vented-Box Loudspeaker Systems Part I: Analysis
- `literature/thiele_small/thiele_1971_vented_boxes.md`

## Notes

- All Hornresp input files were generated using `gsd.hornresp.export.export_to_hornresp()`
- This ensures driver parameters match exactly between gsd and Hornresp
- Port dimensions calculated using `calculate_port_length_for_area()` from Helmholtz resonance formula
- Test cases validate Thiele (1971) alignment theory for both drivers
- Port sweeps validate port physics across different diameter-to-length ratios
- Total 6 test cases: 3 alignments + 3 port sweeps

---
Generated: 2025-12-27 12:58:01
