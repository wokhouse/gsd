# Simulation Gaps and Known Limitations

This document tracks gaps in our physics simulation capabilities - areas where we don't have validated models yet.

## Critical Gap: Horn SPL/Frequency Response Calculation

### What We Have (✅ Validated)
- `exponential_horn_throat_impedance()` - Throat impedance validated against Hornresp
- `multisegment_horn_throat_impedance()` - Multi-segment horns validated
- Ported box SPL response - Validated against Hornresp
- Sealed box SPL response - Validated against Hornresp

### What We DON'T Have (❌ Missing)
- **Horn radiated SPL/frequency response** - Cannot calculate actual sound output from horn

### The Problem

Throat impedance ≠ Radiated SPL!

When we tried using:
```python
pressure ∝ 1/|Z_throat|
```

This gave **WRONG results**:
- Below cutoff: High throat impedance (reactive, imaginary)
- Our formula: High impedance → Low pressure calculation → **WRONG**
- Reality: High impedance = energy stored, not radiated = **NO output**

The correct relationship is:
- Throat impedance = Load seen by driver
- Radiated power = Real(resistive) part of mouth impedance
- SPL = f(radiated power, distance, directivity)

### Why This Matters

The CrossoverDesignAssistant currently uses UNVALIDATED approximations:
- Simplified -12 dB/octave high-pass filter
- Artificial resonances (Gaussian peaks)
- Datasheet sensitivity (not calculated from physics)

**This violates Rule #1 of CLAUDE.md!**

### Required Solution

We need to implement proper horn SPL calculation using:

1. **Throat impedance** (we have this ✅)
2. **Mouth radiation impedance** (we have this ✅)
3. **Power flow calculation** - Real power radiated from mouth
4. **SPL from radiated power** - At 1m distance, including directivity

Literature to research:
- Beranek (1954) - Horn efficiency and power radiation
- Olson (1947) - Horn throat pressure to mouth pressure transformation
- Klippel (2005) - Radiation impedance and power flow

### Interim Solution (Until Proper Implementation)

**DO NOT USE** CrossoverDesignAssistant for production designs without:
1. Validating final design with Hornresp
2. Measuring actual prototype
3. Clearly marking as "Approximation model - unvalidated"

### Implementation Priority

**HIGH PRIORITY** - This blocks accurate multi-way system design.

Estimated effort:
- Research literature: 2-4 hours
- Implementation: 4-8 hours
- Validation against Hornresp: 2-4 hours
- Total: 8-16 hours

## Other Known Gaps

### Directivity Patterns
- We don't have directivity simulation (off-axis response)
- Hornresp can do this
- Literature: Olson (1947), Beranek (1954)

### Horn Driver Integration
- `horn_driver_integration.py` exists but may need validation
- Need to verify against Hornresp's driver + horn models

### Non-Exponential Horns
- Hyperbolic, conical, tractrix horns need validation
- Only exponential horns are fully validated

## Template for Documenting New Gaps

When you discover a missing physics capability, add it here:

```markdown
### [Name of Gap]

**What We Have:**
- [Existing validated functions]

**What We Need:**
- [Missing physics calculation]

**Why It Matters:**
- [Impact on design/accuracy]

**Required Solution:**
- [Physics approach needed]
- [Literature references]

**Priority:** [HIGH/MEDIUM/LOW]
**Estimated Effort:** [hours]
```

## Keeping This Document Updated

When you encounter a physics simulation need:
1. Check if validated function exists in `src/gsd/simulation/`
2. If NO: Add gap to this document
3. DO NOT create unvalidated approximation (see CLAUDE.md Rule #1)
4. Either implement properly or use Hornresp directly
