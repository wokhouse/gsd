"""
Data structures for horn geometry and simulation parameters.

This module defines Pydantic models for horn parameters, ensuring
type safety and validation throughout the simulation code.

Literature:
- Kolbrek Part 1 - Horn profile definitions
- Olson (1947), Chapter 5 - Horn geometry parameters
- Beranek (1954), Chapter 5 - Horn terminology
"""

from dataclasses import dataclass
from typing import List, Optional, Union

import numpy as np
from scipy.optimize import brentq


@dataclass
class ExponentialHorn:
    """
    Exponential horn geometry parameters.

    The exponential horn has a cross-sectional area that varies
    exponentially with distance from the throat:

        S(x) = S_throat · exp(m·x)

    where m is the flare constant.

    Literature:
        - Olson (1947), Eq. 5.12 - Exponential horn profile
        - Kolbrek Part 1 - Modern treatment
        - literature/horns/olson_1947.md

    Attributes:
        throat_area: Throat cross-sectional area (m²)
        mouth_area: Mouth cross-sectional area (m²)
        length: Horn axial length (m)
        flare_constant: Flare constant m (1/m), calculated from geometry
                      if not provided. m = (1/L) · ln(S_mouth/S_throat)

    Examples:
        >>> horn = ExponentialHorn(
        ...     throat_area=0.001,  # 10 cm²
        ...     mouth_area=0.1,     # 1000 cm²
        ...     length=1.5          # 1.5 m
        ... )
        >>> horn.flare_constant
        3.068...  # 1/m
    """

    throat_area: float
    mouth_area: float
    length: float
    flare_constant: Optional[float] = None

    def __post_init__(self):
        """Calculate flare constant from geometry if not provided."""
        if self.flare_constant is None:
            # Olson (1947), Chapter 5: m = (1/L) · ln(S_m/S_t)
            self.flare_constant = np.log(self.mouth_area / self.throat_area) / self.length

    def throat_radius(self) -> float:
        """Calculate throat radius from throat area (assuming circular)."""
        return np.sqrt(self.throat_area / np.pi)

    def mouth_radius(self) -> float:
        """Calculate mouth radius from mouth area (assuming circular)."""
        return np.sqrt(self.mouth_area / np.pi)

    def area_at(self, x: float) -> float:
        """
        Calculate cross-sectional area at distance x from throat.

        S(x) = S_throat · exp(m·x)

        Literature:
            - Olson (1947), Eq. 5.12
            - literature/horns/olson_1947.md

        Args:
            x: Axial distance from throat (m), 0 ≤ x ≤ length

        Returns:
            Cross-sectional area at position x (m²)
        """
        return self.throat_area * np.exp(self.flare_constant * x)


