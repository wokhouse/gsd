"""
Predefined optimization presets for common design scenarios.

This module provides pre-configured optimization templates that encapsulate
best practices for different design goals. Each preset specifies objectives,
constraints, and parameter space settings for a specific use case.

Presets:
    f3_target: Optimize for specific cutoff frequency with smooth response
    size_vs_f3: Explore trade-off between enclosure size and bass extension
    compact_bass: Small enclosure with acceptable bass extension
    max_efficiency: Maximize horn efficiency at target frequency
    flat_response: Prioritize smooth frequency response over extension
    balanced: Balanced trade-off between size, extension, and response quality

    Sealed Box Presets:
        sealed_butterworth: Maximally flat sealed box (Qtc=0.707)
        sealed_compact: Small sealed box for space-constrained designs
        sealed_deep_bass: Large sealed box for deep bass extension
        sealed_car: Car audio optimized (small box with cabin gain)

    Ported Box Presets:
        ported_b4: Butterworth B4 alignment (maximally flat)
        ported_qb3: Quasi-Butterworth 3rd order (tighter bass)
        ported_bb4: Extended bass shelf (more bass output)
        ported_compact: Compact ported design
        ported_car_audio: Car audio optimized (small box, higher tuning)
"""

from typing import Dict, Any, List


# Preset configurations
# Each preset defines: objectives, default constraints, parameter space preset
OPTIMIZATION_PRESETS: Dict[str, Dict[str, Any]] = {
    "f3_target": {
        "description": "Optimize for specific cutoff frequency with smooth response",
        "objectives": ["f3_deviation", "flatness"],
        "default_constraints": {
            "f3_target": 34.0,
            "f3_tolerance": 2.0,
        },
        "parameter_space_preset": "bass_horn",
        "typical_use_cases": [
            "Match room gain characteristics",
            "Align with main speaker crossover point",
            "Meet specific performance requirements",
        ],
    },

    "size_vs_f3": {
        "description": "Explore trade-off between enclosure size and bass extension",
        "objectives": ["f3", "volume", "flatness"],
        "default_constraints": {
            "max_volume": 500.0,  # liters
        },
        "parameter_space_preset": "bass_horn",
        "typical_use_cases": [
            "Find optimal size for given space constraints",
            "Understand size vs performance trade-offs",
            "Select design for specific application",
        ],
    },

    "compact_bass": {
        "description": "Small enclosure with acceptable bass extension",
        "objectives": ["volume", "flatness"],
        "default_constraints": {
            "f3_max": 45.0,
            "max_volume": 200.0,  # liters
        },
        "parameter_space_preset": "bass_horn",
        "typical_use_cases": [
            "Desktop or bookshelf systems",
            "Portable sound systems",
            "Space-constrained installations",
        ],
    },

    "max_efficiency": {
        "description": "Maximize horn efficiency at target frequency",
        "objectives": ["efficiency", "flatness"],
        "default_constraints": {
            "f3_max": 50.0,
            "min_efficiency": 0.15,  # 15%
        },
        "parameter_space_preset": "bass_horn",
        "typical_use_cases": [
            "High-efficiency main speakers",
            "Sound reinforcement systems",
            "Applications requiring high SPL with low power",
        ],
    },

    "flat_response": {
        "description": "Prioritize smooth frequency response over extension",
        "objectives": ["flatness", "f3"],
        "default_constraints": {
            "max_volume": 400.0,  # liters
        },
        "parameter_space_preset": "bass_horn",
        "typical_use_cases": [
            "High-fidelity systems",
            "Critical listening applications",
            "Studio monitoring",
        ],
    },

    "balanced": {
        "description": "Balanced trade-off between size, extension, and response quality",
        "objectives": ["f3", "volume", "flatness"],
        "default_constraints": {
            "max_volume": 350.0,  # liters
            "f3_max": 40.0,
        },
        "parameter_space_preset": "bass_horn",
        "typical_use_cases": [
            "General purpose bass horn",
            "Home theater subwoofers",
            "All-around performance",
        ],
    },

    "large_bass_horn": {
        "description": "Large bass horn for maximum extension and output",
        "objectives": ["f3", "flatness"],
        "default_constraints": {
            "min_mouth_area": 0.8,  # m² (large mouth for proper loading)
            "min_length": 2.5,  # meters (long horn for low cutoff)
        },
        "parameter_space_preset": "bass_horn",
        "typical_use_cases": [
            "Dedicated home theater",
            "High-output PA systems",
            "Applications where size is not constrained",
        ],
    },

    "midrange_horn": {
        "description": "Optimize midrange horn for smooth response and pattern control",
        "objectives": ["flatness"],
        "default_constraints": {
            "max_volume": 50.0,  # liters
        },
        "parameter_space_preset": "midrange_horn",
        "typical_use_cases": [
            "Midrange horns in multi-way systems",
            "Constant directivity horns",
            "PA system midrange drivers",
        ],
    },

    "folded_compact": {
        "description": "Optimize horn for compact folded implementation",
        "objectives": ["volume", "flatness", "f3"],
        "default_constraints": {
            "max_depth": 0.6,  # meters (fold depth constraint)
            "max_width": 0.5,  # meters
            "max_height": 0.5,  # meters
            "f3_max": 45.0,
        },
        "parameter_space_preset": "bass_horn",
        "typical_use_cases": [
            "Folded horns for home use",
            "Compact bass bins",
            "Space-constrained folded designs",
        ],
    },

    # Sealed Box Presets
    "sealed_butterworth": {
        "description": "Sealed box with maximally flat Butterworth response (Qtc=0.707)",
        "objectives": ["f3", "flatness"],
        "default_constraints": {
            "max_volume": 200.0,  # liters (will be overridden by driver Vas)
            "f3_max": 60.0,
        },
        "parameter_space_preset": "sealed",
        "typical_use_cases": [
            "High-fidelity home audio",
            "Critical listening systems",
            "Studio monitoring subwoofers",
            "Applications prioritizing transient response",
        ],
    },

    "sealed_compact": {
        "description": "Small sealed box for space-constrained installations",
        "objectives": ["volume", "f3"],
        "default_constraints": {
            "max_volume": 50.0,  # liters (very small)
            "f3_max": 80.0,  # Accept higher cutoff for small size
        },
        "parameter_space_preset": "sealed",
        "typical_use_cases": [
            "Desktop or bookshelf systems",
            "Compact home theater",
            "Multi-room audio systems",
            "Applications where space is at a premium",
        ],
    },

    "sealed_deep_bass": {
        "description": "Large sealed box for deep bass extension",
        "objectives": ["f3", "flatness"],
        "default_constraints": {
            "max_volume": 500.0,  # liters (large box)
            "f3_max": 30.0,  # Target deep bass
        },
        "parameter_space_preset": "sealed",
        "typical_use_cases": [
            "Dedicated home theater subwoofers",
            "High-end audio systems",
            "Applications where size is not constrained",
            "Critical music listening with deep bass requirements",
        ],
    },

    "sealed_car": {
        "description": "Sealed box optimized for car audio (small box, cabin gain)",
        "objectives": ["volume", "flatness"],
        "default_constraints": {
            "max_volume": 30.0,  # liters (very small for trunk/under-seat)
            "f3_max": 70.0,  # Cabin gain will extend response
        },
        "parameter_space_preset": "sealed",
        "typical_use_cases": [
            "Car audio subwoofers",
            "Trunk or under-seat installations",
            "Systems with cabin gain (12dB/octave below 50Hz)",
            "Mobile audio applications",
        ],
    },

    # Ported Box Presets
    "ported_b4": {
        "description": "Butterworth B4 alignment - maximally flat vented box response",
        "objectives": ["f3", "flatness"],
        "default_constraints": {
            "max_volume": 300.0,  # liters
            "f3_max": 40.0,
        },
        "parameter_space_preset": "ported",
        "typical_use_cases": [
            "High-fidelity home audio subwoofers",
            "Critical music listening",
            "Studio monitoring subwoofers",
            "Applications requiring accurate bass reproduction",
        ],
    },

    "ported_qb3": {
        "description": "Quasi-Butterworth 3rd order - tighter bass with good transient response",
        "objectives": ["f3", "flatness"],
        "default_constraints": {
            "max_volume": 250.0,  # liters
            "f3_max": 35.0,
        },
        "parameter_space_preset": "ported",
        "typical_use_cases": [
            "Music-oriented subwoofers",
            "Home theater with music priority",
            "Applications valuing transient response",
            "Tighter bass than B4 alignment",
        ],
    },

    "ported_bb4": {
        "description": "Extended bass shelf - maximum bass output with gentle rolloff",
        "objectives": ["f3", "flatness"],
        "default_constraints": {
            "max_volume": 200.0,  # liters (smaller than B4)
            "f3_max": 45.0,
        },
        "parameter_space_preset": "ported",
        "typical_use_cases": [
            "Home theater subwoofers",
            "High-output applications",
            "Party/dance music systems",
            "Applications prioritizing bass output over extension",
        ],
    },

    "ported_compact": {
        "description": "Compact ported design for space-constrained installations",
        "objectives": ["volume", "f3", "flatness"],
        "default_constraints": {
            "max_volume": 80.0,  # liters (compact)
            "f3_max": 50.0,  # Accept higher cutoff for small size
        },
        "parameter_space_preset": "ported",
        "typical_use_cases": [
            "Compact home theater",
            "Bookshelf subwoofers",
            "Desktop audio systems",
            "Space-constrained bass reinforcement",
        ],
    },

    "ported_car_audio": {
        "description": "Ported box optimized for car audio (small box, higher tuning)",
        "objectives": ["volume", "flatness"],
        "default_constraints": {
            "max_volume": 40.0,  # liters (small for car)
            "f3_max": 50.0,  # Cabin gain will extend response
        },
        "parameter_space_preset": "ported",
        "typical_use_cases": [
            "Car audio subwoofers",
            "Trunk or hatchback installations",
            "Systems with cabin gain",
            "Mobile audio with SPL requirements",
        ],
    },
}


