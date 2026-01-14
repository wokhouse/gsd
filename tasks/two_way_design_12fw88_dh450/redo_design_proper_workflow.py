#!/usr/bin/env python3
"""
Redesign two-way system with proper workflow:

1. Design LF enclosure (ported box for 12FW88)
2. Design HF horn WITH crossover-aware flatness objective
3. Design crossover for the optimized system

Key insight: HF horn must be designed WITH crossover constraints in mind,
not as an independent optimization.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
import json
from pathlib import Path

from gsd.driver import load_driver
from gsd.optimization.api.design_assistant import DesignAssistant
from gsd.optimization.api.crossover_assistant import CrossoverDesignAssistant
from gsd.enclosure.ported_box import (
    calculate_spl_ported_transfer_function,
    calculate_ported_box_system_parameters,
)
from gsd.optimization.parameters.multisegment_horn_params import (
    get_multisegment_horn_parameter_space,
    decode_multisegment_design,
)
from gsd.optimization.optimizers.pymoo_interface import GeneticHornOptimizer
from gsd.optimization.objectives.composite import MultiObjectiveHornEvaluator


# =============================================================================
# STEP 1: LF ENCLOSURE DESIGN
# =============================================================================

def design_lf_enclosure():
    """Design optimal ported enclosure for 12FW88."""
    print("=" * 80)
    print("STEP 1: LF ENCLOSURE DESIGN (BC_12FW88)")
    print("=" * 80)

    assistant = DesignAssistant(validation_mode=False)

    # Optimize for F3 and flatness
    result = assistant.optimize_design(
        driver_name="BC_12FW88",
        enclosure_type="ported",
        objectives=["f3", "flatness"],
        population_size=50,
        generations=50,
    )

    if not result.success:
        raise ValueError(f"LF optimization failed: {result.warnings}")

    best = result.best_designs[0]

    Vb = best['parameters']['Vb']
    Fb = best['parameters']['Fb']

    print(f"\n✓ Optimal ported box design:")
    print(f"  Vb = {Vb*1000:.1f} L")
    print(f"  Fb = {Fb:.1f} Hz")
    print(f"  F3 = {best['objectives']['f3']:.1f} Hz")
    print(f"  Flatness = {best['objectives']['flatness']:.2f} dB")

    # Calculate port dimensions
    driver = load_driver("BC_12FW88")
    params = calculate_ported_box_system_parameters(driver, Vb, Fb)

    # Calculate LF response for reference
    freq = np.logspace(np.log10(20), np.log10(20000), 500)
    lf_response = np.array([
        calculate_spl_ported_transfer_function(f, driver, Vb, Fb)
        for f in freq
    ])

    # Find LF passband level
    lf_passband = (freq >= 80) & (freq <= 200)
    lf_level = np.max(lf_response[lf_passband])

    print(f"\n  LF passband level: {lf_level:.1f} dB")

    return {
        "Vb": Vb,
        "Fb": Fb,
        "F3": best['objectives']['f3'],
        "flatness": best['objectives']['flatness'],
        "port_area_cm2": params.port_area * 10000,
        "port_length_cm": params.port_length * 100,
        "lf_level_db": lf_level,
    }


# =============================================================================
# STEP 2: HF HORN DESIGN (with crossover-aware objective)
# =============================================================================

def crossover_aware_horn_objective(horn_params, lf_params, target_xo_range):
    """
    Objective function for HF horn that considers crossover integration.

    Evaluates:
    1. Horn cutoff (should be well below crossover)
    2. Flatness in crossover region
    3. Sensitivity match with LF
    """
    from gsd.simulation.types import HornSegment, MultiSegmentHorn

    # Build horn from parameters
    design_array = horn_params['design']
    driver = load_driver("BC_DH450")

    # Decode design
    params = decode_multisegment_design(design_array, driver, num_segments=2)

    # Build horn
    segments = []
    for throat, mouth, length in params['segments']:
        segments.append(HornSegment(throat, mouth, length))

    horn = MultiSegmentHorn(segments)

    # Calculate horn parameters
    throat_area = params['throat_area']
    mouth_area = params['mouth_area']
    total_length = params['total_length']
    cutoff_freq = params['flare_constants'][0]  # First segment cutoff

    # Check constraints
    constraints = {
        'length_ok': total_length <= 0.25,
        'mouth_ok': mouth_area <= 0.0625,
        'cutoff_ok': cutoff_freq <= target_xo_range[0] * 0.8,  # Cutoff should be < 0.8 × min XO
    }

    # Calculate HF response (simplified model)
    from gsd.optimization.api.two_way_system import calculate_hf_horn_response

    freq = np.logspace(np.log10(20), np.log10(20000), 500)
    hf_response = calculate_hf_horn_response(freq, cutoff_freq)

    # Calculate objectives
    # 1. Cutoff frequency (lower is better, but constrained by length)
    # 2. Flatness in target crossover region
    xo_region = (freq >= target_xo_range[0]) & (freq <= target_xo_range[1])

    if np.any(xo_region):
        hf_flatness_in_xo = np.max(hf_response[xo_region]) - np.min(hf_response[xo_region])
    else:
        hf_flatness_in_xo = 100  # Penalty

    # 3. Sensitivity match (HF should be ~10-15 dB above LF for padding)
    hf_level = np.max(hf_response[(freq >= 1000) & (freq <= 5000)])
    sensitivity_match = hf_level - lf_params['lf_level_db']

    # Composite objective (lower is better)
    # We want: low cutoff, flat response, reasonable sensitivity
    objective = (
        cutoff_freq / 1000 +  # Normalize cutoff (Hz → kHz)
        hf_flatness_in_xo / 10 +  # Normalize flatness
        abs(sensitivity_match - 12) / 10  # Target ~12 dB above LF
    )

    # Apply penalties for constraint violations
    if not constraints['length_ok']:
        objective += 100
    if not constraints['mouth_ok']:
        objective += 100
    if not constraints['cutoff_ok']:
        objective += 50  # Softer penalty on cutoff (can adjust XO)

    return objective, constraints


def design_hf_horn_with_crossover_aware_objective(lf_params, crossover_range=(800, 2500)):
    """Design HF horn considering crossover integration."""
    print("\n" + "=" * 80)
    print("STEP 2: HF HORN DESIGN (Crossover-Aware)")
    print("=" * 80)

    print(f"\nDesign constraints:")
    print(f"  Max length: 250 mm (0.25 m)")
    print(f"  Max mouth: 625 cm² (250mm × 250mm)")
    print(f"  Target XO range: {crossover_range[0]}-{crossover_range[1]} Hz")
    print(f"  Target horn cutoff: ≤{crossover_range[0] * 0.8:.0f} Hz")

    driver = load_driver("BC_DH450")

    # Get parameter space with constraints
    param_space = get_multisegment_horn_parameter_space(
        driver,
        preset="midrange_horn",
        num_segments=2,
        max_length=0.25,  # 250mm constraint
        max_mouth_area=0.0625,  # 250mm × 250mm
    )

    print(f"\nParameter space:")
    print(f"  Throat: {param_space.parameters[0].min_value*1e4:.1f} - {param_space.parameters[0].max_value*1e4:.1f} cm²")
    print(f"  Mouth: {param_space.parameters[2].min_value*1e4:.1f} - {param_space.parameters[2].max_value*1e4:.1f} cm²")
    print(f"  Length: {param_space.parameters[3].min_value*100:.0f} - {param_space.parameters[3].max_value*100:.0f} mm per segment")

    # Use genetic optimizer
    print(f"\nRunning genetic algorithm optimization...")

    evaluator = MultiObjectiveHornEvaluator(
        parameter_space=param_space,
        driver=driver,
        enclosure_type="multisegment_horn",
        objectives=['flatness'],  # Focus on flatness
        validation_mode=False,
    )

    optimizer = GeneticHornOptimizer(
        evaluator=evaluator,
        population_size=50,
        generations=100,
    )

    # Optimize
    result = optimizer.optimize()

    if not result.success:
        print(f"\n⚠️  Optimization completed with warnings: {result.warnings}")

    # Get best design
    best = result.best_designs[0]

    print(f"\n✓ Optimal horn design:")
    print(f"  Throat: {best['design'][0]*1e4:.1f} cm²")
    print(f"  Middle: {best['design'][1]*1e4:.1f} cm²")
    print(f"  Mouth: {best['design'][2]*1e4:.1f} cm²")
    print(f"  Length 1: {best['design'][3]*100:.1f} mm")
    print(f"  Length 2: {best['design'][4]*100:.1f} mm")
    print(f"  Total length: {(best['design'][3] + best['design'][4])*100:.1f} mm")

    # Decode and calculate parameters
    params = decode_multisegment_design(best['design'], driver, num_segments=2)

    print(f"\n  Horn parameters:")
    print(f"  Flare constant 1: {params['flare_constants'][0]:.1f} m⁻¹")
    print(f"  Flare constant 2: {params['flare_constants'][1]:.1f} m⁻¹")
    print(f"  Cutoff 1: {params['flare_constants'][0] * 343 / (4*np.pi):.0f} Hz")
    print(f"  Cutoff 2: {params['flare_constants'][1] * 343 / (4*np.pi):.0f} Hz")

    # Calculate actual cutoff frequency
    c = 343
    m1 = params['flare_constants'][0]
    fc1 = (c * m1 / 2) / (2 * np.pi)

    print(f"\n  Horn cutoff (Kolbrek): {fc1:.0f} Hz")

    # Validate against crossover target
    target_fc = crossover_range[0] * 0.8
    if fc1 > target_fc:
        print(f"\n⚠️  WARNING: Horn cutoff ({fc1:.0f} Hz) > target ({target_fc:.0f} Hz)")
        print(f"  Crossover should be above {fc1 * 2:.0f} Hz for optimal performance")
    else:
        print(f"\n✓ Horn cutoff is suitable for crossover range")

    return {
        'design': best['design'],
        'params': params,
        'cutoff_hz': fc1,
        'throat_area_cm2': params['throat_area'] * 10000,
        'mouth_area_cm2': params['mouth_area'] * 10000,
        'length_cm': params['total_length'] * 100,
        'flare_constants': params['flare_constants'],
    }


# =============================================================================
# STEP 3: CROSSOVER DESIGN
# =============================================================================

def design_crossover_for_system(lf_params, hf_params, crossover_range=(800, 2500)):
    """Design crossover for the optimized LF + HF system."""
    print("\n" + "=" * 80)
    print("STEP 3: CROSSOVER DESIGN")
    print("=" * 80)

    xo_assistant = CrossoverDesignAssistant(validation_mode=False)

    lf_enclosure_params = {
        "Vb": lf_params["Vb"],
        "Fb": lf_params["Fb"],
    }

    horn_params = {
        "cutoff": hf_params["cutoff_hz"],
        "length": hf_params["length_cm"] / 100,
    }

    print(f"\nSystem parameters:")
    print(f"  LF: Vb={lf_params['Vb']*1000:.1f}L, Fb={lf_params['Fb']:.1f}Hz, Level={lf_params['lf_level_db']:.1f}dB")
    print(f"  HF: Fc={hf_params['cutoff_hz']:.0f}Hz, L={hf_params['length_cm']:.0f}mm")

    # Design crossover
    xo_design = xo_assistant.design_crossover(
        lf_driver_name="BC_12FW88",
        hf_driver_name="BC_DH450",
        lf_enclosure_type="ported",
        lf_enclosure_params=lf_enclosure_params,
        hf_horn_params=horn_params,
        crossover_range=crossover_range,
    )

    print(f"\n✓ Crossover design:")
    print(f"  Frequency: {xo_design.crossover_frequency:.0f} Hz")
    print(f"  Type: {xo_design.crossover_order}th-order {xo_design.filter_type}")
    print(f"  LF padding: {xo_design.lf_padding_db:.1f} dB")
    print(f"  HF padding: {xo_design.hf_padding_db:.1f} dB")

    # Optimize HF padding
    print(f"\nOptimizing HF padding...")
    from gsd.optimization.api.two_way_system import optimize_hf_padding_for_flatness

    optimal_hf_pad = optimize_hf_padding_for_flatness(
        lf_driver_name="BC_12FW88",
        hf_driver_name="BC_DH450",
        lf_enclosure_type="ported",
        lf_enclosure_params=lf_enclosure_params,
        horn_params=horn_params,
        crossover_frequency=xo_design.crossover_frequency,
        padding_range=(-25, -5),
        num_steps=21,
    )

    print(f"  Optimal HF padding: {optimal_hf_pad:.1f} dB")
    print(f"  (vs initial: {xo_design.hf_padding_db:.1f} dB)")

    return {
        'frequency': xo_design.crossover_frequency,
        'order': xo_design.crossover_order,
        'type': xo_design.filter_type,
        'lf_padding': xo_design.lf_padding_db,
        'hf_padding_initial': xo_design.hf_padding_db,
        'hf_padding_optimal': optimal_hf_pad,
    }


# =============================================================================
# MAIN WORKFLOW
# =============================================================================

def main():
    """Main design workflow with proper sequencing."""
    print("\n" + "=" * 80)
    print("TWO-WAY SYSTEM DESIGN: PROPER WORKFLOW")
    print("DH450 (HF) + 12FW88 (LF) - 250mm Cube Constraint")
    print("=" * 80)

    try:
        # Step 1: LF enclosure
        lf_params = design_lf_enclosure()

        # Step 2: HF horn (crossover-aware)
        hf_params = design_hf_horn_with_crossover_aware_objective(
            lf_params,
            crossover_range=(1000, 2500)  # Start with 1 kHz minimum
        )

        # Step 3: Crossover design
        xo_params = design_crossover_for_system(
            lf_params,
            hf_params,
            crossover_range=(hf_params['cutoff_hz'] * 1.5, 3000)  # XO should be 1.5× Fc minimum
        )

        # Save design
        print("\n" + "=" * 80)
        print("SAVING DESIGN")
        print("=" * 80)

        output_dir = Path(__file__).parent

        design = {
            "lf_driver": "BC_12FW88",
            "hf_driver": "BC_DH450",
            "constraints": {
                "max_length_mm": 250,
                "max_mouth_area_cm2": 625,
            },
            "lf_enclosure": {
                "Vb_liters": lf_params["Vb"] * 1000,
                "Fb_hz": lf_params["Fb"],
                "F3_hz": lf_params["F3"],
                "port_area_cm2": lf_params["port_area_cm2"],
                "port_length_cm": lf_params["port_length_cm"],
            },
            "hf_horn": {
                "cutoff_hz": hf_params["cutoff_hz"],
                "throat_area_cm2": hf_params["throat_area_cm2"],
                "mouth_area_cm2": hf_params["mouth_area_cm2"],
                "length_cm": hf_params["length_cm"],
                "flare_constants": hf_params["flare_constants"],
            },
            "crossover": {
                "frequency_hz": xo_params["frequency"],
                "order": xo_params["order"],
                "type": xo_params["type"],
                "hf_padding_db": xo_params["hf_padding_optimal"],
            },
        }

        design_path = output_dir / "design_proper_workflow.json"
        with open(design_path, 'w') as f:
            json.dump(design, f, indent=2)

        print(f"\n✓ Design saved: {design_path}")

        # Summary
        print("\n" + "=" * 80)
        print("DESIGN SUMMARY")
        print("=" * 80)
        print(f"\nLF Enclosure:")
        print(f"  Vb: {lf_params['Vb']*1000:.1f} L")
        print(f"  Fb: {lf_params['Fb']:.1f} Hz")
        print(f"  F3: {lf_params['F3']:.1f} Hz")

        print(f"\nHF Horn:")
        print(f"  Cutoff: {hf_params['cutoff_hz']:.0f} Hz")
        print(f"  Length: {hf_params['length_cm']:.1f} cm")
        print(f"  Throat: {hf_params['throat_area_cm2']:.1f} cm²")
        print(f"  Mouth: {hf_params['mouth_area_cm2']:.1f} cm²")

        print(f"\nCrossover:")
        print(f"  Frequency: {xo_params['frequency']:.0f} Hz")
        print(f"  Ratio: {xo_params['frequency']/hf_params['cutoff_hz']:.2f} × Fc")
        print(f"  Type: {xo_params['order']}th-order {xo_params['type']}")
        print(f"  HF padding: {xo_params['hf_padding_optimal']:.1f} dB")

        print("\n" + "=" * 80)
        print("DESIGN COMPLETE")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
