"""Tapped horn parameter space for optimization.

This module defines parameter ranges and typical values for optimizing
tapped horn loudspeaker systems.

Literature:
- Danley, US Patent 8,457,341 B2 - Tapped horn design criteria
- Berzborn & Smithers (2018), AES Paper 10047 - Tapped horn modeling
- literature/horns/tapped_horn_theory.md
"""

import numpy as np
from gsd.driver.parameters import ThieleSmallParameters
from gsd.optimization.parameters.parameter_space import (
    ParameterRange,
    EnclosureParameterSpace,
)
from gsd.simulation.constants import SPEED_OF_SOUND


def get_tapped_horn_parameter_space(
    driver: ThieleSmallParameters,
    preset: str = "subwoofer"
) -> EnclosureParameterSpace:
    """
    Get parameter space for tapped horn optimization.

    Optimizes 5 parameters:
    - upstream_throat_area: Closed throat area (cm²)
    - tap_area: Area at driver location (cm²)
    - downstream_mouth_area: Mouth area (cm²)
    - upstream_length: Length from throat to driver (cm)
    - downstream_length: Length from driver to mouth (cm)

    Fixed parameters (not optimized):
    - upstream_profile: 'exponential' (most common)
    - downstream_profile: 'exponential' (most common)

    Literature:
        - Danley, US Patent 8,457,341 B2 - Tapped horn geometry guidelines
        - Berzborn & Smithers (2018), AES Paper 10047
        - literature/horns/tapped_horn_theory.md

    Args:
        driver: ThieleSmallParameters for the driver
        preset: Design preset ("subwoofer", "bass_bin")
            - subwoofer: Low-frequency optimized (20-60 Hz) [default]
            - bass_bin: Pro audio bass (40-100 Hz)

    Returns:
        EnclosureParameterSpace: Parameter space definition

    Raises:
        ValueError: If preset is not recognized

    Examples:
        >>> from gsd.driver import load_driver
        >>> param_space = get_tapped_horn_parameter_space(driver, preset="subwoofer")
        >>> param_space.get_parameter_names()
        ['upstream_throat_area', 'tap_area', 'downstream_mouth_area',
         'upstream_length', 'downstream_length']
    """
    # Driver parameters for scaling
    S_d_cm2 = driver.S_d * 1e4  # Diaphragm area [cm²]
    V_as_liters = driver.V_as * 1000  # Equivalent volume [L]

    # Define preset-specific ranges
    # Literature: Danley (2013) patent - Practical tapped horn dimensions
    # Typical subwoofer tapped horns: 30-200 cm mouth, 150-300 cm total length
    if preset == "subwoofer":
        # Subwoofer tapped horn: Optimized for 20-60 Hz
        # Quarter-wave resonance should be in target range
        # F_qw = c / (4 * L_upstream) ≈ 30-60 Hz
        # L_upstream ≈ c / (4 * F_qw) ≈ 34400 / (4 * 45) ≈ 190 cm

        upstream_throat_min = 0.3 * S_d_cm2  # Smaller than driver area
        upstream_throat_max = 0.8 * S_d_cm2
        tap_min = 1.0 * S_d_cm2  # Tap at driver area
        tap_max = 1.5 * S_d_cm2  # Slightly larger
        mouth_min = 500.0  # cm² (radius ~12.6 cm)
        mouth_max = 5000.0  # cm² (radius ~40 cm)
        upstream_len_min = 100.0  # cm (F_qw ≈ 86 Hz)
        upstream_len_max = 300.0  # cm (F_qw ≈ 29 Hz)
        downstream_len_min = 100.0  # cm
        downstream_len_max = 300.0  # cm

    elif preset == "bass_bin":
        # Pro audio bass bin: Higher frequency range (40-100 Hz)
        # Shorter total length, more compact

        upstream_throat_min = 0.3 * S_d_cm2
        upstream_throat_max = 0.8 * S_d_cm2
        tap_min = 1.0 * S_d_cm2
        tap_max = 1.5 * S_d_cm2
        mouth_min = 400.0  # cm²
        mouth_max = 3000.0  # cm²
        upstream_len_min = 60.0  # cm (F_qw ≈ 143 Hz)
        upstream_len_max = 200.0  # cm (F_qw ≈ 43 Hz)
        downstream_len_min = 80.0  # cm
        downstream_len_max = 200.0  # cm

    else:
        raise ValueError(
            f"Unknown preset: {preset}. "
            f"Choose from: 'subwoofer', 'bass_bin'"
        )

    # Define parameter ranges
    # Literature: Danley patent - Area expansion must be monotonic
    # S_throat < S_tap < S_mouth
    parameters = [
        ParameterRange(
            name="upstream_throat_area",
            display_name="Upstream Throat Area",
            min=upstream_throat_min,
            max=upstream_throat_max,
            units="cm²",
            description="Cross-sectional area at closed throat"
        ),
        ParameterRange(
            name="tap_area",
            display_name="Tap Area",
            min=tap_min,
            max=tap_max,
            units="cm²",
            description="Cross-sectional area at driver location"
        ),
        ParameterRange(
            name="downstream_mouth_area",
            display_name="Mouth Area",
            min=mouth_min,
            max=mouth_max,
            units="cm²",
            description="Cross-sectional area at mouth"
        ),
        ParameterRange(
            name="upstream_length",
            display_name="Upstream Length",
            min=upstream_len_min,
            max=upstream_len_max,
            units="cm",
            description="Length from throat to driver"
        ),
        ParameterRange(
            name="downstream_length",
            display_name="Downstream Length",
            min=downstream_len_min,
            max=downstream_len_max,
            units="cm",
            description="Length from driver to mouth"
        ),
    ]

    return EnclosureParameterSpace(
        parameters=parameters,
        enclosure_type="tapped_horn",
        preset=preset
    )


def build_tapped_horn_from_params(
    driver: ThieleSmallParameters,
    design_vector: np.ndarray,
    preset: str = "subwoofer"
):
    """
    Build a TappedHorn object from optimization design vector.

    Args:
        driver: ThieleSmallParameters for the driver
        design_vector: Array of [upstream_throat_area, tap_area,
                         downstream_mouth_area, upstream_length, downstream_length]
        preset: Design preset (determines profile types)

    Returns:
        TappedHorn object

    Raises:
        ValueError: If design_vector has wrong shape
    """
    from gsd.simulation.types import TappedHorn

    if len(design_vector) != 5:
        raise ValueError(
            f"design_vector must have 5 elements, got {len(design_vector)}"
        )

    # For now, always use exponential profiles
    # TODO: Add profile selection as discrete parameter
    upstream_profile = 'exponential'
    downstream_profile = 'exponential'

    return TappedHorn(
        upstream_throat_area=float(design_vector[0]),
        tap_area=float(design_vector[1]),
        downstream_mouth_area=float(design_vector[2]),
        upstream_length=float(design_vector[3]),
        downstream_length=float(design_vector[4]),
        upstream_profile=upstream_profile,
        downstream_profile=downstream_profile,
    )
