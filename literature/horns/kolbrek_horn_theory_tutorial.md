# Horn Theory: An Introduction, Part 1 & 2 - 2012

**Authors:** Bjørn Kolbrek
**Publication:** audioXpress
**URL:** https://www.grc.com/acoustics/an-introduction-to-horn-theory.pdf
**DOI:** N/A (Magazine article)

**Relevance to GSD:** Comprehensive modern tutorial on horn theory covering Webster's horn equation, exponential/hyperbolic/conical horns, throat impedance calculations, cutoff frequency, and finite horn behavior. This is the primary reference for understanding horn simulation methodology used in Hornresp.

---

## Summary

This two-part tutorial provides a complete modern treatment of horn theory for loudspeaker design. Part 1 covers fundamental theory, horn equation solutions for different horn types, throat impedance, cutoff frequency, and finite horn behavior. Part 2 covers curved wave-fronts, tractrix/spherical wave horns, directivity control, and distortion mechanisms.

Key contributions:
- **Webster's Horn Equation** derivation and assumptions (Eq. 2)
- **Throat impedance formulas** for infinite exponential, conical, and hyperbolic horns
- **Cutoff frequency concept** for exponential/hyperbolic horns
- **Finite horn behavior** with mouth termination effects
- **Radiation impedance** at the mouth (piston in infinite baffle assumption)

This tutorial bridges the gap between classical horn theory (Olson, Beranek) and modern horn simulation tools like Hornresp.

---

## Key Equations

### Eq. 2: Webster's Horn Equation

**Mathematical Expression:**

```
d²φ/dx² + (d ln S/dx)(dφ/dx) - k²φ = 0
```

**Variables:**
- **φ**: Velocity potential (related to pressure)
- **x**: Axial distance along horn (m)
- **S(x)**: Cross-sectional area as function of x (m²)
- **k**: Wavenumber = ω/c = 2πf/c (1/m)

**Page/Section:** Part 1, Page 3, Equation 2

**Implementation Notes:**
- This is the fundamental 1D equation for horn simulation
- Assumes plane wave fronts (good approximation below higher-order mode cutoff)
- Assumes infinitesimal amplitude (linear acoustics)
- Assumes lossless propagation
- Solvable analytically for exponential, conical, and hyperbolic horns

**Assumptions/limitations:**
1. Infinitesimal amplitude (small signal)
2. Uniform fluid (no viscosity/thermal losses)
3. No external forces (gravity ignored)
4. Irrotational motion
5. Rigid smooth walls
6. Pressure uniform over wave-front (1P wave assumption)

### Eq. 4: Throat Impedance - Uniform Pipe

**Mathematical Expression:**

For an infinite uniform pipe:
```
z_A = ρ₀c / S_t
```

**Variables:**
- **z_A**: Specific acoustic impedance (Rayl)
- **ρ₀**: Air density = 1.205 kg/m³ at 20°C
- **c**: Speed of sound = 344 m/s at 20°C
- **S_t**: Throat area (m²)

**Page/Section:** Part 1, Page 5, Equation 4

**Implementation Notes:**
- Pure resistance (no reactance)
- Characteristic impedance of uniform tube
- Used as ideal load for plane wave tube testing
- No frequency dependence (infinite pipe)

### Eq. 7: Throat Impedance - Conical Horn

**Mathematical Expression:**

For an infinite conical horn:
```
z_A = (ρ₀c / S_t) · [(k²x₀² + jkx₀) / (1 + k²x₀²)]
```

Where:
- **x₀**: Distance from vertex to throat
- **k**: Wavenumber

For a conical horn with half-angle θ:
```
Ω = 2π(1 - cosθ)
```
where Ω is the solid angle.

**Page/Section:** Part 1, Page 5, Equation 7

**Implementation Notes:**
- No sharp cutoff frequency (unlike exponential)
- Throat resistance rises slowly with frequency
- Depends on solid angle Ω (smaller Ω = better low-frequency loading)
- Higher-order modes appear at lower frequencies than exponential horns

### Eq. 9: Throat Impedance - Exponential Horn (Infinite, Above Cutoff)

**Mathematical Expression:**

```
z_A = (ρ₀c / S_t) · [√(1 - m²/(4k²)) + j(m/(2k))]
```

Where:
- **m**: Flare constant (1/m)
- For exponential horn: S(x) = S_t · e^(mx)
- Flare constant from geometry: m = (1/L)·ln(S_m/S_t)

**Page/Section:** Part 1, Page 6, Equation 9

**Implementation Notes:**
- **Cutoff occurs when m = 2k** or **f_c = mc/(4π)**
- Above cutoff: throat resistance rises quickly
- Below cutoff: throat impedance is purely reactive (see Eq. 13)
- Rapid flare near throat provides good low-frequency loading

