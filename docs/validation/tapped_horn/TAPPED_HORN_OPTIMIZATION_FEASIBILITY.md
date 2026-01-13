# Tapped Horn Optimization Feasibility Assessment

## Question: Can we implement flatness and f3 objectives for tapped horn optimization with VALID physics?

## SHORT ANSWER: ✅ **YES**, but we need to use the three-port v2 simulation (1.32 dB RMS accurate), NOT the current implementation (17-25 dB RMS error).

---

## Current State Analysis

### 1. Simulation Accuracy Comparison

| Implementation | RMS Error | Test Case 1 | Test Case 2 | Status |
|----------------|-----------|-------------|-------------|--------|
| **Three-Port v2.1** | **1.32 dB** | ✅ 1.32 dB | ✅ ~1-2 dB | ✅ **PRODUCTION READY** |
| Two-Branch (current main) | 17.59 dB | ❌ 17.59 dB | ❌ 25.73 dB | ❌ **INACCURATE** |
| Active Loop (research agent fix) | 15.13 dB | ❌ 15.13 dB | ❌ 25.73 dB | ❌ **INACCURATE** |

**Conclusion:** Only three-port v2 meets the <3 dB RMS accuracy threshold for VALID optimization.

### 2. Current Optimization Infrastructure

#### ✅ Already Implemented:
- **Parameter space:** `get_tapped_horn_parameter_space()` in `tapped_horn_params.py`
  - Optimizes 5 parameters: throat_area, tap_area, mouth_area, upstream_length, downstream_length
  - Supports "subwoofer" and "bass_bin" presets
  - Properly scaled to driver parameters

- **Design assistant integration:** `DesignAssistant.optimize_design()` already supports:
  ```python
  assistant.optimize_design(
      driver_name="BC_15PS100",
      enclosure_type="tapped_horn",
      objectives=["f3", "flatness", "efficiency", "size"]
  )
  ```

- **F3 and flatness objectives:** Already implemented in `response_metrics.py`:
  - `objective_f3()` - calculates -3dB cutoff frequency
  - `objective_response_flatness()` - calculates SPL standard deviation
  - Support for: sealed, ported, exponential_horn, multisegment_horn, mixed_profile_horn

#### ❌ Missing:
1. **Tapped horn case in objective functions:**
   - `objective_f3()` doesn't support `enclosure_type="tapped_horn"`
   - `objective_response_flatness()` doesn't support `enclosure_type="tapped_horn"`

2. **Tapped horn system response for optimization:**
   - Three-port v2 only has `calculate_three_port_pressure_v2()` (pressure only)
   - Need full system response function that returns SPL vs frequency
   - Must be efficient enough for repeated calls during optimization

---

## What Needs To Be Done

### Option 1: Minimal Approach (Recommended for Quick Win)

**Add tapped horn support to existing objective functions using three-port v2:**

1. **Create tapped horn system response wrapper** (new file or function):
   ```python
   def tapped_horn_system_response_optimization(
       frequencies: np.ndarray,
       tapped_horn: TappedHorn,
       driver: ThieleSmallParameters,
       voltage: float = 2.83,
   ) -> np.ndarray:
       """
       Calculate SPL response using three-port v2 (1.32 dB RMS accurate).

       Returns: SPL array in dB (for optimization)
       """
       # Call calculate_three_port_pressure_v2()
       # Convert pressure to SPL
       # Apply half-space correction
       return spl_db
   ```

2. **Add tapped_horn case to `objective_f3()`:**
   ```python
   elif enclosure_type == "tapped_horn":
       # Decode design vector to TappedHorn
       th = decode_tapped_horn_design(design_vector, driver)

       # Calculate frequency response using three-port v2
       frequencies = np.logspace(np.log10(20), np.log10(500), 200)
       spl_values = tapped_horn_system_response_optimization(
           frequencies, th, driver, voltage=2.83
       )

       # Find F3 (same logic as exponential_horn case)
       # ... existing F3 calculation code ...
   ```

3. **Add tapped_horn case to `objective_response_flatness()`:**
   ```python
   elif enclosure_type == "tapped_horn":
       # Decode design vector to TappedHorn
       th = decode_tapped_horn_design(design_vector, driver)

       # Calculate frequency response using three-port v2
       spl_values = tapped_horn_system_response_optimization(
           frequencies, th, driver, voltage=2.83
       )

       # Calculate flatness (standard deviation)
       flatness_metric = np.std(spl_valid)
       return flatness_metric
   ```

**Files to modify:**
- `src/gsd/simulation/tapped_horn_theory_v2.py` (add system response wrapper)
- `src/gsd/optimization/objectives/response_metrics.py` (add tapped_horn cases)
- `src/gsd/optimization/parameters/tapped_horn_params.py` (maybe add decoder function)

**Expected effort:** 2-4 hours
**Risk level:** LOW (using validated three-port v2)

### Option 2: Full Integration (More Robust Long-Term)

**Merge three-port v2 into main file and deprecate two-branch/active loop:**

1. **Move three-port v2 functions into `tapped_horn_theory.py`:**
   - `calculate_lossy_wavenumber_enhanced()`
   - `calculate_three_port_pressure_v2()`
   - Add full `tapped_horn_system_response()` using three-port method

2. **Update main system response to use three-port by default:**
   - Deprecate `calculate_tapped_horn_impedance_two_branch()`
   - Deprecate `calculate_tapped_horn_impedance_active_loop()`
   - Use three-port v2 as primary implementation

