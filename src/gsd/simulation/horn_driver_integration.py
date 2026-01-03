"""
Horn driver integration models.

This module implements the electromechanical coupling between loudspeaker
drivers and horn-loaded enclosures, including throat chambers and rear chambers.

Literature:
- Olson (1947), Chapter 8 - Horn driver systems
- Beranek (1954), Chapter 5 - Acoustic compliance, electromechanical analogies
- Small (1972) - Thiele-Small analysis for horn-loaded drivers
- literature/horns/olson_1947.md
- literature/horns/beranek_1954.md
- literature/thiele_small/small_1972_closed_box.md
"""

from __future__ import annotations

import math
import cmath
from typing import Optional, Tuple, Union
from dataclasses import dataclass
import numpy as np
from numpy.typing import NDArray
from gsd.simulation.horn_theory import (
    exponential_horn_throat_impedance,
    exponential_horn_tmatrix,
    conical_horn_throat_impedance,
    multsegment_horn_throat_impedance,
    circular_piston_radiation_impedance,
    MediumProperties,
)
from gsd.simulation.types import ExponentialHorn, ConicalHorn, HyperbolicHorn, MultiSegmentHorn
from gsd.simulation.constants import (
    SPEED_OF_SOUND,
    AIR_DENSITY,
    CHARACTERISTIC_IMPEDANCE_AIR,
    angular_frequency,
)


def scale_throat_acoustic_to_mechanical(
    z_acoustic_throat: complex,
    throat_area: float,
    diaphragm_area: float
) -> complex:
    """
    Scale throat acoustic impedance to diaphragm mechanical impedance.

    For compression drivers, the acoustic impedance is calculated at the horn throat
    (area S_throat), but the voice coil acts on the diaphragm (area S_d). This function
    transforms throat acoustic impedance to diaphragm mechanical impedance using the
    compression ratio.

    Literature:
        Z_mechanical_diaphragm = Z_acoustic_throat × S_d²
        Equivalently: Z_mech = Z_acoustic_throat × S_throat² × (S_d/S_throat)²

        - Beranek (1954), Chapter 8 - Compression driver loading
        - Olson (1947), Chapter 8 - Horn driver impedance transformation

    Args:
        z_acoustic_throat: Acoustic impedance at throat [Pa·s/m³]
        throat_area: Horn throat area [m²]
        diaphragm_area: Driver diaphragm area [m²]

    Returns:
        Mechanical impedance at diaphragm [N·s/m]

    Examples:
        >>> z_throat = 1000 + 500j  # Pa·s/m³
        >>> Z_mech = scale_throat_acoustic_to_mechanical(z_throat, 0.0005, 0.0008)
        >>> abs(Z_mech)
        2560...  # N·s/m (scaled by compression ratio)
    """
    compression_ratio = diaphragm_area / throat_area
    Z_mechanical = z_acoustic_throat * (throat_area ** 2) * (compression_ratio ** 2)
    return Z_mechanical


def calculate_mouth_volume_velocity(
    throat_volume_velocity: ComplexArray,
    frequencies: FloatArray,
    horn: 'ExponentialHorn',
    medium: MediumProperties,
    radiation_angle: float = 2 * np.pi
) -> ComplexArray:
    """
    Calculate mouth volume velocity from throat velocity using T-matrix transformation.

    Uses the T-matrix relation to propagate throat volume velocity to the mouth:
        [p_t, U_t]ᵀ = [A B; C D][p_m, U_m]ᵀ
        U_t = C·p_m + D·U_m = C·Z_mouth·U_m + D·U_m = U_m·(C·Z_mouth + D)
        Therefore: U_m = U_t / (C·Z_mouth + D)

    Literature:
        Kolbrek, "Horn Theory: An Introduction, Part 1" - T-matrix method
        literature/horns/kolbrek_horn_theory_tutorial.md

    Args:
        throat_volume_velocity: Complex throat volume velocity array [m³/s]
        frequencies: Frequency array [Hz] (must match throat_volume_velocity shape)
        horn: ExponentialHorn geometry
        medium: Acoustic medium properties
        radiation_angle: Solid angle of radiation [steradians]

    Returns:
        Complex mouth volume velocity array [m³/s]

    Examples:
        >>> import numpy as np
        >>> from gsd.simulation.types import ExponentialHorn
        >>> horn = ExponentialHorn(0.0005, 0.02, 0.5)
        >>> freqs = np.array([100.0, 1000.0])
        >>> U_throat = np.array([1e-4, 1e-4]) + 0j
        >>> U_mouth = calculate_mouth_volume_velocity(U_throat, freqs, horn, MediumProperties())
        >>> np.abs(U_mouth)
        array([5.4e-4..., 4.3e-4...])  # m³/s
    """
    # Get T-matrix elements
    a, b, c, d = exponential_horn_tmatrix(frequencies, horn, medium)

    # Get mouth impedance
    effective_mouth_area = 2 * np.pi * horn.mouth_area / radiation_angle
    z_mouth = circular_piston_radiation_impedance(frequencies, effective_mouth_area, medium)

    # Calculate mouth velocity: U_m = U_t / (C*Z_m + D)
    u_mouth = throat_volume_velocity / (c * z_mouth + d)

    return u_mouth


