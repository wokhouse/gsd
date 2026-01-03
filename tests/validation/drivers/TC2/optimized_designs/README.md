# TC2 Optimized Horn Designs - Validation Data

This directory contains validation outputs from multi-objective optimization of exponential horn designs using the TC2 compression driver.

## Contents

### Optimization Results Plots
- `flatness_optimization_target_band.png` - Single-objective flatness optimization with target band constraint
- `multiobjective_with_target_band.png` - Multi-objective optimization (flatness + size) with target band
- `new_designs_frequency_response.png` - Frequency response comparison of optimized designs
- `optimization_comparison_summary.png` - Comparison of different optimization approaches
- `single_objective_flatness_optimization.png` - Single-objective flatness optimization results

### Parameter Sweep Analysis
- `sweep1_mouth_area.png` - Mouth area parameter sweep
- `sweep2_throat_area.png` - Throat area parameter sweep
- `sweep3_horn_length.png` - Horn length parameter sweep
- `sweep4_parameter_interaction.png` - Multi-parameter interaction analysis

### Hornresp Exports
Optimized designs exported to Hornresp format for validation:
- `tc2_optimized_1.txt` - Optimized design #1
- `tc2_optimized_2.txt` - Optimized design #2
- `tc2_optimized_3.txt` - Optimized design #3
- `tc2_3_opt_sim.txt` - Simulation results for design #3

### Result Summaries
- `flatness_optimization_target_band_results.txt` - Target band optimization results
- `multiobjective_with_target_band_summary.txt` - Multi-objective optimization summary
- `optimization_comparison_summary.txt` - Comparison of optimization methods
- `single_objective_flatness_results.txt` - Single-objective results

## Driver Specifications

**TC2 Compression Driver** (from `src/gsd/driver/test_drivers.py`)
- Sd = 8.0 cm² (diaphragm area)
- Mmd = 8.0 g (driver mass only)
- Cms = 5.00E-05 m/N (compliance)
- Rms = 3.0 N·s/m (mechanical resistance)
- Re = 6.5 Ω (voice coil resistance)
- Le = 0.1 mH (voice coil inductance)
- BL = 12.0 T·m (force factor)
- Fs ≈ 251 Hz (resonance frequency)

## Optimization Details

### Objectives
- **Response Flatness**: Minimize SPL variation in target frequency band
- **Enclosure Size**: Minimize horn volume

### Constraints
- Mouth size limits (for practical construction)
- Flare constant limits (maintain exponential profile)
- Target frequency band (user-specified optimization range)

### Algorithm
- NSGA-II (Non-dominated Sorting Genetic Algorithm II)
- Population: 20 individuals
- Generations: 10

## Validation

All designs were validated against Hornresp to ensure:
1. Accurate frequency response predictions
2. Proper horn impedance calculations
3. Correct cutoff frequency behavior

See `docs/validation/` for detailed validation reports and analysis.

## Related Documentation

- `docs/validation/VALIDATION_REPORT.md` - Overall validation summary
- `docs/validation/SLOPE_ANALYSIS_AND_FIX.md` - Analysis and fixes for response slope issues
- `docs/validation/SWEEP_ANALYSIS_SUMMARY.md` - Parameter sweep findings
- `docs/validation/TARGET_BAND_OPTIMIZATION_SUMMARY.md` - Target band optimization details
