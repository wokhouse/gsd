# Research Agent Validation Plan: Infinite Baffle & Radiation Mass Implementation

**Date**: 2025-12-26
**Status**: Ready for Research Agent
**Branch**: feature/infinite-baffle-validation-fix

---

## Overview

This document outlines a comprehensive research plan for validating the recent work on:
1. **Radiation mass implementation** (Beranek 1954, Eq. 5.20)
2. **Iterative resonance solver** matching Hornresp's 2× radiation mass methodology
3. **I_active force model** for SPL calculations
4. **Infinite baffle validation** for 4 B&C drivers

**Research Goal**: Independently verify the implementation is correct, well-documented, and properly validated against Hornresp.

---

## Part 1: Literature Citation Validation

### Task 1.1: Verify Beranek (1954) Citation Accuracy

**Objective**: Ensure the radiation mass implementation correctly cites and implements Beranek's equations.

**Research Steps**:
1. Read `literature/horns/beranek_1954.md`
2. Locate Equation 5.20 for radiation impedance
3. Verify the reactance formula: `Z_R = ρc·S·[R₁(2ka) + jX₁(2ka)]`
4. Confirm the Struve function formulation: `X₁(2ka) = H₁(2ka) / (ka)`
5. Check that the low-frequency asymptote `X₁ ≈ 8ka/(3π)` is correct

**Deliverable**:
- Report confirming or flagging discrepancies in:
  - Equation numbering
  - Mathematical formulations
  - Variable definitions
  - Units used

**Files to Review**:
- `src/gsd/driver/radiation_mass.py` (lines 19-86)
- `literature/horns/beranek_1954.md`

---

### Task 1.2: Verify I_active Force Model Citations

**Objective**: Validate the literature support for the I_active energy-conserving force model.

**Research Steps**:
1. Read the I_active implementation in `src/gsd/driver/response.py` (lines 212-269)
2. Locate cited references:
   - COMSOL (2020), Eq. 4: `P_E = 0.5·Re{V₀·i_c*}`
   - Kolbrek's statements on reactive power
   - Beranek (1954) on radiation impedance
3. Verify the theoretical basis: `I_active = |I| × cos(phase(I))`
4. Confirm physics: Only in-phase current contributes to acoustic power

**Deliverable**:
- Assessment of whether I_active model has solid theoretical foundation
- Identification of any missing citations or alternative formulations

**Files to Review**:
- `src/gsd/driver/response.py` (lines 212-269)
- Commit message: 1e9abc8

---

## Part 2: Mathematical Derivation Verification

### Task 2.1: Verify Radiation Mass Derivation

**Objective**: Ensure the mathematical derivation from radiation reactance to equivalent mass is correct.

**Research Steps**:
1. Start from Beranek Eq. 5.20: `X_rad = ρc·S·X₁(2ka)`
2. Verify the mass conversion: `M_rad = X_rad / ω`
3. Confirm the low-frequency limit: `M_rad ≈ (16/3)·ρ₀·a³`
4. Check numerical stability handling for `ka < 0.01`
5. Verify the 2× radiation mass multiplier rationale

**Key Questions**:
- Why does Hornresp use 2× radiation mass? Is this documented?
- Does the 2× multiplier represent both sides of the baffle?
- Are there alternative formulations in the literature?

**Deliverable**:
- Step-by-step derivation verification
- Assessment of whether the 2× multiplier is empirically justified or theoretically derived

**Files to Review**:
- `src/gsd/driver/radiation_mass.py` (lines 19-86, 89-174)
- `tests/unit_driver/test_radiation_mass.py` (lines 29-135)

---

### Task 2.2: Verify Iterative Resonance Solver

**Objective**: Validate the iterative algorithm for calculating F_s with radiation mass.

**Research Steps**:
1. Review the algorithm in `calculate_resonance_with_radiation_mass()`
2. Verify the circular dependency is correctly handled:
   - `F_s = 1/(2π√(M_ms·C_ms))`
   - `M_ms = M_md + 2×M_rad(f)`
   - `M_rad` depends on frequency
