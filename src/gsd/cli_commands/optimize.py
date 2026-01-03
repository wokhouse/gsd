"""
Optimization CLI commands.

Provides command-line interface for running optimizations using
OptimizationScriptFactory.

Literature:
    - Deb et al. (2002) - NSGA-II multi-objective optimization algorithm
    - Small (1972) - Closed-box and vented box system parameters
    - Olson (1947) - Horn theory and cutoff frequency
"""

import click
from pathlib import Path
from datetime import datetime
import json


@click.group()
def optimize():
    """Optimization commands using OptimizationScriptFactory."""
    pass


@optimize.command(name='run')
@click.option('--driver', required=True, help='Driver name (e.g., BC_15DS115)')
@click.option('--enclosure-type', required=True, type=click.Choice([
    'exponential_horn', 'multisegment_horn', 'mixed_profile_horn',
    'conical_horn', 'sealed', 'ported'
]), help='Type of enclosure')
@click.option('--objectives', required=True, help='Comma-separated objective names (e.g., f3,flatness)')
@click.option('--preset', default='bass_horn', help='Parameter space preset (default: bass_horn)')
@click.option('--output', type=click.Path(), help='Output JSON file path')
@click.option('--config', type=click.Path(exists=True), help='YAML config file (alternative to CLI options)')
@click.option('--pop-size', type=int, help='Population size (default: 100)')
@click.option('--generations', type=int, help='Number of generations (default: 100)')
@click.option('--seed', type=int, help='Random seed for reproducibility')
@click.option('--quiet', '-q', is_flag=True, help='Suppress progress output')
def optimize_run(driver, enclosure_type, objectives, preset, output, config,
                 pop_size, generations, seed, quiet):
    """
    Run optimization from configuration.

    This command executes multi-objective optimization using the
    OptimizationScriptFactory. You can specify parameters via CLI options
    or provide a YAML configuration file.

    \b
    Valid objectives:
        - f3: Minimize -3dB cutoff frequency
        - f3_deviation: Minimize deviation from target F3
        - volume: Minimize enclosure volume
        - flatness: Minimize passband ripple
        - efficiency: Maximize efficiency
        - passband_flatness: Minimize passband ripple in specific range

    \b
    Examples:
        # Run optimization with CLI options
        gsd optimize run --driver BC_8NDL51 --enclosure-type sealed \\
            --objectives f3,size --output test_opt.json

        # Run horn optimization with custom parameters
        gsd optimize run --driver BC_15DS115 \\
            --enclosure-type multisegment_horn \\
            --objectives f3,flatness \\
            --preset bass_horn \\
            --pop-size 50 --generations 100 \\
            --output results.json

        # Run from YAML config
        gsd optimize run --config my_config.yaml

    Literature:
        - Deb et al. (2002) - NSGA-II multi-objective optimization
        - Small (1972) - Closed-box system parameters
    """
    from gsd.optimization.factory import OptimizationScriptFactory
    from gsd.optimization.config import OptimizationConfig, AlgorithmConfig

    # Load config from YAML if provided
    if config:
        click.echo(f"Loading configuration from: {config}")
        opt_config = OptimizationConfig.from_yaml(config)
        if quiet:
            opt_config.verbose = False
    else:
        # Build config from CLI options
        click.echo(f"Building configuration for: {driver} - {enclosure_type}")

        # Parse objectives
        objective_list = [obj.strip() for obj in objectives.split(',')]

        # Build algorithm config
        algo_config = AlgorithmConfig(
            type="nsga2",
            pop_size=pop_size or 100,
            n_generations=generations or 100,
        )

        # Create optimization config
        opt_config = OptimizationConfig(
            driver_name=driver,
            enclosure_type=enclosure_type,
            objectives=objective_list,
            parameter_space_preset=preset,
            algorithm=algo_config,
            save_results=True,
            verbose=not quiet,
        )

    # Set seed if provided
    if seed is not None:
        import numpy as np
        np.random.seed(seed)
        click.echo(f"Random seed set to: {seed}")

    # Run optimization
    click.echo("\nStarting optimization...")
    factory = OptimizationScriptFactory(opt_config)
    result = factory.run()

    # Save results
    if output is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output = f"optimization_{driver}_{enclosure_type}_{timestamp}.json"

    # Ensure output directory exists
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert result to dict and save
    result_dict = {
        "success": result.success,
        "n_designs_found": result.n_designs_found,
        "pareto_front": result.pareto_front,
        "best_designs": result.best_designs,
        "parameter_names": result.parameter_names,
        "objective_names": result.objective_names,
        "optimization_metadata": result.optimization_metadata,
        "convergence_info": result.convergence_info,
        "warnings": result.warnings,
    }

    with open(output, 'w') as f:
        json.dump(result_dict, f, indent=2)

    click.echo(f"\n✓ Optimization complete!")
    click.echo(f"✓ Found {result.n_designs_found} Pareto-optimal designs")
    click.echo(f"✓ Results saved to: {output}")


