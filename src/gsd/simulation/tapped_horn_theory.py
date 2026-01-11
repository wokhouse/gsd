"""Tapped horn acoustic theory and impedance calculations.

This module implements the acoustic model for tapped horns, where the driver
is mounted partway along the horn path. The driver's front and rear radiation
feed into separate horn sections that combine at the mouth.

Literature:
    Berzborn, M. & Smithers, M. (2018). "An Acoustic Model of the Tapped Horn
    Loudspeaker." AES Convention Paper 10047.

    Danley, T.J. (2013). US Patent 8,457,341 B2: "Sound reproduction with
    improved low frequency characteristics."

    Kolbrek, B. "Horn Loudspeaker Simulation" series.
    https://kolbrek.hornspeakersystems.info/

    literature/horns/tapped_horn_theory.md
"""

import numpy as np
from numpy.typing import NDArray

from .types import ExponentialHorn, ConicalHorn, TappedHorn
from .horn_theory import (
    exponential_horn_tmatrix,
    circular_piston_radiation_impedance,
    MediumProperties,
)


def upstream_section_impedance(
    frequencies: NDArray[np.float64],
    tapped_horn: TappedHorn,
    medium: MediumProperties = None,
) -> NDArray[np.complex128]:
    """Calculate acoustic impedance of upstream (throat-side) section.

    The upstream section has a closed (rigid) throat termination. For a
    closed termination (Z_load → ∞), the impedance seen from the tap point is:

        Z_upstream = a / c

    where (a, b, c, d) are the T-matrix elements of the upstream section.

    Literature:
        Kolbrek, B. "Horn Loudspeaker Simulation part 1: Radiation and T-Matrix"
        https://kolbrek.hornspeakersystems.info/

        Danley, US Patent 8,457,341 B2 - Closed throat boundary condition

    Args:
        frequencies: Array of frequencies in Hz
        tapped_horn: TappedHorn geometry specification
        medium: Acoustic medium properties (air density, sound speed).
                 If None, uses default MediumProperties().

    Raises:
        ValueError: If upstream_profile is not supported

    Examples:
        >>> from gsd.simulation.types import TappedHorn, Medium
        >>> th = TappedHorn(
        ...     upstream_throat_area=50.0,
        ...     tap_area=200.0,
        ...     downstream_mouth_area=2000.0,
        ...     upstream_length=40.0,
        ...     downstream_length=150.0
        ... )
        >>> freqs = np.array([20.0, 50.0, 100.0])
        >>> z_up = upstream_section_impedance(freqs, th, Medium())
        >>> z_up.shape
        (3,)
        >>> np.all(np.isfinite(z_up))
        True
    """
    if medium is None:
        medium = MediumProperties()

    frequencies = np.atleast_1d(frequencies).astype(float)

    # Get upstream horn section (converts cm² to m², cm to m)
    upstream_horn = tapped_horn.upstream_section()

    # Get T-matrix elements based on horn type
    if isinstance(upstream_horn, ExponentialHorn):
        a, b, c, d = exponential_horn_tmatrix(
            frequencies, upstream_horn, medium
        )
    elif isinstance(upstream_horn, ConicalHorn):
        # Conical horns use calculate_t_matrix method (single frequency)
        # Need to loop for each frequency
        a = np.zeros(len(frequencies), dtype=complex)
        b = np.zeros(len(frequencies), dtype=complex)
        c = np.zeros(len(frequencies), dtype=complex)
        d = np.zeros(len(frequencies), dtype=complex)

        for i, f in enumerate(frequencies):
            T = upstream_horn.calculate_t_matrix(f, medium.c, medium.rho)
            a[i], b[i], c[i], d[i] = T[0, 0], T[0, 1], T[1, 0], T[1, 1]
    else:
        raise ValueError(f"Unsupported upstream profile: {tapped_horn.upstream_profile}")

    # For closed throat (Z → ∞): Z_upstream = a / c
    # Add small epsilon to avoid division by zero
    epsilon = 1e-12 * (np.abs(c).max() if len(c) > 0 else 1.0)
    z_upstream = a / (c + epsilon)

    return z_upstream


