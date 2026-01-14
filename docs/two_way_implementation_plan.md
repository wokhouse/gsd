# Two-Way System Implementation Plan

**Based on:** BC 12FW88 + DH450 Case Study
**Goal:** Enable one-shot design success by integrating horn and crossover optimization

---

## New Functions to Add

### 1. Horn Physics Calculations

**File:** `src/gsd/optimization/api/horn_physics.py` (NEW FILE)

```python
"""
Horn physics calculations for two-way system integration.

These functions bridge the gap between horn geometry and crossover design,
allowing designers to work backwards from crossover targets to horn parameters.
"""

import numpy as np
from typing import Dict, Tuple, Optional


def calculate_lf_beaming_frequency(driver) -> float:
    """
    Calculate the frequency where LF driver starts beaming.

    Beaming occurs when ka > 2, where k = 2πf/c and a = piston radius.
    Solving for f: f_beam = 2c/(π×d) where d is piston diameter.

    Literature:
    - Beranek (1954) - Directivity of circular pistons
    - Olson (1947) - Radiation impedance and directivity

    Args:
        driver: ThieleSmallParameters object

    Returns:
        Beaming frequency (Hz), above which directivity increases rapidly

    Example:
        >>> driver = load_driver("BC_12FW88")
        >>> f_beam = calculate_lf_beaming_frequency(driver)
        >>> print(f"LF driver beaming: {f_beam:.0f} Hz")
    """
    c = 343.0  # Speed of sound (m/s)
    piston_diameter = 2 * np.sqrt(driver.S_d / np.pi)  # S_d = π×a²
    f_beam = (2 * c) / (np.pi * piston_diameter)
    return f_beam


def calculate_target_horn_fc(
    desired_crossover_hz: float,
    lf_driver_beaming_hz: Optional[float] = None,
    xo_fc_ratio: float = 2.0
) -> float:
    """
    Calculate target horn cutoff frequency for desired crossover.

    The traditional rule is XO = 2×Fc, but optimized systems can use
    XO = 1.2-1.5×Fc if the horn has smooth response below cutoff.

    Args:
        desired_crossover_hz: Target crossover frequency (Hz)
        lf_driver_beaming_hz: LF driver beaming frequency (Hz) - caps XO if provided
        xo_fc_ratio: Desired XO/Fc ratio (default 2.0, use 1.3 for optimized)

    Returns:
        Target horn cutoff frequency (Hz)

    Example:
        >>> # For 800Hz XO with 2×Fc rule
        >>> fc = calculate_target_horn_fc(800, xo_fc_ratio=2.0)
        >>> print(f"Target Fc: {fc:.0f} Hz")  # 400 Hz

        >>> # For 800Hz XO with optimized integration
        >>> fc = calculate_target_horn_fc(800, xo_fc_ratio=1.3)
        >>> print(f"Target Fc: {fc:.0f} Hz")  # 615 Hz
    """
    # Cap XO at LF beaming frequency if provided
    if lf_driver_beaming_hz:
        xo_hz = min(desired_crossover_hz, 0.8 * lf_driver_beaming_hz)
    else:
        xo_hz = desired_crossover_hz

    return xo_hz / xo_fc_ratio


def calculate_mouth_area_for_fc(
    throat_area_cm2: float,
    length_cm: float,
    target_fc_hz: float,
    speed_of_sound: float = 343.0
) -> float:
    """
    Calculate required mouth area for target cutoff frequency.

    For exponential horn:
        Fc = (c/4π) × m
        where m = ln(mouth/throat) / L

    Solving for mouth:
        m = 4π × Fc / c
        ln(mouth/throat) = m × L
        mouth = throat × exp(m × L)

    Literature:
        - Olson (1947), Eq. 5.18 - Horn cutoff frequency
        - Beranek (1954), Chapter 5 - Exponential horn theory

    Args:
        throat_area_cm2: Throat area (cm²)
        length_cm: Horn length (cm)
        target_fc_hz: Target cutoff frequency (Hz)
        speed_of_sound: Speed of sound (m/s), default 343 m/s at 20°C

    Returns:
        Required mouth area (cm²)

    Example:
        >>> # Calculate mouth for 400Hz Fc, 250mm horn, 7cm² throat
        >>> mouth = calculate_mouth_area_for_fc(7.0, 25.0, 400)
        >>> print(f"Mouth: {mouth:.0f} cm²")  # ~273 cm²
    """
    L = length_cm / 100.0  # Convert to meters
    throat_m2 = throat_area_cm2 / 10000.0  # Convert to m²

    # Calculate required flare constant
    m = (4 * np.pi * target_fc_hz) / speed_of_sound

    # Calculate required mouth area
    mouth_m2 = throat_m2 * np.exp(m * L)

    return mouth_m2 * 10000.0  # Convert back to cm²


def calculate_fc_from_mouth(
    throat_area_cm2: float,
    mouth_area_cm2: float,
    length_cm: float,
    speed_of_sound: float = 343.0
) -> float:
    """
    Calculate horn cutoff frequency from geometry.

    Inverse of calculate_mouth_area_for_fc().

    Args:
        throat_area_cm2: Throat area (cm²)
        mouth_area_cm2: Mouth area (cm²)
        length_cm: Horn length (cm)
        speed_of_sound: Speed of sound (m/s)

    Returns:
        Horn cutoff frequency (Hz)

    Example:
        >>> fc = calculate_fc_from_mouth(7.0, 250.0, 25.0)
        >>> print(f"Fc: {fc:.0f} Hz")  # ~390 Hz
    """
    L = length_cm / 100.0  # Convert to meters
    throat_m2 = throat_area_cm2 / 10000.0
    mouth_m2 = mouth_area_cm2 / 10000.0

    # Calculate flare constant
    m = np.log(mouth_m2 / throat_m2) / L

    # Calculate cutoff frequency
    fc = (speed_of_sound * m) / (4 * np.pi)

    return fc


def assess_mouth_area_feasibility(
    required_mouth_cm2: float,
    available_mouth_cm2: float,
    target_fc_hz: float,
    throat_area_cm2: float = 7.0,
    length_cm: float = 25.0
) -> Dict[str, any]:
    """
    Assess if required mouth area is feasible within constraints.

    Provides recommendations if constraints cannot be met.

    Args:
        required_mouth_cm2: Required mouth area for target Fc (cm²)
        available_mouth_cm2: Maximum mouth area from printer constraint (cm²)
        target_fc_hz: Target cutoff frequency (Hz)
        throat_area_cm2: Throat area (cm²), default 7.0
        length_cm: Horn length (cm), default 25.0

    Returns:
        Dict with:
        - feasible: bool
        - required_mouth_cm2: float
        - available_mouth_cm2: float
        - resulting_fc_hz: float (if not feasible)
        - fc_error_hz: float (if not feasible)
        - recommendation: str
        - sensitivity_penalty_db: float (if not feasible)

    Example:
        >>> result = assess_mouth_area_feasibility(
        ...     required_mouth_cm2=273,
        ...     available_mouth_cm2=250,
        ...     target_fc_hz=400
        ... )
        >>> if not result['feasible']:
        ...     print(result['recommendation'])
    """
    if required_mouth_cm2 <= available_mouth_cm2:
        return {
            "feasible": True,
            "required_mouth_cm2": required_mouth_cm2,
            "available_mouth_cm2": available_mouth_cm2,
            "recommendation": f"Design with {required_mouth_cm2:.0f}cm² mouth (fits constraint)",
            "sensitivity_penalty_db": 0.0
        }
    else:
        # Calculate resulting Fc with max available mouth
        resulting_fc = calculate_fc_from_mouth(
            throat_area_cm2,
            available_mouth_cm2,
            length_cm
        )

        fc_error = resulting_fc - target_fc_hz

        # Estimate sensitivity penalty
        # Smaller mouth = less HF sensitivity
        # Rough approximation: 10×log10(available/required) dB
        sensitivity_penalty = 10 * np.log10(available_mouth_cm2 / required_mouth_cm2)

        recommendation = (
            f"Required mouth ({required_mouth_cm2:.0f}cm²) exceeds constraint ({available_mouth_cm2:.0f}cm²).\n"
            f"Options:\n"
            f"  1. Use max mouth ({available_mouth_cm2:.0f}cm²): Fc={resulting_fc:.0f}Hz "
            f"({fc_error:+.0f}Hz error, {sensitivity_penalty:+.1f}dB sensitivity loss)\n"
            f"  2. Use multi-piece horn (2× length)\n"
            f"  3. Accept higher crossover frequency"
        )

        return {
            "feasible": False,
            "required_mouth_cm2": required_mouth_cm2,
            "available_mouth_cm2": available_mouth_cm2,
            "resulting_fc_hz": resulting_fc,
            "fc_error_hz": fc_error,
            "sensitivity_penalty_db": sensitivity_penalty,
            "recommendation": recommendation
        }
```

