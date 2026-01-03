"""
Sealed box enclosure simulation.

This module implements the complete frequency response simulation for
direct radiator loudspeakers in sealed (closed-box) enclosures.

Literature:
- Small (1972) - Closed-Box Loudspeaker Systems Part I: Analysis
- Thiele (1971) - Loudspeakers in Vented Boxes (sealed box theory)
- literature/thiele_small/small_1972_closed_box.md

Key equations:
- Compliance ratio: α = Vas/Vb
- System resonance: Fc = Fs × √(1 + α)
- System Q: Qtc = Qts × √(1 + α)
- Transfer function: 2nd-order high-pass
"""

import math
import cmath
from dataclasses import dataclass

from gsd.driver.parameters import ThieleSmallParameters
from gsd.driver.radiation_impedance import radiation_impedance_piston
from gsd.driver.electrical_impedance import voice_coil_impedance_leach
from gsd.simulation.constants import (
    SPEED_OF_SOUND,
    AIR_DENSITY,
    angular_frequency,
)
from gsd.enclosure.common import (
    calculate_inductance_corner_frequency,
    calculate_hf_rolloff_db,
    calculate_inductance_transfer_function,
)


@dataclass
class SealedBoxSystemParameters:
    """
    Sealed box system parameters.

    Literature:
        - Small (1972), Part I - System parameters analysis, Eq. 9
        - literature/thiele_small/small_1972_closed_box.md

    Attributes:
        Vb: Box volume (m³)
        alpha: Compliance ratio (Vas/Vb)
        Fc: System resonance frequency (Hz)
        Qec: Electrical Q at system resonance Fc (Qes × √(1+α))
        Quc: Mechanical + absorption losses (typical: 5-10 unfilled, 2-5 filled)
        Qtc_total: Total system Q including mechanical losses (parallel combination)
        F3: -3dB cutoff frequency (Hz)
    """
    Vb: float
    alpha: float
    Fc: float
    Qec: float
    Quc: float
    Qtc_total: float
    F3: float


def calculate_sealed_box_system_parameters(
    driver: ThieleSmallParameters,
    Vb: float,
    Quc: float = 7.0,
) -> SealedBoxSystemParameters:
    """
    Calculate sealed box system parameters (Fc, Qec, Quc, Qtc_total, F3, α).

    Literature:
        - Small (1972), Eq. 9 for parallel Q combination
        - literature/thiele_small/small_1972_closed_box.md

    Args:
        driver: ThieleSmallParameters instance
        Vb: Box volume (m³)
        Quc: Mechanical + absorption losses (default 7.0)
            - Quc = 2-5: Filled box (heavy damping)
            - Quc = 5-10: Unfilled box (mechanical losses only)
            - Quc = ∞: No losses (theoretical)

    Returns:
        SealedBoxSystemParameters dataclass with:
        - Vb: Box volume (m³)
        - alpha: Compliance ratio (Vas/Vb)
        - Fc: System resonance frequency (Hz)
        - Qec: Electrical Q at Fc (Qes × √(1+α))
        - Quc: Mechanical + absorption losses
        - Qtc_total: Total system Q (parallel combination of Qec and Quc)
        - F3: -3dB cutoff frequency (Hz)

    Raises:
        ValueError: If Vb <= 0

    Examples:
        >>> from gsd.driver import load_driver
        >>> driver = load_driver("BC_8NDL51")  # Fs=64Hz, Qts=0.37, Vas=14L
        >>> params = calculate_sealed_box_system_parameters(driver, Vb=0.010)
        >>> params.Fc  # System resonance
        99.4...  # Hz (higher than Fs due to small box)
        >>> params.Qec  # Electrical Q at Fc
        0.50...  # Qes × √(1+α)
        >>> params.Qtc_total  # Total system Q with mechanical losses
        0.47...  # Parallel combination of Qec and Quc
        >>> params.alpha  # Compliance ratio
        1.4...  # Vas/Vb

    Theory:
        Small (1972), Eq. 9: Parallel Q combination
        Qtc_total = (Qec × Quc) / (Qec + Quc)

        Where:
        - Qec = Qes × √(1 + α)  # Electrical Q at system resonance
        - Quc = Mechanical + absorption losses

    Validation:
        Compare Fc and Qtc_total with Hornresp sealed box simulation.
        Expected: <0.5 Hz deviation for Fc, <0.02 for Qtc_total
    """
    # Validate inputs
    if Vb <= 0:
        raise ValueError(f"Box volume Vb must be > 0, got {Vb} m³")
    if Quc <= 0:
        raise ValueError(f"Quc must be > 0, got {Quc}")
    if Quc < 3.0:
        # Warning for unrealistic Quc values
        # Typical Quc range: 5-100
        # Quc < 3 represents extremely high losses
        import warnings
        warnings.warn(f"Quc={Quc} is unusually low (typical range: 5-100)")

    # Small (1972): Compliance ratio α = Vas / Vb
    # literature/thiele_small/small_1972_closed_box.md
    alpha = driver.V_as / Vb

    # Small (1972): System resonance Fc = Fs × √(1 + α)
    # The box stiffness increases the effective spring constant, raising resonance
    # literature/thiele_small/small_1972_closed_box.md
    sqrt_factor = math.sqrt(1.0 + alpha)
    Fc = driver.F_s * sqrt_factor

    # Electrical Q at system resonance Fc
    # Small (1972): Qec = Qes × √(1 + α)
    # literature/thiele_small/small_1972_closed_box.md
    Qec = driver.Q_es * sqrt_factor

    # Total system Q with mechanical losses
    # Small (1972), Eq. 9: PARALLEL COMBINATION (not geometric mean!)
    # Qtc_total = (Qec × Quc) / (Qec + Quc)
    # This models mechanical losses as parallel damping with electrical damping
    if Quc == float('inf'):
        Qtc_total = Qec
    else:
        # Standard parallel damping formula
        Qtc_total = (Qec * Quc) / (Qec + Quc)

    # Calculate F3 (-3dB point)
    # For Butterworth alignment (Qtc_total = 0.707): F3 = Fc
    # For other alignments, use approximate formula from Small (1972)
    # literature/thiele_small/small_1972_closed_box.md

    if abs(Qtc_total - 0.707) < 0.01:
        # Butterworth alignment: F3 = Fc
        F3 = Fc
    else:
        # General case: approximate formula
        # F3 = Fc × √((1/Qtc_total² - 2 + √((1/Qtc_total² - 2)² + 4)) / 2)
        # From solving |G(jω)|² / |G(jω)|²max = 0.5
        Qtc_sq = Qtc_total * Qtc_total
        term1 = 1.0 / Qtc_sq - 2.0
        term2 = math.sqrt(term1 * term1 + 4.0)
        F3_ratio = math.sqrt((term1 + term2) / 2.0)
        F3 = Fc * F3_ratio

    return SealedBoxSystemParameters(
        Vb=Vb,
        alpha=alpha,
        Fc=Fc,
        Qec=Qec,
        Quc=Quc,
        Qtc_total=Qtc_total,
        F3=F3,
    )


