"""
Structured result types for agent-friendly API.

This module provides dataclasses for structured return types that AI agents
and other tools can easily parse and process. All API methods return these
structures rather than printing text output.

Classes:
    DesignRecommendation: Enclosure type recommendation with reasoning
    OptimizationResult: Multi-objective optimization results
    ParameterSweepResult: Parameter sweep results with insights
    DesignExplorationQuery: Query parameters for exploration
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import numpy as np


@dataclass
class DesignExplorationQuery:
    """
    Query parameters for design space exploration.

    Attributes:
        driver_name: Name of driver (e.g., "BC_12NDL76")
        objectives: List of objectives to optimize
        constraints: Dict of constraint names and values
        enclosure_preference: Preferred enclosure type ("sealed", "ported", "horn", "auto")
        max_enclosure_volume: Maximum allowed volume in m³
        target_f3: Target cutoff frequency in Hz
        priorities: Dict of objective priorities (1-5, higher = more important)
    """
    driver_name: str
    objectives: List[str] = field(default_factory=lambda: ["f3", "size"])
    constraints: Dict[str, float] = field(default_factory=dict)
    enclosure_preference: str = "auto"
    max_enclosure_volume: Optional[float] = None
    target_f3: Optional[float] = None
    priorities: Dict[str, int] = field(default_factory=dict)


@dataclass
class DesignRecommendation:
    """
    Structured enclosure recommendation for agents.

    This class provides a complete recommendation with enclosure type,
    suggested parameters, expected performance, and reasoning.

    Attributes:
        enclosure_type: Recommended enclosure type ("sealed", "ported", "exponential_horn")
        confidence: Confidence score (0.0 to 1.0) in the recommendation
        reasoning: Explanation of recommendation with literature citations
        suggested_parameters: Dict of parameter values (e.g., {"Vb": 0.020})
        expected_performance: Dict of expected performance metrics
        alternatives: List of alternative enclosure types with reasons
        trade_offs: Description of key design trade-offs
        validation_notes: List of validation warnings or notes

    Examples:
        >>> rec = DesignRecommendation(
        ...     enclosure_type="sealed",
        ...     confidence=0.85,
        ...     reasoning="Qts=0.37 is ideal for sealed box (Small 1972)",
        ...     suggested_parameters={"Vb": 0.020},
        ...     expected_performance={"F3": 58.2, "Qtc": 0.71}
        ... )
        >>> rec.enclosure_type
        'sealed'
        >>> rec.suggested_parameters['Vb']
        0.020
    """
    enclosure_type: str
    confidence: float
    reasoning: str
    suggested_parameters: Dict[str, float]
    expected_performance: Dict[str, float]
    alternatives: List[Dict] = field(default_factory=list)
    trade_offs: str = ""
    validation_notes: List[str] = field(default_factory=list)


@dataclass
class OptimizationResult:
    """
    Result from multi-objective optimization.

    This class contains the complete results from running NSGA-II or other
    multi-objective optimization algorithms.

    Attributes:
        success: True if optimization completed successfully
        pareto_front: List of all Pareto-optimal designs found
        n_designs_found: Number of designs on Pareto front
        best_designs: Top N designs ranked by criteria
        parameter_names: List of parameter names
        objective_names: List of objective names optimized
        optimization_metadata: Dict with algorithm, population, generations, etc.
        convergence_info: Convergence metrics (if available)
        warnings: List of warnings about results

    Examples:
        >>> result = OptimizationResult(
        ...     success=True,
        ...     pareto_front=[{"parameters": {"Vb": 0.018}, "objectives": {"f3": 60.2, "size": 0.018}}],
        ...     n_designs_found=89,
        ...     best_designs=[...],
        ...     parameter_names=["Vb"],
        ...     objective_names=["f3", "size"],
        ...     optimization_metadata={"algorithm": "NSGA-II", "generations": 100}
        ... )
        >>> result.n_designs_found
        89
        >>> result.best_designs[0]['objectives']['f3']
        60.2
    """
    success: bool
    pareto_front: List[Dict[str, Any]]
    n_designs_found: int
    best_designs: List[Dict]
    parameter_names: List[str]
    objective_names: List[str]
    optimization_metadata: Dict
    convergence_info: Dict = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ParameterSweepResult:
    """
    Result from parameter sweep exploration.

    This class contains the results of sweeping a single parameter
    across a range of values and evaluating the objectives.

    Attributes:
        parameter_swept: Name of parameter that was swept
        parameter_values: Array of parameter values tested
        results: Dict mapping objective names to arrays of values
        sensitivity_analysis: Dict with sensitivity metrics
        recommendations: List of textual insights from sweep

    Examples:
        >>> sweep = ParameterSweepResult(
        ...     parameter_swept="Vb",
        ...     parameter_values=np.linspace(0.01, 0.03, 50),
        ...     results={"F3": f3_array, "size": size_array},
        ...     sensitivity_analysis={"f3_sensitivity": 0.85},
        ...     recommendations=["Best F3 at Vb=0.025m³"]
        ... )
        >>> sweep.parameter_swept
        'Vb'
        >>> sweep.recommendations[0]
        'Best F3 at Vb=0.025m³'
    """
    parameter_swept: str
    parameter_values: np.ndarray
    results: Dict[str, np.ndarray]
    sensitivity_analysis: Dict
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """
    Result from validating a design against Hornresp.

    Attributes:
        design_valid: True if design passes all validation checks
        f3_error_percent: Error in F3 calculation compared to Hornresp
        spl_max_error_db: Maximum SPL error across frequency range
        impedance_max_error_percent: Maximum impedance error
        all_passed: True if all metrics within tolerance
        warnings: List of validation warnings
    """
    design_valid: bool
    f3_error_percent: float
    spl_max_error_db: float
    impedance_max_error_percent: float
    all_passed: bool
    warnings: List[str] = field(default_factory=list)


# Utility functions for working with results
def design_to_dict(design: Dict, parameter_names: List[str], objective_names: List[str]) -> Dict:
    """
    Convert a design from array format to dict format.

    Args:
        design: Dict with 'x' (parameters) and 'F' (objectives) arrays
        parameter_names: List of parameter names
        objective_names: List of objective names

    Returns:
        Dict with parameter and objective key-value pairs
    """
    return {
        "parameters": dict(zip(parameter_names, design['x'])),
        "objectives": dict(zip(objective_names, design['F']))
    }


def rank_pareto_designs(
    pareto_front: List[Dict],
    objectives: List[str],
    weights: Dict[str, float] = None
) -> List[Dict]:
    """
    Rank Pareto-optimal designs by weighted objectives.

    Args:
        pareto_front: List of designs with 'parameters' and 'objectives'
        objectives: List of objective names
        weights: Dict mapping objective names to weights (default: equal weights)

    Returns:
        List of designs sorted by rank (best first)
    """
    if weights is None:
        weights = {obj: 1.0 for obj in objectives}

    ranked = []
    for design in pareto_front:
        # Calculate weighted score
        score = 0.0
        for obj in objectives:
            if obj in weights:
                # Normalize objective to 0-1 range (simplified)
                # In practice, should use proper normalization
                score += weights[obj] * design['objectives'].get(obj, 0)

        ranked.append({**design, 'rank_score': score})

    # Sort by score (lower is better for minimization)
    ranked.sort(key=lambda d: d['rank_score'])

    return ranked
