"""
Multi-objective optimization problem for enclosure design.

This module implements the EnclosureOptimizationProblem class that
integrates gsd's objective functions with pymoo's optimization
framework.

Literature:
    - Deb (2001) - Multi-Objective Optimization using Evolutionary Algorithms
    - pymoo documentation - NSGA-II implementation
    - Small (1972) - Enclosure design objectives

The problem class supports:
- Multiple objectives (F3, flatness, efficiency, size)
- Mixed constraints (physical and performance)
- Different enclosure types (sealed, ported)
"""

import numpy as np
from typing import List, Dict, Callable, Optional, Tuple
from dataclasses import dataclass

from pymoo.core.problem import Problem

from gsd.driver.parameters import ThieleSmallParameters


@dataclass
class ObjectiveConfig:
    """
    Configuration for a single objective.

    Attributes:
        name: Objective name (e.g., "f3", "size")
        function: Objective function that takes (design_vector, driver, enclosure_type)
        minimize: True if objective should be minimized, False if maximized
        weight: Weight for weighted sum calculations (optional)
    """
    name: str
    function: Callable
    minimize: bool = True
    weight: float = 1.0


class EnclosureOptimizationProblem(Problem):
    """
    Multi-objective enclosure optimization problem for pymoo.

    This class wraps gsd's objective functions into a format that
    pymoo's optimization algorithms can work with.

    Literature:
        - Deb (2001) - Multi-Objective Optimization using Evolutionary Algorithms
        - pymoo documentation - NSGA-II implementation
        - Small (1972) - Enclosure design objectives

    Attributes:
        driver: ThieleSmallParameters instance
        enclosure_type: Type of enclosure to optimize
        objective_configs: List of ObjectiveConfig objects
        constraint_funcs: List of constraint functions
        parameter_bounds: Dict mapping parameter names to (min, max) tuples
        param_names: List of parameter names in order
        n_obj: Number of objectives
        n_constr: Number of constraints
        num_segments: Number of segments for multisegment_horn (2 or 3)

    Examples:
        >>> driver = load_driver("BC_8NDL51")
        >>> problem = EnclosureOptimizationProblem(
        ...     driver=driver,
        ...     enclosure_type="sealed",
        ...     objectives=["f3", "size"],
        ...     parameter_bounds={"Vb": (0.005, 0.030)}
        ... )
        >>> from pymoo.optimize import minimize
        >>> from pymoo.algorithms.moo.nsga2 import NSGA2
        >>> algorithm = NSGA2(pop_size=100)
        >>> result = minimize(problem, algorithm, termination=('n_gen', 100))
    """

    def __init__(
        self,
        driver: ThieleSmallParameters,
        enclosure_type: str,
        objectives: List[str],
        parameter_bounds: Dict[str, tuple],
        constraints: List[str] = None,
        param_space = None,
        num_segments: int = 2,
        target_band: Tuple[float, float] = None,
        hf_cutoff: float = None
    ):
        """
        Initialize optimization problem.

        Args:
            driver: ThieleSmallParameters instance
            enclosure_type: "sealed", "ported", "exponential_horn", "multisegment_horn", etc.
            objectives: List of objective names ["f3", "flatness", "passband_flatness",
                       "efficiency", "size", "wavefront_sphericity", "impedance_smoothness"]
            parameter_bounds: Dict of parameter ranges
            constraints: Optional list of constraint function names
            param_space: Optional EnclosureParameterSpace with metadata for constraint parameters
            num_segments: Number of segments for multisegment_horn (2 or 3)
            target_band: Optional (f_min, f_max) tuple for constraining flatness optimization
                        to a specific frequency band (e.g., (500, 5000) for midrange)
            hf_cutoff: Optional HF cutoff frequency for passband_flatness objective (Hz).
                       If using passband_flatness, this defines the upper frequency bound
                       (e.g., 200 Hz for subwoofers, 500 Hz for bass horns).
        """
        # Import objective functions
        from gsd.optimization.objectives.response_metrics import (
            objective_f3,
            objective_response_flatness,
            objective_passband_flatness,
            objective_wavefront_sphericity,
            objective_impedance_smoothness,
        )
        from gsd.optimization.objectives.efficiency import (
            objective_efficiency,
        )
        from gsd.optimization.objectives.size_metrics import (
            objective_enclosure_volume,
        )

        # Map objective names to functions
        objective_map = {
            "f3": objective_f3,
            "flatness": objective_response_flatness,
            "passband_flatness": objective_passband_flatness,
            "composite_flatness": objective_response_flatness,  # Alias for now
            "efficiency": objective_efficiency,
            "size": objective_enclosure_volume,
            "wavefront_sphericity": objective_wavefront_sphericity,
            "impedance_smoothness": objective_impedance_smoothness,
        }

        # Create objective configurations
        self.objective_configs = []
        for obj_name in objectives:
            if obj_name not in objective_map:
                raise ValueError(f"Unknown objective: {obj_name}")

            self.objective_configs.append(ObjectiveConfig(
                name=obj_name,
                function=objective_map[obj_name],
                minimize=True  # All objectives are minimization
            ))

        # Import constraint functions
        self.constraint_funcs = []
        if constraints:
            from gsd.optimization.constraints.physical import (
                constraint_max_displacement,
                constraint_port_velocity,
                constraint_multisegment_continuity,
                constraint_multisegment_flare_limits,
                constraint_multisegment_flare_curvature,
                constraint_conical_expansion_ratio,
                constraint_exponential_monotonic_expansion,
                constraint_total_length,
            )
            from gsd.optimization.constraints.performance import (
                constraint_f3_limit,
                constraint_qtc_range,
                constraint_volume_limit,
                constraint_mouth_size,
            )

            constraint_map = {
                "max_displacement": constraint_max_displacement,
                "port_velocity": constraint_port_velocity,
                "f3_limit": constraint_f3_limit,
                "qtc_range": constraint_qtc_range,
                "volume_limit": constraint_volume_limit,
                "segment_continuity": constraint_multisegment_continuity,
                "flare_constant_limits": constraint_multisegment_flare_limits,
                "flare_curvature": constraint_multisegment_flare_curvature,
                "mouth_size": constraint_mouth_size,
                "expansion_ratio": constraint_conical_expansion_ratio,
                "monotonic_expansion": constraint_exponential_monotonic_expansion,
                "total_length": constraint_total_length,
            }

            for constr_name in constraints:
                if constr_name in constraint_map:
                    self.constraint_funcs.append(constraint_map[constr_name])

        # Store problem parameters
        self.driver = driver
        self.enclosure_type = enclosure_type
        self.param_names = list(parameter_bounds.keys())
        self.num_segments = num_segments
        self.target_band = target_band
        self.hf_cutoff = hf_cutoff
        # Store metadata for constraint functions (e.g., max_length, max_mouth_area)
        self.metadata = param_space.metadata if param_space and hasattr(param_space, 'metadata') else {}

        # Extract parameter bounds in order
        xl = np.array([parameter_bounds[p][0] for p in self.param_names])
        xu = np.array([parameter_bounds[p][1] for p in self.param_names])

        # Determine problem dimensions
        n_var = len(self.param_names)
        n_obj = len(self.objective_configs)
        n_constr = len(self.constraint_funcs)

        # Determine variable types (continuous vs integer)
        # For mixed_profile_horn, profile_type parameters are integers
        if enclosure_type == "mixed_profile_horn":
            # Find profile_type parameter indices
            vtype = np.ones(n_var, dtype=bool)  # Start with all continuous (True)
            for i, param_name in enumerate(self.param_names):
                if param_name.startswith("profile_type"):
                    vtype[i] = False  # Mark as integer
        else:
            vtype = np.ones(n_var, dtype=bool)  # All continuous

        # Initialize parent Problem class
        super().__init__(
            n_var=n_var,
            n_obj=n_obj,
            n_constr=n_constr,
            xl=xl,
            xu=xu,
            vtype=vtype  # Mix of continuous (True) and integer (False)
        )

    def _evaluate(self, X, out, *args, **kwargs):
        """
        Evaluate objective functions for population X.

        pymoo calls this method with design matrix X (n_individuals × n_variables)

        Args:
            X: Design matrix where each row is a design vector
            out: Output dictionary to store results

        Note:
            Invalid designs (e.g., calculation failures) are heavily penalized
            by assigning large objective values.
        """
        n_individuals = X.shape[0]

        # Initialize objective matrix
        F = np.zeros((n_individuals, self.n_obj))

        # Determine if we need to pass num_segments parameter
        # (for multisegment_horn and mixed_profile_horn objectives)
        needs_num_segments = self.enclosure_type in ["multisegment_horn", "mixed_profile_horn"]

        # Evaluate each individual
        for i in range(n_individuals):
            design_vector = X[i].copy()

            # For mixed_profile_horn, ensure profile_type parameters are integers
            if self.enclosure_type == "mixed_profile_horn":
                for param_idx, param_name in enumerate(self.param_names):
                    if param_name.startswith("profile_type"):
                        design_vector[param_idx] = int(np.round(design_vector[param_idx]))

            # Evaluate each objective
            for j, obj_config in enumerate(self.objective_configs):
                try:
                    # Check if this objective needs target_band parameter
                    needs_target_band = (
                        self.target_band is not None and
                        obj_config.name in ["flatness", "response_flatness"]
                    )

                    # Check if this objective needs hf_cutoff parameter
                    needs_hf_cutoff = (
                        self.hf_cutoff is not None and
                        obj_config.name == "passband_flatness"
                    )

                    # For passband_flatness, pass hf_cutoff and num_segments
                    if needs_hf_cutoff:
                        obj_value = obj_config.function(
                            design_vector,
                            self.driver,
                            self.enclosure_type,
                            hf_cutoff=self.hf_cutoff,
                            n_points=100,
                            voltage=2.83,
                            num_segments=self.num_segments
                        )
                    # For multisegment_horn objectives, pass num_segments
                    elif needs_num_segments and obj_config.name in [
                        "wavefront_sphericity", "impedance_smoothness",
                        "response_flatness", "response_slope", "flatness", "slope"
                    ]:
                        # Pass both num_segments and target_band (if needed)
                        if needs_target_band:
                            obj_value = obj_config.function(
                                design_vector,
                                self.driver,
                                self.enclosure_type,
                                frequency_range=self.target_band,
                                n_points=100,
                                voltage=2.83,
                                num_segments=self.num_segments,
                                target_band=self.target_band
                            )
                        else:
                            obj_value = obj_config.function(
                                design_vector,
                                self.driver,
                                self.enclosure_type,
                                num_segments=self.num_segments
                            )
                    elif needs_target_band:
                        # Not multisegment, but needs target_band
                        obj_value = obj_config.function(
                            design_vector,
                            self.driver,
                            self.enclosure_type,
                            frequency_range=self.target_band,
                            n_points=100,
                            voltage=2.83,
                            target_band=self.target_band
                        )
                    else:
                        # Standard evaluation
                        obj_value = obj_config.function(
                            design_vector,
                            self.driver,
                            self.enclosure_type
                        )
                    F[i, j] = obj_value
                except Exception as e:
                    # Penalize invalid designs heavily
                    F[i, j] = 1e10
                    # Log warning for debugging (in development)
                    import warnings
                    warnings.warn(
                        f"Objective evaluation failed for design {i}, "
                        f"objective {j} ({obj_config.name}): {e}"
                    )

        # Evaluate constraints if any
        if self.n_constr > 0:
            G = np.zeros((n_individuals, self.n_constr))
            for i in range(n_individuals):
                design_vector = X[i]
                for j, constraint_func in enumerate(self.constraint_funcs):
                    try:
                        # For multisegment_horn constraints, pass num_segments
                        # Check if this is a multisegment constraint by name
                        func_name = constraint_func.__name__ if hasattr(constraint_func, '__name__') else ''

                        # Map constraint function names to their metadata parameters
                        # These parameters are stored in param_space.metadata and need
                        # to be passed to constraint functions that require them
                        constraint_param_map = {
                            'constraint_total_length': ['max_length'],
                            'constraint_mouth_loading': ['min_circumference_ratio'],
                            'constraint_multisegment_flare_limits': ['min_mL', 'max_mL'],
                            'constraint_minimum_expansion': ['min_expansion_ratio'],
                        }

                        # Extract constraint-specific parameters from metadata
                        constraint_params = {}
                        if func_name in constraint_param_map:
                            for param_name in constraint_param_map[func_name]:
                                if param_name in self.metadata:
                                    constraint_params[param_name] = self.metadata[param_name]

                        # Call constraint function with appropriate parameters
                        if needs_num_segments and 'multisegment' in func_name:
                            # Multisegment constraints need num_segments
                            G[i, j] = constraint_func(
                                design_vector,
                                self.driver,
                                self.enclosure_type,
                                num_segments=self.num_segments,
                                **constraint_params  # PASS CONSTRAINT PARAMETERS!
                            )
                        elif func_name == 'constraint_total_length':
                            # Total length constraint needs num_segments + max_length
                            G[i, j] = constraint_func(
                                design_vector,
                                self.driver,
                                self.enclosure_type,
                                num_segments=self.num_segments,
                                **constraint_params  # Includes max_length from metadata
                            )
                        else:
                            # Other constraints may or may not need extra params
                            G[i, j] = constraint_func(
                                design_vector,
                                self.driver,
                                self.enclosure_type,
                                **constraint_params  # PASS CONSTRAINT PARAMETERS!
                            )
                    except Exception:
                        # If constraint fails, treat as violation
                        G[i, j] = 1000.0
            out["G"] = G

        out["F"] = F

    def decode_design_vector(self, x: np.ndarray) -> Dict[str, float]:
        """
        Decode design vector into parameter dictionary.

        Args:
            x: Design vector (1D array)

        Returns:
            Dict mapping parameter names to values
        """
        return dict(zip(self.param_names, x))

    def encode_design_vector(self, params: Dict[str, float]) -> np.ndarray:
        """
        Encode parameter dictionary into design vector.

        Args:
            params: Dict mapping parameter names to values

        Returns:
            Design vector (1D array)
        """
        return np.array([params[p] for p in self.param_names])
