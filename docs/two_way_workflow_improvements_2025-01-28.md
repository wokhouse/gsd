# Two-Way Design Workflow - Lessons Learned

**Date:** 2025-01-28
**Session:** Two-Way Horn-Loaded System Design Optimization

## Summary

Through extensive exploration and analysis, we discovered that the **maximum circular mouth that fits the build plate (491 cm², Ø250mm)** provides the **best overall performance** for the DH450 + BC12FW88 two-way system, contrary to the initial optimizer's recommendation of a smaller 110 cm² mouth.

## Key Findings

### 1. Larger Mouth ≠ Lower Fc is OK

**Initial assumption:** Lower horn cutoff frequency (Fc) is always better.

**Reality:** A larger mouth with **higher Fc** can provide **better system integration** because:
- Higher HF sensitivity requires less padding
- Better sensitivity matching reduces crossover dip
- Lower dip = better flatness

**Evidence:**
- 110 cm² mouth (Fc=336 Hz): Dip=3.52 dB, Flatness=4.06 dB
- 491 cm² mouth (Fc=499 Hz): Dip=**3.18 dB**, Flatness=**3.73 dB** ✅

### 2. XO/Fc Ratio of 1.2-1.3 is Optimal (Not 2.0!)

**Initial assumption:** XO = 2×Fc is optimal (standard practice).

**Reality:** XO/Fc = **1.2** gave better results:
- 600 Hz XO with 499 Hz Fc (ratio=1.20)
- Optimal crossover found by sweep, not by formula
- Previous design: 600 Hz XO with 336 Hz Fc (ratio=1.79) - worse!

### 3. Dispersion Quality vs Width

**Key insight:** Pattern quality matters as much as beamwidth.

**Comparison at crossover:**
- Previous (110 cm²): ka=0.65, omnidirectional, but higher dip
- MAX CIRCULAR (491 cm²): ka=1.37, moderate directivity, **lower dip**
- MAX SQUARE (625 cm²): ka=1.63, narrower, similar dip to circular

**Winner:** MAX CIRCULAR (491 cm²)
- Best flatness (3.73 dB)
- Lowest crossover dip (3.18 dB)
- Manageable dispersion (ka=1.37)
- Fits 250mm build plate perfectly

### 4. Build Plate Constraints are Critical

**Problem:** Initial design used 625 cm² square mouth (282mm diameter) which **doesn't fit** 250mm circular build plate.

**Solution:** MAX CIRCULAR mouth:
- Area: 491 cm² (vs 625 cm² square)
- Diameter: Ø250 mm (fits exactly!)
- Same exponential flare behavior
- Better directivity consistency

## Optimizer Limitations Discovered

### Issue 1: Backward Calculation Constrained Search Space

The `design_two_way_system_integrated()` function:
```python
# OLD APPROACH:
target_fc = calculate_target_horn_fc(xo, f_beam, xo_fc_ratio=2.0)
required_mouth = calculate_mouth_area_for_fc(...)
# Only calculated minimum required mouth!
```

**Problem:** Never explored larger mouths even though they might perform better.

### Issue 2: XO/Fc Ratio Fixed at 2.0

```python
# OLD ASSUMPTION:
target_fc = desired_xo / 2.0  # Always use 2:1 ratio
```

**Problem:** Optimal ratio was 1.2, not 2.0. Should optimize XO, not calculate Fc.

### Issue 3: Didn't Optimize for Crossover Dip

**Old objective:** Minimize F3 + maximize flatness

**Missing:** Crossover dip wasn't primary objective, but it dominates perceived quality!

## Recommendations for Workflow Improvements

### 1. Add Mouth Area as Design Variable

```python
design_variables = [
    'mouth_area',  # Explore 50-625 cm²
    'crossover_frequency',  # Free parameter (don't derive from Fc)
    'port_tuning',
    ...
]
```

### 2. Multi-Objective Optimization

```python
objectives = [
    'f3',              # Extend bass response
    'flatness',        # Minimize passband variation
    'crossover_dip',   # NEW: Minimize integration dip!
    'dispersion',      # NEW: Control directivity at XO
]
```

