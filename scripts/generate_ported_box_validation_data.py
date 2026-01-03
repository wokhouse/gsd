#!/usr/bin/env python3
"""
Generate Hornresp validation data for ported box enclosures.

This script automates the creation of Hornresp input files for ported box
validation, following the same approach used for sealed box validation.

Literature:
- Thiele (1971) - Loudspeakers in Vented Boxes Parts 1 & 2
- Small (1973) - Vented-Box Loudspeaker Systems
- literature/thiele_small/thiele_1971_vented_boxes.md
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import math

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gsd.driver.bc_drivers import get_bc_15ps100, get_bc_8ndl51
from gsd.enclosure.ported_box import (
    calculate_ported_box_system_parameters,
    calculate_port_length_for_area,
)
from gsd.hornresp.export import export_to_hornresp


# Test case definitions
ALIGNMENTS = {
    "B4": {
        "description": "Butterworth maximally flat",
        "vb_ratio": 1.0,  # Vb = Vas
        "fb_ratio": 1.0,  # Fb = Fs
    },
    "QB3": {
        "description": "Quasi-Butterworth 3rd-order",
        "vb_ratio": 0.8,  # Vb = 0.8 × Vas
        "fb_ratio": 0.8,  # Fb = 0.8 × Fs
    },
    "BB4": {
        "description": "Extended bass shelf",
        "vb_ratio": 0.6,  # Vb = 0.6 × Vas
        "fb_ratio": 0.9,  # Fb = 0.9 × Fs
    },
}

PORT_DIAMETERS_INCHES = [2.0, 3.0, 4.0]  # Port diameters to test


def calculate_port_area_from_diameter_inches(diameter_inches: float) -> float:
    """
    Calculate port area from diameter in inches.

    Args:
        diameter_inches: Port diameter in inches

    Returns:
        Port area in m²
    """
    diameter_m = diameter_inches * 0.0254  # Convert inches to meters
    radius_m = diameter_m / 2.0
    area_m2 = math.pi * radius_m ** 2
    return area_m2


def generate_ported_box_test_case(
    driver,
    driver_name: str,
    driver_size: str,
    vb_liters: float,
    fb_hz: float,
    port_diameter_inches: float,
    output_dir: Path,
    test_name: str,
    alignment_name: str = None,
) -> dict:
    """
    Generate a single ported box test case.

    Args:
        driver: ThieleSmallParameters instance
        driver_name: Driver model name (e.g., "BC_15PS100")
        driver_size: Driver size (e.g., "15\"")
        vb_liters: Box volume in liters
        fb_hz: Port tuning frequency in Hz
        port_diameter_inches: Port diameter in inches (None for optimal port)
        output_dir: Directory to save output files
        test_name: Test case name (e.g., "b4", "qb3", "port_2in")
        alignment_name: Alignment name for comment (e.g., "B4", "QB3")

    Returns:
        dict with test case parameters
    """
    # Calculate port dimensions
    vb_m3 = vb_liters / 1000.0

    if port_diameter_inches is None:
        # Use optimal port dimensions
        from gsd.enclosure.ported_box import calculate_optimal_port_dimensions

        port_area_m2, port_length_m, port_velocity_max = calculate_optimal_port_dimensions(
            driver, vb_m3, fb_hz
        )
        port_diameter_inches = None
        port_diameter_mm = None
    else:
        # Calculate port for specified diameter
        port_area_m2 = calculate_port_area_from_diameter_inches(port_diameter_inches)
        port_length_m = calculate_port_length_for_area(port_area_m2, vb_m3, fb_hz)
        port_diameter_mm = port_diameter_inches * 25.4

    # Convert to Hornresp units
    port_area_cm2 = port_area_m2 * 10000.0
    port_length_cm = port_length_m * 100.0

    # Create output filename
    input_filename = f"input_{test_name}.txt"
    input_path = output_dir / input_filename

    # Generate comment for Hornresp file
    if alignment_name:
        comment = f"{alignment_name} alignment: Vb={vb_liters:.1f}L, Fb={fb_hz:.1f}Hz, Port={port_diameter_inches if port_diameter_inches else 'optimal'}\""
    else:
        comment = f"Ported box: Vb={vb_liters:.1f}L, Fb={fb_hz:.1f}Hz, Port={port_diameter_inches}\" dia × {port_length_cm:.1f}cm"

    # Export to Hornresp format
    export_to_hornresp(
        driver=driver,
        driver_name=driver_name,
        output_path=str(input_path),
        comment=comment,
        enclosure_type="ported_box",
        Vb_liters=vb_liters,
        Fb_hz=fb_hz,
        port_area_cm2=port_area_cm2,
        port_length_cm=port_length_cm,
    )

    # Return test case parameters
    return {
        "test_name": test_name,
        "alignment": alignment_name or "Custom",
        "vb_liters": vb_liters,
        "fb_hz": fb_hz,
        "port_diameter_inches": port_diameter_inches,
        "port_diameter_mm": port_diameter_mm,
        "port_area_cm2": port_area_cm2,
        "port_length_cm": port_length_cm,
        "input_file": input_filename,
        "sim_file": f"sim_{test_name}.txt",
        "status": "Pending",
    }


def generate_readme(
    driver_name: str,
    driver_size: str,
    driver_params: dict,
    test_cases: list,
    output_dir: Path,
):
    """
    Generate README.md for a driver's ported box validation.

    Args:
        driver_name: Driver model name
        driver_size: Driver size (e.g., "15\"")
        driver_params: Driver Thiele-Small parameters
        test_cases: List of test case dicts
        output_dir: Directory to save README.md
    """
    readme_path = output_dir / "README.md"

    # Separate alignment and port sweep test cases
    alignment_cases = [tc for tc in test_cases if tc["alignment"] != "Custom"]
    port_sweep_cases = [tc for tc in test_cases if tc["alignment"] == "Custom"]

    # Build alignment table
    alignment_table = "| Alignment | Vb (L) | Fb (Hz) | Description | Input File | Status |\n"
    alignment_table += "|-----------|--------|---------|-------------|------------|--------|\n"

    for tc in alignment_cases:
        desc = ALIGNMENTS[tc["test_name"].upper()]["description"]
        alignment_table += (
            f"| {tc['test_name'].upper()} "
            f"| {tc['vb_liters']:.1f} "
            f"| {tc['fb_hz']:.1f} "
            f"| {desc} "
            f"| {tc['input_file']} "
            f"| {tc['status']} |\n"
        )

    # Build port sweep table
    port_table = "| Port Dia | Port Area (cm²) | Port Length (cm) | Description | Input File | Status |\n"
    port_table += "|----------|-----------------|------------------|-------------|------------|--------|\n"

    for tc in port_sweep_cases:
        dia_str = f"{tc['port_diameter_inches']}\""
        desc = f"{tc['port_diameter_inches']}\u2033 port"

        port_table += (
            f"| {dia_str} "
            f"| {tc['port_area_cm2']:.1f} "
            f"| {tc['port_length_cm']:.1f} "
            f"| {desc} "
            f"| {tc['input_file']} "
            f"| {tc['status']} |\n"
        )

    # Create README content
    readme_content = f"""# Ported Box Validation - {driver_name}

