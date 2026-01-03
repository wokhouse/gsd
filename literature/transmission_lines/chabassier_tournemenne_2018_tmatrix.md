# About the Transfer Matrix Method in the Context of Acoustical Wave Propagation in Wind Instruments - 2018

**Authors:** Juliette Chabassier and Robin Tournemenne
**Publication:** INRIA Research Report RR-9254
**URL:** https://rtournem.frama.io/assets/pdfs/PersoRR-2019.pdf
**DOI:** N/A (Research report)

**Relevance to GSD:** Provides unified formulation of transfer matrices for cones and cylinders, with and without viscothermal losses. Shows how to compute input impedance using T-matrix method, which is the foundation for horn simulation in tools like Hornresp.

---

## Summary

This report presents a unified formulation of transfer matrix coefficients for cylindrical and conical ducts, both with and without viscothermal losses. The transfer matrix method (TMM) allows computation of input impedance by decomposing a complex bore into simple geometric segments (cylinders, cones, etc.).

Key contributions:
- **Unified T-matrix formula** that works for both cylinders and cones
- **Seamless formulation** that doesn't diverge when Ri → Ri+1 (cone → cylinder)
- **Viscothermal losses** included via Kirchhoff's theory
- **Exact analytical solutions** for lossless case
- **Approximate solutions** for lossy cones (discretization approach)

This provides the mathematical foundation for simulating horns as cascaded T-matrices.

---

## Key Equations

### Eq. 1: Webster's Horn Equation (Lossless)

**Mathematical Expression:**

```
(1/S)(dS/dx)(dp̂/dx) + k²p̂ = 0
```

Where:
- **S(x)**: Cross-sectional area at position x
- **p̂(x, ω)**: Acoustic pressure (frequency domain)
- **k = ω/c**: Wavenumber
- **x**: Axial coordinate

**Page/Section:** Page 4, Equation 1

**Equivalent form (Equation 2a):**
```
k²p̂ + (1/S)(dS/dx)(dp̂/dx) + d²p̂/dx² = 0
```

**Volume velocity (Equation 1b):**
```
jωρSû + dp̂/dx = 0
```

Where **û** is volume velocity.

**Implementation Notes:**
- Assumes plane wave propagation (1P wave)
- Assumes lossless propagation (no viscosity/thermal losses)
- Assumes infinitesimal amplitude (linear acoustics)
- k = ω/c is real for lossless case

### Eq. 8: Transfer Matrix Definition

**Mathematical Expression:**

```
[p̂ᵢ]   [aᵢ  bᵢ]   [p̂ᵢ₊₁]
[ûᵢ] = [cᵢ  dᵢ] · [ûᵢ₊₁]
```

Or:
```
ζᵢ = Tᵢ(ω) · ζᵢ₊₁
```

**Page/Section:** Page 5, Equation 8

**Variables:**
- **p̂ᵢ**: Pressure at segment input
- **ûᵢ**: Volume velocity at segment input
- **Tᵢ**: Transfer matrix for segment i

**Global relation (Equation 9):**
```
ζ₀ = (∏ᵢ Tᵢ) · [Z_R(ω); 1]
```

Where **Z_R** is radiation impedance at the output.

**Implementation Notes:**
- T-matrices are multiplied in reverse order (from output to input)
- Global T-matrix: T_total = T_N · ... · T_2 · T_1
- Input impedance: Z_in = ζ₀(1) / ζ₀(2) = p̂₀ / û₀

### Eq. 11: Cylinder T-Matrix (Lossless)

**Mathematical Expression:**

For a cylinder of length ℓ and area S:
```
T = [cos(kℓ)      jZ_c sin(kℓ)]
     [j sin(kℓ)/Z_c   cos(kℓ)  ]
```

Where:
```
Z_c = ρc/S  (characteristic impedance)
```

**Page/Section:** Page 5, Equation 11

