# Agent Task: Update Optimizer to Use Calibrated Transfer Functions

**Priority:** HIGH
**Status:** Ready to start
**Dependencies:** SPL calibration complete (-25.25 dB applied to transfer functions)
**Estimated time:** 1-2 hours

## Context

The SPL transfer function has been successfully calibrated against Hornresp with a -25.25 dB offset. However, the flatness optimizer in `src/gsd/optimization/objectives/response_metrics.py` is currently using `direct_radiator_electrical_impedance` (infinite baffle model) instead of the calibrated sealed/ported box transfer functions.

**Current Issue:**
- Optimizer uses infinite baffle SPL calculation
- Does not benefit from the calibrated transfer function
- Shows rising response artifacts (old impedance coupling bug)

**Required Fix:**
- Update optimizer to use `sealed_box_electrical_impedance()` for sealed boxes
- Update optimizer to use `ported_box_electrical_impedance()` for ported boxes
- Both MUST use `use_transfer_function_spl=True` to get calibrated SPL

## Objective

Update the response flatness optimizer to use the calibrated transfer function SPL calculation, ensuring correct frequency response modeling for enclosure optimization.

## Current Implementation

**File:** `src/gsd/optimization/objectives/response_metrics.py`

**Current Code (lines 95-150):**
```python
def objective_response_flatness(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    frequency_range: Tuple[float, float] = (20.0, 500.0),
    n_points: int = 100,
    voltage: float = 2.83
) -> float:
    # ... documentation ...

    if enclosure_type == "sealed":
        Vb = design_vector[0]

        # Calculate SPL across frequency range
        for freq in frequencies:
            result = direct_radiator_electrical_impedance(
                freq, driver, voltage=voltage, measurement_distance=1.0
            )
            spl_values.append(result['SPL'])

    elif enclosure_type == "ported":
        Vb = design_vector[0]
        Fb = design_vector[1]

        # Calculate SPL across frequency range
        for freq in frequencies:
            result = direct_radiator_electrical_impedance(
                freq, driver, voltage=voltage, measurement_distance=1.0
            )
            spl_values.append(result['SPL'])
```

**Problem:** Uses `direct_radiator_electrical_impedance()` which:
- Models infinite baffle (no box compliance effects)
- Uses impedance coupling method for SPL
- Does not benefit from transfer function calibration

## Implementation Steps

### Step 1: Import Required Functions

Add these imports at the top of the file:

```python
from gsd.enclosure.sealed_box import sealed_box_electrical_impedance
from gsd.enclosure.ported_box import ported_box_electrical_impedance
from gsd.enclosure.ported_box import calculate_optimal_port_dimensions
```

### Step 2: Update Sealed Box Branch

**Find the sealed box section** (around line 140-150) and replace:

**OLD CODE:**
```python
if enclosure_type == "sealed":
    Vb = design_vector[0]

    for freq in frequencies:
        result = direct_radiator_electrical_impedance(
            freq, driver, voltage=voltage, measurement_distance=1.0
        )
        spl_values.append(result['SPL'])
```

**NEW CODE:**
```python
if enclosure_type == "sealed":
    Vb = design_vector[0]

    for freq in frequencies:
        result = sealed_box_electrical_impedance(
            freq, driver, Vb, voltage=voltage, measurement_distance=1.0,
            use_transfer_function_spl=True  # CRITICAL: Use calibrated transfer function
        )
        spl_values.append(result['SPL'])
```

### Step 3: Update Ported Box Branch

**Find the ported box section** (around line 150-165) and replace:

**OLD CODE:**
```python
elif enclosure_type == "ported":
    Vb = design_vector[0]
    Fb = design_vector[1]

    for freq in frequencies:
        result = direct_radiator_electrical_impedance(
            freq, driver, voltage=voltage, measurement_distance=1.0
        )
        spl_values.append(result['SPL'])
```