---

### 2. Crossover Optimization

**Add to:** `src/gsd/optimization/api/two_way_system.py`

```python
def optimize_crossover_frequency(
    lf_driver_name: str,
    hf_driver_name: str,
    lf_enclosure_params: Dict[str, float],
    horn_fc_hz: float,
    horn_length_cm: float,
    xo_range_hz: Tuple[float, float] = (600, 1200),
    step_hz: int = 50
) -> Dict[str, any]:
    """
    Find optimal crossover frequency by sweeping range.

    Tests each crossover frequency and:
    1. Optimizes HF padding for flatness
    2. Calculates system response
    3. Measures crossover region dip
    4. Selects frequency with minimal dip

    Args:
        lf_driver_name: Low-frequency driver name
        hf_driver_name: High-frequency driver name
        lf_enclosure_params: {"Vb": m³, "Fb": Hz}
        horn_fc_hz: Horn cutoff frequency (Hz)
        horn_length_cm: Horn length (cm)
        xo_range_hz: (min, max) crossover frequencies to test (Hz)
        step_hz: Step size for sweep (Hz)

    Returns:
        Dict with:
        - optimal_xo_hz: float
        - hf_padding_db: float
        - dip_db: float
        - flatness_db: float
        - xo_vs_fc_ratio: float
        - system_response: np.ndarray
        - all_results: List of Dict with all tested frequencies

    Example:
        >>> result = optimize_crossover_frequency(
        ...     "BC_12FW88",
        ...     "BC_DH450",
        ...     {"Vb": 0.1145, "Fb": 47.6},
        ...     horn_fc_hz=468,
        ...     xo_range_hz=(600, 1200)
        ... )
        >>> print(f"Optimal XO: {result['optimal_xo_hz']:.0f} Hz")
        >>> print(f"XO/Fc ratio: {result['xo_vs_fc_ratio']:.2f}")
    """
    from gsd.driver import load_driver
    from gsd.enclosure.ported_box import calculate_spl_ported_transfer_function

    # Load drivers
    lf_driver = load_driver(lf_driver_name)

    # Generate frequency array
    freq = np.logspace(np.log10(20), np.log10(20000), 500)

    # Calculate LF response
    lf_response = np.array([
        calculate_spl_ported_transfer_function(
            f, lf_driver,
            lf_enclosure_params["Vb"],
            lf_enclosure_params["Fb"]
        )
        for f in freq
    ])

    # Calculate HF response
    hf_response = calculate_hf_horn_response(freq, horn_fc_hz)

    # Sweep crossover frequencies
    results = []

    for xo_freq in np.arange(xo_range_hz[0], xo_range_hz[1] + step_hz, step_hz):
        # Optimize HF padding
        try:
            hf_pad = optimize_hf_padding_for_flatness(
                lf_driver_name=lf_driver_name,
                hf_driver_name=hf_driver_name,
                lf_enclosure_type="ported",
                lf_enclosure_params=lf_enclosure_params,
                horn_params={"cutoff": horn_fc_hz, "length": horn_length_cm / 100},
                crossover_frequency=xo_freq,
                padding_range=(-25, -10),
                num_steps=16
            )
        except:
            hf_pad = -16.0

        # Calculate system response
        lp_gain_db, hp_gain_db = calculate_lr4_crossover_gains(freq, xo_freq)
        lf_combined = lf_response + lp_gain_db
        hf_combined = (hf_response + hf_pad) + hp_gain_db
        system_response = 10 * np.log10(10**(lf_combined/10) + 10**(hf_combined/10))

        # Calculate metrics
        flatness = calculate_system_flatness(freq, system_response)

        # Dip in crossover region
        xo_region = (freq >= xo_freq/2) & (freq <= xo_freq*2)
        xo_spl = system_response[xo_region]
        dip = np.max(xo_spl) - np.min(xo_spl)

        results.append({
            'xo_freq': xo_freq,
            'hf_pad': hf_pad,
            'flatness': flatness,
            'dip': dip,
            'xo_vs_fc_ratio': xo_freq / horn_fc_hz,
            'system_response': system_response
        })

    # Sort by dip (primary), then flatness (secondary)
    results_sorted = sorted(results, key=lambda x: (x['dip'], x['flatness']))
    best = results_sorted[0]

    return {
        'optimal_xo_hz': best['xo_freq'],
        'hf_padding_db': best['hf_pad'],
        'dip_db': best['dip'],
        'flatness_db': best['flatness'],
        'xo_vs_fc_ratio': best['xo_vs_fc_ratio'],
        'system_response': best['system_response'],
        'all_results': results
    }
```

