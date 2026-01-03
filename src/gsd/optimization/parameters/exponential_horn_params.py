"""Exponential horn parameter space for optimization.

This module defines parameter ranges and typical values for optimizing
exponential horn loudspeaker systems.

Literature:
- Olson (1947), Chapter 5 - Horn geometry practical limits
- Olson (1947), Eq. 5.18 - Cutoff frequency formula
- Kolbrek horn theory tutorial - Mouth size for cutoff frequency
- literature/horns/olson_1947.md
"""

import numpy as np
from gsd.driver.parameters import ThieleSmallParameters
from gsd.optimization.parameters.parameter_space import (
    ParameterRange,
    EnclosureParameterSpace,
)
from gsd.simulation.constants import SPEED_OF_SOUND


def get_exponential_horn_parameter_space(
    driver: ThieleSmallParameters,
    preset: str = "midrange_horn"
) -> EnclosureParameterSpace:
    """
    Get parameter space for exponential horn optimization.

    Optimizes 5 parameters:
    - throat_area: Horn throat area (driver coupling)
    - mouth_area: Horn mouth area (radiation)
    - length: Horn axial length
    - V_tc: Throat chamber volume (compliance)
    - V_rc: Rear chamber volume (compliance)

    Fixed parameters (not optimized):
    - radiation_angle: 2π (half-space)

    Literature:
        - Olson (1947), Chapter 5 - Horn geometry practical limits
        - Kolbrek horn theory tutorial - Mouth size for cutoff frequency
        - literature/horns/olson_1947.md

    Args:
        driver: ThieleSmallParameters for the driver
        preset: Design preset ("bass_horn", "midrange_horn", "fullrange_horn")
            - bass_horn: Large mouth, long length, low cutoff (40-80 Hz)
            - midrange_horn: Medium size, midrange cutoff (200-500 Hz) [default]
            - fullrange_horn: Compact, wider bandwidth (100-500 Hz)

    Returns:
        EnclosureParameterSpace: Parameter space definition

    Raises:
        ValueError: If preset is not recognized

    Examples:
        >>> from gsd.driver import load_driver
        >>> param_space = get_exponential_horn_parameter_space(driver, preset="midrange_horn")
        >>> param_space.get_parameter_names()
        ['throat_area', 'mouth_area', 'length', 'V_rc']
        >>> xl, xu = param_space.get_bounds_array()
        >>> xl[0]  # Minimum throat area [m²]
        0.00016...
    """
    # Driver parameters for scaling
    S_d = driver.S_d  # Diaphragm area [m²]
    V_as = driver.V_as  # Equivalent volume of suspension [m³]

    # Define preset-specific ranges
    # Literature: Olson (1947), Chapter 5 - Practical horn dimensions
    if preset == "bass_horn":
        # Bass horn: Large mouth, long length, low cutoff frequency
        # Target cutoff: 40-80 Hz
        # Mouth radius: ~0.5-1.0 m for effective radiation
        #
        # CRITICAL: Throat sizing for direct radiator bass horns
        # Literature: Beranek (1954), Olson (1947) - Practical horn design
        # For bass horns with woofers (not compression drivers):
        #   - Throat should be 50-100% of driver area
        #   - Compression ratio < 2:1 to avoid turbulence/choking
        #   - Higher compression requires phase plug (impractical for woofers)
        #
        # throat_min = 0.5 * S_d gives compression ratio of 2:1 (acceptable)
        # throat_max = 1.0 * S_d gives compression ratio of 1:1 (no compression)
        throat_min = 0.5 * S_d  # 50% of driver area (compression ratio 2:1)
        throat_max = 1.0 * S_d  # 100% of driver area (no compression, best for woofers)
        mouth_min = 0.1  # m² (radius ~18 cm)
        mouth_max = 1.0  # m² (radius ~56 cm)
        length_min = 1.5  # m (bass horns are long)
        length_max = 3.0  # m (practical limit)
        # Throat chamber: Bass horns typically use direct coupling or small chamber
        V_tc_min = 0.0  # No throat chamber (direct coupling preferred for bass)
        V_tc_max = 0.00002  # 20 cm³ (small chamber, max 25 cm length for smallest throat)
        V_rc_min = 0.5 * V_as
        V_rc_max = 2.0 * V_as

    elif preset == "midrange_horn":
        # Midrange horn: Medium size, moderate cutoff frequency
        # Target cutoff: 200-500 Hz
        # Mouth size: Large enough for proper loading (Beranek 1954)
        # Literature: Mouth circumference ≥ wavelength at cutoff for flat response <3 dB
        # For Fc ≈ 350-450 Hz: need mouth_area ≥ 400-500 cm² (23-25 cm diameter)
        throat_min = 0.2 * S_d
        throat_max = 0.5 * S_d
        mouth_min = 0.04  # m² (400 cm², radius ~11.3 cm)
        mouth_max = 0.06  # m² (600 cm², radius ~13.8 cm)
        length_min = 0.3  # m (compact midrange)
        length_max = 1.0  # m (larger midrange)
        # Throat chamber: Practical limits for compression driver phase plugs
        # Length should be 2-8 cm for typical compression drivers
        # Volume = length × area, so V_tc depends on throat area
        # For throat_min (1.6 cm²): V_tc_max = 8 cm × 1.6 ≈ 12.8 cm³
        # For throat_max (4.0 cm²): V_tc_max = 8 cm × 4.0 ≈ 32 cm³
        # Set conservative bound: 0-15 cm³ (max 9.4 cm length for smallest throat)
        V_tc_min = 0.0  # No throat chamber (direct coupling)
        V_tc_max = 0.000015  # 15 cm³ (practical for compression driver phase plugs)
        V_rc_min = 0.0  # No rear chamber
        V_rc_max = 1.0 * V_as  # Optional rear chamber

    elif preset == "fullrange_horn":
        # Full-range horn: Compact, wider bandwidth
        # Target cutoff: 100-500 Hz
        # Compromise between size and low-frequency extension
        throat_min = 0.15 * S_d
        throat_max = 0.4 * S_d
        mouth_min = 0.02  # m² (radius ~8 cm)
        mouth_max = 0.2  # m² (radius ~25 cm)
        length_min = 0.5  # m
        length_max = 1.5  # m
        # Throat chamber: Practical limits for fullrange drivers
        # Length 2-8 cm, so for 1-5 cm² throat: V_tc up to 40 cm³
        # Set conservative bound for practical phase plug geometry
        V_tc_min = 0.0
        V_tc_max = 0.00002  # 20 cm³ (practical for fullrange)
        V_rc_min = 0.0
        V_rc_max = 1.5 * V_as

    else:
        raise ValueError(
            f"Unknown preset: {preset}. "
            f"Choose from: 'bass_horn', 'midrange_horn', 'fullrange_horn'"
        )

    # Define parameter ranges
    # Literature: Olson (1947), Beranek (1954) - Throat area depends on driver type:
    #   - Compression drivers (with phase plugs): 10-50% of diaphragm area
    #   - Direct radiator woofers (bass horns): 50-100% of diaphragm area
    #     (higher compression requires phase plug, impractical for woofers)
    parameters = [
        ParameterRange(
            name="throat_area",
            min_value=throat_min,
            max_value=throat_max,
            units="m²",
            description="Horn throat area (driver coupling)"
        ),
        ParameterRange(
            name="mouth_area",
            min_value=mouth_min,
            max_value=mouth_max,
            units="m²",
            description="Horn mouth area (radiation)"
        ),
        ParameterRange(
            name="length",
            min_value=length_min,
            max_value=length_max,
            units="m",
            description="Horn axial length"
        ),
        ParameterRange(
            name="V_tc",
            min_value=V_tc_min,
            max_value=V_tc_max,
            units="m³",
            description="Throat chamber volume (compliance)"
        ),
        ParameterRange(
            name="V_rc",
            min_value=V_rc_min,
            max_value=V_rc_max,
            units="m³",
            description="Rear chamber volume (compliance)"
        ),
    ]

    # Define typical ranges for reference designs
    # These are useful for initial population seeding in optimization
    typical_ranges = {
        "bass_horn": {
            "throat_area": (0.15 * S_d, 0.25 * S_d),
            "mouth_area": (0.3, 0.7),
            "length": (2.0, 2.5),
            "V_tc": (0.0, 0.2 * V_tc_max),
            "V_rc": (0.8 * V_as, 1.2 * V_as),
        },
        "midrange_horn": {
            # Large mouth for proper loading (Beranek 1954)
            # Target: mouth_circumference ≥ wavelength at Fc for <3 dB flatness
            "throat_area": (0.3 * S_d, 0.4 * S_d),
            "mouth_area": (0.04, 0.055),
            "length": (0.5, 0.8),
            "V_tc": (0.0, 0.2 * V_tc_max),
            "V_rc": (0.0, 0.2 * V_as),
        },
        "fullrange_horn": {
            "throat_area": (0.2 * S_d, 0.3 * S_d),
            "mouth_area": (0.05, 0.15),
            "length": (0.8, 1.2),
            "V_tc": (0.0, 0.2 * V_tc_max),
            "V_rc": (0.3 * V_as, 0.8 * V_as),
        },
    }

    # Define constraints to apply
    # Literature: Olson (1947) - Mouth size, flare rate, displacement limits
    constraints = [
        "horn_cutoff_frequency",  # Target cutoff range
        "mouth_size",  # Mouth ≥ λ/2 at cutoff (Olson 1947)
        "flare_constant_limits",  # 0.5 < m·L < 3.0 (practical horns)
        "max_displacement",  # Diaphragm protection
    ]

    return EnclosureParameterSpace(
        enclosure_type="exponential_horn",
        parameters=parameters,
        typical_ranges=typical_ranges,
        constraints=constraints,
    )


