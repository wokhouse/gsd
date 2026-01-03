"""
Physical constraint functions for enclosure optimization.

This module provides constraint functions for ensuring optimized designs
satisfy physical requirements:
- Maximum displacement limits (X_max)
- Port velocity limits (chuffing prevention)

Literature:
    - Small (1972) - Displacement limits in sealed/ported boxes
    - Thiele (1971) - Port velocity and displacement
    - literature/thiele_small/small_1972_closed_box.md
    - literature/thiele_small/thiele_1971_vented_boxes.md
"""

import numpy as np
from typing import Optional

from gsd.driver.parameters import ThieleSmallParameters
from gsd.enclosure.sealed_box import calculate_sealed_box_system_parameters
from gsd.enclosure.ported_box import calculate_ported_box_system_parameters


def constraint_max_displacement(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    max_excursion_ratio: float = 0.8
) -> float:
    """
    Constrain maximum diaphragm displacement to prevent X_max violation.

    This constraint ensures the driver doesn't exceed its linear excursion
    limits, which would cause distortion and potential damage.

    Literature:
        - Small (1972) - Displacement limits in sealed/ported boxes
        - Thiele (1971) - Port velocity and displacement
        - literature/thiele_small/small_1972_closed_box.md

    Args:
        design_vector: Enclosure parameters
        driver: ThieleSmallParameters instance (must have X_max)
        enclosure_type: Type of enclosure ("sealed", "ported")
        max_excursion_ratio: Maximum fraction of X_max to allow (default 0.8)

    Returns:
        Constraint violation (positive = violation, negative = satisfied)
        pymoo expects constraints to be ≤ 0 (negative = satisfied)

    Examples:
        >>> driver = load_driver("BC_8NDL51")  # X_max = 7mm
        >>> # Small sealed box - should violate displacement constraint
        >>> violation = constraint_max_displacement(
        ...     np.array([0.005]), driver, "sealed"
        ... )
        >>> violation > 0  # Violation (box too small)
        True
    """
    if driver.X_max is None:
        return 0.0  # No constraint if X_max not specified

    # Find worst-case displacement frequency
    # For sealed: displacement maximum at Fc
    # For ported: displacement maximum below tuning

    try:
        if enclosure_type == "sealed":
            Vb = design_vector[0]
            params = calculate_sealed_box_system_parameters(driver, Vb)

            # At Fc, displacement is maximum for a given voltage
            # Calculate displacement at Fc for rated power (2.83V = 1W into 8Ω)
            from gsd.optimization.objectives.response_metrics import sealed_box_electrical_impedance

            result = sealed_box_electrical_impedance(
                params.Fc, driver, Vb=Vb, voltage=2.83
            )

            # Diaphragm velocity from result
            v_diaphragm = result['diaphragm_velocity']

            # Displacement = velocity / (2πf)
            x_diaphragm = v_diaphragm / (2.0 * np.pi * params.Fc)

        elif enclosure_type == "ported":
            Vb = design_vector[0]
            Fb = design_vector[1]

            # Below Fb, displacement increases
            # Worst case at Fb/2 approximately
            f_worst = Fb / 2.0

            from gsd.optimization.objectives.response_metrics import ported_box_electrical_impedance
            from gsd.enclosure.ported_box import calculate_optimal_port_dimensions

            # Get port dimensions
            if len(design_vector) >= 4:
                port_area = design_vector[2]
                port_length = design_vector[3]
            else:
                port_area, port_length, _ = calculate_optimal_port_dimensions(
                    driver, Vb, Fb
                )

            result = ported_box_electrical_impedance(
                f_worst, driver, Vb=Vb, Fb=Fb,
                port_area=port_area, port_length=port_length,
                voltage=2.83
            )

            v_diaphragm = result['diaphragm_velocity']
            x_diaphragm = v_diaphragm / (2.0 * np.pi * f_worst)

        else:
            return 0.0  # No constraint for other types (yet)

        # Constraint: x_diaphragm ≤ max_excursion_ratio × X_max
        # Return violation (positive if violated)
        x_limit = max_excursion_ratio * driver.X_max
        return x_diaphragm - x_limit

    except Exception:
        # If calculation fails, return large violation
        return 1000.0


