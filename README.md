# bugworks GSD (Genetic Speaker Designer)
Shield: [![CC BY-SA 4.0][cc-by-sa-shield]][cc-by-sa]

**Loudspeaker enclosure design and simulation with Hornresp validation**

bugworks GSD (Genetic Speaker Designer) is a CLI tool for simulating horn-loaded loudspeaker enclosures using acoustic theory from first principles. Every algorithm is grounded in established literature and validated against Hornresp, the industry-standard horn simulation tool.

## Features

- **Automated optimization** - Multi-objective optimization using NSGA-II algorithm
- **Agent-friendly API** - Python API optimized for AI agent interaction
- **Enclosure recommendations** - Qts-based enclosure type suggestions
- **Sealed box support** - Complete sealed box simulation and optimization
- **Ported box support** - Bass reflex design with tuning optimization
- **Literature-based** - All algorithms cite established acoustic theory
- **Hornresp validation** - Results validated against Hornresp (in development)
- **Pareto analysis** - Explore trade-offs between competing objectives

## Project Status

**Phase 7.4 Complete** - bugworks GSD (Genetic Speaker Designer) has fully functional optimization and parameter sweep tools. Horn simulation is in development.

### ✅ Implemented (Phase 7)
- Multi-objective optimization (NSGA-II)
- Sealed box design and optimization
- Ported box design and optimization
- Enclosure type recommendations
- Agent-friendly Python API
- Constraint handling (physical and performance)
- Pareto front analysis
- **Parameter sweep with sensitivity analysis** (NEW!)
- **Automatic design recommendations** (optimal ranges, trends, diminishing returns)

### 🔄 In Development
- Horn simulation engine (exponential, hyperbolic, conical)
- Hornresp validation integration
- CLI interface for human users

### ⏳ Planned
- Folded horn support
- Multi-segment horn optimization
- Advanced visualizations

See [ROADMAP.md](ROADMAP.md) for detailed development phases.

## Installation

### Requirements

- Python 3.10 or higher
- Poetry (for development) or pip (for installation)

### Install from Source

```bash
# Clone the repository
git clone https://github.com/yourusername/gsd.git
cd gsd

# Create virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### Development Setup

```bash
# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (optional)
pre-commit install
```

## Quick Start

### 1. Import Driver Parameters

```bash
gsd driver import
```

You'll be prompted to enter Thiele-Small parameters:

```
Enter driver name: Eminence Delta-15
Enter resonance frequency Fs (Hz): 45
Enter DC resistance Re (ohms): 5.9
Enter Qes: 0.42
Enter Qms: 3.5
Enter Vas (liters): 175
Enter cone area Sd (sq cm): 855
...
Driver saved as 'eminence-delta-15'
```

### 2. Design a Horn Enclosure

```bash
gsd design new
```

```
Select driver: eminence-delta-15
Horn type [exponential/hyperbolic/conical]: exponential

Enter horn parameters:
  Throat area (sq cm): 50
  Mouth area (sq cm): 500
  Length (m): 1.5

Calculating horn parameters...
  Flare constant m: 4.25 1/m
  Cutoff frequency fc: 232 Hz
Design saved as 'eminence-delta-15-exp-horn'
```

### 3. Simulate Performance

```bash
gsd simulate eminence-delta-15-exp-horn --output plot
```

This generates:
- Frequency response curve (dB vs Hz)
- Throat impedance curve (ohms vs Hz)
- Directivity patterns
- Efficiency estimates

### 4. Export to Hornresp

```bash
gsd export eminence-delta-15-exp-horn --format hornresp
```

Generates a Hornresp input file for cross-validation:

```
File exported to: eminence-delta-15-exp-horn.inp
You can now open this file in Hornresp to verify the results.
```

### 5. Validate Against Hornresp

```bash
gsd validate eminence-delta-15-exp-horn --reference hornresp_results.txt
```

Generates a comparison report showing agreement between bugworks GSD (Genetic Speaker Designer) and Hornresp.

## AI/Agent Usage

bugworks GSD (Genetic Speaker Designer) provides a **Python API optimized for AI agents** (like Claude Code). All functions return structured data (dataclasses, not text) for easy programmatic processing.

### Quick Start for Agents

```python
from gsd.optimization import DesignAssistant

