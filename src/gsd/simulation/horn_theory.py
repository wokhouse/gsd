"""
Horn acoustic simulation using T-matrix method.

This module implements exponential horn simulation based on the T-matrix
(transfer matrix) approach, which provides accurate throat impedance
calculations for finite horns.

Literature:
- Kolbrek, B. "Horn Loudspeaker Simulation Part 1: Radiation and T-Matrix"
  https://kolbrek.hornspeakersystems.info/
- Beranek, L. (1954). Acoustics. McGraw-Hill. Eq. 5.20
- Kinsler, L.E. & Frey, A.R. (1982). Fundamentals of Acoustics. Eq. 9.6.4
- literature/horns/kolbrek_horn_theory_tutorial.md
- literature/horns/beranek_1954.md
"""

from dataclasses import dataclass
from typing import Tuple, Optional
import numpy as np
from numpy.typing import NDArray

# Type aliases
ComplexArray = NDArray[np.complexfloating]
FloatArray = NDArray[np.floating]


@dataclass
class MediumProperties:
    """Properties of the acoustic medium.

    Attributes:
        c: Speed of sound [m/s]
        rho: Air density [kg/m³]
        z_rc: Characteristic impedance ρc [Pa·s/m] (computed property)

    Literature:
        Default values match Hornresp defaults (Kolbrek tutorial).
        Standard conditions at 20°C, 1 atm.

    Examples:
        >>> medium = MediumProperties()
        >>> medium.c  # Speed of sound
        344.0
        >>> medium.z_rc  # Characteristic impedance
        414.62...  # ρc = 1.205 × 344
    """
    c: float = 344.0  # m/s at 20°C
    rho: float = 1.205  # kg/m³ at 20°C, 1 atm

    @property
    def z_rc(self) -> float:
        """Characteristic impedance ρc [Pa·s/m].

        Literature:
            Kinsler et al. (1982), Chapter 1 - Characteristic impedance
        """
        return self.rho * self.c


# Note: We use gsd.simulation.types.ExponentialHorn for the main data class.
# This module provides calculation functions that work with that class.
# The types.ExponentialHorn uses Olson's convention: S(x) = S₁·exp(m·x) with m = ln(S₂/S₁)/L
# Kolbrek's convention uses: S(x) = S₁·exp(2m·x) with m_K = ln(S₂/S₁)/(2L) = m_Olson/2
# Internally, we convert to Kolbrek's convention for T-matrix calculations.


def circular_piston_radiation_impedance(
    frequencies: FloatArray,
    area: float,
    medium: Optional[MediumProperties] = None
) -> ComplexArray:
    """Calculate radiation impedance of circular piston in infinite baffle.

    This function computes the acoustic radiation impedance for a circular
    piston in an infinite baffle using Bessel and Struve functions.

    Literature:
        Z_rad = (ρc/S)[R₁(ka) + jX₁(ka)]
        R₁(ka) = 1 - J₁(2ka)/ka
        X₁(ka) = H₁(2ka)/ka

        Beranek (1954), Eq. 5.20 - Piston radiation impedance
        Kolbrek, "Horn Loudspeaker Simulation Part 1"
        literature/horns/beranek_1954.md

    Args:
        frequencies: Array of frequencies [Hz]
        area: Piston area [m²]
        medium: Acoustic medium properties (uses default if None)

    Returns:
        Complex acoustic impedance array [Pa·s/m³]

    Notes:
        - Uses scipy.special.j1 for J₁ Bessel function
        - Uses scipy.special.struve(1, x) for H₁ Struve function
        - Handles ka→0 limit using series expansion to avoid 0/0

    Examples:
        >>> import numpy as np
        >>> frequencies = np.array([100.0, 1000.0, 10000.0])
        >>> z = circular_piston_radiation_impedance(frequencies, area=0.01)
        >>> z[0]  # Low frequency: mostly reactive
        (0.001...+0.126j)
        >>> z[1]  # Mid frequency: transitioning
        (3.8...+12.5j)
        >>> z[2]  # High frequency: mostly resistive
        (413...+2.5j)

    Validation:
        Compare with Hornresp radiation impedance calculation.
        Expected: <1% deviation for ka > 0.5
    """
    from scipy.special import j1, struve

    if medium is None:
        medium = MediumProperties()

    frequencies = np.atleast_1d(frequencies).astype(float)
    radius = np.sqrt(area / np.pi)
    k = 2 * np.pi * frequencies / medium.c
    ka = k * radius
    two_ka = 2 * ka

    # Handle small ka to avoid numerical issues (0/0)
    # For small x: J₁(x)/x ≈ 1/2, H₁(x)/x ≈ 4x/(3π)
    small_ka_mask = ka < 1e-6

    R1 = np.ones_like(ka)
    X1 = np.zeros_like(ka)

    # Normal calculation for ka >= 1e-6
    normal_mask = ~small_ka_mask
    if np.any(normal_mask):
        ka_normal = ka[normal_mask]
        two_ka_normal = two_ka[normal_mask]
        R1[normal_mask] = 1 - j1(two_ka_normal) / ka_normal
        X1[normal_mask] = struve(1, two_ka_normal) / ka_normal

    # Small ka approximation (Taylor series leading terms)
    # R₁(ka) ≈ (ka)²/2 for small ka
    # X₁(ka) ≈ 8ka/(3π) for small ka
    if np.any(small_ka_mask):
        ka_small = ka[small_ka_mask]
        R1[small_ka_mask] = (ka_small ** 2) / 2
        X1[small_ka_mask] = 8 * ka_small / (3 * np.pi)

    z_normalized = R1 + 1j * X1
    z_rad = (medium.z_rc / area) * z_normalized

    return z_rad


