# GSD Project-Specific Instructions

This file contains project-specific instructions for Claude Code when working on the gsd codebase.

## Project Overview

GSD is a CLI tool for loudspeaker enclosure design and simulation, with initial focus on **horn-loaded enclosures**. The simulation engine implements acoustic theory from first principles and validates results against Hornresp (the industry-standard horn simulation tool).

**Key workflow:**
1. Import driver parameters (manual entry via CLI)
2. Explore enclosure types and variables
3. Export to Hornresp for validation
4. Iterate based on validation results

## CRITICAL Rules for Physics Simulation

### Rule #1: ALWAYS Use Validated Physics Models for Output

**NEVER create simplified approximations or "fudge factors" for SPL/response calculations.**

When generating frequency response, SPL curves, impedance plots, or ANY physics-based output:
- ✅ **USE:** Validated functions from `src/gsd/simulation/` (tested against Hornresp)
- ❌ **NEVER:** Create your own simplified models, approximations, or heuristic formulas

**Examples of WRONG approaches (garden paths to avoid):**
- ❌ "Let's just use a -12 dB/octave high-pass filter" → **NOT validated**
- ❌ "I'll add some Gaussian peaks for resonances" → **NOT physics-based**
- ❌ "The datasheet says 108.5 dB, so I'll use that" → **NOT calculated from first principles**
- ❌ "Pressure ∝ 1/|Z_throat|" → **WRONG** (throat impedance ≠ radiated SPL)

**What to do INSTEAD:**
1. Check `src/gsd/simulation/` for existing validated functions
2. If no validated function exists: **STOP** - do not create approximation
3. Either:
   - Research and implement proper physics (with literature citations)
   - Use Hornresp directly for that calculation
   - Clearly label as "UNVALIDATED APPROXIMATION - DO NOT USE FOR PRODUCTION"

**Validation requirement:** All physics output must be validated against Hornresp before use in design tools.

### Rule #2: Literature Citation Requirements

**ALL Simulation Code MUST Cite Literature**

Every function in the `src/gsd/simulation/` module that implements acoustic theory **MUST** cite the literature it implements.

### Citation Format

Every simulation function must include:

1. **Docstring with literature citations** - Reference specific literature files and equation numbers
2. **Inline comments** - Link to specific equations from the literature
3. **Validation requirements** - State how the implementation will be validated against Hornresp

#### Example - Correct Citation Format

```python
def calculate_horn_cutoff(flare_constant: float, speed_of_sound: float = 343.0) -> float:
    """
    Calculate the cutoff frequency of an exponential horn.

    The cutoff frequency is the frequency below which the horn acts as a
    high-pass filter and does not efficiently propagate sound waves.

    Based on Olson (1947), Equation 5.18 and Beranek (1954), Chapter 5.
    Both sources derive the same expression from the horn equation.

    Literature:
    - literature/horns/olson_1947.md - Exponential horn theory, Eq. 5.12, 5.18
    - literature/horns/beranek_1954.md - Horn impedance, Chapter 5, Eq. 5.20
    - literature/horns/kolbrek_horn_theory_tutorial.md - Modern treatment with validation

    Args:
        flare_constant: Horn flare constant m (1/m), where S(x) = S_t · exp(m·x)
        speed_of_sound: Speed of sound in air (m/s), default 343 m/s at 20°C

    Returns:
        Cutoff frequency f_c (Hz), below which the horn does not propagate efficiently

    Validation:
        Compare with Hornresp's cutoff frequency calculation for identical
        flare constant. Expected agreement: <0.1% deviation.

    Examples:
        >>> calculate_horn_cutoff(flare_constant=4.6)
        250.0  # Hz (for m=4.6, c=343)
    """
    # Olson (1947), Eq. 5.18: f_c = c·m/(2π)
    # Beranek (1954), Chapter 5: Same expression derived from horn equation
    return (speed_of_sound * flare_constant) / (2 * math.pi)
```

### What Requires Citations

**MUST cite literature:**
- All acoustic impedance calculations
- Horn profile equations (exponential, hyperbolic, conical)
- Frequency response calculations
- Directivity patterns
- Throat/mouth impedance transformations
- Cutoff frequency formulas
- Efficiency calculations
- Power handling estimates

**Does NOT require citations:**
- CLI interface code (click commands, prompts)
- File I/O operations
- Data validation
- Testing infrastructure
- Plotting/visualization code
- Configuration management

### Code Review Criteria

When reviewing simulation code, check:

1. [ ] Does the function have a docstring?
2. [ ] Does the docstring include a "Literature:" section?
3. [ ] Are specific literature files referenced?
4. [ ] Are equation numbers cited (e.g., "Olson Eq. 5.18")?
5. [ ] Do inline comments reference the literature?
6. [ ] Is there a validation section describing how to verify against Hornresp?
7. [ ] Does the implementation match the cited equations?

