"""
Hornresp simulation query tools.

This module provides efficient tools for querying and analyzing Hornresp
simulation output files (_sim.txt) without loading entire file contents
into context. Functions return compact summaries or selective data extraction.

Literature:
- Hornresp manual: http://www.hornresp.net/
"""

from pathlib import Path
from typing import Literal, Optional
import numpy as np

from gsd.hornresp.results_parser import load_hornresp_sim_file, HornrespSimulationResult


# Valid column names for extraction
VALID_COLUMNS = {
    'frequency', 'ra_norm', 'xa_norm', 'za_norm', 'spl_db', 'ze_ohms',
    'xd_mm', 'wphase_deg', 'uphase_deg', 'cphase_deg', 'delay_msec',
    'efficiency_percent', 'ein_volts', 'pin_watts', 'iin_amps', 'zephase_deg'
}

# Valid metrics for find_extremes
VALID_METRICS = {
    'spl_db', 'ze_ohms', 'efficiency_percent', 'xd_mm',
    'ra_norm', 'xa_norm', 'za_norm'
}


def get_simulation_summary(
    filepath: str | Path,
    freq_range: Optional[tuple[float, float]] = None
) -> dict:
    """
    Generate compact summary statistics from Hornresp simulation file.

    Returns dictionary with min/max/mean of key metrics, impedance peaks,
    SPL characteristics, efficiency, and notable features.

    Args:
        filepath: Path to _sim.txt file
        freq_range: Optional (min_freq_hz, max_freq_hz) to filter analysis range

    Returns:
        Dictionary with summary statistics:
        {
            'metadata': {...},  # From HornrespSimulationResult.metadata
            'frequency': {'min_hz': float, 'max_hz': float, 'num_points': int},
            'impedance': {'min_ohms': float, 'max_ohms': float, 'mean_ohms': float,
                          'peaks': [{'freq_hz': float, 'magnitude_ohms': float, 'index': int}, ...]},
            'spl': {'min_db': float, 'max_db': float, 'mean_db': float,
                    'bandwidth': {'minus_3db_hz': float | None, 'minus_10db_hz': float | None}},
            'efficiency': {'min_percent': float, 'max_percent': float, 'at_max_spl': float},
            'notable_features': [str, ...]
        }

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid

    Examples:
        >>> summary = get_simulation_summary("sim.txt")
        >>> print(summary['notable_features'][0])
        'Impedance peak at 64.5 Hz: 42.38 Ω'

        >>> # Analyze bass region only
        >>> bass_summary = get_simulation_summary("sim.txt", freq_range=(20, 100))
        >>> bass_summary['impedance']['max_ohms']
        42.38
    """
    # Load simulation data
    result: HornrespSimulationResult = load_hornresp_sim_file(filepath)

    # Apply frequency range filter if specified
    mask = np.ones(len(result), dtype=bool)
    if freq_range is not None:
        freq_min, freq_max = freq_range
        mask = (result.frequency >= freq_min) & (result.frequency <= freq_max)

    # Extract masked arrays
    freq = result.frequency[mask]
    spl = result.spl_db[mask]
    ze = result.ze_ohms[mask]
    efficiency = result.efficiency_percent[mask]
    xd = result.xd_mm[mask]

    # Calculate impedance peaks
    impedance_peaks = _detect_peaks(ze, freq, min_height=None, min_distance=5)

    # Calculate SPL bandwidth
    max_spl_idx = np.argmax(spl)
    max_spl_freq = freq[max_spl_idx]
    max_spl_val = spl[max_spl_idx]

    bandwidth_3db = _calculate_bandwidth(spl, freq, db_down=3, reference=max_spl_val)
    bandwidth_10db = _calculate_bandwidth(spl, freq, db_down=10, reference=max_spl_val)

    # Generate notable features
    notable_features = []

    if impedance_peaks:
        main_peak = impedance_peaks[0]
        notable_features.append(
            f"Impedance peak at {main_peak['freq_hz']:.1f} Hz: {main_peak['magnitude_ohms']:.2f} Ω"
        )

    notable_features.append(
        f"Maximum SPL at {max_spl_freq:.1f} Hz: {max_spl_val:.2f} dB"
    )

    if bandwidth_3db is not None:
        notable_features.append(f"-3dB bandwidth at {bandwidth_3db:.1f} Hz")

    efficiency_at_max = efficiency[max_spl_idx]
    notable_features.append(
        f"Efficiency at max SPL: {efficiency_at_max:.3f}%"
    )

    # Build summary dictionary
    summary = {
        'metadata': result.metadata.copy(),
        'frequency': {
            'min_hz': float(np.min(freq)),
            'max_hz': float(np.max(freq)),
            'num_points': len(freq)
        },
        'impedance': {
            'min_ohms': float(np.min(ze)),
            'max_ohms': float(np.max(ze)),
            'mean_ohms': float(np.mean(ze)),
            'peaks': impedance_peaks
        },
        'spl': {
            'min_db': float(np.min(spl)),
            'max_db': float(np.max(spl)),
            'mean_db': float(np.mean(spl)),
            'bandwidth': {
                'minus_3db_hz': bandwidth_3db,
                'minus_10db_hz': bandwidth_10db
            }
        },
        'efficiency': {
            'min_percent': float(np.min(efficiency)),
            'max_percent': float(np.max(efficiency)),
            'at_max_spl': float(efficiency_at_max)
        },
        'notable_features': notable_features
    }

    return summary