---

### 3. Integrated Design Function

**Add to:** `src/gsd/optimization/api/two_way_system.py`

```python
def design_two_way_system_integrated(
    lf_driver_name: str,
    hf_driver_name: str,
    target_crossover_hz: float,
    printer_constraints: Dict[str, float],
    enclosure_type: str = "ported",
    xo_fc_ratio: float = 2.0,
    accept_sensitivity_loss: bool = False,
    verbose: bool = True
) -> TwoWaySystemDesign:
    """
    Complete two-way system design with integrated optimization.

    This function considers horn geometry and crossover as an integrated system,
    working backwards from the target crossover frequency to determine required
    horn parameters, then optimizing the complete system.

    Workflow:
    1. Analyze LF driver (beaming frequency)
    2. Design LF enclosure
    3. Calculate target horn Fc from XO target
    4. Calculate required mouth area for target Fc
    5. Check feasibility against printer constraints
    6. Optimize horn geometry
    7. Optimize crossover frequency (sweep, don't assume 2×Fc)
    8. Validate complete system

    Args:
        lf_driver_name: Low-frequency driver name
        hf_driver_name: High-frequency driver name
        target_crossover_hz: Target crossover frequency (Hz)
        printer_constraints: {
            "max_length": 0.25,  # meters
            "max_mouth_area": 0.0625,  # m² (250mm × 250mm)
        }
        enclosure_type: "ported" or "sealed"
        xo_fc_ratio: Desired XO/Fc ratio (default 2.0, use 1.3 for optimized)
        accept_sensitivity_loss: If True, use smaller mouth if needed
        verbose: Print progress messages

    Returns:
        TwoWaySystemDesign with complete system design

    Example:
        >>> design = design_two_way_system_integrated(
        ...     lf_driver_name="BC_12FW88",
        ...     hf_driver_name="BC_DH450",
        ...     target_crossover_hz=800,
        ...     printer_constraints={"max_length": 0.25, "max_mouth_area": 0.0625},
        ...     xo_fc_ratio=2.0,
        ...     accept_sensitivity_loss=True
        ... )
        >>> print(f"Horn Fc: {design.horn_fc_hz:.0f} Hz")
        >>> print(f"Actual XO: {design.crossover_frequency_hz:.0f} Hz")
        >>> print(f"Dip: {design.dip_db:.2f} dB")
    """
    from gsd.driver import load_driver
    from gsd.optimization.api.design_assistant import DesignAssistant
    from gsd.optimization.api.horn_physics import (
        calculate_lf_beaming_frequency,
        calculate_target_horn_fc,
        calculate_mouth_area_for_fc,
        assess_mouth_area_feasibility,
        optimize_crossover_frequency
    )

    if verbose:
        print("\n" + "=" * 70)
        print("INTEGRATED TWO-WAY SYSTEM DESIGN")
        print("=" * 70)

    # Load drivers
    lf_driver = load_driver(lf_driver_name)
    hf_driver = load_driver(hf_driver_name)

    # ========================================================================
    # STEP 1: LF Driver Analysis
    # ========================================================================

    if verbose:
        print("\nStep 1: LF Driver Analysis")

    f_beam = calculate_lf_beaming_frequency(lf_driver)

    if verbose:
        print(f"  LF beaming frequency: {f_beam:.0f} Hz")

    # Adjust target XO if needed (cap at 0.8×beaming)
    adjusted_xo = min(target_crossover_hz, 0.8 * f_beam)

    if adjusted_xo < target_crossover_hz:
        if verbose:
            print(f"  ⚠ Target XO ({target_crossover_hz}Hz) > 0.8×beaming")
            print(f"  → Adjusting to {adjusted_xo:.0f} Hz")

    # ========================================================================
    # STEP 2: LF Enclosure Design
    # ========================================================================

    if verbose:
        print("\nStep 2: LF Enclosure Design")

    assistant = DesignAssistant(validation_mode=False)

    lf_result = assistant.optimize_design(
        driver_name=lf_driver_name,
        enclosure_type=enclosure_type,
        objectives=["f3", "flatness"],
        population_size=50,
        generations=50
    )

    if not lf_result.success:
        raise ValueError(f"LF enclosure optimization failed: {lf_result.warnings}")

    lf_params = lf_result.best_designs[0]['parameters']

    if verbose:
        print(f"  Vb = {lf_params['Vb']*1000:.1f} L")
        print(f"  Fb = {lf_params['Fb']:.1f} Hz")

    # ========================================================================
    # STEP 3: Horn Requirements
    # ========================================================================

    if verbose:
        print("\nStep 3: Horn Requirements")

    target_fc = calculate_target_horn_fc(
        adjusted_xo,
        f_beam,
        xo_fc_ratio
    )

    max_length = printer_constraints.get("max_length", 0.3)
    max_mouth_area = printer_constraints.get("max_mouth_area", 0.1)

    # Assume throat area from HF driver
    throat_area = hf_driver.S_d  # Typically 7cm² for DH450

    required_mouth = calculate_mouth_area_for_fc(
        throat_area * 10000,  # m² to cm²
        max_length * 100,  # m to cm
        target_fc
    )

    if verbose:
        print(f"  Target XO: {adjusted_xo:.0f} Hz")
        print(f"  Target Fc: {target_fc:.0f} Hz (XO/Fc = {adjusted_xo/target_fc:.2f})")
        print(f"  Required mouth: {required_mouth:.0f} cm²")
        print(f"  Available mouth: {max_mouth_area*10000:.0f} cm²")

    # ========================================================================
    # STEP 4: Feasibility Check
    # ========================================================================

    if verbose:
        print("\nStep 4: Feasibility Check")

    feasibility = assess_mouth_area_feasibility(
        required_mouth,
        max_mouth_area * 10000,
        target_fc,
        throat_area * 10000,
        max_length * 100
    )

    if not feasibility['feasible']:
        if verbose:
            print(feasibility['recommendation'])

        if not accept_sensitivity_loss:
            raise ValueError(
                f"Required mouth ({required_mouth:.0f}cm²) exceeds constraint. "
                f"Set accept_sensitivity_loss=True to proceed with smaller mouth."
            )

        # Use max available mouth
        design_mouth = max_mouth_area * 10000
    else:
        design_mouth = required_mouth

    if verbose:
        print(f"  Design mouth: {design_mouth:.0f} cm²")

    # ========================================================================
    # STEP 5: Horn Optimization
    # ========================================================================

    if verbose:
        print("\nStep 5: Horn Optimization")

    horn_constraints = {
        "max_length": max_length,
        "max_mouth_area": design_mouth / 10000  # cm² to m²
    }

    horn_result = assistant.optimize_design(
        driver_name=hf_driver_name,
        enclosure_type="multisegment_horn",
        objectives=["flatness", "wavefront_sphericity"],
        constraints=horn_constraints,
        population_size=50,
        generations=50,
        num_segments=2
    )

    if not horn_result.success:
        raise ValueError(f"Horn optimization failed: {horn_result.warnings}")

    horn_params = horn_result.best_designs[0]['parameters']

    # Calculate actual horn Fc
    actual_fc = calculate_fc_from_mouth(
        horn_params['throat_area'] * 10000,
        horn_params['mouth_area'] * 10000,
        horn_params['length1'] * 100 + horn_params['length2'] * 100
    )

    if verbose:
        print(f"  Throat: {horn_params['throat_area']*10000:.1f} cm²")
        print(f"  Mouth: {horn_params['mouth_area']*10000:.0f} cm²")
        print(f"  Length: {(horn_params['length1'] + horn_params['length2'])*100:.0f} cm")
        print(f"  Actual Fc: {actual_fc:.0f} Hz")

    # ========================================================================
    # STEP 6: Crossover Optimization
    # ========================================================================

    if verbose:
        print("\nStep 6: Crossover Optimization")

    xo_result = optimize_crossover_frequency(
        lf_driver_name=lf_driver_name,
        hf_driver_name=hf_driver_name,
        lf_enclosure_params={"Vb": lf_params['Vb'], "Fb": lf_params['Fb']},
        horn_fc_hz=actual_fc,
        horn_length_cm=(horn_params['length1'] + horn_params['length2']) * 100,
        xo_range_hz=(max(600, int(actual_fc * 1.2)), int(adjusted_xo * 1.5))
    )

    if verbose:
        print(f"  Optimal XO: {xo_result['optimal_xo_hz']:.0f} Hz")
        print(f"  XO/Fc ratio: {xo_result['xo_vs_fc_ratio']:.2f}")
        print(f"  HF padding: {xo_result['hf_padding_db']:.1f} dB")
        print(f"  Dip: {xo_result['dip_db']:.2f} dB")
        print(f"  Flatness: {xo_result['flatness_db']:.2f} dB")

    # ========================================================================
    # STEP 7: Validation
    # ========================================================================

    if verbose:
        print("\nStep 7: Validation")

    # Rate the design
    if xo_result['dip_db'] < 1.5:
        rating = "✅ Excellent"
    elif xo_result['dip_db'] < 2.5:
        rating = "✅ Good"
    elif xo_result['dip_db'] < 4:
        rating = "⚠️ Acceptable"
    else:
        rating = "❌ Poor"

    if verbose:
        print(f"  Rating: {rating}")

    # Construct result
    design = TwoWaySystemDesign(
        lf_driver_name=lf_driver_name,
        hf_driver_name=hf_driver_name,
        lf_enclosure_params=lf_params,
        hf_horn_params=horn_params,
        crossover_frequency_hz=xo_result['optimal_xo_hz'],
        hf_padding_db=xo_result['hf_padding_db'],
        system_response=xo_result['system_response'],
        dip_db=xo_result['dip_db'],
        flatness_db=xo_result['flatness_db'],
        horn_fc_hz=actual_fc,
        lf_beaming_frequency_hz=f_beam,
        validation={
            "passes": xo_result['dip_db'] < 4,
            "rating": rating,
            "recommendations": [] if xo_result['dip_db'] < 4 else ["Consider multi-piece horn"]
        }
    )

    return design
```