def downstream_section_impedance(
    frequencies: NDArray[np.float64],
    tapped_horn: TappedHorn,
    medium: MediumProperties = None,
) -> NDArray[np.complex128]:
    """Calculate acoustic impedance of downstream (mouth-side) section.

    The downstream section terminates at the mouth with radiation impedance.
    The impedance seen from the tap point is:

        Z_downstream = (a · Z_rad + b) / (c · Z_rad + d)

    where (a, b, c, d) are the T-matrix elements and Z_rad is the mouth
    radiation impedance.

    Literature:
        Kolbrek, B. "Horn Loudspeaker Simulation part 1: Radiation and T-Matrix"

        Beranek (1954), Eq. 5.20 - Mouth radiation impedance

    Args:
        frequencies: Array of frequencies in Hz
        tapped_horn: TappedHorn geometry specification
        medium: Acoustic medium properties. If None, uses default MediumProperties().

    Returns:
        Complex acoustic impedance array (Pa·s/m³) at each frequency

    Raises:
        ValueError: If downstream_profile is not supported

    Examples:
        >>> from gsd.simulation.types import TappedHorn, Medium
        >>> th = TappedHorn(
        ...     upstream_throat_area=50.0,
        ...     tap_area=200.0,
        ...     downstream_mouth_area=2000.0,
        ...     upstream_length=40.0,
        ...     downstream_length=150.0
        ... )
        >>> freqs = np.array([20.0, 50.0, 100.0])
        >>> z_down = downstream_section_impedance(freqs, th, Medium())
        >>> z_down.shape
        (3,)
        >>> np.all(np.isfinite(z_down))
        True
    """
    if medium is None:
        medium = MediumProperties()

    frequencies = np.atleast_1d(frequencies).astype(float)

    # Get downstream horn section (converts cm² to m², cm to m)
    downstream_horn = tapped_horn.downstream_section()

    # Calculate mouth radiation impedance
    z_rad = circular_piston_radiation_impedance(
        frequencies, downstream_horn.mouth_area, medium
    )

    # Get T-matrix elements based on horn type
    if isinstance(downstream_horn, ExponentialHorn):
        a, b, c, d = exponential_horn_tmatrix(
            frequencies, downstream_horn, medium
        )
    elif isinstance(downstream_horn, ConicalHorn):
        # Conical horns use calculate_t_matrix method (single frequency)
        # Need to loop for each frequency
        a = np.zeros(len(frequencies), dtype=complex)
        b = np.zeros(len(frequencies), dtype=complex)
        c = np.zeros(len(frequencies), dtype=complex)
        d = np.zeros(len(frequencies), dtype=complex)

        for i, f in enumerate(frequencies):
            T = downstream_horn.calculate_t_matrix(f, medium.c, medium.rho)
            a[i], b[i], c[i], d[i] = T[0, 0], T[0, 1], T[1, 0], T[1, 1]
    else:
        raise ValueError(f"Unsupported downstream profile: {tapped_horn.downstream_profile}")

    # Transform radiation impedance to tap point
    # Z_downstream = (a * Z_rad + b) / (c * Z_rad + d)
    z_downstream = (a * z_rad + b) / (c * z_rad + d)

    return z_downstream


def tapped_horn_tap_impedance(
    frequencies: NDArray[np.float64],
    tapped_horn: TappedHorn,
    medium: MediumProperties = None,
) -> NDArray[np.complex128]:
    """Calculate total acoustic impedance at the tap point.

    The driver at the tap point sees both the upstream and downstream sections.
    The total impedance is the parallel combination:

        Z_tap = Z_upstream ∥ Z_downstream = (Z_up · Z_down) / (Z_up + Z_down)

    Note: The front and rear of the driver are 180° out of phase, but for
    impedance magnitude calculations (which determine driver loading), this
    parallel combination gives the correct acoustic load. The phase effects
    appear in the pressure response calculation.

    Literature:
        Berzborn & Smithers (2018), AES Paper 10047 - Tap point impedance model

        Danley, US Patent 8,457,341 B2 - Parallel impedance combination

    Args:
        frequencies: Array of frequencies in Hz
        tapped_horn: TappedHorn geometry specification
        medium: Acoustic medium properties. If None, uses default MediumProperties().

    Returns:
        Complex acoustic impedance array (Pa·s/m³) at each frequency

    Examples:
        >>> from gsd.simulation.types import TappedHorn, Medium
        >>> th = TappedHorn(
        ...     upstream_throat_area=50.0,
        ...     tap_area=200.0,
        ...     downstream_mouth_area=2000.0,
        ...     upstream_length=40.0,
        ...     downstream_length=150.0
        ... )
        >>> freqs = np.array([20.0, 50.0, 100.0])
        >>> z_tap = tapped_horn_tap_impedance(freqs, th, Medium())
        >>> z_tap.shape
        (3,)
        >>> # Verify parallel combination
        >>> z_up = upstream_section_impedance(freqs, th, Medium())
        >>> z_down = downstream_section_impedance(freqs, th, Medium())
        >>> z_expected = (z_up * z_down) / (z_up + z_down)
        >>> np.allclose(z_tap, z_expected)
        True
    """
    if medium is None:
        medium = MediumProperties()

    z_up = upstream_section_impedance(frequencies, tapped_horn, medium)
    z_down = downstream_section_impedance(frequencies, tapped_horn, medium)

    # Parallel combination with numerical stability
    # Z_tap = (Z_up * Z_down) / (Z_up + Z_down)
    z_sum = z_up + z_down

    # Avoid division by zero near resonances
    # Use small regularization when |Z_up + Z_down| is very small
    epsilon = 1e-12 * np.maximum(np.abs(z_up), np.abs(z_down)).max()
    mask = np.abs(z_sum) < epsilon

    # Regularize only where needed
    z_sum_safe = z_sum.copy()
    z_sum_safe[mask] += epsilon

    z_tap = (z_up * z_down) / z_sum_safe

    return z_tap