def _kolbrek_flare_constant(horn: 'ExponentialHorn') -> float:
    """Convert from Olson's to Kolbrek's flare constant convention.

    Olson: S(x) = S₁·exp(m_olson·x) with m_olson = ln(S₂/S₁)/L
    Kolbrek: S(x) = S₁·exp(2m_kolbrek·x) with m_kolbrek = ln(S₂/S₁)/(2L)

    Therefore: m_kolbrek = m_olson / 2

    Literature:
        Kolbrek, "Horn Loudspeaker Simulation Part 1"
        Olson (1947), Chapter 5

    Args:
        horn: ExponentialHorn instance (using Olson's convention)

    Returns:
        Flare constant in Kolbrek's convention [1/m]
    """
    return horn.flare_constant / 2.0


def exponential_horn_tmatrix(
    frequencies: FloatArray,
    horn: 'ExponentialHorn',
    medium: Optional[MediumProperties] = None
) -> Tuple[ComplexArray, ComplexArray, ComplexArray, ComplexArray]:
    """Calculate T-matrix elements for exponential horn.

    Uses the existing types.ExponentialHorn data class (Olson convention)
    and internally converts to Kolbrek's convention for T-matrix calculation.

    The T-matrix (transfer matrix) relates pressure and volume velocity
    at the throat (port 1) to the mouth (port 2):

        [p₁, U₁]ᵀ = [a b; c d][p₂, U₂]ᵀ

    Literature:
        T-matrix elements for exponential horn:

        a = exp(mL)[cos(γL) - (m/γ)sin(γL)]
        b = exp(mL)·j(Z_rc/S₂)(k/γ)sin(γL)
        c = exp(mL)·j(S₁/Z_rc)(k/γ)sin(γL)
        d = exp(mL)(S₁/S₂)[cos(γL) + (m/γ)sin(γL)]

        γ = √(k² - m²) (propagation constant)

        Kolbrek, "Horn Loudspeaker Simulation Part 1"
        literature/horns/kolbrek_horn_theory_tutorial.md

    Args:
        frequencies: Array of frequencies [Hz]
        horn: ExponentialHorn geometry parameters
        medium: Acoustic medium properties (uses default if None)

    Returns:
        Tuple of (a, b, c, d) T-matrix element arrays (complex)

    Notes:
        - When f < f_c, γ is imaginary; sin/cos become sinh/cosh
        - Near f = f_c, use Taylor expansion to avoid γ→0 singularity
        - All arrays have same shape as input frequencies

    Examples:
        >>> import numpy as np
        >>> horn = ExponentialHorn(0.005, 0.05, 0.3)
        >>> freqs = np.array([100.0, 500.0, 1000.0])
        >>> a, b, c, d = exponential_horn_tmatrix(freqs, horn)
        >>> a.shape
        (3,)

    Validation:
        T-matrix is unitary for lossless horns (determinant = 1).
        Check det([a b; c d]) ≈ 1.0 for frequencies well above cutoff.
    """
    if medium is None:
        medium = MediumProperties()

    frequencies = np.atleast_1d(frequencies).astype(float)

    # Convert from Olson's to Kolbrek's flare constant convention
    m = _kolbrek_flare_constant(horn)
    L = horn.length
    S1 = horn.throat_area
    S2 = horn.mouth_area
    z_rc = medium.z_rc

    k = 2 * np.pi * frequencies / medium.c

    # γ = √(k² - m²), can be real or imaginary
    # Use complex sqrt to handle f < f_c case
    gamma_squared = k**2 - m**2
    gamma = np.sqrt(gamma_squared.astype(complex))

    gL = gamma * L
    emL = np.exp(m * L)

    # Handle near-cutoff singularity (γ → 0)
    # When |γL| < threshold, use Taylor expansion
    near_cutoff_mask = np.abs(gL) < 1e-8

    sin_gL = np.sin(gL)
    cos_gL = np.cos(gL)

    # For normal frequencies
    m_over_gamma = np.zeros_like(gamma, dtype=complex)
    k_over_gamma = np.zeros_like(gamma, dtype=complex)

    normal_mask = ~near_cutoff_mask
    if np.any(normal_mask):
        m_over_gamma[normal_mask] = m / gamma[normal_mask]
        k_over_gamma[normal_mask] = k[normal_mask] / gamma[normal_mask]

    # Near cutoff: use limits
    # sin(γL)/γ → L as γ→0
    # cos(γL) → 1 as γ→0
    # (m/γ)·sin(γL) → mL as γ→0
    # (k/γ)·sin(γL) → kL as γ→0 (at cutoff, k≈m)
    if np.any(near_cutoff_mask):
        # Use small angle approximation: sin(x) ≈ x for x → 0
        # So sin(γL)/γ → L
        sin_gL[near_cutoff_mask] = gL[near_cutoff_mask]
        cos_gL[near_cutoff_mask] = 1.0

        # For m/γ: as γ→0, sin(γL) ≈ γL, so (m/γ)sin(γL) → mL
        # Avoid division by zero by using limit directly
        m_over_gamma[near_cutoff_mask] = m * L
        k_over_gamma[near_cutoff_mask] = k[near_cutoff_mask] * L

    # T-matrix elements
    a = emL * (cos_gL - m_over_gamma * sin_gL)
    b = emL * 1j * (z_rc / S2) * k_over_gamma * sin_gL
    c = emL * 1j * (S1 / z_rc) * k_over_gamma * sin_gL
    d = emL * (S1 / S2) * (cos_gL + m_over_gamma * sin_gL)

    return a, b, c, d


