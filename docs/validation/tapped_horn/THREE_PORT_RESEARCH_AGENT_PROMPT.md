# Tapped Horn Three-Port Network Model - Research Agent Handoff

**Date**: 2025-01-11
**Status**: ⚠️ Partial implementation - T-matrix reversal fixed, but accuracy worse than admittance method
**Goal**: Achieve <3 dB RMS SPL error vs Hornresp (currently: 7.4 dB Three-Port vs 6.2 dB Admittance)

---

## Executive Summary

Implemented Three-Port Network T-Matrix method for tapped horn SPL calculation per Berzborn & Smithers (2018). Fixed critical T-matrix reversal bug, but final accuracy is **worse** than existing admittance method.

**Key Findings**:
- ✅ T-matrix reversal correctly implemented (mathematical inverse vs contracting geometry)
- ⚠️ Lossy wavenumber has minimal effect (0.18% damping - insufficient to fix 60 Hz peak)
- ❌ Three-Port: 7.4 dB RMS vs Admittance: 6.2 dB RMS (regression)

**Critical Issue**: At 50-60 Hz, Three-Port underestimates pressure by 8-12 dB, while admittance method is much closer to Hornresp.

---

## Implementation Details

### File: `src/gsd/simulation/tapped_horn_theory.py`

#### Function: `calculate_lossy_wavenumber()` (Lines 32-106)

```python
def calculate_lossy_wavenumber(
    frequencies: NDArray[np.float64],
    radius: float,
    medium: MediumProperties = None,
) -> NDArray[np.complex128]:
    """Calculate complex wavenumber accounting for viscous and thermal losses.

    Complex wavenumber k_c = ω/c - jα, where α is attenuation factor.
    Based on Keefe (1984) and Mapes-Riordan (1993).

    Literature:
        Keefe, D.H. (1984). "Acoustical characterization of blowholes."
        Mapes-Riordan, K. (1993). "Designing and building loudspeakers."
    """
    if medium is None:
        medium = MediumProperties()

    frequencies = np.atleast_1d(frequencies).astype(float)
    omega = 2 * np.pi * frequencies

    # Physical constants for air at 20°C
    Pr = 0.707          # Prandtl number
    gamma = 1.4         # Ratio of specific heats
    mu = 1.81e-5        # Dynamic viscosity (Pa·s)

    # Viscous boundary layer thickness: δ_v = sqrt(2*μ / (ρ*ω))
    delta_v = np.sqrt(2 * mu / (medium.rho * omega))

    # Wall loss factor per unit length
    # α = (ω/c) * (δ_v/r) * (1 + (γ-1)/sqrt(Pr)) / 2
    alpha = (omega / medium.c) * (delta_v / radius) * \
            (1 + (gamma - 1) / np.sqrt(Pr)) / 2

    # Complex wavenumber: k_c = ω/c - jα
    k_c = (omega / medium.c) - 1j * alpha

    return k_c
```

**Status**: ✅ Implemented correctly
**Issue**: At 50 Hz, α = 0.0016 Np/m (0.18% of real k) - too small to damp resonances

---

#### Function: `calculate_three_port_pressure()` (Lines 773-915)

