# Tapped Horn Full System Response Implementation

**Branch:** `feature/tapped-horn`

## Current Status

### ✅ Completed
1. Tapped horn geometry (`TappedHorn` dataclass)
2. Acoustic impedance calculation at tap point
3. T-matrix framework for exponential/conical profiles
4. Test suite (18 tests passing)
5. DesignAssistant integration
6. Parameter space for optimization
7. Literature documentation

### ⏳ Missing - **YOUR TASK**
Full system response coupling to get:
- **Electrical impedance** (Ze in ohms)
- **SPL output** (dB at 1m)
- **Cone excursion** (mm)
- **Efficiency** (%)

## Problem

Currently, `tapped_horn_tap_impedance()` calculates the **acoustic impedance** at the tap point in Pa·s/m³. This is correct, but it's not what Hornresp displays as "Ze" (electrical impedance in ohms).

To validate against Hornresp, we need to couple the acoustic load to the driver's electrical parameters.

## Implementation Required

### File: `src/gsd/simulation/tapped_horn_theory.py`

Add a new function:

```python
def tapped_horn_system_response(
    frequencies: NDArray[np.float64],
    tapped_horn: TappedHorn,
    driver: ThieleSmallParameters,
    medium: MediumProperties = None,
    voltage: float = 2.83,
) -> dict:
    """
    Calculate complete tapped horn system response.

    Returns dict with keys:
        - 'acoustic_impedance': Acoustic impedance at tap point (Pa·s/m³)
        - 'electrical_impedance': Electrical impedance seen at terminals (Ω)
        - 'spl': SPL at 1m (dB)
        - 'excursion': Cone excursion (mm)
        - 'efficiency': Reference efficiency (%)
        - 'phase': Acoustic phase at tap point (degrees)

    Literature:
        Berzborn & Smithers (2018), AES Paper 10047, Eq. 10-16

    Args:
        frequencies: Array of frequencies in Hz
        tapped_horn: TappedHorn geometry
        driver: Driver ThieleSmallParameters
        medium: Acoustic medium (default: c=344 m/s, rho=1.205 kg/m³)
        voltage: Input voltage (default: 2.83V = 1W @ 8Ω)

    Returns:
        Dictionary with complete system response
    """
```

### Algorithm (from Berzborn & Smithers 2018)

**Step 1: Calculate acoustic impedance at tap point**
```python
z_acoustic = tapped_horn_tap_impedance(frequencies, tapped_horn, medium)
```

**Step 2: Convert acoustic impedance to electrical domain**

For a tapped horn, the driver sees two loads:
- Front of driver → upstream section (Z_up)
- Rear of driver → downstream section (Z_down)

The electrical impedance is:
```python
# Force factor
Bl = driver.BL  # T·m

# Acoustic load impedance (parallel combination)
z_acoustic = tapped_horn_tap_impedance(frequencies, tapped_horn, medium)

# Convert to mechanical impedance
Z_mechanical = z_acoustic * (driver.S_d ** 2)

# Add driver mechanical impedance
omega = 2 * np.pi * frequencies
Z_mech_driver = driver.M_ms * 1j * omega + driver.R_ms / (1j * omega) + driver.C_ms

# Total mechanical impedance
Z_mech_total = Z_mechanical + Z_mech_driver

# Convert to electrical impedance
Z_electrical = (Bl ** 2) / Z_mech_total

# Add voice coil impedance
Z_vc = driver.R_e + 1j * omega * driver.L_e

# Total electrical impedance
Ze = Z_electrical + Z_vc
```

**Step 3: Calculate SPL**

From Berzborn & Smithers Eq. 13-15:

```python
# Volume velocity at tap point
# For parallel impedance: U = p / Z
# Pressure at tap point depends on throat radiation
# This requires integrating through the horn to the mouth

# Simplified approach (validate with Hornresp):
# Use the radiation impedance at the mouth
z_mouth = downstream_section_impedance(frequencies, tapped_horn, medium)
p_mouth = ... # pressure at mouth
U_mouth = p_mouth / z_mouth

# SPL at 1m
spl = 20 * np.log10(np.abs(p_mouth) / 20e-6)  # ref 20 µPa
```

**Step 4: Calculate cone excursion**

```python
# Cone displacement from volume velocity
xd = U_mouth / (1j * omega * driver.S_d)
excursion_mm = np.abs(xd) * 1000
```

### Reference: Front-Loaded Horn Coupling

Check `src/gsd/simulation/horn_driver_integration.py` for how this is done for standard horns. The tapped horn is similar but with:
- **Different acoustic load** (parallel combination instead of single throat)
- **Driver position** (at tap point, not throat)
- **Phase relationships** (front/rear radiation are 180° out of phase)

## Validation Data

Location: `tests/validation/drivers/bc_15ps100/tapped_horn/`

Files:
- `params.txt` - Hornresp parameters
- `simulation.txt` - Hornresp results (535 lines of data)
- `README.md` - Design summary

