"""
Validation CLI commands for gsd.

Provides command-line interface for managing validation data,
generating Hornresp files, and running validation comparisons.

Literature:
- Hornresp User Manual - File format and validation procedures
- ROADMAP Phase 5 - Validation framework
"""

import click
import json
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple

from gsd.hornresp.export import export_to_hornresp
from gsd.hornresp.results_parser import load_hornresp_sim_file
from gsd.validation.compare import (
    compare_electrical_impedance,
    compare_electrical_impedance_phase,
    compare_spl,
    generate_validation_report
)


def get_validation_base_path() -> Path:
    """Get the base path for validation data."""
    # commands.py is in src/gsd/validation/
    # Go up 4 levels: validation/ → gsd/ → src/ → project_root
    # Then down to tests/validation
    return Path(__file__).parent.parent.parent.parent / "tests" / "validation"


def get_driver_path(driver_name: str) -> Path:
    """Get the path to a driver's validation directory."""
    return get_validation_base_path() / "drivers" / driver_name.lower()


def get_enclosure_path(driver_name: str, enclosure_type: str) -> Path:
    """Get the path to a driver's enclosure validation directory."""
    return get_driver_path(driver_name) / enclosure_type


def load_driver_json(driver_name: str) -> dict:
    """Load driver.json for a given driver."""
    driver_path = get_driver_path(driver_name)
    driver_file = driver_path / "driver.json"

    if not driver_file.exists():
        raise click.ClickException(f"Driver file not found: {driver_file}")

    with open(driver_file, 'r') as f:
        return json.load(f)


def load_test_cases_json(driver_name: str, enclosure_type: str) -> dict:
    """Load test_cases.json for a given driver/enclosure combination."""
    enclosure_path = get_enclosure_path(driver_name, enclosure_type)
    test_cases_file = enclosure_path / "test_cases.json"

    if not test_cases_file.exists():
        raise click.ClickException(f"Test cases file not found: {test_cases_file}")

    with open(test_cases_file, 'r') as f:
        return json.load(f)


def get_driver_from_json(driver_data: dict):
    """Import driver from YAML files based on driver name."""
    from gsd.driver import load_driver

    driver_name = driver_data["driver_name"]
    try:
        return load_driver(driver_name)
    except FileNotFoundError as e:
        raise click.ClickException(f"Unknown driver: {driver_name}")


# ============================================================================
# Migration Helper Functions
# ============================================================================

def parse_readme_driver_params(readme_path: Path) -> Optional[Dict]:
    """
    Parse driver parameters from README.md file.

    Extracts Thiele-Small parameters from the "## Driver" section.

    Args:
        readme_path: Path to README.md file

    Returns:
        Dictionary with driver parameters or None if not found
    """
    if not readme_path.exists():
        return None

    with open(readme_path, 'r') as f:
        content = f.read()

    # Extract driver section
    driver_section = re.search(
        r'## Driver\s+(.*?)(?=##|\Z)',
        content,
        re.DOTALL
    )

    if not driver_section:
        return None

    section_text = driver_section.group(1)

    # Parse Thiele-Small parameters
    params = {}

    # Extract model
    model_match = re.search(r'\*\*Model\*\*:\s*(.+?)\s*$', section_text, re.MULTILINE)
    if model_match:
        params["model"] = model_match.group(1).strip()

    # Extract manufacturer
    manufacturer_match = re.search(r'\*\*Manufacturer\*\*:\s*(.+?)\s*$', section_text, re.MULTILINE)
    if manufacturer_match:
        params["manufacturer"] = manufacturer_match.group(1).strip()

    # Extract size
    size_match = re.search(r'\*\*Size\*\*:\s*([0-9.]+)"', section_text)
    if size_match:
        params["size_inches"] = float(size_match.group(1))

    # Extract Thiele-Small parameters (support both bold and list formats)
    # Format 1: **F_s**: 75.0 Hz
    # Format 2: - F_s: 75.0 Hz
    ts_pattern = r'(?:\*\*)?([A-Z_a-z]+)(?:\*\*)?:\s*([0-9.eE+-]+)\s*(?:Hz|L|cm²|T·m|Ω|g|m/N|H)?'
    for match in re.finditer(ts_pattern, section_text):
        param_name = match.group(1)
        param_value = match.group(2)

        # Map common parameter names
        param_mapping = {
            "F_s": "F_s",
            "Q_ts": "Q_ts",
            "Q_es": "Q_es",
            "Q_ms": "Q_ms",
            "V_as": "V_as",
            "S_d": "S_d",
            "BL": "BL",
            "R_e": "R_e",
            "M_md": "M_md",
            "C_ms": "C_ms",
            "R_ms": "R_ms",
            "L_e": "L_e",
        }

        if param_name in param_mapping:
            # Convert units if necessary
            if param_name in ["V_as"]:
                # Convert liters to m³
                params[param_mapping[param_name]] = float(param_value) / 1000
            elif param_name in ["S_d"]:
                # Convert cm² to m²
                params[param_mapping[param_name]] = float(param_value) / 10000
            elif param_name in ["M_md"]:
                # Convert g to kg
                params[param_mapping[param_name]] = float(param_value) / 1000
            else:
                params[param_mapping[param_name]] = float(param_value)

    return params if params else None


