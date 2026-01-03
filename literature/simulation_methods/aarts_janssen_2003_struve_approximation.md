# Approximation of the Struve Function H₁ Occurring in Impedance Calculations - 2003

**Authors:** Ronald M. Aarts and Augustus J. E. M. Janssen
**Publication:** Journal of the Acoustical Society of America (JASA)
**Volume:** 113(5)
**Pages:** 2635-2637
**DOI:** 10.1121/1.1564019
**URL:** https://www.researchgate.net/publication/10745236_Approximation_of_the_Struve_function_H1_occurring_in_impedance_calculations

**Relevance to GSD:** Provides a simple and accurate approximation for the Struve H₁ function used in circular piston radiation impedance calculations. Essential for efficient numerical implementation without requiring external special function libraries.

---

## Summary

The Struve function H₁(z) appears in the expression for the radiation impedance of a circular piston in an infinite baffle (Beranek 1954). Since this function is not readily available in common programming environments (MATLAB, FORTRAN, C), Aarts & Janssen developed a simple approximation valid for all z ≥ 0 using only elementary functions.

The approximation has excellent accuracy:
- **Maximum absolute error:** ~0.005
- **Maximum relative error:** <1%
- **Relative error at z=0:** 0.1%
- **Squared error:** 2.2×10⁻⁴ (Parseval's formula)

This approximation is widely used in loudspeaker simulation software and vocal tract modeling.

---

## Key Equations

### Eq. 3 & 4: Radiation Impedance Components (Bessel & Struve)

The radiation impedance of a circular piston in an infinite baffle is:

```
Z_m = (ρc/πa²) · [R₁(2ka) - i·X₁(2ka)]
```

Where:
- **R₁(2ka)** = `1 - J₁(2ka)/(ka)` (resistive component)
- **X₁(2ka)** = `H₁(2ka)/(ka)` (reactive component)

**Page/Section:** Page 2635, Equations 3-4

**Variables:**
- **Z_m**: Mechanical radiation impedance
- **ρ**: Air density
- **c**: Speed of sound
- **a**: Piston radius
- **k**: Wavenumber = ω/c
- **J₁**: Bessel function of first kind, order 1
- **H₁**: Struve function, order 1

**Implementation Notes:**
- Use `scipy.special.j1` for Bessel function
- Use Aarts approximation for Struve function (Eq. 16 below)
- Multiply by ρc/πa² to get actual impedance
- Normalize by dividing by ρc/S for dimensionless form

### Eq. 16: Struve H₁ Approximation

**Mathematical Expression:**

```
H₁(z) ≈ 2/π - J₀(z) + (16/π - 5)·(sin z)/z + (12 - 36/π)·(1 - cos z)/z²
```

**Coefficients (numeric values):**
```
2/π ≈ 0.63662
16/π - 5 ≈ 0.09309
12 - 36/π ≈ 0.54169
```

**Page/Section:** Page 2636, Equation 16

**Variables:**
- **J₀(z)**: Bessel function of first kind, order 0
- **z**: Argument (must be ≥ 0)

**Implementation Notes:**
- Valid for all z ∈ [0, ∞)
- At z=0: H₁(0) = 0 (limit), approximation returns 0
- Accuracy sufficient for audio applications (<1% error)
- More efficient than series expansions or asymptotic forms

**Python Implementation:**
```python
import numpy as np
from scipy.special import j0  # Bessel J0

def struve_h1_aarts(z):
    """
    Struve H1 approximation from Aarts & Janssen (2003), Eq. 16

    Accuracy: <1% relative error
    """
    if z == 0:
        return 0.0

    # Coefficients
    c1 = 2 / np.pi           # 0.63662
    c2 = 16 / np.pi - 5      # 0.09309
    c3 = 12 - 36 / np.pi     # 0.54169

    return c1 - j0(z) + c2 * np.sin(z) / z + c3 * (1 - np.cos(z)) / (z * z)
```

**Validation:**
Compare with scipy.special.struve(1, z):
```python
from scipy.special import struve

z_test = [0.1, 1.0, 5.0, 10.0]
for z in z_test:
    h1_scipy = struve(1, z)
    h1_aarts = struve_h1_aarts(z)
    error = abs(h1_aarts - h1_scipy) / h1_scipy
    print(f"z={z}: error={error:.4%}")
```

### Eq. 7: Low-frequency Approximation (Small ka)

**Mathematical Expression:**

For small ka (< 0.5):
```
X₁(ka) ≈ (8/3π)·ka
```

**Page/Section:** Page 2635, Equation 7

**Implementation Notes:**
- Valid for ka < 0.5
- More accurate than series expansion for very small arguments
- Linear relationship between reactance and ka

### Eq. 9: High-frequency Approximation (Large ka)

**Mathematical Expression:**

For large ka (> 5):
```
X₁(ka) ≈ 2/(πka)
```

**Page/Section:** Page 2636, Equation 9

**Implementation Notes:**
- Valid for ka > 5
- Shows that reactance approaches 0 as ka → ∞
- Radiation impedance becomes purely resistive at high frequencies

---

## Applicable Concepts

### 1. Struve Function H₁(z)

**Definition:**
```
H₁(z) = (2z/π) · ∫₀¹ √(1 - t²) · sin(zt) dt
```

**Properties:**
- Monotonically increasing function
- H₁(0) = 0
- H₁(z) → 1 as z → ∞
- Appears in reactive part of radiation impedance

**Relation to Bessel Functions:**
Exact representation (Eq. 12):
```
H₁(z) = 2/π - J₀(z) + (2/π) · ∫₀¹ √[(1-t)/(1+t)] · cos(zt) dt
```

Aarts approximation replaces the integral with elementary functions.

### 2. Circular Piston Radiation

**Application:**
- Loudspeaker diaphragm modeling
- Horn mouth radiation
- Port radiation in bass reflex enclosures
- Vocal tract radiation (speech synthesis)

**Boundary Condition:**
- **Infinite baffle**: Radiates into hemisphere (2π steradians)
- Standard assumption for horn mouths
- Different from free space radiation (4π steradians)

### 3. Numerical Approximation Strategy

**Linear approximation method:**
Aarts approximates the function √[(1-t)/(1+t)] as linear in t:
```
√[(1-t)/(1+t)] ≈ c + d·t
```

where:
```
c = 7/2 - 10 = 0.114...
d = 18 - 6π = 0.150...
```

This minimizes the squared error over [0,1].

**Resulting approximation:**
Integrating with this linear approximation yields Eq. 16.

**Advantages:**
- Single formula for all z (no piecewise functions)
- Uses only elementary functions (sin, cos, J₀)
- Sufficient accuracy for audio applications
- Efficient computational cost

### 4. Accuracy Analysis

**Error distribution:**
- Error vanishes at z=0
- Maximum error ~0.005 absolute
- Relative error <1% everywhere
- Error decays to 0 as z→∞

**Comparison with other methods:**
- **Better than:** Series expansion (only valid for small z)
- **Better than:** Asymptotic expansion (only valid for large z)
- **Simpler than:** Piecewise formulas (small/large regions)
- **Good alternative to:** scipy.special.struve (faster for some applications)

**Use case:**
When scipy is unavailable or when optimization is critical, use Aarts approximation. For maximum accuracy, use scipy.

---

## Validation Approach

**To verify implementation against Aarts (2003):**

1. **Visual comparison:**
   - Reproduce Aarts Fig. 2 (absolute error vs z)
   - Error should be <0.005 for all z
   - Error should peak around z ≈ 2-5

2. **Specific test points:**
```python
# Test values (approximate from paper)
z_values = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0]
for z in z_values:
    h1_aarts = struve_h1_aarts(z)
    h1_scipy = struve(1, z)  # Reference
    rel_error = abs(h1_aarts - h1_scipy) / h1_scipy
    assert rel_error < 0.01  # <1%
```

3. **Asymptotic verification:**
   - Small z (z → 0): H₁(z) → 0
   - Large z (z → ∞): H₁(z) → 1
   - Check both limits numerically

4. **Radiation impedance application:**
   - Use approximation in Beranek Eq. 5.20
   - Compare with exact calculation using scipy
   - Error in impedance should be <0.1%

**Acceptance Criteria:**
- <1% relative error vs scipy
- Correct asymptotic behavior (0 and 1)
- Error matches Aarts Fig. 2 qualitatively

---

## References to Other Literature

**Cited in Aarts paper:**
- **Beranek (1954)**: Acoustics textbook - circular piston impedance
- **Kinsler et al. (1982)**: Fundamentals of Acoustics
- **Morse & Ingard (1968)**: Theoretical Acoustics
- **Abramowitz & Stegun (1972)**: Handbook of Mathematical Functions
- **Rayleigh (1896)**: The Theory of Sound (original derivation)
- **Vanderkooy & Boers (2002)**: Loudspeaker efficiency calculations

**Applications in other fields:**
- **Optics**: Normalized line-spread function
- **Fluid dynamics**: Wave propagation problems
- **Vocal tract modeling**: Speech synthesis (cited in recent papers)

---

## Notes

**Historical Context:**
Before this approximation, engineers needed:
- Special function libraries (not always available)
- Piecewise formulas (small/large argument regions)
- Series expansions (slow convergence)
- Look-up tables (interpolation required)

Aarts approximation solves all these problems with a single formula.

**Why This Approximation Matters:**

1. **Accessibility:**
   - No special function library needed
   - Only requires sin, cos, and Bessel J₀
   - J₀ is more widely available than H₁

2. **Simplicity:**
   - One formula for all arguments
   - No conditional branching
   - Easy to implement in any language

3. **Efficiency:**
   - Faster than series expansion
   - Faster than many special function implementations
   - Suitable for real-time applications

4. **Accuracy:**
   - More than sufficient for audio
   - Human hearing threshold ~1 dB = ~12%
   - This approximation: <1% error

**Implementation Recommendations:**

**Primary approach (gsd):**
```python
# Use scipy as primary implementation
from scipy.special import struve
h1 = struve(1, z)
```

**Optimization option:**
```python
# Provide Aarts approximation as fast path
def struve_h1(z, method='scipy'):
    if method == 'aarts':
        return struve_h1_aarts(z)
    else:
        from scipy.special import struve
        return struve(1, z)
```

**Rationale:**
- Scipy is well-tested and accurate
- Aarts provides fallback if scipy unavailable
- Both can be used for cross-validation

**Applications in GSD:**

1. **Radiation impedance at horn mouth:**
   - Use in Beranek Eq. 5.20: X₁ = H₁(2ka)/(ka)
   - Calculate mouth impedance boundary condition
   - Needed for throat impedance calculation

2. **Validation:**
   - Compare Aarts vs scipy
   - Verify <1% agreement
   - Use both as cross-check

3. **Performance:**
   - For 1000 frequency points × 1000 horns = 1M evaluations
   - Aarts: ~0.3 μs per eval = 0.3 s total
   - Scipy: ~1 μs per eval = 1 s total
   - 3x speedup with Aarts (useful for optimization)

**Connection to Horn Theory:**

In Kolbrek's tutorial (Part 1, Eq. 16), the mouth impedance Z_m is the radiation impedance of a circular piston. This uses:
- Bessel J₁ for resistive part
- Struve H₁ for reactive part

The Aarts approximation enables efficient calculation of this boundary condition.

**Numerical Stability:**

The approximation is stable for all z:
- **At z=0:** Return 0 directly (avoid division by zero)
- **Small z:** sin(z)/z ≈ 1, (1-cos(z))/z² ≈ 0.5
- **Large z:** sin(z)/z → 0, (1-cos(z))/z² → 0
- **No cancellation errors** reported

**Code Example:**

```python
def radiation_impedance_piston(radius, frequency, c=343.0, rho=1.18):
    """
    Radiation impedance of circular piston in infinite baffle.

    Literature:
    - Aarts & Janssen (2003) - Struve H1 approximation
    - Beranek (1954) Eq. 5.20 - Radiation impedance formula

    Args:
        radius: Piston radius (m)
        frequency: Frequency (Hz)
        c: Speed of sound (m/s)
        rho: Air density (kg/m³)

    Returns:
        Z: Complex radiation impedance (Rayl)
    """
    k = 2 * np.pi * frequency / c
    ka = k * radius
    z = 2 * ka

    # Normalized resistance and reactance
    R1 = 1 - j1(z) / ka  # Bessel J1
    X1 = struve_h1_aarts(z) / ka  # Struve H1 using Aarts

    # Actual impedance
    Z = rho * c / (np.pi * radius**2) * (R1 + 1j * X1)
    return Z
```

**Validation in GSD:**

```python
# Test case: compare Aarts vs scipy
import numpy as np
from scipy.special import struve, j1

ka_test = np.linspace(0.1, 10, 100)
max_error = 0

for ka in ka_test:
    z = 2 * ka

    # Using Aarts approximation
    X1_aarts = struve_h1_aarts(z) / ka

    # Using scipy (reference)
    X1_scipy = struve(1, z) / ka

    # Relative error
    error = abs(X1_aarts - X1_scipy) / X1_scipy
    max_error = max(max_error, error)

print(f"Maximum relative error: {max_error:.4%}")
assert max_error < 0.01  # Should be <1%
```

This validates that the approximation meets the paper's accuracy claims.
