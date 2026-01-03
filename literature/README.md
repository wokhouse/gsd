# Literature Library

This directory will contain the foundational references for the gsd simulation engine. All algorithms implemented in gsd must be derived from and cite the literature contained in this library.

## Status

**Literature references will be added during development.**

The literature citation framework is established, but specific reference documents have not yet been populated. As simulation features are implemented, relevant literature will be added following the structure below.

## Purpose

The literature library will serve as:
1. **Authoritative source** for all acoustic theory and equations implemented in gsd
2. **Reference documentation** linking code implementations to theoretical foundations
3. **Validation framework** ensuring the simulation engine is grounded in established science
4. **Educational resource** for understanding the acoustic principles behind horn design

## Planned Structure

### `horns/` - Horn Theory References
Foundational texts on horn-loaded loudspeaker design:
- Exponential and hyperbolic horn profiles
- Acoustic impedance calculations
- Throat and mouth area requirements
- Directivity patterns
- Horn equation derivations

**Planned key references:**
- Olson (1947) - Elements of Acoustical Engineering
- Beranek (1954) - Acoustics
- Kinsler et al. (1982) - Fundamentals of Acoustics

### `thiele_small/` - Thiele-Small Parameters
Driver parameters and small-signal modeling:
- Thiele (1971) - Loudspeaker enclosure calculations
- Small (1972) - Direct radiator loudspeaker analysis
- Equivalent circuit models
- Parameter measurement techniques

### `transmission_lines/` - Transmission Line Theory
Quarter-wave and transmission line enclosures (future development):
- Transmission line acoustic theory
- Tapered line designs
- Absorptive loading techniques

### `simulation_methods/` - Numerical Methods
Implementation techniques:
- Electrical analogies for acoustic systems
- Numerical solution methods
- Frequency response calculations
- Optimization algorithms

## Adding New Literature

When adding new references:

1. Create a new markdown file in the appropriate directory
2. Include:
   - Full citation (authors, title, publication, year)
   - DOI or ISBN if available
   - Key equations with numbering
   - Relevant page numbers
   - Summary of applicable theory
3. Update this README with the new reference
4. Link to the reference from any code that uses it

## Validation Against Hornresp

Hornresp is the industry-standard tool for horn simulation. All gsd implementations must:
1. Implement the theory as described in literature/
2. Validate results against Hornresp for test cases
3. Document any discrepancies and their causes
4. Maintain agreement within acceptable tolerances (typically <1% for key parameters)

This ensures gsd provides accurate exploration results while being grounded in established acoustic theory.
