"""
Common plotting styles and themes for bugworks GSD visualizations.

This module provides consistent styling across all plot types, ensuring
publication-quality visualizations with a cohesive appearance.

Styles are applied using matplotlib's style context system.
"""

import matplotlib.pyplot as plt
import matplotlib as mpl
from typing import Dict, Any, Optional


# Default style configuration
VIBERESP_STYLE = {
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'axes.grid': True,
    'axes.grid.axis': 'both',
    'axes.grid.which': 'major',
    'axes.labelsize': 11,
    'axes.titlesize': 12,
    'axes.titleweight': 'bold',
    'axes.linewidth': 1.0,
    'axes.unicode_minus': False,

    'grid.alpha': 0.3,
    'grid.linestyle': '-',
    'grid.linewidth': 0.5,

    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'xtick.major.width': 1.0,
    'ytick.major.width': 1.0,
    'xtick.minor.width': 0.5,
    'ytick.minor.width': 0.5,

    'legend.fontsize': 10,
    'legend.framealpha': 0.9,
    'legend.edgecolor': 'gray',

    'lines.linewidth': 2.0,
    'lines.markersize': 6,

    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'DejaVu Sans', 'Liberation Sans', 'sans-serif'],

    'savefig.dpi': 150,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.1,

    'image.cmap': 'viridis',
}


def get_style(style_name: str = 'default') -> Dict[str, Any]:
    """
    Get style configuration dictionary.

    Args:
        style_name: Style name ('default', 'dark', 'presentation', 'publication')

    Returns:
        Dictionary of matplotlib rcParams

    Examples:
        >>> style = get_style('publication')
        >>> with plt.style.context(style):
        ...     plt.plot([1, 2, 3])
    """
    base_style = VIBERESP_STYLE.copy()

    if style_name == 'dark':
        base_style.update({
            'figure.facecolor': '#2E3440',
            'axes.facecolor': '#3B4252',
            'axes.labelcolor': 'white',
            'axes.titlecolor': 'white',
            'text.color': 'white',
            'xtick.color': 'white',
            'ytick.color': 'white',
            'legend.facecolor': '#3B4252',
            'legend.edgecolor': '#4C566A',
            'grid.color': '#4C566A',
        })
    elif style_name == 'presentation':
        base_style.update({
            'axes.labelsize': 14,
            'axes.titlesize': 16,
            'xtick.labelsize': 12,
            'ytick.labelsize': 12,
            'legend.fontsize': 12,
            'lines.linewidth': 3.0,
            'lines.markersize': 8,
        })
    elif style_name == 'publication':
        base_style.update({
            'axes.labelsize': 10,
            'axes.titlesize': 11,
            'xtick.labelsize': 9,
            'ytick.labelsize': 9,
            'legend.fontsize': 9,
            'lines.linewidth': 1.5,
            'font.family': 'serif',
            'font.serif': ['Times New Roman', 'DejaVu Serif', 'serif'],
        })

    return base_style


def apply_style(style_name: str = 'default'):
    """
    Apply bugworks GSD plotting style globally.

    Args:
        style_name: Style name to apply

    Examples:
        >>> apply_style('publication')
        >>> plt.plot([1, 2, 3])  # Uses publication style
    """
    style = get_style(style_name)
    mpl.rcParams.update(style)


def style_context(style_name: str = 'default'):
    """
    Create a style context for temporary styling.

    Args:
        style_name: Style name to use in context

    Yields:
        None (context manager)

    Examples:
        >>> with style_context('dark'):
        ...     plt.plot([1, 2, 3])  # Uses dark style
        >>> plt.plot([1, 2, 3])  # Back to default style
    """
    return plt.style.context(get_style(style_name))


# Color palettes for different plot types
COLOR_PALETTES = {
    'pareto': {
        'primary': '#2E86AB',
        'secondary': '#A23B72',
        'tertiary': '#F18F01',
        'highlight': '#C73E1D',
        'neutral': '#6B705C',
    },
    'frequency_response': {
        'curve1': '#006BA4',
        'curve2': '#FF800E',
        'curve3': '#ABABAB',
        'curve4': '#595959',
        'curve5': '#5F9ED1',
    },
    'geometry': {
        'outline': '#2C3E50',
        'fill': '#3498DB',
        'dimensions': '#E74C3C',
        'labels': '#7F8C8D',
    },
}


def get_palette(palette_name: str) -> Dict[str, str]:
    """
    Get color palette for specific plot type.

    Args:
        palette_name: Name of palette ('pareto', 'frequency_response', 'geometry')

    Returns:
        Dictionary mapping color names to hex codes

    Examples:
        >>> palette = get_palette('pareto')
        >>> color = palette['primary']
        '#2E86AB'
    """
    return COLOR_PALETTES.get(palette_name, COLOR_PALETTES['pareto'])


# Marker styles for scatter plots
MARKER_STYLES = {
    'default': 'o',
    'best': '*',
    'knee': 'D',
    'pareto': 'o',
    'dominated': 'x',
}


def get_marker(marker_name: str) -> str:
    """
    Get marker style for scatter plots.

    Args:
        marker_name: Marker type name

    Returns:
        matplotlib marker code

    Examples:
        >>> get_marker('best')
        '*'
    """
    return MARKER_STYLES.get(marker_name, MARKER_STYLES['default'])


# Standard figure sizes for different purposes
FIGURE_SIZES = {
    'square': (8, 8),
    'landscape': (12, 8),
    'portrait': (8, 12),
    'wide': (16, 6),
    'presentation': (14, 10),
    'publication_half': (6, 4),
    'publication_full': (8, 6),
}


def get_figure_size(size_name: str = 'landscape') -> tuple:
    """
    Get standard figure size.

    Args:
        size_name: Size name ('square', 'landscape', 'portrait', etc.)

    Returns:
        Tuple of (width, height) in inches

    Examples:
        >>> get_figure_size('square')
        (8, 8)
    """
    return FIGURE_SIZES.get(size_name, FIGURE_SIZES['landscape'])