@dataclass
class HyperbolicHorn:
    """
    A hyperbolic (Hypex) horn segment with T parameter.

    Implements the Salmon hyperbolic family:
        S(x) = S_0 * [cosh(mx) + T * sinh(mx)]^2

    The hyperbolic horn family ("Hypex") was generalized by Vincent Salmon in 1946.
    While the Exponential horn expands at a constant rate, the Hyperbolic family
    allows for manipulation of the expansion rate near the throat, governed by
    the shape parameter T.

    Literature:
        - Salmon, V. (1946). "A New Family of Horns", J. Acoust. Soc. Am.
          - Defines the hyperbolic family: r(x) = r₀[cosh(mx) + T·sinh(mx)]
        - Kolbrek, B. (2008). "Horn Theory: An Introduction, Part 1 & 2".
          - T-parameter ranges and optimal values (0.5-0.85 for extended bass)
        - Freehafer, J. E. (1940). "The Acoustical Impedance of an Infinite
          Hyperbolic Horn", J. Acoust. Soc. Am.
          - Foundational solution for hyperbolic horn impedance
        - Olson (1947), Chapter 5 - Horn profiles
        - literature/horns/kolbrek_horn_theory_tutorial.md

    Attributes:
        throat_area: Throat area [m²]
        mouth_area: Mouth area [m²]
        length: Axial length [m]
        T: Shape parameter (0 < T <= 1 for hypex, T=1 is exponential)
            T < 1: Hyperbolic/Hypex - better low-frequency extension
            T = 1: Exponential
            T > 1: Toward conical (constant directivity)
        m: Flare constant [1/m] (calculated from geometry)

    Examples:
        >>> horn = HyperbolicHorn(
        ...     throat_area=0.001,  # 10 cm²
        ...     mouth_area=0.1,     # 1000 cm²
        ...     length=1.5,         # 1.5 m
        ...     T=0.7               # Hypex with better low-end loading
        ... )
        >>> horn.m  # Flare constant calculated from geometry
        3.068...  # 1/m
    """

    throat_area: float
    mouth_area: float
    length: float
    T: float = 1.0  # Default to exponential
    m: float = 0.0  # Calculated post-init

    def __post_init__(self):
        """Solve for the unique flare constant m that fits the geometry and T."""
        if self.length <= 0 or self.throat_area <= 0 or self.mouth_area <= 0:
            raise ValueError("Dimensions must be positive nonzero values.")

        if self.T < 0.01:
            raise ValueError("T must be > 0.01 (T=0 is undefined catenoidal).")

        # Optimization target: Find m such that geometry is satisfied
        # sqrt(S_mouth/S_throat) = cosh(m*L) + T*sinh(m*L)
        target_ratio = np.sqrt(self.mouth_area / self.throat_area)

        def geometry_error(m_guess):
            # Using m convention for amplitude flare matching Salmon
            # S(x) = S0 * (cosh(mx) + T*sinh(mx))^2
            val = np.cosh(m_guess * self.length) + self.T * np.sinh(m_guess * self.length)
            return val - target_ratio

        # Corner case: Exponential (T=1)
        if abs(self.T - 1.0) < 1e-4:
            # Simple analytical solution for exponential
            # S = S0 * e^(2mL) -> sqrt(S/S0) = e^(mL) -> mL = ln(sqrt(rat))
            self.m = np.log(target_ratio) / self.length
        else:
            # Numerical solution for Hyperbolic
            try:
                # Search for m typically between 1e-6 and 50
                # Lower bound very small for very long/narrow horns
                # Upper bound for very short/wide horns
                self.m = brentq(geometry_error, 1e-6, 100.0)
            except ValueError:
                # Fallback for extreme geometries (very short/wide)
                # Use exponential approximation
                self.m = np.log(target_ratio) / self.length

    def throat_radius(self) -> float:
        """Calculate throat radius from throat area (assuming circular)."""
        return np.sqrt(self.throat_area / np.pi)

    def mouth_radius(self) -> float:
        """Calculate mouth radius from mouth area (assuming circular)."""
        return np.sqrt(self.mouth_area / np.pi)

    def area_at(self, x: float) -> float:
        """
        Calculate cross-sectional area at distance x from throat.

        S(x) = S_throat * [cosh(mx) + T*sinh(mx)]^2

        Literature:
            - Salmon (1946), Eq. for hyperbolic horns
            - Kolbrek Part 1 - Modern treatment

        Args:
            x: Axial distance from throat (m), 0 ≤ x ≤ length

        Returns:
            Cross-sectional area at position x (m²)
        """
        if x < 0 or x > self.length:
            raise ValueError("x must be within segment length")

        factor = np.cosh(self.m * x) + self.T * np.sinh(self.m * x)
        return self.throat_area * (factor ** 2)

    def calculate_t_matrix(self, f: float, c: float = 343.2, rho: float = 1.205) -> np.ndarray:
        """
        Calculate the 2x2 Transfer Matrix [A, B; C, D] for this segment.

        Based on exact solution to Webster's horn equation for Hyperbolic profile.
        For the hyperbolic family, the curvature term r''/r = m² (constant),
        reducing the wave equation to ψ'' + (k² - m²)ψ = 0.

        Literature:
            - Mapes-Riordan (1993), Eq 13a-13d - Hyperbolic horn T-matrix
              with logarithmic gradient terms grad_in, grad_out
            - Kolbrek, "Horn Theory: An Introduction, Part 1 & 2"
            - Freehafer (1940) - Hyperbolic horn impedance solution
            - literature/horns/kolbrek_horn_theory_tutorial.md

        Theory:
            Effective wavenumber: μ = √(k² - m²)
            - Above cutoff (k > m): μ is real (propagating waves)
            - Below cutoff (k < m): μ is imaginary (evanescent waves)

            Logarithmic gradient: r'/r = m[sinh(mx) + T·cosh(mx)]/[cosh(mx) + T·sinh(mx)]
            - At throat (x=0): grad_in = m·T
            - At mouth (x=L): grad_out = m[sinh(mL) + T·cosh(mL)]/[cosh(mL) + T·sinh(mL)]

        Args:
            f: Frequency [Hz]
            c: Speed of sound [m/s]
            rho: Air density [kg/m³]

        Returns:
            2x2 np.ndarray of complex floats [[A, B], [C, D]]

        Notes:
            The T-matrix relates pressure and volume velocity at throat (port 1)
            to mouth (port 2): [p₁, U₁]ᵀ = [A B; C D][p₂, U₂]ᵀ

            Uses effective wavenumber k' = √(k² - m²).
            Below cutoff (k < m), k' becomes imaginary, handling reactive component.
        """
        k = 2 * np.pi * f / c
        L = self.length
        m = self.m

        # Characteristic parameters
        # mu is the complex propagation constant
        discriminant = k**2 - m**2

        if discriminant >= 0:
            mu = np.sqrt(discriminant)
            # Above cutoff (propagating)
            cos_mu_L = np.cos(mu * L)
            sin_mu_L = np.sin(mu * L)

            # Use sinc function for stability when mu -> 0 (cutoff)
            if mu < 1e-9:
                sinc_mu_L = L
            else:
                sinc_mu_L = sin_mu_L / mu
        else:
            # Below cutoff (evanescent)
            mu = np.sqrt(-discriminant)  # Real value
            cos_mu_L = np.cosh(mu * L)
            sin_mu_L = 1j * np.sinh(mu * L)  # Returns imaginary
            # Adjust sinc divisor to handle the imaginary mu properly
            sinc_mu_L = np.sinh(mu * L) / mu if mu > 1e-9 else L

        # Ratios of areas (used for impedance scaling)
        # p scales with 1/r, u scales with 1/r
        r_in = np.sqrt(self.throat_area)
        r_out = np.sqrt(self.mouth_area)

        # Calculating Derivatives of the shape function at boundaries
        # h(x) = cosh(mx) + T*sinh(mx). r(x) = r0 * h(x)
        # r'(x)/r(x) = m * (sinh(mx) + T*cosh(mx)) / h(x)
        #
        # At x=0 (throat): h(0)=1, h'(0)=m·T  → grad_in = m·T
        # At x=L (mouth): grad_out = m[sinh(mL) + T·cosh(mL)]/[cosh(mL) + T·sinh(mL)]

        def flare_grad(x_loc):
            h = np.cosh(m * x_loc) + self.T * np.sinh(m * x_loc)
            h_prime = m * (np.sinh(m * x_loc) + self.T * np.cosh(m * x_loc))
            return h_prime / h

        grad_in = flare_grad(0)      # = m·T (verified analytically)
        grad_out = flare_grad(L)     # = m[sinh(mL) + T·cosh(mL)]/[cosh(mL) + T·sinh(mL)]

        # Matrix Elements derivation from Mapes-Riordan (1993) Eq 13a-13d
        # Adapted for general Hypex shape function

        # A = (r_in/r_out) * (cos(mu L) - grad_in * sin(mu L)/mu)
        A = (r_in / r_out) * (cos_mu_L - grad_in * sinc_mu_L)

        # B = j * k * Z_scale / sqrt(S_in * S_out) * sinc_mu_L
        Z_scale = rho * c
        B = (1j * k * Z_scale / np.sqrt(self.throat_area * self.mouth_area)) * sinc_mu_L

        # D = (r_out/r_in) * (cos(mu L) + grad_out * sinc_mu_L)
        D = (r_out / r_in) * (cos_mu_L + grad_out * sinc_mu_L)

        # Calculate C using Determinant = 1 property for reciprocal passive system
        # AD - BC = 1  => C = (AD - 1)/B
        if abs(B) < 1e-12:
            # Special case: L=0 or resonance node. Fallback to limit.
            C = 0  # Approximation for safety
        else:
            C = (A * D - 1.0) / B

        return np.array([[A, B], [C, D]], dtype=complex)


