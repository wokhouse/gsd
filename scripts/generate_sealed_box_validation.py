#!/usr/bin/env python3
"""
Generate sealed box validation cases for Hornresp comparison.

This script creates Hornresp input files for sealed box enclosures across
multiple Qtc alignments, enabling systematic comparison between viberesp
and Hornresp simulations.

Literature:
- Small (1972) - Closed-Box Loudspeaker Systems Part I: Analysis
- literature/thiele_small/small_1972_closed_box.md
"""

import argparse
import json
from pathlib import Path
from typing import Optional

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gsd.driver.bc_drivers import get_bc_8ndl51
from gsd.driver.parameters import ThieleSmallParameters
from gsd.enclosure.sealed_box import calculate_sealed_box_system_parameters
from gsd.hornresp.export import export_to_hornresp


def calculate_vb_for_qtc(driver: ThieleSmallParameters, qtc_target: float) -> Optional[float]:
    """
    Calculate box volume for target Qtc alignment.

    Small (1972): Qtc = Qts × √(1 + α) where α = Vas/Vb
    Rearranging: Vb = Vas / ((Qtc/Qts)² - 1)

    Args:
        driver: ThieleSmallParameters instance
        qtc_target: Desired system Q factor

    Returns:
        Box volume in liters, or None if impossible (Qtc <= Qts)

    Literature:
        - Small (1972), Eq. for system Q
        - literature/thiele_small/small_1972_closed_box.md
    """
    if qtc_target <= driver.Q_ts:
        return None  # Impossible: Qtc must be > Qts

    # Small (1972): Vb = Vas / ((Qtc/Qts)² - 1)
    vb_m3 = driver.V_as / ((qtc_target / driver.Q_ts)**2 - 1)
    return vb_m3 * 1000.0  # Convert to liters


def classify_alignment(qtc: float) -> str:
    """
    Classify alignment based on Qtc value.

    Args:
        qtc: System Q factor

    Returns:
        Human-readable classification string
    """
    if qtc < 0.5:
        return "Over-damped (Qtc < 0.5)"
    elif 0.5 <= qtc < 0.6:
        return "Over-damped (transient-perfect)"
    elif 0.6 <= qtc < 0.68:
        return "Slightly over-damped"
    elif 0.68 <= qtc < 0.73:
        return "Butterworth (maximally flat) ✓"
    elif 0.73 <= qtc < 0.9:
        return "Bessel-like (smooth roll-off)"
    elif 0.9 <= qtc < 1.1:
        return "Chebyshev-like (slight peak)"
    elif qtc >= 1.1:
        return "Under-damped (prominent peak)"
    else:
        return "Unknown"


def get_alignment_description(qtc: float) -> str:
    """
    Get detailed description of response characteristics.

    Args:
        qtc: System Q factor

    Returns:
        Description of frequency response characteristics
    """
    if 0.68 <= qtc < 0.73:
        return "Maximally flat amplitude response in the passband."
    elif 0.5 <= qtc < 0.68:
        return "Optimal transient response, slightly rolled-off bass."
    elif 0.9 <= qtc < 1.1:
        return "Slight bass peak (~1-2 dB), good transient response."
    elif qtc >= 1.1:
        return "Prominent bass peak (>2 dB), degraded transient response."
    else:
        return "Smooth roll-off with gentle bass emphasis."


