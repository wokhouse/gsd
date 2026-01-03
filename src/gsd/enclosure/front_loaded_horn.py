"""
Front-loaded horn enclosure simulation.

This module implements the complete frequency response simulation for
front-loaded horn loudspeaker systems, combining driver electromechanical
parameters with horn acoustic theory.

Literature:
- Olson (1947), Chapter 8 - Horn driver systems
- Beranek (1954), Chapter 5 - Electromechanical analogies
- Small (1972) - Thiele-Small analysis
- literature/horns/olson_1947.md
- literature/horns/beranek_1954.md
- literature/thiele_small/small_1972_closed_box.md
"""

import math
import cmath
from dataclasses import dataclass
from typing import Optional
import numpy as np
from numpy.typing import NDArray

from gsd.driver.parameters import ThieleSmallParameters
from gsd.simulation.types import ExponentialHorn
from gsd.simulation.horn_theory import MediumProperties
from gsd.simulation.horn_driver_integration import (
    horn_electrical_impedance,
    horn_system_acoustic_impedance,
)
from gsd.simulation.constants import (
    SPEED_OF_SOUND,
    AIR_DENSITY,
    CHARACTERISTIC_IMPEDANCE_AIR,
    angular_frequency,
)

# Type aliases
FloatArray = NDArray[np.floating]


