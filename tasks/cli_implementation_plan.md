# CLI Implementation Plan for Optimization and Plotting Factories

## Objective

Add CLI commands for both OptimizationScriptFactory and PlotFactory to provide command-line interfaces for:
1. Running optimizations from configuration
2. Generating plots from optimization results

## Current State

### Existing CLI Structure
- Main entry: `src/gsd/cli.py` using Click framework
- Current commands: `driver`, `export`, `validate`, `sim-*`
- No optimization or plotting CLI commands exist yet

### Existing Factories
1. **OptimizationScriptFactory** (`src/gsd/optimization/factory.py`)
   - ✅ Fully implemented
   - Supports configuration-driven optimization
   - Exports results to JSON

2. **PlotFactory** (`src/gsd/visualization/factory.py`)
   - ✅ Fully implemented
   - Supports 5 plot types (pareto_2d, pareto_3d, spl_response, horn_profile, parameter_distribution)
   - Loads results from JSON files

## Implementation Plan

### Phase 1: Optimization CLI Commands

Create new file: `src/gsd/cli/optimize.py`

#### Command 1.1: `gsd optimize run`

Run optimization from configuration.

```bash
gsd optimize run \
    --driver BC_15DS115 \
    --enclosure-type multisegment_horn \
    --objectives f3,flatness \
    --preset bass_horn \
    --output results.json
```

**Options:**
- `--driver`: Driver name (required)
- `--enclosure-type`: Enclosure type (required)
  - Options: exponential_horn, multisegment_horn, mixed_profile_horn, conical_horn, sealed, ported
- `--objectives`: Comma-separated objective names (required)
  - Common: f3, flatness, size, efficiency
- `--preset`: Parameter space preset (optional)
  - For horns: bass_horn, midrange_horn, fullrange_horn
  - For sealed/ported: uses defaults
- `--output`: Output JSON file path (default: auto-generated)
- `--config`: YAML config file (alternative to CLI options)
- `--pop-size`: Population size (default: from preset)
- `--generations`: Number of generations (default: from preset)
- `--seed`: Random seed (default: None)

**Implementation:**
```python
@cli.command()
@click.option('--driver', required=True, help='Driver name')
@click.option('--enclosure-type', required=True, type=click.Choice([...]))
@click.option('--objectives', required=True, help='Comma-separated objectives')
@click.option('--preset', default='default')
@click.option('--output', type=click.Path())
@click.option('--config', type=click.Path(exists=True))
@click.option('--pop-size', type=int)
@click.option('--generations', type=int)
@click.option('--seed', type=int)
def optimize_run(driver, enclosure_type, objectives, preset, output, config, pop_size, generations, seed):
    """Run optimization using OptimizationScriptFactory."""
    from gsd.optimization import OptimizationScriptFactory, OptimizationConfig

    # Load config from YAML if provided
    if config:
        opt_config = OptimizationConfig.from_yaml(config)
    else:
        # Build config from CLI options
        opt_config = OptimizationConfig(
            driver_name=driver,
            enclosure_type=enclosure_type,
            objectives=objectives.split(','),
            parameter_space_preset=preset,
            population_size=pop_size,
            n_generations=generations,
            seed=seed,
        )

    # Run optimization
    factory = OptimizationScriptFactory(opt_config)
    result = factory.run()

    # Save results
    if output is None:
        from datetime import datetime
        output = f"optimization_{driver}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    factory.save_results(result, output)
    click.echo(f"✓ Optimization complete: {result.n_designs_found} designs found")
    click.echo(f"✓ Results saved to: {output}")
```

#### Command 1.2: `gsd optimize preset`

Run optimization using predefined presets.

```bash
gsd optimize preset \
    --driver BC_15DS115 \
    --preset f3_target \
    --f3-target 35 \
    --output results.json
```

**Options:**
- `--driver`: Driver name (required)
- `--preset`: Preset name (required)
  - Available presets: f3_target, size_vs_f3, compact_bass, flat_response, max_efficiency, balanced, mini_monitor, bookshelf, subwoofer
- `--output`: Output JSON file path
- Additional preset-specific options (e.g., `--f3-target`, `--max-volume`)

**Implementation:**
```python
@cli.command()
@click.option('--driver', required=True)
@click.option('--preset', required=True, type=click.Choice(PRESETS))
@click.option('--output', type=click.Path())
@click.option('--f3-target', type=float)
@click.option('--max-volume', type=float)
@click.option('--target-flatness', type=float)
# ... other preset-specific options
def optimize_preset(driver, preset, output, **kwargs):
    """Run optimization using predefined preset."""
    from gsd.optimization.presets import get_preset_config

    # Get preset config
    opt_config = get_preset_config(preset, driver=driver, **kwargs)

    # Run optimization
    factory = OptimizationScriptFactory(opt_config)
    result = factory.run()

    # Save results
    factory.save_results(result, output or f"{preset}_results.json")
    click.echo(f"✓ Preset '{preset}' optimization complete")
```

