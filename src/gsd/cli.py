"""
bugworks GSD CLI interface.

Provides command-line interface for driver management and Hornresp export.
Based on Click for CLI commands and prompts.

Usage:
    gsd driver import           # Interactive T/S parameter entry
    gsd driver list             # List available B&C drivers
    gsd export <driver>         # Export driver to Hornresp format
"""

import click
from pathlib import Path

from gsd.driver.parameters import ThieleSmallParameters
from gsd.hornresp.export import export_to_hornresp, batch_export_to_hornresp
from gsd.validation.commands import (
    validate_generate_input,
    validate_parse_output,
    validate_run,
    validate_status,
    validate_migrate
)

# Import CLI subcommands
from gsd.cli_commands import optimize, plot


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """
    bugworks GSD (Genetic Speaker Designer) - Loudspeaker enclosure design and simulation tool.

    Initial focus on horn-loaded enclosures with validation against Hornresp.
    """
    pass


@cli.group()
def driver():
    """Driver parameter management commands."""
    pass


@cli.group()
def validate():
    """Validation commands for comparing gsd with Hornresp."""
    pass


@driver.command(name="import")
@click.option("--name", prompt="Driver name", help="Name/identifier for the driver")
@click.option("--M-ms", prompt="Moving mass (kg)", type=float, help="M_ms: Moving mass (kg)")
@click.option("--C-ms", prompt="Compliance (m/N)", type=float, help="C_ms: Suspension compliance (m/N)")
@click.option("--R-ms", prompt="Mechanical resistance (N·s/m)", type=float, default=0.0, help="R_ms: Mechanical resistance")
@click.option("--R-e", prompt="DC resistance (ohms)", type=float, help="R_e: Voice coil DC resistance (Ω)")
@click.option("--L-e", prompt="Inductance (H)", type=float, help="L_e: Voice coil inductance (H)")
@click.option("--B-L", prompt="Force factor (T·m)", type=float, help="BL: Force factor (T·m)")
@click.option("--S-d", prompt="Piston area (m²)", type=float, help="S_d: Effective piston area (m²)")
@click.option("--output", "-o", type=click.Path(), help="Output file path (optional)")
def driver_import(name, M_ms, C_ms, R_ms, R_e, L_e, B_L, S_d, output):
    """
    Interactively import driver Thiele-Small parameters.

    Prompts for all required T/S parameters and creates a ThieleSmallParameters
    instance that can be exported to Hornresp format.

    Literature:
        - Small (1972) - Thiele-Small parameter definitions
        - COMSOL (2020) - Lumped parameter model

    Examples:
        $ gsd driver import
        Driver name: BC_12NDL76
        Moving mass (kg): 0.054
        Compliance (m/N): 0.00019
        ...
    """
    # Create ThieleSmallParameters instance
    driver_params = ThieleSmallParameters(
        M_ms=M_ms,
        C_ms=C_ms,
        R_ms=R_ms,
        R_e=R_e,
        L_e=L_e,
        BL=B_L,
        S_d=S_d
    )

    # Display calculated derived properties
    click.echo(f"\n✓ Driver '{name}' created successfully")
    click.echo(f"\nDerived Properties:")
    click.echo(f"  F_s = {driver_params.F_s:.2f} Hz")
    click.echo(f"  Q_es = {driver_params.Q_es:.3f}")
    click.echo(f"  Q_ms = {driver_params.Q_ms if driver_params.Q_ms != float('inf') else 'inf'}")
    click.echo(f"  Q_ts = {driver_params.Q_ts:.3f}")
    click.echo(f"  V_as = {driver_params.V_as:.4f} m³")

    # Save to file if output path provided
    if output:
        export_to_hornresp(driver_params, name, output, comment=f"Imported via gsd driver import")
        click.echo(f"\n✓ Exported to {output}")