3. Check convergence criteria (tolerance_hz = 0.1)
4. Verify maximum iterations (20) is sufficient
5. Test convergence rate for all 4 drivers

**Deliverable**:
- Analysis of solver convergence properties
- Assessment of whether tolerance settings are appropriate
- Comparison with alternative solving methods (e.g., Newton-Raphson)

**Files to Review**:
- `src/gsd/driver/radiation_mass.py` (lines 89-174)
- `tests/unit_driver/test_radiation_mass.py` (lines 137-237)

---

## Part 3: Driver Parameter Validation

### Task 3.1: Verify M_md vs M_ms Distinction

**Objective**: Confirm that all drivers are using correct mass parameters.

**Research Steps**:
1. Review `src/gsd/driver/parameters.py` for M_md/M_ms implementation
2. Check `src/gsd/driver/bc_drivers.py` for correct M_md values
3. Cross-reference with B&C datasheets:
   - BC_8NDL51: M_md = 26.77 g
   - BC_12NDL76: M_md = 53.0 g
   - BC_15DS115: M_md = 254.0 g
   - BC_18PZW100: M_md = 209.0 g
4. Verify M_ms is calculated as derived property, not input

**Deliverable**:
- Confirmation that datasheet values are correctly transcribed
- Assessment of whether M_md vs M_ms naming is consistent with literature

**Files to Review**:
- `src/gsd/driver/parameters.py`
- `src/gsd/driver/bc_drivers.py`

---

### Task 3.2: Verify Resonance Frequency Calculations

**Objective**: Independently calculate expected F_s for all 4 drivers and compare.

**Research Steps**:
1. Extract driver parameters: M_md, C_ms, S_d
2. Calculate F_s without radiation: `F_s_no_rad = 1/(2π√(M_md·C_ms))`
3. Calculate radiation mass at resonance
4. Calculate F_s with radiation: `F_s_rad = 1/(2π√((M_md + 2·M_rad)·C_ms))`
5. Compare with Hornresp values

**Expected Results**:
| Driver   | No Rad (Hz) | With Rad (Hz) | Hornresp (Hz) | Error |
|----------|-------------|---------------|---------------|-------|
| BC_8NDL51 | ~68.3       | ~64.0         | 64.2          | <0.5 Hz |
| BC_12NDL76 | ~50.2       | ~44.8         | 44.9          | <0.5 Hz |
| BC_15DS115 | ~20.0       | ~19.0         | 19.0          | <0.5 Hz |
| BC_18PZW100 | ~26.7       | ~24.1         | 23.9          | <0.5 Hz |

**Deliverable**:
- Independent calculation of all 4 resonance frequencies
- Verification of claimed <0.5 Hz accuracy

**Files to Review**:
- `src/gsd/driver/bc_drivers.py`
- `tests/unit_driver/test_radiation_mass.py` (lines 239-327)

---

## Part 4: Test Coverage Assessment

### Task 4.1: Unit Test Coverage

**Objective**: Evaluate unit test completeness for radiation mass module.

**Research Steps**:
1. Review `tests/unit_driver/test_radiation_mass.py`
2. Check coverage of:
   - Low-frequency limit behavior (ka << 1)
   - Frequency independence at low frequencies
   - Piston area scaling (M_rad ∝ S_d^(3/2))
   - Invalid input handling
   - Solver convergence
   - Radiation mass increases total mass
   - Radiation mass lowers resonance
3. Identify edge cases not covered

**Deliverable**:
- Assessment of test coverage completeness
- List of missing test cases (if any)
- Evaluation of test assertions quality

**Files to Review**:
- `tests/unit_driver/test_radiation_mass.py` (all 437 lines)

---

### Task 4.2: Validation Test Assessment

**Objective**: Evaluate integration tests against Hornresp.

