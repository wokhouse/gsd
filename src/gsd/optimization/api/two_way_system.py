"""
Two-Way System Design API for Loudspeaker Systems.

This module provides high-level tools for designing complete two-way loudspeaker
systems, including crossover design and optimization for bi-amped configurations.

The workflow is:
1. Optimize LF enclosure (ported/sealed) using DesignAssistant
2. Optimize HF horn within physical constraints
3. Design crossover using CrossoverDesignAssistant
4. Optimize HF padding for bi-amped systems

Literature:
- Linkwitz (1976) - Active crossover networks
- D'Appolito (1984) - Optimizing two-way loudspeaker systems
- Small (1972) - Closed-box loudspeaker systems
- Olson (1947) - Horn loading theory
"""

import numpy as np
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass

from gsd.driver.parameters import ThieleSmallParameters
from gsd.driver import load_driver
from gsd.optimization.api.design_assistant import DesignAssistant
from gsd.optimization.api.crossover_assistant import CrossoverDesignAssistant


@dataclass
class TwoWaySystemDesign:
    """
    Complete two-way system design specification.

    Attributes:
        lf_driver_name: Low-frequency driver name
        hf_driver_name: High-frequency driver name
        lf_enclosure_type: Type of LF enclosure ('sealed', 'ported', 'horn')
        lf_enclosure_params: LF enclosure parameters (Vb, Fb, etc.)
        horn_params: HF horn parameters (if applicable)
        crossover_frequency: Crossover frequency in Hz
        hf_padding_db: HF driver padding in dB (for bi-amping)
        lf_padding_db: LF driver padding in dB (typically 0)
        f3: System -3 dB frequency (Hz)
        flatness: System passband flatness (dB)
        system_level: Maximum SPL in passband (dB)
    """
    lf_driver_name: str
    hf_driver_name: str
    lf_enclosure_type: str
    lf_enclosure_params: Dict
    horn_params: Optional[Dict]
    crossover_frequency: float
    hf_padding_db: float
    lf_padding_db: float
    f3: float
    flatness: float
    system_level: float

    def __str__(self) -> str:
        """Return formatted design summary."""
        lines = [
            "Two-Way System Design",
            "=" * 70,
            f"",
            f"LF Driver: {self.lf_driver_name}",
            f"  Enclosure: {self.lf_enclosure_type}",
            f"  Parameters: {self.lf_enclosure_params}",
            f"",
            f"HF Driver: {self.hf_driver_name}",
        ]

        if self.horn_params:
            lines.append(f"  Horn Parameters:")
            for key, value in self.horn_params.items():
                lines.append(f"    {key}: {value}")

        lines.extend([
            f"",
            f"Crossover:",
            f"  Frequency: {self.crossover_frequency:.0f} Hz",
            f"  HF Padding: {self.hf_padding_db:.2f} dB",
            f"  LF Padding: {self.lf_padding_db:.2f} dB",
            f"",
            f"Performance:",
            f"  F3: {self.f3:.1f} Hz",
            f"  Flatness: {self.flatness:.2f} dB",
            f"  System Level: {self.system_level:.1f} dB",
            f"",
            "=" * 70,
        ])

        return "\n".join(lines)