Key test frequencies from Hornresp:
```
Freq (Hz)  SPL (dB)  Ze (Ω)   Xd (mm)
----------------------------------------
20.0       41.33     6.29     1.54
30.0       66.42     26.14    1.41
40.0       76.37     34.76    1.23
50.0       85.55     29.63    0.88
60.0       91.18     21.84    0.61
80.0       94.73     18.82    0.42
100.0      98.61     10.19    0.31
150.0      102.04    7.50     0.19
200.0      102.71    6.83     0.19
300.0      102.48    6.93     0.26
400.0      101.89    7.06     0.32
```

Expected accuracy (from CLAUDE.md):
- **SPL**: < 1 dB deviation in passband
- **Ze magnitude**: < 5% deviation at peaks
- **Xd**: < 5% deviation
- **Phase**: < 10° deviation

## Implementation Steps

1. **Read existing coupling code**
   - Study `horn_driver_integration.py:horn_electrical_impedance()`
   - Understand how front-loaded horns couple acoustic→mechanical→electrical

2. **Adapt for tapped horn**
   - Key difference: acoustic load is parallel Z_up || Z_down
   - Driver is at tap point, not throat
   - Front and rear radiation both feed into horn

3. **Implement function**
   - Create `tapped_horn_system_response()` in `tapped_horn_theory.py`
   - Follow Berzborn & Smithers (2018) equations
   - Add proper literature citations in docstring

4. **Test against Hornresp**
   - Load validation data from `tests/validation/drivers/bc_15ps100/tapped_horn/simulation.txt`
   - Compare Ze, SPL, Xd at key frequencies
   - Verify accuracy requirements met

5. **Add tests**
   - Create test in `tests/test_tapped_horn.py`
   - Compare with Hornresp reference data
   - Mark as skipped until data is loaded (or implement now)

6. **Commit changes**
   - Document in commit message
   - Reference this task file

## Literature Citations Required

All simulation code MUST cite literature (per CLAUDE.md):

```python
def tapped_horn_system_response(...):
    """
    Calculate complete tapped horn system response.

    Literature:
        Berzborn, M. & Smithers, M. (2018). "An Acoustic Model of the
        Tapped Horn Loudspeaker." AES Convention Paper 10047.

        Eqs. 10-16: Electro-acoustic coupling for tapped horns

        Danley, T.J. (2013). US Patent 8,457,341 B2
        Fig. 7-9: Driver coupling to tap point

    Validation:
        Compare with Hornresp simulation at:
        tests/validation/drivers/bc_15ps100/tapped_horn/simulation.txt

        Expected accuracy:
        - SPL: <1 dB in passband (40-200 Hz)
        - Ze: <5% at impedance peaks
        - Xd: <5% deviation
    """
```

## Key Challenges

1. **Phase relationships** - Front and rear radiation are 180° out of phase
   - Berzborn & Smithers handle this in the impedance transformation
   - Must account for this in SPL calculation

2. **Parallel impedance** - Two horn sections in parallel at tap point
   - Already implemented in `tapped_horn_tap_impedance()`
   - Need to ensure this carries through to electrical domain correctly

3. **Mouth radiation** - SPL is measured at mouth, not at tap point
   - Need to propagate pressure from tap point to mouth
   - Use T-matrix or radiation impedance at mouth

## Success Criteria

After implementation, running:

```python
from gsd.simulation.types import TappedHorn
from gsd.simulation.tapped_horn_theory import tapped_horn_system_response
from gsd.driver import load_driver

driver = load_driver("BC_15PS100")
th = TappedHorn(
    upstream_throat_area=150.0,
    tap_area=855.0,
    downstream_mouth_area=6000.0,
    upstream_length=180.0,
    downstream_length=200.0,
)

result = tapped_horn_system_response(
    frequencies=np.array([40.0, 50.0, 60.0, 100.0]),
    tapped_horn=th,
    driver=driver,
    voltage=2.83
)

print(result['electrical_impedance'])  # Should match Hornresp Ze
print(result['spl'])  # Should match Hornresp SPL
print(result['excursion'])  # Should match Hornresp Xd
```

Should produce results within specified tolerances of Hornresp.

## Files to Modify

1. `src/gsd/simulation/tapped_horn_theory.py` - Add `tapped_horn_system_response()`
2. `tests/test_tapped_horn.py` - Add validation tests
3. This file (`IMPLEMENTATION_TASK.md`) - Delete when complete

## Commit Message Template

```
Implement tapped horn full system response coupling

Add complete system response calculation for tapped horns including:
- Electrical impedance (Ze) from acoustic load coupling
- SPL output at 1m
- Cone excursion calculation
- Reference efficiency

Based on Berzborn & Smithers (2018), AES Paper 10047.
Validated against Hornresp at tests/validation/drivers/bc_15ps100/tapped_horn/

Accuracy:
- SPL: <1 dB in passband
- Ze: <5% at peaks
- Xd: <5% deviation

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

**Ready to implement!** Start by reading the existing horn driver integration code, then adapt it for tapped horn topology.