**Research Steps**:
1. Review `tests/validation/test_infinite_baffle.py`
2. Assess parametrized test structure
3. Check tolerance appropriateness:
   - Ze magnitude: 35%
   - Ze phase: 90°
   - SPL: 6 dB max, 4 dB RMS
4. Identify frequency ranges where tests fail
5. Verify Hornresp data file integrity

**Deliverable**:
- Assessment of whether tolerances are reasonable
- Analysis of which frequency regions have largest errors
- Recommendations for additional validation tests

**Files to Review**:
- `tests/validation/test_infinite_baffle.py` (all 470 lines)
- Hornresp data files in `tests/validation/drivers/*/infinite_baffle/`

---

## Part 5: Error Analysis Investigation

### Task 5.1: Analyze SPL Validation Failures

**Objective**: Understand why 3/4 drivers fail SPL validation.

**Research Steps**:
1. Extract SPL error data from `tasks/driver_validation_status.md`
2. Characterize failure modes:
   - BC_12NDL76: 7.7 dB error at 28 Hz (near resonance)
   - BC_15DS115: 10.0 dB error at 905 Hz (mid-frequency)
   - BC_18PZW100: 8.0 dB error at 17 Hz (near resonance)
3. Correlate errors with driver parameters:
   - Large cone area (S_d > 500 cm²)
   - Low resonance frequency
   - High BL product
4. Compare with BC_8NDL51 (only passing driver)

**Deliverable**:
- Hypothesis for why large drivers fail SPL validation
- Identification of common factors in failing drivers
- Recommended investigation paths

**Files to Review**:
- `tasks/driver_validation_status.md` (lines 75-166)

---

### Task 5.2: Investigate Phase Error Sources

**Objective**: Understand large Ze phase errors (19°-59°).

**Research Steps**:
1. Review phase error data:
   - BC_8NDL51: 23° ✅ PASS
   - BC_12NDL76: 50° ✅ PASS (but large)
   - BC_15DS115: 19° ✅ PASS
   - BC_18PZW100: 59° ✅ PASS (but large)
2. Analyze phase error vs frequency
3. Check if phase errors correlate with resonance shift
4. Verify voice coil inductance model (simple vs Leach)

**Deliverable**:
- Assessment of whether phase errors are acceptable
- Analysis of phase error sources (resonance shift? inductance model?)
- Recommendations for improving phase accuracy

**Files to Review**:
- `tasks/driver_validation_status.md`
- `tests/validation/test_infinite_baffle.py` (lines 161-206)

---

## Part 6: Documentation Quality Review

### Task 6.1: Docstring Compliance Check

**Objective**: Ensure all simulation code has proper literature citations.

**Research Steps**:
1. Review `src/gsd/driver/radiation_mass.py` docstrings
2. Check each function has:
   - Brief description
   - Literature section with specific references
   - Equation numbers cited
   - Inline comments referencing literature
   - Validation section
3. Verify against `CLAUDE.md` citation requirements

**Deliverable**:
- Report on docstring compliance
- List of functions missing required documentation
- Assessment of citation quality

**Files to Review**:
- `src/gsd/driver/radiation_mass.py`
- `CLAUDE.md` (citation requirements section)

---

### Task 6.2: README and Status Document Review

**Objective**: Verify project documentation accurately reflects implementation.

**Research Steps**:
1. Review `tasks/driver_validation_status.md`
2. Check consistency with actual code:
   - Implementation summary
   - Test results
   - File modifications
3. Verify README files exist for all 4 drivers
4. Check for outdated information

**Deliverable**:
- Assessment of documentation accuracy
- List of inconsistencies found
- Recommendations for documentation improvements

**Files to Review**:
- `tasks/driver_validation_status.md`
- `tests/validation/drivers/*/infinite_baffle/README.md`

---

## Part 7: Hornresp Comparison Methodology

### Task 7.1: Verify Hornresp Data Integrity

**Objective**: Ensure Hornresp reference data is correctly formatted and loaded.