@optimize.command(name='preset')
@click.option('--driver', required=True, help='Driver name')
@click.option('--preset', 'preset_name', required=True, type=click.Choice([
    'f3_target', 'size_vs_f3', 'compact_bass', 'max_efficiency',
    'flat_response', 'balanced', 'large_bass_horn', 'midrange_horn', 'folded_compact',
    'sealed_butterworth', 'sealed_compact', 'sealed_deep_bass', 'sealed_car',
    'ported_b4', 'ported_qb3', 'ported_bb4', 'ported_compact', 'ported_car_audio'
]), help='Preset name')
@click.option('--enclosure-type', default='multisegment_horn', type=click.Choice([
    'exponential_horn', 'multisegment_horn', 'mixed_profile_horn',
    'conical_horn', 'sealed', 'ported'
]), help='Enclosure type (default: multisegment_horn)')
@click.option('--output', type=click.Path(), help='Output JSON file path')
@click.option('--f3-target', type=float, help='Target F3 frequency (Hz)')
@click.option('--max-volume', type=float, help='Maximum volume (liters)')
@click.option('--f3-max', type=float, help='Maximum acceptable F3 (Hz)')
@click.option('--min-efficiency', type=float, help='Minimum efficiency (0-1)')
@click.option('--pop-size', type=int, help='Population size (default: from preset)')
@click.option('--generations', type=int, help='Number of generations (default: from preset)')
@click.option('--seed', type=int, help='Random seed for reproducibility')
@click.option('--quiet', '-q', is_flag=True, help='Suppress progress output')
@click.option('--plot', is_flag=True, help='Generate plots after optimization')
@click.option('--plot-preset', type=click.Choice(['overview', 'spl', 'quality', 'correlations']),
              default='overview', help='Plot preset to use with --plot (default: overview)')
