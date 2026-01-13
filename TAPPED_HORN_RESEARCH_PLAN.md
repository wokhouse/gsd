# Tapped Horn Research Plan - Front/Rear Path Combination

## Problem Statement

Current tapped horn implementation in `gsd/` produces results that don't match Hornresp:
- SPL too high at low frequencies (+14-16 dB error at 40-50 Hz)
- Excursion too low (-60-77% error)
- Impedance mismatch (-24-69% error)

**Root Cause Hypothesis**: Current model only accounts for **rear radiation path** (driver rear → tap → mouth). Missing **front radiation path** (driver front → tap → closed throat → reflection → mouth) with proper phase relationships.

## Research Objectives

### Primary Objective
Find the complete equations and methodology for calculating tapped horn system response that properly accounts for both front and rear radiation paths combining at the mouth.

### Secondary Objectives
1. Understand the reflection mechanism at closed throat (phase shift, amplitude)
2. Determine how to combine upstream and downstream path contributions at the mouth
3. Find validation methods or test cases to verify correctness
4. Identify any simplifying assumptions or approximations that can be made

## Key Questions to Answer

### 1. Berzborn & Smithers (2018) Model
- **What are the complete equations (10-16) for combining front and rear paths?**
- How do they calculate the pressure at the mouth from both paths?
- What is the phase relationship they use between front and rear radiation?
- Do they have a simplified equivalent circuit model?

### 2. Closed Throat Reflection
- **What is the reflection coefficient at a closed (rigid) throat?**
- Phase shift upon reflection: 0°, 180°, or frequency-dependent?
- How does the reflection propagate back through the upstream section to the tap point?
- Then from tap point to mouth (via downstream section)?

### 3. Path Combination at Mouth
- **How do the two path contributions combine at the mouth?**
- Simple addition? Vector sum with phase? Complex pressure addition?
- Are there any interference effects not captured by simple addition?
- How does this vary with frequency (especially near quarter-wave resonance)?

### 4. Hornresp Compatibility
- **Does Hornresp documentation or source code provide clues?**
- Any papers by David McBean (Hornresp author) on tapped horn modeling?
- Are there any validation examples comparing theory vs Hornresp?

### 5. Alternative Approaches
- **Can this be modeled as a 2-port network problem?**
- Use T-matrices for both paths and combine at mouth?
- Any transmission line models that handle this topology?
- Can we derive equivalent circuit from first principles?

## Literature to Investigate

### Primary Sources (Already have)
1. **Berzborn, M. & Smithers, M. (2018)** - AES Paper 10047
   - Need: Complete equations, not just Eq. 10-12

### Secondary Sources (Need to find)
1. **Danley (2013)** - US Patent 8,457,341 B2
   - Search for: Phase relationship, path combination, reflection handling

2. **Kolbrek** - Horn simulation papers
   - Any tapped horn specific content?
   - Multi-port network approach?

3. **Hornresp documentation/source**
   - Any technical notes on TH model implementation
   - Validation examples

4. **Academic papers on tapped horns**
   - Search terms: "tapped horn interference", "tapped horn phase",
     "quarter-wave resonance tapped horn", "front-rear combination"

## Search Strategy

### Search Terms
1. "Berzborn Smithers AES 10047 equation 13 14 15"
2. "tapped horn front rear radiation phase"
3. "tapped horn closed throat reflection"
4. "tapped horn quarter wave resonance"
5. "Hornresp tapped horn model validation"
6. "tapped horn interference pattern"
7. "tapped horn mouth pressure calculation"

### Databases
- Google Scholar
- AES E-Library
- IEEE Xplore
- Acoustical Society of America
- arXiv (physics.ao-ph)

## Success Criteria

Research is successful when we have:

1. **Complete equations** for calculating:
   - Upstream path contribution to mouth pressure
   - Downstream path contribution to mouth pressure
   - Phase relationship between the two paths
   - Combined mouth pressure as function of frequency

2. **Implementation guidance**:
   - Step-by-step algorithm
   - Required intermediate calculations
   - Any numerical considerations or pitfalls

3. **Validation approach**:
   - Test cases to verify correctness
   - Expected accuracy tolerances
   - Comparison with Hornresp methodology

## Deliverables

1. **Research Findings Document** (markdown)
   - Complete equations with citations
   - Explanation of physics
   - Implementation notes
   - Pseudocode or algorithm outline

2. **Implementation Instructions** (for Claude Code)
   - File modifications needed
   - Code changes (ready to apply)
   - Validation test cases
   - Expected results

## Timeline Considerations

This is a complex acoustic modeling problem that requires:
- Understanding wave propagation in multi-segment horns
- Phase relationships and interference
- Possibly deriving equations if not explicitly given in literature

**Estimated effort**: 2-4 hours of focused research + implementation work

## Risk Mitigation

### If Berzborn & Smithers equations are insufficient:
- Look for alternative papers on tapped horn modeling
- Consider deriving from first principles (Webster's horn equation)
- May need to implement simplified version and iterate

### If no complete model found:
- Implement best-known approximation
- Document limitations clearly
- Create validation plan for iterative improvement

## Repository Context

**Codebase**: `gsd` - Loudspeaker enclosure design and simulation tool
**Branch**: `feature/tapped-horn`
**Key files**:
- `src/gsd/simulation/tapped_horn_theory.py` - Current implementation
- `src/gsd/simulation/types.py` - TappedHorn dataclass
- `tests/validation/drivers/bc_15ps100/tapped_horn/` - Hornresp validation data

**Current state**: Infrastructure complete, but results don't match Hornresp due to missing front/rear path combination.
