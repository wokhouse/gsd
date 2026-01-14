"""
Trade-off analysis and visualization for two-way system design.

This module provides tools for analyzing and visualizing the trade-offs
between mouth area, horn cutoff frequency, HF sensitivity, and crossover
integration quality.

Literature:
- Olson (1947), Eq. 5.18 - Horn cutoff frequency
- Beranek (1954), Chapter 5 - Exponential horn theory
- Case study: docs/two_way_design_review_12fw88_dh450.md
"""

import numpy as np
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import warnings

from gsd.driver import load_driver
from gsd.optimization.api.horn_physics import (
    calculate_fc_from_mouth,
    calculate_mouth_area_for_fc
)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MouthFcTradeOff:
    """
    Result of mouth area vs Fc trade-off analysis.

    Attributes:
        mouth_areas_cm2: Array of mouth areas tested (cm²)
        fc_hz: Array of cutoff frequencies (Hz)
        sensitivity_penalties_db: Array of sensitivity penalties (dB)
        recommended_xo_ranges: List of (min_xo, max_xo) tuples for each mouth
        best_mouth_cm2: Recommended mouth area (cm²)
        best_fc_hz: Recommended cutoff frequency (Hz)
        analysis: Text explanation of results
    """
    mouth_areas_cm2: np.ndarray
    fc_hz: np.ndarray
    sensitivity_penalties_db: np.ndarray
    recommended_xo_ranges: list
    best_mouth_cm2: float
    best_fc_hz: float
    analysis: str


@dataclass
class SensitivityCurveData:
    """
    Result of mouth-sensitivity curve analysis.

    Attributes:
        mouth_areas_cm2: Array of mouth areas (cm²)
        fc_values_hz: Array of cutoff frequencies (Hz)
        sensitivity_penalties_db: Array of sensitivity penalties (dB)
        crossover_options_hz: Array of optimal crossover frequencies (Hz)
        dip_predictions_db: Array of predicted crossover dips (dB)
        recommendation: Text recommendation
    """
    mouth_areas_cm2: np.ndarray
    fc_values_hz: np.ndarray
    sensitivity_penalties_db: np.ndarray
    crossover_options_hz: np.ndarray
    dip_predictions_db: np.ndarray
    recommendation: str


# =============================================================================
# TRADE-OFF ANALYSIS FUNCTIONS
# =============================================================================