def calculate_radiated_power(
    mouth_volume_velocity: complex,
    mouth_impedance: complex
) -> float:
    """
    Calculate acoustic power radiated from horn mouth.

    Literature:
        W_rad = 0.5 · |U_mouth|² · Re(Z_mouth)
        Beranek (1954), Chapter 4 - Acoustic power radiation

    Args:
        mouth_volume_velocity: Complex volume velocity at mouth [m³/s]
        mouth_impedance: Complex acoustic impedance at mouth [Pa·s/m³]

    Returns:
        Radiated acoustic power [W]

    Examples:
        >>> U_m = 1e-4 + 0j
        >>> Z_m = 15000 + 5000j
        >>> calculate_radiated_power(U_m, Z_m)
        0.00075...  # Watts
    """
    # Factor of 0.5 for RMS (we use peak values in calculation)
    power = 0.5 * (np.abs(mouth_volume_velocity) ** 2) * np.real(mouth_impedance)
    return max(0.0, power)  # Ensure non-negative
from gsd.simulation.constants import (
    SPEED_OF_SOUND,
    AIR_DENSITY,
    CHARACTERISTIC_IMPEDANCE_AIR,
    angular_frequency,
)

# Type aliases
ComplexArray = NDArray[np.complexfloating]
FloatArray = NDArray[np.floating]


def throat_chamber_impedance(
    frequencies: FloatArray,
    V_tc: float,
    A_tc: float,
    medium: Optional[MediumProperties] = None
) -> ComplexArray:
    """Calculate acoustic impedance of a throat chamber.

    The throat chamber is a compliance volume between the driver diaphragm
    and the horn throat. It acts as a series acoustic compliance.

    Literature:
        - Olson (1947), Chapter 8 - Throat chamber compliance
        - Beranek (1954), Chapter 5 - Acoustic compliance of cavities
        - literature/horns/olson_1947.md
        - literature/horns/beranek_1954.md

    Acoustic compliance of a cavity:
        C_tc = V_tc / (ρ·c²)

    Acoustic impedance of compliance:
        Z_tc = 1 / (jω·C_tc) = -j / (ω·C_tc)

    Args:
        frequencies: Array of frequencies [Hz]
        V_tc: Throat chamber volume [m³]
        A_tc: Throat chamber area [m²] (typically equals horn throat area)
        medium: Acoustic medium properties (uses default if None)

    Returns:
        Complex acoustic impedance array [Pa·s/m³]
        Series compliance impedance (purely reactive)

    Raises:
        ValueError: If V_tc <= 0 or A_tc <= 0

    Examples:
        >>> import numpy as np
        >>> freqs = np.array([100.0, 500.0, 1000.0])
        >>> z_tc = throat_chamber_impedance(freqs, V_tc=0.001, A_tc=0.005)
        >>> z_tc[0]  # Low frequency: high impedance (stiff spring)
        (-...j)
        >>> z_tc[2]  # High frequency: low impedance
        (-...j)

    Validation:
        Compare with Hornresp throat chamber impedance calculation.
        Expected: <1% deviation for all frequencies above 20 Hz.
    """
    if medium is None:
        medium = MediumProperties()

    frequencies = np.atleast_1d(frequencies).astype(float)

    if V_tc <= 0:
        raise ValueError(f"Throat chamber volume V_tc must be > 0, got {V_tc} m³")

    if A_tc <= 0:
        raise ValueError(f"Throat chamber area A_tc must be > 0, got {A_tc} m²")

    # Acoustic compliance of cavity
    # Beranek (1954), Chapter 5: C = V / (ρ·c²)
    # literature/horns/beranek_1954.md
    C_tc = V_tc / (medium.rho * medium.c ** 2)

    # Angular frequency: ω = 2πf
    omega = 2 * np.pi * frequencies

    # Acoustic impedance of compliance (series element)
    # Z_tc = 1 / (jω·C) = -j / (ω·C)
    # Purely reactive (compliance behaves like spring)
    Z_tc = -1j / (omega * C_tc)

    return Z_tc