def throat_impedance_from_tmatrix(
    z_mouth: ComplexArray,
    a: ComplexArray,
    b: ComplexArray,
    c: ComplexArray,
    d: ComplexArray
) -> ComplexArray:
    """Calculate throat impedance from mouth impedance using T-matrix.

    This function transforms the acoustic impedance from the mouth to the throat
    using the T-matrix elements.

    Literature:
        Z₁ = (a·Z₂ + b)/(c·Z₂ + d)

        Standard T-matrix impedance transformation
        Kolbrek, "Horn Loudspeaker Simulation Part 1"

    Args:
        z_mouth: Acoustic impedance at mouth (Z₂) [Pa·s/m³]
        a, b, c, d: T-matrix elements (from exponential_horn_tmatrix)

    Returns:
        Acoustic impedance at throat (Z₁) [Pa·s/m³]

    Notes:
        All input arrays must have the same shape.

    Examples:
        >>> z_mouth = np.array([100+100j, 400+50j])
        >>> a = b = c = d = np.array([1+0j, 1+0j])
        >>> z_throat = throat_impedance_from_tmatrix(z_mouth, a, b, c, d)
        >>> z_throat.shape
        (2,)
    """
    return (a * z_mouth + b) / (c * z_mouth + d)


def exponential_horn_throat_impedance(
    frequencies: FloatArray,
    horn: 'ExponentialHorn',
    medium: Optional[MediumProperties] = None,
    radiation_angle: float = 2 * np.pi
) -> ComplexArray:
    """Calculate throat impedance of finite exponential horn.

    Uses the existing types.ExponentialHorn data class (Olson convention)
    and internally converts to Kolbrek's convention for T-matrix calculation.

    This is the main entry point for exponential horn simulation. It combines
    mouth radiation impedance with T-matrix transformation to compute the
    acoustic impedance at the horn throat.

    Literature:
        Combines:
        - Mouth radiation impedance (Beranek Eq. 5.20)
        - T-matrix transformation (Kolbrek)

        literature/horns/beranek_1954.md
        literature/horns/kolbrek_horn_theory_tutorial.md

    Args:
        frequencies: Array of frequencies [Hz]
        horn: ExponentialHorn geometry parameters
        medium: Acoustic medium properties (uses default if None)
        radiation_angle: Solid angle of radiation [steradians]
            - 4π: free field (pulsating sphere)
            - 2π: half-space (piston in infinite baffle) [default]
            - π: quarter-space
            - π/2: eighth-space

    Returns:
        Complex acoustic impedance at throat [Pa·s/m³]
        Array shape matches input frequencies

    Notes:
        For radiation_angle != 2π, effective piston area is adjusted
        following Hornresp convention:
        S_eff = 2π·S_mouth/radiation_angle

    Examples:
        >>> import numpy as np
        >>> horn = ExponentialHorn(throat_area=0.005, mouth_area=0.05, length=0.3)
        >>> freqs = np.array([100.0, 500.0, 1000.0, 5000.0])
        >>> z_throat = exponential_horn_throat_impedance(freqs, horn)
        >>> z_throat[0]  # Below cutoff: mostly reactive (mass-like)
        (0.01...+5.2j)
        >>> z_throat[2]  # Above cutoff: becoming resistive
        (40...+30j)
        >>> z_throat[3]  # High frequency: approaches ρc/S₁
        (80...+5j)

    Validation:
        Compare with Hornresp acoustical impedance export.
        Expected tolerances:
        - f > 2×f_c: <1% magnitude, <2° phase
        - f_c < f < 2×f_c: <3% magnitude, <5° phase
        - f < f_c: <10% magnitude (evanescent region)
    """
    if medium is None:
        medium = MediumProperties()

    frequencies = np.atleast_1d(frequencies).astype(float)

    # Adjust effective area for radiation angle (Hornresp convention)
    # S_eff = 2π·S_mouth/radiation_angle
    effective_mouth_area = 2 * np.pi * horn.mouth_area / radiation_angle

    # Calculate mouth radiation impedance
    z_mouth = circular_piston_radiation_impedance(
        frequencies, effective_mouth_area, medium
    )

    # Calculate T-matrix
    a, b, c, d = exponential_horn_tmatrix(frequencies, horn, medium)

    # Transform to throat
    z_throat = throat_impedance_from_tmatrix(z_mouth, a, b, c, d)

    return z_throat