def analyze_mouth_vs_fc_tradeoff(
    lf_driver_name: str,
    hf_driver_name: str,
    horn_length_cm: float,
    mouth_areas_cm2: np.ndarray,
    target_xo_hz: float,
    throat_area_cm2: float = 7.0
) -> MouthFcTradeOff:
    """
    Analyze trade-off between mouth area and horn Fc.

    Generates data showing how mouth area affects:
    - Horn cutoff frequency
    - HF sensitivity penalty
    - Recommended crossover range

    Literature:
    - Olson (1947), Eq. 5.18 - Horn cutoff vs mouth area
    - Fc = (c/4π) × (1/L) × ln(mouth/throat)

    Args:
        lf_driver_name: Low-frequency driver name
        hf_driver_name: High-frequency driver name
        horn_length_cm: Horn length (cm)
        mouth_areas_cm2: Array of mouth areas to test (cm²)
        target_xo_hz: Target crossover frequency (Hz)
        throat_area_cm2: Throat area (cm²), default 7.0

    Returns:
        MouthFcTradeOff with analysis results

    Example:
        >>> import numpy as np
        >>> mouths = np.linspace(200, 600, 9)
        >>> result = analyze_mouth_vs_fc_tradeoff(
        ...     "BC_12FW88", "BC_DH450",
        ...     horn_length_cm=25.0,
        ...     mouth_areas_cm2=mouths,
        ...     target_xo_hz=800
        ... )
        >>> print(result.analysis)
    """
    from gsd.optimization.api.horn_physics import calculate_lf_beaming_frequency

    # Load LF driver for beaming calculation
    lf_driver = load_driver(lf_driver_name)
    f_beam = calculate_lf_beaming_frequency(lf_driver)

    # Calculate Fc for each mouth area
    fc_values = np.array([
        calculate_fc_from_mouth(throat_area_cm2, mouth, horn_length_cm)
        for mouth in mouth_areas_cm2
    ])

    # Calculate sensitivity penalty relative to maximum mouth
    max_mouth = np.max(mouth_areas_cm2)
    sensitivity_penalties = 10 * np.log10(mouth_areas_cm2 / max_mouth)

    # Calculate recommended XO range for each mouth
    # XO should be: 1.2×Fc to min(2×Fc, 0.8×f_beam)
    recommended_xo_ranges = []
    for fc in fc_values:
        xo_min = int(fc * 1.2)
        xo_max = int(min(fc * 2.0, 0.8 * f_beam))
        recommended_xo_ranges.append((xo_min, xo_max))

    # Find best mouth: one that allows target XO within recommended range
    best_mouth_idx = 0
    best_mouth_score = np.inf

    for i, (mouth, fc) in enumerate(zip(mouth_areas_cm2, fc_values)):
        xo_min, xo_max = recommended_xo_ranges[i]

        # Check if target XO is in range
        if xo_min <= target_xo_hz <= xo_max:
            # In range - score by how close to center of range
            range_center = (xo_min + xo_max) / 2
            score = abs(target_xo_hz - range_center)
            if score < best_mouth_score:
                best_mouth_score = score
                best_mouth_idx = i

    # If none in range, pick closest
    if best_mouth_score == np.inf:
        for i, (mouth, fc) in enumerate(zip(mouth_areas_cm2, fc_values)):
            xo_min, xo_max = recommended_xo_ranges[i]

            # Score by distance to range
            if target_xo_hz < xo_min:
                score = xo_min - target_xo_hz
            elif target_xo_hz > xo_max:
                score = target_xo_hz - xo_max
            else:
                score = 0

            if score < best_mouth_score:
                best_mouth_score = score
                best_mouth_idx = i

    best_mouth = mouth_areas_cm2[best_mouth_idx]
    best_fc = fc_values[best_mouth_idx]

    # Build analysis text
    analysis_lines = [
        f"Mouth Area vs Fc Trade-off Analysis",
        f"=" * 70,
        f"",
        f"Drivers: {lf_driver_name} + {hf_driver_name}",
        f"Horn length: {horn_length_cm:.0f} cm",
        f"Target XO: {target_xo_hz:.0f} Hz",
        f"LF beaming: {f_beam:.0f} Hz",
        f"",
        f"Results Summary:",
        f"  • Best mouth: {best_mouth:.0f} cm² → Fc = {best_fc:.0f} Hz",
        f"  • Sensitivity penalty: {sensitivity_penalties[best_mouth_idx]:+.1f} dB",
        f"",
        f"Mouth Area → Fc → XO Range:",
    ]

    for i, (mouth, fc, penalty) in enumerate(zip(
        mouth_areas_cm2, fc_values, sensitivity_penalties
    )):
        xo_min, xo_max = recommended_xo_ranges[i]
        marker = " ← BEST" if i == best_mouth_idx else ""
        in_range = " ✓" if xo_min <= target_xo_hz <= xo_max else " ✗"
        analysis_lines.append(
            f"  {mouth:6.0f} cm² → Fc {fc:4.0f} Hz → XO {xo_min:4.0f}-{xo_max:4.0f} Hz{in_range}{marker}"
        )

    analysis = "\n".join(analysis_lines)

    return MouthFcTradeOff(
        mouth_areas_cm2=mouth_areas_cm2,
        fc_hz=fc_values,
        sensitivity_penalties_db=sensitivity_penalties,
        recommended_xo_ranges=recommended_xo_ranges,
        best_mouth_cm2=best_mouth,
        best_fc_hz=best_fc,
        analysis=analysis
    )