# Create design assistant
assistant = DesignAssistant()
```

### Available Drivers

```python
# Pre-configured B&C drivers
drivers = ["BC_8NDL51", "BC_12NDL76", "BC_15DS115", "BC_18PZW100"]

# You can also import custom drivers using Thiele-Small parameters
```

### 1. Get Enclosure Recommendation

```python
# Get recommended enclosure type based on driver characteristics
rec = assistant.recommend_design(
    driver_name="BC_12NDL76",
    max_volume_liters=50,      # Maximum enclosure size
    target_f3=60,               # Target cutoff frequency (Hz)
    enclosure_preference="auto"  # "auto", "sealed", "ported", or "horn"
)

# Returns DesignRecommendation dataclass:
print(f"Recommended: {rec.enclosure_type}")        # "sealed" or "ported"
print(f"Confidence: {rec.confidence:.0%}")         # 0.0 to 1.0
print(f"Reasoning: {rec.reasoning}")               # Explanation with citations
print(f"Parameters: {rec.suggested_parameters}")   # Dict of Vb, Fb, etc.
print(f"Performance: {rec.expected_performance}")  # Dict of F3, Qtc, etc.
print(f"Trade-offs: {rec.trade_offs}")             # Explanation of design choices

# Recommendation logic (from Small 1972):
# - Qts < 0.35  → Horn (high efficiency)
# - 0.35 ≤ Qts < 0.45 → Sealed box (transient response)
# - 0.45 ≤ Qts < 0.55 → Ported box (bass extension)
# - Qts ≥ 0.55  → Sealed box (high Qts)
```

### 2. Optimize Design (Multi-Objective)

```python
# Run automated optimization to find best designs
result = assistant.optimize_design(
    driver_name="BC_12NDL76",
    enclosure_type="sealed",           # "sealed" or "ported"
    objectives=["f3", "size"],         # Minimize F3 and enclosure size
    population_size=50,                # Population size (default: 100)
    generations=30,                    # Generations (default: 100)
    top_n=5                            # Return top 5 designs
)

# Returns OptimizationResult dataclass:
print(f"Success: {result.success}")                    # True if optimization completed
print(f"Found {result.n_designs_found} designs")       # Number on Pareto front
print(f"Algorithm: {result.optimization_metadata['algorithm']}")  # "NSGA-II"

# Access best designs
for i, design in enumerate(result.best_designs, 1):
    params = design['parameters']
    objs = design['objectives']

    if 'Fb' in params:  # Ported box has Fb parameter
        Vb_liters = params['Vb'] * 1000
        Fb_hz = params['Fb']
        F3_hz = objs['f3']
        print(f"Design #{i}: Vb={Vb_liters:.1f}L, Fb={Fb_hz:.1f}Hz, F3={F3_hz:.1f}Hz")
    else:  # Sealed box
        Vb_liters = params['Vb'] * 1000
        F3_hz = objs['f3']
        print(f"Design #{i}: Vb={Vb_liters:.1f}L, F3={F3_hz:.1f}Hz")
```

### Available Objectives

```python
# All objectives are minimized (lower is better)
objectives = [
    "f3",         # Cutoff frequency (-3dB point) in Hz
    "flatness",   # Response flatness (deviation from perfect flat)
    "efficiency", # Reference efficiency (negated for minimization)
    "size"        # Enclosure volume in m³
]

# Common combinations:
# - ["f3", "size"]          → Trade bass extension vs box size
# - ["f3", "flatness"]      → Best bass response with flat response
# - ["f3"]                  → Single-objective: minimize F3 only
# - ["f3", "flatness", "size"] → Three-objective optimization
```

### 3. Explore Design Space

```python
# Example: Find smallest sealed box that achieves F3 ≤ 60 Hz
result = assistant.optimize_design(
    driver_name="BC_12NDL76",
    enclosure_type="sealed",
    objectives=["f3", "size"],
    population_size=50,
    generations=30,
    top_n=10
)

# Filter results for F3 ≤ 60 Hz
for design in result.best_designs:
    if design['objectives']['f3'] <= 60:
        Vb = design['parameters']['Vb'] * 1000
        print(f"Vb={Vb:.1f}L gives F3={design['objectives']['f3']:.1f}Hz")
