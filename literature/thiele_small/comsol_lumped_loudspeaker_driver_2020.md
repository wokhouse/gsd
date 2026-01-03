# Lumped Loudspeaker Driver - COMSOL Model Documentation

**Authors:** COMSOL (application library documentation)
**Publication:** COMSOL Application Library (Acoustics Module)
**URL:** https://www.comsol.com/model/download/1179101/models.aco.lumped_loudspeaker_driver.pdf
**DOI:** N/A (Application documentation)

**Relevance to GSD:** Provides complete electro-mechano-acoustical equivalent circuit model for moving-coil loudspeakers. Shows how to transform electrical, mechanical, and acoustic domains using impedance and mobility analogies. Includes all Thiele-Small parameters and their relationships.

---

## Summary

This document describes a lumped parameter model of a moving-coil loudspeaker where the electrical and mechanical components are represented as equivalent circuits. The model couples the lumped circuit to a 2D axisymmetric pressure acoustics FEM model of the surrounding air, providing a complete electro-mechano-acoustical simulation.

Key contributions:
- **Electroacoustic analogy** (Table I) relating mechanical/acoustic quantities to electrical circuit elements
- **Equivalent circuit diagrams** (Figure 2) for electrical and mechanical domains
- **Thiele-Small parameters** (Table 2) - fundamental physical parameters
- **Small-signal parameters** (Table 3) - measured quantities derived from fundamentals
- **Coupling equations** between electrical, mechanical, and acoustic domains
- **Leach model** for voice coil inductance and magnetic losses

This provides the theoretical foundation for driver modeling used in horn simulation tools.

---

## Key Concepts

### Table I: Electroacoustic Analogies

**Mechanical (Impedance Analogy):**

| Electrical Component | Mechanical Analog | SI Unit |
|---------------------|-------------------|----------|
| Resistor | Mechanical resistance (damping/friction) | N·s/m |
| Inductor | Mass (inertance) | kg |
| Capacitor | Compliance (1/spring constant) | m/N |

**Acoustical:**

| Electrical Component | Acoustic Analog | SI Unit |
|---------------------|----------------|----------|
| Resistor | Acoustic resistance (viscous/thermal losses) | kg/(m⁴·s) |
| Inductor | Acoustic mass (inertance of air volume) | kg/m⁴ |
| Capacitor | Acoustic compliance (compressibility) | m⁵/N |

**Key mappings:**
- **Voltage** → Force (mechanical) or Pressure (acoustic)
- **Current** → Velocity (mechanical) or Volume velocity (acoustic)

**Page/Section:** Page 1, Table I

---

## Key Equations

### Electro-Mechanical Coupling (Lorentz Force)

**Force on voice coil:**
```
F = BL · i_c
```

**Back EMF voltage:**
```
V_back = BL · u_D
```

**Variables:**
- **F**: Lorentz force (N)
- **BL**: Force factor (T·m or Wb/m) - product of magnetic field B and voice coil length L
- **i_c**: Voice coil current (A)
- **u_D**: Diaphragm velocity (m/s)

**Page/Section:** Page 2, Figure 2 description

**Implementation Notes:**
- Two controlled sources couple electrical and mechanical circuits
- Force source in mechanical circuit: F = BL·i_c
- Voltage source in electrical circuit: V = BL·u_D (back EMF)

### Mechano-Acoustic Coupling

**Force on diaphragm:**
```
F_D = ∫(Δp · n_z) dA
```

**Diaphragm velocity:**
```
v = u_D · e_z
```

**Variables:**
- **F_D**: Acoustic pressure force on diaphragm (N)
- **Δp**: Pressure drop across diaphragm (Pa)
- **n_z**: Axial component of surface normal
- **dA**: Surface area element
- **v**: Velocity vector (m/s)
- **u_D**: Current in mechanical circuit (represents diaphragm velocity, m/s)
- **e_z**: Unit vector in axial direction

**Page/Section:** Page 2, Equations 1-2

**Implementation Notes:**
- Force from acoustics applied to mechanical circuit
- Velocity from mechanical circuit applied to acoustics boundary
- This is the coupling between FEM acoustics and lumped circuit

