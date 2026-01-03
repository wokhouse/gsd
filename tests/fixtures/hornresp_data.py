"""
Test fixtures for Hornresp reference data.

This module provides fixtures for loading Hornresp test data
for validation. Test cases will be added as they are created.

Literature:
- ROADMAP Phase 5 - Validation framework
- Implementation plan Stage 0-6
"""

import numpy as np
import pytest


@pytest.fixture
def standard_air_conditions():
    """
    Standard air conditions for testing.

    Returns:
        dict: {temperature: 20°C, pressure: 101325 Pa, density: 1.18 kg/m³, c: 343 m/s}
    """
    return {
        "temperature": 20.0,  # °C
        "pressure": 101325.0,  # Pa
        "density": 1.18,  # kg/m³
        "speed_of_sound": 343.0,  # m/s
    }


@pytest.fixture
def sample_exponential_horn():
    """
    Sample exponential horn for testing.

    A typical midrange exponential horn.

    Returns:
        ExponentialHorn: Horn geometry with:
            - Throat area: 10 cm² (0.001 m²)
            - Mouth area: 500 cm² (0.05 m²)
            - Length: 1.5 m
    """
    from gsd.simulation.types import ExponentialHorn

    return ExponentialHorn(
        throat_area=0.001,  # 10 cm²
        mouth_area=0.05,  # 500 cm²
        length=1.5,  # 1.5 m
    )


@pytest.fixture
def test_frequencies():
    """
    Standard frequency sweep for testing.

    Log-spaced frequencies from 20 Hz to 5 kHz.

    Returns:
        ndarray: 100 frequency points from 20 to 5000 Hz
    """
    return np.logspace(np.log10(20), np.log10(5000), 100)


@pytest.fixture
def low_frequency_range():
    """
    Low frequency range for testing below cutoff.

    Returns:
        ndarray: Frequencies from 10 Hz to 200 Hz
    """
    return np.linspace(10, 200, 50)


@pytest.fixture
def mid_frequency_range():
    """
    Mid frequency range for testing around cutoff.

    Returns:
        ndarray: Frequencies from 200 Hz to 2 kHz
    """
    return np.linspace(200, 2000, 50)


@pytest.fixture
def high_frequency_range():
    """
    High frequency range for testing above cutoff.

    Returns:
        ndarray: Frequencies from 2 kHz to 10 kHz
    """
    return np.linspace(2000, 10000, 50)


# TODO: Add fixtures for Hornresp test case data
# These will load from tests/validation_data/hornresp_references/
#
# @pytest.fixture
# def hornresp_tc_p1_rad_01():
#     """Load TC-P1-RAD-01: Low frequency radiation impedance."""
#     pass
#
# @pytest.fixture
# def hornresp_tc_p1_rad_02():
#     """Load TC-P1-RAD-02: Transition region."""
#     pass