### 3. Crossover Sweep (Don't Assume 2×Fc)

```python
# NEW APPROACH:
# Calculate horn geometry first (from constraints)
horn_fc = calculate_fc_from_mouth(throat, max_mouth, length)

# Then sweep XO to find optimal (don't assume ratio)
xo_result = optimize_crossover_frequency(
    xo_range=(fc*1.2, fc*2.5),  # Wide range
    minimize_dip=True  # Primary objective
)
```

### 4. Add DXF Export Capability

**New feature:** Export horn profile to DXF for CAD/CAM

```python
from gsd.optimization.api.horn_export import export_horn_profile_dxf

export_horn_profile_dxf(
    throat_area_cm2,
    mouth_area_cm2,
    length_cm,
    output_file="horn_profile.dxf"
)
```

### 5. Dispersion Analysis

**New feature:** Analyze directivity patterns

```python
from gsd.optimization.api.horn_dispersion import analyze_directivity

directivity = analyze_directivity(
    mouth_area_cm2,
    crossover_frequency,
    plot_type='polar'
)

# Returns ka, DI, beamwidth, recommendations
```

## Design Comparison Table

| Design | Mouth | Fc | XO | XO/Fc | Dip | Flatness | ka@XO | Dispersion |
|--------|-------|-----|-----|-------|-----|----------|-------|------------|
| **Previous** | 110 cm² | 336 Hz | 600 Hz | 1.79 | 3.52 dB | 4.06 dB | 0.65 | Wide |
| MAX SQUARE | 625 cm² | 526 Hz | 630 Hz | 1.20 | 3.23 dB | 3.88 dB | 1.63 | Narrow |
| **MAX CIRCULAR** | **491 cm²** | **499 Hz** | **600 Hz** | **1.20** | **3.18 dB** ✅ | **3.73 dB** ✅ | **1.37** | **Moderate** |

## Files Created During Investigation

**Design & Analysis:**
- `tasks/dh450_two_way_design.py` - Initial design attempts
- `tasks/dh450_max_circular_mouth.py` - Optimal design discovery
- `tasks/compare_flatness.py` - Flatness comparison
- `tasks/export_horn_profile_dxf.py` - DXF export
- `tasks/dispersion_max_circular.py` - Dispersion analysis

**Outputs:**
- `tasks/dh450_horn_profile.dxf` - Final horn profile (MAX CIRCULAR)
- `tasks/dh450_horn_profile_preview.png` - Profile visualization
- `tasks/dh450_dispersion_max_circular.png` - Dispersion plots
- `tasks/flatness_comparison.png` - Flatness comparison
- `tasks/dh450_system_response.png` - System response plot

## Implementation Plan

### Phase 1: Core Workflow Improvements
1. ✅ Create branch
2. ⏳ Update `design_two_way_system_integrated()` with learnings
3. ⏳ Add DXF export function to API
4. ⏳ Add dispersion analysis to API

### Phase 2: Enhanced Optimizer
5. ⏳ Add crossover sweep (don't assume 2×Fc)
6. ⏳ Add mouth area as design variable
7. ⏳ Multi-objective optimization (include crossover dip)

### Phase 3: Documentation
8. ⏳ Update CLAUDE.md with new insights
9. ⏳ Update ROADMAP.md with completed features
10. ⏳ Create example: "Complete two-way design with DXF export"

## Next Steps

1. Commit learnings document to branch
2. Update `src/gsd/optimization/api/two_way_system.py`
3. Create `src/gsd/optimization/api/horn_export.py`
4. Create `src/gsd/optimization/api/horn_dispersion.py`
5. Update examples with new workflow
6. Test with different drivers to validate generalizability

## References

- Literature: `literature/horns/olson_1947.md` - Horn cutoff theory
- Literature: `literature/horns/beranek_1954.md` - Directivity patterns
- Case Study: `docs/two_way_design_review_12fw88_dh450.md` - Previous optimization
- Original PR: PR #57 - Two-way workflow implementation
