"""
Visualization module for bugworks GSD.

This module provides factory classes for generating standard plots from
optimization results, eliminating code duplication across plotting scripts.

Main classes:
    PlotFactory: Generate individual plots from optimization results
    PlotConfig: Configuration for plot generation

Plot types supported:
    - Pareto fronts (2D and 3D)
    - SPL frequency response
    - Horn geometry/profile
    - Parameter distributions

Examples:
    >>> from gsd.visualization import PlotFactory, PlotConfig
    >>>
    >>> # Create Pareto front plot
    >>> config = PlotConfig(
    ...     plot_type="pareto_2d",
    ...     data_source="optimization_results.json",
    ...     x_objective="f3",
    ...     y_objective="flatness"
    ... )
    >>> factory = PlotFactory(config)
    >>> factory.create_plot()
"""

from gsd.visualization.factory import PlotFactory
from gsd.visualization.config import (
    PlotConfig,
    MultiPlotConfig,
    PlotTheme,
    get_preset_config,
)
from gsd.visualization.styles import (
    apply_style,
    style_context,
    get_style,
    get_palette,
    get_figure_size,
)
from gsd.visualization.utils import (
    setup_frequency_axis,
    setup_spl_axis,
    find_f3_frequency,
    normalize_objectives,
    find_knee_point,
    create_text_box,
    save_figure,
)

__all__ = [
    # Main factory
    'PlotFactory',

    # Configuration
    'PlotConfig',
    'MultiPlotConfig',
    'PlotTheme',
    'get_preset_config',

    # Styling
    'apply_style',
    'style_context',
    'get_style',
    'get_palette',
    'get_figure_size',

    # Utilities
    'setup_frequency_axis',
    'setup_spl_axis',
    'find_f3_frequency',
    'normalize_objectives',
    'find_knee_point',
    'create_text_box',
    'save_figure',
]
