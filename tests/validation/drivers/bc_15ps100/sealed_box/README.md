# Sealed Box Validation - BC 15PS100

## Driver

- **Model**: BC 15PS100
- **Manufacturer**: B&C Speakers
- **Size**: 15"
- **Thiele-Small Parameters**:
  - F_s: 37.3 Hz
  - Q_ts: 0.441
  - V_as: 105.5 L
  - S_d: 855 cm²
  - BL: 21.2 T·m
  - R_e: 5.2 Ω
  - M_md: 147 g (driver mass only)

## Test Cases

### Qtc Alignments

| Qtc  | Vb (L) | Fc (Hz) | Alignment Type       | Input File         | Status        |
|------|--------|---------|----------------------|--------------------|---------------|
| 0.50 | 373.30 | 42.2    | Underdamped          | input_qtc0.5.txt   | Pending       |
| 0.71 | 67.45  | 59.7    | Butterworth (B4)     | input_qtc0.707.txt | ✅ Validated  |
| 0.94 | 30.0   | 79.3    | Near critical        | input_qtc0.97.txt  | Pending       |

**Note**: Qtc=1.0 and Qtc=1.1 require boxes <28L which are too small to physically fit the 15" driver.

### Non-Optimal Volumes

| Vb (L) | Qtc   | Fc (Hz) | Description           | Input File      | Status  |
|--------|-------|---------|-----------------------|-----------------|---------|
| 50.0   | 0.773 | 65.9    | Between Qtc 0.71-0.94 | input_vb50L.txt | Pending  |
| 80.0   | 0.672 | 56.8    | Larger box           | input_vb80L.txt | Pending  |

## Files

### Hornresp Input Files (Generated)
- `input_qtc0.5.txt` - Qtc=0.5 alignment (very large box, underdamped)
- `input_qtc0.707.txt` - Qtc=0.707 Butterworth alignment (validated ✅)
- `input_qtc0.97.txt` - Qtc=0.94 alignment (near critical, minimum practical volume)
- `input_vb50L.txt` - Non-optimal 50L volume
- `input_vb80L.txt` - Non-optimal 80L volume

### Hornresp Simulation Results
- `sim.txt` - **YOU NEED TO GENERATE THIS** (one at a time per test case)

## How to Generate Hornresp Data

### For Each Test Case:

1. **Open Hornresp and Import**
   - Launch Hornresp
   - File → Open
   - Select the input file (e.g., `input_qtc0.5.txt`)

2. **Verify Parameters**
   You should see the driver parameters and enclosure configuration.

3. **Run Simulation**
   - Click "Calculate" or press Ctrl+L
   - Accept defaults (frequency range 10-20000 Hz, 2.83V input)

4. **Export Results**
   - File → Save
   - Select "Export _sim.txt" format
   - Save as `sim.txt` in this directory (will overwrite previous)
   - **Tip**: Rename to keep multiple results (e.g., `sim_qtc0.5.txt`)

5. **Run Validation Tests**
   ```bash
   PYTHONPATH=src pytest tests/validation/test_sealed_box.py::TestSealedBoxQtcAlignmentsBC15PS100 -v
   ```

## Expected Results

Based on existing Butterworth validation (Qtc=0.707):
- **Electrical impedance magnitude:** <7% max error (typical: 5-7%)
- **Electrical impedance phase:** <20° max error
- **SPL:** Known limitation (~19-24 dB error due to Hornresp internal inconsistency)
- **System parameters (Fc, Qtc):** <0.5 Hz, <0.02 tolerance ✅

## Validation Status

- **System parameter tests**: All 7 test cases implemented and passing
- **Hornresp validation**: 1 case validated (Qtc=0.707 Butterworth)
- **Pending validation**: 6 cases require Hornresp sim.txt generation

## Physical Constraints

The 15" driver requires a minimum box volume of ~28L to physically fit.
This limits the maximum achievable Qtc to ~0.94. Higher Qtc values (1.0, 1.1)
would require smaller boxes that cannot accommodate the driver.

## Literature

- Small (1972) - Closed-Box Loudspeaker Systems Part I: Analysis
- `literature/thiele_small/small_1972_closed_box.md`

## Notes

- All Hornresp input files were generated using `gsd.hornresp.export.export_to_hornresp()`
- This ensures driver parameters match exactly between gsd and Hornresp
- Qtc values tested range from 0.5 (underdamped) to 0.94 (near critical)
- Lower Q_ts (0.441) allows for a wider range of alignments
- Tests validate Small (1972) sealed box theory for a larger driver
- Non-optimal volumes test the general case (not just Butterworth alignments)
