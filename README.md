# bugworks GSD (Genetic Speaker Designer)

**A loudspeaker simulation engine with genetic algorithm optimization for enclosure and horn design**

> **⚠️ AI-Generated Code Disclaimer:** This repository was created with assistance from Claude Sonnet 4.5 using Claude Code. While the physics models are validated against Hornresp and the code is tested, **AI-generated code may contain mistakes**. Always verify results, validate in Hornresp before building, and review critical calculations carefully.

bugworks GSD is a Python-based tool that simulates loudspeaker enclosures and horns using acoustic theory from first principles, then uses genetic algorithms (NSGA-II) to automatically optimize designs for your objectives: flatness, F3, size, efficiency, and more.

## What It Does

GSD combines two capabilities:

1. **Physics-based Simulation** - Calculates frequency response, impedance, and SPL from Thiele-Small parameters
2. **Genetic Algorithm Optimization** - Evolves designs to find optimal enclosure and horn geometries for your target objectives

**Key Features:**
- Multi-objective optimization using NSGA-II (find Pareto-optimal designs)
- Optimize for: F3 (cutoff frequency), response flatness, enclosure size, efficiency
- Supports sealed boxes, ported enclosures, and horns
- **Physics models validated against Hornresp** (industry-standard simulation tool)
- Export to Hornresp for final validation before building
- All algorithms cite established acoustic literature

> **⚠️ Important:** While GSD's physics models are validated against Hornresp, **always validate your final design in Hornresp before building**. Use GSD for rapid exploration and optimization, then export to Hornresp for verification. This is especially important for AI-generated code—**verify before you build**.

## Quick Start

### Installation

```bash
git clone https://github.com/wokhouse/gsd.git
cd gsd
pip install -e .
```

### Python API (Recommended)

```python
from gsd.optimization import DesignAssistant

# Create design assistant
assistant = DesignAssistant()

# Optimize a sealed box for BC_12NDL76
result = assistant.optimize_design(
    driver_name="BC_12NDL76",
    enclosure_type="sealed",
    objectives=["f3", "size"],  # Minimize F3 and box size
    population_size=50,
    generations=30,
    top_n=5
)

# Inspect best designs
for design in result.best_designs:
    Vb_liters = design['parameters']['Vb'] * 1000
    F3_hz = design['objectives']['f3']
    print(f"Vb={Vb_liters:.1f}L, F3={F3_hz:.1f}Hz")
```

**Output:**
```
Vb=25.3L, F3=58.2Hz
Vb=31.8L, F3=52.1Hz
Vb=41.2L, F3=47.6Hz
```

### CLI

```bash
# List available drivers
gsd driver list

# Export driver to Hornresp format
gsd export BC_12NDL76 -o bc_12ndl76.txt

# Validate against Hornresp simulation
gsd validate compare BC_12NDL76 infinite_baffle
```

## Optimization Objectives

GSD can optimize for any combination of these objectives:

| Objective | Description | Minimize/Maximize |
|-----------|-------------|-------------------|
| `f3` | Cutoff frequency (-3dB point) | Lower is better |
| `flatness` | Response deviation from flat | Lower is better |
| `size` | Enclosure volume (m³) | Lower is better |
| `efficiency` | Reference efficiency (%) | Higher is better |

**Common combinations:**
- `["f3", "size"]` - Trade bass extension vs box size
- `["f3", "flatness"]` - Best bass with flat response
- `["f3", "flatness", "size"]` - Three-objective optimization

## Design Workflow

```
┌─────────────────┐
│  Import Driver  │  Load Thiele-Small parameters
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Define Goals   │  Choose objectives (F3, size, etc.)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Optimize       │  Genetic algorithm finds Pareto front
│  (NSGA-II)      │  of optimal designs
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Export        │  Generate Hornresp file
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ⚠️ Validate    │  Verify in Hornresp BEFORE building
└─────────────────┘
```

## Supported Enclosures

| Type | Status | Parameters Optimized |
|------|--------|---------------------|
| Sealed box | ✅ | Vb (volume) |
| Ported box | ✅ | Vb, Fb, port_area, port_length |
| Horn (exponential, hyperbolic, conical) | 🔄 | Throat area, mouth area, length, flare |

See [ROADMAP.md](ROADMAP.md) for development status.

## How It Works

### 1. Simulation Engine

GSD implements acoustic theory from first principles:

- **Small (1972)** - Closed-box and vented-box systems
- **Thiele (1971)** - Vented box alignments (B4, QB3, BB4)
- **Beranek (1954)** - Horn theory, radiation impedance
- **Olson (1947)** - Exponential and hyperbolic horns

