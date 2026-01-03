"""
Efficiency and SPL output objective functions.

This module implements efficiency-related objective functions for
multi-objective optimization:
- Average SPL over bandwidth
- Reference sensitivity (SPL at 1m, 2.83V)
- Bandwidth efficiency

Literature:
    - Beranek (1954), Chapter 8 - Efficiency definitions and power bandwidth
    - Olson (1947), Section 5.11 - Horn efficiency
    - Small (1972) - Direct radiator efficiency
    - literature/horns/beranek_1954.md
    - literature/horns/olson_1947.md
"""

import numpy as np
from typing import Tuple

from gsd.driver.parameters import ThieleSmallParameters
from gsd.simulation.types import ExponentialHorn
from gsd.enclosure.front_loaded_horn import FrontLoadedHorn


def objective_efficiency(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    reference_frequency: float = 100.0,
    bandwidth_octaves: float = 2.0,
    voltage: float = 2.83
) -> float:
    """
    Calculate average efficiency over specified bandwidth (for maximization).

    Higher efficiency means louder output for the same input power, which is
    generally desirable. This function returns the negative of average SPL
    because pymoo minimizes objectives by default.

    Literature:
        - Beranek (1954), Chapter 8 - Efficiency definitions
        - Olson (1947), Section 5.11 - Horn efficiency
        - Small (1972) - Direct radiator efficiency
        - literature/horns/beranek_1954.md
        - literature/horns/olson_1947.md

    Args:
        design_vector: Enclosure parameters
            - Sealed: [Vb] (m³)
            - Ported: [Vb, Fb, port_area, port_length] (m³, Hz, m², m)
        driver: ThieleSmallParameters instance
        enclosure_type: Type of enclosure ("sealed", "ported", "infinite_baffle")
        reference_frequency: Center frequency for efficiency calculation (Hz)
        bandwidth_octaves: Bandwidth in octaves around reference frequency
        voltage: Input voltage for SPL calculation (default 2.83V)

    Returns:
        Negative average SPL over bandwidth (dB at 1m, 2.83V)
        (Return negative because pymoo minimizes by default)

    Note:
        Uses 1/3-octave spacing (standard for efficiency measurements)
        per Kinsler et al. (1982), Chapter 4.

    Examples:
        >>> driver = load_driver("BC_12NDL76")
        >>> # High efficiency design
        >>> eff = objective_efficiency(
        ...     np.array([0.020]), driver, "sealed",
        ...     reference_frequency=100, bandwidth_octaves=2
        ... )
        >>> -eff  # Convert back to positive SPL
        89.5  # dB average SPL (example value)
    """
    # For multi-segment and mixed-profile horns, use true efficiency calculation (percentage)
    # instead of SPL-based approximation
    if enclosure_type in ["multisegment_horn", "mixed_profile_horn"]:
        return objective_efficiency_percent(
            design_vector, driver, enclosure_type, reference_frequency, voltage
        )

    from gsd.optimization.objectives.response_metrics import (
        sealed_box_electrical_impedance,
        ported_box_electrical_impedance
    )
    from gsd.driver.response import direct_radiator_electrical_impedance
    from gsd.enclosure.ported_box import calculate_optimal_port_dimensions

    # Calculate frequency range
    f_min = reference_frequency / (2.0 ** (bandwidth_octaves / 2.0))
    f_max = reference_frequency * (2.0 ** (bandwidth_octaves / 2.0))

    # Use 1/3-octave spacing (standard for efficiency measurements)
    # Kinsler et al. (1982), Chapter 4
    frequencies = 10.0 ** np.arange(
        np.log10(f_min),
        np.log10(f_max),
        np.log10(2) / 3.0  # 1/3 octave steps
    )

    # If no frequencies in range, use simple midpoint
    if len(frequencies) == 0:
        frequencies = np.array([reference_frequency])

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

                # Get port dimensions
                if len(design_vector) >= 4:
                    port_area = design_vector[2]
                    port_length = design_vector[3]
                else:
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
                # Olson (1947), Section 5.11 - Horn efficiency
                horn = ExponentialHorn(throat_area, mouth_area, length)
                flh = FrontLoadedHorn(driver, horn, V_tc=V_tc, V_rc=V_rc)

                # Calculate SPL at this frequency
                spl = flh.spl_response(freq, voltage=voltage)
                result = {'SPL': spl}
            elif enclosure_type == "multisegment_horn":
                from gsd.optimization.parameters.multisegment_horn_params import build_multisegment_horn

                # Build horn (handles both standard and hyperbolic designs)
                horn, V_tc, V_rc = build_multisegment_horn(design_vector, driver, num_segments=2)
                flh = FrontLoadedHorn(driver, horn, V_tc=V_tc, V_rc=V_rc)

                # Calculate SPL at this frequency
                spl = flh.spl_response(freq, voltage=voltage)
                result = {'SPL': spl}
            elif enclosure_type == "mixed_profile_horn":
                from gsd.optimization.parameters.multisegment_horn_params import build_mixed_profile_horn

                # Build mixed-profile horn (exponential/conical/hyperbolic segments)
                horn, V_tc, V_rc = build_mixed_profile_horn(design_vector, driver, num_segments=2)
                flh = FrontLoadedHorn(driver, horn, V_tc=V_tc, V_rc=V_rc)

                # Calculate SPL at this frequency
                spl = flh.spl_response(freq, voltage=voltage)
                result = {'SPL': spl}
            else:
                raise ValueError(f"Unsupported enclosure type: {enclosure_type}")

            spl_values.append(result['SPL'])

        except Exception as e:
            import warnings
            warnings.warn(f"Efficiency calculation failed at {freq:.1f}Hz: {e}")
            spl_values.append(np.nan)

    spl_values = np.array(spl_values)

    # Remove NaN values
    valid_mask = ~np.isnan(spl_values)
    if np.sum(valid_mask) == 0:
        return -1000.0  # Large penalty if all calculations failed

    spl_valid = spl_values[valid_mask]

    # Average SPL over bandwidth (for maximization)
    # Beranek (1954), Chapter 8 - Power bandwidth
    avg_spl = np.mean(spl_valid)

    # Return as negative for minimization (pymoo minimizes by default)
    return -avg_spl