@click.option('--plot-output-dir', type=click.Path(), help='Plot output directory (default: plots/)')
@click.option('--plot-dpi', type=int, default=150, help='Plot image resolution')
@click.option('--plot-style', default='default', help='Plot style (default, dark, presentation)')
@click.option('--num-spl-designs', type=int, default=5, help='Number of designs for SPL plot (overrides preset)')
def optimize_preset(driver, preset_name, enclosure_type, output,
                    f3_target, max_volume, f3_max, min_efficiency,
                    pop_size, generations, seed, quiet, plot, plot_preset,
                    plot_output_dir, plot_dpi, plot_style, num_spl_designs):
    """
    Run optimization using predefined preset.

    Presets provide pre-configured objective/constraint combinations
    for common optimization scenarios.

    \b
    Horn Presets:
        f3_target: Optimize for specific cutoff frequency with smooth response
        size_vs_f3: Explore trade-off between enclosure size and bass extension
        compact_bass: Small enclosure with acceptable bass extension
        max_efficiency: Maximize horn efficiency at target frequency
        flat_response: Prioritize smooth frequency response over extension
        balanced: Balanced trade-off between size, extension, and quality
        large_bass_horn: Large bass horn for maximum extension
        midrange_horn: Optimize midrange horn for smooth response
        folded_compact: Optimize horn for compact folded implementation

    \b
    Sealed Box Presets:
        sealed_butterworth: Maximally flat sealed box (Qtc=0.707)
        sealed_compact: Small sealed box for space-constrained designs
        sealed_deep_bass: Large sealed box for deep bass extension
        sealed_car: Car audio optimized (small box with cabin gain)

    \b
    Ported Box Presets:
        ported_b4: Butterworth B4 alignment (maximally flat)
        ported_qb3: Quasi-Butterworth 3rd order (tighter bass)
        ported_bb4: Extended bass shelf (more bass output)
        ported_compact: Compact ported design
        ported_car_audio: Car audio optimized (small box, higher tuning)

    \b
    Examples:
        # Use sealed_butterworth preset with plots
        gsd optimize preset --driver BC_8NDL51 \\
            --preset sealed_butterworth --enclosure-type sealed \\
            --output sealed_sub.json --plot

        # Use ported_b4 preset with custom plot directory
        gsd optimize preset --driver BC_12NDL76 \\
            --preset ported_b4 --enclosure-type ported \\
            --output ported_sub.json --plot --plot-output-dir my_plots/

        # Use compact_bass preset with custom volume constraint
        gsd optimize preset --driver BC_8NDL51 \\
            --preset sealed_compact --max-volume 30 \\
            --output compact_sealed.json --plot --num-spl-designs 3

        # Generate high-res plots with custom style
        gsd optimize preset --driver BC_15DS115 \\
            --preset compact_bass --enclosure-type multisegment_horn \\
            --plot --plot-dpi 300 --plot-style dark

    Literature:
        - Deb et al. (2002) - NSGA-II multi-objective optimization
        - Small (1972) - Closed-box system parameters
        - Thiele (1971) - Vented box alignments
    """
    from gsd.optimization.factory import OptimizationScriptFactory
    from gsd.optimization.config import OptimizationConfig, AlgorithmConfig

    # Build constraints from CLI options
    constraints = {}

    if f3_target is not None:
        constraints['f3_target'] = f3_target

    if max_volume is not None:
        constraints['max_volume'] = max_volume

    if f3_max is not None:
        constraints['f3_max'] = f3_max

    if min_efficiency is not None:
        constraints['min_efficiency'] = min_efficiency

    # Build algorithm config
    algo_config = AlgorithmConfig(
        type="nsga2",
        pop_size=pop_size or 100,
        n_generations=generations or 100,
    )

    # Create config from preset
    click.echo(f"Using preset: {preset_name}")
    opt_config = OptimizationConfig.from_preset(
        preset_name,
        driver_name=driver,
        enclosure_type=enclosure_type,
        constraints=constraints,
        algorithm={
            'type': algo_config.type,
            'pop_size': algo_config.pop_size,
            'n_generations': algo_config.n_generations,
        },
        verbose=not quiet,
    )

    # Set seed if provided
    if seed is not None:
        import numpy as np
        np.random.seed(seed)
        click.echo(f"Random seed set to: {seed}")

    # Run optimization
    click.echo("\nStarting optimization...")
    factory = OptimizationScriptFactory(opt_config)
    result = factory.run()

    # Save results
    if output is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output = f"{preset_name}_{driver}_{timestamp}.json"

    # Ensure output directory exists
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert result to dict and save
    result_dict = {
        "success": result.success,
        "n_designs_found": result.n_designs_found,
        "pareto_front": result.pareto_front,
        "best_designs": result.best_designs,
        "parameter_names": result.parameter_names,
        "objective_names": result.objective_names,
        "optimization_metadata": result.optimization_metadata,
        "convergence_info": result.convergence_info,
        "warnings": result.warnings,
    }

    with open(output, 'w') as f:
        json.dump(result_dict, f, indent=2)

    click.echo(f"\n✓ Preset '{preset_name}' optimization complete!")
    click.echo(f"✓ Found {result.n_designs_found} Pareto-optimal designs")
    click.echo(f"✓ Results saved to: {output}")

    # Generate plots if requested
    if plot:
        from gsd.visualization.factory import PlotFactory
        from gsd.visualization.config import PlotConfig
        from gsd.visualization.presets import expand_preset_to_configs

        # Determine plot output directory
        if plot_output_dir is None:
            # Use directory containing the results file
            plot_output_path = Path(output).parent / "plots"
        else:
            plot_output_path = Path(plot_output_dir)

        plot_output_path.mkdir(parents=True, exist_ok=True)

        click.echo(f"\nGenerating plots...")
        click.echo(f"Output directory: {plot_output_path}")
        click.echo(f"Using plot preset: {plot_preset}")

        # Build preset configuration
        overrides = {"dpi": plot_dpi, "style": plot_style} if plot_style != "default" else {}
        if num_spl_designs != 5:
            # User specified custom num_spl_designs
            overrides["num_designs"] = num_spl_designs

        preset_config = expand_preset_to_configs(plot_preset, output, overrides=overrides)

        plot_results = []
        for i, pc in enumerate(preset_config, 1):
            plot_type = pc.pop("plot_type")
            click.echo(f"[{i}/{len(preset_config)}] Creating {plot_type}...")

            try:
                # Build PlotConfig from preset dict
                config = PlotConfig(
                    plot_type=plot_type,
                    data_source=pc.pop("data_source"),
                    dpi=pc.pop("dpi", plot_dpi),
                    style=pc.pop("style", plot_style),
                    **pc
                )

                factory = PlotFactory(config)
                fig = factory.create_plot()

                output_file = plot_output_path / f"{plot_type}.png"
                fig.savefig(str(output_file), dpi=plot_dpi, bbox_inches='tight')

                plot_results.append(str(output_file))
                click.echo(f"  ✓ Generated: {output_file.name}")

            except Exception as e:
                click.echo(f"  ✗ Failed: {e}")
                continue

        click.echo(f"\n✓ Generated {len(plot_results)}/{len(preset_config)} plots")
        click.echo(f"✓ Plots saved to: {plot_output_path}")


@optimize.command(name='list-presets')
def optimize_list_presets():
    """List all available optimization presets."""
    from gsd.optimization.presets import OPTIMIZATION_PRESETS

    click.echo("\nAvailable Optimization Presets:")
    click.echo("=" * 80)

    for name, config in OPTIMIZATION_PRESETS.items():
        click.echo(f"\n{name}:")
        click.echo(f"  Description: {config['description']}")
        click.echo(f"  Objectives: {', '.join(config['objectives'])}")
        click.echo(f"  Parameter Space: {config['parameter_space_preset']}")
        click.echo(f"  Use Cases:")
        for use_case in config['typical_use_cases']:
            click.echo(f"    - {use_case}")

    click.echo("\n" + "=" * 80)
    click.echo("\nUsage:")
    click.echo("  gsd optimize preset --driver BC_15DS115 --preset f3_target")
