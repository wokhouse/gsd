"""
Plotting CLI commands.

Provides command-line interface for generating plots using PlotFactory.

Literature:
    - Matplotlib documentation - Plotting best practices
    - Small (1972) - Loudspeaker enclosure response characteristics
    - Olson (1947) - Horn theory (for geometry plots)
"""

import click
from pathlib import Path


@click.group()
def plot():
    """Plotting commands using PlotFactory."""
    pass


@plot.command(name='create')
@click.option('--type', 'plot_type', required=True, type=click.Choice([
    'pareto_2d', 'pareto_3d', 'spl_response',
    'horn_profile', 'parameter_distribution'
]), help='Plot type')
@click.option('--input', 'input_file', required=True, type=click.Path(exists=True),
              help='Input JSON file from optimization')
@click.option('--output', type=click.Path(), help='Output image file')
@click.option('--x-objective', default='f3', help='X-axis objective for Pareto plots')
@click.option('--y-objective', default='flatness', help='Y-axis objective for Pareto plots')
@click.option('--z-objective', help='Color objective for 3D Pareto plots')
@click.option('--num-designs', type=int, help='Limit to N designs')
@click.option('--design-indices', help='Specific design indices (comma-separated)')
@click.option('--frequency-min', type=float, default=20, help='Min frequency for SPL plots (Hz)')
@click.option('--frequency-max', type=float, default=20000, help='Max frequency for SPL plots (Hz)')
@click.option('--voltage', type=float, default=2.83, help='Input voltage for SPL (V)')
@click.option('--dpi', type=int, default=150, help='Image resolution')
@click.option('--style', default='default', help='Plot style (default, dark, presentation)')
@click.option('--width', type=int, default=12, help='Figure width (inches)')
@click.option('--height', type=int, default=8, help='Figure height (inches)')
@click.option('--show', is_flag=True, help='Display plot interactively')
def plot_create(plot_type, input_file, output, x_objective, y_objective, z_objective,
                num_designs, design_indices, frequency_min, frequency_max,
                voltage, dpi, style, width, height, show):
    """
    Create a single plot from optimization results.

    Generates publication-quality plots from optimization results.
    Supports Pareto fronts, SPL responses, horn profiles, and parameter distributions.

    \b
    Plot types:
        - pareto_2d: 2D Pareto front scatter plot
        - pareto_3d: 3D Pareto front scatter plot
        - spl_response: SPL frequency response curve
        - horn_profile: Horn cross-section geometry
        - parameter_distribution: Parameter distribution (box plots)

    \b
    Examples:
        # Create Pareto front
        gsd plot create --type pareto_2d --input results.json \\
            --x-objective f3 --y-objective flatness --output pareto.png

        # Create SPL response for first 5 designs
        gsd plot create --type spl_response --input results.json \\
            --num-designs 5 --output spl.png

        # Create 3D Pareto front with custom objectives
        gsd plot create --type pareto_3d --input results.json \\
            --x-objective f3 --y-objective flatness --z-objective volume \\
            --output pareto_3d.png

        # Create plot and display interactively
        gsd plot create --type pareto_2d --input results.json --show

    Literature:
        - Matplotlib documentation - Plotting best practices
        - Small (1972) - Loudspeaker enclosure response
    """
    from gsd.visualization.factory import PlotFactory
    from gsd.visualization.config import PlotConfig

    # Parse design indices
    design_idx_list = None
    if design_indices:
        design_idx_list = [int(i.strip()) for i in design_indices.split(',')]

    # Build config
    config = PlotConfig(
        plot_type=plot_type,
        data_source=input_file,
        x_objective=x_objective,
        y_objective=y_objective,
        z_objective=z_objective,
        num_designs=num_designs,
        design_indices=design_idx_list,
        frequency_range=(frequency_min, frequency_max),
        voltage=voltage,
        dpi=dpi,
        style=style,
        figure_size=(width, height),
        show_plot=show,
    )

    # Generate plot
    click.echo(f"Generating {plot_type} plot...")
    factory = PlotFactory(config)
    fig = factory.create_plot()

    # Determine output path
    if output is None:
        input_path = Path(input_file)
        output = str(input_path.stem + f"_{plot_type}.png")

    # Save or show
    if show:
        import matplotlib.pyplot as plt
        plt.show()
    else:
        fig.savefig(output, dpi=dpi, bbox_inches='tight')
        click.echo(f"✓ Plot saved to: {output}")