@driver.command(name="list")
def driver_list():
    """
    List all available drivers.

    Shows all available drivers from YAML definitions including
    B&C drivers and test cases for validation.
    """
    from gsd.driver import load_driver, list_drivers

    drivers = list_drivers()

    click.echo(f"\nAvailable Drivers ({len(drivers)}):")
    click.echo("=" * 70)

    # Group by type (B&C vs Test)
    bc_drivers = {k: v for k, v in drivers.items() if k.startswith("BC_")}
    test_drivers = {k: v for k, v in drivers.items() if k.startswith("TC")}

    if bc_drivers:
        click.echo("\nB&C Speakers:")
        click.echo("-" * 70)
        for name, desc in sorted(bc_drivers.items()):
            # Load driver to get key specs
            driver = load_driver(name)
            click.echo(f"\n{name} - {desc}")
            click.echo(f"  F_s: {driver.F_s:.1f} Hz,  Q_ts: {driver.Q_ts:.2f},  "
                      f"V_as: {driver.V_as*1000:.1f} L")
            click.echo(f"  R_e: {driver.R_e:.1f} Ω,  S_d: {driver.S_d*10000:.0f} cm²")

    if test_drivers:
        click.echo("\n\nTest Cases (for validation):")
        click.echo("-" * 70)
        for name, desc in sorted(test_drivers.items()):
            driver = load_driver(name)
            click.echo(f"\n{name} - {desc}")
            click.echo(f"  F_s: {driver.F_s:.1f} Hz,  S_d: {driver.S_d*10000:.1f} cm²")

    click.echo("\n" + "=" * 70)
    click.echo("\nUse driver names with:")
    click.echo("  'gsd export <driver>'          - Export to Hornresp format")
    click.echo("  'gsd driver info <driver>'     - Show detailed driver info")
    click.echo("\nExample: gsd export BC_12NDL76 -o output.txt")


@driver.command(name="info")
@click.argument("driver_name")
def driver_info(driver_name: str):
    """
    Show detailed information about a driver.

    Displays complete driver parameters including datasheet specifications,
    physical parameters, and literature references.

    Examples:
        gsd driver info BC_8NDL51
        gsd driver info TC2
    """
    from gsd.driver import get_driver_info

    try:
        info = get_driver_info(driver_name)
    except FileNotFoundError:
        click.echo(f"Error: Driver '{driver_name}' not found.")
        click.echo("\nUse 'gsd driver list' to see available drivers.")
        return

    click.echo(f"\n{info['name']}")
    if info.get('manufacturer'):
        click.echo(f"Manufacturer: {info['manufacturer']}")
    if info.get('model'):
        click.echo(f"Model: {info['model']}")
    click.echo(f"Description: {info['description']}")
    click.echo("=" * 70)

    # Datasheet specifications
    if 'datasheet' in info:
        click.echo("\nDatasheet Specifications:")
        ds = info['datasheet']
        for key, value in sorted(ds.items()):
            click.echo(f"  {key}: {value}")

    # Physical parameters
    if 'parameters' in info:
        click.echo("\nPhysical Parameters:")
        params = info['parameters']
        click.echo(f"  M_md:  {params['M_md']:.6f} kg  # Driver mass only (excludes radiation mass)")
        click.echo(f"  C_ms:  {params['C_ms']:.6e} m/N # Compliance")
        click.echo(f"  R_ms:  {params['R_ms']:.2f} N·s/m  # Mechanical resistance")
        click.echo(f"  R_e:   {params['R_e']:.2f} Ω    # Voice coil DC resistance")
        click.echo(f"  L_e:   {params['L_e']:.6f} H    # Voice coil inductance")
        click.echo(f"  BL:    {params['BL']:.2f} T·m   # Force factor")
        click.echo(f"  S_d:   {params['S_d']:.6f} m²   # Effective piston area")
        if 'X_max' in params and params['X_max'] is not None:
            click.echo(f"  X_max: {params['X_max']:.6f} m   # Maximum linear excursion")

    # Notes
    if 'notes' in info:
        click.echo("\nNotes:")
        for line in info['notes'].strip().split('\n'):
            click.echo(f"  {line}")

    # Literature
    if 'literature' in info:
        click.echo("\nLiterature:")
        for ref in info['literature']:
            click.echo(f"  - {ref}")

    click.echo("=" * 70)


