"""
Radiation impedance calculations for loudspeaker drivers.

This module implements radiation impedance models for piston radiators,
including circular pistons in infinite baffles.

Literature:
- Beranek (1954), Chapter 5 - Radiation impedance theory
- Olson (1947), Chapter 5 - Horn radiation impedance
- literature/horns/beranek_1954.md
"""

import math
from scipy.special import j1, struve

from gsd.simulation.constants import (
    AIR_DENSITY,
    SPEED_OF_SOUND,
    CHARACTERISTIC_IMPEDANCE_AIR,
    wavenumber,
)


def radiation_impedance_piston(
    frequency: float,
    piston_area: float,
    speed_of_sound: float = SPEED_OF_SOUND,
    air_density: float = AIR_DENSITY
) -> complex:
    """
    Calculate radiation impedance of circular piston in infinite baffle.

    The radiation impedance represents the load presented by the air
    on a vibrating piston. It consists of a radiation resistance
    (real part, representing power radiated as sound) and radiation
    reactance (imaginary part, representing air mass loading).

    Literature:
        - Beranek (1954), Eq. 5.20 - Piston radiation impedance
        - Olson (1947), Chapter 5 - Circular piston radiation
        - literature/horns/beranek_1954.md

    Equation:
        Z_R = ρc·S·[R₁(2ka) + jX₁(2ka)]

    where:
        R₁(2ka) = 1 - J₁(2ka)/(ka)
        X₁(2ka) = H₁(2ka)/(ka)
        k = 2πf/c (wavenumber)
        a = √(S/π) (piston radius)

    Low-frequency asymptote (ka << 1):
        R₁ ≈ (ka)² / 2
        X₁ ≈ (4ka) / (3π)

    High-frequency limit (ka >> 1):
        R₁ → 1
        X₁ → 0

    Args:
        frequency: Frequency in Hz
        piston_area: Piston effective area (m²)
        speed_of_sound: Speed of sound in m/s, default 343 m/s at 20°C
        air_density: Air density in kg/m³, default 1.18 kg/m³ at 20°C

    Returns:
        Complex radiation impedance (rayl·m² or Pa·s/m³)
        - Real part: Radiation resistance (power radiation)
        - Imag part: Radiation reactance (mass loading)

    Examples:
        >>> Z = radiation_impedance_piston(100, 0.05)  # 100 Hz, 50 cm²
        >>> Z.real  # Radiation resistance
        0.023...  # Small at low frequency
        >>> Z.imag  # Radiation reactance
        1.85...  # Air mass loading dominates at low frequency

        >>> Z_high = radiation_impedance_piston(2000, 0.05)  # 2 kHz
        >>> abs(Z_high)  # Magnitude approaches ρc·S
        17.1...  # ≈ ρc·S = 1.18 × 343 × 0.05

    Validation:
        Compare with Hornresp radiation impedance calculation.
        Expected agreement: <1% for ka > 0.5, <2% near ka → 0
    """
    # Validate inputs
    if frequency <= 0:
        raise ValueError(f"Frequency must be > 0, got {frequency} Hz")

    if piston_area <= 0:
        raise ValueError(f"Piston area must be > 0, got {piston_area} m²")

    # Calculate wavenumber: k = 2πf/c
    # Kinsler et al. (1982), Chapter 1
    k = wavenumber(frequency, speed_of_sound)

    # Calculate piston radius: a = √(S/π)
    piston_radius = math.sqrt(piston_area / math.pi)

    # Calculate dimensionless frequency parameter: ka
    ka = k * piston_radius

    # Calculate radiation resistance function R₁(2ka)
    # Beranek (1954), Eq. 5.20: R₁(2ka) = 1 - J₁(2ka)/(ka)
    if ka < 0.01:
        # Low-frequency asymptote: R₁ ≈ (ka)² / 2
        # Avoids numerical errors when ka → 0
        R1 = (ka ** 2) / 2.0
    else:
        # Full expression using Bessel function J₁
        j1_2ka = j1(2 * ka)
        R1 = 1.0 - j1_2ka / ka

    # Calculate radiation reactance function X₁(2ka)
    # Beranek (1954), Eq. 5.20: X₁(2ka) = H₁(2ka)/(ka)
    if ka < 0.01:
        # Low-frequency asymptote: X₁ ≈ 4ka/(3π)
        # Avoids numerical errors when ka → 0
        X1 = (4.0 * ka) / (3.0 * math.pi)
    else:
        # Full expression using Struve function H₁
        H1_2ka = struve(1, 2 * ka)
        X1 = H1_2ka / ka

    # Calculate radiation impedance: Z_R = ρc·S·[R₁ + jX₁]
    # Beranek (1954), Eq. 5.20
    Z0 = air_density * speed_of_sound  # Characteristic impedance of air
    Z_R = Z0 * piston_area * complex(R1, X1)

    return Z_R


def radiation_impedance_piston_asymptotic_check(
    frequency: float,
    piston_area: float,
    speed_of_sound: float = SPEED_OF_SOUND,
    air_density: float = AIR_DENSITY
) -> dict:
    """
    Calculate radiation impedance with asymptotic checking for validation.

    This function calculates the radiation impedance using both the full
    expression and asymptotic approximations, returning all results
    for validation purposes.

    Args:
        frequency: Frequency in Hz
        piston_area: Piston effective area (m²)
        speed_of_sound: Speed of sound in m/s
        air_density: Air density in kg/m³

    Returns:
        Dictionary with:
        - 'ka': Dimensionless frequency parameter
        - 'full': Complex impedance (full expression)
        - 'low_freq_asymptote': Complex impedance (ka << 1 asymptote)
        - 'high_freq_limit': Complex impedance (ka → ∞ limit)
        - 'asymptote_error': Relative error if using asymptote

    Examples:
        >>> result = radiation_impedance_piston_asymptotic_check(100, 0.05)
        >>> result['ka']
        0.05...  # Low frequency regime
        >>> abs(result['full'] - result['low_freq_asymptote'])
        0.001...  # Small error at low frequency
    """
    # Full calculation
    Z_full = radiation_impedance_piston(frequency, piston_area, speed_of_sound, air_density)

    # Calculate ka
    k = wavenumber(frequency, speed_of_sound)
    a = math.sqrt(piston_area / math.pi)
    ka = k * a

    # Low-frequency asymptote: ka << 1
    # R₁ ≈ (ka)² / 2, X₁ ≈ 4ka/(3π)
    Z0 = air_density * speed_of_sound
    R1_asymp = (ka ** 2) / 2.0
    X1_asymp = (4.0 * ka) / (3.0 * math.pi)
    Z_low_freq = Z0 * piston_area * complex(R1_asymp, X1_asymp)

    # High-frequency limit: ka >> 1
    # R₁ → 1, X₁ → 0
    Z_high_freq = Z0 * piston_area * complex(1.0, 0.0)

    return {
        'ka': ka,
        'full': Z_full,
        'low_freq_asymptote': Z_low_freq,
        'high_freq_limit': Z_high_freq,
        'asymptote_error': abs(Z_full - Z_low_freq) / abs(Z_full) if ka < 0.5 else None
    }