#### Command 1.3: `gsd optimize list-presets`

List all available optimization presets.

```bash
gsd optimize list-presets
```

**Implementation:**
```python
@cli.command()
def optimize_list_presets():
    """List all available optimization presets."""
    from gsd.optimization.config import _PRESET_CONFIGS

    click.echo("Available Optimization Presets:")
    for name, config in _PRESET_CONFIGS.items():
        click.echo(f"  {name}: {config.get('description', 'No description')}")
```

### Phase 2: Plotting CLI Commands

Create new file: `src/gsd/cli/plot.py`

#### Command 2.1: `gsd plot create`

Create a single plot from optimization results.

```bash
gsd plot create \
    --type pareto_2d \
    --input results.json \
    --output pareto.png \
    --x-objective f3 \
    --y-objective flatness
```

**Options:**
- `--type`: Plot type (required)
  - Options: pareto_2d, pareto_3d, spl_response, horn_profile, parameter_distribution
- `--input`: Input JSON file (required)
- `--output`: Output image file (default: auto-generated)
- `--x-objective`: X-axis objective for Pareto plots
- `--y-objective`: Y-axis objective for Pareto plots
- `--z-objective`: Color objective for 3D Pareto plots
- `--num-designs`: Limit to N designs
- `--design-indices`: Specific design indices (comma-separated)
- `--frequency-min`: Min frequency for SPL plots (Hz)
- `--frequency-max`: Max frequency for SPL plots (Hz)
- `--voltage`: Input voltage for SPL (V)
- `--dpi`: Image resolution (default: 150)
- `--style`: Plot style (default, dark, presentation, publication)
- `--show`: Display plot interactively

**Implementation:**
```python
@cli.command()
@click.option('--type', 'plot_type', required=True, type=click.Choice(PlotFactory.PLOT_TYPES))
@click.option('--input', 'input_file', required=True, type=click.Path(exists=True))
@click.option('--output', type=click.Path())
@click.option('--x-objective')
@click.option('--y-objective')
@click.option('--z-objective')
@click.option('--num-designs', type=int)
@click.option('--design-indices')
@click.option('--frequency-min', type=float, default=20)
@click.option('--frequency-max', type=float, default=20000)
@click.option('--voltage', type=float, default=2.83)
@click.option('--dpi', type=int, default=150)
@click.option('--style', default='default')
@click.option('--show', is_flag=True)
def plot_create(plot_type, input_file, output, x_objective, y_objective, z_objective,
                num_designs, design_indices, frequency_min, frequency_max,
                voltage, dpi, style, show):
    """Create a single plot from optimization results."""
    from gsd.visualization import PlotFactory, PlotConfig

    # Build config
    config = PlotConfig(
        plot_type=plot_type,
        data_source=input_file,
        x_objective=x_objective or 'f3',
        y_objective=y_objective or 'flatness',
        z_objective=z_objective,
        num_designs=num_designs,
        design_indices=[int(i) for i in design_indices.split(',')] if design_indices else None,
        frequency_range=(frequency_min, frequency_max),
        voltage=voltage,
        dpi=dpi,
        style=style,
        show_plot=show,
    )

    # Generate plot
    factory = PlotFactory(config)
    fig = factory.create_plot()

    # Save
    if output is None:
        from pathlib import Path
        output = Path(input_file).stem + f"_{plot_type}.png"

    fig.savefig(output, dpi=dpi, bbox_inches='tight')
    click.echo(f"✓ Plot saved to: {output}")
```

#### Command 2.2: `gsd plot batch`

Create multiple plots at once.

```bash
gsd plot batch \
    --input results.json \
    --output-dir plots/ \
    --plots pareto_2d,spl_response,horn_profile
```

**Options:**
- `--input`: Input JSON file (required)
- `--output-dir`: Output directory (required)
- `--plots`: Comma-separated plot types to generate (required)
- All other options from `plot create` apply globally

**Implementation:**
```python
@cli.command()
@click.option('--input', 'input_file', required=True, type=click.Path(exists=True))
@click.option('--output-dir', 'output_dir', required=True, type=click.Path())
@click.option('--plots', required=True, help='Comma-separated plot types')
@click.option('--dpi', type=int, default=150)
@click.option('--style', default='default')
def plot_batch(input_file, output_dir, plots, dpi, style):
    """Create multiple plots from optimization results."""
    from pathlib import Path
    from gsd.visualization import PlotFactory, PlotConfig

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    plot_types = plots.split(',')
    results = []

    for plot_type in plot_types:
        config = PlotConfig(
            plot_type=plot_type,
            data_source=input_file,
            output_path=str(output_dir / f"{plot_type}.png"),
            dpi=dpi,
            style=style,
        )

        factory = PlotFactory(config)
        fig = factory.create_plot()
        fig.savefig(config.output_path, dpi=dpi, bbox_inches='tight')

        results.append(config.output_path)
        click.echo(f"✓ Generated: {config.output_path}")

    click.echo(f"\n✓ Generated {len(results)} plots in {output_dir}/")
```

