# Two-Way System Design Guide

**For GSD Horn Loudspeaker Design Tool**

Version: 1.0
Date: 2025-01-13

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Physics Background](#2-physics-background)
3. [Step-by-Step Workflow](#3-step-by-step-workflow)
4. [Decision Trees](#4-decision-trees)
5. [Case Studies](#5-case-studies)
6. [Troubleshooting](#6-troubleshooting)
7. [API Reference](#7-api-reference)
8. [Best Practices](#8-best-practices)
9. [Glossary](#9-glossary)

---

## 1. Introduction

### What is Two-Way System Design?

A two-way loudspeaker system uses two drivers to reproduce the full frequency range:
- **LF (Low-Frequency) driver**: Handles bass and midrange (typically 20 Hz - 2 kHz)
- **HF (High-Frequency) driver**: Handles treble (typically 1 kHz - 20 kHz)

A **crossover network** splits the audio signal between the two drivers at the crossover frequency.

### Why Use Horn-Loaded HF Drivers?

Horn-loaded compression drivers offer significant advantages:
- **Higher efficiency**: 105-110 dB sensitivity (vs 85-90 dB for dome tweeters)
- **Better transient response**: Low mass diaphragm
- **Controlled directivity**: Horn pattern controls dispersion
- **Lower distortion**: Horn loading reduces excursion

However, horn-loaded HF drivers require careful crossover integration to avoid frequency response dips.

### Why Integrated Approach Matters

The **critical insight** from the BC 12FW88 + DH450 case study:

> **Horn geometry and crossover design are coupled.** You cannot design them independently.

The horn's cutoff frequency (Fc) directly affects:
- Minimum usable crossover frequency
- HF sensitivity (larger mouth = more sensitivity)
- Crossover integration quality

**Traditional approach (WRONG):**
```python
# Design LF enclosure
lf_box = optimize_ported_box(driver)

# Design HF horn independently
horn = optimize_horn(driver)

# Try to make crossover work
crossover = design_crossover(lf_box, horn)  # May have huge dip!
```

**Integrated approach (RIGHT):**
```python
from gsd.optimization.api.two_way_system import design_two_way_system_integrated

design = design_two_way_system_integrated(
    lf_driver_name="BC_12FW88",
    hf_driver_name="BC_DH450",
    target_crossover_hz=800,
    printer_constraints={"max_length": 0.25, "max_mouth_area": 0.0625},
    accept_sensitivity_loss=True
)

print(f"Horn Fc: {design.horn_fc_hz:.0f} Hz")
print(f"Crossover: {design.crossover_frequency_hz:.0f} Hz")
print(f"Dip: {design.dip_db:.2f} dB")
```

### Key Principles

1. **Calculate BEFORE Optimizing**: Determine horn requirements from crossover target BEFORE running optimizer
2. **Check Feasibility First**: Verify mouth area fits printer constraints before proceeding
3. **Sweep Crossover**: Don't assume 2×Fc is optimal - sweep the range
4. **Validate Against Physics**: All calculations must match Hornresp validation

---

## 2. Physics Background

### Horn Cutoff Frequency (Fc)

The horn cutoff frequency is the frequency below which the horn acts as a high-pass filter and does not efficiently propagate sound waves.

**Formula (Olson 1947, Eq. 5.18):**
```
Fc = (c / 4π) × m

where:
  c = speed of sound (343 m/s at 20°C)
  m = flare constant = ln(mouth/throat) / L
```

**Key implications:**
- For fixed length L, **larger mouth → higher Fc**
- **Small mouth changes have LARGE effects on Fc** (logarithmic relationship)
- Fc determines minimum usable crossover frequency

**Example calculation:**
```python
from gsd.optimization.api.horn_physics import calculate_fc_from_mouth

# 7 cm² throat, 250 cm² mouth, 25 cm length
fc = calculate_fc_from_mouth(7.0, 250.0, 25.0)
print(f"Fc = {fc:.0f} Hz")  # ~390 Hz
```

**Literature:**
- `literature/horns/olson_1947.md` - Exponential horn theory, Eq. 5.18
- `literature/horns/beranek_1954.md` - Horn impedance, Chapter 5

### LF Driver Beaming Frequency

LF drivers become directional (beam) at higher frequencies. This limits the maximum usable crossover frequency.

**Formula:**
```
f_beam = 2c / (π × d)

where:
  c = speed of sound (343 m/s)
  d = piston diameter
```

**Design rule:**
```
XO < 0.8 × f_beam  (for flat response)
```

**Example:**
```python
from gsd.optimization.api.horn_physics import calculate_lf_beaming_frequency
from gsd.driver import load_driver

driver = load_driver("BC_12FW88")  # 12" driver
f_beam = calculate_lf_beaming_frequency(driver)
print(f"Beaming: {f_beam:.0f} Hz")  # ~840 Hz
print(f"Max XO: {0.8*f_beam:.0f} Hz")  # ~670 Hz
```

**Literature:**
- Beranek (1954), Chapter 5 - Directivity of circular pistons

### Horn Cutoff vs Mouth Area (for Fixed Length)

For a fixed horn length, mouth area directly controls Fc:

```
Fc = (c / 4π) × (1 / L) × ln(mouth / throat)
```

**Case study data (L = 250mm, throat = 7cm²):**
| Mouth (cm²) | Fc (Hz) | XO Option | Dip Rating |
|-------------|---------|-----------|------------|
| 250 | 390 | ~600Hz | ✅ Good (3.2dB) |
| 350 | 427 | ~850Hz | ⚠️ Acceptable (3.7dB) |
| 504 | 467 | ~950Hz | ❌ Poor (13.8dB) |

**Critical insight:** Small mouth changes → large Fc changes

### Crossover Integration Theory

**Traditional rule:** XO = 2×Fc

**Optimized rule:** XO = 1.2-1.5×Fc (if horn has smooth response)

**Case study finding:**
- BC 12FW88 + DH450 system: Optimal XO = 600 Hz with Fc = 468 Hz
- **XO/Fc ratio = 1.28**, not 2.0!

**Why sweep works better:**
- Traditional rule is conservative
- Actual optimum depends on:
  - Horn response smoothness
  - LF driver rolloff
  - Crossover filter type

---

## 3. Step-by-Step Workflow

### Overview

The complete two-way design workflow has 7 steps:

```
1. Calculate Requirements
   ├─ LF driver beaming frequency
   ├─ Target horn Fc from XO target
   └─ Required mouth area for target Fc

2. Check Feasibility
   ├─ Does mouth fit printer constraints?
   └─ If not, what are the trade-offs?

3. Design LF Enclosure
   ├─ Run DesignAssistant for ported/sealed box
   └─ Get Vb, Fb parameters

4. Optimize Horn Geometry
   ├─ Use multi-segment horn optimizer
   ├─ Constraints: max_length, max_mouth_area
   └─ Get actual horn parameters

5. Optimize Crossover
   ├─ Sweep XO range (don't assume 2×Fc!)
   ├─ Optimize HF padding for flatness
   └─ Select frequency with minimal dip

6. Validate System
   ├─ Calculate crossover dip
   ├─ Calculate system flatness
   └─ Rate design (Excellent/Good/Acceptable/Poor)

7. Export and Validate
   └─ Export to Hornresp for final validation
```

### Step 1: Calculate Requirements

**Before optimizing anything, calculate what you need:**

```python
from gsd.driver import load_driver
from gsd.optimization.api.horn_physics import (
    calculate_lf_beaming_frequency,
    calculate_target_horn_fc,
    calculate_mouth_area_for_fc
)

# Load drivers
lf_driver = load_driver("BC_12FW88")
hf_driver = load_driver("BC_DH450")

# Calculate LF beaming
f_beam = calculate_lf_beaming_frequency(lf_driver)
print(f"LF beaming: {f_beam:.0f} Hz")

# Calculate target horn Fc
desired_xo = 800  # Hz
target_fc = calculate_target_horn_fc(
    desired_crossover_hz=desired_xo,
    lf_driver_beaming_hz=f_beam,
    xo_fc_ratio=2.0  # Traditional 2×Fc rule
)
print(f"Target Fc: {target_fc:.0f} Hz")

# Calculate required mouth
throat_area = hf_driver.S_d * 10000  # m² to cm²
required_mouth = calculate_mouth_area_for_fc(
    throat_area_cm2=throat_area,
    length_cm=25.0,  # 250mm horn
    target_fc_hz=target_fc
)
print(f"Required mouth: {required_mouth:.0f} cm²")
```

**Output:**
```
LF beaming: 840 Hz
Target Fc: 400 Hz
Required mouth: 273 cm²
```

### Step 2: Check Feasibility

```python
from gsd.optimization.api.horn_physics import assess_mouth_area_feasibility

# Check if required mouth fits printer constraint
feasibility = assess_mouth_area_feasibility(
    required_mouth_cm2=273,
    available_mouth_cm2=625,  # 250mm × 250mm printer
    target_fc_hz=400
)

if feasibility['feasible']:
    print("✓ Design is feasible")
else:
    print("✗ Design not feasible")
    print(feasibility['recommendation'])
```

**If not feasible, options:**
1. Use multi-piece horn (2× effective length)
2. Accept higher Fc (smaller mouth)
3. Accept HF sensitivity loss
4. Use larger printer

### Step 3: Design LF Enclosure

```python
from gsd.optimization.api.design_assistant import DesignAssistant

assistant = DesignAssistant(validation_mode=False)

lf_result = assistant.optimize_design(
    driver_name="BC_12FW88",
    enclosure_type="ported",
    objectives=["f3", "flatness"],
    population_size=50,
    generations=50
)

lf_params = lf_result.best_designs[0]['parameters']
print(f"Vb = {lf_params['Vb']*1000:.1f} L")
print(f"Fb = {lf_params['Fb']:.1f} Hz")
```

### Step 4: Optimize Horn Geometry

```python
# Optimize horn with constraints
horn_constraints = {
    "max_length": 0.25,  # 25 cm
    "max_mouth_area": 0.0625,  # 625 cm² (from feasibility check)
}

horn_result = assistant.optimize_design(
    driver_name="BC_DH450",
    enclosure_type="multisegment_horn",
    objectives=["flatness", "wavefront_sphericity"],
    constraints=horn_constraints,
    population_size=50,
    generations=50,
    num_segments=2
)

horn_params = horn_result.best_designs[0]['parameters']
print(f"Throat: {horn_params['throat_area']*10000:.1f} cm²")
print(f"Mouth: {horn_params['mouth_area']*10000:.0f} cm²")
```

### Step 5: Optimize Crossover

```python
from gsd.optimization.api.two_way_system import optimize_crossover_frequency

# Sweep XO range to find optimal point
xo_result = optimize_crossover_frequency(
    lf_driver_name="BC_12FW88",
    hf_driver_name="BC_DH450",
    lf_enclosure_type="ported",
    lf_enclosure_params={"Vb": lf_params['Vb'], "Fb": lf_params['Fb']},
    horn_fc_hz=468,  # From horn optimization
    horn_length_cm=25.0,
    xo_range_hz=(600, 1200)  # Sweep range
)

print(f"Optimal XO: {xo_result['optimal_xo_hz']:.0f} Hz")
print(f"XO/Fc ratio: {xo_result['xo_vs_fc_ratio']:.2f}")
print(f"Dip: {xo_result['dip_db']:.2f} dB")
```

### Step 6: Validate System

```python
# Rate the design
dip = xo_result['dip_db']

if dip < 1.5:
    rating = "✅ Excellent"
elif dip < 2.5:
    rating = "✅ Good"
elif dip < 4:
    rating = "⚠️ Acceptable"
else:
    rating = "❌ Poor"

print(f"System rating: {rating}")
```

### Step 7: Export to Hornresp

```python
from gsd.hornresp.export import export_to_hornresp

export_to_hornresp(
    driver=lf_driver,
    driver_name="12FW88_Design",
    output_path="design.txt",
    comment="Two-way system design",
    enclosure_type="ported_box",
    Vb_liters=lf_params['Vb'] * 1000,
    Fb_hz=lf_params['Fb']
)
```

Then import into Hornresp for validation.

### One-Shot Design (All Steps Combined)

For most users, the integrated function does all 7 steps automatically:

```python
from gsd.optimization.api.two_way_system import design_two_way_system_integrated

design = design_two_way_system_integrated(
    lf_driver_name="BC_12FW88",
    hf_driver_name="BC_DH450",
    target_crossover_hz=800,
    printer_constraints={"max_length": 0.25, "max_mouth_area": 0.0625},
    enclosure_type="ported",
    xo_fc_ratio=2.0,
    accept_sensitivity_loss=True,
    verbose=True
)

print(f"\nHorn Fc: {design.horn_fc_hz:.0f} Hz")
print(f"Crossover: {design.crossover_frequency_hz:.0f} Hz")
print(f"Dip: {design.dip_db:.2f} dB")
print(f"Rating: {design.validation['rating']}")
```

---

## 4. Decision Trees

### Decision Tree 1: Choose Crossover Frequency

```
START: What crossover frequency do you want?

  ↓

Calculate LF driver beaming frequency:
  f_beam = 2c / (π × d)

  ↓

Is desired XO < 0.8 × f_beam?
  ├─ YES → Use desired XO
  └─ NO  → Cap XO at 0.8 × f_beam

  ↓

Calculate target horn Fc:
  Option A: Fc = XO / 2.0 (traditional, max sensitivity)
  Option B: Fc = XO / 1.3 (optimized, better integration)

  ↓

Calculate required mouth area for target Fc:
  mouth = throat × exp((4π × Fc × L) / c)

  ↓

Does required mouth fit printer constraint?
  ├─ YES → Proceed with design
  └─ NO  → See Decision Tree 2
```

### Decision Tree 2: Mouth Area Trade-off

```
START: Required mouth exceeds constraint

  ↓

What's your priority?

  ├─ Priority: Best crossover integration
  │    ↓
  │  Accept smaller mouth (use max available)
  │    ↓
  │  Result: Lower Fc, lower sensitivity, better integration
  │    ↓
  │  Use accept_sensitivity_loss=True
  │
  └─ Priority: Max HF sensitivity
       ↓
     Options:
       1. Use multi-piece horn (2× length)
       2. Increase crossover frequency
       3. Use larger printer
```

### Decision Tree 3: Handle Crossover Dip

```
START: Dip > 4 dB (Poor rating)

  ↓

What's the XO/Fc ratio?

  ├─ XO/Fc < 1.2
  │    ↓
  │  Problem: XO too close to horn cutoff
  │    ↓
  │  Solution: Increase crossover frequency
  │
  ├─ 1.2 ≤ XO/Fc ≤ 2.0
  │    ↓
  │  Problem: Crossover optimization failed
  │    ↓
  │  Solution: Check HF padding optimization
  │
  └─ XO/Fc > 2.0
       ↓
     Problem: XO too high for LF driver
       ↓
     Solution: Lower XO to < 0.8 × f_beam
```

---

## 5. Case Studies

### Case Study 1: BC 12FW88 + DH450 (250mm³ Printer)

**Problem:**
Design a two-way system with:
- LF: BC 12FW88 (12" woofer)
- HF: BC DH450 (compression driver)
- Target XO: 800 Hz
- Printer: 250mm cube

**Initial Attempt (Failed):**
- Used preset horn: 504cm² mouth
- Result: Fc = 1865 Hz → XO = 3730 Hz → **13.75 dB dip** (POOR)

**Root Cause:**
Horn Fc too high → XO too high → LF driver beaming

**Solution (Successful):**
```python
design = design_two_way_system_integrated(
    lf_driver_name="BC_12FW88",
    hf_driver_name="BC_DH450",
    target_crossover_hz=800,
    printer_constraints={"max_length": 0.25, "max_mouth_area": 0.0625},
    accept_sensitivity_loss=True
)
```

**Results:**
- Mouth: 250 cm² (vs 504 cm² required)
- Horn Fc: 468 Hz
- Crossover: 600 Hz (1.28×Fc)
- Dip: **3.17 dB** (ACCEPTABLE)

**Key Insight:**
Optimal XO = 1.28×Fc, not 2×Fc

### Case Study 2: BC 8NDL51 + DH450 (Compact System)

**Problem:**
Design compact two-way system with:
- LF: BC 8NDL51 (8" woofer)
- HF: BC DH450
- Printer: 200mm cube

**Analysis:**
```python
# LF beaming frequency
f_beam = calculate_lf_beaming_frequency(load_driver("BC_8NDL51"))
# f_beam ≈ 1300 Hz
# Max XO ≈ 1040 Hz

# Target XO for 8" driver: 1000-1200 Hz
target_xo = 1100  # Hz
```

**Design:**
```python
design = design_two_way_system_integrated(
    lf_driver_name="BC_8NDL51",
    hf_driver_name="BC_DH450",
    target_crossover_hz=1100,
    printer_constraints={"max_length": 0.20, "max_mouth_area": 0.04},
    accept_sensitivity_loss=True
)
```

**Results:**
- Horn Fc: ~800 Hz
- Crossover: ~1100 Hz (1.4×Fc)
- Dip: ~3.5 dB (ACCEPTABLE)

### Case Study 3: Different XO Targets (12FW88 + DH450)

**Comparison of three XO targets:**

| Target XO | Horn Fc | XO Used | XO/Fc | Dip | Rating |
|-----------|---------|---------|-------|-----|--------|
| 600 Hz | 468 Hz | 600 Hz | 1.28 | 3.17 dB | ✅ Good |
| 800 Hz | 468 Hz | 850 Hz | 1.82 | 3.72 dB | ⚠️ Acceptable |
| 1200 Hz | 468 Hz | N/A | N/A | > 8 dB | ❌ Poor (XO > beaming) |

**Conclusion:**
Lower XO (600 Hz) gives better integration with same horn.

---

## 6. Troubleshooting

### Problem 1: Dip Too Large (> 4 dB)

**Symptoms:**
- Crossover region has deep notch
- Dip > 4 dB

**Diagnosis:**
```python
print(f"XO/Fc ratio: {crossover_freq / horn_fc:.2f}")
print(f"XO vs beaming: {crossover_freq / lf_beaming:.2f}")
```

**Solutions:**

**If XO/Fc < 1.2:**
- XO too close to horn cutoff
- **Solution:** Increase crossover frequency

**If 1.2 ≤ XO/Fc ≤ 2.0:**
- Crossover optimization issue
- **Solution:** Check HF padding optimization

**If XO/Fc > 2.0:**
- XO too high for LF driver
- **Solution:** Lower XO to < 0.8 × f_beam

### Problem 2: HF Sensitivity Too Low

**Symptoms:**
- HF driver requires > -20 dB padding
- System sensitivity < 90 dB

**Diagnosis:**
```python
# Check mouth area ratio
actual_mouth = horn_params['mouth_area'] * 10000  # to cm²
required_mouth = calculate_mouth_area_for_fc(...)

ratio = actual_mouth / required_mouth
penalty = 10 * np.log10(ratio)

print(f"Sensitivity penalty: {penalty:.1f} dB")
```

**Solutions:**
1. Use multi-piece horn (larger effective mouth)
2. Accept higher crossover frequency
3. Use larger printer
4. Use different HF driver with higher sensitivity

### Problem 3: Constraints Not Met

**Symptoms:**
- Required mouth > available mouth
- ValueError raised

**Diagnosis:**
```python
from gsd.optimization.api.horn_physics import assess_mouth_area_feasibility

feasibility = assess_mouth_area_feasibility(
    required_mouth_cm2=required,
    available_mouth_cm2=available,
    target_fc_hz=target_fc
)

print(feasibility['recommendation'])
```

**Solutions:**

**Option 1: Accept sensitivity loss**
```python
design = design_two_way_system_integrated(
    ...,
    accept_sensitivity_loss=True  # Use smaller mouth
)
```

**Option 2: Use multi-piece horn**
```python
design = design_two_way_system_integrated(
    ...,
    printer_constraints={"max_length": 0.50},  # 2× length
    allow_multi_piece=True
)
```

**Option 3: Increase XO frequency**
```python
design = design_two_way_system_integrated(
    ...,
    target_crossover_hz=1200  # Higher XO = smaller required mouth
)
```

### Problem 4: Optimization Fails

**Symptoms:**
- `ValueError: optimization failed`
- Empty best_designs list

**Diagnosis:**
```python
print(result.warnings)
print(result.constraints)
```

**Solutions:**
1. Relax constraints (increase max_length or max_mouth_area)
2. Increase population_size and generations
3. Check driver parameters are valid
4. Try different objectives

---

## 7. API Reference

### horn_physics Module

**Calculate LF beaming frequency:**
```python
from gsd.optimization.api.horn_physics import calculate_lf_beaming_frequency

f_beam = calculate_lf_beaming_frequency(driver)
# Returns: float (Hz)
```

**Calculate target horn Fc:**
```python
from gsd.optimization.api.horn_physics import calculate_target_horn_fc

fc = calculate_target_horn_fc(
    desired_crossover_hz=800,
    lf_driver_beaming_hz=840,  # Optional
    xo_fc_ratio=2.0  # Traditional: 2.0, Optimized: 1.3
)
# Returns: float (Hz)
```

**Calculate required mouth for target Fc:**
```python
from gsd.optimization.api.horn_physics import calculate_mouth_area_for_fc

mouth = calculate_mouth_area_for_fc(
    throat_area_cm2=7.0,
    length_cm=25.0,
    target_fc_hz=400
)
# Returns: float (cm²)
```

**Calculate Fc from mouth geometry:**
```python
from gsd.optimization.api.horn_physics import calculate_fc_from_mouth

fc = calculate_fc_from_mouth(
    throat_area_cm2=7.0,
    mouth_area_cm2=250.0,
    length_cm=25.0
)
# Returns: float (Hz)
```

**Assess mouth area feasibility:**
```python
from gsd.optimization.api.horn_physics import assess_mouth_area_feasibility

result = assess_mouth_area_feasibility(
    required_mouth_cm2=273,
    available_mouth_cm2=250,
    target_fc_hz=400,
    throat_area_cm2=7.0,
    length_cm=25.0
)
# Returns: Dict with 'feasible', 'recommendation', etc.
```

### two_way_system Module

**Optimize crossover frequency (sweep):**
```python
from gsd.optimization.api.two_way_system import optimize_crossover_frequency

result = optimize_crossover_frequency(
    lf_driver_name="BC_12FW88",
    hf_driver_name="BC_DH450",
    lf_enclosure_type="ported",
    lf_enclosure_params={"Vb": 0.1145, "Fb": 47.6},
    horn_fc_hz=468,
    horn_length_cm=25.0,
    xo_range_hz=(600, 1200),
    step_hz=50
)
# Returns: Dict with 'optimal_xo_hz', 'dip_db', etc.
```

**Integrated two-way design (one-shot):**
```python
from gsd.optimization.api.two_way_system import design_two_way_system_integrated

design = design_two_way_system_integrated(
    lf_driver_name="BC_12FW88",
    hf_driver_name="BC_DH450",
    target_crossover_hz=800,
    printer_constraints={"max_length": 0.25, "max_mouth_area": 0.0625},
    enclosure_type="ported",
    xo_fc_ratio=2.0,
    accept_sensitivity_loss=False,
    verbose=True
)
# Returns: TwoWaySystemDesign object
```

**Parameters:**
- `lf_driver_name`: Low-frequency driver name (str)
- `hf_driver_name`: High-frequency driver name (str)
- `target_crossover_hz`: Target crossover frequency (float, Hz)
- `printer_constraints`: Dict with 'max_length' (m) and 'max_mouth_area' (m²)
- `enclosure_type`: "ported" or "sealed" (str)
- `xo_fc_ratio`: Desired XO/Fc ratio (float, default 2.0)
- `accept_sensitivity_loss`: Use smaller mouth if needed (bool, default False)
- `verbose`: Print progress messages (bool, default True)

**Returns:**
TwoWaySystemDesign object with:
- `horn_fc_hz`: Horn cutoff frequency (Hz)
- `crossover_frequency_hz`: Actual crossover used (Hz)
- `dip_db`: Crossover dip (dB)
- `flatness_db`: System flatness (dB)
- `validation`: Dict with rating and recommendations

### Decision Tree Module

**Interactive design guide:**
```python
from gsd.optimization.api.two_way_decision_tree import guide_two_way_design_decisions

rec = guide_two_way_design_decisions()
# Follow prompts...

# Get config for integrated design
config = rec.to_dict()
design = design_two_way_system_integrated(**config)
```

**Non-interactive mode:**
```python
rec = guide_two_way_design_decisions(
    lf_driver_name="BC_12FW88",
    hf_driver_name="BC_DH450",
    target_crossover_hz=800,
    printer_preset="250mm_cube"
)
```

### Trade-off Analysis Module

**Analyze mouth vs Fc trade-off:**
```python
from gsd.optimization.api.trade_off_analysis import analyze_mouth_vs_fc_tradeoff
import numpy as np

mouths = np.linspace(200, 600, 9)
result = analyze_mouth_vs_fc_tradeoff(
    lf_driver_name="BC_12FW88",
    hf_driver_name="BC_DH450",
    horn_length_cm=25.0,
    mouth_areas_cm2=mouths,
    target_xo_hz=800
)

print(result.analysis)
```

**Plot mouth-sensitivity curve:**
```python
from gsd.optimization.api.trade_off_analysis import plot_mouth_sensitivity_curve

plot_mouth_sensitivity_curve(
    lf_driver_name="BC_12FW88",
    hf_driver_name="BC_DH450",
    horn_length_cm=25.0,
    target_xo_hz=800,
    save_path="tradeoff.png"
)
```

**Generate trade-off report:**
```python
from gsd.optimization.api.trade_off_analysis import generate_trade_off_report

generate_trade_off_report(
    lf_driver_name="BC_12FW88",
    hf_driver_name="BC_DH450",
    target_xo_hz=800,
    printer_constraints={"max_length": 0.25, "max_mouth_area": 0.0625},
    output_path="report.txt"
)
```

---

## 8. Best Practices

### DO: Always Calculate Before Optimizing

```python
# ✓ RIGHT: Calculate requirements first
target_fc = calculate_target_horn_fc(desired_xo, f_beam)
required_mouth = calculate_mouth_area_for_fc(...)

# Check feasibility before optimizing
feasibility = assess_mouth_area_feasibility(required_mouth, available, target_fc)
```

```python
# ✗ WRONG: Jump straight to optimization
horn = optimize_horn(driver)  # May have wrong Fc!
crossover = design_crossover(horn)  # Dip may be huge!
```

### DO: Check Feasibility First

```python
# ✓ RIGHT: Check if design fits constraints
if not feasibility['feasible']:
    # Make informed decision about trade-offs
    print(feasibility['recommendation'])
```

### DO: Sweep Crossover Range

```python
# ✓ RIGHT: Sweep to find optimal XO
result = optimize_crossover_frequency(
    ...,
    xo_range_hz=(600, 1200)  # Sweep range
)
# May find XO = 1.28×Fc (not 2×Fc)
```

```python
# ✗ WRONG: Assume 2×Fc is optimal
crossover_freq = horn_fc * 2.0  # May not be optimal!
```

### DO: Validate Against Hornresp

```python
# ✓ RIGHT: Export and validate
export_to_hornresp(...)
# Load in Hornresp
# Compare responses
# Investigate discrepancies
```

### DON'T: Design LF and HF Independently

```python
# ✗ WRONG: Sequential design
lf_design = optimize_lf_enclosure(driver)
hf_design = optimize_horn(driver)  # Ignores LF!
crossover = design_crossover(lf_design, hf_design)  # May fail!
```

```python
# ✓ RIGHT: Integrated design
design = design_two_way_system_integrated(
    lf_driver_name="BC_12FW88",
    hf_driver_name="BC_DH450",
    target_crossover_hz=800,  # Specify upfront
    ...
)
```

### DON'T: Ignore LF Driver Beaming

```python
# ✗ WRONG: Use arbitrary XO
crossover = design_crossover(xo=2500)  # Too high for 12" driver!
# Result: Poor integration due to beaming
```

```python
# ✓ RIGHT: Cap XO at beaming
f_beam = calculate_lf_beaming_frequency(lf_driver)
max_xo = 0.8 * f_beam
crossover = design_crossover(xo=min(desired_xo, max_xo))
```

### DON'T: Use Preset Horns Without Checking Fc

```python
# ✗ WRONG: Use preset without checking
horn = get_preset_horn("large_horn")
# Horn Fc may be 1865 Hz → XO must be > 3700 Hz → LF beaming!
```

```python
# ✓ RIGHT: Calculate required mouth for target Fc
target_fc = calculate_target_horn_fc(desired_xo, ...)
required_mouth = calculate_mouth_area_for_fc(...)
# Design horn with required mouth
```

---

## 9. Glossary

**Beaming Frequency (f_beam)**
Frequency above which a driver becomes directional. For circular pistons:
```
f_beam = 2c / (π × d)
```

**Crossover Dip**
Notch in frequency response at crossover point. Caused by:
- XO too close to horn cutoff (XO/Fc < 1.2)
- XO too close to LF beaming (XO > 0.8 × f_beam)
- Improper HF padding

**Cutoff Frequency (Fc)**
Frequency below which horn acts as high-pass filter. For exponential horn:
```
Fc = (c / 4π) × (1 / L) × ln(mouth / throat)
```

**Exponential Horn**
Horn profile where cross-sectional area grows exponentially with distance:
```
S(x) = S_t × exp(m × x)
```

**LF Driver**
Low-frequency driver (woofer) in two-way system.

**HF Driver**
High-frequency driver (compression driver) in two-way system.

**Linkwitz-Riley 4th-Order (LR4)**
Crossover filter with -24 dB/octave slope. Perfect summation at crossover.

**Mouth Area**
Horn mouth cross-sectional area. Larger mouth → higher Fc → more sensitivity.

**Multi-Piece Horn**
Horn printed in multiple sections and assembled. Allows larger than printer build volume.

**Sensitivity Penalty**
HF sensitivity loss due to smaller mouth area. Approx:
```
penalty (dB) = 10 × log10(actual_mouth / required_mouth)
```

**Throat Area**
Horn throat cross-sectional area (typically equals HF driver diaphragm area).

**Two-Way System**
Loudspeaker with LF and HF drivers and crossover network.

**XO/Fc Ratio**
Ratio of crossover frequency to horn cutoff frequency.
- Traditional: 2.0
- Optimized: 1.2-1.5

---

## References

**Literature:**
- Olson (1947) - Elements of Acoustical Engineering
- Beranek (1954) - Acoustics
- Small (1972) - Closed-box loudspeaker systems
- Linkwitz (1976) - Active crossover networks

**Case Studies:**
- `docs/two_way_design_review_12fw88_dh450.md` - Complete design review

**Implementation Plan:**
- `docs/two_way_implementation_plan.md` - Full technical details

**Validation:**
- Hornresp: http://www.hornresp.net/

---

**End of Guide**

For questions or issues, see:
- GSD Documentation: `README.md`
- GSD Roadmap: `ROADMAP.md`
- Project Issues: https://github.com/wokhouse/gsd/issues
