"""
Predefined plot presets for common analysis workflows.

This module provides pre-configured plot templates that encapsulate
best practices for different visualization scenarios. Each preset
specifies plot types, objectives, and parameters for a specific use case.

Literature:
    - Small (1972) - Loudspeaker enclosure response characteristics
    - Olson (1947) - Horn theory and wavefront quality
    - Keele (1975) - Wavefront sphericity and diffraction
"""

from typing import Dict, Any, List
from pathlib import Path


# Preset configurations
# Each preset defines: plot types with parameters, description, use cases
PLOT_PRESETS: Dict[str, Dict[str, Any]] = {
    "overview": {
        "description": "Quick assessment of optimization results",
        "plot_types": [
            {
                "type": "pareto_2d",
                "x_objective": "f3",
                "y_objective": "flatness",
            },
            {
                "type": "parameter_distribution",
            },
            {
                "type": "spl_response",
                "num_designs": 3,
            },
        ],
        "typical_use_cases": [
            "Initial review after optimization completes",
            "Quick check before diving deeper",
        ],
    },

    "spl": {
        "description": "Acoustic performance focus",
        "plot_types": [
            {
                "type": "spl_response",
                "num_designs": 5,
            },
            {
                "type": "pareto_2d",
                "x_objective": "f3",
                "y_objective": "efficiency",
            },
        ],
        "typical_use_cases": [
            "Evaluating sound quality",
            "Comparing designs for listening tests",
            "Selecting final design based on response",
        ],
    },

    "quality": {
        "description": "Qualitative metrics (wavefront, impedance, response quality)",
        "plot_types": [
            {
                "type": "pareto_2d",
                "x_objective": "wavefront_sphericity",
                "y_objective": "impedance_smoothness",
            },
            {
                "type": "pareto_2d",
                "x_objective": "flatness",
                "y_objective": "f3",
            },
            {
                "type": "parameter_distribution",
            },
        ],
        "typical_use_cases": [
            "Horn optimization for clean, non-harsh sound",
            "Minimizing diffraction and resonances",
            "Understanding quality vs extension trade-offs",
        ],
    },

    "correlations": {
        "description": "Parameter-objective relationship analysis",
        "plot_types": [
            {
                "type": "correlation_matrix",
            },
            {
                "type": "quality_dashboard",
            },
        ],
        "typical_use_cases": [
            "Understanding which parameters drive performance",
            "Identifying critical parameters",
            "Sensitivity analysis",
        ],
    },
}


def get_preset(preset_name: str) -> Dict[str, Any]:
    """
    Get preset configuration by name.

    Args:
        preset_name: Name of preset to retrieve

    Returns:
        Dictionary with preset configuration

    Raises:
        ValueError: If preset_name is not found

    Examples:
        >>> preset = get_preset("overview")
        >>> print(preset['description'])
        Quick assessment of optimization results
    """
    if preset_name not in PLOT_PRESETS:
        available = ", ".join(sorted(PLOT_PRESETS.keys()))
        raise ValueError(
            f"Unknown preset: '{preset_name}'. "
            f"Available presets: {available}"
        )

    return PLOT_PRESETS[preset_name]


def expand_preset_to_configs(
    preset_name: str,
    data_source: str,
    overrides: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Expand preset into list of plot configurations.

    Args:
        preset_name: Name of preset to expand
        data_source: Path to optimization results JSON file
        overrides: Optional overrides for plot parameters

    Returns:
        List of plot configuration dictionaries

    Examples:
        >>> configs = expand_preset_to_configs("spl", "results.json")
        >>> for config in configs:
        ...     print(f"{config['plot_type']}: {config.get('num_designs', 'all')}")
    """
    preset = get_preset(preset_name)
    configs = []

    for plot_config in preset["plot_types"]:
        # Start with preset configuration
        config = {
            "plot_type": plot_config["type"],
            "data_source": data_source,
        }

        # Add preset-specific parameters
        for key, value in plot_config.items():
            if key != "type":
                config[key] = value

        # Apply overrides if provided
        if overrides:
            for key, value in overrides.items():
                config[key] = value

        configs.append(config)

    return configs


def list_presets() -> List[str]:
    """
    List all available preset names.

    Returns:
        Sorted list of preset names

    Examples:
        >>> list_presets()
        ['overview', 'quality', 'spl']
    """
    return sorted(PLOT_PRESETS.keys())
