# Small (1972) - Closed-Box Loudspeaker Systems Part I: Analysis

**Citation:** R.H. Small, "Closed-Box Loudspeaker Systems Part I: Analysis",
Journal of the Audio Engineering Society, Vol. 20, No. 10, pp. 798-809, December 1972.

**Source:** [PDF - SDLabo](https://sdlabo.jp/archives/Closed_Box_Loudspeaker_Systems_Part_1-2.pdf)

**Alternative Source:** [DIY Audio Projects](http://diyaudioprojects.com/Technical/Papers/Closed-Box-Loudspeaker-Systems-Part-II-Synthesis.pdf)

## Overview

This paper presents a comprehensive analysis of direct-radiator loudspeaker systems in sealed (closed-box) enclosures. Small extends Thiele's earlier work on vented boxes to sealed systems, establishing the mathematical framework used universally today for sealed-box design.

The paper derives:
1. System resonance frequency (Fc) as a function of box volume
2. System Q factor (Qtc) relationships
3. Low-frequency transfer functions
4. Electrical impedance behavior
5. Displacement limitations

---

## Key Equations

### 1. Compliance Ratio (α)

**Definition:**
```
α = Vas / Vb
```

**Where:**
- α = Compliance ratio (dimensionless)
- Vas = Driver equivalent air volume compliance (m³)
- Vb = Box net internal volume (m³)

**Physical Meaning:**
The compliance ratio describes how much stiffer the system becomes when the driver is mounted in a closed box. The air in the box acts as an additional spring in series with the driver's suspension.

- α = 0: Infinite baffle (no box stiffness)
- α = 1: Box stiffness equals driver stiffness
- α >> 1: Very small box (system dominated by box stiffness)

**Page:** Not explicitly numbered in paper, fundamental definition used throughout.

---

### 2. System Resonance Frequency (Fc)

**Formula:**
```
Fc = Fs × √(1 + α)
```

**Where:**
- Fc = Closed-box system resonance frequency (Hz)
- Fs = Driver free-air resonance frequency (Hz)
- α = Compliance ratio (Vas/Vb)

**Derivation:**
The total compliance of the system is the series combination of driver compliance and box compliance:

```
1/C_total = 1/C_ms + 1/C_ab
```

where:
- C_ms = Driver mechanical compliance (m/N)
- C_ab = Box acoustic compliance = Vb / (ρ₀·c²·S_d²)

This leads to:
```
C_mb = C_ms / (1 + α)
```

Since resonance frequency is:
```
Fc = 1 / (2π√(M_ms·C_mb))
```

Substituting C_mb:
```
Fc = 1 / (2π√(M_ms·C_ms / (1 + α)))
   = Fs × √(1 + α)
```

**Page:** Equation derived in text around Eq. 1-2 (p. 2 in PDF)

---

### 3. System Q Factor (Qtc)

**Formula:**
```
Qtc = Qts × √(1 + α)
```

**Where:**
- Qtc = Closed-box system total Q factor
- Qts = Driver total Q factor (free-air)
- α = Compliance ratio (Vas/Vb)

**Derivation:**
The Q factor is proportional to √(stiffness). Since the system stiffness increases by (1 + α):
```
Qtc ∝ √(1 + α)
Qtc = Qts × √(1 + α)
```

**Physical Meaning:**
- Qtc < 0.5: Over-damped (large box, reduced efficiency, extended bandwidth)
- Qtc = 0.5: Critically damped (maximally flat transient response)
- Qtc = 0.577: Bessel alignment (best transient response)
- Qtc = 0.707: Butterworth B2 alignment (maximally flat magnitude)
- Qtc = 1.0: Maximally flat efficiency
- Qtc > 1.0: Under-damped (small box, peaky response, poor transients)

**Page:** Derived in text following Fc derivation

---

### 4. Normalized Pressure Response (Transfer Function)

**Formula:**
```
G(s) = (s²/Fc²) / [s²/Fc² + (s/Qtc·Fc) + 1]
```

**Where:**
- G(s) = Normalized pressure response (complex)
- s = jω (complex frequency variable)
- Fc = System resonance frequency (Hz)
- Qtc = System Q factor

**Physical Meaning:**
This is a 2nd-order high-pass filter. The response rises at 12 dB/octave below Fc and is flat above Fc.

**Alternative form (from Small Eq. 1, p. 2):**
```
G(s) = (s²/Fs²) / [s²/Fs² + (s/Qts·Fs) + 1]
```

For closed box, substitute Fc and Qtc for Fs and Qts.

**Page:** Equation 1, Page 2

---

### 5. Electrical Impedance

**Formula:**
```
Ze(s) = Re + Rg + (BL)²·s / [s²Mms + sRms + Cms⁻¹ + Cas⁻¹]
```

**Where:**
- Ze = Electrical impedance (Ω)
- Re = Voice coil DC resistance (Ω)
- Rg = Generator resistance (Ω)
- BL = Force factor (T·m)
- Mms = Total moving mass (kg)
- Rms = Mechanical resistance (N·s/m)
- Cms = Driver compliance (m/N)
- Cas = Enclosure acoustic compliance

**At resonance (Fc):**
The impedance magnitude peaks at:
```
Ze(Fc) ≈ Re · (1 + Qes²)
```

where Qes is the electrical Q factor.

**Physical Meaning:**
The electrical impedance peaks at the system resonance frequency Fc, NOT at the driver's free-air resonance Fs. This is a key diagnostic for sealed-box systems.

**Page:** Derived around Figure 2, Page 3

---

### 6. F3 (-3dB Cutoff Frequency)

**For Butterworth alignment (Qtc = 0.707):**
```
F3 = Fc
```

**General case:**
Solve the equation:
```
|G(jω)|² / |G(jω)|²max = 0.5
```

**Approximate formula (for any Qtc):**
```
F3 = Fc × √((1/Qtc² - 2 + √((1/Qtc² - 2)² + 4)) / 2)
```

**Values from Figure 3 (p. 4):**
- Qtc = 0.5: F3 ≈ 1.55 × Fc
- Qtc = 0.707: F3 = 1.0 × Fc (Butterworth)
- Qtc = 1.0: F3 ≈ 0.79 × Fc

**Page:** Figure 3, Page 4

---

### 7. Reference Efficiency

**Formula:**
```
η₀ = (ρ₀/2πc) · (4π²Fs³Vas/Qes)
```

**Where:**
- η₀ = Reference efficiency (dimensionless)
- ρ₀ = Density of air (kg/m³)
- c = Speed of sound (m/s)
- Fs = Driver resonance (Hz)
- Vas = Equivalent volume (m³)
- Qes = Electrical Q factor

**For closed box:**
```
η = η₀ / (α + 1)
```

**Physical Meaning:**
Larger boxes (smaller α) are more efficient. Maximum efficiency occurs as α → 0 (infinite baffle).

**Page:** Derived in text, p. 5-6

---

### 8. System Displacement

**Formula:**
```
Xmax(s) = Eg / [(s²/Fs² + s/Qts·Fs + 1) · (BL·Re)]
```

**Physical Meaning:**
Cone displacement is maximum below resonance and decreases with frequency. Larger boxes reduce displacement at a given frequency, which is why large sealed boxes can handle more power.

**Page:** Figure 5, Page 6

---

## Key Figures and Diagrams

- **Figure 1 (p. 2):** Analog circuit model showing mechanical and electrical parameters
- **Figure 2 (p. 3):** Normalized electrical impedance curves for different Qtc values
- **Figure 3 (p. 4):** Normalized pressure response for different Qtc values (key figure)
- **Figure 4 (p. 5):** Transient response (impulse) for different Qtc values
- **Figure 5 (p. 6):** Normalized cone displacement for different Qtc values
- **Figure 6 (p. 8):** System response vs. box volume for a given driver

---

## Implementation Notes for GSD

### 1. Radiation Mass Multiplier

**Critical:** Sealed boxes radiate from the **front side only**.

- Infinite baffle: radiation_multiplier = 2.0 (both sides radiate)
- Sealed box: radiation_multiplier = 1.0 (front only)

This is because:
- Infinite baffle: Driver in large baffle, both front and rear radiate into half-space
- Sealed box: Rear is enclosed, only front radiates

**Implementation:**
Use `calculate_resonance_with_radiation_mass_tuned(M_md, C_mb, S_d, radiation_multiplier=1.0)`

---

### 2. Box Compliance Calculation

The box adds stiffness in series with the driver suspension:

```
C_mb = C_ms / (1 + α)
```

where α = Vas/Vb.

**Do NOT use** `C_ms` directly for sealed box calculations. Use `C_mb` instead.

---

### 3. System Resonance Frequency

For sealed box, the system resonance is **Fc, not Fs**.

- Fs: Driver free-air resonance (used for infinite baffle)
- Fc: Sealed-box system resonance = Fs × √(1 + α)

All calculations should reference Fc, not Fs, when the driver is in a sealed box.

---

### 4. Iterative Solver for Resonance

Since radiation mass depends on frequency, and frequency depends on radiation mass (through M_ms), an iterative solver is required:

```
Initialize: M_ms = M_md
Iterate:
    Fc = 1 / (2π√(M_ms·C_mb))
    M_rad = calculate_radiation_mass(Fc, S_d)
    M_ms = M_md + 1.0 × M_rad  # 1× for sealed box
Until: |Fc_new - Fc_old| < tolerance
```

**Note:** Use C_mb (box compliance), not C_ms (driver compliance).

---

### 5. Impedance Peak Location

**Key diagnostic:** The electrical impedance peaks at **Fc**, not Fs.

This is used to verify that the model is working correctly:
1. Calculate Fc from system parameters
2. Find frequency of maximum Ze
3. Verify they match (within tolerance)

If the impedance peak occurs at Fs instead of Fc, the model is not accounting for the box stiffness correctly.

---

### 6. Transfer Function Shape

Sealed box is a **2nd-order high-pass** filter:
- 12 dB/octave slope below Fc
- Flat response above Fc
- No double peaks (unlike vented box)
- Single impedance peak at Fc

---

## Validation Data

### Hornresp Configuration

**Sealed box:**
- Rear chamber: Vrc = Vb, Lrc = 0
- Front: S1 = L45 = 0 (infinite baffle)
- Option: "Rear Lined"

### Expected Results for BC_8NDL51 + 10L Box

**Driver parameters:**
- Fs = 64 Hz (with 2×M_rad)
- Qts = 0.37
- Vas = 14 L

**System parameters:**
- α = 14/10 = 1.4
- Fc = 64 × √(1 + 1.4) = 64 × 1.553 = 99.4 Hz
- Qtc = 0.37 × √(1 + 1.4) = 0.37 × 1.553 = 0.575

**Expected validation results:**
- Impedance peak at Fc ≈ 99 Hz
- Single impedance peak (not double)
- F3 ≈ 99 Hz (for Qtc ≈ 0.58)
- SPL slope: 12 dB/octave below Fc

---

## References

1. Small, R.H. (1972). "Closed-Box Loudspeaker Systems Part I: Analysis". *Journal of the Audio Engineering Society*, 20(10), 798-809.

2. Thiele, A.N. (1971). "Loudspeakers in Vented Boxes". *Journal of the Audio Engineering Society*, 19(5), 382-392. (Sealed box theory precursor)

3. Beranek, L.L. (1954). *Acoustics*. McGraw-Hill. (Radiation impedance theory)

---

## Notes

- All equations assume small-signal operation (linear regime)
- Large-signal effects (Xmax, power compression) not covered
- Leakage losses (Ql) assumed infinite (perfectly sealed box)
- Absorption losses neglected
- Voice coil inductance effects neglected at low frequencies
- High-frequency directivity not considered (low-frequency model only)
