"""
Enclosure modeling for gsd.

This module implements acoustic simulation for loudspeaker enclosures,
including sealed (closed-box) and ported (vented/bass-reflex) systems.

Literature:
- Small (1972) - Closed-Box Loudspeaker Systems Part I: Analysis
- Thiele (1971) - Loudspeakers in Vented Boxes Parts 1 & 2
- literature/thiele_small/small_1972_closed_box.md
- literature/thiele_small/thiele_1971_vented_boxes.md
"""

from gsd.enclosure.sealed_box import (
    SealedBoxSystemParameters,
    calculate_sealed_box_system_parameters,
    sealed_box_electrical_impedance,
)

from gsd.enclosure.ported_box import (
    PortedBoxSystemParameters,
    helmholtz_resonance_frequency,
    calculate_port_length_for_area,
    calculate_optimal_port_dimensions,
    calculate_ported_box_system_parameters,
    ported_box_electrical_impedance,
)

__all__ = [
    # Sealed box
    "SealedBoxSystemParameters",
    "calculate_sealed_box_system_parameters",
    "sealed_box_electrical_impedance",
    # Ported box
    "PortedBoxSystemParameters",
    "helmholtz_resonance_frequency",
    "calculate_port_length_for_area",
    "calculate_optimal_port_dimensions",
    "calculate_ported_box_system_parameters",
    "ported_box_electrical_impedance",
]