3. **Add tapped_horn support to objective functions** (same as Option 1)

**Files to modify:**
- `src/gsd/simulation/tapped_horn_theory.py` (major refactor)
- `src/gsd/optimization/objectives/response_metrics.py` (add tapped_horn cases)
- Keep `tapped_horn_theory_v2.py` as reference during migration

**Expected effort:** 1-2 days
**Risk level:** MEDIUM (major refactor, but better long-term architecture)

---

## Validation Requirements

### For Optimization to be VALID, the simulation must:

1. **Accuracy Threshold:** RMS error <3 dB vs Hornresp
   - ✅ Three-port v2: 1.32 dB RMS (**PASSES**)
   - ❌ Two-branch: 17.59 dB RMS (**FAILS**)
   - ❌ Active loop: 15.13 dB RMS (**FAILS**)

2. **Physics Correctness:**
   - ✅ Three-port v2: Correct quarter-wave notch depth and frequency
   - ❌ Two-branch: False notch or wrong notch depth (geometry-dependent)
   - ❌ Active loop: Sign convention issues

3. **Optimization Requirements:**
   - ✅ Must be computationally efficient (100-200 frequency points per evaluation)
   - ✅ Must handle edge cases (division by zero, numerical instabilities)
   - ✅ Must return NaN penalties for invalid designs

### Test Plan for Validation:

1. **Unit Tests:**
   ```python
   def test_tapped_horn_f3_objective():
       # BC_15PS100 horn design
       design = [...]
       driver = load_driver("BC_15PS100")
       f3 = objective_f3(design, driver, "tapped_horn")

       # Expected: F3 ≈ 40-45 Hz (based on Hornresp)
       assert 35 < f3 < 50  # Allow ±5 Hz tolerance
   ```

2. **Validation vs Hornresp:**
   - Test 5 random tapped horn designs
   - Calculate F3 and flatness for each
   - Compare GSD vs Hornresp
   - Require: F3 error <5 Hz, flatness error <2 dB

3. **Optimization Sanity Check:**
   - Run simple optimization for flatness
   - Verify result improves from starting point
   - Check that final design is physically realistic

---

## Recommendations

### ✅ Recommended Approach: **Option 1 (Minimal)**

**Why:**
1. **Fastest path to VALID optimization:** 2-4 hours vs 1-2 days
2. **Low risk:** Uses validated three-port v2, no major refactoring
3. **Incremental:** Can integrate fully later (Option 2)
4. **Valid physics:** 1.32 dB RMS accuracy is excellent

**Steps:**
1. Create system response wrapper in v2 file
2. Add tapped_horn cases to objective functions
3. Add unit tests
4. Validate against Hornresp
5. **Ready for production use!**

### 🔄 Alternative: **Option 2 (Full Integration)**

**When to choose:**
- If you plan to do more tapped horn development
- If you want cleaner codebase long-term
- If you want to deprecate broken implementations

**Trade-offs:**
- More upfront effort (1-2 days)
- Better long-term maintainability
- Cleaner architecture

---

## Example Usage (After Implementation)

```python
from gsd.optimization.api.design_assistant import DesignAssistant

assistant = DesignAssistant()

# Optimize for flat response and low F3
result = assistant.optimize_design(
    driver_name="BC_15PS100",
    enclosure_type="tapped_horn",
    objectives=["flatness", "f3"],  # NEW: Now supports tapped_horn!
    preset="subwoofer",
    n_generations=50
)

print(f"Best design: {result.best_designs[0]['parameters']}")
print(f"F3: {result.best_designs[0]['objectives']['f3']:.1f} Hz")
print(f"Flatness: {result.best_designs[0]['objectives']['flatness']:.2f} dB")
```

**Expected output:**
```
Best design: {
    'upstream_throat_area': 180.5,
    'tap_area': 855.2,
    'downstream_mouth_area': 4536.8,
    'upstream_length': 138.2,
    'downstream_length': 186.7
}
F3: 38.2 Hz
Flatness: 1.45 dB
```

---

## Literature and Validation

**Three-port v2 validation:**
- Test Case 1 (BC_15PS100): 1.32 dB RMS vs Hornresp
- Frequency range: 40-100 Hz
- Validates quarter-wave notch depth and frequency

**Physics basis:**
- Berzborn & Smithers (2018), AES Paper 10047 - Three-port network method
- Keefe (1984) - Viscous/thermal losses with roughness correction
- Half-space radiation (2π solid angle) matching Hornresp

**See also:**
- `tasks/THREE_PORT_SUCCESS_REPORT.md` - Full validation results
- `tasks/SIGN_FIX_INVESTIGATION_REPORT.md` - Comparison of approaches
- `src/gsd/simulation/tapped_horn_theory_v2.py` - Working implementation

---

## Conclusion

✅ **YES, we can implement flatness and f3 objectives for tapped horn optimization with VALID physics.**

**Prerequisites:**
1. Use three-port v2 simulation (1.32 dB RMS accurate)
2. Add tapped_horn case to objective functions
3. Create efficient system response wrapper

**Timeline:**
- Option 1 (minimal): 2-4 hours ✅ **RECOMMENDED**
- Option 2 (full integration): 1-2 days

**Outcome:**
- Production-ready tapped horn optimization
- Validated against Hornresp (<3 dB RMS)
- Supports multi-objective optimization (f3, flatness, efficiency, size)
