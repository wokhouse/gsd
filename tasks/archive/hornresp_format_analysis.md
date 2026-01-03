# Hornresp File Format Analysis

## ✅ COMPARISON COMPLETE - FILES FIXED

### Files Compared:
- `hornresp_example.txt` - Reference example (exponential horn)
- `exports/BC_12NDL76.txt` - Our exported file (direct radiator)

---

## Issues Found and Fixed

### ✅ Issue 1: Line Endings (CRITICAL)

**Problem:**
- `hornresp_example.txt`: **CRLF** (Windows `\r\n`)
- Original export: **LF** (Unix `\n`)

**Fix Applied:**
- Updated `export_to_hornresp()` to use `newline='\r\n'` when writing files
- All exported files now have CRLF line terminators

**Verification:**
```bash
$ file exports/*.txt
exports/BC_12NDL76.txt:  ASCII text, with CRLF line terminators  ✓
exports/BC_15DS115.txt:  ASCII text, with CRLF line terminators  ✓
exports/BC_18PZW100.txt: ASCII text, with CRLF line terminators  ✓
exports/BC_8NDL51.txt:   ASCII text, with CRLF line terminators  ✓
```

### ✅ Issue 2: Cms Scientific Notation Format

**Problem:**
- Example: `1.00E-06` (2 decimal places: `.2E`)
- Original: `1.900E-04` (3 decimal places: `.3E`)

**Fix Applied:**
- Changed format from `{self.Cms:.3E}` to `{self.Cms:.2E}`
- Now outputs: `1.90E-04` ✓

**Verification:**
```bash
$ grep "Cms =" exports/*.txt
exports/BC_12NDL76.txt:  Cms = 1.90E-04  ✓
exports/BC_15DS115.txt:  Cms = 2.50E-04  ✓
exports/BC_18PZW100.txt: Cms = 1.70E-04  ✓
exports/BC_8NDL51.txt:   Cms = 2.03E-04  ✓
```

### ✅ Issue 2b: CRITICAL - Unit Conversion Bug (MASS & INDUCTANCE)

**Problem:**
- Hornresp expects **grams (g)** for Mmd, but exporter was passing **kilograms (kg)**
- Hornresp expects **millihenries (mH)** for Le, but exporter was passing **henries (H)**
- This resulted in exported values being 1000x too small!

**Symptoms:**
- Export showed `Mmd = 0.054` (kg) instead of `54.000` (g)
- Export showed `Le = 0.001` (H) instead of `1.000` (mH)
- These values are 1000x smaller than Hornresp expects!

**Fix Applied:**
- Added unit conversions in `driver_to_hornresp_record()`:
  ```python
  # Convert mass from kg to g
  mmd_g = driver.M_ms * 1000.0

  # Convert inductance from H to mH
  le_mh = driver.L_e * 1000.0
  ```

**Verification:**
```bash
$ grep -E "^(Mmd|Le) =" tests/validation/drivers/*/infinite_baffle/*.txt
bc_15ds115.txt: Mmd = 254.000  ✓ (was 0.254 kg, now 254g)
bc_15ds115.txt: Le = 4.500     ✓ (was 0.0045 H, now 4.5mH)
bc_18pzw100.txt: Mmd = 209.000  ✓ (was 0.209 kg, now 209g)
bc_18pzw100.txt: Le = 1.580     ✓ (was 0.00158 H, now 1.58mH)
```

**Impact:** All driver parameters were updated to match official datasheets after this fix was applied.

### ✅ Issue 3: Direct Radiator Configuration (CRITICAL for Stage 1B)

**Problem:**
- Initial exports used exponential horn parameters (S1=100, S2=5000, Exp=1.30)
- Attempted to use driver area for horn parameters (S1=S2=Sd)
- **Hornresp requirement:** "Unused horn segments must have all parameters set to zero"

**Fix Applied:**
- Set all horn parameters to 0 for direct radiator mode:
  ```
  S1 = 0.00, S2 = 0.00, Exp = 0.00, F12 = 0.00
  S2 = 0.00, S3 = 0.00, Exp = 0.00, AT = 0.00
  S3 = 0.00, S4 = 0.00, L34 = 0.00, F34 = 0.00
  S4 = 0.00, S5 = 0.00, L45 = 0.00, F45 = 0.00
  ```
