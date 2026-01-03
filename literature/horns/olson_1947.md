# Olson (1947): Elements of Acoustical Engineering

**Citation**: Harry F. Olson, *Elements of Acoustical Engineering*, 1947.

**Status**: Classic reference, needs full PDF review for equation extraction

**Key Equations for GSD Implementation**:

### Exponential Horn Profile

**Equation 5.12**: Exponential horn area function
```
S(x) = S_t · e^(mx)
```
where:
- `S(x)` = cross-sectional area at distance x from throat
- `S_t` = throat area
- `m` = flare constant (1/m)
- `x` = axial distance from throat

This is the fundamental equation defining the exponential horn shape.

### Cutoff Frequency

**Equation 5.18**: Exponential horn cutoff frequency
```
f_c = mc / (4π)
```
where:
- `f_c` = cutoff frequency (Hz)
- `m` = flare constant (1/m)
- `c` = speed of sound (m/s)

**Physical interpretation**:
- Below f_c, the horn acts as a high-pass filter (no efficient sound propagation)
- At f_c, the acoustical resistance is zero
- Above f_c, the horn transmits sound efficiently

### Infinite Exponential Horn Throat Impedance

Above cutoff (m < 2k):
```
z_A = (ρ₀c / S_t) · [√(1 - m²/(4k²)) + j(m/(2k))]
```

Below cutoff (m > 2k):
```
z_A = j(ρ₀c / S_t) · [(m/(2k)) - √(m²/(4k²) - 1)]
```

where:
- `z_A` = specific acoustic impedance at throat
- `ρ₀` = air density
- `c` = speed of sound
- `S_t` = throat area
- `k` = wavenumber = ω/c
- `j` = imaginary unit

**Key behavior**:
- Above cutoff: resistive component dominates (real power transfer)
- Below cutoff: purely reactive (no real power transfer)
- At cutoff: real part → 0

### Flare Constant from Geometry

From throat/mouth areas and length:
```
m = (1/L) · ln(S_m/S_t)
```
where:
- `L` = horn length
- `S_m` = mouth area
- `S_t` = throat area

## Implementation Notes for GSD

**What to implement**:
1. ✅ Exponential horn area function (Stage 2)
2. ✅ Cutoff frequency calculation (Stage 2)
3. ✅ Flare constant from geometry (Stage 2)
4. ✅ Infinite horn throat impedance (Stage 6 - for validation)

**Validation approach**:
- Compare cutoff frequency with Hornresp (<0.1% tolerance)
- Verify throat impedance matches analytical solutions
- Check cutoff behavior (real part → 0 at f_c)

## Resources

**Primary source**: Olson (1947), "Elements of Acoustical Engineering"
- PDF available: [http://cyrille.pinton.free.fr/electroac/lectures_utiles/son/Olson.pdf](http://cyrille.pinton.free.fr/electroac/lectures_utiles/son/Olson.pdf)
- Chapter 5: Horns and Horn-Type Loudspeakers

**Secondary references**:
- Kolbrek Part 1: Revisits Olson's equations with modern notation
- Beranek (1954): Alternative derivations of same equations

**TODO**: Full PDF review to extract exact equation numbers and page numbers