**Variables:**
- **ℓ**: Segment length (m)
- **k**: Wavenumber = ω/c
- **Z_c**: Characteristic impedance (Rayl·m² or Pa·s/m³)
- **ρ**: Air density
- **c**: Speed of sound

**Implementation Notes:**
- Determinant = 1 (lossless case)
- Symmetric structure: diagonal elements equal
- Off-diagonal elements related by Z_c
- For small kℓ: T ≈ [1, jZ_c kℓ; jkℓ/Z_c, 1]

### Eq. 12: Cone T-Matrix (Lossless)

**Mathematical Expression:**

For a cone with input radius Rᵢ, output radius Rᵢ₊₁, length ℓ:
```
a = (x̃ᵢ₊₁/x̃ᵢ)·cos(kℓ) - (1/(kx̃ᵢ))·sin(kℓ)
b = (x̃ᵢ/x̃ᵢ₊₁)·jZ_cᵢ·sin(kℓ)
c = jZ_cᵢ·(x̃ᵢ₊₁/x̃ᵢ)·[k²x̃ᵢ²·sin(kℓ) - ℓk·cos(kℓ)] / (k²x̃ᵢx̃ᵢ₊₁²)
d = (x̃ᵢ/x̃ᵢ₊₁)·cos(kℓ) + (1/(kx̃ᵢ))·sin(kℓ)
```

Where:
- **x̃**: Distance from cone apex (can be negative for convergent cone)
- **Z_cᵢ = ρc/(πRᵢ²)**: Characteristic impedance at input

**Page/Section:** Page 6, Equation 12

**Variables:**
- **Rᵢ**: Input radius
- **Rᵢ₊₁**: Output radius
- **ℓ = x̃ᵢ₊₁ - x̃ᵢ**: Length along cone axis
- **x̃ᵢ < 0** for convergent cone (apex "behind" input)

**Implementation Notes:**
- More complex than cylinder due to varying area
- Depends on geometry (apex location)
- Formula from Mapes-Riordan (1993) referenced

**Important:** x̃ coordinates are negative for convergent sections!

### Eq. 13: Unified Cone/Cylinder T-Matrix (Lossless)

**Mathematical Expression:**

Single formula that works for both cone and cylinder:
```
a = (Rᵢ₊₁/Rᵢ)·cos(kℓ) - (β/k)·sin(kℓ)
b = (Rᵢ/Rᵢ₊₁)·jZ_cᵢ·sin(kℓ)
c = jZ_cᵢ·(Rᵢ₊₁/Rᵢ)·[(β²/k²)·sin(kℓ) - (ℓβ²/k)·cos(kℓ)]
d = (Rᵢ/Rᵢ₊₁)·cos(kℓ) + (β/k)·sin(kℓ)
```

Where:
```
β = (Rᵢ₊₁ - Rᵢ)/(ℓ·Rᵢ)
```

**Page/Section:** Page 7, Equation 13

**Implementation Notes:**
- **No divergence** when Rᵢ → Rᵢ₊₁ (cone → cylinder)
- When Rᵢ = Rᵢ₊₁: β = 0, recovers cylinder formula
- When Rᵢ ≠ Rᵢ₊₁: gives cone formula
- β can be interpreted as 1/x̃ in cone coordinates

**Python Implementation:**
```python
def unified_tmatrix(R_in, R_out, length, k, rho_c):
    """
    Unified T-matrix for cone or cylinder (lossless).

    Literature: Chabassier & Tournemenne (2018), Eq. 13
    """
    if R_in == 0 or R_out == 0:
        raise ValueError("Radius cannot be zero")

    S_in = np.pi * R_in**2
    Z_c = rho_c / S_in

    beta = (R_out - R_in) / (length * R_in)

    kl = k * length
    sin_kl = np.sin(kl)
    cos_kl = np.cos(kl)

    a = (R_out / R_in) * cos_kl - (beta / k) * sin_kl
    b = (R_in / R_out) * 1j * Z_c * sin_kl
    c = 1j * Z_c * (R_out / R_in) * ((beta**2 / k**2) * sin_kl -
                                       (length * beta**2 / k) * cos_kl)
    d = (R_in / R_out) * cos_kl + (beta / k) * sin_kl

    return np.array([[a, b], [c, d]])
```

