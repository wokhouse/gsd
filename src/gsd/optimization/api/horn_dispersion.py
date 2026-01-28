"""
Horn Dispersion Analysis Module

Analyzes directivity patterns of exponential horns for two-way
system integration.

Literature:
- Olson (1947) - Horn directivity patterns
- Beranek (1954) - Radiation from circular pistons
- Morse & Ingard (1968) - Directivity index calculations
"""

import numpy as np
from scipy.special import j1
from typing import Dict, Tuple
from dataclasses import dataclass


@dataclass
class DirectivityResult:
    """
    Result of horn directivity analysis.

    Attributes:
        ka: Size parameter at specified frequency
        directivity_index_db: Directivity index in dB
        beam_width_6db: -6dB beamwidth in degrees
        beam_width_10db: -10dB beamwidth in degrees
        dispersion_quality: Qualitative assessment
    """
    ka: float
    directivity_index_db: float
    beam_width_6db: float
    beam_width_10db: float
    dispersion_quality: str

    def __str__(self) -> str:
        """Return formatted result."""
        return (
            f"Directivity Result:\n"
            f"  ka: {self.ka:.2f}\n"
            f"  Directivity Index: {self.directivity_index_db:.1f} dB\n"
            f"  -6dB Beamwidth: {self.beam_width_6db:.0f}°\n"
            f"  -10dB Beamwidth: {self.beam_width_10db:.0f}°\n"
            f"  Quality: {self.dispersion_quality}"
        )


def circular_piston_directivity(
    ka: float,
    angle_rad: np.ndarray
) -> np.ndarray:
    """
    Calculate directivity of a circular piston in infinite baffle.

    Uses Bessel function J1 for circular aperture:
        D(θ) = |2*J1(ka*sin(θ)) / (ka*sin(θ))|

    Literature:
        - Beranek (1954), Chapter 5 - Directivity of circular radiators
        - Olson (1947), Section 4.4 - Radiation patterns

    Args:
        ka: Size parameter (k = 2π/λ, a = radius)
        angle_rad: Observation angle from axis (radians)

    Returns:
        Normalized pressure (0-1)

    Example:
        >>> ka = 1.37
        >>> angles = np.linspace(-np.pi/2, np.pi/2, 181)
        >>> response = circular_piston_directivity(ka, angles)
        >>> print(f"On-axis: {response[90]:.3f}")
        On-axis: 1.000
    """
    if ka == 0:
        return np.ones_like(angle_rad)

    x = ka * np.sin(angle_rad)

    # Handle x=0 case (on-axis)
    result = np.ones_like(x)

    # Off-axis calculation
    mask = x != 0
    x_masked = x[mask]
    result[mask] = np.abs(2 * j1(x_masked) / x_masked)

    return result


def calculate_directivity_index(ka: float) -> float:
    """
    Calculate Directivity Index (DI) for circular source.

    DI = 10*log10(2*ka²) for ka >> 1 (high frequency approximation)

    Literature:
        - Beranek (1954) - Directivity index definition
        - Morse & Ingard (1968) - Radiation impedance

    Args:
        ka: Size parameter

    Returns:
        Directivity index in dB

    Example:
        >>> di = calculate_directivity_index(1.37)
        >>> print(f"DI: {di:.1f} dB")
        DI: 5.8 dB
    """
    if ka < 0.1:
        return 0.0  # Omnidirectional

    # Approximation for circular piston
    di = 10 * np.log10(2 * ka**2)
    return max(0.0, di)


