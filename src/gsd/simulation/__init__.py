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

from __future__ import annotations

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
    TappedHorn,
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

# NOTE: Tapped horn functions are imported lazily via __getattr__ to avoid circular import
# with driver.parameters. They will be imported on first access.
#
# The circular import chain is:
# - simulation/__init__.py → tapped_horn_theory.py → driver.parameters → simulation.constants
# - But simulation.constants triggers simulation/__init__.py to be imported before
#   driver.parameters finishes loading
#
# By using lazy imports, we break this cycle.

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
    # Tapped horn functions (lazily imported)
    "calculate_three_port_pressure",
    "calculate_three_port_acoustic_impedance",
    "tapped_horn_spl_response",
    "calculate_lossy_wavenumber_enhanced",
    # Data structures
    "ConicalHorn",
    "ExponentialHorn",
    "FrequencyResponse",
    "SimulationResult",
    "TappedHorn",
]


def __getattr__(name: str):
    """
    Lazy import for tapped horn functions to avoid circular import.

    The circular import occurs because:
    1. simulation/__init__.py imports tapped_horn_theory
    2. tapped_horn_theory imports ThieleSmallParameters from driver.parameters
    3. driver.parameters imports simulation.constants
    4. simulation.constants triggers simulation/__init__.py to be imported
    5. But tapped_horn_theory is still loading, creating a circular dependency

    By deferring the import until first access, we break the cycle.
    """
    # Tapped horn functions (lazy loaded)
    if name in ("calculate_three_port_pressure", "calculate_three_port_acoustic_impedance",
                "tapped_horn_spl_response", "calculate_lossy_wavenumber_enhanced"):
        from gsd.simulation import tapped_horn_theory
        return getattr(tapped_horn_theory, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
