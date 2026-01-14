"""
Manufacturing and 3D printing utilities for horn design.

This module provides functions for assessing whether horn designs fit
within 3D printer constraints and suggesting multi-piece printing strategies.

Literature:
    - Olson (1947) - Exponential horn theory, Eq. 5.18
    - Practical guide to multi-piece horn printing
"""

import numpy as np
from typing import Dict
from gsd.driver.parameters import ThieleSmallParameters


# Constants for design assessment
# Speed of sound at 20°C, 1 atm (m/s)
# From Kinsler et al. (1982), Chapter 1
SPEED_OF_SOUND = 343.0

# Safety margin for printer fit: design must be 95% of max length
# This accounts for tolerances in 3D printing and assembly
PRINTER_FIT_TOLERANCE = 0.95

# Throat area estimate for compression drivers
# Typical throat is ~30% of diaphragm area for 1" drivers
# This is a rule of thumb - actual value depends on driver design
THROAT_AREA_RATIO = 0.3


def suggest_printing_strategy(
    driver: ThieleSmallParameters,
    target_cutoff: float,
    printer_max_length: float,
    target_mouth_area: float = None
) -> Dict:
    """
    Analyze if horn design fits printer and suggest strategy.

    Uses Olson (1947) horn theory to estimate required length for target cutoff.

    Literature:
    - Olson (1947) - Exponential horn theory, Eq. 5.18
    - Practical guide to multi-piece horn printing

    Args:
        driver: Compression driver parameters
        target_cutoff: Desired horn cutoff frequency (Hz)
        printer_max_length: Maximum printable length (m)
        target_mouth_area: Optional desired mouth area (m²)

    Returns:
        {
            "fits_single_piece": bool,
            "num_sections_required": int,
            "estimated_length": float,
            "strategy": "single" | "multi_piece" | "redesign_needed",
            "message": str,
            "sections": list of section lengths
        }

    Raises:
        ValueError: If input parameters are invalid
    """
    # Validate inputs
    if target_cutoff <= 0:
        raise ValueError(
            f"target_cutoff must be positive, got {target_cutoff} Hz"
        )

    if printer_max_length <= 0:
        raise ValueError(
            f"printer_max_length must be positive, got {printer_max_length} m"
        )

    if target_mouth_area is not None and target_mouth_area <= 0:
        raise ValueError(
            f"target_mouth_area must be positive, got {target_mouth_area} m²"
        )

    if not hasattr(driver, 'S_d') or driver.S_d <= 0:
        raise ValueError(
            f"Driver must have valid S_d parameter, got {getattr(driver, 'S_d', None)}"
        )

    c = SPEED_OF_SOUND

    # Estimate required horn parameters
    # From Olson: Fc = c * m / (2π), m = ln(mouth/throat) / L
    # For given Fc, we need: L = ln(mouth/throat) * (2π * Fc) / c

    # Typical throat area for 1" compression driver
    throat_area = THROAT_AREA_RATIO * driver.S_d  # ~30% of diaphragm area

    # Estimate mouth area from cutoff (quarter-wavelength rule)
    # Mouth circumference should be ≥ wavelength at Fc
    if target_mouth_area is None:
        wavelength = c / target_cutoff
        mouth_circumference = wavelength
        mouth_area = (mouth_circumference / (2 * np.pi))**2 * np.pi
    else:
        mouth_area = target_mouth_area

    # Calculate required flare constant
    m_required = 2 * np.pi * target_cutoff / c

    # Calculate minimum length for this expansion
    expansion_ratio = mouth_area / throat_area
    min_length = np.log(expansion_ratio) / m_required

    # Assess strategy
    if min_length <= printer_max_length * PRINTER_FIT_TOLERANCE:
        # Fits comfortably
        return {
            "fits_single_piece": True,
            "num_sections_required": 1,
            "estimated_length": min_length,
            "strategy": "single",
            "message": f"✓ Design fits in {printer_max_length*100:.0f}mm printer " +
                      f"({min_length*100:.1f}cm required)",
            "sections": [min_length]
        }

    elif min_length <= printer_max_length * 2.5:
        # Fits in 2-3 pieces
        num_sections = int(np.ceil(min_length / printer_max_length))
        section_length = min_length / num_sections

        return {
            "fits_single_piece": False,
            "num_sections_required": num_sections,
            "estimated_length": min_length,
            "strategy": "multi_piece",
            "message": f"⚠ Multi-piece design: {num_sections} sections required " +
                      f"({min_length*100:.1f}cm total, {printer_max_length*100:.0f}mm each)",
            "sections": [section_length] * num_sections,
            "assembly_notes": [
                f"Print {num_sections} sections separately",
                f"Bolt together at flanged junctions",
                "Ensure alignment during assembly"
            ]
        }

    else:
        # Needs many sections or redesign
        num_sections = int(np.ceil(min_length / printer_max_length))

        return {
            "fits_single_piece": False,
            "num_sections_required": num_sections,
            "estimated_length": min_length,
            "strategy": "redesign_needed",
            "message": f"✗ Requires {num_sections} sections ({min_length*100:.1f}cm total)",
            "sections": [],
            "alternatives": [
                f"Use larger printer (≥{min_length*100:.0f}mm)",
                f"Increase target_cutoff to {target_cutoff*1.5:.0f} Hz",
                "Accept higher cutoff + EQ correction",
                "Consider different HF driver"
            ]
        }


def print_printing_strategy(strategy: Dict):
    """Print strategy in user-friendly format."""
    print("\n" + "=" * 70)
    print("PRINTING STRATEGY ASSESSMENT")
    print("=" * 70)
    print(f"\n{strategy['message']}")

    if strategy['strategy'] == 'multi_piece':
        print("\nMulti-Piece Design Details:")
        print(f"  Sections: {strategy['num_sections_required']}")
        print(f"  Section length: {strategy['sections'][0]*100:.1f} cm each")
        if 'assembly_notes' in strategy:
            print("\n  Assembly:")
            for note in strategy['assembly_notes']:
                print(f"    • {note}")

    elif strategy['strategy'] == 'redesign_needed':
        print("\nAlternatives:")
        for i, alt in enumerate(strategy.get('alternatives', []), 1):
            print(f"  {i}. {alt}")

    print("\n" + "=" * 70)