@dataclass
class ConicalHorn:
    """
    A conical horn with linear radius expansion.

    The conical horn is the simplest horn geometry, consisting of a straight-sided
    cone. Unlike exponential horns, it expands linearly in radius and quadratically
    in area. It supports spherical wavefronts rather than the plane waves assumed
    in Webster's equation for exponential horns.

    Area function:
        S(x) = S_t * (1 + x/x0)^2

    Equivalently, using linear radius expansion:
        r(x) = r_t + (r_m - r_t) * (x/L)
        S(x) = π * r(x)^2

    where x0 is the distance from the projected apex to the throat.

    Literature:
        - Olson (1947), Section 5.15 - Conical horn geometry
        - Beranek (1954), Chapter 5 - Spherical wave horns
        - Kolbrek, "Horn Theory: An Introduction, Part 1" - T-matrix method
        - literature/horns/conical_theory.md

    Attributes:
        throat_area: Throat cross-sectional area [m²]
        mouth_area: Mouth cross-sectional area [m²]
        length: Axial length [m]
        x0: Distance from projected apex to throat [m] (calculated if not provided)

    Examples:
        >>> horn = ConicalHorn(
        ...     throat_area=0.005,  # 50 cm²
        ...     mouth_area=0.05,    # 500 cm²
        ...     length=0.5          # 50 cm
        ... )
        >>> horn.x0
        0.166...  # Distance from apex to throat

    Notes:
        Conical horns have NO sharp cutoff frequency (unlike exponential horns).
        Resistance rises gradually from zero frequency, providing wider bandwidth
        but less optimal loading at any specific frequency.
    """

    throat_area: float
    mouth_area: float
    length: float
    x0: Optional[float] = None

    def __post_init__(self):
        """Calculate x0 from geometry if not provided."""
        if self.throat_area <= 0 or self.mouth_area <= 0 or self.length <= 0:
            raise ValueError("All dimensions must be positive")

        if self.mouth_area <= self.throat_area:
            raise ValueError(
                f"Conical horn must expand (mouth_area > throat_area), "
                f"got mouth_area={self.mouth_area}, throat_area={self.throat_area}"
            )

        if self.x0 is None:
            # x0 = r_t * L / (r_m - r_t) from similar triangles
            # Or equivalently: x0 = L * sqrt(S_t) / (sqrt(S_m) - sqrt(S_t))
            r_t = np.sqrt(self.throat_area / np.pi)
            r_m = np.sqrt(self.mouth_area / np.pi)

            # Handle cylindrical case (no expansion)
            if abs(r_m - r_t) < 1e-9:
                self.x0 = np.inf
            else:
                self.x0 = (r_t * self.length) / (r_m - r_t)

    def throat_radius(self) -> float:
        """Calculate throat radius from throat area (assuming circular)."""
        return np.sqrt(self.throat_area / np.pi)

    def mouth_radius(self) -> float:
        """Calculate mouth radius from mouth area (assuming circular)."""
        return np.sqrt(self.mouth_area / np.pi)

    def area_at(self, x: float) -> float:
        """
        Calculate cross-sectional area at distance x from throat.

        S(x) = π * [r_t + (r_m - r_t) * (x/L)]^2

        Literature:
            - Olson (1947), Section 5.15 - Conical horn geometry
            - literature/horns/conical_theory.md

        Args:
            x: Axial distance from throat [m], 0 ≤ x ≤ length

        Returns:
            Cross-sectional area at position x [m²]
        """
        if x < 0 or x > self.length:
            raise ValueError(f"x must be in [0, {self.length}], got {x}")

        r_t = self.throat_radius()
        r_m = self.mouth_radius()
        r_x = r_t + (r_m - r_t) * (x / self.length)
        return np.pi * (r_x ** 2)

    def calculate_t_matrix(self, f: float, c: float = 343.2, rho: float = 1.205,
                           use_explicit_form: bool = True) -> np.ndarray:
        """
        Calculate the 2x2 Transfer Matrix [A, B; C, D] for this conical horn
        using spherical wave theory.

        Uses spherical Bessel functions to properly account for the spherical
        wavefronts in conical horns (not plane waves like exponential horns).

        Literature:
            - Olson (1947), Section 5.21 - Conical horn T-matrix
            - J.O. Smith, "Conical Acoustic Tubes", Physical Audio Signal Processing
              https://ccrma.stanford.edu/~jos/pasp/Conical_Acoustic_Tubes.html
            - Pierce, A.D., Acoustics, Eq. 7-6.2
            - literature/horns/conical_theory.md

        Theory:
            For a conical horn, Webster's equation solution is in terms of spherical
            Bessel functions. The state vector V(r) = [p(r), U(r)]ᵀ is:

                V(r) = M(r) * [C₁, C₂]ᵀ

            where M(r) is constructed from spherical Bessel functions:
                p(r) = C₁·j₀(kr) + C₂·y₀(kr)
                U(r) = (S/jρc) · [C₁·j₁(kr) + C₂·y₁(kr)]

            The T-matrix relates throat to mouth: V_throat = T · V_mouth
            where T = M(r_throat) · M(r_mouth)⁻¹

            This implementation uses explicit ABCD formulas derived from the
            Wronskian identity: j₀(z)y₁(z) - j₁(z)y₀(z) = -z⁻²

            This provides better numerical stability than matrix inversion
            at low frequencies where spherical Bessel functions become singular.

        Args:
            f: Frequency [Hz]
            c: Speed of sound [m/s]
            rho: Air density [kg/m³]
            use_explicit_form: If True (default), use explicit ABCD formulas
                derived from Wronskian. If False, use numerical matrix inversion.

        Returns:
            2x2 np.ndarray of complex floats [[A, B], [C, D]]

        Notes:
            The T-matrix relates pressure and volume velocity at throat (port 1)
            to mouth (port 2): [p₁, U₁]ᵀ = [A B; C D][p₂, U₂]ᵀ

            Pressure scales as 1/r for spherical waves (not √S as in plane waves).
            This is the KEY difference from exponential horns.

        Examples:
            >>> horn = ConicalHorn(throat_area=0.015, mouth_area=0.15, length=1.2)
            >>> T = horn.calculate_t_matrix(1000.0)
            >>> det = np.linalg.det(T)
            >>> abs(det - 1.0) < 1e-6  # Reciprocal network
            True
        """
        from scipy import special

        k = 2 * np.pi * f / c
        L = self.length
        S_t = self.throat_area
        S_m = self.mouth_area

        # Handle DC limit (very small k)
        if k * L < 1e-4:
            # Identity matrix for DC
            return np.array([[1.0, 0.0], [0.0, 1.0]], dtype=complex)

        # Get x0 (distance from apex to throat)
        x0 = self.x0

        # Handle cylindrical case (no expansion)
        if np.isinf(x0):
            # Plane wave propagation (cylindrical pipe)
            Z_c = (rho * c) / S_t
            cos_kl = np.cos(k * L)
            sin_kl = np.sin(k * L)
            return np.array([
                [cos_kl, 1j * Z_c * sin_kl],
                [1j * (1 / Z_c) * sin_kl, cos_kl]
            ], dtype=complex)

        # Conical case (Spherical Wave)
        r1 = x0  # Throat radius from apex
        r2 = x0 + L  # Mouth radius from apex
        kr1 = k * r1
        kr2 = k * r2

        # Calculate spherical Bessel functions at throat and mouth
        j0_1 = special.spherical_jn(0, kr1)
        j1_1 = special.spherical_jn(1, kr1)
        y0_1 = special.spherical_yn(0, kr1)
        y1_1 = special.spherical_yn(1, kr1)

        j0_2 = special.spherical_jn(0, kr2)
        j1_2 = special.spherical_jn(1, kr2)
        y0_2 = special.spherical_yn(0, kr2)
        y1_2 = special.spherical_yn(1, kr2)

        # Characteristic impedance of medium
        Z0 = rho * c

        if use_explicit_form:
            # Use explicit ABCD formulas derived from Wronskian
            # This is numerically stable at low frequencies
            #
            # The Wronskian for spherical Bessel functions:
            # W{j₀, y₀}(z) = j₀(z)y₁(z) - j₁(z)y₀(z) = -z⁻²
            #
            # Using this identity, we can derive explicit formulas for the
            # T-matrix elements without numerical matrix inversion:
            #
            # Let A_ij = j_i(kr₁)y_j(kr₂) - y_i(kr₁)j_j(kr₂)
            #
            # Then the T-matrix elements are:
            # A = -(kr₂)² · A₀₀
            # B = (jZ₀/S_m)(kr₂)² · [j₀(kr₁)y₀(kr₂) - j₀(kr₂)y₀(kr₁)]
            # C = -(S_t/jZ₀)(kr₂)² · A₁₁
            # D = (S_t/S_m)(r₁/r₂) · [j₀(kr₂)y₁(kr₁) - j₁(kr₁)y₀(kr₂)]

            # Cross products needed for T-matrix elements
            A_00 = j0_1 * y1_2 - y0_1 * j1_2  # j₀(kr₁)y₁(kr₂) - y₀(kr₁)j₁(kr₂)
            A_01 = j0_1 * y0_2 - y0_1 * j0_2  # j₀(kr₁)y₀(kr₂) - y₀(kr₁)j₀(kr₂)
            A_11 = j1_1 * y1_2 - y1_1 * j1_2  # j₁(kr₁)y₁(kr₂) - y₁(kr₁)j₁(kr₂)
            A_10 = j0_2 * y1_1 - j1_1 * y0_2  # j₀(kr₂)y₁(kr₁) - j₁(kr₁)y₀(kr₂)

            # Prefactors
            kr2_sq = (kr2) ** 2
            impedance_scale_t = S_t / (1j * Z0)
            impedance_scale_m = S_m / (1j * Z0)

            # T-matrix elements (explicit formulas using Wronskian)
            # All elements scale with (kr2)² for consistency
            A = -kr2_sq * A_00
            B = (1j * Z0 / S_m) * kr2_sq * A_01
            C = -(impedance_scale_t) * kr2_sq * A_11
            D = -kr2_sq * (S_t / S_m) * A_10

        else:
            # Legacy method: numerical matrix inversion
            # This is retained for testing/validation purposes
            u_scale_t = S_t / (1j * rho * c)
            u_scale_m = S_m / (1j * rho * c)

            M_throat = np.array([
                [j0_1, y0_1],
                [u_scale_t * j1_1, u_scale_t * y1_1]
            ], dtype=complex)

            M_mouth = np.array([
                [j0_2, y0_2],
                [u_scale_m * j1_2, u_scale_m * y1_2]
            ], dtype=complex)

            M_mouth_inv = np.linalg.inv(M_mouth)
            T = np.matmul(M_throat, M_mouth_inv)

            A, B = T[0, 0], T[0, 1]
            C, D = T[1, 0], T[1, 1]

        return np.array([[A, B], [C, D]], dtype=complex)