```

### 4. Parameter Sweep (Design Space Exploration)

```python
# Sweep a parameter to see how it affects performance
sweep = assistant.sweep_parameter(
    driver_name="BC_12NDL76",
    enclosure_type="sealed",
    parameter="Vb",
    param_min=0.010,  # 10L
    param_max=0.050,  # 50L
    steps=50
)

# Access sweep results
print(f"Swept: {sweep.parameter_swept}")
print(f"Points: {len(sweep.parameter_values)}")

# Find best F3
import numpy as np
best_idx = np.nanargmin(sweep.results["F3"])
best_f3 = sweep.results["F3"][best_idx]
best_vb = sweep.parameter_values[best_idx] * 1000
print(f"Best F3: {best_f3:.1f} Hz at Vb={best_vb:.1f}L")

# Check sensitivity
print(f"F3 sensitivity: {sweep.sensitivity_analysis['f3_sensitivity']:.2f}")
print(f"Trend: {sweep.sensitivity_analysis['trend_description']}")

# View recommendations
for rec in sweep.recommendations:
    print(f"  • {rec}")
```

**What Parameter Sweep Provides:**

- **Complete visibility**: See entire relationship between parameter and performance
- **Sensitivity analysis**: Understand which objectives are most affected by parameter changes
- **Optimal ranges**: Identify "good enough" parameter ranges (not just optimal points)
- **Diminishing returns**: Detect when further increases give minimal benefit
- **Trend identification**: See if increasing parameter helps or hurts performance

**Sweep vs Optimization:**

```python
# Use sweep when:
# - You have 1-2 parameters to explore
# - You want to understand the physics/relationships
# - You need to identify "good enough" ranges
# - You want sensitivity analysis

# Use optimization when:
# - You have 3+ parameters (ported box with Vb, Fb, port dimensions)
# - You want the optimal design for multiple objectives
# - You have complex constraints
# - You just want the answer, not the exploration
```

### 5. Ported Box Optimization

```python
# Ported box optimization includes tuning frequency (Fb)
result = assistant.optimize_design(
    driver_name="BC_12NDL76",
    enclosure_type="ported",
    objectives=["f3", "size"],
    population_size=80,        # Ported boxes need larger populations
    generations=50,
    top_n=5
)

# Ported box parameters include:
# - Vb: Box volume (m³)
# - Fb: Tuning frequency (Hz)
# - port_area: Port cross-sectional area (m²)
# - port_length: Port length (m)

for design in result.best_designs:
    Vb = design['parameters']['Vb'] * 1000
    Fb = design['parameters']['Fb']
    F3 = design['objectives']['f3']
    print(f"Vb={Vb:.1f}L, Fb={Fb:.1f}Hz → F3={F3:.1f}Hz")
```

### 6. Complete Example: Design Subwoofer

```python
from gsd.optimization import DesignAssistant

# Goal: Design a subwoofer with BC_12NDL76
# Constraints: Max 50L volume, target F3 ≤ 55 Hz

assistant = DesignAssistant()

# Step 1: Get recommendation
rec = assistant.recommend_design(
    driver_name="BC_12NDL76",
    max_volume_liters=50,
    target_f3=55
)

print(f"Recommended: {rec.enclosure_type}")
print(f"Reasoning: {rec.reasoning}")

# Step 2: Optimize for best performance within constraints
result = assistant.optimize_design(
    driver_name="BC_12NDL76",
    enclosure_type=rec.enclosure_type,
    objectives=["f3", "size"],
    population_size=60,
    generations=40,
    top_n=3
)

# Step 3: Select best design meeting constraints
best_design = None
for design in result.best_designs:
    Vb_liters = design['parameters']['Vb'] * 1000
    F3 = design['objectives']['f3']

    if Vb_liters <= 50 and F3 <= 55:
        best_design = design
        break

if best_design:
    print(f"\n✓ Found optimal design:")
    print(f"  Vb = {best_design['parameters']['Vb']*1000:.1f} L")
    print(f"  F3 = {best_design['objectives']['f3']:.1f} Hz")
    if 'Fb' in best_design['parameters']:
        print(f"  Fb = {best_design['parameters']['Fb']:.1f} Hz")