def objective_reference_sensitivity(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    reference_frequency: float = 100.0,
    voltage: float = 2.83
) -> float:
    """
    Calculate SPL at reference frequency (for maximization).

    This is a simpler efficiency metric that just measures SPL at a single
    reference frequency rather than averaging over a bandwidth.

    Literature:
        - Small (1972) - Reference efficiency definition
        - Beranek (1954), Chapter 8 - Sensitivity calculations

    Args:
        design_vector: Enclosure parameters
        driver: ThieleSmallParameters instance
        enclosure_type: Type of enclosure
        reference_frequency: Frequency for sensitivity measurement (Hz)
        voltage: Input voltage (default 2.83V = 1W into 8Ω)

    Returns:
        Negative SPL at reference frequency in dB
        (Return negative because pymoo minimizes by default)

    Examples:
        >>> driver = load_driver("BC_8NDL51")
        >>> sens = objective_reference_sensitivity(
        ...     np.array([0.010]), driver, "sealed", reference_frequency=100
        ... )
        >>> -sens  # Convert back to positive
        87.2  # dB at 1m, 2.83V (example value)
    """
    from gsd.optimization.objectives.response_metrics import (
        sealed_box_electrical_impedance,
        ported_box_electrical_impedance
    )
    from gsd.driver.response import direct_radiator_electrical_impedance
    from gsd.enclosure.ported_box import calculate_optimal_port_dimensions

    try:
        if enclosure_type == "sealed":
            Vb = design_vector[0]
            result = sealed_box_electrical_impedance(
                reference_frequency, driver, Vb=Vb, voltage=voltage
            )
        elif enclosure_type == "ported":
            Vb = design_vector[0]
            Fb = design_vector[1]

            # Get port dimensions
            if len(design_vector) >= 4:
                port_area = design_vector[2]
                port_length = design_vector[3]
            else:
                port_area, port_length = calculate_optimal_port_dimensions(
                    driver, Vb, Fb
                )

            result = ported_box_electrical_impedance(
                reference_frequency, driver, Vb=Vb, Fb=Fb,
                port_area=port_area, port_length=port_length,
                voltage=voltage
            )
        elif enclosure_type == "infinite_baffle":
            result = direct_radiator_electrical_impedance(
                reference_frequency, driver, voltage=voltage
            )
        elif enclosure_type == "exponential_horn":
            throat_area = design_vector[0]
            mouth_area = design_vector[1]
            length = design_vector[2]
            V_tc = design_vector[3] if len(design_vector) >= 4 else 0.0
            V_rc = design_vector[4] if len(design_vector) >= 5 else 0.0

            # Create horn system
            # Olson (1947), Section 5.11 - Horn efficiency
            horn = ExponentialHorn(throat_area, mouth_area, length)
            flh = FrontLoadedHorn(driver, horn, V_tc=V_tc, V_rc=V_rc)

            # Calculate SPL at reference frequency
            spl = flh.spl_response(reference_frequency, voltage=voltage)
            result = {'SPL': spl}
        elif enclosure_type == "multisegment_horn":
            from gsd.optimization.parameters.multisegment_horn_params import build_multisegment_horn

            # Build horn (handles both standard and hyperbolic designs)
            horn, V_tc, V_rc = build_multisegment_horn(design_vector, driver, num_segments=2)
            flh = FrontLoadedHorn(driver, horn, V_tc=V_tc, V_rc=V_rc)

            # Calculate SPL at reference frequency
            spl = flh.spl_response(reference_frequency, voltage=voltage)
            result = {'SPL': spl}
        elif enclosure_type == "mixed_profile_horn":
            from gsd.optimization.parameters.multisegment_horn_params import build_mixed_profile_horn

            # Build mixed-profile horn (exponential/conical/hyperbolic segments)
            horn, V_tc, V_rc = build_mixed_profile_horn(design_vector, driver, num_segments=2)
            flh = FrontLoadedHorn(driver, horn, V_tc=V_tc, V_rc=V_rc)

            # Calculate SPL at reference frequency
            spl = flh.spl_response(reference_frequency, voltage=voltage)
            result = {'SPL': spl}
        else:
            raise ValueError(f"Unsupported enclosure type: {enclosure_type}")

        return -result['SPL']  # Return negative for minimization

    except Exception:
        return -1000.0  # Large penalty on failure