@dataclass
class HornSegment:
    """
    Single segment of a multi-segment horn with exponential flare.

    Each segment has constant flare constant m, defining an exponential
    expansion from throat to mouth of that segment.

    Literature:
        - Olson (1947), Eq. 5.12 - Exponential horn profile
        - Kolbrek Part 1 - Multi-segment horns via T-matrix chaining
        - literature/horns/olson_1947.md

    Attributes:
        throat_area: Throat cross-sectional area of this segment (m²)
        mouth_area: Mouth cross-sectional area of this segment (m²)
        length: Axial length of this segment (m)
        flare_constant: Flare constant m (1/m), calculated from geometry
                      if not provided. m = (1/L) · ln(S_mouth/S_throat)

    Examples:
        >>> segment = HornSegment(
        ...     throat_area=0.001,  # 10 cm²
        ...     mouth_area=0.01,    # 100 cm²
        ...     length=0.5          # 50 cm
        ... )
        >>> segment.flare_constant
        4.605...  # 1/m
    """

    throat_area: float
    mouth_area: float
    length: float
    flare_constant: Optional[float] = None

    def __post_init__(self):
        """Calculate flare constant from geometry if not provided."""
        if self.flare_constant is None:
            # Olson (1947), Chapter 5: m = (1/L) · ln(S_m/S_t)
            self.flare_constant = np.log(self.mouth_area / self.throat_area) / self.length

    def throat_radius(self) -> float:
        """Calculate throat radius from throat area (assuming circular)."""
        return np.sqrt(self.throat_area / np.pi)

    def mouth_radius(self) -> float:
        """Calculate mouth radius from mouth area (assuming circular)."""
        return np.sqrt(self.mouth_area / np.pi)

    def area_at(self, x: float) -> float:
        """
        Calculate cross-sectional area at distance x from segment throat.

        S(x) = S_throat · exp(m·x)

        Args:
            x: Axial distance from segment throat (m), 0 ≤ x ≤ length

        Returns:
            Cross-sectional area at position x (m²)
        """
        return self.throat_area * np.exp(self.flare_constant * x)

    def calculate_t_matrix(self, f: float, c: float = 343.2, rho: float = 1.205) -> np.ndarray:
        """
        Calculate the 2x2 Transfer Matrix [A, B; C, D] for exponential segment.

        This provides a consistent interface with HyperbolicHorn for multi-segment
        horn simulation. For exponential segments, this uses the Kolbrek convention
        for T-matrix calculations.

        Literature:
            - Kolbrek, "Horn Theory: An Introduction, Part 1"
            - Olson (1947), Chapter 5 - Exponential horn theory
            - literature/horns/kolbrek_horn_theory_tutorial.md

        Args:
            f: Frequency [Hz]
            c: Speed of sound [m/s]
            rho: Air density [kg/m³]

        Returns:
            2x2 np.ndarray of complex floats [[A, B], [C, D]]

        Notes:
            The T-matrix relates pressure and volume velocity at throat (port 1)
            to mouth (port 2): [p₁, U₁]ᵀ = [A B; C D][p₂, U₂]ᵀ

            Uses effective wavenumber k' = √(k² - m²).
            Below cutoff (k < m), k' becomes imaginary.
        """
        # Convert to Kolbrek convention (m_kolbrek = m_olson / 2)
        m = self.flare_constant / 2.0
        k = 2 * np.pi * f / c
        L = self.length
        S1 = self.throat_area
        S2 = self.mouth_area
        z_rc = rho * c

        # γ = √(k² - m²), can be real or imaginary
        gamma_squared = k**2 - m**2
        gamma = np.sqrt(gamma_squared.astype(complex))

        gL = gamma * L
        emL = np.exp(m * L)

        # Handle near-cutoff singularity (γ → 0)
        near_cutoff = np.abs(gL) < 1e-8

        if near_cutoff:
            # Use small angle approximation: sin(x) ≈ x for x → 0
            sin_gL = gL
            cos_gL = 1.0
            m_over_gamma = m * L
            k_over_gamma = k * L
        else:
            sin_gL = np.sin(gL)
            cos_gL = np.cos(gL)
            m_over_gamma = m / gamma
            k_over_gamma = k / gamma

        # T-matrix elements (Kolbrek convention)
        A = emL * (cos_gL - m_over_gamma * sin_gL)
        B = emL * 1j * (z_rc / S2) * k_over_gamma * sin_gL
        C = emL * 1j * (S1 / z_rc) * k_over_gamma * sin_gL
        D = emL * (S1 / S2) * (cos_gL + m_over_gamma * sin_gL)

        return np.array([[A, B], [C, D]], dtype=complex)


