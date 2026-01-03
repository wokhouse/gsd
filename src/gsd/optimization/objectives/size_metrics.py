"""
Enclosure size objective functions.

This module implements size-related objective functions for
multi-objective optimization:
- Total enclosure volume
- External dimensions (assuming cubic enclosure)
- Footprint area

Literature:
    - Small (1972) - Box volume definitions
    - Thiele (1971) - Vented box volume requirements
    - literature/thiele_small/small_1972_closed_box.md
"""

import numpy as np

from gsd.driver.parameters import ThieleSmallParameters
from gsd.optimization.parameters.exponential_horn_params import calculate_horn_volume


def objective_enclosure_volume(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str
) -> float:
    """
    Calculate total enclosure volume (for minimization).

    Lower volume is generally desirable for space-constrained applications
    and portability, but there is a trade-off with bass extension (F3).

    Literature:
        - Small (1972) - Box volume definitions
        - Thiele (1971) - Vented box volume requirements
        - literature/thiele_small/small_1972_closed_box.md

    Args:
        design_vector: Enclosure parameters
            - Sealed: [Vb] (m³)
            - Ported: [Vb, Fb, port_area, port_length] (m³, Hz, m², m)
            - Exponential horn: [throat_area, mouth_area, length, V_rc] (m², m², m, m³)
        driver: ThieleSmallParameters instance (for S_d in port area calc)
        enclosure_type: Type of enclosure ("sealed", "ported", "exponential_horn")

    Returns:
        Total volume in m³ (lower is better)

    Note:
        For ported boxes, this includes the box volume plus port volume
        displacement with a 20% safety factor for bracing and internal
        displacement.
        For exponential horns, this includes the horn internal volume
        (calculated analytically from the exponential profile) plus the
        rear chamber volume.

    Examples:
        >>> driver = load_driver("BC_8NDL51")
        >>> # 10L sealed box
        >>> objective_enclosure_volume(np.array([0.010]), driver, "sealed")
        0.010  # m³
        >>> # Ported box with ports
        >>> objective_enclosure_volume(
        ...     np.array([0.020, 50.0, 0.002, 0.1]), driver, "ported"
        ... )
        0.02248  # m³ (includes port volume)
    """
    if enclosure_type == "sealed":
        # Simple box volume
        return design_vector[0]  # Vb in m³

    elif enclosure_type == "ported":
        # Box volume + port volume displacement
        Vb = design_vector[0]

        # If port dimensions are provided (design_vector has 4 elements)
        if len(design_vector) >= 4:
            port_area = design_vector[2]
            port_length = design_vector[3]

            # Port volume = port_area × port_length
            # Add 20% safety factor for bracing and internal displacement
            port_volume = port_area * port_length * 1.2
            return Vb + port_volume
        else:
            # Port dimensions not provided, just return box volume
            return Vb

    elif enclosure_type == "exponential_horn":
        # Horn volume + rear chamber volume
        throat_area = design_vector[0]
        mouth_area = design_vector[1]
        length = design_vector[2]
        V_rc = design_vector[3] if len(design_vector) >= 4 else 0.0

        # Calculate horn volume analytically
        # For exponential horn: V_horn = (S₂ - S₁) / m where m = ln(S₂/S₁)/L
        v_horn = calculate_horn_volume(throat_area, mouth_area, length)

        # Total volume = horn + rear chamber
        return v_horn + V_rc

    elif enclosure_type in ["multisegment_horn", "mixed_profile_horn", "conical_horn"]:
        # For multisegment/mixed/conical horns, estimate volume from parameters
        # design_vector format: [throat_area, middle_area, mouth_area, length1, length2, V_tc, V_rc]
        # or for conical: [throat_area, mouth_area, length, V_tc, V_rc]

        if enclosure_type in ["multisegment_horn", "mixed_profile_horn"]:
            # Estimate as conical sections
            S_t = design_vector[0]  # throat area
            S_m = design_vector[1]  # middle area
            S_mouth = design_vector[2]  # mouth area
            L1 = design_vector[3]  # first segment length
            L2 = design_vector[4]  # second segment length
            V_tc = design_vector[5] if len(design_vector) >= 6 else 0.0
            V_rc = design_vector[6] if len(design_vector) >= 7 else 0.0

            # Volume of conical frustum: V = (L/3) * (A1 + A2 + sqrt(A1*A2))
            # First segment
            r1_t = np.sqrt(S_t / np.pi)
            r1_m = np.sqrt(S_m / np.pi)
            V1 = (L1 / 3) * (S_t + S_m + np.sqrt(S_t * S_m))

            # Second segment
            r2_m = np.sqrt(S_m / np.pi)
            r2_mouth = np.sqrt(S_mouth / np.pi)
            V2 = (L2 / 3) * (S_m + S_mouth + np.sqrt(S_m * S_mouth))

            # Total volume
            return V1 + V2 + V_tc + V_rc

        else:  # conical_horn
            S_t = design_vector[0]  # throat area
            S_m = design_vector[1]  # mouth area
            L = design_vector[2]  # length
            V_tc = design_vector[3] if len(design_vector) >= 4 else 0.0
            V_rc = design_vector[4] if len(design_vector) >= 5 else 0.0

            # Volume of conical horn
            V_horn = (L / 3) * (S_t + S_m + np.sqrt(S_t * S_m))

            # Total volume
            return V_horn + V_tc + V_rc

    else:
        raise ValueError(f"Unsupported enclosure type: {enclosure_type}")


