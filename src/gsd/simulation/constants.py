"""
Physical constants for acoustic simulations.

This module defines standard conditions and physical constants used
throughout the gsd simulation code. All values are cited from
the literature.

Literature:
- Kinsler et al. (1982), Chapter 1 - Standard atmospheric conditions
- Beranek (1954), Chapter 1 - Physical properties of air
- Olson (1947), Chapter 1 - Acoustic constants

Validation:
    Values match standard references (Kinsler, Beranek) within
    significant figures.
"""

# Standard conditions at 20°C, 1 atm (sea level)
# From Kinsler et al. (1982), "Fundamentals of Acoustics", Chapter 1
# Table 1.1: Properties of Air
SPEED_OF_SOUND = 343.0  # c: Speed of sound in air (m/s) at 20°C
AIR_DENSITY = 1.18  # ρ₀: Density of air (kg/m³) at 20°C, 1 atm
ATMOSPHERIC_PRESSURE = 101325  # P₀: Standard atmospheric pressure (Pa)

# Acoustic impedance of free space
# Z₀ = ρ₀c (characteristic impedance of air)
# Kinsler et al. (1982), Eq. 1.11
CHARACTERISTIC_IMPEDANCE_AIR = AIR_DENSITY * SPEED_OF_SOUND  # ~405 rayl

# Universal constants
PI = 3.141592653589793


def wavenumber(frequency: float, speed_of_sound: float = SPEED_OF_SOUND) -> float:
    """
    Calculate wavenumber from frequency.

    k = ω/c = 2πf/c

    Literature:
        - Kinsler et al. (1982), Chapter 1 - Wave equation fundamentals
        - Beranek (1954), Chapter 1 - Wavenumber definition

    Args:
        frequency: Frequency in Hz
        speed_of_sound: Speed of sound in m/s, default 343 m/s at 20°C

    Returns:
        Wavenumber k in radians/meter

    Examples:
        >>> wavenumber(1000)
        18.320...  # rad/m for 1 kHz at 20°C

        >>> wavenumber(343)  # frequency where wavelength = 1 m
        6.283...  # = 2π
    """
    return 2 * PI * frequency / speed_of_sound


def angular_frequency(frequency: float) -> float:
    """
    Calculate angular frequency from frequency.

    ω = 2πf

    Literature:
        - Kinsler et al. (1982), Chapter 1 - Harmonic motion
        - Beranek (1954), Chapter 1 - Time dependence

    Args:
        frequency: Frequency in Hz

    Returns:
        Angular frequency ω in radians/second

    Examples:
        >>> angular_frequency(1000)
        6283.185...  # rad/s for 1 kHz
    """
    return 2 * PI * frequency


def wavelength(frequency: float, speed_of_sound: float = SPEED_OF_SOUND) -> float:
    """
    Calculate wavelength from frequency.

    λ = c/f

    Literature:
        - Kinsler et al. (1982), Chapter 1 - Wave propagation
        - Beranek (1954), Chapter 1 - Wavelength definition

    Args:
        frequency: Frequency in Hz
        speed_of_sound: Speed of sound in m/s, default 343 m/s at 20°C

    Returns:
        Wavelength λ in meters

    Examples:
        >>> wavelength(343)
        1.0  # 1 meter wavelength for 343 Hz
    """
    return speed_of_sound / frequency
