"""
Configuration classes for plot generation.

This module provides dataclasses for configuring plot generation,
supporting both single and multi-plot scenarios.
"""

from dataclasses import dataclass, field
from typing import Union, Optional, List, Tuple, Dict, Any
from pathlib import Path


@dataclass
class PlotConfig:
    """
    Configuration for generating a single plot.

    Attributes:
        plot_type: Type of plot to generate
            - "pareto_2d": 2D Pareto front scatter plot
            - "pareto_3d": 3D Pareto front scatter plot
            - "spl_response": SPL frequency response curve
            - "horn_profile": Horn cross-section geometry
            - "parameter_distribution": Parameter distribution (box/violin plots)
        data_source: Data source (file path or OptimizationResult object)
        output_path: Where to save the plot (None means display only)
        figure_size: Figure size (width, height) in inches
        dpi: Resolution for saved figures
        style: Plot style name (from styles.py)
        show_plot: Whether to display the plot interactively
        x_objective: First objective for Pareto plots (e.g., "f3")
        y_objective: Second objective for Pareto plots (e.g., "flatness")
        z_objective: Third objective for 3D Pareto color (optional)
        mark_knee: Whether to mark knee/best compromise point
        frequency_range: Frequency range for SPL plots (min, max) in Hz
        num_designs: Maximum number of designs to show (None = all)
        design_indices: Specific design indices to plot (overrides num_designs)

    Examples:
        >>> config = PlotConfig(
        ...     plot_type="pareto_2d",
        ...     data_source="results.json",
        ...     x_objective="f3",
        ...     y_objective="flatness"
        ... )
    """
    plot_type: str
    data_source: Union[str, Path, 'OptimizationResult']
    output_path: Optional[Union[str, Path]] = None
    figure_size: Tuple[int, int] = (12, 8)
    dpi: int = 150
    style: str = "default"
    show_plot: bool = False

    # Pareto-specific settings
    x_objective: str = "f3"
    y_objective: str = "flatness"
    z_objective: Optional[str] = None
    mark_knee: bool = True

    # SPL response settings
    frequency_range: Tuple[float, float] = (20, 20000)
    voltage: float = 2.83
    measurement_distance: float = 1.0

    # Design selection
    num_designs: Optional[int] = None
    design_indices: Optional[List[int]] = None

    # Horn profile settings
    show_dimensions: bool = True
    show_labels: bool = True
    profile_color: str = '#3498DB'

    # Parameter distribution settings
    plot_type_dist: str = "box"  # "box" or "violin"

    # Additional customization
    title: Optional[str] = None
    xlabel: Optional[str] = None
    ylabel: Optional[str] = None
    legend_loc: str = 'best'


@dataclass
class MultiPlotConfig:
    """
    Configuration for generating multiple plots in a grid layout.

    Attributes:
        plot_configs: List of individual plot configurations
        rows: Number of rows in subplot grid (None = auto)
        cols: Number of columns in subplot grid (None = auto)
        figure_size: Overall figure size (width, height) in inches
        dpi: Resolution for saved figures
        style: Plot style name
        output_path: Where to save the combined figure
        show_plot: Whether to display interactively
        share_x: Whether to share x-axis across subplots
        share_y: Whether to share y-axis across subplots

    Examples:
        >>> configs = [
        ...     PlotConfig(plot_type="pareto_2d", data_source="results.json"),
        ...     PlotConfig(plot_type="spl_response", data_source="results.json"),
        ... ]
        >>> multi_config = MultiPlotConfig(plot_configs, cols=2)
    """
    plot_configs: List[PlotConfig]
    rows: Optional[int] = None
    cols: Optional[int] = None
    figure_size: Tuple[int, int] = (14, 10)
    dpi: int = 150
    style: str = "default"
    output_path: Optional[Union[str, Path]] = None
    show_plot: bool = False
    share_x: bool = False
    share_y: bool = False


@dataclass
class PlotTheme:
    """
    Visual theme configuration for plots.

    Attributes:
        color_palette: Name of color palette to use
        marker_style: Marker style for scatter plots
        line_width: Line width for curves
        grid_alpha: Grid transparency (0-1)
        font_family: Font family name
        background_color: Figure background color
    """
    color_palette: str = "pareto"
    marker_style: str = "default"
    line_width: float = 2.0
    grid_alpha: float = 0.3
    font_family: str = "sans-serif"
    background_color: str = "white"


# Type alias for result loading
OptimizationResult = dict  # Will be properly imported in factory.py


# Preset configurations (data_source must be provided by user)
# These are templates that require data_source to be set
_PRESET_TEMPLATES = {
    'pareto_2d': {
        'plot_type': 'pareto_2d',
        'x_objective': 'f3',
        'y_objective': 'flatness',
        'mark_knee': True,
    },
    'pareto_3d': {
        'plot_type': 'pareto_3d',
        'x_objective': 'f3',
        'y_objective': 'flatness',
        'z_objective': 'size',
        'mark_knee': True,
    },
    'spl_response': {
        'plot_type': 'spl_response',
        'frequency_range': (20, 20000),
        'voltage': 2.83,
        'measurement_distance': 1.0,
    },
    'horn_profile': {
        'plot_type': 'horn_profile',
        'show_dimensions': True,
        'show_labels': True,
    },
    'parameter_distribution': {
        'plot_type': 'parameter_distribution',
        'plot_type_dist': 'box',
    },
}


def get_preset_config(preset_name: str, data_source: Union[str, Path, 'OptimizationResult'] = None) -> PlotConfig:
    """
    Get a preset plot configuration.

    Args:
        preset_name: Name of preset ('pareto_2d', 'pareto_3d', 'spl_response',
                     'horn_profile', 'parameter_distribution')
        data_source: Data source (file path or OptimizationResult object)

    Returns:
        PlotConfig instance

    Examples:
        >>> config = get_preset_config('pareto_2d', data_source="results.json")
        >>> config.plot_type
        'pareto_2d'
    """
    if preset_name not in _PRESET_TEMPLATES:
        raise ValueError(f"Unknown preset: {preset_name}. Available: {list(_PRESET_TEMPLATES.keys())}")

    # Create PlotConfig from template
    template = _PRESET_TEMPLATES[preset_name].copy()
    if data_source is not None:
        template['data_source'] = data_source

    return PlotConfig(**template)
