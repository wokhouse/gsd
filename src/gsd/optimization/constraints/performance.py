"""
Performance constraint functions for enclosure optimization.

This module provides constraint functions for ensuring optimized designs
meet performance requirements:
- F3 limits (bass extension)
- Qtc ranges (transient response)
- Bandwidth requirements

Literature:
    - Small (1972) - F3 definition and calculation
    - Thiele (1971) - Alignment selection and system parameters
    - literature/thiele_small/small_1972_closed_box.md
    - literature/thiele_small/thiele_1971_vented_boxes.md
"""

import numpy as np

from gsd.driver.parameters import ThieleSmallParameters
from gsd.optimization.objectives.response_metrics import objective_f3
from gsd.enclosure.sealed_box import calculate_sealed_box_system_parameters


def constraint_f3_limit(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    max_f3: float = 100.0
) -> float:
    """
    Constrain F3 to be below specified limit.

    This is useful for ensuring a minimum level of bass extension.

    Literature:
        - Small (1972) - F3 definition and calculation

    Args:
        design_vector: Enclosure parameters
        driver: ThieleSmallParameters instance
        enclosure_type: Type of enclosure ("sealed", "ported")
        max_f3: Maximum allowed F3 in Hz (default 100 Hz)

    Returns:
        Constraint violation (positive if F3 > max_f3)
        pymoo expects constraints to be ≤ 0 (negative = satisfied)

    Examples:
        >>> driver = load_driver("BC_12NDL76")
        >>> # Require F3 < 80 Hz
        >>> violation = constraint_f3_limit(
        ...     np.array([0.020]), driver, "sealed", max_f3=80
        ... )
        >>> # If violation > 0, F3 is higher than 80 Hz (constraint failed)
    """
    try:
        f3 = objective_f3(design_vector, driver, enclosure_type)
        return f3 - max_f3
    except Exception:
        return 1000.0  # Large violation if calculation fails


def constraint_f3_target(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    target_f3: float = 60.0,
    tolerance: float = 5.0
) -> float:
    """
    Constrain F3 to be close to target value.

    This is useful when you want a specific bass extension target.

    Literature:
        - Small (1972) - F3 calculation

    Args:
        design_vector: Enclosure parameters
        driver: ThieleSmallParameters instance
        enclosure_type: Type of enclosure
        target_f3: Target F3 in Hz (default 60 Hz)
        tolerance: Allowed deviation from target in Hz (default 5 Hz)

    Returns:
        Maximum constraint violation (positive if outside tolerance range)
        pymoo expects constraints to be ≤ 0 (negative = satisfied)

    Examples:
        >>> driver = load_driver("BC_8NDL51")
        >>> # Target F3 = 70 Hz ± 5 Hz
        >>> violation = constraint_f3_target(
        ...     np.array([0.010]), driver, "sealed",
        ...     target_f3=70, tolerance=5
        ... )
        >>> # If |violation| <= 0, F3 is in [65, 75] Hz range
    """
    try:
        f3 = objective_f3(design_vector, driver, enclosure_type)

        # Two-sided constraint: target - tolerance <= F3 <= target + tolerance
        violation_low = (target_f3 - tolerance) - f3  # Positive if F3 too low
        violation_high = f3 - (target_f3 + tolerance)  # Positive if F3 too high

        # Return maximum violation (must be <= 0 for satisfaction)
        return max(violation_low, violation_high, 0.0)

    except Exception:
        return 1000.0


def constraint_qtc_range(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    qtc_min: float = 0.5,
    qtc_max: float = 1.2
) -> float:
    """
    Constrain system Qtc to be within acceptable range.

    Qtc affects transient response and bass character:
    - Qtc < 0.5: Overdamped (poor transient response, weak bass)
    - Qtc 0.5-0.71: Critically damped to Butterworth (tight, accurate bass)
    - Qtc 0.71-1.0: Slightly underdamped (warm bass, good transient)
    - Qtc > 1.2: Underdamped (boomy, ringing, poor transient)

    Literature:
        - Small (1972) - Qtc and its effect on transient response
        - literature/thiele_small/small_1972_closed_box.md

    Args:
        design_vector: Enclosure parameters (only for sealed boxes)
        driver: ThieleSmallParameters instance
        enclosure_type: Must be "sealed"
        qtc_min: Minimum acceptable Qtc (default 0.5)
        qtc_max: Maximum acceptable Qtc (default 1.2)

    Returns:
        Maximum constraint violation (positive if outside range)
        pymoo expects constraints to be ≤ 0 (negative = satisfied)

    Examples:
        >>> driver = load_driver("BC_8NDL51")
        >>> # Require Butterworth alignment (Qtc = 0.707 ± 0.05)
        >>> violation = constraint_qtc_range(
        ...     np.array([0.010]), driver, "sealed",
        ...     qtc_min=0.65, qtc_max=0.75
        ... )
        >>> # If violation <= 0, Qtc is in [0.65, 0.75] range
    """
    if enclosure_type != "sealed":
        return 0.0  # Not applicable for other enclosures

    try:
        Vb = design_vector[0]
        params = calculate_sealed_box_system_parameters(driver, Vb)

        # Return maximum violation (positive if outside range)
        violation_low = qtc_min - params.Qtc
        violation_high = params.Qtc - qtc_max

        return max(violation_low, violation_high, 0.0)

    except Exception:
        return 1000.0


