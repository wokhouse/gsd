"""
Tests for driver loader module.

Tests the YAML-based driver loading system.
"""

import pytest

from gsd.driver import load_driver, list_drivers, get_driver_info
from gsd.driver.parameters import ThieleSmallParameters


class TestLoadDriver:
    """Tests for load_driver function."""

    def test_load_bc_8ndl51(self):
        """Test loading BC_8NDL51 driver."""
        driver = load_driver("BC_8NDL51")

        assert isinstance(driver, ThieleSmallParameters)
        assert driver.F_s == pytest.approx(75.0, rel=0.01)
        assert driver.Q_ts == pytest.approx(0.62, rel=0.05)
        assert driver.V_as == pytest.approx(0.0101, rel=0.05)
        assert driver.S_d == 0.0220
        assert driver.X_max == 0.007

    def test_load_bc_15ds115(self):
        """Test loading BC_15DS115 subwoofer."""
        driver = load_driver("BC_15DS115")

        assert isinstance(driver, ThieleSmallParameters)
        assert driver.F_s == pytest.approx(33.0, rel=0.01)
        assert driver.X_max == 0.0165

    def test_load_tc2(self):
        """Test loading TC2 test driver."""
        driver = load_driver("TC2")

        assert isinstance(driver, ThieleSmallParameters)
        assert driver.F_s == pytest.approx(251.0, rel=0.05)
        assert driver.S_d == 0.0008  # 8.0 cm²

    def test_load_tc3(self):
        """Test loading TC3 test driver."""
        driver = load_driver("TC3")

        assert isinstance(driver, ThieleSmallParameters)
        # TC3 uses same driver as TC2
        assert driver.S_d == 0.0008

    def test_load_tc4(self):
        """Test loading TC4 test driver."""
        driver = load_driver("TC4")

        assert isinstance(driver, ThieleSmallParameters)
        # TC4 uses same driver as TC2
        assert driver.S_d == 0.0008

    def test_load_invalid_driver_raises_error(self):
        """Test that loading invalid driver raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Driver 'INVALID' not found"):
            load_driver("INVALID")


class TestListDrivers:
    """Tests for list_drivers function."""

    def test_list_drivers_returns_dict(self):
        """Test that list_drivers returns a dictionary."""
        drivers = list_drivers()

        assert isinstance(drivers, dict)
        assert len(drivers) > 0

    def test_list_drivers_contains_all_b_c_drivers(self):
        """Test that list_drivers contains all B&C drivers."""
        drivers = list_drivers()

        # Check for B&C drivers
        assert "BC_8NDL51" in drivers
        assert "BC_8FMB51" in drivers
        assert "BC_12NDL76" in drivers
        assert "BC_15DS115" in drivers
        assert "BC_15PS100" in drivers
        assert "BC_18PZW100" in drivers
        assert "BC_18RBX100" in drivers

    def test_list_drivers_contains_test_drivers(self):
        """Test that list_drivers contains test drivers."""
        drivers = list_drivers()

        # Check for test drivers
        assert "TC2" in drivers
        assert "TC3" in drivers
        assert "TC4" in drivers

    def test_list_drivers_has_descriptions(self):
        """Test that list_drivers has descriptions for all drivers."""
        drivers = list_drivers()

        for name, description in drivers.items():
            assert isinstance(name, str)
            assert isinstance(description, str)
            assert len(description) > 0


class TestGetDriverInfo:
    """Tests for get_driver_info function."""

    def test_get_driver_info_returns_dict(self):
        """Test that get_driver_info returns a dictionary."""
        info = get_driver_info("BC_8NDL51")

        assert isinstance(info, dict)

    def test_get_driver_info_has_required_fields(self):
        """Test that get_driver_info has all required fields."""
        info = get_driver_info("BC_8NDL51")

        # Check for required top-level fields
        assert "name" in info
        assert "manufacturer" in info
        assert "model" in info
        assert "description" in info
        assert "parameters" in info

    def test_get_driver_info_has_datasheet_info(self):
        """Test that get_driver_info includes datasheet information."""
        info = get_driver_info("BC_8NDL51")

        assert "datasheet" in info
        datasheet = info["datasheet"]
        assert "fs" in datasheet
        assert "re" in datasheet

    def test_get_driver_info_has_parameters(self):
        """Test that get_driver_info includes parameters."""
        info = get_driver_info("BC_8NDL51")

        params = info["parameters"]
        assert "M_md" in params
        assert "C_ms" in params
        assert "R_ms" in params
        assert "R_e" in params
        assert "L_e" in params
        assert "BL" in params
        assert "S_d" in params

    def test_get_driver_info_has_notes_and_literature(self):
        """Test that get_driver_info includes notes and literature."""
        info = get_driver_info("BC_8NDL51")

        assert "notes" in info
        assert "literature" in info

    def test_get_driver_info_invalid_driver_raises_error(self):
        """Test that get_driver_info raises FileNotFoundError for invalid driver."""
        with pytest.raises(FileNotFoundError, match="Driver 'INVALID' not found"):
            get_driver_info("INVALID")


class TestDriverParameters:
    """Tests for loaded driver parameter validation."""

    def test_all_drivers_have_valid_parameters(self):
        """Test that all drivers have valid physical parameters."""
        drivers = list_drivers()

        for driver_name in drivers:
            driver = load_driver(driver_name)

            # Check that derived parameters are calculated
            assert driver.F_s is not None
            assert driver.Q_ts is not None
            assert driver.V_as is not None

            # Check that values are physically reasonable
            assert driver.F_s > 0  # Resonance frequency should be positive
            assert driver.Q_ts > 0  # Total Q should be positive
            assert driver.V_as > 0  # Equivalent volume should be positive
            assert driver.S_d > 0  # Effective area should be positive

    def test_all_b_c_drivers_have_xmax(self):
        """Test that all B&C drivers have X_max specified."""
        b_c_drivers = [
            "BC_8NDL51", "BC_8FMB51", "BC_12NDL76",
            "BC_15DS115", "BC_15PS100", "BC_18PZW100", "BC_18RBX100"
        ]

        for driver_name in b_c_drivers:
            driver = load_driver(driver_name)
            assert driver.X_max is not None
            assert driver.X_max > 0
