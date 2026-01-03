"""
Configuration dataclasses for optimization factory.

This module provides structured configuration classes for the OptimizationScriptFactory,
making it easy to specify optimization parameters without writing code.

Classes:
    OptimizationConfig: Main configuration for optimization runs
    AlgorithmConfig: Algorithm-specific configuration
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional, Union


@dataclass
class AlgorithmConfig:
    """
    Configuration for optimization algorithm parameters.

    Attributes:
        type: Algorithm type ("nsga2", "nsga3", "moead")
        pop_size: Population size for genetic algorithm
        n_generations: Number of generations to run
        sampling: Sampling method ("lhs", "random")
        crossover_prob: Crossover probability (0-1)
        crossover_eta: Crossover distribution index (higher = more near-parent)
        mutation_eta: Mutation distribution index (higher = more small mutations)
        eliminate_duplicates: Whether to eliminate duplicate solutions

    Examples:
        >>> config = AlgorithmConfig(type="nsga2", pop_size=100, n_generations=100)
        >>> config.type
        'nsga2'
    """
    type: str = "nsga2"
    pop_size: int = 100
    n_generations: int = 100
    sampling: str = "lhs"
    crossover_prob: float = 0.9
    crossover_eta: float = 15.0
    mutation_eta: float = 20.0
    eliminate_duplicates: bool = True

    def __post_init__(self):
        """Validate configuration parameters."""
        valid_algorithms = ["nsga2", "nsga3", "moead"]
        if self.type not in valid_algorithms:
            raise ValueError(
                f"Invalid algorithm '{self.type}'. Must be one of {valid_algorithms}"
            )

        valid_sampling = ["lhs", "random"]
        if self.sampling not in valid_sampling:
            raise ValueError(
                f"Invalid sampling '{self.sampling}'. Must be one of {valid_sampling}"
            )

        if not 0 <= self.crossover_prob <= 1:
            raise ValueError(f"crossover_prob must be between 0 and 1, got {self.crossover_prob}")

        if self.pop_size < 10:
            raise ValueError(f"pop_size must be at least 10, got {self.pop_size}")

        if self.n_generations < 1:
            raise ValueError(f"n_generations must be at least 1, got {self.n_generations}")


@dataclass
class OptimizationConfig:
    """
    Configuration for optimization runs.

    This class encapsulates all parameters needed to run an optimization,
    including driver selection, enclosure type, objectives, constraints,
    and algorithm settings.

    Attributes:
        driver_name: Name of driver (e.g., "BC_21DS115", "BC_15DS115")
        enclosure_type: Type of enclosure ("exponential_horn", "multisegment_horn",
                       "mixed_profile_horn", "sealed", "ported")
        objectives: List of objectives to optimize (e.g., ["f3", "volume", "flatness"])
        constraints: Dict of constraint parameters (e.g., {"f3_target": 34.0})
        parameter_space_preset: Preset parameter space ("bass_horn", "midrange_horn",
                               "fullrange_horn", "compact")
        parameter_overrides: Dict of parameter bounds to override
                             (e.g., {"mouth_area": (0.4, 1.5)})
        algorithm: Algorithm configuration
        output_dir: Directory to save results
        save_results: Whether to save results to file
        verbose: Whether to print progress during optimization

    Valid objectives:
        - "f3": Minimize -3dB cutoff frequency
        - "f3_deviation": Minimize deviation from target F3
        - "volume": Minimize enclosure volume
        - "flatness": Minimize passband ripple
        - "efficiency": Maximize efficiency (note: minimization framework, so -efficiency)

    Valid constraints:
        - "f3_target": Target cutoff frequency (Hz)
        - "f3_tolerance": Acceptable deviation from target (Hz)
        - "f3_max": Maximum acceptable F3 (Hz)
        - "max_volume": Maximum enclosure volume (liters)
        - "min_efficiency": Minimum efficiency (0-1)
        - "throat_area_min/max": Throat area bounds (m²)
        - "mouth_area_min/max": Mouth area bounds (m²)

    Examples:
        >>> config = OptimizationConfig(
        ...     driver_name="BC_21DS115",
        ...     enclosure_type="multisegment_horn",
        ...     objectives=["f3_deviation", "flatness"],
        ...     constraints={"f3_target": 34.0, "f3_tolerance": 2.0},
        ...     parameter_space_preset="bass_horn"
        ... )
        >>> result = factory.run()

        Using preset:
        >>> config = OptimizationConfig.from_preset(
        ...     "f3_target",
        ...     driver_name="BC_21DS115",
        ...     constraints={"f3_target": 34.0}
        ... )
    """

    driver_name: str
    enclosure_type: str
    objectives: List[str]
    constraints: Dict[str, Any] = field(default_factory=dict)
    parameter_space_preset: str = "bass_horn"
    parameter_overrides: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    algorithm: AlgorithmConfig = field(default_factory=AlgorithmConfig)
    output_dir: str = "tasks"
    save_results: bool = True
    verbose: bool = True

    def __post_init__(self):
        """Validate configuration parameters."""
        # Validate objectives
        valid_objectives = [
            "f3",
            "f3_deviation",
            "volume",
            "flatness",
            "efficiency",
        ]
        for obj in self.objectives:
            if obj not in valid_objectives:
                raise ValueError(
                    f"Invalid objective '{obj}'. Must be one of {valid_objectives}"
                )

        # Validate enclosure type
        valid_enclosures = [
            "exponential_horn",
            "multisegment_horn",
            "mixed_profile_horn",
            "conical_horn",
            "sealed",
            "ported",
        ]
        if self.enclosure_type not in valid_enclosures:
            raise ValueError(
                f"Invalid enclosure_type '{self.enclosure_type}'. "
                f"Must be one of {valid_enclosures}"
            )

        # Validate parameter space preset
        valid_presets = [
            "bass_horn",
            "midrange_horn",
            "fullrange_horn",
            # Sealed/ported box presets (generic, box params are driver-specific)
            "sealed",
            "ported",
        ]
        if self.parameter_space_preset not in valid_presets:
            raise ValueError(
                f"Invalid parameter_space_preset '{self.parameter_space_preset}'. "
                f"Must be one of {valid_presets}"
            )

        # Validate objectives match constraints
        if "f3_deviation" in self.objectives and "f3_target" not in self.constraints:
            raise ValueError(
                "When using 'f3_deviation' objective, must specify 'f3_target' constraint"
            )

    @classmethod
    def from_preset(
        cls,
        preset: str,
        driver_name: str,
        enclosure_type: str = "multisegment_horn",
        **kwargs
    ) -> "OptimizationConfig":
        """
        Create configuration from predefined preset.

        Presets provide pre-configured objective/constraint combinations
        for common optimization scenarios.

        Args:
            preset: Preset name ("f3_target", "size_vs_f3", "compact_bass")
            driver_name: Name of driver
            enclosure_type: Type of enclosure (default: "multisegment_horn")
            **kwargs: Additional parameters to override

        Returns:
            OptimizationConfig configured from preset

        Examples:
            >>> config = OptimizationConfig.from_preset(
            ...     "f3_target",
            ...     driver_name="BC_21DS115",
            ...     constraints={"f3_target": 34.0}
            ... )
        """
        from gsd.optimization.presets import OPTIMIZATION_PRESETS

        if preset not in OPTIMIZATION_PRESETS:
            raise ValueError(
                f"Unknown preset '{preset}'. "
                f"Available: {list(OPTIMIZATION_PRESETS.keys())}"
            )

        preset_config = OPTIMIZATION_PRESETS[preset]

        # Merge preset constraints with user-provided constraints
        constraints = preset_config.get("constraints", {}).copy()
        constraints.update(kwargs.get("constraints", {}))

        # Create configuration
        return cls(
            driver_name=driver_name,
            enclosure_type=enclosure_type,
            objectives=preset_config.get("objectives", ["f3", "volume"]),
            constraints=constraints,
            parameter_space_preset=kwargs.get(
                "parameter_space_preset", preset_config.get("parameter_space_preset", "bass_horn")
            ),
            parameter_overrides=kwargs.get("parameter_overrides", {}),
            algorithm=AlgorithmConfig(**kwargs.get("algorithm", {})),
            output_dir=kwargs.get("output_dir", "tasks"),
            save_results=kwargs.get("save_results", True),
            verbose=kwargs.get("verbose", True),
        )

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "OptimizationConfig":
        """
        Load configuration from YAML file.

        YAML file format:
            driver: BC_21DS115
            enclosure_type: multisegment_horn
            objectives:
              - f3_deviation
              - flatness
            constraints:
              f3_target: 34.0
              f3_tolerance: 2.0
            parameter_space_preset: bass_horn
            parameter_overrides:
              mouth_area: [0.4, 1.5]
            algorithm:
              type: nsga2
              pop_size: 100
              n_generations: 100

        Args:
            yaml_path: Path to YAML configuration file

        Returns:
            OptimizationConfig loaded from file

        Examples:
            >>> config = OptimizationConfig.from_yaml("config.yaml")
        """
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "PyYAML is required to load YAML configs. "
                "Install with: pip install pyyaml"
            )

        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)

        # Parse algorithm config if present
        algorithm_data = data.pop("algorithm", {})
        algorithm = AlgorithmConfig(**algorithm_data)

        # Parse parameter overrides
        param_overrides = {}
        if "parameter_overrides" in data:
            for param, bounds in data["parameter_overrides"].items():
                if isinstance(bounds, list) and len(bounds) == 2:
                    param_overrides[param] = tuple(bounds)
                else:
                    raise ValueError(
                        f"Parameter override for '{param}' must be [min, max], got {bounds}"
                    )

        return cls(
            algorithm=algorithm,
            parameter_overrides=param_overrides,
            **data
        )

    def to_yaml(self, yaml_path: str):
        """
        Save configuration to YAML file.

        Args:
            yaml_path: Path to save YAML file

        Examples:
            >>> config = OptimizationConfig(...)
            >>> config.to_yaml("my_config.yaml")
        """
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "PyYAML is required to save YAML configs. "
                "Install with: pip install pyyaml"
            )

        # Convert to dict
        data = {
            "driver": self.driver_name,
            "enclosure_type": self.enclosure_type,
            "objectives": self.objectives,
            "constraints": self.constraints,
            "parameter_space_preset": self.parameter_space_preset,
            "parameter_overrides": {
                k: list(v) for k, v in self.parameter_overrides.items()
            },
            "algorithm": {
                "type": self.algorithm.type,
                "pop_size": self.algorithm.pop_size,
                "n_generations": self.algorithm.n_generations,
                "sampling": self.algorithm.sampling,
                "crossover_prob": self.algorithm.crossover_prob,
                "crossover_eta": self.algorithm.crossover_eta,
                "mutation_eta": self.algorithm.mutation_eta,
                "eliminate_duplicates": self.algorithm.eliminate_duplicates,
            },
            "output_dir": self.output_dir,
            "save_results": self.save_results,
            "verbose": self.verbose,
        }

        with open(yaml_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