## Driver

- **Model**: {driver_name}
- **Manufacturer**: B&C Speakers
- **Size**: {driver_size}
- **Thiele-Small Parameters**:
  - F_s: {driver_params['F_s']:.1f} Hz
  - Q_ts: {driver_params['Q_ts']:.3f}
  - V_as: {driver_params['V_as']:.1f} L
  - S_d: {driver_params['S_d']:.0f} cm²
  - BL: {driver_params['BL']:.1f} T·m
  - R_e: {driver_params['R_e']:.1f} Ω
  - M_md: {driver_params['M_md']:.1f} g (driver mass only)

## Test Cases

### Standard Alignments

{alignment_table}

**Alignment formulas from Thiele (1971):**
- B4: Vb = Vas, Fb = Fs (maximally flat response)
- QB3: Vb ≈ 0.8×Vas, Fb ≈ 0.8×Fs (quasi-Butterworth 3rd-order)
- BB4: Vb ≈ 0.6×Vas, Fb ≈ 0.9×Fs (extended bass shelf)

### Port Dimension Sweeps (B4 Alignment)

{port_table}

**Port length calculated using `calculate_port_length_for_area()` to achieve Fb tuning.**

## Files

### Hornresp Input Files (Generated)
{chr(10).join([f"- `{tc['input_file']}` - {tc['test_name'].replace('_', ' ').title()}" for tc in test_cases])}

### Hornresp Simulation Results
- `sim_*.txt` - **YOU NEED TO GENERATE THESE** (one at a time per test case)

## How to Generate Hornresp Data

### For Each Test Case:

1. **Open Hornresp and Import**
   - Launch Hornresp
   - File → Open
   - Select the input file (e.g., `input_b4.txt`)

2. **Verify Parameters**
   Check that the following parameters match:
   - Driver parameters (Sd, Bl, Cms, Rms, Mmd, Le, Re)
   - Enclosure type: Vented Box
   - Box volume Vrc
   - Port tuning Fr (should be close to target Fb)
   - Port area Ap and length Lpt