**Cutoff frequency formula:**
```
f_c = mc / (4π)  [Hz]
```
where:
- m: flare constant (1/m)
- c: speed of sound (m/s)

### Eq. 13: Throat Impedance - Exponential Horn (Below Cutoff)

**Mathematical Expression:**

```
z_A = j(ρ₀c / S_t) · [(m/(2k)) - √(m²/(4k²) - 1)]
```

**Page/Section:** Part 1, Page 7, Equation 13

**Implementation Notes:**
- Purely reactive (no real part = no power transmission)
- Infinite horn doesn't transmit below cutoff
- Finite horn CAN transmit below cutoff if mouth has resistive impedance
- Reactance is mass-like (positive imaginary)

### Eq. 10 & 12: Throat Impedance - Hyperbolic (Hypex) Horn

**Mathematical Expression:**

Wave-front area expansion:
```
S = S_t[cosh(x/x₀) + T·sinh(x/x₀)]²
```

where **x₀ = c/(2πf_c)**

Throat impedance above cutoff:
```
z_A = (ρ₀c / S_t) · [√(1 - 1/μ²) / (1 - (1-T²)/μ²) + j(T/μ) / (1 - (1-T²)/μ²)]
```

where:
- **μ = f/f_c**: Normalized frequency
- **T**: Taper parameter (0 < T < ∞)
  - T = 1: Exponential horn
  - T → ∞: Conical horn
  - T < 1: Faster impedance rise, higher distortion
  - T = 0: No reactance above cutoff

**Page/Section:** Part 1, Page 7, Equations 10-12

**Implementation Notes:**
- General family including exponential (T=1) and conical (T→∞)
- Lower T values = faster throat resistance rise
- Range 0.5 < T < 1 most useful for improved loading
- Trade-off: T < √2 has resistance peak above asymptotic value

### Eq. 16: Throat Impedance - Finite Horn

**Mathematical Expression:**

```
Z_t = (g·Z_m - b) / (a - f·Z_m)
```

Where:
- **Z_m**: Terminating impedance at the mouth
- **a, b, f, g**: Horn parameters (functions of k and flare)
- **Z_t**: Throat impedance

**Page/Section:** Part 1, Page 9, Equation 16

**Implementation Notes:**
- Mouth impedance Z_m determines throat impedance
- Reflections from mouth cause throat impedance variations
- For minimum reflection: mouth radius should satisfy **kr_m ≥ 1** at cutoff
- Using radiation impedance of piston in infinite baffle as termination

**Mouth termination:**
- Piston in infinite baffle (standard assumption)
- Requires kr_m ≥ 0.7-1 for smooth response
- kr_m > 1 can INCREASE reflections for plane-wave horns
- Spherical wave calculation shows no optimum (larger is better)

### Tractrix Horn Contour (Part 2)

**Mathematical Expression:**

```
x = r_m·ln[(r_m + √(r_m² - r_x²)) / r_x] - √(r_m² - r_x²)
```

Where:
- **r_m**: Mouth radius
- **r_x**: Radius at distance x from mouth
- **x₀ = c/(2πf_c)**: Reference distance

**Page/Section:** Part 2, Page 3

**Implementation Notes:**
- Assumes spherical wave-fronts with constant radius r_m
- Wave-fronts tangent to horn walls
- Expands faster than exponential near mouth
- Not a true 1P horn (wave-fronts not exactly spherical)
- Similar throat impedance to spherical wave horn

---

## Applicable Concepts

### 1. Cutoff Frequency

**Definition:** The frequency below which an exponential or hyperbolic horn acts as a high-pass filter.

**For exponential horn:**
```
f_c = mc / (4π) = [c/(4πL)] · ln(S_m/S_t)
```

**Physical interpretation:**
- Above f_c: Propagating waves, resistive loading
- Below f_c: Evanescent waves, reactive loading (no power transmission in infinite horn)
- Finite horns CAN transmit below f_c if mouth presents resistive load

### 2. Horn as Acoustic Transformer

The horn transforms:
- **High pressure, low velocity** at throat → **Low pressure, high velocity** at mouth
- **High impedance at throat** → **Low impedance at mouth** (matching driver to air)

Purpose:
1. **Driver loading**: Present optimal load to driver (supress resonances)
2. **Directivity control**: Focus sound into desired solid angle

### 3. Plane vs Spherical Wave-fronts

**Plane waves:**
- Uniform impedance along tube
- Conical horn with spherical waves is NOT true 1P horn
- Webster's equation assumes plane wave-fronts
- Actual wave-fronts curve (shown by Hall 1932 measurements)