def optimize_hf_padding_for_flatness(
    lf_driver_name: str,
    hf_driver_name: str,
    lf_enclosure_type: str,
    lf_enclosure_params: Dict,
    horn_params: Dict,
    crossover_frequency: float,
    padding_range: Tuple[float, float] = (-25, -10),
    num_steps: int = 31
) -> float:
    """
    Optimize HF driver padding for best system flatness (bi-amped systems).

    For bi-amped systems with digital crossovers, the HF level can be adjusted
    to optimize system flatness. This function sweeps HF padding values and
    returns the optimal value.

    The F3 calculation uses the LF driver's passband as reference (80-200 Hz
    for typical woofers), not the system passband which would be skewed by
    the HF horn's higher sensitivity.

    Literature:
        - Small (1972) - F3 definition for enclosure systems
        - D'Appolito (1984) - System flatness optimization

    Args:
        lf_driver_name: Low-frequency driver name
        hf_driver_name: High-frequency driver name (for horn model)
        lf_enclosure_type: 'sealed', 'ported', or 'horn'
        lf_enclosure_params: LF enclosure parameters (Vb, Fb, etc.)
        horn_params: Horn parameters (cutoff, length, throat_area, mouth_area)
        crossover_frequency: Crossover frequency in Hz
        padding_range: (min, max) padding range in dB (default: -25 to -10)
        num_steps: Number of padding values to test

    Returns:
        Optimal HF padding in dB

    Example:
        >>> optimal_pad = optimize_hf_padding_for_flatness(
        ...     lf_driver_name="BC_12FW88",
        ...     hf_driver_name="BC_DH450",
        ...     lf_enclosure_type="ported",
        ...     lf_enclosure_params={"Vb": 0.1145, "Fb": 46.4},
        ...     horn_params={"cutoff": 400, "length": 0.24},
        ...     crossover_frequency=1000
        ... )
        >>> print(f"Optimal HF padding: {optimal_pad:.2f} dB")
        Optimal HF padding: -15.50 dB
    """
    from gsd.enclosure.ported_box import calculate_spl_ported_transfer_function

    # Load drivers
    lf_driver = load_driver(lf_driver_name)
    hf_driver = load_driver(hf_driver_name)

    # Frequency array
    freq = np.logspace(np.log10(20), np.log10(20000), 500)

    # Get LF response
    if lf_enclosure_type == "ported":
        Vb = lf_enclosure_params["Vb"]
        Fb = lf_enclosure_params["Fb"]
        lf_response = np.array([
            calculate_spl_ported_transfer_function(f, lf_driver, Vb, Fb)
            for f in freq
        ])
    elif lf_enclosure_type == "sealed":
        from gsd.enclosure.sealed_box import calculate_spl_from_transfer_function
        Vb = lf_enclosure_params["Vb"]
        lf_response = np.array([
            calculate_spl_from_transfer_function(f, lf_driver, Vb)
            for f in freq
        ])
    else:
        raise ValueError(f"Unsupported enclosure type: {lf_enclosure_type}")

    # Get horn parameters
    horn_fc = horn_params.get("cutoff", 800)
    hf_sensitivity = 110  # Default for compression drivers

    # Calculate HF response (horn model)
    hf_response = np.zeros_like(freq)
    for i, f in enumerate(freq):
        if f > 5000:
            # HF beaming rolloff
            hf_rolloff = 3 * np.log2(f / 5000)
            transition = 0.5 * (1 + np.tanh((f - 7000) / 1000))
            hf_response[i] = hf_sensitivity - hf_rolloff * transition
        elif f <= horn_fc / 2:
            # Below cutoff: 12 dB/octave rolloff
            octaves_below = np.log2(max(f, 10) / horn_fc)
            hf_response[i] = hf_sensitivity + octaves_below * 12
        elif f <= horn_fc * 1.5:
            # Transition region with smooth blend
            blend = (f - horn_fc/2) / horn_fc
            blend_smooth = blend * blend * (3 - 2 * blend)
            octaves_below = np.log2(max(f, 10) / horn_fc)
            below_cutoff = hf_sensitivity + octaves_below * 12
            hf_response[i] = below_cutoff * (1 - blend_smooth) + hf_sensitivity * blend_smooth
        else:
            # Above cutoff: nominal sensitivity
            hf_response[i] = hf_sensitivity

    # Calculate LF passband level (for F3 reference)
    # Use 80-200 Hz range for woofer passband
    lf_passband = (freq >= 80) & (freq <= 200)
    lf_passband_level = np.max(lf_response[lf_passband])

    # Sweep HF padding values
    padding_values = np.linspace(padding_range[0], padding_range[1], num_steps)
    flatness_values = []

    for pad in padding_values:
        # Apply padding
        hf_padded = hf_response + pad

        # Apply LR4 crossover
        lp_gain = np.zeros_like(freq)
        hp_gain = np.zeros_like(freq)

        for i, f in enumerate(freq):
            ratio = f / crossover_frequency
            # LR4: 4th order Linkwitz-Riley
            lp_gain[i] = 1.0 / (1.0 + ratio**4)
            hp_gain[i] = 1.0 / (1.0 + (1.0/ratio)**4)

        lp_gain_db = 20 * np.log10(lp_gain + 1e-10)
        hp_gain_db = 20 * np.log10(hp_gain + 1e-10)

        # Combine responses
        lf_combined = lf_response + lp_gain_db
        hf_combined = hf_padded + hp_gain_db

        # Power sum
        system_response = 10 * np.log10(
            10**(lf_combined/10) + 10**(hf_combined/10)
        )

        # Calculate flatness in passband
        passband = (freq >= 100) & (freq <= 10000)
        if np.sum(passband) > 0:
            passband_response = system_response[passband]
            flatness = np.max(passband_response) - np.min(passband_response)
        else:
            flatness = np.inf

        flatness_values.append(flatness)

    # Find optimal (minimum flatness)
    flatness_values = np.array(flatness_values)
    valid_mask = np.isfinite(flatness_values)

    if not np.any(valid_mask):
        raise ValueError("No valid responses found in padding range")

    best_idx = np.argmin(flatness_values[valid_mask])
    optimal_padding = padding_values[valid_mask][best_idx]

    return optimal_padding


