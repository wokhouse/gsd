"""
Driver loader for YAML-based driver definitions.

This module provides functions to load loudspeaker driver parameters
from YAML files, making it easy to add new drivers without modifying code.

Literature:
- Driver datasheets (manufacturer specifications)
"""

from pathlib import Path
from typing import Any

import yaml

from gsd.driver.parameters import ThieleSmallParameters


# Directory containing driver YAML files
_DATA_DIR = Path(__file__).parent / "data"


def load_driver(driver_name: str) -> ThieleSmallParameters:
    """
    Load a driver by name from YAML file.

    The driver name should match the YAML filename (without extension).
    For example, "BC_8NDL51" loads from "BC_8NDL51.yaml".

    Args:
        driver_name: Name of the driver to load (e.g., "BC_8NDL51", "TC2")

    Returns:
        ThieleSmallParameters: Driver parameters with calculated derived values

    Raises:
        FileNotFoundError: If driver YAML file does not exist
        ValueError: If YAML file is missing required fields or has invalid values

    Examples:
        >>> from gsd.driver import load_driver
        >>> driver = load_driver("BC_8NDL51")
        >>> driver.F_s
        75.0...  # Hz
        >>> driver.Q_ts
        0.57...
        >>> driver = load_driver("TC2")
        >>> driver.S_d
        0.0008  # m²
    """
    yaml_path = _DATA_DIR / f"{driver_name}.yaml"

    if not yaml_path.exists():
        available = _get_available_drivers()
        raise FileNotFoundError(
            f"Driver '{driver_name}' not found. "
            f"Available drivers: {', '.join(sorted(available))}"
        )

    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    # Validate and extract parameters
    if "parameters" not in data:
        raise ValueError(f"Driver '{driver_name}' missing required 'parameters' section")

    params = data["parameters"]

    # Check for required parameters
    required_params = ["M_md", "C_ms", "R_ms", "R_e", "L_e", "BL", "S_d"]
    missing_params = [p for p in required_params if p not in params]
    if missing_params:
        raise ValueError(
            f"Driver '{driver_name}' missing required parameters: {', '.join(missing_params)}"
        )

    # X_max is optional
    x_max = params.get("X_max", None)

    # throat_area_cm2 is optional (for compression drivers)
    # Extract from compression_driver section if available
    throat_area_cm2 = None
    if "compression_driver" in data:
        throat_area_m2 = data["compression_driver"].get("throat_area")
        if throat_area_m2 is not None:
            throat_area_cm2 = throat_area_m2 * 10000  # m² to cm²

    # Create ThieleSmallParameters (derived values calculated automatically)
    return ThieleSmallParameters(
        M_md=params["M_md"],
        C_ms=params["C_ms"],
        R_ms=params["R_ms"],
        R_e=params["R_e"],
        L_e=params["L_e"],
        BL=params["BL"],
        S_d=params["S_d"],
        X_max=x_max,
        throat_area_cm2=throat_area_cm2,
    )


def list_drivers() -> dict[str, str]:
    """
    List all available drivers as {name: description} dict.

    Returns:
        Dictionary mapping driver names to their descriptions

    Examples:
        >>> from gsd.driver import list_drivers
        >>> drivers = list_drivers()
        >>> for name, desc in drivers.items():
        ...     print(f"{name}: {desc}")
        BC_8NDL51: 8 inch Midrange driver
        BC_15DS115: 15 inch Subwoofer driver
        ...
    """
    drivers = {}

    for yaml_path in _DATA_DIR.glob("*.yaml"):
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)

        name = data.get("name", yaml_path.stem)
        description = data.get("description", "")
        drivers[name] = description

    return dict(sorted(drivers.items()))


def get_driver_info(driver_name: str) -> dict[str, Any]:
    """
    Get complete driver info including metadata from YAML.

    Returns the full YAML data including datasheet specifications,
    notes, and literature references.

    Args:
        driver_name: Name of the driver (e.g., "BC_8NDL51", "TC2")

    Returns:
        Dictionary with all driver information from YAML:
        - name: Driver identifier
        - manufacturer: Manufacturer name
        - model: Model number
        - description: Driver description
        - datasheet: Datasheet specifications (if available)
        - parameters: Physical parameters
        - notes: Notes and warnings
        - literature: Literature references

    Raises:
        FileNotFoundError: If driver YAML file does not exist

    Examples:
        >>> from gsd.driver import get_driver_info
        >>> info = get_driver_info("BC_8NDL51")
        >>> info["manufacturer"]
        'B&C Speakers'
        >>> info["datasheet"]["fs"]
        75
        >>> info["notes"][:50]
        'M_md is driver mass only (excludes radiation mass).'
    """
    yaml_path = _DATA_DIR / f"{driver_name}.yaml"

    if not yaml_path.exists():
        available = _get_available_drivers()
        raise FileNotFoundError(
            f"Driver '{driver_name}' not found. "
            f"Available drivers: {', '.join(sorted(available))}"
        )

    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    return data


def _get_available_drivers() -> set[str]:
    """Get set of available driver names from YAML files."""
    return {path.stem for path in _DATA_DIR.glob("*.yaml")}
