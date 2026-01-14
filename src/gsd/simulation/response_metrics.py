"""
Response metrics for frequency response analysis.

This module provides helper functions for analyzing frequency response data,
including finding -3dB cutoff frequencies (F3) for high-pass and low-pass filters.

Literature:
    - Small (1972) - Closed-box system parameters, F3 definition
    - Thiele (1971) - Vented box alignments and F3 calculation
    - Beranek (1954), Chapter 8 - Bandwidth and flatness definitions
"""

import numpy as np
from typing import Tuple, Optional


def find_f3_frequency(
    freq: np.ndarray,
    spl: np.ndarray,
    passband_level: float,
    search_range: Tuple[float, float] = (10, 200),
    filter_type: str = "highpass",
    warn_on_fallback: bool = True
) -> float:
    """
    Find -3dB frequency for high-pass or low-pass filters.

    For high-pass (ported box): F3 is where response rises to passband - 3dB
    For low-pass: F3 is where response drops from passband by 3dB

    Literature:
    - Small (1972) - F3 definition for enclosure systems
    - Standard definition: F3 is where response is -3dB relative to passband

    Args:
        freq: Frequency array (Hz), must be sorted
        spl: SPL array (dB), same length as freq
        passband_level: Reference passband level (dB)
        search_range: (min_freq, max_freq) to search for F3 (Hz)
        filter_type: "highpass" for ported boxes, "lowpass" for sealed
        warn_on_fallback: Log warning if using fallback (default: True)

    Returns:
        F3 frequency (Hz) with linear interpolation for accuracy

    Raises:
        ValueError: If F3 not found in search range

    Warnings:
        Issues warning if fallback to closest value is used

    Examples:
        >>> freq = np.logspace(1, 4, 1000)
        >>> spl = ported_box_response(freq, ...)
        >>> passband = np.mean(spl[(freq >= 80) & (freq <= 200)])
        >>> f3 = find_f3_frequency(freq, spl, passband, filter_type="highpass")
        >>> assert 40 < f3 < 60  # Should be near tuning frequency
    """
    target_level = passband_level - 3

    # Limit to search range
    search_mask = (freq >= search_range[0]) & (freq <= search_range[1])
    freq_search = freq[search_mask]
    spl_search = spl[search_mask]

    if len(freq_search) == 0:
        raise ValueError(
            f"No frequencies found in search range {search_range}. "
            f"Freq range: {freq.min():.1f} - {freq.max():.1f} Hz"
        )

    # Find crossing point
    if filter_type == "highpass":
        # For high-pass: find where response crosses target going UP
        # (response increases with frequency)
        crossings = np.where(np.diff(np.sign(spl_search - target_level)) > 0)[0]
    else:
        # For low-pass: find where response crosses target going DOWN
        crossings = np.where(np.diff(np.sign(spl_search - target_level)) < 0)[0]

    if len(crossings) == 0:
        # Fallback: find closest frequency to target
        closest_idx = np.argmin(np.abs(spl_search - target_level))
        f3_fallback = freq_search[closest_idx]

        if warn_on_fallback:
            import warnings
            warnings.warn(
                f"F3 crossing not found in search range {search_range}. "
                f"Using closest value: {f3_fallback:.1f} Hz "
                f"(target: {target_level:.1f} dB, closest: {spl_search[closest_idx]:.1f} dB). "
                f"This may indicate incorrect search range or filter type.",
                UserWarning
            )

        return f3_fallback

    # Linear interpolation for accuracy
    idx = crossings[0]
    f_low = freq_search[idx]
    f_high = freq_search[idx + 1]
    spl_low = spl_search[idx]
    spl_high = spl_search[idx + 1]

    # Avoid division by zero
    if spl_high == spl_low:
        return f_low

    # Interpolate
    f3 = f_low + (f_high - f_low) * (target_level - spl_low) / (spl_high - spl_low)

    return f3