@dataclass
class MultiSegmentHorn:
    """
    Horn composed of multiple horn segments (exponential, hyperbolic, or mixed).

    A multi-segment horn allows approximating arbitrary horn profiles
    by chaining together segments with different flare constants and profiles.
    This enables discovery of optimal profiles beyond standard exponential,
    tractrix, or hyperbolic shapes.

    Literature:
        - Kolbrek Part 1 - T-matrix chaining for multi-segment horns
        - Olson (1947), Chapter 8 - Compound horns
        - literature/horns/kolbrek_horn_theory_tutorial.md

    Attributes:
        segments: List of horn segments (HornSegment or HyperbolicHorn),
                  ordered from throat to mouth. Each segment's mouth must
                  match next segment's throat.

    Examples:
        >>> from gsd.simulation.types import HornSegment, HyperbolicHorn
        >>> segment1 = HornSegment(throat_area=0.001, mouth_area=0.01, length=0.3)
        >>> segment2 = HyperbolicHorn(throat_area=0.01, mouth_area=0.1, length=0.6, T=0.7)
        >>> horn = MultiSegmentHorn(segments=[segment1, segment2])
        >>> horn.total_length()
        0.9
        >>> horn.throat_area
        0.001
        >>> horn.mouth_area
        0.1
    """

    segments: List[Union['HornSegment', 'HyperbolicHorn', 'ConicalHorn']]

    def __post_init__(self):
        """Validate segment continuity."""
        if len(self.segments) < 1:
            raise ValueError("MultiSegmentHorn must have at least one segment")

        # Check that segments are continuous (mouth area matches next throat)
        for i in range(len(self.segments) - 1):
            if not np.isclose(self.segments[i].mouth_area, self.segments[i + 1].throat_area):
                raise ValueError(
                    f"Segment {i} mouth area ({self.segments[i].mouth_area}) "
                    f"must match segment {i+1} throat area ({self.segments[i+1].throat_area})"
                )

    @property
    def throat_area(self) -> float:
        """Overall horn throat area (m²)."""
        return self.segments[0].throat_area

    @property
    def mouth_area(self) -> float:
        """Overall horn mouth area (m²)."""
        return self.segments[-1].mouth_area

    @property
    def num_segments(self) -> int:
        """Number of segments in the horn."""
        return len(self.segments)

    def total_length(self) -> float:
        """Calculate total horn length (sum of all segments)."""
        return sum(seg.length for seg in self.segments)

    def throat_radius(self) -> float:
        """Calculate overall horn throat radius (assuming circular)."""
        return np.sqrt(self.throat_area / np.pi)

    def mouth_radius(self) -> float:
        """Calculate overall horn mouth radius (assuming circular)."""
        return np.sqrt(self.mouth_area / np.pi)

    def area_at(self, x: float) -> float:
        """
        Calculate cross-sectional area at distance x from overall horn throat.

        Finds the appropriate segment and calculates area within that segment.

        Args:
            x: Axial distance from horn throat (m), 0 ≤ x ≤ total_length()

        Returns:
            Cross-sectional area at position x (m²)
        """
        if x < 0 or x > self.total_length():
            raise ValueError(f"x={x} is outside horn length [0, {self.total_length()}]")

        # Find which segment contains position x
        cumulative_length = 0.0
        for segment in self.segments:
            if x <= cumulative_length + segment.length:
                # x is within this segment
                x_local = x - cumulative_length
                return segment.area_at(x_local)
            cumulative_length += segment.length

        # Shouldn't reach here if x is within bounds
        return self.mouth_area

    def segment_boundaries(self) -> List[float]:
        """
        Get axial positions of segment boundaries.

        Returns:
            List of positions [0, L1, L1+L2, ..., total_length]
        """
        boundaries = [0.0]
        cumulative_length = 0.0
        for segment in self.segments:
            cumulative_length += segment.length
            boundaries.append(cumulative_length)
        return boundaries