def get_available_presets() -> List[str]:
    """
    Get list of available preset names.

    Returns:
        List of preset names

    Examples:
        >>> get_available_presets()
        ['f3_target', 'size_vs_f3', 'compact_bass', ...]
    """
    return list(OPTIMIZATION_PRESETS.keys())


def get_preset_info(preset: str) -> Dict[str, Any]:
    """
    Get detailed information about a preset.

    Args:
        preset: Preset name

    Returns:
        Dictionary with preset information including description,
        objectives, constraints, and use cases

    Raises:
        ValueError: If preset not found

    Examples:
        >>> info = get_preset_info("f3_target")
        >>> print(info['description'])
        Optimize for specific cutoff frequency with smooth response
        >>> print(info['objectives'])
        ['f3_deviation', 'flatness']
    """
    if preset not in OPTIMIZATION_PRESETS:
        raise ValueError(
            f"Unknown preset '{preset}'. Available: {get_available_presets()}"
        )

    return OPTIMIZATION_PRESETS[preset].copy()


def print_preset_table():
    """
    Print a formatted table of all available presets.

    Useful for CLI display of available options.

    Examples:
        >>> print_preset_table()
        Available Optimization Presets:
        ...
    """
    print("\nAvailable Optimization Presets:")
    print("=" * 80)

    for name, config in OPTIMIZATION_PRESETS.items():
        print(f"\n{name}:")
        print(f"  Description: {config['description']}")
        print(f"  Objectives: {', '.join(config['objectives'])}")
        print(f"  Parameter Space: {config['parameter_space_preset']}")
        print(f"  Use Cases:")
        for use_case in config['typical_use_cases']:
            print(f"    - {use_case}")

    print("=" * 80)