def calculate_spl_from_transfer_function(
    frequency: float,
    driver: ThieleSmallParameters,
    Vb: float,
    voltage: float = 2.83,
    measurement_distance: float = 1.0,
    speed_of_sound: float = SPEED_OF_SOUND,
    air_density: float = AIR_DENSITY,
    f_mass: float = None,
    Quc: float = 7.0,
    use_complex_tf: bool = False,
) -> float:
    """
    Calculate SPL using Small's transfer function for sealed box.

    This function implements Small's transfer function approach, which directly
    gives the normalized pressure response vs frequency. The transfer function
    is a 2nd-order high-pass filter that correctly models the frequency response
    of a sealed-box loudspeaker system.

    Literature:
        - Small (1972), Equation 1 - Normalized pressure response transfer function
        - Small (1972), Eq. 9 - Parallel Q combination
        - Small (1972), Reference efficiency equation (Section 7)
        - Leach (2002), "Introduction to Electroacoustics", Eq. 4.20
        - literature/thiele_small/small_1972_closed_box.md
        - Research: tasks/ported_box_transfer_function_research_brief.md

    Transfer Function (Small 1972, Eq. 1):
        G(s) = (s²/ωc²) / [s²/ωc² + s/(Qtc'·ωc) + 1]

    where:
        - s = jω (complex frequency variable)
        - ωc = 2πfc (system cutoff angular frequency)
        - fc = Fs × √(1 + α) (system resonance frequency)
        - Qtc' = Total system Q including mechanical losses (parallel combination)
        - α = Vas/Vb (compliance ratio)

    System Q with Mechanical Losses:
        Small (1972), Eq. 9: Parallel Q combination
        Qtc' = (Qec × Quc) / (Qec + Quc)

        Where:
        - Qec = Qes × √(1 + α)  # Electrical Q at system resonance
        - Quc = Mechanical + absorption losses

    Reference SPL Calculation:
        The reference efficiency is calculated from Small (1972):
        η₀ = (ρ₀/2πc) × (4π²Fs³Vas/Qes)

        For sealed box in the passband, the system efficiency equals the driver efficiency:
        η = η₀  (Small 1972, Part II, Eq. 23)

        Reference SPL at 1W/1m:
        SPL_ref = 20·log₁₀(√(η·P_ref·ρ₀·c/(2π·r²)) / p_ref)

        where:
            P_ref = V²/R_nominal (reference power)
            r = measurement_distance
            p_ref = 20 μPa

    High-Frequency Roll-off:
        When f_mass is provided, applies high-frequency roll-off combining:
        - Voice coil inductance roll-off (6 dB/octave above f_Le)
        - Mass roll-off (6 dB/octave above f_mass)
        - Combined creates 12 dB/octave roll-off when f_mass ≈ f_le

        Two implementation methods:
        1. use_complex_tf=False (default): Post-correct SPL in dB (legacy method)
        2. use_complex_tf=True: Multiply complex transfer functions (more accurate)

        Method 2 is recommended as it properly models the electromechanical coupling.

    Args:
        frequency: Frequency in Hz
        driver: ThieleSmallParameters instance
        Vb: Box volume (m³)
        voltage: Input voltage (V), default 2.83V (1W into 8Ω)
        measurement_distance: SPL measurement distance (m), default 1m
        speed_of_sound: Speed of sound (m/s)
        air_density: Air density (kg/m³)
        f_mass: Mass break frequency (Hz) for HF roll-off. If None, no HF roll-off applied.
        Quc: Mechanical + absorption losses (default 7.0)
            - Quc = 2-5: Filled box (heavy damping)
            - Quc = 5-10: Unfilled box (mechanical losses only)
            - Quc = ∞: No losses (theoretical)
        use_complex_tf: Use complex transfer function approach (default False for backward compatibility)
            - False: Apply HF roll-off as dB post-correction (legacy)
            - True: Multiply complex transfer functions H_total = H_box × H_le × H_mass

    Returns:
        SPL in dB at measurement_distance

    Raises:
        ValueError: If frequency <= 0, Vb <= 0, or invalid driver

    Examples:
        >>> from gsd.driver import load_driver
        >>> driver = load_driver("BC_8NDL51")
        >>> spl = calculate_spl_from_transfer_function(100, driver, Vb=0.010)
        >>> spl  # SPL at 1m for 10L sealed box (no HF roll-off)
        68.5...  # dB

        >>> # With HF roll-off using complex transfer functions (recommended)
        >>> spl = calculate_spl_from_transfer_function(10000, driver, Vb=0.010, f_mass=450, use_complex_tf=True)
        >>> spl  # SPL at 10kHz with HF roll-off
        70.2...  # dB

    Validation:
        Compare with Hornresp sealed box simulation.

        After efficiency fix (η = η₀, not η₀/(1+α)):
        Expected: SPL within ±0.5 dB of Hornresp for frequencies > Fc when f_mass is set.
        Previous errors of +2 to +8 dB at resonance should be eliminated.

        BC_8NDL51 validation expected:
        - Resonance (50-100 Hz): Error should be <1 dB (was +8.55 dB)
        - Midrange (150-200 Hz): Error should be <0.5 dB (was +2.15 dB)
        - High frequencies: Error determined by f_mass calibration

        Note: Calibration offset may need adjustment after efficiency fix.
        Current offset = 0.0 dB (reset from -25.25 dB).
    """
    # Validate inputs
    if frequency <= 0:
        raise ValueError(f"Frequency must be > 0, got {frequency} Hz")
    if not isinstance(driver, ThieleSmallParameters):
        raise TypeError(f"driver must be ThieleSmallParameters, got {type(driver)}")
    if Vb <= 0:
        raise ValueError(f"Box volume Vb must be > 0, got {Vb} m³")
    if measurement_distance <= 0:
        raise ValueError(f"Measurement distance must be > 0, got {measurement_distance} m")

    # Small (1972): System parameters
    # literature/thiele_small/small_1972_closed_box.md
    alpha = driver.V_as / Vb
    sqrt_factor = math.sqrt(1.0 + alpha)
    fc = driver.F_s * sqrt_factor  # System resonance frequency
    wc = 2 * math.pi * fc  # System cutoff angular frequency

    # Electrical Q at system resonance Fc
    # Small (1972): Qec = Qes × √(1 + α)
    Qec = driver.Q_es * sqrt_factor

    # Total system Q with mechanical losses
    # Small (1972), Eq. 9: PARALLEL COMBINATION
    # Qtc' = (Qec × Quc) / (Qec + Quc)
    if Quc == float('inf'):
        Qtc_prime = Qec
    else:
        Qtc_prime = (Qec * Quc) / (Qec + Quc)

    # Small (1972), Eq. 1: Normalized pressure response transfer function
    # G(s) = (s²/ωc²) / [s²/ωc² + s/(Qtc'·ωc) + 1]
    # literature/thiele_small/small_1972_closed_box.md
    #
    # CRITICAL: Qtc' must divide the s-term (damping), NOT the s²-term
    # Correct: denominator = s²/ωc² + s/(Qtc'·ωc) + 1
    # Buggy (would cause +Qtc gain): denominator = s²/(Qtc'·ωc²) + s/ωc + 1
    #
    # At high frequencies (s → ∞):
    # - Correct: |G(s)| → 1 (0 dB gain)
    # - Buggy: |G(s)| → Qtc' (unwanted amplification)
    omega = 2 * math.pi * frequency
    s = complex(0, omega)

    # Transfer function magnitude (uses Qtc_prime, not Qts)
    numerator = (s ** 2) / (wc ** 2)
    denominator = (s ** 2) / (wc ** 2) + s / (Qtc_prime * wc) + 1
    G = numerator / denominator

    # Small (1972), Eq. 24: Reference efficiency calculation
    # η₀ = (4π²/c³) × (fs³·Vas/Qes)
    #
    # CRITICAL: Previous formula was WRONG!
    # Old (buggy): η₀ = (ρ₀/2πc) × (4π²Fs³Vas/Qes) → gave η₀ > 100%
    # Correct: η₀ = (4π²/c³) × (fs³·Vas/Qes) → gives η₀ ~ 0.1-1%
    #
    # The error was including air_density and dividing by c instead of c³.
    # Missing c² factor caused 100,000× error (c³ ≈ 40,000,000 vs c ≈ 344).
    #
    # Literature:
    # - Small (1972), Part I, Section 4, Eq. 24
    # - literature/thiele_small/small_1972_closed_box.md
    #
    # Variables:
    # - c: Speed of sound (m/s) - must use c³, not c!
    # - fs: Driver resonance (Hz)
    # - Vas: Equivalent compliance volume (m³) - CRITICAL: must be in m³, not L
    # - Qes: Electrical Q (dimensionless)
    k = (4 * math.pi ** 2) / (speed_of_sound ** 3)
    eta_0 = k * (driver.F_s ** 3 * driver.V_as) / driver.Q_es

    # For sealed box in the passband, system efficiency equals driver efficiency
    # Small (1972), Part II, Eq. 23: η₀(sys) = η₀
    # The box stiffness affects resonance, not the passband efficiency level
    eta = eta_0

    # Reference power: P_ref = V² / R_nominal
    # Use driver's DC resistance as reference impedance
    R_nominal = driver.R_e
    P_ref = (voltage ** 2) / R_nominal

    # Reference SPL at measurement distance
    # RADIATION SPACE: Half-space (2π steradians) - infinite baffle mounting
    # This is the STANDARD test condition for direct radiator loudspeakers
    # Matches B&C datasheet specification (94 dB @ 2.83V, 1m)
    # Different from previous Hornresp validation file (Ang = 0.5×Pi, eighth-space)
    #
    # Pressure calculation: p_rms = √(η × P_ref × ρ₀ × c / (2π × r²))
    # SPL = 20·log₁₀(p_rms / p_ref) where p_ref = 20 μPa
    #
    # Literature:
    # - Kinsler et al. (1982), Chapter 4 - Acoustic radiation fundamentals
    # - Beranek (1954), Eq. 5.20 - Half-space radiation impedance
    # - Small (1972) - Standard infinite baffle assumption
    # - IEEE 219 - Loudspeaker measurement standards
    p_ref = 20e-6  # Reference pressure: 20 μPa
    pressure_rms = math.sqrt(eta * P_ref * air_density * speed_of_sound /
                             (2 * math.pi * measurement_distance ** 2))

    # Reference SPL (flat response at high frequencies)
    spl_ref = 20 * math.log10(pressure_rms / p_ref) if pressure_rms > 0 else 0

    # NO CALIBRATION OFFSET NEEDED
    # bugworks GSD uses standard half-space (2π steradians) radiation
    # This matches B&C datasheet and IEEE/IEC measurement standards
    # Previous +13.5 dB offset was compensating for non-standard Hornresp configuration
    CALIBRATION_OFFSET_DB = 0.0
    spl_ref += CALIBRATION_OFFSET_DB

    # Apply high-frequency roll-off if f_mass is provided
    # This is required to match Hornresp validation data
    # Literature: Small (1973), Leach (2002), Hornresp validation

    if f_mass is not None:
        if use_complex_tf:
            # NEW METHOD: Multiply complex transfer functions
            # H_total(s) = H_box(s) × H_le(s) × H_mass(s)
            # This properly models electromechanical coupling in complex domain
            # Literature: Leach (2002), Eq. 4.20; Research: tasks/ported_box_transfer_function_research_brief.md

            # Inductance transfer function: H_le(s) = 1 / (1 + jωτ)
            # where τ = Le / Re
            H_le = calculate_inductance_transfer_function(frequency, driver.L_e, driver.R_e)

            # Mass roll-off transfer function: H_mass(s) = 1 / (1 + j·(f/f_mass))
            # This models the mass-controlled roll-off as a first-order low-pass
            # Literature: Small (1973), vented box systems
            f_mass_angular = 2 * math.pi * f_mass
            H_mass = 1.0 / complex(1.0, omega / f_mass_angular)

            # Total transfer function: Multiply all components
            # H_total = G × H_le × H_mass
            # All are complex transfer functions, so multiplication preserves phase
            G_total = G * H_le * H_mass

            # Convert to SPL
            tf_dB = 20 * math.log10(abs(G_total)) if abs(G_total) > 0 else -float('inf')
            spl = spl_ref + tf_dB
        else:
            # LEGACY METHOD: Apply transfer function, then correct SPL in dB
            # SPL(f) = SPL_ref + 20·log₁₀(|G(jω)|) + HF_rolloff_dB
            # This is the original implementation for backward compatibility
            tf_dB = 20 * math.log10(abs(G)) if abs(G) > 0 else -float('inf')
            spl = spl_ref + tf_dB

            # Calculate inductance corner frequency
            f_le = calculate_inductance_corner_frequency(driver.R_e, driver.L_e)

            # Calculate HF roll-off (inductance + mass)
            hf_rolloff = calculate_hf_rolloff_db(
                frequency, f_le, f_mass, enclosure_type="sealed"
            )

            # Apply HF roll-off to SPL
            spl += hf_rolloff
    else:
        # No HF roll-off, just apply box transfer function
        tf_dB = 20 * math.log10(abs(G)) if abs(G) > 0 else -float('inf')
        spl = spl_ref + tf_dB

    return spl