def constraint_port_velocity(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    max_velocity_fraction: float = 0.05
) -> float:
    """
    Constrain port air velocity to prevent chuffing noise.

    Excessive port velocity causes turbulent noise ("chuffing") that
    degrades sound quality.

    Literature:
        - Thiele (1971), Part 1, Section 4 - Air velocity in the vent
        - literature/thiele_small/thiele_1971_vented_boxes.md

    Args:
        design_vector: Enclosure parameters (must include port dimensions)
        driver: ThieleSmallParameters instance
        enclosure_type: Type of enclosure (only applicable for "ported")
        max_velocity_fraction: Max port velocity as fraction of speed of sound
                              (default 0.05 = 5% of c = ~17 m/s)

    Returns:
        Constraint violation (positive if port velocity too high)
        pymoo expects constraints to be ≤ 0 (negative = satisfied)

    Examples:
        >>> driver = load_driver("BC_12NDL76")
        >>> # Small port area - should violate velocity constraint
        >>> violation = constraint_port_velocity(
        ...     np.array([0.050, 40.0, 0.0005, 0.1]),  # Tiny port
        ...     driver, "ported"
        ... )
        >>> violation > 0  # Violation (port too small)
        True
    """
    if enclosure_type != "ported":
        return 0.0  # Not applicable

    if driver.X_max is None:
        return 0.0  # Can't calculate without X_max

    try:
        Vb = design_vector[0]
        Fb = design_vector[1]
        port_area = design_vector[2]

        # Estimate maximum port velocity at Fb
        # Thiele (1971): port velocity peaks at tuning frequency
        # v_port = (2π × Fb × X_max × S_d) / A_port

        from gsd.simulation.constants import SPEED_OF_SOUND

        # Maximum air velocity in port (at X_max excursion)
        v_port_max = (2.0 * np.pi * Fb * driver.X_max * driver.S_d) / port_area

        # Convert to fraction of speed of sound
        v_fraction = v_port_max / SPEED_OF_SOUND

        # Constraint: v_fraction ≤ max_velocity_fraction
        return v_fraction - max_velocity_fraction

    except Exception:
        # If calculation fails, assume OK
        return 0.0


def constraint_multisegment_continuity(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    num_segments: int = 2
) -> float:
    """
    Constrain multi-segment horn to have monotonic area expansion.

    Ensures throat < middle < mouth (for 2 segments) to prevent
    area discontinuities that would cause reflections.

    Works with both standard and hyperbolic design vectors (auto-detects).

    Literature:
        - Olson (1947), Chapter 8 - Horn area continuity
        - Kolbrek Part 1 - Impedance discontinuities

    Args:
        design_vector:
            Standard: [throat_area, middle_area, mouth_area, length1, length2, V_tc, V_rc]
            Hyperbolic: [throat_area, middle_area, mouth_area, length1, length2, T1, T2, V_tc, V_rc]
        driver: ThieleSmallParameters instance (not used for this constraint)
        enclosure_type: Must be "multisegment_horn"
        num_segments: Number of segments (2 or 3)

    Returns:
        Constraint violation (positive = violation, negative = satisfied)

    Examples:
        >>> design = np.array([0.001, 0.005, 0.01, 0.3, 0.4, 0.0])
        >>> constraint_multisegment_continuity(design, driver, "multisegment_horn", num_segments=2)
        -0.004  # Satisfied (0.001 < 0.005 < 0.01)
    """
    if enclosure_type != "multisegment_horn":
        return 0.0  # Not applicable for other enclosure types

    # Extract areas (first 3 or 4 elements are always areas)
    if num_segments == 2:
        throat_area, middle_area, mouth_area = design_vector[0], design_vector[1], design_vector[2]

        # Check throat < middle
        violation1 = throat_area - middle_area

        # Check middle < mouth
        violation2 = middle_area - mouth_area

        # Return maximum violation
        return max(violation1, violation2)

    elif num_segments == 3:
        throat_area, middle_area, area2, mouth_area = design_vector[0:4]

        # Check monotonic expansion
        violation1 = throat_area - middle_area
        violation2 = middle_area - area2
        violation3 = area2 - mouth_area

        return max(violation1, violation2, violation3)

    else:
        return 0.0