#### Command 2.3: `gsd plot auto`

Generate all standard plots for optimization results.

```bash
gsd plot auto \
    --input results.json \
    --output-dir plots/
```

This is a convenience wrapper that runs:
- pareto_2d
- parameter_distribution
- spl_response (first 5 designs)
- horn_profile (first design)

**Implementation:**
```python
@cli.command()
@click.option('--input', 'input_file', required=True, type=click.Path(exists=True))
@click.option('--output-dir', 'output_dir', default='plots', type=click.Path())
@click.option('--dpi', type=int, default=150)
def plot_auto(input_file, output_dir, dpi):
    """Generate all standard plots for optimization results."""
    from pathlib import Path
    import subprocess
    import sys

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Define standard plots
    standard_plots = [
        ('pareto_2d', None),
        ('parameter_distribution', None),
        ('spl_response', '--num-designs 5'),
        ('horn_profile', None),
    ]

    for plot_type, extra_args in standard_plots:
        cmd = [
            sys.executable, '-m', 'gsd.cli', 'plot', 'create',
            '--type', plot_type,
            '--input', input_file,
            '--output', str(output_dir / f"{plot_type}.png"),
            '--dpi', str(dpi),
        ]

        if extra_args:
            cmd.extend(extra_args.split())

        subprocess.run(cmd, check=True)

    click.echo(f"✓ Generated {len(standard_plots)} standard plots in {output_dir}/")
```

#### Command 2.4: `gsd plot list-types`

List all available plot types.

```bash
gsd plot list-types
```

**Implementation:**
```python
@cli.command()
def plot_list_types():
    """List all available plot types."""
    from gsd.visualization.factory import PlotFactory

    click.echo("Available Plot Types:")
    for plot_type in PlotFactory.PLOT_TYPES:
        click.echo(f"  {plot_type}")
```

### Phase 3: CLI Integration

#### 3.1: Update `src/gsd/cli.py`

Add new command groups:

```python
# Add after existing imports
from gsd.cli import optimize, plot

# Add new command groups
cli.add_command(optimize.cli)
cli.add_command(plot.cli)
```

#### 3.2: Create `src/gsd/cli/__init__.py`

```python
"""CLI subcommands for gsd."""

from gsd.cli import optimize, plot
```

#### 3.3: Create `src/gsd/cli/optimize.py`

```python
"""Optimization CLI commands.

Provides command-line interface for running optimizations using
OptimizationScriptFactory.
"""

import click
from pathlib import Path

@click.group()
def optimize():
    """Optimization commands using OptimizationScriptFactory."""
    pass

@optimize.command(name='run')
@click.option('--driver', required=True, help='Driver name')
@click.option('--enclosure-type', required=True,
              type=click.Choice(['exponential_horn', 'multisegment_horn', 'mixed_profile_horn',
                                'conical_horn', 'sealed', 'ported']))
@click.option('--objectives', required=True, help='Comma-separated objective names')
@click.option('--preset', default='default', help='Parameter space preset')
@click.option('--output', type=click.Path(), help='Output JSON file')
@click.option('--config', type=click.Path(exists=True), help='YAML config file')
@click.option('--pop-size', type=int, help='Population size')
@click.option('--generations', type=int, help='Number of generations')
@click.option('--seed', type=int, help='Random seed')
def optimize_run(driver, enclosure_type, objectives, preset, output, config,
                 pop_size, generations, seed):
    """Run optimization from configuration."""
    # Implementation from Phase 1.1
    pass

@optimize.command(name='preset')
@click.option('--driver', required=True)
@click.option('--preset', required=True)
# ... other options
def optimize_preset(driver, preset, **kwargs):
    """Run optimization using predefined preset."""
    # Implementation from Phase 1.2
    pass

@optimize.command(name='list-presets')
def optimize_list_presets():
    """List all available optimization presets."""
    # Implementation from Phase 1.3
    pass
```

#### 3.4: Create `src/gsd/cli/plot.py`

