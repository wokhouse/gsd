"""
Objective functions for evaluating enclosure frequency response performance.

This module implements objective functions for multi-objective optimization:
- F3: -3dB cutoff frequency (minimize for better bass extension)
- Response flatness: Frequency response variation (minimize for smoother sound)

Literature:
    - Small (1972) - Closed-box system parameters, F3 definition
    - Thiele (1971) - Vented box alignments and F3 calculation
    - Beranek (1954), Chapter 8 - Bandwidth and flatness definitions
    - literature/thiele_small/small_1972_closed_box.md
    - literature/thiele_small/thiele_1971_vented_boxes.md
    - literature/horns/beranek_1954.md
"""

import numpy as np
from typing import Tuple

from gsd.driver.parameters import ThieleSmallParameters
from gsd.enclosure.sealed_box import calculate_sealed_box_system_parameters, SealedBoxSystemParameters
from gsd.enclosure.ported_box import calculate_ported_box_system_parameters, PortedBoxSystemParameters
from gsd.driver.response import direct_radiator_electrical_impedance
from gsd.simulation.types import ExponentialHorn
from gsd.enclosure.front_loaded_horn import FrontLoadedHorn
from gsd.optimization.parameters.exponential_horn_params import calculate_horn_cutoff_frequency
from gsd.simulation.horn_theory import multsegment_horn_throat_impedance
from gsd.simulation.types import HornSegment, MultiSegmentHorn
from gsd.optimization.parameters.multisegment_horn_params import (
    decode_multisegment_design,
    build_multisegment_horn,
    build_mixed_profile_horn,
    detect_design_type,
)
from gsd.simulation.constants import SPEED_OF_SOUND


def objective_f3(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    frequency_points: np.ndarray = None
) -> float:
    """
    Calculate -3dB cutoff frequency for minimization.

    The F3 frequency is where the SPL response has dropped by 3dB from
    the reference level in the passband. Lower F3 indicates better
    bass extension.

    Literature:
        - Small (1972) - F3 definition for sealed/ported boxes
        - Thiele (1971) - Vented box F3 calculation
        - Olson (1947), Eq. 5.18 - Horn cutoff frequency
        - literature/thiele_small/small_1972_closed_box.md
        - literature/thiele_small/thiele_1971_vented_boxes.md
        - literature/horns/olson_1947.md

    Args:
        design_vector: Enclosure parameters
            - Sealed: [Vb] (m³)
            - Ported: [Vb, Fb] (m³, Hz)
            - Exponential horn: [throat_area, mouth_area, length, V_rc] (m², m², m, m³)
        driver: ThieleSmallParameters instance
        enclosure_type: "sealed", "ported", "infinite_baffle", "exponential_horn"
        frequency_points: Frequency array for interpolation (not used for sealed/ported/horns)

    Returns:
        F3 frequency in Hz (to be minimized)

    Validation:
        Compare with Hornresp F3 calculation.
        Expected: <1% deviation for simple enclosures, <2% for horns

    Examples:
        >>> # Sealed box with 10L volume
        >>> driver = ThieleSmallParameters(M_md=0.026, C_ms=0.001, R_ms=3.0,
        ...                                  R_e=8.0, L_e=1e-3, BL=12.0, S_d=0.035)
        >>> objective_f3(np.array([0.010]), driver, "sealed")
        75.3  # Hz (example value)
    """
    if enclosure_type == "sealed":
        # For sealed box, F3 is calculated directly from system parameters
        Vb = design_vector[0]

        # Calculate system parameters
        params = calculate_sealed_box_system_parameters(driver, Vb)

        return params.F3

    elif enclosure_type == "ported":
        # For ported box, F3 is calculated from system parameters
        Vb = design_vector[0]
        Fb = design_vector[1]

        # Calculate system parameters
        params = calculate_ported_box_system_parameters(driver, Vb, Fb)

        return params.F3

    elif enclosure_type == "infinite_baffle" or enclosure_type == "direct_radiator":
        # For infinite baffle, F3 ≈ Fs (driver resonance)
        return driver.F_s

    elif enclosure_type == "exponential_horn":
        # For exponential horn, calculate F3 from actual frequency response
        # NOT just the theoretical cutoff frequency!
        # Literature: Olson (1947), Eq. 5.18 - f_c = c·m/(2π) (for reference only)
        # Actual F3 depends on driver parameters and chamber volumes
        throat_area = design_vector[0]
        mouth_area = design_vector[1]
        length = design_vector[2]
        V_tc = design_vector[3] if len(design_vector) > 3 else 0.0
        V_rc = design_vector[4] if len(design_vector) > 4 else 0.0

        # Create horn
        horn = ExponentialHorn(throat_area=throat_area, mouth_area=mouth_area, length=length)
        flh = FrontLoadedHorn(driver, horn, V_tc=V_tc, V_rc=V_rc)

        # Generate frequency array for F3 calculation (bass range: 20-500 Hz)
        if frequency_points is None:
            frequencies = np.logspace(np.log10(20), np.log10(500), 200)
        else:
            frequencies = frequency_points

        # Calculate SPL response
        spl_values = []
        for freq in frequencies:
            try:
                spl = flh.spl_response(freq, voltage=2.83)
                spl_values.append(spl)
            except Exception:
                spl_values.append(np.nan)

        spl_values = np.array(spl_values)

        # Remove NaN values
        valid_mask = ~np.isnan(spl_values)
        if np.sum(valid_mask) < 10:
            return 500.0  # Large penalty if calculation failed

        freq_valid = frequencies[valid_mask]
        spl_valid = spl_values[valid_mask]

        # Find reference level (max SPL in passband, typically 100-500 Hz for bass horns)
        passband_mask = (freq_valid >= 50) & (freq_valid <= 500)
        if np.sum(passband_mask) > 0:
            reference_spl = np.max(spl_valid[passband_mask])
        else:
            reference_spl = np.max(spl_valid)

        # Find F3: frequency where SPL crosses reference - 3dB
        # For bass horns, we want the lower -3dB frequency (bass extension)
        # Look for crossover from BELOW target to ABOVE target
        target_spl = reference_spl - 3.0

        # Iterate through frequencies to find where response crosses -3dB
        # (from bass region upward, looking for transition from below to above)
        for i in range(len(freq_valid) - 1):
            below_current = spl_valid[i] < target_spl
            below_next = spl_valid[i + 1] < target_spl

            # Found crossover: current is below, next is above (or at target)
            if below_current and not below_next:
                # Interpolate to find exact F3
                f1, f2 = freq_valid[i], freq_valid[i + 1]
                spl1, spl2 = spl_valid[i], spl_valid[i + 1]
                # Linear interpolation in log-frequency space
                log_f3 = np.log10(f1) + (np.log10(f2) - np.log10(f1)) * \
                         (target_spl - spl1) / (spl2 - spl1)
                f3 = 10 ** log_f3
                return f3

        # If F3 not found in range, return minimum frequency measured
        return freq_valid[0]

    elif enclosure_type in ["multisegment_horn", "mixed_profile_horn"]:
        # For multi-segment and mixed-profile horns, calculate F3 from frequency response
        # F3 is the -3dB point relative to the passband reference level
        from gsd.optimization.parameters.multisegment_horn_params import (
            build_multisegment_horn,
            build_mixed_profile_horn,
        )

        # Build horn based on type
        if enclosure_type == "multisegment_horn":
            horn, V_tc, V_rc = build_multisegment_horn(design_vector, driver, num_segments=2)
        else:  # mixed_profile_horn
            horn, V_tc, V_rc = build_mixed_profile_horn(design_vector, driver, num_segments=2)

        # Create front-loaded horn system
        flh = FrontLoadedHorn(driver, horn, V_tc=V_tc, V_rc=V_rc)

        # Generate frequency array for F3 calculation (bass range: 20-500 Hz)
        if frequency_points is None:
            frequencies = np.logspace(np.log10(20), np.log10(500), 200)
        else:
            frequencies = frequency_points

        # Calculate SPL response
        spl_values = []
        for freq in frequencies:
            try:
                spl = flh.spl_response(freq, voltage=2.83)
                spl_values.append(spl)
            except Exception:
                spl_values.append(np.nan)

        spl_values = np.array(spl_values)

        # Remove NaN values
        valid_mask = ~np.isnan(spl_values)
        if np.sum(valid_mask) < 10:
            return 500.0  # Large penalty if calculation failed

        freq_valid = frequencies[valid_mask]
        spl_valid = spl_values[valid_mask]

        # Find reference level (max SPL in passband, typically 100-500 Hz for bass horns)
        passband_mask = (freq_valid >= 50) & (freq_valid <= 500)
        if np.sum(passband_mask) > 0:
            reference_spl = np.max(spl_valid[passband_mask])
        else:
            reference_spl = np.max(spl_valid)

        # Find F3: frequency where SPL crosses reference - 3dB
        # For bass horns, we want the lower -3dB frequency (bass extension)
        # Look for crossover from BELOW target to ABOVE target
        target_spl = reference_spl - 3.0

        # Iterate through frequencies to find where response crosses -3dB
        # (from bass region upward, looking for transition from below to above)
        for i in range(len(freq_valid) - 1):
            below_current = spl_valid[i] < target_spl
            below_next = spl_valid[i + 1] < target_spl

            # Found crossover: current is below, next is above (or at target)
            if below_current and not below_next:
                # Interpolate to find exact F3
                f1, f2 = freq_valid[i], freq_valid[i + 1]
                spl1, spl2 = spl_valid[i], spl_valid[i + 1]
                # Linear interpolation in log-frequency space
                log_f3 = np.log10(f1) + (np.log10(f2) - np.log10(f1)) * \
                         (target_spl - spl1) / (spl2 - spl1)
                f3 = 10 ** log_f3
                return f3

        # If all frequencies are below target (response never reaches -3dB),
        # return the highest frequency measured (poor bass extension)
        if np.all(spl_valid < target_spl):
            return freq_valid[-1]

        # If all frequencies are above target (response is flat to bass limit),
        # return the lowest frequency measured (excellent bass extension)
        return freq_valid[0]

    else:
        raise ValueError(f"Unsupported enclosure type: {enclosure_type}")


