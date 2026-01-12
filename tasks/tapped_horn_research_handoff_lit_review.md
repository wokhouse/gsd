# Tapped Horn Research Handoff - Literature Review Request

**Date**: 2025-01-11
**Status**: CRITICAL - Model has 59% impedance error at quarter-wave, SPL completely broken in subwoofer range
**Repository**: https://github.com/wokhouse/gsd

## Executive Summary

We're implementing a tapped horn simulation using T-matrix transmission line methods. The implementation works well at high frequencies (>200 Hz: <2% error) but fails catastrophically in the subwoofer range (20-80 Hz: 50-284% impedance error, 13 dB SPL error). This blocks use for design assistant since subwoofer flatness is a core objective.

**Need**: Literature review of tapped horn simulation methods to find the correct physics approach, particularly for quarter-wave resonance behavior.

---

## Current Implementation Approach

### Architecture Overview

We use T-matrix (transfer matrix) methods to model acoustic wave propagation through horn segments. Each segment is represented by a 2×2 matrix relating pressure and volume velocity at input/output ports.

**T-Matrix Convention**:
```
[p₁, U₁]ᵀ = [A  B] [p₂, U₂]ᵀ
            [C  D]
```

Where:
- p₁, U₁: Pressure and volume velocity at throat (port 1)
- p₂, U₂: Pressure and volume velocity at tap/mouth (port 2)
- A, B, C, D: Frequency-dependent T-matrix elements

### Code: Exponential Horn T-Matrix

**File**: `src/gsd/simulation/horn_theory.py`

```python
def exponential_horn_tmatrix(
    frequencies: NDArray[np.float64],
    horn: ExponentialHorn,
    medium: MediumProperties = None,
) -> Tuple[NDArray[np.complex128], NDArray[np.complex128],
          NDArray[np.complex128], NDArray[np.complex128]]:
    """
    Calculate T-matrix for exponential horn segment.

    Based on Olson (1947) and Beranek (1954) horn theory.
    Uses Kolbrek's flare constant convention: m = (1/L) × ln(S₂/S₁)

    Returns:
        a, b, c, d: T-matrix elements (complex arrays)
    """
    if medium is None:
        medium = MediumProperties()

    # Flare constant (Kolbrek convention: m = (1/L) × ln(S₂/S₁))
    m = horn.flare_constant

    # Wave number and propagation constant
    k = 2 * np.pi * frequencies / medium.c  # Wave number
    gamma = np.sqrt(k**2 - m**2)  # Propagation constant

    # Characteristic impedance at throat
    Z0 = medium.rho * medium.c / horn.throat_area

    # Horn length
    L = horn.length

    # T-matrix elements for exponential horn
    # Based on transmission line theory
    cosh_gamma_L = np.cosh(gamma * L)
    sinh_gamma_L = np.sinh(gamma * L)

    # Normalized T-matrix (dimensionless)
    a = cosh_gamma_L
    b = Z0 * sinh_gamma_L
    c = (1 / Z0) * sinh_gamma_L
    d = cosh_gamma_L

    return a, b, c, d
```

### Code: Upstream Impedance Calculation

**File**: `src/gsd/simulation/tapped_horn_theory.py`

```python
def upstream_section_impedance(
    frequencies: NDArray[np.float64],
    tapped_horn: TappedHorn,
    medium: MediumProperties = None,
) -> NDArray[np.complex128]:
    """
    Calculate upstream acoustic impedance (throat → tap).

    For a closed throat (U₁ = 0), the input impedance is:
        Z_up = A / C

    This is the standard T-matrix formula for a short-circuited
    transmission line (closed end → pressure maximum).

    Literature:
        - Transmission line theory: Z_in = A/C for U_load = 0
        - Kolbrek, "Horn Loudspeaker Simulation" - T-matrix methods
        - Beranek (1954), Chapter 5 - Horn impedance

    Args:
        frequencies: Frequency array (Hz)
        tapped_horn: TappedHorn geometry
        medium: Acoustic medium properties

    Returns:
        Acoustic impedance at tap looking toward throat (Pa·s/m³)
    """
    if medium is None:
        medium = MediumProperties()

    # Get upstream horn segment (throat → tap)
    upstream_horn = tapped_horn.upstream_section()

    # Calculate T-matrix elements
    if isinstance(upstream_horn, ExponentialHorn):
        a, b, c, d = exponential_horn_tmatrix(
            frequencies, upstream_horn, medium
        )
    elif isinstance(upstream_horn, ConicalHorn):
        # Conical horn T-matrix calculation...
        pass
    else:
        raise ValueError(f"Unsupported profile: {upstream_horn}")

    # Standard formula for closed throat: Z_up = A/C
    # This treats the throat as a rigid wall (U₁ = 0)
    epsilon = 1e-12 * (np.abs(c).max() if len(c) > 0 else 1.0)
    z_upstream = a / (c + epsilon)

    return z_upstream
```

