"""
Hornresp simulation results parser.

This module parses Hornresp simulation output files (_sim.txt) and extracts
the frequency response data for validation against gsd calculations.

Literature:
- Hornresp manual: http://www.hornresp.net/
"""

from dataclasses import dataclass
from pathlib import Path
import numpy as np
from typing import Dict, Any


@dataclass
class HornrespSimulationResult:
    """
    Hornresp simulation result data structure.

    Contains all columns from Hornresp's tab-separated output format.
    All arrays are numpy arrays for efficient numerical operations.

    Attributes:
        frequency: Frequency in Hz
        ra_norm: Normalized radiation resistance (dimensionless)
        xa_norm: Normalized radiation reactance (dimensionless)
        za_norm: Normalized radiation impedance magnitude (dimensionless)
        spl_db: Sound pressure level in dB (at 1m for 2.83V input)
        ze_ohms: Electrical impedance magnitude in ohms
        xd_mm: Diaphragm displacement in mm
        wphase_deg: Phase angle in degrees (W parameter)
        uphase_deg: Phase angle in degrees (U parameter)
        cphase_deg: Phase angle in degrees (C parameter)
        delay_msec: Time delay in milliseconds
        efficiency_percent: Efficiency in percent
        ein_volts: Input voltage in volts
        pin_watts: Input power in watts
        iin_amps: Input current in amps
        zephase_deg: Electrical impedance phase in degrees
        metadata: Additional metadata extracted from the file
    """

    frequency: np.ndarray
    ra_norm: np.ndarray
    xa_norm: np.ndarray
    za_norm: np.ndarray
    spl_db: np.ndarray
    ze_ohms: np.ndarray
    xd_mm: np.ndarray
    wphase_deg: np.ndarray
    uphase_deg: np.ndarray
    cphase_deg: np.ndarray
    delay_msec: np.ndarray
    efficiency_percent: np.ndarray
    ein_volts: np.ndarray
    pin_watts: np.ndarray
    iin_amps: np.ndarray
    zephase_deg: np.ndarray
    metadata: Dict[str, Any]

    def __len__(self) -> int:
        """Return the number of frequency points."""
        return len(self.frequency)

    def __getitem__(self, index):
        """
        Get a single frequency point by index.

        Returns a dictionary with all values at that index.
        """
        return {
            'frequency': self.frequency[index],
            'ra_norm': self.ra_norm[index],
            'xa_norm': self.xa_norm[index],
            'za_norm': self.za_norm[index],
            'spl_db': self.spl_db[index],
            'ze_ohms': self.ze_ohms[index],
            'xd_mm': self.xd_mm[index],
            'wphase_deg': self.wphase_deg[index],
            'uphase_deg': self.uphase_deg[index],
            'cphase_deg': self.cphase_deg[index],
            'delay_msec': self.delay_msec[index],
            'efficiency_percent': self.efficiency_percent[index],
            'ein_volts': self.ein_volts[index],
            'pin_watts': self.pin_watts[index],
            'iin_amps': self.iin_amps[index],
            'zephase_deg': self.zephase_deg[index],
        }


