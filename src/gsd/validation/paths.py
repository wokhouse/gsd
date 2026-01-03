"""
Path resolution utilities for validation data.

Provides functions to locate and load validation datasets,
mapping driver names to factory functions and resolving file paths.

Literature:
- ROADMAP Phase 5 - Validation framework
"""

import re
from pathlib import Path
from typing import Callable, Dict, Tuple

from gsd.driver.parameters import ThieleSmallParameters


def get_driver_factory(driver_name: str) -> Callable[[], ThieleSmallParameters]:
    """
    Map driver name to loader function.

    Args:
        driver_name: Driver name (e.g., "BC_8NDL51")

    Returns:
        Loader function that creates ThieleSmallParameters instance

    Raises:
        ValueError: If driver name not recognized

    Examples:
        >>> factory = get_driver_factory("BC_8NDL51")
        >>> driver = factory()
        >>> print(driver.F_s)
        75.0
    """
    from gsd.driver import load_driver

    # Normalize driver name (uppercase, remove spaces)
    normalized_name = driver_name.upper().strip()

    # Return a lambda that loads the driver
    def _load():
        return load_driver(normalized_name)

    return _load


def parse_config_path(config_path: str) -> Tuple[str, Dict[str, float]]:
    """
    Parse configuration path to extract enclosure type and parameters.

    Args:
        config_path: Configuration path (e.g., "sealed/Vb31.6L", "infinite_baffle",
                      "ported/Vb50L_Fb35Hz", "horn/exp_S10cm_S50cm")

    Returns:
        Tuple of (enclosure_type, parameters_dict):
        - enclosure_type: "infinite_baffle", "sealed", "ported", "horn"
        - parameters_dict: Dict of extracted parameters (e.g., {"Vb_L": 31.6})

    Raises:
        ValueError: If config_path format is invalid

    Examples:
        >>> parse_config_path("infinite_baffle")
        ('infinite_baffle', {})
        >>> parse_config_path("sealed/Vb31.6L")
        ('sealed', {'Vb_L': 31.6})
        >>> parse_config_path("ported/Vb50L_Fb35Hz")
        ('ported', {'Vb_L': 50.0, 'Fb_Hz': 35.0})
    """
    # Handle infinite_baffle (no parameters)
    if config_path == "infinite_baffle":
        return "infinite_baffle", {}

    # Split path into components
    parts = config_path.split("/")

    if len(parts) < 1:
        raise ValueError(f"Invalid config_path: {config_path}")

    # First part is enclosure type
    enclosure_type = parts[0]

    # Map short names to full names
    type_map = {
        "inf": "infinite_baffle",
        "infinite_baffle": "infinite_baffle",
        "sealed": "sealed",
        "sb": "sealed",
        "ported": "ported",
        "pb": "ported",
        "horn": "horn",
        "hn": "horn",
    }

    if enclosure_type not in type_map:
        raise ValueError(
            f"Unknown enclosure type: {enclosure_type}\n"
            f"Valid types: infinite_baffle, sealed, ported, horn"
        )

    enclosure_type = type_map[enclosure_type]
    params = {}

    # Parse parameters from remaining path components
    for part in parts[1:]:
        # Match patterns like "Vb31.6L", "Fb35Hz", "S10cm", etc.
        # Pattern: (key)(value)(unit)
        match = re.match(r"^([A-Za-z]+)([\d.]+)([A-Za-z]*)$", part)
        if not match:
            raise ValueError(f"Invalid path component: {part}")

        key, value, unit = match.groups()
        value = float(value)

        # Build parameter key with unit
        if unit:
            param_key = f"{key}_{unit}"
        else:
            param_key = key

        params[param_key] = value

    return enclosure_type, params


def get_config_directory(driver_name: str, config_path: str) -> Path:
    """
    Get the directory path for a driver's configuration.

    Args:
        driver_name: Driver name (e.g., "BC_8NDL51")
        config_path: Configuration path (e.g., "sealed/Vb31.6L", "infinite_baffle")

    Returns:
        Path to configuration directory containing metadata.json and sim.txt

    Raises:
        FileNotFoundError: If configuration directory doesn't exist

    Examples:
        >>> dir = get_config_directory("BC_8NDL51", "sealed/Vb31.6L")
        >>> dir.name
        'Vb31.6L'
        >>> (dir / "sim.txt").exists()
        True
    """
    # Convert driver name to lowercase for directory path
    driver_lower = driver_name.lower()

    # Construct base path
    # paths.py is at src/gsd/validation/paths.py, so go up 4 levels to repo root
    validation_base = Path(__file__).parent.parent.parent.parent / "tests" / "validation" / "drivers"

    # Build full path
    config_dir = validation_base / driver_lower / config_path

    if not config_dir.exists():
        raise FileNotFoundError(
            f"Configuration directory not found: {config_dir}\n"
            f"Run 'gsd validate list' to see available datasets"
        )

    return config_dir
