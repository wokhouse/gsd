"""
Radiation mass calculations for loudspeaker drivers.

This module implements the frequency-dependent radiation mass loading
for pistons in infinite baffles, following Beranek (1954) and matching
Hornresp's empirical methodology.

Literature:
- Beranek (1954), Eq. 5.20 - Radiation impedance and reactance
- literature/horns/beranek_1954.md
"""

import math
from scipy.special import struve

from gsd.simulation.constants import AIR_DENSITY, SPEED_OF_SOUND


def calculate_radiation_mass(
    frequency: float,
    piston_area: float,
    air_density: float = AIR_DENSITY,
    speed_of_sound: float = SPEED_OF_SOUND
) -> float:
    """
    Calculate frequency-dependent radiation mass for circular piston.

    The radiation mass represents the additional air mass that moves
    with the piston, derived from the radiation reactance component
    of Beranek's radiation impedance equation.

    Literature:
        Beranek (1954), Eq. 5.20: Z_R = ρc·S·[R₁(2ka) + jX₁(2ka)]
        Reactance: X = ω·M_rad
        Therefore: M_rad = X / ω = (ρc·S·X₁) / ω

    Args:
        frequency: Frequency in Hz
        piston_area: Effective piston area (m²)
        air_density: Air density (kg/m³), default 1.18
        speed_of_sound: Speed of sound (m/s), default 343

    Returns:
        Radiation mass (kg)

    Raises:
        ValueError: If frequency <= 0 or piston_area <= 0

    Examples:
        >>> M_rad = calculate_radiation_mass(100, 0.022)  # BC_8NDL51 at 100 Hz
        >>> M_rad * 1000  # Convert to grams
        1.2...  # g
    """
    # Validate inputs
    if frequency <= 0:
        raise ValueError(f"Frequency must be > 0, got {frequency} Hz")

    if piston_area <= 0:
        raise ValueError(f"Piston area must be > 0, got {piston_area} m²")

    # Calculate angular frequency and wavenumber
    omega = 2.0 * math.pi * frequency
    k = omega / speed_of_sound

    # Calculate piston radius
    a = math.sqrt(piston_area / math.pi)
    ka = k * a

    # Beranek (1954), Eq. 5.20: Radiation reactance function
    # X₁(2ka) = H₁(2ka) / (ka)
    # where H₁ is the Struve function of order 1
    if ka < 0.01:
        # Low-frequency asymptote: X₁ ≈ 8ka/(3π)
        # Avoids numerical errors when ka → 0
        X1 = (8.0 * ka) / (3.0 * math.pi)
    else:
        # Full expression using Struve function
        H1_2ka = struve(1, 2 * ka)
        X1 = H1_2ka / ka

    # Radiation reactance: X_rad = ρc·S·X₁
    # Equivalent mass: M_rad = X_rad / ω
    X_rad = air_density * speed_of_sound * piston_area * X1
    M_rad = X_rad / omega

    return M_rad


def calculate_resonance_with_radiation_mass(
    M_md: float,
    C_ms: float,
    S_d: float,
    air_density: float = AIR_DENSITY,
    speed_of_sound: float = SPEED_OF_SOUND,
    max_iterations: int = 20,
    tolerance_hz: float = 0.1
) -> tuple[float, float]:
    """
    Calculate resonance frequency including radiation mass loading.

    Uses iterative solver to handle circular dependency:
    - F_s = 1/(2π√(M_ms·C_ms))
    - M_ms = M_md + 2×M_rad(f)
    - M_rad depends on frequency

    The 2× radiation mass multiplier accounts for both sides of the infinite
    baffle: the piston radiates into half-space on the front and rear sides,
    each contributing equal radiation mass loading. Total: M_rad,total = 2×M_rad.

    Literature:
        - Beranek (1954), Eq. 5.20 - Radiation impedance
        - Beranek (1954), Chapter 4 - Piston in infinite baffle (both sides radiate)
        - Hornresp methodology - 2× radiation mass for infinite baffle
        - literature/horns/beranek_1954.md

    Args:
        M_md: Driver mass only (voice coil + diaphragm, kg)
        C_ms: Suspension compliance (m/N)
        S_d: Effective piston area (m²)
        air_density: Air density (kg/m³)
        speed_of_sound: Speed of sound (m/s)
        max_iterations: Maximum solver iterations
        tolerance_hz: Frequency convergence tolerance (Hz)

    Returns:
        (F_s, M_ms) tuple:
        - F_s: Resonance frequency (Hz)
        - M_ms: Total effective mass including radiation (kg)

    Raises:
        ValueError: If M_md <= 0, C_ms <= 0, or S_d <= 0

    Examples:
        >>> F_s, M_ms = calculate_resonance_with_radiation_mass(
        ...     0.02677, 2.03e-4, 0.022  # BC_8NDL51 parameters
        ... )
        >>> F_s
        64.1...  # Hz (matches Hornresp)
        >>> M_ms * 1000
        30.2...  # g total mass
    """
    # Validate inputs
    if M_md <= 0:
        raise ValueError(f"Driver mass M_md must be > 0, got {M_md} kg")

    if C_ms <= 0:
        raise ValueError(f"Compliance C_ms must be > 0, got {C_ms} m/N")

    if S_d <= 0:
        raise ValueError(f"Area S_d must be > 0, got {S_d} m²")

    # Start with driver mass only (no radiation mass)
    M_ms = M_md
    F_s_prev = 0.0

    for i in range(max_iterations):
        # Calculate resonance with current mass estimate
        F_s = 1.0 / (2.0 * math.pi * math.sqrt(M_ms * C_ms))

        # Check convergence
        if abs(F_s - F_s_prev) < tolerance_hz:
            break

        F_s_prev = F_s

        # Calculate radiation mass at this frequency
        M_rad = calculate_radiation_mass(F_s, S_d, air_density, speed_of_sound)

        # Update total mass (2× radiation mass for infinite baffle)
        # Both front and rear sides radiate, each contributing equal radiation mass
        M_ms = M_md + 2.0 * M_rad

    # Final resonance calculation
    F_s_final = 1.0 / (2.0 * math.pi * math.sqrt(M_ms * C_ms))

    return F_s_final, M_ms