def _validate_parsed_data(
    frequency: np.ndarray,
    ze_ohms: np.ndarray,
    spl_db: np.ndarray,
    filepath: Path,
) -> None:
    """
    Validate that parsed Hornresp data looks reasonable.

    Performs sanity checks to catch parsing errors early:
    - Frequency should be positive and monotonically increasing
    - Impedance should be > DC resistance and < 1000 Ω
    - SPL should be in reasonable range (40-120 dB)

    Args:
        frequency: Parsed frequency array (Hz)
        ze_ohms: Parsed electrical impedance (Ω)
        spl_db: Parsed SPL values (dB)
        filepath: Path to file (for error messages)

    Raises:
        ValueError: If data fails validation checks
    """
    # Check frequency range
    if np.any(frequency <= 0):
        raise ValueError(
            f"Invalid frequency data in {filepath}: "
            f"frequency must be positive, got min={np.min(frequency)}"
        )

    if np.any(frequency[1:] <= frequency[:-1]):
        raise ValueError(
            f"Invalid frequency data in {filepath}: "
            f"frequency must be monotonically increasing"
        )

    # Check impedance range (should be > Re and < 1000 Ω for typical drivers)
    if np.any(ze_ohms <= 0):
        raise ValueError(
            f"Invalid impedance data in {filepath}: "
            f"impedance must be positive, got min={np.min(ze_ohms)} Ω"
        )

    if np.any(ze_ohms > 1000):
        # This might indicate reading wrong column (e.g., reading SPL dB instead of Ze)
        raise ValueError(
            f"Invalid impedance data in {filepath}: "
            f"impedance > 1000 Ω suggests parsing error. "
            f"Max Ze={np.max(ze_ohms)} Ω. "
            f"Check if columns are aligned correctly."
        )

    # Check SPL range (should be reasonable for typical systems at 1m, 2.83V)
    # Sealed boxes below resonance can have very low SPL (< 40 dB)
    # High-efficiency horns can have SPL > 120 dB
    # Only flag clearly unreasonable values
    if np.any(spl_db < 0) or np.any(spl_db > 150):
        raise ValueError(
            f"Invalid SPL data in {filepath}: "
            f"SPL out of reasonable range [0, 150] dB. "
            f"Min={np.min(spl_db):.1f} dB, Max={np.max(spl_db):.1f} dB. "
            f"This may indicate reading wrong column (SPL is column 5, index 4)."
        )