@validate.command(name="list")
@click.option("--driver", "-d", type=click.Choice([
    "BC_8NDL51", "BC_12NDL76", "BC_15DS115", "BC_18PZW100", "all"
], case_sensitive=False), default="all", help="Filter by driver")
def validate_list(driver):
    """
    List available validation datasets.

    Shows which drivers and configurations have Hornresp reference data
    available for validation in a tree view format.

    Examples:
        $ gsd validate list
        $ gsd validate list --driver BC_8NDL51
    """
    from pathlib import Path

    # Path to validation data directory
    validation_base = Path(__file__).parent.parent.parent / "tests" / "validation" / "drivers"

    if not validation_base.exists():
        click.echo(f"No validation data directory found at {validation_base}")
        return

    # Collect all configurations organized by driver
    drivers_data = {}
    for driver_dir in sorted(validation_base.iterdir()):
        if not driver_dir.is_dir():
            continue

        driver_name = driver_dir.name
        # Filter by driver if specified
        if driver != "all" and driver_name.upper() != driver.replace("BC_", "").upper():
            continue

        configs = {}
        for enclosure_dir in sorted(driver_dir.iterdir()):
            if not enclosure_dir.is_dir():
                continue

            enclosure_type = enclosure_dir.name

            # Collect configurations within this enclosure type
            config_list = []

            # Check for flat structure (files directly in enclosure_dir, e.g., infinite_baffle)
            if (enclosure_dir / "metadata.json").exists() and (enclosure_dir / "sim.txt").exists():
                config_list.append("default")

            # Also check for subdirectories (e.g., sealed/Vb31.6L)
            for config_dir in sorted(enclosure_dir.iterdir()):
                if config_dir.is_dir():
                    # Check if it has metadata.json and sim.txt
                    if (config_dir / "metadata.json").exists() and (config_dir / "sim.txt").exists():
                        config_list.append(config_dir.name)

            if config_list:
                configs[enclosure_type] = config_list

        if configs:
            drivers_data[driver_name] = configs

    if not drivers_data:
        click.echo("No validation datasets found.")
        if driver != "all":
            click.echo(f"\nTry running 'gsd validate list' without --driver filter")
        return

    # Display tree view
    click.echo("\nAvailable Validation Datasets")
    click.echo("=" * 70)
    click.echo()

    for driver_name, configs in sorted(drivers_data.items()):
        # Format driver name nicely (bc_8ndl51 -> BC_8NDL51)
        display_name = driver_name.upper().replace("_", "_")  # Keep as is, just uppercase

        if len(drivers_data) > 1:
            # Multiple drivers, show driver name
            click.echo(f"{display_name}")

        for enclosure_type, config_list in sorted(configs.items()):
            # Filter out "default" - used for infinite_baffle which has only one config
            filtered_configs = [c for c in config_list if c != "default"]

            # Check if this is a leaf node (only "default" config)
            is_leaf = len(config_list) == 1 and config_list[0] == "default"

            # Format enclosure type nicely
            if len(drivers_data) > 1:
                if is_leaf:
                    # Leaf node, no sub-configurations to show
                    click.echo(f"├── {enclosure_type}")
                else:
                    click.echo(f"├── {enclosure_type}")
                    prefix = "│   └── "
            else:
                # Single driver, no driver prefix
                if list(configs.keys()).index(enclosure_type) < len(configs) - 1:
                    if is_leaf:
                        click.echo(f"├── {enclosure_type}")
                    else:
                        click.echo(f"├── {enclosure_type}")
                        prefix = "│   ├── "
                else:
                    if is_leaf:
                        click.echo(f"└── {enclosure_type}")
                    else:
                        click.echo(f"└── {enclosure_type}")
                        prefix = "    └── "

            # List configurations (skip "default" as it's already shown)
            if not is_leaf:
                config_list_sorted = sorted(filtered_configs)
                for i, config_name in enumerate(config_list_sorted):
                    if i < len(config_list_sorted) - 1:
                        if len(drivers_data) == 1:
                            # Single driver, show nested tree properly
                            if list(configs.keys()).index(enclosure_type) < len(configs) - 1:
                                click.echo(f"{prefix}{config_name}")
                            else:
                                click.echo(f"{prefix}{config_name}")
                        else:
                            click.echo(f"{prefix}{config_name}")
                    else:
                        click.echo(f"{prefix}{config_name}")

        click.echo()

    click.echo("=" * 70)

    # Count total configurations
    total_configs = sum(len(configs) for configs in [d.values() for d in drivers_data.values()])
    click.echo(f"\nTotal: {total_configs} configuration(s) across {len(drivers_data)} driver(s)")
    click.echo("\nUse 'gsd validate compare <driver> <config_path>' to run validation")
    click.echo("  Example: gsd validate compare bc_8ndl51 sealed/Vb31.6L")


@validate.command()
@click.argument("driver_name", type=click.Choice([
    "BC_8NDL51", "BC_12NDL76", "BC_15DS115", "BC_18PZW100"
], case_sensitive=False))
@click.argument("config_path")
@click.option("--tolerance-ze", type=float, default=35.0,
              help="Electrical impedance magnitude tolerance (%)")
@click.option("--tolerance-phase", type=float, default=90.0,
              help="Electrical impedance phase tolerance (degrees)")
@click.option("--tolerance-spl", type=float, default=6.0,
              help="SPL tolerance (dB)")
@click.option("--verbose", "-v", is_flag=True,
              help="Show detailed error analysis")