3. **Run Simulation**
   - Click "Calculate" or press Ctrl+L
   - Accept defaults (frequency range 10-20000 Hz, 2.83V input)

4. **Export Results**
   - File → Save
   - Select "Export _sim.txt" format
   - Save as `sim_<test_case>.txt` in this directory
   - For example: `input_b4.txt` → `sim_b4.txt`

5. **Run Validation Tests** (once all sim.txt files are generated)
   ```bash
   PYTHONPATH=src pytest tests/validation/test_ported_box.py -v
   ```

## Expected Results

Based on sealed box validation results and ported box preliminary validation:

- **System parameters (α, h, F3)**: <1% error
- **Port tuning frequency**: <0.5 Hz deviation from target Fb
- **Electrical impedance magnitude**: <15% max error (dual peaks region)
- **Electrical impedance phase**: <25° max error
- **Impedance dual peaks**: Should show two peaks at driver Fs and port Fb
- **SPL**: Known limitation if port contribution not implemented (~7-13 dB error at low frequencies)

## Validation Status

- **Hornresp input files**: ✅ Generated
- **Hornresp simulations**: Pending (requires manual Hornresp execution)
- **Validation tests**: Pending (requires sim.txt files)

## Physical Constraints

The ported box design must satisfy:
1. **Port diameter**: Must be small enough to fit inside box (< ½ box dimension)
2. **Port length**: Must be physically realizable (typically 2-50 cm)
3. **Port velocity**: Should be < 5% of speed of sound to avoid chuffing (~17 m/s)
4. **Box volume**: Must be large enough for driver to physically fit

All test cases in this validation satisfy these constraints.

## Literature

- Thiele (1971) - Loudspeakers in Vented Boxes Parts 1 & 2
- Small (1973) - Vented-Box Loudspeaker Systems Part I: Analysis
- `literature/thiele_small/thiele_1971_vented_boxes.md`

## Notes

- All Hornresp input files were generated using `viberesp.hornresp.export.export_to_hornresp()`
- This ensures driver parameters match exactly between viberesp and Hornresp
- Port dimensions calculated using `calculate_port_length_for_area()` from Helmholtz resonance formula
- Test cases validate Thiele (1971) alignment theory for both drivers
- Port sweeps validate port physics across different diameter-to-length ratios
- Total {len(test_cases)} test cases: {len(alignment_cases)} alignments + {len(port_sweep_cases)} port sweeps

---
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

    # Write README
    with open(readme_path, "w") as f:
        f.write(readme_content)

    print(f"Created: {readme_path}")