@dataclass
class FrontLoadedHorn:
    """
    Front-loaded horn enclosure system.

    Combines a driver with an exponential horn and optional throat/rear chambers.

    Literature:
        - Olson (1947), Chapter 8 - Complete horn driver systems
        - Beranek (1954), Chapter 5 - Acoustic impedance networks
        - literature/horns/olson_1947.md
        - literature/horns/beranek_1954.md

    Attributes:
        driver: ThieleSmallParameters instance
        horn: ExponentialHorn geometry
        V_tc: Throat chamber volume [m³], default 0 (no throat chamber)
        A_tc: Throat chamber area [m²], defaults to horn.throat_area
        V_rc: Rear chamber volume [m³], default 0 (no rear chamber)
        radiation_angle: Solid angle of radiation [steradians]
            - 4π: free field (pulsating sphere)
            - 2π: half-space (piston in infinite baffle) [default]

    Examples:
        >>> from gsd.driver import load_driver
        >>> from gsd.simulation.types import ExponentialHorn
        >>> driver = load_driver("BC_8NDL51")
        >>> horn = ExponentialHorn(0.001, 0.01, 0.3)
        >>> flh = FrontLoadedHorn(driver, horn)
        >>> result = flh.electrical_impedance(500)
        >>> result['Ze_magnitude']
        7.2...  # Ω
    """
    driver: ThieleSmallParameters
    horn: ExponentialHorn
    V_tc: float = 0.0  # Throat chamber volume [m³]
    A_tc: Optional[float] = None  # Throat chamber area [m²]
    V_rc: float = 0.0  # Rear chamber volume [m³]
    radiation_angle: float = 2 * np.pi  # Half-space

    def __post_init__(self):
        """Set default throat chamber area and validate parameters."""
        if self.A_tc is None:
            self.A_tc = self.horn.throat_area

    def electrical_impedance(
        self,
        frequency: float,
        voltage: float = 2.83,
        medium: Optional[MediumProperties] = None
    ) -> dict:
        """
        Calculate electrical impedance at a single frequency.

        Literature:
            - Olson (1947), Chapter 8 - Horn driver electrical impedance
            - Small (1972) - Electromechanical analogies
            - literature/horns/olson_1947.md
            - literature/thiele_small/small_1972_closed_box.md

        Args:
            frequency: Frequency [Hz]
            voltage: Input voltage [V], default 2.83V
            medium: Acoustic medium properties (uses default if None)

        Returns:
            Dictionary with electrical impedance and mechanical quantities:
            - 'frequency': Frequency (Hz)
            - 'Ze_magnitude': Electrical impedance magnitude (Ω)
            - 'Ze_phase': Electrical impedance phase (degrees)
            - 'Ze_real': Electrical resistance (Ω)
            - 'Ze_imag': Electrical reactance (Ω)
            - 'diaphragm_velocity': Diaphragm velocity magnitude (m/s)
            - 'diaphragm_displacement': Diaphragm displacement magnitude (m)
            - 'Z_front': Front acoustic impedance (Pa·s/m³)
            - 'Z_rear': Rear acoustic impedance (Pa·s/m³)

        Raises:
            ValueError: If frequency <= 0

        Examples:
            >>> flh.electrical_impedance(500)['Ze_magnitude']
            7.2...  # Ω

        Validation:
            Compare with Hornresp electrical impedance export.
            Expected: <2% magnitude, <5° phase for f > F_s/2
        """
        return horn_electrical_impedance(
            frequency=frequency,
            driver=self.driver,
            horn=self.horn,
            V_tc=self.V_tc,
            A_tc=self.A_tc,
            V_rc=self.V_rc,
            voltage=voltage,
            medium=medium,
            radiation_angle=self.radiation_angle,
        )

    def electrical_impedance_array(
        self,
        frequencies: FloatArray,
        voltage: float = 2.83,
        medium: Optional[MediumProperties] = None
    ) -> dict:
        """
        Calculate electrical impedance across frequency array.

        Vectorized version of electrical_impedance() for batch processing.

        Args:
            frequencies: Array of frequencies [Hz]
            voltage: Input voltage [V], default 2.83V
            medium: Acoustic medium properties (uses default if None)

        Returns:
            Dictionary with arrays:
            - 'frequencies': Frequency array (Hz)
            - 'Ze_magnitude': Electrical impedance magnitude array (Ω)
            - 'Ze_phase': Electrical impedance phase array (degrees)
            - 'Ze_real': Electrical resistance array (Ω)
            - 'Ze_imag': Electrical reactance array (Ω)
            - 'diaphragm_velocity': Diaphragm velocity array (m/s)
            - 'diaphragm_displacement': Diaphragm displacement array (m)

        Examples:
            >>> import numpy as np
            >>> freqs = np.logspace(1, 4, 100)
            >>> result = flh.electrical_impedance_array(freqs)
            >>> result['Ze_magnitude'].shape
            (100,)

        Validation:
            Compare with Hornresp electrical impedance export.
            Expected: <2% magnitude, <5° phase for f > F_s/2
        """
        frequencies = np.atleast_1d(frequencies).astype(float)

        # Pre-allocate result arrays
        Ze_magnitude = np.zeros_like(frequencies)
        Ze_phase = np.zeros_like(frequencies)
        Ze_real = np.zeros_like(frequencies)
        Ze_imag = np.zeros_like(frequencies)
        diaphragm_velocity = np.zeros_like(frequencies)
        diaphragm_displacement = np.zeros_like(frequencies)

        # Calculate at each frequency
        for i, f in enumerate(frequencies):
            result = self.electrical_impedance(f, voltage, medium)
            Ze_magnitude[i] = result['Ze_magnitude']
            Ze_phase[i] = result['Ze_phase']
            Ze_real[i] = result['Ze_real']
            Ze_imag[i] = result['Ze_imag']
            diaphragm_velocity[i] = result['diaphragm_velocity']
            diaphragm_displacement[i] = result['diaphragm_displacement']

        return {
            'frequencies': frequencies,
            'Ze_magnitude': Ze_magnitude,
            'Ze_phase': Ze_phase,
            'Ze_real': Ze_real,
            'Ze_imag': Ze_imag,
            'diaphragm_velocity': diaphragm_velocity,
            'diaphragm_displacement': diaphragm_displacement,
        }

    def acoustic_power(
        self,
        frequency: float,
        voltage: float = 2.83,
        medium: Optional[MediumProperties] = None
    ) -> float:
        """
        Calculate acoustic power output at a single frequency.

        Literature:
            - Kolbrek, "Horn Loudspeaker Simulation Part 3" - Power from T-matrix
            - Beranek (1954), Chapter 4 - Acoustic power radiation
            - Olson (1947), Chapter 8 - Horn efficiency
            - literature/horns/beranek_1954.md
            - literature/horns/olson_1947.md
            - literature/horns/kolbrek_horn_theory_tutorial.md

        Acoustic power at horn mouth:
            W_acoustic = Re(p_m × U_m*)

        where:
            p_m = pressure at mouth [Pa]
            U_m = volume velocity at mouth [m³/s]
            U_m* = complex conjugate of U_m

        The mouth quantities are obtained by transforming throat quantities
        through the horn T-matrix.

        Args:
            frequency: Frequency [Hz]
            voltage: Input voltage [V], default 2.83V
            medium: Acoustic medium properties (uses default if None)

        Returns:
            Acoustic power [Watts]

        Raises:
            ValueError: If frequency <= 0

        Examples:
            >>> flh.acoustic_power(500)
            0.05...  # Watts at 500 Hz

        Validation:
            Compare with Hornresp acoustic power export.
            Expected: <10% deviation in passband
        """
        if medium is None:
            medium = MediumProperties()

        # Get electrical impedance result (complex phasors)
        result = self.electrical_impedance(frequency, voltage, medium)

        # Calculate diaphragm volume velocity (complex)
        # From electrical impedance calculation:
        # I = voltage / Ze
        # F = Bl × I
        # u_d = F / Z_mechanical_total
        # U_d = u_d × S_d (diaphragm volume velocity)
        Ze = result['Ze_real'] + 1j * result['Ze_imag']
        if abs(Ze) == 0:
            return 0.0

        omega = 2 * np.pi * frequency
        I_complex = voltage / Ze
        F_complex = self.driver.BL * I_complex

        # Reconstruct mechanical impedance (same as in horn_electrical_impedance)
        Z_mechanical_driver = (self.driver.R_ms +
                              complex(0, omega * self.driver.M_md) +
                              complex(0, -1 / (omega * self.driver.C_ms)))

        # Get acoustic impedance at throat
        frequencies = np.array([frequency])
        Z_front, Z_rear = horn_system_acoustic_impedance(
            frequencies, self.horn, self.V_tc, self.A_tc,
            self.V_rc, self.driver.S_d, medium, self.radiation_angle
        )
        Z_acoustic_throat = Z_front[0] + Z_rear[0]

        # Transform acoustic impedance to mechanical domain using shared utility
        # Import the shared function to avoid code duplication
        from gsd.simulation.horn_driver_integration import scale_throat_acoustic_to_mechanical

        Z_mechanical_acoustic = scale_throat_acoustic_to_mechanical(
            Z_acoustic_throat, self.horn.throat_area, self.driver.S_d
        )

        # Total mechanical impedance
        Z_mechanical_total = Z_mechanical_driver + Z_mechanical_acoustic

        if abs(Z_mechanical_total) == 0:
            return 0.0

        # Diaphragm velocity (complex)
        u_diaphragm_complex = F_complex / Z_mechanical_total

        # Volume velocity at throat
        # For compression driver: U_throat = u_d × S_d (not S_throat!)
        # The driver's diaphragm area determines the volume velocity
        U_throat_complex = u_diaphragm_complex * self.driver.S_d

        # Pressure at throat
        # p_throat = Z_acoustic_throat × U_throat
        p_throat_complex = Z_acoustic_throat * U_throat_complex

        # Check horn type for appropriate power calculation
        horn_type = type(self.horn).__name__

        if horn_type == "MultiSegmentHorn":
            # For multi-segment horn: transform throat quantities to mouth
            # CRITICAL: Chain T-matrices in FORWARD order (throat -> mouth)
            # Then invert to transform from throat to mouth
            #
            # Literature: Kolbrek "Horn Theory" - T_total = T_1 × T_2 × ... × T_n
            # where matrices are applied from throat to mouth (FORWARD order)

            from gsd.simulation.types import HornSegment, ConicalHorn, HyperbolicHorn
            from gsd.simulation.horn_theory import exponential_horn_tmatrix

            # Start with identity matrix
            a, b, c_mat, d = 1.0, 0.0, 0.0, 1.0

            # Chain T-matrices in FORWARD order (throat to mouth)
            # This is CRITICAL - T-matrices relate throat to mouth
            for segment in self.horn.segments:
                if isinstance(segment, (ConicalHorn, HyperbolicHorn)):
                    # Use the segment's T-matrix method
                    T = segment.calculate_t_matrix(frequency, medium.c, medium.rho)
                    # Chain: T_total = T_total @ T_segment
                    # (apply new segment on the right)
                    a_new = a * T[0, 0] + b * T[1, 0]
                    b_new = a * T[0, 1] + b * T[1, 1]
                    c_new = c_mat * T[0, 0] + d * T[1, 0]
                    d_new = c_mat * T[0, 1] + d * T[1, 1]
                    a, b, c_mat, d = a_new, b_new, c_new, d_new
                else:
                    # HornSegment (exponential): use exponential T-matrix
                    from gsd.simulation.types import ExponentialHorn

                    segment_horn = ExponentialHorn(
                        throat_area=segment.throat_area,
                        mouth_area=segment.mouth_area,
                        length=segment.length
                    )
                    a_seg, b_seg, c_seg, d_seg = exponential_horn_tmatrix(
                        np.array([frequency]), segment_horn, medium
                    )

                    # Chain: T_total = T_total @ T_segment
                    # (apply new segment on the right)
                    a_new = a * a_seg[0] + b * c_seg[0]
                    b_new = a * b_seg[0] + b * d_seg[0]
                    c_new = c_mat * a_seg[0] + d * c_seg[0]
                    d_new = c_mat * b_seg[0] + d * d_seg[0]
                    a, b, c_mat, d = a_new, b_new, c_new, d_new

            # Determinant of T-matrix (should be 1 for lossless horn)
            det = a * d - b * c_mat

            if abs(det) < 1e-15:
                return 0.0

            # Inverse transform: [p_mouth, U_mouth] = (1/det) × [d, -b; -c, a] @ [p_throat, U_throat]
            p_mouth_complex = (d * p_throat_complex - b * U_throat_complex) / det
            U_mouth_complex = (-c_mat * p_throat_complex + a * U_throat_complex) / det

            # Acoustic power at mouth
            # W = Re(p_m × U_m*)
            # Kolbrek, "Horn Loudspeaker Simulation Part 3"
            # Beranek (1954), Chapter 4
            # Factor of 0.5 for RMS (peak values used in calculation)
            power = 0.5 * np.real(p_mouth_complex * np.conj(U_mouth_complex))
        else:
            # For single-segment exponential horn: transform to mouth
            # [p_throat, U_throat] = T_horn @ [p_mouth, U_mouth]
            # Therefore: [p_mouth, U_mouth] = inv(T_horn) @ [p_throat, U_throat]

            from gsd.simulation.horn_theory import exponential_horn_tmatrix

            # Get horn T-matrix
            a, b, c_mat, d = exponential_horn_tmatrix(
                np.array([frequency]), self.horn, medium
            )

            # T-matrix elements at this frequency
            a_f = a[0]
            b_f = b[0]
            c_f = c_mat[0]
            d_f = d[0]

            # Determinant of T-matrix (should be 1 for lossless horn)
            det = a_f * d_f - b_f * c_f

            if abs(det) < 1e-15:
                return 0.0

            # Inverse transform: [p_mouth, U_mouth] = (1/det) × [d, -b; -c, a] @ [p_throat, U_throat]
            p_mouth_complex = (d_f * p_throat_complex - b_f * U_throat_complex) / det
            U_mouth_complex = (-c_f * p_throat_complex + a_f * U_throat_complex) / det

            # Acoustic power at mouth
            # W = Re(p_m × U_m*)
            # Kolbrek, "Horn Loudspeaker Simulation Part 3"
            # Beranek (1954), Chapter 4
            # Factor of 0.5 for RMS (peak values used in calculation)
            power = 0.5 * np.real(p_mouth_complex * np.conj(U_mouth_complex))

        # Ensure non-negative (numerical errors can give tiny negative values)
        return max(0.0, power)

    def spl_response(
        self,
        frequency: float,
        voltage: float = 2.83,
        measurement_distance: float = 1.0,
        medium: Optional[MediumProperties] = None
    ) -> float:
        """
        Calculate sound pressure level at a single frequency.

        Literature:
            - Beranek (1954), Chapter 4 - Pressure from acoustic power
            - Kinsler et al. (1982), Chapter 4 - SPL from power
            - literature/horns/beranek_1954.md

        SPL from acoustic power (half-space radiation):
            SPL = 20·log₁₀(√(W·ρ₀·c/(2π·r²)) / p_ref)

        where p_ref = 20 μPa

        Args:
            frequency: Frequency [Hz]
            voltage: Input voltage [V], default 2.83V
            measurement_distance: SPL measurement distance [m], default 1m
            medium: Acoustic medium properties (uses default if None)

        Returns:
            SPL in dB at measurement_distance

        Raises:
            ValueError: If frequency <= 0 or measurement_distance <= 0

        Examples:
            >>> flh.spl_response(500)
            85.2...  # dB at 1m

        Validation:
            Compare with Hornresp SPL export.
            Expected: <3 dB deviation in passband (f > 2×f_c)
        """
        if medium is None:
            medium = MediumProperties()

        # Calculate acoustic power
        power = self.acoustic_power(frequency, voltage, medium)

        # Pressure from acoustic power (half-space radiation)
        # p_rms = √(W·ρ₀·c/(2π·r²))
        # Kinsler et al. (1982), Chapter 4
        pressure_rms = math.sqrt(
            power * medium.rho * medium.c / (2 * math.pi * measurement_distance ** 2)
        )

        # Sound pressure level
        # SPL = 20·log₁₀(p_rms / p_ref) where p_ref = 20 μPa
        # Kinsler et al. (1982), Chapter 2
        p_ref = 20e-6  # Reference pressure: 20 μPa
        spl = 20 * math.log10(pressure_rms / p_ref) if pressure_rms > 0 else -float('inf')

        return spl

    def spl_response_array(
        self,
        frequencies: FloatArray,
        voltage: float = 2.83,
        measurement_distance: float = 1.0,
        medium: Optional[MediumProperties] = None
    ) -> dict:
        """
        Calculate SPL response across frequency array.

        Vectorized version of spl_response() for batch processing.

        Args:
            frequencies: Array of frequencies [Hz]
            voltage: Input voltage [V], default 2.83V
            measurement_distance: SPL measurement distance [m], default 1m
            medium: Acoustic medium properties (uses default if None)

        Returns:
            Dictionary with arrays:
            - 'frequencies': Frequency array (Hz)
            - 'SPL': SPL array (dB at measurement_distance)

        Examples:
            >>> import numpy as np
            >>> freqs = np.logspace(1, 4, 100)
            >>> result = flh.spl_response_array(freqs)
            >>> result['SPL'].shape
            (100,)

        Validation:
            Compare with Hornresp SPL export.
            Expected: <3 dB deviation in passband (f > 2×f_c)
        """
        frequencies = np.atleast_1d(frequencies).astype(float)

        # Pre-allocate result array
        SPL = np.zeros_like(frequencies)

        # Calculate at each frequency
        for i, f in enumerate(frequencies):
            SPL[i] = self.spl_response(f, voltage, measurement_distance, medium)

        return {
            'frequencies': frequencies,
            'SPL': SPL,
        }

    def system_efficiency(
        self,
        frequency: float,
        voltage: float = 2.83,
        medium: Optional[MediumProperties] = None
    ) -> float:
        """
        Calculate system efficiency (acoustic power / electrical power).

        Literature:
            - Beranek (1954), Chapter 4 - Loudspeaker efficiency
            - Olson (1947), Chapter 8 - Horn efficiency
            - literature/horns/beranek_1954.md
            - literature/horns/olson_1947.md

        Efficiency:
            η = W_acoustic / W_electrical

        where:
            W_acoustic = acoustic power output
            W_electrical = V² × Re(Z_e) / |Z_e|² (real power delivered)

        Args:
            frequency: Frequency [Hz]
            voltage: Input voltage [V], default 2.83V
            medium: Acoustic medium properties (uses default if None)

        Returns:
            Efficiency as dimensionless ratio (0-1)
            Multiply by 100 for percentage

        Raises:
            ValueError: If frequency <= 0

        Examples:
            >>> flh.system_efficiency(500)
            0.15...  # 15% efficiency

        Validation:
            Compare with Hornresp efficiency export.
            Expected: <10% relative error in passband
        """
        # Calculate acoustic power
        W_acoustic = self.acoustic_power(frequency, voltage, medium)

        # Get electrical impedance
        result = self.electrical_impedance(frequency, voltage, medium)
        Ze = result['Ze_real'] + 1j * result['Ze_imag']

        # Electrical power: P_e = V² × Re(Z_e) / |Z_e|²
        # Real power delivered to the system
        if abs(Ze) == 0:
            W_electrical = 0
        else:
            W_electrical = (voltage ** 2) * Ze.real / (abs(Ze) ** 2)

        # Efficiency
        if W_electrical == 0:
            return 0.0

        efficiency = W_acoustic / W_electrical
        return efficiency

    def cutoff_frequency(self) -> float:
        """
        Calculate horn cutoff frequency.

        Uses Kolbrek's convention where the pressure amplitude flare constant is
        half the area expansion flare constant. This matches Hornresp's F12 parameter.

        Literature:
            - Olson (1947), Eq. 5.18 - Area expansion flare constant m = ln(S₂/S₁)/L
            - Kolbrek (2018), Horn Theory Tutorial - Pressure amplitude convention
              m_kolbrek = m_olson/2, f_c = c·m_kolbrek/(2π) = c·m_olson/(4π)
            - literature/horns/olson_1947.md
            - literature/horns/kolbrek_horn_theory_tutorial.md

        Returns:
            Cutoff frequency [Hz]

        Examples:
            >>> flh.cutoff_frequency()
            210.1...  # Hz

        Validation:
            Compare with Hornresp's F12 (cutoff) parameter for identical horn geometry.
            Expected agreement: <0.1% deviation.
        """
        # Kolbrek convention: f_c = c·m_kolbrek/(2π)
        # where m_kolbrek = m_olson/2 (pressure amplitude flare constant)
        # This matches Hornresp's F12 parameter
        #
        # Note: Olson (1947), Eq. 5.18 gives f_c = c·m_olson/(2π)
        # where m_olson is the area flare constant. The pressure amplitude
        # varies as p(x) ∝ exp(m_olson·x/2), so the effective propagation
        # constant uses m_kolbrek = m_olson/2.
        #
        # Literature:
        # - Kolbrek, "Horn Loudspeaker Simulation Part 1"
        # - Olson (1947), Eq. 5.18 (area flare constant)
        medium = MediumProperties()
        m_kolbrek = self.horn.flare_constant / 2.0  # Pressure amplitude flare
        fc = (medium.c * m_kolbrek) / (2 * math.pi)
        return fc

    def horn_system_parameters(self) -> dict:
        """
        Calculate key horn system parameters.

        Returns:
            Dictionary with:
            - 'cutoff_frequency': Horn cutoff frequency [Hz]
            - 'flare_constant': Horn flare constant [1/m]
            - 'expansion_ratio': Mouth area / throat area
            - 'horn_length': Horn length [m]
            - 'throat_radius': Throat radius [m]
            -mouth_radius: Mouth radius [m]
            - 'has_throat_chamber': Boolean
            - 'has_rear_chamber': Boolean
            - 'driver_resonance': Driver Fs [Hz]

        Examples:
            >>> params = flh.horn_system_parameters()
            >>> params['cutoff_frequency']
            210.1...  # Hz
        """
        return {
            'cutoff_frequency': self.cutoff_frequency(),
            'flare_constant': self.horn.flare_constant,
            'expansion_ratio': self.horn.mouth_area / self.horn.throat_area,
            'horn_length': self.horn.length,
            'throat_radius': self.horn.throat_radius(),
            'mouth_radius': self.horn.mouth_radius(),
            'has_throat_chamber': self.V_tc > 0,
            'has_rear_chamber': self.V_rc > 0,
            'driver_resonance': self.driver.F_s,
            'throat_chamber_volume': self.V_tc,
            'rear_chamber_volume': self.V_rc,
        }