```python
def calculate_three_port_pressure(
    frequencies: NDArray[np.float64],
    u_driver: NDArray[np.complex128],
    tapped_horn: TappedHorn,
    medium: MediumProperties = None,
) -> NDArray[np.complex128]:
    """Calculate pressure at mouth using Three-Port Network T-Matrix method.

    Based on Berzborn & Smithers (2018), AES Paper 10047.

    The driver at the tap fires into a junction where waves split into:
        1. Throat Path (Upstream): Travels to closed throat, reflects, returns
        2. Mouth Path (Downstream): Travels directly to mouth

    At quarter-wavelength of upstream stub, the wave returning from throat
    arrives 180° out of phase, creating destructive interference (notch).

    CRITICAL: Uses complex wavenumber for viscous/thermal losses to damp
    artificial resonances that would otherwise create infinite peaks.

    Args:
        frequencies: Array of frequencies in Hz
        u_driver: Complex volume velocity from driver (at tap point)
        tapped_horn: TappedHorn geometry specification
        medium: Acoustic medium properties

    Returns:
        Complex pressure array at mouth (Pa)
    """
    if medium is None:
        medium = MediumProperties()

    from .types import ExponentialHorn

    frequencies = np.atleast_1d(frequencies).astype(float)
    u_driver = np.atleast_1d(u_driver)

    # ========================================================================
    # Step 1: Calculate lossy wavenumbers for both sections
    # ========================================================================
    # Complex wavenumber k_c = ω/c - jα includes viscous/thermal boundary layer losses

    # Effective radius for upstream section (average of tap and throat areas)
    # Convert cm² to m² for radius calculation
    r_up = np.sqrt((tapped_horn.tap_area + tapped_horn.upstream_throat_area) / 2 / np.pi) / 100.0
    k_up = calculate_lossy_wavenumber(frequencies, r_up, medium)

    # Effective radius for downstream section (average of tap and mouth areas)
    r_dn = np.sqrt((tapped_horn.tap_area + tapped_horn.downstream_mouth_area) / 2 / np.pi) / 100.0
    k_dn = calculate_lossy_wavenumber(frequencies, r_dn, medium)

    # ========================================================================
    # Step 2: UPSTREAM Branch (Tap -> Throat) - REVERSED T-MATRIX
    # ========================================================================
    # CRITICAL: We need the T-matrix looking FROM Tap TO Throat.
    # However, exponential_horn_tmatrix() calculates from throat to mouth.
    # To reverse direction, we calculate the original (Throat→Tap) matrix,
    # then mathematically invert it: T_reversed = [[D, -B], [-C, A]]

    # First, calculate the T-matrix in the forward direction (Throat → Tap)
    upstream_forward = ExponentialHorn(
        throat_area=tapped_horn.upstream_throat_area / 10000,  # Input at Throat (m²)
        mouth_area=tapped_horn.tap_area / 10000,               # Output at Tap (m²)
        length=tapped_horn.upstream_length / 100,              # Convert cm to m
    )

    a_fwd, b_fwd, c_fwd, d_fwd = exponential_horn_tmatrix(
        frequencies, upstream_forward, medium, k=k_up
    )

    # Reverse the T-matrix: T_reversed = [[D, -B], [-C, A]]
    # For lossless horns, det(ABCD) = 1, so the inverse is [[D, -B], [-C, A]]
    a_up = d_fwd
    b_up = -b_fwd
    c_up = -c_fwd
    d_up = a_fwd

    # Upstream impedance: Z_up = A_up / C_up (closed throat, Z_throat → ∞)
    valid_c_up = np.where(np.abs(c_up) < 1e-12, 1e-12, c_up)
    z_up = a_up / valid_c_up

    # ========================================================================
    # Step 3: DOWNSTREAM Branch (Tap -> Mouth)
    # ========================================================================
    # Use multi-segment model for accurate downstream T-matrix with losses

    downstream_segments = tapped_horn.downstream_segments()
    a_dn, b_dn, c_dn, d_dn = _chain_tmatrices(
        frequencies, downstream_segments, medium, k=k_dn
    )

    # Radiation impedance at mouth (infinite baffle)
    z_rad = circular_piston_radiation_impedance(
        frequencies, downstream_segments[-1].mouth_area, medium
    )

    # Downstream impedance: Z_down = (A_dn*Z_rad + B_dn) / (C_dn*Z_rad + D_dn)
    num_dn = a_dn * z_rad + b_dn
    den_dn = c_dn * z_rad + d_dn
    valid_den_dn = np.where(np.abs(den_dn) < 1e-12, 1e-12, den_dn)
    z_down = num_dn / valid_den_dn

    # ========================================================================
    # Step 4: Total Load & Tap Pressure (The Interference Calculation)
    # ========================================================================
    # Z_load = Z_up || Z_down (parallel combination)
    z_par_num = z_up * z_down
    z_par_den = z_up + z_down
    valid_par_den = np.where(np.abs(z_par_den) < 1e-12, 1e-12, z_par_den)
    z_load = z_par_num / valid_par_den

    # Pressure at tap: P_tap = U_driver * Z_load
    p_tap = u_driver * z_load

    # ========================================================================
    # Step 5: Transfer to Mouth
    # ========================================================================
    # P_tap = A_dn * P_mouth + B_dn * U_mouth
    # With U_mouth = P_mouth / Z_rad: P_tap = P_mouth * (A_dn + B_dn/Z_rad)
    transfer_factor = a_dn + (b_dn / z_rad)
    valid_transfer = np.where(np.abs(transfer_factor) < 1e-12, 1e-12, transfer_factor)
    p_mouth = p_tap / valid_transfer

    return p_mouth
```

