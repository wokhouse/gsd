"""
Subwoofer-specific objective functions for ported box optimization.

This module implements objective functions specifically designed for subwoofer
design, where the priorities are different from full-range speakers:

1. Deep bass extension (F3 minimization)
2. Bass region flatness (20-80 Hz)
3. Crossover region flatness (80-120 Hz) for integration with mains
4. Overall passband smoothness (minimize ripple)

The key insight is that subwoofers operate in specific frequency ranges
and should be optimized for those ranges, not full 20-200 Hz response.

Literature:
    - Thiele (1971) - Vented box alignments (B4, QB3, BB4)
    - Small (1973) - Butterworth maximally flat response
    - Beranek (1954) - Bandwidth and flatness definitions
    - literature/thiele_small/thiele_1971_vented_boxes.md
    - literature/thiele_small/small_1973_vented_box_part1.md
"""

import numpy as np
from typing import Tuple, Dict, List, Optional
from dataclasses import dataclass

from gsd.driver.parameters import ThieleSmallParameters
from gsd.enclosure.ported_box_vector_sum import (
    calculate_spl_ported_vector_sum_array,
)
from gsd.enclosure.ported_box import (
    calculate_optimal_port_dimensions,
    calculate_ported_box_system_parameters,
)


@dataclass
class SubwooferObjectives:
    """
    Subwoofer performance objectives for multi-objective optimization.

    Attributes:
        f3: -3dB cutoff frequency (Hz) - lower is better for bass extension
        bass_flatness: Standard deviation in 20-80 Hz range (dB) - lower is better
        crossover_flatness: Standard deviation in 80-120 Hz range (dB) - lower is better
        passband_ripple: Peak-to-peak variation in 40-100 Hz range (dB) - lower is better
        max_spl_bass: Maximum SPL in 40-80 Hz range (dB) - higher is better
    """
    f3: float
    bass_flatness: float
    crossover_flatness: float
    passband_ripple: float
    max_spl_bass: float

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for analysis."""
        return {
            'f3': self.f3,
            'bass_flatness': self.bass_flatness,
            'crossover_flatness': self.crossover_flatness,
            'passband_ripple': self.passband_ripple,
            'max_spl_bass': self.max_spl_bass,
        }


def calculate_subwoofer_objectives(
    Vb: float,
    Fb: float,
    driver: ThieleSmallParameters,
    voltage: float = 2.83,
    measurement_distance: float = 1.0,
    freq_points: Optional[np.ndarray] = None,
) -> SubwooferObjectives:
    """
    Calculate subwoofer-specific objectives for a ported box design.

    This function evaluates a ported subwoofer design across multiple
    frequency ranges that are relevant for subwoofer applications:
    - Deep bass: 20-40 Hz (extension and impact)
    - Bass region: 20-80 Hz (main subwoofer operating range)
    - Crossover region: 80-120 Hz (integration with main speakers)
    - Passband: 40-100 Hz (critical music range)

    Literature:
        - Thiele (1971) - B4 alignment targets flat passband
        - Small (1973) - Vented-box system Q and response shape
        - literature/thiele_small/thiele_1971_vented_boxes.md

    Validation:
        Verify F3 calculation matches Thiele's alignment tables for B4, QB3, BB4.
        Confirm flatness calculations produce correct rankings when comparing
        known good designs (e.g., B4 should have minimal passband ripple).
        Test case: BC_15DS115 with Vb=Vas, Fb=Fs should produce F3 ≈ 28 Hz
        with bass_flatness < 3.0 dB.

    Args:
        Vb: Box volume (m³)
        Fb: Port tuning frequency (Hz)
        driver: ThieleSmallParameters instance
        voltage: Input voltage (V), default 2.83V (1W into 8Ω)
        measurement_distance: SPL measurement distance (m), default 1m
        freq_points: Optional frequency array for evaluation

    Returns:
        SubwooferObjectives dataclass with all objective values

    Raises:
        ValueError: If Vb <= 0, Fb <= 0, or invalid driver

    Examples:
        >>> from gsd.driver import load_driver
        >>> objectives = calculate_subwoofer_objectives(
        ...     Vb=0.250, Fb=28.0, driver=driver
        ... )
        >>> objectives.f3  # Cutoff frequency
        28.0  # Hz (example)
        >>> objectives.bass_flatness  # Bass region flatness
        2.3  # dB std dev (example)
    """
    # Validate inputs
    if Vb <= 0:
        raise ValueError(f"Box volume Vb must be > 0, got {Vb} m³")
    if Fb <= 0:
        raise ValueError(f"Tuning frequency Fb must be > 0, got {Fb} Hz")
    if not isinstance(driver, ThieleSmallParameters):
        raise TypeError(f"driver must be ThieleSmallParameters, got {type(driver)}")

    # Calculate optimal port dimensions
    try:
        port_area, port_length, _ = calculate_optimal_port_dimensions(driver, Vb, Fb)
    except ValueError as e:
        # Impractical port dimensions - return penalty values
        # This happens when box is too small for the tuning frequency
        import warnings
        warnings.warn(f"Impractical port dimensions for Vb={Vb*1000:.1f}L @ {Fb:.1f}Hz: {e}")
        # Return large penalty values
        return SubwooferObjectives(
            f3=999.0,
            bass_flatness=999.0,
            crossover_flatness=999.0,
            passband_ripple=999.0,
            max_spl_bass=0.0,
        )

    # Calculate system parameters (for F3)
    sys_params = calculate_ported_box_system_parameters(
        driver, Vb, Fb, port_area, port_length
    )

    # Generate frequency points
    if freq_points is None:
        # Log-spaced frequencies from 10 Hz to 200 Hz
        freq_points = np.logspace(np.log10(10), np.log10(200), 200)

    # Calculate SPL response using electro-mechanical coupling model
    # This replaces the legacy transfer_function with the recommended vector_sum_array
    # The new model naturally includes HF rolloff via voice coil inductance (Le)
    # and provides better accuracy through proper electro-mechanical coupling.
    #
    # Performance improvement: Process entire frequency array at once instead of loop.
    frequencies = freq_points
    spl_values = calculate_spl_ported_vector_sum_array(
        frequencies=frequencies,
        driver=driver,
        Vb=Vb,
        Fb=Fb,
        port_area=port_area,
        port_length=port_length,
        voltage=voltage,
        measurement_distance=measurement_distance,
        QL=7.0,  # Box leakage losses (Qp and QA absorbed into QL)
        end_correction_factor=0.732,  # Port end correction (replaces Qp)
    )

    # Helper function to calculate flatness (standard deviation)
    def calc_flatness(f_min: float, f_max: float) -> float:
        """Calculate SPL standard deviation in frequency range."""
        mask = (frequencies >= f_min) & (frequencies <= f_max)
        if np.sum(mask) == 0:
            return 1000.0  # Penalty if no frequencies in range
        return float(np.std(spl_values[mask]))

    # Helper function to calculate peak-to-peak ripple
    def calc_ripple(f_min: float, f_max: float) -> float:
        """Calculate peak-to-peak SPL variation in frequency range."""
        mask = (frequencies >= f_min) & (frequencies <= f_max)
        if np.sum(mask) == 0:
            return 1000.0  # Penalty if no frequencies in range
        spl_in_range = spl_values[mask]
        return float(np.max(spl_in_range) - np.min(spl_in_range))

    # Helper function to calculate max SPL in range
    def calc_max_spl(f_min: float, f_max: float) -> float:
        """Calculate maximum SPL in frequency range."""
        mask = (frequencies >= f_min) & (frequencies <= f_max)
        if np.sum(mask) == 0:
            return 0.0
        return float(np.max(spl_values[mask]))

    # Calculate objectives
    f3 = sys_params.F3
    bass_flatness = calc_flatness(20.0, 80.0)
    crossover_flatness = calc_flatness(80.0, 120.0)
    passband_ripple = calc_ripple(40.0, 100.0)
    max_spl_bass = calc_max_spl(40.0, 80.0)

    return SubwooferObjectives(
        f3=f3,
        bass_flatness=bass_flatness,
        crossover_flatness=crossover_flatness,
        passband_ripple=passband_ripple,
        max_spl_bass=max_spl_bass,
    )


def objective_subwoofer_flatness(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    Single-objective function for subwoofer flatness optimization.

    This function combines multiple subwoofer objectives into a single
    scalar value using weighted sum. This is useful for single-objective
    optimization algorithms (e.g., differential evolution).

    Default weights prioritize:
    - Bass region flatness (20-80 Hz): 40% - Most important for subwoofer
    - Crossover region flatness (80-120 Hz): 20% - Integration with mains
    - Passband ripple (40-100 Hz): 20% - Smoothness in critical range
    - F3 extension: 10% - Lower is better but not critical
    - Max SPL: 10% - Higher is better

    Literature:
        - Multi-objective optimization theory (weighted sum method)
        - Thiele (1971) - Alignment trade-offs

    Validation:
        Verify weighted sum correctly prioritizes bass flatness as the primary
        objective (40% weight). Test that designs with better bass flatness
        score lower even if other objectives are worse. Confirm normalization
        keeps all objectives in similar ranges (0-1) to prevent domination.

    Args:
        design_vector: [Vb, Fb] where Vb in m³, Fb in Hz
        driver: ThieleSmallParameters instance
        weights: Optional dictionary of objective weights
            Default: {'bass_flatness': 0.4, 'crossover_flatness': 0.2,
                      'passband_ripple': 0.2, 'f3': 0.1, 'max_spl': 0.1}

    Returns:
        Single objective value (lower is better)

    Examples:
        >>> driver = load_driver("BC_15DS115")
        >>> objective = objective_subwoofer_flatness(
        ...     np.array([0.250, 28.0]), driver
        ... )
        >>> objective
        3.2  # Weighted sum (example value)
    """
    # Extract design parameters
    Vb = design_vector[0]
    Fb = design_vector[1]

    # Default weights (prioritize bass flatness)
    if weights is None:
        weights = {
            'bass_flatness': 0.4,      # Most important - main operating range
            'crossover_flatness': 0.2,  # Integration with mains
            'passband_ripple': 0.2,     # Smoothness
            'f3': 0.1,                   # Extension (minimize)
            'max_spl': 0.1,              # Output (maximize, so we'll negate)
        }

    # Calculate objectives
    objectives = calculate_subwoofer_objectives(Vb, Fb, driver)

    # Normalize objectives to similar scales
    # F3: typical range 20-50 Hz, normalize to 0-1
    f3_normalized = objectives.f3 / 50.0

    # Bass flatness: typical range 1-6 dB, normalize to 0-1
    bass_flatness_normalized = objectives.bass_flatness / 6.0

    # Crossover flatness: typical range 0.2-2 dB, normalize to 0-1
    crossover_flatness_normalized = objectives.crossover_flatness / 2.0

    # Passband ripple: typical range 2-10 dB, normalize to 0-1
    passband_ripple_normalized = objectives.passband_ripple / 10.0

    # Max SPL: typical range 85-100 dB, negate for minimization
    # Higher SPL is better, so we use (100 - SPL) for minimization
    max_spl_normalized = (100.0 - objectives.max_spl_bass) / 15.0

    # Weighted sum
    weighted_sum = (
        weights['f3'] * f3_normalized +
        weights['bass_flatness'] * bass_flatness_normalized +
        weights['crossover_flatness'] * crossover_flatness_normalized +
        weights['passband_ripple'] * passband_ripple_normalized +
        weights['max_spl'] * max_spl_normalized
    )

    return weighted_sum


