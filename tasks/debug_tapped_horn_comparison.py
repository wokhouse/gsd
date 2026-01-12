"""Debug script to compare gsd vs Hornresp in detail."""
import sys
sys.path.insert(0, 'src')

import numpy as np
from gsd.simulation.types import TappedHorn
from gsd.simulation.horn_theory import MediumProperties
from gsd.simulation.tapped_horn_theory import tapped_horn_system_response
from gsd.driver.parameters import ThieleSmallParameters

# Hornresp standard conditions
MEDIUM = MediumProperties(rho=1.18, c=343.0)

# Driver from Hornresp parameters
HORNRESP_DRIVER = ThieleSmallParameters(
    S_d=855e-4,       # 855 cm²
    BL=21.2,          # T·m
    M_md=0.147,       # 147 g = 0.147 kg
    R_ms=6.80,        # N·s/m
    R_e=5.20,         # Ω
    L_e=1.40e-3,      # 1.40 mH
    C_ms=1.04e-4,     # m/N
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
hr_xd = data[:, 6]

# Test frequencies (subset for debugging)
test_freqs = np.array([40, 50, 60, 80, 100, 150, 200])

print("=== Tapped Horn Debug Comparison ===\n")

# Run gsd simulation
result = tapped_horn_system_response(
    test_freqs,
    HORNRESP_HORN,
    HORNRESP_DRIVER,
    MEDIUM,
    voltage=2.83,
)

# Get Hornresp values at test frequencies
hr_spl_test = np.interp(test_freqs, hr_freq, hr_spl)
hr_ze_test = np.interp(test_freqs, hr_freq, hr_ze)
hr_xd_test = np.interp(test_freqs, hr_freq, hr_xd)

print("Frequency (Hz) | gsd SPL  | HR SPL   | Diff  | gsd Ze   | HR Ze    | gsd Xd   | HR Xd")
print("-" * 110)
for i, f in enumerate(test_freqs):
    spl_diff = result['spl'][i] - hr_spl_test[i]
    ze_diff = result['electrical_impedance'][i] - hr_ze_test[i]
    xd_diff = result['excursion'][i] - hr_xd_test[i]
    print(f"{f:10.0f}     | {result['spl'][i]:6.2f}  | {hr_spl_test[i]:6.2f}   | {spl_diff:+5.2f} | "
          f"{result['electrical_impedance'][i]:6.2f}   | {hr_ze_test[i]:6.2f}   | "
          f"{result['excursion'][i]:6.3f}  | {hr_xd_test[i]:6.3f}")

# Check path contributions
print("\n=== Path Contributions ===")
print("Frequency (Hz) | |P_front| | Phase  | |P_rear|  | Phase  | |P_total| | Phase")
print("-" * 85)
for i, f in enumerate(test_freqs):
    p_front = result['p_mouth_front'][i]
    p_rear = result['p_mouth_rear'][i]
    p_total = result['p_mouth'][i]
    print(f"{f:10.0f}     | {np.abs(p_front):6.2e} | {np.angle(p_front, deg=True):+6.1f}° | "
          f"{np.abs(p_rear):6.2e} | {np.angle(p_rear, deg=True):+6.1f}° | "
          f"{np.abs(p_total):6.2e} | {np.angle(p_total, deg=True):+6.1f}°")

# Check impedance split
print("\n=== Impedance Split ===")
print("Frequency (Hz) | |Z_up|   | |Z_down| | Z_tap    | T_up     | T_down")
print("-" * 80)
from gsd.simulation.tapped_horn_theory import (
    upstream_section_impedance,
    downstream_section_impedance,
)

for i, f in enumerate(test_freqs):
    z_up = upstream_section_impedance(np.array([f]), HORNRESP_HORN, MEDIUM)[0]
    z_down = downstream_section_impedance(np.array([f]), HORNRESP_HORN, MEDIUM)[0]
    z_tap = (z_up * z_down) / (z_up + z_down)
    t_up = z_down / (z_up + z_down)
    t_down = z_up / (z_up + z_down)
    print(f"{f:10.0f}     | {np.abs(z_up):6.2e} | {np.abs(z_down):6.2e} | "
          f"{np.abs(z_tap):6.2e} | {np.abs(t_up):6.3f}   | {np.abs(t_down):6.3f}")
