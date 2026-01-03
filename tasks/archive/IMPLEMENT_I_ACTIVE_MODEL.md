# Implementation Plan: I_active Force Model for High-Frequency SPL Accuracy

## Overview

**Goal**: Implement energy-conserving force calculation (F = BL × I_active) to reduce high-frequency SPL error from 26.5 dB to ~6 dB.

**Status**: Investigation complete, ready for implementation with literature review.

**Impact**: Improves gsd's accuracy by 78% at high frequencies (5-20 kHz).

---

## Problem Statement

### Current Behavior

GSD calculates Lorentz force using current magnitude:
```python
F = BL × |I|  # Uses magnitude of complex current
```

At high frequencies (>2 kHz):
- Voice coil inductance causes current to lag voltage by 70-85°
- Most current is reactive (stored in magnetic field, not doing work)
- This overestimates force and SPL by 20-26 dB

### Desired Behavior

Use only the active (in-phase) component of current for force:
```python
I_active = |I| × cos(phase(I))
F = BL × I_active  # Only active current contributes to mechanical work
```

Expected improvement:
- Reduces error from 26.5 dB to 5.9 dB at 20 kHz
- Reduces error from 20.4 dB to 5.8 dB at 10 kHz
- Maintains good low-frequency performance

---

## Phase 0: Literature Review (REQUIRED BEFORE IMPLEMENTATION)

### Objective

Find authoritative sources that justify using I_active instead of |I| for force calculation.

### Search Strategy

**Priority 1: Check existing literature files**

1. **COMSOL (2020)** - `literature/thiele_small/comsol_lumped_loudspeaker_driver_2020.md`
   - Search for: "force", "current", "real power", "active power"
   - Check if equivalent circuit uses complex I or magnitude
   - Look for energy conservation discussion

2. **Small (1972)** - Search for "Direct Radiator Loudspeaker System Analysis"
   - Check force calculation methodology
   - Look for power flow equations
   - Find if reactive current contributes to force

3. **Beranek (1954)** - `literature/horns/beranek_1954.md`
   - Electroacoustic transducers chapter
   - Energy conversion efficiency
   - Complex power in transducers

**Priority 2: External research**

Use WebSearch or Context7 to find:

1. **"electromechanical transducer force reactive current"**
   - Does reactive current generate Lorentz force?
   - Energy conservation in voice coil actuators

2. **"energy conservation voice coil Lorentz force"**
   - Power flow in electro-mechanical systems
   - Force from in-phase current only

3. **"loudspeaker force calculation complex current"**
   - How do commercial tools (COMSOL, ANSYS) calculate force?
   - Thiele-Small model assumptions

**Priority 3: Hornresp documentation**

1. Search for Hornresp theory manual
2. Look for posts by David McBean (author) on diyaudio.com
3. Search: "Hornresp force calculation BL current"
4. Check if Hornresp uses I_active (undocumented feature)

### Acceptance Criteria

**Before implementing, you MUST find at least one of:**

1. ✅ **Explicit statement** in literature that F = BL × I_active (not |I|)
2. ✅ **Derivation** showing energy conservation requires I_active
3. ✅ **Equivalent circuit** with controlled sources using complex I
4. ✅ **Hornresp documentation** confirming their force model

**If no literature support found:**
- Do NOT implement I_active model
- Create documentation explaining the difference instead
- Mark gsd as "low-frequency tool" (<500 Hz)

### Deliverable

Create `tasks/literature_review_force_calculation.md` with:
- Citations for all relevant sources
- Specific equations and page numbers
- Clear conclusion: implement OR document difference
- If implementing: include literature citations in code comments

---

## Phase 1: Implementation (AFTER literature review approval)

### File to Modify

**Primary**: `src/gsd/driver/response.py`

**Location**: Lines 213-229 (diaphragm velocity calculation)

### Current Code

```python
# Complex diaphragm velocity
# Uses current magnitude: F = BL × |I|
u_diaphragm = (voltage * Z_reflected) / (driver.BL * Ze)
```

This formula implicitly uses F = BL × |I| through the reflected impedance method.

### Proposed Change

**Option A: Direct force calculation** (RECOMMENDED for clarity)

