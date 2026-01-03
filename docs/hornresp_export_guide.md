# Hornresp Export Guide

## Overview

GSD can export front-loaded horn designs to Hornresp format for validation and simulation. This guide covers exporting horn-loaded systems with throat and rear chambers.

## Function Reference

### `export_front_loaded_horn_to_hornresp()`

Exports a complete front-loaded horn system to Hornresp .txt format.

```python
from gsd.simulation import ExponentialHorn
from gsd.hornresp import export_front_loaded_horn_to_hornresp
from gsd.driver.parameters import ThieleSmallParameters

# Create driver
driver = ThieleSmallParameters(
    M_md=0.008, C_ms=5e-5, R_ms=3.0,
    R_e=6.5, L_e=0.1e-3, BL=12.0, S_d=0.0008
)

# Create horn
horn = ExponentialHorn(
    throat_area=0.0005,  # 5 cm² in SI (m²)
    mouth_area=0.02,      # 200 cm² in SI (m²)
    length=0.5            # 0.5 m
)

# Export to Hornresp format
export_front_loaded_horn_to_hornresp(
    driver=driver,
    horn=horn,
    driver_name="My_Horn_System",
    output_path="my_horn.txt",
    V_tc_liters=0.05,    # Throat chamber: 50 cm³
    A_tc_cm2=5.0,        # Throat chamber area: 5 cm²
    V_rc_liters=2.0,     # Rear chamber: 2.0 L
    L_rc_cm=12.6,        # Rear chamber depth: 12.6 cm
)
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `driver` | ThieleSmallParameters | **required** | Driver parameters (SI units) |
| `horn` | ExponentialHorn | **required** | Horn geometry (SI units) |
| `driver_name` | str | **required** | System name/identifier |
| `output_path` | str | **required** | Output .txt file path |
| `comment` | str | auto | Optional description |
| `V_tc_liters` | float | 0.0 | Throat chamber volume (L) |
| `A_tc_cm2` | float | None | Throat chamber area (cm²) |
| `V_rc_liters` | float | 0.0 | Rear chamber volume (L) |
| `L_rc_cm` | float | None | Rear chamber depth (cm) |
| `radiation_angle` | str | "2pi" | "2pi" (half-space) or "pi" (quarter-space) |
| `input_voltage` | float | 2.83 | Input voltage (V) |
| `source_resistance` | float | 0.0 | Source resistance (Ω) |

## Unit Conversions

The function automatically converts SI units to Hornresp format:

| Parameter | GSD (SI) | Hornresp Format |
|-----------|---------------|-----------------|
| Horn areas | m² | cm² (×10000) |
| Horn length | m | m (same) |
| Driver mass | kg | g (×1000) |
| Driver area | m² | cm² (×10000) |
| Chamber volume | m³ | L (×1000) |
| Chamber area | m² | cm² (×10000) |
| Chamber depth | m | cm (×100) |

## Usage Examples

### Example 1: Simple Horn (No Chambers)

```python
export_front_loaded_horn_to_hornresp(
    driver=driver,
    horn=horn,
    driver_name="TC2_Baseline",
    output_path="tc2.txt"
)
```

### Example 2: Horn with Throat Chamber

```python
export_front_loaded_horn_to_hornresp(
    driver=driver,
    horn=horn,
    driver_name="TC3_Throat",
    output_path="tc3.txt",
    V_tc_liters=0.05,    # 50 cm³
    A_tc_cm2=5.0         # 5 cm² (equals horn throat)
)
```

### Example 3: Horn with Both Chambers (TC4)

```python
export_front_loaded_horn_to_hornresp(
    driver=driver,
    horn=horn,
    driver_name="TC4_Complete",
    output_path="tc4.txt",
    V_tc_liters=0.05,    # Throat: 50 cm³
    A_tc_cm2=5.0,        # Throat area: 5 cm²
    V_rc_liters=2.0,     # Rear: 2.0 L
    L_rc_cm=12.6         # Rear depth: 12.6 cm
)
```

### Example 4: Auto-Calculate Rear Chamber Depth

```python
# Omit L_rc_cm to auto-calculate from V_rc
# Assumes cube-shaped chamber (V = L³)
export_front_loaded_horn_to_hornresp(
    driver=driver,
    horn=horn,
    driver_name="Auto_Depth",
    output_path="auto_depth.txt",
    V_rc_liters=5.0,     # 5 L rear chamber
    # L_rc_cm omitted → calculated as ∛5000 ≈ 17.1 cm
)
```

## Validation Workflow

The typical validation workflow is:

1. **Design in GSD**: Create your horn system using FrontLoadedHorn
2. **Export to Hornresp**: Use `export_front_loaded_horn_to_hornresp()`
3. **Import into Hornresp**: File → Import in Hornresp
4. **Run Simulations**: Generate impedance, SPL, etc.
5. **Compare Results**: Use validation scripts to verify agreement

```python
from gsd.enclosure.front_loaded_horn import FrontLoadedHorn
from gsd.hornresp import export_front_loaded_horn_to_hornresp
import numpy as np