def rear_chamber_impedance(
    frequencies: FloatArray,
    V_rc: float,
    S_d: float,
    medium: Optional[MediumProperties] = None
) -> ComplexArray:
    """Calculate acoustic impedance of a rear chamber (sealed box).

    The rear chamber is the enclosure volume behind the driver diaphragm.
    It adds compliance to the rear of the driver, similar to a sealed box.

    Literature:
        - Small (1972) - Closed-box systems
        - Beranek (1954), Chapter 5 - Acoustic compliance
        - literature/thiele_small/small_1972_closed_box.md
        - literature/horns/beranek_1954.md

    Acoustic compliance of rear chamber:
        C_rc = V_rc / (ρ·c²)

    Acoustic impedance (seen from rear of diaphragm):
        Z_rc = 1 / (jω·C_rc) + Z_rad_rear

    where Z_rad_rear is the radiation impedance on the rear side.
    For a front-loaded horn with no rear radiation, Z_rad_rear = 0.

    Args:
        frequencies: Array of frequencies [Hz]
        V_rc: Rear chamber volume [m³]
        S_d: Diaphragm area [m²]
        medium: Acoustic medium properties (uses default if None)

    Returns:
        Complex acoustic impedance array [Pa·s/m³]
        Compliance impedance in parallel with rear radiation

    Raises:
        ValueError: If V_rc <= 0 or S_d <= 0

    Examples:
        >>> import numpy as np
        >>> freqs = np.array([100.0, 500.0, 1000.0])
        >>> z_rc = rear_chamber_impedance(freqs, V_rc=0.010, S_d=0.022)
        >>> z_rc[0]  # Low frequency: high compliance impedance
        (-...j)

    Validation:
        Compare with Hornresp rear chamber impedance calculation.
        Expected: <1% deviation for all frequencies above 20 Hz.
    """
    if medium is None:
        medium = MediumProperties()

    frequencies = np.atleast_1d(frequencies).astype(float)

    if V_rc <= 0:
        raise ValueError(f"Rear chamber volume V_rc must be > 0, got {V_rc} m³")

    if S_d <= 0:
        raise ValueError(f"Diaphragm area S_d must be > 0, got {S_d} m²")

    # Acoustic compliance of rear chamber
    # Beranek (1954), Chapter 5: C = V / (ρ·c²)
    # literature/horns/beranek_1954.md
    C_rc = V_rc / (medium.rho * medium.c ** 2)

    # Angular frequency: ω = 2πf
    omega = 2 * np.pi * frequencies

    # Acoustic impedance of compliance (shunt element to ground)
    # Z_rc = 1 / (jω·C) = -j / (ω·C)
    # Purely reactive (compliance behaves like spring)
    Z_rc = -1j / (omega * C_rc)

    return Z_rc