### Code: Tap Point Impedance (Passive Stub Model)

**File**: `src/gsd/simulation/tapped_horn_theory.py`

```python
def tapped_horn_tap_impedance(
    frequencies: NDArray[np.float64],
    tapped_horn: TappedHorn,
    medium: MediumProperties = None,
) -> NDArray[np.complex128]:
    """
    Calculate total acoustic impedance at the tap point.

    The driver at the tap sees both upstream and downstream sections
    in parallel:
        Z_tap = Z_upstream || Z_downstream
              = (Z_up × Z_down) / (Z_up + Z_down)

    Literature:
        - Berzborn & Smithers (2018), AES Paper 10047
        - Danley, US Patent 8,457,341 B2
    """
    if medium is None:
        medium = MediumProperties()

    z_up = upstream_section_impedance(frequencies, tapped_horn, medium)
    z_down = downstream_section_impedance(frequencies, tapped_horn, medium)

    # Parallel combination with numerical stability
    z_sum = z_up + z_down
    epsilon = 1e-12 * np.maximum(np.abs(z_up), np.abs(z_down)).max()
    mask = np.abs(z_sum) < epsilon
    z_sum_safe = z_sum.copy()
    z_sum_safe[mask] += epsilon

    z_tap = (z_up * z_down) / z_sum_safe

    return z_tap
```

### Code: Active Loop Impedance Model

**File**: `src/gsd/simulation/tapped_horn_theory.py`

```python
def calculate_tapped_horn_impedance_active_loop(
    frequencies: NDArray[np.float64],
    tapped_horn: TappedHorn,
    medium: MediumProperties = None,
) -> NDArray[np.complex128]:
    """
    Calculate tapped horn impedance with active driver excitation.

    CRITICAL: This models the PHYSICAL REALITY of a tapped horn:
    - The driver rear radiates into the throat (S₁)
    - The driver front radiates into the tap (S₂)
    - Both ends of the upstream segment are actively driven

    The acoustic impedance loading the driver is:
        Z_acoustic = (p_throat - p_tap) / U_sd

    Derivation:
        For upstream segment (S₁ → S₂), the T-matrix equation is:
            [p₁, U₁]ᵀ = T_12 × [p₂, U₂_in]ᵀ

        Boundary conditions:
            U₁ = -U_sd (driver rear flow into throat)
            p₂ = Z_dn × U₂_out (tap pressure drives downstream)
            U₂_out = U₂_in + U_sd (flow conservation at tap)

        Solving this system:
            p₂ = U_sd × [Z_dn × (D_12 - 1)] / [C_12 × Z_dn + D_12]
            p₁ = p₂ × (A_12 + B_12/Z_dn) - B_12 × U_sd

            Z_acoustic = (p_2 - p_1) / U_sd

    Literature:
        - Berzborn & Smithers (2018), AES Paper 10047
        - Danley, US Patent 8,457,341 B2
        - Kolbrek, "Horn Loudspeaker Simulation" - T-matrix methods
    """
    if medium is None:
        medium = MediumProperties()

    # Get downstream impedance (load at tap looking to mouth)
    # Z_dn = (A_dn × Z_rad + B_dn) / (C_dn × Z_rad + D_dn)
    downstream_segments = tapped_horn.downstream_segments()
    z_rad = circular_piston_radiation_impedance(
        frequencies, downstream_segments[-1].mouth_area, medium
    )
    a_dn, b_dn, c_dn, d_dn = _chain_tmatrices(
        frequencies, downstream_segments, medium
    )

    # Downstream impedance
    num_dn = a_dn * z_rad + b_dn
    den_dn = c_dn * z_rad + d_dn
    z_dn = num_dn / den_dn

    # Get upstream T-matrix elements (throat S₁ → tap S₂)
    upstream_horn = tapped_horn.upstream_section()

    if isinstance(upstream_horn, ExponentialHorn):
        a_up, b_up, c_up, d_up = exponential_horn_tmatrix(
            frequencies, upstream_horn, medium
        )
    # ... (conical horn handling)

    # Solve for pressure at tap (p₂) per unit volume velocity
    p2_numerator = z_dn * (d_up - 1.0)
    p2_denominator = (c_up * z_dn) + d_up

    with np.errstate(divide='ignore', invalid='ignore'):
        p2_per_u = p2_numerator / p2_denominator
        p2_per_u = np.where(np.abs(p2_denominator) < 1e-12, 0, p2_per_u)

    # Solve for pressure at throat (p₁) per unit volume velocity
    # From T-matrix row 1: p₁ = A_12×p₂ + B_12×(p₂/Z_dn - U_sd)
    term_b = b_up * ((p2_per_u / z_dn) - 1.0)
    p1_per_u = (a_up * p2_per_u) + term_b

    # Total acoustic impedance loading the driver
    # Z_acoustic = (p_throat - p_tap) / U_sd
    z_acoustic_load = p1_per_u - p2_per_u

    return z_acoustic_load
```