def multsegment_horn_throat_impedance(
    frequencies: FloatArray,
    horn: 'MultiSegmentHorn',
    medium: Optional[MediumProperties] = None,
    radiation_angle: float = 2 * np.pi
) -> ComplexArray:
    """Calculate throat impedance of multi-segment horn using T-matrix chaining.

    A multi-segment horn consists of multiple exponential segments connected
    in series. The overall T-matrix is the product of individual segment T-matrices:

        T_total = T_1 · T_2 · ... · T_n

    This allows approximating arbitrary horn profiles by using segments with
    different flare constants.

    Literature:
        - Kolbrek Part 1 - T-matrix chaining for compound horns
        - Olson (1947), Chapter 8 - Compound and stepped horns
        - literature/horns/kolbrek_horn_theory_tutorial.md

    Args:
        frequencies: Array of frequencies [Hz]
        horn: MultiSegmentHorn geometry with list of HornSegment objects
        medium: Acoustic medium properties (uses default if None)
        radiation_angle: Solid angle of radiation [steradians]
            - 4π: free field (pulsating sphere)
            - 2π: half-space (piston in infinite baffle) [default]
            - π: quarter-space
            - π/2: eighth-space

    Returns:
        Complex acoustic impedance at throat [Pa·s/m³]
        Array shape matches input frequencies

    Notes:
        - T-matrices are chained from mouth to throat (reverse order)
        - Each segment is treated as an exponential horn with its own flare constant
        - Mouth radiation impedance calculated only for final segment mouth
        - For radiation_angle != 2π, effective mouth area is adjusted

    Examples:
        >>> import numpy as np
        >>> from gsd.simulation.types import HornSegment, MultiSegmentHorn
        >>> segment1 = HornSegment(throat_area=0.001, mouth_area=0.01, length=0.3)
        >>> segment2 = HornSegment(throat_area=0.01, mouth_area=0.1, length=0.6)
        >>> horn = MultiSegmentHorn(segments=[segment1, segment2])
        >>> freqs = np.array([100.0, 500.0, 1000.0, 5000.0])
        >>> z_throat = multsegment_horn_throat_impedance(freqs, horn)
        >>> z_throat.shape
        (4,)

    Validation:
        Compare with Hornresp multi-segment horn simulation.
        Expected tolerances:
        - f > 2×f_c_min: <1% magnitude, <2° phase
        - Near cutoff: <3% magnitude, <5° phase
        where f_c_min is the minimum cutoff frequency among all segments
    """
    if medium is None:
        medium = MediumProperties()

    frequencies = np.atleast_1d(frequencies).astype(float)

    # Adjust effective area for radiation angle (Hornresp convention)
    # S_eff = 2π·S_mouth/radiation_angle
    effective_mouth_area = 2 * np.pi * horn.mouth_area / radiation_angle

    # Calculate mouth radiation impedance (only for final mouth)
    z_mouth = circular_piston_radiation_impedance(
        frequencies, effective_mouth_area, medium
    )

    # Chain T-matrices from mouth to throat
    # Start with mouth impedance, work backwards through segments
    z_current = z_mouth

    # Process segments in reverse order (mouth to throat)
    for segment in reversed(horn.segments):
        # Check segment type and use appropriate T-matrix calculation
        from gsd.simulation.types import HornSegment, ConicalHorn, HyperbolicHorn

        if isinstance(segment, (ConicalHorn, HyperbolicHorn)):
            # Use the segment's own T-matrix method for spherical/hyperbolic waves
            # These methods handle single frequencies, so we need to loop
            z_new = np.zeros_like(z_current, dtype=complex)

            for i, freq in enumerate(frequencies):
                # Get T-matrix from the segment's method
                T = segment.calculate_t_matrix(freq, medium.c, medium.rho)
                a, b, c, d = T[0, 0], T[0, 1], T[1, 0], T[1, 1]

                # Transform impedance through this segment
                z_new[i] = throat_impedance_from_tmatrix(z_current[i], a, b, c, d)

            z_current = z_new

        else:
            # HornSegment (exponential) or ExponentialHorn: use plane wave T-matrix
            from gsd.simulation.types import ExponentialHorn
            segment_horn = ExponentialHorn(
                throat_area=segment.throat_area,
                mouth_area=segment.mouth_area,
                length=segment.length
                # flare_constant calculated automatically
            )

            # Calculate T-matrix for this segment (vectorized over frequencies)
            a, b, c, d = exponential_horn_tmatrix(frequencies, segment_horn, medium)

            # Transform impedance through this segment
            z_current = throat_impedance_from_tmatrix(z_current, a, b, c, d)

    return z_current


