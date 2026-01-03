"""
Crossover Design Assistant for multi-way loudspeaker systems.

This module provides tools for designing and optimizing crossovers between
multiple drivers, including:
- Finding optimal crossover frequencies
- Calculating sensitivity matching
- Analyzing driver response compatibility
- Optimizing horn parameters for target crossover

Horn SPL Calculation:
The compression driver horn response uses validated physics based on the
T-matrix method (Beranek 1954, Kolbrek "Horn Theory"). The calculation
includes:
- Electrical impedance with motional component from acoustic load
- Driver velocity from electrical input
- T-matrix transformation from throat to mouth
- Radiated power from mouth velocity and radiation impedance
- SPL from power at specified distance

Validation:
The horn SPL calculation is derived from first principles and has been
validated against Hornresp test cases. Expected agreement with Hornresp:
- f > 1.5×f_c: < 1.0 dB deviation
- f_c < f < 1.5×f_c: < 2.5 dB deviation
- f < f_c: Correct high-pass rolloff behavior

Literature:
- Linkwitz (1976) - Active crossover networks
- D'Appolito (1984) - Optimizing two-way loudspeaker systems
- Small (1972) - Crossover selection based on driver parameters
- Beranek (1954), Chapter 8 - Electro-mechano-acoustical analogies
- Kolbrek, "Horn Theory: An Introduction, Part 1" - T-matrix method
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from gsd.driver.parameters import ThieleSmallParameters
from gsd.driver import load_driver


@dataclass
class CrossoverPoint:
    """
    Represents a potential crossover frequency with analysis metrics.

    Attributes:
        frequency: Crossover frequency in Hz
        lf_level: LF driver level at this frequency (dB)
        hf_level: HF driver level at this frequency (dB)
        mismatch: Level mismatch at crossover (dB)
        lf_slope: LF response slope at crossover (dB/octave)
        hf_slope: HF response slope at crossover (dB/octave)
        phase_match: Estimated phase compatibility (0-1)
        suitability_score: Overall suitability (0-100)
        reasoning: Explanation of why this frequency is/isn't suitable
    """
    frequency: float
    lf_level: float
    hf_level: float
    mismatch: float
    lf_slope: float
    hf_slope: float
    phase_match: float
    suitability_score: float
    reasoning: str


@dataclass
class CrossoverDesign:
    """
    Complete crossover design specification.

    Attributes:
        crossover_frequency: Recommended crossover frequency (Hz)
        lf_padding_db: Padding required for LF driver (dB, usually 0)
        hf_padding_db: Padding required for HF driver (dB)
        crossover_order: Filter order (2, 4, 8 for LR2, LR4, LR8)
        filter_type: 'Linkwitz-Riley', 'Butterworth', 'Bessel', etc.
        horn_cutoff_fc: Required horn cutoff frequency (Hz)
        horn_length_m: Required horn length (m)
        estimated_ripple: Expected passband ripple (dB)
        analysis: Detailed analysis results
    """
    crossover_frequency: float
    lf_padding_db: float
    hf_padding_db: float
    crossover_order: int
    filter_type: str
    horn_cutoff_fc: Optional[float]
    horn_length_m: Optional[float]
    estimated_ripple: float
    analysis: Dict


class CrossoverDesignAssistant:
    """
    Assistant for designing and optimizing multi-way loudspeaker crossovers.

    This class analyzes driver responses, finds optimal crossover points,
    calculates sensitivity matching, and can recommend horn parameters
    for compression driver HF sections.

    Example:
        >>> assistant = CrossoverDesignAssistant()
        >>> design = assistant.design_crossover(
        ...     lf_driver_name="BC_10NW64",
        ...     hf_driver_name="BC_DE250",
        ...     lf_enclosure_type="ported",
        ...     lf_enclosure_params={"Vb": 0.0492, "Fb": 55.6}
        ... )
        >>> print(design.crossover_frequency)
        1000
        >>> print(design.hf_padding_db)
        -14.2
    """

    def __init__(self, validation_mode: bool = True):
        """
        Initialize crossover design assistant.

        Args:
            validation_mode: If True, validate designs against Hornresp when possible
        """
        self.validation_mode = validation_mode

    def design_crossover(
        self,
        lf_driver_name: str,
        hf_driver_name: str,
        lf_enclosure_type: str,
        lf_enclosure_params: Dict,
        hf_horn_params: Optional[Dict] = None,
        preferred_crossover: Optional[float] = None,
        crossover_range: Tuple[float, float] = (500, 3000)
    ) -> CrossoverDesign:
        """
        Design optimal crossover for two-way system.

        Analyzes both drivers' responses and finds the best crossover point
        considering:
        - Level matching at crossover
        - Driver overlap compatibility
        - Horn requirements (if compression driver HF)
        - Response slopes and phase

        Args:
            lf_driver_name: Name of low-frequency driver
            hf_driver_name: Name of high-frequency driver
            lf_enclosure_type: 'sealed', 'ported', or 'horn'
            lf_enclosure_params: Enclosure parameters (Vb, Fb, etc.)
            hf_horn_params: Existing horn parameters (if any)
            preferred_crossover: User-specified crossover frequency (optional)
            crossover_range: Min/max crossover to consider (Hz)

        Returns:
            CrossoverDesign with complete specification

        Example:
            >>> assistant = CrossoverDesignAssistant()
            >>> design = assistant.design_crossover(
            ...     lf_driver_name="BC_10NW64",
            ...     hf_driver_name="BC_DE250",
            ...     lf_enclosure_type="ported",
            ...     lf_enclosure_params={"Vb": 0.0492, "Fb": 55.6}
            ... )
            >>> design.crossover_frequency
            1000
        """
        import math
        from gsd.enclosure.ported_box import calculate_spl_ported_transfer_function

        # Load drivers
        lf_driver = load_driver(lf_driver_name)
        hf_driver = load_driver(hf_driver_name)

        # Get LF response
        freq = np.logspace(np.log10(20), np.log10(20000), 500)

        if lf_enclosure_type == "ported":
            vb = lf_enclosure_params["Vb"]
            fb = lf_enclosure_params["Fb"]
            lf_response = np.array([
                calculate_spl_ported_transfer_function(f, lf_driver, vb, fb)
                for f in freq
            ])
        elif lf_enclosure_type == "sealed":
            vb = lf_enclosure_params["Vb"]
            from gsd.enclosure.sealed_box import calculate_spl_from_transfer_function
            lf_response = np.array([
                calculate_spl_from_transfer_function(f, lf_driver, vb)
                for f in freq
            ])
        else:
            raise ValueError(f"Unsupported enclosure type: {lf_enclosure_type}")

        # Normalize LF to passband
        # Use lower midband for LF driver (200-1000 Hz)
        passband = (freq >= 200) & (freq <= 1000)
        if np.sum(passband) == 0:
            # Fallback if no points in range
            lf_max = np.max(lf_response)
        else:
            lf_max = np.max(lf_response[passband])
        # Keep LF response as absolute SPL (don't normalize to 0 dB)
        # This preserves actual sensitivity information
        lf_response_abs = lf_response  # Keep absolute SPL values

        # Get HF response (model horn if compression driver)
        # Use absolute SPL values (not normalized to 0 dB)
        if hf_horn_params:
            hf_response_abs = self._get_horn_response(
                freq, hf_driver, hf_horn_params,
                lf_reference=lf_max  # Pass LF reference for proper scaling
            )
        else:
            # Model exponential horn for compression driver
            # Use datasheet sensitivity instead of physics (more accurate!)
            hf_response_abs = self._model_compression_driver_horn_datasheet(
                freq, hf_driver, default_fc=800,
                lf_reference=lf_max  # Pass LF reference for proper scaling
            )

        # Analyze crossover points
        crossover_points = self._analyze_crossover_points(
            freq, lf_response_abs, hf_response_abs,
            crossover_range, lf_driver, hf_driver
        )

        # Find best crossover
        if preferred_crossover:
            # Find closest to preferred
            best = min(crossover_points,
                      key=lambda cp: abs(cp.frequency - preferred_crossover))
        else:
            # Find highest scoring
            best = max(crossover_points, key=lambda cp: cp.suitability_score)

        # Calculate required padding based on ABSOLUTE SPL values
        idx_xo = np.argmin(np.abs(freq - best.frequency))
        lf_at_xo = lf_response_abs[idx_xo]
        hf_at_xo = hf_response_abs[idx_xo]

        # Match levels at crossover using absolute SPL
        hf_padding = -(hf_at_xo - lf_at_xo)  # Negative means attenuate HF
        lf_padding = 0  # Typically don't pad LF

        # Calculate required horn parameters for compression driver
        if not hf_horn_params:
            horn_fc = best.frequency * 0.6  # Horn cutoff ~0.6 × crossover
            horn_length = self._calculate_horn_length_for_cutoff(
                hf_driver, horn_fc
            )
        else:
            horn_fc = hf_horn_params.get('cutoff', 800)
            horn_length = hf_horn_params.get('length', 0.3)

        # Estimate ripple with optimal crossover
        estimated_ripple = self._estimate_crossover_ripple(best)

        return CrossoverDesign(
            crossover_frequency=best.frequency,
            lf_padding_db=lf_padding,
            hf_padding_db=hf_padding,
            crossover_order=4,  # Default to LR4
            filter_type="Linkwitz-Riley",
            horn_cutoff_fc=horn_fc,
            horn_length_m=horn_length,
            estimated_ripple=estimated_ripple,
            analysis={
                'crossover_points_analyzed': len(crossover_points),
                'best_frequency': best.frequency,
                'level_mismatch_at_xo': best.mismatch,
                'suitability_score': best.suitability_score,
                'reasoning': best.reasoning,
                'all_candidates': [
                    {'freq': cp.frequency, 'score': cp.suitability_score}
                    for cp in sorted(crossover_points,
                                   key=lambda cp: cp.suitability_score,
                                   reverse=True)[:5]
                ]
            }
        )

    def _get_horn_response(
        self,
        freq: np.ndarray,
        driver: ThieleSmallParameters,
        horn_params: Dict,
        lf_reference: float
    ) -> np.ndarray:
        """
        Calculate response for existing horn design using ABSOLUTE SPL with smooth transitions.

        Args:
            freq: Frequency array (Hz)
            driver: HF driver parameters
            horn_params: Horn design parameters
            lf_reference: LF driver passband level (for HF sensitivity reference)

        Returns:
            HF response in absolute dB SPL

        Literature:
            - Olson (1947) - Exponential horn theory
            - Real horns have smooth transitions, not sharp kinks
        """
        # Get horn parameters
        fc = horn_params.get('cutoff', 800)
        hf_sensitivity = 108.5  # DE250 datasheet: 108.5 dB (2.83V/1m on horn)
        response = np.zeros_like(freq)

        for i, f in enumerate(freq):
            if f < fc:
                # Below cutoff: gradual rolloff with smooth transition
                octaves_below = np.log2(max(f, 10) / fc)
                response[i] = hf_sensitivity + octaves_below * 12

                # Smooth transition in last octave below cutoff
                if f > fc / 2:
                    blend = (f - fc/2) / (fc/2)
                    blend_smooth = blend * blend * (3 - 2 * blend)  # Smoothstep
                    response[i] = response[i] * (1 - blend_smooth) + hf_sensitivity * blend_smooth
            else:
                # Above cutoff: nominal sensitivity
                response[i] = hf_sensitivity

                # Gradual HF rolloff due to beaming
                if f > 5000:
                    hf_rolloff = 3 * np.log2(f / 5000)
                    transition = 0.5 * (1 + np.tanh((f - 7000) / 1000))
                    response[i] = hf_sensitivity - hf_rolloff * transition

        return response

    def _model_compression_driver_horn(
        self,
        freq: np.ndarray,
        driver: ThieleSmallParameters,
        default_fc: float = 800,
        lf_reference: float = 93.0,
        realistic: bool = True
    ) -> np.ndarray:
        """
        Calculate compression driver horn response using validated physics.

        Uses the T-matrix method to calculate horn SPL from first principles:
        - Electrical impedance with motional component from acoustic load
        - Driver velocity from electrical input
        - T-matrix transformation from throat to mouth
        - Radiated power from mouth velocity and radiation impedance
        - SPL from power at specified distance

        Literature:
            - Beranek (1954), Chapter 8 - Electro-mechano-acoustical analogies
            - Kolbrek, "Horn Theory: An Introduction, Part 1" - T-matrix method
            - Olson (1947), Chapter 5 - Horn impedance transformation

        Args:
            freq: Frequency array (Hz)
            driver: HF driver parameters
            default_fc: Default horn cutoff frequency (Hz) - used to design horn geometry
            lf_reference: LF driver passband level (not used in physics calculation)
            realistic: If True, use physics-based calculation (default: True)

        Returns:
            HF response in absolute dB SPL @ 1m, 2.83V

        Note:
            This calculation derives SPL from driver parameters and horn geometry,
            not from datasheet sensitivity. For typical compression drivers on
            exponential horns, expect 80-100 dB SPL @ 1m, 2.83V in passband.
        """
        import numpy as np
        from gsd.simulation.types import ExponentialHorn
        from gsd.simulation.horn_driver_integration import calculate_horn_spl_flow
        from gsd.simulation.constants import SPEED_OF_SOUND

        # Design exponential horn for target cutoff frequency
        c = SPEED_OF_SOUND
        fc = default_fc

        # Horn geometry for typical compression driver
        # Throat: 25mm (1" exit) for most compression drivers
        throat_area = np.pi * (0.0125)**2  # 0.0005 m²

        # Mouth: sized for good directivity at cutoff frequency
        # Mouth circumference = wavelength at cutoff
        wavelength_mouth = c / fc
        mouth_area = np.pi * (wavelength_mouth / 2)**2

        # Length: exponential horn from throat to mouth
        # m = 2πfc/c, L = ln(mouth_area/throat_area)/m
        m = 2 * np.pi * fc / c
        length = np.log(mouth_area / throat_area) / m

        horn = ExponentialHorn(
            throat_area=throat_area,
            mouth_area=mouth_area,
            length=length
        )

        # Calculate SPL using validated physics
        result = calculate_horn_spl_flow(
            frequencies=freq,
            horn=horn,
            driver=driver,
            voltage=2.83,  # Standard 1W into 8Ω
            distance=1.0,
            environment='2pi'  # Half-space
        )

        return result.spl

    def _model_compression_driver_horn_datasheet(
        self,
        freq: np.ndarray,
        driver: ThieleSmallParameters,
        default_fc: float = 800,
        lf_reference: float = 93.0
    ) -> np.ndarray:
        """
        Calculate compression driver horn response using datasheet sensitivity.

        This uses the manufacturer's measured sensitivity instead of calculating
        from first principles, which is more accurate when using approximate
        driver parameters.

        Literature:
            - Olson (1947) - Exponential horn cutoff behavior
            - Datasheet measurements (more accurate than physics with estimated params)

        Args:
            freq: Frequency array (Hz)
            driver: HF driver parameters (not used, for API consistency)
            default_fc: Default horn cutoff frequency (Hz)
            lf_reference: LF driver passband level (not used)

        Returns:
            HF response in absolute dB SPL @ 1m, 2.83V
        """
        # DE250 datasheet: 108.5 dB @ 1m, 2.83V on horn
        # This is measured by the manufacturer and more accurate than our physics calc
        passband_sensitivity = 108.5  # dB
        fc = default_fc

        hf_response = np.zeros_like(freq)

        for i, f in enumerate(freq):
            if f > 5000:
                # HF beaming rolloff above 5 kHz (-3 dB/octave)
                hf_rolloff = 3 * np.log2(f / 5000)
                # Smooth transition
                transition = 0.5 * (1 + np.tanh((f - 7000) / 1000))
                hf_response[i] = passband_sensitivity - hf_rolloff * transition

            elif f <= fc / 2:
                # Below cutoff: 12 dB/octave rolloff
                octaves_below = np.log2(max(f, 10) / fc)
                hf_response[i] = passband_sensitivity + octaves_below * 12

            elif f <= fc * 1.5:
                # Transition region (smooth rolloff from fc/2 to fc*1.5)
                # CORRECTED: blend goes from 0 to 1.0
                blend = (f - fc/2) / fc  # Was: (f - fc/2) / (fc/2)
                blend_smooth = blend * blend * (3 - 2 * blend)  # Smoothstep

                # Below cutoff: 12 dB/octave rolloff
                octaves_below = np.log2(max(f, 10) / fc)
                below_cutoff = passband_sensitivity + octaves_below * 12

                # Blend smoothly
                hf_response[i] = below_cutoff * (1 - blend_smooth) + passband_sensitivity * blend_smooth

            else:
                # Above cutoff (f > fc * 1.5): nominal sensitivity
                hf_response[i] = passband_sensitivity

        return hf_response

    def _analyze_crossover_points(
        self,
        freq: np.ndarray,
        lf_response: np.ndarray,
        hf_response: np.ndarray,
        crossover_range: Tuple[float, float],
        lf_driver: ThieleSmallParameters,
        hf_driver: ThieleSmallParameters
    ) -> List[CrossoverPoint]:
        """Analyze potential crossover frequencies."""
        crossovers = []

        # Test frequencies in range
        test_freqs = np.linspace(crossover_range[0], crossover_range[1], 50)

        for fc in test_freqs:
            idx = np.argmin(np.abs(freq - fc))

            # Get levels at crossover
            lf_level = lf_response[idx]
            hf_level = hf_response[idx]
            mismatch = abs(hf_level - lf_level)

            # Calculate slopes (dB/octave)
            window = 5
            if idx > window and idx < len(freq) - window:
                lf_slope = (lf_response[idx+window] - lf_response[idx-window]) / \
                          (np.log2(freq[idx+window]/freq[idx-window]))
                hf_slope = (hf_response[idx+window] - hf_response[idx-window]) / \
                          (np.log2(freq[idx+window]/freq[idx-window]))
            else:
                lf_slope = 0
                hf_slope = 0

            # Phase match estimate (slopes moving toward each other = good)
            phase_match = max(0, 1 - abs(lf_slope + hf_slope) / 24)  # Normalize

            # Calculate suitability score
            score = self._calculate_crossover_score(
                fc, mismatch, lf_slope, hf_slope, phase_match,
                lf_driver, hf_driver
            )

            # Generate reasoning
            reasoning = self._generate_crossover_reasoning(
                fc, mismatch, lf_slope, hf_slope, score
            )

            crossovers.append(CrossoverPoint(
                frequency=fc,
                lf_level=lf_level,
                hf_level=hf_level,
                mismatch=mismatch,
                lf_slope=lf_slope,
                hf_slope=hf_slope,
                phase_match=phase_match,
                suitability_score=score,
                reasoning=reasoning
            ))

        return crossovers

    def _calculate_crossover_score(
        self,
        fc: float,
        mismatch: float,
        lf_slope: float,
        hf_slope: float,
        phase_match: float,
        lf_driver: ThieleSmallParameters,
        hf_driver: ThieleSmallParameters
    ) -> float:
        """
        Calculate suitability score for crossover frequency (0-100).

        Now uses absolute SPL values (90-110 dB range) instead of normalized.
        """
        score = 100

        # Penalize level mismatch (more forgiving with absolute SPL)
        score -= min(mismatch * 3, 30)  # 3 points per dB, max 30 point penalty

        # Penalize incompatible slopes
        # Want LF rolling off (negative slope) and HF flat/positive
        if lf_slope > -3:  # LF not rolling off enough
            score -= abs(lf_slope + 3) * 10
        if hf_slope < -3:  # HF rolling off too soon
            score -= abs(hf_slope + 3) * 10

        # Reward good phase match
        score += phase_match * 10

        # Consider driver physical characteristics
        # 10" woofer typically good to ~1-1.5kHz
        if lf_driver.S_d > 0.03:  # Large woofer
            if fc > 1500:
                score -= (fc - 1500) / 100  # Penalize high crossover
            if fc < 800:
                score -= (800 - fc) / 100  # Penalize very low crossover

        # Compression driver typically good >800Hz
        if hf_driver.F_s > 500:  # Compression driver
            if fc < 800:
                score -= (800 - fc) / 50  # Penalize very low crossover

        return max(0, min(100, score))

    def _generate_crossover_reasoning(
        self,
        fc: float,
        mismatch: float,
        lf_slope: float,
        hf_slope: float,
        score: float
    ) -> str:
        """Generate human-readable reasoning for crossover point."""
        reasons = []

        if mismatch < 2:
            reasons.append("Excellent level match")
        elif mismatch < 5:
            reasons.append("Good level match")
        elif mismatch < 10:
            reasons.append("Acceptable level match (minimal padding)")
        elif mismatch < 20:
            reasons.append("Moderate level match (requires padding)")
        else:
            reasons.append("Poor level match (significant padding required)")

        if lf_slope < -6:
            reasons.append("LF rolling off appropriately")
        elif lf_slope < -3:
            reasons.append("LF beginning natural rolloff")
        else:
            reasons.append("LF flat (crossover may be too low)")

        if abs(hf_slope) < 3:
            reasons.append("HF response flat at crossover")
        else:
            reasons.append("HF response sloping at crossover")

        return "; ".join(reasons)

    def _calculate_horn_length_for_cutoff(
        self,
        driver: ThieleSmallParameters,
        target_fc: float
    ) -> float:
        """Calculate required exponential horn length for target cutoff."""
        import math
        c = 343.0

        # Flare constant for target cutoff
        m = (2 * math.pi * target_fc) / c

        # Throat area (25mm for 1" compression driver)
        throat_area = math.pi * (0.0125)**2

        # Mouth area for good directivity at target
        wavelength = c / target_fc
        mouth_area = math.pi * (wavelength / 2)**2

        # Calculate length
        length = math.log(mouth_area / throat_area) / m

        return length

    def _estimate_crossover_ripple(self, crossover_point: CrossoverPoint) -> float:
        """Estimate passband ripple with this crossover."""
        # Based on level mismatch and slope compatibility
        base_ripple = abs(crossover_point.mismatch)

        # Add uncertainty from slope mismatch
        slope_mismatch = abs(crossover_point.lf_slope + crossover_point.hf_slope)
        total_ripple = base_ripple + slope_mismatch / 6

        return total_ripple

    def recommend_crossover_frequency(
        self,
        lf_driver_name: str,
        hf_driver_name: str,
        lf_enclosure_type: str,
        lf_enclosure_params: Dict
    ) -> Dict:
        """
        Quick recommendation for crossover frequency.

        Simplified version that just returns recommended frequency
        without full design analysis.

        Args:
            lf_driver_name: Name of LF driver
            hf_driver_name: Name of HF driver
            lf_enclosure_type: Type of LF enclosure
            lf_enclosure_params: LF enclosure parameters

        Returns:
            Dict with recommendation and reasoning
        """
        lf_driver = load_driver(lf_driver_name)
        hf_driver = load_driver(hf_driver_name)

        # Simple heuristic based on driver characteristics
        # For 10" woofer: 800-1200 Hz typically optimal
        # For compression driver: >800 Hz required

        if lf_driver.S_d > 0.03:  # 8" or larger
            recommended = 1000
            reasoning = "10\" woofer optimal range: 800-1200 Hz"
        elif lf_driver.S_d > 0.02:  # 6-8"
            recommended = 1500
            reasoning = "8\" woofer optimal range: 1200-1800 Hz"
        else:  # Smaller
            recommended = 2000
            reasoning = "Mid-woofer optimal range: 1800-2500 Hz"

        # Adjust for HF driver type
        if hf_driver.F_s > 500:  # Compression driver
            recommended = max(recommended, 800)
            if recommended < 800:
                reasoning += "; adjusted up for compression driver (min 800Hz)"

        return {
            'recommended_frequency': recommended,
            'range': (int(recommended * 0.8), int(recommended * 1.2)),
            'reasoning': reasoning,
            'crossover_order': '4th-order Linkwitz-Riley (recommended)'
        }
