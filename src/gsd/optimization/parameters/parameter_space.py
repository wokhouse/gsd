"""
Parameter space definitions for enclosure optimization.

This module provides base classes and definitions for parameter spaces
that define the valid ranges of design variables for different enclosure
types.

Literature:
    - Small (1972) - Practical ranges for Vb, Qtc
    - Thiele (1971) - Ported box parameter ranges
    - Olson (1947) - Horn geometry practical limits
"""

from dataclasses import dataclass
from typing import Dict, Tuple, List
import numpy as np


@dataclass
class ParameterRange:
    """
    Definition of a single parameter's optimization range.

    Attributes:
        name: Parameter name (e.g., "Vb", "Fb", "throat_area")
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        units: Units string (e.g., "m³", "Hz", "m²")
        description: Human-readable description
    """
    name: str
    min_value: float
    max_value: float
    units: str
    description: str

    def to_tuple(self) -> Tuple[float, float]:
        """Return as (min, max) tuple for pymoo."""
        return (self.min_value, self.max_value)


@dataclass
class EnclosureParameterSpace:
    """
    Complete parameter space definition for an enclosure type.

    Literature:
        - Small (1972) - Practical ranges for sealed/ported boxes
        - Thiele (1971) - Alignment parameter ranges
        - Olson (1947) - Horn geometry limits
        - literature/thiele_small/small_1972_closed_box.md
        - literature/thiele_small/thiele_1971_vented_boxes.md

    Attributes:
        enclosure_type: Type of enclosure ("sealed", "ported", etc.)
        parameters: List of ParameterRange objects
        typical_ranges: Dict of typical values for reference designs
        constraints: List of constraint function names to apply
    """
    enclosure_type: str
    parameters: List[ParameterRange]
    typical_ranges: Dict[str, Tuple[float, float]]
    constraints: List[str] = None

    def get_bounds_dict(self) -> Dict[str, Tuple[float, float]]:
        """Return parameter bounds as dictionary."""
        return {p.name: p.to_tuple() for p in self.parameters}

    def get_bounds_array(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Return parameter bounds as arrays for pymoo.

        Returns:
            (lower_bounds, upper_bounds) tuple
        """
        xl = np.array([p.min_value for p in self.parameters])
        xu = np.array([p.max_value for p in self.parameters])
        return (xl, xu)

    def get_parameter_names(self) -> List[str]:
        """Return list of parameter names in order."""
        return [p.name for p in self.parameters]