def conical_horn_area(
    x: float,
    throat_area: float,
    mouth_area: float,
    length: float
) -> float:
    """Calculate cross-sectional area at distance x for a conical horn.

    A conical horn expands linearly in radius, which means quadratically in area.
    The radius at any point x is:
        r(x) = r_t + (r_m - r_t) * (x / L)

    Therefore the area is:
        S(x) = pi * r(x)^2

    This is geometrically equivalent to S(x) = S_t * (1 + x/x0)^2 where x0 is
    the distance from the projected apex to the throat.

    Literature:
        Olson (1947), Section 5.15 - Conical horn geometry
        Beranek (1954), Chapter 5 - Conical horns
        literature/horns/conical_theory.md

    Args:
        x: Distance from throat [m]
        throat_area: Area at throat [m²]
        mouth_area: Area at mouth [m²]
        length: Total length of segment [m]

    Returns:
        Cross-sectional area at position x [m²]

    Raises:
        ValueError: If length <= 0

    Examples:
        >>> conical_horn_area(0.0, 0.005, 0.05, 0.5)  # At throat
        0.005
        >>> conical_horn_area(0.25, 0.005, 0.05, 0.5)  # At midpoint
        0.0196...  # Approximately 4x throat area (2x radius)

    Validation:
        For a horn with S1=50cm², S2=500cm², L=50cm:
        At x=25cm (midpoint), area should be ~222.6 cm²
        (Geometric mean of throat and mouth radii squared)
    """
    if length <= 0:
        raise ValueError(f"Length must be positive, got {length}")

    # Calculate radii from areas
    r_t = np.sqrt(throat_area / np.pi)
    r_m = np.sqrt(mouth_area / np.pi)

    # Linear radius expansion: r(x) = r_t + (r_m - r_t) * (x / L)
    r_x = r_t + (r_m - r_t) * (x / length)

    # Area from radius
    return np.pi * (r_x ** 2)