### Eq. 15: Webster's Equation with Viscothermal Losses

**Mathematical Expression:**

```
Z_v(ω, x)·û + dp̂/dx = 0
Y_t(ω, x)·p̂ + dû/dx = 0
```

Where (Equation 16):
```
Z_v(ω, x) = (jωρ/S(x)) · [1 - J(kv(ω)·R(x))]⁻¹
Y_t(ω, x) = (jωS(x)/ρc²) · [1 + (γ-1)·J(kt(ω)·R(x))]
```

**Page/Section:** Page 8, Equations 15-16

**Variables:**
- **Z_v**: Series impedance per unit length (viscous losses)
- **Y_t**: Shunt admittance per unit length (thermal losses)
- **J(z)**: Loss function = 2z·J₁(z)/J₀(z)
- **kv(ω)**: Viscous wavenumber = √(jωρ/µ)
- **kt(ω)**: Thermal wavenumber = √(jωρC_p/κ)
- **µ**: Dynamic viscosity
- **κ**: Thermal conductivity
- **γ**: Specific heat ratio = 1.402 for air

**Loss function J(z):**
```
J(z) = 2z·J₁(z) / J₀(z)
```

where J₀ and J₁ are Bessel functions.

**Implementation Notes:**
- Losses depend on radius R(x)
- Complex wavenumber kv, kt
- No exact analytical solution for cones (only cylinders)
- Requires numerical discretization for cones

### Eq. 18: Cylinder T-Matrix (With Losses)

**Mathematical Expression:**

For a cylinder with losses:
```
T = [cosh(Γℓ)      Z_c·sinh(Γℓ)]
     [sinh(Γℓ)/Z_c   cosh(Γℓ)   ]
```

Where:
```
Γ = √(Z_v·Y_t)  (complex propagation constant)
Z_c = √(Z_v/Y_t)  (characteristic impedance with losses)
```

**Page/Section:** Page 8, below Equation 18

**Implementation Notes:**
- Same form as lossless case but:
  - cos(kℓ) → cosh(Γℓ)
  - sin(kℓ) → sinh(Γℓ)
  - k → Γ (complex)
  - Z_c includes losses

**Relation to lossless:**
When losses → 0:
- Γ → jk
- Z_c → ρc/S
- Recovers lossless formulas

### Eq. 21: Unified T-Matrix (With Losses - Approximate)

**Mathematical Expression:**

Approximate T-matrix for cones with losses:
```
a = (Rᵢ₊₁/Rᵢ)·cosh(Γᵢℓ) - (β/Γᵢ)·sinh(Γᵢℓ)
b = (Rᵢ/Rᵢ₊₁)·Z_cᵢ·sinh(Γᵢℓ)
c = (1/Z_cᵢ)·(Rᵢ₊₁/Rᵢ)·[-(β²/Γᵢ²)·sinh(Γᵢℓ) + (ℓβ²/Γᵢ)·cosh(Γᵢℓ)]
d = (Rᵢ/Rᵢ₊₁)·cosh(Γᵢℓ) + (β/Γᵢ)·sinh(Γᵢℓ)
```

Where:
```
β = (Rᵢ₊₁ - Rᵢ)/(ℓ·Rᵢ)
Γᵢ = Γ(ω, R_⊙ᵢ)  (evaluated at effective radius)
Z_cᵢ = Z_c(ω, R_⊙ᵢ)
R_⊙ᵢ = (2·min(Rᵢ, Rᵢ₊₁) + max(Rᵢ, Rᵢ₊₁)) / 3
```

**Page/Section:** Page 10, Equation 21