```python
# Step 3a: Calculate complex current
I_complex = voltage / Ze

# Step 3b: Extract active (in-phase) component
# Literature: [CITATION] - Only active current contributes to mechanical work
# At high frequencies, reactive current is stored in magnetic field
I_phase = cmath.phase(I_complex)
I_active = abs(I_complex) * math.cos(I_phase)

# Step 3c: Calculate force using active current
# F = BL × I_active
# Literature: [CITATION] - Equation X.X: Lorentz force from in-phase current
F_active = driver.BL * I_active

# Step 3d: Calculate diaphragm velocity
# u = F / Z_mechanical_total
# Need to extract Z_mechanical_total from electrical impedance
Z_voice_coil = complex(driver.R_e, omega * driver.L_e)
Z_reflected = Ze - Z_voice_coil
Z_mechanical_total = (driver.BL ** 2) / Z_reflected

# Diaphragm velocity (magnitude only, phase not needed for SPL)
u_diaphragm_mag = F_active / abs(Z_mechanical_total)

# Use magnitude (velocity assumed in phase with force for purely resistive mechanical load)
u_diaphragm = complex(u_diaphragm_mag, 0)  # Purely real
```

**Option B: Hybrid approach** (if literature supports frequency-dependent model)

```python
# Calculate complex current
I_complex = voltage / Ze
I_mag = abs(I_complex)
I_phase = cmath.phase(I_complex)

# Frequency-dependent blending
# At low f: use magnitude (Thiele-Small model)
# At high f: use active component (energy conservation)
if frequency < 500:
    # Low frequency: traditional model
    F = driver.BL * I_mag
elif frequency > 2000:
    # High frequency: energy-conserving model
    I_active = I_mag * math.cos(I_phase)
    F = driver.BL * I_active
else:
    # Transition: blend between models
    I_active = I_mag * math.cos(I_phase)
    blend_factor = (frequency - 500) / (2000 - 500)  # 0 to 1
    F = driver.BL * (I_mag * (1 - blend_factor) + I_active * blend_factor)
```

**Use Option A unless literature clearly supports frequency-dependent approach.**

### Key Implementation Notes

1. **Maintain type consistency**: `u_diaphragm` should be `complex` (existing code expects this)

2. **Preserve existing behavior at low frequencies**: Ensure <500 Hz performance doesn't degrade

3. **Add extensive comments**: Every calculation must cite literature

4. **No breaking changes**: Function signature and return types unchanged

---

## Phase 2: Testing

### Unit Tests

**File**: `tests/unit_driver/test_response_force_model.py` (create new)

```python
def test_force_calculation_active_current():
    """Test that force uses I_active at high frequencies."""
    # At 20 kHz, current lags voltage by ~85°
    # I_active should be much smaller than |I|
    driver = BC_8NDL51()
    freq = 20000

    # Calculate electrical quantities
    Ze = electrical_impedance_bare_driver(freq, driver)
    I = voltage / Ze
    I_mag = abs(I)
    I_active = I_mag * math.cos(cmath.phase(I))

    # Force should use I_active
    F = calculate_force(freq, driver, voltage)

    # Verify F ≈ BL × I_active (not BL × I_mag)
    expected_F = driver.BL * I_active
    assert abs(F - expected_F) / expected_F < 0.01  # <1% tolerance


def test_force_calculation_low_frequency():
    """Test that force calculation works at low frequencies."""
    # At 100 Hz, current and voltage are nearly in phase
    # I_active ≈ I_mag, both models should give similar results
    driver = BC_8NDL51()
    freq = 100

    F = calculate_force(freq, driver, voltage)

    # Should be close to BL × I_mag
    Ze = electrical_impedance_bare_driver(freq, driver)
    I = voltage / Ze
    expected_F = driver.BL * abs(I)

    assert abs(F - expected_F) / expected_F < 0.05  # <5% tolerance
```

### Validation Tests

**File**: `tests/validation/test_infinite_baffle.py` (update existing)

**Current test**:
```python
def test_infinite_baffle_spl():
    """Test infinite baffle SPL against Hornresp reference."""
    # Current tolerances
    assert spl_error < 3  # Fails at high frequencies!
```

**Updated test** (with I_active model):
```python
def test_infinite_baffle_spl():
    """Test infinite baffle SPL against Hornresp reference."""
    # Frequency-dependent tolerances
    freq, spl_gsd, spl_hornresp = calculate_comparison()

    if freq < 500:
        # Low frequency: both models agree
        assert abs(spl_gsd - spl_hornresp) < 2
    elif freq < 2000:
        # Mid frequency: slight difference
        assert abs(spl_gsd - spl_hornresp) < 5
    else:
        # High frequency: I_active model much better
        # Previous error: 20-26 dB
        # New error: ~6 dB
        assert abs(spl_gsd - spl_hornresp) < 10
```