def parse_readme_test_cases(readme_path: Path) -> List[Dict]:
    """
    Parse test cases from README.md markdown tables.

    Extracts test case information from markdown tables under "## Test Cases".

    Args:
        readme_path: Path to README.md file

    Returns:
        List of test case dictionaries
    """
    if not readme_path.exists():
        return []

    with open(readme_path, 'r') as f:
        content = f.read()

    test_cases = []

    # Find all markdown tables
    table_pattern = r'\|(.+)\|\n\|[-\s:|]+\|\n((?:\|.+\|\n?)*)'
    for match in re.finditer(table_pattern, content):
        header_row = match.group(1)
        data_rows = match.group(2)

        # Parse headers (no [1:-1] needed since regex doesn't capture outer |)
        headers = [h.strip() for h in header_row.split('|')]

        # Check if this is a test case table
        if not any(h in headers for h in ["Input File", "test_case_id", "Status"]):
            continue

        # Parse data rows
        for row in data_rows.strip().split('\n'):
            if not row.strip():
                continue

            # Extract cells (use [1:-1] for data rows since they have outer |)
            cells = [cell.strip() for cell in row.split('|')[1:-1]]

            if len(cells) != len(headers):
                continue

            row_data = dict(zip(headers, cells))

            # Look for input file column
            input_file = None
            for key in ["Input File", "Input", "File"]:
                if key in row_data:
                    input_file = row_data[key]
                    break

            if not input_file or input_file == "-":
                continue

            # Extract status
            status = row_data.get("Status", "pending")
            if "✅" in status or "validated" in status.lower():
                status = "passed"
            elif "pending" in status.lower():
                status = "pending"
            else:
                status = "pending"

            # Build test case dict
            test_case = {
                "input_file": input_file,
                "status": status,
                "row_data": row_data
            }

            test_cases.append(test_case)

    return test_cases


def extract_test_case_id_from_filename(filename: str, driver_name: str, enclosure_type: str) -> str:
    """
    Generate test_case_id from input filename.

    Examples:
        input_qtc0.707.txt -> bc_8ndl51_sealed_box_qtc0_707
        input_ql5.txt -> bc_8ndl51_sealed_box_ql5
        input_vb20L.txt -> bc_8ndl51_sealed_box_vb20l

    Args:
        filename: Input filename (e.g., "input_qtc0.707.txt")
        driver_name: Normalized driver name (e.g., "bc_8ndl51")
        enclosure_type: Enclosure type (e.g., "sealed_box")

    Returns:
        Test case ID string
    """
    # Remove "input_" prefix and ".txt" extension
    base_name = filename.replace("input_", "").replace(".txt", "")

    # Clean up the name (lowercase, replace special chars)
    base_name = base_name.lower().replace(".", "_").replace("-", "_")

    # Remove multiple underscores
    base_name = re.sub(r'_+', '_', base_name)

    return f"{driver_name}_{enclosure_type}_{base_name}"


def infer_enclosure_parameters_from_filename(filename: str, enclosure_type: str) -> Dict:
    """
    Infer enclosure parameters from filename.

    Args:
        filename: Input filename (e.g., "input_qtc0.707.txt", "input_vb20L.txt")
        enclosure_type: Enclosure type

    Returns:
        Dictionary of inferred parameters
    """
    params = {}

    base_name = filename.lower().replace("input_", "").replace(".txt", "")

    if enclosure_type == "sealed_box":
        # Check for Qtc alignment
        qtc_match = re.search(r'qtc([\d.]+)', base_name)
        if qtc_match:
            params["Qtc"] = float(qtc_match.group(1))

        # Check for Vb (box volume)
        vb_match = re.search(r'vb([\d.]+)l?', base_name)
        if vb_match:
            params["Vb_liters"] = float(vb_match.group(1))

        # Check for QL parameter
        ql_match = re.search(r'ql(\d+)', base_name)
        if ql_match:
            params["QL"] = int(ql_match.group(1))

    elif enclosure_type == "ported_box":
        # Check for B4, QB3, BB4 alignments
        if "b4" in base_name:
            params["alignment"] = "B4"
        elif "qb3" in base_name:
            params["alignment"] = "QB3"
        elif "bb4" in base_name:
            params["alignment"] = "BB4"

        # Check for port diameter (e.g., "port_2in", "port_3in")
        port_match = re.search(r'port_(\d+)in', base_name)
        if port_match:
            # Convert diameter to area (circular port)
            diameter_inches = float(port_match.group(1))
            diameter_cm = diameter_inches * 2.54
            radius_cm = diameter_cm / 2
            area_cm2 = 3.14159 * radius_cm ** 2
            params["port_area_cm2"] = round(area_cm2, 2)

        # Check for QL parameter
        ql_match = re.search(r'ql(\d+)', base_name)
        if ql_match:
            params["QL"] = int(ql_match.group(1))

    return params


