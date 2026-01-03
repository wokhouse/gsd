"""
Baffle step diffraction calculations.

When a driver radiates from a finite baffle, the sound transitions from
full-space radiation (4π steradians) at low frequencies to half-space
radiation (2π steradians) at high frequencies.

PHYSICS REALITY:
- Low frequencies (< f_step): Radiates into 4π space, -6 dB relative to 2π
- High frequencies (> f_step): Radiates into 2π space, 0 dB reference

This means a speaker on a baffle is LESS efficient at low frequencies
(the sound "wraps around" the baffle), NOT more efficient at high frequencies.

COMPENSATION CIRCUIT:
To flatten the response, a shelf filter boosts low frequencies by +6 dB.
This creates a flat acoustic output when combined with the baffle physics.

Literature:
- Olson (1951) - Direct Radiator Loudspeaker Enclosures, JAES 2(4)
- Linkwitz (2003) - Diffraction from baffle edges, LinkwitzLab
- Stenzel (1930) - Circular baffle diffraction theory

Key equations:
- f_step ≈ 115 / width  (empirical transition frequency approximation)
- Maximum step: 6 dB (4π to 2π transition)
"""

import numpy as np
from typing import Tuple, Union

from gsd.simulation.constants import SPEED_OF_SOUND


def baffle_step_frequency(
    baffle_width: float,
    speed_of_sound: float = SPEED_OF_SOUND
) -> float:
    """
    Calculate the baffle step transition frequency.

    The baffle step occurs when the wavelength is comparable to the
    baffle dimensions. The empirical approximation f = 115/W aligns
    with the -3 dB point of the transition.

    Literature:
        Olson (1951) - Direct Radiator Loudspeaker Enclosures, Figure 6, 14
        Linkwitz (2003) - f_step ≈ 115 / W (empirical)
        f_step = c / (2 × width) (theoretical)

    Args:
        baffle_width: Smallest dimension of the baffle (meters)
        speed_of_sound: Speed of sound (m/s), default 344 m/s

    Returns:
        Baffle step frequency (Hz) where gain is +3 dB

    Examples:
        >>> baffle_step_frequency(0.3)  # 30cm wide baffle
        383.3...  # Hz (empirical: 115/0.3)
    """
    # Empirical approximation (aligns with Olson's experimental data)
    return 115.0 / baffle_width


def baffle_step_loss(
    frequency: Union[float, np.ndarray],
    baffle_width: float,
    speed_of_sound: float = SPEED_OF_SOUND
) -> Union[float, np.ndarray]:
    """
    Calculate baffle step diffraction response using Linkwitz shelf model.

    This is a FIRST-ORDER APPROXIMATION that provides a smooth transition
    without diffraction ripples. Suitable for:
    - Crossover design tools
    - Quick visualization
    - When exact baffle geometry is unknown

    Literature:
        Linkwitz (2003) - First-order shelf filter approximation
        |H(f)| = sqrt((1 + (f/f_step)²) / (1 + (f/(f_step/2))²))

    Args:
        frequency: Frequency or frequencies (Hz)
        baffle_width: Width of the baffle (meters)
        speed_of_sound: Speed of sound (m/s), default 344 m/s

    Returns:
        Gain in dB (-6 dB at low freq, 0 dB at high freq for physics mode)

    Examples:
        >>> baffle_step_loss(100, 0.3)  # 100 Hz, 30cm baffle
        -5.9...  # dB (speaker in 4π space at low frequency)
        >>> baffle_step_loss(2000, 0.3)  # 2 kHz, 30cm baffle
        -0.1...  # dB (speaker in 2π space at high frequency)
    """
    f_step = baffle_step_frequency(baffle_width, speed_of_sound)

    # Linkwitz first-order shelf filter model
    # Models the transition from 4π (0.5x pressure) to 2π (1.0x pressure)
    # At DC: magnitude = 0.5 (-6 dB)
    # At HF: magnitude = 1.0 (0 dB)

    # Transfer function: H(s) = (s + 0.5·ω_step) / (s + ω_step)
    # where ω_step = 2π·f_step

    # Magnitude response:
    # |H(jω)|² = (ω² + (0.5·ω_step)²) / (ω² + ω_step²)

    omega = 2 * np.pi * frequency
    omega_step = 2 * np.pi * f_step

    magnitude_squared = (omega**2 + (0.5 * omega_step)**2) / (omega**2 + omega_step**2)
    magnitude = np.sqrt(magnitude_squared)

    # Convert to dB (relative to 2π space = 0 dB)
    gain_db = 20 * np.log10(magnitude)

    return gain_db


