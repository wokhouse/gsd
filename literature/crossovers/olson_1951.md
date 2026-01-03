# Olson (1951) - Direct Radiator Loudspeaker Enclosures

**Citation:**
Olson, H. F. (1951). Direct Radiator Loudspeaker Enclosures. *Journal of the Audio Engineering Society*, 2(4).

**Relevance to GSD:**
Primary reference for baffle diffraction phenomena. Olson experimentally verified that a point source on a finite baffle transitions from unity pressure (4π full space) at low frequencies to double pressure (2π half space, +6 dB gain) at high frequencies.

**Key Figures:**
- **Figure 6**: Sphere baffle diffraction pattern
- **Figure 14**: Cube baffle diffraction pattern

**Key Physical Principle:**
A loudspeaker on a finite baffle experiences:
- **Low frequencies** (below baffle step): Radiates into full space (4π steradians)
  - Pressure reference: 1.0 (0 dB)
- **High frequencies** (above baffle step): Radiates into half space (2π steradians)
  - Pressure reference: 2.0 (+6 dB)
- **Transition region**: Diffraction ripples determined by baffle shape

**Baffle Step Frequency:**
The transition frequency is approximately:
```
f_step ≈ 115 / W
```
where W is the smallest baffle dimension in meters.

**Implementation Notes:**
1. Olson's experimental data shows diffraction ripples in the transition region
2. For smooth approximation (no ripples), use Linkwitz shelf filter model
3. For accurate ripple simulation, use Stenzel (1930) circular baffle model
4. Hornresp typically uses the circular baffle model for direct radiator simulations

**Relationship to Hornresp:**
Hornresp's baffle diffraction modeling aligns with Olson's experimental measurements. The ripple pattern in Hornresp's output matches Olson's Figure 6 (sphere) and Figure 14 (cube).

**See Also:**
- `literature/crossovers/linkwitz_2003.md` - Practical baffle step compensation circuits
- `literature/horns/beranek_1954.md` - Radiation impedance theory
- Stenzel (1930) - Mathematical treatment of circular baffle diffraction
