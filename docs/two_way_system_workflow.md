# Two-Way Loudspeaker System Design Workflow

This guide explains how to design complete two-way loudspeaker systems using the GSD optimization tools, including crossover design and bi-amped system optimization.

## Overview

The two-way system design workflow consists of four main steps:

1. **LF Enclosure Optimization** - Design ported/sealed box for woofer
2. **HF Horn Optimization** (optional) - Design horn for compression driver
3. **Crossover Design** - Find optimal crossover frequency and filter type
4. **HF Padding Optimization** - Tune HF level for bi-amped systems

## Quick Start

```python
from gsd.optimization.api.two_way_system import design_two_way_system

# Design complete two-way system
design = design_two_way_system(
    lf_driver_name="BC_12FW88",
    hf_driver_name="BC_DH450",
    lf_enclosure_type="ported",
    horn_constraints={
        "max_length": 0.25,  # 250mm max (for 3D printing)
        "target_cutoff": 400  # Hz
    }
)

print(design)
```

## Detailed Workflow

### Step 1: LF Enclosure Optimization

Use the `DesignAssistant` to optimize the low-frequency enclosure:

```python
from gsd.optimization.api.design_assistant import DesignAssistant

assistant = DesignAssistant()

# Optimize ported box
result = assistant.optimize_design(
    driver_name="BC_12FW88",
    enclosure_type="ported",
    objectives=["f3", "flatness"],
    population_size=50,
    generations=50
)

best_design = result.best_designs[0]
print(f"Vb = {best_design['parameters']['Vb']*1000:.1f} L")
print(f"Fb = {best_design['parameters']['Fb']:.1f} Hz")
print(f"F3 = {best_design['objectives']['f3']:.1f} Hz")
```

### Step 2: HF Horn Optimization (Compression Drivers)

For compression drivers, optimize horn parameters within physical constraints:

```python
from gsd.optimization.api.design_assistant import DesignAssistant

assistant = DesignAssistant()

# Optimize exponential horn
result = assistant.optimize_design(
    driver_name="BC_DH450",
    enclosure_type="exponential_horn",
    objectives=["flatness", "efficiency"],
    constraints={
        "preset": "midrange_horn",
        "max_length": 0.25,  # 250mm
        "max_mouth_area": 0.0625,  # 250mm x 250mm
        "max_volume": 0.015625,  # 15.6 L
    }
)
```

**Key Horn Parameters:**
- `throat_area`: Coupling to driver (typically 20-50% of S_d)
- `mouth_area`: Radiation area (affects cutoff frequency)
- `length`: Axial length (longer = lower cutoff)
- `V_tc`: Throat chamber volume (phase plug cavity)
- `V_rc`: Rear chamber volume (optional compliance)

**Horn Cutoff Frequency:**

For exponential horns, the cutoff frequency is:

```
f_c = (c * m) / (4π)

where:
    c = speed of sound (343 m/s)
    m = flare constant = ln(mouth_area/throat_area) / length
```

The horn cutoff should be **below the crossover frequency** by a factor of 2-3× for optimal performance.

### Step 3: Crossover Design

Use the `CrossoverDesignAssistant` to design the crossover:

```python
from gsd.optimization.api.crossover_assistant import CrossoverDesignAssistant

assistant = CrossoverDesignAssistant()

design = assistant.design_crossover(
    lf_driver_name="BC_12FW88",
    hf_driver_name="BC_DH450",
    lf_enclosure_type="ported",
    lf_enclosure_params={"Vb": 0.1145, "Fb": 46.4},
    hf_horn_params={"cutoff": 400, "length": 0.24},
    crossover_range=(800, 2500)
)

print(f"Crossover: {design.crossover_frequency:.0f} Hz")
print(f"HF padding: {design.hf_padding_db:.2f} dB")
```

**Crossover Design Guidelines:**

1. **Crossover Frequency** should be:
   - Above the woofer's beaming frequency (typically >1-1.5 kHz for 10-12" drivers)
   - Above the horn cutoff by 2-3×
   - In the range where both drivers have flat response

2. **Filter Type** recommendations:
   - **LR4 (4th-order Linkwitz-Riley)**: Most common, good phase alignment
   - **LR2 (2nd-order Linkwitz-Riley)**: Simpler, wider overlap
   - **Butterworth**: Alternative to LR with different characteristics

3. **Crossover/Horn Ratio**:
   - For compression drivers on horns: `XO_frequency / horn_cutoff ≥ 2.0`
   - This ensures the horn is operating in its passband at crossover

### Step 4: HF Padding Optimization (Bi-amped Systems)

For bi-amped systems with digital crossovers, optimize the HF padding for best flatness:

```python
from gsd.optimization.api.two_way_system import optimize_hf_padding_for_flatness

optimal_pad = optimize_hf_padding_for_flatness(
    lf_driver_name="BC_12FW88",
    hf_driver_name="BC_DH450",
    lf_enclosure_type="ported",
    lf_enclosure_params={"Vb": 0.1145, "Fb": 46.4},
    horn_params={"cutoff": 400, "length": 0.24},
    crossover_frequency=1000,
    padding_range=(-25, -10),  # Search range in dB
    num_steps=31
)

print(f"Optimal HF padding: {optimal_pad:.2f} dB")
```

**Why Optimize Padding?**

Compression drivers typically have higher sensitivity (105-110 dB) than woofers (85-95 dB). For bi-amped systems, you can:
- Attenuate the HF channel in the digital crossover
- Match levels at crossover for optimal flatness
- Avoid excessive padding that would waste HF headroom

## F3 Calculation Methodology

The **F3** (-3 dB frequency) is calculated using the **LF driver's passband** as the reference, NOT the system passband.

**Why?**

The system response includes both LF and HF drivers. If we used the system maximum (which includes the HF horn's 110 dB), the F3 would be incorrectly calculated.

**Correct Method:**

1. Define LF driver passband (typically 80-200 Hz for woofers)
2. Find maximum level in this range
3. Find frequency where response drops to (max_level - 3 dB)
4. Use linear interpolation for accuracy

```python
# LF passband reference
lf_passband = (freq >= 80) & (freq <= 200)
lf_passband_level = np.max(lf_response[lf_passband])
threshold = lf_passband_level - 3

# Find crossing point
for i in range(len(freq) - 1):
    if lf_response[i] < threshold and lf_response[i + 1] >= threshold:
        # Linear interpolation
        f1, f2 = freq[i], freq[i + 1]
        r1, r2 = lf_response[i], lf_response[i + 1]
        f3 = f1 + (threshold - r1) * (f2 - f1) / (r2 - r1)
        break
```

This method gives the **actual F3 of the LF enclosure**, independent of HF driver sensitivity.

## System Performance Metrics

When evaluating a two-way system design, check:

1. **F3** - Should be <60 Hz for full-range speakers
2. **Flatness** - Should be <6 dB across 100 Hz - 10 kHz
3. **Crossover ratio** - XO/horn_cutoff ≥ 2.0 for horns
4. **Sensitivity matching** - HF padding <20 dB preferred

## Complete Example

```python
from gsd.optimization.api.two_way_system import design_two_way_system

# Design complete system with constraints
design = design_two_way_system(
    lf_driver_name="BC_12FW88",
    hf_driver_name="BC_DH450",
    lf_enclosure_type="ported",
    crossover_range=(800, 2500),
    optimize_hf_padding=True,
    horn_constraints={
        "max_length": 0.25,      # 250mm cube constraint
        "max_mouth_area": 0.0625, # 250mm x 250mm
        "max_volume": 0.015625,   # 15.6 L
        "target_cutoff": 400      # Hz
    },
    population_size=50,
    generations=50
)

# Print design summary
print(design)

# Access individual parameters
print(f"\nLF Enclosure:")
print(f"  Vb = {design.lf_enclosure_params['Vb']*1000:.1f} L")
print(f"  Fb = {design.lf_enclosure_params['Fb']:.1f} Hz")
print(f"  F3 = {design.f3:.1f} Hz")

print(f"\nCrossover:")
print(f"  Frequency = {design.crossover_frequency:.0f} Hz")
print(f"  HF gain = {design.hf_padding_db:.2f} dB")

print(f"\nPerformance:")
print(f"  Flatness = {design.flatness:.2f} dB")
print(f"  System level = {design.system_level:.1f} dB")
```

## Troubleshooting

### Poor Flatness (>10 dB)

**Causes:**
- Crossover too close to horn cutoff
- Large sensitivity mismatch between drivers
- Incorrect padding

**Solutions:**
1. Increase crossover/horn_cutoff ratio to ≥2.5
2. Optimize HF padding for bi-amped systems
3. Consider different HF driver with better sensitivity match

### F3 Seems Too Low (<40 Hz)

**Check:** Are you using system passband or LF passband as reference?

The F3 should be calculated from the **LF driver's passband only**, not the system maximum which includes the HF horn.

### Horn Too Large for Constraints

**Solutions:**
1. Increase target cutoff frequency (higher Fc = shorter horn)
2. Accept larger mouth area (compromises low-frequency loading)
3. Consider multi-segment horn for better size/performance tradeoff

## Literature References

- Small, R. H. (1972). "Closed-Box Loudspeaker Systems"
- D'Appolito, J. (1984). "Optimizing Two-Way Loudspeaker Systems"
- Linkwitz, S. (1976). "Active Crossover Networks"
- Olson, H. F. (1947). "Elements of Acoustical Engineering"
- Thiele, N. (1971). "Loudspeakers in Vented Boxes"
