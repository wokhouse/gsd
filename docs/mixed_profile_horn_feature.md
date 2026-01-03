# Mixed-Profile Horn Optimization

**Status**: Implemented and tested
**Branch**: `feature/mixed-profile-horns`
**Date**: 2024-12-31

## Overview

Implemented ability to combine exponential, conical, and hyperbolic horn profiles within the same multi-segment horn optimization. Each segment can independently choose its profile type via optimization.

## Implementation

### New Functions

Added to `src/gsd/optimization/parameters/multisegment_horn_params.py`:

1. **`get_mixed_profile_parameter_space()`**
   - Creates parameter space for mixed-profile horns
   - Each segment has `profile_type` parameter (0=Exp, 1=Con, 2=Hyp)
   - Includes T parameters for hyperbolic segments

2. **`decode_mixed_profile_design()`**
   - Decodes optimization array into structured parameters
   - Returns profile types, segment classes, T values

3. **`build_mixed_profile_horn()`**
   - Constructs `MultiSegmentHorn` from design vector
   - Instantiates appropriate segment types (HornSegment, ConicalHorn, HyperbolicHorn)

### Integration

- Added `mixed_profile_horn` to `DesignAssistant` supported enclosure types
- Updated `response_metrics.py` to handle mixed-profile horns in objective functions
- Updated `composite.py` to recognize `mixed_profile_horn` for `num_segments` parameter

### Profile Type Codes

```python
0 = HornSegment    # Exponential (S = S_t · exp(m·x))
1 = ConicalHorn     # Conical (r = r_t + (r_m - r_t) · x/L)
2 = HyperbolicHorn  # Hyperbolic with T parameter
```

## Example Usage

```python
from gsd.optimization.parameters import (
    get_mixed_profile_parameter_space,
    build_mixed_profile_horn,
)
from gsd.driver import load_driver
import numpy as np

driver = load_driver("BC_DE250")

# Get parameter space
param_space = get_mixed_profile_parameter_space(
    driver, preset="midrange_horn", num_segments=2
)

# Design vector: [throat, middle, mouth, L1, L2, ptype1, ptype2, T1, T2, V_tc, V_rc]
# Conical throat, exponential mouth:
design = np.array([
    5.07e-4,    # throat_area (m²)
    0.01,       # middle_area (m²)
    0.02,       # mouth_area (m²)
    0.15,       # length1 (m) - conical
    0.25,       # length2 (m) - exponential
    1,          # profile_type1 = conical
    0,          # profile_type2 = exponential
    1.0, 1.0,   # T1, T2 (not used for these profiles)
    0.0, 0.0,   # V_tc, V_rc
])

horn, V_tc, V_rc = build_mixed_profile_horn(design, driver, num_segments=2)

# Result: horn with ConicalHorn segment 1, HornSegment segment 2
```

## Test Scripts

### `tasks/optimize_mixed_profile_horn.py`
Standalone optimization script for mixed-profile horns with:
- Profile seeding (Exp+Exp, Con+Exp, Exp+Hyp combinations)
- LHS sampling
- NSGA-II optimization
- Pareto front analysis

### `tasks/optimize_two_way_mixed_profile.py`
Two-way system optimization:
- BC_8NDL51 in ported enclosure (bass/midrange)
- BC_DE250 in mixed-profile horn (high frequency)
- 1 kHz crossover
- Sequential optimization (ported → horn)

## Literature

- Olson (1947), Chapter 8 - Compound horns with mixed profiles
- Kolbrek Part 1 - T-matrix chaining for arbitrary segment types
- `literature/horns/kolbrek_horn_theory_tutorial.md`

## Limitations

1. **impedance_smoothness objective** not yet supported for `mixed_profile_horn`
   - Only implemented for standard `multisegment_horn`
   - Can use flatness-only optimization

2. **Profile type parameters are integer-valued**
   - Optimized as continuous (0, 1, 2)
   - Should use discrete/categorical optimization for true profile selection
   - Current approach: round to nearest integer in `build_mixed_profile_horn()`

## Future Work

- [ ] Add `impedance_smoothness` support for mixed-profile horns
- [ ] Implement discrete optimization for profile type selection
- [ ] Add 3-segment mixed-profile optimization
- [ ] Validate against Hornresp for mixed-profile designs