def create_driver_json(driver_params: Dict, enclosures_validated: List[str]) -> Dict:
    """
    Create driver.json structure from parsed parameters.

    Args:
        driver_params: Parsed driver parameters
        enclosures_validated: List of enclosure types validated

    Returns:
        Driver JSON dictionary
    """
    driver_name_upper = driver_params.get("model", "").upper().replace(" ", "_").replace("-", "_")

    # Extract Thiele-Small params
    ts_params = {}
    ts_fields = ["F_s", "Q_ts", "Q_es", "Q_ms", "V_as", "S_d", "BL", "R_e", "M_md", "C_ms", "R_ms", "L_e"]
    for field in ts_fields:
        if field in driver_params:
            ts_params[field] = driver_params[field]

    driver_json = {
        "driver_name": driver_name_upper,
        "manufacturer": driver_params.get("manufacturer", "Unknown"),
        "size_inches": driver_params.get("size_inches"),
        "thiele_small": ts_params,
        "enclosures_validated": enclosures_validated,
        "validation_status": "pending"
    }

    return driver_json


def create_test_cases_json(
    driver_name: str,
    enclosure_type: str,
    parsed_test_cases: List[Dict],
    readme_content: str
) -> Dict:
    """
    Create test_cases.json structure from parsed test cases.

    Args:
        driver_name: Driver name (normalized)
        enclosure_type: Enclosure type
        parsed_test_cases: List of parsed test case dictionaries
        readme_content: Full README.md content for reference

    Returns:
        Test cases JSON dictionary
    """
    driver_name_upper = driver_name.upper().replace("-", "_")

    test_cases = []

    for tc in parsed_test_cases:
        filename = tc["input_file"]
        test_case_id = extract_test_case_id_from_filename(filename, driver_name, enclosure_type)

        # Infer parameters from filename
        params = infer_enclosure_parameters_from_filename(filename, enclosure_type)

        # Get description from row data
        description = tc["row_data"].get("Alignment Type", tc["row_data"].get("Description", ""))

        # Build test case
        test_case = {
            "test_case_id": test_case_id,
            "description": description,
            "parameters": params,
            "status": tc["status"]
        }

        # Add validation criteria if available
        if "ze_max_error" in tc["row_data"]:
            test_case["validation_criteria"] = {
                "ze_max_error_percent": float(tc["row_data"]["ze_max_error"])
            }

        test_cases.append(test_case)

    test_cases_json = {
        "driver": driver_name_upper,
        "enclosure_type": enclosure_type,
        "test_cases": test_cases
    }

    return test_cases_json


# ============================================================================
# CLI Commands
# ============================================================================