def predict_crossover_dip(
    xo_freq_hz: float,
    horn_fc_hz: float,
    lf_beaming_hz: float
) -> float:
    """
    Predict crossover dip based on system parameters.

    This is an empirical model based on the BC 12FW88 + DH450 case study.
    Dip is worst when XO is too close to Fc or too close to beaming.

    Literature:
    - Empirical model from case study analysis
    - docs/two_way_design_review_12fw88_dh450.md

    Args:
        xo_freq_hz: Crossover frequency (Hz)
        horn_fc_hz: Horn cutoff frequency (Hz)
        lf_beaming_hz: LF driver beaming frequency (Hz)

    Returns:
        Predicted dip in dB

    Example:
        >>> dip = predict_crossover_dip(600, 468, 840)
        >>> print(f"Predicted dip: {dip:.2f} dB")
    """
    # Calculate XO/Fc ratio
    xo_fc_ratio = xo_freq_hz / horn_fc_hz

    # Calculate XO vs beaming
    xo_vs_beaming = xo_freq_hz / lf_beaming_hz

    # Model: dip is minimal when:
    # 1. XO/Fc is in optimal range (1.2-2.0)
    # 2. XO is well below beaming (< 0.8)

    # Penalty for XO too close to Fc
    if xo_fc_ratio < 1.2:
        fc_penalty = 10 * (1.2 - xo_fc_ratio)  # Up to 10 dB penalty
    elif xo_fc_ratio > 2.0:
        fc_penalty = 2 * (xo_fc_ratio - 2.0)  # Smaller penalty for high ratio
    else:
        fc_penalty = 0

    # Penalty for XO too close to beaming
    if xo_vs_beaming > 0.8:
        beaming_penalty = 15 * (xo_vs_beaming - 0.8)  # Up to 15 dB penalty
    else:
        beaming_penalty = 0

    # Base dip (ideal case)
    base_dip = 2.0  # Even ideal systems have some dip

    # Total dip
    dip = base_dip + fc_penalty + beaming_penalty

    # Cap at reasonable values
    dip = max(1.5, min(dip, 15.0))

    return dip


