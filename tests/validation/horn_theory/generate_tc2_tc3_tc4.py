#!/usr/bin/env python3
"""
Generate Hornresp export files for TC2-4 validation test cases.

Creates Hornresp .txt files for front-loaded horn validation:
- TC2: Driver + Horn (no chambers)
- TC3: Driver + Horn + Throat Chamber
- TC4: Driver + Horn + Both Chambers

Usage:
    python generate_tc2_tc3_tc4.py
"""

import math
from pathlib import Path


def generate_hornresp_horn_file(
    output_path: str,
    driver_name: str,
    comment: str,
    Sd_cm2: float,
    Bl: float,
    Cms: float,
    Rms: float,
    Mmd_g: float,
    Le_mH: float,
    Re_ohm: float,
    S1_cm2: float,
    S2_cm2: float,
    L12_m: float,
    Vtc_liters: float = 0.0,
    Atc_cm2: float = None,
    Vrc_liters: float = 0.0,
):
    """
    Generate Hornresp input file for front-loaded horn system.

    Parameters:
        output_path: Path to output .txt file
        driver_name: Name/identifier for the driver
        comment: Description/comment
        Sd_cm2: Diaphragm area [cm²]
        Bl: Force factor [T·m]
        Cms: Compliance [m/N]
        Rms: Mechanical resistance [N·s/m]
        Mmd_g: Driver mass [g] (M_md only, no radiation mass)
        Le_mH: Inductance [mH]
        Re_ohm: DC resistance [Ω]
        S1_cm2: Throat area [cm²]
        S2_cm2: Mouth area [cm²]
        L12_m: Horn length [m]
        Vtc_liters: Throat chamber volume [L]
        Atc_cm2: Throat chamber area [cm²] (defaults to S1 if not specified)
        Vrc_liters: Rear chamber volume [L]
    """

    # Default throat chamber area equals throat area
    if Atc_cm2 is None:
        Atc_cm2 = S1_cm2

    # Format Cms in scientific notation with exactly 2 decimal places
    cms_formatted = f"{Cms:.2E}"

    # Calculate rear chamber depth if Vrc > 0
    # Hornresp requires Lrc > 0 for sealed rear chamber
    if Vrc_liters > 0:
        # Vrc [L] = Vrc_cm³ / 1000
        # Vrc_cm³ = Lrc_cm × Area_cm²
        # Assume chamber area is 10× diaphragm area
        chamber_area_cm2 = Sd_cm2 * 10
        vrc_cm3 = Vrc_liters * 1000.0
        lrc_cm = vrc_cm3 / chamber_area_cm2
    else:
        lrc_cm = 0.0

    # Hornresp format requires CRLF line endings
    lines = [
        f"{comment}",
        "",
        "|TRADITIONAL DRIVER PARAMETER VALUES:",
        "",
        f"Sd = {Sd_cm2:.2f}",
        f"Bl = {Bl:.2f}",
        f"Cms = {cms_formatted}",
        f"Rms = {Rms:.2f}",
        f"Mmd = {Mmd_g:.2f}",
        f"Le = {Le_mH:.2f}",
        f"Re = {Re_ohm:.2f}",
        "Nd = 1",
        "",
        "|LOUDSPEAKER ENCLOSURE OR HORN-LOADED SYSTEM PARAMETERS:",
        "",
        # Horn parameters
        f"S1 = {S1_cm2:.2f}",
        f"S2 = {S2_cm2:.2f}",
        f"L12 = {L12_m:.3f}",
        f"Vtc = {Vtc_liters:.4f}",
        f"Atc = {Atc_cm2:.2f}",
        f"Vrc = {Vrc_liters:.4f}",
        f"Lrc = {lrc_cm:.4f}",
        # No port (front-loaded horn)
        "Ap = 0.00",
        "Lpt = 0.00",
        "Fr = 0.00",
        # Radiation angle (2π for half-space)
        "Ang = 2.00 * Pi",
        # Throat/segment parameters (not used for simple exponential horn)
        "Vtc = 0.0000",
        "Atc = 0.00",
        # Rear chamber
        "Vrc = 0.0000",
        "Lrc = 0.00",
        # Additional parameters
        "ta = 0.00",
        "tb = 0.00",
        "tc = 0.00",
        "td = 0.00",
        "te = 0.00",
        "tf = 0.00",
        "tg = 0.00",
        "th = 0.00",
        # Input parameters
        "Input Parameters = 1.00 100.00 10.00 0.00",
        # Chart settings
        "Chart = 0.00",
        # Material properties (default air)
        "Eg = 2.83",
        "Rg = 0.00",
        "Pt = 1.00",
        "Ngc = 0",
        "Th = 293.2",
        "Pb = 101325.0",
        "Ro = 1.205",
        "B = 344.0",
        "Sp = 0.00",
        "Sd = 0.00",
    ]

    # Join with CRLF line endings (Hornresp requirement)
    content = "\r\n".join(lines)

    # Write to file
    Path(output_path).write_text(content)

    return output_path


