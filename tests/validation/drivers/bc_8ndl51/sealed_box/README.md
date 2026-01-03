# Sealed Box Validation - BC 8NDL51

## Driver

- **Model**: BC 8NDL51-8
- **Manufacturer**: B&C Speakers
- **Size**: 8"
- **Thiele-Small Parameters**:
  - F_s: 75.0 Hz
  - Q_ts: 0.616
  - V_as: 10.1 L
  - S_d: 232 cm²
  - BL: 7.3 T·m
  - R_e: 6.2 Ω
  - M_md: 26.77 g (driver mass only)

## Test Cases

### Qtc Alignments

| Qtc  | Vb (L) | Fc (Hz) | Alignment Type       | Input File         | Status        |
|------|--------|---------|----------------------|--------------------|---------------|
| 0.65 | 87.83  | 79.2    | Near Butterworth     | input_qtc0.65.txt  | Pending       |
| 0.71 | 31.65  | 86.1    | Butterworth (B4)     | input_qtc0.707.txt | ✅ Validated  |
| 0.80 | 14.66  | 97.5    | Slight overdamp      | input_qtc0.8.txt   | Pending       |
| 1.00 | 6.16   | 121.8   | Critical damped      | input_qtc1.0.txt   | Pending       |
| 1.10 | 4.60   | 134.0   | Overdamped           | input_qtc1.1.txt   | Pending       |

### Non-Optimal Volumes

| Vb (L) | Qtc   | Fc (Hz) | Description           | Input File       | Status  |
|--------|-------|---------|-----------------------|------------------|---------|
| 20.0   | 0.755 | 92.0    | Between Qtc 0.8-1.0   | input_vb20L.txt   | Pending  |

## Files

### Hornresp Input Files (Generated)
- `input_qtc0.65.txt` - Qtc=0.65 alignment (large box, near Butterworth)
- `input_qtc0.707.txt` - Qtc=0.707 Butterworth alignment (validated ✅)
- `input_qtc0.8.txt` - Qtc=0.8 alignment (slight overdamp)
- `input_qtc1.0.txt` - Qtc=1.0 alignment (critically damped)
- `input_qtc1.1.txt` - Qtc=1.1 alignment (overdamped)
- `input_vb20L.txt` - Non-optimal 20L volume

### Hornresp Simulation Results
- `sim.txt` - **YOU NEED TO GENERATE THIS** (one at a time per test case)

## How to Generate Hornresp Data

### For Each Test Case:

1. **Open Hornresp and Import**
   - Launch Hornresp
   - File → Open
   - Select the input file (e.g., `input_qtc0.65.txt`)

2. **Verify Parameters**
   You should see the driver parameters and enclosure configuration.

3. **Run Simulation**
   - Click "Calculate" or press Ctrl+L
   - Accept defaults (frequency range 10-20000 Hz, 2.83V input)

4. **Export Results**
   - File → Save
   - Select "Export _sim.txt" format
   - Save as `sim.txt` in this directory (will overwrite previous)
   - **Tip**: Rename to keep multiple results (e.g., `sim_qtc0.65.txt`)

5. **Run Validation Tests**
   ```bash
   PYTHONPATH=src pytest tests/validation/test_sealed_box.py::TestSealedBoxQtcAlignmentsBC8NDL51 -v
   ```

## Expected Results

Based on existing Butterworth validation (Qtc=0.707):
- **Electrical impedance magnitude:** <8% max error (typical: 5-8%)
- **Electrical impedance phase:** <20° max error
- **SPL:** Known limitation (~19-24 dB error due to Hornresp internal inconsistency)
- **System parameters (Fc, Qtc):** <0.5 Hz, <0.02 tolerance ✅

## Validation Status

- **System parameter tests**: All 9 test cases implemented and passing
- **Hornresp validation**: 1 case validated (Qtc=0.707 Butterworth)
- **Pending validation**: 8 cases require Hornresp sim.txt generation

## Literature

- Small (1972) - Closed-Box Loudspeaker Systems Part I: Analysis
- `literature/thiele_small/small_1972_closed_box.md`

## Notes

- All Hornresp input files were generated using `gsd.hornresp.export.export_to_hornresp()`
- This ensures driver parameters match exactly between gsd and Hornresp
- Qtc values tested range from 0.65 (underdamped) to 1.1 (overdamped)
- Minimum achievable Qtc is 0.616 (infinite baffle, Qts)
- Tests validate Small (1972) sealed box theory across different alignments
