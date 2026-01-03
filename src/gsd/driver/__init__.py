"""bugworks GSD driver module.

Provides Thiele-Small parameter definitions for various loudspeaker drivers
loaded from YAML files, making it easy to add new drivers without modifying code.

Usage:
    >>> from gsd.driver import load_driver, list_drivers
    >>> # List available drivers
    >>> drivers = list_drivers()
    >>> # Load a specific driver
    >>> driver = load_driver("BC_8NDL51")
    >>> driver.F_s
    75.0...
"""

from gsd.driver.loader import get_driver_info, load_driver, list_drivers

__all__ = [
    "load_driver",
    "list_drivers",
    "get_driver_info",
]
