# GSD Development Roadmap

This roadmap outlines the development phases for gsd, a CLI tool for horn-loaded loudspeaker simulation and design.

## Project Vision

Create a validated loudspeaker simulation tool that:
- Implements horn theory from first principles with proper literature citations
- Validates results against Hornresp at every development stage
- Provides interactive exploration of enclosure parameters
- Exports designs to Hornresp format for cross-checking

---

## Phase 1: Literature Review & Algorithm Selection ✅

**Status:** Complete
**Deliverables:**
- [x] Literature directory structure created
- [x] Foundational references documented (Olson 1947, Beranek 1954, Kinsler 1982)
- [x] Citation system established in `CLAUDE.md`
- [x] Key equations identified for implementation

**Key Algorithms Selected:**
- Exponential horn profile: Olson Eq. 5.12, Beranek Chapter 5
- Horn cutoff frequency: Olson Eq. 5.18
- Throat impedance: Kinsler Eq. 9.6.4 (transmission line approach)
- Mouth impedance: Beranek Eq. 5.20 (piston radiation)
- Finite horn corrections: Beranek Chapter 5, Kinsler Section 9.6

**Next:** Implement these algorithms with proper citations

---

## Phase 2: Driver Parameter Input System ✅

**Status:** Complete
**Deliverables:**
- [x] Define Thiele-Small Parameter Data Structure
- [x] B&C driver test fixtures (8NDL51, 12NDL76, 15DS115, 18PZW100)
- [x] Driver database with test data in `tests/validation/drivers/`
- [x] Radiation impedance calculations (piston in infinite baffle)
  - Literature: Beranek (1954), Eq. 5.20
- [x] Electrical impedance calculations (bare driver)
  - Literature: COMSOL (2020), Small (1972)

**Bug Fix:**
- [x] Fixed acoustic impedance scaling: `Z_a · S_d²` (was `Z_a / S_d²`)

---

## Phase 3: Horn Simulation Engine (In Progress)

**Status:** Partially Complete
**Goal:** Implement core horn acoustic theory with proper citations

### Completed Tasks

3.0 **Direct Radiator Simulation** ✅
- [x] `direct_radiator_electrical_impedance()` in `driver/response.py`
  - Literature: COMSOL (2020), Small (1972), Beranek (1954), Kinsler (1982)
  - Calculates electrical impedance and SPL for infinite baffle
- [x] Radiation impedance for circular piston in infinite baffle
  - Literature: Beranek (1954), Eq. 5.20
  - Bessel J₁ and Struve H₁ functions
- [x] Electrical impedance with acoustic load coupling
  - Literature: COMSOL (2020), Figure 2
  - Reflected impedance from mechanical domain

**Known Issues:**
- [x] ~~Voice coil inductance model needs refinement~~ ✅ RESOLVED
  - Implemented: Leach (2002) lossy inductor model
  - Literature: `literature/thiele_small/leach_2002_voice_coil_inductance.md`
  - Results: High-frequency error reduced from 688% to <5%
  - Validation: High-frequency test passes with 4.3% max error
- [ ] Hornresp validation data mismatch (KNOWN ISSUE)
  - Existing .sim files have Mmd=1.78g instead of 25g (wrong driver parameters)
  - Causes resonance at 165 Hz instead of 65 Hz
  - Workaround: High-frequency validation (>1 kHz) where data is consistent
  - TODO: Regenerate Hornresp data with correct parameters

### Pending Tasks

3.1 **Horn Profile Functions**
- [ ] Exponential horn: S(x) = S_t·exp(m·x) ✅ (Stage 2 complete)
  - Literature: Olson Eq. 5.12, Beranek Chapter 5
- [ ] Hyperbolic horn: S(x) = S_t·[cosh(mx) + T·sinh(mx)]²
  - Literature: Olson Eq. 5.30, Kinsler Section 9.8
- [ ] Conical horn: S(x) = S_t·(1 + x/x_t)²
  - Literature: Kinsler Section 9.7

3.2 **Cutoff Frequency Calculations**
- [ ] Exponential horn cutoff: f_c = c·m/(2π)
  - Literature: Olson Eq. 5.18