**NEW CODE:**
```python
elif enclosure_type == "ported":
    Vb = design_vector[0]
    Fb = design_vector[1]

    # Auto-calculate optimal port dimensions if not in design vector
    if len(design_vector) == 2:
        port_area, port_length, _ = calculate_optimal_port_dimensions(driver, Vb, Fb)
    else:
        # Use provided port dimensions
        port_area = design_vector[2]
        port_length = design_vector[3]

    for freq in frequencies:
        result = ported_box_electrical_impedance(
            freq, driver, Vb, Fb, port_area, port_length,
            voltage=voltage, measurement_distance=1.0,
            use_transfer_function_spl=True  # CRITICAL: Use calibrated transfer function
        )
        spl_values.append(result['SPL'])
```

### Step 4: Update Infinite Baffle Branch

**For infinite baffle**, the current implementation is actually correct. Keep using `direct_radiator_electrical_impedance()` since there's no box compliance to model.

**No changes needed for infinite baffle.**

### Step 5: Test the Optimizer

Run the flatness optimizer test:

```bash
PYTHONPATH=src python3 tasks/test_optimizer_flatness.py
```

**Expected Results:**
- Optimizer should find TRULY flat responses
- SPL should roll off at high frequencies (not rise!)
- Standard deviation should be reasonable (3-6 dB for typical designs)

**Before Fix (Expected Current Behavior):**
```
Freq (Hz) | SPL (dB) | Note
20 Hz     | 93 dB    |
100 Hz    | 79 dB    |
200 Hz    | 73 dB    |
✗ Response ROLLS OFF (correct shape) but absolute level may be off
```

**After Fix (Expected New Behavior):**
```
Freq (Hz) | SPL (dB) | Note
20 Hz     | 85 dB    |
50 Hz     | 82 dB    |
100 Hz    | 81 dB    |
200 Hz    | 78 dB    |
✓ Response is FLAT with correct roll-off at high frequencies
✓ Absolute SPL level is calibrated (-25.25 dB)
```

### Step 6: Verify with Multiple Drivers

Test with different drivers to ensure the optimizer works correctly:

```python
from gsd.driver.bc_drivers import get_bc_8ndl51, get_bc_15ds115

# Test BC_8NDL51 sealed box
driver = get_bc_8ndl51()
Vb = 0.020  # 20L

# Test BC_15DS115 ported box
driver = get_bc_15ds115()
Vb = 0.180  # 180L
Fb = 28.0   # 28Hz
```

**Expected:** Both drivers show flat responses when optimized.

## Validation Criteria

After updating the optimizer, the following criteria must be met:

1. **Frequency Response Shape**
   - ✅ Response is flat in the passband (not rising with frequency)
   - ✅ Response rolls off at high frequencies (mass-controlled region)
   - ✅ Response shows proper tuning characteristics for ported boxes

2. **Absolute SPL Level**
   - ✅ SPL values are calibrated (within ±25 dB of Hornresp)
   - ✅ Average SPL is reasonable (70-90 dB for 1W/1m in passband)
   - ✅ No double-counting of radiation effects

3. **Optimizer Behavior**
   - ✅ Optimizer minimizes flatness metric correctly
   - ✅ Chooses reasonable designs (not extreme volumes)
   - ✅ Works for both sealed and ported boxes

4. **No Regressions**
   - ✅ Code still runs without errors
   - ✅ Design vectors are handled correctly
   - ✅ Port dimensions are auto-calculated if not provided

## Common Pitfalls

### Pitfall 1: Forgetting `use_transfer_function_spl=True`

**Symptom:** SPL shows rising response (old bug)

**Fix:** Always specify `use_transfer_function_spl=True` when calling:
- `sealed_box_electrical_impedance()`
- `ported_box_electrical_impedance()`

### Pitfall 2: Not Providing Port Dimensions

**Symptom:** `TypeError: missing required argument 'port_area'`

**Fix:** Auto-calculate port dimensions using `calculate_optimal_port_dimensions()`:

```python
port_area, port_length, _ = calculate_optimal_port_dimensions(driver, Vb, Fb)
```

### Pitfall 3: Using Infinite Baffle for Sealed/Ported Boxes

**Symptom:** No box compliance effects (wrong Fc, wrong Fb)

**Fix:** Use the correct function for each enclosure type:
- Sealed box → `sealed_box_electrical_impedance()`
- Ported box → `ported_box_electrical_impedance()`
- Infinite baffle → `direct_radiator_electrical_impedance()` (keep this one)

## Files to Modify