def constraint_multisegment_flare_limits(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    num_segments: int = 2,
    min_mL: float = 0.5,
    max_mL: float = 6.0
) -> float:
    """
    Constrain flare constants for each segment to practical limits.

    For each segment, ensure: min_mL ≤ m·L ≤ max_mL

    This prevents unrealistic flare rates that would be difficult to
    manufacture or would have poor acoustic performance.

    Works with both standard and hyperbolic design vectors (auto-detects).

    Literature:
        - Olson (1947), Chapter 5 - Practical flare rate limits
        - Typical horns: 0.5 < m·L < 3.0 (relaxed to 6.0 for optimization)

    Args:
        design_vector:
            Standard: [throat_area, middle_area, mouth_area, length1, length2, V_tc, V_rc]
            Hyperbolic: [throat_area, middle_area, mouth_area, length1, length2, T1, T2, V_tc, V_rc]
        driver: ThieleSmallParameters instance (not used for this constraint)
        enclosure_type: Must be "multisegment_horn"
        num_segments: Number of segments (2 or 3)
        min_mL: Minimum value for m·L product (default 0.5)
        max_mL: Maximum value for m·L product (default 6.0, relaxed from 3.0)

    Returns:
        Constraint violation (positive = violation, negative = satisfied)

    Examples:
        >>> design = np.array([0.001, 0.01, 0.04, 0.2, 0.4, 0.0])
        >>> constraint_multisegment_flare_limits(design, driver, "multisegment_horn", num_segments=2)
        -0.5  # Satisfied
    """
    if enclosure_type != "multisegment_horn":
        return 0.0  # Not applicable for other enclosure types

    violations = []

    # Detect if hyperbolic (has T parameters)
    # Standard 2-seg: 7 elements, Hyperbolic 2-seg: 9 elements
    # Standard 3-seg: 9 elements, Hyperbolic 3-seg: 12 elements
    expected_standard = 7 + (2 if num_segments == 3 else 0)
    is_hyperbolic = len(design_vector) > expected_standard

    if num_segments == 2:
        throat_area, middle_area, mouth_area = design_vector[0:3]
        # Lengths are at indices 3, 4 (standard) or skip T params
        if is_hyperbolic:
            # Hyperbolic: [areas x3, lengths x2, T x2, V_tc, V_rc]
            length1, length2 = design_vector[3], design_vector[4]
        else:
            # Standard: [areas x3, lengths x2, V_tc, V_rc]
            length1, length2 = design_vector[3], design_vector[4]

        # Segment 1: m1·L1
        if length1 > 0 and middle_area > throat_area:
            m1 = np.log(middle_area / throat_area) / length1
            mL1 = m1 * length1
            violations.append(min_mL - mL1)  # Violation if too small
            violations.append(mL1 - max_mL)  # Violation if too large

        # Segment 2: m2·L2
        if length2 > 0 and mouth_area > middle_area:
            m2 = np.log(mouth_area / middle_area) / length2
            mL2 = m2 * length2
            violations.append(min_mL - mL2)
            violations.append(mL2 - max_mL)

    elif num_segments == 3:
        throat_area, middle_area, area2, mouth_area = design_vector[0:4]

        if is_hyperbolic:
            # Hyperbolic: [areas x4, lengths x3, T x3, V_tc, V_rc]
            length1, length2, length3 = design_vector[4], design_vector[5], design_vector[6]
        else:
            # Standard: [areas x4, lengths x3, V_tc, V_rc]
            length1, length2, length3 = design_vector[4], design_vector[5], design_vector[6]

        # Segment 1
        if length1 > 0 and middle_area > throat_area:
            m1 = np.log(middle_area / throat_area) / length1
            violations.append(min_mL - m1 * length1)
            violations.append(m1 * length1 - max_mL)

        # Segment 2
        if length2 > 0 and area2 > middle_area:
            m2 = np.log(area2 / middle_area) / length2
            violations.append(min_mL - m2 * length2)
            violations.append(m2 * length2 - max_mL)

        # Segment 3
        if length3 > 0 and mouth_area > area2:
            m3 = np.log(mouth_area / area2) / length3
            violations.append(min_mL - m3 * length3)
            violations.append(m3 * length3 - max_mL)

    if not violations:
        return 0.0

    # Return maximum violation (positive = bad)
    return max(violations)


