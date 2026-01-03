#!/usr/bin/env python3
"""
Analyze bass offset between viberesp and Hornresp.

Check if the issue is in the sealed box transfer function at low frequencies.
"""

import sys
sys.path.insert(0, 'src')

import numpy as np
from gsd.driver.parameters import ThieleSmallParameters
from gsd.enclosure.sealed_box import calculate_spl_from_transfer_function

# Driver parameters
driver = ThieleSmallParameters(
    M_md=0.0267,
    C_ms=0.0008,
    R_ms=1.53,
    R_e=6.3,
    L_e=0.00035,
    BL=5.8,
    S_d=0.0217,
)

Vb = 0.010  # 10L
f_mass = 450

# Calculate system parameters
Fc = driver.F_s * np.sqrt(1 + driver.V_as / Vb)

print("=" * 80)
print("BASS OFFSET ANALYSIS")
print("=" * 80)
print()
print(f"System resonance Fc: {Fc:.2f} Hz")
print(f"Driver resonance Fs: {driver.F_s:.2f} Hz")
print()

# Load Hornresp data
hornresp_file = "imports/hf_roll_sim.txt"
freqs_hr = []
spl_hr = []

with open(hornresp_file, 'r') as f:
    lines = f.readlines()
    for line in lines[2:]:
        if line.strip() and not line.startswith('Freq'):
            parts = line.split()
            if len(parts) >= 5:
                try:
                    freq = float(parts[0])
                    spl = float(parts[4])
                    freqs_hr.append(freq)
                    spl_hr.append(spl)
                except ValueError:
                    continue

freqs_hr = np.array(freqs_hr)
spl_hr = np.array(spl_hr)

# Calculate viberesp predictions
spl_vib = np.array([
    calculate_spl_from_transfer_function(
        f, driver, Vb, f_mass=f_mass, Quc=float('inf')
    )
    for f in freqs_hr
])

# Analyze different frequency ranges
bass_mask = freqs_hr < 200
mid_mask = (freqs_hr >= 200) & (freqs_hr < 2000)
hf_mask = freqs_hr >= 2000

diff_bass = spl_vib[bass_mask] - spl_hr[bass_mask]
diff_mid = spl_vib[mid_mask] - spl_hr[mid_mask]
diff_hf = spl_vib[hf_mask] - spl_hr[hf_mask]

print("OFFSET BY FREQUENCY RANGE:")
print()
print(f"Bass (<200 Hz):     Mean = {np.mean(diff_bass):.2f} dB, Std = {np.std(diff_bass):.2f} dB")
print(f"Mid (200-2000 Hz):  Mean = {np.mean(diff_mid):.2f} dB, Std = {np.std(diff_mid):.2f} dB")
print(f"HF (≥2000 Hz):      Mean = {np.mean(diff_hf):.2f} dB, Std = {np.std(diff_hf):.2f} dB")
print()

# Check specific frequencies
test_freqs = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]

print("OFFSET AT KEY FREQUENCIES:")
print(f"{'Freq (Hz)':>12} | {'Hornresp':>10} | {'Viberesp':>10} | {'Diff':>10} | {'Note'}")
print("-" * 70)

for f in test_freqs:
    idx = np.argmin(np.abs(freqs_hr - f))
    f_actual = freqs_hr[idx]
    spl_hr_f = spl_hr[idx]
    spl_vib_f = spl_vib[idx]
    diff = spl_vib_f - spl_hr_f

    note = ""
    if abs(f_actual - Fc) < 5:
        note = "≈Fc"
    elif f_actual < 100:
        note = "Deep bass"

    print(f"{f_actual:>10.1f} | {spl_hr_f:>10.2f} | {spl_vib_f:>10.2f} | {diff:>10.2f} | {note}")

print()

# Check if offset is frequency-dependent within bass region
print("FREQUENCY DEPENDENCE OF BASS OFFSET:")
print()

bass_freqs = freqs_hr[bass_mask]
bass_diffs = diff_bass

# Calculate correlation between frequency and offset in bass
if len(bass_freqs) > 10:
    # Bin the bass region
    bins = [0, 50, 100, 150, 200]
    for i in range(len(bins) - 1):
        bin_mask = (bass_freqs >= bins[i]) & (bass_freqs < bins[i+1])
        if np.sum(bin_mask) > 0:
            bin_mean = np.mean(bass_diffs[bin_mask])
            bin_std = np.std(bass_diffs[bin_mask])
            print(f"  {bins[i]:3d}-{bins[i+1]:3d} Hz:  Mean offset = {bin_mean:+.2f} dB ± {bin_std:.2f} dB")

print()
print("=" * 80)
print("ANALYSIS:")
print("=" * 80)
print()
print("If the bass offset is consistent across frequencies:")
print("  → Suggests calibration issue (constant offset)")
print()
print("If the bass offset varies with frequency:")
print("  → Suggests transfer function shape mismatch")
print()
