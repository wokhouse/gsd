"""
Agent-friendly API for enclosure design optimization.

This module provides structured, programmatic interfaces for AI agents
and other tools to interact with gsd's optimization capabilities.

Classes:
    DesignAssistant: High-level API for design exploration
    DesignRecommendation: Structured recommendation with reasoning
    OptimizationResult: Result from multi-objective optimization
    ParameterSweepResult: Result from parameter sweep
"""

from gsd.optimization.api.result_structures import (
    DesignRecommendation,
    OptimizationResult,
    ParameterSweepResult,
    DesignExplorationQuery,
)
from gsd.optimization.api.design_assistant import DesignAssistant

# Horn export and dispersion analysis
from gsd.optimization.api import horn_export
from gsd.optimization.api import horn_dispersion

__all__ = [
    "DesignAssistant",
    "DesignRecommendation",
    "OptimizationResult",
    "ParameterSweepResult",
    "DesignExplorationQuery",
    # Horn export
    "export_horn_profile",
    "export_horn_profile_dxf",
    "export_horn_profile_csv",
    "calculate_exponential_horn_profile",
    # Horn dispersion
    "analyze_horn_dispersion",
    "circular_piston_directivity",
    "calculate_directivity_index",
    "calculate_beam_width",
    "recommend_mouth_size",
]