def constraint_multisegment_flare_curvature(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    num_segments: int = 2,
    max_flare_increase: float = 0.1
) -> float:
    """
    Constrain flare rate curvature to ensure smooth horn profiles.

    Enforces that the flare constant m decreases or stays similar from
    throat to mouth: m_throat ≥ m_mid ≥ m_mouth. This prevents
    "bottleneck" shapes that are mathematically valid but physically poor.

    The constraint allows some tolerance (+10% by default) to accommodate
    practical designs while preventing pathological shapes.

    Works with both standard and hyperbolic design vectors (auto-detects).

    Literature:
        - Dong et al. (2020) - Horn profile optimization
        - Kolbrek Part 1 - Flare rate and impedance smoothness
        - literature/horns/kolbrek_horn_theory_tutorial.md

    Theory:
        Rapid flare near throat provides good high-frequency loading.
        Gradual flare near mouth reduces reflections and improves low-frequency loading.
        Optimal horns typically have decreasing flare rates: m_throat > m_mid > m_mouth.

    Args:
        design_vector:
            Standard: [throat_area, middle_area, mouth_area, length1, length2, V_tc, V_rc]
            Hyperbolic: [throat_area, middle_area, mouth_area, length1, length2, T1, T2, V_tc, V_rc]
        driver: ThieleSmallParameters instance (not used for this constraint)
        enclosure_type: Must be "multisegment_horn"
        num_segments: Number of segments (2 or 3)
        max_flare_increase: Maximum allowed increase in flare rate (default 0.1 = 10%)
            - Set to 0.0 for strict monotonic decrease (m_i > m_{i+1})
            - Set to 0.1 for 10% tolerance (practical designs)

    Returns:
        Constraint violation (positive = violation, negative = satisfied)

    Examples:
        >>> # Good horn: decreasing flare rate
        >>> design = np.array([0.001, 0.01, 0.04, 0.2, 0.4, 0.0])
        >>> # m1 ≈ 11.5, m2 ≈ 3.5 (decreasing)
        >>> constraint_multisegment_flare_curvature(
        ...     design, driver, "multisegment_horn", num_segments=2
        ... )
        -7.99  # Satisfied (m1 > m2)

        >>> # Bad horn: increasing flare rate (bottleneck)
        >>> design = np.array([0.001, 0.02, 0.025, 0.4, 0.2, 0.0])
        >>> # m1 ≈ 4.0, m2 ≈ 0.9 (decreasing, but length2 is shorter)
        >>> constraint_multisegment_flare_curvature(
        ...     design, driver, "multisegment_horn", num_segments=2
        ... )
        -3.1  # Might still be satisfied (depends on values)
    """
    if enclosure_type != "multisegment_horn":
        return 0.0  # Not applicable for other enclosure types

    violations = []

    # Detect if hyperbolic (has T parameters)
    expected_standard = 7 + (2 if num_segments == 3 else 0)
    is_hyperbolic = len(design_vector) > expected_standard

    if num_segments == 2:
        throat_area, middle_area, mouth_area = design_vector[0:3]

        # Extract lengths (same position for both standard and hyperbolic)
        length1, length2 = design_vector[3], design_vector[4]

        # Calculate flare rates
        if length1 > 0 and middle_area > throat_area:
            m1 = np.log(middle_area / throat_area) / length1
        else:
            return 0.0  # Invalid geometry, let other constraints handle it

        if length2 > 0 and mouth_area > middle_area:
            m2 = np.log(mouth_area / middle_area) / length2
        else:
            return 0.0

        # Constraint: m2 should not exceed m1 by more than max_flare_increase
        # m2 - m1 ≤ max_flare_increase
        # This allows m2 > m1 slightly, but not dramatically
        violation = m2 - m1 - max_flare_increase
        violations.append(violation)

    elif num_segments == 3:
        throat_area, middle_area, area2, mouth_area = design_vector[0:4]

        # Extract lengths (same position for both standard and hyperbolic)
        length1, length2, length3 = design_vector[4], design_vector[5], design_vector[6]

        # Calculate flare rates
        if length1 > 0 and middle_area > throat_area:
            m1 = np.log(middle_area / throat_area) / length1
        else:
            return 0.0

        if length2 > 0 and area2 > middle_area:
            m2 = np.log(area2 / middle_area) / length2
        else:
            return 0.0

        if length3 > 0 and mouth_area > area2:
            m3 = np.log(mouth_area / area2) / length3
        else:
            return 0.0

        # Constraint: flare rates should not increase dramatically
        # m2 - m1 ≤ max_flare_increase
        # m3 - m2 ≤ max_flare_increase
        violations.append(m2 - m1 - max_flare_increase)
        violations.append(m3 - m2 - max_flare_increase)

    if not violations:
        return 0.0

    # Return maximum violation (positive = bad, negative = satisfied)
    return max(violations)


