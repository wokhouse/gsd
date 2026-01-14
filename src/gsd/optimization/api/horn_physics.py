"""
Horn physics calculations for two-way system integration.

These functions bridge the gap between horn geometry and crossover design,
allowing designers to work backwards from crossover targets to horn parameters.

Literature:
- Olson (1947) - Horn cutoff and flare theory
- Beranek (1954) - Directivity and radiation impedance
- Small (1972) - Enclosure alignment theory
"""

import numpy as np
from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass


def calculate_lf_beaming_frequency(driver) -> float:
    """
    Calculate the frequency where LF driver starts beaming.

    Beaming occurs when ka > 2, where k = 2πf/c and a = piston radius.
    Solving for f: f_beam = 2c/(π×d) where d is piston diameter.

    Literature:
    - Beranek (1954), Chapter 5 - Directivity of circular pistons
    - Olson (1947), Section 4.3 - Radiation impedance and directivity

    Args:
        driver: ThieleSmallParameters object with S_d attribute

    Returns:
        Beaming frequency (Hz), above which directivity increases rapidly

    Example:
        >>> from gsd.driver import load_driver
        >>> driver = load_driver("BC_12FW88")
        >>> f_beam = calculate_lf_beaming_frequency(driver)
        >>> print(f"LF driver beaming: {f_beam:.0f} Hz")
    """
    c = 343.0  # Speed of sound (m/s) at 20°C
    # S_d = π×a² (piston area), so diameter = 2×sqrt(S_d/π)
    piston_diameter = 2 * np.sqrt(driver.S_d / np.pi)
    f_beam = (2 * c) / (np.pi * piston_diameter)
    return f_beam


def calculate_target_horn_fc(
    desired_crossover_hz: float,
    lf_driver_beaming_hz: Optional[float] = None,
    xo_fc_ratio: float = 2.0
) -> float:
    """
    Calculate target horn cutoff frequency for desired crossover.

    The traditional rule is XO = 2×Fc, but optimized systems can use
    XO = 1.2-1.5×Fc if the horn has smooth response below cutoff.

    Literature:
    - Olson (1947), Section 5.6 - Horn cutoff and operating range
    - Standard practice: Horn should operate 2 octaves above cutoff

    Args:
        desired_crossover_hz: Target crossover frequency (Hz)
        lf_driver_beaming_hz: LF driver beaming frequency (Hz) - caps XO if provided
        xo_fc_ratio: Desired XO/Fc ratio (default 2.0, use 1.3 for optimized)

    Returns:
        Target horn cutoff frequency (Hz)

    Example:
        >>> # For 800Hz XO with 2×Fc rule
        >>> fc = calculate_target_horn_fc(800, xo_fc_ratio=2.0)
        >>> print(f"Target Fc: {fc:.0f} Hz")  # 400 Hz

        >>> # For 800Hz XO with optimized integration
        >>> fc = calculate_target_horn_fc(800, xo_fc_ratio=1.3)
        >>> print(f"Target Fc: {fc:.0f} Hz")  # 615 Hz
    """
    # Cap XO at LF beaming frequency if provided
    # XO should be < 0.8×beaming for flat response
    if lf_driver_beaming_hz is not None:
        xo_hz = min(desired_crossover_hz, 0.8 * lf_driver_beaming_hz)
    else:
        xo_hz = desired_crossover_hz

    return xo_hz / xo_fc_ratio