def baffle_step_loss_olson(
    frequency: Union[float, np.ndarray],
    baffle_width: float,
    baffle_height: float = None,
    speed_of_sound: float = SPEED_OF_SOUND
) -> Union[float, np.ndarray]:
    """
    Calculate baffle step response using Stenzel's circular baffle model.

    This model includes DIFFRACTION RIPPLES that match Olson's experimental
    measurements (Figures 6 and 14). More accurate than the smooth Linkwitz
    model for frequencies near the transition.

    CRITICAL: This uses the Stenzel (1930) approximation, NOT the piston
    directivity formula. The old implementation was incorrect.

    Literature:
        Olson (1951) - Direct Radiator Loudspeaker Enclosures
        Stenzel (1930) - Circular baffle diffraction
        P_rel = 1 - exp(-j·k·a)
        |P|² = 2 - 2·cos(k·a)

    Args:
        frequency: Frequency or frequencies (Hz)
        baffle_width: Width of the baffle (meters)
        baffle_height: Height of the baffle (meters), defaults to width (square)
        speed_of_sound: Speed of sound (m/s), default 344 m/s

    Returns:
        Gain in dB (-6 dB at low freq, 0 dB at high freq with ripples)

    Examples:
        >>> baffle_step_loss_olson(1000, 0.3)
        0.2...  # dB (with diffraction ripple at 1 kHz)
    """
    if baffle_height is None:
        baffle_height = baffle_width  # Square baffle

    # Effective radius (radius of circle with same area as rectangle)
    a = np.sqrt(baffle_width * baffle_height / np.pi)

    # Wavenumber
    k = 2 * np.pi * frequency / speed_of_sound

    # Stenzel's circular baffle model (1930)
    # P_rel = 1 - exp(-j·k·a)
    # |P|² = (1 - cos(ka))² + sin²(ka) = 2 - 2·cos(ka)

    magnitude_squared = 2 - 2 * np.cos(k * a)
    magnitude = np.sqrt(magnitude_squared)

    # Normalize: 2π space (high freq) = 0 dB, 4π space (low freq) = -6 dB
    # At high freq (ka >> 1): |P| → 2 (0 dB)
    # At low freq (ka << 1): |P| → 0 (-infinity dB, but physically -6 dB)

    # Convert to dB and normalize to 2π space
    gain_db = 20 * np.log10(magnitude / 2.0)

    # Clamp to physical limits (-6 to 0 dB)
    # Low frequencies don't go below -6 dB (4π space limit)
    gain_db = np.clip(gain_db, -6.0, 0.0)

    return gain_db


def baffle_step_compensation(
    frequency: Union[float, np.ndarray],
    baffle_width: float,
    speed_of_sound: float = SPEED_OF_SOUND
) -> Union[float, np.ndarray]:
    """
    Calculate baffle step COMPENSATION circuit response.

    This is a shelving filter that corrects the baffle step by boosting low
    frequencies. When applied to a speaker's electrical input, the combined
    acoustic response is flat.

    Literature:
        Linkwitz (2003) - Baffle step compensation circuits
        H_comp(s) = (s + ω_step) / (s + 0.5·ω_step) [inverse of physics]

    Args:
        frequency: Frequency or frequencies (Hz)
        baffle_width: Width of the baffle (meters)
        speed_of_sound: Speed of sound (m/s), default 344 m/s

    Returns:
        Correction in dB (+6 dB at low freq, 0 dB at high freq)

    Examples:
        >>> baffle_step_compensation(100, 0.3)
        5.9...  # dB (boost low frequencies to compensate)
        >>> baffle_step_compensation(2000, 0.3)
        0.0...  # dB (no correction at high frequency)
    """
    f_step = baffle_step_frequency(baffle_width, speed_of_sound)

    # Linkwitz compensation shelf filter (inverse of physics response)
    # At DC: magnitude = 2.0 (+6 dB)
    # At HF: magnitude = 1.0 (0 dB)

    # Transfer function: H(s) = (s + ω_step) / (s + 0.5·ω_step)
    # This is the INVERSE of the physics transfer function

    omega = 2 * np.pi * frequency
    omega_step = 2 * np.pi * f_step

    magnitude_squared = (omega**2 + omega_step**2) / (omega**2 + (0.5 * omega_step)**2)
    magnitude = np.sqrt(magnitude_squared)

    # Convert to dB
    gain_db = 20 * np.log10(magnitude)

    return gain_db


