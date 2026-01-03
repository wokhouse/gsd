"""
B&C Speakers driver fixtures for validation.

These fixtures represent real B&C drivers with complete Thiele-Small
parameters sourced from official datasheets. They are used for
validation against Hornresp.

Literature:
- B&C Speakers datasheets (official manufacturer specifications)
- Tests for Stage 1B: Bare Driver Model & Hornresp Export
"""

import pytest
from gsd.driver import load_driver


@pytest.fixture
def bc_8ndl51():
    """
    B&C 8NDL51-8 8" Midrange driver.

    Datasheet specifications:
    - Fs: 66 Hz
    - Re: 5.3 Ω
    - Qts: 0.37
    - Qes: 0.39
    - Qms: 4.5
    - Vas: 15 L
    - Sd: 215 cm²
    - BL: 7.5 T·m
    - Mms: 25 g
    - Cms: 0.24 mm/N
    - Rms: 2.3 N·s/m
    - Le: 0.5 mH

    Literature: B&C 8NDL51 datasheet
    """
    return load_driver("BC_8NDL51")


@pytest.fixture
def bc_12ndl76():
    """
    B&C 12NDL76-4 12" Mid-Woofer driver.

    Datasheet specifications:
    - Fs: 50 Hz
    - Re: 3.1 Ω
    - Qts: 0.19
    - Qes: 0.20
    - Qms: 3.25
    - Vas: 67 L
    - Sd: 522 cm²
    - BL: 16.5 T·m
    - Mms: 54 g
    - Cms: 0.19 mm/N
    - Rms: 5.2 N·s/m
    - Le: 0.72 mH

    Literature: B&C 12NDL76 datasheet
    """
    return load_driver("BC_12NDL76")


@pytest.fixture
def bc_15ds115():
    """
    B&C 15DS115-8 15" Subwoofer driver.

    Datasheet specifications:
    - Fs: 33 Hz
    - Re: 4.9 Ω
    - Qts: 0.17
    - Qes: 0.18
    - Qms: 4.2
    - Vas: 132 L
    - Sd: 860 cm²
    - BL: 18.5 T·m
    - Mms: 95 g
    - Cms: 0.25 mm/N
    - Rms: 4.7 N·s/m
    - Le: 1.2 mH

    Literature: B&C 15DS115 datasheet
    """
    return load_driver("BC_15DS115")


@pytest.fixture
def bc_18pzw100():
    """
    B&C 18PZW100-8 18" Subwoofer driver.

    Datasheet specifications:
    - Fs: 37 Hz
    - Re: 5.1 Ω
    - Qts: 0.36
    - Qes: 0.38
    - Qms: 6.5
    - Vas: 280 L
    - Sd: 1250 cm²
    - BL: 14.5 T·m
    - Mms: 155 g
    - Cms: 0.17 mm/N
    - Rms: 5.5 N·s/m
    - Le: 2.1 mH

    Literature: B&C 18PZW100 datasheet
    """
    return load_driver("BC_18PZW100")


@pytest.fixture
def all_bc_drivers():
    """Return all 4 B&C drivers as a list for batch testing."""
    return [
        load_driver("BC_8NDL51"),
        load_driver("BC_12NDL76"),
        load_driver("BC_15DS115"),
        load_driver("BC_18PZW100")
    ]
