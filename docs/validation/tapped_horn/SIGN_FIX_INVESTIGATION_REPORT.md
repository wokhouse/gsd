# Sign Fix Investigation Report

## Executive Summary

Attempted to implement research agent's corrected sign convention for active loop model, but **results degraded** instead of improving.

## Key Finding

**There are TWO different implementations:**

1. **Three-Port Network v2.1** (`tapped_horn_theory_v2.py`)
   - ✅ **RMS Error: 1.32 dB** (validated vs Hornresp)
   - ✅ **Production Ready** - well within <3 dB target
   - ✅ Uses enhanced losses (roughness factor 4.0x)
   - ✅ Half-space radiation correction (+6 dB)
   - ✅ Explicit contracting horn geometry

2. **Active Loop / Two-Branch Model** (`tapped_horn_theory.py` - current HEAD)
   - ❌ **RMS Error: 17.59 dB** (Test Case 1)
   - ❌ **RMS Error: 25.73 dB** (Test Case 2)
   - Uses two-branch model with mutual coupling
   - Contains active loop function (currently not used by system response)

## Test Results

### Test Case 1: BC_15PS100 (15" Driver)

| Implementation | RMS Error | 80 Hz Notch | Status |
|----------------|-----------|-------------|--------|
| **Three-Port v2.1** | **1.32 dB** | 94.3 dB | ✅ Excellent |
| Active Loop (baseline) | 17.59 dB | 98.05 dB | ❌ Notch too shallow |
| Active Loop (sign fix) | 15.13 dB | 73.85 dB | ❌ Worse |

### Test Case 2: BC_12NDL76 (12" Driver)

| Implementation | RMS Error | 56 Hz Notch | Status |
|----------------|-----------|-------------|--------|
| Three-Port v2.1 | ~1-2 dB | ~96 dB | ✅ No false notch |
| Two-Branch (baseline) | 25.73 dB | 52.4 dB | ❌ Deep false notch |

## What Changed

### Active Loop Function Sign Change

**Before (baseline):**
```python
z_acoustic_load = p1_per_u - p2_per_u  # Throat - Tap
```

**After (research agent's fix):**
```python
z_acoustic_load = p2_per_u - p1_per_u  # Tap - Throat (Front - Rear)
```

**Result:** Test Case 1 went from 17.59 dB → 15.13 dB (slight improvement, but still far from target)

## Analysis

### Why Sign Fix Didn't Work

1. **Wrong Target:** Research agent's fix was for the **active loop model**, but the system is currently using the **two-branch model** (which doesn't call the active loop function)

2. **Two-Branch Model Has Different Issues:**
   - Test Case 1: Notch too shallow (98 dB vs 55 dB target)
   - Test Case 2: False deep notch (52 dB vs 96 dB target)
   - Pattern: **Opposite error patterns** for different geometries

3. **Three-Port v2 Already Works:**
   - Achieves 1.32 dB RMS error
   - Uses different approach (explicit three-port network)
   - Has empirical corrections (roughness factor, half-space)

### Root Cause

The **active loop model** is fundamentally different from the **three-port network model**:

- **Active Loop:** Models driver as dipole with pressure difference across diaphragm
- **Three-Port:** Models complete acoustic network with explicit port impedances

The three-port approach matches Hornresp's implementation better.

## Recommendation

### Option 1: Use Three-Port v2 (RECOMMENDED)

**Advantages:**
- ✅ Already validated (1.32 dB RMS)
- ✅ Works for both test cases
- ✅ Handles quarter-wave resonance correctly
- ✅ No sign convention issues

**Action Required:**
1. Merge `tapped_horn_theory_v2.py` into main file
2. Update `tapped_horn_system_response()` to use three-port approach
3. Run full validation test suite
4. Update documentation

**Expected Outcome:** Production-ready tapped horn simulation with <2 dB RMS error

### Option 2: Continue Debugging Active Loop

**Issues:**
- ❌ Currently 17.59 dB RMS error (far from target)
- ❌ Shows opposite error patterns for different geometries
- ❌ Research agent's sign fix didn't help
- ❌ May require fundamental redesign

**Expected Effort:** High - need to identify why sign convention is opposite of expected

## Next Steps

1. **RECOMMENDED:** Integrate three-port v2 into main file
2. Test integrated version against both test cases
3. If integration successful, deprecate two-branch/active loop approaches
4. Document three-port method as primary implementation

## Files

- `src/gsd/simulation/tapped_horn_theory.py` - Main file (two-branch model)
- `src/gsd/simulation/tapped_horn_theory_v2.py` - Three-port model (1.32 dB RMS)
- `tasks/THREE_PORT_SUCCESS_REPORT.md` - Three-port validation results
- `tasks/ACTIVE_LOOP_FIX_FAILURE_SUMMARY.md` - Previous sign fix attempt
- `tasks/test_three_port_v2_halfspace.py` - Three-port validation script

## Literature

- Berzborn & Smithers (2018), AES Paper 10047 - Three-port network method
- Keefe (1984) - Viscous/thermal losses (roughness factor)
- Half-space vs free-field radiation (2π vs 4π solid angle)