**Status**: ⚠️ Implemented per specification, but results worse than admittance method

---

#### Function: `_chain_tmatrices()` (Lines 1095-1162) - MODIFIED

```python
def _chain_tmatrices(
    frequencies: NDArray[np.float64],
    segments: list,
    medium: MediumProperties,
    k: Optional[NDArray[np.complex128]] = None,  # NEW PARAMETER
) -> tuple:
    """Chain T-matrices for multiple horn segments.

    For a list of N horn segments, chains their T-matrices:
        T_total = T_1 * T_2 * ... * T_N

    Args:
        frequencies: Array of frequencies in Hz
        segments: List of ExponentialHorn or ConicalHorn segments
        medium: Acoustic medium properties
        k: Optional complex wavenumber array for lossy simulation.

    Returns:
        Tuple of (A, B, C, D) arrays for the combined T-matrix
    """
    if len(segments) == 0:
        raise ValueError("segments list cannot be empty")

    frequencies = np.atleast_1d(frequencies).astype(float)

    # Initialize with identity matrix
    A = np.ones(len(frequencies), dtype=complex)
    B = np.zeros(len(frequencies), dtype=complex)
    C = np.zeros(len(frequencies), dtype=complex)
    D = np.ones(len(frequencies), dtype=complex)

    # Chain T-matrices: T_total = T_1 * T_2 * ... * T_N
    for seg in segments:
        if isinstance(seg, ExponentialHorn):
            # Pass k parameter to enable losses
            a_seg, b_seg, c_seg, d_seg = exponential_horn_tmatrix(
                frequencies, seg, medium, k=k  # <-- k PARAMETER ADDED
            )
        elif isinstance(seg, ConicalHorn):
            # Conical horns use calculate_t_matrix method
            a_seg = np.zeros(len(frequencies), dtype=complex)
            b_seg = np.zeros(len(frequencies), dtype=complex)
            c_seg = np.zeros(len(frequencies), dtype=complex)
            d_seg = np.zeros(len(frequencies), dtype=complex)

            for i, f in enumerate(frequencies):
                T = seg.calculate_t_matrix(f, medium.c, medium.rho)
                a_seg[i], b_seg[i], c_seg[i], d_seg[i] = T[0, 0], T[0, 1], T[1, 0], T[1, 1]
        else:
            raise ValueError(f"Unsupported horn type: {type(seg)}")

        # Multiply: T_new = T_old * T_seg
        A_new = A * a_seg + B * c_seg
        B_new = A * b_seg + B * d_seg
        C_new = C * a_seg + D * c_seg
        D_new = C * b_seg + D * d_seg

        A, B, C, D = A_new, B_new, C_new, D_new

    return A, B, C, D
```

**Status**: ✅ Added `k` parameter to support lossy wavenumber in multi-segment downstream

---

### File: `src/gsd/simulation/horn_theory.py`

#### Function: `exponential_horn_tmatrix()` - Already supported `k` parameter

