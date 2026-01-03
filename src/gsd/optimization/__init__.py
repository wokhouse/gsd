"""
Optimization and design exploration module for gsd.

This module provides automated multi-objective optimization, parameter space
exploration, and design assistance for loudspeaker enclosure design.

Key components:
- objectives: Functions for evaluating enclosure performance (F3, flatness, efficiency, size)
- constraints: Physical and performance constraint functions
- parameters: Parameter space definitions for different enclosure types
- recommenders: Enclosure type and alignment recommendation
- optimizers: Multi-objective optimization algorithms (NSGA-II)
- api: Agent-friendly Python API for programmatic access
- results: Pareto front analysis and design ranking
- validation: Validation against Hornresp
- factory: Optimization factory for script generation

Literature:
    - Small (1972) - Closed-box and vented box system parameters
    - Thiele (1971) - Vented box alignments
    - Beranek (1954) - Frequency response and efficiency
    - Olson (1947) - Horn theory
"""

from gsd.optimization.api import DesignAssistant, DesignRecommendation, OptimizationResult
from gsd.optimization.factory import OptimizationScriptFactory
from gsd.optimization.config import OptimizationConfig, AlgorithmConfig
from gsd.optimization.presets import (
    OPTIMIZATION_PRESETS,
    get_available_presets,
    get_preset_info,
    print_preset_table,
    suggest_preset,
)

__all__ = [
    # API
    "DesignAssistant",
    "DesignRecommendation",
    "OptimizationResult",
    # Factory
    "OptimizationScriptFactory",
    "OptimizationConfig",
    "AlgorithmConfig",
    # Presets
    "OPTIMIZATION_PRESETS",
    "get_available_presets",
    "get_preset_info",
    "print_preset_table",
    "suggest_preset",
]
