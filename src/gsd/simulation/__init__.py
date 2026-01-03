"""
bugworks GSD simulation module for horn-loaded loudspeaker systems.

This module implements acoustic theory for horn simulation with
continuous validation against Hornresp.

Literature:
- literature/horns/olson_1947.md - Exponential horn theory
- literature/horns/beranek_1954.md - Radiation impedance
- literature/horns/kolbrek_horn_theory_tutorial.md - Modern treatment
- literature/transmission_lines/chabassier_tournemenne_2018_tmatrix.md - T-matrix method
"""

from gsd.simulation.constants import (
    AIR_DENSITY,
    ATMOSPHERIC_PRESSURE,
    CHARACTERISTIC_IMPEDANCE_AIR,
    PI,
    SPEED_OF_SOUND,
    angular_frequency,
    wavelength,
    wavenumber,
)
from gsd.simulation.types import (
    ConicalHorn,
    ExponentialHorn,
    FrequencyResponse,
    SimulationResult,
)

# Horn theory functions (T-matrix method)
from gsd.simulation.horn_theory import (
    MediumProperties,
    circular_piston_radiation_impedance,
    conical_horn_throat_impedance,
    exponential_horn_throat_impedance,
    exponential_horn_tmatrix,
    throat_impedance_from_tmatrix,
)

# Horn driver integration functions
from gsd.simulation.horn_driver_integration import (
    throat_chamber_impedance,
    rear_chamber_impedance,
    horn_system_acoustic_impedance,
    horn_electrical_impedance,
)

__all__ = [
    # Constants
    "SPEED_OF_SOUND",
    "AIR_DENSITY",
    "ATMOSPHERIC_PRESSURE",
    "CHARACTERISTIC_IMPEDANCE_AIR",
    "PI",
    # Functions from constants
    "wavenumber",
    "angular_frequency",
    "wavelength",
    # Horn theory functions
    "MediumProperties",
    "circular_piston_radiation_impedance",
    "conical_horn_throat_impedance",
    "exponential_horn_throat_impedance",
    "exponential_horn_tmatrix",
    "throat_impedance_from_tmatrix",
    # Horn driver integration functions
    "throat_chamber_impedance",
    "rear_chamber_impedance",
    "horn_system_acoustic_impedance",
    "horn_electrical_impedance",
    # Data structures
    "ConicalHorn",
    "ExponentialHorn",
    "FrequencyResponse",
    "SimulationResult",
]
