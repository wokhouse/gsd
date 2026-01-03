"""
Pareto front analysis and design ranking.

This module provides functions for analyzing multi-objective optimization
results, extracting Pareto fronts, and ranking designs by various criteria.

Literature:
    - Deb (2001) - Multi-Objective Optimization using Evolutionary Algorithms
    - Pareto dominance principles
"""

import numpy as np
from typing import List, Dict, Tuple, Optional


def analyze_pareto_front(
    result,
    objectives: List[str],
    parameter_names: List[str]
) -> Dict:
    """
    Analyze Pareto front from optimization result.

    Literature:
        - Deb (2001) - Pareto dominance and front analysis

    Args:
        result: pymoo optimization result
        objectives: List of objective names
        parameter_names: List of parameter names

    Returns:
        Dict with Pareto front analysis including:
        - n_designs: Number of designs on Pareto front
        - objective_ranges: Min/max for each objective
        - extreme_designs: Best design for each objective
        - correlation: Correlation matrix between objectives
    """
    F = result.F  # Objective values (n_designs × n_obj)
    X = result.X  # Design variables (n_designs × n_var)

    n_designs = len(F)

    # Calculate objective ranges
    objective_ranges = {}
    for i, obj_name in enumerate(objectives):
        objective_ranges[obj_name] = {
            "min": float(np.min(F[:, i])),
            "max": float(np.max(F[:, i])),
            "mean": float(np.mean(F[:, i])),
            "std": float(np.std(F[:, i]))
        }

    # Find extreme designs (best for each objective)
    extreme_designs = {}
    for i, obj_name in enumerate(objectives):
        best_idx = np.argmin(F[:, i])
        extreme_designs[obj_name] = {
            "index": int(best_idx),
            "objective_value": float(F[best_idx, i]),
            "parameters": dict(zip(parameter_names, X[best_idx])),
            "all_objectives": dict(zip(objectives, F[best_idx]))
        }

    # Calculate correlation between objectives
    # This shows trade-offs (negative correlation = trade-off)
    if n_designs > 1:
        correlation_matrix = np.corrcoef(F.T)
        correlation = {}
        for i, obj1 in enumerate(objectives):
            for j, obj2 in enumerate(objectives):
                if i < j:  # Only upper triangle
                    corr_key = f"{obj1}_vs_{obj2}"
                    correlation[corr_key] = float(correlation_matrix[i, j])
    else:
        correlation = {}

    return {
        "n_designs": n_designs,
        "objective_ranges": objective_ranges,
        "extreme_designs": extreme_designs,
        "correlation": correlation
    }


def rank_designs(
    result,
    objectives: List[str],
    parameter_names: List[str],
    weights: Optional[Dict[str, float]] = None,
    top_n: Optional[int] = None
) -> List[Dict]:
    """
    Rank Pareto-optimal designs by multiple criteria.

    This function ranks designs using a weighted sum approach. Lower rank
    is better (minimization).

    Args:
        result: pymoo optimization result
        objectives: List of objective names
        parameter_names: List of parameter names
        weights: Optional dict mapping objective names to weights
        top_n: Only return top N designs (None = return all)

    Returns:
        List of dicts, each containing:
        - rank: Overall rank score
        - parameters: Dict of parameter values
        - objectives: Dict of objective values
    """
    F = result.F  # Objective values
    X = result.X  # Design variables

    # Handle single-objective case (F is 1D)
    if len(objectives) == 1:
        # For single objective, just sort by objective value
        # F might be 1D array or 2D array with shape (n, 1)
        if len(F.shape) == 1:
            f_values = F  # Already 1D
            X_values = X if len(X.shape) == 2 else X.reshape(-1, 1)
        else:
            f_values = F[:, 0]  # Convert (n, 1) to (n,)
            X_values = X

        indices = np.argsort(f_values)
        if top_n:
            indices = indices[:top_n]

        output = []
        for idx in indices:
            # Handle both 1D and 2D X arrays
            if len(X.shape) == 1:
                x_row = X  # Single design
            elif len(X.shape) == 2:
                x_row = X[idx]
            else:
                x_row = X[idx]

            output.append({
                "rank": float(f_values[idx]),
                "parameters": dict(zip(parameter_names, x_row)),
                "objectives": {objectives[0]: float(f_values[idx])}
            })
        return output

    # Multi-objective case
    # Set default weights (equal weighting)
    if weights is None:
        weights = {obj: 1.0 for obj in objectives}

    # Normalize objectives to [0, 1] range
    # This prevents objectives with large magnitudes from dominating
    F_normalized = np.zeros_like(F)
    for i in range(F.shape[1]):
        f_min = np.min(F[:, i])
        f_max = np.max(F[:, i])
        if f_max > f_min:
            F_normalized[:, i] = (F[:, i] - f_min) / (f_max - f_min)
        else:
            F_normalized[:, i] = 0.0

    # Calculate weighted scores
    ranked = []
    for i in range(len(F)):
        # Weighted sum of normalized objectives
        score = 0.0
        for j, obj_name in enumerate(objectives):
            if obj_name in weights:
                score += weights[obj_name] * F_normalized[i, j]

        ranked.append({
            "rank": score,
            "x": X[i],
            "F": F[i]
        })

    # Sort by rank (ascending - lower is better)
    ranked.sort(key=lambda d: d["rank"])

    # Convert to output format
    output = []
    for i, design in enumerate(ranked[:top_n] if top_n else ranked):
        output.append({
            "rank": float(design["rank"]),
            "parameters": dict(zip(parameter_names, design["x"])),
            "objectives": dict(zip(objectives, design["F"]))
        })

    return output