# 1. Design system in gsd
flh = FrontLoadedHorn(
    driver=driver,
    horn=horn,
    V_tc=50e-6,
    V_rc=0.002
)

# 2. Export to Hornresp
export_front_loaded_horn_to_hornresp(
    driver, horn, "MyDesign", "my_design.txt",
    V_tc_liters=0.05, V_rc_liters=2.0, L_rc_cm=12.6
)

# 3. Open Hornresp, import my_design.txt, run simulation

# 4. Compare results
freqs = np.logspace(1, 4.3, 500)  # 10 Hz - 20 kHz
ve_response = flh.electrical_impedance_array(freqs)
# Compare with Hornresp exported data...
```

## Physical Constraints

The export function validates physical realizability:

### Rear Chamber Depth

When `V_rc_liters > 0` and `L_rc_cm` is not specified, the function:
1. Calculates minimum depth for magnet clearance: `L_min = 2 × r_piston`
2. Calculates maximum depth for fit: `L_max = V_rc / S_piston`
3. Assumes cube proportions: `L_cube = ∛V_rc`
4. Returns depth clamped to valid range: `L_rc = max(L_min, min(L_cube, L_max))`

**Errors raised if:**
- Box too small for driver (L_min > L_max)
- Rear chamber specified but depth ≤ 0

### Throat Chamber

**Important**: Throat chamber volume should be physically reasonable:
- **Realistic**: 10-100 cm³ (0.01-0.1 L) for compression drivers
- **Unrealistic**: 500 cm³ would give 100 cm length for 5 cm² throat

**Rule of thumb**: Throat chamber length `L_tc ≈ V_tc / A_tc` should be < 20 cm for compression drivers.

## Hornresp File Format

The generated .txt files follow Hornresp's native format with:

- **CRLF line endings** (`\r\n`) - required by Hornresp
- **All required sections** populated
- **Proper unit conversions** applied
- **Tab-separated values** in data sections

**Key sections:**
- `|TRADITIONAL DRIVER PARAMETER VALUES:` - Driver TS parameters
- `|HORN PARAMETER VALUES:` - Horn geometry (S1, S2, L12, etc.)
- `|CHAMBER PARAMETER VALUES:` - Throat/rear chambers
- `|RADIATION, SOURCE AND MOUTH PARAMETER VALUES:` - Boundary conditions

## Validation Results

The export function has been validated against TC2-4 test cases:

| Test Case | Configuration | Agreement |
|-----------|--------------|------------|
| TC2 | No chambers | <1% impedance error |
| TC3 | + Throat chamber | <1% impedance error |
| TC4 | + Both chambers | <1% impedance error |

Exported files produce identical simulation results in Hornresp when parameters match.

## Troubleshooting

### "File won't import in Hornresp"

**Check:**
1. File has CRLF line endings (not Unix LF)
2. All required sections are present
3. Values are in correct format (cm², L, etc.)

**Verify:**
```bash
# Check line endings
file your_export.txt
# Should show: CRLF line terminators

# View format
head -20 your_export.txt
```

### "Parameters don't match design"

**Common issues:**
- Unit confusion (m² vs cm², L vs m³)
- Throat area vs diaphragm area
- Chamber depth auto-calculated differently

**Solution**: Export with explicit parameters, verify against Hornresp display.

### "Box volume too small for driver"

**Error**: `Vrc is too small for driver. Minimum volume: X.X L`

**Cause**: Driver won't physically fit in chamber

**Solution**: Increase `V_rc_liters` or decrease driver size

## Literature

- Hornresp User Manual: http://www.hornresp.net/
- Olson (1947), Chapter 8 - Horn driver system parameters
- Beranek (1954), Chapter 5 - Horn radiation parameters
- TC2-4 Validation: `tests/validation/horn_theory/exp_midrange_tc*/`

## Related Functions

- `export_to_hornresp()` - Export sealed/ported box designs
- `driver_to_hornresp_record()` - Convert driver to Hornresp format
- `batch_export_to_hornresp()` - Export multiple drivers

## Example: Complete Workflow

```python
#!/usr/bin/env python3
"""Export gsd horn design to Hornresp."""