def compare(driver_name, config_path, tolerance_ze, tolerance_phase,
            tolerance_spl, verbose):
    """
    Compare gsd simulation with Hornresp reference data.

    Validates gsd predictions against Hornresp simulation results
    for the specified driver and configuration path.

    DRIVER_NAME: B&C driver model (BC_8NDL51, BC_12NDL76, BC_15DS115, BC_18PZW100)
    CONFIG_PATH: Configuration path (e.g., "infinite_baffle", "sealed/Vb31.6L")

    Literature:
        - Small (1972) - Closed-box system parameters
        - Beranek (1954) - Acoustic theory

    Examples:
        $ gsd validate compare BC_8NDL51 infinite_baffle
        $ gsd validate compare BC_8NDL51 sealed/Vb31.6L
        $ gsd validate compare BC_8NDL51 sealed/Vb31.6L --verbose
    """
    import json
    import numpy as np

    from gsd.validation.paths import get_driver_factory, parse_config_path, get_config_directory
    from gsd.hornresp.results_parser import load_hornresp_sim_file
    from gsd.validation.compare import (
        compare_electrical_impedance,
        compare_electrical_impedance_phase,
        compare_spl,
        generate_validation_report
    )

    try:
        # Step 1: Load driver parameters
        click.echo(f"Loading driver: {driver_name}...")
        driver_factory = get_driver_factory(driver_name)
        driver = driver_factory()
        click.echo(f"  F_s = {driver.F_s:.2f} Hz, Q_ts = {driver.Q_ts:.3f}")

        # Step 2: Parse config path and get directory
        click.echo(f"\nLoading Hornresp reference data...")

        enclosure_type, params = parse_config_path(config_path)
        config_dir = get_config_directory(driver_name, config_path)

        # Load sim file and metadata
        sim_path = config_dir / "sim.txt"
        metadata_path = config_dir / "metadata.json"

        hornresp_data = load_hornresp_sim_file(str(sim_path))
        click.echo(f"  Loaded {len(hornresp_data.frequency)} frequency points")

        # Load metadata for configuration parameters
        with open(metadata_path) as f:
            metadata = json.load(f)

        # Step 3: Calculate gsd response
        click.echo(f"\nCalculating gsd response...")

        if enclosure_type == "infinite_baffle":
            from gsd.driver.response import direct_radiator_electrical_impedance

            # Calculate response at each frequency
            ze_gsd = []
            ze_phase_gsd = []
            spl_gsd = []

            for freq in hornresp_data.frequency:
                result = direct_radiator_electrical_impedance(freq, driver)
                ze_gsd.append(result["Ze_magnitude"])
                ze_phase_gsd.append(result["Ze_phase"])
                spl_gsd.append(result["SPL"])

        elif enclosure_type == "sealed":
            from gsd.enclosure.sealed_box import sealed_box_electrical_impedance

            # Get Vb from metadata (in liters, convert to m³)
            Vb_L = metadata.get("Vb_L")
            if Vb_L is None:
                raise ValueError(f"Metadata missing Vb_L for sealed configuration")
            Vb_m3 = Vb_L / 1000.0

            click.echo(f"  Vb = {Vb_L} L")

            # Calculate response at each frequency
            ze_gsd = []
            ze_phase_gsd = []
            spl_gsd = []

            for freq in hornresp_data.frequency:
                result = sealed_box_electrical_impedance(freq, driver, Vb_m3)
                ze_gsd.append(result["Ze_magnitude"])
                ze_phase_gsd.append(result["Ze_phase"])
                spl_gsd.append(result["SPL"])

        else:
            raise ValueError(f"Enclosure type '{enclosure_type}' not yet supported")

        # Convert to numpy arrays
        ze_gsd = np.array(ze_gsd)
        ze_phase_gsd = np.array(ze_phase_gsd)
        spl_gsd = np.array(spl_gsd)

        # Step 4: Run comparisons
        click.echo(f"\nRunning comparisons...")

        ze_result = compare_electrical_impedance(
            hornresp_data.frequency,
            ze_gsd,
            hornresp_data,
            tolerance_percent=tolerance_ze
        )

        phase_result = compare_electrical_impedance_phase(
            hornresp_data.frequency,
            ze_gsd,
            hornresp_data,
            tolerance_degrees=tolerance_phase
        )

        spl_result = compare_spl(
            hornresp_data.frequency,
            spl_gsd,
            hornresp_data.spl_db,
            tolerance_db=tolerance_spl
        )

        results = [ze_result, phase_result, spl_result]

        # Step 5: Display report
        click.echo(f"\n{'='*70}")
        click.echo(f"VALIDATION REPORT: {driver_name} - {config_path}")
        click.echo(f"{'='*70}\n")

        # Electrical Impedance Magnitude
        click.echo("Electrical Impedance Magnitude:")
        click.echo(f"  Max error: {ze_result.max_percent_error:.2f}% @ {ze_result.frequencies[ze_result.percent_error.argmax()]:.1f} Hz")
        click.echo(f"  RMS error: {ze_result.rms_error:.2f} Ω")
        click.echo(f"  Mean error: {ze_result.mean_absolute_error:.2f} Ω")
        click.echo(f"  Pass: {'✓' if ze_result.passed else '✗'}\n")

        # Electrical Impedance Phase
        click.echo("Electrical Impedance Phase:")
        click.echo(f"  Max error: {phase_result.max_absolute_error:.2f}° @ {phase_result.frequencies[phase_result.absolute_error.argmax()]:.1f} Hz")
        click.echo(f"  RMS error: {phase_result.rms_error:.2f}°")
        click.echo(f"  Mean error: {phase_result.mean_absolute_error:.2f}°")
        click.echo(f"  Pass: {'✓' if phase_result.passed else '✗'}\n")

        # SPL
        click.echo("SPL (1m, 2.83V):")
        click.echo(f"  Max error: {spl_result.max_absolute_error:.2f} dB @ {spl_result.frequencies[spl_result.absolute_error.argmax()]:.1f} Hz")
        click.echo(f"  RMS error: {spl_result.rms_error:.2f} dB")
        click.echo(f"  Mean error: {spl_result.mean_absolute_error:.2f} dB")
        click.echo(f"  Pass: {'✓' if spl_result.passed else '✗'}\n")

        # Overall result
        all_passed = all(r.passed for r in results)
        click.echo(f"Overall Result: {'PASS ✓' if all_passed else 'FAIL ✗'}")

        # Verbose mode: show worst errors
        if verbose:
            click.echo(f"\n{'='*70}")
            click.echo("Worst Errors:")
            click.echo(f"{'='*70}\n")

            for i, result in enumerate(results):
                click.echo(f"{result.metric_name}:")
                worst_errors = result.get_worst_errors(3)
                for j, error in enumerate(worst_errors, 1):
                    click.echo(f"  {j}. {error['frequency']:.1f} Hz: error = {error['absolute_error']:.3f}")
                    if result.metric_name == "Ze magnitude":
                        click.echo(f"     bugworks GSD: {error['gsd']:.2f} Ω, Hornresp: {error['hornresp']:.2f} Ω")
                    elif result.metric_name == "Ze phase":
                        click.echo(f"     bugworks GSD: {error['gsd']:.1f}°, Hornresp: {error['hornresp']:.1f}°")
                    elif result.metric_name == "SPL":
                        click.echo(f"     bugworks GSD: {error['gsd']:.2f} dB, Hornresp: {error['hornresp']:.2f} dB")
                click.echo()

    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        click.echo("\nRun 'gsd validate list' to see available datasets", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"Error during validation: {e}", err=True)
        raise click.Abort()