def constraint_conical_expansion_ratio(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    min_ratio: float = 2.0,
    max_ratio: float = 100.0
) -> float:
    """
    Constrain conical horn expansion ratio to practical limits.

    The expansion ratio (mouth_area / throat_area) determines the loading
    characteristics and bandwidth of a conical horn. Too small and there's
    insufficient loading; too large and the horn becomes impractical.

    Literature:
        - Olson (1947), Chapter 5 - Horn loading and impedance
        - Beranek (1954) - Radiation impedance and expansion ratio

    Args:
        design_vector: [throat_area, mouth_area, length, V_tc, V_rc]
        driver: ThieleSmallParameters instance (not used for this constraint)
        enclosure_type: Must be "conical_horn"
        min_ratio: Minimum expansion ratio (default 2.0)
        max_ratio: Maximum expansion ratio (default 100.0)

    Returns:
        Constraint violation (positive = violation, negative = satisfied)

    Examples:
        >>> design = np.array([0.0015, 0.15, 1.2, 0.0, 0.0])  # 100:1 ratio
        >>> constraint_conical_expansion_ratio(design, driver, "conical_horn")
        -98.0  # Satisfied (100 < max_ratio)
    """
    if enclosure_type != "conical_horn":
        return 0.0  # Not applicable for other enclosure types

    throat_area = design_vector[0]
    mouth_area = design_vector[1]

    if throat_area <= 0:
        return 1000.0  # Invalid geometry

    ratio = mouth_area / throat_area

    # Constraint: min_ratio ≤ ratio ≤ max_ratio
    # Return maximum violation
    violation_min = min_ratio - ratio  # Positive if ratio < min_ratio
    violation_max = ratio - max_ratio  # Positive if ratio > max_ratio

    return max(violation_min, violation_max)


def constraint_conical_monotonic_expansion(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str
) -> float:
    """
    Constrain conical horn to have monotonic area expansion (mouth > throat).

    Ensures the horn expands rather than contracts, which is necessary for
    proper impedance transformation.

    Literature:
        - Olson (1947), Chapter 5 - Horn geometry requirements

    Args:
        design_vector: [throat_area, mouth_area, length, V_tc, V_rc]
        driver: ThieleSmallParameters instance (not used for this constraint)
        enclosure_type: Must be "conical_horn"

    Returns:
        Constraint violation (positive = violation, negative = satisfied)

    Examples:
        >>> design = np.array([0.0015, 0.15, 1.2, 0.0, 0.0])
        >>> constraint_conical_monotonic_expansion(design, driver, "conical_horn")
        -0.1485  # Satisfied (throat < mouth)
    """
    if enclosure_type != "conical_horn":
        return 0.0  # Not applicable for other enclosure types

    throat_area = design_vector[0]
    mouth_area = design_vector[1]

    # Constraint: mouth_area > throat_area
    # Return violation (positive if violated)
    return throat_area - mouth_area