from gsd.simulation import ExponentialHorn
from gsd.enclosure.front_loaded_horn import FrontLoadedHorn
from gsd.hornresp import export_front_loaded_horn_to_hornresp
from gsd.driver.parameters import ThieleSmallParameters
import numpy as np

# Define system
driver = ThieleSmallParameters(
    M_md=0.015, C_ms=2.5e-4, R_ms=2.5,
    R_e=5.5, L_e=0.8e-3, BL=18.0, S_d=0.012
)

horn = ExponentialHorn(
    throat_area=0.001,   # 10 cm²
    mouth_area=0.2,      # 2000 cm²
    length=1.2           # 1.2 m
)

# Design: Horn with compression chamber
flh = FrontLoadedHorn(
    driver=driver,
    horn=horn,
    V_tc=80e-6,          # 80 cm³ compression chamber
    A_tc=0.001,          # 10 cm² (equals throat)
    V_rc=0.005           # 5 L rear chamber
)

# Calculate performance
freqs = np.logspace(1, 4.5, 1000)  # 10 Hz - 30 kHz
impedance = flh.electrical_impedance_array(freqs)
spl = flh.spl_response_array(freqs)
efficiency = flh.system_efficiency_array(freqs)

# Export to Hornresp for validation
export_front_loaded_horn_to_hornresp(
    driver=driver,
    horn=horn,
    driver_name="10cm2_2000cm2_Horn",
    output_path="exports/horn_validation.txt",
    comment="Compression driver horn: 10→2000cm², 1.2m, fc=180Hz",
    V_tc_liters=0.08,        # 80 cm³
    A_tc_cm2=10.0,           # 10 cm²
    V_rc_liters=5.0,         # 5 L
    L_rc_cm=17.1,            # ∛5000 cm
    radiation_angle="2pi",   # Half-space
    input_voltage=2.83
)

print(f"Horn cutoff: {flh.cutoff_frequency():.1f} Hz")
print(f"Driver Fs: {driver.F_s:.1f} Hz")
print(f"Max efficiency: {np.max(efficiency['efficiency']*100):.1f}%")
print("Exported to exports/horn_validation.txt")
```

## Multi-Segment Horn Export

### CRITICAL Format Differences

Multi-segment horns use **different parameter names** than single-segment horns. Hornresp reuses parameter names in different contexts:

| Parameter | Single-Segment | Multi-Segment Active | Multi-Segment Inactive |
|-----------|---------------|---------------------|----------------------|
| Length | `L12` | `Exp` | `L34`, `L45` |
| Flare constant | `Exp = 50.00` | N/A | N/A |
| Segment areas | S1, S2 | S1, S2, S3, S4, S5 | S3=0, S4=0 |

**Key Insight**: `Exp` parameter has different meanings:
- **Single-segment**: `Exp` = flare constant (typically 50.00)
- **Multi-segment active**: `Exp` = segment LENGTH in cm
- **Multi-segment inactive**: Use `L34`, `L45` instead of `Exp`

### Multi-Segment Format Example

**For a 2-segment horn**:
```
|HORN PARAMETER VALUES:

S1 = 1.84
S2 = 241.20
Exp = 33.74          ← Active segment 1: LENGTH in cm
F12 = 394.66         ← 2 decimal places
S2 = 241.20
S3 = 405.13
Exp = 59.85          ← Active segment 2: LENGTH in cm
F23 = 23.65          ← 2 decimal places
S3 = 0.00            ← Inactive: ZERO (not repeated mouth area!)
S4 = 0.00
L34 = 0.00           ← Inactive: Use L34 (not Exp)
F34 = 0.00
S4 = 0.00
S5 = 0.00
L45 = 0.00           ← Inactive: Use L45 (not Exp)
F45 = 0.00
```

### Export Function for Multi-Segment

```python
from gsd.simulation import MultiSegmentHorn, HornSegment
from gsd.hornresp import export_multisegment_horn_to_hornresp

# Create multi-segment horn
segments = [
    HornSegment(throat_area=0.000184, mouth_area=0.02412, length=0.337, m=7.2),
    HornSegment(throat_area=0.02412, mouth_area=0.04051, length=0.598, m=1.7),
]
horn = MultiSegmentHorn(segments)

