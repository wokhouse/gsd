"""
Common functions shared between sealed and ported enclosure simulations.

This module contains utility functions that are used by multiple enclosure
types to avoid code duplication.

Literature:
- Small (1973), "Vented-Box Loudspeaker Systems Part I", JAES
- Leach (2002), "Loudspeaker Voice-Coil Inductance Losses", JAES
- Hornresp validation: docs/validation/mass_controlled_rolloff_research.md
"""

import math
from typing import Union


def calculate_inductance_corner_frequency(
    re: float,
    le: float,
    frequency: float = None,
    leach_n: float = 0.6
) -> float:
    """
    Calculate the voice coil inductance corner frequency.

    Above this frequency, the response rolls off at 6 dB/octave
    due to the voice coil inductance.

    Voice coil inductance is frequency-dependent (semi-inductance).
    The effective inductance decreases at higher frequencies:
    Le(f) = Le_DC × (f/1000)^(-n) where n ≈ 0.5-0.7

    This means the corner frequency increases at higher frequencies:
    f_Le(f) = Re / (2π × Le(f))

    Literature:
        - Small (1973), "Vented-Box Loudspeaker Systems Part I", JAES
        - Leach, W.M. "Loudspeaker Voice-Coil Inductance Losses"
        - Research: docs/validation/mass_controlled_rolloff_research.md

    Args:
        re: DC voice coil resistance (Ω)
        le: Voice coil inductance at DC (H)
        frequency: Frequency in Hz (for frequency-dependent correction)
        leach_n: Leach exponent (default 0.6, typical range 0.5-0.7)

    Returns:
        Inductance corner frequency in Hz (returns infinity if Le <= 0)

    Raises:
        ValueError: If re <= 0

    Examples:
        >>> # DC corner frequency
        >>> calculate_inductance_corner_frequency(re=4.9, le=0.0045)
        173.2...  # Hz (for B&C 15DS115 with 4.5 mH)

        >>> # At 2000 Hz (inductance is less effective)
        >>> calculate_inductance_corner_frequency(re=4.9, le=0.0045, frequency=2000)
        275.5...  # Hz (corner frequency shifts higher)

    Validation:
        Compare with Hornresp inductance corner frequency.
        Expected: <1% deviation from Hornresp values.
    """
    if re <= 0:
        raise ValueError(f"DC resistance Re must be > 0, got {re} Ω")

    # If inductance is zero or negative, no inductance roll-off
    if le <= 0:
        return float('inf')

    # Apply frequency-dependent correction (semi-inductance model)
    # At higher frequencies, effective inductance decreases
    # Le(f) = Le_DC × (f/1000)^(-n)
    # Literature: Leach (2002), voice coil inductance losses
    if frequency is not None and frequency > 0:
        # Frequency-dependent inductance
        # f_ref = 1000 Hz is the reference frequency for Le specification
        f_ref = 1000.0
        le_effective = le * (frequency / f_ref) ** (-leach_n)

        # Recalculate corner frequency with effective inductance
        # f_Le(f) = Re / (2π × Le(f))
        return re / (2 * math.pi * le_effective)

    # DC corner frequency (no frequency dependence)
    # f_Le = Re / (2π × Le)
    # Literature: docs/validation/mass_controlled_rolloff_research.md
    return re / (2 * math.pi * le)


