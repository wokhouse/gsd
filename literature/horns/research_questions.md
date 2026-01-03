# Research Prompt: Horn Simulation Implementation for GSD

**Date:** 2025-12-27
**Context:** GSD is a Python CLI tool for loudspeaker enclosure design, with focus on horn-loaded enclosures. We validate all simulations against Hornresp (industry standard).

---

## RESEARCH OBJECTIVE

We need to implement horn simulation (exponential, hyperbolic, conical horns) and validate against Hornresp. Before writing code, we need to validate our assumptions about:

1. **Horn simulation approach**: Which acoustic model should we use? (transmission line vs. impedance transformation vs. T-matrix)
2. **Key parameters**: What inputs does Hornresp need for horn simulation? (throat area, mouth area, length, flare constant, etc.)
3. **Output validation**: What outputs should we compare? (throat impedance, frequency response, SPL, efficiency)
4. **Literature sources**: Which references provide implementable equations (not just theory)?

We want to avoid implementing the wrong model and having to rewrite it later.

---

## SUCCESS CRITERIA

A successful answer will provide:

1. **Recommended implementation approach** for exponential horn simulation
   - Specific equations (with formula notation, not just references)
   - Algorithm pseudocode or clear step-by-step procedure
   - Parameter definitions with units

2. **Hornresp parameter mapping**
   - What parameters Hornresp uses for horn definition
   - How to map our Python data structures to Hornresp inputs
   - Any hidden assumptions or empirical corrections Hornresp uses

3. **Validation methodology**
   - Which Hornresp outputs to compare (impedance, SPL, efficiency?)
   - Expected tolerance levels (1%, 5%, etc.)
   - Test cases we should create

4. **Literature with IMPLEMENTABLE equations**
   - Not just theory papers - we need equations we can translate to code
   - Sources that match Hornresp's approach (or explain differences)
   - Numerical methods if analytical solutions don't exist

---

## CONTEXT

**GSD Project Status:**
- Already implemented: Direct radiator simulation (sealed/ported boxes) with Hornresp validation
- Implemented: Driver parameters (Thiele-Small), radiation impedance, voice coil inductance (Leach model)
- Implemented: Hornresp export/import functionality
- Literature directory exists: `literature/horns/olson_1947.md`, `beranek_1954.md`, `kolbrek_horn_theory_tutorial.md`
- Validation framework exists with comparison functions

**Project Constraints:**
- All simulation code MUST cite literature (per project CLAUDE.md)
- Must validate against Hornresp (industry standard tool)
- Python-based, using scipy for Bessel/Struve functions, complex math
- Accuracy requirement: <1% deviation from Hornresp for well-behaved cases
- Cannot assume user has access to Hornresp - we must be able to generate test data

**GitHub Repository:**
https://github.com/wokhouse/gsd

Relevant code locations:
- `src/gsd/simulation/` - Simulation modules (need to add horn theory)
- `src/gsd/hornresp/export.py` - Export to Hornresp format
- `literature/horns/` - Acoustic theory references

---

## SPECIFIC QUESTIONS

### 1. Horn Simulation Approach

**Our current assumptions:**
- Use transmission line approach (Kinsler Eq. 9.6.4) for finite exponential horn
- Calculate throat impedance from mouth impedance using transmission line formula
- Account for flare constant m, throat area S_t, mouth area S_m, length L

**Questions to validate:**
- Is transmission line the right approach? Or should we use T-matrix (Kolbrek)?
- Does Hornresp use analytical solutions or numerical methods?
- Are there empirical corrections we need to match Hornresp?
- How does Hornresp handle mouth radiation impedance? (piston model? infinite baffle? free field?)

**What we need:**
- Clear recommendation with justification
- Equations ready to implement (with variable definitions)
- Comparison of different approaches if multiple exist

---

### 2. Exponential Horn Cutoff Frequency

**Our current understanding:**
- Olson Eq. 5.18: `f_c = c·m/(2π)` where m is flare constant
- Horn doesn't propagate efficiently below f_c (evanescent waves)
- This is well-established theory

**Questions to validate:**
- Does Hornresp use this exact formula? Any corrections?
- What is the valid frequency range for the equations? (f > f_c? f > 1.5×f_c?)
- How does cutoff frequency affect impedance calculations near f_c?
- Are there numerical issues near f_c we should handle?

**What we need:**
- Confirmation or correction of cutoff frequency formula
- Frequency range limitations for each equation
- Handling of evanescent wave region (f < f_c)

---

### 3. Throat Impedance Calculation

**Our current assumptions:**
- Start with mouth radiation impedance (Beranek Eq. 5.20 for circular piston)
- Transform back to throat using transmission line formula
- Account for varying cross-section S(x) = S_t · exp(m·x)
- Use characteristic impedance Z_0 = ρc/S(x)

**Questions to validate:**
- Is this the correct impedance transformation direction? (mouth → throat or throat → mouth?)
- What characteristic impedance should we use? (ρc/S(x)? something else?)
- How do we handle the complex impedance transformation through varying cross-section?
- Does Hornresp include corrections for: mouth diffraction, throat chamber, folding?