@validate.command(name="import")
@click.argument("file", type=click.Path(exists=True))
@click.option("--driver", "-d", required=True,
              help="Driver name (e.g., BC_8NDL51)")
@click.option("--config", "-c", required=True,
              type=click.Choice(["infinite_baffle", "sealed"]),
              help="Configuration type")
@click.option("--vb", type=float,
              help="Box volume in liters (required for sealed)")
@click.option("--fb", type=float,
              help="Port tuning frequency in Hz (for future ported enclosures)")
@click.option("--force", is_flag=True,
              help="Overwrite existing files")
def import_cmd(file, driver, config, vb, fb, force):
    """
    Import Hornresp simulation result into validation dataset.

    Imports a single Hornresp simulation file to the validation dataset.
    Creates a nested directory structure organized by enclosure type and parameters.

    FILE: Hornresp simulation file to import

    Examples:
        $ gsd validate import imports/8ndl51_sim.txt --driver BC_8NDL51 --config infinite_baffle
        $ gsd validate import imports/8ndl51_sealed.txt --driver BC_8NDL51 --config sealed --vb 31.6

    For sealed boxes, use --vb to specify box volume in liters.
    """
    import json
    import shutil
    from datetime import datetime
    from pathlib import Path

    # Validate arguments
    if config == "sealed" and vb is None:
        raise click.BadArgumentUsage(
            "--vb is required for sealed configuration\n"
            "Example: --vb 31.6  (box volume in liters)"
        )

    # Validate file is Hornresp format
    file_path = Path(file)
    try:
        with open(file_path) as f:
            first_line = f.readline()
            if "Freq (hertz)" not in first_line and "Freq\t" not in first_line:
                raise click.FileError(f"{file_path} is not a valid Hornresp simulation file")
    except (IOError, UnicodeDecodeError) as e:
        raise click.FileError(f"Failed to read {file_path}: {e}")

    # Build config directory path
    driver_lower = driver.lower()

    if config == "infinite_baffle":
        config_subdir = "infinite_baffle"
    elif config == "sealed":
        config_subdir = f"sealed/Vb{vb}L"
    elif config == "ported":
        # For future implementation
        if fb is None:
            raise click.BadArgumentUsage("--fb is required for ported configuration")
        config_subdir = f"ported/Vb{vb}L_Fb{fb}Hz"
    else:
        config_subdir = config

    # Setup target directory
    # cli.py is at src/gsd/cli.py, so go up 3 levels to repo root
    validation_base = Path(__file__).parent.parent.parent / "tests" / "validation" / "drivers"
    target_dir = validation_base / driver_lower / config_subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    # Check for existing files
    sim_path = target_dir / "sim.txt"
    metadata_path = target_dir / "metadata.json"

    if sim_path.exists() and not force:
        click.echo(f"Warning: sim.txt already exists at {target_dir}")
        click.echo("Use --force to overwrite")
        return

    # Copy sim file
    shutil.copy2(file_path, sim_path)
    click.echo(f"✓ Imported {file_path.name} → {config_subdir}/sim.txt")

    # Generate metadata.json
    click.echo(f"Creating metadata.json...")

    metadata = {
        "driver": driver,
        "manufacturer": "B&C Speakers",
        "configuration": config,
        "date_created": datetime.now().strftime("%Y-%m-%d"),
        "date_run": datetime.now().strftime("%Y-%m-%d"),
        "hornresp_version": "unknown",
        "voice_coil_model": "simple",
        "validation_status": "ready",
    }

    # Add configuration-specific parameters
    if config == "sealed":
        metadata["Vb_L"] = vb
    elif config == "ported":
        metadata["Vb_L"] = vb
        metadata["Fb_Hz"] = fb

    # Write metadata
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    click.echo(f"\n  Driver: {driver}")
    click.echo(f"  Configuration: {config}")
    if config == "sealed":
        click.echo(f"  Vb: {vb} L")
    elif config == "ported":
        click.echo(f"  Vb: {vb} L")
        click.echo(f"  Fb: {fb} Hz")

    click.echo(f"\n✓ Successfully imported validation dataset")
    click.echo(f"\nNext steps:")
    click.echo(f"  Run 'gsd validate list' to see all datasets")
    click.echo(f"  Run 'gsd validate compare {driver} {config_subdir}' to validate")


