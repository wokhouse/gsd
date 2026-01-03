# QL (Box Losses) Validation Dataset

## Overview

This dataset validates gsd's QL (box losses) implementation against Hornresp simulations across various QL values for both sealed and ported box enclosures.

## Directory Structure

```
bc_8ndl51/
├── sealed_box/
│   ├── ql5/          # Quc = 5 (low losses, well-filled box)
│   ├── ql7/          # Quc = 7 (Hornresp default)
│   ├── ql10/         # Quc = 10 (moderate losses)
│   ├── ql20/         # Quc = 20 (low losses, well-sealed)
│   ├── ql100/        # Quc = 100 (near-lossless)
│   └── generate_ql_validation_files.py
└── ported/
    ├── ql5/          # QL = 5 (large box with more leakage)
    ├── ql7/          # QL = 7 (Hornresp default)
    ├── ql10/         # QL = 10 (WinISD default)
    ├── ql20/         # QL = 20 (well-sealed box)
    └── generate_ql_validation_files.py
```

## Driver Specifications

**BC 8NDL51** (8" driver from B&C Speakers)
- Fs = 64 Hz
- Qts = 0.37
- Qes = 0.38
- Qms = 6.67
- Vas = 14.0 L
- Sd = 232 cm²

## Enclosure Designs

### Sealed Box
- **Vb = 10.0 L** (moderate compliance ratio α ≈ 1.4)
- **Fc ≈ 99 Hz** (system resonance)

### Ported Box
- **Vb = 20.0 L**
- **Fb = 50.0 Hz**
- **Port**: 42.3 cm² × 22.1 cm (single circular port)

## QL Value Reference

### Sealed Box (Quc - Mechanical + Absorption)

| Quc | Description | Typical Use |
|-----|-------------|-------------|
| 5   | Low losses (well-filled box) | Heavy damping with polyfill |
| 7   | Hornresp default | Typical unfilled box |
| 10  | Moderate losses | Large box, light filling |
| 20  | Low losses | Very well-sealed |
| 100 | Near-lossless | Theoretical limit |

**Literature**:
- Small (1972), Eq. 9 - Parallel Q combination
- Bullock (1991) - Typical Quc values

### Ported Box (QL - Leakage Losses)

| QL  | Description | Typical Use |
|-----|-------------|-------------|
| 5   | Large box with more leakage | Poorly sealed |
| 7   | Hornresp default | Standard DIY construction |
| 10  | WinISD default | Well-sealed box |
| 20  | Well-sealed box | Professional construction |

**Literature**:
- Small (1973), Eq. 19 - Combined box losses
- Hornresp V53.20 - Default QL = 7

## How to Generate Hornresp Data

### For Each QL Directory:

1. **Open Hornresp**
   ```
   Hornresp → File → Import → Select input.txt
   ```

2. **Set QL Value** (CRITICAL STEP)
   - Double-click the "QL" label in the schematic
   - Enter the QL value for that directory (e.g., 7 for ql7/)
   - Press Enter

3. **Calculate Response**
   ```
   Tools → Loudspeaker Wizard → Calculate
   ```
   - Accept defaults (10-20000 Hz, 2.83V)
   - Click "Calculate"

4. **Export Results**
   ```
   Tools → Export → Angular Frequency
   ```
   - Save as `sim.txt` in the same directory as `input.txt`
   - This creates the validation reference data

5. **Verify Export**
   - Check that `sim.txt` was created
   - File should contain frequency, impedance, phase, SPL columns

## Validation Tests

Once Hornresp data is generated, run validation tests:

```bash
# Unit tests (formula verification)
PYTHONPATH=src pytest tests/validation/test_ql_box_losses.py -v

# Integration tests (Hornresp comparison)
PYTHONPATH=src pytest tests/integration/test_ql_hornresp_comparison.py -v
```

## Expected Validation Tolerances

### Sealed Box
- **System parameters (Fc, Qtc)**: <0.5 Hz, <0.02 tolerance
- **Impedance magnitude**: <10% error across 20-500 Hz
- **Impedance peak height**: Should decrease with lower Quc (more damping)

### Ported Box
- **Impedance peaks**: Dual peaks at Fb/√2 and Fb×√2
- **Impedance dip depth**: Should increase with lower QL (more leakage)
- **Overall impedance**: <12% error across 20-200 Hz

## Theory Reference

### Sealed Box (Small 1972, Eq. 9)

**Parallel Q Combination**:
```
Qtc_total = (Qec × Quc) / (Qec + Quc)

Where:
- Qec = Qes × √(1 + α)  # Electrical Q at system resonance
- Quc = Mechanical + absorption losses (5-100 typical)
- α = Vas / Vb  # Compliance ratio
- Qtc_total = Total system Q (used in transfer function)
```

**Physical Meaning**:
- Quc represents mechanical losses (box walls, suspension) + absorption losses (filling material)
- Lower Quc = more losses = more damping
- Quc = ∞ represents no losses (theoretical)

### Ported Box (Small 1973, Eq. 19)

**Combined Box Losses**:
```
1/QB = 1/QL + 1/QA + 1/QP

Where:
- QL = Leakage losses (air through gaps/seams) - 5-20 typical
- QA = Absorption losses (damping material) - 50-100 typical
- QP = Port losses (viscous friction) - 5-20 typical
- QB = Combined losses (used in transfer function)
```

**Physical Meaning**:
- QL dominated by box construction quality
- QA dominated by damping material (often neglected = ∞)
- QP dominated by port geometry (large ports ≈ ∞)
- Smallest Q dominates (parallel combination)

## Regenerating Input Files

If you need to regenerate the Hornresp input files:

```bash
# Sealed box
cd tests/validation/drivers/bc_8ndl51/sealed_box
PYTHONPATH=../../../.. python generate_ql_validation_files.py

# Ported box
cd tests/validation/drivers/bc_8ndl51/ported
PYTHONPATH=../../../.. python generate_ql_validation_files.py
```

## Literature

1. **Small, R.H.** "Closed-Box Loudspeaker Systems Part I: Analysis", JAES Vol. 20, 1972
   - Eq. 9: Parallel Q combination for sealed boxes
   - Quc definition and typical values

2. **Small, R.H.** "Vented-Box Loudspeaker Systems Part I", JAES Vol. 21, 1973
   - Eq. 13: Ported box transfer function (uses Q_T)
   - Eq. 19: Combined box losses formula

3. **Hornresp V53.20**
   - Default QL = 7 for both sealed and ported boxes
   - User Manual: QL parameter documentation

4. **Bullock, R.M.** "System Q and QP", Speaker Builder, 1991
   - Typical Quc values for sealed boxes
   - Effects of damping material

## Validation Status

### Current Status
- ✅ Hornresp input files generated for all QL variations
- ⏳ Hornresp sim.txt files - **NEED TO BE GENERATED MANUALLY**
- ✅ Unit tests implemented (test_ql_box_losses.py)
- ✅ Integration tests implemented (test_ql_hornresp_comparison.py)

### Next Steps
1. Generate sim.txt files in each QL directory using Hornresp
2. Run validation tests to verify implementation
3. Document any discrepancies >10%
4. Update implementation if needed

## Contact

For questions about this validation dataset, see:
- `tasks/ql_research_findings_summary.md` - Research findings and corrections
- `tests/validation/test_ql_box_losses.py` - Unit test implementation
- `tests/integration/test_ql_hornresp_comparison.py` - Integration test implementation