---

## File Changes Summary

### New Files to Create

1. **`src/gsd/optimization/api/horn_physics.py`**
   - `calculate_lf_beaming_frequency()`
   - `calculate_target_horn_fc()`
   - `calculate_mouth_area_for_fc()`
   - `calculate_fc_from_mouth()`
   - `assess_mouth_area_feasibility()`

2. **`docs/two_way_design_guide.md`** (USER GUIDE)
   - Physics background
   - Step-by-step workflow
   - Decision trees
   - Case studies

### Files to Modify

1. **`src/gsd/optimization/api/two_way_system.py`**
   - Add `optimize_crossover_frequency()`
   - Add `design_two_way_system_integrated()`
   - Update docstrings

2. **`examples/complete_two_way_workflow.py`**
   - Update to use new `design_two_way_system_integrated()`
   - Add physics-first approach example

3. **`docs/two_way_design_review_12fw88_dh450.md`**
   - Already created ✓

---

## Testing Plan

### Unit Tests

Create `tests/optimization/api/test_horn_physics.py`:

```python
def test_calculate_lf_beaming_frequency():
    driver = load_driver("BC_12FW88")
    f_beam = calculate_lf_beaming_frequency(driver)
    assert 800 < f_beam < 900  # Should be ~840Hz

def test_calculate_mouth_area_for_fc():
    mouth = calculate_mouth_area_for_fc(7.0, 25.0, 400)
    assert 270 < mouth < 280  # Should be ~273cm²

def test_calculate_fc_from_mouth():
    fc = calculate_fc_from_mouth(7.0, 250.0, 25.0)
    assert 380 < fc < 400  # Should be ~390Hz

def test_round_trip():
    # Verify inverse functions agree
    fc1 = 400
    mouth = calculate_mouth_area_for_fc(7.0, 25.0, fc1)
    fc2 = calculate_fc_from_mouth(7.0, mouth, 25.0)
    assert abs(fc1 - fc2) < 1  # Within 1Hz
```

