"""
Utility functions for plotting.

This module provides helper functions for common plotting tasks such as
setting up frequency axes, formatting labels, and calculating plot statistics.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from typing import Tuple, Optional, List, Dict, Any, Union
from pathlib import Path


def setup_frequency_axis(
    ax: Axes,
    freq_min: float = 20,
    freq_max: float = 20000,
    major_ticks: Optional[List[float]] = None,
    minor_ticks: Optional[List[float]] = None,
) -> Axes:
    """
    Set up logarithmic frequency axis with standard formatting.

    Args:
        ax: Matplotlib axes object
        freq_min: Minimum frequency (Hz)
        freq_max: Maximum frequency (Hz)
        major_ticks: List of major tick frequencies (e.g., [100, 1000, 10000])
        minor_ticks: List of minor tick frequencies (e.g., [200, 500, 2000, 5000])

    Returns:
        Modified axes object

    Examples:
        >>> fig, ax = plt.subplots()
        >>> setup_frequency_axis(ax, 20, 20000)
    """
    ax.set_xscale('log')
    ax.set_xlim(freq_min, freq_max)

    # Standard audio frequency ticks
    if major_ticks is None:
        major_ticks = [100, 1000, 10000]

    if minor_ticks is None:
        minor_ticks = [20, 50, 200, 500, 2000, 5000, 20000]

    ax.set_xticks(major_ticks)
    ax.set_xticks(minor_ticks, minor=True)

    ax.set_xlabel('Frequency (Hz)', fontsize=11)

    return ax


def setup_spl_axis(
    ax: Axes,
    spl_min: Optional[float] = None,
    spl_max: Optional[float] = None,
    ref_line: Optional[float] = None,
) -> Axes:
    """
    Set up SPL (sound pressure level) axis with standard formatting.

    Args:
        ax: Matplotlib axes object
        spl_min: Minimum SPL (dB), auto-detect if None
        spl_max: Maximum SPL (dB), auto-detect if None
        ref_line: Optional reference line level (dB)

    Returns:
        Modified axes object

    Examples:
        >>> fig, ax = plt.subplots()
        >>> setup_spl_axis(ax, 40, 100, ref_line=94)
    """
    ax.set_ylabel('Sound Pressure Level (dB)', fontsize=11)

    if spl_min is not None:
        ax.set_ylim(bottom=spl_min)
    if spl_max is not None:
        ax.set_ylim(top=spl_max)

    # Add reference line if specified
    if ref_line is not None:
        ax.axhline(ref_line, color='gray', linestyle='--', alpha=0.5, linewidth=1)

    return ax


def find_f3_frequency(
    frequencies: np.ndarray,
    spl: np.ndarray,
    reference_level: Optional[float] = None,
    freq_range: Tuple[float, float] = (20, 500),
) -> Optional[float]:
    """
    Find F3 frequency (-3dB cutoff frequency) from SPL response.

    Args:
        frequencies: Frequency array (Hz)
        spl: SPL array (dB)
        reference_level: Reference SPL level (dB), uses max if None
        freq_range: Frequency range to search (min, max) in Hz

    Returns:
        F3 frequency in Hz, or None if not found in range

    Examples:
        >>> freqs = np.logspace(1, 4, 100)
        >>> spl = 90 - 3 * (freqs / 100)**-1  # Simple rolloff
        >>> f3 = find_f3_frequency(freqs, spl)
    """
    if reference_level is None:
        # Use maximum SPL as reference
        reference_level = np.max(spl)

    target_level = reference_level - 3

    # Find frequency range where to search
    mask = (frequencies >= freq_range[0]) & (frequencies <= freq_range[1])
    freqs_search = frequencies[mask]
    spl_search = spl[mask]

    # Find where SPL crosses -3dB (interpolate for accuracy)
    if len(spl_search) < 2:
        return None

    # Find crossings
    crossings = np.where(spl_search < target_level)[0]

    if len(crossings) == 0:
        return None

    # Interpolate to find exact frequency
    idx = crossings[0]
    if idx == 0:
        return freqs_search[0]

    # Linear interpolation
    f1, f2 = freqs_search[idx - 1], freqs_search[idx]
    s1, s2 = spl_search[idx - 1], spl_search[idx]

    if s2 == s1:
        return f1

    f3 = f1 + (target_level - s1) * (f2 - f1) / (s2 - s1)

    return f3


def normalize_objectives(
    values: np.ndarray,
    direction: str = 'minimize'
) -> np.ndarray:
    """
    Normalize objective values to 0-1 range.

    Args:
        values: Array of objective values
        direction: 'minimize' or 'maximize'

    Returns:
        Normalized array in range [0, 1]

    Examples:
        >>> values = np.array([10, 20, 30, 40, 50])
        >>> normalized = normalize_objectives(values, 'minimize')
        >>> normalized
        array([0., 0.25, 0.5, 0.75, 1.])
    """
    min_val = np.min(values)
    max_val = np.max(values)

    if max_val == min_val:
        return np.zeros_like(values)

    normalized = (values - min_val) / (max_val - min_val)

    if direction == 'maximize':
        normalized = 1 - normalized

    return normalized


def find_knee_point(
    x: np.ndarray,
    y: np.ndarray,
    normalize: bool = True
) -> int:
    """
    Find knee point in Pareto front (best compromise design).

    Uses the distance from origin method after normalizing objectives
    to 0-1 range. The point closest to the "ideal" (min x, min y) is selected.

    Args:
        x: First objective array (e.g., F3)
        y: Second objective array (e.g., flatness)
        normalize: Whether to normalize objectives before finding knee

    Returns:
        Index of knee point

    Examples:
        >>> x = np.array([20, 25, 30, 35, 40])
        >>> y = np.array([10, 8, 6, 5, 4.5])
        >>> knee_idx = find_knee_point(x, y)
    """
    x_norm = x.copy()
    y_norm = y.copy()

    if normalize:
        x_norm = normalize_objectives(x, 'minimize')
        y_norm = normalize_objectives(y, 'minimize')

    # Distance from origin (0, 0)
    distances = np.sqrt(x_norm**2 + y_norm**2)

    return np.argmin(distances)


def create_text_box(
    ax: Axes,
    text: str,
    position: str = 'top left',
    bgcolor: str = 'white',
    alpha: float = 0.8,
    fontsize: int = 9,
) -> None:
    """
    Add a formatted text box to axes.

    Args:
        ax: Matplotlib axes object
        text: Text content
        position: Position ('top left', 'top right', 'bottom left', 'bottom right')
        bgcolor: Background color
        alpha: Background transparency
        fontsize: Text font size

    Examples:
        >>> fig, ax = plt.subplots()
        >>> ax.plot([1, 2, 3], [1, 2, 3])
        >>> create_text_box(ax, 'F3 = 45 Hz', 'top right')
    """
    # Position coordinates
    positions = {
        'top left': {'xy': (0.02, 0.98), 'xycoords': 'axes fraction',
                     'verticalalignment': 'top', 'horizontalalignment': 'left'},
        'top right': {'xy': (0.98, 0.98), 'xycoords': 'axes fraction',
                      'verticalalignment': 'top', 'horizontalalignment': 'right'},
        'bottom left': {'xy': (0.02, 0.02), 'xycoords': 'axes fraction',
                        'verticalalignment': 'bottom', 'horizontalalignment': 'left'},
        'bottom right': {'xy': (0.98, 0.02), 'xycoords': 'axes fraction',
                         'verticalalignment': 'bottom', 'horizontalalignment': 'right'},
    }

    if position not in positions:
        raise ValueError(f"Invalid position: {position}")

    props = positions[position]

    ax.annotate(
        text,
        xy=props['xy'],
        xycoords=props['xycoords'],
        verticalalignment=props['verticalalignment'],
        horizontalalignment=props['horizontalalignment'],
        bbox=dict(boxstyle='round,pad=0.5', facecolor=bgcolor, edgecolor='gray', alpha=alpha),
        fontsize=fontsize,
    )


def save_figure(
    fig: Figure,
    output_path: Union[str, Path],
    dpi: int = 150,
    formats: Optional[List[str]] = None,
) -> None:
    """
    Save figure to file with standard settings.

    Args:
        fig: Matplotlib figure object
        output_path: Output file path
        dpi: Resolution (dots per inch)
        formats: List of formats to save ('png', 'pdf', 'svg'), uses extension if None

    Examples:
        >>> fig, ax = plt.subplots()
        >>> ax.plot([1, 2, 3])
        >>> save_figure(fig, 'output.png', dpi=300)
    """
    output_path = Path(output_path)

    if formats is None:
        formats = [output_path.suffix.lstrip('.')]

    for fmt in formats:
        if fmt == output_path.suffix.lstrip('.'):
            path = output_path
        else:
            path = output_path.with_suffix(f'.{fmt}')

        fig.savefig(path, dpi=dpi, bbox_inches='tight', facecolor='white')


def calculate_box_plot_data(data: List[float]) -> Dict[str, float]:
    """
    Calculate box plot statistics (median, quartiles, whiskers).

    Args:
        data: List of data values

    Returns:
        Dictionary with statistics keys

    Examples:
        >>> data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        >>> stats = calculate_box_plot_data(data)
        >>> stats['median']
        5.5
    """
    data_array = np.array(data)

    return {
        'median': np.median(data_array),
        'q1': np.percentile(data_array, 25),
        'q3': np.percentile(data_array, 75),
        'min': np.min(data_array),
        'max': np.max(data_array),
        'mean': np.mean(data_array),
        'std': np.std(data_array),
    }