### Code: System Response Calculation

**File**: `src/gsd/simulation/tapped_horn_theory.py`

```python
def tapped_horn_system_response(
    frequencies: NDArray[np.float64],
    tapped_horn: TappedHorn,
    driver: ThieleSmallParameters,
    medium: MediumProperties = None,
    voltage: float = 2.83,
) -> Dict[str, NDArray[np.float64]]:
    """
    Calculate complete electrical and acoustical response.

    Currently using PASSIVE STUB MODEL (tapped_horn_tap_impedance).
    Active loop model exists but gives similar results.
    """
    if medium is None:
        medium = MediumProperties()

    frequencies = np.atleast_1d(frequencies).astype(float)
    omega = 2 * np.pi * frequencies

    # Step 1: Calculate acoustic impedance loading the driver
    # Using passive stub model: Z_tap = Z_up || Z_down
    z_acoustic = tapped_horn_tap_impedance(
        frequencies, tapped_horn, medium
    )

    # Step 2: Convert acoustic impedance to mechanical impedance
    # Z_mechanical = Z_acoustic × S_d²
    z_mechanical_acoustic = z_acoustic * (driver.S_d ** 2)

    # Step 3: Calculate driver mechanical impedance
    # Z_mech_driver = R_ms + jωM_md + 1/(jωC_ms)
    z_mech_stiffness = 1.0 / (1j * omega * driver.C_ms)
    z_mech_mass = 1j * omega * driver.M_md
    z_mech_resistance = driver.R_ms

    z_mechanical_driver = z_mech_resistance + z_mech_mass + z_mech_stiffness

    # Step 4: Total mechanical impedance
    z_mechanical_total = z_mechanical_driver + z_mechanical_acoustic

    # Step 5: Calculate electrical impedance
    # Z_mot = (BL)² / Z_mechanical_total
    # Z_e = Z_vc + Z_mot
    with np.errstate(divide='ignore', invalid='ignore'):
        z_motional = (driver.BL ** 2) / z_mechanical_total
        z_motional = np.where(np.abs(z_mechanical_total) == 0, 0, z_motional)

    z_voice_coil = driver.R_e + 1j * omega * driver.L_e
    z_electrical = z_voice_coil + z_motional

    # Step 6: Calculate diaphragm velocity
    current = voltage / z_electrical
    force = driver.BL * current
    v_diaphragm = force / z_mechanical_total

    # Step 7: Calculate volume velocity at tap point
    u_tap = v_diaphragm * driver.S_d

    # Step 8: Calculate total pressure at mouth using admittance method
    # ... (pressure calculation - gives wrong results)

    return {
        'electrical_impedance': z_electrical,
        'motional_impedance': z_motional,
        'diaphragm_velocity': v_diaphragm,
        'spl': spl_db,
        'excursion': x_d,
        # ...
    }
```

---

## Current Problems

### Problem 1: Quarter-Wave Impedance Error (HIGH SEVERITY)

**Symptom**: At 50 Hz (quarter-wave frequency f = c/(4L) ≈ 47.6 Hz):
- Our model: Ze = 9.23 Ω
- Hornresp: Ze = 22.49 Ω
- Error: **-59%**

**Expected Physics**:
- At quarter-wave, round trip to throat = λ/2
- This creates 180° phase shift
- Throat should act as pressure node (Z → 0)
- Driver sees low impedance → high excursion → high electrical impedance

