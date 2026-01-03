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

__all__ = [
    "DesignAssistant",
    "DesignRecommendation",
    "OptimizationResult",
    "ParameterSweepResult",
    "DesignExplorationQuery",
]
