# Phase 2: Plot Types Implementation Instructions

**For:** Future Claude Code instance
**Task:** Implement `correlation_matrix` and `quality_dashboard` plot types
**Date:** 2025-12-31
**Status:** Ready to implement

---

## Context

Phase 1 of plot presets has been completed. The preset system is in place and working. Now we need to implement two new plot types that were defined in the plan:

1. **correlation_matrix** - Heatmap showing parameter-objective correlations
2. **quality_dashboard** - Multi-panel view of qualitative metrics

## Prerequisites

- Phase 1 is complete: presets system exists in `src/gsd/visualization/presets.py`
- PlotFactory exists in `src/gsd/visualization/factory.py`
- All existing plot types work: pareto_2d, pareto_3d, spl_response, horn_profile, parameter_distribution

---

## Task 1: Implement correlation_matrix Plot Type

### File to Modify
`src/gsd/visualization/factory.py`

### Step 1.1: Add to PLOT_TYPES list
Add `"correlation_matrix"` to the `PLOT_TYPES` list (around line 64-70):

```python
PLOT_TYPES = [
    "pareto_2d",
    "pareto_3d",
    "spl_response",
    "horn_profile",
    "parameter_distribution",
    "correlation_matrix",  # ADD THIS
]
```

### Step 1.2: Add to plot_methods dictionary
In `create_plot()` method (around line 135-141), add:

```python
plot_methods = {
    "pareto_2d": self._plot_pareto_2d,
    "pareto_3d": self._plot_pareto_3d,
    "spl_response": self._plot_spl_response,
    "horn_profile": self._plot_horn_profile,
    "parameter_distribution": self._plot_parameter_distribution,
    "correlation_matrix": self._plot_correlation_matrix,  # ADD THIS
}
```

### Step 1.3: Implement _plot_correlation_matrix() method

Add this new method to the PlotFactory class. Place it after `_plot_parameter_distribution()` (around line 949):

```python
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
```

### Step 1.4: Test correlation_matrix

```bash
# Test the new plot type
gsd plot create --type correlation_matrix --input <results.json> --output test_corr.png
```

---

## Task 2: Implement quality_dashboard Plot Type

### File to Modify
`src/gsd/visualization/factory.py`

### Step 2.1: Add to PLOT_TYPES list
Add `"quality_dashboard"` to the `PLOT_TYPES` list:

```python
PLOT_TYPES = [
    "pareto_2d",
    "pareto_3d",
    "spl_response",
    "horn_profile",
    "parameter_distribution",
    "correlation_matrix",
    "quality_dashboard",  # ADD THIS
]
```

### Step 2.2: Add to plot_methods dictionary
Add to `create_plot()` method:

```python
plot_methods = {
    "pareto_2d": self._plot_pareto_2d,
    "pareto_3d": self._plot_pareto_3d,
    "spl_response": self._plot_spl_response,
    "horn_profile": self._plot_horn_profile,
    "parameter_distribution": self._plot_parameter_distribution,
    "correlation_matrix": self._plot_correlation_matrix,
    "quality_dashboard": self._plot_quality_dashboard,  # ADD THIS
}
```

### Step 2.3: Implement _plot_quality_dashboard() method

Add this new method after `_plot_correlation_matrix()`:

```python
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
    import numpy as np

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
    import numpy as np

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
    import numpy as np

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
```

### Step 2.4: Test quality_dashboard

```bash
# Test the new plot type
gsd plot create --type quality_dashboard --input <results.json> --output test_quality.png
```

---

## Task 3: Update Presets to Use New Plot Types

### File to Modify
`src/gsd/visualization/presets.py`

### Step 3.1: Add new preset using quality_dashboard

Add a new preset after the `quality` preset:

```python
    "correlations": {
        "description": "Parameter-objective relationship analysis",
        "plot_types": [
            {
                "type": "correlation_matrix",
            },
            {
                "type": "quality_dashboard",
            },
        ],
        "typical_use_cases": [
            "Understanding which parameters drive performance",
            "Identifying critical parameters",
            "Sensitivity analysis",
        ],
    },
```

### Step 3.2: Update CLI to include new preset

### File: `src/gsd/cli_commands/plot.py`

Update the `--preset` choice list (around line 203):

```python
@click.option('--preset', type=click.Choice(['overview', 'spl', 'quality', 'correlations']),
              help='Use preset plot configuration')
```