---

## Thiele-Small Parameters

### Table 2: Fundamental Small-Signal Parameters

**Physical parameters (constants):**

| Symbol | Value | Description |
|--------|--------|-------------|
| M_md | 33.4 g | Moving mass (voice coil + diaphragm) |
| C_ms | 1.18×10⁻³ m/N | Suspension compliance (spider + surround) |
| R_ms | 1.85 N·s/m | Mechanical resistance (damping losses) |
| L_E | 6.89 mH | Voice coil inductance |
| R_E | 6.4 Ω | Voice coil DC resistance |
| BL | 11.4 T·m | Force factor (magnetic field × coil length) |
| S_D | πa² | Driver effective area (piston radius a = 12 cm) |

**Page/Section:** Page 3, Table 2

**Notes:**
- These are **physical parameters** (not directly measured)
- M_md includes voice coil mass, diaphragm mass
- C_ms is inverse of spring constant: C = 1/k where k = F/x
- R_ms represents mechanical losses in suspensions
- S_D calculated from equivalent piston radius (measured half-way into surround)
- All constants given in low-frequency limit

### Table 3: Small-Signal Parameters (Measured)

**Derived parameters (can be measured from impedance curve):**

| Symbol | Expression | Description |
|--------|------------|-------------|
| F_s | 1/(2π√(M_md·C_ms)) | Fundamental resonance frequency |
| Q_es | 2πF_s·M_md / R_E | Electrical Q factor at F_s |
| Q_ms | 2πF_s·M_md / R_ms | Mechanical Q factor at F_s |
| Q_ts | Q_es·Q_ms / (Q_es + Q_ms) | Total Q factor at F_s |
| V_as | ρc²·S_D²·C_ms | Equivalent volume of compliance |
| η₀ | Reference efficiency | Theoretical efficiency |

**Page/Section:** Page 3, Table 3

**Derivation formulas:**

**Resonance frequency:**
```
F_s = 1 / (2π) · √(M_md / C_ms)  [Hz]
```
or equivalently:
```
F_s = (1/2π) · √(1 / (M_md·C_ms))  [Hz]
```

**Q factors (mechanical filter theory):**
```
Q_es = 2πF_s·M_md / R_E
Q_ms = 2πF_s·M_md / R_ms
Q_ts = Q_es·Q_ms / (Q_es + Q_ms)
```

**Equivalent volume:**
```
V_as = ρc²·S_D²·C_ms
```
This is the volume of air having the same compliance as the suspension.

**Reference efficiency:**
```
η₀ = (BL)²·R_es / [R_E·(R_es + R_E)²] · S_D² / (ρc)
```
where R_es = R_E + (BL)²/R_ms

---

## Equivalent Circuit Model

### Electrical Circuit (Figure 2, top)

**Components:**
- **V₀**: Voltage source (input signal)
- **R_g**: Generator output resistance (typically 0 Ω)
- **R_E**: Voice coil DC resistance
- **L_E(ω)**: Frequency-dependent voice coil inductance
- **R'_E(ω)**: Frequency-dependent magnetic loss resistance
- **BL·u_D**: Back EMF voltage source (controlled by mechanical velocity)

**Equations (Leach model):**
```
L_E(ω) = L_E / sin(n_e·π/2) · ω^(n_e-1)
R'_E(ω) = L_E / cos(n_e·π/2) · ω^n_e
```

where **n_e** is voice coil loss factor (0.7 in this model).

**Page/Section:** Page 2, Figure 2 (top) and Page 4

**Current in electrical circuit:** i_c (Amperes)

### Mechanical Circuit (Figure 2, bottom)

**Impedance analogy:**
- **Current → Velocity**: u_D (m/s) is the "current" in mechanical circuit
- **Voltage → Force**: F (N) is the "voltage" in mechanical circuit

**Components:**
- **BL·i_c**: Force source (Lorentz force, controlled by electrical current)
- **M_md**: Inductor (moving mass)
- **R_ms**: Resistor (mechanical losses/damping)
- **C_ms**: Capacitor (suspension compliance)
- **-F_D**: Voltage source representing acoustic pressure force