- **Note:** Line 21 uses `AT` (throat area correction), not `F23`

### ✅ Issue 4: Radiation Angle and Rear Chamber

**Problem:**
- Initial export used `Ang = 4.00` (4π steradians, full-space)
- Hornresp error: "Vrc cannot equal 0 for direct radiator having solid radiation angle of 4 x pi stradians"
- Full-space requires non-zero rear chamber volume

**Fix Applied:**
- Changed to `Ang = 2.00` (2π steradians, half-space / infinite baffle)
- Set `Vrc = 0.00` (no rear chamber required for half-space)
- This is the standard test condition for bare driver impedance validation

---

## Format Comparison

### Driver Parameter Format

| Parameter | Hornresp Units | Example Format | Our Format | Status |
|-----------|---------------|---------------|------------|--------|
| Sd        | cm²           | `100.00`      | `522.00`   | ✓ Match |
| Bl        | T·m           | `1.00`        | `16.50`    | ✓ Match |
| Cms       | m/N           | `1.00E-06`    | `1.90E-04` | ✓ Fixed |
| Rms       | N·s/m         | `0.00`        | `5.20`     | ✓ Match |
| Mmd       | **g** (not kg) | `0.00`       | `53.000`   | ✓ Unit conversion fixed |
| Le        | **mH** (not H) | `0.00`       | `1.000`    | ✓ Unit conversion fixed |
| Re        | Ω             | `0.01`        | `5.30`     | ✓ Match |
| Nd        | count         | `1`           | `1`        | ✓ Match |

**CRITICAL UNIT CONVERSIONS:**
Hornresp uses **non-SI units** for some parameters:
- **Mmd (mass):** grams (g), not kilograms (kg)
  - Conversion: `Mmd_g = M_ms_kg × 1000`
  - Example: 0.053 kg → 53.000 g
- **Le (inductance):** millihenries (mH), not henries (H)
  - Conversion: `Le_mH = L_e_H × 1000`
  - Example: 0.001 H → 1.000 mH
- **Sd (area):** cm², not m²
  - Conversion: `Sd_cm2 = S_d_m2 × 10000`
  - Example: 0.0522 m² → 522.00 cm²

**Implementation:** The `driver_to_hornresp_record()` function handles these conversions automatically.

### Horn Configuration (Direct Radiator)

| Parameter | Example (Horn) | Our Format (Direct Radiator) | Purpose |
|-----------|---------------|------------------------------|---------|
| Ang       | `4.00`        | `2.00`                       | Half-space (2π steradians) |
| S1        | `100.00`      | `0.00`                       | No horn throat |
| S2        | `5000.00`     | `0.00`                       | No horn mouth |
| Exp       | `1.30`        | `0.00`                       | No flare |
| F12       | `150.00`      | `0.00`                       | No horn length |
| Vrc       | `0.001`       | `0.00`                       | No rear chamber |
| Lrc       | `15.00`       | `0.00`                       | No rear chamber length |
| Fr        | `40000.00`    | `0.00`                       | No filling |
| Tal       | `4.00`        | `0.00`                       | No attenuation |

**Default Configuration:** Half-space (2π steradians) infinite baffle mounting,
which is the standard test condition for loudspeaker driver validation.

---

## File Structure

All sections match the Hornresp format:
- ✓ ID and Comment
- ✓ RADIATION, SOURCE AND MOUTH PARAMETER VALUES (Ang=2.00)
- ✓ HORN PARAMETER VALUES (all zeros for direct radiator)
- ✓ TRADITIONAL DRIVER PARAMETER VALUES (real driver T/S parameters)
- ✓ ADVANCED DRIVER PARAMETER VALUES (both models, not used)
- ✓ PASSIVE RADIATOR PARAMETER VALUE (not used)
- ✓ CHAMBER PARAMETER VALUES (all zeros for bare driver)
- ✓ MAXIMUM SPL PARAMETER VALUES
- ✓ ABSORBENT FILLING MATERIAL PARAMETER VALUES
- ✓ ACTIVE BAND PASS FILTER PARAMETER VALUES
- ✓ PASSIVE FILTER PARAMETER VALUES
- ✓ EQUALISER FILTER PARAMETER VALUES
- ✓ STATUS FLAGS
- ✓ OTHER SETTINGS