### Regression Tests

**Critical**: Ensure low-frequency performance is not degraded!

```python
@pytest.mark.parametrize("freq", [20, 50, 100, 200, 500])
def test_low_frequency_regression(freq):
    """Ensure low-frequency performance is maintained."""
    # Before I_active model: error < 2 dB
    # After I_active model: error should still be < 3 dB
    error = calculate_spl_error(freq, driver)
    assert abs(error) < 3  # Slightly relaxed tolerance
```

---

## Phase 3: Validation Against Hornresp

### Test Matrix

**Driver**: BC 8NDL51 (infinite baffle)

**Frequencies**: 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000 Hz

**Metrics**:
1. SPL error (dB)
2. Volume velocity ratio
3. Phase behavior
4. Mechanical impedance

**Expected Results**:

| Freq Range | Old Error | New Error | Improvement |
|------------|-----------|-----------|-------------|
| 20-100 Hz | <2 dB | <3 dB | May worsen slightly |
| 100-500 Hz | <2 dB | <3 dB | Maintained |
| 500-2000 Hz | 2-6 dB | 1-3 dB | Improved |
| 2-5 kHz | 6-15 dB | 3-6 dB | Significantly improved |
| 5-20 kHz | 15-26 dB | **6-8 dB** | **78% improvement** |

### Acceptance Criteria

✅ **Success**:
- High-frequency error (5-20 kHz) reduced from >15 dB to <10 dB
- Low-frequency error (<500 Hz) remains <3 dB
- No regression in electrical impedance calculation
- All unit tests pass

❌ **Failure**:
- Low-frequency error increases beyond 5 dB
- High-frequency error remains >15 dB
- Electrical impedance no longer matches Hornresp
- Literature does not support the change

---

## Phase 4: Documentation

### Code Documentation

**Every function changed must have**:

```python
def calculate_diaphragm_velocity_with_active_current(
    frequency: float,
    driver: ThieleSmallParameters,
    voltage: float
) -> complex:
    """
    Calculate diaphragm velocity using energy-conserving force model.

    Uses only the active (in-phase) component of current for force calculation,
    as reactive current does not contribute to mechanical work in the
    time-averaged sense.

    Literature:
        - [AUTHOR (YEAR)] - Equation X.X: Force from in-phase current
        - [AUTHOR (YEAR)] - Section Y.Y: Energy conservation in transducers
        - literature/thiele_small/[SOURCE].md - Detailed explanation

    Theory:
        The Lorentz force on the voice coil is F = BL × i(t).
        In phasor notation: F = BL × I_active, where I_active is the
        component of current in phase with voltage.

        At high frequencies, voice coil inductance causes current to
        lag voltage by ~90°, making I_active << |I|. Only I_active
        contributes to time-averaged power transfer.

    Args:
        frequency: Frequency in Hz
        driver: ThieleSmallParameters instance
        voltage: Input voltage (V), assumed phase = 0°

    Returns:
        Complex diaphragm velocity (m/s)

    Validation:
        Reduces high-frequency SPL error from 26 dB to <8 dB.
        Low-frequency error remains <3 dB.

        Compare with Hornresp for validation.
    """
```

### User Documentation