def objective_external_height(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    aspect_ratio: float = 1.0
) -> float:
    """
    Calculate external height assuming cubic or rectangular enclosure.

    This is useful for designs with height constraints (e.g., fitting under
    a desk or in a specific space).

    Literature:
        - Small (1972) - Practical cabinet dimensions

    Args:
        design_vector: Enclosure parameters
        driver: ThieleSmallParameters instance
        enclosure_type: Type of enclosure
        aspect_ratio: Width/depth ratio (1.0 = cube)

    Returns:
        External height in meters (lower is better)

    Note:
        This assumes a simple rectangular prism shape with wall thickness
        of 18mm (0.75") typical for MDF construction. Actual dimensions
        may vary based on construction method.

    Examples:
        >>> driver = load_driver("BC_8NDL51")
        >>> # 20L box as a cube
        >>> h = objective_external_height(
        ...     np.array([0.020]), driver, "sealed", aspect_ratio=1.0
        ... )
        >>> # Height ≈ cube root of (0.020 m³) + wall thickness
    """
    # Get internal volume
    V_internal = objective_enclosure_volume(design_vector, driver, enclosure_type)

    # Add wall thickness allowance (18mm per side = 36mm total per dimension)
    wall_thickness = 0.018  # 18mm MDF
    V_external = V_internal + (
        2 * wall_thickness * (V_internal ** (1/3)) ** 2 +
        4 * wall_thickness ** 2 * (V_internal ** (1/3)) +
        8 * wall_thickness ** 3
    )

    # For a rectangular prism with width/depth ratio:
    # V = width × depth × height
    # With aspect_ratio = width/depth:
    # width = aspect_ratio^(1/2) × height^(1/2) × V^(1/3)
    # depth = height / aspect_ratio^(1/2) × V^(1/3)
    # Simplified: assuming cube for now
    height = V_external ** (1/3)

    return height


def objective_footprint_area(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    aspect_ratio: float = 1.0
) -> float:
    """
    Calculate floor footprint area (width × depth).

    This is useful for designs where floor space is limited.

    Literature:
        - Small (1972) - Practical cabinet dimensions

    Args:
        design_vector: Enclosure parameters
        driver: ThieleSmallParameters instance
        enclosure_type: Type of enclosure
        aspect_ratio: Width/depth ratio (1.0 = square footprint)

    Returns:
        Footprint area in m² (lower is better)

    Examples:
        >>> driver = load_driver("BC_12NDL76")
        >>> # 30L box with square footprint
        >>> area = objective_footprint_area(
        ...     np.array([0.030]), driver, "sealed", aspect_ratio=1.0
        ... )
        >>> # Area ≈ (0.030)^(2/3) ≈ 0.09 m²
    """
    # Get internal volume
    V_internal = objective_enclosure_volume(design_vector, driver, enclosure_type)

    # Add wall thickness (simplified)
    wall_thickness = 0.018
    V_external = V_internal * 1.1  # Approximate 10% increase for walls

    # For cube: footprint area = V^(2/3)
    # For rectangular: adjust by aspect ratio
    base_area = V_external ** (2/3)

    if aspect_ratio == 1.0:
        return base_area
    else:
        # width = sqrt(aspect_ratio) × height
        # depth = height / sqrt(aspect_ratio)
        # footprint = width × depth = height² = V^(2/3) / aspect_ratio^(1/3)
        return base_area / (aspect_ratio ** (1/3))
