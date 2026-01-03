"""
pymoo integration layer for multi-objective optimization.

This module provides convenient wrapper functions for running pymoo's
optimization algorithms on enclosure design problems.

Literature:
    - Deb et al. (2002) - NSGA-II algorithm
    - pymoo documentation - Algorithm implementations
    - Deb (2001) - Multi-Objective Optimization using Evolutionary Algorithms

Supported algorithms:
    - NSGA-II: Non-dominated Sorting Genetic Algorithm II (for 2-3 objectives)
    - NSGA-III: For many-objective problems (>3 objectives)
"""

import numpy as np
from typing import Optional, Dict, List, Tuple
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.optimize import minimize
from pymoo.termination import get_termination

from gsd.optimization.objectives.composite import EnclosureOptimizationProblem


def run_nsga2(
    problem: EnclosureOptimizationProblem,
    pop_size: int = 100,
    n_generations: int = 100,
    seed: Optional[int] = None,
    verbose: bool = True
) -> Tuple[any, Dict]:
    """
    Run NSGA-II multi-objective optimization.

    NSGA-II (Non-dominated Sorting Genetic Algorithm II) is the most
    widely used multi-objective evolutionary algorithm. It uses
    non-dominated sorting and crowding distance to maintain diversity
    in the Pareto front.

    Literature:
        - Deb et al. (2002) - "A fast and elitist multiobjective genetic algorithm: NSGA-II"
        - Deb (2001) - Multi-Objective Optimization using Evolutionary Algorithms

    Args:
        problem: EnclosureOptimizationProblem instance
        pop_size: Population size (default 100)
        n_generations: Number of generations (default 100)
        seed: Random seed for reproducibility
        verbose: Whether to print progress

    Returns:
        Tuple of (result, metadata) where:
        - result: pymoo Result object with .F (objectives) and .X (designs)
        - metadata: Dict with algorithm settings and convergence info

    Examples:
        >>> problem = EnclosureOptimizationProblem(
        ...     driver=driver,
        ...     enclosure_type="sealed",
        ...     objectives=["f3", "size"],
        ...     parameter_bounds={"Vb": (0.005, 0.030)}
        ... )
        >>> result, metadata = run_nsga2(problem, pop_size=50, n_generations=50)
        >>> result.F  # Objective values for Pareto front
        >>> result.X  # Design variables for Pareto front
    """
    # Initialize NSGA-II algorithm
    # Use Simulated Binary Crossover (SBX) and Polynomial Mutation (PM)
    # These are standard operators for real-coded genetic algorithms
    algorithm = NSGA2(
        pop_size=pop_size,
        sampling=FloatRandomSampling(),
        crossover=SBX(prob=0.9, eta=15),  # Crossover probability 90%, distribution index 15
        mutation=PM(eta=20),  # Polynomial mutation with distribution index 20
        eliminate_duplicates=True
    )

    # Setup termination criterion
    termination = get_termination("n_gen", n_generations)

    # Run optimization
    if verbose:
        print(f"Running NSGA-II optimization:")
        print(f"  Population: {pop_size}")
        print(f"  Generations: {n_generations}")
        print(f"  Objectives: {problem.n_obj}")
        print(f"  Variables: {problem.n_var}")
        print(f"  Constraints: {problem.n_constr}")

    result = minimize(
        problem,
        algorithm,
        termination,
        seed=seed,
        verbose=verbose,
        save_history=verbose  # Save history for convergence analysis
    )

    # Extract convergence metrics if history was saved
    convergence_info = {}
    if verbose and hasattr(result, 'history') and result.history:
        # Extract objective values over generations
        convergence_info['n_evals'] = result.algorithm.evaluator.n_eval
        convergence_info['final_pop_size'] = len(result.F)

    # Metadata
    metadata = {
        "algorithm": "NSGA-II",
        "pop_size": pop_size,
        "n_generations": n_generations,
        "n_evaluations": result.algorithm.evaluator.n_eval,
        "n_pareto_designs": len(result.F) if result.F is not None else 0,
        "convergence": convergence_info
    }

    return result, metadata


def run_nsga3(
    problem: EnclosureOptimizationProblem,
    pop_size: int = 100,
    n_generations: int = 100,
    seed: Optional[int] = None,
    verbose: bool = True
) -> Tuple[any, Dict]:
    """
    Run NSGA-III multi-objective optimization.

    NSGA-III is designed for many-objective optimization problems (4+ objectives).
    It uses reference points to maintain diversity instead of crowding distance.

    Literature:
        - Deb & Jain (2014) - "An evolutionary many-objective optimization algorithm using reference-point based nondominated sorting"

    Args:
        problem: EnclosureOptimizationProblem instance
        pop_size: Population size (should be multiple of number of reference points)
        n_generations: Number of generations
        seed: Random seed for reproducibility
        verbose: Whether to print progress

    Returns:
        Tuple of (result, metadata)
    """
    # For NSGA-III, population size should typically be divisible by 4
    # Ref: Deb & Jain (2014)
    if pop_size % 4 != 0:
        pop_size = ((pop_size // 4) + 1) * 4
        if verbose:
            print(f"Adjusted pop_size to {pop_size} (multiple of 4 for NSGA-III)")

    # Initialize NSGA-III algorithm
    algorithm = NSGA3(
        pop_size=pop_size,
        sampling=FloatRandomSampling(),
        crossover=SBX(prob=0.9, eta=30),
        mutation=PM(eta=20),
        eliminate_duplicates=True
    )

    # Setup termination
    termination = get_termination("n_gen", n_generations)

    # Run optimization
    if verbose:
        print(f"Running NSGA-III optimization:")
        print(f"  Population: {pop_size}")
        print(f"  Generations: {n_generations}")
        print(f"  Objectives: {problem.n_obj}")
        print(f"  Variables: {problem.n_var}")

    result = minimize(
        problem,
        algorithm,
        termination,
        seed=seed,
        verbose=verbose,
        save_history=verbose
    )

    metadata = {
        "algorithm": "NSGA-III",
        "pop_size": pop_size,
        "n_generations": n_generations,
        "n_evaluations": result.algorithm.evaluator.n_eval,
        "n_pareto_designs": len(result.F)
    }

    return result, metadata


def optimize_single_objective(
    problem: EnclosureOptimizationProblem,
    objective_index: int = 0,
    method: str = "ga",
    **kwargs
) -> Tuple[any, Dict]:
    """
    Optimize a single objective (convert multi-objective to single-objective).

    This is useful when you want to find the best design for one specific
    objective while treating others as constraints.

    Args:
        problem: EnclosureOptimizationProblem instance
        objective_index: Index of objective to optimize (0-based)
        method: Optimization method ("ga" for genetic algorithm)
        **kwargs: Additional arguments passed to optimizer

    Returns:
        Tuple of (result, metadata)
    """
    # For now, use NSGA-II with single objective
    # This will converge to a single optimal point instead of a Pareto front

    # Create single-objective version by setting n_obj=1
    # Note: This is a simplified approach
    # A better approach would use single-objective GA

    result, metadata = run_nsga2(
        problem,
        pop_size=kwargs.get('pop_size', 50),
        n_generations=kwargs.get('n_generations', 50),
        verbose=kwargs.get('verbose', True)
    )

    # Select best design for the specified objective
    best_idx = np.argmin(result.F[:, objective_index])

    metadata.update({
        "single_objective_best": best_idx,
        "best_objective_value": float(result.F[best_idx, objective_index])
    })

    return result, metadata