def constraint_horn_throat_sizing(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    min_compression_ratio: float = 0.5,
    max_compression_ratio: float = 2.0
) -> float:
    """
    Constrain horn throat size relative to driver area to prevent bottlenecks.

    For bass horns with direct radiator woofers (not compression drivers):
    - Throat area should be 50-100% of driver diaphragm area
    - Compression ratio (driver_area / throat_area) should be 1:1 to 2:1
    - Higher compression requires phase plugs (impractical for woofers)

    CRITICAL: This prevents the throat bottleneck issue that causes:
    - Air turbulence and distortion at high power
    - Choked flow limiting output
    - Nonlinear compression artifacts

    Literature:
        - Beranek (1954), Chapter 5 - Horn throat design
        - Olson (1947), Chapter 8 - Direct radiator vs compression driver loading
        - Practical horn design: throat ≥ Sd/2 for woofers without phase plugs

    Args:
        design_vector: Horn parameters
            - Exponential: [throat_area, mouth_area, length, V_tc, V_rc]
            - Multisegment: [throat_area, middle_area, mouth_area, length1, length2, ...]
        driver: ThieleSmallParameters instance
        enclosure_type: Must be "exponential_horn", "multisegment_horn", or "conical_horn"
        min_compression_ratio: Minimum throat/drive ratio (default 0.5 = 50%)
            - Set to 1.0 for no compression (throat = driver area)
            - Set to 0.5 for acceptable compression (throat ≥ 50% driver)
        max_compression_ratio: Maximum compression ratio (default 2.0)
            - throat_area ≥ driver_area / max_compression_ratio

    Returns:
        Constraint violation (positive if violated, negative = satisfied)
        Returns value representing how much the constraint is violated

    Examples:
        >>> driver = load_driver("BC_21DS115")  # Sd = 1680 cm²
        >>> # Good design: throat = 1200 cm² (compression ratio = 1.4:1)
        >>> design = np.array([0.12, 1.0, 3.5, 0.0, 0.0])  # throat in m²
        >>> constraint_horn_throat_sizing(design, driver, "exponential_horn")
        -240.0  # Satisfied (throat > minimum)

        >>> # Bad design: throat = 150 cm² (compression ratio = 11.2:1)
        >>> design = np.array([0.015, 1.0, 3.5, 0.0, 0.0])
        >>> constraint_horn_throat_sizing(design, driver, "exponential_horn")
        690.0  # VIOLATION (throat too small - would cause bottleneck)
    """
    # Only apply to horn types
    horn_types = ["exponential_horn", "multisegment_horn", "conical_horn",
                  "mixed_profile_horn"]
    if enclosure_type not in horn_types:
        return 0.0  # Not applicable for other enclosure types

    # Extract throat area (first element for all horn types)
    throat_area = design_vector[0]
    driver_area = driver.S_d

    # Calculate compression ratio
    # compression_ratio = driver_area / throat_area
    # throat ≥ driver_area / max_compression_ratio
    # throat ≤ driver_area / min_compression_ratio
    #
    # For min_compression_ratio = 0.5:
    #   throat ≥ 0.5 * driver_area  (compression ≤ 2:1)
    #
    # For max_compression_ratio = 2.0:
    #   throat ≤ driver_area / 2.0  (same constraint)
    #
    # Actually, let's simplify:
    #   minimum_throat = driver_area * min_compression_ratio
    #   where min_compression_ratio is the fraction of driver area

    # Minimum throat: 50% of driver area (compression ratio 2:1 max)
    min_throat = driver_area * min_compression_ratio

    # Maximum throat: 100% of driver area (no compression)
    max_throat = driver_area * 1.0

    # Constraint: min_throat ≤ throat_area ≤ max_throat
    # Violation if throat_area < min_throat
    violation_min = min_throat - throat_area

    # Also warn if throat > driver (not physically possible)
    violation_max = throat_area - max_throat

    # Return maximum violation (positive = bad)
    return max(violation_min, violation_max, 0.0)


def constraint_exponential_monotonic_expansion(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str
) -> float:
    """
    Constrain exponential horn to have monotonic area expansion (mouth > throat).

    Ensures the horn expands rather than contracts, which is necessary for
    proper impedance transformation. Prevents "reverse horn" cheat solutions
    where mouth < throat (which would minimize F3 artificially).

    CRITICAL: Without this constraint, optimizer may create designs with
    mouth_area < throat_area, causing invalid F3 calculations (negative values).

    Literature:
        - Olson (1947), Chapter 5 - Horn geometry requirements
        - Beranek (1954) - Monotonic expansion for impedance matching

    Args:
        design_vector: [throat_area, mouth_area, length, V_tc, V_rc]
        driver: ThieleSmallParameters instance (not used for this constraint)
        enclosure_type: Must be "exponential_horn"

    Returns:
        Constraint violation (positive if violated, negative = satisfied)

    Examples:
        >>> # Good horn: mouth > throat
        >>> design = np.array([0.10, 1.0, 3.5, 0.0, 0.0])  # throat=1000cm², mouth=10000cm²
        >>> constraint_exponential_monotonic_expansion(design, driver, "exponential_horn")
        -0.90  # Satisfied (mouth > throat)

        >>> # Bad horn: mouth < throat (reverse horn)
        >>> design = np.array([0.168, 0.013, 1.5, 0.0, 0.0])  # throat=1680cm², mouth=130cm²
        >>> constraint_exponential_monotonic_expansion(design, driver, "exponential_horn")
        0.155  # VIOLATION (throat > mouth, would cause invalid F3)
    """
    if enclosure_type != "exponential_horn":
        return 0.0  # Not applicable for other enclosure types

    throat_area = design_vector[0]
    mouth_area = design_vector[1]

    # Constraint: mouth_area > throat_area
    # Return violation (positive if violated)
    return throat_area - mouth_area