def calculate_mouth_area_for_fc(
    throat_area_cm2: float,
    length_cm: float,
    target_fc_hz: float,
    speed_of_sound: float = 343.0
) -> float:
    """
    Calculate required mouth area for target cutoff frequency.

    For exponential horn:
        Fc = (c/4π) × m
        where m = ln(mouth/throat) / L (flare constant)

    Solving for mouth:
        m = 4π × Fc / c
        ln(mouth/throat) = m × L
        mouth = throat × exp(m × L)

    Literature:
    - Olson (1947), Eq. 5.18 - Horn cutoff frequency
    - Beranek (1954), Chapter 5 - Exponential horn theory

    Args:
        throat_area_cm2: Throat area (cm²)
        length_cm: Horn length (cm)
        target_fc_hz: Target cutoff frequency (Hz)
        speed_of_sound: Speed of sound (m/s), default 343 m/s at 20°C

    Returns:
        Required mouth area (cm²)

    Example:
        >>> # Calculate mouth for 400Hz Fc, 250mm horn, 7cm² throat
        >>> mouth = calculate_mouth_area_for_fc(7.0, 25.0, 400)
        >>> print(f"Mouth: {mouth:.0f} cm²")  # ~273 cm²
    """
    L = length_cm / 100.0  # Convert to meters
    throat_m2 = throat_area_cm2 / 10000.0  # Convert to m²

    # Calculate required flare constant
    # From Olson Eq. 5.18: Fc = (c × m) / (4π), so m = (4π × Fc) / c
    m = (4 * np.pi * target_fc_hz) / speed_of_sound

    # Calculate required mouth area
    # From exponential horn definition: S(x) = S_t × exp(m × x)
    # At mouth (x=L): S_m = S_t × exp(m × L)
    mouth_m2 = throat_m2 * np.exp(m * L)

    return mouth_m2 * 10000.0  # Convert back to cm²


def calculate_fc_from_mouth(
    throat_area_cm2: float,
    mouth_area_cm2: float,
    length_cm: float,
    speed_of_sound: float = 343.0
) -> float:
    """
    Calculate horn cutoff frequency from geometry.

    Inverse of calculate_mouth_area_for_fc().

    Literature:
    - Olson (1947), Eq. 5.18 - Horn cutoff frequency
    - Beranek (1954), Chapter 5 - Exponential horn theory

    Args:
        throat_area_cm2: Throat area (cm²)
        mouth_area_cm2: Mouth area (cm²)
        length_cm: Horn length (cm)
        speed_of_sound: Speed of sound (m/s)

    Returns:
        Horn cutoff frequency (Hz)

    Example:
        >>> fc = calculate_fc_from_mouth(7.0, 250.0, 25.0)
        >>> print(f"Fc: {fc:.0f} Hz")  # ~390 Hz
    """
    L = length_cm / 100.0  # Convert to meters
    throat_m2 = throat_area_cm2 / 10000.0
    mouth_m2 = mouth_area_cm2 / 10000.0

    # Calculate flare constant
    # From exponential horn definition: S_m = S_t × exp(m × L)
    # Solving for m: m = ln(S_m/S_t) / L
    m = np.log(mouth_m2 / throat_m2) / L

    # Calculate cutoff frequency
    # From Olson Eq. 5.18: Fc = (c × m) / (4π)
    fc = (speed_of_sound * m) / (4 * np.pi)

    return fc