**What we need:**
- Step-by-step impedance calculation procedure
- Exact formulas with variable definitions
- Special cases or edge conditions to handle

---

### 4. Hornresp Parameter Mapping

**We understand Hornresp needs:**
- Throat area (Sd in Hornresp?) - area where driver connects to horn
- Mouth area (Sm) - final horn exit area
- Horn length (L12 or similar)
- Flare constant or throat/mouth area ratio
- Possibly: throat chamber volume, compression ratio

**Questions to validate:**
- What are the exact Hornresp input parameters for exponential horn?
- How does our driver parameter set (Thiele-Small) map to Hornresp inputs?
- Are there Hornresp-specific parameters we need to calculate?
- Does Hornresp assume infinite baffle at mouth? Free field? Something else?

**What we need:**
- Complete parameter mapping (gsd → Hornresp)
- Parameter definitions with units (m², m, etc.)
- Any constraints or relationships between parameters

---

### 5. Literature with Implementable Equations

**We have these literature sources:**
- Olson (1947) - Classic horn theory (exponential profiles, cutoff frequency)
- Beranek (1954) - Radiation impedance (piston in infinite baffle)
- Kinsler (1982) - Transmission line approach (Eq. 9.6.4)
- Kolbrek horn theory tutorial - T-matrix method, modern treatment

**Questions to validate:**
- Which source provides the most implementable approach? (ready-to-code equations)
- Are there modern sources that match Hornresp's implementation better?
- Do we need numerical methods (scipy.integrate)? Or are there analytical solutions?
- Which sources provide validation data or examples?

**What we need:**
- Specific literature recommendations with equation numbers
- Code snippets or pseudocode if available
- Warning about which sources are too theoretical (no implementable equations)

---

### 6. Validation Strategy

**Our current validation approach:**
- Create test cases with simple horn parameters
- Run Hornresp simulation with same parameters
- Compare throat impedance magnitude and phase vs frequency
- Compare SPL response if available
- Accept <1% deviation for f > 1.5×f_c, <5% near f_c

**Questions to validate:**
- Is this the right validation approach? Should we validate something else first?
- What frequency range should we test? (10 Hz to 20 kHz? specific bands?)
- How do we create Hornresp test data? (manual export? existing files?)
- What tolerance is realistic? (1% seems strict for acoustic simulation)
- Are there known discrepancies between theory and Hornresp we should document?

**What we need:**
- Recommended test cases (specific horn parameters)
- Step-by-step validation procedure
- Expected accuracy tolerances for different frequency ranges
- How to generate Hornresp reference data

---

## CONSTRAINTS

1. **Python-based solution** - We're implementing in Python, can use scipy, numpy, but not Matlab/Fortran
2. **Must cite literature** - Every equation needs a literature source (Olson, Beranek, Kinsler, etc.)
3. **Numerical accuracy is critical** - This drives physical horn designs, errors propagate
4. **Avoid over-engineering** - Start with exponential horn, validate, then extend to hyperbolic/conical
5. **Match Hornresp where possible** - If there are multiple approaches, prefer the one that matches Hornresp
6. **Handle edge cases** - Near cutoff, very small horns, very large horns

---

## DELIVERABLES

Please provide:

### Section 1: Research Findings (for human review)
- Theory explanation (keep it concise but complete)
- Recommended implementation approach with justification
- Equations with full notation (define every variable)
- Literature citations with equation numbers
- Implementation notes and caveats
- Validation methodology with expected tolerances

### Section 2: Implementation Instructions (for Claude Code)
Write this as a direct task specification for a future Claude Code instance, including:

**2.1 Functions to Implement**
- Function signatures (with exact parameter names and types)
- Docstring templates (with Literature sections pre-filled)
- Input validation requirements
- Return value specifications

**2.2 Implementation Steps**
- Step-by-step algorithm (pseudocode or numbered list)
- Which scipy functions to use (scipy.special.j1, scipy.fft, etc.)
- Numerical stability considerations (divide-by-zero, very small numbers, etc.)
- Test cases to validate each function

**2.3 Validation Approach**
- Hornresp export parameters for test cases
- Expected outputs (numerical values if possible)
- Frequency ranges to test
- Pass/fail criteria for validation tests

**2.4 File Structure**
- Which files to create (`src/gsd/simulation/horn_theory.py`?)
- Import structure
- How this integrates with existing codebase

---

## IMPORTANT NOTES

1. **We need EQUATIONS, not just references** - Please provide the actual formulas with LaTeX notation or clear text, not just "see Olson Eq. 5.18"

2. **Be specific about scipy usage** - If we need Bessel functions, tell us: `scipy.special.jv(0, x)` or `scipy.special.j1(x)`, not just "use Bessel functions"

3. **Warn about numerical issues** - If an equation has singularities or numerical problems, tell us upfront

4. **Prioritize matching Hornresp** - If theory and Hornresp disagree, explain why and recommend which to follow

5. **Start simple** - Recommend implementing exponential horn first, validate it, then extend to other profiles

---

**REMEMBER: You are writing to BOTH (1) human researchers AND (2) a future Claude Code instance. Structure your response with two clear sections.**
