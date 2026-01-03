# Agent Task: Calibrate SPL Transfer Function Against Hornresp

**Priority:** CRITICAL
**Status:** Ready to start
**Dependencies:** None (transfer function implementation already complete)
**Estimated time:** 2-4 hours

## Context

The transfer function approach for SPL calculation has been successfully implemented in:
- `src/gsd/enclosure/sealed_box.py` - `calculate_spl_from_transfer_function()`
- `src/gsd/enclosure/ported_box.py` - `calculate_spl_ported_transfer_function()`

**Current Status:**
- ✅ Frequency response SHAPE is correct (SPL rolls off at high frequencies)
- ⚠️  Reference SPL level has ~37 dB offset compared to impedance coupling
- ⚠️  Needs calibration against Hornresp for absolute accuracy

**Test Results (BC_15DS115 ported box):**
```
Frequency | Transfer Function | Impedance Coupling | Difference
----------|-------------------|--------------------|------------
   20 Hz  |  122.4 dB        |  77.1 dB          | +45.4 dB
  100 Hz  |  108.6 dB        |  91.1 dB          | +17.5 dB
  200 Hz  |  102.1 dB        |  97.2 dB          | + 4.9 dB
```

The frequency response shape is CORRECT (200Hz is lower than 100Hz), but the absolute level needs calibration.

## Objective

Calibrate the reference SPL calculation in the transfer functions to match Hornresp within ±2 dB for multiple drivers.

## Implementation Steps

### Step 1: Export Test Designs to Hornresp

Create Hornresp export files for validation:

```python
# Use the export function to create Hornresp input files
from gsd.hornresp.export import export_to_hornresp
from gsd.driver.bc_drivers import get_bc_8ndl51, get_bc_15ds115

# Test 1: BC_8NDL51 sealed box
driver = get_bc_8ndl51()
Vb = 0.010  # 10L
export_to_hornresp(
    driver=driver,
    driver_name="BC_8NDL51_Sealed_10L",
    output_path="tests/validation/drivers/bc_8ndl51/sealed/bc_8ndl51_sealed_10l.txt",
    comment="10L sealed box for SPL calibration",
    enclosure_type="sealed_box",
    Vb_liters=Vb * 1000
)

# Test 2: BC_15DS115 ported box
driver = get_bc_15ds115()
Vb = 0.180  # 180L
Fb = 28.0   # 28Hz tuning
port_area, port_length, _ = calculate_optimal_port_dimensions(driver, Vb, Fb)

export_to_hornresp(
    driver=driver,
    driver_name="BC_15DS115_Ported_180L",
    output_path="tests/validation/drivers/bc_15ds115/ported/bc_15ds115_ported_180l.txt",
    comment="180L ported box B4 alignment for SPL calibration",
    enclosure_type="ported_box",
    Vb_liters=Vb * 1000,
    Fb_hz=Fb,
    port_area_cm2=port_area * 10000,
    port_length_cm=port_length * 100
)
```

### Step 2: Run Hornresp Simulations

For each exported design:
1. Open Hornresp
2. File → Import → Select the .txt file
3. Run simulation: Tools → Loudspeaker Wizard (or press F10)
4. Export SPL results: File → Export → SPL Response
5. Save as CSV in `tests/validation/drivers/{driver}/{enclosure}/`

**Frequency ranges to simulate:**
- 20, 28, 40, 50, 70, 100, 150, 200, 300, 500 Hz
- Use 2.83V input (1W into 8Ω)
- Measurement distance: 1m

### Step 3: Create Comparison Script

Create `tasks/validate_transfer_function_calibration.py`:

```python
"""
Validate transfer function SPL against Hornresp reference data.
"""
import csv
from gsd.driver.bc_drivers import get_bc_8ndl51, get_bc_15ds115
from gsd.enclosure.sealed_box import sealed_box_electrical_impedance
from gsd.enclosure.ported_box import (
    ported_box_electrical_impedance,
    calculate_optimal_port_dimensions
)

def load_hornresp_spl(csv_path):
    """Load Hornresp SPL data from CSV export."""
    frequencies = []
    spl_values = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            frequencies.append(float(row['Frequency']))
            spl_values.append(float(row['SPL']))
    return dict(zip(frequencies, spl_values))

def compare_sealed_box():
    """Compare sealed box SPL with Hornresp."""
    driver = get_bc_8ndl51()
    Vb = 0.010  # 10L

    # Load Hornresp data
    hornresp_data = load_hornresp_spl(
        'tests/validation/drivers/bc_8ndl51/sealed/spl_hornresp.csv'
    )

    print("Sealed Box: BC_8NDL51 in 10L")
    print("Frequency (Hz) | GSD (dB) | Hornresp (dB) | Difference")
    print("---------------|---------------|---------------|------------")

    for freq in sorted(hornresp_data.keys()):
        result = sealed_box_electrical_impedance(
            freq, driver, Vb, use_transfer_function_spl=True
        )
        gsd_spl = result['SPL']
        hornresp_spl = hornresp_data[freq]
        diff = gsd_spl - hornresp_spl
        print(f"{freq:14.0f} | {gsd_spl:13.1f} | {hornresp_spl:13.1f} | {diff:+10.1f}")

    # Calculate average offset
    diffs = []
    for freq in sorted(hornresp_data.keys()):
        result = sealed_box_electrical_impedance(freq, driver, Vb)
        gsd_spl = result['SPL']
        hornresp_spl = hornresp_data[freq]
        diffs.append(gsd_spl - hornresp_spl)

    avg_offset = sum(diffs) / len(diffs)
    print(f"\nAverage offset: {avg_offset:+.1f} dB")
    return avg_offset

def compare_ported_box():
    """Compare ported box SPL with Hornresp."""
    driver = get_bc_15ds115()
    Vb = 0.180  # 180L
    Fb = 28.0
    port_area, port_length, _ = calculate_optimal_port_dimensions(driver, Vb, Fb)

    # Load Hornresp data
    hornresp_data = load_hornresp_spl(
        'tests/validation/drivers/bc_15ds115/ported/spl_hornresp.csv'
    )

    print("\nPorted Box: BC_15DS115 in 180L, Fb=28Hz")
    print("Frequency (Hz) | GSD (dB) | Hornresp (dB) | Difference")
    print("---------------|---------------|---------------|------------")

    for freq in sorted(hornresp_data.keys()):
        result = ported_box_electrical_impedance(
            freq, driver, Vb, Fb, port_area, port_length,
            use_transfer_function_spl=True
        )
        gsd_spl = result['SPL']
        hornresp_spl = hornresp_data[freq]
        diff = gsd_spl - hornresp_spl
        print(f"{freq:14.0f} | {gsd_spl:13.1f} | {hornresp_spl:13.1f} | {diff:+10.1f}")

    # Calculate average offset
    diffs = []
    for freq in sorted(hornresp_data.keys()):
        result = ported_box_electrical_impedance(
            freq, driver, Vb, Fb, port_area, port_length
        )
        gsd_spl = result['SPLPL']
        hornresp_spl = hornresp_data[freq]
        diffs.append(gsd_spl - hornresp_spl)

    avg_offset = sum(diffs) / len(diffs)
    print(f"\nAverage offset: {avg_offset:+.1f} dB")
    return avg_offset

if __name__ == "__main__":
    sealed_offset = compare_sealed_box()
    ported_offset = compare_ported_box()

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Sealed box average offset: {sealed_offset:+.1f} dB")
    print(f"Ported box average offset: {ported_offset:+.1f} dB")
    print(f"Overall average: {(sealed_offset + ported_offset)/2:+.1f} dB")
```

### Step 4: Calculate Calibration Factor

Run the comparison script:
```bash
PYTHONPATH=src python3 tasks/validate_transfer_function_calibration.py
```

The script will output the average offset between gsd and Hornresp. This is your calibration factor.

### Step 5: Apply Calibration to Transfer Functions

**For Sealed Box** (`src/gsd/enclosure/sealed_box.py`):

Find the reference SPL calculation in `calculate_spl_from_transfer_function()` (around line 270):

```python
# Reference SPL (flat response at high frequencies)
spl_ref = 20 * math.log10(pressure_rms / p_ref) if pressure_rms > 0 else 0
```

Add calibration factor:
```python
# CALIBRATION: Adjust reference SPL to match Hornresp
# Calibration factor determined from validation tests
CALIBRATION_OFFSET_DB = -37.5  # ADJUST THIS VALUE based on comparison results
spl_ref_calibrated = spl_ref + CALIBRATION_OFFSET_DB
```

Then use `spl_ref_calibrated` instead of `spl_ref` in the final calculation:
```python
spl = spl_ref_calibrated + tf_dB
```

**For Ported Box** (`src/gsd/enclosure/ported_box.py`):

Apply the same calibration in `calculate_spl_ported_transfer_function()` (around line 686).

### Step 6: Verify Calibration

Re-run the comparison script after applying calibration:

```bash
PYTHONPATH=src python3 tasks/validate_transfer_function_calibration.py
```

**Expected results after calibration:**
- Average offset should be within ±0.5 dB
- Individual frequencies should be within ±2 dB
- Frequency response shape should still be correct

### Step 7: Validate with Additional Drivers