def generate_qtc_alignments(
    driver: ThieleSmallParameters,
    driver_name: str,
    output_base: Path,
    qtc_targets: list[float],
) -> list[dict]:
    """
    Generate Hornresp files for standard Qtc alignments.

    Args:
        driver: ThieleSmallParameters instance
        driver_name: Driver name (e.g., "BC_8NDL51")
        output_base: Base directory for output
        qtc_targets: List of target Qtc values to generate

    Returns:
        List of summary dictionaries for each generated case
    """
    summary_data = []

    # Qtc label mapping
    qtc_labels = {
        0.707: "butterworth",
        1.0: "underdamped_slight",
        1.2: "underdamped",
    }

    print(f"\nGenerating {len(qtc_targets)} Qtc alignments for {driver_name}...")

    for qtc_target in qtc_targets:
        print(f"\n{'='*60}")
        print(f"Qtc = {qtc_target:.3f}")
        print(f"{'='*60}")

        # Calculate box volume for target Qtc
        vb_liters = calculate_vb_for_qtc(driver, qtc_target)

        if vb_liters is None or vb_liters <= 0:
            print(f"⚠ Skipping Qtc={qtc_target:.3f} (impossible for {driver_name})")
            print(f"   Driver Qts={driver.Q_ts:.3f} must be < target Qtc")
            continue

        print(f"✓ Box volume: {vb_liters:.2f} L")

        # Calculate expected system parameters
        params = calculate_sealed_box_system_parameters(driver, vb_liters / 1000.0)

        print(f"✓ System resonance (Fc): {params.Fc:.1f} Hz")
        print(f"✓ System Q (Qtc): {params.Qtc:.3f}")
        print(f"✓ -3dB frequency (F3): {params.F3:.1f} Hz")
        print(f"✓ Compliance ratio (α): {params.alpha:.2f}")
        print(f"✓ Classification: {classify_alignment(params.Qtc)}")

        # Create directory
        label = qtc_labels.get(qtc_target, f"qtc_{qtc_target:.3f}")
        case_name = f"qtc_{qtc_target:.3f}_{label}"
        case_dir = output_base / driver_name / case_name
        case_dir.mkdir(parents=True, exist_ok=True)

        print(f"✓ Output directory: {case_dir.relative_to(output_base)}")

        # Generate Hornresp file
        hornresp_file = case_dir / f"{driver_name}_qtc{qtc_target:.3f}.txt"
        try:
            export_to_hornresp(
                driver,
                driver_name,
                str(hornresp_file),
                enclosure_type="sealed_box",
                Vb_liters=vb_liters,
                comment=f"Qtc={qtc_target:.3f} alignment - {classify_alignment(params.Qtc)}",
            )
            print(f"✓ Hornresp file: {hornresp_file.name}")
        except ValueError as e:
            # Box too small to physically fit the driver
            print(f"⚠ Skipping Qtc={qtc_target:.3f} (box too small for driver)")
            print(f"   {str(e)}")
            # Clean up directory
            for item in case_dir.iterdir():
                if item.is_dir():
                    for subitem in item.iterdir():
                        subitem.unlink()
                    item.rmdir()
                else:
                    item.unlink()
            case_dir.rmdir()
            continue

        # Generate metadata.json
        metadata = {
            "driver_name": f"{driver_name}-8",
            "driver_parameters": {
                "Fs_Hz": round(driver.F_s, 1),
                "Qts": round(driver.Q_ts, 3),
                "Vas_L": round(driver.V_as * 1000, 1),
                "Re_ohm": round(driver.R_e, 1),
                "M_md_g": round(driver.M_md * 1000, 2),
                "S_d_cm2": round(driver.S_d * 10000, 0),
            },
            "literature": "Small (1972) - Closed-Box Loudspeaker Systems Part I",
            "literature_reference": "literature/thiele_small/small_1972_closed_box.md",
        }

        metadata_file = case_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
        print(f"✓ Metadata: {metadata_file.name}")

        # Generate expected_parameters.json
        expected = {
            "target_Qtc": qtc_target,
            "box_parameters": {
                "Vb_L": round(vb_liters, 2),
                "alpha": round(params.alpha, 3),
            },
            "system_parameters": {
                "Fc_Hz": round(params.Fc, 1),
                "Qtc": round(params.Qtc, 3),
                "F3_Hz": round(params.F3, 1),
            },
            "alignment_class": classify_alignment(params.Qtc),
            "alignment_description": get_alignment_description(params.Qtc),
            "literature": "Small (1972) - Closed-Box Loudspeaker Systems Part I",
            "validation_tolerance": {
                "Fc_Hz": 0.5,
                "Qtc": 0.02,
                "F3_Hz": 0.5,
            },
        }

        expected_file = case_dir / "expected_parameters.json"
        with open(expected_file, "w") as f:
            json.dump(expected, f, indent=2)
        print(f"✓ Expected parameters: {expected_file.name}")

        # Generate README.md
        readme_content = f"""# Sealed Box Validation Case: Qtc = {qtc_target:.3f}

**Driver:** {driver_name}-8
**Alignment:** {classify_alignment(params.Qtc)}
**Box Volume:** {vb_liters:.2f} L
**System Resonance:** {params.Fc:.1f} Hz

## Description

{get_alignment_description(params.Qtc)}

## Hornresp Simulation Instructions

1. **Import the Hornresp file**
   - Open Hornresp
   - File → Open → Select `{hornresp_file.name}`
   - Verify: Ang=0.5xPi, Vrc={vb_liters:.2f}, Lrc=<auto>

2. **Configure sealed box**
   - Select "Rear Lined" (sealed box option)
   - This ensures the box is modeled as a sealed enclosure

3. **Set up frequency sweep**
   - Tools → Multiple Frequencies
   - Frequency range: 20 Hz - 20000 Hz
   - Number of points: 535 (Hornresp default)
   - Sweep type: Logarithmic
   - Input voltage: 2.83 V (1W into 8Ω)
   - Measurement distance: 1 m

4. **Run simulation**
   - Calculate
   - File → Save → Export _sim.txt
   - Save as: `sim.txt` in this directory

## Expected Results

Based on Small (1972) closed-box theory:

| Parameter | Expected Value | Tolerance |
|-----------|---------------|-----------|
| System Resonance (Fc) | {params.Fc:.1f} Hz | ±0.5 Hz |
| System Q (Qtc) | {params.Qtc:.3f} | ±0.02 |
| -3dB Frequency (F3) | {params.F3:.1f} Hz | ±0.5 Hz |
| Compliance Ratio (α) | {params.alpha:.2f} | ±0.01 |

## Key Validation Frequencies

When analyzing results, pay special attention to:

- **Fc/2** ({params.Fc/2:.1f} Hz) - Below resonance
- **Fc** ({params.Fc:.1f} Hz) - At resonance (impedance peak)
- **2×Fc** ({params.Fc*2:.1f} Hz) - Above resonance
- **F3** ({params.F3:.1f} Hz) - -3dB cutoff point
- **1 kHz** - Midrange reference
- **10 kHz** - High-frequency reference

## Literature

- Small (1972) - Closed-Box Loudspeaker Systems Part I: Analysis
- Reference: `literature/thiele_small/small_1972_closed_box.md`
"""

        readme_file = case_dir / "README.md"
        with open(readme_file, "w") as f:
            f.write(readme_content)
        print(f"✓ README: {readme_file.name}")

        # Add to summary
        summary_data.append({
            "case": case_name,
            "target_Qtc": qtc_target,
            "actual_Qtc": round(params.Qtc, 3),
            "Vb_L": round(vb_liters, 2),
            "Fc_Hz": round(params.Fc, 1),
            "F3_Hz": round(params.F3, 1),
            "alpha": round(params.alpha, 2),
            "classification": classify_alignment(params.Qtc),
        })

    return summary_data