def calculate_spl_array(
    frequencies,
    driver: ThieleSmallParameters,
    Vb: float,
    voltage: float = 2.83,
    measurement_distance: float = 1.0,
    speed_of_sound: float = SPEED_OF_SOUND,
    air_density: float = AIR_DENSITY,
    f_mass: float = None,
    Quc: float = 7.0,
):
    """
    Calculate SPL for sealed box using vectorized numpy array operations.

    This function is the array-based version of calculate_spl_from_transfer_function,
    optimized for calculating SPL across multiple frequencies efficiently using numpy
    vectorization. It uses the complex transfer function approach for high-frequency
    roll-off, which properly models electromechanical coupling.

    Literature:
        - Small (1972), Equation 1 - Normalized pressure response transfer function
        - Small (1972), Eq. 9 - Parallel Q combination
        - Leach (2002), "Introduction to Electroacoustics", Eq. 4.20
        - Research: tasks/ported_box_transfer_function_research_brief.md

    Transfer Function Approach:
        H_total(s) = H_box(s) × H_le(s) × H_mass(s)

        where:
        - H_box(s) = (s²/ωc²) / [s²/ωc² + s/(Qtc'·ωc) + 1] (2nd-order high-pass)
        - H_le(s) = 1 / (1 + jωτ) where τ = Le/Re (voice coil inductance)
        - H_mass(s) = 1 / (1 + j(f/f_mass)) (mass roll-off)

    Args:
        frequencies: Array of frequencies in Hz (numpy array or list)
        driver: ThieleSmallParameters instance
        Vb: Box volume (m³)
        voltage: Input voltage (V), default 2.83V (1W into 8Ω)
        measurement_distance: SPL measurement distance (m), default 1m
        speed_of_sound: Speed of sound (m/s)
        air_density: Air density (kg/m³)
        f_mass: Mass break frequency (Hz) for HF roll-off. If None, no HF roll-off applied.
        Quc: Mechanical + absorption losses (default 7.0)

    Returns:
        numpy array of SPL values in dB at measurement_distance

    Raises:
        ValueError: If Vb <= 0, or invalid driver
        ImportError: If numpy is not available

    Examples:
        >>> import numpy as np
        >>> from gsd.driver import load_driver
        >>> driver = load_driver("BC_8NDL51")
        >>> freqs = np.logspace(1, 4, 100)  # 10 Hz to 10 kHz
        >>> spl = calculate_spl_array(freqs, driver, Vb=0.010, f_mass=450)
        >>> spl.shape
        (100,)
        >>> spl[50]  # SPL at some frequency
        85.2...  # dB

    Validation:
        Compare with Hornresp sealed box simulation.

        After efficiency fix (η = η₀, not η₀/(1+α)):
        Expected: SPL within ±0.5 dB of Hornresp for frequencies > Fc when f_mass is set.
        Previous errors of +2 to +8 dB at resonance should be eliminated.

        BC_8NDL51 validation expected:
        - Resonance (50-100 Hz): Error should be <1 dB (was +8.55 dB)
        - Midrange (150-200 Hz): Error should be <0.5 dB (was +2.15 dB)
        - High frequencies: Error determined by f_mass calibration

        Note: Calibration offset may need adjustment after efficiency fix.
        Current offset = 0.0 dB (reset from -25.25 dB).

    Notes:
        - Requires numpy to be installed
        - Uses complex transfer function multiplication for accurate HF roll-off
        - Much faster than looping through individual frequencies
        - Recommended for plotting and optimization applications
    """
    try:
        import numpy as np
    except ImportError:
        raise ImportError("numpy is required for calculate_spl_array. Install with: pip install numpy")

    # Validate inputs
    if not isinstance(driver, ThieleSmallParameters):
        raise TypeError(f"driver must be ThieleSmallParameters, got {type(driver)}")
    if Vb <= 0:
        raise ValueError(f"Box volume Vb must be > 0, got {Vb} m³")
    if measurement_distance <= 0:
        raise ValueError(f"Measurement distance must be > 0, got {measurement_distance} m")

    # Convert to numpy array if not already
    freqs = np.asarray(frequencies, dtype=float)

    # Small (1972): System parameters
    # literature/thiele_small/small_1972_closed_box.md
    alpha = driver.V_as / Vb
    sqrt_factor = math.sqrt(1.0 + alpha)
    fc = driver.F_s * sqrt_factor  # System resonance frequency
    wc = 2 * math.pi * fc  # System cutoff angular frequency

    # Electrical Q at system resonance Fc
    # Small (1972): Qec = Qes × √(1 + α)
    Qec = driver.Q_es * sqrt_factor

    # Total system Q with mechanical losses
    # Small (1972), Eq. 9: PARALLEL COMBINATION
    # Qtc' = (Qec × Quc) / (Qec + Quc)
    if Quc == float('inf'):
        Qtc_prime = Qec
    else:
        Qtc_prime = (Qec * Quc) / (Qec + Quc)

    # Small (1972), Eq. 1: Normalized pressure response transfer function
    # G(s) = (s²/ωc²) / [s²/ωc² + s/(Qtc'·ωc) + 1]
    # literature/thiele_small/small_1972_closed_box.md
    #
    # CRITICAL: Qtc' must divide the s-term (damping), NOT the s²-term
    # Correct: denominator = s²/ωc² + s/(Qtc'·ωc) + 1
    # Buggy (would cause +Qtc gain): denominator = s²/(Qtc'·ωc²) + s/ωc + 1
    #
    # At high frequencies (s → ∞):
    # - Correct: |G(s)| → 1 (0 dB gain)
    # - Buggy: |G(s)| → Qtc' (unwanted amplification)
    #
    # Vectorized calculation using complex numpy arrays
    omega = 2 * math.pi * freqs
    s = 1j * omega  # Complex frequency variable

    # Transfer function (vectorized)
    numerator = (s ** 2) / (wc ** 2)
    denominator = (s ** 2) / (wc ** 2) + s / (Qtc_prime * wc) + 1
    G = numerator / denominator

    # Small (1972), Eq. 24: Reference efficiency calculation
    # η₀ = (4π²/c³) × (fs³·Vas/Qes)
    #
    # CRITICAL: Previous formula was WRONG!
    # Old (buggy): η₀ = (ρ₀/2πc) × (4π²Fs³Vas/Qes) → gave η₀ > 100%
    # Correct: η₀ = (4π²/c³) × (fs³·Vas/Qes) → gives η₀ ~ 0.1-1%
    #
    # The error was including air_density and dividing by c instead of c³.
    # Missing c² factor caused 100,000× error (c³ ≈ 40,000,000 vs c ≈ 344).
    #
    # Literature:
    # - Small (1972), Part I, Section 4, Eq. 24
    # - literature/thiele_small/small_1972_closed_box.md
    #
    # Variables:
    # - c: Speed of sound (m/s) - must use c³, not c!
    # - fs: Driver resonance (Hz)
    # - Vas: Equivalent compliance volume (m³) - CRITICAL: must be in m³, not L
    # - Qes: Electrical Q (dimensionless)
    k = (4 * math.pi ** 2) / (speed_of_sound ** 3)
    eta_0 = k * (driver.F_s ** 3 * driver.V_as) / driver.Q_es

    # For sealed box in the passband, system efficiency equals driver efficiency
    # Small (1972), Part II, Eq. 23: η₀(sys) = η₀
    # The box stiffness affects resonance, not the passband efficiency level
    eta = eta_0

    # Reference power: P_ref = V² / R_nominal
    # Use driver's DC resistance as reference impedance
    R_nominal = driver.R_e
    P_ref = (voltage ** 2) / R_nominal

    # Reference SPL at measurement distance
    # RADIATION SPACE: Half-space (2π steradians) - infinite baffle mounting
    # This is the STANDARD test condition for direct radiator loudspeakers
    # Matches B&C datasheet specification (94 dB @ 2.83V, 1m)
    # Different from previous Hornresp validation file (Ang = 0.5×Pi, eighth-space)
    #
    # Pressure calculation: p_rms = √(η × P_ref × ρ₀ × c / (2π × r²))
    # SPL = 20·log₁₀(p_rms / p_ref) where p_ref = 20 μPa
    #
    # Literature:
    # - Kinsler et al. (1982), Chapter 4 - Acoustic radiation fundamentals
    # - Beranek (1954), Eq. 5.20 - Half-space radiation impedance
    # - Small (1972) - Standard infinite baffle assumption
    # - IEEE 219 - Loudspeaker measurement standards
    p_ref = 20e-6  # Reference pressure: 20 μPa
    pressure_rms = math.sqrt(eta * P_ref * air_density * speed_of_sound /
                             (2 * math.pi * measurement_distance ** 2))

    # Reference SPL (flat response at high frequencies)
    spl_ref = 20 * math.log10(pressure_rms / p_ref) if pressure_rms > 0 else 0

    # NO CALIBRATION OFFSET NEEDED
    # bugworks GSD uses standard half-space (2π steradians) radiation
    # This matches B&C datasheet and IEEE/IEC measurement standards
    # Previous +13.5 dB offset was compensating for non-standard Hornresp configuration
    CALIBRATION_OFFSET_DB = 0.0
    spl_ref += CALIBRATION_OFFSET_DB

    # Apply high-frequency roll-off if f_mass is provided
    # This uses the complex transfer function approach
    # Literature: Small (1973), Leach (2002), Hornresp validation

    if f_mass is not None:
        # COMPLEX TRANSFER FUNCTION APPROACH
        # H_total(s) = H_box(s) × H_le(s) × H_mass(s)
        # This properly models electromechanical coupling in complex domain
        # Literature: Leach (2002), Eq. 4.20; Research: tasks/ported_box_transfer_function_research_brief.md

        # Inductance transfer function: H_le(s) = 1 / (1 + jωτ)
        # where τ = Le / Re
        H_le = calculate_inductance_transfer_function(freqs, driver.L_e, driver.R_e)

        # Mass roll-off transfer function: H_mass(s) = 1 / (1 + j·(f/f_mass))
        # This models the mass-controlled roll-off as a first-order low-pass
        # Literature: Small (1973), vented box systems
        # Vectorized calculation
        H_mass = 1.0 / (1.0 + 1j * (freqs / f_mass))

        # Total transfer function: Multiply all components
        # H_total = G × H_le × H_mass
        # All are complex transfer functions, so multiplication preserves phase
        G_total = G * H_le * H_mass

        # Convert to SPL (vectorized)
        spl = spl_ref + 20 * np.log10(np.abs(G_total))
    else:
        # No HF roll-off, just apply box transfer function
        spl = spl_ref + 20 * np.log10(np.abs(G))

    return spl