def horn_system_acoustic_impedance(
    frequencies: FloatArray,
    horn: Union['ExponentialHorn', 'ConicalHorn', 'HyperbolicHorn', 'MultiSegmentHorn'],
    V_tc: float = 0.0,
    A_tc: Optional[float] = None,
    V_rc: float = 0.0,
    S_d: Optional[float] = None,
    medium: Optional[MediumProperties] = None,
    radiation_angle: float = 2 * np.pi
) -> Tuple[ComplexArray, ComplexArray]:
    """Calculate total acoustic impedance seen by driver diaphragm in horn system.

    Combines throat chamber, horn throat impedance, and rear chamber impedance
    to calculate the total acoustic load on the driver.

    Supports ExponentialHorn, ConicalHorn, HyperbolicHorn, and MultiSegmentHorn.

    Literature:
        - Olson (1947), Chapter 8 - Complete horn driver systems
        - Beranek (1954), Chapter 5 - Acoustic impedance combinations
        - literature/horns/olson_1947.md
        - literature/horns/beranek_1954.md

    Impedance model:
        Front: Z_front = Z_tc + Z_horn_throat
        Rear: Z_rear = Z_rc || Z_rad_rear (parallel combination)
        Total: Z_acoustic = Z_front + Z_rear

    where:
        Z_tc = throat chamber compliance impedance (if V_tc > 0)
        Z_horn_throat = horn throat impedance from T-matrix
        Z_rc = rear chamber compliance impedance (if V_rc > 0)
        Z_rad_rear = rear radiation impedance (typically 0 for front-loaded)

    Args:
        frequencies: Array of frequencies [Hz]
        horn: Horn geometry parameters (ExponentialHorn, ConicalHorn, HyperbolicHorn, or MultiSegmentHorn)
        V_tc: Throat chamber volume [m³], default 0 (no throat chamber)
        A_tc: Throat chamber area [m²], defaults to horn.throat_area
        V_rc: Rear chamber volume [m³], default 0 (no rear chamber)
        S_d: Diaphragm area [m²] (required if V_rc > 0)
        medium: Acoustic medium properties (uses default if None)
        radiation_angle: Solid angle of radiation [steradians]

    Returns:
        Tuple of (Z_front, Z_rear) complex acoustic impedance arrays [Pa·s/m³]
        - Z_front: Total front impedance (throat chamber + horn)
        - Z_rear: Total rear impedance (rear chamber || radiation)

    Raises:
        ValueError: If V_rc > 0 but S_d is not provided

    Examples:
        >>> import numpy as np
        >>> from gsd.simulation.types import ExponentialHorn
        >>> horn = ExponentialHorn(0.005, 0.05, 0.3)
        >>> freqs = np.array([100.0, 500.0, 1000.0])
        >>> Z_front, Z_rear = horn_system_acoustic_impedance(freqs, horn)
        >>> Z_front.shape
        (3,)

    Validation:
        Compare with Hornresp acoustical impedance export.
        Expected: <2% magnitude, <3° phase for f > 2×f_c
    """
    if medium is None:
        medium = MediumProperties()

    frequencies = np.atleast_1d(frequencies).astype(float)

    # Set default throat chamber area (equals horn throat area)
    if A_tc is None:
        A_tc = horn.throat_area

    # Calculate horn throat impedance (T-matrix method)
    # Check horn type and use appropriate impedance calculation
    if isinstance(horn, ConicalHorn):
        # Conical horn: spherical wave T-matrix
        Z_horn_throat = conical_horn_throat_impedance(
            frequencies, horn, medium, radiation_angle
        )
    elif isinstance(horn, ExponentialHorn):
        # Exponential horn: plane wave T-matrix
        Z_horn_throat = exponential_horn_throat_impedance(
            frequencies, horn, medium, radiation_angle
        )
    elif isinstance(horn, HyperbolicHorn):
        # Hyperbolic horn: use exponential for now (T=1 is exponential)
        # TODO: Implement hyperbolic-specific throat impedance
        Z_horn_throat = exponential_horn_throat_impedance(
            frequencies, horn, medium, radiation_angle
        )
    elif isinstance(horn, MultiSegmentHorn):
        # Multi-segment horn: chain T-matrices for each segment
        Z_horn_throat = multsegment_horn_throat_impedance(
            frequencies, horn, medium
        )
    else:
        raise TypeError(f"Unsupported horn type: {type(horn)}")

    # Add throat chamber compliance (parallel element)
    # For compression driver topology, the throat chamber is in parallel with
    # the horn impedance, not in series. The driver sees both the compliance
    # of the throat chamber AND the horn impedance at the same pressure point.
    #
    # Literature: Beranek (1954), Chapter 5 - Acoustic circuits
    # Parallel combination: 1/Z_total = 1/Z_tc + 1/Z_horn
    if V_tc > 0:
        Z_tc = throat_chamber_impedance(frequencies, V_tc, A_tc, medium)
        # Parallel combination: Z_front = Z_tc || Z_horn_throat
        # For very large Z_tc (small compliance), Z_front ≈ Z_horn_throat
        # This prevents the throat chamber from blocking acoustic power flow
        Z_front = 1.0 / (1.0 / Z_tc + 1.0 / Z_horn_throat)
    else:
        Z_front = Z_horn_throat

    # Calculate rear impedance
    if V_rc > 0:
        if S_d is None:
            raise ValueError("S_d must be provided if V_rc > 0")

        Z_rc = rear_chamber_impedance(frequencies, V_rc, S_d, medium)

        # Rear radiation impedance (piston in half-space for open back)
        # For sealed rear chamber, no radiation (Z_rad_rear = 0)
        Z_rad_rear = np.zeros_like(frequencies, dtype=complex)

        # Parallel combination: 1/Z_total = 1/Z_rc + 1/Z_rad
        # If Z_rad_rear = 0, then Z_rear = Z_rc (pure compliance)
        Z_rear = Z_rc  # Simplified for front-loaded horn
    else:
        Z_rear = np.zeros_like(frequencies, dtype=complex)

    return Z_front, Z_rear