# Register new validation commands (Phase 1.5)
validate.add_command(validate_generate_input)
validate.add_command(validate_parse_output)
validate.add_command(validate_run)
validate.add_command(validate_status)
validate.add_command(validate_migrate)


# Register new CLI command groups
cli.add_command(optimize.optimize)
cli.add_command(plot.plot)


@cli.command()
@click.argument("driver_name", type=click.Choice([
    "BC_8NDL51",
    "BC_12NDL76",
    "BC_15DS115",
    "BC_18PZW100"
], case_sensitive=False))
@click.option("--output", "-o", type=click.Path(), default=".", help="Output directory or file path")
def export(driver_name, output):
    """
    Export B&C driver to Hornresp format.

    Exports one of the predefined B&C drivers to a Hornresp .txt file
    ready for import into Hornresp for simulation.

    Literature:
        - Hornresp User Manual - File format specification

    Args:
        driver_name: Name of B&C driver (BC_8NDL51, BC_12NDL76, BC_15DS115, BC_18PZW100)
        output: Output file or directory path (default: current directory)

    Examples:
        $ gsd export BC_12NDL76
        $ gsd export BC_12NDL76 -o exports/
        $ gsd export BC_12NDL76 -o bc_12ndl76.txt
    """
    # Import driver loader
    from gsd.driver import load_driver

    # Load driver
    driver = load_driver(driver_name)

    # Determine output path
    output_path = Path(output)
    if output_path.is_dir() or output == ".":
        # Output is a directory, create filename from driver name
        filename = f"{driver_name.lower()}.txt"
        output_file = output_path / filename
    else:
        # Output is a file path
        output_file = output_path

    # Export to Hornresp format
    export_to_hornresp(
        driver,
        driver_name,
        str(output_file),
        comment=f"B&C {driver_name} driver parameters - exported from gsd"
    )

    click.echo(f"\n✓ Successfully exported {driver_name} to {output_file}")
    click.echo(f"\nImport this file into Hornresp to verify parameters.")