def objective_efficiency_percent(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    reference_frequency: float = 1000.0,
    voltage: float = 2.83
) -> float:
    """
    Calculate actual efficiency as percentage (for maximization).

    This function calculates true efficiency (acoustic power / electrical power)
    rather than SPL. For multi-segment horns, this uses the corrected
    acoustic_power() method.

    Literature:
        - Kolbrek, "Horn Simulation Part 3" - Power calculation
        - Beranek (1954), Chapter 4 - Acoustic power efficiency
        - Olson (1947), Chapter 8 - Horn efficiency

    Args:
        design_vector: Enclosure parameters
        driver: ThieleSmallParameters instance
        enclosure_type: Type of enclosure (must be "multisegment_horn")
        reference_frequency: Frequency for efficiency measurement (Hz), default 1 kHz
        voltage: Input voltage (default 2.83V)

    Returns:
        Negative efficiency percentage (for minimization)
        Multiply by -1 to get positive percentage

    Examples:
        >>> driver = load_driver("TC2")
        >>> eff = objective_efficiency_percent(
        ...     design_vector, driver, "multisegment_horn", reference_frequency=1000
        ... )
        >>> -eff  # Convert back to positive
        0.57  # % efficiency at 1 kHz (example value)
    """
    try:
        if enclosure_type == "multisegment_horn":
            from gsd.optimization.parameters.multisegment_horn_params import build_multisegment_horn

            # Build horn (handles both standard and hyperbolic designs)
            horn, V_tc, V_rc = build_multisegment_horn(design_vector, driver, num_segments=2)
            flh = FrontLoadedHorn(driver, horn, V_tc=V_tc, V_rc=V_rc)

            # Calculate acoustic power at reference frequency
            power_acoustic = flh.acoustic_power(reference_frequency, voltage=voltage)

            # Calculate electrical power
            result = flh.electrical_impedance(reference_frequency, voltage=voltage)
            Ze = result['Ze_real'] + 1j * result['Ze_imag']

            if abs(Ze) > 0:
                power_electrical = (voltage ** 2) * Ze.real / (abs(Ze) ** 2)
            else:
                power_electrical = 0

            # Calculate efficiency as percentage
            if power_electrical > 0:
                efficiency_percent = (power_acoustic / power_electrical) * 100
            else:
                efficiency_percent = 0

            # Return as negative for minimization (pymoo minimizes by default)
            return -efficiency_percent
        elif enclosure_type == "mixed_profile_horn":
            from gsd.optimization.parameters.multisegment_horn_params import build_mixed_profile_horn

            # Build mixed-profile horn (exponential/conical/hyperbolic segments)
            horn, V_tc, V_rc = build_mixed_profile_horn(design_vector, driver, num_segments=2)
            flh = FrontLoadedHorn(driver, horn, V_tc=V_tc, V_rc=V_rc)

            # Calculate acoustic power at reference frequency
            power_acoustic = flh.acoustic_power(reference_frequency, voltage=voltage)

            # Calculate electrical power
            result = flh.electrical_impedance(reference_frequency, voltage=voltage)
            Ze = result['Ze_real'] + 1j * result['Ze_imag']

            if abs(Ze) > 0:
                power_electrical = (voltage ** 2) * Ze.real / (abs(Ze) ** 2)
            else:
                power_electrical = 0

            # Calculate efficiency as percentage
            if power_electrical > 0:
                efficiency_percent = (power_acoustic / power_electrical) * 100
            else:
                efficiency_percent = 0

            # Return as negative for minimization (pymoo minimizes by default)
            return -efficiency_percent
        else:
            # For other enclosure types, not implemented yet
            import warnings
            warnings.warn(f"Efficiency percent not implemented for {enclosure_type}")
            return -1000.0

    except Exception:
        return -1000.0  # Large penalty on failure
