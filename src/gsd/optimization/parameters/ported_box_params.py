"""
Parameter space definitions for ported box optimization.

This module defines valid parameter ranges for ported box (bass reflex)
enclosure optimization.

Literature:
    - Thiele (1971), Table 1 - Alignment tables (B4, QB3, etc.)
    - Typical Vb: 0.7×Vas to 2.0×Vas
    - Typical Fb: 0.6×Fs to 1.0×Fs
    - literature/thiele_small/thiele_1971_vented_boxes.md
"""

from typing import Dict, Tuple

from gsd.optimization.parameters.parameter_space import (
    EnclosureParameterSpace,
    ParameterRange
)
from gsd.driver.parameters import ThieleSmallParameters


def get_ported_box_parameter_space(
    driver: ThieleSmallParameters
) -> EnclosureParameterSpace:
    """
    Get parameter space for ported box optimization.

    Literature:
        - Thiele (1971), Table 1 - Alignment tables
        - Vb range: 0.5×Vas to 2.5×Vas
        - Fb range: 0.5×Fs to 1.0×Fs
        - literature/thiele_small/thiele_1971_vented_boxes.md

    Args:
        driver: ThieleSmallParameters instance

    Returns:
        EnclosureParameterSpace for ported box

    Examples:
        >>> driver = load_driver("BC_12NDL76")
        >>> space = get_ported_box_parameter_space(driver)
        >>> bounds = space.get_bounds_dict()
        >>> bounds['Vb']     # (0.0365, 0.1825) m³
        >>> bounds['Fb']     # (25.0, 50.0) Hz
    """
    vas = driver.V_as
    fs = driver.F_s
    sd = driver.S_d

    # Volume range: 0.5×Vas to 2.5×Vas
    # Thiele (1971) alignment tables
    vb_min = 0.5 * vas
    vb_max = 2.5 * vas

    # Tuning frequency range: 0.5×Fs to 1.0×Fs
    fb_min = 0.5 * fs
    fb_max = 1.0 * fs

    # Port area range
    # Minimum: prevent chuffing (velocity < 5% of c)
    # Maximum: must fit inside box
    # Typical port areas: 2" to 6" diameter equivalent
    port_area_min = 0.001  # ~35mm diameter
    port_area_max = min(0.02, sd * 0.5)  # ~160mm diameter max, or 50% of cone area

    # Port length range
    # Very short port: 2cm
    # Very long port: 50cm (practical limit)
    port_length_min = 0.02  # 2cm
    port_length_max = 0.50  # 50cm

    parameters = [
        ParameterRange(
            name="Vb",
            min_value=vb_min,
            max_value=vb_max,
            units="m³",
            description="Box internal volume"
        ),
        ParameterRange(
            name="Fb",
            min_value=fb_min,
            max_value=fb_max,
            units="Hz",
            description="Port tuning frequency"
        ),
        ParameterRange(
            name="port_area",
            min_value=port_area_min,
            max_value=port_area_max,
            units="m²",
            description="Port cross-sectional area"
        ),
        ParameterRange(
            name="port_length",
            min_value=port_length_min,
            max_value=port_length_max,
            units="m",
            description="Port physical length"
        )
    ]

    # Typical alignments from Thiele (1971)
    typical_ranges = {
        "B4_alignment": {  # Butterworth maximally flat
            "Vb": (1.0 * vas, 1.2 * vas),
            "Fb": (0.7 * fs, 1.0 * fs)
        },
        "QB3_alignment": {  # Quasi-Butterworth 3rd-order
            "Vb": (0.7 * vas, 0.9 * vas),
            "Fb": (0.6 * fs, 0.8 * fs)
        },
        "BB4_alignment": {  # Extended bass shelf
            "Vb": (0.5 * vas, 0.7 * vas),
            "Fb": (0.8 * fs, 1.0 * fs)
        }
    }

    return EnclosureParameterSpace(
        enclosure_type="ported",
        parameters=parameters,
        typical_ranges=typical_ranges,
        constraints=["max_displacement", "port_velocity", "f3_limit"]
    )