def suggest_preset(
    target_f3: float = None,
    max_volume_liters: float = None,
    priority: str = "balanced"
) -> str:
    """
    Suggest appropriate preset based on design requirements.

    Args:
        target_f3: Target cutoff frequency in Hz
        max_volume_liters: Maximum enclosure volume in liters
        priority: Design priority ("size", "extension", "efficiency", "balanced")

    Returns:
        Recommended preset name

    Examples:
        >>> suggest_preset(target_f3=35, max_volume_liters=300)
        'f3_target'
        >>> suggest_preset(max_volume_liters=100, priority="size")
        'compact_bass'
    """
    # Size-constrained designs
    if max_volume_liters and max_volume_liters < 150:
        if target_f3 and target_f3 < 40:
            return "folded_compact"
        return "compact_bass"

    # Extension-focused
    if target_f3 and target_f3 < 35:
        if max_volume_liters and max_volume_liters > 400:
            return "large_bass_horn"
        return "f3_target"

    # Priority-based selection
    if priority == "size":
        return "compact_bass"
    elif priority == "extension":
        return "f3_target"
    elif priority == "efficiency":
        return "max_efficiency"
    elif priority == "balanced":
        if max_volume_liters and max_volume_liters < 300:
            return "size_vs_f3"
        return "balanced"

    # Default
    return "balanced"