### File: `src/gsd/cli_commands/optimize.py`

Update the `--plot-preset` choice list (around line 175):

```python
@click.option('--plot-preset', type=click.Choice(['overview', 'spl', 'quality', 'correlations']),
              default='overview', help='Plot preset to use with --plot (default: overview)')
```

---

## Task 4: Testing

### Step 4.1: Test individual plot types

```bash
# Test correlation_matrix with actual optimization results
gsd plot create --type correlation_matrix \
    --input tasks/BC_15DS115_multisegment_horn_20251231_165015.json \
    --output test_correlation.png

# Test quality_dashboard with actual optimization results
gsd plot create --type quality_dashboard \
    --input tasks/BC_15DS115_multisegment_horn_20251231_165015.json \
    --output test_quality.png
```

### Step 4.2: Test preset integration

```bash
# Test new correlations preset
gsd plot auto \
    --input tasks/BC_15DS115_multisegment_horn_20251231_165015.json \
    --preset correlations \
    --output-dir test_plots/

# List presets to verify new one appears
gsd plot list-presets
```

### Step 4.3: Verify help text

```bash
# Verify new plot type appears in list
gsd plot list-types

# Verify new preset appears in help
gsd plot auto --help | grep correlations
gsd optimize preset --help | grep correlations
```

---

## Task 5: Documentation

### Update Plan File

Mark Phase 2 items as complete in the plan file:
`/Users/fungj/.claude/plans/smooth-sleeping-koala.md`

### Update Code Comments

Ensure all new methods have proper docstrings with:
- Description
- Literature citations
- Args/Returns documentation
- Usage examples

---

## Dependencies

The new plot types require these Python packages:

1. **pandas** - For DataFrame operations in correlation matrix
2. **seaborn** - For heatmap visualization in correlation matrix

Check if they're already installed:

```bash
# Check if pandas is available
python3 -c "import pandas; print(pandas.__version__)"

# Check if seaborn is available
python3 -c "import seaborn; print(seaborn.__version__)"
```

If not installed, add to project dependencies:
- Add to `pyproject.toml` in `dependencies` section
- Install with: `pip install pandas seaborn`

---

## Success Criteria

✅ **correlation_matrix plot type:**
- [x] Compiles without errors
- [x] Generates heatmap with parameter-objective correlations
- [x] Shows proper color scale (-1 to +1)
- [x] Has correct labels and title
- [x] Works with `plot create` command

✅ **quality_dashboard plot type:**
- [x] Compiles without errors
- [x] Generates 2x2 subplot grid
- [x] Shows all 4 panels (wavefront, impedance, slope, composite)
- [x] Has proper labels and titles
- [x] Works with `plot create` command

✅ **Presets integration:**
- [x] New `correlations` preset created
- [x] Appears in `gsd plot list-presets`
- [x] Works with `gsd plot auto --preset correlations`
- [x] Works with `gsd optimize preset --plot --plot-preset correlations`

✅ **Testing:**
- [x] All plot types tested with real data
- [x] Help text shows new options
- [x] No regression in existing functionality

---

## Troubleshooting

### Issue: "No module named 'pandas'" or "No module named 'seaborn'"

**Solution:** Install dependencies
```bash
pip install pandas seaborn
```

### Issue: KeyError when extracting objectives

**Cause:** Optimization results don't contain the expected objective names (e.g., `wavefront_sphericity`)

**Solution:**
1. Check what objectives are actually in the results:
   ```python
   import json
   with open('results.json') as f:
       data = json.load(f)
       print(data['pareto_front'][0]['objectives'].keys())
   ```
2. Adjust the plot to handle missing objectives gracefully (add NaN checks)
3. Use objectives that exist in the data

### Issue: Empty plots (no data displayed)

**Cause:** All objective values are NaN or objectives don't exist in results

**Solution:**
1. Add validation/warnings when objectives are missing
2. Show informative message in plot (e.g., "No wavefront_sphericity data available")
3. Consider making the plot type more flexible to work with available objectives

---

## Next Steps (After Phase 2)

Phase 3 is optional and includes:
1. Add `--num-spl-designs` override support
2. Add enclosure-type awareness (skip horn_profile for sealed/ported)
3. Add custom preset creation via YAML config

These can be implemented later if needed.
