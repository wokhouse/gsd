# Sealed Box SPL Validation Investigation

## Problem Statement

Sealed box validation against Hornresp shows large SPL errors:
- **Max SPL error**: 16.84 dB @ 69.9 Hz
- **RMS SPL error**: 10.13 dB
- **Expected tolerance**: <6 dB max, <4 dB RMS

## Test Configuration

- **Driver**: BC 8NDL51
- **Box volume**: Vb = 31.65 L
- **Alignment**: Qtc = 0.707 (Butterworth)
- **System resonance**: Fc = 86.1 Hz
- **Analysis frequency**: 100 Hz

## Hornresp Reference Data @ 100 Hz

```
Freq:     100.0 Hz
SPL:      104.93 dB
Ze:        11.11 Ω @ -47.1°
Xd:        0.755 mm (displacement)
Iin:       0.255 A
UPhase:    78.2°
```

Calculated Hornresp velocity:
```
u = ω × Xd = 2π × 100 × 0.000755 = 0.474 m/s
```

## GSD Results @ 100 Hz

```
Freq:     100.0 Hz
SPL:       89.64 dB
Ze:        13.56 Ω @ -47.2°
Velocity:  0.234 m/s
I_active:  0.142 A
```

## Error Breakdown

### 1. Velocity Error (50.7% low)
```
Velocity ratio (gsd / Hornresp): 0.493
Expected SPL difference: 20×log10(0.493) = -6.14 dB
Actual SPL difference: -15.29 dB
```

### 2. Additional SPL Error (~9 dB)
Even accounting for the low velocity, the SPL is ~9 dB lower than expected.

## Root Cause Analysis

### Issue 1: Incorrect Mechanical Impedance

**Current Implementation:**
```python
# sealed_box.py, line 266-273
Fc, M_ms_enclosed = calculate_resonance_with_radiation_mass_tuned(
    driver.M_md,
    C_mb,  # Box compliance
    driver.S_d,
    radiation_multiplier=1.0,  # Front radiation only
    ...
)

# Then calculates mechanical impedance:
Z_mechanical = driver.R_ms + complex(0, omega * M_ms_enclosed) + \
               complex(0, -1 / (omega * C_mb))
```

**Mechanical Impedance Components @ 100 Hz:**
```
R_ms:                    2.44 N·s/m
Mass term jωM_ms:       17.67 N·s/m @ 90°
Compliance term 1/jωC_mb: 13.97 N·s/m @ -90°
────────────────────────────────────
Z_mechanical:             4.43 N·s/m @ 56.6°
```

**Required Z_mech for Hornresp velocity:**
- If using I_active: 2.67 N·s/m
- If using full I: 3.92 N·s/m
- **Actual: 4.43 N·s/m (too high!)**

### Issue 2: Mass Value at Different Frequencies

`M_ms_enclosed` is calculated at Fc (86 Hz) using `radiation_multiplier=1.0`:
```
M_ms_enclosed @ Fc: 28.12 g (M_md + 1×M_rad at 86 Hz)
```

But at 100 Hz, the radiation mass is slightly different, and the total mass should be:
```
M_rad @ 100 Hz = 1.83 g
M_ms @ 100 Hz (1× radiation) = 26.29 + 1.83 = 28.12 g (same as at Fc)
```

So the mass value is approximately correct.

### Issue 3: Compliance Model Question

The code uses `C_mb = C_ms / (1 + α)` for mechanical impedance, where α = Vas/Vb.

**Theory from Small (1972):**
- The box and driver compliances are in series
- C_mb = C_ms / (1 + α) is the **effective compliance** for resonance calculation
- But should mechanical impedance use C_mb or C_ms?

**Current:** Uses C_mb
**Alternative:** Use C_ms (driver compliance only)

Test with C_ms:
```
Z_mechanical @ 100 Hz (using C_ms): 8.59 N·s/m
```