def assess_mouth_area_feasibility(
    required_mouth_cm2: float,
    available_mouth_cm2: float,
    target_fc_hz: float,
    throat_area_cm2: float = 7.0,
    length_cm: float = 25.0
) -> Dict[str, Any]:
    """
    Assess if required mouth area is feasible within constraints.

    Provides recommendations if constraints cannot be met.

    Args:
        required_mouth_cm2: Required mouth area for target Fc (cm²)
        available_mouth_cm2: Maximum mouth area from printer constraint (cm²)
        target_fc_hz: Target cutoff frequency (Hz)
        throat_area_cm2: Throat area (cm²), default 7.0
        length_cm: Horn length (cm), default 25.0

    Returns:
        Dict with:
        - feasible: bool
        - required_mouth_cm2: float
        - available_mouth_cm2: float
        - resulting_fc_hz: float (if not feasible)
        - fc_error_hz: float (if not feasible)
        - recommendation: str
        - sensitivity_penalty_db: float (if not feasible)

    Example:
        >>> result = assess_mouth_area_feasibility(
        ...     required_mouth_cm2=273,
        ...     available_mouth_cm2=250,
        ...     target_fc_hz=400
        ... )
        >>> if not result['feasible']:
        ...     print(result['recommendation'])
    """
    if required_mouth_cm2 <= available_mouth_cm2:
        return {
            "feasible": True,
            "target_fc_hz": target_fc_hz,
            "required_mouth_cm2": required_mouth_cm2,
            "available_mouth_cm2": available_mouth_cm2,
            "recommendation": f"Design with {required_mouth_cm2:.0f}cm² mouth (fits constraint)",
            "sensitivity_penalty_db": 0.0
        }
    else:
        # Calculate resulting Fc with max available mouth
        resulting_fc = calculate_fc_from_mouth(
            throat_area_cm2,
            available_mouth_cm2,
            length_cm
        )

        fc_error = resulting_fc - target_fc_hz

        # Estimate sensitivity penalty
        # Smaller mouth = less HF sensitivity
        # Approximation: 10×log10(available/required) dB
        # This is a rough estimate based on mouth area ratio
        sensitivity_penalty = 10 * np.log10(available_mouth_cm2 / required_mouth_cm2)

        recommendation = (
            f"Required mouth ({required_mouth_cm2:.0f}cm²) exceeds constraint ({available_mouth_cm2:.0f}cm²).\n"
            f"Options:\n"
            f"  1. Use max mouth ({available_mouth_cm2:.0f}cm²): Fc={resulting_fc:.0f}Hz "
            f"({fc_error:+.0f}Hz error, {sensitivity_penalty:+.1f}dB sensitivity loss)\n"
            f"  2. Use multi-piece horn (2× length)\n"
            f"  3. Accept higher crossover frequency"
        )

        return {
            "feasible": False,
            "target_fc_hz": target_fc_hz,
            "required_mouth_cm2": required_mouth_cm2,
            "available_mouth_cm2": available_mouth_cm2,
            "resulting_fc_hz": resulting_fc,
            "fc_error_hz": fc_error,
            "sensitivity_penalty_db": sensitivity_penalty,
            "recommendation": recommendation
        }


@dataclass
class HornFeasibilityResult:
    """
    Result of horn feasibility assessment.

    Attributes:
        feasible: Whether design is feasible within constraints
        target_fc_hz: Target cutoff frequency (Hz)
        required_mouth_cm2: Required mouth area (cm²)
        available_mouth_cm2: Available mouth area (cm²)
        resulting_fc_hz: Actual Fc if using available mouth (Hz)
        sensitivity_penalty_db: Sensitivity loss if using smaller mouth (dB)
        recommendation: Text recommendation
    """
    feasible: bool
    target_fc_hz: float
    required_mouth_cm2: float
    available_mouth_cm2: float
    resulting_fc_hz: Optional[float] = None
    sensitivity_penalty_db: float = 0.0
    recommendation: str = ""

    def __str__(self) -> str:
        """Return formatted result."""
        lines = [
            "Horn Feasibility Assessment",
            "=" * 70,
            f"Target Fc: {self.target_fc_hz:.0f} Hz",
            f"Required mouth: {self.required_mouth_cm2:.0f} cm²",
            f"Available mouth: {self.available_mouth_cm2:.0f} cm²",
        ]

        if self.feasible:
            lines.append(f"\n✓ FEASIBLE: Design with {self.required_mouth_cm2:.0f}cm² mouth")
        else:
            lines.extend([
                f"\n✗ NOT FEASIBLE within constraints",
                f"Resulting Fc: {self.resulting_fc_hz:.0f} Hz (error: {self.resulting_fc_hz - self.target_fc_hz:+.0f} Hz)",
                f"Sensitivity penalty: {self.sensitivity_penalty_db:+.1f} dB",
                f"\nRecommendation:",
                f"{self.recommendation}"
            ])

        return "\n".join(lines)