@plot.command(name='batch')
@click.option('--input', 'input_file', required=True, type=click.Path(exists=True),
              help='Input JSON file from optimization')
@click.option('--output-dir', 'output_dir', required=True, type=click.Path(),
              help='Output directory for plots')
@click.option('--plots', required=True, help='Comma-separated plot types to generate')
@click.option('--dpi', type=int, default=150, help='Image resolution')
@click.option('--style', default='default', help='Plot style')
@click.option('--num-designs', type=int, help='Limit to N designs for SPL plots')
def plot_batch(input_file, output_dir, plots, dpi, style, num_designs):
    """
    Create multiple plots at once.

    Generates multiple plots from the same optimization results.
    Useful for creating comprehensive analysis reports.

    \b
    Examples:
        # Generate Pareto and SPL plots
        gsd plot batch --input results.json --output-dir plots/ \\
            --plots pareto_2d,spl_response

        # Generate all standard plots
        gsd plot batch --input results.json --output-dir analysis/ \\
            --plots pareto_2d,pareto_3d,spl_response,horn_profile,parameter_distribution

        # Generate with custom settings
        gsd plot batch --input results.json --output-dir plots/ \\
            --plots spl_response,pareto_2d --dpi 300 --num-designs 10
    """
    from gsd.visualization.factory import PlotFactory
    from gsd.visualization.config import PlotConfig

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    plot_types = [p.strip() for p in plots.split(',')]
    results = []

    click.echo(f"Generating {len(plot_types)} plots...")

    for i, plot_type in enumerate(plot_types, 1):
        click.echo(f"[{i}/{len(plot_types)}] Creating {plot_type}...")

        try:
            config = PlotConfig(
                plot_type=plot_type,
                data_source=input_file,
                dpi=dpi,
                style=style,
                num_designs=num_designs,
            )

            factory = PlotFactory(config)
            fig = factory.create_plot()

            output_file = output_path / f"{plot_type}.png"
            fig.savefig(str(output_file), dpi=dpi, bbox_inches='tight')

            results.append(str(output_file))
            click.echo(f"  ✓ Generated: {output_file}")

        except Exception as e:
            click.echo(f"  ✗ Failed: {e}")
            continue

    click.echo(f"\n✓ Generated {len(results)}/{len(plot_types)} plots in {output_dir}/")


@plot.command(name='auto')
@click.option('--input', 'input_file', required=True, type=click.Path(exists=True),
              help='Input JSON file from optimization')
@click.option('--output-dir', 'output_dir', default='plots', type=click.Path(),
              help='Output directory (default: plots/)')
@click.option('--dpi', type=int, default=150, help='Image resolution')
@click.option('--style', default='default', help='Plot style')
@click.option('--num-spl-designs', type=int, default=5, help='Number of designs for SPL plot')
@click.option('--preset', type=click.Choice(['overview', 'spl', 'quality', 'correlations']),
              help='Use preset plot configuration')
