# Beranek (1954): Acoustics

**Citation**: Leo L. Beranek, *Acoustics*, McGraw-Hill, 1954.

**Status**: Classic reference, needs full PDF review for equation extraction

**Key Equations for GSD Implementation**:

### Radiation Impedance of Circular Piston

**Equation 5.20**: Radiation impedance for circular piston in infinite baffle
```
Z_R = ρc·S · [R₁(2ka) + jX₁(2ka)]
```
where:
- `Z_R` = radiation impedance (complex Ω)
- `ρ` = air density (kg/m³)
- `c` = speed of sound (m/s)
- `S` = piston area = πa² (m²)
- `a` = piston radius (m)
- `k` = wavenumber = ω/c = 2πf/c
- `R₁(2ka)` = radiation resistance function
- `X₁(2ka)` = radiation reactance function

**Component functions**:
```
R₁(2ka) = 1 - J₁(2ka)/(ka)
X₁(2ka) = H₁(2ka)/(ka)
```
where:
- `J₁` = Bessel function of first kind, order 1
- `H₁` = Struve function of order 1

### Asymptotic Behavior

**Low frequency limit (ka << 1)**:
```
R₁ ≈ (ka)²/2
X₁ ≈ (8ka)/(3π)
```
Radiation impedance is stiffness-like (mass controlled).

**High frequency limit (ka >> 1)**:
```
R₁ ≈ 1
X₁ ≈ 1/(πka)
```
Radiation impedance approaches ρc/S (characteristic impedance of free space).

## Radiation Mass Derivation

The radiation reactance component `X_rad = ρc·S·X₁(2ka)` represents an additional mass load on the piston. This can be expressed as an equivalent mass:

**Radiation Mass**:
```
X_rad = ω·M_rad
M_rad = X_rad / ω = (ρc·S·X₁(2ka)) / ω
```

where:
- `X_rad` = radiation reactance (Ω)
- `ω` = angular frequency = 2πf
- `M_rad` = radiation mass (kg)

**Physical interpretation**:
The radiation mass represents the air mass that moves with the piston. At low frequencies (ka << 1), this becomes:
```
M_rad ≈ (16/3)·ρ₀·a³  (low-frequency limit)
```

This is typically 5-20% of the driver's physical mass for typical loudspeaker drivers.

### Effect on Resonance Frequency

The total moving mass in the resonance equation includes radiation mass:
```
F_s = 1 / (2π√(M_ms·C_ms))

where M_ms = M_md + 2×M_rad(F_s)
```

**Key points**:
- `M_md` = driver mass only (voice coil + diaphragm)
- `M_rad` is frequency-dependent (varies with ω and ka)
- The 2× multiplier on `M_rad` matches Hornresp's empirical methodology
- Iterative solver required because F_s depends on M_rad, which depends on F_s

**Example: BC_8NDL51 driver**
- M_md = 26.77 g (physical driver mass)
- M_rad ≈ 3.7 g at resonance (radiation mass)
- M_ms ≈ 30.5 g total (26.77 + 2×3.7)
- Resonance shift: 68.3 Hz → 64.0 Hz (6.7% lower with radiation mass)

**Why 2× radiation mass?**
Hornresp uses a 2× multiplier on radiation mass (empirically determined from validation data). This may represent:
1. Both sides of the piston (front and back radiation paths)
2. Additional mass loading effects not captured by simple piston theory
3. Empirical correction factor to match measured driver response

**GSD implementation**:
- File: `src/gsd/driver/radiation_mass.py`
- Function: `calculate_radiation_mass(frequency, piston_area, ...)`
- Function: `calculate_resonance_with_radiation_mass(M_md, C_ms, S_d, ...)`
- Iterative solver converges in <10 iterations for typical drivers
- Matches Hornresp resonance frequencies within 0.5 Hz for all B&C test drivers

**Validation results** (December 2025):

| Driver | GSD F_s | Hornresp F_s | Error | Radiation Mass |
|--------|-------------|--------------|-------|----------------|
| BC_8NDL51 | 64.0 Hz | 64.2 Hz | 0.2 Hz | 3.7g (14%) |
| BC_12NDL76 | 44.8 Hz | 44.9 Hz | 0.1 Hz | 13.4g (20%) |
| BC_15DS115 | 19.0 Hz | 19.0 Hz | 0.05 Hz | 28.2g (10%) |
| BC_18PZW100 | 24.1 Hz | 23.9 Hz | 0.2 Hz | 47.5g (19%) |

## Implementation Notes for GSD

**What to implement**:
1. ✅ Bessel J₁ function via scipy.special.j1 (Stage 5)
2. ✅ Struve H₁ function via scipy.special.struve (Stage 5)
3. ✅ Aarts approximation for Struve H₁ (optional, for speed) (Stage 5)
4. ✅ Radiation impedance calculation (Stage 5, Stage 1B)
5. ✅ **Radiation mass calculation for resonance frequency** (Stage 1B, December 2025)
   - Implemented in `src/gsd/driver/radiation_mass.py`
   - Iterative solver matching Hornresp's 2× radiation mass methodology
   - Validated against 4 B&C drivers with <0.5 Hz F_s error

**Numerical considerations**:
- Use scipy.special for Bessel and Struve functions
- Handle small ka carefully (use series expansion if needed)
- High-frequency approximation can speed up calculations

**Validation approach**:
- Compare with Hornresp test cases TC-P1-RAD-01 through TC-P1-RAD-04
- Verify asymptotic limits (ka → 0, ka → ∞)
- Check accuracy of Aarts approximation (<0.1% vs scipy)

### Finite Horn Corrections

Beranek Chapter 5 also discusses:
- Mouth reflection corrections for finite horns
- Effect of horn length on impedance transformation
- Equivalent circuit representations

These become important in Stage 6 (finite horn impedance).

## Resources

**Primary source**: Beranek (1954), "Acoustics"
- PDF available: [https://cdn.preterhuman.net/texts/science_and_technology/physics/Waves_and_Thermodynamics/Acoustics%20-%20L.%20Beranek.pdf](https://cdn.preterhuman.net/texts/science_and_technology/physics/Waves_and_Thermodynamics/Acoustics%20-%20L.%20Beranek.pdf)
- Chapter 5: Radiation of Sound

**Secondary references**:
- Aarts (2003): Efficient Struve H₁ approximation
- Kolbrek Part 1: Summarizes Beranek Eq. 5.20

**Companion references**:
- Olson (1947): Throat impedance equations
- Chabassier (2018): T-matrix propagation through finite horns

**TODO**: Full PDF review to extract exact equation numbers and page numbers

## Connection to Other References

**In Kolbrek Part 1**:
- Revisits Beranek's radiation impedance formula
- Provides implementation notes for Bessel/Struve functions
- Discusses numerical methods for evaluation

**In Aarts (2003)**:
- Provides fast approximation for Struve H₁ function
- Cites Beranek as original source for radiation impedance equation
- Achieves 0.1% accuracy with rational function approximation

**Implementation priority**:
1. High priority for Stage 5 (radiation impedance)
2. Also needed for Stage 1B (bare driver model)
3. Essential for validation against Hornresp