# Export to Hornresp
export_multisegment_horn_to_hornresp(
    driver=driver,
    horn=horn,
    driver_name="TC2_2Segment",
    output_path="tc2_2seg.txt",
    V_tc_liters=0.014,    # Throat chamber
    A_tc_cm2=None,        # Auto = throat area
    V_rc_liters=0.004,    # Rear chamber
    L_rc_cm=None          # Auto-calculate
)
```

### Critical Multi-Segment Rules

#### 1. Active Segments: Use `Exp` for Length
```
S1 = <throat>
S2 = <middle>
Exp = <length_cm>    ← Use "Exp", NOT "L12"
F12 = <frequency>
```

#### 2. Inactive Segments: Zero Areas + `L34`/`L45`
```
S3 = 0.00            ← CRITICAL: Must be 0.00
S4 = 0.00
L34 = 0.00           ← Use "L34", NOT "Exp"
F34 = 0.00
```

#### 3. F12/F23 Formula: Use 4π NOT 2π

```python
# WRONG (Olson's theoretical cutoff):
f12 = (c * flare_constant) / (2 * math.pi)

# CORRECT (Hornresp's F parameter):
f12 = (c * flare_constant) / (4 * math.pi)
```

**Why the difference?** Hornresp's F12/F23 parameters are half the theoretical cutoff frequency. This has been verified against actual Hornresp output.

#### 4. Precision: 2 Decimals for F12/F23
```python
# WRONG:
F12 = {f12:.4f}  # Outputs 394.6578

# CORRECT:
F12 = {f12:.2f}  # Outputs 394.66
```

#### 5. Vtc Unit: cm³ NOT liters
```python
# WRONG:
Vtc = {V_tc_liters:.2f}  # Exports 0.01 (interpreted as 0.01 cm³)

# CORRECT:
Vtc = {V_tc_liters * 1000:.2f}  # Exports 12.89 (12.89 cm³)
```

### Common Multi-Segment Pitfalls

#### ❌ Error: Repeating Mouth Area for Inactive Segments
```
S3 = 405.13          ← Wrong! This is mouth area from segment 2
S4 = 0.00
L34 = 0.00
```
**Result**: Hornresp gives "S4 = 0.00" import error

#### ✓ Correct: Zero for Inactive Segments
```
S3 = 0.00            ← Correct!
S4 = 0.00
L34 = 0.00
```

#### ❌ Error: Using L12/L23 for Multi-Segment
```
S1 = 1.84
S2 = 241.20
L12 = 33.74          ← Wrong! L12 is for single-segment only
F12 = 394.66
```
**Result**: Hornresp may not recognize the format

#### ✓ Correct: Using Exp for Multi-Segment
```
S1 = 1.84
S2 = 241.20
Exp = 33.74          ← Correct! Exp = length in cm
F12 = 394.66
```

#### ❌ Error: Using Exp for Inactive Segments
```
S3 = 0.00
S4 = 0.00
Exp = 0.00           ← Wrong! Use L34 for inactive
F34 = 0.00
```

#### ✓ Correct: Using L34/L45 for Inactive
```
S3 = 0.00
S4 = 0.00
L34 = 0.00           ← Correct!
F34 = 0.00
```

### Validation Checklist for Multi-Segment

Before exporting a multi-segment horn, verify:

- [ ] Active segments (1-N) use `Exp` for length parameter
- [ ] Inactive segments (N+1 to 4) use `L34`, `L45` for length
- [ ] Inactive segments have `S3=0.00`, `S4=0.00` (not repeated areas)
- [ ] F12/F23/F34/F45 use formula: `F = c*m/(4π)` (not 2π)
- [ ] F12/F23/F34/F45 have 2 decimal places (not 4)
- [ ] Vtc is in cm³: `V_tc_liters * 1000`
- [ ] Vrc is in liters with 2 decimal places
- [ ] All areas in cm² (×10000 from m²)
- [ ] All lengths in cm (×100 from m)

### Reference Files

- **Correct format**: `imports/tc2_multiseg.txt`
- **Hornresp re-export**: `imports/tc2_optimized_multisegment_horn.txt`
- **Format analysis**: `docs/validation/multisegment_hornresp_format_discrepancies.md`
- **Comparison**: `docs/validation/multisegment_hornresp_comparison.md`

### Implementation Reference

**File**: `src/gsd/hornresp/export.py`

**Key sections**:
- Lines 961-1250: `export_multisegment_horn_to_hornresp()`
- Lines 1069-1090: Flare constant conversion (uses 4π)
- Lines 1102-1119: Horn section formatting

**Critical code patterns**:

```python
# Line 1072: Correct F12 formula (4π not 2π)
f12 = (c * segments[0].flare_constant) / (4.0 * math.pi)

# Lines 1112-1114: Inactive segment format
S3 = 0.00      ← Hardcoded zero
S4 = 0.00
L34 = {l34:.2f} ← Use L34, not Exp

# Line 763: Vtc conversion (cm³ not liters)
Vtc = {V_tc_liters * 1000:.2f}
```

This completes the documentation for Hornresp export functionality.