def calculate_resonance_with_radiation_mass_tuned(
    M_md: float,
    C_ms: float,
    S_d: float,
    radiation_multiplier: float = 2.0,
    air_density: float = AIR_DENSITY,
    speed_of_sound: float = SPEED_OF_SOUND,
    max_iterations: int = 20,
    tolerance_hz: float = 0.1
) -> tuple[float, float]:
    """
    Calculate resonance frequency with configurable radiation mass multiplier.

    Uses iterative solver to handle circular dependency:
    - F_s = 1/(2π√(M_ms·C_ms))
    - M_ms = M_md + radiation_multiplier × M_rad(f)
    - M_rad depends on frequency

    The radiation_multiplier accounts for different enclosure configurations:
    - 2.0 = Infinite baffle (both sides radiate equally)
    - 1.0 = Sealed box (front side only radiates)

    Literature:
        - Beranek (1954), Eq. 5.20 - Radiation impedance and mass loading
        - Beranek (1954), Chapter 4 - Piston in infinite baffle
        - Small (1972) - Closed-box systems (front-side radiation only)
        - Hornresp methodology - 2× for infinite baffle, 1× for sealed box
        - literature/horns/beranek_1954.md
        - literature/thiele_small/small_1972_closed_box.md

    Args:
        M_md: Driver mass only (voice coil + diaphragm, kg)
        C_ms: Suspension compliance (m/N)
        S_d: Effective piston area (m²)
        radiation_multiplier: Radiation mass multiplier
            - 2.0 = Infinite baffle (both front and rear sides radiate)
            - 1.0 = Sealed box (front side only radiates)
            - Other values for specialized configurations
        air_density: Air density (kg/m³)
        speed_of_sound: Speed of sound (m/s)
        max_iterations: Maximum solver iterations
        tolerance_hz: Frequency convergence tolerance (Hz)

    Returns:
        (F_s, M_ms) tuple:
        - F_s: Resonance frequency (Hz)
        - M_ms: Total effective mass including radiation (kg) = M_md + radiation_multiplier × M_rad

    Raises:
        ValueError: If M_md <= 0, C_ms <= 0, S_d <= 0, or radiation_multiplier <= 0

    Examples:
        >>> # Infinite baffle (default, 2× radiation mass)
        >>> F_s_ib, M_ms_ib = calculate_resonance_with_radiation_mass_tuned(
        ...     0.02677, 2.03e-4, 0.022, radiation_multiplier=2.0
        ... )
        >>> F_s_ib
        64.1...  # Hz (matches Hornresp infinite baffle)

        >>> # Sealed box (1× radiation mass, front only)
        >>> F_s_sb, M_ms_sb = calculate_resonance_with_radiation_mass_tuned(
        ...     0.02677, 2.03e-4, 0.022, radiation_multiplier=1.0
        ... )
        >>> F_s_sb
        66.8...  # Hz (higher due to less mass loading)

        >>> # Compare: sealed box has higher Fs due to less radiation mass
        >>> F_s_sb > F_s_ib
        True
    """
    # Validate inputs
    if M_md <= 0:
        raise ValueError(f"Driver mass M_md must be > 0, got {M_md} kg")

    if C_ms <= 0:
        raise ValueError(f"Compliance C_ms must be > 0, got {C_ms} m/N")

    if S_d <= 0:
        raise ValueError(f"Area S_d must be > 0, got {S_d} m²")

    if radiation_multiplier <= 0:
        raise ValueError(f"Radiation multiplier must be > 0, got {radiation_multiplier}")

    # Start with driver mass only (no radiation mass)
    M_ms = M_md
    F_s_prev = 0.0

    for i in range(max_iterations):
        # Calculate resonance with current mass estimate
        F_s = 1.0 / (2.0 * math.pi * math.sqrt(M_ms * C_ms))

        # Check convergence
        if abs(F_s - F_s_prev) < tolerance_hz:
            break

        F_s_prev = F_s

        # Calculate radiation mass at this frequency
        M_rad = calculate_radiation_mass(F_s, S_d, air_density, speed_of_sound)

        # Update total mass with configurable radiation multiplier
        # For infinite baffle: 2.0 × M_rad (both sides radiate)
        # For sealed box: 1.0 × M_rad (front side only)
        M_ms = M_md + radiation_multiplier * M_rad

    # Final resonance calculation
    F_s_final = 1.0 / (2.0 * math.pi * math.sqrt(M_ms * C_ms))

    return F_s_final, M_ms