**Pull requests without proper citations will be rejected.**

## Development Workflow

### Literature-First Development

When implementing a new simulation feature:

1. **Start with literature/** - Read the relevant reference files
2. **Identify the equations** - Find the specific equations to implement
3. **Write the docstring first** - Include full citations before coding
4. **Implement the equations** - Translate math to code
5. **Validate against Hornresp** - Create test cases comparing results
6. **Document any discrepancies** - Explain any deviations from reference

### Validation Against Hornresp

Every simulation algorithm must be validated against Hornresp:

1. Create test cases with known horn parameters
2. Run gsd simulation
3. Run Hornresp with identical parameters
4. Compare results (impedance, frequency response, etc.)
5. Document agreement percentage
6. Investigate and explain any discrepancies >1%

Acceptable tolerances:
- Well above cutoff (f > 2·f_c): <1% deviation
- Near cutoff (f ≈ 1.2·f_c to 2·f_c): <2% deviation
- Close to cutoff (f ≈ f_c): <5% deviation (numerical sensitivity)
- Below cutoff (f < f_c): qualitative agreement only

### Exporting to Hornresp Format

GSD can export driver and enclosure parameters to Hornresp's native `.txt` file format for direct import and validation.

**Using the export function:**

```python
from gsd.hornresp.export import export_to_hornresp
from gsd.driver.bc_drivers import get_bc_15ps100

# Get driver
driver = get_bc_15ps100()

# Export ported box design
export_to_hornresp(
    driver=driver,
    driver_name="15PS100 Ported B4",
    output_path="15ps100_ported.txt",
    comment="B4 Butterworth alignment",
    enclosure_type="ported_box",
    Vb_liters=105.5,
    Fb_hz=37.3,
    port_area_cm2=140.2,
    port_length_cm=22.8
)
```

**Supported enclosure types:**
- `"infinite_baffle"` - No enclosure parameters needed
- `"sealed_box"` - Requires `Vb_liters` (box volume in liters)
- `"ported_box"` - Requires `Vb_liters`, `Fb_hz`, `port_area_cm2`, `port_length_cm`

**Critical differences between gsd and Hornresp:**

1. **M_md vs M_ms**: Hornresp expects **M_md** (driver mass only, without radiation mass)
   - GSD exports `M_md` automatically via `driver_to_hornresp_record()`
   - Hornresp calculates its own radiation mass loading
   - **Never export M_ms** to Hornresp (would double-count radiation mass)

2. **Unit conversions** (handled automatically by export function):
   - Area: m² → cm² (multiply by 10000)
   - Mass: kg → g (multiply by 1000)
   - Inductance: H → mH (multiply by 1000)
   - Compliance: m/N (scientific notation format: X.XXE-XX)

3. **File format requirements**:
   - CRLF line endings (`\r\n`) - not Unix LF (`\n`)
   - Section headers with `|` prefix (e.g., `|TRADITIONAL DRIVER PARAMETER VALUES:`)
   - Cms in scientific notation with exactly 2 decimal places
   - All required sections must be present

4. **Multi-segment horn format (CRITICAL - Segment type labels, NOT L12/L23)**:
   Hornresp uses **segment type labels** followed by length, NOT `L12`/`L23` labels:

   **2-segment exponential horn example:**
   ```
   S1 = 3.56        (throat area in cm²)
   S2 = 101.50      (middle/junction area in cm²)
   Exp = 15.00      ← "Exponential segment, 15.00 cm long" (NOT L12!)
   F12 = 611.42     (flare frequency for segment 1)
   S2 = 101.50      (middle area repeated)
   S3 = 401.10      (mouth area in cm²)
   Exp = 15.00      ← "Exponential segment, 15.00 cm long" (NOT L23!)
   F23 = 250.78     (flare frequency for segment 2)
   ```

   **All segment type labels:**
   - `Exp = <length>` → Exponential segment
   - `Con = <length>` → Conical segment
   - `Trx = <length>` → Tractrix segment (where x is variant)
   - `Obi = <length>` → Oblate spheroidal segment
   - `Hyp = <length>` → Hyperbolic (catenoidal) segment

   **Key points:**
   - The LABEL indicates the horn profile type (Exp/Con/etc.)
   - The VALUE following the label is the segment length in cm
   - Do NOT use `L12 =` or `L23 =` - use profile type labels instead
   - Format is position-based: 4 lines per segment (S1, S2, <Type>, Fxx)
   - S2 is repeated at start of each subsequent segment

5. **Radiation angle setting**:
   - Use `Cir = -200.00` for half-space (2π steradians) - typical for freestanding speakers
   - Do NOT use `Cir = 0.73` (this is full sphere, 4π steradians) unless speaker is free-space

6. **Chamber depth (Lrc)**: Auto-calculated if not provided
   - Must be > 0 for sealed/ported boxes (Hornresp requirement)
   - Calculated as cube root of Vb, clamped to physical constraints
   - Constraints: `2×piston_radius ≤ Lrc ≤ Vb/S_piston`

**Example: Exporting a complete design**

```python
# Calculate optimal design
from gsd.enclosure.ported_box import (
    calculate_ported_box_system_parameters,
    calculate_optimal_port_dimensions
)

# Design parameters
Vb = driver.V_as  # Use Vas for B4 alignment
Fb = driver.F_s   # Use Fs for B4 alignment

# Get system parameters
params = calculate_ported_box_system_parameters(driver, Vb, Fb)
port_area_m2, port_length_m, _ = calculate_optimal_port_dimensions(driver, Vb, Fb)

# Export to Hornresp
export_to_hornresp(
    driver=driver,
    driver_name="15PS100_B4",
    output_path="designs/15ps100_b4.txt",
    comment="B4 Butterworth: Vb=Vas, Fb=Fs",
    enclosure_type="ported_box",
    Vb_liters=Vb * 1000,
    Fb_hz=Fb,
    port_area_cm2=port_area_m2 * 10000,
    port_length_cm=port_length_m * 100
)
```

**Validation workflow:**

1. Export design from gsd
2. Import into Hornresp (File → Import)
3. Run simulations in both tools
4. Compare frequency responses, impedance curves
5. Document any discrepancies

**Literature:**
- Hornresp User Manual - File format specification
- `src/gsd/hornresp/export.py` - Implementation with format details

## File Organization Guidelines

### CRITICAL: No Files in Top-Level Directory (TLD)

**DO NOT create files in the project root directory.** All files must be organized in appropriate subdirectories.

### Directory Structure for Documentation and Research

```
gsd/
├── docs/                    # Documentation (git tracked)
│   ├── validation/          # Validation investigation reports
│   │   ├── sealed_box_spl_investigation.md
│   │   ├── sealed_box_spl_research_summary.md
│   │   └── ported_box_impedance_fix.md
│   └── [other docs]
├── tasks/                   # Active work items (git tracked)
│   ├── research_validation_plan.md
│   ├── driver_validation_status.md
│   └── [other active tasks]
├── tests/                   # Test infrastructure (git tracked)
│   └── validation/
│       └── drivers/
│           └── [driver_name]/
│               └── [enclosure_type]/
│                   ├── README.md
│                   ├── VALIDATION_ISSUE.md
│                   └── sim.txt
└── [only CLAUDE.md, README.md, ROADMAP.md, pyproject.toml in TLD]
```

### File Placement Rules

**Documentation (permanent reference material):**
- Validation investigation results → `docs/validation/`
- Technical specifications → `docs/`
- User guides → `docs/`

**Active Tasks (work-in-progress):**
- Research plans → `tasks/`
- Investigation notes → `tasks/`
- Status tracking → `tasks/`
- Temporary analysis scripts → `tasks/`

**Test Data:**
- Hornresp simulation results → `tests/validation/drivers/{driver}/{enclosure}/`
- Test configuration → `tests/validation/drivers/{driver}/{enclosure}/`
- Validation status → `tests/validation/drivers/{driver}/{enclosure}/VALIDATION_ISSUE.md`

**Literature:**
- Academic papers → `literature/{category}/`
- Reference materials → `literature/{category}/`

**Code:**
- Source code → `src/gsd/`
- Tests → `tests/`
- Examples → `examples/` (if it exists)

### What Belongs in TLD (Top-Level Directory)

**ONLY these files should be in the project root:**
- `CLAUDE.md` - Project-specific instructions (this file)
- `README.md` - Project overview and setup
- `ROADMAP.md` - Development roadmap
- `pyproject.toml` - Python project configuration
- `.gitignore` - Git ignore rules
- `LICENSE` - License file
- Standard config files (`.github/`, etc.)

**NOT in TLD:**
- ❌ Investigation notes (→ `tasks/` or `docs/validation/`)
- ❌ Research summaries (→ `tasks/` or `docs/validation/`)
- ❌ Status reports (→ `tasks/`)
- ❌ Temporary analysis scripts (→ `tasks/`)
- ❌ Test data (→ `tests/`)

### Tracked vs Untracked Files

**Git Tracked (project files):**
- All documentation in `docs/`
- Active tasks in `tasks/`
- Test data in `tests/`
- Source code in `src/`
- Literature reference files in `literature/`

**Git Untracked (personal/temporary):**
- Python cache in `/tmp/` or `/private/tmp/`
- Session summaries in `/tmp/`
- Personal notes outside project tree
- Build artifacts (handled by `.gitignore`)
- Virtual environments (`.venv/`)

**When to commit:**
- Investigation results → Yes (to `docs/` or `tasks/`)
- Completed research → Yes (to `docs/validation/`)
- Working scripts → Yes (to `tasks/`)
- `/tmp/` files → No (temporary workspace)

### Examples

**✅ CORRECT:**
```bash
# Create investigation report in docs/
docs/validation/sealed_box_spl_investigation.md

# Create active research plan in tasks/
tasks/research_validation_plan.md

# Create temporary script for debugging
tasks/diagnose_spl_rolloff.py
```

**❌ WRONG:**
```bash
# DON'T create in TLD
sealed_box_investigation.md  # Wrong! → docs/validation/
research_plan.md             # Wrong! → tasks/
debug_script.py              # Wrong! → tasks/
```

## Code Structure Conventions

### Directory Organization

```
src/gsd/
├── cli.py                   # CLI entry point (click commands)
├── driver/                  # Driver parameter handling
│   └── parameters.py        # Thiele-Small parameter data structures
├── simulation/              # SIMULATION CODE MUST CITE LITERATURE
│   ├── horn_theory.py       # Horn acoustic models (cite literature/horns/)
│   ├── electrical_analogies.py  # Circuit representations
│   └── response.py          # Frequency response calculation
├── hornresp/                # Hornresp integration
│   └── export.py            # Export to Hornresp format
└── validation/              # Validation framework
    └── compare.py           # Compare gsd vs Hornresp results
```

### Import Conventions

- Use absolute imports: `from gsd.simulation import horn_theory`
- Keep simulation modules independent of CLI code
- Validation code should import both simulation and hornresp modules

### Naming Conventions

- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Module names: `snake_case`

For physics functions, use descriptive names:
- `calculate_horn_impedance()` (not `calc_z()`)
- `exponential_horn_area()` (not `exp_area()`)
- `cutoff_frequency()` (not `fc()`)

## Testing Requirements

### Unit Tests

All simulation functions must have unit tests:

```python
def test_calculate_horn_cutoff():
    """Test cutoff frequency calculation against Olson Eq. 5.18"""
    # Test case from Olson (1947), Section 5.6
    m = 4.6  # flare constant (1/m)
    c = 343.0  # speed of sound (m/s)
    fc_expected = 250.0  # Hz

    fc_calculated = calculate_horn_cutoff(m, c)

    assert abs(fc_calculated - fc_expected) < 0.1  # <0.1% tolerance
```

### Validation Tests

Create validation tests comparing with Hornresp:

```python
def test_exponential_horn_vs_hornresp():
    """Validate exponential horn impedance against Hornresp"""
    # Define horn parameters
    horn_params = ExponentialHorn(
        throat_area=0.001,  # m²
        mouth_area=0.1,     # m²
        length=1.5,         # m
    )

    # Calculate impedance with gsd
    z_gsd = calculate_throat_impedance(horn_params, frequency=500)

    # Load Hornresp reference data
    z_hornresp = load_hornresp_reference("test_data/exp_horn_001.csv")

    # Compare
    assert abs(z_gsd - z_hornresp) / z_hornresp < 0.01  # <1% deviation
```

### Test Data Organization

Store Hornresp reference data in `tests/validation_data/`:

```
tests/validation_data/
├── exponential_horns/
│   ├── exp_horn_001.csv     # Frequency, impedance, phase from Hornresp
│   ├── exp_horn_002.csv
│   └── ...
└── hyperbolic_horns/
    └── ...
```

## Documentation Standards

### Docstring Format

Use Google-style docstrings with extensions:

```python
def function_name(param1: type, param2: type) -> return_type:
    """
    Brief description of what the function does.

    Longer description explaining the physics and theory if needed.
    Mention any assumptions or limitations.

    Based on Author (Year), Equation X.Y and possibly other sources.

    Literature:
    - literature/path/to/reference1.md - Description of what's used
    - literature/path/to/reference2.md - Additional relevant info

    Args:
        param1: Description with units (e.g., meters, Hz)
        param2: Description with units

    Returns:
        Description of return value with units

    Raises:
        ValueError: Description of when error occurs

    Validation:
        How to validate against Hornresp, expected tolerance

    Examples:
        >>> function_name(1.0, 2.0)
        42.0
    """
```

### Physical Constants

Define constants with citations:

```python
# Standard conditions at 20°C, 1 atm
# From Kinsler et al. (1982), Chapter 1
SPEED_OF_SOUND = 343.0  # m/s
AIR_DENSITY = 1.18  # kg/m³
```

## Optimization and Exploration

### Enclosure Optimization Code: Generic vs Driver-Specific

**CRITICAL:** Enclosure optimization code committed to the repository **MUST be generic** and work with any driver, not hardcoded for specific drivers.

**What this means:**
- ✅ **DO:** Create generic optimization functions that accept any `ThieleSmallParameters` object
- ✅ **DO:** Parameterize optimization constraints by driver properties (e.g., `Vb_min = driver.V_as * 0.5`)
- ❌ **DON'T:** Hardcode driver-specific values in optimization logic
- ❌ **DON'T:** Create optimization workflows that only work with one driver

**Examples:**

✅ **CORRECT - Generic optimization:**
```python
def optimize_ported_box(driver: ThieleSmallParameters, alignment: str):
    """
    Optimize ported box parameters for a given alignment.

    Args:
        driver: Any driver with Thiele-Small parameters
        alignment: 'B4', 'QB3', 'BB4', etc.

    Returns:
        Optimized Vb, Fb, port dimensions
    """
    if alignment == 'B4':
        Vb = driver.V_as
        Fb = driver.F_s
    # ... generic optimization logic
```

❌ **WRONG - Driver-specific hardcoding:**
```python
def optimize_for_bc_15ps100():
    """
    Optimize for BC 15PS100 only.
    """
    Vb = 105.5  # Hardcoded for 15PS100
    Fb = 37.3   # Hardcoded for 15PS100
    # ... will not work with any other driver
```

**Where driver-specific code belongs:**
- Driver parameter definitions → `src/gsd/driver/bc_drivers.py` or similar
- Test cases and examples → `tests/` or `examples/` (can show usage with specific drivers)
- User's local workspace (not committed to repo)

**Rationale:**
The gsd tool is a general-purpose enclosure design calculator, not a collection of one-off designs for specific drivers. Generic optimization code:
- Is reusable across all drivers
- Makes the codebase more maintainable
- Allows users to optimize for their own drivers
- Keeps the project focused on enclosure design methodology, not specific products

### Future Features (Roadmap Phases 6-7)

When implementing optimization and parameter exploration:

1. Maintain citation requirements for all simulation code
2. Optimization algorithms (pymoo) don't need citations, but objective functions do
3. Document which literature provides the optimization criteria (e.g., "maximize efficiency at 80 Hz per Beranek Chapter 8")

### Parameter Sweep Conventions

When exploring parameter space:

- Store results with full parameter metadata
- Include literature citations for each calculation
- Validate spot checks against Hornresp
- Warn if parameters violate assumptions from literature (e.g., horn too short for cutoff frequency)

## Two-Way System Design

When designing two-way systems with horn-loaded HF drivers, **ALWAYS use the integrated approach**.

### CRITICAL: Use Integrated Design Function

**One-shot design success:**

```python
from gsd.optimization.api.two_way_system import design_two_way_system_integrated

design = design_two_way_system_integrated(
    lf_driver_name="BC_12FW88",
    hf_driver_name="BC_DH450",
    target_crossover_hz=800,
    printer_constraints={"max_length": 0.25, "max_mouth_area": 0.0625},
    accept_sensitivity_loss=True  # Allow smaller mouth for better integration
)

print(f"Horn Fc: {design.horn_fc_hz:.0f} Hz")
print(f"Crossover: {design.crossover_frequency_hz:.0f} Hz")
print(f"Dip: {design.dip_db:.2f} dB")
print(f"Rating: {design.validation['rating']}")
```

### Workflow Requirements

**1. Calculate BEFORE Optimizing:**
```python
from gsd.optimization.api.horn_physics import (
    calculate_target_horn_fc,
    calculate_mouth_area_for_fc,
    assess_mouth_area_feasibility
)

# Work backwards from XO target to horn Fc
target_fc = calculate_target_horn_fc(
    desired_crossover_hz=800,
    lf_driver_beaming_hz=840,
    xo_fc_ratio=2.0
)

# Calculate required mouth area for target Fc
required_mouth = calculate_mouth_area_for_fc(
    throat_area_cm2=7.0,
    length_cm=25.0,
    target_fc_hz=target_fc
)

# Check feasibility against printer constraints
feasibility = assess_mouth_area_feasibility(
    required_mouth_cm2=required_mouth,
    available_mouth_cm2=625,
    target_fc_hz=target_fc
)
```

**2. Verify Constraints:**
- XO frequency must be < 0.8×LF_beaming
- Mouth area must fit printer constraints
- Horn length must fit printer constraints

**3. Optimize Crossover:**
```python
from gsd.optimization.api.two_way_system import optimize_crossover_frequency

# Sweep XO range to find optimal point (don't assume 2×Fc)
result = optimize_crossover_frequency(
    lf_driver_name="BC_12FW88",
    hf_driver_name="BC_DH450",
    lf_enclosure_type="ported",
    lf_enclosure_params={"Vb": 0.1145, "Fb": 47.6},
    horn_fc_hz=468,
    xo_range_hz=(600, 1200)
)

print(f"Optimal XO: {result['optimal_xo_hz']:.0f} Hz")
print(f"XO/Fc ratio: {result['xo_vs_fc_ratio']:.2f}")  # May not be 2.0!
```

### Physics Background

**Horn Cutoff vs Mouth Area (for fixed length):**
```
Fc = (c/4π) × (1/L) × ln(mouth/throat)

For L=250mm, throat=7cm²:
- mouth=250cm² → Fc=390Hz  (excellent for 800Hz XO)
- mouth=504cm² → Fc=467Hz  (good for 800Hz XO)

**Critical:** Small mouth changes have LARGE effects on Fc due to logarithm
```

**LF Driver Beaming:**
```
f_beam = 2c/(π×d) where d = piston diameter

For 12" driver: f_beam ≈ 840Hz
XO should be < 0.8×f_beam ≈ 670Hz for flat response
```

**Trade-off: HF Sensitivity vs Crossover Integration**
| Mouth (cm²) | Fc (Hz) | HF Sensitivity | XO Option | Dip Rating |
|-------------|---------|----------------|-----------|------------|
| 504 | 467 | Best | ~950Hz | ❌ Poor (13.8dB) |
| 350 | 427 | Good -2dB | ~850Hz | ⚠️ Acceptable (3.7dB) |
| 250 | 390 | Fair -4dB | ~600Hz | ✅ Good (3.2dB) |

**User's preference:** "HF sensitivity is definitely something we can sacrifice"

### Common Pitfalls

❌ **WRONG:** Design LF and HF independently, then try to make crossover work
```python
# This fails because horn Fc may force XO too high
lf_design = optimize_lf_enclosure(driver)
horn_design = optimize_horn(driver)
crossover = design_crossover(lf_design, horn_design)  # May have huge dip!
```

✅ **RIGHT:** Use integrated design from start
```python
design = design_two_way_system_integrated(...)  # One function call
```

❌ **WRONG:** Use preset horn without checking Fc
```python
# Preset horn may have wrong Fc for your XO target
horn = get_preset_horn("large_horn")  # Fc=1865Hz!
# Now XO must be >3700Hz → LF driver beaming → poor integration
```

✅ **RIGHT:** Calculate required mouth for target Fc
```python
target_fc = calculate_target_horn_fc(desired_xo, ...)
required_mouth = calculate_mouth_area_for_fc(...)
```

❌ **WRONG:** Assume XO = 2×Fc
```python
# Case study found optimal XO = 1.28×Fc, not 2×Fc!
crossover_freq = horn_fc * 2.0  # May not be optimal
```

✅ **RIGHT:** Sweep XO range to find optimal point
```python
result = optimize_crossover_frequency(...)  # Finds best XO
```

❌ **WRONG:** Ignore LF driver beaming
```python
# XO too high causes LF driver beaming → poor integration
crossover_freq = 2500  # Too high for 12" driver!
```

✅ **RIGHT:** Calculate f_beam and cap XO accordingly
```python
f_beam = calculate_lf_beaming_frequency(driver)
xo = min(desired_xo, 0.8 * f_beam)
```

### Available Functions

**Horn Physics (`src/gsd/optimization/api/horn_physics.py`):**
- `calculate_lf_beaming_frequency(driver)` → float
- `calculate_target_horn_fc(desired_xo, f_beam, xo_ratio)` → float
- `calculate_mouth_area_for_fc(throat, length, target_fc)` → float
- `calculate_fc_from_mouth(throat, mouth, length)` → float
- `assess_mouth_area_feasibility(required, available, ...)` → dict

**Crossover Optimization (`src/gsd/optimization/api/two_way_system.py`):**
- `optimize_crossover_frequency(...)` → dict with optimal_xo_hz, dip_db, etc.
- `design_two_way_system_integrated(...)` → TwoWaySystemDesign

### Case Study: BC 12FW88 + DH450

See: `docs/two_way_design_review_12fw88_dh450.md`

**Initial attempt (failed):**
- Used preset horn: 504cm² mouth, Fc=1865Hz (from incorrect doc calculation)
- Crossover at 2×Fc = 3730Hz
- Result: 13.75dB dip (POOR)

**Root cause:**
- Horn Fc too high → XO too high → LF driver beaming

**Solution (successful):**
- Calculated required mouth for Fc≈400Hz
- Used 250cm² mouth → Fc=468Hz
- Optimized XO by sweep → 600Hz (1.28×Fc)
- Result: 3.17dB dip (ACCEPTABLE)

**Key insight:** For fixed horn length, mouth area directly controls Fc, which controls crossover integration quality.

## Common Pitfalls

### Units

**Always include units in documentation and variable names:**
- `area_m2` not `area`
- `length_m` not `length`
- `frequency_hz` not `frequency`

### Reference Frame

Clarify coordinate system:
- `x = 0` at throat or mouth? (Convention: x=0 at throat)
- Positive x direction toward mouth

### Frequency Range

Document valid frequency ranges:
- Exponential horn theory valid for f > f_c
- Below cutoff, results are qualitative (evanescent waves)
- Very high frequencies may need directivity corrections

### Finite vs Infinite Horns

Be explicit about which model you're implementing:
- Infinite horn: Olson (1947) analytical solutions
- Finite horn: Beranek (1954) with mouth corrections, Kinsler (1982) transmission line approach

### M_md vs M_ms: Driver Mass Parameters

**CRITICAL**: Understand the distinction between driver mass parameters:

- **M_md** (Driver Mass): Physical mass of voice coil + diaphragm only (kg)
  - This is what you specify when creating a driver
  - Sourced from datasheet as "Mmd" or "Mms" (note: datasheet naming is inconsistent)
  - Does NOT include radiation mass loading

- **M_ms** (Total Moving Mass): M_md + radiation mass (kg)
  - This is calculated automatically in `ThieleSmallParameters.__post_init__()`
  - Includes frequency-dependent radiation mass from the air load
  - Used for resonance frequency and Q factor calculations

**Why this matters:**
Radiation mass loading significantly affects resonance frequency:
```
F_s = 1 / (2π√(M_ms·C_ms))

where M_ms = M_md + 2×M_rad(F_s)
```

The 2× multiplier on radiation mass matches Hornresp's empirical methodology
(see `src/gsd/driver/radiation_mass.py` for implementation).

**Example: BC_8NDL51**
- M_md = 26.77 g (driver mass only, from datasheet)
- M_rad ≈ 3.7 g (radiation mass at resonance, from Beranek theory)
- M_ms ≈ 30.5 g (total mass = 26.77 + 2×3.7)
- Resonance shift: 68.3 Hz (driver only) → 64.0 Hz (with radiation) = 6.7% lower

**Literature:**
- Beranek (1954), Eq. 5.20 - Radiation impedance and mass loading
- `literature/horns/beranek_1954.md`
- `src/gsd/driver/radiation_mass.py` - Implementation with iterative solver

## When in Doubt

1. **Read the literature** - Check `literature/horns/` for relevant equations
2. **Cite your sources** - Even if uncertain, cite the literature you're using
3. **Validate against Hornresp** - When gsd and Hornresp disagree, investigate why
4. **Ask for clarification** - It's better to ask than to implement without citations

## Using an Online Research Agent

For difficult questions requiring external research, you can delegate to an online research agent. This is particularly useful for:
- Complex acoustic theory not in the existing literature
- Finding alternative approaches or implementations
- Researching specific libraries, frameworks, or tools
- Investigating edge cases or advanced topics

### When to Use a Research Agent

**Good candidates:**
- "How does pymoo handle constrained optimization for acoustic parameters?"
- "Find modern approaches to calculating horn throat impedance"
- "What are the best practices for validating physics simulations?"
- "Research numerical methods for solving transmission line equations"

**Not suitable for:**
- Questions about local code structure (use Explore agent instead)
- Simple documentation lookups (use Context7 instead)
- File searching or code navigation (use Glob/Grep instead)

### Research Agent Workflow

**Important:** The online research agent **does NOT have access to the local codebase**, but it **CAN access the public GitHub repository** at:
```
https://github.com/wokhouse/gsd
```

When delegating to the research agent, provide relevant context or reference specific files/paths in the repo.

**Step 1: Prepare the research prompt**

Use the following template to generate a prompt for the research agent:

```
RESEARCH OBJECTIVE:
[Clearly state what you need to find out]

SUCCESS CRITERIA:
[What would a successful answer look like? What specific information do you need?]

CONTEXT:
[Briefly explain the gsd project context - it's a horn simulation tool, validates against Hornresp, etc.]

RELEVANT CODE/DETAILS:
[Paste relevant code snippets, function signatures, or error messages here]

CONSTRAINTS:
- Focus on Python-based solutions
- Prefer approaches with citations to acoustic literature
- Numerical accuracy is critical (validated against Hornresp)
- Avoid over-engineering - keep solutions minimal

DELIVERABLE:
[Specifically what you want the agent to provide: explanation, code example, references, etc.]
```

**Step 2: Generate and copy the prompt**

Generate a well-structured prompt following the template above and use `pbcopy` to copy it for the user:

```bash
echo "YOUR_RESEARCH_PROMPT_HERE" | pbcopy
```

**Step 3: Inform the user**

Tell the user the prompt has been copied and instruct them to paste it to the online research agent.

### Example Research Prompt

Here's an example for researching numerical optimization:

```
RESEARCH OBJECTIVE:
Find the best approach for optimizing horn parameters (flare constant, length, mouth area) to maximize efficiency at a target frequency range.

SUCCESS CRITERIA:
- Recommend a Python library for constrained optimization
- Provide code example showing how to set up the optimization problem
- Explain how to handle constraints (e.g., minimum horn length, maximum mouth size)
- Reference any acoustic literature on horn optimization

CONTEXT:
GSD is a Python CLI tool for horn-loaded enclosure design. It calculates horn impedance and frequency response from first principles, validated against Hornresp. We're adding optimization capabilities to help users find optimal horn parameters.

RELEVANT CODE/DETAILS:
We have these functions already implemented:
- `calculate_horn_efficiency(flare_constant, length, mouth_area, frequency)` -> returns efficiency (0-1)
- `calculate_horn_cutoff(flare_constant)` -> returns cutoff frequency (Hz)
- Driver Thiele-Small parameters available via `driver.F_s`, `driver.V_as`, etc.

Target frequency range: 40-80 Hz (bass horn)

CONSTRAINTS:
- Must use Python libraries (preferably already common in scientific computing)
- Solution must be numerically accurate - this drives physical horn designs
- Need to handle both continuous and discrete parameters
- Should provide convergence diagnostics

DELIVERABLE:
1. Recommended library with rationale
2. Code example showing objective function and constraint setup
3. Explanation of how to validate the optimization results
4. Any acoustic literature references on horn parameter optimization
```

### After Research

When the research agent provides results:
1. **Evaluate the solution** - Check if it meets the success criteria
2. **Verify citations** - Ensure any literature references are accurate
3. **Test locally** - Create a minimal test case before full implementation
4. **Document** - Add proper citations to CLAUDE.md or function docstrings
5. **Integrate** - Implement following the project's coding conventions

### Research Agent Output Format

The research agent should provide:
- **Direct answer** to your question
- **Code examples** (if applicable)
- **References** to literature or documentation
- **Recommendations** with rationale
- **Caveats or limitations** of the suggested approach

### Research Agent Response Format for Implementation Tasks

**IMPORTANT:** When delegating implementation research tasks, instruct the research agent to structure their response in two sections:

1. **Section 1: Research Findings** (for human review)
   - Theory explanation
   - Equations and derivations
   - Literature citations
   - Implementation notes and caveats

2. **Section 2: Implementation Instructions** (for Claude Code)
   - Write as a direct task specification for a future Claude Code instance
   - Include exact file paths and line numbers where possible
   - Provide complete code snippets ready to copy-paste
   - Specify validation steps and expected results

Template for implementation tasks:
```
IMPORTANT - RESPONSE FORMAT:
You are writing to BOTH (1) human researchers AND (2) a future Claude Code instance.
Structure your response with two sections:

## SECTION 1: RESEARCH FINDINGS (for human review)
- Theory explanation
- Equations and derivations
- Literature citations
- Implementation notes

## SECTION 2: IMPLEMENTATION INSTRUCTIONS (for Claude Code)
Write this as a direct task specification for Claude Code, including:
- Files to modify (with exact paths)
- Implementation steps (with line numbers)
- Code changes (complete, ready to apply)
- Validation approach
- Expected results
```

This ensures the research agent's output can be directly used by Claude Code to implement the findings without needing additional interpretation.

## Resources

- `literature/README.md` - Overview of citation system
- `ROADMAP.md` - Development phases
- Hornresp manual: http://www.hornresp.net/
- `literature/horns/olson_1947.md` - Classic horn theory (exponential profiles, cutoff frequency)
- `literature/horns/beranek_1954.md` - Radiation impedance (piston in infinite baffle)
- `literature/horns/kolbrek_horn_theory_tutorial.md` - Modern horn theory with T-matrix method
- `literature/transmission_lines/chabassier_tournemenne_2018_tmatrix.md` - T-matrix propagation
- `literature/simulation_methods/aarts_janssen_2003_struve_approximation.md` - Struve H₁ approximation

---

**Remember: The goal is to create a simulation tool grounded in established acoustic theory, with every algorithm traceable to the literature. This is what makes gsd trustworthy and useful for horn design.**