def create_compression_driver_params():
    """Return compression driver parameters (B&C DE10-style)."""
    return {
        'Sd_cm2': 8.0,      # 8 cm² diaphragm area
        'Bl': 12.0,         # 12 T·m force factor
        'Cms': 5.0e-5,      # 0.05 mm/N compliance
        'Rms': 3.0,         # 3 N·s/m mechanical resistance
        'Mmd_g': 8.0,       # 8g driver mass (M_md only)
        'Le_mH': 0.1,       # 0.1 mH inductance
        'Re_ohm': 6.5,      # 6.5 Ω DC resistance
    }


def generate_tc2():
    """Generate TC2: Driver + Horn (no chambers)."""
    driver = create_compression_driver_params()

    # Horn parameters
    S1_cm2 = 5.0      # Throat area: 5 cm²
    S2_cm2 = 200.0    # Mouth area: 200 cm² (40:1 expansion)
    L12_m = 0.5       # Horn length: 50 cm

    output_path = Path(__file__).parent / "exp_midrange_tc2" / "horn_params.txt"

    generate_hornresp_horn_file(
        output_path=str(output_path),
        driver_name="Compression_Driver_TC2",
        comment="TC2: Driver + Horn (Vtc=0, Vrc=0) - No chambers",
        Sd_cm2=driver['Sd_cm2'],
        Bl=driver['Bl'],
        Cms=driver['Cms'],
        Rms=driver['Rms'],
        Mmd_g=driver['Mmd_g'],
        Le_mH=driver['Le_mH'],
        Re_ohm=driver['Re_ohm'],
        S1_cm2=S1_cm2,
        S2_cm2=S2_cm2,
        L12_m=L12_m,
        Vtc_liters=0.0,
        Atc_cm2=S1_cm2,
        Vrc_liters=0.0,
    )

    print(f"✓ Generated TC2: {output_path}")
    return output_path


def generate_tc3():
    """Generate TC3: Driver + Horn + Throat Chamber."""
    driver = create_compression_driver_params()

    # Horn parameters
    S1_cm2 = 5.0
    S2_cm2 = 200.0
    L12_m = 0.5

    # Throat chamber
    Vtc_liters = 0.5  # 0.5 liters

    output_path = Path(__file__).parent / "exp_midrange_tc3" / "horn_params.txt"

    generate_hornresp_horn_file(
        output_path=str(output_path),
        driver_name="Compression_Driver_TC3",
        comment="TC3: Driver + Horn + Throat Chamber (Vtc=0.5L, Vrc=0)",
        Sd_cm2=driver['Sd_cm2'],
        Bl=driver['Bl'],
        Cms=driver['Cms'],
        Rms=driver['Rms'],
        Mmd_g=driver['Mmd_g'],
        Le_mH=driver['Le_mH'],
        Re_ohm=driver['Re_ohm'],
        S1_cm2=S1_cm2,
        S2_cm2=S2_cm2,
        L12_m=L12_m,
        Vtc_liters=Vtc_liters,
        Atc_cm2=S1_cm2,
        Vrc_liters=0.0,
    )

    print(f"✓ Generated TC3: {output_path}")
    return output_path