@click.command(name="generate-input")
@click.argument("driver_name")
@click.argument("enclosure_type")
@click.option("--output-dir", "-o", type=click.Path(), help="Output directory (default: results/)")
def validate_generate_input(driver_name: str, enclosure_type: str, output_dir: Optional[str]):
    """
    Generate Hornresp input.txt files from test_cases.json.

    Generates Hornresp input files for all test cases defined in test_cases.json.
    Each test case gets its own input.txt file in the results/{test_case_id}/ directory.

    DRIVER_NAME: Driver name (e.g., bc_8ndl51)
    ENCLOSURE_TYPE: Enclosure type (infinite_baffle, sealed_box, ported_box)

    Example:
        gsd validate generate-input bc_8ndl51 sealed_box
    """
    driver_name_normalized = driver_name.lower().replace("-", "_")

    # Load test cases
    test_cases_data = load_test_cases_json(driver_name_normalized, enclosure_type)

    # Load driver parameters
    driver_data = load_driver_json(driver_name_normalized)
    driver = get_driver_from_json(driver_data)

    # Determine output directory
    if output_dir:
        base_output_path = Path(output_dir)
    else:
        base_output_path = get_enclosure_path(driver_name_normalized, enclosure_type) / "results"

    click.echo(f"Generating Hornresp input files for {driver_name} / {enclosure_type}")
    click.echo(f"Output directory: {base_output_path}")
    click.echo()

    generated_count = 0
    for test_case in test_cases_data["test_cases"]:
        test_case_id = test_case["test_case_id"]
        params = test_case["parameters"]
        description = test_case["description"]

        # Create output directory
        output_path = base_output_path / test_case_id
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate output filename
        output_file = output_path / "input.txt"

        # Generate input.json for reference
        input_json = {
            "test_case_id": test_case_id,
            "driver": driver_name.upper(),
            "enclosure_type": enclosure_type,
            "enclosure_parameters": params,
            "generated_at": datetime.now().isoformat(),
        }

        with open(output_path / "input.json", 'w') as f:
            json.dump(input_json, f, indent=2)

        # Export to Hornresp format
        export_kwargs = {}
        if enclosure_type == "infinite_baffle":
            export_kwargs["enclosure_type"] = "infinite_baffle"
        elif enclosure_type == "sealed_box":
            export_kwargs["enclosure_type"] = "sealed_box"
            export_kwargs["Vb_liters"] = params.get("Vb_liters")
            if params.get("QL"):
                export_kwargs["QL"] = params["QL"]
        elif enclosure_type == "ported_box":
            export_kwargs["enclosure_type"] = "ported_box"
            export_kwargs["Vb_liters"] = params.get("Vb_liters")
            export_kwargs["Fb_hz"] = params.get("Fb_hz")
            export_kwargs["port_area_cm2"] = params.get("port_area_cm2")
            export_kwargs["port_length_cm"] = params.get("port_length_cm")
            if params.get("QL"):
                export_kwargs["QL"] = params["QL"]
        else:
            click.echo(f"⚠ Unknown enclosure type: {enclosure_type}, skipping {test_case_id}")
            continue

        export_to_hornresp(
            driver=driver,
            driver_name=f"{driver_name}_{test_case_id}"[:48],  # Hornresp limit
            output_path=str(output_file),
            comment=f"{description} | {test_case_id}",
            **export_kwargs
        )

        click.echo(f"✓ Generated: {output_file}")
        generated_count += 1

    click.echo()
    click.echo(f"✓ Generated {generated_count} input files")


@click.command(name="parse-output")
@click.argument("driver_name")
@click.argument("enclosure_type")
@click.option("--input-dir", "-i", type=click.Path(), help="Input directory (default: results/)")
def validate_parse_output(driver_name: str, enclosure_type: str, input_dir: Optional[str]):
    """
    Parse Hornresp sim.txt files to sim.json.

    Parses Hornresp simulation output files and converts them to JSON format
    for programmatic access and validation comparisons.

    DRIVER_NAME: Driver name (e.g., bc_8ndl51)
    ENCLOSURE_TYPE: Enclosure type (infinite_baffle, sealed_box, ported_box)

    Example:
        gsd validate parse-output bc_8ndl51 sealed_box
    """
    driver_name_normalized = driver_name.lower().replace("-", "_")

    # Load test cases to know which test cases to parse
    test_cases_data = load_test_cases_json(driver_name_normalized, enclosure_type)

    # Determine input directory
    if input_dir:
        base_input_path = Path(input_dir)
    else:
        base_input_path = get_enclosure_path(driver_name_normalized, enclosure_type) / "results"

    click.echo(f"Parsing Hornresp sim.txt files for {driver_name} / {enclosure_type}")
    click.echo(f"Input directory: {base_input_path}")
    click.echo()

    parsed_count = 0
    for test_case in test_cases_data["test_cases"]:
        test_case_id = test_case["test_case_id"]
        sim_file = base_input_path / test_case_id / "sim.txt"

        if not sim_file.exists():
            click.echo(f"⚠ File not found: {sim_file}")
            continue

        try:
            # Parse Hornresp simulation file
            sim_data = load_hornresp_sim_file(str(sim_file))

            # Create sim.json
            sim_json = {
                "test_case_id": test_case_id,
                "metadata": {
                    "hornresp_version": "unknown",  # Not in sim.txt format
                    "date_parsed": datetime.now().isoformat(),
                    "source_file": str(sim_file),
                    "frequency_range": {
                        "start_hz": float(sim_data.frequency[0]),
                        "end_hz": float(sim_data.frequency[-1]),
                        "num_points": len(sim_data.frequency)
                    }
                },
                "data": {
                    "frequency": sim_data.frequency.tolist(),
                    "ra": sim_data.ra.tolist(),
                    "xa": sim_data.xa.tolist(),
                    "za": sim_data.za.tolist(),
                    "spl": sim_data.spl.tolist(),
                    "ze": sim_data.ze_ohms.tolist(),
                    "zephase": sim_data.zephase_deg.tolist(),
                    "xg": sim_data.xg.tolist(),
                    "eg": sim_data.eg.tolist(),
                }
            }

            output_file = base_input_path / test_case_id / "sim.json"
            with open(output_file, 'w') as f:
                json.dump(sim_json, f, indent=2)

            click.echo(f"✓ Parsed: {output_file}")
            parsed_count += 1

        except Exception as e:
            click.echo(f"✗ Error parsing {sim_file}: {e}")

    click.echo()
    click.echo(f"✓ Parsed {parsed_count} files")