**Impedances:**
- **Mass impedance**: Z_m = jωM_md
- **Mechanical resistance**: Z_R = R_ms
- **Compliance impedance**: Z_C = 1/(jωC_ms)

**Page/Section:** Page 2, Figure 2 (bottom)

**Current in mechanical circuit:** u_D (velocity in m/s)

### Circuit Equations

**Electrical domain:**
```
V₀ = (R_g + R_E + jωL_E)·i_c + BL·u_D
```

**Mechanical domain:**
```
BL·i_c = (R_ms + jωM_md + 1/(jωC_ms))·u_D + F_D
```

**Coupling:**
- Electrical → Mechanical: Force = BL·i_c
- Mechanical → Electrical: Back EMF = BL·u_D
- Acoustics → Mechanical: Force F_D applied
- Mechanical → Acoustics: Velocity u_D applied to boundary

**Page/Section:** Pages 2-3, Figure 2

---

## Electrical Impedance

**Definition:**
```
Z_e = V₀ / i_c
```

**From equivalent circuit:**
```
Z_e = R_E + R'_E(ω) + jωL_E(ω) + Z_mech_to_electrical
```

Where **Z_mech_to_electrical** is the mechanical impedance reflected to the electrical side through the BL coupling.

**At resonance (F_s):**
- Impedance minimum occurs
- Reactance components cancel
- Z_e ≈ R_E + R'_E + (BL)²·R_ms

**At low frequencies (f << F_s):**
- Controlled by compliance C_ms (capacitive reactance)
- Z_e ≈ R_E + j·(BL)²/(ωC_ms) - large

**At high frequencies (f >> F_s):**
- Controlled by mass M_md (inductive reactance)
- Z_e ≈ R_E + jωL_E

**Page/Section:** Page 3, discussion and Page 6 (Figure 6 top right)

---

## Power and Efficiency

### Electric Input Power (Equation 4)

```
P_E = 0.5·Re{V₀·i_c*}
```

Where * denotes complex conjugate.

**Page/Section:** Page 4, Equation 4

### Acoustic Radiated Power (Equation 3)

```
P_AR = ∫(n · I) dA
```

Where:
- **n**: Surface normal
- **I**: Acoustic intensity vector
- Integral over diaphragm surface

**Page/Section:** Page 4, Equation 3

### Efficiency (Equation 5)

```
η = P_AR / P_E
```

**Reference efficiency:**
```
η₀ = (BL)²·R_es / [R_E·(R_es + R_E)²] · S_D² / (ρc)
```

**Page/Section:** Page 4, Equation 5

**Typical values:**
- Low-frequency drivers: η₀ ~ 0.1% to 1%
- Midrange drivers: η₀ ~ 1% to 5%
- Compression drivers: η₀ ~ 10% to 50%

---

## System Response

### Diaphragm Velocity

**Low-frequency approximation (piston mass-controlled):**
```
u_D ≈ BL·i_c / (jωM_md)
```

**High-frequency approximation:**
```
u_D ≈ BL·i_c / √(R_ms·jωM_md)  [More complex due to mass and damping]
```

**Resonance behavior:**
- At F_s: velocity maximum (current minimum in impedance)
- Below F_s: stiffness-controlled (compliance dominates)
- Above F_s: mass-controlled (inductance dominates)

**Page/Section:** Page 5, Figure 5 (top left)

### Voice Coil Impedance

**Magnitude:**
```
|Z_e| = |V₀ / i_c|
```

**Phase:**
- Below F_s: Phase approaches +90° (capacitive)
- At F_s: Phase = 0° (resistive minimum)
- Above F_s: Phase approaches +90° (inductive)

**Page/Section:** Page 6, Figure 6 (top right)

### Sensitivity

**Definition:** Sound pressure level at 1 m for 1 V RMS input

**Low-frequency (piston approximation):**
```
SPL ≈ 20·log₁₀(f) + constant
```
Roll-off: 12 dB/octave below F_s (closed back) or 6 dB/octave (open back)

**Reference sensitivity:**
```
S_ref = 20·log₁₀(ρc/2π) + 10·log₁₀(η₀) + 20·log₁₀(BL²·R_es/(R_E·M_md))
```