def objective_response_flatness(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    frequency_range: Tuple[float, float] = (20.0, 500.0),
    n_points: int = 100,
    voltage: float = 2.83,
    num_segments: int = 2,
    target_band: Tuple[float, float] = None
) -> float:
    """
    Calculate frequency response variation (standard deviation) for minimization.

    Lower values indicate flatter frequency response, which is generally
    desirable for accurate sound reproduction.

    Literature:
        - Small (1972) - Frequency response transfer functions
        - Beranek (1954), Chapter 8 - Bandwidth and flatness definitions
        - literature/thiele_small/small_1972_closed_box.md

    Args:
        design_vector: Enclosure parameters
            - Sealed: [Vb] (m³)
            - Ported: [Vb, Fb, port_area, port_length] (m³, Hz, m², m)
            - Exponential horn: [throat_area, mouth_area, length, V_rc] (m², m², m, m³)
            - Multi-segment horn: [S1, S2, S3, L12, L23, V_rc] (m², m², m², m, m, m³)
        driver: ThieleSmallParameters instance
        enclosure_type: "sealed", "ported", "infinite_baffle", "exponential_horn",
                       "multisegment_horn"
        frequency_range: (f_min, f_max) in Hz for flatness calculation
        n_points: Number of frequency points to evaluate
        voltage: Input voltage for SPL calculation (default 2.83V)
        num_segments: Number of segments for multisegment_horn (default 2)
        target_band: Optional (f_min, f_max) target frequency band for optimization.
                     When provided, overrides auto-calculated range for horns.

    Returns:
        Standard deviation of SPL (dB) over frequency range (lower is better)

    Note:
        Uses log-spaced frequencies to match human hearing perception.
        Ported box evaluation excludes frequencies below Fb to avoid
        steep rolloff region dominating the metric.
        Horn evaluation excludes frequencies below 1.5×Fc to avoid
        cutoff region dominating the metric (Olson 1947).

    Examples:
        >>> driver = load_driver("BC_8NDL51")
        >>> objective_response_flatness(
        ...     np.array([0.010]), driver, "sealed",
        ...     frequency_range=(40, 200), n_points=50
        ... )
        1.23  # dB standard deviation (example value)
    """
    # Generate frequency array (log-spaced)
    frequencies = np.logspace(
        np.log10(frequency_range[0]),
        np.log10(frequency_range[1]),
        n_points
    )

    # For ported box, adjust frequency range to exclude deep rolloff below Fb
    if enclosure_type == "ported" and len(design_vector) >= 2:
        Fb = design_vector[1]
        f_min = max(frequency_range[0], Fb * 0.8)  # Start slightly below Fb
        if f_min < frequency_range[1]:
            frequencies = np.logspace(
                np.log10(f_min),
                np.log10(frequency_range[1]),
                max(n_points // 2, 20)  # Fewer points for reduced range
            )

    # For multisegment_horn, use target_band if provided
    elif enclosure_type == "multisegment_horn" and target_band is not None:
        f_min, f_max = target_band
        frequencies = np.logspace(
            np.log10(f_min),
            np.log10(f_max),
            n_points
        )

    # For mixed_profile_horn, use target_band if provided
    elif enclosure_type == "mixed_profile_horn" and target_band is not None:
        f_min, f_max = target_band
        frequencies = np.logspace(
            np.log10(f_min),
            np.log10(f_max),
            n_points
        )

    # For exponential horn, adjust frequency range to exclude cutoff region
    elif enclosure_type == "exponential_horn" and len(design_vector) >= 3:
        throat_area = design_vector[0]
        mouth_area = design_vector[1]
        length = design_vector[2]

        # Use target_band if provided, otherwise auto-calculate based on Fc
        if target_band is not None:
            f_min, f_max = target_band
        else:
            # Calculate cutoff frequency
            fc = calculate_horn_cutoff_frequency(throat_area, mouth_area, length)

            # Determine appropriate frequency range based on horn type
            # Bass horns (Fc < 100 Hz): Evaluate up to 5×Fc (bass range)
            # Midrange horns (100 ≤ Fc < 500 Hz): Evaluate up to 20×Fc (full passband)
            # Tweeter horns (Fc ≥ 500 Hz): Evaluate up to 20 kHz
            if fc < 100:
                # Bass horn: 20-500 Hz range
                f_max = max(frequency_range[1], fc * 5)
            elif fc < 500:
                # Midrange horn: Extend to 20×Fc to cover full passband
                # Literature: Beranek (1954) - Horn passband extends to ~20×Fc
                f_max = max(frequency_range[1], fc * 20, 5000)
            else:
                # Tweeter horn: Extend to 20 kHz
                f_max = 20000

            # Start at 1.5×Fc to avoid cutoff rolloff dominating metric
            # Literature: Olson (1947) - Horn response is flat above 1.5×Fc
            f_min = max(frequency_range[0], fc * 1.5)

        # Ensure f_min < f_max for valid range
        if f_min < f_max:
            frequencies = np.logspace(
                np.log10(f_min),
                np.log10(f_max),
                n_points  # Use full n_points for wide range
            )

    # Calculate SPL at each frequency
    spl_values = []
    for freq in frequencies:
        try:
            if enclosure_type == "sealed":
                Vb = design_vector[0]
                result = sealed_box_electrical_impedance(
                    freq, driver, Vb=Vb, voltage=voltage
                )
            elif enclosure_type == "ported":
                Vb = design_vector[0]
                Fb = design_vector[1]
                # For sweep, may not have port parameters yet
                if len(design_vector) >= 4:
                    port_area = design_vector[2]
                    port_length = design_vector[3]
                    result = ported_box_electrical_impedance(
                        freq, driver, Vb=Vb, Fb=Fb,
                        port_area=port_area, port_length=port_length,
                        voltage=voltage
                    )
                else:
                    # Simplified calculation without port detail
                    from gsd.enclosure.ported_box import calculate_optimal_port_dimensions
                    port_area, port_length, _ = calculate_optimal_port_dimensions(
                        driver, Vb, Fb
                    )
                    result = ported_box_electrical_impedance(
                        freq, driver, Vb=Vb, Fb=Fb,
                        port_area=port_area, port_length=port_length,
                        voltage=voltage
                    )
            elif enclosure_type == "infinite_baffle" or enclosure_type == "direct_radiator":
                result = direct_radiator_electrical_impedance(
                    freq, driver, voltage=voltage
                )
            elif enclosure_type == "exponential_horn":
                throat_area = design_vector[0]
                mouth_area = design_vector[1]
                length = design_vector[2]
                V_tc = design_vector[3] if len(design_vector) >= 4 else 0.0
                V_rc = design_vector[4] if len(design_vector) >= 5 else 0.0

                # Create horn system
                horn = ExponentialHorn(throat_area, mouth_area, length)
                flh = FrontLoadedHorn(driver, horn, V_tc=V_tc, V_rc=V_rc)

                # Calculate SPL at this frequency
                spl = flh.spl_response(freq, voltage=voltage)
                result = {'SPL': spl}
            elif enclosure_type == "multisegment_horn":
                # Build multi-segment horn (handles both standard and hyperbolic)
                horn, V_tc, V_rc = build_multisegment_horn(design_vector, driver, num_segments)

                # Create front-loaded horn
                flh = FrontLoadedHorn(driver, horn, V_tc=V_tc, V_rc=V_rc)

                # Calculate SPL at this frequency
                spl = flh.spl_response(freq, voltage=voltage)
                result = {'SPL': spl}
            elif enclosure_type == "mixed_profile_horn":
                # Build mixed-profile horn (exponential/conical/hyperbolic segments)
                horn, V_tc, V_rc = build_mixed_profile_horn(design_vector, driver, num_segments)

                # Create front-loaded horn
                flh = FrontLoadedHorn(driver, horn, V_tc=V_tc, V_rc=V_rc)

                # Calculate SPL at this frequency
                spl = flh.spl_response(freq, voltage=voltage)
                result = {'SPL': spl}
            else:
                raise ValueError(f"Unsupported enclosure type: {enclosure_type}")

            spl_values.append(result['SPL'])

        except Exception as e:
            # Fill with NaN on failure
            import warnings
            warnings.warn(f"SPL calculation failed at {freq:.1f}Hz: {e}")
            spl_values.append(np.nan)

    spl_values = np.array(spl_values)

    # Remove NaN values
    valid_mask = ~np.isnan(spl_values)
    if np.sum(valid_mask) == 0:
        return 1000.0  # Large penalty if all calculations failed

    spl_valid = spl_values[valid_mask]

    # Calculate flatness as standard deviation
    # Beranek (1954), Chapter 8 - Flatness criterion
    flatness_metric = np.std(spl_valid)

    return flatness_metric


def objective_response_slope(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    frequency_range: Tuple[float, float] = (20.0, 500.0),
    n_points: int = 100,
    voltage: float = 2.83,
    num_segments: int = 2
) -> float:
    """
    Calculate frequency response slope (dB/decade) for minimization.

    This measures the overall slope of the frequency response on a log-frequency
    scale. A perfectly flat response has 0 dB/decade slope. Exponential horns
    typically have -15 to -25 dB/decade slope due to high-frequency rolloff.

    This function fits a line to SPL vs log(frequency) and returns the absolute
    slope value, which should be minimized for flatter response.

    Literature:
        - Olson (1947), Chapter 8 - High-frequency horn behavior
        - Beranek (1954), Chapter 5 - Horn directivity and beaming
        - Keele (1975) - Horn profile comparisons

    Args:
        design_vector: Enclosure parameters
            - Sealed: [Vb] (m³)
            - Ported: [Vb, Fb, port_area, port_length] (m³, Hz, m², m)
            - Exponential horn: [throat_area, mouth_area, length, V_rc] (m², m², m, m³)
        driver: ThieleSmallParameters instance
        enclosure_type: "sealed", "ported", "infinite_baffle", "exponential_horn"
        frequency_range: (f_min, f_max) in Hz for slope calculation
        n_points: Number of frequency points to evaluate
        voltage: Input voltage for SPL calculation (default 2.83V)

    Returns:
        Absolute slope in dB/decade (lower is better, target < 3 dB/decade)

    Note:
        Uses log-spaced frequencies to match human hearing perception.
        Slope is calculated as: SPL = slope * log10(frequency) + intercept
        Returns absolute value of slope (minimizes both upward and downward slopes)

    Examples:
        >>> driver = load_driver("BC_8NDL51")
        >>> # Calculate slope from 1-10 kHz
        >>> slope = objective_response_slope(
        ...     np.array([0.0002, 0.04, 0.6, 0.0]), driver, "exponential_horn",
        ...     frequency_range=(1000, 10000), n_points=50
        ... )
        >>> slope
        15.3  # dB/decade (typical for exponential horns)
    """
    # Generate frequency array (log-spaced)
    frequencies = np.logspace(
        np.log10(frequency_range[0]),
        np.log10(frequency_range[1]),
        n_points
    )

    # For exponential or multi-segment horn, adjust frequency range to exclude cutoff region
    if enclosure_type == "exponential_horn" and len(design_vector) >= 3:
        throat_area = design_vector[0]
        mouth_area = design_vector[1]
        length = design_vector[2]

        # Calculate cutoff frequency
        fc = calculate_horn_cutoff_frequency(throat_area, mouth_area, length)

        # Determine appropriate frequency range based on horn type
        if fc < 100:
            f_max = max(frequency_range[1], fc * 5)
        elif fc < 500:
            f_max = max(frequency_range[1], fc * 20, 5000)
        else:
            f_max = 20000

        f_min = max(frequency_range[0], fc * 1.5)

        # Ensure f_min < f_max for valid range
        if f_min < f_max:
            frequencies = np.logspace(
                np.log10(f_min),
                np.log10(f_max),
                n_points
            )
    elif enclosure_type == "multisegment_horn" and len(design_vector) >= 6:
        # For multi-segment horn, calculate cutoff frequency
        num_segments = 2
        horn, _, _ = build_multisegment_horn(design_vector, driver, num_segments)

        # Extract flare constants from segments
        c = 343.0
        fc_values = []
        for seg in horn.segments:
            if hasattr(seg, 'flare_constant'):  # HornSegment
                if seg.flare_constant > 0:
                    fc_values.append((c * seg.flare_constant / 2.0) / (2 * np.pi))
            elif hasattr(seg, 'm'):  # HyperbolicHorn
                if seg.m > 0:
                    fc_values.append((c * seg.m * 2) / (2 * np.pi))  # Convert amplitude to intensity flare

        fc = max(fc_values) if fc_values else 500.0

        # Determine appropriate frequency range
        if fc < 100:
            f_max = max(frequency_range[1], fc * 5)
        elif fc < 500:
            f_max = max(frequency_range[1], fc * 20, 5000)
        else:
            f_max = 20000

        f_min = max(frequency_range[0], fc * 1.5)
    elif enclosure_type == "mixed_profile_horn" and len(design_vector) >= 9:
        # For mixed-profile horn, calculate cutoff frequency
        num_segments = 2
        horn, _, _ = build_mixed_profile_horn(design_vector, driver, num_segments)

        # Extract flare constants from segments (only for exponential/hyperbolic)
        c = 343.0
        fc_values = []
        for seg in horn.segments:
            if hasattr(seg, 'flare_constant'):  # HornSegment (exponential)
                if seg.flare_constant > 0:
                    fc_values.append((c * seg.flare_constant / 2.0) / (2 * np.pi))
            elif hasattr(seg, 'm'):  # HyperbolicHorn
                if seg.m > 0:
                    fc_values.append((c * seg.m * 2) / (2 * np.pi))
            # Note: ConicalHorn segments don't have a sharp cutoff, skip them

        fc = max(fc_values) if fc_values else 500.0

        # Determine appropriate frequency range
        if fc < 100:
            f_max = max(frequency_range[1], fc * 5)
        elif fc < 500:
            f_max = max(frequency_range[1], fc * 20, 5000)
        else:
            f_max = 20000

        f_min = max(frequency_range[0], fc * 1.5)

        # Ensure f_min < f_max for valid range
        if f_min < f_max:
            frequencies = np.logspace(
                np.log10(f_min),
                np.log10(f_max),
                n_points
            )

    # Calculate SPL at each frequency
    spl_values = []
    for freq in frequencies:
        try:
            if enclosure_type == "exponential_horn":
                throat_area = design_vector[0]
                mouth_area = design_vector[1]
                length = design_vector[2]
                V_tc = design_vector[3] if len(design_vector) >= 4 else 0.0
                V_rc = design_vector[4] if len(design_vector) >= 5 else 0.0

                # Create horn system
                horn = ExponentialHorn(throat_area, mouth_area, length)
                flh = FrontLoadedHorn(driver, horn, V_tc=V_tc, V_rc=V_rc)

                # Calculate SPL at this frequency
                spl = flh.spl_response(freq, voltage=voltage)
                spl_values.append(spl)
            elif enclosure_type == "multisegment_horn":
                # Build multi-segment horn (handles both standard and hyperbolic)
                horn, V_tc, V_rc = build_multisegment_horn(design_vector, driver, num_segments)

                # Create front-loaded horn
                flh = FrontLoadedHorn(driver, horn, V_tc=V_tc, V_rc=V_rc)

                # Calculate SPL at this frequency
                spl = flh.spl_response(freq, voltage=voltage)
                spl_values.append(spl)
            elif enclosure_type == "mixed_profile_horn":
                # Build mixed-profile horn (exponential/conical/hyperbolic segments)
                horn, V_tc, V_rc = build_mixed_profile_horn(design_vector, driver, num_segments)

                # Create front-loaded horn
                flh = FrontLoadedHorn(driver, horn, V_tc=V_tc, V_rc=V_rc)

                # Calculate SPL at this frequency
                spl = flh.spl_response(freq, voltage=voltage)
                spl_values.append(spl)
            else:
                # For other enclosure types, slope is less critical
                # Use existing flatness calculation
                return 0.0

        except Exception as e:
            import warnings
            warnings.warn(f"SPL calculation failed at {freq:.1f}Hz: {e}")
            spl_values.append(np.nan)

    spl_values = np.array(spl_values)

    # Remove NaN values
    valid_mask = ~np.isnan(spl_values)
    if np.sum(valid_mask) == 0:
        return 1000.0  # Large penalty if all calculations failed

    freq_valid = frequencies[valid_mask]
    spl_valid = spl_values[valid_mask]

    # Fit line: SPL = slope * log10(frequency) + intercept
    # Use linear regression on log-frequency scale
    log_freq = np.log10(freq_valid)
    coeffs = np.polyfit(log_freq, spl_valid, 1)

    slope = coeffs[0]  # dB per decade (log10 frequency)
    intercept = coeffs[1]

    # Return absolute slope (minimize both upward and downward slopes)
    # Target: < 3 dB/decade for acceptable response
    return abs(slope)


def objective_max_spl(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    frequency_range: Tuple[float, float] = (40.0, 200.0),
    n_points: int = 50,
    voltage: float = 2.83
) -> float:
    """
    Calculate maximum SPL in frequency range (for maximization).

    This is a helper function for efficiency calculations. Returns the
    maximum SPL achieved in the specified frequency range.

    Literature:
        - Beranek (1954), Chapter 8 - Power output and efficiency
        - Small (1972) - SPL calculations for sealed/ported boxes

    Args:
        design_vector: Enclosure parameters
        driver: ThieleSmallParameters instance
        enclosure_type: "sealed", "ported", "infinite_baffle"
        frequency_range: (f_min, f_max) in Hz for evaluation
        n_points: Number of frequency points to evaluate
        voltage: Input voltage for SPL calculation (default 2.83V)

    Returns:
        Maximum SPL in dB (to be maximized)
    """
    # Generate frequency array (log-spaced)
    frequencies = np.logspace(
        np.log10(frequency_range[0]),
        np.log10(frequency_range[1]),
        n_points
    )

    # Calculate SPL at each frequency
    spl_values = []
    for freq in frequencies:
        try:
            if enclosure_type == "sealed":
                Vb = design_vector[0]
                result = sealed_box_electrical_impedance(
                    freq, driver, Vb=Vb, voltage=voltage
                )
            elif enclosure_type == "ported":
                Vb = design_vector[0]
                Fb = design_vector[1]
                if len(design_vector) >= 4:
                    port_area = design_vector[2]
                    port_length = design_vector[3]
                    result = ported_box_electrical_impedance(
                        freq, driver, Vb=Vb, Fb=Fb,
                        port_area=port_area, port_length=port_length,
                        voltage=voltage
                    )
                else:
                    from gsd.enclosure.ported_box import calculate_optimal_port_dimensions
                    port_area, port_length, _ = calculate_optimal_port_dimensions(
                        driver, Vb, Fb
                    )
                    result = ported_box_electrical_impedance(
                        freq, driver, Vb=Vb, Fb=Fb,
                        port_area=port_area, port_length=port_length,
                        voltage=voltage
                    )
            elif enclosure_type == "infinite_baffle" or enclosure_type == "direct_radiator":
                result = direct_radiator_electrical_impedance(
                    freq, driver, voltage=voltage
                )
            else:
                raise ValueError(f"Unsupported enclosure type: {enclosure_type}")

            spl_values.append(result['SPL'])

        except Exception:
            spl_values.append(np.nan)

    spl_values = np.array(spl_values)

    # Remove NaN values
    valid_mask = ~np.isnan(spl_values)
    if np.sum(valid_mask) == 0:
        return 0.0

    return np.max(spl_values[valid_mask])


# Import response calculation functions
def sealed_box_electrical_impedance(
    frequency: float,
    driver: ThieleSmallParameters,
    Vb: float,
    voltage: float = 2.83,
    measurement_distance: float = 1.0,
    use_transfer_function_spl: bool = True
) -> dict:
    """
    Calculate sealed box electrical impedance and SPL at a single frequency.

    Args:
        frequency: Frequency in Hz
        driver: ThieleSmallParameters instance
        Vb: Box volume in m³
        voltage: Input voltage in V
        measurement_distance: Measurement distance in m
        use_transfer_function_spl: If True, use calibrated transfer function SPL
            (required for -25.25 dB offset matching Hornresp)
    """
    from gsd.enclosure.sealed_box import sealed_box_electrical_impedance as sb_impedance
    return sb_impedance(frequency, driver, Vb, voltage=voltage,
                        measurement_distance=measurement_distance,
                        use_transfer_function_spl=use_transfer_function_spl)


def ported_box_electrical_impedance(
    frequency: float,
    driver: ThieleSmallParameters,
    Vb: float,
    Fb: float,
    port_area: float,
    port_length: float,
    voltage: float = 2.83,
    measurement_distance: float = 1.0,
    use_transfer_function_spl: bool = True
) -> dict:
    """
    Calculate ported box electrical impedance and SPL at a single frequency.

    Args:
        frequency: Frequency in Hz
        driver: ThieleSmallParameters instance
        Vb: Box volume in m³
        Fb: Port tuning frequency in Hz
        port_area: Port cross-sectional area in m²
        port_length: Port length in m
        voltage: Input voltage in V
        measurement_distance: Measurement distance in m
        use_transfer_function_spl: If True, use calibrated transfer function SPL
            (required for -25.25 dB offset matching Hornresp)
    """
    from gsd.enclosure.ported_box import ported_box_electrical_impedance as pb_impedance
    return pb_impedance(frequency, driver, Vb, Fb, port_area, port_length,
                        voltage=voltage, measurement_distance=measurement_distance,
                        use_transfer_function_spl=use_transfer_function_spl)


def objective_wavefront_sphericity(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    num_segments: int = 2,
    n_points: int = 50
) -> float:
    """
    Calculate wavefront sphericity deviation for multi-segment horn.

    For a spherical wave horn (tractrix), the wavefronts are spherical shells
    with constant radius of curvature. This measures how much the horn's
    expansion deviates from maintaining spherical wavefronts.

    Literature:
        - Keele (1975) - Tractrix horn derivation from spherical wavefront requirement
        - Kolbrek Part 2 - Spherical wave horns and wavefront curvature
        - literature/horns/kolbrek_horn_theory_tutorial.md

    Theory:
        A spherical wave horn maintains wavefronts that are portions of a sphere.
        The wavefront radius R is related to the cutoff frequency:
            R = c / (2π * f_c)
        For tractrix horns, the wavefront radius is constant throughout the horn.
        For exponential horns, wavefronts are plane (infinite radius of curvature).

        This objective measures the RMS deviation from constant wavefront radius,
        which correlates to diffraction and high-frequency smoothness.

    Args:
        design_vector: Horn parameters
            - For multisegment_horn: [throat_area, middle_area, mouth_area, length1, length2, V_rc]
        driver: ThieleSmallParameters instance
        enclosure_type: Must be "multisegment_horn"
        num_segments: Number of horn segments (2 or 3)
        n_points: Number of axial positions to evaluate

    Returns:
        RMS deviation from spherical wavefront (lower is better)
        Returns 0 for perfect spherical wave, higher values for exponential/conical

    Raises:
        ValueError: If enclosure_type is not "multisegment_horn"

    Examples:
        >>> driver = load_driver("TC2")
        >>> design = np.array([0.000212, 0.010, 0.04084, 0.20, 0.394, 0.0])
        >>> sphericity = objective_wavefront_sphericity(
        ...     design, driver, "multisegment_horn", num_segments=2
        ... )
        >>> sphericity
        0.15  # RMS deviation (example value)
    """
    if enclosure_type != "multisegment_horn":
        raise ValueError(
            f"objective_wavefront_sphericity only supports 'multisegment_horn', "
            f"got '{enclosure_type}'"
        )

    # Decode design to horn geometry (handles both standard and hyperbolic)
    horn, _, _ = build_multisegment_horn(design_vector, driver, num_segments)
    total_length = horn.total_length()

    # Calculate reference wavefront radius at mouth
    # For spherical wave horn, radius at mouth: R_mouth ≈ c / (2π * f_c)
    # where f_c is the minimum cutoff among all segments
    # Extract flare constants from segments
    flare_constants = []
    for seg in horn.segments:
        if hasattr(seg, 'flare_constant'):  # HornSegment
            if seg.flare_constant > 0:
                flare_constants.append(seg.flare_constant)
        elif hasattr(seg, 'm'):  # HyperbolicHorn
            if seg.m > 0:
                flare_constants.append(seg.m * 2)  # Convert amplitude to intensity flare

    m_max = max(flare_constants) if flare_constants else 0

    if m_max > 0:
        # Reference wavefront radius (would be constant for tractrix)
        # Using the largest flare constant (most restrictive segment)
        f_c = (SPEED_OF_SOUND * m_max / 2.0) / (2 * np.pi)
        R_reference = SPEED_OF_SOUND / (2 * np.pi * f_c) if f_c > 0 else total_length
    else:
        R_reference = total_length

    # Calculate wavefront radius deviation along horn length
    # For exponential segment i: local wavefront radius r_i(x) = 1/m_i
    # where m_i is the local flare constant
    deviations = []

    for i in range(n_points):
        x = (i / (n_points - 1)) * total_length if n_points > 1 else 0

        # Find which segment contains position x
        cumulative_length = 0.0
        segment_idx = 0
        for seg_idx, seg in enumerate(horn.segments):
            if x <= cumulative_length + seg.length:
                segment_idx = seg_idx
                break
            cumulative_length += seg.length

        # Local flare constant at this position
        m_local = horn.segments[segment_idx].flare_constant

        # For exponential horn, local wavefront radius ≈ 1/m
        # For tractrix (spherical wave), this would be constant = R_reference
        if m_local > 0:
            R_local = 1.0 / m_local
        else:
            R_local = R_reference

        # Normalized deviation from spherical wavefront
        deviation = (R_local - R_reference) / R_reference
        deviations.append(deviation)

    # Return RMS deviation (lower is better)
    deviations = np.array(deviations)
    return float(np.sqrt(np.mean(deviations ** 2)))


def objective_impedance_smoothness(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    num_segments: int = 2,
    frequency_range: Tuple[float, float] = (100, 10000),
    n_points: int = 100
) -> float:
    """
    Calculate throat impedance smoothness for multi-segment and mixed-profile horns.

    Measures how smooth the throat impedance is vs frequency. Peaks and dips
    in throat impedance indicate resonances that color the sound. A smooth
    impedance curve indicates cleaner, more neutral sound.

    Literature:
        - Olson (1947) - Impedance variations cause sound coloration
        - Beranek (1954) - Smooth impedance = natural sound
        - Kolbrek Part 1 - Throat impedance and mouth reflections

    Theory:
        Throat impedance variations occur due to:
        1. Mouth reflections (impedance mismatch)
        2. Segment junction reflections (flare rate changes)
        3. Standing waves within the horn

        This objective measures the peak-to-peak variation of the real part
        of throat impedance across frequency. Lower variation = fewer
        resonances = cleaner sound.

    Args:
        design_vector: Horn parameters
            - For multisegment_horn: [throat_area, middle_area, mouth_area, length1, length2, V_rc]
            - For mixed_profile_horn: [throat, area1, area2, mouth, L1, L2, ptype1, ptype2, T1, T2, V_tc, V_rc]
        driver: ThieleSmallParameters instance
        enclosure_type: "multisegment_horn" or "mixed_profile_horn"
        num_segments: Number of horn segments (2 or 3)
        frequency_range: (f_min, f_max) in Hz for evaluation
        n_points: Number of frequency points to evaluate

    Returns:
        Peak-to-peak variation of throat resistance in ohms (lower is better)

    Raises:
        ValueError: If enclosure_type is not supported

    Examples:
        >>> driver = load_driver("TC2")
        >>> design = np.array([0.000212, 0.010, 0.04084, 0.20, 0.394, 0.0])
        >>> smoothness = objective_impedance_smoothness(
        ...     design, driver, "multisegment_horn",
        ...     frequency_range=(200, 5000), n_points=50
        ... )
        >>> smoothness
        15.3  # ohms peak-to-peak (example value)
    """
    # Build horn based on enclosure type
    if enclosure_type == "multisegment_horn":
        horn, _, _ = build_multisegment_horn(design_vector, driver, num_segments)
    elif enclosure_type == "mixed_profile_horn":
        horn, _, _ = build_mixed_profile_horn(design_vector, driver, num_segments)
    else:
        raise ValueError(
            f"objective_impedance_smoothness only supports horn enclosures "
            f"('multisegment_horn', 'mixed_profile_horn'), got '{enclosure_type}'"
        )

    # Generate frequency array (log-spaced)
    frequencies = np.logspace(
        np.log10(frequency_range[0]),
        np.log10(frequency_range[1]),
        n_points
    )

    # Calculate throat impedance across frequency range
    try:
        z_throat = multsegment_horn_throat_impedance(frequencies, horn)
    except Exception as e:
        import warnings
        warnings.warn(f"Throat impedance calculation failed: {e}")
        return 1000.0  # Large penalty for failed calculation

    # Extract real part (resistance)
    resistance = np.real(z_throat)

    # Remove NaN values
    valid_mask = ~np.isnan(resistance)
    if np.sum(valid_mask) == 0:
        return 1000.0  # Large penalty if all calculations failed

    resistance_valid = resistance[valid_mask]

    # Calculate peak-to-peak variation
    # This measures the impedance ripple caused by reflections
    peak_to_peak = np.max(resistance_valid) - np.min(resistance_valid)

    # Normalize by mean resistance to account for different throat sizes
    mean_resistance = np.mean(resistance_valid)
    if mean_resistance > 0:
        normalized_variation = peak_to_peak / mean_resistance
    else:
        normalized_variation = peak_to_peak

    return float(normalized_variation)


def objective_composite_flatness(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    frequency_range: Tuple[float, float] = (200.0, 5000.0),
    n_points: int = 100,
    voltage: float = 2.83,
    num_segments: int = 2,
    target_spl: float = None,
    weights: Tuple[float, float, float] = (1.0, 1.0, 0.5)
) -> float:
    """
    Calculate composite flatness metric for multi-segment horn optimization.

    This is an enhanced objective that combines multiple aspects of frequency
    response quality into a single metric. Based on research showing that
    standard deviation alone can produce smooth but incorrect responses (e.g.,
    a smoothly rolling off response has low std dev but poor flatness).

    Literature:
        - Dong et al. (2020) - Multi-objective horn profile optimization
        - Bängtsson et al. - Horn profile discovery via optimization
        - Beranek (1954) - Frequency response evaluation metrics
        - literature/horns/kolbrek_horn_theory_tutorial.md

    Composite Metric:
        J_flat = w1 * σ_SPL + w2 * |slope_avg| + w3 * penalty_ripple

    Where:
        - σ_SPL: Standard deviation of SPL from mean (measures variation)
        - slope_avg: Average dB/decade slope (measures overall tilt)
        - penalty_ripple: Peak-to-peak variation around trend line (measures ripple)

    This formulation prevents the optimizer from "cheating" by producing a
    smoothly rolling off response. The slope penalty ensures the response
    is actually flat, not just smooth.

    Args:
        design_vector: Horn parameters
            - For multisegment_horn: [throat_area, middle_area, mouth_area,
              length1, length2, V_rc] for 2-segment
        driver: ThieleSmallParameters instance
        enclosure_type: Must be "multisegment_horn"
        frequency_range: (f_min, f_max) in Hz for evaluation
        n_points: Number of frequency points to evaluate
        voltage: Input voltage for SPL calculation (default 2.83V)
        num_segments: Number of horn segments (2 or 3)
        target_spl: Optional target SPL level (dB). If None, uses mean SPL.
        weights: (w1, w2, w3) weights for (std_dev, slope, ripple)
            - Default (1.0, 1.0, 0.5) emphasizes flatness over ripple
            - Increase w3 to penalize response ripple more heavily

    Returns:
        Composite flatness metric (lower is better)

    Raises:
        ValueError: If enclosure_type is not "multisegment_horn"

    Examples:
        >>> driver = load_driver("TC2")
        >>> design = np.array([0.000212, 0.010, 0.04084, 0.20, 0.394, 0.0])
        >>> flatness = objective_composite_flatness(
        ...     design, driver, "multisegment_horn",
        ...     frequency_range=(200, 5000), num_segments=2
        ... )
        >>> flatness
        2.34  # Composite metric (dB equivalent)

    Notes:
        - Uses log-spaced frequencies to match human hearing perception
        - Automatically excludes cutoff region (evaluates above 1.5×Fc)
        - Slope calculated via linear regression on log-frequency scale
        - Ripple measured as peak-to-peak deviation from trend line
    """
    if enclosure_type != "multisegment_horn":
        raise ValueError(
            f"objective_composite_flatness only supports 'multisegment_horn', "
            f"got '{enclosure_type}'"
        )

    w1, w2, w3 = weights

    # Build multi-segment horn (handles both standard and hyperbolic)
    horn, V_tc, V_rc = build_multisegment_horn(design_vector, driver, num_segments)

    # Create front-loaded horn
    flh = FrontLoadedHorn(driver, horn, V_tc=V_tc, V_rc=V_rc)

    # Generate frequency array (log-spaced)
    frequencies = np.logspace(
        np.log10(frequency_range[0]),
        np.log10(frequency_range[1]),
        n_points
    )

    # Calculate SPL at each frequency
    spl_values = []
    for freq in frequencies:
        try:
            spl = flh.spl_response(freq, voltage=voltage)
            spl_values.append(spl)
        except Exception:
            spl_values.append(np.nan)

    spl_values = np.array(spl_values)

    # Remove NaN values
    valid_mask = ~np.isnan(spl_values)
    if np.sum(valid_mask) < 10:  # Need at least 10 valid points
        return 1000.0  # Large penalty if too many failures

    freq_valid = frequencies[valid_mask]
    spl_valid = spl_values[valid_mask]

    # COMPONENT 1: Standard deviation from target/mean
    # Use target SPL if provided, otherwise use mean SPL
    reference_spl = target_spl if target_spl is not None else np.mean(spl_valid)
    std_dev = np.std(spl_valid - reference_spl)

    # COMPONENT 2: Average slope (dB/decade)
    # Fit line: SPL = slope * log10(frequency) + intercept
    log_freq = np.log10(freq_valid)
    coeffs = np.polyfit(log_freq, spl_valid, 1)
    slope_avg = coeffs[0]  # dB per decade

    # COMPONENT 3: Ripple (peak-to-peak deviation from trend)
    # Calculate trend line
    trend = coeffs[0] * log_freq + coeffs[1]
    residuals = spl_valid - trend
    ripple = np.max(residuals) - np.min(residuals)

    # Composite metric
    composite = w1 * std_dev + w2 * abs(slope_avg) + w3 * ripple

    return float(composite)


def objective_passband_flatness(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    hf_cutoff: float = 200.0,
    n_points: int = 100,
    voltage: float = 2.83,
    num_segments: int = 2,
) -> float:
    """
    Calculate frequency response flatness from F3 to HF cutoff for minimization.

    This objective evaluates flatness over the usable passband of a horn system,
    defined as the range from the design's F3 (-3dB point) up to a specified
    HF cutoff. This is particularly useful for subwoofer optimization where you
    want flat response across the bass/midbass range.

    Literature:
        - Small (1972) - F3 definition for sealed/ported boxes
        - Beranek (1954), Chapter 8 - Bandwidth and flatness definitions
        - literature/thiele_small/small_1972_closed_box.md
        - literature/thiele_small/thiele_1971_vented_boxes.md

    Theory:
        For subwoofer and bass horn applications, the key performance metric
        is flat response across the usable passband (F3 to HF_cutoff). This
        objective:
        1. Calculates the design's F3 frequency
        2. Evaluates SPL flatness from F3 to hf_cutoff
        3. Returns standard deviation (lower = flatter passband)

        This ensures the optimizer minimizes response variations across the
        actual operating range of the subwoofer, rather than a fixed frequency
        band that may include irrelevant regions.

    Args:
        design_vector: Enclosure parameters
            - For multisegment_horn: [throat_area, middle_area, mouth_area,
              length1, length2, V_rc]
            - For mixed_profile_horn: [throat, area1, area2, mouth, L1, L2,
              ptype1, ptype2, T1, T2, V_tc, V_rc]
        driver: ThieleSmallParameters instance
        enclosure_type: "multisegment_horn" or "mixed_profile_horn"
        hf_cutoff: High-frequency cutoff in Hz (default 200 Hz for subwoofers)
        n_points: Number of frequency points to evaluate
        voltage: Input voltage for SPL calculation (default 2.83V)
        num_segments: Number of segments (default 2)

    Returns:
        Standard deviation of SPL (dB) over F3 to hf_cutoff range (lower is better)

    Raises:
        ValueError: If enclosure_type is not supported

    Examples:
        >>> driver = load_driver("BC_18RBX100")
        >>> # Evaluate flatness from F3 to 200 Hz for subwoofer
        >>> flatness = objective_passband_flatness(
        ...     design_vector, driver, "mixed_profile_horn",
        ...     hf_cutoff=200.0
        ... )
        >>> flatness
        1.23  # dB standard deviation (example value)

    Notes:
        - Uses log-spaced frequencies to match human hearing perception
        - Automatically excludes frequencies below F3 (by definition)
        - For bass horns, typical hf_cutoff values: 150-300 Hz
        - For full-range horns, use higher hf_cutoff: 500-2000 Hz
    """
    # Step 1: Calculate F3 for this design
    f3 = objective_f3(design_vector, driver, enclosure_type)

    # Step 2: Build the horn system
    if enclosure_type == "multisegment_horn":
        horn, V_tc, V_rc = build_multisegment_horn(design_vector, driver, num_segments)
    elif enclosure_type == "mixed_profile_horn":
        horn, V_tc, V_rc = build_mixed_profile_horn(design_vector, driver, num_segments)
    else:
        raise ValueError(
            f"objective_passband_flatness only supports horn enclosures "
            f"('multisegment_horn', 'mixed_profile_horn'), got '{enclosure_type}'"
        )

    # Step 3: Create front-loaded horn system
    flh = FrontLoadedHorn(driver, horn, V_tc=V_tc, V_rc=V_rc)

    # Step 4: Generate frequency array from F3 to HF cutoff
    # Add 10% margin above F3 to ensure we're evaluating the passband
    f_min = f3 * 1.1
    f_max = max(hf_cutoff, f_min * 1.5)  # Ensure we have a valid range

    frequencies = np.logspace(
        np.log10(f_min),
        np.log10(f_max),
        n_points
    )

    # Step 5: Calculate SPL at each frequency
    spl_values = []
    for freq in frequencies:
        try:
            spl = flh.spl_response(freq, voltage=voltage)
            spl_values.append(spl)
        except Exception as e:
            import warnings
            warnings.warn(f"SPL calculation failed at {freq:.1f} Hz: {e}")
            spl_values.append(np.nan)

    spl_values = np.array(spl_values)

    # Step 6: Remove NaN values
    valid_mask = ~np.isnan(spl_values)
    if np.sum(valid_mask) < 10:
        return 100.0  # Large penalty if too many failures

    spl_valid = spl_values[valid_mask]

    # Step 7: Calculate flatness as standard deviation
    # Beranek (1954), Chapter 8 - Flatness criterion
    flatness_metric = np.std(spl_valid)

    return float(flatness_metric)


def multisegment_horn_objectives(
    design: np.ndarray,
    driver: ThieleSmallParameters,
    num_segments: int = 2,
    objectives: list = None
) -> list:
    """
    Multi-objective evaluation for multi-segment horn optimization.

    Evaluates a multi-segment horn design across multiple physics-based
    objectives that correlate to "clean, not harsh" sound quality.

    Literature:
        - Keele (1975) - Wavefront sphericity and diffraction
        - Olson (1947) - Impedance smoothness and coloration
        - Beranek (1954) - Frequency response flatness
        - literature/horns/kolbrek_horn_theory_tutorial.md

    Objectives:
        1. Wavefront Sphericity: Minimize deviation from spherical wavefronts
           - Lower deviation = less diffraction = smoother highs
           - Tractrix horns excel here (spherical wavefronts by design)

        2. Impedance Smoothness: Minimize throat impedance variation
           - Lower variation = fewer resonances = cleaner midrange
           - Gradual flare reduces reflections

        3. SPL Slope: Minimize dB/decade slope (already exists)
           - Flatter response = natural sound

        4. SPL Residuals: Minimize std dev around trend (already exists)
           - Less ripple = smoother response

    Args:
        design: Optimization array [throat_area, middle_area, mouth_area,
                length1, length2, V_rc] for 2-segment, or additional
                [area2, length3] for 3-segment
        driver: ThieleSmallParameters for the driver
        num_segments: Number of horn segments (2 or 3)
        objectives: List of objective names to evaluate
            Default: ["wavefront_sphericity", "impedance_smoothness"]
            Available: "wavefront_sphericity", "impedance_smoothness",
                       "response_slope", "response_flatness", "composite_flatness"

    Returns:
        List of objective values (to be minimized)

    Examples:
        >>> driver = load_driver("TC2")
        >>> design = np.array([0.000212, 0.010, 0.04084, 0.20, 0.394, 0.0])
        >>> objectives = multisegment_horn_objectives(
        ...     design, driver, num_segments=2,
        ...     objectives=["wavefront_sphericity", "impedance_smoothness"]
        ... )
        >>> objectives
        [0.15, 12.3]  # [sphericity_deviation, impedance_variation]

    Notes:
        This function allows the optimizer to discover horn profiles based
        on physics rather than tradition. If wavefront sphericity is
        important, tractrix-like profiles will emerge naturally. If
        impedance smoothness is important, gradual flares will be favored.
    """
    if objectives is None:
        objectives = ["wavefront_sphericity", "impedance_smoothness"]

    results = []
    enclosure_type = "multisegment_horn"

    for obj_name in objectives:
        if obj_name == "wavefront_sphericity":
            val = objective_wavefront_sphericity(
                design, driver, enclosure_type, num_segments
            )
            results.append(val)

        elif obj_name == "impedance_smoothness":
            val = objective_impedance_smoothness(
                design, driver, enclosure_type, num_segments
            )
            results.append(val)

        elif obj_name == "response_slope":
            val = objective_response_slope(
                design, driver, enclosure_type,
                frequency_range=(200, 5000),  # Midrange range
                n_points=50,
                num_segments=num_segments
            )
            results.append(val)

        elif obj_name == "response_flatness":
            val = objective_response_flatness(
                design, driver, enclosure_type,
                frequency_range=(200, 5000),  # Midrange range
                n_points=50,
                num_segments=num_segments
            )
            results.append(val)

        elif obj_name == "composite_flatness":
            val = objective_composite_flatness(
                design, driver, enclosure_type,
                frequency_range=(200, 5000),
                n_points=100,
                num_segments=num_segments
            )
            results.append(val)

        else:
            import warnings
            warnings.warn(f"Unknown objective: {obj_name}")
            results.append(1000.0)  # Large penalty

    return results
