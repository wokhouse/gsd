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

    # Get downstream horn segments (handles both 2-segment and 3-segment models)
    downstream_segments = tapped_horn.downstream_segments()

    # Calculate mouth radiation impedance (from last segment's mouth area)
    z_rad = circular_piston_radiation_impedance(
        frequencies, downstream_segments[-1].mouth_area, medium
    )

    # Chain T-matrices for all downstream segments
    a, b, c, d = _chain_tmatrices(frequencies, downstream_segments, medium)

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


def _chain_tmatrices(
    frequencies: NDArray[np.float64],
    segments: list,
    medium: MediumProperties,
) -> tuple:
    """Chain T-matrices for multiple horn segments.

    For a list of N horn segments, chains their T-matrices:
        T_total = T_1 * T_2 * ... * T_N

    Literature:
        Kolbrek, "Horn Theory: An Introduction, Part 3" - Multi-segment horns

    Args:
        frequencies: Array of frequencies in Hz
        segments: List of ExponentialHorn or ConicalHorn segments
        medium: Acoustic medium properties

    Returns:
        Tuple of (A, B, C, D) arrays for the combined T-matrix

    Examples:
        >>> seg1 = ExponentialHorn(0.01, 0.02, 1.0)
        >>> seg2 = ExponentialHorn(0.02, 0.05, 1.5)
        >>> a, b, c, d = _chain_tmatrices(np.array([100.0]), [seg1, seg2], MediumProperties())
    """
    if len(segments) == 0:
        raise ValueError("segments list cannot be empty")

    frequencies = np.atleast_1d(frequencies).astype(float)

    # Initialize with identity matrix
    A = np.ones(len(frequencies), dtype=complex)
    B = np.zeros(len(frequencies), dtype=complex)
    C = np.zeros(len(frequencies), dtype=complex)
    D = np.ones(len(frequencies), dtype=complex)

    # Chain T-matrices: T_total = T_1 * T_2 * ... * T_N
    for seg in segments:
        if isinstance(seg, ExponentialHorn):
            a_seg, b_seg, c_seg, d_seg = exponential_horn_tmatrix(
                frequencies, seg, medium
            )
        elif isinstance(seg, ConicalHorn):
            # Conical horns use calculate_t_matrix method (single frequency)
            a_seg = np.zeros(len(frequencies), dtype=complex)
            b_seg = np.zeros(len(frequencies), dtype=complex)
            c_seg = np.zeros(len(frequencies), dtype=complex)
            d_seg = np.zeros(len(frequencies), dtype=complex)

            for i, f in enumerate(frequencies):
                T = seg.calculate_t_matrix(f, medium.c, medium.rho)
                a_seg[i], b_seg[i], c_seg[i], d_seg[i] = T[0, 0], T[0, 1], T[1, 0], T[1, 1]
        else:
            raise ValueError(f"Unsupported horn type: {type(seg)}")

        # Multiply: T_new = T_old * T_seg
        # [A B; C D] * [a_seg b_seg; c_seg d_seg]
        # = [A*a_seg + B*c_seg, A*b_seg + B*d_seg]
        #   [C*a_seg + D*c_seg, C*b_seg + D*d_seg]
        A_new = A * a_seg + B * c_seg
        B_new = A * b_seg + B * d_seg
        C_new = C * a_seg + D * c_seg
        D_new = C * b_seg + D * d_seg

        A, B, C, D = A_new, B_new, C_new, D_new

    return A, B, C, D