1. **`src/gsd/optimization/objectives/response_metrics.py`**
   - Update imports (Step 1)
   - Update sealed box branch (Step 2)
   - Update ported box branch (Step 3)

## Files to Reference

- **Current implementation:** `src/gsd/enclosure/sealed_box.py` (lines 280-605)
- **Current implementation:** `src/gsd/enclosure/ported_box.py` (lines 884-1413)
- **Calibration documentation:** `tasks/SPL_CALIBRATION_RESULTS.md`
- **Test script:** `tasks/test_optimizer_flatness.py`

## Testing Checklist

- [ ] Run `tasks/test_optimizer_flatness.py`
- [ ] Verify frequency response shape is correct (flat with high-freq roll-off)
- [ ] Verify SPL level is calibrated (reasonable absolute values)
- [ ] Test with BC_8NDL51 sealed box
- [ ] Test with BC_15DS115 ported box
- [ ] Verify optimizer chooses reasonable designs
- [ ] Check for any errors or warnings

## Success Criteria

The optimizer update is successful when:

1. ✅ Flatness optimizer uses transfer function SPL calculation
2. ✅ Frequency response shape is correct (no rising response bug)
3. ✅ SPL values are calibrated against Hornresp
4. ✅ Optimizer works for both sealed and ported boxes
5. ✅ No errors or exceptions during execution
6. ✅ Test output shows truly flat responses when optimized

## Troubleshooting

**Issue: "ImportError: cannot import name 'sealed_box_electrical_impedance'"**
- **Cause:** Missing import statement
- **Fix:** Add import: `from gsd.enclosure.sealed_box import sealed_box_electrical_impedance`

**Issue: "TypeError: missing required argument 'port_area'"**
- **Cause:** Port dimensions not provided for ported box
- **Fix:** Auto-calculate using `calculate_optimal_port_dimensions()` or include in design vector

**Issue: Optimizer chooses extreme designs (very large or very small boxes)**
- **Cause:** May be due to frequency range or optimization metric
- **Fix:** Check frequency range is appropriate (20-200Hz for bass optimization)

**Issue: SPL values are way too high (> 120 dB)**
- **Cause:** Not using transfer function (use_transfer_function_spl=False or missing)
- **Fix:** Ensure `use_transfer_function_spl=True` is specified

## Commit Message Template

```
Update optimizer to use calibrated transfer function SPL

Fixed flatness optimizer to use sealed/ported box transfer functions
instead of infinite baffle model. This ensures:

- Correct frequency response shape (flat in passband, rolls off at high freq)
- Calibrated absolute SPL level (-25.25 dB offset from Hornresp)
- Proper box compliance effects for sealed and ported enclosures

Changes:
- objective_response_flatness() now calls sealed_box_electrical_impedance()
  for sealed boxes with use_transfer_function_spl=True
- objective_response_flatness() now calls ported_box_electrical_impedance()
  for ported boxes with use_transfer_function_spl=True
- Port dimensions auto-calculated if not in design vector
- Infinite baffle still uses direct_radiator_electrical_impedance()

Testing:
- Verified flatness optimizer finds truly flat responses
- Checked SPL rolls off at high frequencies (no rising response)
- Tested with BC_8NDL51 sealed and BC_15DS115 ported

Related: SPL calibration task (tasks/SPL_CALIBRATION_RESULTS.md)

🤖 Generated with Claude Code

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

## Reference Materials

- **SPL Calibration Results:** `tasks/SPL_CALIBRATION_RESULTS.md`
- **Sealed Box Transfer Function:** `src/gsd/enclosure/sealed_box.py:143-277`
- **Ported Box Transfer Function:** `src/gsd/enclosure/ported_box.py:509-693`
- **Optimizer Test:** `tasks/test_optimizer_flatness.py`
- **Original Task:** `tasks/agent_instructions_spl_transfer_function.md`

---

**IMPORTANT NOTES:**

1. **ALWAYS specify `use_transfer_function_spl=True`** when calling sealed/ported box functions
2. **Auto-calculate port dimensions** if not in design vector
3. **Keep infinite baffle implementation** unchanged (it's correct as-is)
4. **Test thoroughly** with both sealed and ported boxes after changes
5. **Verify frequency response shape** is correct (flat with roll-off, not rising)

Good luck! 🚀
