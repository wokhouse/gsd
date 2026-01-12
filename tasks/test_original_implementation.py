"""Test original implementation to see if it was closer to correct."""
import sys
sys.path.insert(0, 'src')

import numpy as np
from gsd.simulation.types import TappedHorn
from gsd.simulation.horn_theory import MediumProperties
from gsd.simulation.tapped_horn_theory import (
    tapped_horn_tap_impedance,
    _chain_tmatrices,
    circular_piston_radiation_impedance,
)
from gsd.simulation.horn_theory import exponential_horn_tmatrix
from gsd.driver.parameters import ThieleSmallParameters

# Hornresp standard conditions
MEDIUM = MediumProperties(rho=1.18, c=343.0)

# Driver from Hornresp parameters
HORNRESP_DRIVER = ThieleSmallParameters(
    S_d=855e-4,
    BL=21.2,
    M_md=0.147,
    R_ms=6.80,
    R_e=5.20,
    L_e=1.40e-3,
    C_ms=1.04e-4,
)

# Horn geometry
HORNRESP_HORN = TappedHorn(
    upstream_throat_area=150.0,
    tap_area=855.0,
    downstream_mouth_area=6000.0,
    upstream_length=180.0,
    downstream_length=200.0,
    upstream_profile='exponential',
    downstream_profile='exponential',
    intermediate_area=2265.0,
)

# Load Hornresp data
data = np.loadtxt("imports/th_sim.txt", skiprows=1, delimiter='\t')
hr_freq = data[:, 0]
hr_spl = data[:, 4]
hr_ze = data[:, 5]

# Test frequencies
test_freqs = np.array([40, 50, 60, 80, 100, 150, 200])

print("=== Testing Original Simple Implementation ===\n")

# Calculate tap impedance (original method)
z_tap = tapped_horn_tap_impedance(test_freqs, HORNRESP_HORN, MEDIUM)

# Convert to mechanical impedance
z_mechanical_acoustic = z_tap * (HORNRESP_DRIVER.S_d ** 2)

# Driver mechanical impedance
omega = 2 * np.pi * test_freqs
z_mech_stiffness = 1.0 / (1j * omega * HORNRESP_DRIVER.C_ms)
z_mech_mass = 1j * omega * HORNRESP_DRIVER.M_md
z_mech_resistance = HORNRESP_DRIVER.R_ms
z_mechanical_driver = z_mech_resistance + z_mech_mass + z_mech_stiffness

# Total mechanical impedance
z_mechanical_total = z_mechanical_driver + z_mechanical_acoustic

# Electrical impedance
z_motional = (HORNRESP_DRIVER.BL ** 2) / z_mechanical_total
z_voice_coil = HORNRESP_DRIVER.R_e + 1j * omega * HORNRESP_DRIVER.L_e
z_electrical = z_voice_coil + z_motional

# Diaphragm velocity (2.83V input)
voltage = 2.83
current = voltage / z_electrical
force = HORNRESP_DRIVER.BL * current
v_diaphragm = force / z_mechanical_total

# Volume velocity at tap
u_tap = v_diaphragm * HORNRESP_DRIVER.S_d

# ORIGINAL SIMPLE METHOD: Inverse T-matrix
downstream_segments = HORNRESP_HORN.downstream_segments()
a, b, c, d = _chain_tmatrices(test_freqs, downstream_segments, MEDIUM)
z_rad = circular_piston_radiation_impedance(test_freqs, downstream_segments[-1].mouth_area, MEDIUM)

# Mouth volume velocity
u_mouth = u_tap / (c * z_rad + d)

# Mouth pressure
p_mouth = u_mouth * z_rad

# Calculate SPL
radiated_power = 0.5 * (np.abs(u_mouth) ** 2) * np.real(z_rad)
distance = 1.0
intensity = radiated_power / (4 * np.pi * distance ** 2)
p_ref = 20e-6
spl = 20 * np.log10(np.sqrt(intensity * MEDIUM.rho * MEDIUM.c) / p_ref + 1e-20)

# Get Hornresp values
hr_spl_test = np.interp(test_freqs, hr_freq, hr_spl)
hr_ze_test = np.interp(test_freqs, hr_freq, hr_ze)

print("Frequency (Hz) | gsd SPL  | HR SPL   | Diff  | gsd Ze   | HR Ze")
print("-" * 90)
for i, f in enumerate(test_freqs):
    spl_diff = spl[i] - hr_spl_test[i]
    ze_diff = np.abs(z_electrical[i]) - hr_ze_test[i]
    print(f"{f:10.0f}     | {spl[i]:6.2f}  | {hr_spl_test[i]:6.2f}   | {spl_diff:+5.2f} | "
          f"{np.abs(z_electrical[i]):6.2f}   | {hr_ze_test[i]:6.2f}")

print(f"\nCorrelation check:")
print(f"SPL RMS error: {np.sqrt(np.mean((spl - hr_spl_test)**2)):.2f} dB")
print(f"Ze RMS error: {np.sqrt(np.mean((np.abs(z_electrical) - hr_ze_test)**2)):.2f} Ω")
