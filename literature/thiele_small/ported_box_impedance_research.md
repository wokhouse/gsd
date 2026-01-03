# Research Agent Instructions: Ported Box Impedance Discrepancy

## Research Objective

Investigate why gsd's ported box electrical impedance calculation produces values that are exactly **50% of Hornresp's values** across all test cases, and determine the correct fix.

## Success Criteria

The research should find:
1. **The correct R_es (motional resistance) formula** from Small (1973) or Thiele (1971)
2. **Whether a factor of 2 is missing** in the impedance calculation
3. **The correct polynomial scaling factor** for Small's transfer function
4. **Any documented differences** between Small/Thiele theory and Hornresp's implementation
5. **Working code examples** or formulas that can be implemented

## Context

### Project Background
GSD is a Python CLI tool for loudspeaker enclosure design. We validate our simulations against Hornresp (the industry-standard tool). Our sealed box implementation validates correctly (<7% error), but ported box has systematic 50% error.

### Current Implementation

We're using **Small's (1973) 4th-order transfer function** for vented boxes:

```python
# Current (incorrect) implementation:
R_ms = omega_s * M_ms / Q_ms
R_es = (BL)² / R_ms  # Motional impedance
polynomial_ratio = (numerator / denominator) * (omega_s ** 2)
Z_e = R_e + R_es * polynomial_ratio
```

**Results:**
- Hornresp peak: 23.54 Ω @ 44.9 Hz
- GSD peak: 12.02 Ω @ 44.9 Hz
- Error: -49% (exactly 2x too low)

### What We've Tried

1. ✅ **Box damping fix** (Q_box = 15.0): Reduced error from 118% to 45%, but not enough
2. ✅ **Circuit model**: Even worse (950%+ error)
3. ❌ **Q_box tuning**: Tested values from 5 to 30, best result at Q_box = 10 (45% error)

### Key Numbers to Validate

**BC_8NDL51 Driver:**
- BL = 7.3 T·m
- M_ms = 0.0305 kg (with radiation mass)
- Q_ms = 5.43
- R_e = 2.6 Ω
- F_s = 75 Hz

**At first impedance peak (44.9 Hz):**
- Current R_es = 13.83 Ω
- Current polynomial_ratio magnitude = 0.6463
- Current Z_e = 2.6 + 13.83 × 0.6463 = 11.54 Ω
- **Target Z_e = 23.54 Ω**
- **Required R_es ≈ 32.4 Ω** (to match Hornresp)

**Missing factor:** 32.4 / 13.83 = **2.34×**

## Specific Questions for Research Agent

### 1. Small (1973) Paper Verification

**Find and verify the exact equations from Small's 1973 paper "Vented-Box Loudspeaker Systems Part I":**

- **Equation for R_es (motional resistance):**
  - Is it `R_es = (BL)² / R_ms` or `R_es = 2 × (BL)² / R_ms`?
  - What does Small say about the peak motional impedance value?
  - Are there any additional factors we're missing?

- **Voice coil impedance equation (Eq. 13, 14, or 16):**
  - Find the exact form of `Z_vc(s) = R_e + R_es × N(s) / D'(s)`
  - Is there a frequency-dependent scaling factor?
  - What is the exact form of the frequency scaling (ω_s²)?

- **Polynomial coefficients:**
  - Verify the a1, a2, a3, a4 coefficients in D'(s)
  - Check if (α+1) term is correct
  - Are we missing any factors in the coefficients?

### 2. Thiele (1971) Comparison

**Find Thiele's 1971 paper "Loudspeakers in Vented Boxes":**

- Compare Thiele's impedance formulas with Small's 1973 version
- Are there differences between Thiele and Small formulations?
- Does Thiele include any factors that Small doesn't?

### 3. Hornresp-Specific Information

**Search for Hornresp documentation or discussions:**

- Does Hornresp use Small's equations exactly, or modifications?
- Are there any undocumented corrections Hornresp applies?
- Search for "Hornresp vented box impedance formula" or similar

### 4. Alternative Formulations

**Look for other sources that implement vented box impedance:**

- Academic papers with worked examples
- Open source speaker simulation tools (e.g., Akabak, VituixCAD)
- Textbook examples with actual impedance calculations
- Forum discussions where people implemented Small's equations

### 5. Factor of 2 Explanation

**Specifically search for:**

- "Why is vented box impedance 2x higher than expected"
- "Small (1973) motional impedance factor"
- "R_es vented box doubling"
- "Thiele Small impedance scaling factor"
- Similar issues in other simulation tools

## What We Need

### Primary Deliverables

1. **Exact equations** from Small (1973) with equation numbers
2. **Explanation of the 2× discrepancy** - is it a known issue?
3. **Corrected formulas** we should implement
4. **Code examples** if available (Python, MATLAB, or pseudocode)
5. **Citations** for all sources

### Secondary Deliverables

1. **Comparison of different formulations** (Thiele vs Small vs others)
2. **Worked examples** with actual impedance values
3. **Discussion of any known errata** in the papers
4. **References to working implementations**

## Research Strategy

### Recommended Search Terms

```
"Small 1973 vented box impedance equation"
"Thiele 1971 vented box impedance formula"
"Small vented box R_es motional impedance"
"ported box electrical impedance derivation"
"Hornresp impedance calculation method"
"vented box transfer function impedance"
"Small Thiele vented box R_es"
"loudspeaker vented box impedance peak calculation"
```

### Recommended Sources

1. **Academic papers** (IEEE Xplore, AES E-library)
   - Small (1973) "Vented-Box Loudspeaker Systems Part I"
   - Thiele (1971) "Loudspeakers in Vented Boxes"

2. **Textbooks**
   - Beranek (1954) "Acoustics"
   - Kinsler et al. "Fundamentals of Acoustics"
   - Loudspeaker design handbooks

3. **Technical forums**
   - DIY Audio forum (diyaudio.com)
   - Home Theater Shack
   - Audioholics

4. **Open source projects**
   - Akabak source code
   - VituixCAD documentation
   - Other speaker simulation tools

## Technical Details to Include

When finding relevant information, include:

1. **Full equations** with all variables defined
2. **Equation numbers** from the original papers
3. **Worked examples** if available
4. **Variable definitions** (what is R_es, R_ms, M_ms, etc.)
5. **Units** for all quantities
6. **Any corrections or errata** to the equations

## Constraints

- Focus on **vented box (bass reflex)** enclosures, not sealed boxes
- The issue is specifically with **electrical impedance magnitude**
- We're using Small's transfer function approach, not simple analogies
- All calculations are at low frequency (<200 Hz), voice coil inductance is negligible

## Output Format

Please provide findings in a structured format:

```
## Finding 1: [Title]

**Source:** [Paper, book, forum, etc.]

**Equation:** [The actual equation]

**Explanation:** [What it means]

**Relevance:** [How this helps solve the 2× discrepancy]

## Finding 2: ...
...
```

## Critical Information Needed

Most importantly: **We need to find the exact formula for R_es and verify whether our implementation is correct.**

If you find that R_es should be doubled, or that there's a missing factor in the polynomial ratio, or that Small's equations have an errata - that would solve our problem.

---

**Generated:** 2025-12-27
**Project:** GSD
**Contact:** See GitHub repository for context