else:
    print("\n✗ No design meets constraints. Try relaxing requirements.")
```

### API Reference

#### DesignAssistant

```python
class DesignAssistant:
    """High-level API for enclosure design optimization."""

    def recommend_design(
        self,
        driver_name: str,
        objectives: List[str] = None,
        max_volume_liters: float = None,
        target_f3: float = None,
        enclosure_preference: str = "auto",
        efficiency_priority: bool = False
    ) -> DesignRecommendation:
        """Recommend enclosure type and initial design."""

    def optimize_design(
        self,
        driver_name: str,
        enclosure_type: str,
        objectives: List[str],
        constraints: Dict[str, float] = None,
        population_size: int = 100,
        generations: int = 100,
        top_n: int = 10
    ) -> OptimizationResult:
        """Run multi-objective optimization using NSGA-II."""
```

#### Data Structures

```python
@dataclass
class DesignRecommendation:
    enclosure_type: str              # "sealed", "ported", or "horn"
    confidence: float                # 0.0 to 1.0
    reasoning: str                   # Explanation with literature citations
    suggested_parameters: Dict[str, float]  # Vb, Fb, etc.
    expected_performance: Dict[str, float]   # F3, Qtc, Fc, etc.
    alternatives: List[Dict]         # Other enclosure types considered
    trade_offs: str                  # Design trade-off explanation
    validation_notes: List[str]      # Any validation warnings

@dataclass
class OptimizationResult:
    success: bool                    # True if optimization completed
    pareto_front: List[Dict]         # All Pareto-optimal designs
    n_designs_found: int             # Number on Pareto front
    best_designs: List[Dict]         # Top N designs ranked
    parameter_names: List[str]       # ["Vb", "Fb", ...]
    objective_names: List[str]       # ["f3", "size", ...]
    optimization_metadata: Dict      # Algorithm, population, etc.
    warnings: List[str]              # Any optimization warnings
```

### Theory Behind Optimization

bugworks GSD (Genetic Speaker Designer) uses **NSGA-II** (Non-dominated Sorting Genetic Algorithm II) for multi-objective optimization:

- **Literature**: Deb et al. (2002) - "A fast and elitist multiobjective genetic algorithm: NSGA-II"
- **Pareto Front**: Set of optimal designs where no objective can be improved without degrading another
- **Trade-offs**: Explore the design space to understand trade-offs between objectives (e.g., F3 vs size)

### Supported Enclosure Types

| Type | Status | Parameters | Use Case |
|------|--------|------------|----------|
| Sealed | ✅ Implemented | Vb | Transient response, moderate bass |
| Ported | ✅ Implemented | Vb, Fb, port_area, port_length | Extended bass, lower F3 |
| Horn | ⏳ Planned | Throat area, mouth area, length, flare | High efficiency, controlled directivity |

### Literature Citations

All optimization algorithms cite established literature:

- **Enclosure parameters**: Small (1972) - Closed-box system parameters
- **Alignments**: Thiele (1971) - Vented box alignments (B4, QB3, BB4)
- **Objectives**: Beranek (1954) - Frequency response and efficiency
- **Optimization**: Deb (2002) - NSGA-II multi-objective algorithm

See individual function docstrings for specific citations.

## Workflow

bugworks GSD (Genetic Speaker Designer) follows a literature-first design workflow:

```
┌─────────────────┐
│  Import Driver  │  Thiele-Small parameters
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Design Horn    │  Specify geometry (throat, mouth, length)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Simulate      │  Calculate response (cites literature)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Export        │  Generate Hornresp input file
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Validate      │  Compare with Hornresp results
└────────┬────────┘
         │
         ▼
    ┌─────────┐
    │ Iterate │  Adjust parameters based on validation
    └─────────┘