def plot_auto(input_file, output_dir, dpi, style, num_spl_designs, preset):
    """
    Generate plots for optimization results.

    This command generates plots from optimization results. Use --preset to
    generate predefined plot collections, or omit it for standard plots.

    \b
    Standard plots (without --preset):
      - pareto_2d
      - parameter_distribution
      - spl_response (first N designs)
      - horn_profile

    \b
    Preset options:
      - overview: Quick assessment (pareto_2d, parameter_distribution, spl_response)
      - spl: Acoustic performance focus (spl_response, pareto_2d f3 vs efficiency)
      - quality: Qualitative metrics (wavefront vs impedance, flatness vs f3, parameters)
      - correlations: Parameter-objective relationship analysis (correlation_matrix, quality_dashboard)

    \b
    Examples:
        # Generate all standard plots
        gsd plot auto --input results.json

        # Use preset for specific analysis
        gsd plot auto --input results.json --preset spl

        # Generate with custom output directory
        gsd plot auto --input results.json --output-dir my_plots/

        # Generate high-resolution plots
        gsd plot auto --input results.json --preset quality --dpi 300

    Literature:
        - Matplotlib documentation - Plotting best practices
        - Small (1972) - Loudspeaker enclosure response
    """
    from gsd.visualization.factory import PlotFactory
    from gsd.visualization.config import PlotConfig
    from gsd.visualization.presets import expand_preset_to_configs

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Determine plot configurations
    if preset:
        # Use preset configuration
        click.echo(f"Using preset: {preset}")
        preset_config = expand_preset_to_configs(
            preset,
            input_file,
            overrides={"dpi": dpi, "style": style} if style != "default" else None
        )
        plot_configs = []
        for pc in preset_config:
            # Build PlotConfig from preset dict
            config = PlotConfig(
                plot_type=pc.pop("plot_type"),
                data_source=pc.pop("data_source"),
                dpi=pc.pop("dpi", dpi),
                style=pc.pop("style", style),
                **pc
            )
            plot_configs.append((config, config.plot_type))
    else:
        # Use standard plots
        standard_plots = [
            ('pareto_2d', None),
            ('parameter_distribution', None),
            ('spl_response', num_spl_designs),
            ('horn_profile', None),
        ]
        plot_configs = []
        for plot_type, num_designs in standard_plots:
            config = PlotConfig(
                plot_type=plot_type,
                data_source=input_file,
                dpi=dpi,
                style=style,
                num_designs=num_designs,
            )
            plot_configs.append((config, plot_type))

    results = []
    click.echo(f"Generating plots...")

    for i, (config, plot_type) in enumerate(plot_configs, 1):
        click.echo(f"[{i}/{len(plot_configs)}] Creating {plot_type}...")

        try:
            factory = PlotFactory(config)
            fig = factory.create_plot()

            output_file = output_path / f"{plot_type}.png"
            fig.savefig(str(output_file), dpi=dpi, bbox_inches='tight')

            results.append(str(output_file))
            click.echo(f"  ✓ Generated: {output_file}")

        except Exception as e:
            click.echo(f"  ✗ Failed: {e}")
            continue

    click.echo(f"\n✓ Generated {len(results)}/{len(plot_configs)} plots in {output_dir}/")
    click.echo("\nGenerated plots:")
    for result in results:
        click.echo(f"  - {Path(result).name}")


@plot.command(name='list-types')
def plot_list_types():
    """List all available plot types with descriptions."""
    from gsd.visualization.factory import PlotFactory

    plot_descriptions = {
        'pareto_2d': '2D Pareto front scatter plot showing trade-offs between two objectives',
        'pareto_3d': '3D Pareto front scatter plot showing trade-offs between three objectives',
        'spl_response': 'SPL frequency response curves for selected designs',
        'horn_profile': 'Horn cross-section geometry showing expansion profile',
        'parameter_distribution': 'Box plots showing parameter ranges across Pareto front',
    }

    click.echo("\nAvailable Plot Types:")
    click.echo("=" * 80)

    for plot_type in PlotFactory.PLOT_TYPES:
        description = plot_descriptions.get(plot_type, 'No description available')
        click.echo(f"\n{plot_type}:")
        click.echo(f"  {description}")

    click.echo("\n" + "=" * 80)
    click.echo("\nUsage:")
    click.echo("  gsd plot create --type <type> --input results.json")
    click.echo("\nExamples:")
    click.echo("  gsd plot create --type pareto_2d --input results.json")
    click.echo("  gsd plot create --type spl_response --input results.json --num-designs 5")


@plot.command(name='list-presets')
def plot_list_presets():
    """List all available plot presets with descriptions."""
    from gsd.visualization.presets import PLOT_PRESETS

    click.echo("\nAvailable Plot Presets:")
    click.echo("=" * 80)

    for name, config in sorted(PLOT_PRESETS.items()):
        click.echo(f"\n{name}:")
        click.echo(f"  Description: {config['description']}")

        # Show plot types in this preset
        plot_types = [pt['type'] for pt in config['plot_types']]
        click.echo(f"  Plot types: {', '.join(plot_types)}")

        # Show use cases
        if config.get('typical_use_cases'):
            click.echo(f"  Use cases:")
            for use_case in config['typical_use_cases']:
                click.echo(f"    - {use_case}")

    click.echo("\n" + "=" * 80)
    click.echo("\nUsage:")
    click.echo("  gsd plot auto --input results.json --preset <preset>")
    click.echo("\nExamples:")
    click.echo("  gsd plot auto --input results.json --preset overview")
    click.echo("  gsd plot auto --input results.json --preset spl")
    click.echo("  gsd plot auto --input results.json --preset quality")