def objective_b4_alignment_error(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
) -> float:
    """
    Calculate deviation from Butterworth B4 alignment (maximally flat).

    The B4 (Butterworth 4th-order) alignment is the classic "maximally flat"
    vented box alignment. It occurs when:
    - Vb = Vas (α = 1.0)
    - Fb = Fs (h = 1.0)
    - Qts ≈ 0.38-0.45 (for true Butterworth response)

    This function measures how far a design is from the B4 ideal.

    Literature:
        - Thiele (1971), Table 1 - Alignment constants
        - Small (1973) - Butterworth response conditions
        - literature/thiele_small/thiele_1971_vented_boxes.md

    Validation:
        Perfect B4 alignment (Vb=Vas, Fb=Fs) should return error=0.0.
        Designs far from B4 should return proportionally larger errors.
        Test case: BC_15DS115 with Vb=Vas*1.5, Fb=Fs*1.2 should return
        error > 0.5 (significant deviation from ideal).

    Args:
        design_vector: [Vb, Fb] where Vb in m³, Fb in Hz
        driver: ThieleSmallParameters instance

    Returns:
        Alignment error (lower is better, 0 = perfect B4)

    Examples:
        >>> driver = load_driver("BC_15DS115")
        >>> # Perfect B4 alignment
        >>> error = objective_b4_alignment_error(
        ...     np.array([driver.V_as, driver.F_s]), driver
        ... )
        >>> error
        0.0  # Perfect alignment
    """
    Vb = design_vector[0]
    Fb = design_vector[1]

    # B4 alignment conditions
    alpha_target = 1.0  # Vb = Vas
    h_target = 1.0      # Fb = Fs

    # Calculate actual values
    alpha_actual = driver.V_as / Vb
    h_actual = Fb / driver.F_s

    # Calculate normalized deviations
    alpha_error = abs(alpha_actual - alpha_target) / alpha_target
    h_error = abs(h_actual - h_target) / h_target

    # Combined error (RMS)
    alignment_error = np.sqrt(alpha_error**2 + h_error**2)

    return alignment_error