def constraint_volume_limit(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    max_volume_liters: float = 50.0
) -> float:
    """
    Constrain enclosure volume to be below maximum limit.

    This is useful for space-constrained applications.

    Literature:
        - Small (1972) - Box volume definitions

    Args:
        design_vector: Enclosure parameters
        driver: ThieleSmallParameters instance
        enclosure_type: Type of enclosure ("sealed", "ported")
        max_volume_liters: Maximum allowed volume in liters (default 50L)

    Returns:
        Constraint violation (positive if volume > max_volume)
        pymoo expects constraints to be ≤ 0 (negative = satisfied)

    Examples:
        >>> driver = load_driver("BC_15DS115")
        >>> # Maximum 100L enclosure
        >>> violation = constraint_volume_limit(
        ...     np.array([0.080]), driver, "sealed",
        ...     max_volume_liters=100
        ... )
        >>> # If violation <= 0, volume is <= 100L
    """
    from gsd.optimization.objectives.size_metrics import objective_enclosure_volume

    try:
        volume_m3 = objective_enclosure_volume(design_vector, driver, enclosure_type)
        volume_liters = volume_m3 * 1000.0

        return volume_liters - max_volume_liters

    except Exception:
        return 1000.0


def constraint_horn_cutoff_frequency(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    target_fc: float = 60.0,
    tolerance: float = 10.0
) -> float:
    """
    Constrain horn cutoff frequency to target range.

    The cutoff frequency is the frequency below which the horn acts as a
    high-pass filter. This constraint ensures the horn is designed for a
    specific frequency range.

    Literature:
        - Olson (1947), Eq. 5.18 - f_c = c·m/(2π)
        - literature/horns/olson_1947.md

    Args:
        design_vector: Horn parameters [throat_area, mouth_area, length, V_rc]
        driver: ThieleSmallParameters instance (not used, kept for interface)
        enclosure_type: Must be "exponential_horn"
        target_fc: Target cutoff frequency in Hz (default 60 Hz)
        tolerance: Allowed deviation from target in Hz (default 10 Hz)

    Returns:
        Maximum constraint violation (positive if outside tolerance range)
        pymoo expects constraints to be ≤ 0 (negative = satisfied)

    Examples:
        >>> driver = load_driver("TC2")
        >>> # Target Fc = 400 Hz ± 20 Hz
        >>> violation = constraint_horn_cutoff_frequency(
        ...     np.array([0.0005, 0.02, 0.5, 0.0]), driver, "exponential_horn",
        ...     target_fc=400, tolerance=20
        ... )
        >>> # If violation <= 0, Fc is in [380, 420] Hz range
    """
    if enclosure_type != "exponential_horn":
        return 0.0  # Not applicable for other enclosures

    try:
        from gsd.optimization.parameters.exponential_horn_params import (
            calculate_horn_cutoff_frequency
        )
        from gsd.simulation.constants import SPEED_OF_SOUND

        throat_area = design_vector[0]
        mouth_area = design_vector[1]
        length = design_vector[2]

        fc = calculate_horn_cutoff_frequency(
            throat_area, mouth_area, length, SPEED_OF_SOUND
        )

        # Two-sided constraint: target - tolerance <= Fc <= target + tolerance
        violation_low = (target_fc - tolerance) - fc  # Positive if Fc too low
        violation_high = fc - (target_fc + tolerance)  # Positive if Fc too high

        # Return maximum violation (must be <= 0 for satisfaction)
        return max(violation_low, violation_high, 0.0)

    except Exception:
        return 1000.0


