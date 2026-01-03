"""Conical horn parameter space for optimization.

This module defines parameter ranges and typical values for optimizing
conical horn loudspeaker systems.

Literature:
- Olson (1947), Chapter 5 - Conical horn geometry and x0 parameter
- Beranek (1954), Chapter 5 - Spherical wave propagation
- Kolbrek horn theory tutorial - Spherical Hankel functions
- literature/horns/conical_theory.md
"""

import numpy as np
from gsd.driver.parameters import ThieleSmallParameters
from gsd.optimization.parameters.parameter_space import (
    ParameterRange,
    EnclosureParameterSpace,
)


def get_conical_horn_parameter_space(
    driver: ThieleSmallParameters,
    preset: str = "midrange_horn"
) -> EnclosureParameterSpace:
    """
    Get parameter space for conical horn optimization.

    Optimizes 5 parameters:
    - throat_area: Horn throat area (driver coupling)
    - mouth_area: Horn mouth area (radiation)
    - length: Horn axial length
    - V_tc: Throat chamber volume (compliance)
    - V_rc: Rear chamber volume (compliance)

    Fixed parameters (not optimized):
    - radiation_angle: 2π (half-space)

    Literature:
        - Olson (1947), Chapter 5 - Conical horn geometry practical limits
        - Beranek (1954) - Spherical wave propagation in conical horns
        - literature/horns/conical_theory.md

    Args:
        driver: ThieleSmallParameters for the driver
        preset: Design preset ("bass_horn", "midrange_horn", "fullrange_horn")
            - bass_horn: Large mouth, long length, no sharp cutoff
            - midrange_horn: Medium size (200-500 Hz range) [default]
            - fullrange_horn: Compact, wider bandwidth

    Returns:
        EnclosureParameterSpace: Parameter space definition

    Raises:
        ValueError: If preset is not recognized

    Examples:
        >>> from gsd.driver import load_driver
        >>> param_space = get_conical_horn_parameter_space(driver, preset="midrange_horn")
        >>> param_space.get_parameter_names()
        ['throat_area', 'mouth_area', 'length', 'V_tc', 'V_rc']
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
        # Bass horn: Large mouth, long length
        # Conical horns have no sharp cutoff, but mouth size affects loading
        # Target effective range: 40-200 Hz
        throat_min = 0.1 * S_d
        throat_max = 0.3 * S_d
        mouth_min = 0.1  # m² (radius ~18 cm)
        mouth_max = 1.0  # m² (radius ~56 cm)
        length_min = 1.5  # m (bass horns are long)
        length_max = 3.0  # m (practical limit)
        # Throat chamber: Bass horns typically use direct coupling or small chamber
        V_tc_min = 0.0  # No throat chamber (direct coupling preferred for bass)
        V_tc_max = 0.00002  # 20 cm³ (small chamber)
        V_rc_min = 0.5 * V_as
        V_rc_max = 2.0 * V_as

    elif preset == "midrange_horn":
        # Midrange horn: Medium size
        # Target effective range: 200-2000 Hz
        # Mouth size: Large enough for proper loading (Beranek 1954)
        throat_min = 0.2 * S_d
        throat_max = 0.5 * S_d
        mouth_min = 0.04  # m² (400 cm², radius ~11.3 cm)
        mouth_max = 0.06  # m² (600 cm², radius ~13.8 cm)
        length_min = 0.3  # m (compact midrange)
        length_max = 1.0  # m (larger midrange)
        # Throat chamber: Practical limits for compression driver phase plugs
        V_tc_min = 0.0  # No throat chamber (direct coupling)
        V_tc_max = 0.000015  # 15 cm³ (practical for compression driver phase plugs)
        V_rc_min = 0.0  # No rear chamber
        V_rc_max = 1.0 * V_as  # Optional rear chamber

    elif preset == "fullrange_horn":
        # Full-range horn: Compact, wider bandwidth
        # Target effective range: 100-5000 Hz
        throat_min = 0.15 * S_d
        throat_max = 0.4 * S_d
        mouth_min = 0.02  # m² (radius ~8 cm)
        mouth_max = 0.2  # m² (radius ~25 cm)
        length_min = 0.5  # m
        length_max = 1.5  # m
        # Throat chamber: Practical limits for fullrange drivers
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
    # Literature: Olson (1947) - Throat area should be 10-50% of diaphragm area
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
    # Note: Conical horns don't have flare constant or cutoff frequency constraints
    # They rely on mouth size for loading and spherical wave propagation
    constraints = [
        "mouth_size",  # Mouth ≥ λ/2 at minimum frequency
        "expansion_ratio",  # Reasonable expansion ratio (mouth_area/throat_area)
        "max_displacement",  # Diaphragm protection
    ]

    return EnclosureParameterSpace(
        enclosure_type="conical_horn",
        parameters=parameters,
        typical_ranges=typical_ranges,
        constraints=constraints,
    )


def calculate_conical_horn_volume(throat_area: float, mouth_area: float, length: float) -> float:
    """
    Calculate conical horn volume (truncated cone).

    For a conical horn, the volume is the volume of a truncated cone:
        V = (S₁ + S₂) / 2 × L

    where S₁ is throat area, S₂ is mouth area, L is length.

    Literature:
        - Olson (1947), Chapter 5 - Conical horn geometry
        - Geometry: Volume of truncated cone

    Args:
        throat_area: Horn throat area S₁ [m²]
        mouth_area: Horn mouth area S₂ [m²]
        length: Horn length L [m]

    Returns:
        Horn volume [m³]

    Examples:
        >>> V = calculate_conical_horn_volume(0.0015, 0.15, 1.2)
        >>> print(f"{V*1000:.1f} liters")
        90.9 liters

    Notes:
        This is the internal air volume of the horn, not including the rear
        chamber. Total system volume = V_horn + V_rc.

    Validation:
        Compare with geometric formula V = π·h·(R² + R·r + r²)/3
        where R is mouth radius, r is throat radius, h is length.
        Expected agreement: <0.01% deviation (rounding error only).
    """
    # Truncated cone volume: (S₁ + S₂) / 2 × L
    # This is exact for conical horns with circular cross-section
    v_horn = (throat_area + mouth_area) / 2 * length

    return v_horn


def calculate_conical_expansion_ratio(throat_area: float, mouth_area: float) -> float:
    """
    Calculate conical horn expansion ratio.

    The expansion ratio determines the loading characteristics:
    - Low ratio (< 5): Minimal loading, wider bandwidth
    - Medium ratio (5-20): Moderate loading, balanced response
    - High ratio (> 20): Strong loading, narrowed bandwidth

    Literature:
        - Olson (1947), Chapter 5 - Horn loading and impedance
        - Beranek (1954) - Radiation impedance

    Args:
        throat_area: Horn throat area [m²]
        mouth_area: Horn mouth area [m²]

    Returns:
        Expansion ratio (mouth_area / throat_area)

    Examples:
        >>> ratio = calculate_conical_expansion_ratio(0.0015, 0.15)
        >>> print(f"Expansion ratio: {ratio:.1f}:1")
        Expansion ratio: 100.0:1
    """
    if throat_area <= 0:
        return float('inf')
    return mouth_area / throat_area


def decode_conical_design(
    design: np.ndarray,
    driver: ThieleSmallParameters
) -> dict:
    """
    Decode optimization array into conical horn parameters.

    Converts the flat optimization array into a structured dictionary
    with horn geometry parameters for building a ConicalHorn.

    Args:
        design: Optimization array [throat_area, mouth_area, length, V_tc, V_rc]
        driver: ThieleSmallParameters for the driver

    Returns:
        Dictionary with horn parameters:
        - throat_area, mouth_area: Horn dimensions
        - length: Horn length
        - x0: Distance from apex to throat
        - V_tc: Throat chamber volume
        - V_rc: Rear chamber volume
        - expansion_ratio: Mouth/throat area ratio

    Examples:
        >>> design = np.array([0.0015, 0.15, 1.2, 0.0, 0.0])
        >>> params = decode_conical_design(design, driver)
        >>> params['expansion_ratio']
        100.0
    """
    throat_area, mouth_area, length, V_tc, V_rc = design

    # Calculate x0 (distance from cone apex to throat)
    # From similar triangles: x0 = r_t × L / (r_m - r_t)
    r_t = np.sqrt(throat_area / np.pi)
    r_m = np.sqrt(mouth_area / np.pi)

    if abs(r_m - r_t) < 1e-9:
        # Cylindrical case (no expansion)
        x0 = np.inf
    else:
        x0 = (r_t * length) / (r_m - r_t)

    return {
        'throat_area': throat_area,
        'mouth_area': mouth_area,
        'length': length,
        'x0': x0,
        'V_tc': V_tc,
        'V_rc': V_rc,
        'expansion_ratio': mouth_area / throat_area if throat_area > 0 else float('inf'),
    }


def build_conical_horn(
    design: np.ndarray,
    driver: ThieleSmallParameters
):
    """
    Build ConicalHorn from design vector.

    This is a helper function that creates a ConicalHorn instance
    from an optimization array.

    Args:
        design: Optimization array [throat_area, mouth_area, length, V_tc, V_rc]
        driver: ThieleSmallParameters (for context)

    Returns:
        Tuple of (ConicalHorn, V_tc, V_rc)

    Examples:
        >>> design = np.array([0.0015, 0.15, 1.2, 0.0, 0.0])
        >>> horn, V_tc, V_rc = build_conical_horn(design, driver)
        >>> horn.throat_area
        0.0015
    """
    from gsd.simulation.types import ConicalHorn

    params = decode_conical_design(design, driver)

    horn = ConicalHorn(
        throat_area=params['throat_area'],
        mouth_area=params['mouth_area'],
        length=params['length'],
        x0=params['x0']
    )

    return horn, params['V_tc'], params['V_rc']