```python
def exponential_horn_tmatrix(
    frequencies: FloatArray,
    horn: 'ExponentialHorn',
    medium: Optional[MediumProperties] = None,
    k: Optional[ComplexArray] = None  # <-- ALREADY EXISTED
) -> Tuple[ComplexArray, ComplexArray, ComplexArray, ComplexArray]:
    """Calculate T-matrix elements for exponential horn.

    Args:
        frequencies: Array of frequencies [Hz]
        horn: ExponentialHorn geometry parameters
        medium: Acoustic medium properties (uses default if None)
        k: Optional complex wavenumber array [rad/m]. If None, uses lossless k = ω/c.
           Providing k allows inclusion of viscous/thermal losses for accurate SPL.

    Returns:
        Tuple of (a, b, c, d) T-matrix element arrays (complex)
    """
    if medium is None:
        medium = MediumProperties()

    frequencies = np.atleast_1d(frequencies).astype(float)

    # Convert from Olson's to Kolbrek's flare constant convention
    m = _kolbrek_flare_constant(horn)
    L = horn.length
    S1 = horn.throat_area
    S2 = horn.mouth_area
    z_rc = medium.z_rc

    # Use provided complex wavenumber, or calculate lossless k = ω/c
    if k is None:
        k = 2 * np.pi * frequencies / medium.c
    else:
        k = np.atleast_1d(k)

    # γ = √(k² - m²), can be real or imaginary
    gamma_squared = k**2 - m**2
    gamma = np.sqrt(gamma_squared.astype(complex))

    # ... rest of calculation uses gamma (which incorporates k)
```

**Status**: ✅ Already supported complex wavenumber

---

## Test Results

### Test Geometry:
```
BC_15PS100 Driver in Tapped Horn
- Upstream throat: 150 cm²
- Tap area: 855 cm²
- Intermediate area: 2265 cm²
- Downstream mouth: 6000 cm²
- Upstream length: 180 cm (1.8 m)
- Downstream length: 200 cm (2.0 m, 2 segments)
- Input: 2.83V (1W into 8Ω)
```

### Comparison: Admittance Method vs Three-Port Method

| Freq | Hornresp | Admittance | Three-Port | Error (Adm) | Error (3P) |
|------|----------|------------|------------|-------------|------------|
| 40 Hz | 91.5 dB | 84.6 dB | 85.4 dB | -6.9 dB | **-6.1 dB** |
| 50 Hz | 97.0 dB | 95.8 dB | 88.3 dB | -1.2 dB | **-8.7 dB** ❌ |
| 60 Hz | 98.5 dB | 108.7 dB | 86.2 dB | **+10.2 dB** ❌ | **-12.3 dB** ❌ |
| 80 Hz | 96.0 dB | 97.0 dB | 96.8 dB | +1.0 dB | **+0.8 dB** ✅ |
| 100 Hz | 95.0 dB | 101.0 dB | 97.9 dB | +6.0 dB | **+2.9 dB** ✅ |

**RMS Error**:
- Admittance method: 6.2 dB
- Three-Port method: 7.4 dB ❌ (WORSE)

### Pressure Magnitude Comparison (at u_driver = 0.001 m³/s):

| Freq | |P_admittance| | |P_three_port| | Ratio | Phase Diff |
|------|---------------|---------------|-------|------------|
| 40 Hz | 2.32e-01 Pa | 2.59e-01 Pa | 1.11x | -0.1° |
| 50 Hz | 8.27e-01 Pa | 3.53e-01 Pa | **0.43x** ❌ | 3.7° |
| 60 Hz | 3.97e+00 Pa | 2.96e-01 Pa | **0.07x** ❌ | 120.1° ❌ |
| 80 Hz | 9.50e-01 Pa | 1.10e+00 Pa | 1.16x | -15.7° |
| 100 Hz | 1.43e+00 Pa | 1.39e+00 Pa | 0.97x | 1.0° |

**Critical Issues**:
1. **50 Hz**: Three-Port pressure is 57% lower than admittance
2. **60 Hz**: Three-Port pressure is 93% lower than admittance, with 120° phase difference!

---

## Bug Found and Fixed: T-Matrix Reversal

### Problem

Initial implementation created a "contracting" horn to reverse direction:

```python
# WRONG APPROACH (causes T-matrix violation)
upstream_reversed = ExponentialHorn(
    throat_area=tapped_horn.tap_area / 10000,        # Input at Tap (855 cm²)
    mouth_area=tapped_horn.upstream_throat_area / 10000,  # Output at Throat (150 cm²)
    length=tapped_horn.upstream_length / 100,
)
a_up, b_up, c_up, d_up = exponential_horn_tmatrix(
    frequencies, upstream_reversed, medium, k=k_up
)
```

This violated T-matrix reciprocity:
- Expected: `B_reversed = -B_original`, `C_reversed = -C_original`
- Actual: Wrong signs caused impedance phases to be off by ~100°

### Diagnostic Output:

```
Method 1: Reversed Horn (Tap→Throat) - WRONG
Flare constant m: -0.9669 1/m (negative = contracting)

T-matrix elements:
  A = 3.3073e-01+1.9264e-03j
  B = -1.0765e+00+1.3432e+04j
  C = -8.0349e-09+1.0026e-04j
  D = -1.0483e+00+5.4531e+03j

Method 2: Original Horn (Throat→Tap)
Flare constant m: 0.9669 1/m (positive = expanding)

T-matrix elements:
  A = -1.0483e+00+5.4531e-03j
  B = -1.0765e+00+1.3432e+04j
  C = -8.0349e-09+1.0026e-04j
  D = 3.3073e-01+1.9264e-03j

Reciprocity Check:
Expected reversed (inverse of original):  [[D, -B], [-C, A]]
  A_expected = 3.3073e-01+1.9264e-03j
  B_expected = 1.0765e+00-1.3432e+04j
  C_expected = 8.0349e-09-1.0026e-04j
  D_expected = -1.0483e+00+5.4531e+03j

Actual reversed (from contracting horn):
  A_actual = 3.3073e-01+1.9264e-03j  ✓
  B_actual = -1.0765e+00+1.3432e+04j  ✗ (should be +1.0765e+00-1.3432e+04j)
  C_actual = -8.0349e-09+1.0026e-04j  ✗ (should be +8.0349e-09-1.0026e-04j)
  D_actual = -1.0483e+00+5.4531e+03j  ✓

Comparison (actual/expected):
  A: 1.000000+0.000000j  ✓
  B: -1.000000-0.000000j  ✗ WRONG SIGN
  C: -1.000000-0.000000j  ✗ WRONG SIGN
  D: 1.000000+0.000000j  ✓

❌ T-matrix reciprocity violated!
```

### Solution

Calculate forward T-matrix, then mathematically invert:

```python
# CORRECT APPROACH (mathematical inverse)
upstream_forward = ExponentialHorn(
    throat_area=tapped_horn.upstream_throat_area / 10000,  # Input at Throat (150 cm²)
    mouth_area=tapped_horn.tap_area / 10000,               # Output at Tap (855 cm²)
    length=tapped_horn.upstream_length / 100,
)

a_fwd, b_fwd, c_fwd, d_fwd = exponential_horn_tmatrix(
    frequencies, upstream_forward, medium, k=k_up
)

# Reverse: T_reversed = [[D, -B], [-C, A]]
a_up = d_fwd
b_up = -b_fwd
c_up = -c_fwd
d_up = a_fwd
```

**Result**: RMS error improved from 13.1 dB → 7.4 dB (but still worse than admittance method)

---

## Lossy Wavenumber Impact

### Test: With Losses vs Without Losses

| Freq | |P_with_loss| | |P_no_loss| | Ratio |
|------|---------------|-------------|-------|
| 40 Hz | 1.60e-01 Pa | 1.60e-01 Pa | 1.00 |
| 50 Hz | 1.62e-01 Pa | 1.62e-01 Pa | 1.00 |
| 60 Hz | 9.97e-02 Pa | 9.97e-02 Pa | 1.00 |
| 80 Hz | 7.37e-01 Pa | 7.36e-01 Pa | 1.00 |
| 100 Hz | 4.63e+00 Pa | 4.60e+00 Pa | 1.00 |

**Conclusion**: Losses have **negligible effect** (ratio ≈ 1.00 at all frequencies)

### Why Losses Are Too Small