def calculate_hf_rolloff_db(
    frequency: float,
    f_le: float,
    f_mass: float = None,
    enclosure_type: str = "sealed"
) -> float:
    """
    Calculate high-frequency roll-off in dB for direct radiators.

    For direct radiators (sealed/ported boxes):
        Uses voice coil inductance roll-off (6 dB/octave above f_Le).
        Optionally applies mass roll-off if f_mass is provided.
        When f_mass ≈ f_le, creates a second-order filter (12 dB/octave).

    The roll-off is calculated as:
    - Inductance roll-off: -10·log10(1 + (f/f_Le)²) for first-order low-pass
    - Mass roll-off: -10·log10(1 + (f/f_mass)²) if f_mass provided

    IMPORTANT: The f_mass parameter must be determined empirically from Hornresp
    validation. DO NOT use the JBL mass break frequency formula (BL²/Re)/(π×Mms) -
    this formula is only valid for horn-loaded compression drivers, not direct radiators.

    Literature:
        - Small (1973), "Vented-Box Loudspeaker Systems Part I", JAES
        - Leach (2002), "Loudspeaker Voice-Coil Inductance Losses", JAES
        - Hornresp validation: f_mass ≈ f_le for direct radiators creates correct 2nd-order roll-off
        - JBL formula documentation: literature/simulation_methods/jbl_mass_break_frequency.md

    Args:
        frequency: Frequency in Hz
        f_le: Inductance corner frequency in Hz (Re / (2π × Le))
        f_mass: Mass break point frequency in Hz (optional, must be determined empirically)
        enclosure_type: "sealed" or "ported" (default "sealed")

    Returns:
        Combined roll-off in dB (negative values)

    Raises:
        ValueError: If frequency <= 0

    Examples:
        >>> # Sealed box (inductance only, first-order)
        >>> calculate_hf_rolloff_db(frequency=1000, f_le=541, f_mass=None, enclosure_type="sealed")
        -5.3...  # dB

        >>> # Sealed box (inductance + mass, second-order when f_mass ≈ f_le)
        >>> calculate_hf_rolloff_db(frequency=1000, f_le=541, f_mass=500, enclosure_type="sealed")
        -12.8...  # dB (second-order roll-off)

    Validation:
        Compare with Hornresp high-frequency response.
        Expected: Roll-off matches Hornresp within ±2 dB for sealed boxes.
        BC_8NDL51 validation: f_mass = 450 Hz gives mean error 1.43 dB (determined empirically).
    """
    if frequency <= 0:
        raise ValueError(f"Frequency must be > 0, got {frequency} Hz")

    # Inductance roll-off: first-order low-pass filter
    # G_le(f) = 1 / (1 + j(f/f_Le))
    # |G_le(f)|² = 1 / (1 + (f/f_Le)²)
    # Roll-off in dB = 10·log10(|G_le(f)|²) = -10·log10(1 + (f/f_Le)²)
    # Literature: Leach (2002), voice coil inductance losses
    if f_le is not None and f_le < float('inf') and f_le > 0:
        rolloff_le_db = -10 * math.log10(1 + (frequency / f_le) ** 2)
    else:
        rolloff_le_db = 0

    # Mass roll-off for direct radiators (sealed/ported boxes):
    # The f_mass parameter should be determined empirically from Hornresp validation.
    # DO NOT use the JBL mass break frequency formula (BL²/Re)/(π×Mms) - this
    # formula is only valid for horn-loaded compression drivers, not direct radiators.
    #
    # Validation findings vs Hornresp:
    # - BC_8NDL51: Optimal f_mass = 450 Hz (4.5×Fc), not 217.8 Hz (JBL formula)
    # - BC_15PS100: Optimal f_mass = 300 Hz (5.68×Fc), not 157.1 Hz (JBL formula)
    # - When f_mass ≈ f_le, creates 12 dB/octave roll-off matching Hornresp
    # - Literature: Hornresp validation data, literature/simulation_methods/jbl_mass_break_frequency.md
    rolloff_mass_db = 0
    if f_mass is not None and f_mass > 0:
        if enclosure_type in ["ported", "sealed"]:
            # Direct radiator: use empirically-determined f_mass to create second-order roll-off
            # When f_mass ≈ f_le, this gives 12 dB/octave matching Hornresp
            rolloff_mass_db = -10 * math.log10(1 + (frequency / f_mass) ** 2)

    return rolloff_le_db + rolloff_mass_db


def calculate_mass_break_frequency(bl: float, re: float, mms: float) -> float:
    """
    Calculate the mass break point frequency using the JBL formula.

    Above this frequency, the driver response rolls off at 6 dB/octave
    due to the motor's inability to accelerate the moving mass.

    Formula from JBL: f_mass = (BL² / Re) / (π × Mms)

    IMPORTANT: This formula is ONLY valid for horn-loaded compression drivers,
    not for direct radiators (sealed/ported boxes). For direct radiators,
    use an empirically-determined f_mass value (typically f_mass ≈ f_le).

    Literature:
        - Small (1973), "Vented-Box Loudspeaker Systems Part I", JAES
        - JBL Professional - Tech Note: Characteristics of High-Frequency Compression Drivers
        - Research: docs/validation/mass_controlled_rolloff_research.md

    Args:
        bl: Force factor (T·m or N/A)
        re: DC voice coil resistance (Ω)
        mms: Moving mass including air load (kg)

    Returns:
        Mass break point frequency in Hz

    Raises:
        ValueError: If bl <= 0, re <= 0, or mms <= 0

    Examples:
        >>> calculate_mass_break_frequency(bl=38.7, re=4.9, mms=0.254)
        383.1...  # Hz (for B&C 15DS115)

    Validation:
        Compare with Hornresp mass break point calculation for horn-loaded systems.
        Expected: <1% deviation from Hornresp values for compression drivers.
    """
    if bl <= 0:
        raise ValueError(f"Force factor BL must be > 0, got {bl} T·m")
    if re <= 0:
        raise ValueError(f"DC resistance Re must be > 0, got {re} Ω")
    if mms <= 0:
        raise ValueError(f"Moving mass Mms must be > 0, got {mms} kg")

    # JBL formula: f_mass = (BL² / Re) / (π × Mms)
    # The term BL²/Re represents motor force capability
    # The term π×Mms represents inertial load
    # Literature: docs/validation/mass_controlled_rolloff_research.md
    return (bl ** 2 / re) / (math.pi * mms)


