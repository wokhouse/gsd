# Sealed Box QL=7 Validation

## Purpose

Validate gsd's sealed box QL implementation with Quc=7 (Hornresp default).

## Design Parameters

- **Driver**: BC 8NDL51 (8" driver)
  - Fs = 64 Hz
  - Qts = 0.37
  - Vas = 14.0 L
- **Enclosure**: Sealed Box
  - Vb = 10.0 L
  - Quc = 7.0 (Hornresp default for unfilled box)

## Quc=7 Characteristics

**Quc = 7** represents:
- Typical unfilled box with mechanical losses only
- No absorption material
- Standard Hornresp default value
- Most common for validation comparisons

## Expected Results

### System Parameters
```
α = Vas / Vb = 14.0 / 10.0 = 1.4
Fc = Fs × √(1 + α) = 64 × √2.4 ≈ 99 Hz
Qec = Qes × √(1 + α) = 0.38 × √2.4 ≈ 0.59
Qtc_total = (Qec × Quc) / (Qec + Quc) = (0.59 × 7) / 7.59 ≈ 0.54
```

### Hornresp Comparison

**Expected validation tolerances:**
- Impedance magnitude: <10% error across frequency range
- Impedance peak height: Should be lower than Quc=20 (more damping)
- Impedance peak frequency: Should match Fc within 5%

## How to Generate sim.txt

1. Open Hornresp
2. File → Import → Select `input.txt`
3. **CRITICAL**: Double-click the "QL" label in the schematic
4. Set QL = **7.0**
5. Tools → Loudspeaker Wizard → Calculate
6. Tools → Export → Angular Frequency
7. Save as `sim.txt` in this directory

## Theory

**Parallel Q Combination** (Small 1972, Eq. 9):
```
Qtc_total = (Qec × Quc) / (Qec + Quc)

Where:
- Qec = 0.59 (electrical Q at Fc)
- Quc = 7.0 (mechanical + absorption losses)
- Qtc_total = 0.54 (total system Q)
```

## Literature

- Small (1972), Eq. 9 - Parallel Q combination
- Hornresp V53.20 - Default QL = 7
- Bullock (1991) - Typical Quc values for unfilled boxes