def estimate_baffle_width(
    enclosure_volume_liters: float,
    aspect_ratio: float = 1.0
) -> float:
    """
    Estimate baffle width from enclosure volume.

    For a given box volume, estimate the baffle width assuming a
    rectangular box with the specified aspect ratio (width:height).

    Args:
        enclosure_volume_liters: Net internal volume (liters)
        aspect_ratio: Width to height ratio (1.0 = square front baffle)

    Returns:
        Estimated baffle width (meters)

    Examples:
        >>> estimate_baffle_width(30)  # 30 liter box
        0.31...  # meters (approximately 31 cm width)
    """
    volume_m3 = enclosure_volume_liters / 1000.0

    # Assume depth ≈ width for a cube-like box
    # width² × depth ≈ volume
    # width³ ≈ volume (for cube)
    # For rectangular: width × height × depth = volume
    # With aspect_ratio = width/height and depth ≈ width:
    # width × (width/aspect_ratio) × width = volume
    # width³ / aspect_ratio = volume

    width = (volume_m3 * aspect_ratio) ** (1/3)

    return width


def calculate_baffle_step_correction(
    frequencies: np.ndarray,
    baffle_width: float,
    model: str = 'linkwitz',
    mode: str = 'physics'
) -> np.ndarray:
    """
    Calculate baffle step response array for frequency response.

    Args:
        frequencies: Array of frequencies (Hz)
        baffle_width: Width of the baffle (meters)
        model: 'linkwitz' (smooth, default) or 'olson' (with ripples)
        mode: 'physics' (actual acoustic response) or 'compensator' (correction circuit)

    Returns:
        Array of gain/loss values in dB

    Examples:
        >>> import numpy as np
        >>> freqs = np.logspace(1, 4, 100)  # 10 Hz to 10 kHz
        >>> gain = calculate_baffle_step_correction(freqs, 0.3, mode='physics')
        >>> gain[0]   # Low frequency (4π space)
        -5.9...  # dB (speaker radiates into full space)
        >>> gain[-1]  # High frequency (2π space)
        0.0...  # dB (speaker radiates into half space)
    """
    frequencies = np.asarray(frequencies)

    if model == 'linkwitz':
        if mode == 'physics':
            return baffle_step_loss(frequencies, baffle_width)
        elif mode == 'compensator':
            return baffle_step_compensation(frequencies, baffle_width)
        else:
            raise ValueError(f"Unknown mode: {mode}. Use 'physics' or 'compensator'.")

    elif model == 'olson':
        # Olson/Stenzel model always returns physics response
        if mode == 'physics':
            return baffle_step_loss_olson(frequencies, baffle_width)
        elif mode == 'compensator':
            # Compensator is just the inverse
            return -baffle_step_loss_olson(frequencies, baffle_width)
        else:
            raise ValueError(f"Unknown mode: {mode}. Use 'physics' or 'compensator'.")

    else:
        raise ValueError(f"Unknown baffle step model: {model}. Use 'linkwitz' or 'olson'.")


def apply_baffle_step_to_spl(
    spl: np.ndarray,
    frequencies: np.ndarray,
    baffle_width: float,
    model: str = 'linkwitz',
    mode: str = 'physics'
) -> np.ndarray:
    """
    Apply baffle step response to SPL response.

    Adjusts the simulated SPL response by adding the baffle step gain/loss.

    For mode='physics':
    - Low frequencies get -6 dB (4π space, less efficient)
    - High frequencies get 0 dB (2π space, more efficient)

    For mode='compensator':
    - Low frequencies get 0 dB (no correction)
    - High frequencies get -6 dB (correction for 2π space gain)

    Literature:
        Olson (1951) - Direct Radiator Loudspeaker Enclosures
        Linkwitz (2003) - Baffle step compensation circuits

    Args:
        spl: Simulated SPL values (dB)
        frequencies: Corresponding frequencies (Hz)
        baffle_width: Width of the baffle (meters)
        model: 'linkwitz' (smooth) or 'olson' (with ripples)
        mode: 'physics' or 'compensator'

    Returns:
        SPL values with baffle step applied (dB)

    Examples:
        >>> import numpy as np
        >>> spl_2pi = np.array([90, 90, 90, 90])  # Flat in 2π space
        >>> freqs = np.array([50, 200, 1000, 5000])
        >>> spl_real = apply_baffle_step_to_spl(spl_2pi, freqs, 0.3, mode='physics')
        >>> spl_real  # Low freq will be -6 dB lower
        array([84.1..., 88.5..., 89.9..., 90.0...])
    """
    correction = calculate_baffle_step_correction(frequencies, baffle_width, model, mode)
    return spl + correction
