"""
Design validation for two-way loudspeaker systems.

This module provides validation functions that check two-way designs
against best practices and acoustic principles.

Literature:
    - Small (1972) - Enclosure design criteria
    - D'Appolito (1984) - Crossover design guidelines
    - literature/thiele_small/small_1972_closed_box.md
    - literature/thiele_small/d_appolito_1984.md
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import numpy as np


# Validation criteria constants
# Horn cutoff should be ≤ 0.5 × crossover for clean integration
# Based on D'Appolito (1984) crossover design guidelines
MAX_HORN_CUTOFF_RATIO = 0.5
CRITICAL_HORN_CUTOFF_RATIO = 0.8

# Acceptable passband variation (dB)
# From Beranek (1954), Chapter 8 - Bandwidth definitions
MAX_FLATNESS_DB = 6.0

# Acceptable sensitivity mismatch after padding (dB)
# From loudspeaker system design best practices
MAX_SENSITIVITY_MISMATCH_DB = 6.0


@dataclass
class DesignValidation:
    """Validation results for two-way system design."""
    passes: bool
    warnings: List[str]
    recommendations: List[str]
    scores: Dict[str, float]

    def __str__(self) -> str:
        lines = [
            f"Validation: {'✓ PASS' if self.passes else '✗ FAIL'}",
            f"\nWarnings ({len(self.warnings)}):"
        ]
        for w in self.warnings:
            lines.append(f"  ⚠ {w}")

        if self.recommendations:
            lines.append(f"\nRecommendations:")
            for r in self.recommendations:
                lines.append(f"  → {r}")

        if self.scores:
            lines.append(f"\nScores:")
            for key, val in self.scores.items():
                status = "✓" if val > 0.7 else "⚠" if val > 0.5 else "✗"
                lines.append(f"  {key}: {val:.2f} {status}")

        return "\n".join(lines)


def validate_two_way_design(design, verbose: bool = True) -> DesignValidation:
    """
    Validate two-way system design against best practices.

    Checks:
    1. Horn cutoff vs crossover frequency
    2. System F3 within expected range
    3. Passband flatness
    4. Crossover within driver capabilities
    5. Sensitivity matching

    Literature:
    - Small (1972) - Enclosure design criteria
    - D'Appolito (1984) - Crossover design guidelines

    Args:
        design: TwoWaySystemDesign instance
        verbose: Print validation messages

    Returns:
        DesignValidation with assessment

    Raises:
        ValueError: If required design attributes are missing
    """
    from gsd.driver import load_driver

    # Validate required attributes
    required_attrs = ['lf_driver_name', 'hf_driver_name', 'crossover_frequency']
    missing = [attr for attr in required_attrs if not hasattr(design, attr)]
    if missing:
        raise ValueError(
            f"Design missing required attributes: {missing}. "
            f"Cannot validate incomplete design."
        )

    warnings = []
    recommendations = []
    scores = {}

    # Check 1: Horn cutoff vs crossover
    # Horn cutoff should be ≤ 0.5 × crossover frequency for clean integration
    if hasattr(design, 'horn_params') and design.horn_params:
        horn_fc = design.horn_params.get('cutoff', 0)
        xo_freq = design.crossover_frequency

        if horn_fc > 0:
            ratio = horn_fc / xo_freq
            scores['horn_cutoff_ratio'] = min(1.0, MAX_HORN_CUTOFF_RATIO / ratio) if ratio > 0 else 0

            if horn_fc > xo_freq * MAX_HORN_CUTOFF_RATIO:
                warnings.append(
                    f"Horn cutoff ({horn_fc:.0f} Hz) > {MAX_HORN_CUTOFF_RATIO} × crossover ({xo_freq:.0f} Hz)"
                )

                if horn_fc > xo_freq * CRITICAL_HORN_CUTOFF_RATIO:
                    recommendations.append("CRITICAL: Horn cutoff too close to crossover!")
                    recommendations.append("  Options: (a) Raise crossover to 1.5-2 kHz")
                    recommendations.append("         (b) Use multi-piece horn for lower cutoff")
                    recommendations.append("         (c) Consider sealed box for LF (higher F3, simpler)")

    # Check 2: System F3
    if hasattr(design, 'f3'):
        f3 = design.f3
        scores['f3_score'] = 1.0 if f3 < 60 else 0.8 if f3 < 80 else 0.5

        if f3 > 100:
            warnings.append(f"System F3 ({f3:.1f} Hz) > 100 Hz - weak bass")
        elif f3 < 30:
            recommendations.append("F3 very low - verify subwoofer not needed")

    # Check 3: Flatness
    if hasattr(design, 'flatness'):
        flatness = design.flatness
        scores['flatness_score'] = max(0, 1.0 - flatness / MAX_FLATNESS_DB)

        if flatness > MAX_FLATNESS_DB:
            warnings.append(f"Flatness {flatness:.2f} dB > {MAX_FLATNESS_DB} dB - poor response")
        elif flatness > 3:
            recommendations.append(f"Flatness {flatness:.2f} dB - consider EQ or XO adjustment")

    # Check 4: Crossover frequency vs driver capabilities
    xo_freq = design.crossover_frequency
    try:
        lf_driver = load_driver(design.lf_driver_name)

        # LF driver: 12" woofers typically good to 1-1.5 kHz
        if lf_driver.S_d > 0.05:  # Large woofer
            if xo_freq > 1500:
                warnings.append(f"Crossover ({xo_freq:.0f} Hz) high for {design.lf_driver_name}")
                scores['xo_frequency_score'] = 0.5
            elif xo_freq > 1200:
                recommendations.append("Monitor for beaming at crossover")
                scores['xo_frequency_score'] = 0.7
            else:
                scores['xo_frequency_score'] = 1.0
        else:
            scores['xo_frequency_score'] = 1.0  # Smaller woofers OK higher
    except Exception:
        # Driver not found, skip this check
        pass

    # Check 5: Sensitivity matching
    if hasattr(design, 'lf_sensitivity') and hasattr(design, 'hf_sensitivity'):
        lf_sens = design.lf_sensitivity
        hf_sens = design.hf_sensitivity
        padding = design.hf_padding_db

        # After padding, should be within 3 dB
        matched_sensitivity = hf_sens + padding
        diff = abs(matched_sensitivity - lf_sens)

        scores['sensitivity_match'] = max(0, 1.0 - diff / 10.0)

        if diff > MAX_SENSITIVITY_MISMATCH_DB:
            warnings.append(f"Sensitivity mismatch {diff:.1f} dB after padding")
            recommendations.append("Adjust HF/LF padding or consider different crossover")

    # Overall score
    if scores:
        overall = np.mean(list(scores.values()))
        scores['overall'] = overall

    # Final assessment
    passes = len(warnings) == 0 and (not scores or scores.get('overall', 1.0) > 0.5)

    if verbose:
        print("\n" + "=" * 70)
        print("DESIGN VALIDATION")
        print("=" * 70)

    return DesignValidation(
        passes=passes,
        warnings=warnings,
        recommendations=recommendations,
        scores=scores
    )