**Implementation Notes:**
- Approximation: losses evaluated at effective radius R_⊙
- R_⊙ chosen as weighted average of input/output radii
- Alternative: discretize cone into many small cones
- More accurate than lossless for long horns

**Approximation accuracy:**
- Good for slowly varying cones
- Improves with more subdivisions
- Widely used in musical instrument modeling

---

## Applicable Concepts

### 1. Transfer Matrix Method (TMM)

**Purpose:**
Compute input impedance of a duct with complex geometry by:
1. Dividing duct into simple segments (cylinders, cones)
2. Computing T-matrix for each segment
3. Multiplying matrices: T_total = T_N · ... · T_2 · T_1
4. Applying radiation impedance at output
5. Extracting input impedance from result

**Advantages:**
- Efficient for piecewise-constant geometries
- Analytical solutions for simple shapes
- Easy to cascade different segment types
- Widely used in horn and wind instrument modeling

**Limitations:**
- Assumes plane wave propagation (breaks down at high frequencies)
- Assumes linear acoustics (no distortion)
- Requires discretization for complex profiles

### 2. Webster's Horn Equation

**Derivation:**
From 3D wave equation → 1D approximation using:
- Slowly varying cross-section S(x)
- Plane wave fronts
- No transverse modes
- Asymptotic expansion in small parameter ε = diameter/wavelength

**Result (Equation 32):**
```
(1/S)(dS/dx)(dp̂/dx) + k²p̂ = 0
```

**Assumptions:**
1. Perfect gas
2. Isentropic flow
3. No mean flow
4. Rigid smooth walls
5. Slowly varying cross-section
6. Wavelength >> duct diameter

**Error term:** O(ε²) where ε = diameter/wavelength

### 3. Characteristic Impedance

**Definition:**
```
Z_c = √(Z_series / Y_shunt) = √((jωρ/S) / (jωS/ρc²)) = ρc/S
```

**Physical meaning:**
- Impedance seen by a wave in infinite uniform duct
- Ratio of pressure to volume velocity for propagating wave
- Real for lossless case
- Complex for lossy case

**Cylinder:**
```
Z_c = ρc/S  (constant along duct)
```

**Cone:**
```
Z_c(x) = ρc/S(x)  (varies with position)
```

### 4. Viscothermal Losses

**Two mechanisms:**

1. **Viscous losses** (friction with walls):
   - Depend on boundary layer thickness
   - Modeled by series impedance Z_v
   - Dominant at low frequencies, small radii

2. **Thermal losses** (heat conduction to walls):
   - Depend on thermal boundary layer
   - Modeled by shunt admittance Y_t
   - Also significant at low frequencies, small radii

**Loss function J(z):**
```
J(z) = 2z·J₁(z) / J₀(z)
```
where J₀, J₁ are Bessel functions.

For small z (thin boundary layer):
```
J(z) ≈ 1 - j·z/√2
```

For large z (thick boundary layer):
```
J(z) ≈ 1 - j/z
```

**Combined effect:**
- Complex propagation constant Γ
- Attenuation per unit length
- Phase velocity different from c
- More important for narrow tubes (wind instruments)
- Less important for horns (larger radii)

### 5. Radiation Impedance

**Boundary condition at output (Equation 3):**
```
p̂(L, ω) / û(L, ω) = Z_R(ω)
```

**Models:**
- **Piston in infinite baffle** (circular piston)
- **Piston in free space** (no baffle)
- **Flanged pipe** (finite baffle)
- **Unflanged pipe** (free end)

**For horns:**
- Standard assumption: piston in infinite baffle
- Use Beranek Eq. 5.20 or Kolbrek formulation
- Depends on mouth radius and frequency

**Approximation for large mouth (ka >> 1):**
```
Z_R ≈ ρc/S  (matched to free field)
```

### 6. Cone Coordinate System