@dataclass
class TappedHorn:
    """
    Tapped horn geometry with driver mounted at tap point.

    A tapped horn divides the horn path into upstream (throat-side) and downstream
    (mouth-side) sections. The driver's front radiates into the upstream section
    (closed throat), while the rear radiates into the downstream section (open mouth).
    Both paths combine at the mouth, creating unique interference characteristics
    that enable efficient low-frequency reproduction in a compact enclosure.

    Hornresp Compatibility:
        Hornresp requires at least 3 segments for tapped horns:
        - S1 (throat) → S2 (tap point, driver location)
        - S2 → S3 (intermediate point)
        - S3 → S4 (mouth)

        To match Hornresp's 3-segment model, specify the intermediate_area
        parameter. The downstream_length will be split proportionally between
        the two segments based on the area ratios.

    Literature:
        Berzborn, M. & Smithers, M. (2018). "An Acoustic Model of the Tapped Horn
        Loudspeaker." AES Convention Paper 10047.

        Danley, T.J. (2013). US Patent 8,457,341 B2: "Sound reproduction with
        improved low frequency characteristics."

        Kolbrek, B. "Horn Loudspeaker Simulation" series.
        https://kolbrek.hornspeakersystems.info/

        literature/horns/tapped_horn_theory.md

    Attributes:
        upstream_throat_area: Cross-sectional area at closed throat S1 (cm²)
        tap_area: Cross-sectional area at driver location S2 (cm²)
        downstream_mouth_area: Cross-sectional area at mouth S4 (cm²)
        upstream_length: Length from throat to driver L12 (cm)
        downstream_length: Total length from driver to mouth L23+L34 (cm)
        upstream_profile: Expansion profile for upstream section ('exponential' or 'conical')
        downstream_profile: Expansion profile for downstream section ('exponential' or 'conical')
        intermediate_area: Optional intermediate area S3 (cm²) for 3-segment downstream
        flow_resistivity: Internal damping material flow resistivity (Pa·s/m²)
            - 0: Undamped (no batting)
            - 400-800: Light batting for tapped horn subwoofers (20-200 Hz)
                        (σ=500 gives ~12 dB notch depth, typical for commercial TH)
            - 2000-4000: Polyester batting (for mid/high frequency applications)
            - 5000-10000: Fiberglass insulation
            - 20000+: Carpet/felt (very high damping)

        Note: Tapped horn subwoofers require MUCH lower flow resistivity than
        room acoustics applications. The Miki model was designed for higher
        frequencies (>500 Hz). For 20-200 Hz range, use σ ≈ 500 Pa·s/m²
        for realistic 10-15 dB notch depth (calibrated against commercial
        designs like Danley TH-115, Labhorn).

    Examples:
        >>> # 2-segment tapped horn (not Hornresp compatible)
        >>> th = TappedHorn(
        ...     upstream_throat_area=50.0,
        ...     tap_area=200.0,
        ...     downstream_mouth_area=2000.0,
        ...     upstream_length=40.0,
        ...     downstream_length=150.0,
        ... )
        >>> # 3-segment tapped horn (Hornresp compatible)
        >>> th = TappedHorn(
        ...     upstream_throat_area=150.0,
        ...     tap_area=855.0,
        ...     downstream_mouth_area=6000.0,
        ...     upstream_length=180.0,
        ...     downstream_length=200.0,
        ...     intermediate_area=2265.0,  # S3 for 3-segment model
        ... )
        >>> th.total_length
        380.0  # cm
        >>> th.downstream_segments()  # Returns 2 ExponentialHorn segments
    """

    upstream_throat_area: float  # cm² (S1)
    tap_area: float  # cm² (S2)
    downstream_mouth_area: float  # cm² (S4)
    upstream_length: float  # cm (L12)
    downstream_length: float  # cm (L23 + L34)
    upstream_profile: str = 'exponential'  # 'exponential' or 'conical'
    downstream_profile: str = 'exponential'  # 'exponential' or 'conical'
    intermediate_area: float = None  # cm² (S3), optional for 3-segment model
    flow_resistivity: float = 0.0  # Pa·s/m² (Rayls/m) - Internal damping (0=undamped)

    def __post_init__(self):
        """Validate tapped horn parameters."""
        if self.upstream_throat_area <= 0:
            raise ValueError("upstream_throat_area must be positive")
        if self.tap_area <= 0:
            raise ValueError("tap_area must be positive")
        if self.downstream_mouth_area <= 0:
            raise ValueError("downstream_mouth_area must be positive")
        if self.upstream_length <= 0:
            raise ValueError("upstream_length must be positive")
        if self.downstream_length <= 0:
            raise ValueError("downstream_length must be positive")
        if self.upstream_profile not in ('exponential', 'conical'):
            raise ValueError("upstream_profile must be 'exponential' or 'conical'")
        if self.downstream_profile not in ('exponential', 'conical'):
            raise ValueError("downstream_profile must be 'exponential' or 'conical'")

        # Validate flow_resistivity (can be zero for undamped)
        if self.flow_resistivity < 0:
            raise ValueError("flow_resistivity must be >= 0 (0 = undamped)")

        # Validate area expansion (must be monotonic)
        if self.tap_area <= self.upstream_throat_area:
            raise ValueError(
                f"tap_area ({self.tap_area}) must be > upstream_throat_area "
                f"({self.upstream_throat_area})"
            )
        if self.downstream_mouth_area <= self.tap_area:
            raise ValueError(
                f"downstream_mouth_area ({self.downstream_mouth_area}) must be > tap_area "
                f"({self.tap_area})"
            )

        # Validate intermediate area (if specified)
        if self.intermediate_area is not None:
            if self.intermediate_area <= self.tap_area:
                raise ValueError(
                    f"intermediate_area ({self.intermediate_area}) must be > tap_area "
                    f"({self.tap_area})"
                )
            if self.downstream_mouth_area <= self.intermediate_area:
                raise ValueError(
                    f"downstream_mouth_area ({self.downstream_mouth_area}) must be > intermediate_area "
                    f"({self.intermediate_area})"
                )

    @property
    def total_length(self) -> float:
        """Total acoustic path length from throat to mouth (cm)."""
        return self.upstream_length + self.downstream_length

    @property
    def quarter_wave_frequency(self) -> float:
        """
        Approximate quarter-wave resonance frequency (Hz).

        Based on upstream section length where λ/4 = upstream_length.
        This is the frequency where the tapped horn's unique interference
        characteristics are most pronounced.

        Literature:
            Danley, US Patent 8,457,341 B2 - Quarter-wave resonance operation

        Returns:
            Quarter-wave frequency in Hz (using c = 34400 cm/s)
        """
        c = 34400  # Speed of sound in cm/s (344 m/s)
        return c / (4 * self.upstream_length)

    def upstream_section(self) -> 'Union[ExponentialHorn, ConicalHorn]':
        """
        Get upstream horn section as a horn object.

        Converts area units from cm² to m² and length from cm to m for
        compatibility with existing horn simulation functions.

        Returns:
            ExponentialHorn or ConicalHorn representing upstream section
        """
        # Convert to m² and m
        throat_area = self.upstream_throat_area * 1e-4
        mouth_area = self.tap_area * 1e-4
        length = self.upstream_length * 1e-2

        if self.upstream_profile == 'exponential':
            from gsd.simulation.types import ExponentialHorn
            return ExponentialHorn(
                throat_area=throat_area,
                mouth_area=mouth_area,
                length=length
            )
        else:  # conical
            from gsd.simulation.types import ConicalHorn
            return ConicalHorn(
                throat_area=throat_area,
                mouth_area=mouth_area,
                length=length
            )

    def downstream_section(self) -> 'Union[ExponentialHorn, ConicalHorn]':
        """
        Get downstream horn section as a single horn object.

        Converts area units from cm² to m² and length from cm to m for
        compatibility with existing horn simulation functions.

        Note: If intermediate_area is specified (3-segment model), this
        returns a single equivalent segment spanning the full downstream length.
        For proper 3-segment modeling, use downstream_segments() instead.

        Returns:
            ExponentialHorn or ConicalHorn representing downstream section
        """
        # Convert to m² and m
        throat_area = self.tap_area * 1e-4
        mouth_area = self.downstream_mouth_area * 1e-4
        length = self.downstream_length * 1e-2

        if self.downstream_profile == 'exponential':
            from gsd.simulation.types import ExponentialHorn
            return ExponentialHorn(
                throat_area=throat_area,
                mouth_area=mouth_area,
                length=length
            )
        else:  # conical
            from gsd.simulation.types import ConicalHorn
            return ConicalHorn(
                throat_area=throat_area,
                mouth_area=mouth_area,
                length=length
            )

    def downstream_segments(self) -> list:
        """
        Get downstream horn sections as a list of horn objects.

        For 2-segment model (no intermediate_area), returns a single segment.
        For 3-segment model (intermediate_area specified), returns two segments
        matching Hornresp's S2→S3→S4 topology.

        The downstream_length is split proportionally between segments based
        on the logarithmic area expansion (matching Hornresp's approach).

        Returns:
            List of ExponentialHorn or ConicalHorn segments

        Examples:
            >>> th = TappedHorn(
            ...     upstream_throat_area=150.0,
            ...     tap_area=855.0,
            ...     downstream_mouth_area=6000.0,
            ...     upstream_length=180.0,
            ...     downstream_length=200.0,
            ...     intermediate_area=2265.0,
            ... )
            >>> segments = th.downstream_segments()
            >>> len(segments)
            2
            >>> segments[0].throat_area * 1e4  # cm²
            855.0
            >>> segments[0].mouth_area * 1e4   # cm²
            2265.0
            >>> segments[1].throat_area * 1e4  # cm²
            2265.0
            >>> segments[1].mouth_area * 1e4   # cm²
            6000.0
        """
        if self.intermediate_area is None:
            # 2-segment model: single downstream segment
            return [self.downstream_section()]

        # 3-segment model: split downstream_length into two segments
        # Hornresp splits the length proportionally to the logarithmic area expansion
        import numpy as np

        # Calculate logarithmic area ratios
        log_total = np.log(self.downstream_mouth_area / self.tap_area)
        log_seg1 = np.log(self.intermediate_area / self.tap_area)
        log_seg2 = np.log(self.downstream_mouth_area / self.intermediate_area)

        # Split length proportionally
        length1 = self.downstream_length * (log_seg1 / log_total)
        length2 = self.downstream_length * (log_seg2 / log_total)

        # Convert to m² and m
        throat_area_1 = self.tap_area * 1e-4
        mouth_area_1 = self.intermediate_area * 1e-4
        length_1 = length1 * 1e-2

        throat_area_2 = self.intermediate_area * 1e-4
        mouth_area_2 = self.downstream_mouth_area * 1e-4
        length_2 = length2 * 1e-2

        if self.downstream_profile == 'exponential':
            from gsd.simulation.types import ExponentialHorn
            seg1 = ExponentialHorn(
                throat_area=throat_area_1,
                mouth_area=mouth_area_1,
                length=length_1
            )
            seg2 = ExponentialHorn(
                throat_area=throat_area_2,
                mouth_area=mouth_area_2,
                length=length_2
            )
            return [seg1, seg2]
        else:  # conical
            from gsd.simulation.types import ConicalHorn
            seg1 = ConicalHorn(
                throat_area=throat_area_1,
                mouth_area=mouth_area_1,
                length=length_1
            )
            seg2 = ConicalHorn(
                throat_area=throat_area_2,
                mouth_area=mouth_area_2,
                length=length_2
            )
            return [seg1, seg2]