def evaluate_subwoofer_designs(
    driver: ThieleSmallParameters,
    designs: List[Tuple[str, float, float]],
    voltage: float = 2.83,
) -> Dict[str, SubwooferObjectives]:
    """
    Evaluate multiple subwoofer designs and compare objectives.

    This function is useful for design exploration and comparison.
    It calculates all subwoofer objectives for each design and returns
    a dictionary keyed by design name.

    Args:
        driver: ThieleSmallParameters instance
        designs: List of (name, Vb, Fb) tuples
            - name: Design name (e.g., "B4 Alignment")
            - Vb: Box volume (m³)
            - Fb: Tuning frequency (Hz)
        voltage: Input voltage (V), default 2.83V

    Returns:
        Dictionary mapping design names to SubwooferObjectives

    Examples:
        >>> driver = load_driver("BC_15DS115")
        >>> designs = [
        ...     ("Small", 0.060, 34.0),
        ...     ("B4", driver.V_as, driver.F_s),
        ...     ("Large", 0.300, 27.0),
        ... ]
        >>> results = evaluate_subwoofer_designs(driver, designs)
        >>> for name, obj in results.items():
        ...     print(f"{name}: F3={obj.f3:.1f}Hz, σ_bass={obj.bass_flatness:.2f}dB")
    """
    results = {}

    for name, Vb, Fb in designs:
        try:
            objectives = calculate_subwoofer_objectives(
                Vb, Fb, driver, voltage=voltage
            )
            results[name] = objectives
        except Exception as e:
            import warnings
            warnings.warn(f"Failed to evaluate {name}: {e}")
            # Add placeholder with bad values
            results[name] = SubwooferObjectives(
                f3=999.0,
                bass_flatness=999.0,
                crossover_flatness=999.0,
                passband_ripple=999.0,
                max_spl_bass=0.0,
            )

    return results