```

## Literature and Theory

bugworks GSD (Genetic Speaker Designer) is built on established acoustic theory. Every simulation algorithm cites the literature it implements.

### Foundational References

- **Olson (1947)** - Elements of Acoustical Engineering
  - Exponential and hyperbolic horn profiles
  - Horn equation and cutoff frequency
  - Throat impedance calculations

- **Beranek (1954)** - Acoustics
  - Finite horn corrections (mouth termination)
  - Radiation impedance
  - Directivity patterns

- **Kinsler et al. (1982)** - Fundamentals of Acoustics
  - Rigorous derivation of horn equation
  - Transmission line approach for finite horns
  - Driver-horn interaction

See the [`literature/`](literature/) directory for complete reference documentation with specific equations.

### Citation Example

```python
def calculate_horn_cutoff(flare_constant: float, speed_of_sound: float = 343.0) -> float:
    """
    Calculate the cutoff frequency of an exponential horn.

    Based on Olson (1947), Equation 5.18 and Beranek (1954), Chapter 5.

    Literature:
    - literature/horns/olson_1947.md - Exponential horn theory, Eq. 5.18
    - literature/horns/beranek_1954.md - Horn impedance, Chapter 5

    Args:
        flare_constant: Horn flare constant m (1/m)
        speed_of_sound: Speed of sound (m/s), default 343 m/s at 20°C

    Returns:
        Cutoff frequency f_c (Hz)

    Validation:
        Compare with Hornresp cutoff frequency calculation.
        Expected agreement: <0.1% deviation.
    """
    # Olson (1947), Eq. 5.18: f_c = c·m/(2π)
    return (speed_of_sound * flare_constant) / (2 * math.pi)
```

**This citation requirement ensures all algorithms are traceable to established theory.**

## Validation Against Hornresp

Hornresp is the industry standard for horn simulation. bugworks GSD (Genetic Speaker Designer) validates all results against Hornresp:

### Validation Process

1. Implement algorithm from literature with proper citations
2. Create test case with known horn parameters
3. Run bugworks GSD (Genetic Speaker Designer) simulation
4. Run Hornresp with identical parameters
5. Compare results (impedance, frequency response, etc.)
6. Document agreement percentage

### Acceptable Tolerances

- **Well above cutoff** (f > 2·f_c): <1% deviation
- **Near cutoff** (f ≈ 1.2·f_c to 2·f_c): <2% deviation
- **Close to cutoff** (f ≈ f_c): <5% deviation (numerical sensitivity)
- **Below cutoff** (f < f_c): qualitative agreement only

This ensures bugworks GSD (Genetic Speaker Designer) provides accurate exploration results while maintaining transparency about theoretical foundations.

## Development

### Project Structure

```
gsd/
├── README.md              # This file
├── CLAUDE.md              # Project-specific instructions (citation requirements)
├── ROADMAP.md             # Development phases
├── pyproject.toml         # Project configuration
├── literature/            # Acoustic theory references
│   ├── README.md          # Citation guide
│   └── horns/             # Horn theory papers
│       ├── olson_1947.md
│       ├── beranek_1954.md
│       └── kinsler_1982.md
└── src/gsd/
    ├── cli.py             # CLI entry point
    ├── driver/            # Driver parameter handling
    ├── simulation/        # Horn simulation engine (cites literature)
    ├── hornresp/          # Hornresp integration
    ├── validation/        # Validation framework
    └── optimization/      # Parameter optimization (future)
```

### Contributing

We welcome contributions! Please ensure:

1. ✅ **All simulation code cites literature** per [`CLAUDE.md`](CLAUDE.md)
2. ✅ **New features are validated against Hornresp** where applicable
3. ✅ **Tests are included** for new functionality
4. ✅ **Code passes style checks** (black, isort, mypy)
5. ✅ **Documentation is updated** (docstrings, README)

See [`CLAUDE.md`](CLAUDE.md) for detailed coding conventions.

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=gsd --cov-report=html

# Run validation tests only
pytest tests/validation/
```

### Code Style

```bash
# Format code
black src/gsd tests

# Sort imports
isort src/gsd tests

# Type checking
mypy src/gsd
```

## Dependencies

### Core Dependencies
- **numpy** - Numerical computations
- **scipy** - Scientific functions (Bessel, Struve functions for horn theory)
- **pydantic** - Data validation
- **click** - CLI interface
- **matplotlib** - Plotting
- **pandas** - Data handling

### Optimization
- **pymoo** - Multi-objective optimization (Phase 7)