def design_two_way_system(
    lf_driver_name: str,
    hf_driver_name: str,
    lf_enclosure_type: str,
    crossover_range: Tuple[float, float] = (500, 3000),
    optimize_hf_padding: bool = True,
    horn_constraints: Optional[Dict] = None,
    **kwargs
) -> TwoWaySystemDesign:
    """
    Design complete two-way loudspeaker system.

    This is a high-level function that orchestrates the complete two-way system
    design workflow:

    1. Optimize LF enclosure using DesignAssistant
    2. Optimize HF horn (if compression driver) with constraints
    3. Design crossover using CrossoverDesignAssistant
    4. Optimize HF padding for bi-amped systems (optional)

    Literature:
        - Small (1972) - Enclosure alignment theory
        - D'Appolito (1984) - Two-way system optimization
        - Linkwitz (1976) - Crossover design

    Args:
        lf_driver_name: Low-frequency driver name
        hf_driver_name: High-frequency driver name
        lf_enclosure_type: 'sealed', 'ported', or 'horn'
        crossover_range: (min, max) crossover frequency range (Hz)
        optimize_hf_padding: If True, optimize HF padding for flatness
        horn_constraints: Optional dict with horn size constraints:
            - max_length: Maximum horn length (m)
            - max_mouth_area: Maximum mouth area (m²)
            - max_volume: Maximum horn volume (m³)
            - target_cutoff: Target horn cutoff frequency (Hz)
        **kwargs: Additional parameters passed to DesignAssistant.optimize_design()

    Returns:
        TwoWaySystemDesign with complete specification

    Example:
        >>> design = design_two_way_system(
        ...     lf_driver_name="BC_12FW88",
        ...     hf_driver_name="BC_DH450",
        ...     lf_enclosure_type="ported",
        ...     horn_constraints={"max_length": 0.25, "target_cutoff": 400}
        ... )
        >>> print(design)
        Two-Way System Design
        ...

    Note:
        This function requires that drivers be available in the driver database.
        For compression drivers, horn_params will be generated automatically.
    """
    # Step 1: Optimize LF enclosure
    print("Step 1: Optimizing LF enclosure...")
    assistant = DesignAssistant(validation_mode=False)

    lf_result = assistant.optimize_design(
        driver_name=lf_driver_name,
        enclosure_type=lf_enclosure_type,
        objectives=["f3", "flatness"],
        **kwargs
    )

    if not lf_result.success:
        raise ValueError(f"LF enclosure optimization failed: {lf_result.warnings}")

    # Extract best LF design
    best_lf = lf_result.best_designs[0]
    lf_enclosure_params = {
        k: float(v) for k, v in best_lf['parameters'].items()
    }

    # Step 2: Design crossover
    print("\nStep 2: Designing crossover...")
    xo_assistant = CrossoverDesignAssistant(validation_mode=False)

    # Get HF driver to check if compression driver
    hf_driver = load_driver(hf_driver_name)
    is_compression_driver = hf_driver.F_s > 500  # Typical for compression drivers

    horn_params = None
    if is_compression_driver and horn_constraints:
        # Generate horn parameters based on constraints
        # This is a simplified approach - for production, use proper horn optimization
        from gsd.optimization.parameters.exponential_horn_params import (
            calculate_horn_cutoff_frequency
        )

        # Default horn parameters (user should override with proper optimization)
        target_cutoff = horn_constraints.get("target_cutoff", 500)
        horn_params = {
            "cutoff": target_cutoff,
            "length": horn_constraints.get("max_length", 0.3) * 0.9,
        }

    # Design crossover
    crossover_design = xo_assistant.design_crossover(
        lf_driver_name=lf_driver_name,
        hf_driver_name=hf_driver_name,
        lf_enclosure_type=lf_enclosure_type,
        lf_enclosure_params=lf_enclosure_params,
        hf_horn_params=horn_params,
        crossover_range=crossover_range,
    )

    # Step 3: Optimize HF padding for bi-amped systems
    if optimize_hf_padding and horn_params:
        print("\nStep 3: Optimizing HF padding for bi-amped system...")
        hf_padding = optimize_hf_padding_for_flatness(
            lf_driver_name=lf_driver_name,
            hf_driver_name=hf_driver_name,
            lf_enclosure_type=lf_enclosure_type,
            lf_enclosure_params=lf_enclosure_params,
            horn_params=horn_params,
            crossover_frequency=crossover_design.crossover_frequency,
        )
    else:
        hf_padding = crossover_design.hf_padding_db

    # Step 4: Calculate final system performance
    print("\nStep 4: Calculating final system performance...")
    from gsd.enclosure.ported_box import calculate_spl_ported_transfer_function

    lf_driver = load_driver(lf_driver_name)

    # Calculate responses with final padding
    freq = np.logspace(np.log10(20), np.log10(20000), 500)

    if lf_enclosure_type == "ported":
        Vb = lf_enclosure_params["Vb"]
        Fb = lf_enclosure_params["Fb"]
        lf_response = np.array([
            calculate_spl_ported_transfer_function(f, lf_driver, Vb, Fb)
            for f in freq
        ])
    elif lf_enclosure_type == "sealed":
        from gsd.enclosure.sealed_box import calculate_spl_from_transfer_function
        Vb = lf_enclosure_params["Vb"]
        lf_response = np.array([
            calculate_spl_from_transfer_function(f, lf_driver, Vb)
            for f in freq
        ])

    # Calculate F3 (using LF driver passband)
    lf_passband = (freq >= 80) & (freq <= 200)
    lf_passband_level = np.max(lf_response[lf_passband])
    threshold = lf_passband_level - 3

    # Find F3 crossing point
    below_threshold = lf_response < threshold
    f3 = np.nan
    if np.any(below_threshold):
        for i in range(len(freq) - 1):
            if lf_response[i] < threshold and lf_response[i + 1] >= threshold:
                # Linear interpolation
                f1, f2 = freq[i], freq[i + 1]
                r1, r2 = lf_response[i], lf_response[i + 1]
                f3 = f1 + (threshold - r1) * (f2 - f1) / (r2 - r1)
                break

    # Calculate system flatness
    # (Would need full system response calculation - placeholder for now)
    flatness = best_lf['objectives']['flatness']

    # Calculate system level
    system_level = np.max(lf_response[lf_passband])

    return TwoWaySystemDesign(
        lf_driver_name=lf_driver_name,
        hf_driver_name=hf_driver_name,
        lf_enclosure_type=lf_enclosure_type,
        lf_enclosure_params=lf_enclosure_params,
        horn_params=horn_params,
        crossover_frequency=crossover_design.crossover_frequency,
        hf_padding_db=hf_padding,
        lf_padding_db=0.0,
        f3=f3,
        flatness=flatness,
        system_level=system_level,
    )