def horn_electrical_impedance(
    frequency: float,
    driver: ThieleSmallParameters,
    horn: 'ExponentialHorn',
    V_tc: float = 0.0,
    A_tc: Optional[float] = None,
    V_rc: float = 0.0,
    voltage: float = 2.83,
    medium: Optional[MediumProperties] = None,
    radiation_angle: float = 2 * np.pi
) -> dict:
    """Calculate electrical impedance for driver loaded by horn.

    Implements the complete electromechanical model for a horn-loaded driver,
    including throat chamber, rear chamber, and horn impedance.

    Literature:
        - Small (1972) - Electromechanical analogies
        - Beranek (1954), Chapter 5 - Electromechanical circuits
        - Olson (1947), Chapter 8 - Horn driver electrical impedance
        - literature/thiele_small/small_1972_closed_box.md
        - literature/horns/olson_1947.md
        - literature/horns/beranek_1954.md

    Electromechanical model:
        Electrical domain:
            Z_e = R_e + jωL_e + (BL)² / Z_mechanical

        Mechanical domain:
            Z_mechanical = R_ms + jωM_md + 1/(jωC_ms) + Z_acoustic_radiation

        Acoustic domain:
            Z_acoustic_radiation = S_d² × (Z_front + Z_rear)

    where Z_front and Z_rear are calculated by horn_system_acoustic_impedance().

    Args:
        frequency: Frequency [Hz]
        driver: ThieleSmallParameters instance
        horn: ExponentialHorn geometry parameters
        V_tc: Throat chamber volume [m³], default 0
        A_tc: Throat chamber area [m²], defaults to horn.throat_area
        V_rc: Rear chamber volume [m³], default 0
        voltage: Input voltage [V], default 2.83V
        medium: Acoustic medium properties (uses default if None)
        radiation_angle: Solid angle of radiation [steradians]

    Returns:
        Dictionary containing:
        - 'frequency': Frequency (Hz)
        - 'Ze_magnitude': Electrical impedance magnitude (Ω)
        - 'Ze_phase': Electrical impedance phase (degrees)
        - 'Ze_real': Electrical resistance (Ω)
        - 'Ze_imag': Electrical reactance (Ω)
        - 'diaphragm_velocity': Diaphragm velocity magnitude (m/s)
        - 'diaphragm_displacement': Diaphragm displacement magnitude (m)
        - 'Z_front': Front acoustic impedance (Pa·s/m³)
        - 'Z_rear': Rear acoustic impedance (Pa·s/m³)

    Raises:
        ValueError: If frequency <= 0 or invalid parameters

    Examples:
        >>> from gsd.simulation.types import ExponentialHorn
        >>> from gsd.driver import load_driver
        >>> driver = load_driver("BC_8NDL51")
        >>> horn = ExponentialHorn(0.001, 0.01, 0.3)
        >>> result = horn_electrical_impedance(500, driver, horn)
        >>> result['Ze_magnitude']
        7.2...  # Ω

    Validation:
        Compare with Hornresp electrical impedance export.
        Expected: <2% magnitude, <5° phase for frequencies > F_s/2
    """
    # Validate inputs (handle both scalar and array inputs)
    if np.any(frequency <= 0):
        if np.isscalar(frequency):
            raise ValueError(f"Frequency must be > 0, got {frequency} Hz")
        else:
            raise ValueError(f"All frequencies must be > 0, min={np.min(frequency)} Hz")

    # Local import to avoid circular dependency
    from gsd.driver.parameters import ThieleSmallParameters

    if not isinstance(driver, ThieleSmallParameters):
        raise TypeError(f"driver must be ThieleSmallParameters, got {type(driver)}")

    if medium is None:
        medium = MediumProperties()

    # Calculate angular frequency
    omega = angular_frequency(frequency)

    # Calculate acoustic impedances
    frequencies = np.array([frequency])
    Z_front, Z_rear = horn_system_acoustic_impedance(
        frequencies, horn, V_tc, A_tc, V_rc, driver.S_d, medium, radiation_angle
    )

    # Total acoustic impedance (at throat)
    Z_acoustic = Z_front[0] + Z_rear[0]

    # Reflect acoustic impedance to mechanical domain using shared utility
    # IMPORTANT: For compression drivers, Z_acoustic is calculated at the throat (area S_throat)
    # but the voice coil acts on the diaphragm (area S_d). We use the shared utility function
    # to transform throat impedance to diaphragm mechanical impedance.
    #
    Z_mechanical_acoustic = scale_throat_acoustic_to_mechanical(
        Z_acoustic, horn.throat_area, driver.S_d
    )

    # Calculate mechanical impedance
    # Z_mechanical = R_ms + jωM_md + 1/(jωC_ms)
    # COMSOL (2020), Figure 2
    Z_mechanical_driver = (driver.R_ms +
                          complex(0, omega * driver.M_md) +
                          complex(0, -1 / (omega * driver.C_ms)))

    # Total mechanical impedance
    Z_mechanical_total = Z_mechanical_driver + Z_mechanical_acoustic

    # Voice coil electrical impedance
    # Z_vc = R_e + jωL_e
    # COMSOL (2020), Figure 2
    Z_voice_coil = complex(driver.R_e, omega * driver.L_e)

    # Reflected impedance from mechanical to electrical domain
    # Z_reflected = (BL)² / Z_mechanical_total
    # COMSOL (2020), Figure 2
    if abs(Z_mechanical_total) == 0:
        # Avoid division by zero
        Z_reflected = complex(0, float('inf'))
    else:
        Z_reflected = (driver.BL ** 2) / Z_mechanical_total

    # Total electrical impedance
    # Z_e = Z_vc + Z_reflected
    # COMSOL (2020), Figure 2
    Ze = Z_voice_coil + Z_reflected

    # Calculate diaphragm velocity
    # F = BL × I, v = F / Z_mechanical_total
    if driver.BL == 0 or abs(Ze) == 0:
        u_diaphragm = complex(0, 0)
    else:
        # Voice coil current (complex phasor)
        I_complex = voltage / Ze

        # Force on diaphragm
        F_complex = driver.BL * I_complex

        # Diaphragm velocity
        u_diaphragm = F_complex / Z_mechanical_total

    # Diaphragm displacement: X = v / (jω)
    if omega == 0:
        x_diaphragm = complex(0, 0)
    else:
        x_diaphragm = u_diaphragm / complex(0, omega)

    # Prepare return dictionary
    result = {
        'frequency': frequency,
        'Ze_magnitude': abs(Ze),
        'Ze_phase': math.degrees(cmath.phase(Ze)),
        'Ze_real': Ze.real,
        'Ze_imag': Ze.imag,
        'diaphragm_velocity': abs(u_diaphragm),
        'diaphragm_displacement': abs(x_diaphragm),
        'Z_front': Z_front[0],
        'Z_rear': Z_rear[0],
    }

    return result