def extract_columns(
    filepath: str | Path,
    columns: list[str],
    freq_range: Optional[tuple[float, float]] = None,
    as_dict: bool = True
) -> dict | np.ndarray:
    """
    Extract specific columns from Hornresp simulation file.

    Args:
        filepath: Path to _sim.txt file
        columns: List of column names to extract.
                 Valid: 'frequency', 'spl_db', 'ze_ohms', 'zephase_deg',
                        'efficiency_percent', 'ra_norm', 'xa_norm', 'za_norm',
                        'xd_mm', 'pin_watts', 'iin_amps', 'wphase_deg',
                        'uphase_deg', 'cphase_deg', 'delay_msec', 'ein_volts'
        freq_range: Optional (min_freq_hz, max_freq_hz) to filter
        as_dict: If True, return dict with column names as keys.
                 If False, return numpy array with columns in requested order.

    Returns:
        Dictionary mapping column names to numpy arrays, or 2D numpy array.

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If invalid column names provided

    Examples:
        >>> data = extract_columns("sim.txt", columns=['frequency', 'spl_db'])
        >>> data['spl_db'][:10]  # First 10 SPL values
        array([85.2, 86.1, 87.3, ...])

        >>> # Extract only impedance data in 50-100 Hz range
        >>> ze = extract_columns("sim.txt",
        ...                      columns=['ze_ohms'],
        ...                      freq_range=(50, 100))
        >>> ze['ze_ohms']
        array([42.3, 38.7, 35.2, ...])
    """
    # Validate column names
    invalid_columns = set(columns) - VALID_COLUMNS
    if invalid_columns:
        raise ValueError(
            f"Invalid column names: {invalid_columns}. "
            f"Valid columns: {sorted(VALID_COLUMNS)}"
        )

    # Load simulation data
    result: HornrespSimulationResult = load_hornresp_sim_file(filepath)

    # Apply frequency range filter if specified
    mask = np.ones(len(result), dtype=bool)
    if freq_range is not None:
        freq_min, freq_max = freq_range
        mask = (result.frequency >= freq_min) & (result.frequency <= freq_max)

    # Extract requested columns
    # Map column names to dataclass attributes
    column_map = {
        'frequency': result.frequency[mask],
        'ra_norm': result.ra_norm[mask],
        'xa_norm': result.xa_norm[mask],
        'za_norm': result.za_norm[mask],
        'spl_db': result.spl_db[mask],
        'ze_ohms': result.ze_ohms[mask],
        'xd_mm': result.xd_mm[mask],
        'wphase_deg': result.wphase_deg[mask],
        'uphase_deg': result.uphase_deg[mask],
        'cphase_deg': result.cphase_deg[mask],
        'delay_msec': result.delay_msec[mask],
        'efficiency_percent': result.efficiency_percent[mask],
        'ein_volts': result.ein_volts[mask],
        'pin_watts': result.pin_watts[mask],
        'iin_amps': result.iin_amps[mask],
        'zephase_deg': result.zephase_deg[mask],
    }

    if as_dict:
        # Return dictionary with only requested columns
        return {col: column_map[col] for col in columns}
    else:
        # Return 2D numpy array with columns in requested order
        return np.column_stack([column_map[col] for col in columns])