```python
"""Plotting CLI commands.

Provides command-line interface for generating plots using PlotFactory.
"""

import click

@click.group()
def plot():
    """Plotting commands using PlotFactory."""
    pass

@plot.command(name='create')
@click.option('--type', 'plot_type', required=True, type=click.Choice([...]))
@click.option('--input', 'input_file', required=True, type=click.Path(exists=True))
@click.option('--output', type=click.Path())
# ... other options
def plot_create(plot_type, input_file, output, **kwargs):
    """Create a single plot from optimization results."""
    # Implementation from Phase 2.1
    pass

@plot.command(name='batch')
@click.option('--input', 'input_file', required=True)
@click.option('--output-dir', 'output_dir', required=True)
@click.option('--plots', required=True)
# ... other options
def plot_batch(input_file, output_dir, plots, **kwargs):
    """Create multiple plots from optimization results."""
    # Implementation from Phase 2.2
    pass

@plot.command(name='auto')
@click.option('--input', 'input_file', required=True)
@click.option('--output-dir', 'output_dir', default='plots')
# ... other options
def plot_auto(input_file, output_dir, **kwargs):
    """Generate all standard plots."""
    # Implementation from Phase 2.3
    pass

@plot.command(name='list-types')
def plot_list_types():
    """List all available plot types."""
    # Implementation from Phase 2.4
    pass
```

### Phase 4: Examples and Testing

#### Example Workflow: Full Optimization + Plotting

```bash
# Step 1: Run optimization
gsd optimize run \
    --driver BC_15DS115 \
    --enclosure-type multisegment_horn \
    --objectives f3,flatness \
    --preset bass_horn \
    --pop-size 20 \
    --generations 50 \
    --output bass_horn_results.json

# Step 2: Generate all standard plots
gsd plot auto \
    --input bass_horn_results.json \
    --output-dir plots/

# Step 3: Create custom plot
gsd plot create \
    --type pareto_3d \
    --input bass_horn_results.json \
    --x-objective f3 \
    --y-objective flatness \
    --z-objective size \
    --output custom_3d_pareto.png
```

#### Example Workflow: Using Presets

```bash
# Use predefined F3 target preset
gsd optimize preset \
    --driver BC_21DS115 \
    --preset f3_target \
    --f3-target 34 \
    --output subwoofer_opt.json

# Generate plots
gsd plot batch \
    --input subwoofer_opt.json \
    --output-dir subwoofer_plots/ \
    --plots pareto_2d,spl_response,parameter_distribution
```

#### Example Workflow: Quick Design Comparison

```bash
# Compare first 10 designs
gsd plot create \
    --type spl_response \
    --input results.json \
    --num-designs 10 \
    --output comparison.png
```

### Phase 5: Documentation

#### 5.1: Update README.md

Add CLI usage section with examples.

#### 5.2: Create CLI Reference Documentation

Document all commands, options, and usage patterns.

#### 5.3: Add Help Text

Ensure all commands have comprehensive help text (already in Click decorators).

## File Structure After Implementation

```
src/gsd/
├── cli.py                           # Main CLI entry point (update)
├── cli/
│   ├── __init__.py                  # CLI subcommands package
│   ├── optimize.py                  # Optimization commands (NEW)
│   └── plot.py                      # Plotting commands (NEW)
├── optimization/
│   └── factory.py                   # OptimizationScriptFactory (existing)
└── visualization/
    └── factory.py                   # PlotFactory (existing)
```

## Success Criteria

1. ✅ All optimization commands work (`run`, `preset`, `list-presets`)
2. ✅ All plotting commands work (`create`, `batch`, `auto`, `list-types`)
3. ✅ CLI integrates with existing `gsd` command
4. ✅ Full workflow test: optimize → generate plots → verify outputs
5. ✅ Comprehensive help text available (`--help`)
6. ✅ Error handling for invalid inputs

## Testing Plan

```bash
# Test optimization
gsd optimize run --driver BC_8NDL51 --enclosure-type sealed --objectives f3,size --output test_opt.json

# Test plotting
gsd plot create --type pareto_2d --input test_opt.json --output test_pareto.png

# Test batch plotting
gsd plot batch --input test_opt.json --output-dir test_plots/ --plots pareto_2d,horn_profile

# Test auto plots
gsd plot auto --input test_opt.json --output-dir auto_plots/

# Verify help
gsd optimize --help
gsd optimize run --help
gsd plot --help
gsd plot create --help
```

## Implementation Priority

1. **High Priority:**
   - `gsd optimize run` - Core optimization command
   - `gsd plot create` - Core plotting command
   - `gsd plot auto` - Convenience command for standard plots

2. **Medium Priority:**
   - `gsd optimize preset` - Preset-based optimization
   - `gsd plot batch` - Batch plotting
   - `gsd optimize list-presets` - List available presets

3. **Low Priority:**
   - `gsd plot list-types` - List plot types (can use --help)
   - Advanced options (custom constraints, specialized plotting options)

## Notes

- Use Click framework (already used in cli.py)
- Follow existing CLI patterns and conventions
- Ensure proper error handling and user feedback
- Add progress indicators for long-running optimizations
- Support both CLI options and YAML config files
- Make output paths optional with sensible defaults
- Use auto-generated timestamps for output files when not specified