def generate_tc4():
    """Generate TC4: Driver + Horn + Both Chambers."""
    driver = create_compression_driver_params()

    # Horn parameters
    S1_cm2 = 5.0
    S2_cm2 = 200.0
    L12_m = 0.5

    # Both chambers
    Vtc_liters = 0.5  # 0.5 liters throat chamber
    Vrc_liters = 2.0  # 2.0 liters rear chamber

    output_path = Path(__file__).parent / "exp_midrange_tc4" / "horn_params.txt"

    generate_hornresp_horn_file(
        output_path=str(output_path),
        driver_name="Compression_Driver_TC4",
        comment="TC4: Driver + Horn + Both Chambers (Vtc=0.5L, Vrc=2.0L)",
        Sd_cm2=driver['Sd_cm2'],
        Bl=driver['Bl'],
        Cms=driver['Cms'],
        Rms=driver['Rms'],
        Mmd_g=driver['Mmd_g'],
        Le_mH=driver['Le_mH'],
        Re_ohm=driver['Re_ohm'],
        S1_cm2=S1_cm2,
        S2_cm2=S2_cm2,
        L12_m=L12_m,
        Vtc_liters=Vtc_liters,
        Atc_cm2=S1_cm2,
        Vrc_liters=Vrc_liters,
    )

    print(f"✓ Generated TC4: {output_path}")
    return output_path