@dataclass
class FrequencyResponse:
    """
    Frequency response data for a horn or driver.

    Stores complex impedance or pressure response across frequency.

    Attributes:
        frequencies: Array of frequency points (Hz)
        impedance: Complex impedance at each frequency (Ω)
        magnitude: Impedance magnitude |Z| (Ω)
        phase: Impedance phase in degrees

    Examples:
        >>> response = FrequencyResponse(
        ...     frequencies=np.array([20, 50, 100, 200, 500]),
        ...     impedance=np.array([10+5j, 15+3j, 20+1j, 25+0.5j, 30+0.1j])
        ... )
        >>> response.magnitude[0]
        11.18...  # |10 + 5j|
    """

    frequencies: np.ndarray
    impedance: np.ndarray
    magnitude: Optional[np.ndarray] = None
    phase: Optional[np.ndarray] = None

    def __post_init__(self):
        """Calculate magnitude and phase from complex impedance."""
        if self.magnitude is None:
            self.magnitude = np.abs(self.impedance)
        if self.phase is None:
            self.phase = np.angle(self.impedance, deg=True)


@dataclass
class SimulationResult:
    """
    Container for simulation results with metadata.

    Attributes:
        horn: Horn geometry used in simulation (ExponentialHorn, HyperbolicHorn,
              ConicalHorn, or MultiSegmentHorn)
        frequencies: Frequency array (Hz)
        throat_impedance: Complex throat impedance at each frequency (Ω)
        radiation_impedance: Radiation impedance at mouth (Ω)
        cutoff_frequency: Horn cutoff frequency (Hz), if applicable

    Examples:
        >>> result = SimulationResult(
        ...     horn=ExponentialHorn(0.001, 0.1, 1.5),
        ...     frequencies=np.logspace(1, 4, 100),
        ...     throat_impedance=z_array,
        ...     radiation_impedance=z_rad,
        ...     cutoff_frequency=50.0
        ... )
    """

    horn: Union[ExponentialHorn, HyperbolicHorn, ConicalHorn, MultiSegmentHorn]
    frequencies: np.ndarray
    throat_impedance: np.ndarray
    radiation_impedance: Optional[np.ndarray] = None
    cutoff_frequency: Optional[float] = None