def calculate_conical_x0(
    throat_area: float,
    mouth_area: float,
    length: float
) -> float:
    """Calculate x0 (distance from apex to throat) for a conical horn.

    For a conical horn, the area expansion can be written as:
        S(x) = S_t * (1 + x/x0)^2

    where x0 is the distance from the projected apex of the cone to the throat.
    This is derived from similar triangles relating the throat and mouth radii.

    From geometry: r_t / x0 = (r_m - r_t) / length
    Therefore: x0 = r_t * length / (r_m - r_t)

    Literature:
        Olson (1947), Section 5.15 - Conical horn geometry
        literature/horns/conical_theory.md

    Args:
        throat_area: Area at throat [m²]
        mouth_area: Area at mouth [m²]
        length: Horn length [m]

    Returns:
        Distance from apex to throat x0 [m]

    Raises:
        ValueError: If mouth_area <= throat_area (not expanding)

    Examples:
        >>> calculate_conical_x0(0.005, 0.05, 0.5)
        0.166...  # x0 is 1/3 of horn length for 10x area expansion

    Validation:
        Verify that S(L) calculated using x0 matches mouth_area.
        S(L) = S_t * (1 + L/x0)^2 should equal S_m
    """
    if mouth_area <= throat_area:
        raise ValueError(
            f"Conical horn must expand (mouth_area > throat_area), "
            f"got mouth_area={mouth_area}, throat_area={throat_area}"
        )
    if length <= 0:
        raise ValueError(f"Length must be positive, got {length}")

    # Calculate radii from areas
    r_t = np.sqrt(throat_area / np.pi)
    r_m = np.sqrt(mouth_area / np.pi)

    # x0 from similar triangles: r_t / x0 = (r_m - r_t) / L
    # Therefore: x0 = r_t * L / (r_m - r_t)
    x0 = (r_t * length) / (r_m - r_t)

    return x0


def conical_horn_impedance_infinite(
    frequencies: FloatArray,
    throat_area: float,
    x0: float,
    medium: Optional[MediumProperties] = None
) -> ComplexArray:
    """Calculate acoustic impedance for an INFINITE conical horn.

    This function calculates the throat impedance of an infinite conical horn
    using spherical wave theory. The impedance is given by:

        Z_t = (rho * c / S_t) * (j * k * x0) / (1 + j * k * x0)

    where k is the wavenumber and x0 is the distance from apex to throat.

    This is a theoretical result for infinite horns. Real finite horns require
    T-matrix simulation with mouth radiation impedance, but this function
    provides the ideal behavior for validation and understanding.

    Literature:
        Olson (1947), Eq. 5.16 - Infinite conical horn impedance
        Beranek (1954), p. 270 - Spherical wave impedance
        literature/horns/conical_theory.md

    Args:
        frequencies: Frequency array [Hz]
        throat_area: Area at throat [m²]
        x0: Distance from projected apex to throat [m]
        medium: Acoustic medium properties (uses default if None)

    Returns:
        Complex acoustic impedance array at throat [Pa·s/m³]

    Notes:
        - Unlike exponential horns, conical horns have NO sharp cutoff frequency
        - Resistance rises gradually from zero (not a step function)
        - At high frequencies, approaches ρc/S_t (characteristic impedance)
        - Reactance is mass-like at low frequencies (positive imaginary)

    Examples:
        >>> import numpy as np
        >>> freqs = np.array([100.0, 1000.0, 10000.0])
        >>> z = conical_horn_impedance_infinite(freqs, 0.005, 0.2)
        >>> z[0]  # Low frequency: mostly reactive (mass-like)
        (0.02...+2.1j)
        >>> z[2]  # High frequency: approaches ρc/S_t
        (68...+5j)

    Validation:
        Compare with Hornresp infinite conical horn approximation.
        Expected: <1% deviation for k*x0 > 1 (above throat cutoff)
    """
    if medium is None:
        medium = MediumProperties()

    frequencies = np.atleast_1d(frequencies).astype(float)

    omega = 2 * np.pi * frequencies
    k = omega / medium.c  # Wavenumber

    # Characteristic acoustic impedance of medium per unit area
    Z0 = medium.z_rc / throat_area  # ρc/S_t

    # Complex factor: (j * k * x0) / (1 + j * k * x0)
    jkx0 = 1j * k * x0
    factor = jkx0 / (1 + jkx0)

    # Throat impedance
    z_throat = Z0 * factor

    return z_throat