**Apex-based coordinates:**
- Origin at cone apex (virtual or real)
- x̃ measured from apex
- x̃ can be negative (apex behind input)
- Convergent cone: x̃ < 0
- Divergent cone: x̃ > 0

**Throat and mouth locations:**
- Throat at x̃ = x̃ᵢ (distance from apex)
- Mouth at x̃ = x̃ᵢ₊₁
- Length: ℓ = x̃ᵢ₊₁ - x̃ᵢ

**Relation to physical geometry:**
For a cone with half-angle θ:
```
x̃ = R / tan(θ)
```
where R is radius at that position.

---

## Validation Approach

**To verify implementation against Chabassier (2018):**

1. **Cylinder T-matrix:**
   - Compare with analytical solution
   - Check: determinant = 1 for lossless
   - Check: a = d (symmetry)
   - Verify: T(kℓ=0) = identity matrix

2. **Cone T-matrix:**
   - Compare with Mapes-Riordan (1993)
   - Verify convergence to cylinder as Rᵢ → Rᵢ₊₁
   - Test divergent and convergent cones
   - Check throat impedance for infinite cone

3. **Unified formulation:**
   - Verify Rᵢ = Rᵢ₊₁ recovers cylinder
   - Test continuity at small radius differences
   - Compare with separate formulas

4. **Lossy cylinder:**
   - Verify Γ → jk as losses → 0
   - Check attenuation increases with frequency
   - Compare with numerical solution

5. **Multi-segment systems:**
   - Test cascaded cylinders
   - Test cylinder-cone combinations
   - Verify continuity at interfaces

**Acceptance Criteria:**
- Determinant = 1 for lossless matrices
- Continuous behavior for radius transitions
- Convergence to known solutions
- Input impedance matches literature examples

---

## References to Other Literature

**Cited in report:**
- **Mapes-Riordan (1993)**: Horn modeling with conical/cylindrical elements (J. Audio Eng. Soc.)
- **Rienstra (2005)**: Webster's horn equation revisited (SIAM)
- **Kergomard (1984)**: Input impedance of brass instruments
- **Kirchhoff (1868)**: Heat conduction in gases (original loss theory)
- **Zwikker & Kosten (1949)**: Sound absorbing materials

**Related to gsd:**
- **Kolbrek tutorial**: Uses same T-matrix approach
- **Hornresp**: Implements T-matrix method for multi-segment horns
- **Aarts (2003)**: Struve function for radiation impedance

---

## Notes

**Historical Context:**
Transfer matrix method has been used since the 1960s for:
- Musical instrument acoustics (wind instruments)
- Horn loudspeaker design
- Duct acoustics
- Transmission line modeling

**Why T-Matrix Method?**

1. **Modularity:**
   - Each segment: simple analytical solution
   - Complex systems: cascade segments
   - Easy to add new segment types

2. **Efficiency:**
   - 2×2 matrix multiplication
   - No need to solve full wave equation
   - Fast for many segments

3. **Physical insight:**
   - Input/output impedance relations
   - Forward/backward waves
   - Reflection coefficients

**Implementation Strategy for GSD:**

**Phase 1: Lossless cylinders and cones**
```python
# T-matrix for lossless duct
def tmatrix_lossless(R_in, R_out, length, k, rho_c):
    """Unified T-matrix (Eq. 13)"""
    beta = (R_out - R_in) / (length * R_in)
    S_in = np.pi * R_in**2
    Z_c = rho_c / S_in

    kl = k * length
    c = np.cos(kl)
    s = np.sin(kl)

    a = (R_out / R_in) * c - (beta / k) * s
    b = (R_in / R_out) * 1j * Z_c * s
    c = 1j * Z_c * (R_out / R_in) * ((beta**2/k**2)*s - (length*beta**2/k)*c)
    d = (R_in / R_out) * c + (beta / k) * s

    return np.array([[a, b], [c, d]])
```