@click.command(name="run")
@click.argument("driver_name")
@click.argument("enclosure_type")
@click.option("--test-case", "-t", help="Specific test case ID (default: all)")
@click.option("--metrics", "-m", multiple=True, default=["ze", "phase", "spl"],
              help="Metrics to validate (default: ze, phase, spl)")
def validate_run(driver_name: str, enclosure_type: str, test_case: Optional[str], metrics: tuple):
    """
    Run validation comparisons and generate validation.json.

    Compares gsd simulation results against Hornresp reference data
    and generates validation.json files with pass/fail status and error metrics.

    DRIVER_NAME: Driver name (e.g., bc_8ndl51)
    ENCLOSURE_TYPE: Enclosure type (infinite_baffle, sealed_box, ported_box)
    --test-case: Optional specific test case ID

    Example:
        gsd validate run bc_8ndl51 sealed_box
        gsd validate run bc_8ndl51 ported_box --test-case bc_8ndl51_ported_b4
    """
    driver_name_normalized = driver_name.lower().replace("-", "_")

    # Load test cases
    test_cases_data = load_test_cases_json(driver_name_normalized, enclosure_type)

    # Load driver
    driver_data = load_driver_json(driver_name_normalized)
    driver = get_driver_from_json(driver_data)

    results_path = get_enclosure_path(driver_name_normalized, enclosure_type) / "results"

    click.echo(f"Running validation for {driver_name} / {enclosure_type}")
    click.echo()

    # Filter test cases if specific one requested
    test_cases_to_validate = test_cases_data["test_cases"]
    if test_case:
        test_cases_to_validate = [tc for tc in test_cases_to_validate if tc["test_case_id"] == test_case]
        if not test_cases_to_validate:
            raise click.ClickException(f"Test case not found: {test_case}")

    validated_count = 0

    for test_case in test_cases_to_validate:
        test_case_id = test_case["test_case_id"]

        # Load sim.json
        sim_json_file = results_path / test_case_id / "sim.json"
        if not sim_json_file.exists():
            click.echo(f"⚠ Skipping {test_case_id}: sim.json not found")
            continue

        with open(sim_json_file, 'r') as f:
            sim_data = json.load(f)

        import numpy as np
        frequencies = np.array(sim_data["data"]["frequency"])
        ze_hornresp = np.array(sim_data["data"]["ze"])
        zephase_hornresp = np.array(sim_data["data"]["zephase"])
        spl_hornresp = np.array(sim_data["data"]["spl"])

        # Run gsd simulation (placeholder - actual implementation depends on enclosure type)
        # For now, we'll create a placeholder validation result
        click.echo(f"⚠ {test_case_id}: bugworks GSD simulation not yet implemented")

        # TODO: Implement actual gsd simulation based on enclosure type
        # This would call the appropriate enclosure simulation function
        # ze_gsd = calculate_electrical_impedance(driver, enclosure_params, frequencies)
        # spl_gsd = calculate_spl(driver, enclosure_params, frequencies)

        # Placeholder: Create validation.json with "skipped" status
        validation_json = {
            "test_case_id": test_case_id,
            "validation_date": datetime.now().strftime("%Y-%m-%d"),
            "gsd_version": "0.1.0",
            "hornresp_version": sim_data["metadata"]["hornresp_version"],
            "status": "skipped",
            "metrics": {
                "ze_magnitude": {"passed": None, "note": "bugworks GSD simulation not yet implemented"},
                "ze_phase": {"passed": None, "note": "bugworks GSD simulation not yet implemented"},
                "spl": {"passed": None, "note": "bugworks GSD simulation not yet implemented"}
            },
            "notes": "bugworks GSD simulation calculations not yet integrated with validation workflow"
        }

        output_file = results_path / test_case_id / "validation.json"
        with open(output_file, 'w') as f:
            json.dump(validation_json, f, indent=2)

        click.echo(f"✓ Generated: {output_file}")
        validated_count += 1

    click.echo()
    click.echo(f"✓ Validated {validated_count} test cases")


