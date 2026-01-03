"""
Optimization factory for automated horn design workflows.

This module provides the OptimizationScriptFactory class, which generates
and executes optimization workflows from configuration objects. It eliminates
code duplication across optimization scripts and provides a consistent interface.

Literature:
    - Deb et al. (2002) - NSGA-II multi-objective optimization algorithm
    - Small (1972) - Closed-box and vented box system parameters
    - Olson (1947) - Horn theory and cutoff frequency
"""

import os
import json
import numpy as np
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.operators.sampling.lhs import LHS
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.optimize import minimize
from pymoo.core.problem import Problem
from pymoo.util.ref_dirs import get_reference_directions

from gsd.driver import load_driver
from gsd.driver.parameters import ThieleSmallParameters
from gsd.optimization.config import OptimizationConfig, AlgorithmConfig
from gsd.optimization.api.result_structures import OptimizationResult


class OptimizationScriptFactory:
    """
    Factory for creating and executing optimization workflows.

    This class provides a high-level interface for running multi-objective
    optimization of loudspeaker enclosures. It handles parameter space setup,
    problem formulation, algorithm configuration, and result processing.

    Attributes:
        config: Optimization configuration
        driver: Driver parameters
        param_space: Parameter space for optimization

    Examples:
        >>> from gsd.optimization.factory import OptimizationScriptFactory
        >>> from gsd.optimization.config import OptimizationConfig
        >>>
        >>> config = OptimizationConfig(
        ...     driver_name="BC_21DS115",
        ...     enclosure_type="multisegment_horn",
        ...     objectives=["f3_deviation", "flatness"],
        ...     constraints={"f3_target": 34.0, "f3_tolerance": 2.0}
        ... )
        >>> factory = OptimizationScriptFactory(config)
        >>> results = factory.run()
        >>> print(results.best_designs[0]['objectives']['f3'])
    """

    def __init__(self, config: OptimizationConfig):
        """
        Initialize factory with configuration.

        Args:
            config: Optimization configuration

        Raises:
            ValueError: If configuration is invalid
        """
        self.config = config
        self.driver = load_driver(config.driver_name)
        self.param_space = None
        self._problem = None
        self._algorithm = None

    def _get_parameter_space(self):
        """Get parameter space for enclosure type."""
        if self.config.enclosure_type == "exponential_horn":
            from gsd.optimization.parameters.exponential_horn_params import (
                get_exponential_horn_parameter_space,
            )
            return get_exponential_horn_parameter_space(
                self.driver, preset=self.config.parameter_space_preset
            )

        elif self.config.enclosure_type == "multisegment_horn":
            from gsd.optimization.parameters.multisegment_horn_params import (
                get_multisegment_horn_parameter_space,
            )
            return get_multisegment_horn_parameter_space(
                self.driver,
                preset=self.config.parameter_space_preset,
                num_segments=2
            )

        elif self.config.enclosure_type == "mixed_profile_horn":
            from gsd.optimization.parameters.multisegment_horn_params import (
                get_mixed_profile_parameter_space,
            )
            return get_mixed_profile_parameter_space(
                self.driver,
                preset=self.config.parameter_space_preset,
                num_segments=2
            )

        elif self.config.enclosure_type == "conical_horn":
            from gsd.optimization.parameters.conical_horn_params import (
                get_conical_horn_parameter_space,
            )
            return get_conical_horn_parameter_space(
                self.driver, preset=self.config.parameter_space_preset
            )

        elif self.config.enclosure_type == "sealed":
            from gsd.optimization.parameters.sealed_box_params import (
                get_sealed_box_parameter_space,
            )
            return get_sealed_box_parameter_space(self.driver)

        elif self.config.enclosure_type == "ported":
            from gsd.optimization.parameters.ported_box_params import (
                get_ported_box_parameter_space,
            )
            return get_ported_box_parameter_space(self.driver)

        else:
            raise ValueError(
                f"Unsupported enclosure type: {self.config.enclosure_type}"
            )

    def _apply_parameter_overrides(self, base_space):
        """Apply parameter override bounds from config."""
        from gsd.optimization.parameters.parameter_space import ParameterRange

        if not self.config.parameter_overrides:
            return base_space

        # Create new parameters list with overrides
        new_parameters = []
        for param in base_space.parameters:
            if param.name in self.config.parameter_overrides:
                min_val, max_val = self.config.parameter_overrides[param.name]
                new_param = ParameterRange(
                    name=param.name,
                    min_value=min_val,
                    max_value=max_val,
                    units=param.units,
                    description=param.description
                )
                new_parameters.append(new_param)
            else:
                new_parameters.append(param)

        # Create new parameter space with overridden parameters
        base_space.parameters = new_parameters
        return base_space

    def _build_objective_functions(self) -> List[Tuple[str, Callable]]:
        """
        Build list of (objective_name, objective_function) tuples.

        Returns:
            List of objective functions
        """
        from gsd.optimization.objectives.response_metrics import (
            objective_f3,
            objective_response_flatness,
            objective_passband_flatness,
        )
        from gsd.optimization.objectives.size_metrics import (
            objective_enclosure_volume,
        )
        from gsd.optimization.objectives.efficiency import (
            objective_efficiency,
        )

        objectives_map = {
            "f3": ("f3", objective_f3),
            "f3_deviation": ("f3_deviation", self._create_f3_deviation_objective()),
            "flatness": ("flatness", objective_response_flatness),
            "passband_flatness": ("passband_flatness", objective_passband_flatness),
            "volume": ("volume", objective_enclosure_volume),
            "efficiency": ("efficiency", objective_efficiency),
        }

        return [objectives_map[obj] for obj in self.config.objectives]

    def _create_f3_deviation_objective(self) -> Callable:
        """Create F3 deviation objective function from target in constraints."""
        target_f3 = self.config.constraints.get("f3_target", 40.0)

        def f3_deviation(X, driver, enclosure_type, **kwargs):
            """Calculate absolute deviation from target F3."""
            from gsd.optimization.objectives.response_metrics import objective_f3
            f3_actual = objective_f3(X, driver, enclosure_type, **kwargs)
            return abs(f3_actual - target_f3)

        return f3_deviation

    def _build_constraint_functions(self) -> List[Tuple[str, Callable]]:
        """
        Build list of (constraint_name, constraint_function) tuples.

        Returns:
            List of constraint functions
        """
        from gsd.optimization.constraints.physical import (
            constraint_multisegment_continuity,
            constraint_multisegment_flare_limits,
            constraint_horn_throat_sizing,
            constraint_max_displacement,
            constraint_mouth_loading,
        )
        from gsd.optimization.constraints.performance import (
            constraint_f3_limit,
            constraint_volume_limit,
        )

        # Standard horn constraints
        constraints = []

        # Always include continuity for multisegment horns
        if "multisegment" in self.config.enclosure_type or "mixed" in self.config.enclosure_type:
            constraints.append(("continuity", constraint_multisegment_continuity))
            constraints.append(("flare_limits", constraint_multisegment_flare_limits))

        # Throat sizing
        if "horn" in self.config.enclosure_type:
            constraints.append(("throat_sizing", constraint_horn_throat_sizing))
            constraints.append(("max_displacement", constraint_max_displacement))

        # Performance constraints from config
        if "f3_max" in self.config.constraints:
            f3_limit = self.config.constraints["f3_max"]
            # Create wrapper function with parameter
            def f3_max_constraint(X, driver, enclosure_type):
                return constraint_f3_limit(X, driver, enclosure_type, f3_max_hz=f3_limit)
            constraints.append(("f3_max", f3_max_constraint))

        if "max_volume" in self.config.constraints:
            volume_limit = self.config.constraints["max_volume"]
            # Create wrapper function with parameter
            def volume_limit_constraint(X, driver, enclosure_type):
                return constraint_volume_limit(X, driver, enclosure_type, max_volume_liters=volume_limit)
            constraints.append(("volume_limit", volume_limit_constraint))

        return constraints

    def _create_problem(self) -> Problem:
        """
        Create pymoo Problem from configuration.

        Returns:
            Configured optimization problem
        """
        # Get parameter space
        param_space = self._get_parameter_space()
        param_space = self._apply_parameter_overrides(param_space)
        self.param_space = param_space

        # Get bounds
        xl, xu = param_space.get_bounds_array()
        n_var = len(xl)

        # Get objectives and constraints
        objective_funcs = self._build_objective_functions()
        constraint_funcs = self._build_constraint_functions()

        n_obj = len(objective_funcs)
        n_constr = len(constraint_funcs)

        # Create problem class dynamically
        class FactoryOptimizationProblem(Problem):
            def __init__(self, factory):
                self.factory = factory
                self.objective_funcs = objective_funcs
                self.constraint_funcs = constraint_funcs
                self.driver = factory.driver
                self.enclosure_type = factory.config.enclosure_type

                super().__init__(
                    n_var=n_var,
                    n_obj=n_obj,
                    n_constr=n_constr,
                    xl=xl,
                    xu=xu,
                )

            def _evaluate(self, X, out, *args, **kwargs):
                """Evaluate designs."""
                n_samples = X.shape[0]
                objectives = np.zeros((n_samples, n_obj))
                constraints = np.zeros((n_samples, n_constr))

                for i in range(n_samples):
                    design = X[i]

                    try:
                        # Evaluate objectives - each may have different signature
                        for j, (obj_name, obj_func) in enumerate(self.objective_funcs):
                            # Call objective with appropriate arguments
                            if obj_name in ["flatness", "passband_flatness"]:
                                obj_val = obj_func(
                                    design,
                                    self.driver,
                                    self.enclosure_type,
                                    frequency_range=(20.0, 200.0),
                                    n_points=100,
                                )
                            else:
                                # For f3, volume, efficiency - use simpler signature
                                obj_val = obj_func(
                                    design,
                                    self.driver,
                                    self.enclosure_type,
                                )
                            objectives[i, j] = obj_val

                        # Evaluate constraints
                        for j, (constr_name, constr_func) in enumerate(self.constraint_funcs):
                            constr_val = constr_func(
                                design,
                                self.driver,
                                self.enclosure_type,
                            )
                            constraints[i, j] = constr_val

                    except Exception as e:
                        # Penalize invalid designs
                        if self.factory.config.verbose:
                            print(f"Warning: Design {i} failed: {e}")
                        objectives[i, :] = 1e6
                        constraints[i, :] = 1e6

                out["F"] = objectives
                out["G"] = constraints

        return FactoryOptimizationProblem(self)

    def _create_algorithm(self) -> NSGA2:
        """
        Create optimization algorithm from config.

        Returns:
            Configured algorithm instance
        """
        algo_config = self.config.algorithm

        # Select sampling method
        if algo_config.sampling == "lhs":
            sampling = LHS()
        else:
            sampling = FloatRandomSampling()

        # Create algorithm based on type
        if algo_config.type == "nsga2":
            algorithm = NSGA2(
                pop_size=algo_config.pop_size,
                sampling=sampling,
                crossover=SBX(
                    prob=algo_config.crossover_prob,
                    eta=algo_config.crossover_eta
                ),
                mutation=PM(eta=algo_config.mutation_eta),
                eliminate_duplicates=algo_config.eliminate_duplicates
            )

        elif algo_config.type == "nsga3":
            # NSGA-III requires reference directions for >2 objectives
            ref_dirs = get_reference_directions(
                "das-dennis",
                len(self.config.objectives),
                n_partitions=12
            )
            algorithm = NSGA3(
                pop_size=algo_config.pop_size,
                ref_dirs=ref_dirs,
                sampling=sampling,
                crossover=SBX(
                    prob=algo_config.crossover_prob,
                    eta=algo_config.crossover_eta
                ),
                mutation=PM(eta=algo_config.mutation_eta),
                eliminate_duplicates=algo_config.eliminate_duplicates
            )

        else:
            raise ValueError(f"Unsupported algorithm: {algo_config.type}")

        return algorithm

    def run(self) -> OptimizationResult:
        """
        Execute optimization and return results.

        Returns:
            OptimizationResult with Pareto front and best designs

        Raises:
            RuntimeError: If optimization fails
        """
        if self.config.verbose:
            print("=" * 80)
            print(f"Optimization: {self.config.driver_name} - {self.config.enclosure_type}")
            print(f"Objectives: {', '.join(self.config.objectives)}")
            if self.config.constraints:
                print(f"Constraints:")
                for key, value in self.config.constraints.items():
                    print(f"  - {key}: {value}")
            print("=" * 80)

        # Create problem
        if self.config.verbose:
            print("\n[1/4] Creating optimization problem...")
        self._problem = self._create_problem()

        # Create algorithm
        if self.config.verbose:
            print("[2/4] Configuring algorithm...")
        self._algorithm = self._create_algorithm()

        # Run optimization
        if self.config.verbose:
            print(f"[3/4] Running optimization ({self.config.algorithm.n_generations} generations)...")
            print("  Progress: [", end="", flush=True)

        result = minimize(
            self._problem,
            self._algorithm,
            termination=('n_gen', self.config.algorithm.n_generations),
            verbose=False,
            callback=lambda alg: print("=", end="", flush=True) if alg.n_gen % max(1, self.config.algorithm.n_generations // 20) == 0 and self.config.verbose else None
        )

        if self.config.verbose:
            print(f"] {self.config.algorithm.n_generations}/{self.config.algorithm.n_generations} generations")

        # Process results
        if self.config.verbose:
            print("[4/4] Processing results...")

        processed_result = self._process_results(result)

        # Save results if requested
        if self.config.save_results:
            self._save_results(processed_result)

        if self.config.verbose:
            print("\n" + "=" * 80)
            print(f"Optimization complete! Found {processed_result.n_designs_found} Pareto-optimal designs.")
            print("=" * 80)

        return processed_result

    def _process_results(self, pymoo_result) -> OptimizationResult:
        """
        Process pymoo result into structured OptimizationResult.

        Args:
            pymoo_result: Raw result from pymoo minimize()

        Returns:
            Processed OptimizationResult
        """
        import numpy as np

        # Extract Pareto front
        pareto_front = []

        # Handle both 1D and 2D result arrays
        X = pymoo_result.X
        F = pymoo_result.F

        if X is None or F is None:
            raise ValueError("Optimization failed to produce any results")

        # Ensure 2D arrays
        if X.ndim == 1:
            X = X.reshape(1, -1)
        if F.ndim == 1:
            F = F.reshape(1, -1)

        for i, design in enumerate(X):
            # Create design dictionary
            design_dict = {
                "parameters": {},
                "objectives": {},
                "constraints": {},
            }

            # Decode parameters
            param_names = [p.name for p in self.param_space.parameters]
            for j, name in enumerate(param_names):
                design_dict["parameters"][name] = float(design[j])

            # Objectives
            for j, obj_name in enumerate(self.config.objectives):
                design_dict["objectives"][obj_name] = float(F[i, j])

            # Constraints (if available)
            if pymoo_result.G is not None:
                G = pymoo_result.G
                if G.ndim == 1:
                    G = G.reshape(1, -1)
                for j, (constr_name, _) in enumerate(self._build_constraint_functions()):
                    design_dict["constraints"][constr_name] = float(G[i, j])

            pareto_front.append(design_dict)

        # Rank designs (simple approach: sort by first objective)
        ranked_designs = sorted(
            pareto_front,
            key=lambda d: list(d["objectives"].values())[0]
        )

        # Create metadata
        metadata = {
            "algorithm": self.config.algorithm.type,
            "pop_size": self.config.algorithm.pop_size,
            "n_generations": self.config.algorithm.n_generations,
            "driver": self.config.driver_name,
            "enclosure_type": self.config.enclosure_type,
            "objectives": self.config.objectives,
            "timestamp": datetime.now().isoformat(),
        }

        return OptimizationResult(
            success=True,
            pareto_front=pareto_front,
            n_designs_found=len(pareto_front),
            best_designs=ranked_designs[:10],  # Top 10 designs
            parameter_names=param_names,
            objective_names=self.config.objectives,
            optimization_metadata=metadata,
            warnings=[]
        )

    def _save_results(self, result: OptimizationResult):
        """
        Save results to file.

        Args:
            result: Optimization result to save
        """
        # Create output directory if needed
        os.makedirs(self.config.output_dir, exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{self.config.driver_name}_{self.config.enclosure_type}_{timestamp}"

        # Save JSON
        json_path = os.path.join(self.config.output_dir, f"{base_name}.json")

        # Convert to serializable format
        result_dict = {
            "success": result.success,
            "n_designs_found": result.n_designs_found,
            "pareto_front": result.pareto_front,
            "best_designs": result.best_designs,
            "parameter_names": result.parameter_names,
            "objective_names": result.objective_names,
            "optimization_metadata": result.optimization_metadata,
            "convergence_info": result.convergence_info,
            "warnings": result.warnings,
        }

        with open(json_path, 'w') as f:
            json.dump(result_dict, f, indent=2)

        if self.config.verbose:
            print(f"\nResults saved to: {json_path}")