def print_subwoofer_comparison(results: Dict[str, SubwooferObjectives]):
    """
    Print formatted comparison table of subwoofer designs.

    Args:
        results: Dictionary from evaluate_subwoofer_designs()
    """
    print("\n" + "=" * 100)
    print("SUBWOOFER DESIGN COMPARISON")
    print("=" * 100)
    print(f"{'Design':<25} | {'F3':>6} | {'σ(20-80)':>9} | {'σ(80-120)':>10} | {'Ripple':>7} | {'Max SPL':>8}")
    print("-" * 100)

    for name, obj in results.items():
        print(f"{name:<25} | {obj.f3:>6.1f} | {obj.bass_flatness:>9.2f} | "
              f"{obj.crossover_flatness:>10.2f} | {obj.passband_ripple:>7.2f} | "
              f"{obj.max_spl_bass:>8.1f}")

    print()

    # Find best designs for each objective
    best_f3 = min(results.items(), key=lambda x: x[1].f3)
    best_bass = min(results.items(), key=lambda x: x[1].bass_flatness)
    best_xover = min(results.items(), key=lambda x: x[1].crossover_flatness)
    best_ripple = min(results.items(), key=lambda x: x[1].passband_ripple)
    best_spl = max(results.items(), key=lambda x: x[1].max_spl_bass)

    print("BEST BY CATEGORY:")
    print(f"  Bass Extension:  {best_f3[0]:<25} (F3 = {best_f3[1].f3:.1f} Hz)")
    print(f"  Bass Flatness:  {best_bass[0]:<25} (σ = {best_bass[1].bass_flatness:.2f} dB)")
    print(f"  Crossover Flat: {best_xover[0]:<25} (σ = {best_xover[1].crossover_flatness:.2f} dB)")
    print(f"  Passband Smooth:{best_ripple[0]:<25} (ripple = {best_ripple[1].passband_ripple:.2f} dB)")
    print(f"  Max Output:     {best_spl[0]:<25} (SPL = {best_spl[1].max_spl_bass:.1f} dB)")
    print()