### Integration Tests

Create `tests/integration/test_integrated_two_way_design.py`:

```python
def test_integrated_design_12fw88_dh450():
    design = design_two_way_system_integrated(
        lf_driver_name="BC_12FW88",
        hf_driver_name="BC_DH450",
        target_crossover_hz=800,
        printer_constraints={"max_length": 0.25, "max_mouth_area": 0.0625},
        accept_sensitivity_loss=True
    )
    assert design.dip_db < 4  # Should be <4dB
    assert design.horn_fc_hz < 500  # Should be <500Hz
    assert 600 < design.crossover_frequency_hz < 900  # Should be 600-900Hz
```

---

## Documentation Updates

### Update CLAUDE.md

Add to project instructions:

```markdown
## Two-Way System Design

When designing two-way systems with horn-loaded HF drivers:

1. **ALWAYS check LF driver beaming frequency** - XO must be <~0.8×f_beam
2. **Calculate target Fc from XO target BEFORE designing horn**
3. **Check mouth area feasibility** - don't assume preset works
4. **Optimize XO by sweep** - don't assume 2×Fc is optimal
5. **Use integrated design function** - `design_two_way_system_integrated()`

**Physics:**
- Horn Fc = (c/4π) × (1/L) × ln(mouth/throat)
- For fixed L, small mouth changes = large Fc changes
- Trade-off: HF sensitivity vs crossover integration

**Common Pitfall:** Designing LF and HF independently, then trying to make crossover work.
**Solution:** Use `design_two_way_system_integrated()` from start.
```

---

## Priority Implementation Order

### Phase 1: Critical Path (Week 1)
1. Create `horn_physics.py` with physics functions
2. Add unit tests for physics functions
3. Add `optimize_crossover_frequency()` to `two_way_system.py`
4. Test with BC 12FW88 + DH450 case

### Phase 2: Integration (Week 2)
1. Add `design_two_way_system_integrated()`
2. Add integration tests
3. Update example workflow
4. Update documentation

### Phase 3: Polish (Week 3)
1. Add decision tree helper
2. Add trade-off analysis
3. Add more case studies
4. Create user guide

---

## Success Criteria

The implementation is successful when:

1. ✅ Can design BC 12FW88 + DH450 system in ONE call
2. ✅ Result has dip < 4dB (acceptable) or < 2.5dB (good)
3. ✅ Function warns about trade-offs before optimizing
4. ✅ User can specify priorities (sensitivity vs flatness)
5. ✅ All functions have unit tests
6. ✅ Documentation is clear with examples
7. ✅ Works for other driver combinations (test with 2-3 cases)