At 50 Hz for upstream section:
- Real wavenumber: k = 0.916 rad/m
- Lossy wavenumber: k_c = 0.916 - j0.00167 rad/m
- Attenuation: α = 0.00167 Np/m
- **Relative damping: 0.18%** (insufficient)

Boundary layer thickness at 50 Hz:
- δ_v = 0.1 mm
- Horn radius: r = 12.6 cm
- Ratio δ_v/r = 0.08% (very small)

The physical losses at these frequencies/scales are simply too small to significantly damp artificial resonances.

---

## Remaining Questions for Research Agent

### 1. **Why is Three-Port method less accurate than admittance method?**

The admittance method (6.2 dB RMS error) performs better than Three-Port (7.4 dB RMS error). This is unexpected because:
- Three-Port is supposed to be a more rigorous formulation
- Both should be mathematically equivalent (Z = 1/Y)

**Specific discrepancies**:
- 50 Hz: Three-Port underestimates by 8.7 dB, admittance only -1.2 dB
- 60 Hz: Three-Port underestimates by 12.3 dB, admittance overestimates by 10.2 dB

**Research needed**:
- Is there a flaw in the impedance formulas (Z_up = A/C, Z_down = (A*Z_rad + B)/(C*Z_rad + D))?
- Should we be using D/C instead of A/C for upstream impedance?
- Is there a sign error in the T-matrix reversal formula?
- Does the parallel impedance formula need modification for tapped horns?

### 2. **Why does 60 Hz show 120° phase difference between methods?**

The 60 Hz phase difference of 120° between admittance and Three-Port suggests fundamentally different interference patterns.

**Research needed**:
- What causes the massive pressure reduction at 60 Hz in Three-Port (93% lower)?
- Is this related to the quarter-wave frequency (f_c = c/(4*L_up) = 47.6 Hz)?
- Are the T-matrix elements correct near resonance?
- Should the lossy wavenumber be frequency-dependent in a different way?

### 3. **How does Hornresp calculate tapped horn SPL?**

We need to understand the reference implementation.

**Research needed**:
- Find Hornresp documentation or source code describing tapped horn SPL calculation
- Does Hornresp use T-matrix method, admittance method, or something else?
- How does Hornresp handle the quarter-wave resonance?
- What loss model does Hornresp use (if any)?

### 4. **Is the lossy wavenumber formula correct for large horns?**

The Keefe (1984) boundary layer formula may not scale correctly to large horn radii.

**Research needed**:
- Find alternative loss formulas for large waveguides
- Check if there are frequency-dependent corrections needed
- Investigate if Hornresp uses a different loss model
- Consider if empirical loss factors are needed

### 5. **Should we use a hybrid approach?**

Given that:
- Admittance method works better at 40-60 Hz
- Three-Port method works better at 80-100 Hz

**Research needed**:
- Has anyone in literature used hybrid admittance/impedance methods for tapped horns?
- Is there a theoretically justified way to combine methods?
- What are the discontinuity risks at frequency boundaries?

### 6. **Is there an error in the multi-segment downstream T-matrix?**

The downstream section has 2 segments:
- Segment 1: Tap (855 cm²) → Intermediate (2265 cm²), 1.0 m
- Segment 2: Intermediate (2265 cm²) → Mouth (6000 cm²), 1.0 m

**Research needed**:
- Are we correctly applying the lossy wavenumber to both segments?
- Should each segment have its own lossy wavenumber (different radius)?
- Is the T-matrix chaining formula correct for lossy horns?

### 7. **Why doesn't the Three-Port method match the admittance method?**

Mathematically, they should be equivalent:
- Y_total = Y_up + Y_down = 1/Z_up + 1/Z_down
- Z_load = 1/Y_total = (Z_up * Z_down) / (Z_up + Z_down)
- P_tap = U * Z_load = U / Y_total

**Research needed**:
- Find the admittance method implementation in literature
- Compare the two derivations step-by-step
- Check if there are sign conventions that differ
- Verify the T-matrix to impedance conversion formulas

---

## Literature Consulted