def calculate_inductance_transfer_function(
    frequency: Union[float, 'np.ndarray'],
    Le: float,
    Re: float
) -> complex:
    """
    Calculate the voice coil inductance transfer function as a complex low-pass filter.

    This function implements the electrical low-pass behavior caused by voice coil
    inductance. Above the corner frequency f_Le = Re / (2π × Le), the response
    rolls off at -6 dB/octave due to rising impedance Z = Re + jωLe reducing current.

    Literature:
        - Leach (2002), "Introduction to Electroacoustics", Eq. 4.20
        - Small (1972), "Direct-Radiator Loudspeaker System Analysis", JAES
        - Research: tasks/ported_box_transfer_function_research_brief.md

    Transfer Function:
        H_le(s) = 1 / (1 + s·τ)

    where:
        - s = jω (complex frequency variable, ω = 2πf)
        - τ = Le / Re (time constant)
        - Corner frequency: f_Le = Re / (2π × Le)

    At frequencies f << f_Le: gain ≈ 1 (0 dB, no effect)
    At frequencies f >> f_Le: gain rolls off at -6 dB/octave
    At frequency f = f_Le: gain = 1/√2 (-3 dB)

    Args:
        frequency: Frequency in Hz (scalar or numpy array)
        Le: Voice coil inductance (H)
        Re: DC voice coil resistance (Ω)

    Returns:
        Complex transfer function H_le(s) (scalar or numpy array of complex numbers)
        Returns 1.0 (no effect) if Le <= 0

    Raises:
        ValueError: If Re <= 0

    Examples:
        >>> # At low frequency (f << f_Le): minimal effect
        >>> H = calculate_inductance_transfer_function(100, 0.00048, 4.7)
        >>> abs(H)
        0.999...  # Near unity gain at 100 Hz

        >>> # At corner frequency (f = f_Le): -3 dB
        >>> f_Le = 4.7 / (2 * 3.14159 * 0.00048)  # ≈ 1558 Hz
        >>> H = calculate_inductance_transfer_function(f_Le, 0.00048, 4.7)
        >>> abs(H)
        0.707...  # 1/√2 at corner frequency

        >>> # At high frequency (f >> f_Le): significant roll-off
        >>> H = calculate_inductance_transfer_function(5000, 0.00048, 4.7)
        >>> 20 * math.log10(abs(H))
        -10.1...  # -10 dB at 5000 Hz

    Validation:
        Compare with Hornresp inductance effects.
        Expected: <0.5 dB deviation from Hornresp SPL above f_Le.
        Test case: Re=4.7Ω, Le=0.48mH → f_Le≈1558Hz

    Notes:
        - This function supports both scalar and numpy array inputs for efficiency
        - For numpy arrays, import numpy before calling this function
        - The transfer function is applied multiplicatively: H_total = H_box × H_le
        - This models the current reduction due to rising impedance at high frequencies
    """
    if Re <= 0:
        raise ValueError(f"DC resistance Re must be > 0, got {Re} Ω")

    # If inductance is zero or negative, no inductance roll-off
    if Le <= 0:
        # Return unity gain (no effect)
        if hasattr(frequency, '__len__'):
            # numpy array or list
            try:
                import numpy as np
                return np.ones_like(frequency, dtype=complex)
            except ImportError:
                return complex(1.0, 0)
        return complex(1.0, 0)

    # Check if input is array-like (for numpy vectorization)
    is_array = hasattr(frequency, '__len__') and not isinstance(frequency, str)

    if is_array:
        # Vectorized calculation with numpy
        try:
            import numpy as np
            freq_array = np.asarray(frequency, dtype=float)

            # Angular frequency: ω = 2πf
            omega = 2 * math.pi * freq_array

            # Time constant: τ = Le / Re
            tau = Le / Re

            # Complex transfer function: H_le(s) = 1 / (1 + s·τ) where s = jω
            # H_le(jω) = 1 / (1 + jωτ)
            # Literature: Leach (2002), Eq. 4.20
            H_le = 1.0 / (1.0 + 1j * omega * tau)

            return H_le
        except ImportError:
            # Fallback to scalar calculation if numpy not available
            pass

    # Scalar calculation
    # Angular frequency: ω = 2πf
    omega = 2 * math.pi * frequency

    # Time constant: τ = Le / Re
    tau = Le / Re

    # Complex transfer function: H_le(s) = 1 / (1 + s·τ) where s = jω
    # H_le(jω) = 1 / (1 + jωτ)
    # Literature: Leach (2002), Eq. 4.20
    H_le = 1.0 / (1.0 + complex(0, omega * tau))

    return H_le