- [ ] Hyperbolic horn cutoff (depends on taper parameter T)
- [ ] Validate against Hornresp for various flare constants

3.3 **Acoustic Impedance Calculations**
- [ ] Throat impedance for finite exponential horn
  - Literature: Kinsler Eq. 9.6.4 (transmission line)
  - Input: horn geometry, frequency
  - Output: complex impedance Z_t
- [ ] Mouth radiation impedance
  - Literature: Beranek Eq. 5.20 (piston in infinite baffle)
  - Implement Bessel and Struve functions (use scipy.special)
- [ ] Characteristic impedance Z_0
  - Literature: Kinsler Eq. 9.5.12

3.4 **Frequency Response Calculation**
- [ ] Pressure response vs frequency
- [ ] Power output vs frequency
- [ ] Efficiency calculation
  - Literature: Beranek Chapter 8, Olson Section 5.11

3.5 **Directivity Patterns**
- [ ] Directivity index vs frequency
  - Literature: Beranek Chapter 8
- [ ] Polar plot generation (for visualization)

**Validation:**
- Create test cases with known horn geometries
- Compare impedance curves with Hornresp
- Verify cutoff frequency within <0.1%
- Verify impedance magnitude within <1% for f > 1.5·f_c
- Investigate and explain any discrepancies >1%

**Deliverables:**
- `simulation/horn_theory.py` - All horn profile functions
- `simulation/response.py` - Frequency response calculations
- `simulation/electrical_analogies.py` - Circuit representations
- Unit tests for each function with literature citations
- Validation test suite comparing with Hornresp

---

## Phase 4: Hornresp Export Functionality ✅

**Status:** Complete
**Deliverables:**
- [x] Document Hornresp input format (.inp, .txt)
- [x] Understand parameter naming conventions
- [x] `hornresp/export.py` with export functionality
- [x] Map gsd parameters to Hornresp format
- [x] Include metadata (driver name, date, gsd version)
- [x] Test export with B&C drivers
- [x] Validation data collected for infinite baffle tests (4 drivers)

### Tasks Completed

4.1 **Research Hornresp Input Format** ✅
- [x] Document Hornresp file format (.inp, .txt)
- [x] Understand parameter naming conventions
- [x] Test importing known driver files

4.2 **Export Module** ✅
- [x] Implement `hornresp/export.py`
- [x] `export_to_hornresp()` function
- [x] `driver_to_hornresp_record()` conversion
- [x] Map gsd parameters to Hornresp format
- [x] Include metadata (driver name, date, gsd version)

4.3 **Results Parser** ✅ (New in Phase 5)
- [x] Implement `hornresp/results_parser.py`
- [x] `load_hornresp_sim_file()` parser for _sim.txt files
- [x] Parse 16 columns: Freq, Ra, Xa, Za, SPL, Ze, Xd, phases, efficiency, etc.
- [x] `HornrespSimulationResult` dataclass

4.4 **CLI Commands**
- [ ] `gsd export <design>` - Export to Hornresp format ✅ (implemented)
- [ ] `gsd import <hornresp_file>` - Import from Hornresp (planned)

**Deliverables:**
- `hornresp/export.py` - Export functionality
- `hornresp/import.py` - Import functionality
- Test cases with known Hornresp files
- CLI commands for import/export

---

## Phase 5: Validation Framework (In Progress)

**Status:** Partially Complete
**Goal:** Automated validation against Hornresp

### Completed Tasks