@cli.command()
@click.argument('filepath', type=click.Path(exists=True))
@click.option('--freq-min', type=float, help='Minimum frequency (Hz)')
@click.option('--freq-max', type=float, help='Maximum frequency (Hz)')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
def sim_summary(filepath, freq_min, freq_max, as_json):
    """
    Display summary statistics for Hornresp simulation file.

    FILEPATH: Path to _sim.txt file

    Shows key metrics including impedance peaks, SPL range, efficiency,
    and notable features. Efficiently analyzes data without loading
    entire file into context.

    Examples:
        $ gsd sim-summary tests/validation/drivers/bc_8ndl51/infinite_baffle/sim.txt
        $ gsd sim-summary sim.txt --freq-min 50 --freq-max 200
        $ gsd sim-summary sim.txt --json > summary.json
    """
    from gsd.hornresp.query_tools import get_simulation_summary

    # Build freq_range if provided
    freq_range = None
    if freq_min is not None and freq_max is not None:
        freq_range = (freq_min, freq_max)

    # Get summary
    summary = get_simulation_summary(filepath, freq_range)

    if as_json:
        import json
        click.echo(json.dumps(summary, indent=2, default=str))
    else:
        # Human-readable output
        click.echo(f"\n{'='*70}")
        click.echo(f"Hornresp Simulation Summary: {summary['metadata']['filename']}")
        click.echo(f"{'='*70}\n")

        click.echo("Frequency Range:")
        click.echo(f"  {summary['frequency']['min_hz']:.1f} - {summary['frequency']['max_hz']:.1f} Hz")
        click.echo(f"  {summary['frequency']['num_points']} data points\n")

        click.echo("Electrical Impedance (Ze):")
        click.echo(f"  Range: {summary['impedance']['min_ohms']:.2f} - {summary['impedance']['max_ohms']:.2f} Ω")
        click.echo(f"  Mean: {summary['impedance']['mean_ohms']:.2f} Ω")
        if summary['impedance']['peaks']:
            click.echo(f"  Peaks:")
            for peak in summary['impedance']['peaks']:
                click.echo(f"    {peak['freq_hz']:.1f} Hz: {peak['magnitude_ohms']:.2f} Ω")
        click.echo()

        click.echo("Sound Pressure Level (SPL @ 1m, 2.83V):")
        click.echo(f"  Range: {summary['spl']['min_db']:.1f} - {summary['spl']['max_db']:.1f} dB")
        click.echo(f"  Mean: {summary['spl']['mean_db']:.1f} dB")
        if summary['spl']['bandwidth']['minus_3db_hz']:
            click.echo(f"  -3dB bandwidth: {summary['spl']['bandwidth']['minus_3db_hz']:.1f} Hz")
        click.echo()

        click.echo("Efficiency:")
        click.echo(f"  Range: {summary['efficiency']['min_percent']:.3f} - {summary['efficiency']['max_percent']:.3f} %")
        click.echo()

        if summary['notable_features']:
            click.echo("Notable Features:")
            for feature in summary['notable_features']:
                click.echo(f"  • {feature}")
            click.echo()


@cli.command()
@click.argument('filepath', type=click.Path(exists=True))
@click.option('--columns', '-c', required=True,
              help='Comma-separated list of columns (e.g., "frequency,spl_db,ze_ohms")')