def analyze_mouth_sensitivity_curve(
    lf_driver_name: str,
    hf_driver_name: str,
    horn_length_cm: float,
    target_xo_hz: float,
    mouth_range_cm2: Tuple[float, float] = (200, 600),
    num_points: int = 9,
    throat_area_cm2: float = 7.0
) -> SensitivityCurveData:
    """
    Analyze mouth-sensitivity trade-off curve.

    Shows how smaller mouth affects:
    - Horn Fc (lower)
    - HF sensitivity (reduced)
    - Crossover integration (improved)
    - Predicted dip

    Literature:
    - Olson (1947) - Horn cutoff vs mouth area
    - Empirical dip prediction model

    Args:
        lf_driver_name: Low-frequency driver name
        hf_driver_name: High-frequency driver name
        horn_length_cm: Horn length (cm)
        target_xo_hz: Target crossover frequency (Hz)
        mouth_range_cm2: (min, max) mouth area range (cm²)
        num_points: Number of points to analyze
        throat_area_cm2: Throat area (cm²), default 7.0

    Returns:
        SensitivityCurveData with analysis results

    Example:
        >>> result = analyze_mouth_sensitivity_curve(
        ...     "BC_12FW88", "BC_DH450",
        ...     horn_length_cm=25.0,
        ...     target_xo_hz=800
        ... )
        >>> print(result.recommendation)
    """
    from gsd.optimization.api.horn_physics import calculate_lf_beaming_frequency

    # Generate mouth area range
    mouth_areas = np.linspace(mouth_range_cm2[0], mouth_range_cm2[1], num_points)

    # Load LF driver
    lf_driver = load_driver(lf_driver_name)
    f_beam = calculate_lf_beaming_frequency(lf_driver)

    # Calculate values for each mouth
    fc_values = np.array([
        calculate_fc_from_mouth(throat_area_cm2, mouth, horn_length_cm)
        for mouth in mouth_areas
    ])

    # Sensitivity penalty (relative to max mouth)
    max_mouth = np.max(mouth_areas)
    sensitivity_penalties = 10 * np.log10(mouth_areas / max_mouth)

    # Optimal XO for each mouth (use target XO if in range, else nearest)
    optimal_xo = []
    for fc in fc_values:
        xo_min = fc * 1.2
        xo_max = min(fc * 2.0, 0.8 * f_beam)

        if xo_min <= target_xo_hz <= xo_max:
            optimal_xo.append(target_xo_hz)
        elif target_xo_hz < xo_min:
            optimal_xo.append(xo_min)
        else:
            optimal_xo.append(xo_max)

    optimal_xo = np.array(optimal_xo)

    # Predict dip for each configuration
    dip_predictions = np.array([
        predict_crossover_dip(xo, fc, f_beam)
        for xo, fc in zip(optimal_xo, fc_values)
    ])

    # Find best configuration (minimum dip)
    best_idx = np.argmin(dip_predictions)
    best_mouth = mouth_areas[best_idx]
    best_fc = fc_values[best_idx]
    best_dip = dip_predictions[best_idx]
    best_sensitivity = sensitivity_penalties[best_idx]

    # Build recommendation
    rec_lines = [
        f"Mouth-Sensitivity Trade-off Analysis",
        f"=" * 70,
        f"",
        f"Target: XO = {target_xo_hz:.0f} Hz",
        f"Horn: L = {horn_length_cm:.0f} cm, throat = {throat_area_cm2:.0f} cm²",
        f"",
        f"Optimal Configuration:",
        f"  • Mouth: {best_mouth:.0f} cm²",
        f"  • Horn Fc: {best_fc:.0f} Hz",
        f"  • XO/Fc ratio: {optimal_xo[best_idx]/best_fc:.2f}",
        f"  • Predicted dip: {best_dip:.2f} dB",
        f"  • Sensitivity penalty: {best_sensitivity:+.1f} dB",
        f"",
        f"Trade-off Summary:",
    ]

    if best_dip < 2.5:
        rating = "✅ Excellent"
    elif best_dip < 4:
        rating = "⚠️ Acceptable"
    else:
        rating = "❌ Poor"

    rec_lines.append(f"  Rating: {rating}")

    if best_sensitivity < -3:
        rec_lines.append(f"  • Significant sensitivity loss ({best_sensitivity:+.1f} dB)")
        rec_lines.append(f"  • Best crossover integration possible")
    elif best_sensitivity < -1:
        rec_lines.append(f"  • Moderate sensitivity loss ({best_sensitivity:+.1f} dB)")
        rec_lines.append(f"  • Good crossover integration")
    else:
        rec_lines.append(f"  • Minimal sensitivity loss ({best_sensitivity:+.1f} dB)")
        rec_lines.append(f"  • Crossover integration may be compromised")

    # Add specific recommendations
    if best_dip > 4:
        rec_lines.append(f"")
        rec_lines.append(f"  ⚠️ WARNING: Predicted dip is large ({best_dip:.2f} dB)")
        rec_lines.append(f"  Recommendations:")
        rec_lines.append(f"    • Consider multi-piece horn for larger mouth")
        rec_lines.append(f"    • Or accept higher crossover frequency")
        rec_lines.append(f"    • Or consider different driver combination")

    recommendation = "\n".join(rec_lines)

    return SensitivityCurveData(
        mouth_areas_cm2=mouth_areas,
        fc_values_hz=fc_values,
        sensitivity_penalties_db=sensitivity_penalties,
        crossover_options_hz=optimal_xo,
        dip_predictions_db=dip_predictions,
        recommendation=recommendation
    )