@click.command(name="status")
@click.option("--driver", "-d", help="Filter by driver name")
@click.option("--enclosure", "-e", help="Filter by enclosure type")
@click.option("--detailed", is_flag=True, help="Show detailed validation results")
def validate_status(driver: Optional[str], enclosure: Optional[str], detailed: bool):
    """
    Query and display validation status.

    Shows the current validation status for all drivers, test cases, and metrics.
    Use --detailed to see full error metrics and pass/fail information.

    Examples:
        gsd validate status
        gsd validate status --driver bc_8ndl51
        gsd validate status --driver bc_8ndl51 --enclosure sealed_box --detailed
    """
    base_path = get_validation_base_path() / "drivers"

    # Collect all drivers
    if driver:
        drivers_to_check = [base_path / driver.lower()]
    else:
        drivers_to_check = [d for d in base_path.iterdir() if d.is_dir()]

    click.echo("=" * 60)
    click.echo("VALIDATION STATUS")
    click.echo("=" * 60)
    click.echo()

    for driver_path in sorted(drivers_to_check):
        if not driver_path.exists():
            continue

        driver_name = driver_path.name
        driver_json_file = driver_path / "driver.json"

        # Load driver metadata
        if driver_json_file.exists():
            with open(driver_json_file, 'r') as f:
                driver_data = json.load(f)
            validation_status = driver_data.get("validation_status", "unknown")
            enclosures = driver_data.get("enclosures_validated", [])
        else:
            validation_status = "no_metadata"
            enclosures = []

        click.echo(f"Driver: {driver_name.upper()}")
        click.echo(f"  Status: {validation_status}")

        # Filter enclosures if specified
        if enclosure:
            enclosures_to_check = [driver_path / enclosure]
        else:
            enclosures_to_check = [driver_path / e for e in enclosures if (driver_path / e).exists()]

        for enclosure_path in sorted(enclosures_to_check):
            if not enclosure_path.exists():
                continue

            enclosure_type = enclosure_path.name
            test_cases_file = enclosure_path / "test_cases.json"

            if not test_cases_file.exists():
                click.echo(f"  {enclosure_type}: No test cases defined")
                continue

            with open(test_cases_file, 'r') as f:
                test_cases_data = json.load(f)

            # Count test cases by status
            total = len(test_cases_data["test_cases"])
            passed = sum(1 for tc in test_cases_data["test_cases"] if tc["status"] == "passed")
            failed = sum(1 for tc in test_cases_data["test_cases"] if tc["status"] == "failed")
            pending = sum(1 for tc in test_cases_data["test_cases"] if tc["status"] == "pending")

            click.echo(f"  {enclosure_type}:")
            click.echo(f"    Total: {total} | Passed: {passed} | Failed: {failed} | Pending: {pending}")

            # Show detailed results if requested
            if detailed:
                results_path = enclosure_path / "results"
                for tc in test_cases_data["test_cases"]:
                    tc_id = tc["test_case_id"]
                    status = tc["status"]

                    # Load validation.json if exists
                    validation_json_file = results_path / tc_id / "validation.json"
                    if validation_json_file.exists():
                        with open(validation_json_file, 'r') as f:
                            validation_data = json.load(f)

                        click.echo(f"      {tc_id}: {status}")

                        if validation_data.get("metrics"):
                            for metric_name, metric_data in validation_data["metrics"].items():
                                passed = metric_data.get("passed")
                                if passed is True:
                                    click.echo(f"        ✓ {metric_name}")
                                elif passed is False:
                                    click.echo(f"        ✗ {metric_name}")
                                elif passed is None:
                                    note = metric_data.get("note", "skipped")
                                    click.echo(f"        ⊘ {metric_name}: {note}")
                    else:
                        click.echo(f"      {tc_id}: {status} (no validation data)")

        click.echo()

    click.echo("=" * 60)