### Development
- **pytest** - Testing
- **pytest-cov** - Coverage reporting
- **black** - Code formatting
- **isort** - Import sorting
- **mypy** - Type checking

## Configuration

bugworks GSD (Genetic Speaker Designer) stores configuration and data in `~/.gsd/`:

```
~/.gsd/
├── config.yaml          # User configuration
├── drivers/             # Saved driver profiles
│   └── eminence-delta-15.json
└── designs/             # Saved enclosure designs
    └── eminence-delta-15-exp-horn.json
```

### Example Configuration

```yaml
# ~/.gsd/config.yaml
defaults:
  temperature: 20        # Celsius
  air_density: 1.18      # kg/m³
  speed_of_sound: 343    # m/s

simulation:
  frequency_range:
    min: 20              # Hz
    max: 20000           # Hz
    points: 1000         # Logarithmic spacing

plotting:
  figure_size: [10, 6]
  dpi: 100
  style: 'seaborn-v0_8-darkgrid'

validation:
  hornresp_path: '/path/to/hornresp'
  tolerance_high: 0.01   # 1% for f > 2*fc
  tolerance_near: 0.02   # 2% for f ≈ 1.2*fc to 2*fc
  tolerance_close: 0.05  # 5% for f ≈ fc
```

## Roadmap

See [ROADMAP.md](ROADMAP.md) for detailed development phases:

- **Phase 1**: ✅ Literature review and algorithm selection
- **Phase 2**: 🔄 Driver parameter input system
- **Phase 3**: ⏳ Horn simulation engine
- **Phase 4**: ⏳ Hornresp export functionality
- **Phase 5**: ⏳ Validation framework
- **Phase 6**: ⏳ CLI user interface and workflow
- **Phase 7**: ⏳ Optimization and exploration tools

## FAQ

### How accurate is bugworks GSD (Genetic Speaker Designer) compared to Hornresp?

bugworks GSD (Genetic Speaker Designer) implements the same acoustic theory as Hornresp. For well-behaved cases (frequencies well above cutoff), we expect agreement within <1%. Differences may occur due to:
- Numerical methods (discretization vs analytical)
- Mouth termination models
- Frequency range and resolution

We actively validate against Hornresp and document all discrepancies.

### Why implement from literature instead of using existing libraries?

This ensures:
1. **Transparency** - Every algorithm is traceable to established theory
2. **Validation** - We can verify each step against Hornresp
3. **Education** - The code documents the connection between theory and practice
4. **Correctness** - Literature-cited code is more likely to be correct

Existing libraries often lack proper documentation of theoretical foundations.

### Can I use bugworks GSD (Genetic Speaker Designer) for sealed or ported enclosures?

**Yes!** bugworks GSD (Genetic Speaker Designer) supports sealed and ported enclosures with automated optimization. Use the Python API for design assistance and optimization. See the "AI/Agent Usage" section below.

### What horn types are supported?

Currently implemented (in development):
- Exponential horns
- Hyperbolic horns (with taper parameter)
- Conical horns

Planned:
- Folded horns
- Multi-segment horns
- Transmission line enclosures

### How do I cite bugworks GSD (Genetic Speaker Designer) in my research?

If you use bugworks GSD (Genetic Speaker Designer) in your research, please cite both the software and the underlying literature:

```bibtex
@software{gsd,
  author = {Your Name},
  title = {bugworks GSD (Genetic Speaker Designer): Horn-loaded Loudspeaker Simulation with Literature-based Validation},
  year = {2025},
  url = {https://github.com/yourusername/gsd}
}

@book{olson1947,
  author = {Olson, Harry F.},
  title = {Elements of Acoustical Engineering},
  year = {1947},
  publisher = {D. Van Nostrand Company}
}
```

## Acknowledgments

- **Hornresp** by David McBean - The industry-standard horn simulation tool that makes validation possible
- **Olson, Beranek, Kinsler** and other authors of foundational acoustic theory texts
- **Python scientific community** - numpy, scipy, matplotlib, and the entire ecosystem

## Contact

- **Issues**: [GitHub Issues](https://github.com/yourusername/gsd/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/gsd/discussions)
- **Email**: your.email@example.com

---

**Built with science, validated with Hornresp, designed for accuracy.**