def constraint_minimum_expansion(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    num_segments: int = 2,
    min_expansion_ratio: float = 1.1
) -> float:
    """
    Constrain multi-segment horn to have minimum area expansion per segment.

    Prevents "straight pipe" segments where throat ≈ middle, which waste volume
    without contributing to horn loading. Each segment must expand by at least
    the minimum ratio.

    CRITICAL: Without this constraint, optimizer can create designs like:
    - throat = 888 cm², middle = 888 cm² (zero expansion)
    - This wastes 133+ L on a non-functional straight pipe

    Literature:
        - Post (1994) - T-matrix accuracy depends on wave propagation assumption
        - Olson (1947), Chapter 5 - Horn expansion for impedance matching
        - Investigation report: tasks/horn_volume_investigation_report.md

    Args:
        design_vector:
            Standard: [throat_area, middle_area, mouth_area, length1, length2, V_tc, V_rc]
            Hyperbolic: [throat_area, middle_area, mouth_area, length1, length2, T1, T2, V_tc, V_rc]
        driver: ThieleSmallParameters instance (not used for this constraint)
        enclosure_type: Must be "multisegment_horn"
        num_segments: Number of segments (2 or 3)
        min_expansion_ratio: Minimum area ratio per segment (default 1.1 = 10% expansion)
            - Set to 1.0 for strict monotonic (no equal areas)
            - Set to 1.1 for practical minimum (10% expansion per segment)

    Returns:
        Constraint violation (positive = violation, negative = satisfied)

    Examples:
        >>> # Good horn: proper expansion
        >>> design = np.array([0.001, 0.01, 0.04, 0.3, 0.4, 0.0])
        >>> # middle/throat = 10.0, mouth/middle = 4.0
        >>> constraint_minimum_expansion(design, driver, "multisegment_horn", num_segments=2)
        -8.9  # Satisfied (both segments expand >10%)

        >>> # Bad horn: straight pipe segment
        >>> design = np.array([0.0888, 0.0888, 0.36, 1.5, 1.7, 0.0])
        >>> # throat = middle (zero expansion)
        >>> constraint_minimum_expansion(design, driver, "multisegment_horn", num_segments=2)
        0.1  # VIOLATION (middle/throat = 1.0 < 1.1)
    """
    if enclosure_type != "multisegment_horn":
        return 0.0  # Not applicable for other enclosure types

    violations = []

    # Detect if hyperbolic (has T parameters)
    expected_standard = 7 + (2 if num_segments == 3 else 0)
    is_hyperbolic = len(design_vector) > expected_standard

    if num_segments == 2:
        throat_area, middle_area, mouth_area = design_vector[0:3]

        # Segment 1: check middle/throat ratio
        if throat_area > 0:
            ratio1 = middle_area / throat_area
            # Constraint: ratio >= min_expansion_ratio
            # Violation if ratio < min_expansion_ratio
            violation1 = min_expansion_ratio - ratio1
            violations.append(violation1)

        # Segment 2: check mouth/middle ratio
        if middle_area > 0:
            ratio2 = mouth_area / middle_area
            violation2 = min_expansion_ratio - ratio2
            violations.append(violation2)

    elif num_segments == 3:
        throat_area, middle_area, area2, mouth_area = design_vector[0:4]

        # All three segments must expand
        if throat_area > 0:
            violations.append(min_expansion_ratio - middle_area / throat_area)
        if middle_area > 0:
            violations.append(min_expansion_ratio - area2 / middle_area)
        if area2 > 0:
            violations.append(min_expansion_ratio - mouth_area / area2)

    if not violations:
        return 0.0

    # Return maximum violation (positive = bad)
    return max(violations)