**What We Observe**:
- Z_up = A/C = 1.03e+04 Pa·s/m³ (very high)
- This gives Ze = 9.23 Ω (too low)
- But D/B and C/A give near-zero impedance (~5.6e-05)

**Question**: Why doesn't the quarter-wave create a pressure node as expected?

**T-matrix elements at 50 Hz**:
```python
A = 4.377382316108072 - 0.016372338921467607j
B = -31463.363935948364 + 108.0186876335037j
C = -0.0002463260103886807 + 8.45676019460253e-07j
D = 1.9989641206013304 - 0.004680401479814429j

Determinant (AD - BC) = 0.9999999999999991 + 1.3877787807814457e-17j ≈ 1.0 ✓

Z_A_over_C = 1.03e+04 Pa·s/m³ (high, gives Ze = 9.23 Ω)
Z_D_over_B = 6.35e-05 Pa·s/m³ (near zero, would give high Ze!)
Z_C_over_A = 5.63e-05 Pa·s/m³ (near zero, would give high Ze!)
```

### Problem 2: SPL Calculation Completely Wrong (CRITICAL)

**Symptom**: SPL has 13 dB RMS error, completely wrong shape

**Current Method**: Admittance summation
```python
def calculate_front_path_pressure_contribution(...):
    """
    The source at the tap drives into a parallel combination of:
    1. Upstream stub admittance: Y_stub = C_up / A_up
    2. Downstream horn admittance: Y_down = ...
    """
    # Calculate total mouth pressure using admittance method
    # This returns the total pressure, accounting for all reflections
    p_mouth_total = ...
```

**Result**: Wrong magnitude and phase across all frequencies

**Question**: What is the correct method for calculating SPL in a tapped horn?

### Problem 3: Subwoofer Range Failure (BLOCKING ISSUE)

**Symptom**: Model has worst errors exactly where we need it most

| Frequency | Ze Error | SPL Error |
|-----------|----------|-----------|
| 40 Hz | +284% | -23 dB |
| 50 Hz (quarter-wave) | -59% | -4 dB |
| 60 Hz | -21% | ~0 dB |

**Impact**: Cannot use for design assistant because flatness optimization in subwoofer range is a core objective

---

## Test Case for Validation

**Hornresp Parameters**:
```
Driver: BC 15PS100
  S_d = 855 cm²
  BL = 21.2 T·m
  M_md = 147 g
  R_ms = 6.80 N·s/m
  R_e = 5.20 Ω
  L_e = 1.40 mH
  C_ms = 1.04e-4 m/N

Tapped Horn:
  S1 (throat) = 150 cm² → CLOSED
  S2 (tap) = 855 cm²
  S3 (intermediate) = 2265 cm²
  S4 (mouth) = 6000 cm²
  L12 (upstream) = 180 cm
  L23 (intermediate) = 200 cm
  L34 (downstream) = 200 cm
  Profile: exponential (both segments)
  Flare constant: m = 0.967 m⁻¹ (Olson convention)

Medium:
  ρ = 1.18 kg/m³
  c = 343 m/s
  T = 20°C
```

**Hornresp Results at 50 Hz**:
```
Electrical Impedance: Ze = 22.49 Ω
SPL: 97.05 dB (at 2.83 V, 1m)
Cone Excursion: Xd = 0.541 mm
```

**Our Results at 50 Hz**:
```
Electrical Impedance: Ze = 9.23 Ω (-59% error)
SPL: 93.38 dB (-4 dB error)
Cone Excursion: Xd = 0.326 mm (-40% error)
```

---

## Research Questions

### CRITICAL: Tapped Horn Impedance Physics

1. **What is the correct impedance model for a tapped horn?**
   - Passive stub (Z = Z_up || Z_down)? Currently gives Ze = 9.23 Ω
   - Active loop (driver excites both ends)? Currently gives Ze = 6.14 Ω
   - Something else entirely?

2. **Why is quarter-wave behavior different than expected?**
   - For a closed pipe of length L at f = c/(4L):
     - Round trip = λ/2
     - Reflection is 180° out of phase
     - Should create pressure node at open end (Z → 0)
   - But in our tapped horn at 50 Hz:
     - Z_up = A/C = 1.03e+04 (high, not zero)
     - D/B and C/A give near-zero (matches physics!)
     - Why doesn't A/C give zero?