@click.command(name="migrate")
@click.argument("driver_name")
@click.option("--dry-run", is_flag=True, help="Show migration plan without executing")
@click.option("--backup", is_flag=True, help="Create backup before migrating")
def validate_migrate(driver_name: str, dry_run: bool, backup: bool):
    """
    Migrate existing validation data to new format.

    Converts legacy validation data (README.md tables, input_*.txt files)
    to the new standardized JSON-based format.

    DRIVER_NAME: Driver name (e.g., bc_8ndl51)

    Examples:
        gsd validate migrate bc_8ndl51 --dry-run
        gsd validate migrate bc_8ndl51 --backup
    """
    driver_name_normalized = driver_name.lower().replace("-", "_")
    driver_path = get_driver_path(driver_name_normalized)

    if not driver_path.exists():
        raise click.ClickException(f"Driver directory not found: {driver_path}")

    click.echo("=" * 70)
    click.echo(f"MIGRATION PLAN: {driver_name.upper()}")
    click.echo("=" * 70)
    click.echo()

    # Step 1: Find all enclosure directories
    enclosure_dirs = []
    for item in driver_path.iterdir():
        if item.is_dir() and not item.name.startswith('.') and item.name != "results":
            enclosure_dirs.append(item)

    if not enclosure_dirs:
        raise click.ClickException(f"No enclosure directories found in {driver_path}")

    click.echo(f"Found {len(enclosure_dirs)} enclosure directories:")
    for enc_dir in enclosure_dirs:
        click.echo(f"  - {enc_dir.name}/")
    click.echo()

    # Step 2: Parse driver parameters from first README.md found
    driver_params = None
    for enc_dir in enclosure_dirs:
        readme_path = enc_dir / "README.md"
        if readme_path.exists():
            params = parse_readme_driver_params(readme_path)
            if params:
                driver_params = params
                click.echo(f"✓ Parsed driver parameters from {enc_dir.name}/README.md")
                click.echo(f"  Model: {params.get('model', 'Unknown')}")
                click.echo(f"  Manufacturer: {params.get('manufacturer', 'Unknown')}")
                if "size_inches" in params:
                    click.echo(f"  Size: {params['size_inches']}\"")
                click.echo()
                break

    if not driver_params:
        click.echo("⚠ Warning: Could not parse driver parameters from README.md")
        click.echo()

    # Step 3: Process each enclosure directory
    migration_plan = []

    for enc_dir in enclosure_dirs:
        enclosure_type = enc_dir.name
        readme_path = enc_dir / "README.md"

        click.echo(f"Processing {enclosure_type}/")
        click.echo("-" * 70)

        if not readme_path.exists():
            click.echo(f"  ⚠ No README.md found, skipping")
            click.echo()
            continue

        # Parse test cases from README
        parsed_test_cases = parse_readme_test_cases(readme_path)

        if not parsed_test_cases:
            click.echo(f"  ⚠ No test cases found in README.md")
            click.echo()
            continue

        click.echo(f"  Found {len(parsed_test_cases)} test cases:")
        for tc in parsed_test_cases:
            click.echo(f"    - {tc['input_file']} ({tc['status']})")

        # Check for ql/ subdirectory
        ql_dir = enc_dir / "ql"
        has_ql_subdir = ql_dir.exists() and ql_dir.is_dir()

        if has_ql_subdir:
            click.echo(f"  Found ql/ subdirectory (will be flattened)")

        # Collect existing input files
        input_files = list(enc_dir.glob("input_*.txt"))
        if has_ql_subdir:
            input_files.extend(ql_dir.glob("input_*.txt"))

        click.echo(f"  Found {len(input_files)} input files")

        # Collect existing sim files
        sim_files = list(enc_dir.glob("sim*.txt"))
        if has_ql_subdir:
            sim_files.extend(ql_dir.glob("sim*.txt"))

        click.echo(f"  Found {len(sim_files)} simulation files")
        click.echo()

        migration_plan.append({
            "enclosure_type": enclosure_type,
            "test_cases": parsed_test_cases,
            "has_ql_subdir": has_ql_subdir,
            "input_files": input_files,
            "sim_files": sim_files
        })

    # Step 4: Create migration summary
    click.echo("=" * 70)
    click.echo("MIGRATION SUMMARY")
    click.echo("=" * 70)
    click.echo()

    total_test_cases = sum(len(plan["test_cases"]) for plan in migration_plan)
    total_input_files = sum(len(plan["input_files"]) for plan in migration_plan)
    total_sim_files = sum(len(plan["sim_files"]) for plan in migration_plan)

    click.echo(f"Total test cases to migrate: {total_test_cases}")
    click.echo(f"Total input files to reorganize: {total_input_files}")
    click.echo(f"Total sim files to reorganize: {total_sim_files}")
    click.echo()

    # Files that will be created
    click.echo("Files to be created:")
    click.echo(f"  - {driver_path}/driver.json")
    for plan in migration_plan:
        enc_type = plan["enclosure_type"]
        click.echo(f"  - {driver_path}/{enc_type}/test_cases.json")
        for tc in plan["test_cases"]:
            test_case_id = extract_test_case_id_from_filename(
                tc["input_file"], driver_name_normalized, enc_type
            )
            click.echo(f"    └─ {enc_type}/results/{test_case_id}/")
            click.echo(f"       ├── input.txt")
            click.echo(f"       ├── input.json")
            if any(sim.name.startswith(tc["input_file"].replace("input", "sim").split(".")[0]) for sim in plan["sim_files"]):
                click.echo(f"       ├── sim.txt (if exists)")
                click.echo(f"       └── sim.json")
    click.echo()

    if dry_run:
        click.echo("=" * 70)
        click.echo("DRY RUN COMPLETE - No files were modified")
        click.echo("=" * 70)
        click.echo()
        click.echo("To run the migration, execute:")
        click.echo(f"  gsd validate migrate {driver_name}")
        if backup:
            click.echo()
            click.echo("Note: --backup flag will be ignored in dry-run mode")
        return

    # Step 5: Create backup if requested
    if backup:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = driver_path.parent / f"{driver_path.name}_backup_{timestamp}"

        click.echo(f"Creating backup: {backup_path.name}")
        try:
            shutil.copytree(driver_path, backup_path)
            click.echo(f"✓ Backup created successfully")
            click.echo()
        except Exception as e:
            raise click.ClickException(f"Failed to create backup: {e}")

    # Step 6: Execute migration
    click.echo("=" * 70)
    click.echo("EXECUTING MIGRATION")
    click.echo("=" * 70)
    click.echo()

    try:
        # Create driver.json
        if driver_params:
            enclosures_validated = [plan["enclosure_type"] for plan in migration_plan]
            driver_json = create_driver_json(driver_params, enclosures_validated)

            driver_json_path = driver_path / "driver.json"
            with open(driver_json_path, 'w') as f:
                json.dump(driver_json, f, indent=2)

            click.echo(f"✓ Created: {driver_json_path}")

        # Process each enclosure
        for plan in migration_plan:
            enc_type = plan["enclosure_type"]
            enc_dir = driver_path / enc_type
            readme_path = enc_dir / "README.md"

            with open(readme_path, 'r') as f:
                readme_content = f.read()

            # Create test_cases.json
            test_cases_json = create_test_cases_json(
                driver_name_normalized,
                enc_type,
                plan["test_cases"],
                readme_content
            )

            test_cases_json_path = enc_dir / "test_cases.json"
            with open(test_cases_json_path, 'w') as f:
                json.dump(test_cases_json, f, indent=2)

            click.echo(f"✓ Created: {test_cases_json_path}")

            # Create results directory
            results_dir = enc_dir / "results"
            results_dir.mkdir(exist_ok=True)

            # Migrate each test case
            for tc in plan["test_cases"]:
                input_filename = tc["input_file"]
                test_case_id = extract_test_case_id_from_filename(
                    input_filename, driver_name_normalized, enc_type
                )

                # Create test case directory
                tc_dir = results_dir / test_case_id
                tc_dir.mkdir(exist_ok=True)

                # Find input file (check both main dir and ql/ subdirectory)
                input_file = None
                main_input = enc_dir / input_filename
                ql_input = enc_dir / "ql" / input_filename

                if main_input.exists():
                    input_file = main_input
                elif ql_input.exists():
                    input_file = ql_input

                if input_file:
                    # Copy input.txt
                    shutil.copy2(input_file, tc_dir / "input.txt")

                    # Create input.json
                    params = infer_enclosure_parameters_from_filename(input_filename, enc_type)
                    input_json = {
                        "test_case_id": test_case_id,
                        "driver": driver_name_normalized.upper(),
                        "enclosure_type": enc_type,
                        "enclosure_parameters": params,
                        "generated_at": datetime.now().isoformat(),
                    }

                    with open(tc_dir / "input.json", 'w') as f:
                        json.dump(input_json, f, indent=2)

                    click.echo(f"  ✓ Migrated: {test_case_id}")

                    # Check for corresponding sim file
                    sim_prefix = input_filename.replace("input_", "sim_").replace(".txt", "")
                    sim_file = None

                    # Try different naming patterns
                    possible_sim_names = [
                        f"{sim_prefix}.txt",
                        f"{sim_prefix.replace('sim_qtc', 'sim_qtc')}.txt",  # Handle underscores
                        input_filename.replace("input_", "sim.txt"),  # Generic sim.txt
                    ]

                    for sim_name in possible_sim_names:
                        test_sim = enc_dir / sim_name
                        test_sim_ql = enc_dir / "ql" / sim_name
                        if test_sim.exists():
                            sim_file = test_sim
                            break
                        elif test_sim_ql.exists():
                            sim_file = test_sim_ql
                            break

                    if sim_file:
                        shutil.copy2(sim_file, tc_dir / "sim.txt")
                        click.echo(f"    └─ Copied sim.txt")
                        # Note: sim.json will be created by parse-output command

        click.echo()
        click.echo("=" * 70)
        click.echo("MIGRATION COMPLETE")
        click.echo("=" * 70)
        click.echo()
        click.echo("Next steps:")
        click.echo(f"1. Review the migrated data structure:")
        click.echo(f"   ls -la {driver_path}")
        click.echo()
        click.echo(f"2. Parse Hornresp sim.txt files to JSON:")
        click.echo(f"   for enclosure in {' '.join([plan['enclosure_type'] for plan in migration_plan])}; do")
        click.echo(f"     gsd validate parse-output {driver_name} $enclosure")
        click.echo(f"   done")
        click.echo()
        click.echo(f"3. Check validation status:")
        click.echo(f"   gsd validate status --driver {driver_name}")
        click.echo()

    except Exception as e:
        click.echo()
        click.echo("=" * 70)
        click.echo(f"MIGRATION FAILED: {e}")
        click.echo("=" * 70)
        if backup:
            click.echo()
            click.echo(f"Backup is available at: {backup_path}")
            click.echo(f"To restore: mv {backup_path} {driver_path}")
        raise click.ClickException(f"Migration failed: {e}")