This gives Ze = 7.3 Ω (even further from Hornresp's 11.11 Ω).

## Possible Explanations

### Hypothesis 1: Hornresp doesn't use I_active force model

**Test:** What if Hornresp uses full current magnitude for force?

Using full current (0.209 A) instead of I_active (0.142 A):
```
Force: 1.53 N (vs 1.04 N with I_active)
Velocity: 0.344 m/s (vs 0.234 m/s)
Still far from Hornresp's 0.474 m/s
```

**Conclusion:** Doesn't fully explain the discrepancy.

### Hypothesis 2: Mechanical resistance is higher

Hornresp Ze = 11.11 Ω implies:
```
Z_reflected = 11.11 - 2.6 = 8.51 Ω
Z_mech_total = BL² / Z_reflected = 7.3² / 8.51 = 6.26 N·s/m
```

This is significantly higher than gsd's 4.43 N·s/m.

**Additional R_mech needed:** ~1.8 N·s/m

This could be from:
- Box losses (not modeled)
- Different radiation resistance calculation
- Hornresp using different impedance model

### Hypothesis 3: Mass should be M_ms (2× radiation)

Sealed box uses `M_ms_enclosed` (1× radiation), but maybe it should use `driver.M_ms` (2× radiation)?

Test with M_ms:
```
Z_mechanical @ 100 Hz (using M_ms): 5.44 N·s/m
```

Closer, but still not 6.26 N·s/m.

### Hypothesis 4: Compliance or mass calculation is fundamentally different

Hornresp might be using a different formula for sealed box impedance that doesn't match the standard Small (1972) model.

## Recommended Next Steps

### Option 1: Accept the error and adjust tolerances
- Infinite baffle validation: RMS error ~4.04 dB (close to 4 dB limit)
- Sealed box: RMS error ~10.13 dB (2.5× higher)
- This indicates a fundamental modeling issue that needs investigation

### Option 2: Contact Hornresp author
- Ask for clarification on sealed box impedance model
- Specifically: Does Hornresp use C_mb or C_ms for mechanical impedance?
- How is box compliance modeled in the impedance calculation?

### Option 3: Review literature more carefully
- Small (1972) derivation of sealed box impedance
- Beranek (1954) on acoustic impedance
- Check if there's a different formula for sealed box

### Option 4: Experimental validation
- Measure actual driver in sealed box
- Compare with both gsd and Hornresp
- Determine which is correct

## Key Insight

**The mechanical impedance calculation is the root cause.** Current gsd gives Z_mech = 4.43 N·s/m, but Hornresp's behavior suggests Z_mech ≈ 6.26 N·s/m. This ~40% difference causes:
- Lower velocity (0.234 vs 0.474 m/s)
- Lower SPL (89.64 vs 104.93 dB)

**The fix requires determining the correct formula for sealed box mechanical impedance.**

## Files to Review

1. `src/gsd/enclosure/sealed_box.py` - Lines 266-296 (mechanical impedance)
2. `src/gsd/driver/radiation_mass.py` - Mass calculation methods
3. `literature/thiele_small/small_1972_closed_box.md` - Theory reference

## Test Commands

```bash
# Re-run validation after any changes
PYTHONPATH=src pytest tests/validation/test_sealed_box.py -v

# Single frequency debug
PYTHONPATH=src python3 -c "
from gsd.enclosure.sealed_box import sealed_box_electrical_impedance
from gsd.driver.bc_drivers import get_bc_8ndl51

driver = get_bc_8ndl51()
result = sealed_box_electrical_impedance(100, driver, Vb=0.03165)
print(f\"SPL: {result['SPL']:.2f} dB\")
print(f\"Velocity: {result['diaphragm_velocity']:.3f} m/s\")
print(f\"Ze: {result['Ze_magnitude']:.2f} Ω\")
"
```

## Status

**UNRESOLVED** - Requires investigation into correct sealed box impedance model.

---

Generated: 2025-12-27
Investigation: Sealed box SPL validation failure
Root cause: Mechanical impedance calculation discrepancy (4.43 vs 6.26 N·s/m)
Impact: -15.29 dB SPL error @ 100 Hz

---

## Update 2025-12-27: Complex Current Fix

### Root Cause Identified (via Research Agent)

**Primary Issue**: Using `I_active` instead of full complex current for force calculation.

**Correct Model**:
```python
# WRONG (old approach):
I_active = |I| × cos(phase(I))
F = BL × I_active
u = F / |Z_mech|

# CORRECT (standard loudspeaker model):
F_complex = BL × I_complex  # Full complex current
v_complex = F_complex / Z_mech  # Complex phasor division
u = |v_complex|  # Use magnitude for SPL
```

### Results After Fix

**At 100 Hz**:
- **Before**: I_active model
  - Velocity: 0.214 m/s
  - Ze: 13.56 Ω @ -47.2°
  - SPL: 88.89 dB
  
- **After**: Complex current model
  - Velocity: 0.341 m/s (+59% improvement!)
  - Ze: 11.14 Ω @ -51.1° ✓ (matches Hornresp 11.11 Ω)
  - SPL: 92.92 dB (+4 dB improvement)
  
- **Target (Hornresp)**:
  - Velocity: 0.474 m/s
  - SPL: 104.93 dB

### Progress Summary

**Fixed:**
1. ✓ Electrical impedance now matches Hornresp (11.14 vs 11.11 Ω)
2. ✓ Velocity improved by 59%
3. ✓ SPL improved by 4 dB
4. ✓ Complex current model implemented correctly

**Remaining Issue:**
- Velocity still 27% low (0.341 vs 0.474 m/s)
- SPL error: -12 dB at 100 Hz, ~11 dB RMS overall
- Root cause: Mechanical impedance too high (5.44 vs ~3.9 N·s/m needed)

### Analysis of Remaining Issue

To achieve Hornresp's velocity of 0.474 m/s:
- Required Z_mech: ~3.91 N·s/m  
- Current Z_mech: 5.44 N·s/m
- Reduction needed: 28%

**Mass Analysis:**
- Target mass to match Hornresp: M ≈ 27.09 g
- Current driver.M_ms: 29.961 g (2× radiation)
- Difference: -2.87 g (-9.6%)

**Possible Solutions:**
1. Use frequency-dependent radiation mass (varies with frequency)
2. Include box damping (Q_b) in resistance calculation
3. Different compliance model for sealed boxes
4. Investigate Hornresp's exact algorithm for Z_mech

### Code Changes

**Commit 46a903b**: Fixed sealed box mechanical impedance
- Changed from M_ms_enclosed to driver.M_ms
- Simplified Fc calculation

**Commit 6671b6b**: Fixed force calculation to use complex current
- Changed from I_active to full complex I_complex
- Changed from magnitude division to complex phasor division
- Updated documentation

---

## Status (2025-12-27)

**IN PROGRESS** - Major improvement achieved, ~27% velocity discrepancy remains.

The complex current fix was a breakthrough, but the mechanical impedance model
still needs refinement to match Hornresp exactly.