**Spherical waves:**
- Acoustic impedance changes with frequency and distance
- Below kr = 1: Reactance dominated
- Above kr = 1: Resistance dominated
- Wave-front stretching introduces reactance

**Implication:**
- Physical horn contour must be corrected for curved wave-fronts
- Wilson modified exponential: iterative correction
- Spherical wave/tractrix: assume constant radius wave-fronts

### 4. Finite vs Infinite Horns

**Infinite horn:**
- No reflections from mouth
- Pure exponential: zero resistance below cutoff
- Mathematical idealization

**Finite horn:**
- Mouth reflections cause impedance ripple
- Mouth size determines reflection magnitude
- Optimum mouth size: **kr_m ≈ 1** at f_c (for plane wave)
- Spherical wave: no obvious optimum (larger better)

**Design implication:**
- Mouth circumference should be ≥ 1 wavelength at cutoff
- For bass horns: kr_m = 0.7-1 usually adequate
- For midrange/tweeter: kr_m ≥ 1 preferred

### 5. Directivity Factor Q and Directivity Index DI

**Directivity Factor:**
```
Q = 180° / sin⁻¹[sin(α/2)·sin(β/2)]
```

For spherical segment:
```
Q = 4π / Ω
```

**Directivity Index:**
```
DI = 10·log₁₀(Q)  [dB]
```

**Intercept frequency:**
```
f_I = (25×10⁶) / (x·θ)  [Hz]
```

where:
- **x**: Mouth size (mm) in plane of coverage
- **θ**: Coverage angle in that plane

**Physical meaning:**
- Q: Ratio of on-axis intensity to point source intensity (same power)
- DI: dB increase vs point source on-axis
- f_I: Frequency where horn loses directivity control

### 6. Distortion in Horns

**Two types of nonlinear distortion:**

1. **Unequal volume change** (adiabatic compression)
   - Positive pressure: smaller volume change
   - Negative pressure: larger volume change
   - Generates mainly 2nd harmonic

2. **Propagation distortion**
   - Speed of sound increases with pressure
   - Peaks travel faster than troughs
   - Waveform steepening with distance

**2nd harmonic level for exponential horn** (Beranek formula):

```
p₂/p₁ = [(γ+1)/(2√2)] · (p₁t / γp₀) · (ω/c) · (e^(-mx/2) / (m/2))
```

**Asymptotic value** (Holland et al):

```
D₂[λ] = 1.73×10⁻² · (f/f_c) · √I_t
```

where **I_t** is throat intensity (W/m²)

**Design implications:**
- Lower T values in hyperbolic horns = higher distortion
- Slower flare near throat = higher distortion
- Reflections from mouth increase distortion
- Nonlinear load causes driver distortion

### 7. Higher Order Modes

**Definition:** Cross-wave propagation when wavelength comparable to horn dimensions

**Characteristics:**
- Occur at different frequencies throughout horn (smaller radius = higher cutoff)
- More problematic in conical than exponential horns
- Caused by rapid flare changes or discontinuities
- Disturb wave-front shape → unpredictable directivity
- May affect perceived sound quality

**Mitigation:**
- Slower, smoother curvature changes
- Avoid discontinuities
- Use exponential expansion near throat

---

## Validation Approach

**To verify implementation against Kolbrek tutorial:**

1. **Throat impedance comparison:**
   - Compare calculated throat impedance vs Kolbrek Fig. 2
   - Test exponential, conical, hyperbolic horns
   - Verify cutoff frequency behavior

2. **Mouth size effects:**
   - Reproduce Kolbrek Fig. 10 (effect of kr_m on ripple)
   - Verify kr_m ≈ 1 gives minimum ripple for plane wave

3. **Finite horn length effects:**
   - Reproduce Kolbrek Fig. 6 (75Hz exponential, different lengths)
   - Verify longer horns = faster resistance rise, closer-spaced peaks

4. **Cutoff frequency:**
   - Verify f_c = mc/(4π) for exponential horns
   - Test impedance transition at f_c

5. **Wave-front corrections:**
   - Compare plane vs spherical wave throat impedance
   - Verify spherical wave reduces reflections at large kr_m

**Acceptance Criteria:**
- Throat impedance shapes match Kolbrek figures qualitatively
- Cutoff frequency within 1% of calculated value
- Correct asymptotic behavior (resistance → ρ₀c/S_t above cutoff)
- Reactance sign correct (+j above cutoff for exponential)

---

## References to Other Literature