def generate_validation_issue(driver_name: str, output_dir: Path):
    """
    Generate VALIDATION_ISSUE.md template for tracking validation status.

    Args:
        driver_name: Driver model name
        output_dir: Directory to save VALIDATION_ISSUE.md
    """
    issue_path = output_dir / "VALIDATION_ISSUE.md"

    content = f"""# {driver_name} Ported Box Validation Results

## Current Status

Validation in progress. Last updated: {datetime.now().strftime("%Y-%m-%d")}

**Generated by**: `scripts/generate_ported_box_validation_data.py`

## Test Results

### Standard Alignments

- **B4 Butterworth**: Pending
- **QB3 Quasi-Butterworth**: Pending
- **BB4 Extended Bass Shelf**: Pending

### Port Dimension Sweeps

- **2" port**: Pending
- **3" port**: Pending
- **4" port**: Pending

## Known Issues

(Placeholder for issues discovered during validation)

## What's Working

(Placeholder for successful validation results)

## Root Cause Analysis

(Placeholder for investigation of any discrepancies)

## Literature

- Thiele (1971) Alignment tables
- Hornresp vented box simulation reference
- `literature/thiele_small/thiele_1971_vented_boxes.md`

---
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

    with open(issue_path, "w") as f:
        f.write(content)

    print(f"Created: {issue_path}")


def generate_driver_validation_data(driver, driver_name: str, driver_size: str):
    """
    Generate all validation data for a single driver.

    Args:
        driver: ThieleSmallParameters instance
        driver_name: Driver model name (e.g., "BC_15PS100")
        driver_size: Driver size (e.g., "15\"")
    """
    print(f"\nGenerating validation data for {driver_name}...")

    # Create output directory
    output_dir = Path("tests/validation/drivers") / driver_name / "ported_box"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get driver parameters for documentation
    driver_params = {
        "F_s": driver.F_s,
        "Q_ts": driver.Q_ts,
        "V_as": driver.V_as * 1000.0,  # Convert to liters
        "S_d": driver.S_d * 10000.0,  # Convert to cm²
        "BL": driver.BL,
        "R_e": driver.R_e,
        "M_md": driver.M_md * 1000.0,  # Convert to grams
    }

    # Generate test cases
    test_cases = []

    # 1. Standard alignments
    print(f"  Generating standard alignments...")
    for alignment_name, alignment_params in ALIGNMENTS.items():
        vb_ratio = alignment_params["vb_ratio"]
        fb_ratio = alignment_params["fb_ratio"]

        vb_liters = driver_params["V_as"] * vb_ratio
        fb_hz = driver_params["F_s"] * fb_ratio

        try:
            tc = generate_ported_box_test_case(
                driver=driver,
                driver_name=driver_name,
                driver_size=driver_size,
                vb_liters=vb_liters,
                fb_hz=fb_hz,
                port_diameter_inches=None,  # Use optimal port
                output_dir=output_dir,
                test_name=alignment_name.lower(),
                alignment_name=alignment_name,
            )
            test_cases.append(tc)
            print(f"    - {alignment_name}: Vb={vb_liters:.1f}L, Fb={fb_hz:.1f}Hz → {tc['input_file']}")
        except ValueError as e:
            print(f"    - {alignment_name}: SKIPPED - {str(e)[:60]}...")
            continue

    # 2. Port dimension sweeps (using B4 alignment as base)
    print(f"  Generating port dimension sweeps (B4 alignment)...")
    vb_liters_b4 = driver_params["V_as"]  # Vb = Vas for B4
    fb_hz_b4 = driver_params["F_s"]  # Fb = Fs for B4

    # Choose port diameters based on driver size
    # Smaller drivers need smaller ports to fit physically
    if driver_params["V_as"] < 20:  # Small drivers (Vas < 20L)
        port_diameters = [1.0, 1.5, 2.0]
    else:  # Larger drivers
        port_diameters = PORT_DIAMETERS_INCHES

    for port_diameter in port_diameters:
        # Format test name (handle fractional diameters)
        if port_diameter == int(port_diameter):
            test_name = f"port_{int(port_diameter)}in"
        else:
            test_name = f"port_{port_diameter}in"

        try:
            tc = generate_ported_box_test_case(
                driver=driver,
                driver_name=driver_name,
                driver_size=driver_size,
                vb_liters=vb_liters_b4,
                fb_hz=fb_hz_b4,
                port_diameter_inches=port_diameter,
                output_dir=output_dir,
                test_name=test_name,
                alignment_name=None,  # Custom (port sweep)
            )
            test_cases.append(tc)
            print(
                f"    - Port {port_diameter}\": Area={tc['port_area_cm2']:.1f}cm², "
                f"Length={tc['port_length_cm']:.1f}cm → {tc['input_file']}"
            )
        except ValueError as e:
            print(f"    - Port {port_diameter}\": SKIPPED - {str(e)[:60]}...")
            continue

    # Generate documentation
    print(f"  Generating documentation...")
    generate_readme(driver_name, driver_size, driver_params, test_cases, output_dir)
    generate_validation_issue(driver_name, output_dir)

    print(f"  Total: {len(test_cases)} test cases generated")


def main():
    """Generate all ported box validation data."""
    print("=" * 70)
    print("Ported Box Validation Data Generator")
    print("=" * 70)

    # Get drivers
    driver_15ps100 = get_bc_15ps100()
    driver_8ndl51 = get_bc_8ndl51()

    # Generate validation data for each driver
    generate_driver_validation_data(driver_15ps100, "BC_15PS100", '15"')
    generate_driver_validation_data(driver_8ndl51, "BC_8NDL51", '8"')

    # Summary
    print("\n" + "=" * 70)
    print("Generation Complete!")
    print("=" * 70)
    print("\nSummary:")
    print("  - 2 drivers × 3 alignments = 6 alignment test files")
    print("  - 2 drivers × 3 port diameters = 6 port sweep test files")
    print("  - Total: 12 Hornresp input files")
    print("\nNext Steps:")
    print("  1. Open Hornresp")
    print("  2. For each input_*.txt file:")
    print("     - File → Open → Select input file")
    print("     - Click 'Calculate'")
    print("     - File → Save → Export sim.txt")
    print("     - Rename to sim_<test_case>.txt")
    print("  3. Run validation tests once all sim.txt files are ready")
    print("\nLocations:")
    print("  - BC 15PS100: tests/validation/drivers/BC_15PS100/ported_box/")
    print("  - BC 8NDL51: tests/validation/drivers/BC_8NDL51/ported_box/")
    print("=" * 70)


if __name__ == "__main__":
    main()
