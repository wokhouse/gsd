"""
High-level API for AI-assisted enclosure design.

This module provides the DesignAssistant class, which offers a clean,
agent-friendly interface for exploring enclosure design space. All methods
return structured data (dataclasses) rather than printing to stdout.

Example usage:
    >>> assistant = DesignAssistant()
    >>>
    >>> # Get recommendation
    >>> rec = assistant.recommend_design(
    ...     driver_name="BC_12NDL76",
    ...     max_volume_liters=50,
    ...     target_f3=60
    ... )
    >>> print(rec.enclosure_type)  # "sealed"
    >>> print(rec.reasoning)  # Explanation with citations
    >>>
    >>> # Explore parameter space
    >>> result = assistant.optimize_design(
    ...     driver_name="BC_12NDL76",
    ...     enclosure_type="sealed",
    ...     objectives=["f3", "size"]
    ... )
    >>> for design in result.best_designs[:3]:
    ...     print(design['parameters'], design['objectives'])
"""

import numpy as np
from typing import List, Dict, Optional

from gsd.optimization.api.result_structures import (
    DesignRecommendation,
    OptimizationResult,
    ParameterSweepResult,
)
from gsd.driver.parameters import ThieleSmallParameters


class DesignAssistant:
    """
    High-level API for AI-assisted enclosure design.

    This class provides a clean, agent-friendly interface for exploring
    enclosure design space. All methods return structured data (dataclasses)
    rather than printing to stdout.

    Attributes:
        validation_mode: If True, validate designs against Hornresp (when implemented)

    Example:
        >>> assistant = DesignAssistant()
        >>> rec = assistant.recommend_design(driver_name="BC_12NDL76")
        >>> print(rec.enclosure_type, rec.confidence)
    """

    def __init__(self, validation_mode: bool = True):
        """
        Initialize design assistant.

        Args:
            validation_mode: If True, validate designs against Hornresp
        """
        self.validation_mode = validation_mode

    def recommend_design(
        self,
        driver_name: str,
        objectives: List[str] = None,
        max_volume_liters: float = None,
        target_f3: float = None,
        enclosure_preference: str = "auto",
        efficiency_priority: bool = False
    ) -> DesignRecommendation:
        """
        Recommend enclosure type and initial design based on driver parameters.

        Literature:
            - Small (1972), Table 2 - Qts-based enclosure selection
            - Thiele (1971) - Alignment selection
            - Olson (1947) - Horn loading requirements

        Args:
            driver_name: Name of driver (must be in DRIVER_FACTORY)
            objectives: List of objectives (default: ["f3", "size"])
            max_volume_liters: Maximum enclosure volume in liters
            target_f3: Target cutoff frequency in Hz
            enclosure_preference: Preferred type ("sealed", "ported", "horn", "auto")
            efficiency_priority: Whether efficiency is critical

        Returns:
            DesignRecommendation with enclosure type, parameters, and reasoning

        Examples:
            >>> assistant = DesignAssistant()
            >>> rec = assistant.recommend_design(
            ...     driver_name="BC_12NDL76",
            ...     max_volume_liters=50,
            ...     target_f3=60
            ... )
            >>> rec.enclosure_type
            'sealed'
            >>> rec.confidence > 0.7
            True
        """
        from gsd.driver import load_driver

        # Load driver
        try:
            driver = load_driver(driver_name)
        except FileNotFoundError:
            return DesignRecommendation(
                enclosure_type="unknown",
                confidence=0.0,
                reasoning=f"Unknown driver: {driver_name}",
                suggested_parameters={},
                expected_performance={},
                validation_notes=[f"Driver '{driver_name}' not found"]
            )

        # Build user constraints dict
        user_constraints = {}
        if max_volume_liters:
            user_constraints["max_volume"] = max_volume_liters / 1000.0  # L to m³
        if target_f3:
            user_constraints["target_f3"] = target_f3
        if efficiency_priority:
            user_constraints["efficiency_priority"] = True

        # Get recommendation based on Qts
        qts = driver.Q_ts

        if enclosure_preference == "auto":
            # Qts-based recommendation (Small 1972, Table 2)
            if qts < 0.35:
                enc_type = "exponential_horn"
                confidence = 0.8
                reasoning = (
                    f"Qts={qts:.3f} is very low - excellent for horn loading.\n"
                    f"  • Small (1972): Qts < 0.40 suitable for horns\n"
                    f"  • High efficiency possible with proper horn design\n"
                    f"  • Note: Horn optimization requires horn simulation (Phase 3)"
                )
                alternatives = [
                    {"type": "sealed", "reason": "Possible but requires very small box (Qtc > 1.0)"}
                ]
            elif 0.35 <= qts < 0.45:
                enc_type = "sealed"
                confidence = 0.85
                reasoning = (
                    f"Qts={qts:.3f} is ideal for sealed box.\n"
                    f"  • Small (1972): Qts 0.35-0.45 optimal for sealed\n"
                    f"  • Butterworth alignment (Qtc=0.707) achievable\n"
                    f"  • Excellent transient response"
                )
                alternatives = [
                    {"type": "ported", "reason": "Possible but may require tuning below Fs"}
                ]
            elif 0.45 <= qts < 0.55:
                enc_type = "ported"
                confidence = 0.85
                reasoning = (
                    f"Qts={qts:.3f} is ideal for ported box.\n"
                    f"  • Thiele (1971): Qts ~0.38-0.45 for B4 alignment\n"
                    f"  • Lower F3 than sealed for same size\n"
                    f"  • Good efficiency"
                )
                alternatives = [
                    {"type": "sealed", "reason": "Good alternative with slightly larger box"}
                ]
            else:  # qts >= 0.55
                enc_type = "sealed"
                confidence = 0.75
                reasoning = (
                    f"Qts={qts:.3f} is high - best for sealed box or infinite baffle.\n"
                    f"  • Small (1972): Qts > 0.55 for large sealed boxes\n"
                    f"  • Ported box would be very large\n"
                    f"  • Good bass extension with large box"
                )
                alternatives = [
                    {"type": "infinite_baffle", "reason": "Also suitable for high Qts drivers"}
                ]
        else:
            enc_type = enclosure_preference
            confidence = 1.0  # User override
            reasoning = f"User-selected enclosure type: {enclosure_preference}"
            alternatives = []

        # Get alignment suggestions (simplified version)
        if enc_type == "sealed":
            # Target Qtc = 0.707 for Butterworth
            qtc_target = 0.707
            # Small (1972): Qtc = Qts × √(1 + Vas/Vb)
            # Solve for Vb: Vb = Vas / ((Qtc/Qts)² - 1)
            alpha = (qtc_target / qts) ** 2 - 1
            Vb = driver.V_as / alpha

            from gsd.enclosure.sealed_box import calculate_sealed_box_system_parameters
            params = calculate_sealed_box_system_parameters(driver, Vb)

            expected_perf = {
                "F3": params.F3,
                "Qtc": params.Qtc,
                "Fc": params.Fc,
                "volume_liters": Vb * 1000
            }
            suggested_params = {"Vb": Vb}

        elif enc_type == "ported":
            # B4 alignment: Fb ≈ Fs, Vb ≈ Vas
            Vb = driver.V_as
            Fb = driver.F_s

            from gsd.enclosure.ported_box import calculate_ported_box_system_parameters
            params = calculate_ported_box_system_parameters(driver, Vb, Fb)

            expected_perf = {
                "F3": params.F3,
                "Fb": Fb,
                "volume_liters": Vb * 1000
            }
            suggested_params = {"Vb": Vb, "Fb": Fb}

        else:
            # Horn - simplified placeholder
            expected_perf = {
                "note": "Horn optimization requires horn simulation (Phase 3)"
            }
            suggested_params = {}

        return DesignRecommendation(
            enclosure_type=enc_type,
            confidence=confidence,
            reasoning=reasoning,
            suggested_parameters=suggested_params,
            expected_performance=expected_perf,
            alternatives=alternatives,
            trade_offs=self._explain_trade_offs(driver, enc_type, expected_perf),
            validation_notes=[]
        )

    def optimize_design(
        self,
        driver_name: str,
        enclosure_type: str,
        objectives: List[str],
        constraints: Dict[str, float] = None,
        population_size: int = 100,
        generations: int = 100,
        top_n: int = 10,
        num_segments: int = 2
    ) -> OptimizationResult:
        """
        Run multi-objective optimization for enclosure design.

        Uses NSGA-II algorithm to find Pareto-optimal designs trading off
        multiple objectives.

        Literature:
            - Deb et al. (2002) - NSGA-II algorithm
            - Small (1972) - Enclosure design objectives

        Args:
            driver_name: Name of driver
            enclosure_type: "sealed", "ported", "exponential_horn", "multisegment_horn"
            objectives: List of objectives ["f3", "flatness", "efficiency", "size",
                       "wavefront_sphericity", "impedance_smoothness"]
            constraints: Dict of constraint values (optional)
            population_size: Population size for NSGA-II (default 100)
            generations: Number of generations (default 100)
            top_n: Number of top designs to return (default 10)
            num_segments: Number of segments for multisegment_horn (2 or 3)

        Returns:
            OptimizationResult with Pareto front and best designs

        Examples:
            >>> assistant = DesignAssistant()
            >>> result = assistant.optimize_design(
            ...     driver_name="TC2",
            ...     enclosure_type="multisegment_horn",
            ...     objectives=["wavefront_sphericity", "impedance_smoothness"],
            ...     population_size=50,
            ...     generations=50
            ... )
            >>> result.success
            True
            >>> result.n_designs_found
            47
            >>> len(result.best_designs)
            10
        """
        from gsd.driver import load_driver
        from gsd.optimization.parameters import (
            get_sealed_box_parameter_space,
            get_ported_box_parameter_space
        )
        from gsd.optimization.parameters.exponential_horn_params import (
            get_exponential_horn_parameter_space
        )
        from gsd.optimization.parameters.multisegment_horn_params import (
            get_multisegment_horn_parameter_space
        )
        from gsd.optimization.parameters.conical_horn_params import (
            get_conical_horn_parameter_space
        )
        from gsd.optimization.parameters.multisegment_horn_params import (
            get_mixed_profile_parameter_space,
            build_mixed_profile_horn,
        )
        from gsd.optimization.objectives.composite import EnclosureOptimizationProblem
        from gsd.optimization.optimizers.pymoo_interface import run_nsga2
        from gsd.optimization.results.pareto_front import rank_designs

        # Load driver
        try:
            driver = load_driver(driver_name)
        except FileNotFoundError:
            return OptimizationResult(
                success=False,
                pareto_front=[],
                n_designs_found=0,
                best_designs=[],
                parameter_names=[],
                objective_names=objectives,
                optimization_metadata={},
                warnings=[f"Unknown driver: {driver_name}"]
            )

        # Validate enclosure type
        supported_types = ["sealed", "ported", "exponential_horn", "multisegment_horn", "conical_horn", "mixed_profile_horn"]
        if enclosure_type not in supported_types:
            return OptimizationResult(
                success=False,
                pareto_front=[],
                n_designs_found=0,
                best_designs=[],
                parameter_names=[],
                objective_names=objectives,
                optimization_metadata={},
                warnings=[
                    f"Unsupported enclosure type: {enclosure_type}",
                    f"Currently supported: {', '.join(supported_types)}"
                ]
            )

        # Get parameter space
        if enclosure_type == "sealed":
            param_space = get_sealed_box_parameter_space(driver)
        elif enclosure_type == "ported":
            param_space = get_ported_box_parameter_space(driver)
        elif enclosure_type == "exponential_horn":
            # Get preset from constraints, default to midrange_horn
            preset = constraints.get("preset", "midrange_horn") if constraints else "midrange_horn"
            param_space = get_exponential_horn_parameter_space(driver, preset=preset)
        elif enclosure_type == "multisegment_horn":
            # Get preset from constraints, default to midrange_horn
            preset = constraints.get("preset", "midrange_horn") if constraints else "midrange_horn"
            # Extract size constraints for 3D printing or other physical limitations
            max_length = constraints.get("max_length") if constraints else None
            max_mouth_area = constraints.get("max_mouth_area") if constraints else None
            max_volume = constraints.get("max_volume") if constraints else None
            param_space = get_multisegment_horn_parameter_space(
                driver, preset=preset, num_segments=num_segments,
                max_length=max_length, max_mouth_area=max_mouth_area,
                max_volume=max_volume
            )
        elif enclosure_type == "conical_horn":
            # Get preset from constraints, default to midrange_horn
            preset = constraints.get("preset", "midrange_horn") if constraints else "midrange_horn"
            param_space = get_conical_horn_parameter_space(driver, preset=preset)
        elif enclosure_type == "mixed_profile_horn":
            # Get preset from constraints, default to midrange_horn
            preset = constraints.get("preset", "midrange_horn") if constraints else "midrange_horn"
            # Extract size constraints for 3D printing or other physical limitations
            max_length = constraints.get("max_length") if constraints else None
            max_mouth_area = constraints.get("max_mouth_area") if constraints else None
            max_volume = constraints.get("max_volume") if constraints else None
            param_space = get_mixed_profile_parameter_space(
                driver, preset=preset, num_segments=num_segments,
                max_length=max_length, max_mouth_area=max_mouth_area,
                max_volume=max_volume
            )
        else:
            return OptimizationResult(
                success=False,
                pareto_front=[],
                n_designs_found=0,
                best_designs=[],
                parameter_names=[],
                objective_names=objectives,
                optimization_metadata={},
                warnings=[f"Enclosure type {enclosure_type} not yet implemented"]
            )

        bounds_dict = param_space.get_bounds_dict()

        # Build constraint list
        constraint_list = []
        if constraints:
            if enclosure_type == "sealed":
                if "max_qtc" in constraints or "min_qtc" in constraints:
                    constraint_list.append("qtc_range")
            if "max_f3" in constraints:
                constraint_list.append("f3_limit")
            if "max_volume_liters" in constraints:
                constraint_list.append("volume_limit")

            # Add physical constraints
            constraint_list.append("max_displacement")

            if enclosure_type == "ported":
                constraint_list.append("port_velocity")

            if enclosure_type == "exponential_horn":
                # Horn-specific constraints
                constraint_list.extend(constraints.get(
                    "constraint_list",
                    ["mouth_size", "flare_constant_limits", "monotonic_expansion"]
                ))

            if enclosure_type == "conical_horn":
                # Conical horn-specific constraints
                constraint_list.extend(constraints.get(
                    "constraint_list",
                    ["mouth_size", "expansion_ratio"]
                ))

            if enclosure_type == "multisegment_horn":
                # Multisegment horn constraints
                constraint_list.extend(constraints.get(
                    "constraint_list",
                    ["segment_continuity", "flare_constant_limits"]
                ))

            if enclosure_type == "mixed_profile_horn":
                # Mixed profile horn constraints (similar to multisegment)
                constraint_list.extend(constraints.get(
                    "constraint_list",
                    ["segment_continuity", "flare_constant_limits"]
                ))
        else:
            # Default constraints
            constraint_list = ["max_displacement"]
            if enclosure_type == "ported":
                constraint_list.append("port_velocity")
            if enclosure_type == "exponential_horn":
                # Default horn constraints
                constraint_list.extend(["mouth_size", "flare_constant_limits", "monotonic_expansion"])
            if enclosure_type == "conical_horn":
                # Default conical horn constraints
                constraint_list.extend(["mouth_size", "expansion_ratio"])
            if enclosure_type == "multisegment_horn":
                # Default multisegment horn constraints
                constraint_list.extend(["segment_continuity", "flare_constant_limits"])
            if enclosure_type == "mixed_profile_horn":
                # Default mixed profile horn constraints
                constraint_list.extend(["segment_continuity", "flare_constant_limits"])

        # Setup problem
        try:
            problem = EnclosureOptimizationProblem(
                driver=driver,
                enclosure_type=enclosure_type,
                objectives=objectives,
                parameter_bounds=bounds_dict,
                constraints=constraint_list,
                num_segments=num_segments
            )
        except Exception as e:
            return OptimizationResult(
                success=False,
                pareto_front=[],
                n_designs_found=0,
                best_designs=[],
                parameter_names=[],
                objective_names=objectives,
                optimization_metadata={},
                warnings=[f"Problem setup failed: {e}"]
            )

        # Run optimization
        try:
            result, metadata = run_nsga2(
                problem=problem,
                pop_size=population_size,
                n_generations=generations,
                verbose=False  # Don't print progress
            )
            # Check if optimization succeeded
            if result.F is None or len(result.F) == 0:
                return OptimizationResult(
                    success=False,
                    pareto_front=[],
                    n_designs_found=0,
                    best_designs=[],
                    parameter_names=param_space.get_parameter_names(),
                    objective_names=objectives,
                    optimization_metadata={},
                    warnings=["Optimization completed but found no valid designs. This may indicate all designs violated constraints."]
                )
        except Exception as e:
            return OptimizationResult(
                success=False,
                pareto_front=[],
                n_designs_found=0,
                best_designs=[],
                parameter_names=param_space.get_parameter_names(),
                objective_names=objectives,
                optimization_metadata={},
                warnings=[f"Optimization failed: {e}"]
            )

        # Rank designs
        ranked = rank_designs(
            result,
            objectives=objectives,
            parameter_names=param_space.get_parameter_names(),
            top_n=top_n
        )

        # Convert to structured format
        pareto_designs = []
        for i in range(len(result.F)):
            # Handle both 1D and 2D arrays
            if len(result.X.shape) == 1:
                x_row = result.X
            elif len(result.X.shape) == 2:
                x_row = result.X[i]
            else:
                x_row = result.X[i]

            if len(result.F.shape) == 1:
                f_row = [result.F[i]]  # Make it iterable
            elif len(result.F.shape) == 2:
                f_row = result.F[i]
            else:
                f_row = result.F[i]

            pareto_designs.append({
                "parameters": dict(zip(param_space.get_parameter_names(), x_row)),
                "objectives": dict(zip(objectives, f_row))
            })

        # Apply constraint-specific overrides if provided
        if constraints:
            for i, design in enumerate(pareto_designs):
                # Add constraint values to metadata
                design["constraint_values"] = constraints

        return OptimizationResult(
            success=True,
            pareto_front=pareto_designs,
            n_designs_found=len(result.F),
            best_designs=ranked,
            parameter_names=param_space.get_parameter_names(),
            objective_names=objectives,
            optimization_metadata=metadata,
            warnings=[]
        )

    def sweep_parameter(
        self,
        driver_name: str,
        enclosure_type: str,
        parameter: str,
        param_min: float,
        param_max: float,
        steps: int = 50,
        fixed_params: Dict[str, float] = None
    ) -> ParameterSweepResult:
        """
        Perform parameter sweep to explore design space.

        This method sweeps a single parameter across a range of values and
        evaluates all objectives at each point. This provides complete
        visibility into how the parameter affects performance, allowing
        you to identify optimal ranges and understand trade-offs.

        Literature:
            - Small (1972) - Enclosure parameter relationships
            - Thiele (1971) - Vented box alignments

        Args:
            driver_name: Name of driver
            enclosure_type: "sealed" or "ported"
            parameter: Parameter name to sweep (e.g., "Vb", "Fb")
            param_min: Minimum parameter value (in SI units: m³ for volume, Hz for frequency)
            param_max: Maximum parameter value
            steps: Number of steps to evaluate
            fixed_params: Dict of other fixed parameters (e.g., {"Fb": 45.0} for ported)

        Returns:
            ParameterSweepResult with sweep data and recommendations

        Examples:
            >>> assistant = DesignAssistant()
            >>> # Sweep box volume for sealed enclosure
            >>> sweep = assistant.sweep_parameter(
            ...     driver_name="BC_12NDL76",
            ...     enclosure_type="sealed",
            ...     parameter="Vb",
            ...     param_min=0.010,  # 10 liters
            ...     param_max=0.050,  # 50 liters
            ...     steps=50
            ... )
            >>> # Find best F3
            >>> best_idx = np.argmin(sweep.results["F3"])
            >>> print(f"Best F3: {sweep.results['F3'][best_idx]:.1f} Hz at Vb={sweep.parameter_values[best_idx]*1000:.1f} L")
            Best F3: 52.3 Hz at Vb=35.2 L
            >>>
            >>> # Check sensitivity
            >>> sweep.sensitivity_analysis["f3_sensitivity"]
            0.87  # Strong correlation between Vb and F3

        Note:
            - For sealed boxes, you can sweep "Vb" only
            - For ported boxes, you can sweep "Vb" or "Fb"
            - If sweeping "Vb" for ported, fix "Fb" in fixed_params (and vice versa)
            - All parameter values should be in SI units (m³ for volume, Hz for frequency)
        """
        from gsd.driver import load_driver
        from gsd.optimization.objectives.response_metrics import (
            objective_f3, objective_response_flatness
        )
        from gsd.optimization.objectives.efficiency import objective_efficiency
        from gsd.optimization.objectives.size_metrics import objective_enclosure_volume

        # Load driver
        try:
            driver = load_driver(driver_name)
        except FileNotFoundError:
            return ParameterSweepResult(
                parameter_swept=parameter,
                parameter_values=np.array([]),
                results={},
                sensitivity_analysis={},
                recommendations=[f"Unknown driver: {driver_name}"]
            )

        # Validate parameter
        if enclosure_type == "sealed" and parameter != "Vb":
            return ParameterSweepResult(
                parameter_swept=parameter,
                parameter_values=np.array([]),
                results={},
                sensitivity_analysis={},
                recommendations=[f"Sealed box only supports sweeping 'Vb', got '{parameter}'"]
            )

        if enclosure_type == "ported" and parameter not in ["Vb", "Fb"]:
            return ParameterSweepResult(
                parameter_swept=parameter,
                parameter_values=np.array([]),
                results={},
                sensitivity_analysis={},
                recommendations=[f"Ported box supports sweeping 'Vb' or 'Fb', got '{parameter}'"]
            )

        # Set up fixed parameters
        fixed_params = fixed_params or {}

        # For ported boxes, provide intelligent defaults if not specified
        if enclosure_type == "ported":
            if parameter == "Vb" and "Fb" not in fixed_params:
                fixed_params["Fb"] = driver.F_s * 0.7  # Default tuning
            elif parameter == "Fb" and "Vb" not in fixed_params:
                fixed_params["Vb"] = driver.V_as  # Default volume

        # Generate parameter values
        param_values = np.linspace(param_min, param_max, steps)

        # Storage arrays
        f3_values = []
        flatness_values = []
        efficiency_values = []
        size_values = []

        # Perform sweep
        for value in param_values:
            # Construct design vector
            if enclosure_type == "sealed":
                design_vector = np.array([value])
            elif enclosure_type == "ported":
                if parameter == "Vb":
                    fb = fixed_params.get("Fb", driver.F_s * 0.7)
                    design_vector = np.array([value, fb])
                elif parameter == "Fb":
                    vb = fixed_params.get("Vb", driver.V_as)
                    design_vector = np.array([vb, value])
                else:
                    return ParameterSweepResult(
                        parameter_swept=parameter,
                        parameter_values=np.array([]),
                        results={},
                        sensitivity_analysis={},
                        recommendations=[f"Unknown parameter for ported box: {parameter}"]
                    )
            else:
                return ParameterSweepResult(
                    parameter_swept=parameter,
                    parameter_values=np.array([]),
                    results={},
                    sensitivity_analysis={},
                    recommendations=[f"Unsupported enclosure type: {enclosure_type}"]
                )

            # Calculate objectives
            try:
                f3 = objective_f3(design_vector, driver, enclosure_type)
                flat = objective_response_flatness(design_vector, driver, enclosure_type)
                eff = objective_efficiency(design_vector, driver, enclosure_type)
                size = objective_enclosure_volume(design_vector, driver, enclosure_type)

                f3_values.append(f3)
                flatness_values.append(flat)
                efficiency_values.append(-eff)  # Convert back from negative
                size_values.append(size)
            except Exception as e:
                # Fill with NaN on failure
                f3_values.append(np.nan)
                flatness_values.append(np.nan)
                efficiency_values.append(np.nan)
                size_values.append(np.nan)

        # Convert to numpy arrays
        f3_values = np.array(f3_values)
        flatness_values = np.array(flatness_values)
        efficiency_values = np.array(efficiency_values)
        size_values = np.array(size_values)

        # Analyze sensitivity
        sensitivity = self._analyze_sensitivity(
            param_values,
            f3_values,
            size_values
        )

        # Generate recommendations
        recommendations = self._generate_sweep_recommendations(
            parameter,
            param_values,
            f3_values,
            size_values,
            enclosure_type
        )

        return ParameterSweepResult(
            parameter_swept=parameter,
            parameter_values=param_values,
            results={
                "F3": f3_values,
                "flatness": flatness_values,
                "efficiency": efficiency_values,
                "size": size_values
            },
            sensitivity_analysis=sensitivity,
            recommendations=recommendations
        )

    def _explain_trade_offs(
        self,
        driver: ThieleSmallParameters,
        enclosure_type: str,
        performance: Dict
    ) -> str:
        """Generate explanation of design trade-offs."""
        if enclosure_type == "sealed":
            qtc = performance.get('Qtc', 'N/A')
            f3 = performance.get('F3', 'N/A')

            return (
                f"Sealed box trade-offs:\n"
                f"  • Larger box → lower F3 (better bass extension) but bigger size\n"
                f"  • Qtc = {qtc}: "
                f"{'Butterworth (flat)' if isinstance(qtc, float) and abs(qtc - 0.707) < 0.05 else 'Custom alignment'}\n"
                f"  • F3 = {f3 if isinstance(f3, float) else 'N/A'} Hz: "
                f"{'Good bass' if isinstance(f3, float) and f3 < 60 else 'Limited bass'}\n"
                f"  • Transient response: Excellent (sealed box has best damping)\n"
                f"  • Power handling: Good (acoustic suspension)"
            )
        elif enclosure_type == "ported":
            fb = performance.get('Fb', 'N/A')

            return (
                f"Ported box trade-offs:\n"
                f"  • Lower F3 than sealed for same size (~3-5 Hz improvement)\n"
                f"  • Fb = {fb if isinstance(fb, float) else 'N/A'} Hz: tuning frequency\n"
                f"  • Trade-off: Steep rolloff below Fb (driver unloading risk)\n"
                f"  • Size vs bass: Larger box + lower tuning = deeper bass\n"
                f"  • Efficiency: Better than sealed (typically +3dB)\n"
                f"  • Transient response: Good near Fb, poorer below tuning"
            )
        elif enclosure_type == "exponential_horn":
            return (
                f"Horn-loaded trade-offs:\n"
                f"  • Efficiency: Much higher than direct radiator (+6-10dB)\n"
                f"  • Size: Large enclosure required for low-frequency extension\n"
                f"  • Bass extension: Limited by horn length and mouth size\n"
                f"  • Complexity: More difficult to design and build\n"
                f"  • Note: Requires horn simulation (Phase 3) for optimization"
            )
        return "Trade-off analysis not available for this enclosure type."

    def _analyze_sensitivity(
        self,
        param_values: np.ndarray,
        f3_values: np.ndarray,
        size_values: np.ndarray
    ) -> Dict:
        """
        Analyze parameter sensitivity from sweep results.

        Calculates correlation coefficients between the swept parameter
        and each objective to determine which objectives are most
        sensitive to parameter changes.

        Args:
            param_values: Array of parameter values tested
            f3_values: Array of F3 values at each parameter point
            size_values: Array of size values at each parameter point

        Returns:
            Dict with sensitivity metrics:
            - f3_sensitivity: Absolute correlation with F3
            - size_sensitivity: Absolute correlation with size
            - most_sensitive_objective: Which objective is most affected
            - f3_correlation: Raw correlation coefficient (can be negative)
            - trend_description: Human-readable trend description

        Note:
            Correlation values range from -1 to 1:
            - Near -1: Strong negative correlation (parameter up, objective down)
            - Near 0: No correlation
            - Near 1: Strong positive correlation (parameter up, objective up)
        """
        # Filter out NaN values
        valid_mask = ~np.isnan(f3_values)
        if np.sum(valid_mask) < 2:
            return {
                "parameter_sensitivity": "insufficient_data",
                "f3_sensitivity": 0.0,
                "size_sensitivity": 0.0,
                "most_sensitive_objective": "unknown",
                "f3_correlation": 0.0,
                "trend_description": "Insufficient valid data points"
            }

        f3_valid = f3_values[valid_mask]
        param_valid = param_values[valid_mask]

        # Calculate correlation coefficient with F3
        if len(param_valid) > 1:
            f3_corr = np.corrcoef(param_valid, f3_valid)[0, 1]
            # Handle case where correlation is undefined (zero variance)
            if np.isnan(f3_corr):
                f3_corr = 0.0
        else:
            f3_corr = 0.0

        # Size is directly related to Vb (for sealed boxes)
        # For ported boxes sweeping Fb, size doesn't change
        size_corr = 1.0 if np.std(size_values) > 0 else 0.0

        # Determine most sensitive objective
        most_sensitive = "F3" if abs(f3_corr) > abs(size_corr) else "size"

        # Generate trend description
        if abs(f3_corr) < 0.3:
            trend = "Weak correlation - parameter has little effect on F3"
        elif abs(f3_corr) < 0.7:
            trend = "Moderate correlation - parameter affects F3"
        else:
            trend = "Strong correlation - parameter significantly affects F3"

        if f3_corr < -0.3:
            trend += " (increasing parameter reduces F3 - better bass)"
        elif f3_corr > 0.3:
            trend += " (increasing parameter increases F3 - worse bass)"

        return {
            "f3_sensitivity": abs(f3_corr),
            "size_sensitivity": abs(size_corr),
            "most_sensitive_objective": most_sensitive,
            "f3_correlation": float(f3_corr),
            "trend_description": trend
        }

    def _generate_sweep_recommendations(
        self,
        parameter: str,
        param_values: np.ndarray,
        f3_values: np.ndarray,
        size_values: np.ndarray,
        enclosure_type: str
    ) -> List[str]:
        """
        Generate design recommendations from sweep results.

        Analyzes sweep data to provide actionable insights about:
        - Optimal parameter values
        - Diminishing returns
        - Design trade-offs
        - Sweet spots

        Args:
            parameter: Name of parameter that was swept
            param_values: Array of parameter values tested
            f3_values: Array of F3 values at each point
            size_values: Array of size values at each point
            enclosure_type: Type of enclosure ("sealed" or "ported")

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Filter out NaN values
        valid_mask = ~np.isnan(f3_values)
        if np.sum(valid_mask) == 0:
            return ["No valid designs found in sweep range"]

        f3_valid = f3_values[valid_mask]
        param_valid = param_values[valid_mask]

        # Find overall best F3
        best_f3_idx = np.argmin(f3_valid)
        best_f3 = f3_valid[best_f3_idx]
        best_param = param_valid[best_f3_idx]

        # Format parameter value for display
        if parameter == "Vb":
            param_str = f"{best_param*1000:.1f}L"
        else:
            param_str = f"{best_param:.1f}Hz"

        recommendations.append(
            f"Best F3 ({best_f3:.1f} Hz) at {parameter}={param_str}"
        )

        # Analyze trend
        if len(param_valid) > 1:
            correlation = np.corrcoef(param_valid, f3_valid)[0, 1]

            if np.isnan(correlation):
                correlation = 0.0

            if correlation < -0.7:
                recommendations.append(
                    f"Strong trend: Increasing {parameter} significantly reduces F3 (better bass extension)"
                )
            elif correlation < -0.3:
                recommendations.append(
                    f"Trend: Increasing {parameter} reduces F3 (better bass extension)"
                )
            elif correlation > 0.7:
                recommendations.append(
                    f"Strong trend: Increasing {parameter} significantly increases F3 (worse bass extension)"
                )
            elif correlation > 0.3:
                recommendations.append(
                    f"Trend: Increasing {parameter} increases F3 (worse bass extension)"
                )
            else:
                recommendations.append(
                    f"Weak trend: {parameter} has minimal effect on F3 in this range"
                )

        # Check for diminishing returns
        if len(param_valid) >= 10:
            # Split range into thirds
            n = len(param_valid)
            first_third = f3_valid[:n//3]
            middle_third = f3_valid[n//3:2*n//3]
            last_third = f3_valid[2*n//3:]

            if len(first_third) > 0 and len(last_third) > 0:
                improvement_1st = np.mean(first_third) - np.mean(middle_third)
                improvement_2nd = np.mean(middle_third) - np.mean(last_third)

                # If second half improvement is < 30% of first half
                if improvement_2nd < 0.3 * improvement_1st and improvement_1st > 1.0:
                    # Find sweet spot
                    sweet_idx = np.where(param_valid >= param_valid[n//3])[0]
                    if len(sweet_idx) > 0:
                        sweet_param = param_valid[sweet_idx[0]]
                        if parameter == "Vb":
                            sweet_str = f"{sweet_param*1000:.1f}L"
                        else:
                            sweet_str = f"{sweet_param:.1f}Hz"

                        recommendations.append(
                            f"Diminishing returns: Above {sweet_str}, further {parameter} increases give minimal F3 improvement"
                        )

        # Check for optimal range (within 10% of best F3)
        if len(f3_valid) >= 5:
            f3_threshold = best_f3 * 1.10  # 10% threshold
            optimal_mask = f3_valid <= f3_threshold
            optimal_params = param_valid[optimal_mask]

            if len(optimal_params) >= 3:
                min_opt = np.min(optimal_params)
                max_opt = np.max(optimal_params)

                if parameter == "Vb":
                    range_str = f"{min_opt*1000:.1f}L - {max_opt*1000:.1f}L"
                else:
                    range_str = f"{min_opt:.1f}Hz - {max_opt:.1f}Hz"

                recommendations.append(
                    f"Optimal range: {parameter} in [{range_str}] gives F3 within 10% of optimal"
                )

        # Add enclosure-specific advice
        if enclosure_type == "sealed" and parameter == "Vb":
            # Check Qtc values
            driver_Qts = 0.37  # Typical value (would be better to pass actual driver)
            for i, (vb, f3) in enumerate(zip(param_valid, f3_valid)):
                if np.isnan(f3):
                    continue

                # Estimate Qtc: Qtc = Qts * sqrt(Vas/Vb)
                # Rough approximation without driver Vas
                if i == len(param_valid) // 2:  # Check middle value
                    if parameter == "Vb":
                        recommendations.append(
                            f"Tip: Smaller {parameter} = higher Qtc (tighter bass, less extension)"
                        )
                        recommendations.append(
                            f"Tip: Larger {parameter} = lower Qtc (deeper bass, softer sound)"
                        )
                    break

        return recommendations