def select_knee_point(
    result,
    objectives: List[str],
    parameter_names: List[str]
) -> Dict:
    """
    Select knee point from Pareto front.

    The knee point is a design that represents a good compromise between
    objectives - it's the point where improving one objective would cause
    a disproportionately large degradation in another.

    Literature:
        - Branke et al. (2004) - "Finding knees in multi-objective optimization"

    Args:
        result: pymoo optimization result
        objectives: List of objective names (must have exactly 2)
        parameter_names: List of parameter names

    Returns:
        Dict with knee point design

    Note:
        Currently only implemented for 2-objective problems.
        For more objectives, returns the design with minimum distance to utopia point.
    """
    F = result.F
    X = result.X

    if len(objectives) == 2:
        # For 2 objectives, find point with maximum angle from origin
        # Normalize to [0, 1]
        F_norm = np.zeros_like(F)
        for i in range(2):
            f_min = np.min(F[:, i])
            f_max = np.max(F[:, i])
            if f_max > f_min:
                F_norm[:, i] = (F[:, i] - f_min) / (f_max - f_min)

        # Find point with minimum distance to (0, 0) in normalized space
        # This is a simplified knee point selection
        distances = np.sqrt(F_norm[:, 0]**2 + F_norm[:, 1]**2)
        knee_idx = np.argmin(distances)

    else:
        # For more than 2 objectives, find point closest to utopia point
        utopia = np.min(F, axis=0)
        distances = np.sqrt(np.sum((F - utopia)**2, axis=1))
        knee_idx = np.argmin(distances)

    return {
        "parameters": dict(zip(parameter_names, X[knee_idx])),
        "objectives": dict(zip(objectives, F[knee_idx])),
        "distance_to_ideal": float(distances[knee_idx]) if len(objectives) > 2 else float(distances[knee_idx])
    }


def calculate_hypervolume(
    result,
    reference_point: np.ndarray
) -> float:
    """
    Calculate hypervolume indicator for Pareto front.

    Hypervolume measures the volume of objective space dominated by the
    Pareto front relative to a reference point. Larger is better.

    Literature:
        - Zitzler & Thiele (1999) - "Multiobjective evolutionary algorithms:
          A comparative case study and the strength Pareto approach"

    Args:
        result: pymoo optimization result
        reference_point: Reference point for hypervolume calculation

    Returns:
        Hypervolume value

    Note:
        This requires pymoo's hypervolume calculation.
        For now, returns a placeholder.
    """
    # Placeholder - would use pymoo.indicators.HV in full implementation
    # from pymoo.indicators.hv import HV
    # indicator = HV(ref_point=reference_point)
    # return indicator.calc(result.F)

    # Simple approximation: volume of bounding box
    F = result.F
    hv = 1.0
    for i in range(F.shape[1]):
        hv *= (reference_point[i] - np.min(F[:, i]))

    return hv