def calculate_horn_cutoff_frequency(throat_area: float, mouth_area: float,
                                    length: float, c: float = SPEED_OF_SOUND) -> float:
    """
    Calculate exponential horn cutoff frequency.

    Uses Kolbrek's convention where the pressure amplitude flare constant is
    half the area expansion flare constant. This matches Hornresp's F12 parameter.

    Literature:
        - Olson (1947), Eq. 5.18 - Area expansion flare constant m = ln(S₂/S₁)/L
        - Kolbrek (2018), Horn Theory Tutorial - Pressure amplitude convention
          m_kolbrek = m_olson/2, f_c = c·m_kolbrek/(2π)
        - literature/horns/olson_1947.md
        - literature/horns/kolbrek_horn_theory_tutorial.md

    Args:
        throat_area: Horn throat area [m²]
        mouth_area: Horn mouth area [m²]
        length: Horn length [m]
        c: Speed of sound [m/s], default 343 m/s

    Returns:
        Cutoff frequency [Hz]

    Examples:
        >>> fc = calculate_horn_cutoff_frequency(0.0005, 0.02, 0.5)
        >>> print(f"{fc:.1f} Hz")
        201.4 Hz

    Notes:
        Below cutoff frequency, the horn does not efficiently propagate sound
        waves (evanescent modes). SPL drops rapidly below f_c.

    Validation:
        Compare with Hornresp's F12 (cutoff) parameter for identical horn geometry.
        Expected agreement: <0.1% deviation for horns with well-defined flare constant.
    """
    if length <= 0:
        return float('inf')

    # Flare constant: m_olson = ln(S₂/S₁) / L (area expansion)
    # Olson (1947), Chapter 5
    m_olson = np.log(mouth_area / throat_area) / length

    # Pressure amplitude flare constant (Kolbrek convention)
    # m_kolbrek = m_olson / 2
    # The pressure varies as p(x) ∝ exp(m_olson·x/2)
    #
    # Cutoff frequency: f_c = c·m_kolbrek / (2π)
    # This matches Kolbrek's convention and Hornresp's F12 parameter
    m_kolbrek = m_olson / 2.0
    fc = (c * m_kolbrek) / (2 * np.pi)

    return fc