def calculate_beam_width(
    ka: float,
    level_db: float = -6,
    num_points: int = 361
) -> float:
    """
    Calculate beam width at specified level below on-axis response.

    Typical values:
    - -6 dB: Half-power beamwidth
    - -10 dB: Useful coverage angle

    Args:
        ka: Size parameter
        level_db: Level below on-axis (dB), default -6
        num_points: Number of angle points, default 361

    Returns:
        Beam width in degrees

    Example:
        >>> bw = calculate_beam_width(1.37, -6)
        >>> print(f"Beamwidth: {bw:.0f}°")
        Beamwidth: 180°
    """
    angles_deg = np.linspace(-90, 90, num_points)
    angles_rad = np.deg2rad(angles_deg)

    response = circular_piston_directivity(ka, angles_rad)
    on_axis = response[num_points // 2]  # 0 degrees
    threshold = 10 ** (level_db / 20) * on_axis

    above_threshold = response >= threshold

    if not np.any(above_threshold):
        return 180.0  # Omnidirectional

    # Find first and last crossing
    indices = np.where(above_threshold)[0]
    first = indices[0]
    last = indices[-1]

    return abs(angles_deg[last] - angles_deg[first])


def assess_dispersion_quality(ka: float) -> str:
    """
    Assess dispersion quality based on ka parameter.

    Literature:
        - Beranek (1954) - Directivity regions

    Args:
        ka: Size parameter

    Returns:
        Qualitative assessment

    Example:
        >>> quality = assess_dispersion_quality(1.37)
        >>> print(quality)
        Moderate (slight beaming)
    """
    if ka < 0.5:
        return "Omnidirectional (no beaming)"
    elif ka < 1.0:
        return "Wide (minimal beaming)"
    elif ka < 1.5:
        return "Moderate (slight beaming)"
    elif ka < 2.0:
        return "Narrow (noticeable beaming)"
    elif ka < 3.0:
        return "Very narrow (strong beaming)"
    else:
        return "Highly directional"


def analyze_horn_dispersion(
    mouth_area_cm2: float,
    crossover_frequency_hz: float,
    speed_of_sound: float = 343.0
) -> DirectivityResult:
    """
    Analyze directivity of a circular horn mouth at crossover frequency.

    Args:
        mouth_area_cm2: Mouth area (cm²)
        crossover_frequency_hz: Crossover frequency (Hz)
        speed_of_sound: Speed of sound (m/s), default 343 m/s

    Returns:
        DirectivityResult with analysis

    Example:
        >>> result = analyze_horn_dispersion(491, 600)
        >>> print(result)
        Directivity Result:
          ka: 1.37
          Directivity Index: 5.8 dB
          -6dB Beamwidth: 180°
          -10dB Beamwidth: 180°
          Quality: Moderate (slight beaming)
    """
    # Calculate mouth radius
    mouth_radius_m = np.sqrt((mouth_area_cm2 / 10000) / np.pi)

    # Calculate wavelength
    wavelength = speed_of_sound / crossover_frequency_hz

    # Calculate ka
    k = 2 * np.pi / wavelength
    ka = k * mouth_radius_m

    # Calculate metrics
    di = calculate_directivity_index(ka)
    bw_6 = calculate_beam_width(ka, -6)
    bw_10 = calculate_beam_width(ka, -10)

    # Assess quality
    quality = assess_dispersion_quality(ka)

    return DirectivityResult(
        ka=ka,
        directivity_index_db=di,
        beam_width_6db=bw_6,
        beam_width_10db=bw_10,
        dispersion_quality=quality
    )


def recommend_mouth_size(
    target_crossover_hz: float,
    max_diameter_mm: float,
    desired_dispersion: str = "moderate"
) -> float:
    """
    Recommend mouth size based on dispersion requirements.

    Args:
        target_crossover_hz: Target crossover frequency (Hz)
        max_diameter_mm: Maximum mouth diameter (mm)
        desired_dispersion: 'wide', 'moderate', or 'narrow'

    Returns:
        Recommended mouth area (cm²)

    Example:
        >>> area = recommend_mouth_size(600, 250, "moderate")
        >>> print(f"Recommended: {area:.0f} cm²")
        Recommended: 491 cm²
    """
    max_radius_cm = (max_diameter_mm / 10) / 2
    max_area_cm2 = np.pi * (max_radius_cm ** 2)

    # Calculate ka for max mouth
    result_max = analyze_horn_dispersion(max_area_cm2, target_crossover_hz)

    # If max mouth meets requirements, use it
    if desired_dispersion == "wide" and result_max.ka < 1.0:
        return max_area_cm2
    elif desired_dispersion == "moderate" and result_max.ka < 1.5:
        return max_area_cm2
    elif desired_dispersion == "narrow" and result_max.ka > 1.5:
        return max_area_cm2
    else:
        # Need smaller mouth for desired dispersion
        # Calculate required ka
        if desired_dispersion == "wide":
            target_ka = 0.7
        elif desired_dispersion == "moderate":
            target_ka = 1.2
        else:  # narrow
            target_ka = 2.0

        # Calculate required radius from ka
        wavelength = 34300 / target_crossover_hz  # cm
        k = 2 * np.pi / wavelength
        required_radius_cm = target_ka / k
        required_area_cm2 = np.pi * (required_radius_cm ** 2)

        return min(required_area_cm2, max_area_cm2)
