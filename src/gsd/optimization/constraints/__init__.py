"""
Constraint functions for enclosure optimization.

This module provides constraint functions for ensuring optimized designs
satisfy physical and performance requirements:
- Maximum displacement limits (X_max)
- Port velocity limits (chuffing prevention)
- Qtc ranges (transient response)
- F3 limits (bass extension requirements)

All constraint functions cite relevant literature.
"""

from gsd.optimization.constraints.physical import (
    constraint_max_displacement,
    constraint_port_velocity,
)
from gsd.optimization.constraints.performance import (
    constraint_f3_limit,
    constraint_f3_target,
    constraint_qtc_range,
    constraint_volume_limit,
    constraint_horn_cutoff_frequency,
    constraint_mouth_size,
    constraint_flare_constant_limits,
)

__all__ = [
    "constraint_max_displacement",
    "constraint_port_velocity",
    "constraint_f3_limit",
    "constraint_f3_target",
    "constraint_qtc_range",
    "constraint_volume_limit",
    "constraint_horn_cutoff_frequency",
    "constraint_mouth_size",
    "constraint_flare_constant_limits",
]