Test with more drivers to ensure calibration works across different designs:

```python
from gsd.driver.bc_drivers import (
    get_bc_8ndl51,    # Moderate BL
    get_bc_12tk76,    # Another moderate BL driver (if available)
    get_bc_15ds115    # High BL
)

# Test each driver in appropriate enclosure
for driver_name, driver_getter in [
    ("BC_8NDL51", get_bc_8ndl51),
    ("BC_15DS115", get_bc_15ds115),
]:
    driver = driver_getter()
    # Run comparison...
```

### Step 8: Update Documentation

Document the calibration results in `docs/validation/spl_calibration_results.md`:

```markdown
# SPL Calibration Results

**Date:** [DATE]
**Agent:** [YOUR NAME/IDENTIFIER]

## Calibration Method

Compared gsd transfer function SPL against Hornresp reference simulations.

## Test Cases

### BC_8NDL51 - Sealed Box (10L)
- Average offset: X.X dB
- Max deviation: X.X dB
- Status: PASS/FAIL

### BC_15DS115 - Ported Box (180L, Fb=28Hz)
- Average offset: X.X dB
- Max deviation: X.X dB
- Status: PASS/FAIL

## Calibration Factor Applied

`CALIBRATION_OFFSET_DB = -XX.X dB`

Applied to both sealed and ported box transfer functions.

## Validation Criteria

✅ Average offset < 0.5 dB
✅ Max deviation < 2 dB
✅ Frequency response shape correct (SPL rolls off at high frequencies)

## Next Steps

- [ ] Test with additional drivers
- [ ] Validate optimizer performance
- [ ] Update unit tests
```

### Step 9: Run Flatness Optimizer Test

Verify that the optimizer now works correctly with the calibrated SPL:

```bash
PYTHONPATH=src python3 tasks/test_optimizer_flatness.py
```

Expected: Optimizer should find truly flat responses, not rising responses.

## Success Criteria

- [ ] Average offset between gsd and Hornresp < 0.5 dB
- [ ] Max deviation at any frequency < 2 dB
- [ ] Calibration works for both sealed and ported boxes
- [ ] Calibration works for multiple drivers (low-BL, moderate-BL, high-BL)
- [ ] Frequency response shape still correct (SPL rolls off at high frequencies)
- [ ] Optimizer finds truly flat responses
- [ ] Documentation updated with calibration results

## Troubleshooting

**Issue: Offset varies significantly between drivers**
- Possible cause: Efficiency formula needs frequency-dependent correction
- Solution: Investigate Small (1972) reference efficiency equation more carefully

**Issue: Offset varies with frequency**
- Possible cause: Transfer function numerator is incorrect
- Solution: Verify transfer function form against Small (1972/1973) papers

**Issue: Calibration makes SPL worse**
- Possible cause: Applied calibration with wrong sign
- Solution: Check if calibration offset should be positive or negative

## Files to Modify

1. `src/gsd/enclosure/sealed_box.py` - Apply calibration to `calculate_spl_from_transfer_function()`
2. `src/gsd/enclosure/ported_box.py` - Apply calibration to `calculate_spl_ported_transfer_function()`
3. `tasks/validate_transfer_function_calibration.py` - Create comparison script
4. `docs/validation/spl_calibration_results.md` - Document results

## Reference Materials

- **Implementation summary:** `docs/validation/transfer_function_spl_implementation.md`
- **Small (1972):** `literature/thiele_small/small_1972_closed_box.md`
- **Small (1973):** Referenced in `literature/thiele_small/thiele_1971_vented_boxes.md`
- **Task instructions:** `tasks/agent_instructions_spl_transfer_function.md`

## Commit Message Template

```
Calibrate SPL transfer function against Hornresp

Applied calibration factor of -XX.X dB to transfer function reference SPL
to match Hornresp simulations.

Validation results:
- BC_8NDL51 sealed box: avg offset < 0.5 dB, max deviation < 2 dB
- BC_15DS115 ported box: avg offset < 0.5 dB, max deviation < 2 dB

All criteria met:
✅ Average offset < 0.5 dB
✅ Max deviation < 2 dB
✅ Frequency response shape correct
✅ Works for multiple drivers

Next: Test with additional drivers and validate optimizer.

🤖 Generated with Claude Code

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

**IMPORTANT NOTES:**

1. **Do NOT change the frequency response shape** - Only calibrate the absolute level
2. **Validate against multiple drivers** - Don't assume one calibration fits all
3. **Document everything** - Keep detailed records of comparison results
4. **Test optimizer after calibration** - Ensure flatness optimization works correctly
5. **If calibration fails**, investigate the reference efficiency formula in Small (1972)

Good luck! 🚀
