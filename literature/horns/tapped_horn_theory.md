# Tapped Horn Theory

## Overview

A tapped horn is a horn-loaded loudspeaker where the driver is mounted **partway along the horn path** rather than at the throat. Both the front and rear radiation of the driver feed into the same acoustic path, creating unique interference characteristics that enable efficient low-frequency reproduction in a compact enclosure.

## Key References

### Primary Sources

1. **Berzborn, M. & Smithers, M. (2018)**
   "An Acoustic Model of the Tapped Horn Loudspeaker"
   AES Convention Paper 10047, 145th AES Convention, New York
   - **Contribution**: Presents a lumped-parameter model using two-port matrix representation
   - **Key results**: Far-field SPL prediction from Thiele-Small parameters
   - **Validation**: Correlated with measurements and Hornresp simulations
   - **Access**: AES E-Library (https://secure.aes.org/forum/pubs/conventions/?elib=19773)

2. **Danley, T.J. (2013)**
   US Patent 8,457,341 B2: "Sound reproduction with improved low frequency characteristics"
   - **Contribution**: Original tapped horn patent by inventor Tom Danley
   - **Key theory**: Quarter-wave resonance operation, phase relationships, tap point mechanics
   - **Access**: https://patents.google.com/patent/US8457341B2/en

3. **Kolbrek, B. (2020+)**
   "Horn Loudspeaker Simulation" series
   https://kolbrek.hornspeakersystems.info/
   - **Part 1**: Radiation and T-Matrix method for exponential horns
   - **Part 3**: Multiple segments and T-matrix chaining
   - **Contribution**: T-matrix formulation applicable to tapped horn sections

4. **Leach, W.M. Jr. (1996)**
   "A two-port analogous circuit and SPICE model for Salmon's family of acoustic horns"
   Journal of the Acoustical Society of America, Vol. 99, No. 3, pp. 1459-1464
   - **Contribution**: Transmission matrix approach for acoustic horns
   - **Relevance**: Provides theoretical foundation for T-matrix modeling

### Secondary Sources

5. **Hornresp User Manual**
   David McBean
   - Coverage of TH (tapped horn) option, segment configuration
   - Parameter optimization for tapped horns

6. **DIY Community Resources**
   - diysubwoofers.org tapped horn tutorials
   - AVS Forum tapped horn design guides with Hornresp examples

## Theory

### Physical Arrangement

```
                    ┌─────────────────┐
    Closed Throat ──┤  Upstream Horn  ├──┐
         (Z=∞)      │   Section (T₁)  │  │
                    └─────────────────┘  │
                                         ├── Driver (tap point)
                    ┌─────────────────┐  │
         Mouth ─────┤ Downstream Horn ├──┘
       (Z_rad)      │   Section (T₂)  │
                    └─────────────────┘
```

- **Upstream section**: From closed throat (Z=∞) to driver (front faces this)
- **Downstream section**: From driver (rear faces this) to open mouth (Z=Z_rad)
- **Tap point**: Driver location dividing the horn path

### Quarter-Wave Resonance Mechanism

The key innovation of the tapped horn is using the driver's rear radiation (180° out of phase with front) constructively:

1. **At low cutoff (quarter-wave resonance)**: Upstream length L₁ ≈ λ/4
   - Front radiation reflects from closed throat, arrives 180° out of phase
   - Would normally cause cancellation notch in conventional horn
   - But rear radiation (inherently 180° out of phase) fills in this notch

2. **As frequency increases**: Phase shift between front and rear outputs decreases
   - Combined with 180° physical phase difference, waves become additive
   - Creates smooth bandpass response without cancellation notch

3. **Result**: High-efficiency bandpass behavior in compact enclosure

### Mathematical Model

#### 1. Upstream Section Impedance

For the upstream section with closed throat (Z_throat → ∞):

```
Z_upstream = a₁ / c₁
```

where (a₁, b₁, c₁, d₁) are the T-matrix elements of the upstream horn section.

This follows from the T-matrix impedance transformation:
```
Z₁ = (a · Z₂ + b) / (c · Z₂ + d)
```
When Z₂ → ∞ (closed throat), Z₁ = a/c.

**Literature**: Kolbrek, "Horn Loudspeaker Simulation Part 1"

#### 2. Downstream Section Impedance

For the downstream section with radiating mouth:

```
Z_downstream = (a₂ · Z_rad + b₂) / (c₂ · Z_rad + d₂)
```

where:
- (a₂, b₂, c₂, d₂) are T-matrix elements of downstream section
- Z_rad is mouth radiation impedance (circular piston in infinite baffle)

**Literature**: Kolbrek, "Horn Loudspeaker Simulation Part 1"; Beranek (1954), Eq. 5.20

#### 3. Tap Point Impedance (Combined Load)

The driver sees both sections in parallel:

```
Z_tap = Z_upstream ∥ Z_downstream = (Z_up · Z_down) / (Z_up + Z_down)
```

**Note on phase**: The front and rear of the driver are 180° out of phase, but for impedance magnitude calculations (which determine driver loading), the parallel combination gives the correct acoustic load. Phase effects appear in the pressure response.

**Literature**: Berzborn & Smithers (2018), Eq. 7-10

#### 4. Exponential Horn T-Matrix

For an exponential horn segment with flare constant m:

```
γ = √(k² - m²)  (propagation constant, can be imaginary)
k = ω/c        (wavenumber)

a = e^(mL) [cos(γL) - (m/γ)sin(γL)]
b = e^(mL) j(Z_rc/S₂) (k/γ) sin(γL)
c = e^(mL) j(S₁/Z_rc) (k/γ) sin(γL)
d = e^(mL) (S₁/S₂) [cos(γL) + (m/γ)sin(γL)]
```

where Z_rc = ρc is the characteristic impedance of air.

**Literature**: Kolbrek, "Horn Loudspeaker Simulation Part 1"

### Boundary Conditions

1. **Throat (upstream end)**: Rigid termination, Z = ∞
2. **Mouth (downstream end)**: Radiation impedance of circular piston in infinite baffle
3. **Tap point**: Driver diaphragm with front facing upstream, rear facing downstream

### Design Characteristics

| Aspect | Front-Loaded Horn | Tapped Horn |
|--------|-------------------|-------------|
| Driver position | At throat | Partway along horn path |
| Radiation used | Front only | Both front and rear |
| Low-frequency mechanism | Horn loading | Quarter-wave resonance + interference |
| Typical bandwidth | Wide (multi-octave) | Narrow (subwoofer, ~1-2 octaves) |
| Size efficiency | Large for low frequencies | Compact for given low extension |
| Driver requirements | High BL, low Mms | High Mms acceptable (mass helps QW resonance) |

### Typical Use Cases

- **Subwoofers**: Primary application, typically 20-100 Hz range
- **Pro audio bass bins**: High efficiency in compact enclosures
- **Home theater subwoofers**: DIY community favorite for compact high-output designs

## Implementation Notes

### T-Matrix Framework Integration

The tapped horn implementation naturally extends gsd's existing T-matrix framework:

1. **Reuse existing functions**:
   - `exponential_horn_tmatrix()` for exponential sections
   - `conical_horn_tmatrix()` for conical sections
   - `circular_piston_radiation_impedance()` for mouth radiation

2. **New functions needed**:
   - `upstream_section_impedance()`: Calculate Z_up = a/c for closed throat
   - `downstream_section_impedance()`: Calculate Z_down from T-matrix transform
   - `tapped_horn_tap_impedance()`: Parallel combination Z_tap = Z_up ∥ Z_down

3. **Numerical considerations**:
   - Handle closed throat singularity: Use Z_up = a/c directly (not limit)
   - Avoid division by zero in parallel combination at resonances
   - Complex arithmetic for below-cutoff frequencies (γ imaginary)

### Hornresp Parameter Mapping

Hornresp uses 3-4 horn segments with the TH option:

| Hornresp | gsd TappedHorn |
|----------|----------------|
| S1 | upstream_throat_area |
| S2 | tap_area |
| S3/S4 | downstream_mouth_area |
| L12 | upstream_length |
| L23 + L34 | downstream_length |
| TH flag | Selects tapped horn mode |

### Validation Against Hornresp

1. **Create reference designs**: Use known working tapped horns (Othorn, Lilwrecker)
2. **Compare outputs**:
   - SPL response: <1 dB deviation in passband
   - Electrical impedance: <5% deviation at peaks
   - Cone excursion: <5% deviation
   - Phase response: <10° deviation

3. **Test edge cases**:
   - Short upstream section (driver near throat)
   - Long upstream section (driver near mouth)
   - Below-cutoff frequencies
   - Near quarter-wave resonance

## Common Pitfalls

1. **Driver selection**: Tapped horns work best with high-Mms drivers that can efficiently drive quarter-wave resonance
2. **Upstream length**: Too short = poor LF extension; too long = cancellation notch in passband
3. **Area ratios**: Mouth area should be significantly larger than tap area for proper loading
4. **Damping**: Some designs benefit from light damping in upstream section

## Patent Considerations

The tapped horn concept is covered by US Patent 8,457,341 B2 (Tom Danley/ServoDrive). However:
- The patent covers **physical designs**, not simulation software
- Academic/educational use and simulation tools are generally not infringing
- DIY builders should be aware of patent status for commercial applications

---

**Last updated**: 2025-01-11
**Validation status**: Literature review complete, implementation pending