5.1 **Reference Data Collection** ✅
- [x] B&C driver test cases created:
  - BC 8NDL51 (8" midrange)
  - BC 12NDL76 (12" mid-woofer)
  - BC 15DS115 (15" subwoofer)
  - BC 18PZW100 (18" subwoofer)
- [x] Hornresp simulations run for infinite baffle configuration
- [x] Results stored in `tests/validation/drivers/<driver>/infinite_baffle/`
  - `<driver>_inf.txt` - Hornresp input file
  - `<driver>_inf_sim.txt` - Hornresp simulation results (535 frequency points)
  - `metadata.json` - Validation metadata

5.2 **Comparison Functions** ✅
- [x] Implement `validation/compare.py`
- [x] `compare_electrical_impedance()` - Compare Ze magnitude and phase
- [x] `compare_electrical_impedance_phase()` - Phase comparison with wraparound
- [x] `compare_spl()` - Compare SPL in dB
- [x] Calculate error metrics:
  - Absolute error at each frequency
  - Percent error at each frequency
  - RMS error over frequency range
  - Maximum error and location
- [x] `generate_validation_report()` - Text-based reports
- [x] `ValidationResult` dataclass with worst error tracking

5.3 **Automated Validation Tests** ✅ (In Progress)
- [x] pytest fixtures for loading Hornresp reference data
- [x] BC 8NDL51 infinite baffle validation tests
- [ ] Validation passing (blocked by voice coil inductance issue)
- [ ] Pass/fail criteria based on tolerances:
  - Ze magnitude: <2% above resonance, <5% near resonance
  - Ze phase: <5° general, <10° near resonance
  - SPL: <3 dB (industry standard)

5.4 **Reporting** (Partial)
- [x] Text-based validation reports
- [ ] Side-by-side plots (gsd vs Hornresp)
- [ ] HTML validation reports
- [ ] CI integration (GitHub Actions)

### Current Status

**Validation Framework:** ✅ Complete
**Validation Tests:** ⏳ In Progress (blocked by inductance model)
**CLI Command:** ⏳ Pending (`gsd validate` command)

**Blocker:**
- Voice coil inductance model needs refinement for high-frequency accuracy
- Simple jωL_e model insufficient for >1 kHz
- Need to implement Leach (1991) model or similar lossy inductor model
- See ROADMAP Phase 4: "Investigation needed" for voice coil inductance

---

## Phase 6: CLI User Interface & Workflow (In Progress)

**Status:** Partially Complete

### Completed Tasks

6.1 **Driver Commands** ✅
- [x] `gsd driver list` - List B&C test drivers
- [x] `gsd driver show <name>` - Show driver parameters
- [x] Driver parameter validation and storage

6.2 **Export Commands** ✅
- [x] `gsd export <driver>` - Export to Hornresp format
- [x] `gsd export-all` - Batch export all drivers

### Pending Tasks

6.3 **Simulation Commands**
- [ ] `gsd simulate <design>` - Run simulation
- [ ] `gsd validate <driver>` - Validate against Hornresp (NEW)
  - Compare Ze magnitude and phase
  - Compare SPL
  - Generate validation report
- [ ] `gsd simulate --frequency-range <fmin> <fmax>`
- [ ] `gsd simulate --output <format>` (csv, json, plot)

6.4 **Visualization**
- [ ] Frequency response plot (dB vs Hz)
- [ ] Impedance plot (ohms vs Hz)
- [ ] Direct radiator infinite baffle visualization
- [ ] Interactive plots (matplotlib with interactive backend)

6.5 **Analysis Tools**
- [ ] `gsd analyze cutoff` - Show cutoff frequency
- [ ] `gsd analyze efficiency` - Calculate efficiency
- [ ] `gsd analyze impedance` - Throat impedance vs frequency

**Deliverables:**
- Complete `cli.py` with all commands
- Design storage (JSON format in `~/.gsd/designs/`)
- Plotting utilities
- Configuration management

---

## Phase 7: Optimization & Exploration Tools

**Status:** Pending
**Goal:** Automated parameter optimization and design exploration

### Tasks

7.1 **Parameter Sweep**
- [ ] `gsd sweep parameter <name> --range <min> <max> --steps <n>`
- [ ] Sweep one parameter while holding others constant
- [ ] Generate results showing effect on:
  - Cutoff frequency
  - Efficiency
  - Frequency response
  - Impedance
- [ ] Plot sweep results

7.2 **Multi-Objective Optimization**
- [ ] Integration with pymoo (already in dependencies)
- [ ] Define optimization objectives:
  - Minimize cutoff frequency
  - Maximize efficiency
  - Minimize horn size (volume)
  - Maximize bandwidth
- [ ] Constraints:
  - Maximum horn length
  - Maximum mouth size
  - Minimum throat size (driver compatibility)
- [ ] `gsd optimize <design> --objectives <obj1,obj2,...>`

7.3 **Pareto Front Analysis**
- [ ] Generate Pareto front for competing objectives
- [ ] Interactive exploration of Pareto-optimal designs
- [ ] Export trade-off analysis

7.4 **Design Space Exploration**
- [ ] Monte Carlo sampling of parameter space
- [ ] Sensitivity analysis (which parameters affect performance most)
- [ ] Design feasibility maps

7.5 **Validation of Optimized Designs**
- [ ] Automatically validate optimized designs against Hornresp
- [ ] Warn if optimization results violate assumptions
- [ ] Track validation statistics across optimization runs

**Deliverables:**
- `optimization/` module with sweep and optimization functions
- Optimization objective functions (with literature citations)
- Pareto front visualization
- Design exploration reports

---

## Future Enhancements (Beyond Phase 7)

These are not currently planned but may be considered later:

### Additional Enclosure Types
- [ ] Transmission line enclosures
- [x] Sealed (acoustic suspension) boxes ✅ (Implemented in Phase 1)
- [x] Ported (bass reflex) enclosures ✅ (Implemented Dec 2025)
- [ ] Bandpass enclosures

**Implementation Status:**
- Sealed boxes: Full simulation + Hornresp validation + B4 alignments
- Ported boxes: Helmholtz tuning, port sizing, electrical impedance, Hornresp export
- See `src/gsd/enclosure/` for implementation details

### Advanced Horn Features
- [ ] Folded horns (folding geometry)
- [ ] Multi-segment horns (different profiles in sections)
- [ ] Rear-loaded horns (open-back driver + front horn)
- [ ] Unity horn / synergy horn designs

### Driver Modeling
- [ ] Large-signal parameters (Bl(x), Cms(x))
- [ ] Nonlinear distortion prediction
- [ ] Thermal modeling (power compression)

### Visualization
- [ ] 3D horn geometry rendering
- [ ] Interactive parameter adjustment with real-time plots
- [ ] Directivity balloon plots

### Integration
- [ ] Web interface (Flask/Django)
- [ ] CAD export (STL for 3D printing)
- [ ] Integration with measurement tools (Clio, ARTA)

---

## Contribution Guidelines

We welcome contributions! Please ensure:

1. **All simulation code cites literature** per `CLAUDE.md`
2. **New features are validated against Hornresp** where applicable
3. **Tests are included** for new functionality
4. **Documentation is updated** (README, ROADMAP, docstrings)
5. **Code follows style guidelines** (black, isort, mypy passing)

## Timeline Estimates

These are rough order-of-magnitude estimates for planning purposes:

- Phase 1: ✅ Complete
- Phase 2: ✅ Complete
- Phase 3: ⏳ In Progress (direct radiator complete, horn profiles pending)
- Phase 4: ✅ Complete
- Phase 5: ⏳ 50% Complete (framework done, validation in progress)
- Phase 6: ⏳ 30% Complete (driver and export commands done)
- Phase 7: Pending

**Total to MVP:** ~2 months remaining

**Blockers:**
- Voice coil inductance model refinement (Leach 1991 or similar)
- High-frequency validation accuracy (>1 kHz)

---

## Success Criteria

The project is considered a success when:

1. ✅ All simulation algorithms cite literature
2. ⏳ Core horn types implemented (exponential ✅, hyperbolic pending, conical pending)
3. ⏳ Validation against Hornresp shows <1% agreement for well-behaved cases
   - ✅ Validation framework complete
   - ⏳ Direct radiator validation blocked by inductance model issue
4. ⏳ CLI provides complete workflow (driver → simulate → export → validate)
   - ✅ Driver commands working
   - ✅ Export working
   - ⏳ Validate command pending
   - ⏳ Simulate command pending
5. ⏳ Optimization tools can explore design space efficiently
6. ⏳ Documentation is comprehensive and accessible

---

*Last updated: 2025-12-26*