def generate_summary_table(
    summary_data: list[dict],
    output_base: Path,
    driver_name: str,
):
    """
    Generate summary markdown table.

    Args:
        summary_data: List of case summaries from generate_qtc_alignments
        output_base: Base directory for output
        driver_name: Driver name
    """
    summary_file = output_base / driver_name / "summary.md"

    content = f"""# Sealed Box Validation Summary: {driver_name}

This document summarizes all sealed box validation cases generated for the
{driver_name} driver, comparing different Qtc alignments.

## Driver Parameters

| Parameter | Value |
|-----------|-------|
| Driver | {driver_name}-8 |
| Fs (Resonance) | 75.0 Hz |
| Qts (Total Q) | 0.616 |
| Vas (Equivalent Volume) | 10.1 L |
| Re (DC Resistance) | 2.6 Ω |
| M_md (Driver Mass) | 26.29 g |
| S_d (Piston Area) | 220 cm² |

## Validation Cases

| Case | Target Qtc | Actual Qtc | Vb (L) | Fc (Hz) | F3 (Hz) | α | Classification |
|------|-----------|-----------|--------|--------|--------|---|----------------|
"""

    for case in summary_data:
        content += (
            f"| {case['case']} | {case['target_Qtc']} | {case['actual_Qtc']} | "
            f"{case['Vb_L']} | {case['Fc_Hz']} | {case['F3_Hz']} | "
            f"{case['alpha']} | {case['classification']} |\n"
        )

    content += """
## Hornresp Simulation Settings

For all cases, use the following Hornresp settings:

- **Frequency range:** 20 Hz - 20,000 Hz
- **Number of points:** 535 (Hornresp default)
- **Sweep type:** Logarithmic
- **Input voltage:** 2.83 V (1W into 8Ω)
- **Measurement distance:** 1 m
- **Enclosure type:** Rear Lined (sealed box)

## Literature

All calculations based on:
- Small (1972) - Closed-Box Loudspeaker Systems Part I: Analysis
- Reference: `literature/thiele_small/small_1972_closed_box.md`

## Validation Workflow

1. Run `python scripts/generate_sealed_box_validation.py --driver {driver_name.lower()}`
2. For each case directory, follow the README.md instructions
3. Import Hornresp .txt file and run simulation
4. Export _sim.txt results to case directory
5. Compare viberesp results with Hornresp (future task)

---

Generated by viberesp sealed box validation generator.
"""

    with open(summary_file, "w") as f:
        f.write(content)

    print(f"\n✓ Summary table: {summary_file.relative_to(output_base)}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate sealed box validation cases for Hornresp"
    )
    parser.add_argument(
        "--driver",
        type=str,
        default="bc_8ndl51",
        choices=["bc_8ndl51"],
        help="Driver to generate validation cases for",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="tests/validation_data/sealed_boxes",
        help="Base output directory",
    )

    args = parser.parse_args()

    # Get driver
    if args.driver == "bc_8ndl51":
        driver = get_bc_8ndl51()
        driver_name = "BC_8NDL51"
    else:
        raise ValueError(f"Unknown driver: {args.driver}")

    # Output directory
    output_base = Path(args.output)

    # Qtc alignments to generate
    # Note: Qtc=0.5 is impossible for BC_8NDL51 (Qts=0.616 > 0.5)
    qtc_targets = [0.707, 1.0, 1.2]

    print("="*60)
    print("SEALED BOX VALIDATION GENERATOR")
    print("="*60)
    print(f"Driver: {driver_name}")
    print(f"Output: {output_base}")
    print(f"Qtc targets: {qtc_targets}")

    # Generate cases
    summary_data = generate_qtc_alignments(driver, driver_name, output_base, qtc_targets)

    # Generate summary table
    if summary_data:
        generate_summary_table(summary_data, output_base, driver_name)

    print("\n" + "="*60)
    print(f"✓ Generated {len(summary_data)} validation cases")
    print("="*60)
    print(f"\nOutput directory: {output_base / driver_name}")
    print(f"\nNext steps:")
    print(f"  1. Navigate to each case directory")
    print(f"  2. Follow README.md instructions for Hornresp simulation")
    print(f"  3. Export _sim.txt results")


if __name__ == "__main__":
    main()
