"""
Electrical impedance calculations for loudspeaker drivers.

This module implements the electrical impedance model for moving-coil
loudspeakers, including the coupling between electrical, mechanical,
and acoustic domains via the force factor BL.

Literature:
- COMSOL (2020), Figure 2 - Electro-mechano-acoustical equivalent circuit
- Small (1972) - Electrical impedance model
- Leach (2002) - Voice coil inductance losses
- literature/thiele_small/comsol_lumped_loudspeaker_driver_2020.md
- literature/thiele_small/leach_2002_voice_coil_inductance.md
"""

import math
import cmath

from gsd.driver.parameters import ThieleSmallParameters
from gsd.simulation.constants import angular_frequency


def voice_coil_impedance_leach(
    frequency: float,
    driver: ThieleSmallParameters,
    K: float,
    n: float,
) -> complex:
    """
    Calculate voice coil impedance using Leach (2002) lossy inductance model.

    The Leach model accounts for eddy current losses in the voice coil and
    magnetic circuit. At high frequencies, these losses cause the voice coil
    to behave more like a resistor than an inductor.

    Literature:
        - Leach (2002), "Loudspeaker Voice-Coil Inductance Losses"
        - COMSOL (2020), Page 4, Eqs. for L_E(ω) and R'_E(ω)
        - literature/thiele_small/leach_2002_voice_coil_inductance.md

    Model:
        The lossy inductor impedance is:
        Z_L(jω) = K·(jω)^n = K·ω^n [cos(nπ/2) + j·sin(nπ/2)]

        This can be represented as a series resistor and inductor:
        R_s = K·ω^n·cos(nπ/2)
        L_s = K·ω^(n-1)·sin(nπ/2)

        Where:
        - K is the impedance scaling factor (Ω·s^n)
        - n is the loss exponent (0 ≤ n ≤ 1)
          - n = 1: Lossless inductor (pure inductance, no losses)
          - n = 0: Pure resistor (no inductance, maximum losses)
          - n = 0.6-0.7: Typical values for voice coils

    Args:
        frequency: Frequency in Hz
        driver: ThieleSmallParameters instance (for R_e)
        K: Impedance scaling factor in Ω·s^n
           - For BC 8NDL51: K ≈ 2.7 (empirically fitted)
        n: Loss exponent (0 ≤ n ≤ 1)
           - For BC 8NDL51: n ≈ 0 (resistive at high frequencies)

    Returns:
        Complex voice coil impedance (Ω)
        - Real part: R_e + R_s (total resistance)
        - Imag part: ω·L_s (total reactance)

    Examples:
        >>> # BC 8NDL51 parameters (fitted to Hornresp)
        >>> driver = ThieleSmallParameters(...)
        >>> Z_vc = voice_coil_impedance_leach(20000, driver, K=2.7, n=0.0)
        >>> abs(Z_vc)  # ≈ 8 Ω at 20 kHz

    Validation:
        Compare with Hornresp voice coil impedance at high frequencies.
        Expected: |Z_vc| approaches constant value (R_e + K) as f increases.

    Notes:
        - At low frequencies, the simple jωL_e model may be sufficient
        - At high frequencies (>1 kHz), Leach model matches measurements better
        - Parameters K and n can be fitted to impedance measurements
        - Reference: Leach (2002), AES Journal Vol. 50 No. 6
    """
    if frequency <= 0:
        raise ValueError(f"Frequency must be > 0, got {frequency} Hz")

    if not isinstance(driver, ThieleSmallParameters):
        raise TypeError(f"driver must be ThieleSmallParameters, got {type(driver)}")

    # Calculate angular frequency
    omega = angular_frequency(frequency)

    # Leach (2002), Eq. 19: Z_L(jω) = K·(jω)^n
    # where (jω)^n = ω^n [cos(nπ/2) + j·sin(nπ/2)]
    #
    # Voice coil impedance: Z_vc = R_e + Z_L
    Z_lossy = K * (omega ** n) * complex(math.cos(n * math.pi / 2),
                                         math.sin(n * math.pi / 2))
    Z_voice_coil = complex(driver.R_e, 0) + Z_lossy

    return Z_voice_coil