**Phase 2: Add losses (optional)**
```python
# Loss function J(z)
def loss_function(z):
    """Eq. 17: J(z) = 2z*J1(z)/J0(z)"""
    from scipy.special import j0, j1
    if z == 0:
        return 0
    return 2*z * j1(z) / j0(z)

# Complex propagation constant
def propagation_constant(omega, R):
    """Compute Γ for given radius and frequency"""
    # Air constants
    rho = 1.18  # kg/m³
    mu = 1.708e-5  # viscosity
    kappa = 5.77e-3  # thermal conductivity
    gamma = 1.402  # specific heat ratio
    Cp = 240  # Cal/(kg·°C) - convert to SI
    c = 343  # m/s

    kv = np.sqrt(1j * omega * rho / mu)
    kt = np.sqrt(1j * omega * rho * Cp / kappa)

    Jv = loss_function(kv * R)
    Jt = loss_function(kt * R)

    # Series impedance
    Zv = (1j * omega * rho / (np.pi * R**2)) / (1 - Jv)
    # Shunt admittance
    Yt = (1j * omega * np.pi * R**2 / (rho * c**2)) * (1 + (gamma - 1) * Jt)

    return np.sqrt(Zv * Yt)
```

**Cascading segments:**
```python
def cascade_tmatrices(tmatrices):
    """Multiply T-matrices: T_total = T_N @ ... @ T_2 @ T_1"""
    result = np.eye(2, dtype=complex)
    for T in reversed(tmatrices):
        result = T @ result
    return result

def input_impedance(tmatrices, Z_radiation):
    """Compute input impedance"""
    T_total = cascade_tmatrices(tmatrices)

    # Output state
    p_out = Z_radiation
    u_out = 1

    # Input state
    [p_in, u_in] = T_total @ [p_out, u_out]

    return p_in / u_in
```

**Relation to Hornresp:**

Hornresp uses the same T-matrix approach:
- Each horn segment: 2×2 T-matrix
- Multi-segment horns: matrix product
- Radiation impedance: piston in infinite baffle
- Driver: coupled via equivalent circuit

This report provides the theoretical foundation for understanding Hornresp's methodology.

**Approximation vs Exact:**

**Exact (lossless):**
- Cylinder: analytical solution
- Cone: analytical solution (Eq. 12 or 13)
- Exponential: analytical solution (not in this report)

**Approximate (losses):**
- Cylinder: analytical (Eq. 18)
- Cone: discretize into sub-cones (Section 2.2)
- Exponential: approximate as short cone segments

**Trade-off:**
- Lossless: simpler, faster, adequate for horns
- Lossy: more accurate for narrow tubes (instruments)
- For horns: losses usually negligible (large radii)

**Numerical Considerations:**

1. **Small segment length:**
   - kℓ << 1: numerical precision issues
   - Use series expansion for small kℓ
   - Or limit minimum segment length

2. **Large ka:**
   - sin(kℓ), cos(kℓ): oscillatory
   - Use complex exponentials for stability
   - Or use hyperbolic functions for lossy case

3. **Cone apex singularity:**
   - x̃ → 0: formula diverges
   - Physical cone has finite throat
   - Avoid cones extending to apex

**Connection to Exponential Horns:**

While this report focuses on cones and cylinders, the T-matrix method extends to other profiles:
- Exponential: analytical T-matrix (Kolbrek Eq. T2)
- Hyperbolic: analytical T-matrix (Kolbrek Eq. T3)
- Arbitrary: approximate as short cone/cylinder segments

**GSD Implementation Strategy:**

1. **Phase 1:** Implement lossless cylinder/cone T-matrices
2. **Phase 2:** Add exponential T-matrix (Kolbrek)
3. **Phase 3:** Add radiation impedance (Aarts Struve)
4. **Phase 4:** Add driver coupling (Thiele-Small)
5. **Phase 5:** Add losses (optional enhancement)

Losses can be added later as an optional refinement for improved accuracy, especially for narrow horns or high-precision applications.