Every algorithm cites literature and is validated against Hornresp.

### 2. Genetic Algorithm Optimization

GSD uses **NSGA-II** (Non-dominated Sorting Genetic Algorithm II):

1. **Initialize population** of random designs
2. **Evaluate** each design using physics simulation
3. **Rank** by Pareto dominance (non-dominated sorting)
4. **Select** parents from best designs
5. **Crossover & mutate** to create next generation
6. **Repeat** for N generations

**Result:** Pareto front of optimal designs where no objective can be improved without degrading another.

### 3. Pareto Front Analysis

```python
# After optimization, explore trade-offs
for design in result.pareto_front:
    size = design['objectives']['size']  # m³
    f3 = design['objectives']['f3']      # Hz
    print(f"Size: {size*1000:.1f}L → F3: {f3:.1f}Hz")
```

## Example: Subwoofer Design

```python
from gsd.optimization import DesignAssistant

assistant = DesignAssistant()

# Goal: Small subwoofer with F3 ≤ 55 Hz
result = assistant.optimize_design(
    driver_name="BC_12NDL76",
    enclosure_type="ported",
    objectives=["f3", "size"],
    population_size=80,
    generations=50,
    top_n=3
)

# Find designs meeting constraints
for design in result.best_designs:
    Vb = design['parameters']['Vb'] * 1000  # Convert to liters
    Fb = design['parameters']['Fb']
    F3 = design['objectives']['f3']

    if Vb <= 50 and F3 <= 55:
        print(f"✓ Optimal design: Vb={Vb:.1f}L, Fb={Fb:.1f}Hz, F3={F3:.1f}Hz")
```

## Pre-configured Drivers

GSD includes these B&C Speakers drivers:

- **BC_8NDL51** - 8" neodymium midbass
- **BC_12NDL76** - 12" neodylement mid-woofer
- **BC_15DS115** - 15" direct radiator subwoofer
- **BC_18PZW100** - 18" subwoofer

Plus DE250 compression driver, TC2/TC3/TC4 test drivers, and generic drivers.

Add your own by creating YAML files in `src/gsd/driver/data/`.

## Validation

### Physics Model Validation

GSD's acoustic simulation algorithms are validated against Hornresp (industry standard):

```bash
# Compare GSD vs Hornresp for specific configuration
gsd validate compare BC_8NDL51 infinite_baffle
```

**Acceptable tolerances:**
- Well above cutoff: <1% deviation
- Near cutoff: <2% deviation
- Close to cutoff: <5% deviation

See `tests/validation/` for validation datasets and results.

### ⚠️ Always Validate in Hornresp Before Building

**Workflow:**
1. Use GSD to explore and optimize designs rapidly
2. Export best designs to Hornresp format
3. Verify in Hornresp before building

**Why?**
- GSD provides validated physics models and genetic optimization
- Hornresp has decades of validation and real-world verification
- Different numerical approaches may produce slight variations
- **Your final design should always be verified in Hornresp**

```python
# After optimization, export to Hornresp
from gsd.hornresp.export import export_to_hornresp

export_to_hornresp(
    driver=driver,
    driver_name="MyDesign",
    output_path="my_design.txt",
    enclosure_type="sealed",
    Vb_liters=35.2
)
# Then import my_design.txt into Hornresp for final verification
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest --cov=gsd --cov-report=html

# Format code
black src/gsd tests
isort src/gsd tests
```

### Project Structure

```
gsd/
├── src/gsd/
│   ├── simulation/      # Acoustic simulation engine
│   ├── optimization/    # Genetic algorithm optimizer
│   ├── driver/          # Thiele-Small parameters
│   ├── enclosure/       # Sealed, ported, horn models
│   └── hornresp/        # Hornresp integration
├── literature/          # Acoustic theory references
└── tests/validation/    # Hornresp comparison data
```

## Citation

If you use GSD in your research:

```bibtex
@software{gsd,
  author = {bugworks},
  title = {bugworks GSD: Genetic Speaker Designer},
  year = {2025},
  url = {https://github.com/wokhouse/gsd}
}
```

## License

MIT License - see [LICENSE](LICENSE) file

## Acknowledgments

- **Hornresp** by David McBean - Industry-standard horn simulation
- **Olson, Beranek, Small, Thiele** - Foundational acoustic theory
- **Deb et al. (2002)** - NSGA-II genetic algorithm

---

**Built with science. Validated with Hornresp. Optimized with evolution.**