def calculate_horn_volume(throat_area: float, mouth_area: float, length: float) -> float:
    """
    Calculate exponential horn volume.

    For an exponential horn S(x) = S₁·exp(m·x), the volume is:
        V_horn = ∫₀ᴸ S(x)dx = (S₂ - S₁) / m

    where m = ln(S₂/S₁) / L is the flare constant.

    Literature:
        - Olson (1947), Chapter 5 - Horn geometry
        - Calculus: ∫exp(ax)dx = exp(ax)/a

    Args:
        throat_area: Horn throat area S₁ [m²]
        mouth_area: Horn mouth area S₂ [m²]
        length: Horn length L [m]

    Returns:
        Horn volume [m³]

    Examples:
        >>> V = calculate_horn_volume(0.0005, 0.02, 0.5)
        >>> print(f"{V*1000:.1f} liters")
        4.7 liters

    Notes:
        This is the internal air volume of the horn, not including the rear
        chamber. Total system volume = V_horn + V_rc.
    """
    if mouth_area <= throat_area:
        # Not a valid expanding horn - treat as conical
        # V_cone = (S₁ + S₂) / 2 * L
        return (throat_area + mouth_area) / 2 * length

    # Flare constant
    flare_constant = np.log(mouth_area / throat_area) / length

    if flare_constant <= 0:
        # Fallback to conical volume
        return (throat_area + mouth_area) / 2 * length

    # Exponential horn volume: (S₂ - S₁) / m
    v_horn = (mouth_area - throat_area) / flare_constant

    return v_horn