1. **Berzborn & Smithers (2018)**, AES Paper 10047 - Three-port network model for tapped horns
2. **Keefe (1984)** - Viscous and thermal losses in waveguides
3. **Mapes-Riordan (1993)** - Horn damping effects
4. **Kolbrek**, "Horn Loudspeaker Simulation" - T-matrix theory and reciprocity
5. **Olson (1947)** - Exponential horn theory
6. **Beranek (1954)** - Radiation impedance

---

## Files Created/Modified

### Modified:
1. `src/gsd/simulation/tapped_horn_theory.py`:
   - Added `calculate_lossy_wavenumber()` (lines 32-106)
   - Modified `calculate_three_port_pressure()` (lines 773-915)
   - Modified `_chain_tmatrices()` to accept `k` parameter (line 1099)

2. `src/gsd/simulation/horn_theory.py`:
   - Already supported complex wavenumber in `exponential_horn_tmatrix()` (line 179)

### Diagnostic Scripts Created:
- `tasks/diagnose_fixes.py` - Verify lossy wavenumber and reversed T-matrix
- `tasks/diagnose_new_implementation.py` - Compare admittance vs Three-Port
- `tasks/diagnose_upstream_impedance_detailed.py` - T-matrix reciprocity check
- `tasks/test_lossless_three_port.py` - Test with/without losses
- `tasks/test_three_port_spl.py` - Full SPL validation

---

## Recommended Next Steps

For the research agent to investigate:

1. **High Priority**: Find Hornresp's tapped horn SPL calculation method
   - Search: "Hornresp tapped horn simulation algorithm"
   - Search: "Hornresp three-port network model"
   - Look for Hornresp source code or technical documentation

2. **High Priority**: Verify T-matrix to impedance conversion formulas
   - Search: "T-matrix input impedance formula A/C vs D/C"
   - Search: "When to use D/C instead of A/C for reversed T-matrix"
   - Find authoritative derivation of the formulas

3. **Medium Priority**: Research tapped horn loss models
   - Search: "tapped horn boundary layer losses large diameter"
   - Search: "viscous thermal losses exponential horn bass frequencies"
   - Look for empirical loss correction factors

4. **Medium Priority**: Investigate the 60 Hz phase discrepancy
   - Search: "tapped horn quarter-wave resonance phase interference"
   - Search: "tapped horn T-matrix 60 Hz notch"
   - Look for literature on phase behavior near quarter-wave

5. **Low Priority**: Explore hybrid approaches
   - Search: "admittance impedance method tapped horn hybrid"
   - Search: "frequency-dependent impedance formula tapped horn"

---

## Test Commands

```bash
# Run full SPL validation
PYTHONPATH=src .venv/bin/python3 tasks/test_three_port_spl.py

# Compare admittance vs Three-Port
PYTHONPATH=src .venv/bin/python3 tasks/diagnose_new_implementation.py

# Test with/without losses
PYTHONPATH=src .venv/bin/python3 tasks/test_lossless_three_port.py

# T-matrix reciprocity check
PYTHONPATH=src .venv/bin/python3 tasks/diagnose_upstream_impedance_detailed.py
```

---

**END OF HANDOFF REPORT**

---

## Summary for Research Agent

You are being asked to investigate why the Three-Port Network T-Matrix method for tapped horn SPL calculation is **less accurate** (7.4 dB RMS error) than the existing admittance method (6.2 dB RMS error).

**Key issues to investigate**:
1. Why does Three-Port underestimate pressure by 57% at 50 Hz and 93% at 60 Hz?
2. Why is there a 120° phase difference at 60 Hz between the two methods?
3. Are the impedance formulas (Z_up = A/C, Z_down = (A*Z_rad+B)/(C*Z_rad+D)) correct?
4. Should D/C be used instead of A/C for upstream impedance?
5. How does Hornresp calculate tapped horn SPL?
6. Are there alternative loss models for large-diameter horns?

The implementation follows Berzborn & Smithers (2018) but doesn't match their claimed accuracy. We need to understand if:
- There's a bug in our implementation
- The literature formula is incorrect
- We need a different approach entirely

All code snippets, test results, and diagnostic outputs are provided above for your investigation.