def query_frequency_range(
    filepath: str | Path,
    freq_min: float,
    freq_max: float,
    columns: Optional[list[str]] = None
) -> dict:
    """
    Query data within a specific frequency range.

    Convenience function that combines freq_range filtering with column extraction.

    Args:
        filepath: Path to _sim.txt file
        freq_min: Minimum frequency (Hz)
        freq_max: Maximum frequency (Hz)
        columns: Optional list of columns to extract (default: all)

    Returns:
        Dictionary with:
        {
            'num_points': int,
            'frequency': np.ndarray,
            'data': dict of requested columns (or all if columns=None)
        }

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If freq_min >= freq_max or invalid columns

    Examples:
        >>> # Get bass response data (20-100 Hz)
        >>> bass = query_frequency_range("sim.txt", 20, 100)
        >>> bass['num_points']
        87
        >>> bass['frequency'][:5]
        array([20.5, 21.3, 22.1, 23.0, 23.9])

        >>> # Get specific columns in range
        >>> bass_spl = query_frequency_range("sim.txt", 20, 100,
        ...                                  columns=['spl_db', 'ze_ohms'])
        >>> bass_spl['data']['spl_db']
        array([87.2, 88.1, ...])
    """
    if freq_min >= freq_max:
        raise ValueError(f"freq_min ({freq_min}) must be less than freq_max ({freq_max})")

    # Load simulation data
    result: HornrespSimulationResult = load_hornresp_sim_file(filepath)

    # Apply frequency range filter
    mask = (result.frequency >= freq_min) & (result.frequency <= freq_max)

    if not np.any(mask):
        raise ValueError(
            f"No data points found in frequency range {freq_min}-{freq_max} Hz. "
            f"Data range: {result.frequency[0]:.1f}-{result.frequency[-1]:.1f} Hz"
        )

    # Extract frequency array
    freq = result.frequency[mask]

    # If no columns specified, extract all
    if columns is None:
        columns = list(VALID_COLUMNS)

    # Extract requested columns
    data_dict = extract_columns(filepath, columns, freq_range=(freq_min, freq_max), as_dict=True)

    return {
        'num_points': len(freq),
        'frequency': freq,
        'data': data_dict
    }


def find_extremes(
    filepath: str | Path,
    metric: Literal[
        'spl_db', 'ze_ohms', 'efficiency_percent', 'xd_mm',
        'ra_norm', 'xa_norm', 'za_norm'
    ] = 'spl_db',
    n: int = 5
) -> dict:
    """
    Find n highest and n lowest values for a given metric.

    Args:
        filepath: Path to _sim.txt file
        metric: Metric to analyze ('spl_db', 'ze_ohms', 'efficiency_percent', etc.)
        n: Number of extremes to return (top n and bottom n)

    Returns:
        Dictionary with:
        {
            'highest': [
                {'frequency': float, 'value': float, 'index': int},
                ...
            ],
            'lowest': [
                {'frequency': float, 'value': float, 'index': int},
                ...
            ]
        }

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If invalid metric name

    Examples:
        >>> extremes = find_extremes("sim.txt", metric='spl_db', n=3)
        >>> for p in extremes['highest']:
        ...     print(f"{p['frequency']:.1f} Hz: {p['value']:.1f} dB")
        85.2 Hz: 92.1 dB
        78.4 Hz: 91.3 dB
        92.7 Hz: 90.8 dB
    """
    if metric not in VALID_METRICS:
        raise ValueError(
            f"Invalid metric '{metric}'. Valid metrics: {sorted(VALID_METRICS)}"
        )

    # Load simulation data
    result: HornrespSimulationResult = load_hornresp_sim_file(filepath)

    # Get the metric array
    column_map = {
        'spl_db': result.spl_db,
        'ze_ohms': result.ze_ohms,
        'efficiency_percent': result.efficiency_percent,
        'xd_mm': result.xd_mm,
        'ra_norm': result.ra_norm,
        'xa_norm': result.xa_norm,
        'za_norm': result.za_norm,
    }

    values = column_map[metric]
    freq = result.frequency

    # Find indices of n highest and n lowest values
    # Use argsort for efficiency
    sorted_indices = np.argsort(values)
    lowest_indices = sorted_indices[:n]
    highest_indices = sorted_indices[-n:][::-1]  # Reverse to get descending order

    # Build result lists
    highest = [
        {
            'frequency': float(freq[i]),
            'value': float(values[i]),
            'index': int(i)
        }
        for i in highest_indices
    ]

    lowest = [
        {
            'frequency': float(freq[i]),
            'value': float(values[i]),
            'index': int(i)
        }
        for i in lowest_indices
    ]

    return {
        'highest': highest,
        'lowest': lowest
    }