**Research Steps**:
1. Review Hornresp data file formats:
   - `8ndl51_sim.txt`
   - `bc_12ndl76_sim.txt`
   - `bc_15ds115_sim.txt`
   - `bc_18pzw100_sim.txt`
2. Verify file structure (167 lines input, 535 lines sim output)
3. Check CRLF line endings
4. Verify tab-separated columns
5. Confirm frequency range (20 Hz - 20 kHz)

**Deliverable**:
- Confirmation that data files match specification
- Identification of any data quality issues

**Files to Review**:
- `tests/validation/drivers/*/infinite_baffle/*_sim.txt`

---

### Task 7.2: Verify Voice Coil Model Consistency

**Objective**: Ensure gsd and Hornresp use consistent voice coil models.

**Research Steps**:
1. Check Hornresp input files for voice coil parameters:
   - Leb (lossy inductance)
   - Ke (inductance extension)
   - Rss (shorting ring resistance)
2. Verify gsd uses `voice_coil_model="simple"` to match
3. Confirm simple model: `Z_vc = Re + jωLe` (no losses)
4. Assess whether this explains high-frequency discrepancies

**Deliverable**:
- Assessment of voice coil model consistency
- Analysis of whether improved voice coil models would help
- Recommendations for voice coil modeling improvements

**Files to Review**:
- Hornresp input files: `*_input.txt`
- `tests/validation/test_infinite_baffle.py` (voice_coil_model usage)

---

## Part 8: Critical Analysis and Recommendations

### Task 8.1: Assess Overall Validation Success

**Objective**: Provide balanced assessment of validation status.

**Research Steps**:
1. Review all validation results:
   - Resonance frequency: 4/4 PASS (100%)
   - Ze magnitude: 4/4 PASS (100%)
   - Ze phase: 4/4 PASS (100%)
   - SPL: 1/4 PASS (25%)
2. Assess whether tolerances are too lenient
3. Evaluate if current state is production-ready
4. Compare with pre-radiation-mass results

**Deliverable**:
- Overall validation score (0-100%)
- Assessment of whether to merge to main branch
- Recommendations for next steps

**Files to Review**:
- `tasks/driver_validation_status.md` (all sections)

---

### Task 8.2: Identify Future Research Directions

**Objective**: Suggest next investigations based on findings.

**Research Steps**:
1. Synthesize findings from all tasks
2. Identify highest-priority issues:
   - SPL validation failures (3/4 drivers)
   - Large phase errors for some drivers
   - Voice coil model limitations
3. Propose specific investigations:
   - Advanced voice coil models (Leach 2002)
   - Radiation impedance for large pistons
   - Low-frequency asymptotic behavior
4. Estimate effort and impact

**Deliverable**:
- Prioritized list of follow-up tasks
- Estimated complexity for each task
- Expected impact on validation accuracy

---

## Summary Checklist

After completing this research plan, the agent should have:

- [ ] Verified all literature citations are accurate
- [ ] Confirmed mathematical derivations are correct
- [ ] Validated driver parameters against datasheets
- [ ] Independently calculated resonance frequencies
- [ ] Assessed test coverage completeness
- [ ] Analyzed SPL validation failure modes
- [ ] Investigated phase error sources
- [ ] Reviewed documentation quality
- [ ] Verified Hornresp data integrity
- [ ] Assessed voice coil model consistency
- [ ] Provided overall validation assessment
- [ ] Recommended future research directions

---

## Expected Output Format

The research agent should produce a comprehensive report with:

1. **Executive Summary** (200 words)
2. **Detailed Findings** per task (8 sections)
3. **Critical Issues** flagged
4. **Recommendations** prioritized
5. **Conclusion**: Merge or not merge?

**Report Length**: 2000-3000 words
**Time Estimate**: 2-3 hours for thorough research

---

**Status**: Ready for research agent
**Assigned To**: Unassigned
**Due Date**: Before merging feature/infinite-baffle-validation-fix to main