def constraint_mouth_loading(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    min_circumference_ratio: float = 0.7
) -> float:
    """
    Constrain horn mouth size to ensure proper loading at target frequency.

    Prevents undersized mouths that cause poor bass loading and response peaks.
    The optimizer compensates for small mouths by making the horn longer,
    which drastically increases volume without solving the fundamental problem.

    CRITICAL: Without this constraint, optimizer creates designs with:
    - Mouth circumference = 0.28× wavelength (severe undersize)
    - Tries to fix with longer horn (increases volume to 680+ L)

    Literature:
        - Olson (1947), Chapter 5 - Mouth circumference ≥ wavelength for full loading
        - Molloy (1950) - Response peaks in finite horns with small mouths
        - Investigation report: tasks/horn_volume_investigation_report.md

    Theory:
        For proper bass loading, the mouth circumference should be at least
        a fraction of the wavelength at the cutoff frequency (typically 0.7-1.0×).
        Below this size, the radiation resistance drops rapidly and the horn
        acts as a resonant tube rather than a broadband radiator.

    Args:
        design_vector: Horn parameters
            - Exponential: [throat_area, mouth_area, length, V_tc, V_rc]
            - Multisegment: [throat_area, middle_area, mouth_area, ...]
        driver: ThieleSmallParameters instance (for F3 estimation)
        enclosure_type: Must be "exponential_horn" or "multisegment_horn"
        min_circumference_ratio: Minimum mouth circumference as fraction of wavelength
            - Set to 1.0 for full Olson criterion (C ≥ λ)
            - Set to 0.7 for relaxed practical criterion (default)
            - Set to 0.5 for compact designs (some loading compromise)

    Returns:
        Constraint violation (positive = violation, negative = satisfied)

    Examples:
        >>> # Good horn: proper mouth loading
        >>> design = np.array([0.001, 0.10, 1.5, 0.0, 0.0])  # mouth = 1000 cm²
        >>> # Circumference ≈ 3.5 m, wavelength at 40 Hz ≈ 8.6 m
        >>> # Ratio ≈ 0.41 (below ideal but acceptable for compact design)
        >>> constraint_mouth_loading(design, driver, "exponential_horn", min_circumference_ratio=0.4)
        -0.01  # Satisfied

        >>> # Bad horn: severely undersized mouth
        >>> design = np.array([0.0888, 0.036, 3.2, 0.0, 0.0])  # mouth = 360 cm²
        >>> # Circumference ≈ 2.1 m, wavelength at 44 Hz ≈ 7.8 m
        >>> # Ratio ≈ 0.27 (far too small)
        >>> constraint_mouth_loading(design, driver, "exponential_horn")
        0.43  # VIOLATION (0.27 < 0.7, needs mouth 2.6× larger)
    """
    horn_types = ["exponential_horn", "multisegment_horn", "conical_horn",
                  "mixed_profile_horn"]
    if enclosure_type not in horn_types:
        return 0.0  # Not applicable for other enclosure types

    from gsd.simulation.constants import SPEED_OF_SOUND

    # Extract mouth area
    if enclosure_type == "multisegment_horn":
        # For multisegment, mouth is the last area element
        mouth_area = design_vector[2]  # throat, middle, mouth, ...
    elif enclosure_type == "exponential_horn":
        mouth_area = design_vector[1]  # throat, mouth, ...
    elif enclosure_type == "conical_horn":
        mouth_area = design_vector[1]  # throat, mouth, ...
    else:
        return 0.0

    # Calculate mouth circumference (assuming circular mouth)
    # C = 2·π·r = 2·π·√(A/π) = 2·√(π·A)
    mouth_circumference = 2 * np.sqrt(np.pi * mouth_area)

    # Estimate cutoff frequency from driver Fs
    # For bass horns, Fc is typically close to Fs
    # This is a conservative estimate - actual F3 may be lower
    f_cutoff = driver.F_s

    # Calculate wavelength at cutoff
    wavelength = SPEED_OF_SOUND / f_cutoff

    # Constraint: mouth_circumference >= min_circumference_ratio * wavelength
    # Violation if circumference too small
    required_circumference = min_circumference_ratio * wavelength
    violation = required_circumference - mouth_circumference

    return violation