def plot_mouth_sensitivity_curve(
    lf_driver_name: str,
    hf_driver_name: str,
    horn_length_cm: float,
    target_xo_hz: float,
    save_path: str = "mouth_sensitivity_tradeoff.png",
    mouth_range_cm2: Tuple[float, float] = (200, 600),
    num_points: int = 9,
    throat_area_cm2: float = 7.0
) -> None:
    """
    Plot HF sensitivity penalty vs mouth area.

    Shows how smaller mouth affects:
    - Horn Fc (lower)
    - HF sensitivity (reduced)
    - Crossover integration (improved)

    Creates a PNG file with two subplots:
    - Top: Fc vs mouth area
    - Bottom: Sensitivity penalty vs mouth area

    Args:
        lf_driver_name: Low-frequency driver name
        hf_driver_name: High-frequency driver name
        horn_length_cm: Horn length (cm)
        target_xo_hz: Target crossover frequency (Hz)
        save_path: Output file path for PNG
        mouth_range_cm2: (min, max) mouth area range (cm²)
        num_points: Number of points to analyze
        throat_area_cm2: Throat area (cm²), default 7.0

    Raises:
        ImportError: If matplotlib is not installed

    Example:
        >>> plot_mouth_sensitivity_curve(
        ...     "BC_12FW88", "BC_DH450",
        ...     horn_length_cm=25.0,
        ...     target_xo_hz=800,
        ...     save_path="analysis.png"
        ... )
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        raise ImportError(
            "matplotlib is required for plotting. "
            "Install with: pip install matplotlib"
        )

    # Analyze trade-off
    data = analyze_mouth_sensitivity_curve(
        lf_driver_name,
        hf_driver_name,
        horn_length_cm,
        target_xo_hz,
        mouth_range_cm2,
        num_points,
        throat_area_cm2
    )

    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

    # Plot 1: Fc vs mouth area
    ax1.plot(data.mouth_areas_cm2, data.fc_values_hz, 'bo-', linewidth=2, markersize=8)
    ax1.axhline(y=target_xo_hz/2, color='r', linestyle='--', label=f'Target Fc (2×XO rule): {target_xo_hz/2:.0f} Hz')
    ax1.axhline(y=target_xo_hz/1.3, color='orange', linestyle='--', label=f'Optimized Fc (1.3×XO): {target_xo_hz/1.3:.0f} Hz')
    ax1.set_xlabel('Mouth Area (cm²)', fontsize=12)
    ax1.set_ylabel('Horn Cutoff Frequency (Hz)', fontsize=12)
    ax1.set_title(f'Horn Fc vs Mouth Area (L={horn_length_cm:.0f}cm)', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='best')

    # Plot 2: Sensitivity penalty and dip vs mouth area
    ax2_twin = ax2.twinx()  # Second y-axis for dip

    line1 = ax2.plot(data.mouth_areas_cm2, data.sensitivity_penalties_db, 'ro-', linewidth=2, markersize=8, label='Sensitivity Penalty')
    line2 = ax2_twin.plot(data.mouth_areas_cm2, data.dip_predictions_db, 'bs-', linewidth=2, markersize=8, label='Predicted Dip')

    ax2.set_xlabel('Mouth Area (cm²)', fontsize=12)
    ax2.set_ylabel('Sensitivity Penalty (dB)', fontsize=12, color='r')
    ax2_twin.set_ylabel('Predicted Crossover Dip (dB)', fontsize=12, color='b')
    ax2.set_title(f'Sensitivity vs Integration Quality (Target XO: {target_xo_hz:.0f} Hz)', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)

    # Color tick labels
    ax2.tick_params(axis='y', labelcolor='r')
    ax2_twin.tick_params(axis='y', labelcolor='b')

    # Combine legends
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax2.legend(lines, labels, loc='best')

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"  ✓ Plot saved to: {save_path}")

    # Also print recommendation
    print(f"\n{data.recommendation}")


def generate_trade_off_report(
    lf_driver_name: str,
    hf_driver_name: str,
    target_xo_hz: float,
    printer_constraints: Dict[str, float],
    output_path: str = "trade_off_report.txt",
    horn_length_cm: float = 25.0,
    throat_area_cm2: float = 7.0
) -> None:
    """
    Generate comprehensive trade-off report with design options.

    Report sections:
    1. Driver summary (LF + HF)
    2. Printer constraints
    3. Target crossover analysis
    4. Horn options table (mouth, Fc, sensitivity, XO range)
    5. Trade-off analysis
    6. Recommendation

    Args:
        lf_driver_name: Low-frequency driver name
        hf_driver_name: High-frequency driver name
        target_xo_hz: Target crossover frequency (Hz)
        printer_constraints: {"max_length": m, "max_mouth_area": m²}
        output_path: Output file path for report
        horn_length_cm: Horn length (cm), default 25.0
        throat_area_cm2: Throat area (cm²), default 7.0

    Example:
        >>> generate_trade_off_report(
        ...     "BC_12FW88", "BC_DH450",
        ...     target_xo_hz=800,
        ...     printer_constraints={"max_length": 0.25, "max_mouth_area": 0.0625},
        ...     output_path="report.txt"
        ... )
    """
    from gsd.optimization.api.horn_physics import (
        calculate_lf_beaming_frequency,
        calculate_target_horn_fc,
        calculate_mouth_area_for_fc,
        assess_mouth_area_feasibility
    )

    # Load drivers
    lf_driver = load_driver(lf_driver_name)
    hf_driver = load_driver(hf_driver_name)

    # Calculate parameters
    f_beam = calculate_lf_beaming_frequency(lf_driver)

    # Target Fc options
    target_fc_traditional = calculate_target_horn_fc(target_xo_hz, f_beam, 2.0)
    target_fc_optimized = calculate_target_horn_fc(target_xo_hz, f_beam, 1.3)

    # Required mouth areas
    max_length = printer_constraints["max_length"]
    max_mouth = printer_constraints["max_mouth_area"] * 10000  # to cm²

    required_mouth_traditional = calculate_mouth_area_for_fc(
        throat_area_cm2,
        max_length * 100,
        target_fc_traditional
    )

    required_mouth_optimized = calculate_mouth_area_for_fc(
        throat_area_cm2,
        max_length * 100,
        target_fc_optimized
    )

    # Check feasibility
    feasibility_traditional = assess_mouth_area_feasibility(
        required_mouth_traditional,
        max_mouth,
        target_fc_traditional,
        throat_area_cm2,
        max_length * 100
    )

    feasibility_optimized = assess_mouth_area_feasibility(
        required_mouth_optimized,
        max_mouth,
        target_fc_optimized,
        throat_area_cm2,
        max_length * 100
    )

    # Analyze mouth-sensitivity curve
    curve_data = analyze_mouth_sensitivity_curve(
        lf_driver_name,
        hf_driver_name,
        max_length * 100,
        target_xo_hz,
        throat_area_cm2=throat_area_cm2
    )

    # Build report
    report_lines = [
        "=" * 70,
        "TWO-WAY SYSTEM TRADE-OFF ANALYSIS REPORT",
        "=" * 70,
        "",
        f"Generated by: GSD Two-Way Design Tool",
        f"Drivers: {lf_driver_name} + {hf_driver_name}",
        "",
        "-" * 70,
        "1. DRIVER SUMMARY",
        "-" * 70,
        "",
        f"LF Driver: {lf_driver_name}",
        f"  • Cone area (Sd): {lf_driver.S_d*10000:.1f} cm²",
        f"  • Resonance (Fs): {lf_driver.F_s:.1f} Hz",
        f"  • Beaming frequency: {f_beam:.0f} Hz",
        f"  • Max recommended XO: {0.8*f_beam:.0f} Hz",
        "",
        f"HF Driver: {hf_driver_name}",
        f"  • Throat area: {throat_area_cm2:.1f} cm²",
        f"  • Resonance (Fs): {hf_driver.F_s:.0f} Hz",
        "",
        "-" * 70,
        "2. PRINTER CONSTRAINTS",
        "-" * 70,
        "",
        f"  Max horn length: {max_length*100:.0f} cm ({max_length*3.28:.1f} inches)",
        f"  Max mouth area: {max_mouth:.0f} cm² ({max_mouth/100:.2f} m²)",
        f"  Max mouth size: {np.sqrt(max_mouth):.0f} × {np.sqrt(max_mouth):.0f} cm",
        "",
        "-" * 70,
        "3. TARGET CROSSOVER ANALYSIS",
        "-" * 70,
        "",
        f"Target XO: {target_xo_hz:.0f} Hz",
        f"LF beaming: {f_beam:.0f} Hz",
        f"XO vs beaming: {target_xo_hz/f_beam:.2f} (target XO / beaming)",
        "",
        f"Target Fc options:",
        f"  • Traditional (2×Fc rule): {target_fc_traditional:.0f} Hz",
        f"  • Optimized (1.3×Fc): {target_fc_optimized:.0f} Hz",
        "",
        "-" * 70,
        "4. HORN OPTIONS",
        "-" * 70,
        "",
    ]

    # Option 1: Traditional
    report_lines.extend([
        f"Option 1: Traditional 2×Fc Rule",
        f"  Target Fc: {target_fc_traditional:.0f} Hz",
        f"  Required mouth: {required_mouth_traditional:.0f} cm²",
        f"  Available mouth: {max_mouth:.0f} cm²",
    ])

    if feasibility_traditional['feasible']:
        report_lines.extend([
            f"  Status: ✅ FEASIBLE",
            f"  Sensitivity: Nominal (0 dB penalty)",
            f"  XO range: {target_fc_traditional*2:.0f}-{min(target_fc_traditional*2.5, 0.8*f_beam):.0f} Hz",
        ])
    else:
        report_lines.extend([
            f"  Status: ❌ NOT FEASIBLE",
            f"  Resulting Fc: {feasibility_traditional['resulting_fc_hz']:.0f} Hz",
            f"  Sensitivity penalty: {feasibility_traditional['sensitivity_penalty_db']:+.1f} dB",
            f"  XO range: {feasibility_traditional['resulting_fc_hz']*2:.0f}-{min(feasibility_traditional['resulting_fc_hz']*2.5, 0.8*f_beam):.0f} Hz",
        ])

    # Option 2: Optimized
    report_lines.extend([
        "",
        f"Option 2: Optimized (1.2-1.5×Fc range)",
        f"  Target Fc: {target_fc_optimized:.0f} Hz",
        f"  Required mouth: {required_mouth_optimized:.0f} cm²",
        f"  Available mouth: {max_mouth:.0f} cm²",
    ])

    if feasibility_optimized['feasible']:
        report_lines.extend([
            f"  Status: ✅ FEASIBLE",
            f"  Sensitivity: Nominal (0 dB penalty)",
            f"  XO range: {target_fc_optimized*1.2:.0f}-{min(target_fc_optimized*2.0, 0.8*f_beam):.0f} Hz",
        ])
    else:
        report_lines.extend([
            f"  Status: ❌ NOT FEASIBLE",
            f"  Resulting Fc: {feasibility_optimized['resulting_fc_hz']:.0f} Hz",
            f"  Sensitivity penalty: {feasibility_optimized['sensitivity_penalty_db']:+.1f} dB",
            f"  XO range: {feasibility_optimized['resulting_fc_hz']*1.2:.0f}-{min(feasibility_optimized['resulting_fc_hz']*2.0, 0.8*f_beam):.0f} Hz",
        ])

    # Trade-off analysis
    report_lines.extend([
        "",
        "-" * 70,
        "5. TRADE-OFF ANALYSIS",
        "-" * 70,
        "",
        "Mouth Area → Fc → Sensitivity → Integration:",
        "",
    ])

    for mouth, fc, penalty, dip in zip(
        curve_data.mouth_areas_cm2[::2],  # Every other point
        curve_data.fc_values_hz[::2],
        curve_data.sensitivity_penalties_db[::2],
        curve_data.dip_predictions_db[::2]
    ):
        report_lines.append(
            f"  {mouth:5.0f} cm² → Fc {fc:4.0f} Hz → {penalty:+.1f} dB → Dip {dip:4.1f} dB"
        )

    # Recommendation
    report_lines.extend([
        "",
        "-" * 70,
        "6. RECOMMENDATION",
        "-" * 70,
        "",
        curve_data.recommendation,
        "",
        "Next Steps:",
        "  1. Review trade-offs above",
        "  2. Decide: prioritize sensitivity or integration?",
        "  3. Run design_two_way_system_integrated() with chosen parameters",
        "  4. Validate against Hornresp",
        "",
        "=" * 70,
    ])

    # Write report
    with open(output_path, 'w') as f:
        f.write("\n".join(report_lines))

    print(f"  ✓ Report saved to: {output_path}")
