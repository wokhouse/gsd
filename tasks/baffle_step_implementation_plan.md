# Baffle Step Implementation Plan

**Date:** 2025-12-30
**Status:** READY TO IMPLEMENT
**Priority:** HIGH - Addresses critical validation gaps

---

## Executive Summary

The baffle step physics code has been **corrected** (PR #39), but three critical items remain:

1. **Unit tests** missing for `baffle_step.py` module
2. **Hornresp validation** not yet performed
3. **Two-way system** doesn't use baffle step correction

This plan addresses these gaps to complete the baffle step implementation.

---

## Background

From `docs/validation/baffle_step_fixes.md`, the baffle step implementation was corrected with:

- **Fixed physics formula** - Changed from piston directivity (incorrect) to Stenzel circular baffle model
- **Created literature files** - `olson_1951.md`, `linkwitz_2003.md`
- **Clarified physics vs compensation** - Proper docstrings explaining the phenomenon

**Current Status:**
- ✅ Code corrected in `src/gsd/enclosure/baffle_step.py`
- ✅ Literature files created
- ✅ Manual test script exists (`tasks/test_baffle_step_olson.py`)
- ❌ No pytest unit tests
- ❌ No Hornresp validation
- ❌ Two-way scripts don't use baffle step

---

## Task 1: Create Unit Tests for `baffle_step.py`

**Priority:** HIGH
**Estimated Complexity:** MEDIUM
**Dependencies:** None

### Goal

Create comprehensive pytest unit tests in `tests/unit/test_baffle_step.py`.

### Test Coverage Required

1. **`baffle_step_frequency()`**
   - Test empirical formula: f_step = 115 / width
   - Test edge cases: very small/large baffles

2. **`baffle_step_loss()` (Linkwitz model)**
   - Low frequency behavior (< f_step): should be ~-6 dB
   - High frequency behavior (> f_step): should be ~0 dB
   - At f_step: should be ~-3 dB
   - Test with array inputs (vectorization)

3. **`baffle_step_loss_olson()` (Olson/Stenzel model)**
   - Low frequency (ka << 1): ~-6 dB (4π space)
   - High frequency (ka >> 1): ~0 dB (2π space)
   - Test diffraction ripples exist
   - Test with rectangular baffles (width ≠ height)

4. **`baffle_step_compensation()`**
   - Low frequency: +6 dB boost
   - High frequency: 0 dB
   - Should be inverse of physics response

5. **`estimate_baffle_width()`**
   - Test volume to width conversion
   - Test different aspect ratios

6. **Integration test: `apply_baffle_step_to_spl()`**
   - Test physics mode: LF attenuated, HF unchanged
   - Test compensator mode: LF boosted, HF attenuated
   - Test both Linkwitz and Olson models

### Acceptance Criteria

- All tests pass with `PYTHONPATH=src pytest tests/unit/test_baffle_step.py`
- Test coverage > 90% for the module
- Tests validate physics behavior (not just code execution)

### Implementation Notes

```python
# File: tests/unit/test_baffle_step.py
import pytest
import numpy as np
from gsd.enclosure.baffle_step import (
    baffle_step_frequency,
    baffle_step_loss,
    baffle_step_loss_olson,
    baffle_step_compensation,
    estimate_baffle_width,
    apply_baffle_step_to_spl,
)

class TestBaffleStepFrequency:
    def test_empirical_formula(self):
        # f_step = 115 / width
        result = baffle_step_frequency(0.3)  # 30cm baffle
        assert result == pytest.approx(383.3, rel=0.01)

class TestBaffleStepLoss:
    def test_low_frequency_4pi_space(self):
        # Below f_step: radiates into 4π space, -6 dB
        loss = baffle_step_loss(50, 0.3)
        assert loss < -5.0  # ~-6 dB

    def test_high_frequency_2pi_space(self):
        # Above f_step: radiates into 2π space, 0 dB
        loss = baffle_step_loss(5000, 0.3)
        assert abs(loss) < 0.5  # ~0 dB

    def test_at_step_frequency(self):
        # At f_step: -3 dB point
        f_step = baffle_step_frequency(0.3)
        loss = baffle_step_loss(f_step, 0.3)
        assert abs(loss - (-3.0)) < 0.5  # ~-3 dB

class TestBaffleStepLossOlson:
    def test_olson_low_frequency(self):
        # Olson model: -6 dB at low frequency
        loss = baffle_step_loss_olson(50, 0.3)
        assert loss < -5.0

    def test_olson_high_frequency(self):
        # Olson model: 0 dB at high frequency
        loss = baffle_step_loss_olson(5000, 0.3)
        assert abs(loss) < 0.5

    def test_rectangular_baffle(self):
        # Test width != height
        loss_square = baffle_step_loss_olson(1000, 0.3, 0.3)
        loss_rect = baffle_step_loss_olson(1000, 0.3, 0.4)
        # Should be different due to different effective radius
        assert loss_square != loss_rect

class TestBaffleStepCompensation:
    def test_low_frequency_boost(self):
        # Compensates for -6 dB physics loss
        comp = baffle_step_compensation(50, 0.3)
        assert comp > 5.0  # ~+6 dB

    def test_high_frequency_no_correction(self):
        # No correction needed at HF
        comp = baffle_step_compensation(5000, 0.3)
        assert abs(comp) < 0.5

    def test_compensation_inverts_physics(self):
        # physics + compensation = flat response
        physics = baffle_step_loss(50, 0.3)
        comp = baffle_step_compensation(50, 0.3)
        assert abs(physics + comp) < 0.1

class TestApplyBaffleStepToSPL:
    def test_physics_mode_attenuates_lf(self):
        spl = np.array([90.0, 90.0, 90.0])
        freqs = np.array([50, 1000, 5000])
        result = apply_baffle_step_to_spl(spl, freqs, 0.3, mode='physics')
        # LF should be attenuated
        assert result[0] < spl[0]
        # HF should be unchanged
        assert abs(result[2] - spl[2]) < 0.5

    def test_compensator_mode_boosts_lf(self):
        spl = np.array([90.0, 90.0, 90.0])
        freqs = np.array([50, 1000, 5000])
        result = apply_baffle_step_to_spl(spl, freqs, 0.3, mode='compensator')
        # LF should be boosted
        assert result[0] > spl[0]
```

---

## Task 2: Validate Against Hornresp

**Priority:** HIGH
**Estimated Complexity:** HIGH
**Dependencies:** None

### Goal

Create a Hornresp simulation that includes baffle diffraction and validate the Olson/Stenzel model against it.

### Approach

1. **Create Hornresp simulation file**
   - Use a direct radiator (e.g., BC_8NDL51) in a finite baffle
   - Set baffle dimensions (e.g., 30cm × 30cm)
   - Export simulation results

2. **Create validation test**
   - File: `tests/validation/test_baffle_step_hornresp.py`
   - Compare Olson model to Hornresp baffle diffraction
   - Verify diffraction ripple pattern matches

3. **Acceptance criteria**
   - Ripple frequencies match within 10%
   - Magnitude matches within ±2 dB
   - Overall step shape (-6 to 0 dB) matches

### Hornresp Configuration

```
# Example Hornresp input for baffle diffraction
|Driver parameters:|
BC_8NDL51 (from existing infinite baffle sim)

|Enclosure type:|
Direct Radiator

|Baffle dimensions:|
Width: 30 cm
Height: 30 cm

|Simulation:|
Frequency range: 10 Hz - 10 kHz
```

### Implementation Steps

1. Create Hornresp input file with baffle dimensions
2. Run Hornresp simulation and export results
3. Parse results with `load_hornresp_sim_file()`
4. Compare to Olson model using validation framework

### Expected Challenges

- Hornresp may use different baffle diffraction model
- Need to ensure baffle dimensions match exactly
- Diffraction ripple pattern is sensitive to geometry

---

## Task 3: Integrate into Two-Way System Design

**Priority:** MEDIUM
**Estimated Complexity:** MEDIUM
**Dependencies:** None (but affects existing scripts)

### Goal

Update the two-way system design scripts to include baffle step correction.

### Files to Modify

1. **`tasks/plot_two_way_response.py`**
   - Add baffle step loss calculation
   - Apply to LF response only
   - Update plot to show "with baffle step" curve

2. **`src/gsd/optimization/api/crossover_assistant.py`**
   - Check if this is used for two-way design
   - If so, add baffle step option

### Implementation

```python
# In plot_two_way_response.py
from gsd.enclosure.baffle_step import apply_baffle_step_to_spl

def calculate_lf_response(driver, Vb, Fb, frequencies, baffle_width=None):
    """Calculate LF response (ported box) with optional baffle step."""
    lf_response = np.array([
        calculate_spl_ported_transfer_function(f, driver, Vb, Fb)
        for f in frequencies
    ])

    # Apply baffle step correction (physics mode)
    if baffle_width is not None:
        lf_response = apply_baffle_step_to_spl(
            lf_response, frequencies, baffle_width,
            model='linkwitz', mode='physics'
        )

    return lf_response

# In main():
# Estimate baffle width from box volume
baffle_width = estimate_baffle_width(Vb * 1000)  # Convert m³ to L
lf_response = calculate_lf_response(lf_driver, Vb, Fb, frequencies, baffle_width)
```

### Expected Impact

- Bass response will be ~6 dB lower at low frequencies
- Crossover point may need adjustment
- Overall flatness will decrease (more realistic)

### Documentation Update

Update `docs/validation/two_way_validation_assessment.md`:
- Change baffle step from "MISSING" to "IMPLEMENTED"
- Update flatness metrics
- Note that results are more realistic

---

## Task 4: Update Documentation

**Priority:** LOW
**Estimated Complexity:** LOW
**Dependencies:** Tasks 1-3

### Files to Update

1. **`docs/validation/baffle_step_fixes.md`**
   - Add "Validation Complete" section
   - Link to test file
   - Link to Hornresp comparison results

2. **`docs/validation/two_way_validation_assessment.md`**
   - Update baffle step status
   - Remove from "Missing Effects" list

3. **`README.md`** (if applicable)
   - Mention baffle step support

---

## Success Criteria

The baffle step implementation is complete when:

- [ ] Unit tests exist and pass (>90% coverage)
- [ ] Hornresp validation shows agreement within ±2 dB
- [ ] Two-way scripts include baffle step correction
- [ ] Documentation updated to reflect completion

---

## Order of Implementation

**Recommended sequence:**

1. **Task 1** (Unit tests) - Fastest, provides foundation
2. **Task 2** (Hornresp validation) - Validates physics correctness
3. **Task 3** (Two-way integration) - Applies to real use case
4. **Task 4** (Documentation) - Cleanup

**Estimated total effort:** 4-6 hours

---

## References

- `docs/validation/baffle_step_fixes.md` - Original issue report
- `src/gsd/enclosure/baffle_step.py` - Corrected implementation
- `literature/crossovers/olson_1951.md` - Olson reference
- `literature/crossovers/linkwitz_2003.md` - Linkwitz reference
- `tests/validation/test_infinite_baffle.py` - Example validation test structure

---

**End of Plan**
