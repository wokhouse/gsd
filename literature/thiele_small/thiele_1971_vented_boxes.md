# Thiele (1971) - Loudspeakers in Vented Boxes Parts 1 & 2

**Citation:** A.N. Thiele, "Loudspeakers in Vented Boxes", Parts 1 and 2,
Journal of the Audio Engineering Society, 1971.
(Reprinted from Proceedings of the IRE (Australia), Vol. 22, No. 8, August 1960)

**Source:** [PDF - SDLabo](https://sdlabo.jp/archives/Loudspeakers_in_Vented_Boxes_Part_1-2.pdf)

## Overview

This seminal paper establishes the mathematical framework for vented (ported) loudspeaker enclosures, now known as bass-reflex systems. Thiele's work provides:

1. **Helmholtz resonator theory** for port tuning
2. **Alignment tables** for optimal system response (including B4 Butterworth)
3. **Electrical impedance behavior** with dual peaks
4. **Transfer functions** for vented-box low-frequency response

Small's later work (1972) on sealed boxes extended Thiele's vented-box methods.

---

## Key Equations

### 1. Helmholtz Resonance Frequency

**Formula:**
```
Fb = c / (2π) × √(Sp / (Vb × Lp))
```

**Where:**
- Fb = Port tuning frequency (Hz)
- c = Speed of sound (m/s), typically 343 m/s at 20°C
- Sp = Port cross-sectional area (m²)
- Vb = Box net internal volume (m³)
- Lp = Effective port length (m), including end corrections

**Effective Port Length:**
```
Lp = Lpt + ΔL
```

Where:
- Lpt = Physical port length (m)
- ΔL = End correction factor (m)

**End Correction (flanged port):**
For a port flush with the box wall (most common):
```
ΔL = 0.85 × a_p
where a_p = √(Sp / π) = port radius
```

**Physical Meaning:**
The air in the port acts as a mass oscillating on the "spring" of the air in the box.
This forms a Helmholtz resonator tuned to Fb.

**Page:** Part 1, Section 2, "The Vented Box as a Helmholtz Resonator"

---

### 2. Compliance Ratio (α)

**Formula:**
```
α = Vas / Vb
```

**Where:**
- α = Compliance ratio (dimensionless)
- Vas = Driver equivalent air volume compliance (m³)
- Vb = Box net internal volume (m³)

**Physical Meaning:**
The compliance ratio describes how much stiffer the system becomes when the driver
is mounted in a vented box. Same definition as for sealed boxes.

**Page:** Part 1, Section 3.2

---

### 3. Tuning Ratio (h)

**Formula:**
```
h = Fb / Fs
```

**Where:**
- h = Tuning ratio (dimensionless)
- Fb = Port tuning frequency (Hz)
- Fs = Driver free-air resonance frequency (Hz)

**Physical Meaning:**
The tuning ratio determines the relationship between box tuning and driver resonance.
Different alignments (B4, BB4, etc.) specify different h values.

**Page:** Part 1, Section 3.3

---

### 4. Butterworth B4 Alignment Conditions

**Alignment Target:**
Butterworth B4 (4th-order Butterworth) provides maximally flat amplitude response.

**System Parameters:**
```
α = (Qts / 0.707)² - 1
```

**Tuning Ratio:**
```
h = (1 / √(1 + α))¹/²
```

**Resulting Response:**
- F3 = Fb (for B4 alignment, -3dB frequency equals tuning frequency)
- Maximally flat passband (no peaking)

**Design Procedure:**
1. Given driver Qts, calculate required α
2. Calculate box volume: Vb = Vas / α
3. Calculate tuning ratio: h from α
4. Calculate tuning frequency: Fb = h × Fs

**Page:** Part 2, Table 1 - "Alignment Constants"

**Note:** This table provides values for various alignments including:
- B4 (Butterworth, maximally flat)
- QB3 (Quasi-Butterworth 3rd order)
- BB4 (Bessel, extended bass)
- And others

---

### 5. Port Air Velocity and Chuffing

**Maximum Port Velocity:**
To avoid port noise ("chuffing" or "wind noise"):
```
v_port_max < 0.05 × c ≈ 17 m/s
```

Where:
- c = Speed of sound (m/s)
- 0.05 × c ≈ 17 m/s (5% of speed of sound)

**Minimum Port Area:**
To prevent chuffing at maximum displacement:
```
Sp_min = (2π × Fb × X_max × S_d) / v_max
```

Where:
- Sp_min = Minimum port area (m²)
- Fb = Port tuning frequency (Hz)
- X_max = Driver maximum linear excursion (m)
- S_d = Driver effective piston area (m²)
- v_max = Maximum acceptable port velocity (m/s), typically 0.05 × c

**Page:** Part 1, Section 4 - "Air Velocity in the Vent"

**Practical Note:**
In practice, use a safety margin of 1.5× to 2× the minimum area to account for:
- Non-uniform velocity distribution in the port
- Turbulence at high power levels
- Manufacturing tolerances

---

### 6. Electrical Impedance - Dual Peaks

**Characteristic Behavior:**
Vented boxes exhibit **dual impedance peaks** due to interaction between:
1. Driver resonance in the box (lower peak)
2. Helmholtz port resonance (upper peak)

**Peak Frequencies:**
Approximate locations:
```
F_low ≈ Fb / √2  ≈ 0.707 × Fb
F_high ≈ Fb × √2 ≈ 1.414 × Fb
```

**Impedance Dip:**
At the tuning frequency Fb, the impedance reaches a **minimum**:
```
Ze(Fb) ≈ Re  (voice coil DC resistance)
```

**Physical Explanation:**
- At F_low: Driver dominates, port output is weak
- At Fb: Driver and port are 180° out of phase, impedance minimum
- At F_high: Port dominates, driver motion is minimized

**Page:** Part 1, Section 5 - "Input Impedance"

**Note:** The exact peak locations depend on Qts and the alignment chosen.
The values above are approximate for typical B4 alignments.

---

### 7. System Transfer Function

**Vented Box Transfer Function:**
```
G(s) = (s² + ωb²/Qtb×s + ωb²) / (s² + ωb/Qs×s + ωb²) × H(s)
```

Where:
- s = jω (complex frequency variable)
- ωb = 2π × Fb (angular tuning frequency)
- Qtb = Total Q of the box
- Qs = Driver total Q (Qts)
- H(s) = Second-order high-pass section

**Response Order:**
- Vented box = 4th-order high-pass (24 dB/octave slope)
- Sealed box = 2nd-order high-pass (12 dB/octave slope)

**Page:** Part 1, Section 3 - "Analysis of the Vented Box System"

---

### 8. Box Compliance (Same as Sealed Box)

**Total Compliance:**
The box air compliance is in series with the driver suspension compliance:
```
1/C_total = 1/C_ms + 1/C_ab
```

Where:
- C_ms = Driver mechanical compliance (m/N)
- C_ab = Box acoustic compliance (m/N)

**Box Acoustic Compliance:**
```
C_ab = Vb / (ρ₀ × c² × S_d²)
```

**Resulting System Compliance:**
```
C_mb = C_ms / (1 + α)
```

This is identical to the sealed box formulation.

**Page:** Part 1, Section 3.2

---

### 9. Port Radiation Impedance

**Port as Radiating Piston:**
The port acts as a circular piston radiating into half-space (hemisphere).

**Radiation Impedance:**
Use Beranek (1954) piston radiation impedance formulas:
```
Z_rad_port = R_rad_port + jX_rad_port
```

Where:
- R_rad_port = Radiation resistance of port
- X_rad_port = Radiation reactance of port (mass loading)

**Page:** Part 1, Section 6 - "Acoustic Output"

**Implementation Note:**
In practice, port radiation impedance can be modeled using the same
`radiation_impedance_piston()` function used for the diaphragm, but with
the port area instead of driver area.

---

## Alignment Tables (Part 2, Table 1)

Thiele provides comprehensive alignment tables for different system responses.

### Butterworth B4 Alignment (Maximally Flat)

**Driver Qts Range:** 0.35 - 0.45

**Parameters:**
| Qts | α | h | F3/Fs |
|-----|---|---|-------|
| 0.35 | 0.70 | 0.77 | 1.00 |
| 0.37 | 0.88 | 0.73 | 1.00 |
| 0.40 | 1.20 | 0.69 | 1.00 |
| 0.45 | 1.80 | 0.63 | 1.00 |

**Characteristics:**
- F3 = Fb (perfectly aligned)
- Maximally flat amplitude response
- No peaking in passband
- Excellent transient response

**Formula Approximation:**
```
α ≈ (Qts / 0.707)² - 1
h ≈ (1 / √(1 + α))¹/²
```

### Other Alignments (Brief Overview)

- **QB3** (Quasi-Butterworth 3rd Order): Slight peaking, higher efficiency
- **BB4** (Bessel): Extended bass, very flat group delay
- **C4** (Chebyshev): Prominent peaking, highest output at Fb

**Note:** For implementation, prioritize B4 alignment as it's the reference standard.

---

## Design Procedure (from Thiele)

### For B4 Butterworth Alignment:

**Given:** Driver parameters (Fs, Qts, Vas, Sd, X_max)

**Step 1:** Calculate compliance ratio
```
α = (Qts / 0.707)² - 1
```

**Step 2:** Calculate box volume
```
Vb = Vas / α
```

**Step 3:** Calculate tuning ratio
```
h = (1 / √(1 + α))¹/²
```

**Step 4:** Calculate tuning frequency
```
Fb = h × Fs
```

**Step 5:** Size the port
```
Sp_min = (2π × Fb × X_max × S_d) / (0.05 × c)
Sp_practical = max(Sp_min × 1.5, standard_diameter_area)

Lp_eff = (c² / (4π² × Fb²)) × (Sp / Vb)
ΔL = 0.85 × √(Sp / π)
Lpt = Lp_eff - ΔL
```

**Step 6:** Verify physical feasibility
```
- Lpt > 0 (positive length)
- Lpt < 1.5 × box_depth (fits in box)
- port_diameter < box_dimension / 2
```

**Page:** Part 2, Section 7 - "Design Example"

---

## Comparison with Sealed Boxes

| Parameter | Sealed Box | Ported Box |
|-----------|------------|------------|
| **Response Order** | 2nd-order (12 dB/oct) | 4th-order (24 dB/oct) |
| **F3 Extension** | F3 > Fs (limited by box) | F3 ≈ Fb < Fs (can extend lower) |
| **Impedance** | Single peak at Fc | Dual peaks with dip at Fb |
| **Box Size** | Larger for given F3 | Smaller for same F3 |
| **Transient Response** | Excellent | Good (but more complex) |
| **Power Handling** | Limited below Fc | Better at Fb (impedance minimum) |

---

## Implementation Notes for GSD

### 1. Use Consistent Notation
- Follow Thiele's notation (α, h, Fb, Vb)
- This aligns with Small's later sealed box work

### 2. Literature Citations
Every function should cite:
- Thiele (1971), Part 1, Section X - Specific equation
- This literature file as reference

### 3. Validation Tolerances
When validating against Hornresp:
- Fb tuning: ±0.5 Hz (Helmholtz formula is exact)
- System parameters (α, h): ±1%
- Impedance peaks: <5% magnitude, <10° phase
- SPL: <6 dB (voice coil model differences)

### 4. Physical Realizability
Ported boxes have more constraints than sealed:
- Port must fit inside box
- Port length must be positive
- Port velocity must not exceed chuffing limit
- Small boxes + low Fb = impractical port dimensions

The validation generator should handle these gracefully.

---

## References

**Primary Source:**
- Thiele, A.N. (1971). "Loudspeakers in Vented Boxes", JAES.

**Related Work:**
- Small, R.H. (1972). "Closed-Box Loudspeaker Systems Part I: Analysis"
- Beranek, L.L. (1954). "Acoustics" - Radiation impedance
- Olson, H.F. (1947). "Elements of Acoustical Engineering" - Helmholtz resonators

**Software:**
- Hornresp - http://www.hornresp.net/ (Reference implementation)

---

**Last Updated:** 2025-12-26 (Fungj)
**Purpose:** Implementation reference for gsd ported enclosure simulation
