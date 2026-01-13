#!/usr/bin/env python3
"""
Optimize a ported box design for BC_15DS115 using flatness objective.

This script finds the optimal Vb and Fb that minimize frequency response
variation (standard deviation of SPL) over the target frequency range.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
from scipy.optimize import minimize
from gsd.driver.bc_drivers import get_bc_15ds115
from gsd.optimization.objectives.response_metrics import objective_response_flatness
from gsd.simulation.response_metrics import find_f3_frequency
from gsd.enclosure.ported_box import (
    calculate_optimal_port_dimensions,
    ported_box_electrical_impedance,
    calculate_ported_box_system_parameters
)


def optimize_flatness(driver, freq_range=(20, 200), initial_guess=None):
    """
    Optimize ported box design for flattest frequency response.

    Args:
        driver: ThieleSmallParameters instance
        freq_range: (f_min, f_max) for flatness evaluation
        initial_guess: Initial [Vb, Fb] guess (optional)

    Returns:
        optimization_result with optimal Vb, Fb, and performance metrics
    """
    print("=" * 70)
    print("PORTED BOX FLATNESS OPTIMIZATION")
    print("=" * 70)
    print(f"Driver: {driver.M_md*1000:.1f}g driver, {driver.V_as*1000:.1f}L Vas")
    print(f"Target frequency range: {freq_range[0]}-{freq_range[1]} Hz")
    print()

    # Initial guess: B4 alignment (Vb=Vas, Fb=Fs)
    if initial_guess is None:
        initial_guess = [driver.V_as, driver.F_s]

    # Bounds for optimization
    # Vb: 50L to 300L (practical range for 15" subwoofer)
    # Fb: 20Hz to 40Hz (typical bass range)
    bounds = [(0.050, 0.300), (20.0, 40.0)]

    print("Initial guess:")
    print(f"  Vb = {initial_guess[0]*1000:.1f} L")
    print(f"  Fb = {initial_guess[1]:.1f} Hz")

    # Calculate initial flatness
    from gsd.enclosure.ported_box import calculate_optimal_port_dimensions
    port_area, port_length, _ = calculate_optimal_port_dimensions(driver, initial_guess[0], initial_guess[1])
    initial_vector = np.array([initial_guess[0], initial_guess[1], port_area, port_length])

    initial_flatness = objective_response_flatness(
        initial_vector, driver, "ported",
        frequency_range=freq_range,
        n_points=100,
        voltage=2.83
    )
    print(f"  Initial flatness (σ): {initial_flatness:.2f} dB")
    print()

    # Optimize
    print("Running optimization...")
    print("-" * 70)

    def objective_function(x):
        """Objective function for scipy.optimize."""
        Vb, Fb = x[0], x[1]

        # Auto-calculate port dimensions
        port_area, port_length, _ = calculate_optimal_port_dimensions(driver, Vb, Fb)
        design_vector = np.array([Vb, Fb, port_area, port_length])

        # Calculate flatness
        flatness = objective_response_flatness(
            design_vector, driver, "ported",
            frequency_range=freq_range,
            n_points=100,
            voltage=2.83
        )

        return flatness

    result = minimize(
        objective_function,
        initial_guess,
        method='L-BFGS-B',
        bounds=bounds,
        options={'ftol': 1e-6}
    )

    # Extract optimal parameters
    Vb_opt, Fb_opt = result.x[0], result.x[1]
    port_area_opt, port_length_opt, _ = calculate_optimal_port_dimensions(driver, Vb_opt, Fb_opt)

    print("Optimization complete!")
    print("-" * 70)

    return {
        'Vb': Vb_opt,
        'Fb': Fb_opt,
        'port_area': port_area_opt,
        'port_length': port_length_opt,
        'flatness': result.fun,
        'success': result.success,
        'message': result.message
    }


def evaluate_design(driver, Vb, Fb, port_area, port_length, freq_points=None):
    """
    Evaluate the frequency response of a ported box design.

    Args:
        driver: ThieleSmallParameters instance
        Vb: Box volume (m³)
        Fb: Tuning frequency (Hz)
        port_area: Port area (m²)
        port_length: Port length (m)
        freq_points: Frequency points to evaluate (optional)

    Returns:
        Dictionary with frequency response data and metrics
    """
    if freq_points is None:
        # Generate frequency points from 10 Hz to 500 Hz
        freq_points = np.logspace(np.log10(10), np.log10(500), 100)

    print("=" * 70)
    print("FREQUENCY RESPONSE EVALUATION")
    print("=" * 70)
    print(f"Design: Vb={Vb*1000:.1f}L, Fb={Fb:.1f}Hz")
    print(f"Port: {port_area*10000:.1f} cm², {port_length*100:.1f} cm long")
    print()

    # Calculate system parameters
    system_params = calculate_ported_box_system_parameters(driver, Vb, Fb)
    print(f"System Parameters:")
    print(f"  F3: {system_params.F3:.1f} Hz (-3dB cutoff)")
    print(f"  Fb: {Fb:.1f} Hz (tuning frequency)")
    print(f"  Alpha: {system_params.alpha:.2f} (compliance ratio)")
    print(f"  h: {system_params.h:.2f} (tuning ratio)")
    print()

    # Calculate frequency response
    frequencies = []
    spl_values = []
    impedances = []

    for freq in freq_points:
        result = ported_box_electrical_impedance(
            freq, driver, Vb, Fb, port_area, port_length,
            voltage=2.83, impedance_model="small",
            use_transfer_function_spl=True
        )
        frequencies.append(freq)
        spl_values.append(result['SPL'])
        impedances.append(result['Ze_magnitude'])

    # Calculate metrics
    spl_array = np.array(spl_values)
    freq_array = np.array(frequencies)

    # Find -3dB point
    max_spl = np.max(spl_array)
    f3 = find_f3_frequency(freq_array, spl_array, max_spl,
                           search_range=(10, 150), filter_type="highpass")

    # Find peak
    peak_idx = np.argmax(spl_array)
    peak_freq = freq_array[peak_idx]
    peak_spl = spl_array[peak_idx]

    # Calculate flatness in different ranges
    bass_range = (20, 80)
    midbass_range = (40, 120)
    full_range = (20, 200)

    def calc_flatness(f_min, f_max):
        mask = (freq_array >= f_min) & (freq_array <= f_max)
        return np.std(spl_array[mask])

    flatness_bass = calc_flatness(*bass_range)
    flatness_midbass = calc_flatness(*midbass_range)
    flatness_full = calc_flatness(*full_range)

    print("Frequency Response Metrics:")
    print(f"  Peak SPL: {peak_spl:.1f} dB @ {peak_freq:.1f} Hz")
    print(f"  F3 cutoff: {f3:.1f} Hz" if f3 else "  F3 cutoff: N/A")
    print()
    print("Flatness (standard deviation):")
    print(f"  Bass (20-80 Hz):     σ = {flatness_bass:.2f} dB")
    print(f"  Midbass (40-120 Hz): σ = {flatness_midbass:.2f} dB")
    print(f"  Full range (20-200): σ = {flatness_full:.2f} dB")
    print()

    # Print sample frequencies
    sample_freqs = [20, 30, 40, 50, 60, 80, 100, 150, 200, 300]
    print(f"{'Freq (Hz)':>10} | {'SPL (dB)':>10} | {'Note'}")
    print("-" * 70)

    for freq in sample_freqs:
        result = ported_box_electrical_impedance(
            freq, driver, Vb, Fb, port_area, port_length,
            voltage=2.83, impedance_model="small",
            use_transfer_function_spl=True
        )
        spl = result['SPL']

        if freq < Fb:
            note = "Below tuning"
        elif abs(freq - Fb) < 5:
            note = "Near tuning"
        else:
            note = "Above tuning"

        print(f"{freq:>10.1f} | {spl:>10.1f} | {note}")

    print()

    return {
        'frequencies': np.array(frequencies),
        'spl_values': np.array(spl_values),
        'impedances': np.array(impedances),
        'peak_spl': peak_spl,
        'peak_freq': peak_freq,
        'f3': f3,
        'flatness_bass': flatness_bass,
        'flatness_midbass': flatness_midbass,
        'flatness_full': flatness_full
    }


def main():
    """Main optimization and evaluation workflow."""
    # Get driver
    driver = get_bc_15ds115()

    # Step 1: Optimize for flatness
    print("\n")
    result = optimize_flatness(driver, freq_range=(20, 200))

    if not result['success']:
        print(f"Optimization failed: {result['message']}")
        return

    print("\n")
    print("=" * 70)
    print("OPTIMAL DESIGN")
    print("=" * 70)
    print(f"Box Volume (Vb):     {result['Vb']*1000:.1f} L")
    print(f"Tuning Frequency:    {result['Fb']:.1f} Hz")
    print(f"Port Area:           {result['port_area']*10000:.1f} cm²")
    print(f"Port Length:         {result['port_length']*100:.1f} cm")
    print(f"Flatness (20-200Hz): {result['flatness']:.2f} dB")
    print()

    # Compare with B4 alignment
    print("Comparison with B4 Alignment (Vb=Vas, Fb=Fs):")
    print(f"  B4:  Vb={driver.V_as*1000:.0f}L, Fb={driver.F_s:.1f}Hz")
    print(f"  Opt: Vb={result['Vb']*1000:.0f}L, Fb={result['Fb']:.1f}Hz")
    print(f"  Difference: ΔVb={(result['Vb']-driver.V_as)*1000:+.0f}L, ΔFb={result['Fb']-driver.F_s:+.1f}Hz")
    print()

    # Step 2: Evaluate the optimal design
    evaluation = evaluate_design(
        driver,
        result['Vb'],
        result['Fb'],
        result['port_area'],
        result['port_length']
    )

    # Step 3: Summary
    print("=" * 70)
    print("OPTIMIZATION SUMMARY")
    print("=" * 70)
    print(f"Objective: Minimize frequency response variation (σ)")
    print(f"Optimization range: 20-200 Hz")
    print()
    print(f"Optimal Design:")
    print(f"  Vb = {result['Vb']*1000:.1f} L ({result['Vb']/driver.V_as*100:.1f}% of Vas)")
    print(f"  Fb = {result['Fb']:.1f} Hz ({result['Fb']/driver.F_s*100:.1f}% of Fs)")
    print(f"  Port: {result['port_area']*10000:.1f} cm² × {result['port_length']*100:.1f} cm")
    print()
    print(f"Performance:")
    print(f"  Peak SPL: {evaluation['peak_spl']:.1f} dB @ {evaluation['peak_freq']:.1f} Hz")
    print(f"  F3 cutoff: {evaluation['f3']:.1f} Hz" if evaluation['f3'] else "  F3 cutoff: N/A")
    print(f"  Bass flatness (20-80Hz): σ = {evaluation['flatness_bass']:.2f} dB")
    print(f"  Full range flatness (20-200Hz): σ = {result['flatness']:.2f} dB")
    print()
    print("✅ Optimization complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