def create_readmes():
    """Create README.md files for each test case."""
    tc2_readme = """# Test Case 2: Driver + Horn (No Chambers)

## Purpose
Validate horn driver integration without throat or rear chambers.

## System Configuration
- **Driver**: Compression driver (B&C DE10-style)
  - S_d: 8 cm²
  - M_md: 8g
  - BL: 12 T·m
  - R_e: 6.5 Ω
  - F_s: ~1.2 kHz

- **Horn**: Exponential
  - Throat area (S1): 5 cm²
  - Mouth area (S2): 200 cm²
  - Length (L12): 50 cm
  - Expansion ratio: 40:1
  - Flare constant: ~11.5 1/m
  - Cutoff frequency: ~630 Hz

- **Chambers**: None
  - Vtc = 0 (no throat chamber)
  - Vrc = 0 (no rear chamber, open back)

## Validation Goals
1. Electrical impedance matches Hornresp (<2% magnitude, <5° phase)
2. Diaphragm velocity is physically realistic
3. Horn loading effect is visible in impedance
4. Cutoff frequency behavior matches theory

## Expected Results
- Impedance peak near driver resonance (~1.2 kHz)
- Horn loading reduces impedance above cutoff (~630 Hz)
- No chamber-related resonances
- Smooth impedance curve above cutoff

## Files
- `horn_params.txt` - Hornresp input file (import this)
- `sim.txt` - Hornresp simulation results (run Hornresp to generate)
- `README.md` - This file

## Hornresp Setup
1. Import `horn_params.txt` into Hornresp
2. Set frequency range: 10 Hz - 10 kHz, 10 points/octave
3. Export Electrical Impedance
4. Export Acoustical Impedance
5. Save as `sim.txt`

## Viberesp Validation
Run:
```python
from gsd.simulation import ExponentialHorn
from gsd.enclosure.front_loaded_horn import FrontLoadedHorn
from gsd.driver.parameters import ThieleSmallParameters

driver = ThieleSmallParameters(
    M_md=0.008, C_ms=5e-5, R_ms=3.0,
    R_e=6.5, L_e=0.1e-3, BL=12.0, S_d=0.0008,
)

horn = ExponentialHorn(throat_area=0.0005, mouth_area=0.02, length=0.5)
flh = FrontLoadedHorn(driver, horn)

result = flh.electrical_impedance(1000)  # Test at 1 kHz
```
"""

    tc3_readme = """# Test Case 3: Driver + Horn + Throat Chamber

## Purpose
Validate throat chamber compliance effect on horn-loaded driver.

## System Configuration
- **Driver**: Compression driver (B&C DE10-style)
  - S_d: 8 cm²
  - M_md: 8g
  - BL: 12 T·m
  - R_e: 6.5 Ω

- **Horn**: Exponential
  - Throat area (S1): 5 cm²
  - Mouth area (S2): 200 cm²
  - Length (L12): 50 cm
  - Cutoff frequency: ~630 Hz

- **Throat Chamber**: 0.5 liters
  - Vtc: 0.5 L
  - Atc: 5 cm² (equals throat area)

- **Rear Chamber**: None
  - Vrc = 0 (open back)

## Validation Goals
1. Throat chamber adds series compliance to horn impedance
2. Electrical impedance shows chamber-related effects
3. Comparison with TC2 shows throat chamber impact
4. Compliance resonance is visible

## Expected Results
- Throat chamber creates additional compliance
- Impedance shifts compared to TC2
- Possible resonance from throat chamber compliance
- Lower frequency resonance due to added compliance

## Files
- `horn_params.txt` - Hornresp input file (import this)
- `sim.txt` - Hornresp simulation results (run Hornresp to generate)
- `README.md` - This file

## Hornresp Setup
1. Import `horn_params.txt` into Hornresp
2. Set frequency range: 10 Hz - 10 kHz, 10 points/octave
3. Export Electrical Impedance
4. Export Acoustical Impedance
5. Save as `sim.txt`
"""

    tc4_readme = """# Test Case 4: Driver + Horn + Both Chambers

## Purpose
Validate complete front-loaded horn system with both throat and rear chambers.

## System Configuration
- **Driver**: Compression driver (B&C DE10-style)
  - S_d: 8 cm²
  - M_md: 8g
  - BL: 12 T·m
  - R_e: 6.5 Ω

- **Horn**: Exponential
  - Throat area (S1): 5 cm²
  - Mouth area (S2): 200 cm²
  - Length (L12): 50 cm
  - Cutoff frequency: ~630 Hz

- **Throat Chamber**: 0.5 liters
  - Vtc: 0.5 L
  - Atc: 5 cm²

- **Rear Chamber**: 2.0 liters
  - Vrc: 2.0 L (sealed box behind driver)

## Validation Goals
1. Complete system with both chambers
2. Throat chamber compliance (series element)
3. Rear chamber compliance (shunt element)
4. Full electromechanical chain validation
5. Complex interaction between compliances

## Expected Results
- Both chambers affect impedance
- Complex interaction between throat and rear compliances
- Multiple resonances possible
- System resonance lower than driver Fs

## Files
- `horn_params.txt` - Hornresp input file (import this)
- `sim.txt` - Hornresp simulation results (run Hornresp to generate)
- `README.md` - This file

## Hornresp Setup
1. Import `horn_params.txt` into Hornresp
2. Set frequency range: 10 Hz - 10 kHz, 10 points/octave
3. Export Electrical Impedance
4. Export Acoustical Impedance
5. Export SPL
6. Save as `sim.txt`
"""

    # Write README files
    readme_paths = [
        (Path(__file__).parent / "exp_midrange_tc2" / "README.md", tc2_readme),
        (Path(__file__).parent / "exp_midrange_tc3" / "README.md", tc3_readme),
        (Path(__file__).parent / "exp_midrange_tc4" / "README.md", tc4_readme),
    ]

    for path, content in readme_paths:
        path.write_text(content)
        print(f"✓ Created README: {path}")


def main():
    """Generate all test case files."""
    print("Generating Hornresp export files for TC2-4...")
    print()

    # Generate Hornresp export files
    generate_tc2()
    generate_tc3()
    generate_tc4()

    print()

    # Create README files
    create_readmes()

    print()
    print("=" * 70)
    print("✓ All files generated successfully!")
    print()
    print("Next steps:")
    print("1. Import each horn_params.txt into Hornresp (File → Import)")
    print("2. Run simulations (10 Hz - 10 kHz, 10 points/octave)")
    print("3. Export results:")
    print("   - Electrical Impedance")
    print("   - Acoustical Impedance")
    print("   - SPL (for TC4)")
    print("4. Save as sim.txt in each test case directory")
    print("5. Run validation scripts to compare with viberesp")
    print("=" * 70)


if __name__ == "__main__":
    main()
