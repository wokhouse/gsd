#!/usr/bin/env python3
"""
Custom horn optimization with crossover-aware constraints.

Targets:
- Horn cutoff: ≤400 Hz (for 800 Hz XO, 2×Fc rule)
- Max length: 250mm per segment
- Max mouth: 625 cm² (250mm × 250mm)
- Optimize for flatness in crossover region
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
import json
from pathlib import Path

from gsd.driver import load_driver
from gsd.optimization.parameters.multisegment_horn_params import (
    get_multisegment_horn_parameter_space,
    decode_multisegment_design,
)
from gsd.optimization.optimizers.pymoo_interface import run_nsga2
from gsd.optimization.objectives.composite import EnclosureOptimizationProblem


def custom_horn_objective(design_array, driver, num_segments=2):
    """
    Custom objective function for horn optimization.

    Optimizes for:
    1. Low cutoff frequency (target: ≤400 Hz)
    2. Flatness in 800 Hz crossover region
    3. Reasonable sensitivity

    Returns:
        objectives: [cutoff_error, flatness_error, sensitivity_penalty]
    """
    # Decode design
    params = decode_multisegment_design(design_array, driver, num_segments=num_segments)

    # Calculate parameters
    throat = params['throat_area']
    segments = params['segments']
    mouth = params['mouth_area']
    length1 = segments[0][2]  # First segment length
    length2 = segments[1][2] if num_segments == 2 else segments[1][2]
    total_length = params['total_length']

    # First segment determines overall cutoff (most rapid expansion)
    throat1 = segments[0][0]
    mouth1 = segments[0][1]

    # Calculate cutoff frequency
    c = 343  # m/s

    # First segment flare constant (determines overall cutoff)
    m1 = np.log(mouth1 / throat1) / length1
    fc1 = (c * m1 / 2) / (2 * np.pi)

    # Overall cutoff (max of segment cutoffs)
    fc = fc1  # For 2-segment, first segment dominates

    # Objective 1: Cutoff frequency (target ≤400 Hz)
    target_fc = 400  # Hz
    cutoff_error = max(0, fc - target_fc) / 1000  # Normalize (kHz)

    # Objective 2: Flatness estimate (based on flare profile)
    # Gradual expansion = better flatness
    # Calculate expansion ratios
    exp1 = mouth1 / throat1

    # Ideal: gradual expansion (not too rapid in first segment)
    # Penalty if first segment expands too fast
    flatness_error = max(0, exp1 - 30) / 100  # Penalty if >30:1 expansion in seg1

    # Objective 3: Sensitivity estimate
    # Larger mouth = higher sensitivity, but must fit constraints
    sensitivity_penalty = (0.05 - mouth) / 0.05 if mouth < 0.05 else 0  # Penalty if <500 cm²

    return [cutoff_error, flatness_error, sensitivity_penalty]


def check_horn_constraints(design_array, driver, num_segments=2):
    """
    Check horn constraints.

    Returns:
        violations: List of constraint violations (positive = violation)
    """
    violations = []

    params = decode_multisegment_design(design_array, driver, num_segments=num_segments)

    # Constraint 1: Total length ≤ 250mm
    total_length = params['total_length']
    length_violation = max(0, total_length - 0.25)
    violations.append(length_violation)

    # Constraint 2: Mouth area ≤ 625 cm² (250mm × 250mm)
    mouth_area = params['mouth_area']
    mouth_violation = max(0, mouth_area - 0.0625)
    violations.append(mouth_violation)

    # Constraint 3: Cutoff frequency ≤400 Hz (soft constraint)
    c = 343
    segments = params['segments']
    throat1 = segments[0][0]
    mouth1 = segments[0][1]
    length1 = segments[0][2]

    m1 = np.log(mouth1 / throat1) / length1
    fc = (c * m1 / 2) / (2 * np.pi)

    cutoff_violation = max(0, fc - 400) / 1000  # Normalize
    violations.append(cutoff_violation)

    return np.array(violations)


def optimize_horn_for_crossover(target_fc=400):
    """
    Optimize horn for specific cutoff frequency.

    Args:
        target_fc: Target cutoff frequency (Hz)
    """
    print("\n" + "=" * 80)
    print(f"CUSTOM HORN OPTIMIZATION")
    print(f"Target Fc: ≤{target_fc} Hz (for {target_fc*2:.0f} Hz crossover)")
    print("=" * 80)

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
    print(f"  Middle: {param_space.parameters[1].min_value*1e4:.1f} - {param_space.parameters[1].max_value*1e4:.1f} cm²")
    print(f"  Mouth: {param_space.parameters[2].min_value*1e4:.1f} - {param_space.parameters[2].max_value*1e4:.1f} cm²")
    print(f"  Length1: {param_space.parameters[3].min_value*100:.0f} - {param_space.parameters[3].max_value*100:.0f} mm")
    print(f"  Length2: {param_space.parameters[4].min_value*100:.0f} - {param_space.parameters[4].max_value*100:.0f} mm")

    # Define custom problem
    from pymoo.core.problem import Problem

    class CustomHornProblem(Problem):
        def __init__(self):
            # xl and xu are lower and upper bounds for variables
            # Order: throat, middle, mouth, length1, length2, V_tc, V_rc
            xl = np.array([
                param_space.parameters[0].min_value,
                param_space.parameters[1].min_value,
                param_space.parameters[2].min_value,
                param_space.parameters[3].min_value,
                param_space.parameters[4].min_value,
                param_space.parameters[5].min_value,
                param_space.parameters[6].min_value,
            ])
            xu = np.array([
                param_space.parameters[0].max_value,
                param_space.parameters[1].max_value,
                param_space.parameters[2].max_value,
                param_space.parameters[3].max_value,
                param_space.parameters[4].max_value,
                param_space.parameters[5].max_value,
                param_space.parameters[6].max_value,
            ])

            n_obj = 3
            n_constr = 3

            super().__init__(n_var=7, n_obj=n_obj, n_constr=n_constr, xl=xl, xu=xu)

        def _evaluate(self, X, out, *args, **kwargs):
            n = len(X)
            objectives = np.zeros((n, self.n_obj))
            constraints = np.zeros((n, self.n_constr))

            for i in range(n):
                # Calculate objectives
                obj = custom_horn_objective(X[i], driver, num_segments=2)
                objectives[i] = obj

                # Check constraints
                con = check_horn_constraints(X[i], driver, num_segments=2)
                constraints[i] = con

            out["F"] = objectives
            out["G"] = constraints

    problem = CustomHornProblem()

    # Run optimization
    print(f"\nRunning optimization...")
    print(f"  Objectives: Cutoff error, Flatness error, Sensitivity penalty")
    print(f"  Constraints: Length ≤250mm, Mouth ≤625cm², Fc ≤{target_fc}Hz")

    result, metadata = run_nsga2(
        problem=problem,
        pop_size=100,
        n_generations=100,
        seed=42,
        verbose=True,
    )

    # Analyze results
    print(f"\nOptimization complete!")
    print(f"  Designs found: {len(result.F)}")

    # Find best design (minimize constraint violations, then objectives)
    constraint_violations = np.max(result.G, axis=1)  # Max violation per design
    feasible = constraint_violations <= 0.01  # Allow small tolerance

    if np.any(feasible):
        print(f"  Feasible designs: {np.sum(feasible)}")
        feasible_indices = np.where(feasible)[0]

        # Among feasible, find best (minimize objectives)
        # Weight: cutoff most important, then flatness
        scores = (
            result.F[feasible, 0] * 10 +  # Cutoff error (×10 weight)
            result.F[feasible, 1] * 1 +   # Flatness error
            result.F[feasible, 2] * 1     # Sensitivity
        )

        best_idx = feasible_indices[np.argmin(scores)]
    else:
        print(f"  No fully feasible designs (constraints too tight)")
        print(f"  Finding least infeasible...")
        best_idx = np.argmin(constraint_violations)

    best_design = result.X[best_idx]
    best_objectives = result.F[best_idx]
    best_constraints = result.G[best_idx]

    # Decode and analyze best design
    params = decode_multisegment_design(best_design, driver, num_segments=2)

    print(f"\n{'='*80}")
    print(f"BEST DESIGN FOUND")
    print(f"{'='*80}")

    segments = params['segments']
    throat1 = segments[0][0]
    mouth1 = segments[0][1]
    length1 = segments[0][2]

    print(f"\nDesign Parameters:")
    print(f"  Throat: {params['throat_area']*1e4:.2f} cm²")
    print(f"  Segment 1: {throat1*1e4:.2f} → {mouth1*1e4:.1f} cm² over {length1*100:.1f} mm")
    if num_segments == 2:
        throat2 = segments[1][0]
        mouth2 = segments[1][1]
        length2 = segments[1][2]
        print(f"  Segment 2: {throat2*1e4:.1f} → {mouth2*1e4:.1f} cm² over {length2*100:.1f} mm")
    print(f"  Total: {params['total_length']*100:.1f} mm")

    # Calculate actual cutoff
    c = 343
    m1 = np.log(mouth1 / throat1) / length1
    fc = (c * m1 / 2) / (2 * np.pi)

    print(f"\nPerformance:")
    print(f"  Cutoff: {fc:.0f} Hz")
    print(f"  Target: ≤{target_fc} Hz")
    print(f"  Error: {fc - target_fc:.0f} Hz")

    if fc <= target_fc:
        print(f"  ✓ Meets cutoff target!")
    else:
        print(f"  ⚠ {fc - target_fc:.0f} Hz above target")

    # Check constraints
    print(f"\nConstraints:")
    print(f"  Length: {params['total_length']*100:.1f} mm ≤ 250 mm: {'✓' if params['total_length'] <= 0.25 else '✗'}")
    print(f"  Mouth: {params['mouth_area']*1e4:.1f} cm² ≤ 625 cm²: {'✓' if params['mouth_area'] <= 0.0625 else '✗'}")
    print(f"  Fc: {fc:.0f} Hz ≤ {target_fc} Hz: {'✓' if fc <= target_fc else '✗'}")

    # Save design
    segments = params['segments']
    design = {
        'design_array': best_design.tolist(),
        'parameters': {
            'throat_area_cm2': params['throat_area'] * 10000,
            'mouth_area_cm2': params['mouth_area'] * 10000,
            'segments': [
                {
                    'throat_area_cm2': seg[0] * 10000,
                    'mouth_area_cm2': seg[1] * 10000,
                    'length_cm': seg[2] * 100,
                }
                for seg in segments
            ],
            'total_length_cm': params['total_length'] * 100,
            'cutoff_hz': fc,
        },
        'objectives': best_objectives.tolist(),
        'constraints': best_constraints.tolist(),
        'target_fc_hz': target_fc,
    }

    output_dir = Path(__file__).parent
    design_path = output_dir / f"custom_horn_design_fc{target_fc}.json"

    with open(design_path, 'w') as f:
        json.dump(design, f, indent=2)

    print(f"\n✓ Design saved: {design_path}")

    return design, params


def main():
    """Main workflow."""
    print("\n" + "=" * 80)
    print("CUSTOM HORN OPTIMIZATION WITH CROSSOVER-AWARE CONSTRAINTS")
    print("=" * 80)

    print("\nThis optimization targets:")
    print("  • Horn cutoff: ≤400 Hz (for 800 Hz XO, 2×Fc rule)")
    print("  • Max length: 250mm per segment")
    print("  • Max mouth: 625 cm²")
    print("  • Smooth expansion for flat response")

    # Try optimization with realistic constraints
    try:
        design, params = optimize_horn_for_crossover(target_fc=400)

        print("\n" + "=" * 80)
        print("ASSESSMENT")
        print("=" * 80)

        fc = design['parameters']['cutoff_hz']
        target_fc = design['target_fc_hz']

        if fc <= target_fc * 1.2:  # Within 20%
            print(f"\n✅ SUCCESS!")
            print(f"   Horn Fc = {fc:.0f} Hz is close to target ({target_fc} Hz)")
            print(f"   Can crossover at ~{fc*2:.0f} Hz (2×Fc)")
            print(f"   Recommendation: Proceed with crossover at {fc*2:.0f} Hz")
        else:
            print(f"\n⚠️  PARTIAL SUCCESS")
            print(f"   Horn Fc = {fc:.0f} Hz is {(fc/target_fc - 1)*100:.0f}% above target")
            print(f"   This suggests the 250mm constraint is too tight")
            print(f"   Recommendations:")
            print(f"     1. Use multi-piece horn (2×250mm sections)")
            print(f"     2. Accept higher XO (~{fc*2:.0f} Hz)")
            print(f"     3. Reduce mouth area (will raise Fc slightly)")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