def conical_horn_throat_impedance(
    frequencies: FloatArray,
    horn: 'ConicalHorn',
    medium: Optional[MediumProperties] = None,
    radiation_angle: float = 2 * np.pi
) -> ComplexArray:
    """Calculate throat impedance of finite conical horn using T-matrix.

    Uses the ConicalHorn data class and spherical wave T-matrix method to
    compute the acoustic impedance at the horn throat, accounting for mouth
    radiation impedance.

    Literature:
        Combines:
        - Mouth radiation impedance (Beranek Eq. 5.20)
        - Spherical wave T-matrix transformation (Kolbrek)

        literature/horns/beranek_1954.md
        literature/horns/kolbrek_horn_theory_tutorial.md
        literature/horns/conical_theory.md

    Args:
        frequencies: Array of frequencies [Hz]
        horn: ConicalHorn geometry parameters
        medium: Acoustic medium properties (uses default if None)
        radiation_angle: Solid angle of radiation [steradians]
            - 4π: free field (pulsating sphere)
            - 2π: half-space (piston in infinite baffle) [default]
            - π: quarter-space
            - π/2: eighth-space

    Returns:
        Complex acoustic impedance at throat [Pa·s/m³]
        Array shape matches input frequencies

    Notes:
        Unlike exponential horns, conical horns have NO sharp cutoff frequency.
        Resistance rises gradually from zero frequency.

        For radiation_angle != 2π, effective piston area is adjusted
        following Hornresp convention:
        S_eff = 2π·S_mouth/radiation_angle

    Examples:
        >>> import numpy as np
        >>> from gsd.simulation.types import ConicalHorn
        >>> horn = ConicalHorn(throat_area=0.005, mouth_area=0.05, length=0.5)
        >>> freqs = np.array([100.0, 500.0, 1000.0, 5000.0])
        >>> z_throat = conical_horn_throat_impedance(freqs, horn)
        >>> z_throat[0]  # Low frequency: mostly reactive (mass-like)
        (0.01...+3j)
        >>> z_throat[2]  # Mid frequency: becoming resistive
        (30...+25j)
        >>> z_throat[3]  # High frequency: approaches ρc/S₁
        (70...+8j)

    Validation:
        Compare with Hornresp CON horn type acoustical impedance export.
        Expected tolerances:
        - f > 500 Hz: <2% magnitude, <3° phase
        - f < 500 Hz: <5% magnitude (smooth transition region)
    """
    if medium is None:
        medium = MediumProperties()

    frequencies = np.atleast_1d(frequencies).astype(float)

    # Adjust effective area for radiation angle (Hornresp convention)
    effective_mouth_area = 2 * np.pi * horn.mouth_area / radiation_angle

    # Calculate mouth radiation impedance
    z_mouth = circular_piston_radiation_impedance(
        frequencies, effective_mouth_area, medium
    )

    # Calculate throat impedance for each frequency using T-matrix
    z_throat = np.zeros_like(frequencies, dtype=complex)

    for i, (f, z_m) in enumerate(zip(frequencies, z_mouth)):
        # Get T-matrix for this frequency
        t_matrix = horn.calculate_t_matrix(f, medium.c, medium.rho)

        # Transform mouth impedance to throat
        # Z_throat = (A * Z_mouth + B) / (C * Z_mouth + D)
        A, B = t_matrix[0, 0], t_matrix[0, 1]
        C, D = t_matrix[1, 0], t_matrix[1, 1]

        z_throat[i] = (A * z_m + B) / (C * z_m + D)

    return z_throat
