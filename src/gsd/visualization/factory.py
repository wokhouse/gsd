"""
Plot factory for generating standard visualizations.

This module provides the PlotFactory class for generating publication-quality
plots from optimization results. It supports Pareto fronts, SPL responses,
horn profiles, and parameter distributions.

Literature:
    - Matplotlib documentation - Plotting best practices
    - Small (1972) - Loudspeaker enclosure response characteristics
    - Olson (1947) - Horn theory (for geometry plots)
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass
import warnings

from gsd.visualization.config import PlotConfig, MultiPlotConfig
from gsd.visualization.styles import apply_style, get_palette, get_figure_size
from gsd.visualization.utils import (
    setup_frequency_axis,
    setup_spl_axis,
    find_f3_frequency,
    normalize_objectives,
    find_knee_point,
    create_text_box,
    save_figure,
)


class PlotFactory:
    """
    Factory for generating standard plots from optimization results.

    This class provides a unified interface for creating various types of
    visualizations from optimization results, supporting both file-based and
    object-based data sources.

    Attributes:
        config: Plot configuration
        results: Loaded optimization results

    Examples:
        >>> from gsd.visualization import PlotFactory, PlotConfig
        >>>
        >>> config = PlotConfig(
        ...     plot_type="pareto_2d",
        ...     data_source="results.json",
        ...     x_objective="f3",
        ...     y_objective="flatness"
        ... )
        >>> factory = PlotFactory(config)
        >>> fig = factory.create_plot()
        >>> fig.savefig("output.png", dpi=150)
    """

    # Available plot types
    PLOT_TYPES = [
        "pareto_2d",
        "pareto_3d",
        "spl_response",
        "horn_profile",
        "parameter_distribution",
        "correlation_matrix",
        "quality_dashboard",
    ]

    def __init__(self, config: PlotConfig):
        """
        Initialize plot factory with configuration.

        Args:
            config: Plot configuration

        Raises:
            ValueError: If plot_type is not supported
            FileNotFoundError: If data_source file doesn't exist
        """
        if config.plot_type not in self.PLOT_TYPES:
            raise ValueError(
                f"Unsupported plot_type: {config.plot_type}. "
                f"Available: {self.PLOT_TYPES}"
            )

        self.config = config
        self.results = self._load_results()

        # Apply style
        apply_style(config.style)

    def _load_results(self) -> Dict[str, Any]:
        """
        Load optimization results from file or use passed object.

        Returns:
            Dictionary with optimization results

        Raises:
            FileNotFoundError: If data_source file doesn't exist
            ValueError: If data format is invalid
        """
        # If it's already a dict/object, use it directly
        if isinstance(self.config.data_source, dict):
            return self.config.data_source

        # Otherwise, load from file
        path = Path(self.config.data_source)

        if not path.exists():
            raise FileNotFoundError(f"Results file not found: {path}")

        with open(path, 'r') as f:
            data = json.load(f)

        # Validate basic structure
        if 'pareto_front' not in data:
            raise ValueError("Invalid results format: missing 'pareto_front'")

        return data

    def create_plot(self) -> Figure:
        """
        Generate plot based on configured plot_type.

        Returns:
            Matplotlib Figure object

        Raises:
            ValueError: If plot_type is not supported
        """
        plot_methods = {
            "pareto_2d": self._plot_pareto_2d,
            "pareto_3d": self._plot_pareto_3d,
            "spl_response": self._plot_spl_response,
            "horn_profile": self._plot_horn_profile,
            "parameter_distribution": self._plot_parameter_distribution,
            "correlation_matrix": self._plot_correlation_matrix,
            "quality_dashboard": self._plot_quality_dashboard,
        }

        if self.config.plot_type not in plot_methods:
            raise ValueError(f"Plot type not implemented: {self.config.plot_type}")

        return plot_methods[self.config.plot_type]()

    def _get_selected_designs(self) -> List[Dict[str, Any]]:
        """
        Get selected designs from results based on configuration.

        Returns:
            List of design dictionaries
        """
        pareto_front = self.results['pareto_front']

        # If specific indices provided, use those
        if self.config.design_indices is not None:
            return [pareto_front[i] for i in self.config.design_indices]

        # If num_designs specified, use that many
        if self.config.num_designs is not None:
            return pareto_front[:self.config.num_designs]

        # Otherwise use all
        return pareto_front

    def _extract_objective_values(
        self,
        objective_name: str,
        designs: Optional[List[Dict[str, Any]]] = None
    ) -> np.ndarray:
        """
        Extract objective values from designs.

        Args:
            objective_name: Name of objective to extract
            designs: List of designs (uses pareto_front if None)

        Returns:
            Array of objective values
        """
        if designs is None:
            designs = self.results['pareto_front']

        values = []
        for design in designs:
            if objective_name in design['objectives']:
                values.append(design['objectives'][objective_name])
            else:
                warnings.warn(f"Objective '{objective_name}' not found in design")
                values.append(np.nan)

        return np.array(values)

    def _plot_pareto_2d(self) -> Figure:
        """
        Create 2D Pareto front scatter plot.

        Shows trade-off between two objectives, with optional knee point marking.

        Returns:
            Matplotlib Figure
        """
        # Get designs
        designs = self._get_selected_designs()

        # Extract objective values
        x = self._extract_objective_values(self.config.x_objective, designs)
        y = self._extract_objective_values(self.config.y_objective, designs)

        # Filter out NaN values
        if self.config.z_objective:
            # If using z_objective for coloring, include it in the mask
            z = self._extract_objective_values(self.config.z_objective, designs)
            valid_mask = ~(np.isnan(x) | np.isnan(y) | np.isnan(z))
        else:
            # Only filter x and y
            valid_mask = ~(np.isnan(x) | np.isnan(y))

        n_filtered = len(x) - valid_mask.sum()
        x = x[valid_mask]
        y = y[valid_mask]
        valid_designs = [designs[i] for i in range(len(designs)) if valid_mask[i]]

        if n_filtered > 0:
            warnings.warn(f"Filtered out {n_filtered} designs with NaN objective values")

        if len(x) == 0:
            warnings.warn("No valid data points to plot (all NaN values)")
            fig, ax = plt.subplots(figsize=self.config.figure_size)
            ax.text(0.5, 0.5, "No valid data to display\n(all objective values are NaN)",
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_title(self.config.title or 'Pareto Front')
            return fig

        # Get color palette
        palette = get_palette('pareto')

        # Create figure
        fig, ax = plt.subplots(figsize=self.config.figure_size)

        # Color by third objective if available
        if self.config.z_objective:
            # z was already filtered together with x and y using valid_mask
            z = z[valid_mask]
            scatter = ax.scatter(
                x, y,
                c=z,
                cmap='viridis',
                s=60,
                alpha=0.7,
                edgecolors='black',
                linewidth=0.5,
            )
            # Add colorbar
            cbar = plt.colorbar(scatter, ax=ax)
            cbar.set_label(self.config.z_objective.replace('_', ' ').title(), fontsize=10)
        else:
            ax.scatter(
                x, y,
                color=palette['primary'],
                s=60,
                alpha=0.7,
                edgecolors='black',
                linewidth=0.5,
            )

        # Mark knee point if requested
        if self.config.mark_knee:
            knee_idx = find_knee_point(x, y)
            ax.scatter(
                x[knee_idx], y[knee_idx],
                color=palette['highlight'],
                s=200,
                marker='*',
                edgecolors='black',
                linewidth=1.5,
                label='Best Compromise',
                zorder=10,
            )
            ax.legend()

        # Labels and styling
        ax.set_xlabel(
            self.config.xlabel or self.config.x_objective.replace('_', ' ').title(),
            fontsize=11
        )
        ax.set_ylabel(
            self.config.ylabel or self.config.y_objective.replace('_', ' ').title(),
            fontsize=11
        )

        title = self.config.title or 'Pareto Front'
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)

        # Add text box with stats
        stats_text = (
            f"Pareto-optimal designs: {len(x)}\\n"
            f"{self.config.x_objective}: {x.min():.2f} - {x.max():.2f}\\n"
            f"{self.config.y_objective}: {y.min():.2f} - {y.max():.2f}"
        )
        create_text_box(ax, stats_text, 'top left', fontsize=9)

        plt.tight_layout()

        return fig

    def _plot_pareto_3d(self) -> Figure:
        """
        Create 3D Pareto front scatter plot.

        Shows trade-off between three objectives.

        Returns:
            Matplotlib Figure
        """
        from mpl_toolkits.mplot3d import Axes3D

        # Get designs
        designs = self._get_selected_designs()

        # Extract objective values
        x = self._extract_objective_values(self.config.x_objective, designs)
        y = self._extract_objective_values(self.config.y_objective, designs)
        z = self._extract_objective_values(
            self.config.z_objective or 'size',
            designs
        )

        # Filter out NaN values
        valid_mask = ~(np.isnan(x) | np.isnan(y) | np.isnan(z))
        n_filtered = len(x) - valid_mask.sum()
        x = x[valid_mask]
        y = y[valid_mask]
        z = z[valid_mask]

        if n_filtered > 0:
            warnings.warn(f"Filtered out {n_filtered} designs with NaN objective values (3D plot)")

        if len(x) == 0:
            warnings.warn("No valid data points to plot (all NaN values)")
            fig = plt.figure(figsize=self.config.figure_size)
            ax = fig.add_subplot(111, projection='3d')
            ax.text2D(0.5, 0.5, "No valid data to display\n(all objective values are NaN)",
                     transform=ax.transAxes, ha='center', va='center')
            ax.set_title(self.config.title or '3D Pareto Front')
            return fig

        # Get color palette
        palette = get_palette('pareto')

        # Create figure with 3D axes
        fig = plt.figure(figsize=self.config.figure_size)
        ax = fig.add_subplot(111, projection='3d')

        # Color by one of the objectives
        colors = normalize_objectives(z, 'minimize')

        scatter = ax.scatter(
            x, y, z,
            c=colors,
            cmap='viridis',
            s=60,
            alpha=0.7,
            edgecolors='black',
            linewidth=0.5,
        )

        # Mark knee point if requested
        if self.config.mark_knee:
            # Find knee in 2D projection (x vs y)
            knee_idx = find_knee_point(x, y)
            ax.scatter(
                x[knee_idx], y[knee_idx], z[knee_idx],
                color=palette['highlight'],
                s=200,
                marker='*',
                edgecolors='black',
                linewidth=1.5,
                label='Best Compromise',
                zorder=10,
            )
            ax.legend()

        # Labels
        ax.set_xlabel(
            self.config.xlabel or self.config.x_objective.replace('_', ' ').title(),
            fontsize=10
        )
        ax.set_ylabel(
            self.config.ylabel or self.config.y_objective.replace('_', ' ').title(),
            fontsize=10
        )
        ax.set_zlabel(
            self.config.z_objective or 'size',
            fontsize=10
        )

        title = self.config.title or 'Pareto Front (3D)'
        ax.set_title(title, fontsize=12, fontweight='bold', pad=20)

        # Adjust view angle for better visualization
        ax.view_init(elev=20, azim=45)

        plt.tight_layout()

        return fig

    def _plot_spl_response(self) -> Figure:
        """
        Create SPL frequency response plot for selected designs.

        Calculates and plots SPL vs frequency for each selected design.

        Returns:
            Matplotlib Figure

        Note:
            This requires enclosure-specific response calculation methods.
            For horns, uses FrontLoadedHorn.spl_response_array()
        """
        # Get selected designs
        designs = self._get_selected_designs()

        # Get driver name from metadata
        driver_name = self.results.get('optimization_metadata', {}).get('driver_name', 'Unknown')
        enclosure_type = self.results.get('optimization_metadata', {}).get('enclosure_type', 'unknown')

        # Create figure
        fig, ax = plt.subplots(figsize=self.config.figure_size)

        # Set up frequency axis
        setup_frequency_axis(
            ax,
            freq_min=self.config.frequency_range[0],
            freq_max=self.config.frequency_range[1],
        )

        # Generate frequency points (log spacing)
        frequencies = np.logspace(
            np.log10(self.config.frequency_range[0]),
            np.log10(self.config.frequency_range[1]),
            200
        )

        # Color palette for multiple curves
        colors = plt.cm.viridis(np.linspace(0, 1, len(designs)))

        # Plot SPL for each design
        for i, design in enumerate(designs):
            try:
                # Calculate SPL response
                spl_data = self._calculate_spl_for_design(design, frequencies)

                if spl_data is not None:
                    ax.semilogx(
                        frequencies,
                        spl_data,
                        color=colors[i],
                        linewidth=1.5 if len(designs) > 5 else 2.0,
                        alpha=0.8,
                        label=f"Design {i+1}" if len(designs) <= 10 else None,
                    )

                    # Find and mark F3
                    f3 = find_f3_frequency(frequencies, spl_data)
                    if f3 is not None:
                        ax.axvline(
                            f3,
                            color=colors[i],
                            linestyle='--',
                            alpha=0.3,
                            linewidth=1,
                        )

            except Exception as e:
                warnings.warn(f"Failed to plot design {i}: {e}")
                continue

        # Set up SPL axis
        setup_spl_axis(ax)

        # Labels and title
        title = self.config.title or f'SPL Frequency Response - {driver_name}'
        ax.set_title(title, fontsize=12, fontweight='bold')

        # Legend (only if reasonable number of designs)
        if len(designs) <= 10:
            ax.legend(loc=self.config.legend_loc, fontsize=9)

        plt.tight_layout()

        return fig

    def _calculate_spl_for_design(
        self,
        design: Dict[str, Any],
        frequencies: np.ndarray
    ) -> Optional[np.ndarray]:
        """
        Calculate SPL response for a single design.

        This method implements enclosure-specific SPL calculation using validated
        response methods from the enclosure modules.

        Literature:
            - Olson (1947) - Horn-loaded systems
            - Small (1972) - Sealed box SPL
            - Thiele (1971) - Ported box SPL
            - Beranek (1954) - Acoustic power and SPL

        Args:
            design: Design dictionary with parameters and objectives
            frequencies: Frequency array (Hz)

        Returns:
            SPL array (dB) or None if calculation failed

        Raises:
            ValueError: If enclosure type is not supported
        """
        try:
            # Get driver name from metadata
            metadata = self.results.get('optimization_metadata', {})
            # Support both 'driver' and 'driver_name' keys
            driver_name = metadata.get('driver_name') or metadata.get('driver', 'Unknown')
            enclosure_type = metadata.get('enclosure_type', 'unknown')

            # Load driver
            from gsd.driver import load_driver
            driver = load_driver(driver_name)

            # Get design parameters
            params = design['parameters']

            # Route to appropriate enclosure type
            if enclosure_type in ['exponential_horn', 'multisegment_horn', 'mixed_profile_horn',
                                   'conical_horn', 'hyperbolic_horn']:
                return self._calculate_horn_spl(driver, params, frequencies, enclosure_type)

            elif enclosure_type == 'sealed':
                return self._calculate_sealed_box_spl(driver, params, frequencies)

            elif enclosure_type == 'ported':
                return self._calculate_ported_box_spl(driver, params, frequencies)

            else:
                warnings.warn(f"Unsupported enclosure type: {enclosure_type}")
                return None

        except Exception as e:
            warnings.warn(f"SPL calculation failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _calculate_horn_spl(
        self,
        driver,
        params: Dict[str, float],
        frequencies: np.ndarray,
        horn_type: str
    ) -> Optional[np.ndarray]:
        """
        Calculate SPL response for horn-loaded enclosure.

        Literature:
            - Olson (1947), Chapter 8 - Horn driver systems
            - Beranek (1954), Chapter 5 - Acoustic impedance networks
            - literature/horns/olson_1947.md
            - literature/horns/beranek_1954.md

        Args:
            driver: ThieleSmallParameters instance
            params: Design parameters dictionary
            frequencies: Frequency array (Hz)
            horn_type: Type of horn ('exponential_horn', 'multisegment_horn', etc.)

        Returns:
            SPL array (dB) or None if calculation failed
        """
        try:
            from gsd.enclosure.front_loaded_horn import FrontLoadedHorn
            from gsd.simulation.types import HornSegment, MultiSegmentHorn, ExponentialHorn
            import numpy as np

            # Build horn based on type
            if horn_type in ['multisegment_horn', 'mixed_profile_horn']:
                # Use build_multisegment_horn from the parameters module
                from gsd.optimization.parameters.multisegment_horn_params import (
                    build_multisegment_horn,
                )

                # Convert params dict to design array format
                # For 2-segment horn: [throat, middle, mouth, L1, L2, V_tc, V_rc]
                design_array = np.array([
                    params.get('throat_area', 0.001),
                    params.get('middle_area', 0.01),
                    params.get('mouth_area', 0.1),
                    params.get('length1', 0.3),
                    params.get('length2', 0.3),
                    params.get('V_tc', 0.0),
                    params.get('V_rc', 0.0),
                ])

                horn, V_tc, V_rc = build_multisegment_horn(design_array, driver, num_segments=2)

            elif horn_type == 'exponential_horn':
                # Build exponential horn directly from parameters
                throat_area = params.get('throat_area', 0.001)
                mouth_area = params.get('mouth_area', 0.1)
                length = params.get('length', 1.0)
                V_tc = params.get('V_tc', 0.0)
                V_rc = params.get('V_rc', 0.0)

                horn = ExponentialHorn(throat_area, mouth_area, length)

            elif horn_type == 'conical_horn':
                # Build conical horn directly from parameters
                from gsd.simulation.types import ConicalHorn

                throat_area = params.get('throat_area', 0.001)
                mouth_area = params.get('mouth_area', 0.1)
                length = params.get('length', 1.0)
                V_tc = params.get('V_tc', 0.0)
                V_rc = params.get('V_rc', 0.0)

                horn = ConicalHorn(throat_area, mouth_area, length)

            else:
                warnings.warn(f"Unsupported horn type: {horn_type}")
                return None

            # Get chamber volumes (may not be in params for simple exponential horns)
            V_tc = params.get('V_tc', 0.0)
            V_rc = params.get('V_rc', 0.0)

            # Create front-loaded horn system
            flh = FrontLoadedHorn(
                driver=driver,
                horn=horn,
                V_tc=V_tc,
                V_rc=V_rc,
                radiation_angle=2 * np.pi,  # Half-space
            )

            # Calculate SPL response
            result = flh.spl_response_array(
                frequencies=frequencies,
                voltage=self.config.voltage,
                measurement_distance=self.config.measurement_distance,
            )

            return result['SPL']

        except Exception as e:
            warnings.warn(f"Horn SPL calculation failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _calculate_sealed_box_spl(
        self,
        driver,
        params: Dict[str, float],
        frequencies: np.ndarray
    ) -> Optional[np.ndarray]:
        """
        Calculate SPL response for sealed box enclosure.

        Literature:
            - Small (1972), Equation 1 - Normalized pressure response
            - Small (1972), Eq. 9 - Parallel Q combination
            - literature/thiele_small/small_1972_closed_box.md

        Args:
            driver: ThieleSmallParameters instance
            params: Design parameters dictionary (must contain 'Vb')
            frequencies: Frequency array (Hz)

        Returns:
            SPL array (dB) or None if calculation failed
        """
        try:
            from gsd.enclosure.sealed_box import calculate_spl_array

            Vb = params.get('Vb')
            if Vb is None:
                warnings.warn("Sealed box parameters missing 'Vb'")
                return None

            # Calculate SPL using validated transfer function method
            spl = calculate_spl_array(
                frequencies=frequencies,
                driver=driver,
                Vb=Vb,
                voltage=self.config.voltage,
                measurement_distance=self.config.measurement_distance,
            )

            return spl

        except Exception as e:
            warnings.warn(f"Sealed box SPL calculation failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _calculate_ported_box_spl(
        self,
        driver,
        params: Dict[str, float],
        frequencies: np.ndarray
    ) -> Optional[np.ndarray]:
        """
        Calculate SPL response for ported box enclosure.

        Literature:
            - Small (1973), "Vented-Box Loudspeaker Systems Part I", JAES
            - Thiele (1971), "Loudspeakers in Vented Boxes", Parts 1 & 2
            - literature/thiele_small/thiele_1971_vented_boxes.md

        Args:
            driver: ThieleSmallParameters instance
            params: Design parameters dictionary (must contain 'Vb', 'Fb', 'port_area', 'port_length')
            frequencies: Frequency array (Hz)

        Returns:
            SPL array (dB) or None if calculation failed
        """
        try:
            from gsd.enclosure.ported_box_vector_sum import calculate_spl_ported_vector_sum_array

            Vb = params.get('Vb')
            Fb = params.get('Fb')
            port_area = params.get('port_area')
            port_length = params.get('port_length')

            if None in [Vb, Fb, port_area, port_length]:
                missing = [k for k, v in {'Vb': Vb, 'Fb': Fb, 'port_area': port_area,
                                           'port_length': port_length}.items() if v is None]
                warnings.warn(f"Ported box parameters missing: {missing}")
                return None

            # Calculate SPL using validated vector summation method
            spl = calculate_spl_ported_vector_sum_array(
                frequencies=frequencies,
                driver=driver,
                Vb=Vb,
                Fb=Fb,
                port_area=port_area,
                port_length=port_length,
                voltage=self.config.voltage,
                measurement_distance=self.config.measurement_distance,
            )

            return spl

        except Exception as e:
            warnings.warn(f"Ported box SPL calculation failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _plot_horn_profile(self) -> Figure:
        """
        Create horn cross-section geometry plot.

        Shows the horn profile with throat, segments, and mouth.

        Returns:
            Matplotlib Figure
        """
        # Get selected design (use first if multiple)
        designs = self._get_selected_designs()
        if len(designs) == 0:
            raise ValueError("No designs to plot")

        design = designs[0]

        # Create figure
        fig, ax = plt.subplots(figsize=self.config.figure_size)

        # Extract horn geometry parameters
        params = design['parameters']

        # Try to build horn profile
        try:
            x_profile, y_profile = self._get_horn_profile_coordinates(params)

            # Plot horn outline
            ax.plot(
                x_profile,
                y_profile,
                color=self.config.profile_color,
                linewidth=2,
                label='Horn profile'
            )

            # Plot symmetry (top and bottom)
            ax.plot(
                x_profile,
                -y_profile,
                color=self.config.profile_color,
                linewidth=2
            )

            # Fill horn interior
            ax.fill_between(
                x_profile,
                y_profile,
                -y_profile,
                color=self.config.profile_color,
                alpha=0.2,
            )

        except Exception as e:
            # Fallback: show parameters as text
            ax.text(
                0.5, 0.5,
                f"Horn profile visualization\nnot available for this enclosure type\n\n{str(e)}",
                ha='center',
                va='center',
                fontsize=10,
                transform=ax.transAxes,
            )
            ax.set_xlim(0, 1)
            ax.set_ylim(-1, 1)

        # Labels and styling
        ax.set_xlabel('Axial Distance (m)', fontsize=11)
        ax.set_ylabel('Radius (m)', fontsize=11)

        title = self.config.title or 'Horn Cross-Section Profile'
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.axis('equal')

        plt.tight_layout()

        return fig

    def _get_horn_profile_coordinates(
        self,
        params: Dict[str, float]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get horn profile coordinates from parameters.

        Args:
            params: Design parameters

        Returns:
            Tuple of (x, y) arrays for horn profile

        Note:
            This is a simplified implementation. Real implementation would
            handle different horn types (exponential, conical, multisegment).
        """
        # Placeholder: create a simple expanding horn
        # Real implementation would decode parameters properly

        if 'throat_area' in params and 'mouth_area' in params:
            # Horn-type parameters
            S_t = params['throat_area']
            S_m = params['mouth_area']

            # Calculate radii
            r_t = np.sqrt(S_t / np.pi)
            r_m = np.sqrt(S_m / np.pi)

            # Estimate length (may not be in params)
            if 'length1' in params:
                L = params['length1']
            elif 'length' in params:
                L = params['length']
            else:
                L = 1.0  # Default

            # Create profile
            x = np.linspace(0, L, 100)
            # Linear radius expansion (conical approximation)
            y = r_t + (r_m - r_t) * (x / L)

            return x, y
        else:
            raise ValueError("Parameters don't contain horn geometry")

    def _plot_parameter_distribution(self) -> Figure:
        """
        Create parameter distribution plot (box plots).

        Shows the range and distribution of parameters across Pareto front.

        Returns:
            Matplotlib Figure
        """
        # Get designs
        designs = self._get_selected_designs()

        # Extract parameter names
        param_names = self.results.get('parameter_names', [])
        if not param_names:
            # Infer from first design
            param_names = list(designs[0]['parameters'].keys())

        # Prepare data for box plots
        param_data = []
        param_labels = []

        for param_name in param_names:
            values = []
            for design in designs:
                if param_name in design['parameters']:
                    values.append(design['parameters'][param_name])

            if values:
                param_data.append(values)
                # Create readable label
                label = param_name.replace('_', ' ').replace('area', ' (m²)').replace('length', ' (m)')
                param_labels.append(label)

        if not param_data:
            raise ValueError("No parameter data found")

        # Create figure
        fig, ax = plt.subplots(figsize=self.config.figure_size)

        # Create box plots
        bp = ax.boxplot(
            param_data,
            labels=param_labels,
            patch_artist=True,
            medianprops=dict(color='red', linewidth=2),
            boxprops=dict(facecolor='lightblue', alpha=0.7),
        )

        # Styling
        ax.set_ylabel('Parameter Value', fontsize=11)
        ax.set_title(
            self.config.title or 'Parameter Distribution Across Pareto Front',
            fontsize=12,
            fontweight='bold'
        )
        ax.grid(True, axis='y', alpha=0.3)

        # Rotate x labels if needed
        if len(param_labels) > 5:
            plt.xticks(rotation=45, ha='right')

        plt.tight_layout()

        return fig

    def _plot_correlation_matrix(self) -> Figure:
        """
        Create correlation matrix heatmap.

        Shows Pearson correlation coefficients between all parameters
        and objectives in the Pareto front. Helps identify which
        parameters drive which objectives.

        Literature:
            - Standard statistical methods (Pearson correlation)

        Returns:
            Matplotlib Figure

        Note:
            Positive correlation (red): parameter increases → objective increases
            Negative correlation (blue): parameter increases → objective decreases
            Values near 0 (white): no linear relationship
        """
        import pandas as pd
        import seaborn as sns

        # Get designs from Pareto front
        designs = self.results['pareto_front']

        # Extract parameter names
        param_names = self.results.get('parameter_names', [])
        if not param_names:
            # Infer from first design
            param_names = list(designs[0]['parameters'].keys())

        # Build dataframe: each row is a design, columns are parameters + objectives
        data_rows = []

        for design in designs:
            row = {}

            # Add parameter values
            for param_name in param_names:
                if param_name in design['parameters']:
                    row[param_name] = design['parameters'][param_name]

            # Add objective values
            for obj_name, obj_value in design['objectives'].items():
                row[obj_name] = obj_value

            data_rows.append(row)

        # Create DataFrame
        df = pd.DataFrame(data_rows)

        # Compute correlation matrix
        corr_matrix = df.corr(method='pearson')

        # Separate parameter-parameter, parameter-objective, objective-objective
        # For this plot, we want to show parameters (rows) vs objectives (columns)
        param_cols = [col for col in corr_matrix.columns if col in param_names]
        obj_cols = [col for col in corr_matrix.columns if col not in param_names]

        # If no objectives or parameters found, use full correlation matrix
        if not param_cols or not obj_cols:
            warnings.warn("Could not separate parameters and objectives for correlation matrix")
            # Fall back to full correlation matrix
            corr_po = corr_matrix
        else:
            # Extract parameter-objective correlations only
            corr_po = corr_matrix.loc[param_cols, obj_cols]

        # Create figure
        fig, ax = plt.subplots(figsize=self.config.figure_size)

        # Plot heatmap
        sns.heatmap(
            corr_po,
            annot=True,
            fmt='.2f',
            cmap='RdBu_r',  # Red-blue diverging (reversed so red=negative, blue=positive)
            center=0,
            vmin=-1,
            vmax=1,
            cbar_kws={'label': 'Pearson Correlation'},
            ax=ax,
            linewidths=0.5,
        )

        # Labels and title
        ax.set_xlabel('Objectives', fontsize=11, fontweight='bold')
        ax.set_ylabel('Parameters', fontsize=11, fontweight='bold')

        # Format tick labels
        ax.set_xticklabels([col.replace('_', ' ').title() for col in corr_po.columns], rotation=45, ha='right')
        ax.set_yticklabels([col.replace('_', ' ').title() for col in corr_po.index], rotation=0)

        title = self.config.title or 'Parameter-Objective Correlations'
        ax.set_title(title, fontsize=12, fontweight='bold', pad=20)

        plt.tight_layout()
        return fig

    def _plot_quality_dashboard(self) -> Figure:
        """
        Create multi-panel dashboard of qualitative metrics.

        Shows wavefront quality, impedance smoothness, and response
        quality metrics across the Pareto front in a 2x2 grid.

        Literature:
            - Keele (1975) - Wavefront sphericity and diffraction
            - Olson (1947) - Horn impedance and resonance
            - Beranek (1954) - Acoustic quality assessment

        Returns:
            Matplotlib Figure with 2x2 subplot grid

        Layout:
            Top-left:     Wavefront sphericity vs F3
            Top-right:    Impedance smoothness vs flatness
            Bottom-left:  Response slope distribution
            Bottom-right: Composite quality score
        """
        # Get designs from Pareto front
        designs = self.results['pareto_front']

        # Create 2x2 subplot grid
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # Panel 1: Wavefront sphericity vs F3
        ax1 = axes[0, 0]
        self._add_pareto_to_axis(
            ax1,
            designs,
            'wavefront_sphericity',
            'f3',
            title='Wavefront Quality vs Bass Extension'
        )

        # Panel 2: Impedance smoothness vs flatness
        ax2 = axes[0, 1]
        self._add_pareto_to_axis(
            ax2,
            designs,
            'impedance_smoothness',
            'flatness',
            title='Impedance Quality vs Response Flatness'
        )

        # Panel 3: Response slope distribution
        ax3 = axes[1, 0]
        self._add_quality_boxplot(
            ax3,
            designs,
            'response_slope',
            title='Response Slope Distribution',
            ylabel='Slope (dB/decade)'
        )

        # Panel 4: Composite quality score
        ax4 = axes[1, 1]
        self._add_composite_quality_plot(
            ax4,
            designs,
            title='Composite Quality Score'
        )

        plt.tight_layout()
        return fig

    def _add_pareto_to_axis(
        self,
        ax: Axes,
        designs: List[Dict[str, Any]],
        x_objective: str,
        y_objective: str,
        title: str
    ):
        """Helper: Add Pareto scatter plot to axis."""
        x = self._extract_objective_values(x_objective, designs)
        y = self._extract_objective_values(y_objective, designs)

        # Filter out NaN values
        valid_mask = ~(np.isnan(x) | np.isnan(y))
        x = x[valid_mask]
        y = y[valid_mask]

        if len(x) == 0:
            ax.text(0.5, 0.5, "No data available",
                    ha='center', va='center', transform=ax.transAxes)
            ax.set_title(title)
            return

        # Get palette
        palette = get_palette('pareto')

        # Scatter plot
        ax.scatter(
            x, y,
            color=palette['primary'],
            s=60,
            alpha=0.7,
            edgecolors='black',
            linewidth=0.5,
        )

        # Labels
        ax.set_xlabel(x_objective.replace('_', ' ').title(), fontsize=10)
        ax.set_ylabel(y_objective.replace('_', ' ').title(), fontsize=10)
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3)

    def _add_quality_boxplot(
        self,
        ax: Axes,
        designs: List[Dict[str, Any]],
        metric_name: str,
        title: str,
        ylabel: str
    ):
        """Helper: Add box plot of quality metric to axis."""
        values = []
        for design in designs:
            if metric_name in design['objectives']:
                val = design['objectives'][metric_name]
                if not np.isnan(val):
                    values.append(val)

        if not values:
            ax.text(0.5, 0.5, f"No {metric_name} data",
                    ha='center', va='center', transform=ax.transAxes)
            ax.set_title(title)
            return

        # Create box plot
        bp = ax.boxplot(
            [values],
            labels=[metric_name.replace('_', ' ').title()],
            patch_artist=True,
            medianprops=dict(color='red', linewidth=2),
            boxprops=dict(facecolor='lightblue', alpha=0.7),
        )

        # Add statistics text
        stats_text = (
            f"Min: {min(values):.3f}\n"
            f"Max: {max(values):.3f}\n"
            f"Mean: {np.mean(values):.3f}\n"
            f"Median: {np.median(values):.3f}"
        )
        ax.text(0.95, 0.95, stats_text,
                transform=ax.transAxes,
                verticalalignment='top',
                horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                fontsize=9)

        ax.set_ylabel(ylabel, fontsize=10)
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.grid(True, axis='y', alpha=0.3)

    def _add_composite_quality_plot(
        self,
        ax: Axes,
        designs: List[Dict[str, Any]],
        title: str
    ):
        """
        Helper: Add composite quality score plot.

        Combines multiple quality metrics into a single score.
        Lower is better for most metrics (sphericity, impedance_smoothness, flatness).
        """
        # Extract quality metrics
        metrics = ['wavefront_sphericity', 'impedance_smoothness', 'flatness']

        # Normalize each metric to 0-1 range (lower is better → higher quality)
        quality_scores = []
        design_indices = []

        for i, design in enumerate(designs):
            scores = []
            for metric in metrics:
                if metric in design['objectives']:
                    val = design['objectives'][metric]
                    if not np.isnan(val):
                        scores.append(val)

            if scores:
                # Simple average (lower values → better quality)
                # We'll invert so higher bar = better quality
                avg_quality = np.mean(scores)
                quality_scores.append(avg_quality)
                design_indices.append(i)

        if not quality_scores:
            ax.text(0.5, 0.5, "No quality metrics available",
                    ha='center', va='center', transform=ax.transAxes)
            ax.set_title(title)
            return

        # Create horizontal bar chart
        # Invert scores: lower actual value = higher quality score
        max_val = max(quality_scores)
        normalized_scores = [max_val - s for s in quality_scores]

        colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(design_indices)))
        ax.barh(range(len(design_indices)), normalized_scores, color=colors, alpha=0.7)

        ax.set_yticks(range(len(design_indices)))
        ax.set_yticklabels([f'Design {i+1}' for i in design_indices], fontsize=8)
        ax.set_xlabel('Quality Score (higher = better)', fontsize=10)
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.set_ylim(len(design_indices) - 0.5, -0.5)
        ax.grid(True, axis='x', alpha=0.3)

        # Add best design annotation
        best_idx = normalized_scores.index(max(normalized_scores))
        ax.annotate(
            'Best',
            xy=(normalized_scores[best_idx], best_idx),
            xytext=(normalized_scores[best_idx] * 0.8, best_idx),
            arrowprops=dict(arrowstyle='->', lw=1.5, color='red'),
            fontsize=9,
            fontweight='bold',
            color='red'
        )

    @staticmethod
    def create_multi_plot(configs: List[PlotConfig]) -> Figure:
        """
        Create figure with multiple subplots.

        Args:
            configs: List of plot configurations

        Returns:
            Matplotlib Figure with subplots

        Examples:
            >>> from gsd.visualization import PlotConfig, PlotFactory
            >>>
            >>> configs = [
            ...     PlotConfig(plot_type="pareto_2d", data_source="results.json"),
            ...     PlotConfig(plot_type="horn_profile", data_source="results.json"),
            ... ]
            >>> fig = PlotFactory.create_multi_plot(configs)
        """
        n_plots = len(configs)

        # Determine grid layout
        if n_plots <= 2:
            rows, cols = 1, n_plots
        elif n_plots <= 4:
            rows, cols = 2, 2
        elif n_plots <= 6:
            rows, cols = 2, 3
        else:
            rows, cols = 3, 3

        # Create figure
        fig = plt.figure(figsize=(14, 10))

        # Apply style from first config
        if configs:
            apply_style(configs[0].style)

        # Create subplots
        for i, config in enumerate(configs):
            if i >= rows * cols:
                warnings.warn(f"Too many configs ({n_plots}), showing first {rows * cols}")
                break

            ax = fig.add_subplot(rows, cols, i + 1)

            # Create individual plot
            factory = PlotFactory(config)
            plot_fig = factory.create_plot()

            # Copy axes content to subplot
            # (This is a simplified approach - may need adjustment for complex plots)
            plot_ax = plot_fig.axes[0]
            for child in plot_ax.get_children():
                try:
                    ax.add_artist(child)
                except:
                    pass

            # Copy properties
            ax.set_title(plot_ax.get_title(), fontsize=11, fontweight='bold')
            ax.set_xlabel(plot_ax.get_xlabel(), fontsize=10)
            ax.set_ylabel(plot_ax.get_ylabel(), fontsize=10)
            ax.set_xlim(plot_ax.get_xlim())
            ax.set_ylim(plot_ax.get_ylim())

            plt.close(plot_fig)

        plt.tight_layout()
        return fig