- **Webster (1919)**: Original derivation of horn equation
- **Hall (1932)**: Measurements of wave-fronts in horns (Part 2, Fig. 14-16)
- **Salmon (1946)**: Hyperbolic horn family (T parameter)
- **Beranek (1954)**: Classic textbook "Acoustics"
- **Olson (1947)**: "Elements of Acoustical Engineering"
- **Holland et al (1996)**: Nonlinear distortion model (Part 2, Fig. 42-43)
- **Geddes (1993)**: Oblate spheroidal waveguide theory

---

## Notes

**Historical Context:**
Kolbrek's tutorial updates classical horn theory (1930s-1960s) with modern insights and simulation techniques. Bridges gap between Olson/Beranek era and contemporary horn simulation tools.

**Key Insights from Tutorial:**

1. **Plane vs Spherical Wave-fronts:**
   - Webster's equation assumes plane waves
   - Real horns have curved wave-fronts
   - Must correct physical horn contour for wave-front curvature
   - Spherical wave calculation often more accurate than plane wave

2. **Mouth Size:**
   - Plane wave assumption: optimum kr_m ≈ 1
   - Spherical wave: no optimum (larger better)
   - kr_m > 1 can increase reflections for plane wave
   - Practical: kr_m = 0.7-1 for bass, kr_m ≥ 1 for midrange/tweeter

3. **Horn Types Comparison:**
   - **Exponential**: Best loading, sharp cutoff, beams at high frequencies
   - **Hyperbolic**: Adjustable loading (T parameter), similar beaming
   - **Conical**: Poor loading, no cutoff, predictable directivity
   - **Tractrix/Spherical wave**: Compromise loading and directivity

4. **Directivity vs Loading Trade-off:**
   - Modern horns sacrifice loading for directivity control
   - Constant directivity horns have resonant throat impedance
   - Classical horns prioritize loading over directivity
   - Design choice depends on application

5. **Distortion Sources:**
   - Air nonlinearity (significant at >150 dB SPL)
   - Mouth reflections (nonlinear combination at high levels)
   - Driver working into nonlinear load
   - Higher distortion with lower T values (hyperbolic)

**Implementation Priorities for GSD:**

1. **Radiation impedance at mouth:**
   - Use piston in infinite baffle (Kolbrek Eq. 16, Z_m parameter)
   - Can use Beranek Eq. 5.20 or Bessel/Struve functions

2. **Horn profiles:**
   - Exponential: S(x) = S_t·e^(mx)
   - Conical: S(x) = S_t·[(x+x₀)/x₀]²
   - Hyperbolic: S(x) = S_t[cosh(x/x₀) + T·sinh(x/x₀)]²

3. **Throat impedance calculation:**
   - Use T-matrix method (see Kolbrek Part 2 references)
   - Or use transmission line approach (a, b, f, g parameters)
   - Transform mouth impedance through horn to throat

4. **Finite horn behavior:**
   - Include mouth reflections
   - Calculate ripple magnitude based on mouth size
   - Consider spherical wave corrections for accuracy

**Limitations of Webster's Equation:**

1. **1P wave assumption:**
   - Only true for uniform tube, parabolic horn, conical horn
   - Other horns: approximation
   - Breaks down when higher-order modes appear

2. **Plane wave assumption:**
   - Actual wave-fronts are curved
   - Need to correct physical horn contour
   - Spherical wave calculation more accurate for flaring horns

3. **Lossless:**
   - No viscosity/thermal losses
   - No wall absorption
   - Becomes important for long horns

4. **Linear:**
   - No harmonic distortion
   - No intermodulation
   - Valid for SPL < ~140 dB

**Connection to Hornresp:**

Hornresp uses the same theoretical framework:
- Webster's horn equation for wave propagation
- Radiation impedance of piston in infinite baffle at mouth
- Transfer matrix (T-matrix) method for multi-segment horns
- Plane wave or spherical wave options

This tutorial provides the theoretical foundation for understanding Hornresp's simulation methodology.

**Practical Design Guidelines:**

From Kolbrek's discussion:
1. **Mouth size**: Can hardly be too large, can easily be too small
2. **Bass horns**: kr_m = 0.7-1 adequate
3. **Midrange/tweeters**: kr_m ≥ 1 preferred
4. **Horn length**: Longer = faster impedance rise, closer-spaced resonances
5. **Flare rate**: Slower near throat = better low-frequency loading
6. **Directivity control**: Requires large mouth relative to wavelength

**Validation Strategy:**

Use Kolbrek's figures for qualitative validation:
- Fig. 2: Throat impedance comparison (exponential vs conical vs hyperbolic)
- Fig. 6: Length effects on throat impedance
- Fig. 10: Mouth size effects on ripple
- Fig. 12: Spherical vs plane wave comparison

Quantitative validation should use Hornresp as reference (primary validation tool).