3. **Does the exponential horn flare affect quarter-wave resonance?**
   - In a cylindrical pipe: quarter-wave creates true pressure node
   - In an exponential horn: flare factor prevents A from going to zero
   - Does this change the resonance condition?

4. **What is the correct T-matrix impedance formula?**
   - Standard: Z = A/C (gives 1.03e+04, wrong)
   - Alternatives: Z = D/B or Z = C/A (give near-zero, match physics!)
   - Which one is correct and why?

5. **How does Hornresp calculate tapped horn impedance?**
   - Does Hornresp use T-matrices?
   - What formula does Hornresp use for the upstream section?
   - Can we find Hornresp source code or detailed documentation?

### HIGH PRIORITY: SPL Calculation Method

6. **What is the correct method for calculating mouth pressure?**
   - Current: Admittance summation method
   - Result: 13 dB RMS error
   - Need: Method that gives <3 dB error

7. **How should we handle the multiple paths in a tapped horn?**
   - Path 1: Tap → throat → reflection → tap → mouth
   - Path 2: Tap → mouth (direct)
   - These paths interfere at the mouth
   - Current method doesn't correctly account for this

8. **What is the role of the active driver excitation?**
   - Driver creates pressure at both throat and tap
   - How do these pressures combine?
   - Active loop model vs passive stub model - which is correct?

### MEDIUM PRIORITY: Implementation Details

9. **Are our T-matrix elements correct?**
   - Compare with Kolbrek's MMM_toolbox
   - Test with known analytical solutions
   - Validate exponential horn formulas

10. **What boundary condition does Hornresp use at the throat?**
    - Closed (U = 0)? This is what we assume
    - Finite impedance? Hornresp may include radiation
    - Lossy wall? Hornresp includes viscothermal losses

11. **How should we incorporate losses?**
    - Keefe (1984) viscothermal model?
    - Wall losses?
    - We tried losses - made results worse, not better

---

## Literature We Have

### In Our Repository (`literature/`)

1. **`literature/horns/olson_1947.md`**
   - Exponential horn theory
   - T-matrix methods
   - Cutoff frequency: f_c = mc/(2π)

2. **`literature/horns/beranek_1954.md`**
   - Horn impedance calculations
   - Radiation impedance
   - Transmission line theory

3. **`literature/horns/kolbrek_horn_theory_tutorial.md`**
   - Modern T-matrix treatment
   - Multi-segment horn simulation
   - Input impedance formulas

4. **`literature/transmission_lines/chabassier_tournemenne_2018_tmatrix.md`**
   - T-matrix propagation in waveguides
   - Boundary conditions
   - Impedance transformations

5. **Berzborn & Smithers (2018), AES Paper 10047**
   - Tapped horn impedance model
   - Active loop model derivation
   - We have this referenced but not the full paper

### We Need to Find

1. **Hornresp's actual methodology**
   - Does it use T-matrices?
   - What formulas for tapped horn?
   - How does it handle quarter-wave?

2. **Danley tapped horn patents**
   - US Patent 8,457,341 B2
   - Original tapped horn theory
   - Impedance model derivation

3. **MMM_toolbox by Bjørn Kolbrek**
   - Reference implementation
   - T-matrix methods
   - Can we compare our results?

4. **Alternative tapped horn models**
   - Are there other approaches besides T-matrix?
   - Lumped element models?
   - Finite difference methods?

---

## What We Need From Research Agent

### Primary Objective

Conduct a comprehensive literature review to answer:

**"What is the correct physics model for tapped horn impedance and SPL calculation, particularly at quarter-wave resonance in the subwoofer frequency range (20-80 Hz)?"**

### Specific Deliverables

1. **Tapped Horn Impedance Theory**
   - Correct formula for upstream impedance
   - How to handle quarter-wave resonance
   - Explanation of why A/C vs D/B vs C/A
   - Validation with Hornresp or experimental data

2. **SPL Calculation Method**
   - Correct method for mouth pressure
   - How to account for multiple paths and interference
   - Phase considerations
   - Validation examples

3. **Hornresp's Methodology**
   - What formulas does Hornresp use?
   - Can we find documentation or source code?
   - How does Hornresp differ from standard T-matrix theory?

4. **Quarter-Wave Physics in Exponential Horns**
   - Why doesn't quarter-wave create simple pressure node?
   - Role of horn flare
   - Differences from cylindrical pipes

