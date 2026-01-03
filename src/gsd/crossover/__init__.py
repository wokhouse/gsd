"""
Crossover simulation module for gsd.

This module provides frequency-domain crossover filtering for multi-way
loudspeaker systems, with support for proper time-alignment (Z-offset)
and power summation for magnitude-only data.

Literature:
- literature/crossovers/ - Crossover theory and implementation
"""

from gsd.crossover.lr4 import (
    apply_lr4_crossover,
    design_lr4_filters,
    mag_to_minimum_phase,
    optimize_crossover_and_alignment,
    optimize_crossover_frequency,
)

__all__ = [
    "mag_to_minimum_phase",
    "design_lr4_filters",
    "apply_lr4_crossover",
    "optimize_crossover_frequency",
    "optimize_crossover_and_alignment",
]