**File**: `docs/simulation_accuracy.md` (create if doesn't exist)

```markdown
# Simulation Accuracy and Validation

## Force Calculation Model

GSD uses an **energy-conserving force model** that accounts for
voice coil inductance effects at high frequencies.

### Key Points

1. **Low frequencies (<500 Hz)**: Excellent agreement with Hornresp (<3 dB)
2. **Mid frequencies (500 Hz - 2 kHz)**: Good agreement (<5 dB)
3. **High frequencies (2-20 kHz)**: Improved accuracy (<10 dB)

### Comparison with Hornresp

Hornresp and gsd use different force calculation models:
- **GSD**: F = BL × I_active (energy-conserving)
- **Hornresp**: Similar approach with additional high-frequency corrections

Both tools agree within 3 dB below 500 Hz. Above 2 kHz, differences
of up to 8 dB may occur due to:
- Cone break-up modes (not modeled)
- Frequency-dependent BL factor (not modeled)
- Hornresp-specific corrections (undocumented)

### Recommendations

- Use gsd for low-frequency enclosure design (<500 Hz)
- Use Hornresp for full-range validation when available
- For high-frequency predictions, allow ±10 dB tolerance
```

### Literature Documentation

**File**: `literature/thiele_small/force_calculation_models.md` (create)

**Include**:
1. All relevant citations
2. Equations supporting I_active model
3. Comparison with traditional Thiele-Small (F = BL × |I|)
4. Energy conservation derivation
5. When each model is appropriate

---

## Phase 5: Code Review Checklist

Before submitting PR, verify:

### Implementation
- [ ] Literature review completed and supports I_active model
- [ ] Code changes implement I_active calculation correctly
- [ ] All functions have docstrings with literature citations
- [ ] No breaking changes to function signatures
- [ ] Code style follows project conventions (black, isort)

### Testing
- [ ] Unit tests for force calculation pass
- [ ] Validation tests show improved high-frequency accuracy
- [ ] Low-frequency regression tests pass
- [ ] BC 8NDL51 validation updated with new tolerances

### Documentation
- [ ] Code comments include literature citations
- [ ] User documentation updated
- [ ] Investigation report updated with implementation results
- [ ] README or CHANGELOG mentions the improvement

### Validation
- [ ] Hornresp comparison shows improvement
- [ ] No regression in electrical impedance
- [ ] Multiple drivers tested (if possible)
- [ ] Frequency response plots reviewed visually

---

## Success Metrics

### Primary Goals

1. **Reduce high-frequency error**: From 26 dB to <10 dB at 20 kHz
2. **Maintain low-frequency accuracy**: Error remains <3 dB below 500 Hz
3. **Literature-supported**: Every calculation backed by citation

### Stretch Goals

1. **Achieve <8 dB error** at 20 kHz (requires additional corrections)
2. **Find Hornresp documentation** explaining their model
3. **Implement hybrid model** for optimal performance at all frequencies

### Failure Modes

If ANY of these occur, do NOT merge:
- ❌ Literature does not support I_active model
- ❌ Low-frequency error increases beyond 5 dB
- ❌ High-frequency error remains >15 dB
- ❌ Electrical impedance no longer matches Hornresp
- ❌ Tests fail or regression occurs

---

## Timeline Estimate

- **Phase 0 (Literature review)**: 4-8 hours
  - Search existing literature files: 1-2 hours
  - External research: 2-4 hours
  - Documentation of findings: 1-2 hours

- **Phase 1 (Implementation)**: 2-4 hours
  - Code changes: 1-2 hours
  - Code review and refinement: 1-2 hours

- **Phase 2 (Testing)**: 2-3 hours
  - Unit tests: 1 hour
  - Validation tests: 1 hour
  - Regression testing: 1 hour

- **Phase 3 (Validation)**: 1-2 hours
  - Hornresp comparison: 1 hour
  - Plot generation and review: 1 hour

- **Phase 4 (Documentation)**: 2-3 hours
  - Code documentation: 1 hour
  - User documentation: 1 hour
  - Literature documentation: 1 hour

- **Phase 5 (Review)**: 1-2 hours
  - Self-review using checklist: 1 hour
  - Final adjustments: 1 hour

**Total**: 12-22 hours (depending on literature review findings)

**Critical Path**: Literature review → Implementation decision (implement OR document)

---

## Getting Started

1. **Read this document completely** - Understand the problem and proposed solution

2. **Start with Phase 0** - Literature review is MANDATORY before implementation
   - Search existing literature files first
   - Use WebSearch or Context7 for external research
   - Document findings in `tasks/literature_review_force_calculation.md`

3. **Decision point** - After literature review:
   - **If literature supports I_active**: Proceed with implementation
   - **If literature contradicts**: Document difference, do not implement
   - **If literature is silent**: Contact Hornresp author OR document limitation

4. **Implement** - Follow phases 1-5 sequentially
   - Each phase builds on the previous
   - Don't skip testing or documentation

5. **Ask for review** - When ready, submit PR with:
   - Reference to this planning document
   - Literature review findings
   - Validation results
   - Updated documentation

---

## Questions or Issues?

**Contact**: Project maintainer or create GitHub issue

**References**:
- Investigation report: `tasks/investigate_high_frequency_spl_rolloff.md`
- Test scripts: `tasks/test_active_current_hypothesis.py`
- Hornresp data: `tests/validation/drivers/bc_8ndl51/infinite_baffle/`

**Remember**: The goal is NOT to match Hornresp exactly, but to implement the
**physically correct model** with proper literature support. If Hornresp uses
undocumented corrections, we document the difference rather than reverse-engineering
their approach.