5. **Active vs Passive Models**
   - When to use active loop model
   - When to use passive stub model
   - Which one matches Hornresp?

6. **Implementation Recommendations**
   - Specific code changes needed
   - Formulas to implement
   - Test cases for validation
   - Expected accuracy improvements

### Search Strategy

1. **Search terms**:
   - "tapped horn impedance calculation"
   - "quarter-wave resonance exponential horn"
   - "Hornresp tapped horn formula"
   - "transmission matrix tapped horn"
   - "Danley tapped horn patent"
   - "Kolbrek MMM_toolbox tapped horn"

2. **Key authors to research**:
   - Tom Danley (original tapped horn inventor)
   - Bjørn Kolbrek (MMM_toolbox, horn theory)
   - Berzborn & Smithers (AES paper on tapped horns)
   - Any Hornresp documentation by David McBean

3. **Resources to check**:
   - AES Audio Engineering Society papers
   - Patents (Danley's tapped horn patents)
   - Hornresp user manual/documentation
   - Academic theses on horn loudspeakers
   - GitHub repositories for horn simulation

---

## Success Criteria

Research is successful if it provides:

1. ✅ **Clear explanation** of why quarter-wave impedance doesn't go to zero
2. ✅ **Correct impedance formula** that matches Hornresp within 5%
3. ✅ **SPL calculation method** that matches Hornresp within 3 dB
4. ✅ **Implementation guide** with specific formulas and code structure
5. ✅ **Validation approach** to verify the fix works
6. ✅ **Literature citations** for all methods

---

## Context: Why This Matters

**Project Goal**: GSD is a CLI tool for loudspeaker enclosure design with focus on **flatness in the subwoofer range (20-80 Hz)**.

**Current Blocker**: Tapped horn implementation has 59% impedance error at 50 Hz (exactly in subwoofer range) and 13 dB SPL error, making it **completely unsuitable for design use**.

**Impact**: Cannot include tapped horn support in design assistant until this is fixed. Users must use Hornresp directly for tapped horns.

**Urgency**: HIGH - This is blocking a core feature of the design assistant.

---

## Files to Reference

**Implementation**:
- `src/gsd/simulation/tapped_horn_theory.py` - Main tapped horn code
- `src/gsd/simulation/horn_theory.py` - T-matrix calculations
- `src/gsd/simulation/types.py` - Data structures (TappedHorn, ExponentialHorn)
- `src/gsd/driver/parameters.py` - Thiele-Small parameters

**Documentation**:
- `tasks/TAPPED_HORN_FINAL_STATUS.md` - Complete status summary
- `tasks/tapped_horn_impedance_scaling_investigation.md` - Scaling attempt (failed)
- `tasks/tapped_horn_impedance_fix_status.md` - Active loop implementation

**Validation Data**:
- `imports/th_sim.txt` - Hornresp validation data (534 frequency points)
- `imports/th_params.txt` - Hornresp parameters

**Test Scripts**:
- `tasks/debug_tapped_horn_comparison.py` - Compare with Hornresp
- `tasks/diagnose_correct_impedance.py` - Calculate target impedance
- `tasks/debug_tmatrix_values.py` - Inspect T-matrix elements

---

## Notes for Research Agent

1. **No local codebase access**: You can access the GitHub repo at https://github.com/wokhouse/gsd but not the local filesystem.

2. **Focus on physics**: We need the correct acoustic theory, not just code fixes. The problem is fundamental understanding of tapped horn physics.

3. **Quarter-wave is key**: This is where standard transmission line theory seems to break down. Why?

4. **Hornresp is ground truth**: Whatever formula Hornresp uses, that's what we need to replicate. Hornresp is the industry standard.

5. **Think about subwoofer range**: We need accuracy 20-80 Hz, not just high frequencies. This is where tapped horns are used most.

6. **Include equations**: We need specific formulas, not just conceptual explanations.

7. **Cite sources**: Every method should have a literature citation (paper, book, patent).

---

**READY FOR RESEARCH AGENT**

Please investigate:
1. Correct tapped horn impedance model for quarter-wave resonance
2. SPL calculation method that works for tapped horns
3. How Hornresp calculates tapped horn response
4. Why our T-matrix approach fails at subwoofer frequencies

Provide:
1. Explanation of the correct physics
2. Specific formulas to implement
3. Code examples if possible
4. Literature citations
5. Validation approach

Thank you!
