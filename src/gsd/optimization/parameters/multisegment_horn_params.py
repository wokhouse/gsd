"""Multi-segment horn parameter space for optimization.

This module defines parameter ranges and typical values for optimizing
multi-segment exponential horn loudspeaker systems.

Multi-segment horns allow the optimizer to discover profiles beyond
standard exponential, tractrix, or hyperbolic shapes by varying the
flare rate along the horn length.

Literature:
- Olson (1947), Chapter 8 - Compound and stepped horns
- Kolbrek Part 1 - T-matrix chaining for multi-segment horns
- literature/horns/olson_1947.md
- literature/horns/kolbrek_horn_theory_tutorial.md
"""

import numpy as np
from gsd.driver.parameters import ThieleSmallParameters
from gsd.optimization.parameters.parameter_space import (
    ParameterRange,
    EnclosureParameterSpace,
)
from gsd.simulation.constants import SPEED_OF_SOUND


def get_multisegment_horn_parameter_space(
    driver: ThieleSmallParameters,
    preset: str = "midrange_horn",
    num_segments: int = 2,
    max_length: float = None,
    max_mouth_area: float = None,
    max_volume: float = None
) -> EnclosureParameterSpace:
    """
    Get parameter space for multi-segment horn optimization.

    For a 2-segment horn, optimizes 7 parameters:
    - throat_area: Horn throat area (driver coupling)
    - middle_area: Area at segment junction (segment 1 mouth = segment 2 throat)
    - mouth_area: Horn mouth area (radiation)
    - length1: Length of segment 1 (throat → middle)
    - length2: Length of segment 2 (middle → mouth)
    - V_tc: Throat chamber volume (compliance)
    - V_rc: Rear chamber volume (compliance)

    For a 3-segment horn, optimizes 9 parameters (add area2, length3).

    Fixed parameters (not optimized):
    - radiation_angle: 2π (half-space)

    The flare constants m1, m2 are calculated from geometry:
        m1 = ln(middle_area / throat_area) / length1
        m2 = ln(mouth_area / middle_area) / length2

    This allows the optimizer to discover optimal flare rate profiles
    without being constrained to standard horn types.

    Literature:
        - Olson (1947), Chapter 8 - Compound horns
        - Kolbrek Part 1 - Multi-segment horn theory
        - literature/horns/kolbrek_horn_theory_tutorial.md

    Args:
        driver: ThieleSmallParameters for the driver
        preset: Design preset ("bass_horn", "midrange_horn", "fullrange_horn")
        num_segments: Number of horn segments (2 or 3)
        max_length: Optional maximum TOTAL horn length in meters (applied per segment)
        max_mouth_area: Optional maximum mouth area in m²
        max_volume: Optional maximum horn volume in m³ (not yet implemented)

    Returns:
        EnclosureParameterSpace: Parameter space definition

    Raises:
        ValueError: If preset or num_segments is not recognized

    Examples:
        >>> from gsd.driver import load_driver
        >>> param_space = get_multisegment_horn_parameter_space(
        ...     driver, preset="midrange_horn", num_segments=2
        ... )
        >>> param_space.get_parameter_names()
        ['throat_area', 'middle_area', 'mouth_area', 'length1', 'length2', 'V_rc']
    """
    if num_segments not in [2, 3]:
        raise ValueError(
            f"num_segments must be 2 or 3, got {num_segments}. "
            "Hornresp supports maximum 4 segments, but optimization "
            "with 2-3 segments provides sufficient flexibility."
        )

    # Driver parameters for scaling
    S_d = driver.S_d  # Diaphragm area [m²]
    V_as = driver.V_as  # Equivalent volume of suspension [m³]

    # Define preset-specific ranges
    # Literature: Olson (1947), Chapter 5 - Practical horn dimensions
    if preset == "bass_horn":
        # Bass horn: Large mouth, long length, low cutoff frequency
        # Target cutoff: 40-80 Hz
        #
        # CRITICAL: Throat sizing for direct radiator bass horns
        # Literature: Beranek (1954), Olson (1947) - Practical horn design
        # For bass horns with woofers (not compression drivers):
        #   - Throat should be 50-100% of driver area
        #   - Compression ratio < 2:1 to avoid turbulence/choking
        #   - Higher compression requires phase plug (impractical for woofers)
        throat_min = 0.5 * S_d  # 50% of driver area (compression ratio 2:1)
        throat_max = 1.0 * S_d  # 100% of driver area (no compression, best for woofers)
        middle_min = 0.05  # m²
        middle_max = 0.5  # m²
        mouth_min = 0.3  # m²
        mouth_max = 1.5  # m²
        length_min = 1.5  # m
        length_max = 3.0  # m
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
        middle_min = 0.01  # m² (100 cm²)
        middle_max = 0.04  # m² (400 cm²)
        mouth_min = 0.04  # m² (400 cm², radius ~11.3 cm)
        mouth_max = 0.06  # m² (600 cm², radius ~13.8 cm)
        length_min = 0.15  # m (each segment minimum 15 cm)
        length_max = 0.6  # m (each segment maximum 60 cm, total up to 1.2 m)
        # Throat chamber: Practical limits for compression driver phase plugs
        # Length should be 2-8 cm for typical compression drivers
        # Set conservative bound: 0-15 cm³ (max 9.4 cm length for smallest throat)
        V_tc_min = 0.0  # No throat chamber (direct coupling)
        V_tc_max = 0.000015  # 15 cm³ (practical for compression driver phase plugs)
        V_rc_min = 0.0  # No rear chamber
        V_rc_max = 1.0 * V_as  # Optional rear chamber

    elif preset == "fullrange_horn":
        # Full-range horn: Compact, wider bandwidth
        # Target cutoff: 100-500 Hz
        throat_min = 0.15 * S_d
        throat_max = 0.4 * S_d
        middle_min = 0.01  # m²
        middle_max = 0.1  # m²
        mouth_min = 0.02  # m² (radius ~8 cm)
        mouth_max = 0.2  # m² (radius ~25 cm)
        length_min = 0.2  # m
        length_max = 0.8  # m
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

    # Apply size constraints (e.g., for 3D printing limitations)
    # If max_length is specified, limit per-segment length to max_length / num_segments
    # This ensures the TOTAL horn length fits within the constraint
    if max_length is not None:
        # For num_segments=2, each segment gets max_length/2
        # For num_segments=3, each segment gets max_length/3
        per_segment_max = max_length / num_segments
        # Clamp length_max to the smaller of preset value and constraint
        length_max = min(length_max, per_segment_max)
        # Ensure length_min doesn't exceed length_max after constraint
        length_min = min(length_min, length_max)

    # Apply mouth area constraint
    if max_mouth_area is not None:
        mouth_max = min(mouth_max, max_mouth_area)
        # Ensure mouth_min doesn't exceed mouth_max after constraint
        mouth_min = min(mouth_min, mouth_max)

    # Build parameter list based on num_segments
    parameters = [
        ParameterRange(
            name="throat_area",
            min_value=throat_min,
            max_value=throat_max,
            units="m²",
            description="Horn throat area (driver coupling)"
        ),
        ParameterRange(
            name="middle_area",
            min_value=middle_min,
            max_value=middle_max,
            units="m²",
            description="Area at segment junction (segment 1 mouth = segment 2 throat)"
        ),
        ParameterRange(
            name="mouth_area",
            min_value=mouth_min,
            max_value=mouth_max,
            units="m²",
            description="Horn mouth area (radiation)"
        ),
        ParameterRange(
            name="length1",
            min_value=length_min,
            max_value=length_max,
            units="m",
            description="Segment 1 length (throat → middle)"
        ),
        ParameterRange(
            name="length2",
            min_value=length_min,
            max_value=length_max,
            units="m",
            description="Segment 2 length (middle → mouth)"
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

    # Add third segment parameters if requested
    if num_segments == 3:
        parameters.insert(3, ParameterRange(
            name="area2",
            min_value=middle_min,
            max_value=max(middle_max, mouth_min),
            units="m²",
            description="Area at segment 2-3 junction"
        ))
        parameters.insert(-1, ParameterRange(
            name="length3",
            min_value=length_min,
            max_value=length_max,
            units="m",
            description="Segment 3 length (area2 → mouth)"
        ))

    # Define typical ranges for reference designs
    # These are useful for initial population seeding in optimization
    typical_ranges = {
        "bass_horn": {
            "throat_area": (0.7 * S_d, 1.0 * S_d),  # 70-100% of driver area (practical range)
            "middle_area": (0.2, 0.4),
            "mouth_area": (0.5, 1.0),
            "length1": (1.0, 1.5),
            "length2": (1.0, 1.5),
            "V_tc": (0.0, 0.2 * V_tc_max),
            "V_rc": (0.8 * V_as, 1.2 * V_as),
        },
        "midrange_horn": {
            # Typical: fast flare near throat, gradual near mouth
            "throat_area": (0.3 * S_d, 0.4 * S_d),
            "middle_area": (0.015, 0.025),
            "mouth_area": (0.045, 0.055),
            "length1": (0.18, 0.25),  # Short throat segment
            "length2": (0.35, 0.50),  # Longer mouth segment
            "V_tc": (0.0, 0.2 * V_tc_max),
            "V_rc": (0.0, 0.2 * V_as),
        },
        "fullrange_horn": {
            "throat_area": (0.2 * S_d, 0.3 * S_d),
            "middle_area": (0.03, 0.08),
            "mouth_area": (0.08, 0.15),
            "length1": (0.3, 0.5),
            "length2": (0.4, 0.7),
            "V_tc": (0.0, 0.2 * V_tc_max),
            "V_rc": (0.3 * V_as, 0.8 * V_as),
        },
    }

    # Add 3-segment typical ranges
    if num_segments == 3:
        typical_ranges["midrange_horn_3seg"] = {
            "throat_area": (0.3 * S_d, 0.4 * S_d),
            "middle_area": (0.010, 0.020),
            "area2": (0.025, 0.040),
            "mouth_area": (0.045, 0.055),
            "length1": (0.15, 0.25),
            "length2": (0.20, 0.30),
            "length3": (0.25, 0.40),
            "V_tc": (0.0, 0.2 * V_tc_max),
            "V_rc": (0.0, 0.2 * V_as),
        }

    # Define constraints to apply
    # Literature: Olson (1947) - Mouth size, flare rate, displacement limits
    constraints = [
        "segment_continuity",  # Ensure throat < middle < mouth (monotonic expansion)
        "mouth_size",  # Mouth ≥ λ/2 at minimum cutoff
        "flare_constant_limits",  # Each segment: 0.5 < m·L < 3.0
        "max_displacement",  # Diaphragm protection
    ]

    return EnclosureParameterSpace(
        enclosure_type="multisegment_horn",
        parameters=parameters,
        typical_ranges=typical_ranges,
        constraints=constraints,
    )


def decode_multisegment_design(
    design: np.ndarray,
    driver: ThieleSmallParameters,
    num_segments: int = 2
) -> dict:
    """
    Decode optimization array into multi-segment horn parameters.

    Converts the flat optimization array into a structured dictionary
    with horn geometry parameters for building a MultiSegmentHorn.

    Args:
        design: Optimization array [throat_area, middle_area, mouth_area,
                length1, length2, V_tc, V_rc] for 2-segment, or with additional
                [area2, length3] for 3-segment
        driver: ThieleSmallParameters for the driver
        num_segments: Number of segments (2 or 3)

    Returns:
        Dictionary with horn parameters:
        - throat_area, mouth_area: Overall horn dimensions
        - segments: List of (throat_area, mouth_area, length) tuples
        - V_rc: Rear chamber volume
        - flare_constants: List of m for each segment

    Examples:
        >>> design = np.array([0.000212, 0.010, 0.04084, 0.20, 0.394, 0.0])
        >>> params = decode_multisegment_design(design, driver, num_segments=2)
        >>> params['flare_constants']
        [19.27, 3.57]
    """
    if num_segments == 2:
        throat_area, middle_area, mouth_area, length1, length2, V_tc, V_rc = design

        # Build segment list
        segments = [
            (throat_area, middle_area, length1),  # Segment 1
            (middle_area, mouth_area, length2),     # Segment 2
        ]

        # Calculate flare constants
        m1 = np.log(middle_area / throat_area) / length1 if length1 > 0 else 0
        m2 = np.log(mouth_area / middle_area) / length2 if length2 > 0 else 0
        flare_constants = [m1, m2]

    elif num_segments == 3:
        (throat_area, middle_area, area2, mouth_area,
         length1, length2, length3, V_tc, V_rc) = design

        # Build segment list
        segments = [
            (throat_area, middle_area, length1),  # Segment 1
            (middle_area, area2, length2),        # Segment 2
            (area2, mouth_area, length3),         # Segment 3
        ]

        # Calculate flare constants
        m1 = np.log(middle_area / throat_area) / length1 if length1 > 0 else 0
        m2 = np.log(area2 / middle_area) / length2 if length2 > 0 else 0
        m3 = np.log(mouth_area / area2) / length3 if length3 > 0 else 0
        flare_constants = [m1, m2, m3]

    else:
        raise ValueError(f"num_segments must be 2 or 3, got {num_segments}")

    return {
        'throat_area': throat_area,
        'mouth_area': mouth_area,
        'segments': segments,
        'V_tc': V_tc,
        'V_rc': V_rc,
        'flare_constants': flare_constants,
        'total_length': sum(seg[2] for seg in segments),
    }


def calculate_multisegment_horn_cutoff(
    throat_area: float,
    middle_area: float,
    mouth_area: float,
    length1: float,
    length2: float,
    c: float = SPEED_OF_SOUND
) -> tuple:
    """
    Calculate cutoff frequencies for each segment.

    Each segment has its own cutoff based on its flare constant:
        f_c = c·m_olson/(4π) (Kolbrek convention)

    The overall horn cutoff is the maximum of segment cutoffs
    (highest frequency = most restrictive).

    Literature:
        - Olson (1947), Eq. 5.18 - Area expansion flare constant m = ln(S₂/S₁)/L
        - Kolbrek (2018), Horn Theory Tutorial - Pressure amplitude convention
          m_kolbrek = m_olson/2, f_c = c·m_kolbrek/(2π) = c·m_olson/(4π)
        - literature/horns/olson_1947.md
        - literature/horns/kolbrek_horn_theory_tutorial.md

    Args:
        throat_area: Horn throat area [m²]
        middle_area: Area at segment junction [m²]
        mouth_area: Horn mouth area [m²]
        length1: Segment 1 length [m]
        length2: Segment 2 length [m]
        c: Speed of sound [m/s], default 343 m/s

    Returns:
        Tuple of (fc1, fc2, fc_overall) in Hz

    Examples:
        >>> fc1, fc2, fc_overall = calculate_multisegment_horn_cutoff(
        ...     0.000212, 0.010, 0.04084, 0.20, 0.394
        ... )
        >>> print(f"Segment 1: {fc1:.0f} Hz, Segment 2: {fc2:.0f} Hz")
        >>> print(f"Overall: {fc_overall:.0f} Hz")

    Validation:
        Compare with Hornresp's F12 (cutoff) parameter for each segment.
        Expected agreement: <0.1% deviation for segments with well-defined flare constants.
    """
    # Segment 1 flare constant and cutoff
    # Using Kolbrek convention: f_c = c·m_kolbrek/(2π) where m_kolbrek = m_olson/2
    m1_olson = np.log(middle_area / throat_area) / length1 if length1 > 0 else 0
    fc1 = (c * m1_olson / 2.0) / (2 * np.pi) if m1_olson > 0 else float('inf')

    # Segment 2 flare constant and cutoff
    m2_olson = np.log(mouth_area / middle_area) / length2 if length2 > 0 else 0
    fc2 = (c * m2_olson / 2.0) / (2 * np.pi) if m2_olson > 0 else float('inf')

    # Overall cutoff is the maximum (most restrictive segment)
    fc_overall = max(fc1, fc2)

    return fc1, fc2, fc_overall


def get_hyperbolic_parameter_space(
    driver: ThieleSmallParameters,
    preset: str = "midrange_horn",
    num_segments: int = 2
) -> EnclosureParameterSpace:
    """
    Get parameter space for hyperbolic (Hypex) multi-segment horn optimization.

    This extends the standard multi-segment horn parameter space by adding
    the T (shape) parameter for each segment, enabling optimization of
    hyperbolic horns with variable throat loading characteristics.

    For a 2-segment hyperbolic horn, optimizes 9 parameters:
    - throat_area: Horn throat area (driver coupling)
    - middle_area: Area at segment junction (segment 1 mouth = segment 2 throat)
    - mouth_area: Horn mouth area (radiation)
    - length1: Length of segment 1 (throat → middle)
    - length2: Length of segment 2 (middle → mouth)
    - T1: Shape parameter for segment 1 (0.5 = deep hypex, 1.0 = exponential)
    - T2: Shape parameter for segment 2 (0.5 = deep hypex, 1.0 = exponential)
    - V_tc: Throat chamber volume (compliance)
    - V_rc: Rear chamber volume (compliance)

    Literature:
        - Salmon, V. (1946). "A New Family of Horns", JASA.
        - Kolbrek, B. (2008). "Horn Theory: An Introduction, Part 1".
        - literature/horns/kolbrek_horn_theory_tutorial.md

    Args:
        driver: ThieleSmallParameters for the driver
        preset: Design preset ("bass_horn", "midrange_horn", "fullrange_horn")
        num_segments: Number of horn segments (2 or 3)

    Returns:
        EnclosureParameterSpace: Parameter space definition with T parameters

    Raises:
        ValueError: If preset or num_segments is not recognized

    Examples:
        >>> from gsd.driver import load_driver
        >>> param_space = get_hyperbolic_parameter_space(
        ...     driver, preset="midrange_horn", num_segments=2
        ... )
        >>> param_space.get_parameter_names()
        ['throat_area', 'middle_area', 'mouth_area', 'length1', 'length2',
         'T1', 'T2', 'V_tc', 'V_rc']
    """
    # Get base parameter space (without T parameters)
    base_space = get_multisegment_horn_parameter_space(
        driver, preset=preset, num_segments=num_segments
    )

    # Add T parameters for each segment
    # T ranges: 0.5 (deep hypex) to 1.0 (exponential)
    # Literature: Kolbrek recommends T ≈ 0.6-0.7 for extended bass
    t_parameters = [
        ParameterRange(
            name=f"T{i+1}",
            min_value=0.5,
            max_value=1.0,
            units="",
            description=f"Shape parameter T for segment {i+1} (0.5=hypex, 1.0=exponential)"
        )
        for i in range(num_segments)
    ]

    # Insert T parameters before V_tc (near the end)
    # Find V_tc index and insert T parameters before it
    base_params = base_space.parameters.copy()
    vtc_idx = next(i for i, p in enumerate(base_params) if p.name == "V_tc")

    # Insert T parameters before V_tc
    new_parameters = base_params[:vtc_idx] + t_parameters + base_params[vtc_idx:]

    # Update typical ranges to include T parameters
    typical_ranges = base_space.typical_ranges.copy()
    for preset_name in typical_ranges:
        for i in range(num_segments):
            param_name = f"T{i+1}"
            # Default to exponential (T=1.0) as typical
            typical_ranges[preset_name][param_name] = (0.9, 1.0)

    return EnclosureParameterSpace(
        enclosure_type="multisegment_horn_hyperbolic",
        parameters=new_parameters,
        typical_ranges=typical_ranges,
        constraints=base_space.constraints,
    )


def decode_hyperbolic_design(
    design: np.ndarray,
    driver: ThieleSmallParameters,
    num_segments: int = 2
) -> dict:
    """
    Decode optimization array into hyperbolic multi-segment horn parameters.

    Converts the flat optimization array into a structured dictionary
    with horn geometry parameters including T (shape) parameters for
    building a MultiSegmentHorn with HyperbolicHorn segments.

    Args:
        design: Optimization array
            For 2-segment: [throat_area, middle_area, mouth_area,
                           length1, length2, T1, T2, V_tc, V_rc]
            For 3-segment: adds [area2, length3, T3] before V_tc
        driver: ThieleSmallParameters for the driver
        num_segments: Number of segments (2 or 3)

    Returns:
        Dictionary with horn parameters:
        - throat_area, mouth_area: Overall horn dimensions
        - segments: List of (throat_area, mouth_area, length, T) tuples
        - V_rc: Rear chamber volume
        - T_params: List of T values for each segment
        - segment_types: List recommending "HyperbolicHorn" or "HornSegment"

    Examples:
        >>> design = np.array([0.000212, 0.010, 0.04084, 0.20, 0.394,
        ...                    0.7, 1.0, 0.0])  # T1=0.7, T2=1.0
        >>> params = decode_hyperbolic_design(design, driver, num_segments=2)
        >>> params['T_params']
        [0.7, 1.0]
        >>> params['segment_types']
        ['HyperbolicHorn', 'HornSegment']  # T=1.0 can use exponential
    """
    if num_segments == 2:
        throat_area, middle_area, mouth_area, length1, length2, T1, T2, V_tc, V_rc = design

        # Build segment list with T parameters
        segments = [
            (throat_area, middle_area, length1, T1),  # Segment 1
            (middle_area, mouth_area, length2, T2),     # Segment 2
        ]
        T_params = [T1, T2]

    elif num_segments == 3:
        (throat_area, middle_area, area2, mouth_area,
         length1, length2, length3, T1, T2, T3, V_tc, V_rc) = design

        # Build segment list with T parameters
        segments = [
            (throat_area, middle_area, length1, T1),  # Segment 1
            (middle_area, area2, length2, T2),        # Segment 2
            (area2, mouth_area, length3, T3),         # Segment 3
        ]
        T_params = [T1, T2, T3]

    else:
        raise ValueError(f"num_segments must be 2 or 3, got {num_segments}")

    # Determine segment types based on T values
    # T ≈ 1.0 (within 1%) can use exponential HornSegment
    # T < 0.99 should use HyperbolicHorn
    segment_types = []
    for T in T_params:
        if abs(T - 1.0) < 0.01:
            segment_types.append("HornSegment")
        else:
            segment_types.append("HyperbolicHorn")

    return {
        'throat_area': throat_area,
        'mouth_area': mouth_area,
        'segments': segments,
        'V_tc': V_tc,
        'V_rc': V_rc,
        'T_params': T_params,
        'segment_types': segment_types,
        'total_length': sum(seg[2] for seg in segments),
    }


def detect_design_type(design: np.ndarray, num_segments: int = 2) -> str:
    """
    Detect whether design vector is for standard or hyperbolic horn.

    Args:
        design: Optimization array
        num_segments: Number of segments (2 or 3)

    Returns:
        "hyperbolic" if T parameters are present, "standard" otherwise

    Examples:
        >>> design = np.array([0.001, 0.01, 0.1, 0.3, 0.6, 0.7, 1.0, 0.0, 0.0])
        >>> detect_design_type(design, num_segments=2)
        'hyperbolic'
    """
    # Standard 2-segment: 7 elements [throat, middle, mouth, L1, L2, V_tc, V_rc]
    # Hyperbolic 2-segment: 9 elements [throat, middle, mouth, L1, L2, T1, T2, V_tc, V_rc]
    # Standard 3-segment: 9 elements [throat, middle, area2, mouth, L1, L2, L3, V_tc, V_rc]
    # Hyperbolic 3-segment: 12 elements [throat, middle, area2, mouth, L1, L2, L3, T1, T2, T3, V_tc, V_rc]

    expected_standard = 7 + (2 if num_segments == 3 else 0)
    expected_hyperbolic = expected_standard + num_segments

    if len(design) == expected_hyperbolic:
        return "hyperbolic"
    elif len(design) == expected_standard:
        return "standard"
    else:
        raise ValueError(
            f"Design vector length {len(design)} doesn't match expected "
            f"standard ({expected_standard}) or hyperbolic ({expected_hyperbolic}) "
            f"for {num_segments} segments"
        )


def build_multisegment_horn(
    design: np.ndarray,
    driver: ThieleSmallParameters,
    num_segments: int = 2
):
    """
    Build MultiSegmentHorn from design vector (standard or hyperbolic).

    This is a unified helper function that detects whether the design vector
    contains T parameters for hyperbolic horns, and builds the appropriate
    horn segments (HornSegment or HyperbolicHorn).

    Literature:
        - Salmon, V. (1946). "A New Family of Horns", JASA.
        - Kolbrek, B. (2008). "Horn Theory: An Introduction, Part 1".
        - literature/horns/kolbrek_horn_theory_tutorial.md

    Args:
        design: Optimization array
            - Standard 2-seg: [throat, middle, mouth, L1, L2, V_tc, V_rc]
            - Hyperbolic 2-seg: [throat, middle, mouth, L1, L2, T1, T2, V_tc, V_rc]
            - Standard 3-seg: adds [area2, L3]
            - Hyperbolic 3-seg: adds [area2, L3, T3]
        driver: ThieleSmallParameters (for context, not strictly needed)
        num_segments: Number of segments (2 or 3)

    Returns:
        MultiSegmentHorn instance with appropriate segment types

    Raises:
        ValueError: If design vector has invalid length

    Examples:
        >>> # Standard exponential horn
        >>> design_std = np.array([0.001, 0.01, 0.1, 0.3, 0.6, 0.0, 0.0])
        >>> horn = build_multisegment_horn(design_std, driver, num_segments=2)

        >>> # Hyperbolic horn (T1=0.7, T2=0.9)
        >>> design_hyp = np.array([0.001, 0.01, 0.1, 0.3, 0.6, 0.7, 0.9, 0.0, 0.0])
        >>> horn = build_multisegment_horn(design_hyp, driver, num_segments=2)
        >>> horn.segments[0]  # HyperbolicHorn(T=0.7)
        >>> horn.segments[1]  # HyperbolicHorn(T=0.9)
    """
    from gsd.simulation.types import HornSegment, HyperbolicHorn, MultiSegmentHorn

    design_type = detect_design_type(design, num_segments)

    if design_type == "hyperbolic":
        # Use hyperbolic decode
        params = decode_hyperbolic_design(design, driver, num_segments)

        # Build segments with appropriate types
        segments = []
        for seg_data, seg_type in zip(params['segments'], params['segment_types']):
            throat, mouth, length, T = seg_data

            if seg_type == "HyperbolicHorn":
                segments.append(HyperbolicHorn(throat, mouth, length, T=T))
            else:  # HornSegment (T ≈ 1.0)
                segments.append(HornSegment(throat, mouth, length))

        # Extract chamber volumes
        V_tc = params.get('V_tc', 0.0)
        V_rc = params.get('V_rc', 0.0)

    else:  # standard
        # Use standard decode
        params = decode_multisegment_design(design, driver, num_segments)

        # Build segments (all HornSegment for standard)
        segments = []
        for throat, mouth, length in params['segments']:
            segments.append(HornSegment(throat, mouth, length))

        # Extract chamber volumes
        V_tc = params.get('V_tc', 0.0)
        V_rc = params.get('V_rc', 0.0)

    # Create MultiSegmentHorn
    horn = MultiSegmentHorn(segments)

    return horn, V_tc, V_rc


def calculate_multisegment_horn_volume(
    throat_area: float,
    middle_area: float,
    mouth_area: float,
    length1: float,
    length2: float
) -> float:
    """
    Calculate total volume of 2-segment exponential horn.

    For each segment: V_segment = (S₂ - S₁) / m

    Literature:
        - Olson (1947), Chapter 5 - Horn geometry

    Args:
        throat_area: Horn throat area [m²]
        middle_area: Area at segment junction [m²]
        mouth_area: Horn mouth area [m²]
        length1: Segment 1 length [m]
        length2: Segment 2 length [m]

    Returns:
        Total horn volume [m³]

    Examples:
        >>> V = calculate_multisegment_horn_volume(
        ...     0.000212, 0.010, 0.04084, 0.20, 0.394
        ... )
        >>> print(f"{V*1000:.1f} liters")
    """
    # Segment 1 volume
    if length1 > 0 and middle_area > throat_area:
        m1 = np.log(middle_area / throat_area) / length1
        v1 = (middle_area - throat_area) / m1
    else:
        v1 = (throat_area + middle_area) / 2 * length1

    # Segment 2 volume
    if length2 > 0 and mouth_area > middle_area:
        m2 = np.log(mouth_area / middle_area) / length2
        v2 = (mouth_area - middle_area) / m2
    else:
        v2 = (middle_area + mouth_area) / 2 * length2

    return v1 + v2


def get_mixed_profile_parameter_space(
    driver: ThieleSmallParameters,
    preset: str = "midrange_horn",
    num_segments: int = 2,
    max_length: float = None,
    max_mouth_area: float = None,
    max_volume: float = None
) -> EnclosureParameterSpace:
    """
    Get parameter space for mixed-profile multi-segment horn optimization.

    This extends the standard multi-segment horn parameter space by allowing
    each segment to independently choose its profile type:
    - 0 = Exponential (HornSegment)
    - 1 = Conical (ConicalHorn)
    - 2 = Hyperbolic with T parameter (HyperbolicHorn)

    For a 2-segment mixed profile horn, optimizes 9-11 parameters:
    - throat_area, middle_area, mouth_area: Horn geometry
    - length1, length2: Segment lengths
    - profile_type1, profile_type2: Profile type for each segment (0=exp, 1=con, 2=hyp)
    - T1, T2: Shape parameters (only used if profile_type=2, else ignored)
    - V_tc, V_rc: Chamber volumes

    Literature:
        - Olson (1947), Chapter 8 - Compound horns with mixed profiles
        - Kolbrek Part 1 - T-matrix chaining for arbitrary segment types
        - literature/horns/kolbrek_horn_theory_tutorial.md

    Args:
        driver: ThieleSmallParameters for the driver
        preset: Design preset ("bass_horn", "midrange_horn", "fullrange_horn")
        num_segments: Number of horn segments (2 or 3)
        max_length: Optional maximum TOTAL horn length in meters (applied per segment)
        max_mouth_area: Optional maximum mouth area in m²
        max_volume: Optional maximum horn volume in m³ (not yet implemented)

    Returns:
        EnclosureParameterSpace: Parameter space definition with profile type selection

    Raises:
        ValueError: If preset or num_segments is not recognized

    Examples:
        >>> from gsd.driver import load_driver
        >>> param_space = get_mixed_profile_parameter_space(
        ...     driver, preset="midrange_horn", num_segments=2
        ... )
        >>> param_space.get_parameter_names()
        ['throat_area', 'middle_area', 'mouth_area', 'length1', 'length2',
         'profile_type1', 'profile_type2', 'T1', 'T2', 'V_tc', 'V_rc']
    """
    # Get base parameter space (without profile types or T params)
    base_space = get_multisegment_horn_parameter_space(
        driver, preset=preset, num_segments=num_segments,
        max_length=max_length, max_mouth_area=max_mouth_area, max_volume=max_volume
    )

    # Add profile type selection for each segment
    # 0 = exponential (HornSegment)
    # 1 = conical (ConicalHorn)
    # 2 = hyperbolic (HyperbolicHorn with T parameter)
    profile_type_parameters = [
        ParameterRange(
            name=f"profile_type{i+1}",
            min_value=0,
            max_value=2,
            units="",
            description=f"Profile type for segment {i+1} (0=exponential, 1=conical, 2=hyperbolic)"
        )
        for i in range(num_segments)
    ]

    # Add T parameters for potential hyperbolic segments
    t_parameters = [
        ParameterRange(
            name=f"T{i+1}",
            min_value=0.5,
            max_value=1.0,
            units="",
            description=f"Shape parameter T for segment {i+1} (used only if profile_type={i+1}=2)"
        )
        for i in range(num_segments)
    ]

    # Find V_tc index and insert profile_type and T parameters before it
    base_params = base_space.parameters.copy()
    vtc_idx = next(i for i, p in enumerate(base_params) if p.name == "V_tc")

    # Insert parameters before V_tc: profile_type1, profile_type2, ..., T1, T2, ...
    new_parameters = base_params[:vtc_idx] + profile_type_parameters + t_parameters + base_params[vtc_idx:]

    # Update typical ranges to include new parameters
    typical_ranges = base_space.typical_ranges.copy()
    for preset_name in typical_ranges:
        for i in range(num_segments):
            typical_ranges[preset_name][f"profile_type{i+1}"] = (0, 0)  # Default to exponential
            typical_ranges[preset_name][f"T{i+1}"] = (0.9, 1.0)  # Default T range

    return EnclosureParameterSpace(
        enclosure_type="multisegment_horn_mixed_profile",
        parameters=new_parameters,
        typical_ranges=typical_ranges,
        constraints=base_space.constraints,
    )


def decode_mixed_profile_design(
    design: np.ndarray,
    driver: ThieleSmallParameters,
    num_segments: int = 2
) -> dict:
    """
    Decode optimization array into mixed-profile multi-segment horn parameters.

    Converts the flat optimization array into a structured dictionary
    with horn geometry parameters including profile type selection for
    building a MultiSegmentHorn with mixed segment types.

    Args:
        design: Optimization array
            For 2-segment: [throat_area, middle_area, mouth_area,
                           length1, length2, profile_type1, profile_type2,
                           T1, T2, V_tc, V_rc]
            For 3-segment: adds [area2, length3, profile_type3, T3] before V_tc
        driver: ThieleSmallParameters for the driver
        num_segments: Number of segments (2 or 3)

    Returns:
        Dictionary with horn parameters:
        - throat_area, mouth_area: Overall horn dimensions
        - segments: List of segment specification tuples
        - V_tc, V_rc: Chamber volumes
        - profile_types: List of profile type codes for each segment
        - T_params: List of T values (only used for hyperbolic segments)
        - segment_classes: List of class names for each segment

    Examples:
        >>> # Mixed horn: segment 1 exponential, segment 2 conical
        >>> design = np.array([0.001, 0.01, 0.1, 0.3, 0.6, 0, 1, 0.7, 1.0, 0.0, 0.0])
        >>> params = decode_mixed_profile_design(design, driver, num_segments=2)
        >>> params['profile_types']
        [0, 1]  # [exponential, conical]
        >>> params['segment_classes']
        ['HornSegment', 'ConicalHorn']
    """
    if num_segments == 2:
        (throat_area, middle_area, mouth_area, length1, length2,
         profile_type1, profile_type2, T1, T2, V_tc, V_rc) = design

        # Build segment specification list
        segments = [
            (throat_area, middle_area, length1, profile_type1, T1),
            (middle_area, mouth_area, length2, profile_type2, T2),
        ]
        profile_types = [int(profile_type1), int(profile_type2)]
        T_params = [T1, T2]

    elif num_segments == 3:
        (throat_area, middle_area, area2, mouth_area,
         length1, length2, length3, profile_type1, profile_type2, profile_type3,
         T1, T2, T3, V_tc, V_rc) = design

        # Build segment specification list
        segments = [
            (throat_area, middle_area, length1, profile_type1, T1),
            (middle_area, area2, length2, profile_type2, T2),
            (area2, mouth_area, length3, profile_type3, T3),
        ]
        profile_types = [int(profile_type1), int(profile_type2), int(profile_type3)]
        T_params = [T1, T2, T3]

    else:
        raise ValueError(f"num_segments must be 2 or 3, got {num_segments}")

    # Map profile type codes to class names
    # 0 = HornSegment (exponential)
    # 1 = ConicalHorn
    # 2 = HyperbolicHorn
    type_to_class = {
        0: "HornSegment",
        1: "ConicalHorn",
        2: "HyperbolicHorn",
    }

    segment_classes = [type_to_class.get(pt, "HornSegment") for pt in profile_types]

    return {
        'throat_area': throat_area,
        'mouth_area': mouth_area,
        'segments': segments,
        'V_tc': V_tc,
        'V_rc': V_rc,
        'profile_types': profile_types,
        'T_params': T_params,
        'segment_classes': segment_classes,
        'total_length': sum(seg[2] for seg in segments),
    }


def build_mixed_profile_horn(
    design: np.ndarray,
    driver: ThieleSmallParameters,
    num_segments: int = 2
):
    """
    Build MultiSegmentHorn from mixed-profile design vector.

    This function creates a multi-segment horn where each segment can be
    independently chosen as exponential, conical, or hyperbolic.

    Literature:
        - Olson (1947), Chapter 8 - Compound horns
        - Kolbrek, "Horn Theory: An Introduction, Part 1"
        - literature/horns/kolbrek_horn_theory_tutorial.md

    Args:
        design: Optimization array
            - 2-segment: [throat, middle, mouth, L1, L2, ptype1, ptype2, T1, T2, V_tc, V_rc]
            - 3-segment: adds [area2, L3, ptype3, T3]
        driver: ThieleSmallParameters (for context)
        num_segments: Number of segments (2 or 3)

    Returns:
        Tuple of (MultiSegmentHorn instance, V_tc, V_rc)

    Raises:
        ValueError: If design vector has invalid length or profile type

    Examples:
        >>> # Conical throat, exponential mouth
        >>> design = np.array([0.001, 0.01, 0.1, 0.3, 0.6, 1, 0, 1.0, 0.7, 0.0, 0.0])
        >>> horn, V_tc, V_rc = build_mixed_profile_horn(design, driver, num_segments=2)
        >>> type(horn.segments[0]).__name__
        'ConicalHorn'
        >>> type(horn.segments[1]).__name__
        'HornSegment'
    """
    from gsd.simulation.types import HornSegment, ConicalHorn, HyperbolicHorn, MultiSegmentHorn

    # Decode design
    params = decode_mixed_profile_design(design, driver, num_segments)

    # Build segments with appropriate types
    segments = []
    for seg_spec in params['segments']:
        throat, mouth, length, profile_type, T = seg_spec
        profile_type = int(profile_type)

        if profile_type == 0:
            # Exponential
            segments.append(HornSegment(throat, mouth, length))
        elif profile_type == 1:
            # Conical
            segments.append(ConicalHorn(throat, mouth, length))
        elif profile_type == 2:
            # Hyperbolic
            segments.append(HyperbolicHorn(throat, mouth, length, T=T))
        else:
            raise ValueError(
                f"Unknown profile type {profile_type} for segment "
                f"(throat={throat}, mouth={mouth}). "
                f"Valid types: 0=exponential, 1=conical, 2=hyperbolic"
            )

    # Create MultiSegmentHorn
    horn = MultiSegmentHorn(segments)

    return horn, params['V_tc'], params['V_rc']