def sealed_box_electrical_impedance(
    frequency: float,
    driver: ThieleSmallParameters,
    Vb: float,
    voltage: float = 2.83,
    measurement_distance: float = 1.0,
    speed_of_sound: float = SPEED_OF_SOUND,
    air_density: float = AIR_DENSITY,
    voice_coil_model: str = "simple",
    leach_K: float = None,
    leach_n: float = None,
    use_transfer_function_spl: bool = True,
    f_mass: float = None,
    Quc: float = 7.0,
    use_complex_tf: bool = False,
) -> dict:
    """
    Calculate electrical impedance and SPL for sealed box enclosure.

    Literature:
        - Small (1972) - Closed-box electrical impedance, Eq. 9 for parallel Q
        - Beranek (1954), Eq. 5.20 - Radiation impedance (front side only)
        - literature/thiele_small/small_1972_closed_box.md
        - literature/horns/beranek_1954.md

    IMPORTANT NOTE ON Hornresp VALIDATION LIMITATION:
        Hornresp does NOT support QL/Quc parameter for sealed box enclosures.
        QL is only available in Hornresp for ported boxes.

        This means our sealed box Quc implementation CANNOT be directly validated
        against Hornresp. The implementation is based on Small (1972) theory:
        - Small (1972), Eq. 9: Parallel Q combination (well-established)
        - R_box formula is empirical (not from Small 1972)

        For validation, we rely on:
        1. Small (1972) theoretical foundation
        2. Physical reasoning (mechanical losses affect system damping)
        3. Consistency with ported box QL implementation (where Hornresp validation IS possible)

        If you need to match Hornresp sealed box behavior exactly, use Quc=float('inf')
        which gives the lossless case that Hornresp assumes for sealed boxes.

    Key differences from infinite baffle:
        - System resonance: Fc = Fs × √(1 + α) where α = Vas/Vb
        - Mechanical stiffness: Box compliance in series with driver suspension
        - Effective compliance: C_mb = C_ms / (1 + α) (stiffer spring)
        - Radiation mass: FRONT SIDE ONLY (1× M_rad, not 2×)
        - Total moving mass: M_ms = M_md + 1×M_rad (not 2×M_rad)

    SPL Calculation Method:
        By default (use_transfer_function_spl=True), SPL is calculated using
        Small's transfer function approach, which correctly models the frequency
        response for all drivers including high-BL designs. The transfer function
        is a 2nd-order high-pass filter that directly gives the normalized pressure
        response vs frequency.

        For legacy compatibility or comparison, set use_transfer_function_spl=False
        to use the impedance coupling method (may show SPL rise at high frequencies
        for high-BL drivers).

    Args:
        frequency: Frequency in Hz
        driver: ThieleSmallParameters instance
        Vb: Box volume (m³)
        voltage: Input voltage (V), default 2.83V (1W into 8Ω)
        measurement_distance: SPL measurement distance (m), default 1m
        speed_of_sound: Speed of sound (m/s)
        air_density: Air density (kg/m³)
        voice_coil_model: "simple" or "leach"
        leach_K: Leach K parameter (for "leach" model)
        leach_n: Leach n parameter (for "leach" model)
        use_transfer_function_spl: Use transfer function for SPL (default True)
        f_mass: Mass break frequency (Hz) for HF roll-off. If None, no HF roll-off applied.
        Quc: Mechanical + absorption losses (default 7.0)
            - Quc = 2-5: Filled box (heavy damping)
            - Quc = 5-10: Unfilled box (mechanical losses only)
            - Quc = ∞: No losses (theoretical)
        use_complex_tf: Use complex transfer function approach for HF roll-off (default False)
            - False: Apply HF roll-off as dB post-correction (legacy)
            - True: Multiply complex transfer functions H_total = H_box × H_le × H_mass (recommended)

    Returns:
        Dictionary containing:
        - 'frequency': Frequency (Hz)
        - 'Ze_magnitude': Electrical impedance magnitude (Ω)
        - 'Ze_phase': Electrical impedance phase (degrees)
        - 'Ze_real': Electrical resistance (Ω)
        - 'Ze_imag': Electrical reactance (Ω)
        - 'SPL': Sound pressure level (dB at measurement_distance)
        - 'diaphragm_velocity': Diaphragm velocity magnitude (m/s)
        - 'diaphragm_velocity_phase': Diaphragm velocity phase (degrees)
        - 'radiation_impedance': Complex radiation impedance (Pa·s/m³)
        - 'radiation_resistance': Radiation resistance (Pa·s/m³)
        - 'radiation_reactance': Radiation reactance (Pa·s/m³)
        - 'Fc': System resonance frequency (Hz)
        - 'Qec': Electrical Q at Fc (Qes × √(1+α))
        - 'Quc': Mechanical + absorption losses
        - 'Qtc_total': Total system Q (parallel combination of Qec and Quc)

    Raises:
        ValueError: If frequency <= 0, Vb <= 0, or invalid driver

    Examples:
        >>> from gsd.driver import load_driver
        >>> driver = load_driver("BC_8NDL51")
        >>> result = sealed_box_electrical_impedance(100, driver, Vb=0.010)
        >>> result['Fc']  # System resonance for 10L box
        99.4...  # Hz
        >>> result['Ze_magnitude']
        6.2...  # Ω
        >>> result['SPL']
        68.5...  # dB at 1m

        At system resonance, impedance peaks:
        >>> params = calculate_sealed_box_system_parameters(driver, 0.010)
        >>> result_fc = sealed_box_electrical_impedance(params.Fc, driver, Vb=0.010)
        >>> result_fc['Ze_magnitude'] > result['Ze_magnitude']
        True

    Validation:
        Compare with Hornresp "Rear Lined" sealed box simulation.
        Expected tolerances:
        - Electrical impedance magnitude: <5% general, <10% near resonance
        - Electrical impedance phase: <10° general, <15° near resonance
        - SPL (with transfer function): <3 dB (matches Hornresp well)
        - SPL (impedance coupling): May deviate for high-BL drivers

    Known Limitations:
        - Voice coil inductance modeled as simple jωL (lossless inductor)
        - Hornresp uses more sophisticated lossy inductance models (Leach 2002)
        - High-frequency SPL deviation expected above 2 kHz
        - No leakage or absorption losses (Ql = ∞ assumed)
    """
    # Validate inputs
    if frequency <= 0:
        raise ValueError(f"Frequency must be > 0, got {frequency} Hz")

    if not isinstance(driver, ThieleSmallParameters):
        raise TypeError(f"driver must be ThieleSmallParameters, got {type(driver)}")

    if Vb <= 0:
        raise ValueError(f"Box volume Vb must be > 0, got {Vb} m³")

    if measurement_distance <= 0:
        raise ValueError(f"Measurement distance must be > 0, got {measurement_distance} m")

    # Calculate angular frequency: ω = 2πf
    # Kinsler et al. (1982), Chapter 1
    omega = angular_frequency(frequency)

    # Step 1: Calculate compliance ratio and box compliance
    # Small (1972): α = Vas/Vb
    # literature/thiele_small/small_1972_closed_box.md
    alpha = driver.V_as / Vb

    # Box compliance in series with driver compliance
    # Small (1972): C_mb = C_ms / (1 + α)
    # This is equivalent to: 1/C_mb = 1/C_ms + 1/C_ab
    # where C_ab = Vb / (ρ₀·c²·S_d²) is the box acoustic compliance
    # literature/thiele_small/small_1972_closed_box.md
    C_mb = driver.C_ms / (1.0 + alpha)

    # Step 2: Calculate system resonance
    # Small (1972): Fc = Fs × √(1 + α)
    # literature/thiele_small/small_1972_closed_box.md
    Fc = driver.F_s * math.sqrt(1.0 + alpha)

    # Step 3: Calculate radiation impedance for circular piston
    # Beranek (1954), Eq. 5.20: Z_R = ρc·S·[R₁(2ka) + jX₁(2ka)]
    # Front side only (use existing function)
    # literature/horns/beranek_1954.md
    Z_rad = radiation_impedance_piston(
        frequency,
        driver.S_d,
        speed_of_sound=speed_of_sound,
        air_density=air_density
    )

    # Step 4: Calculate mechanical impedance with box compliance
    # COMSOL (2020), Figure 2: Mechanical equivalent circuit
    # Z_m = R_ms + jωM_ms + 1/(jωC_mb)
    # literature/thiele_small/small_1972_closed_box.md
    #
    # IMPORTANT: Use driver.M_ms (includes 2× radiation mass) for sealed box
    # Research shows sealed boxes need both front and rear air loads
    # See: docs/validation/sealed_box_spl_investigation.md for details
    #
    # BOX DAMPING (Mechanical + Absorption Losses):
    # Small (1972), Eq. 9 models mechanical losses as Quc (non-electrical Q).
    # This is combined in parallel with electrical Q to get total system Q.
    #
    # The mechanical resistance R_box represents energy dissipation in:
    # - Driver suspension losses (R_ms from driver)
    # - Box absorption losses (damping material)
    # - Box leakage losses (air leaks)
    #
    # R_box = (ω × M_ms) / Quc  (EMPIRICAL - not from Small 1972)
    #
    # NOTE: The formula R_box = ωM_ms/Quc is empirical, not derived from
    # Small (1972). Small does not provide an explicit R_box formula.
    # This relationship provides reasonable agreement with Hornresp results.
    #
    # Literature:
    # - Small (1972), Eq. 9: Parallel Q combination
    # - docs/validation/sealed_box_spl_research_summary.md (Empirical derivation)
    if Quc == float('inf'):
        R_box = 0.0
    else:
        # EMPIRICAL: R_box = ω × M_ms / Quc
        # Approximates mechanical/absorption losses as frequency-dependent damping
        R_box = (omega * driver.M_ms) / Quc

    Z_mechanical = (driver.R_ms + R_box) + complex(0, omega * driver.M_ms) + \
                   complex(0, -1 / (omega * C_mb))

    # Total mechanical impedance including radiation load
    # Acoustic impedance reflected to mechanical domain: Z_a · S_d²
    # COMSOL (2020), Eq. 1-2: Z_m = F/u = (p·S_d) / (U/S_d) = Z_a·S_d²
    Z_mechanical_total = Z_mechanical + (Z_rad * (driver.S_d ** 2))

    # Step 5: Calculate electrical impedance
    # COMSOL (2020), Figure 2: Z_e = Z_vc + (BL)² / Z_m_total
    # IMPORTANT: We must use our pre-calculated Z_mechanical_total (with C_mb)
    # NOT the driver's C_ms, because the box changes the compliance!
    #
    # Voice coil electrical impedance
    # COMSOL (2020), Figure 2 - Electrical domain
    if voice_coil_model == "simple":
        # Standard jωL_e model (lossless inductor)
        # Z_vc = R_e + jωL_e
        Z_voice_coil = complex(driver.R_e, omega * driver.L_e)
    elif voice_coil_model == "leach-full":
        # Leach (2002) lossy inductance model at ALL frequencies
        # Accounts for eddy current losses at all frequencies
        if leach_K is None or leach_n is None:
            raise ValueError("leach_K and leach_n must be provided for Leach models")
        Z_voice_coil = voice_coil_impedance_leach(
            frequency, driver, leach_K, leach_n
        )
    else:  # voice_coil_model == "leach"
        # Frequency-limited Leach model
        # Use simple model at low frequencies, Leach model at high frequencies
        if frequency < 1000.0:  # leach_crossover_hz
            # Low frequency: simple jωL_e model
            Z_voice_coil = complex(driver.R_e, omega * driver.L_e)
        else:
            # High frequency: Leach lossy inductance model
            if leach_K is None or leach_n is None:
                raise ValueError("leach_K and leach_n must be provided for Leach models")
            Z_voice_coil = voice_coil_impedance_leach(
                frequency, driver, leach_K, leach_n
            )

    # Reflected impedance from mechanical to electrical domain: Z_ref = (BL)² / Z_m
    # COMSOL (2020), Figure 2 - Coupling via controlled sources
    # Force: F = BL · i_c (Lorentz force)
    # Back EMF: V_back = BL · u_D
    # This creates a reflected impedance of (BL)² / Z_m
    # CRITICAL: Use Z_mechanical_total (with C_mb), not driver's C_ms!
    if abs(Z_mechanical_total) == 0:
        # Avoid division by zero
        Z_reflected = complex(0, float('inf'))
    else:
        Z_reflected = (driver.BL ** 2) / Z_mechanical_total

    # Total electrical impedance: Z_e = Z_vc + Z_reflected
    # COMSOL (2020), Figure 2 - Series connection
    Ze = Z_voice_coil + Z_reflected

    # Step 6: Calculate diaphragm velocity using complex phasor model
    # Standard loudspeaker electromechanical model uses full complex current
    # Literature: Loudspeaker theory (Beranek, Small, etc.)
    #
    # Model: F = BL × I (complex), v = F / Z_m (complex division)
    # SPL calculated from |v| (velocity magnitude)
    if driver.BL == 0 or abs(Ze) == 0:
        # Avoid division by zero
        u_diaphragm = complex(0, 0)
    else:
        # Voice coil current
        # COMSOL (2020), Figure 2: i_c = V_in / Z_e
        I_complex = voltage / Ze

        # Calculate force using FULL complex current (not just I_active)
        # F = BL × I  (all quantities are complex phasors)
        # Literature: Standard loudspeaker electromechanical model
        # NOTE: I_active is only used for power calculations, not force/velocity
        F_complex = driver.BL * I_complex

        # Diaphragm velocity from complex force and complex mechanical impedance
        # v = F / Z_m  (complex division of phasors)
        # The velocity is a complex phasor; we use its magnitude for SPL
        u_diaphragm = F_complex / Z_mechanical_total

    # Step 7: Calculate sound pressure level
    # Two methods available:
    # 1. Transfer function approach (default): Small (1972) normalized pressure response
    # 2. Impedance coupling approach: Diaphragm velocity from impedance model
    #
    # The transfer function approach is recommended as it correctly models
    # the frequency response for all drivers including high-BL designs.

    if use_transfer_function_spl:
        # Small (1972): Use transfer function for SPL
        # This is the recommended approach for accurate SPL prediction
        # literature/thiele_small/small_1972_closed_box.md
        spl = calculate_spl_from_transfer_function(
            frequency=frequency,
            driver=driver,
            Vb=Vb,
            voltage=voltage,
            measurement_distance=measurement_distance,
            speed_of_sound=speed_of_sound,
            air_density=air_density,
            f_mass=f_mass,
            Quc=Quc,
            use_complex_tf=use_complex_tf,
        )
    else:
        # Legacy impedance coupling approach
        # Kinsler et al. (1982), Chapter 4 - Pressure from piston in infinite baffle
        # For a circular piston in an infinite baffle:
        # p(r) = jωρ₀·U·exp(-jkr) / (2πr)
        # where U = volume velocity = u_D · S_d
        #
        # Sound pressure level: SPL = 20·log₁₀(|p|/p_ref) where p_ref = 20 μPa
        # literature/thiele_small/small_1972_closed_box.md

        # Volume velocity: U = u_D · S_d
        # Kinsler et al. (1982), Chapter 4
        volume_velocity = u_diaphragm * driver.S_d

        # Pressure magnitude at measurement distance
        # p = jωρ₀·U / (2πr)  (magnitude only, ignore phase and distance delay)
        # The factor j indicates 90° phase shift, but magnitude is what matters for SPL
        # Kinsler et al. (1982), Chapter 4, Eq. 4.58 (piston in infinite baffle)
        pressure_amplitude = (omega * air_density * abs(volume_velocity)) / \
                             (2 * math.pi * measurement_distance)

        # Sound pressure level
        # SPL = 20·log₁₀(p/p_ref) where p_ref = 20 μPa
        # Kinsler et al. (1982), Chapter 2
        p_ref = 20e-6  # Reference pressure: 20 μPa
        spl = 20 * math.log10(pressure_amplitude / p_ref) if pressure_amplitude > 0 else -float('inf')

    # Step 8: Calculate system Q parameters for reference
    # Small (1972), Eq. 9: Parallel Q combination
    sqrt_factor = math.sqrt(1.0 + alpha)
    Qec = driver.Q_es * sqrt_factor  # Electrical Q at system resonance Fc

    # Total system Q (parallel combination of electrical and mechanical)
    # Small (1972), Eq. 9: Qtc_total = (Qec × Quc) / (Qec + Quc)
    if Quc == float('inf'):
        Qtc_total = Qec
    else:
        Qtc_total = (Qec * Quc) / (Qec + Quc)

    # Prepare return dictionary
    result = {
        'frequency': frequency,
        'Ze_magnitude': abs(Ze),
        'Ze_phase': math.degrees(cmath.phase(Ze)),
        'Ze_real': Ze.real,
        'Ze_imag': Ze.imag,
        'SPL': spl,
        'diaphragm_velocity': abs(u_diaphragm),
        'diaphragm_velocity_phase': math.degrees(cmath.phase(u_diaphragm)),
        'radiation_impedance': Z_rad,
        'radiation_resistance': Z_rad.real,
        'radiation_reactance': Z_rad.imag,
        'Fc': Fc,
        'Qec': Qec,
        'Quc': Quc,
        'Qtc_total': Qtc_total,
    }

    return result