---

## Exported Drivers

All 4 B&C drivers exported with direct radiator configuration and **corrected datasheet parameters**:

| Driver | Sd (cm²) | Mms (g) | BL (T·m) | Le (mH) | Fs (Hz) | Purpose |
|--------|----------|---------|----------|---------|---------|---------|
| BC_8NDL51   | 220.00  | 26.77  | 12.39   | 0.50   | ~66  | 8" Midrange |
| BC_12NDL76  | 522.00  | 53.00  | 20.10   | 1.00   | ~50  | 12" Mid-Woofer |
| BC_15DS115  | 855.00  | 254.00 | 38.70   | 4.50   | ~33  | 15" Subwoofer |
| BC_18PZW100 | 1210.00 | 209.00 | 25.50   | 1.58   | ~37  | 18" Subwoofer |

All configured for:
- Half-space radiation (Ang = 2.0 x Pi)
- Direct radiator (no horn loading)
- Bare driver electrical impedance validation
- **Correct unit conversions** (g for mass, mH for inductance, cm² for area)

---

## Validation Data Structure

Validation data is organized in `tests/validation/drivers/` with the following structure:

```
tests/validation/drivers/
├── bc_8ndl51/
│   └── infinite_baffle/
│       ├── bc_8ndl51_inf.txt       # Hornresp input file
│       ├── bc_8ndl51_inf_sim.txt   # Hornresp simulation results
│       └── metadata.json           # Validation metadata
├── bc_12ndl76/
│   └── infinite_baffle/
│       └── ...
└── ...
```

### Naming Convention

**Input files:** `{driver}_{config}.txt` (max 16 chars for Hornresp)
- `bc_8ndl51_inf.txt` - infinite baffle
- `bc_12ndl76_inf.txt` - infinite baffle
- Future: `bc_8ndl51_exp.txt` - exponential horn
- Future: `bc_8ndl51_hyp.txt` - hyperbolic horn

**Output files:** `{driver}_{config}_sim.txt`
- `bc_8ndl51_inf_sim.txt` - simulation results
- `bc_12ndl76_inf_sim.txt` - simulation results

**Metadata:** `metadata.json` in each config directory
```json
{
  "driver": "BC_8NDL51",
  "configuration": "infinite_baffle",
  "date_created": "2025-12-26",
  "date_run": null,
  "hornresp_version": null,
  "notes": "8 inch midrange driver - bare driver electrical impedance validation"
}
```

### Workflow

1. **Export driver:** `gsd export BC_12NDL76 -o exports/bc_12ndl76_inf.txt`
2. **Copy to Hornresp VM:** Paste file, run simulation
3. **Import results:** Export Hornresp output as `imports/bc_12ndl76_inf_sim.txt`
4. **Move to validation:**
   ```bash
   cp exports/bc_12ndl76_inf.txt tests/validation/drivers/bc_12ndl76/infinite_baffle/
   cp imports/bc_12ndl76_inf_sim.txt tests/validation/drivers/bc_12ndl76/infinite_baffle/
   ```
5. **Update metadata:** Add `date_run` and `hornresp_version` to metadata.json

**Directory Convention:**
- `exports/` - GSD parameter outputs (Hornresp input files, gitignored)
- `imports/` - Hornresp simulation results (validation data, gitignored)
- `tests/validation/drivers/` - Permanent validation data (version controlled)

---

## Test with Hornresp

The exported files should now be importable into Hornresp. Try importing:

1. `exports/BC_8NDL51.txt` - 8" Midrange driver
2. `exports/BC_12NDL76.txt` - 12" Mid-Woofer driver
3. `exports/BC_15DS115.txt` - 15" Subwoofer driver
4. `exports/BC_18PZW100.txt` - 18" Subwoofer driver

---

## Troubleshooting

### Error: "Unused horn segments must have all parameters set to zero"

**Cause:** Setting S1, S2, or other horn parameters to non-zero values when Exp = 0, or attempting to use driver area (Sd) for horn throat/mouth in direct radiator mode.