**Page/Section:** Page 6, Figure 6 (bottom left)

---

## Implementation Approach for GSD

### Phase 1: Define Data Structures

```python
from pydantic import BaseModel, Field, confloat
from typing import Optional

class ThieleSmallParameters(BaseModel):
    """Fundamental Thiele-Small parameters (physical)."""

    # Moving mass
    m_ms: confloat(ge=0.001, le=5.0)  # kg (e.g., 0.001 to 5 kg)

    # Suspension compliance
    c_ms: confloat(ge=1e-6, le=1e-2)  # m/N (e.g., 10⁻⁶ to 10⁻²)

    # Mechanical resistance
    r_ms: confloat(ge=0.1, le=1000.0)  # N·s/m (damping)

    # Electrical parameters
    r_e: confloat(ge=1.0, le=100.0)  # Ohms (DC resistance)
    l_e: confloat(ge=0.1e-6, le=100e-3)  # H (voice coil inductance)
    bl: confloat(ge=1.0, le=50.0)  # T·m (force factor)

    # Diaphragm area
    s_d: confloat(ge=1e-4, le=0.1)  # m² (effective area)

    @property
    def f_s(self) -> float:
        """Resonance frequency (Hz)."""
        return 1 / (2 * np.pi) * np.sqrt(self.m_ms / self.c_ms)

    @property
    def q_es(self) -> float:
        """Electrical Q factor."""
        return 2 * np.pi * self.f_s * self.m_ms / self.r_e

    @property
    def q_ms(self) -> float:
        """Mechanical Q factor."""
        return 2 * np.pi * self.f_s * self.m_ms / self.r_ms

    @property
    def q_ts(self) -> float:
        """Total Q factor."""
        return (self.q_es * self.q_ms) / (self.q_es + self.q_ms)

    @property
    def v_as(self, rho=1.18, c=343.0) -> float:
        """Equivalent volume of compliance (m³)."""
        return rho * c**2 * self.s_d**2 * self.c_ms
```

### Phase 2: Electrical Impedance Calculation

```python
def electrical_impedance(
    driver: ThieleSmallParameters,
    frequency: float,
    radiation_impedance: complex = 0j
) -> complex:
    """
    Calculate driver electrical impedance including coupled load.

    Literature: COMSOL Lumped Loudspeaker Driver documentation

    Args:
        driver: Thiele-Small parameters
        frequency: Analysis frequency (Hz)
        radiation_impedance: Acoustic load at diaphragm (Pa·s/m³)

    Returns:
        Complex electrical impedance (ohms)
    """
    omega = 2 * np.pi * frequency

    # Electrical impedance (voice coil)
    # Simplified: ignore frequency-dependent L_E and R'_E for now
    z_e = driver.r_e + 1j * omega * driver.l_e

    # Mechanical impedance (mass + compliance + resistance)
    z_m = (driver.r_ms +
            1j * omega * driver.m_ms +
            1 / (1j * omega * driver.c_ms))

    # Acoustic impedance (normalized to diaphragm area)
    z_a = radiation_impedance / driver.s_d**2 if radiation_impedance != 0 else 0

    # Coupling factor (BL)²
    bl_squared = driver.bl**2

    # Total electrical impedance with coupled mechanical/acoustic loads
    # From circuit analysis: Z_total = Z_e + (BL)² / (Z_m + Z_a)
    z_total = z_e + bl_squared / (z_m + z_a)

    return z_total
```

### Phase 3: Volume Velocity and SPL