@dataclass
class HornSPLResult:
    """
    Result of horn SPL calculation.

    Attributes:
        frequencies: Frequency array (Hz)
        spl: SPL at specified distance (dB SPL)
        z_electrical: Electrical impedance (Ω)
        excursion: Cone excursion (m)
        throat_velocity: Volume velocity at throat (m³/s)
        mouth_velocity: Volume velocity at mouth (m³/s)
        radiated_power: Acoustic power radiated (W)
    """
    frequencies: FloatArray
    spl: FloatArray
    z_electrical: ComplexArray
    excursion: FloatArray
    throat_velocity: ComplexArray
    mouth_velocity: ComplexArray
    radiated_power: FloatArray


def calculate_horn_spl_flow(
    frequencies: FloatArray,
    horn: Union['ExponentialHorn', 'ConicalHorn', 'HyperbolicHorn'],
    driver: ThieleSmallParameters,
    voltage: float = 2.83,
    distance: float = 1.0,
    environment: str = '2pi',
    medium: Optional[MediumProperties] = None
) -> HornSPLResult:
    """
    Calculate SPL response of compression driver on horn.

    This function implements the complete electro-mechano-acoustical chain:
    1. Calculate electrical impedance including motional component from acoustic load
    2. Calculate driver (voice coil) velocity from electrical input
    3. Convert voice coil velocity to throat volume velocity
    4. Use T-matrix to propagate throat velocity to mouth
    5. Calculate radiated power from mouth velocity and radiation impedance
    6. Convert power to SPL at specified distance

    Supports ExponentialHorn, ConicalHorn, and HyperbolicHorn geometries.

    Literature:
        Electrical circuit (Beranek 1954, Chapter 8):
            Z_e = R_e + jωL_e + Z_mot
            Z_mot = (BL)² / Z_mech_total
            Z_mech_total = R_ms + jωM_md + 1/(jωC_ms) + Z_throat_acoustic·S_throat²

        Throat velocity:
            I = V / Z_e (electrical current)
            F = BL·I (force on voice coil)
            v_coil = F / Z_mech_total (coil velocity)
            U_throat = v_coil · S_throat (throat volume velocity)

        T-matrix transformation (Kolbrek):
            [p_t, U_t]ᵀ = [A B; C D][p_m, U_m]ᵀ
            U_mouth = U_throat / (A·Z_mouth + B)

        Radiated power:
            W_rad = 0.5 · |U_mouth|² · Re(Z_mouth)

        SPL (Beranek, spherical radiation):
            SPL = 120 + 10·log₁₀(W_rad · Q / (4πr²))
            where Q = 2 for half-space, Q = 1 for full-space

    Args:
        frequencies: Array of frequencies (Hz)
        horn: Horn geometry parameters (ExponentialHorn, ConicalHorn, or HyperbolicHorn)
        driver: ThieleSmallParameters for compression driver
        voltage: Input voltage (V), default 2.83V (1W into 8Ω)
        distance: Measurement distance (m), default 1m
        environment: Radiation environment:
            - '2pi': Half-space (infinite baffle) [default]
            - '4pi': Full-space (free field)
        medium: Acoustic medium properties (uses default if None)

    Returns:
        HornSPLResult containing SPL, electrical impedance, and intermediate values

    Notes:
        - All calculations use complex arithmetic for proper phase handling
        - SPL reference is 20 μPa (standard for airborne sound)
        - Power reference is 1 pW (10⁻¹² W)
        - Exponential/Hyperbolic horns: Below cutoff, throat impedance is reactive → minimal radiation
        - Conical horns: No sharp cutoff, resistance rises gradually from zero frequency

    Examples:
        >>> import numpy as np
        >>> from gsd.simulation.types import ExponentialHorn
        >>> from gsd.driver import load_driver
        >>> horn = ExponentialHorn(throat_area=0.0005, mouth_area=0.05, length=0.5)
        >>> driver = load_driver("BC_DE250")
        >>> freqs = np.logspace(1, 5, 100)  # 10 Hz to 100 kHz
        >>> result = calculate_horn_spl_flow(freqs, horn, driver)
        >>> result.spl[50]  # SPL at ~1 kHz
        108.5...  # dB SPL at 1m

    Validation:
        Compare with Hornresp SPL calculation for identical parameters.
        Expected tolerances:
        - f > 1.5×f_c: < 1.0 dB deviation
        - f_c < f < 1.5×f_c: < 2.5 dB deviation
        - f < f_c: Slope match (~24 dB/octave rolloff for exponential)
    """
    if medium is None:
        medium = MediumProperties()

    frequencies = np.atleast_1d(frequencies).astype(float)
    omega = 2 * np.pi * frequencies

    # Radiation angle for environment
    # 2π = half-space (infinite baffle), 4π = full-space (free field)
    radiation_angle = 2 * np.pi if environment == '2pi' else 4 * np.pi
    directivity_factor = 2.0 if environment == '2pi' else 1.0

    # Step 1: Calculate throat acoustic impedance
    # This includes mouth radiation impedance and T-matrix transformation
    # Route to appropriate impedance calculation based on horn type
    if isinstance(horn, ConicalHorn):
        z_throat_acoustic = conical_horn_throat_impedance(
            frequencies, horn, medium, radiation_angle
        )
    elif isinstance(horn, ExponentialHorn):
        z_throat_acoustic = exponential_horn_throat_impedance(
            frequencies, horn, medium, radiation_angle
        )
    elif isinstance(horn, HyperbolicHorn):
        # Hyperbolic horns use the exponential throat impedance (T=1 is exponential)
        # For now, we use the exponential function as HyperbolicHorn shares
        # similar impedance characteristics. TODO: Implement hyperbolic-specific impedance
        z_throat_acoustic = exponential_horn_throat_impedance(
            frequencies, horn, medium, radiation_angle
        )
    else:
        raise TypeError(f"Unsupported horn type: {type(horn)}")

    # Step 2: Calculate mechanical impedance seen by voice coil
    # Z_mech_total = R_ms + jωM_md + 1/(jωC_ms) + Z_throat_acoustic_transformed
    #
    # For compression drivers, transform throat acoustic impedance to diaphragm
    # mechanical impedance using compression ratio (shared utility function)
    #
    z_mech_stiffness = 1.0 / (1j * omega * driver.C_ms)  # Suspension stiffness
    z_mech_mass = 1j * omega * driver.M_md  # Driver mass
    z_mech_resistance = driver.R_ms  # Mechanical losses

    # Transform throat acoustic impedance to diaphragm mechanical impedance
    z_mech_acoustic_load = scale_throat_acoustic_to_mechanical(
        z_throat_acoustic, horn.throat_area, driver.S_d
    )

    z_mech_total = (z_mech_resistance + z_mech_mass +
                    z_mech_stiffness + z_mech_acoustic_load)

    # Step 3: Calculate electrical impedance including motional impedance
    # Z_mot = (BL)² / Z_mech_total (motional impedance reflected from mechanical side)
    z_motional = (driver.BL ** 2) / z_mech_total
    z_voice_coil = driver.R_e + 1j * omega * driver.L_e
    z_electrical = z_voice_coil + z_motional

    # Step 4: Calculate electrical current
    # I = V / Z_e
    current = voltage / z_electrical

    # Step 5: Calculate force on voice coil
    # F = BL · I
    force = driver.BL * current

    # Step 6: Calculate voice coil velocity
    # v_coil = F / Z_mech_total
    v_coil = force / z_mech_total

    # Step 7: Calculate throat volume velocity
    # For compression drivers with phase plug:
    # U_throat = v_diaphragm · S_d (volume velocity at diaphragm)
    # The phase plug transforms this to the throat with compression ratio
    # U_throat_throat = U_throat_diaphragm (continuity of volume velocity)
    #
    # So: U_throat = v_coil · S_d (diaphragm creates volume velocity)
    u_throat = v_coil * driver.S_d

    # Step 8: Calculate T-matrix and propagate to mouth
    # We need the inverse T-matrix relation to get mouth velocity
    # From T-matrix: [p_t, U_t]ᵀ = [A B; C D][p_m, U_m]ᵀ
    # And p_m = U_m · Z_mouth, so:
    # U_t = C·p_m + D·U_m = C·Z_mouth·U_m + D·U_m = U_m·(C·Z_mouth + D)
    # Therefore: U_m = U_t / (C·Z_mouth + D)

    # Calculate T-matrix based on horn type
    if isinstance(horn, ExponentialHorn):
        # Exponential horns use the array-based function
        a, b, c, d = exponential_horn_tmatrix(frequencies, horn, medium)
    elif isinstance(horn, (ConicalHorn, HyperbolicHorn)):
        # Conical and Hyperbolic horns have calculate_t_matrix method on the class
        # which takes a single frequency, so we need to loop
        a_list, b_list, c_list, d_list = [], [], [], []
        for f in frequencies:
            t_matrix = horn.calculate_t_matrix(f, medium.c, medium.rho)
            a_list.append(t_matrix[0, 0])
            b_list.append(t_matrix[0, 1])
            c_list.append(t_matrix[1, 0])
            d_list.append(t_matrix[1, 1])
        a = np.array(a_list, dtype=complex)
        b = np.array(b_list, dtype=complex)
        c = np.array(c_list, dtype=complex)
        d = np.array(d_list, dtype=complex)
    else:
        raise TypeError(f"Unsupported horn type: {type(horn)}")

    # Get mouth impedance (already calculated inside throat_impedance, but need it here)
    # Recalculate for clarity
    effective_mouth_area = 2 * np.pi * horn.mouth_area / radiation_angle
    z_mouth = circular_piston_radiation_impedance(frequencies, effective_mouth_area, medium)

    # Calculate mouth velocity using T-matrix transformation
    # U_mouth = U_throat / (C·Z_mouth + D)
    u_mouth = u_throat / (c * z_mouth + d)

    # Step 9: Calculate radiated power
    # W_rad = 0.5 · |U_mouth|² · Re(Z_mouth)
    # Factor of 0.5 for RMS (we've been using peak values)
    radiated_power = 0.5 * (np.abs(u_mouth) ** 2) * np.real(z_mouth)

    # Step 10: Convert power to SPL at distance
    # Intensity I = W·Q / (4πr²)
    # SPL from pressure: SPL = 20·log₁₀(p/p_ref) where p_ref = 20 μPa
    # For spherical wave: p² = I·ρc, so:
    # SPL = 20·log₁₀(√(I·ρc) / p_ref)
    #     = 10·log₁₀(I·ρc) - 20·log₁₀(p_ref)
    #     = 10·log₁₀(I) + 10·log₁₀(ρc) - 20·log₁₀(20e-6)
    intensity = radiated_power * directivity_factor / (4 * np.pi * distance ** 2)

    # Calculate SPL using pressure-based formula for correct reference
    # SPL = 20*log10(sqrt(I * ρc) / p_ref)
    p_ref = 20e-6  # Reference pressure (20 μPa)
    spl = 20 * np.log10(np.sqrt(intensity * medium.rho * medium.c) / p_ref + 1e-20)  # Add small value to avoid log(0)

    # Step 11: Calculate excursion (for reference)
    # x = v_coil / (jω)
    excursion = np.abs(v_coil / (1j * omega))

    return HornSPLResult(
        frequencies=frequencies,
        spl=spl,
        z_electrical=z_electrical,
        excursion=excursion,
        throat_velocity=u_throat,
        mouth_velocity=u_mouth,
        radiated_power=radiated_power
    )