def electrical_impedance_bare_driver(
    frequency: float,
    driver: ThieleSmallParameters,
    acoustic_load: complex = 0j,
    voice_coil_model: str = "simple",
    leach_K: float = None,
    leach_n: float = None,
    leach_crossover_hz: float = 1000.0,
) -> complex:
    """
    Calculate driver electrical impedance with mechanical/acoustic load.

    This function implements the complete electro-mechano-acoustical model
    of a moving-coat loudspeaker driver. The electrical impedance consists
    of three parts:

    1. Voice coil impedance: Z_vc (depends on model)
    2. Reflected mechanical impedance: Z_mech = (BL)² / Z_m
    3. Reflected acoustic impedance: Z_ac = (BL)² · Z_a / S_d²

    Literature:
        - COMSOL (2020), Figure 2 - Equivalent circuit model
        - Small (1972) - Electrical impedance analysis
        - Leach (2002) - Voice coil inductance losses
        - literature/thiele_small/comsol_lumped_loudspeaker_driver_2020.md

    Equation:
        Z_e = Z_vc + (BL)² / Z_m_total

    where:
        Z_m_total = Z_mechanical + Z_acoustic_reflected
        Z_mechanical = R_ms + jωM_ms + 1/(jωC_ms)
        Z_acoustic_reflected = Z_a · S_d² (acoustic to mechanical transformation)
        ω = 2πf (angular frequency)

    Args:
        frequency: Frequency in Hz
        driver: ThieleSmallParameters instance
        acoustic_load: Acoustic radiation impedance (Pa·s/m³), default 0
                     (bare driver in vacuum, no acoustic load)
        voice_coil_model: Voice coil impedance model
            - "simple": Standard jωL_e model (lossless inductor)
            - "leach": Leach (2002) lossy inductance model (frequency-limited)
            - "leach-full": Leach model applied at all frequencies
        leach_K: Leach model K parameter (Ω·s^n), required for Leach models
                 - For BC 8NDL51: K ≈ 2.02
        leach_n: Leach model n parameter (loss exponent), required for Leach models
                 - n = 0: Pure resistor (maximum losses)
                 - n = 1: Lossless inductor (no losses)
                 - For BC 8NDL51: n ≈ 0.03
        leach_crossover_hz: Crossover frequency for Leach model (Hz), default 1000 Hz
                            - Below: simple jωL_e model
                            - Above: Leach lossy inductance model
                            - Only used for "leach" model (not "leach-full")

    Returns:
        Complex electrical impedance (Ω)
        - Real part: Resistance (Ω)
        - Imag part: Reactance (Ω)

    Examples:
        >>> from gsd.driver.parameters import ThieleSmallParameters
        >>> driver = ThieleSmallParameters(
        ...     M_ms=0.054, C_ms=0.00019, R_ms=5.2,
        ...     R_e=3.1, L_e=0.72e-3, BL=16.5, S_d=0.0522
        ... )
        >>> # Simple model (lossless inductor)
        >>> Z = electrical_impedance_bare_driver(100, driver)
        >>> Z.real  # Resistance at 100 Hz
        >>> Z.imag  # Reactance at 100 Hz

        >>> # Leach model (lossy inductor, frequency-limited)
        >>> Z_leach = electrical_impedance_bare_driver(
        ...     20000, driver,
        ...     voice_coil_model="leach",
        ...     leach_K=2.02, leach_n=0.03
        ... )
        >>> abs(Z_leach)  # ≈ 8 Ω at 20 kHz (matches Hornresp)

        At resonance (F_s), impedance should show a peak:
        >>> Z_res = electrical_impedance_bare_driver(driver.F_s, driver)
        >>> abs(Z_res)  # Maximum impedance at F_s

    Validation:
        Compare with Hornresp electrical impedance for bare driver.
        Check impedance peak at F_s matches expected value.

    Notes:
        The "leach" model uses a frequency-limited approach:
        - Below leach_crossover_hz: simple jωL_e model (accurate at low frequencies)
        - Above leach_crossover_hz: Leach lossy inductance (accurate at high frequencies)
        This accounts for the physical reality that eddy current losses are
        more significant at high frequencies.
    """
    # Validate inputs
    if frequency <= 0:
        raise ValueError(f"Frequency must be > 0, got {frequency} Hz")

    if not isinstance(driver, ThieleSmallParameters):
        raise TypeError(f"driver must be ThieleSmallParameters, got {type(driver)}")

    if voice_coil_model not in ["simple", "leach", "leach-full"]:
        raise ValueError(f"voice_coil_model must be 'simple', 'leach', or 'leach-full', got '{voice_coil_model}'")

    if voice_coil_model in ["leach", "leach-full"] and (leach_K is None or leach_n is None):
        raise ValueError("leach_K and leach_n must be provided for Leach models")

    # Calculate angular frequency: ω = 2πf
    # Kinsler et al. (1982), Chapter 1
    omega = angular_frequency(frequency)

    # Voice coil electrical impedance
    # COMSOL (2020), Figure 2 - Electrical domain
    if voice_coil_model == "simple":
        # Standard jωL_e model (lossless inductor)
        # Z_vc = R_e + jωL_e
        Z_voice_coil = complex(driver.R_e, omega * driver.L_e)
    elif voice_coil_model == "leach-full":
        # Leach (2002) lossy inductance model at ALL frequencies
        # Accounts for eddy current losses at all frequencies
        Z_voice_coil = voice_coil_impedance_leach(
            frequency, driver, leach_K, leach_n
        )
    else:  # voice_coil_model == "leach"
        # Frequency-limited Leach model
        # Use simple model at low frequencies, Leach model at high frequencies
        # This accounts for the physical reality that eddy current losses
        # are more significant at high frequencies
        if frequency < leach_crossover_hz:
            # Low frequency: simple jωL_e model
            Z_voice_coil = complex(driver.R_e, omega * driver.L_e)
        else:
            # High frequency: Leach lossy inductance model
            Z_voice_coil = voice_coil_impedance_leach(
                frequency, driver, leach_K, leach_n
            )

    # Mechanical impedance: Z_m = R_ms + jωM_ms + 1/(jωC_ms)
    # COMSOL (2020), Figure 2 - Mechanical domain
    # Mass: jωM_ms (inductive in impedance analogy)
    # Compliance: 1/(jωC_ms) (capacitive in impedance analogy)
    # Resistance: R_ms (resistive in impedance analogy)
    if frequency == 0:
        # DC case: mechanical impedance is infinite (compliance dominates)
        Z_mechanical = complex(0, float('inf'))
    else:
        Z_mechanical = driver.R_ms + complex(0, omega * driver.M_ms) + complex(0, -1 / (omega * driver.C_ms))

    # Acoustic impedance reflected to mechanical side: Z_a · S_d²
    # COMSOL (2020), Eq. 1-2 - Mechano-acoustic coupling
    # Force on diaphragm: F_D = ∫(Δp · n_z) dA ≈ p · S_d
    # Diaphragm velocity: u_D = U / S_d
    # Mechanical impedance: Z_m = F/u = (p·S_d) / (U/S_d) = Z_a·S_d²
    Z_acoustic_reflected = acoustic_load * (driver.S_d ** 2)

    # Total mechanical impedance (including acoustic load)
    Z_mechanical_total = Z_mechanical + Z_acoustic_reflected

    # Reflected impedance from mechanical to electrical domain: Z_ref = (BL)² / Z_m
    # COMSOL (2020), Figure 2 - Coupling via controlled sources
    # Force: F = BL · i_c (Lorentz force)
    # Back EMF: V_back = BL · u_D
    # This creates a reflected impedance of (BL)² / Z_m
    if abs(Z_mechanical_total) == 0:
        # Avoid division by zero
        Z_reflected = complex(0, float('inf'))
    else:
        Z_reflected = (driver.BL ** 2) / Z_mechanical_total

    # Total electrical impedance: Z_e = Z_vc + Z_reflected
    # COMSOL (2020), Figure 2 - Series connection
    Z_electrical = Z_voice_coil + Z_reflected

    return Z_electrical


