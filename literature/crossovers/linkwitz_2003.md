# Linkwitz (2003) - Diffraction from Baffle Edges

**Citation:**
Linkwitz, S. (2003). Diffraction from baffle edges. LinkwitzLab.
https://linkwitzlab.com/diffraction.htm

**Relevance to GSD:**
Practical implementation of baffle step compensation circuits. Linkwitz provides the shelf filter topology used to correct the +6 dB HF gain described by Olson (1951).

**Key Concepts:**

### Baffle Step Compensation Circuit
The baffle step phenomenon:
```
Low frequency (< f_step):   Speaker radiates into 4π space (reference level)
High frequency (> f_step):  Speaker radiates into 2π space (+6 dB gain)
```

To flatten the response, a shelving filter is needed:
```
Low frequency:   0 dB correction (unity gain)
High frequency:  -6 dB correction (compensate for 2π space gain)
```

### Linkwitz Shelf Filter Formula
First-order shelf filter approximation:
```python
# Transfer function magnitude
|H(f)| = sqrt( (1 + (f/f_step)²) / (1 + (f/(f_step/2))²) )

# At DC (f → 0):
#   |H(0)| = 1.0 (0 dB)

# At high frequency (f → ∞):
#   |H(∞)| = sqrt(1/4) = 0.5 (-6 dB)
```

**Implementation Notes:**
1. This is an **approximation** - smooth transition without diffraction ripples
2. For accurate physics simulation, use Olson/Stenzel models with ripples
3. This model is useful for:
   - Crossover design tools
   - Quick visualization
   - When exact baffle geometry is unknown

**Baffle Step Frequency:**
```
f_step = c / (2 * W)  (theoretical)
f_step ≈ 115 / W      (empirical approximation)
```
where W is the smallest baffle dimension in meters.

**Historical Note:**
The 1976 Linkwitz paper ("Active Crossover Networks for Noncoincident Drivers") focuses on crossover networks, not baffle step compensation. The baffle step compensation circuit is documented on Linkwitz's website (2003).

**See Also:**
- `literature/crossovers/olson_1951.md` - Physical baffle step phenomenon
- Linkwitz Lab website for implementation examples
