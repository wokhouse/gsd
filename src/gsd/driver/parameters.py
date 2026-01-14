"""
Thiele-Small parameter data structures for loudspeaker drivers.

This module defines the complete Thiele-Small parameter model for
moving-coil loudspeakers, including fundamental physical parameters
and derived small-signal parameters.

Literature:
- COMSOL (2020), Lumped Loudspeaker Driver - Complete T/S parameter definitions
- Thiele (1971) - Original T/S parameter papers
- Small (1972) - Closed-box and vented-box systems
- Beranek (1954), Eq. 5.20 - Radiation impedance and mass loading
- literature/thiele_small/comsol_lumped_loudspeaker_driver_2020.md
- literature/horns/beranek_1954.md
"""

from dataclasses import dataclass
import math

from gsd.simulation.constants import (
    AIR_DENSITY,
    SPEED_OF_SOUND,
    CHARACTERISTIC_IMPEDANCE_AIR,
)
from gsd.driver.radiation_mass import calculate_resonance_with_radiation_mass


@dataclass
class ThieleSmallParameters:
    """
    Thiele-Small parameters for a moving-coil loudspeaker driver.

    This dataclass stores the fundamental physical parameters of a driver
    and calculates the derived small-signal parameters (resonance frequency,
    Q factors, equivalent volume).

    Literature:
        - COMSOL (2020), Tables 2-3 - Fundamental and derived parameters
        - Thiele (1971) - T/S parameter definitions
        - Small (1972) - Loudspeaker system analysis
        - Beranek (1954), Eq. 5.20 - Radiation impedance and mass loading
        - literature/thiele_small/comsol_lumped_loudspeaker_driver_2020.md
        - literature/horns/beranek_1954.md

    Attributes:
        M_md: Driver mass only (kg) - voice coil + diaphragm, excludes radiation mass
        C_ms: Suspension compliance (m/N) - spider + surround
        R_ms: Mechanical resistance (N·s/m) - damping losses
        R_e: Voice coil DC resistance (Ω)
        L_e: Voice coil inductance (H)
        BL: Force factor (T·m) - magnetic field × coil length
        S_d: Effective piston area (m²)
        X_max: Maximum linear excursion (m) - optional, for port sizing calculations

    Derived Properties (calculated in __post_init__):
        M_ms: Total moving mass (kg) = M_md + radiation mass
        F_s: Resonance frequency (Hz) - includes radiation mass loading
        Q_es: Electrical Q factor at F_s
        Q_ms: Mechanical Q factor at F_s
        Q_ts: Total Q factor at F_s
        V_as: Equivalent volume of compliance (m³)

    Examples:
        >>> driver = ThieleSmallParameters(
        ...     M_md=0.054,    # 54g driver mass only (excludes radiation mass)
        ...     C_ms=0.00019,  # Compliance
        ...     R_ms=5.2,      # Mechanical resistance
        ...     R_e=3.1,       # DC resistance
        ...     L_e=0.72e-3,   # 0.72mH inductance
        ...     BL=16.5,       # Force factor
        ...     S_d=0.0522     # 522cm² effective area
        ... )
        >>> driver.F_s
        49.78...  # Hz resonance frequency (with radiation mass)
        >>> driver.M_ms * 1000  # Total mass including radiation
        57.2...  # g (M_md + radiation mass)
        >>> driver.Q_ts
        0.19...  # Total Q factor

    Note on M_md vs M_ms:
        M_md is the driver's physical mass (voice coil + diaphragm) only,
        excluding any air load. This is the value you specify when creating
        a driver.

        M_ms includes radiation mass loading from the air mass that moves
        with the piston. This is calculated automatically using Beranek's
        radiation impedance theory.

        Datasheet note: Many manufacturers provide "Mms" which already includes
        radiation mass. When using datasheet values, you may need to subtract
        the radiation component (typically 2-4g for 8" drivers, more for larger
        cones) to obtain M_md. Alternatively, use M_md directly if the datasheet
        provides "Mmd" or specifies the moving mass without air load.
    """

    # Fundamental physical parameters
    M_md: float  # Driver mass only (voice coil + diaphragm, kg)
    C_ms: float  # Suspension compliance (m/N)
    R_ms: float  # Mechanical resistance (N·s/m)
    R_e: float   # Voice coil DC resistance (Ω)
    L_e: float   # Voice coil inductance (H)
    BL: float    # Force factor (T·m)
    S_d: float   # Effective piston area (m²)
    X_max: float = None  # Maximum linear excursion (m), optional parameter for port sizing
    throat_area_cm2: float = None  # Compression driver throat area (cm²), for horn-loaded drivers

    # Derived properties (calculated in __post_init__)
    M_ms: float = None  # Total moving mass including radiation (kg)
    F_s: float = None   # Resonance frequency (Hz)
    Q_es: float = None  # Electrical Q factor
    Q_ms: float = None  # Mechanical Q factor
    Q_ts: float = None  # Total Q factor
    V_as: float = None  # Equivalent volume of compliance (m³)

    def __post_init__(self):
        """
        Calculate derived Thiele-Small parameters.

        Literature:
            - COMSOL (2020), Table 3 - Small-signal parameter formulas
            - Small (1972) - T/S parameter relationships
            - Beranek (1954), Eq. 5.20 - Radiation impedance and mass loading

        Equations:
            F_s = 1 / (2π√(M_ms·C_ms)) where M_ms includes radiation mass
            M_ms = M_md + 2×M_rad(F_s) (iterative solution)
            Q_es = (2π·F_s·M_ms) / R_e
            Q_ms = (2π·F_s·M_ms) / R_ms
            Q_ts = (Q_es·Q_ms) / (Q_es + Q_ms)
            V_as = ρ₀·c²·S_d²·C_ms
        """
        # Validate fundamental parameters
        self._validate_parameters()

        # Calculate resonance frequency including radiation mass loading
        # Uses iterative solver to handle frequency-dependent radiation mass
        # Beranek (1954), Eq. 5.20 - Radiation impedance
        # Hornresp methodology: 2× radiation mass multiplier
        self.F_s, self.M_ms = calculate_resonance_with_radiation_mass(
            self.M_md,
            self.C_ms,
            self.S_d,
            AIR_DENSITY,
            SPEED_OF_SOUND
        )

        # Calculate electrical Q factor
        # COMSOL (2020), Table 3: Q_es = 2πF_s·M_ms·R_E / (BL)²
        # The electrical damping is determined by the force factor BL
        # and the reflected mechanical resistance seen from electrical side
        omega_s = 2.0 * math.pi * self.F_s
        self.Q_es = (omega_s * self.M_ms * self.R_e) / (self.BL ** 2)

        # Calculate mechanical Q factor
        # COMSOL (2020), Table 3: Q_ms = 2πF_s·M_ms / R_ms
        if self.R_ms == 0:
            # Ideal driver with no mechanical losses has infinite Q_ms
            self.Q_ms = float('inf')
        else:
            self.Q_ms = (omega_s * self.M_ms) / self.R_ms

        # Calculate total Q factor
        # COMSOL (2020), Table 3: Q_ts = Q_es·Q_ms / (Q_es + Q_ms)
        if math.isinf(self.Q_ms):
            # If Q_ms is infinite (no mechanical losses), Q_ts = Q_es
            self.Q_ts = self.Q_es
        else:
            self.Q_ts = (self.Q_es * self.Q_ms) / (self.Q_es + self.Q_ms)

        # Calculate equivalent volume of compliance
        # COMSOL (2020), Table 3: V_as = ρc²·S_D²·C_ms
        self.V_as = (
            AIR_DENSITY * (SPEED_OF_SOUND ** 2) * (self.S_d ** 2) * self.C_ms
        )

    def _validate_parameters(self):
        """
        Validate that fundamental parameters are physically reasonable.

        Raises:
            ValueError: If any parameter is outside valid range
        """
        if self.M_md <= 0:
            raise ValueError(f"Driver mass M_md must be > 0, got {self.M_md} kg")

        if self.C_ms <= 0:
            raise ValueError(
                f"Suspension compliance C_ms must be > 0, got {self.C_ms} m/N"
            )

        if self.R_ms < 0:
            raise ValueError(
                f"Mechanical resistance R_ms must be >= 0, got {self.R_ms} N·s/m"
            )

        if self.R_e <= 0:
            raise ValueError(
                f"Voice coil resistance R_e must be > 0, got {self.R_e} Ω"
            )

        if self.L_e < 0:
            raise ValueError(
                f"Voice coil inductance L_e must be >= 0, got {self.L_e} H"
            )

        if self.BL <= 0:
            raise ValueError(f"Force factor BL must be > 0, got {self.BL} T·m")

        if self.S_d <= 0:
            raise ValueError(
                f"Effective area S_d must be > 0, got {self.S_d} m²"
            )

    def piston_radius(self) -> float:
        """
        Calculate effective piston radius from effective area.

        Assumes circular piston: a = √(S_d/π)

        Returns:
            Piston radius (m)

        Examples:
            >>> driver = ThieleSmallParameters(0.05, 0.0002, 5, 3, 0.001, 10, 0.05)
            >>> driver.piston_radius()
            0.126...  # m for S_d = 0.05 m²
        """
        return math.sqrt(self.S_d / math.pi)

    def __repr__(self) -> str:
        """String representation with key parameters."""
        return (
            f"ThieleSmallParameters("
            f"F_s={self.F_s:.1f}Hz, "
            f"Q_ts={self.Q_ts:.2f}, "
            f"V_as={self.V_as*1000:.1f}L, "
            f"R_e={self.R_e:.1f}Ω, "
            f"S_d={self.S_d*10000:.0f}cm²)"
        )