```python
def diaphragm_velocity(
    driver: ThieleSmallParameters,
    frequency: float,
    voltage: float,
    radiation_impedance: complex = 0j
) -> complex:
    """
    Calculate diaphragm velocity for given voltage.

    Literature: COMSOL Lumped Loudspeaker Driver documentation

    Args:
        driver: Thiele-Small parameters
        frequency: Analysis frequency (Hz)
        voltage: Input voltage (V)
        radiation_impedance: Acoustic load (Pa·s/m³)

    Returns:
        Complex velocity (m/s)
    """
    omega = 2 * np.pi * frequency
    i_c = electrical_impedance(driver, frequency, radiation_impedance)

    # Mechanical circuit equation (from Figure 2):
    # BL·i_c = (R_ms + jωM_ms + 1/(jωC_ms))·u_D + F_D

    # Solve for u_D (diaphragm velocity)
    z_mech = (driver.r_ms +
               1j * omega * driver.m_ms +
               1 / (1j * omega * driver.c_ms))

    # Force from acoustic pressure (applied to mechanical circuit)
    f_acoustic = radiation_impedance * driver.s_d if radiation_impedance != 0 else 0

    # Mechanical circuit: BL·i_c - F_acoustic = z_mech·u_D
    u_d = (driver.bl * i_c - f_acoustic) / z_mech

    return u_d
```

---

## Validation Approach

**To verify implementation against COMSOL documentation:**

1. **Resonance frequency:**
   - Compare calculated F_s with specified driver parameters
   - Should match: F_s = 1/(2π)√(M_md/C_ms)
   - Test with Table 2 values

2. **Q factors:**
   - Verify Q_es, Q_ms, Q_ts calculations
   - Check Q_ts relationship: 1/Q_ts = 1/Q_es + 1/Q_ms

3. **Electrical impedance curve:**
   - Reproduce Figure 6 (top right) shape
   - Verify impedance minimum at F_s
   - Check phase behavior (capacitive below, inductive above)

4. **Equivalent volume:**
   - Calculate V_as from physical parameters
   - Verify: V_as = ρc²·S_D²·C_ms

**Acceptance Criteria:**
- Resonance within 1% of calculated value
- Impedance curve shape matches COMSOL Figure 6
- Q factors satisfy relationship formula

---

## Notes

**Impedance vs Mobility Analogy:**

This document uses the **impedance analogy** for mechanical systems:
- **Current** represents velocity
- **Voltage** represents force
- **Mass** → Inductor (Z = jωM)
- **Compliance** → Capacitor (Z = 1/(jωC))
- **Resistance** → Resistor

Alternative is **mobility analogy** (swap V↔I, L↔C):
- Current represents force
- Voltage represents velocity
- Mass → Capacitor
- Compliance → Inductor

Both are valid; impedance analogy is more common in loudspeaker modeling.

**Leach Model:**

The frequency-dependent voice coil model (Page 4) is the Leach model:
```
L_E(ω) = L_E / sin(n_e·π/2) · ω^(n_e-1)
R'_E(ω) = L_E / cos(n_e·π/2) · ω^n_e
```

**n_e = 0**: Lossless case (R'_E open, L_E constant)
**n_e = 1**: Typical measured value

**Coupling Domains:**

**Electrical → Mechanical:**
- Lorentz force: F = BL·i
- Proportional to current

**Mechanical → Electrical:**
- Back EMF: V = BL·u
- Proportional to velocity

**Mechanical ↔ Acoustical:**
- Force: F_D = ∫p·n_z dA (pressure integral)
- Velocity: v = u_D·e_z (uniform velocity boundary)

**Model Limitations:**

1. **Low-frequency assumption:** Piston approximation valid for λ >> diaphragm diameter
2. **Rigid piston:** No cone breakup or modal behavior
3. **Linear acoustics:** No harmonic distortion
4. **Infinite baffle:** Front radiation modeled accurately
5. **Lumped parameter:** Distributed effects not modeled

**Extension to Horns:**

For horn-loaded drivers:
1. Replace radiation impedance (piston in baffle) with horn throat impedance
2. Horn throat impedance calculated using T-matrix method (see Kolbrek, Chabassier)
3. Acoustic load Z_a becomes much larger, better efficiency
4. Resonance shifts due to added stiffness from air volume in horn

**Implementation Priority:**

For gsd Phase 3 (Driver Equivalent Circuit):
1. Implement Thiele-Small parameter class
2. Implement electrical impedance calculation
3. Implement diaphragm velocity calculation
4. Couple to horn throat impedance (from Phase 2)
5. Calculate complete system response

This COMSOL documentation provides exactly the equivalent circuit approach needed for driver modeling in horn simulation.