@click.option('--freq-min', type=float, help='Minimum frequency (Hz)')
@click.option('--freq-max', type=float, help='Maximum frequency (Hz)')
@click.option('--output', '-o', type=click.Path(), help='Save to CSV file')
@click.option('--head', '-n', type=int, help='Show only first N rows')
def sim_extract(filepath, columns, freq_min, freq_max, output, head):
    """
    Extract specific columns from Hornresp simulation file.

    FILEPATH: Path to _sim.txt file

    Extracts only the columns you need, avoiding loading all data.
    Useful for quick analysis or plotting specific metrics.

    Examples:
        $ gsd sim-extract sim.txt -c frequency,spl_db,ze_ohms
        $ gsd sim-extract sim.txt -c spl_db --freq-min 50 --freq-max 200
        $ gsd sim-extract sim.txt -c frequency,ze_ohms,zephase_deg -o impedance.csv
        $ gsd sim-extract sim.txt -c spl_db --head 10
    """
    from gsd.hornresp.query_tools import extract_columns

    # Parse columns
    column_list = [c.strip() for c in columns.split(',')]

    # Build freq_range
    freq_range = None
    if freq_min is not None and freq_max is not None:
        freq_range = (freq_min, freq_max)

    # Extract data
    data = extract_columns(filepath, column_list, freq_range, as_dict=True)

    # Try to use pandas for nice table output
    try:
        import pandas as pd

        # Convert to pandas DataFrame for nice display
        df = pd.DataFrame(data)

        if head:
            click.echo(f"Showing first {head} rows of {len(df)} total\n")
            df = df.head(head)

        if output:
            df.to_csv(output, index=False)
            click.echo(f"✓ Saved {len(df)} rows to {output}")
        else:
            # Display as table
            click.echo(df.to_string(index=False))
    except ImportError:
        # Fallback if pandas not available
        if output:
            # Simple CSV output
            import csv
            with open(output, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=column_list)
                writer.writeheader()
                for i in range(len(data[column_list[0]])):
                    row = {col: data[col][i] for col in column_list}
                    writer.writerow(row)
            click.echo(f"✓ Saved to {output}")
        else:
            # Simple text output
            if head:
                num_rows = min(head, len(data[column_list[0]]))
            else:
                num_rows = len(data[column_list[0]])

            # Print header
            header = "\t".join(column_list)
            click.echo(header)

            # Print data rows
            for i in range(num_rows):
                row = "\t".join(str(data[col][i]) for col in column_list)
                click.echo(row)


@cli.command()
@click.argument('filepath', type=click.Path(exists=True))
@click.option('--metric', '-m', default='spl_db',
              type=click.Choice(['spl_db', 'ze_ohms', 'efficiency_percent', 'xd_mm']),
              help='Metric to analyze')
@click.option('--top', '-t', type=int, default=5, help='Show top N values')
@click.option('--bottom', '-b', type=int, default=5, help='Show bottom N values')
def sim_query(filepath, metric, top, bottom):
    """
    Query extremes in Hornresp simulation data.

    FILEPATH: Path to _sim.txt file

    Quickly find highest/lowest values for any metric.
    Useful for identifying resonance frequencies, efficiency peaks, etc.

    Examples:
        $ gsd sim-query sim.txt -m spl_db
        $ gsd sim-query sim.txt -m ze_ohms --top 3
        $ gsd sim-query sim.txt -m efficiency_percent --top 10 --bottom 0
    """
    from gsd.hornresp.query_tools import find_extremes

    # Map CLI option names to column names
    metric_map = {
        'spl_db': 'SPL (dB)',
        'ze_ohms': 'Ze (Ω)',
        'efficiency_percent': 'Efficiency (%)',
        'xd_mm': 'Displacement (mm)'
    }

    result = find_extremes(filepath, metric=metric, n=max(top, bottom))

    click.echo(f"\n{metric_map[metric]} - Extremes")
    click.echo(f"{'='*70}\n")

    if top > 0:
        click.echo(f"Top {top} values:")
        for i, p in enumerate(result['highest'][:top], 1):
            click.echo(f"  {i}. {p['frequency']:.1f} Hz: {p['value']:.3f}")
        click.echo()

    if bottom > 0:
        click.echo(f"Bottom {bottom} values:")
        for i, p in enumerate(result['lowest'][:bottom], 1):
            click.echo(f"  {i}. {p['frequency']:.1f} Hz: {p['value']:.3f}")
        click.echo()


@cli.command()
@click.option("--output", "-o", type=click.Path(), default="./exports", help="Output directory")
def export_all(output):
    """
    Export all B&C drivers to Hornresp format.

    Generates .txt files for all 4 B&C drivers in the specified directory.

    Examples:
        $ gsd export-all
        $ gsd export-all -o hornresp_inputs/
    """
    # Import driver loader
    from gsd.driver import load_driver

    # Create list of all drivers
    drivers = [
        (load_driver("BC_8NDL51"), "BC_8NDL51"),
        (load_driver("BC_12NDL76"), "BC_12NDL76"),
        (load_driver("BC_15DS115"), "BC_15DS115"),
        (load_driver("BC_18PZW100"), "BC_18PZW100"),
    ]

    # Batch export
    batch_export_to_hornresp(drivers, output)

    click.echo(f"\n✓ Exported {len(drivers)} drivers to {output}/")
    click.echo("\nExported files:")
    for _, name in drivers:
        click.echo(f"  - {name.lower()}.txt")


def main():
    """Entry point for gsd CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