def _detect_peaks(
    values: np.ndarray,
    frequencies: np.ndarray,
    min_height: Optional[float] = None,
    min_distance: int = 5
) -> list[dict]:
    """
    Detect peaks in data array using simple local maxima method.

    Args:
        values: Array of values (e.g., impedance)
        frequencies: Array of corresponding frequencies
        min_height: Minimum peak height (if None, uses mean + std)
        min_distance: Minimum number of samples between peaks

    Returns:
        List of dicts: [{'frequency': float, 'magnitude_ohms': float, 'index': int}, ...]
    """
    if len(values) < 3:
        return []

    # Simple peak detection: local maximum with minimum distance
    peaks = []

    # Set minimum height if not specified
    if min_height is None:
        min_height = np.mean(values) + np.std(values)

    for i in range(1, len(values) - 1):
        # Check if local maximum
        if values[i] > values[i - 1] and values[i] > values[i + 1]:
            # Check minimum height
            if values[i] >= min_height:
                # Check minimum distance from other peaks
                too_close = False
                for peak in peaks:
                    if abs(i - peak['index']) < min_distance:
                        too_close = True
                        break

                if not too_close:
                    peaks.append({
                        'freq_hz': float(frequencies[i]),
                        'magnitude_ohms': float(values[i]),
                        'index': int(i)
                    })

    # Sort by magnitude (descending)
    peaks.sort(key=lambda p: p['magnitude_ohms'], reverse=True)

    return peaks


def _calculate_bandwidth(
    spl_db: np.ndarray,
    frequencies: np.ndarray,
    db_down: float,
    reference: Optional[float] = None
) -> Optional[float]:
    """
    Calculate -X dB bandwidth frequency.

    Finds the frequency where SPL is (reference - db_down) dB.
    Searches for both lower and upper frequencies and returns the one
    closer to the frequency of maximum SPL.

    Args:
        spl_db: SPL array (dB)
        frequencies: Frequency array (Hz)
        db_down: dB down from reference (e.g., 3 for -3dB bandwidth)
        reference: Reference SPL value (if None, uses max SPL)

    Returns:
        Frequency at -X dB point, or None if not found
    """
    if reference is None:
        reference = np.max(spl_db)

    target_level = reference - db_down

    # Check if target level is actually reached
    # (SPL must vary enough to reach the target)
    if np.min(spl_db) > target_level:
        # SPL never drops to target level
        return None

    # Find all points where SPL crosses target level
    crossings = np.where(spl_db >= target_level)[0]

    if len(crossings) == 0:
        return None

    # Return the frequency at the center of the passband
    # (closest to the frequency of max SPL)
    max_idx = np.argmax(spl_db)
    max_freq = frequencies[max_idx]

    # Find crossing closest to max frequency
    distances = np.abs(frequencies[crossings] - max_freq)
    closest_idx = crossings[np.argmin(distances)]

    return float(frequencies[closest_idx])
