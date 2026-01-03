# Sealed Box QL Validation Dataset

## Purpose

Validate gsd's sealed box QL implementation across various Quc (mechanical + absorption losses) values.

## Enclosure Design

- **Driver**: BC 8NDL51 (8" driver)
  - Fs = 64 Hz
  - Qts = 0.37
  - Vas = 14.0 L
- **Enclosure**: Sealed Box, Vb = 10.0 L
  - Fc ≈ 99 Hz (system resonance)
  - α ≈ 1.4 (compliance ratio)

## Input Files

| File | Quc Value | Description |
|------|-----------|-------------|
| `input_ql5.txt` | 5 | Low losses (well-filled box) |
| `input_ql7.txt` | 7 | Hornresp default (typical unfilled) |
| `input_ql10.txt` | 10 | Moderate losses |
| `input_ql20.txt` | 20 | Low losses (well-sealed) |
| `input_ql100.txt` | 100 | Near-lossless (theoretical) |

## How to Generate sim.txt Files

**For each input file:**

1. Open Hornresp
2. File → Import → Select `input_qlXX.txt`
3. **CRITICAL**: Double-click the "QL" label in the schematic
4. Set QL to the file's Quc value (e.g., 7 for input_ql7.txt)
5. Tools → Loudspeaker Wizard → Calculate
6. Tools → Export → Angular Frequency
7. Save as `sim_qlXX.txt` in this directory

**Example for QL=7:**
```bash
cd tests/validation/drivers/bc_8ndl51/sealed_box/ql
# Import input_ql7.txt into Hornresp
# Set QL = 7
# Export as sim_ql7.txt
```

## Expected Results

### System Parameters
```
α = Vas / Vb = 14.0 / 10.0 = 1.4
Fc = Fs × √(1 + α) = 64 × √2.4 ≈ 99 Hz
Qec = Qes × √(1 + α) = 0.38 × √2.4 ≈ 0.59
```

### Quc Variations

| Quc | Qtc_total | Description |
|-----|-----------|-------------|
| 5   | ~0.53 | Heavy damping (filled box) |
| 7   | ~0.54 | Typical unfilled box |
| 10  | ~0.55 | Light damping |
| 20  | ~0.57 | Very light damping |
| 100 | ~0.59 | Nearly lossless |

**Calculation**: `Qtc_total = (Qec × Quc) / (Qec + Quc)`

### Hornresp Comparison

**Expected validation tolerances:**
- System parameters: <0.5 Hz, <0.02 tolerance
- Impedance magnitude: <10% error (20-500 Hz)
- Impedance peak height: Should decrease with lower Quc

## Theory

**Parallel Q Combination** (Small 1972, Eq. 9):
```
Qtc_total = (Qec × Quc) / (Qec + Quc)

Where:
- Qec = Qes × √(1 + α)  # Electrical Q at system resonance
- Quc = Mechanical + absorption losses
- α = Vas / Vb  # Compliance ratio
```

**Physical Meaning**:
- Quc represents mechanical losses (box walls, suspension) + absorption losses (filling)
- Lower Quc = more losses = more damping = lower impedance peak
- Quc = ∞ represents no losses (theoretical limit)

## Literature

- Small (1972), Eq. 9 - Parallel Q combination for sealed boxes
- Hornresp V53.20 - Default QL = 7
- Bullock (1991) - Typical Quc values for filled/unfilled boxes

## Validation Status

- [ ] input_ql5.txt → sim_ql5.txt
- [ ] input_ql7.txt → sim_ql7.txt
- [ ] input_ql10.txt → sim_ql10.txt
- [ ] input_ql20.txt → sim_ql20.txt
- [ ] input_ql100.txt → sim_ql100.txt