**Symptoms:**
- Trying to configure S1 = Sd for direct radiator
- Setting S2 to non-zero with Exp = 0

**Solution:**
For bare driver (direct radiator) testing, set ALL horn parameters to 0:
```
S1 = 0.00
S2 = 0.00
Exp = 0.00
F12 = 0.00
S3 = 0.00
S4 = 0.00
L34 = 0.00
F34 = 0.00
L45 = 0.00
F45 = 0.00
```

---

### Error: "Vrc cannot equal 0 for direct radiator having solid radiation angle of 4 x pi stradians"

**Cause:** Using `Ang = 4.00` (4π steradians, full-space radiation) with `Vrc = 0.00` (no rear chamber). Hornresp requires a non-zero rear chamber volume for full-space radiation.

**Symptoms:**
- Configuration has `Ang = 4.00` and `Vrc = 0.00`

**Solution:**
Use half-space radiation (2π steradians) for bare driver testing:
```
Ang = 2.00    # Half-space (infinite baffle)
Vrc = 0.00    # No rear chamber required
```

This is the standard test condition for loudspeaker driver validation, representing a driver mounted in an infinite baffle.

---

### File Format Issues

**Problem:** Files not accepted by Hornresp (no error message, just won't import)

**Check 1: Line Endings**
```bash
file your_file.txt
# Should show: "ASCII text, with CRLF line terminators"
# If shows "ASCII text" (Unix LF), need CRLF
```

**Check 2: Cms Format**
```bash
grep "Cms =" your_file.txt
# Should show: "Cms = X.XXE-XX" (2 decimal places)
# Wrong: "Cms = X.XXXE-XX" (3 decimal places)
```

**Check 3: All Horn Parameters Zero**
```bash
grep -E "^S[12345] = |^Exp = |^F[1234][245] = " your_file.txt
# All should be 0.00 for direct radiator
```

---

## Import Checklist

Before importing into Hornresp, verify:

- [ ] File has CRLF line terminators (`file` command)
- [ ] Cms uses 2 decimal places in scientific notation
- [ ] All horn parameters are 0.00 (for direct radiator)
- [ ] Ang = 2.00 (half-space) or Ang = 4.00 with Vrc > 0 (full-space)
- [ ] Driver T/S parameters are within reasonable ranges
- [ ] File name ≤ 16 characters (Hornresp limit)

---

## Common Configuration Patterns

### Bare Driver (Infinite Baffle)
```
Ang = 2.00          # Half-space
S1-S5 = 0.00        # No horn
Vrc = 0.00          # No rear chamber
```

### Horn-Loaded System
```
Ang = 2.00 or 4.00  # Radiation pattern
S1 = throat_area    # Non-zero
S2 = mouth_area     # Non-zero
Exp = flare_constant # Non-zero for exponential
F12 = horn_length   # Non-zero
```

---

## Implementation Details

**Location:** `src/gsd/hornresp/export.py`

**Key Functions:**
- `export_to_hornresp()` - Export single driver to Hornresp .txt file
- `driver_to_hornresp_record()` - Convert SI units to Hornresp units
- `HornrespRecord.to_hornresp_format()` - Format driver parameters
- `batch_export_to_hornresp()` - Export multiple drivers

**Unit Conversions (CRITICAL):**
```python
# Input: SI units (ThieleSmallParameters)
M_ms: kg   # Moving mass
L_e: H     # Voice coil inductance
S_d: m²    # Effective piston area

# Output: Hornresp units (HornrespRecord)
Mmd: g     # Moving mass (×1000)
Le: mH     # Voice coil inductance (×1000)
Sd: cm²    # Effective piston area (×10000)
```

**Default Configuration (for Stage 1B bare driver testing):**
```
Ang = 2.0 x Pi     # Half-space (2π steradians)
S1-S5 = 0.00       # No horn segments
Exp = 0.00         # No flare
F12, AT, F34, F45 = 0.00  # No horn lengths (note: AT not F23 on line 21)
Vrc = 0.00         # No rear chamber
```

This configuration represents a driver mounted in an infinite baffle,
radiating into half-space, with no horn loading - ideal for validating
the bare driver electrical impedance model against Hornresp.