def electrical_impedance_at_resonance(driver: ThieleSmallParameters) -> complex:
    """
    Calculate electrical impedance at driver resonance frequency.

    At resonance (ω = ω_s = 1/√(M_ms·C_ms)), the mechanical mass and
    compliance reactances cancel, leaving only the mechanical resistance
    and acoustic load.

    Literature:
        - Small (1972) - Impedance at resonance
        - COMSOL (2020), Figure 2

    Args:
        driver: ThieleSmallParameters instance

    Returns:
        Complex electrical impedance at F_s (Ω)

    Examples:
        >>> driver = ThieleSmallParameters(0.05, 0.0002, 5, 8, 0.001, 10, 0.05)
        >>> Z_res = electrical_impedance_at_resonance(driver)
        >>> Z_res.real > driver.R_e  # Peak resistance at resonance
        True
    """
    return electrical_impedance_bare_driver(driver.F_s, driver, acoustic_load=0j)


def electrical_impedance_high_frequency_limit(
    driver: ThieleSmallParameters,
    frequency: float = 10000.0
) -> complex:
    """
    Calculate electrical impedance at high frequency (ω → ∞).

    At high frequency, the mechanical impedance is dominated by the mass
    (jωM_ms >> 1/jωC_ms), and the reflected impedance becomes negligible.

    Literature:
        - Small (1972) - High-frequency behavior

    Args:
        driver: ThieleSmallParameters instance
        frequency: High frequency to evaluate at (Hz), default 10 kHz

    Returns:
        Complex electrical impedance at high frequency (Ω)

    Examples:
        >>> driver = ThieleSmallParameters(0.05, 0.0002, 5, 8, 0.001, 10, 0.05)
        >>> Z_hf = electrical_impedance_high_frequency_limit(driver)
        >>> abs(Z_hf.real - driver.R_e) < 1  # Approaches R_e
        True
    """
    return electrical_impedance_bare_driver(frequency, driver, acoustic_load=0j)