def tapped_horn_system_response(
    frequencies: NDArray[np.float64],
    tapped_horn: TappedHorn,
    driver,
    medium: MediumProperties = None,
    voltage: float = 2.83,
) -> dict:
    """Calculate complete tapped horn system response.

    Implements the electro-mechano-acoustical coupling for tapped horns,
    including electrical impedance, SPL output, cone excursion, and efficiency.

    Literature:
        Berzborn, M. & Smithers, M. (2018). "An Acoustic Model of the Tapped Horn
        Loudspeaker." AES Convention Paper 10047, Eq. 10-16.

        Danley, T.J. (2013). US Patent 8,457,341 B2 - Driver coupling to tap point

        Small (1972) - Electromechanical analogies for horn-loaded drivers
        literature/horns/tapped_horn_theory.md

    Electromechanical model:
        Acoustic domain:
            Z_acoustic = Z_up ∥ Z_down (parallel combination at tap point)

        Mechanical domain:
            Z_mechanical_acoustic = Z_acoustic × S_d² (acoustic to mechanical)
            Z_mechanical_driver = R_ms + jωM_md + 1/(jωC_ms)
            Z_mechanical_total = Z_mechanical_driver + Z_mechanical_acoustic

        Electrical domain:
            Z_mot = (BL)² / Z_mechanical_total (motional impedance)
            Z_voice_coil = R_e + jωL_e
            Z_electrical = Z_voice_coil + Z_mot

    Args:
        frequencies: Array of frequencies in Hz
        tapped_horn: TappedHorn geometry specification
        driver: ThieleSmallParameters driver parameters
        medium: Acoustic medium properties. If None, uses default MediumProperties().
        voltage: Input voltage (V), default 2.83V (1W into 8Ω)

    Returns:
        Dictionary with keys:
        - 'frequencies': Frequency array (Hz)
        - 'electrical_impedance': Electrical impedance magnitude (Ω)
        - 'electrical_impedance_phase': Electrical impedance phase (degrees)
        - 'acoustic_impedance': Acoustic impedance at tap point (Pa·s/m³)
        - 'spl': SPL at 1m (dB)
        - 'excursion': Cone excursion (mm)
        - 'efficiency': Reference efficiency (%)
        - 'diaphragm_velocity': Diaphragm velocity magnitude (m/s)

    Raises:
        ValueError: If invalid parameters

    Examples:
        >>> import numpy as np
        >>> from gsd.simulation.types import TappedHorn
        >>> from gsd.driver import load_driver
        >>> driver = load_driver("BC_15PS100")
        >>> th = TappedHorn(
        ...     upstream_throat_area=150.0,
        ...     tap_area=855.0,
        ...     downstream_mouth_area=6000.0,
        ...     upstream_length=180.0,
        ...     downstream_length=200.0,
        ... )
        >>> freqs = np.array([40.0, 50.0, 100.0])
        >>> result = tapped_horn_system_response(freqs, th, driver)
        >>> result['spl'].shape
        (3,)

    Validation:
        Compare with Hornresp simulation at:
        tests/validation/drivers/bc_15ps100/tapped_horn/simulation.txt

        Expected accuracy:
        - SPL: <1 dB in passband (40-200 Hz)
        - Ze: <5% at impedance peaks
        - Xd: <5% deviation
    """
    if medium is None:
        medium = MediumProperties()

    frequencies = np.atleast_1d(frequencies).astype(float)
    omega = 2 * np.pi * frequencies

    # Step 1: Calculate acoustic impedance at tap point
    # This is the parallel combination: Z_tap = Z_up || Z_down
    z_acoustic = tapped_horn_tap_impedance(frequencies, tapped_horn, medium)

    # Step 2: Convert acoustic impedance to mechanical impedance
    # Z_mechanical = Z_acoustic × S_d²
    # For tapped horns, the driver area S_d is the coupling area at the tap point
    z_mechanical_acoustic = z_acoustic * (driver.S_d ** 2)

    # Step 3: Calculate driver mechanical impedance
    # Z_mech_driver = R_ms + jωM_md + 1/(jωC_ms)
    # Literature: Small (1972), Beranek (1954), COMSOL (2020)
    z_mech_stiffness = 1.0 / (1j * omega * driver.C_ms)
    z_mech_mass = 1j * omega * driver.M_md
    z_mech_resistance = driver.R_ms

    z_mechanical_driver = z_mech_resistance + z_mech_mass + z_mech_stiffness

    # Step 4: Total mechanical impedance
    z_mechanical_total = z_mechanical_driver + z_mechanical_acoustic

    # Step 5: Calculate electrical impedance
    # Motional impedance: Z_mot = (BL)² / Z_mechanical_total
    # Voice coil impedance: Z_vc = R_e + jωL_e
    # Total: Z_e = Z_vc + Z_mot
    # Literature: Small (1972), COMSOL (2020), Figure 2

    # Avoid division by zero in motional impedance
    with np.errstate(divide='ignore', invalid='ignore'):
        z_motional = (driver.BL ** 2) / z_mechanical_total
        z_motional = np.where(np.abs(z_mechanical_total) == 0, 0, z_motional)

    z_voice_coil = driver.R_e + 1j * omega * driver.L_e
    z_electrical = z_voice_coil + z_motional

    # Step 6: Calculate diaphragm velocity
    # I = V / Z_e (electrical current)
    # F = BL × I (force on voice coil)
    # v_d = F / Z_mechanical_total (diaphragm velocity)
    current = voltage / z_electrical
    force = driver.BL * current
    v_diaphragm = force / z_mechanical_total

    # Step 7: Calculate volume velocity at tap point
    # For tapped horn: U_tap = v_d × S_d
    # The volume velocity splits between upstream and downstream sections
    u_tap = v_diaphragm * driver.S_d

    # Step 8: Propagate to mouth for SPL calculation
    # We need to find the pressure at the mouth using T-matrix transformation
    # Get downstream horn segments (handles both 2-segment and 3-segment models)
    downstream_segments = tapped_horn.downstream_segments()

    # Chain T-matrices for all downstream segments
    a, b, c, d = _chain_tmatrices(frequencies, downstream_segments, medium)

    # Get mouth radiation impedance (from last segment's mouth area)
    z_rad = circular_piston_radiation_impedance(
        frequencies, downstream_segments[-1].mouth_area, medium
    )

    # Calculate mouth volume velocity using inverse T-matrix
    # From T-matrix: [p_t, U_t]ᵀ = [A B; C D][p_m, U_m]ᵀ
    # And p_m = U_m × Z_rad, so:
    # U_t = C·p_m + D·U_m = C·Z_rad·U_m + D·U_m = U_m·(C·Z_rad + D)
    # Therefore: U_m = U_t / (C·Z_rad + D)
    #
    # Note: For tapped horn, U_t is the volume velocity from the driver
    # entering the downstream section
    u_mouth = u_tap / (c * z_rad + d)

    # Step 9: Calculate mouth pressure
    # p_mouth = U_mouth × Z_rad
    p_mouth = u_mouth * z_rad

    # Step 10: Calculate SPL at 1m
    # For spherical wave from mouth: I = W / (4πr²)
    # W = 0.5 × |U_mouth|² × Re(Z_rad) (acoustic power)
    # SPL = 20×log₁₀(√(I·ρc) / p_ref) where p_ref = 20 μPa
    # Literature: Beranek (1954), Chapter 4

    radiated_power = 0.5 * (np.abs(u_mouth) ** 2) * np.real(z_rad)
    distance = 1.0  # 1 meter
    intensity = radiated_power / (4 * np.pi * distance ** 2)

    p_ref = 20e-6  # Reference pressure (20 μPa)
    # Add small value to avoid log(0)
    spl = 20 * np.log10(np.sqrt(intensity * medium.rho * medium.c) / p_ref + 1e-20)

    # Step 11: Calculate cone excursion
    # x_d = v_d / (jω)
    with np.errstate(divide='ignore', invalid='ignore'):
        x_diaphragm = v_diaphragm / (1j * omega)
        x_diaphragm = np.where(omega == 0, 0, x_diaphragm)

    excursion_mm = np.abs(x_diaphragm) * 1000  # Convert m to mm

    # Step 12: Calculate reference efficiency
    # η = W_acoustic / W_electrical
    # W_electrical = 0.5 × Re(Z_e) × |I|²
    # Literature: Beranek (1954), Chapter 8
    electrical_power = 0.5 * np.real(z_electrical) * (np.abs(current) ** 2)
    # Avoid division by zero
    efficiency = np.where(
        electrical_power > 0,
        (radiated_power / electrical_power) * 100,
        0
    )

    return {
        'frequencies': frequencies,
        'electrical_impedance': np.abs(z_electrical),
        'electrical_impedance_phase': np.angle(z_electrical, deg=True),
        'acoustic_impedance': z_acoustic,
        'spl': spl,
        'excursion': excursion_mm,
        'efficiency': efficiency,
        'diaphragm_velocity': np.abs(v_diaphragm),
        'z_electrical_complex': z_electrical,  # For debugging
        'z_mechanical_total': z_mechanical_total,  # For debugging
        'u_mouth': u_mouth,  # For debugging
        'p_mouth': p_mouth,  # For debugging
    }