def constraint_mouth_size(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    min_mouth_radius_wavelengths: float = 0.5
) -> float:
    """
    Constrain mouth size for effective radiation.

    The mouth must be large enough to radiate sound efficiently. This constraint
    ensures the mouth circumference is at least one wavelength at the cutoff
    frequency (equivalent to radius >= λ/2).

    Literature:
        - Olson (1947), Chapter 5 - Mouth size requirements
        - literature/horns/olson_1947.md

    Args:
        design_vector: Horn parameters [throat_area, mouth_area, length, V_rc]
        driver: ThieleSmallParameters instance (not used, kept for interface)
        enclosure_type: Must be "exponential_horn"
        min_mouth_radius_wavelengths: Min mouth radius as fraction of wavelength
            at cutoff (default 0.5, meaning mouth_radius >= 0.5 * λ_cutoff / 2)

    Returns:
        Constraint violation (positive if mouth too small)
        pymoo expects constraints to be ≤ 0 (negative = satisfied)

    Examples:
        >>> driver = load_driver("TC2")
        >>> # Ensure mouth is at least λ/2 at cutoff
        >>> violation = constraint_mouth_size(
        ...     np.array([0.0005, 0.02, 0.5, 0.0]), driver, "exponential_horn"
        ... )
        >>> # If violation <= 0, mouth is large enough
    """
    if enclosure_type != "exponential_horn":
        return 0.0  # Not applicable for other enclosures

    try:
        from gsd.optimization.parameters.exponential_horn_params import (
            calculate_horn_cutoff_frequency
        )
        from gsd.simulation.constants import SPEED_OF_SOUND

        throat_area = design_vector[0]
        mouth_area = design_vector[1]
        length = design_vector[2]

        fc = calculate_horn_cutoff_frequency(
            throat_area, mouth_area, length, SPEED_OF_SOUND
        )
        wavelength_cutoff = SPEED_OF_SOUND / fc
        mouth_radius = np.sqrt(mouth_area / np.pi)

        # Constraint: mouth_radius >= 0.5 * wavelength_cutoff / 2
        # This is equivalent to mouth_circumference >= wavelength_cutoff
        min_radius = min_mouth_radius_wavelengths * wavelength_cutoff / 2

        return max(min_radius - mouth_radius, 0.0)

    except Exception:
        return 1000.0


def constraint_flare_constant_limits(
    design_vector: np.ndarray,
    driver: ThieleSmallParameters,
    enclosure_type: str,
    min_m_length: float = 0.5,
    max_m_length: float = 3.0
) -> float:
    """
    Constrain flare rate for practical horns.

    The product m·L determines how rapidly the horn flares. If m·L is too small,
    the horn approaches a cylindrical pipe. If m·L is too large, the horn
    approximates a rapid expansion which causes reflections.

    Literature:
        - Olson (1947), Chapter 5 - Practical horn design limits
        - literature/horns/olson_1947.md

    Args:
        design_vector: Horn parameters [throat_area, mouth_area, length, V_rc]
        driver: ThieleSmallParameters instance (not used, kept for interface)
        enclosure_type: Must be "exponential_horn"
        min_m_length: Minimum acceptable m·L product (default 0.5)
        max_m_length: Maximum acceptable m·L product (default 3.0)

    Returns:
        Maximum constraint violation (positive if outside range)
        pymoo expects constraints to be ≤ 0 (negative = satisfied)

    Examples:
        >>> driver = load_driver("TC2")
        >>> # Ensure practical horn geometry
        >>> violation = constraint_flare_constant_limits(
        ...     np.array([0.0005, 0.02, 0.5, 0.0]), driver, "exponential_horn"
        ... )
        >>> # If violation <= 0, 0.5 <= m·L <= 3.0
    """
    if enclosure_type != "exponential_horn":
        return 0.0  # Not applicable for other enclosures

    try:
        from gsd.simulation.types import ExponentialHorn

        throat_area = design_vector[0]
        mouth_area = design_vector[1]
        length = design_vector[2]

        horn = ExponentialHorn(throat_area, mouth_area, length)
        m_times_L = horn.flare_constant * horn.length

        # Two-sided constraint
        violation_low = min_m_length - m_times_L
        violation_high = m_times_L - max_m_length

        return max(violation_low, violation_high, 0.0)

    except Exception:
        return 1000.0