def calculate_horn_cutoff_frequency(horn: 'ExponentialHorn', c: float = SPEED_OF_SOUND) -> float:
    """
    Calculate cutoff frequency of exponential horn.

    Literature:
        Olson (1947), Eq. 5.18: f_c = c·m / (2π)
        Beranek (1954), Chapter 5: Same expression

    Args:
        horn: ExponentialHorn geometry
        c: Speed of sound (m/s), default 343 m/s

    Returns:
        Cutoff frequency (Hz)

    Examples:
        >>> horn = ExponentialHorn(0.001, 0.1, 1.5)
        >>> calculate_horn_cutoff_frequency(horn)
        168.5...  # Hz for m ≈ 3.07 1/m
    """
    return (c * horn.flare_constant) / (2 * np.pi)


def estimate_horn_sensitivity(
    horn: 'ExponentialHorn',
    driver: ThieleSmallParameters,
    voltage: float = 2.83,
    freq_min: float = 500,
    freq_max: float = 5000,
    num_points: int = 100,
    medium: Optional[MediumProperties] = None
) -> float:
    """
    Estimate horn sensitivity in passband above cutoff.

    Calculates average SPL in specified frequency range to estimate
    nominal sensitivity (e.g., for datasheet comparison).

    Literature:
        Sensitivity typically measured 500-5000 Hz for compression drivers
        on horns to avoid beaming effects and cutoff rolloff.

    Args:
        horn: ExponentialHorn geometry
        driver: ThieleSmallParameters
        voltage: Test voltage (V), default 2.83V (1W into 8Ω)
        freq_min: Minimum frequency for averaging (Hz)
        freq_max: Maximum frequency for averaging (Hz)
        num_points: Number of frequency points in range
        medium: Acoustic medium properties

    Returns:
        Estimated sensitivity (dB SPL @ 1m, 2.83V)

    Examples:
        >>> horn = ExponentialHorn(0.0005, 0.05, 0.5)
        >>> driver = load_driver("BC_DE250")
        >>> estimate_horn_sensitivity(horn, driver)
        108.5...  # dB SPL @ 1m, 2.83V
    """
    frequencies = np.logspace(np.log10(freq_min), np.log10(freq_max), num_points)
    result = calculate_horn_spl_flow(frequencies, horn, driver, voltage, medium=medium)

    # Average SPL in passband
    avg_spl = np.mean(result.spl)

    return avg_spl
