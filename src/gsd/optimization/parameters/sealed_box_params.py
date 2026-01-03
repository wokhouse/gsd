"""
Parameter space definitions for sealed box optimization.

This module defines valid parameter ranges for sealed box (acoustic
suspension) enclosure optimization.

Literature:
    - Small (1972), Table 1 - Alignment table showing practical Qtc ranges
    - Typical Vb: 0.5×Vas to 2.0×Vas for Qtc in [0.5, 1.2]
    - literature/thiele_small/small_1972_closed_box.md
"""

from typing import Dict, Tuple

from gsd.optimization.parameters.parameter_space import (
    EnclosureParameterSpace,
    ParameterRange
)
from gsd.driver.parameters import ThieleSmallParameters


def get_sealed_box_parameter_space(
    driver: ThieleSmallParameters
) -> EnclosureParameterSpace:
    """
    Get parameter space for sealed box optimization.

    Literature:
        - Small (1972), Table 1 - Alignment table
        - For Qtc in [0.5, 1.2], Vb ranges from ~0.2×Vas to ~5×Vas
        - literature/thiele_small/small_1972_closed_box.md

    Args:
        driver: ThieleSmallParameters instance

    Returns:
        EnclosureParameterSpace for sealed box

    Examples:
        >>> driver = load_driver("BC_8NDL51")
        >>> space = get_sealed_box_parameter_space(driver)
        >>> space.get_bounds_dict()
        {'Vb': (0.00202, 0.0505)}  # m³
    """
    # Calculate reasonable Vb range from driver's Vas
    # Small (1972): Qtc = Qts × √(1 + Vas/Vb)
    # For Qtc in [0.5, 1.2], Vb ranges from ~0.2×Vas to ~5×Vas

    vas = driver.V_as

    # Conservative practical limits
    # Very small box: Qtc ≈ 1.5
    vb_min = 0.2 * vas

    # Large box: Qtc ≈ 0.5
    vb_max = 3.0 * vas

    parameters = [
        ParameterRange(
            name="Vb",
            min_value=vb_min,
            max_value=vb_max,
            units="m³",
            description="Box internal volume"
        )
    ]

    typical_ranges = {
        "compact": (0.5 * vas, 0.8 * vas),    # Qtc ≈ 1.0 to 1.2
        "butterworth": (0.9 * vas, 1.1 * vas), # Qtc ≈ 0.707
        "large": (1.5 * vas, 2.5 * vas)        # Qtc ≈ 0.5 to 0.6
    }

    return EnclosureParameterSpace(
        enclosure_type="sealed",
        parameters=parameters,
        typical_ranges=typical_ranges,
        constraints=["qtc_range", "max_displacement"]
    )