def load_hornresp_sim_file(filepath: str | Path) -> HornrespSimulationResult:
    """
    Load Hornresp simulation results from _sim.txt file.

    Hornresp outputs simulation results in a tab-separated format with
    the following columns:

    ┌─────────────────────────────────────────────────────────────────┐
    │ Hornresp _sim.txt File Format (tab-separated, 16 columns)      │
    ├─────────────────────────────────────────────────────────────────┤
    │ Col │ Index │ Name            │ Unit    │ Description           │
    ├─────┼───────┼─────────────────┼─────────┼───────────────────────┤
    │  1  │   0   │ Freq            │ hertz   │ Frequency             │
    │  2  │   1   │ Ra              │ norm    │ Radiation resistance │
    │  3  │   2   │ Xa              │ norm    │ Radiation reactance  │
    │  4  │   3   │ Za              │ norm    │ Rad. impedance mag.  │
    │  5  │   4   │ SPL             │ dB      │ Sound pressure level │
    │  6  │   5   │ Ze              │ ohms    │ Electrical impedance │
    │  7  │   6   │ Xd              │ mm      │ Diaphragm displac.   │
    │  8  │   7   │ WPhase          │ deg     │ W phase angle        │
    │  9  │   8   │ UPhase          │ deg     │ U phase angle        │
    │ 10  │   9   │ CPhase          │ deg     │ C phase angle        │
    │ 11  │  10   │ Delay           │ msec    │ Time delay           │
    │ 12  │  11   │ Efficiency      │ %       │ Acoustic efficiency   │
    │ 13  │  12   │ Ein             │ volts   │ Input voltage        │
    │ 14  │  13   │ Pin             │ watts   │ Input power          │
    │ 15  │  14   │ Iin             │ amps    │ Input current        │
    │ 16  │  15   │ ZePhase         │ deg     │ Ze phase angle       │
    └─────┴───────┴─────────────────┴─────────┴───────────────────────┘

    IMPORTANT: Column numbers above are 1-indexed (as shown in file).
    Array indices below are 0-indexed (Python standard).

    Example header line:
    Freq (hertz)	Ra (norm)	Xa (norm)	Za (norm)	SPL (dB)	Ze (ohms)	Xd (mm) 	WPhase (deg)	UPhase (deg)	CPhase (deg)	Delay (msec)	Efficiency (%)	Ein (volts)	Pin (watts)	Iin (amps)	ZePhase (deg)

    The file has:
    - Line 1: Header with column names (tab-separated)
    - Line 2: Blank
    - Line 3+: Data rows (tab-separated, 16 columns)

    Args:
        filepath: Path to _sim.txt file

    Returns:
        HornrespSimulationResult with all data loaded as numpy arrays

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid or cannot be parsed

    Examples:
        >>> result = load_hornresp_sim_file("bc_8ndl51_inf_sim.txt")
        >>> result.frequency[0]
        10.0  # First frequency point (column 1, index 0)
        >>> result.ze_ohms[100]
        42.5  # Electrical impedance at 100th point (column 6, index 5)
        >>> result.spl_db[50]
        85.3  # SPL at 50th point (column 5, index 4)
        >>> len(result)
        535  # Number of frequency points

        Accessing data by index:
        >>> point = result[0]
        >>> point['frequency']
        10.0
        >>> point['ze_ohms']
        5.39...

    Validation:
        - Verifies file has exactly 16 columns
        - Verifies all data can be parsed as floats
        - Provides helpful error messages with line numbers

    Literature:
        - Hornresp manual: http://www.hornresp.net/
        - File format specification in Hornresp help documentation
    """
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Hornresp simulation file not found: {filepath}")

    if not filepath.is_file():
        raise ValueError(f"Path is not a file: {filepath}")

    # Read all lines from file
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        raise IOError(f"Failed to read file {filepath}: {e}")

    if len(lines) < 3:
        raise ValueError(f"File too short: {filepath} (expected at least 3 lines, got {len(lines)})")

    # Parse data lines (skip header and blank line)
    data_lines = []
    for line in lines[2:]:  # Skip first 2 lines (header + blank)
        line = line.strip()
        if not line:  # Skip empty lines
            continue
        data_lines.append(line)

    if not data_lines:
        raise ValueError(f"No data found in file: {filepath}")

    # Parse each data line
    # Expected columns (tab-separated):
    # 0: Freq, 1: Ra, 2: Xa, 3: Za, 4: SPL, 5: Ze, 6: Xd,
    # 7: WPhase, 8: UPhase, 9: CPhase, 10: Delay, 11: Efficiency,
    # 12: Ein, 13: Pin, 14: Iin, 15: ZePhase
    # Total: 16 columns

    data = []
    for line_num, line in enumerate(data_lines, start=3):  # Line numbers start from file top
        try:
            values = line.split('\t')
            if len(values) != 16:
                raise ValueError(f"Expected 16 columns, got {len(values)}")

            # Convert to float
            row = [float(v) for v in values]
            data.append(row)

        except ValueError as e:
            raise ValueError(f"Failed to parse line {line_num}: {e}") from e

    # Convert to numpy arrays (transpose so each column is an array)
    data_array = np.array(data).T

    # Extract columns (0-indexed)
    # See table in docstring for column mapping
    frequency = data_array[0]
    ra_norm = data_array[1]
    xa_norm = data_array[2]
    za_norm = data_array[3]
    spl_db = data_array[4]
    ze_ohms = data_array[5]
    xd_mm = data_array[6]
    wphase_deg = data_array[7]
    uphase_deg = data_array[8]
    cphase_deg = data_array[9]
    delay_msec = data_array[10]
    efficiency_percent = data_array[11]
    ein_volts = data_array[12]
    pin_watts = data_array[13]
    iin_amps = data_array[14]
    zephase_deg = data_array[15]

    # Validate parsed data looks reasonable
    _validate_parsed_data(frequency, ze_ohms, spl_db, filepath)

    # Extract metadata from filename
    metadata = {
        'filepath': str(filepath.absolute()),
        'filename': filepath.name,
        'num_points': len(frequency),
        'freq_min': float(np.min(frequency)),
        'freq_max': float(np.max(frequency)),
        'input_voltage': float(ein_volts[0]) if len(ein_volts) > 0 else 2.83,
    }

    return HornrespSimulationResult(
        frequency=frequency,
        ra_norm=ra_norm,
        xa_norm=xa_norm,
        za_norm=za_norm,
        spl_db=spl_db,
        ze_ohms=ze_ohms,
        xd_mm=xd_mm,
        wphase_deg=wphase_deg,
        uphase_deg=uphase_deg,
        cphase_deg=cphase_deg,
        delay_msec=delay_msec,
        efficiency_percent=efficiency_percent,
        ein_volts=ein_volts,
        pin_watts=pin_watts,
        iin_amps=iin_amps,
        zephase_deg=zephase_deg,
        metadata=metadata,
    )
