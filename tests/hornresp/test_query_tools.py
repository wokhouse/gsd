"""
Unit tests for Hornresp simulation query tools.

Tests the query_tools module functions for efficient data extraction and
summarization of Hornresp simulation results.
"""

import pytest
import numpy as np
from pathlib import Path

from gsd.hornresp.query_tools import (
    get_simulation_summary,
    extract_columns,
    query_frequency_range,
    find_extremes,
    _detect_peaks,
    _calculate_bandwidth,
)


class TestQueryTools:
    """Test Hornresp simulation query tools."""

    @pytest.fixture
    def bc_8ndl51_sim_file(self):
        """Get path to BC 8NDL51 Hornresp simulation file."""
        # Note: The actual file is named sim.txt, not bc_8ndl51_inf_sim.txt
        return (
            Path(__file__).parent.parent
            / "validation"
            / "drivers"
            / "bc_8ndl51"
            / "infinite_baffle"
            / "sim.txt"
        )

    @pytest.fixture
    def bc_15ps100_sealed_sim_file(self):
        """Get path to BC 15PS100 sealed box Hornresp simulation file."""
        return (
            Path(__file__).parent.parent
            / "validation"
            / "drivers"
            / "bc_15ps100"
            / "sealed_box"
            / "sim.txt"
        )

    # ============== get_simulation_summary tests ==============

    def test_get_simulation_summary_basic(self, bc_8ndl51_sim_file):
        """Test summary generation without frequency range."""
        summary = get_simulation_summary(bc_8ndl51_sim_file)

        # Check top-level keys
        assert "metadata" in summary
        assert "frequency" in summary
        assert "impedance" in summary
        assert "spl" in summary
        assert "efficiency" in summary
        assert "notable_features" in summary

    def test_summary_frequency_info(self, bc_8ndl51_sim_file):
        """Test summary frequency information."""
        summary = get_simulation_summary(bc_8ndl51_sim_file)

        # Check frequency info
        assert "min_hz" in summary["frequency"]
        assert "max_hz" in summary["frequency"]
        assert "num_points" in summary["frequency"]

        # Should have positive frequency range
        assert summary["frequency"]["min_hz"] > 0
        assert summary["frequency"]["max_hz"] > summary["frequency"]["min_hz"]
        assert summary["frequency"]["num_points"] > 0

    def test_summary_impedance_info(self, bc_8ndl51_sim_file):
        """Test summary impedance information."""
        summary = get_simulation_summary(bc_8ndl51_sim_file)

        # Check impedance info
        assert "min_ohms" in summary["impedance"]
        assert "max_ohms" in summary["impedance"]
        assert "mean_ohms" in summary["impedance"]
        assert "peaks" in summary["impedance"]

        # Should have positive impedance values
        assert summary["impedance"]["min_ohms"] > 0
        assert summary["impedance"]["max_ohms"] > summary["impedance"]["min_ohms"]
        assert summary["impedance"]["mean_ohms"] > 0

        # Max impedance should be much higher than min (resonance peak)
        assert summary["impedance"]["max_ohms"] > 2 * summary["impedance"]["min_ohms"]

        # Should detect at least one impedance peak (driver resonance)
        assert len(summary["impedance"]["peaks"]) >= 1

    def test_summary_spl_info(self, bc_8ndl51_sim_file):
        """Test summary SPL information."""
        summary = get_simulation_summary(bc_8ndl51_sim_file)

        # Check SPL info
        assert "min_db" in summary["spl"]
        assert "max_db" in summary["spl"]
        assert "mean_db" in summary["spl"]
        assert "bandwidth" in summary["spl"]

        # Should have reasonable SPL range
        assert summary["spl"]["min_db"] > 40  # Above noise floor
        assert summary["spl"]["max_db"] < 150  # Below physical limits

        # Max SPL should be higher than min SPL
        assert summary["spl"]["max_db"] > summary["spl"]["min_db"]

    def test_summary_efficiency_info(self, bc_8ndl51_sim_file):
        """Test summary efficiency information."""
        summary = get_simulation_summary(bc_8ndl51_sim_file)

        # Check efficiency info
        assert "min_percent" in summary["efficiency"]
        assert "max_percent" in summary["efficiency"]
        assert "at_max_spl" in summary["efficiency"]

        # Should have positive efficiency
        assert summary["efficiency"]["min_percent"] >= 0
        assert summary["efficiency"]["max_percent"] >= 0

    def test_summary_with_frequency_range(self, bc_8ndl51_sim_file):
        """Test summary generation with frequency range filter."""
        # Filter to bass region (20-100 Hz)
        summary = get_simulation_summary(bc_8ndl51_sim_file, freq_range=(20, 100))

        # Should only include data in specified range
        assert summary["frequency"]["min_hz"] >= 20
        assert summary["frequency"]["max_hz"] <= 100

        # Should have fewer points than full range
        full_summary = get_simulation_summary(bc_8ndl51_sim_file)
        assert summary["frequency"]["num_points"] < full_summary["frequency"]["num_points"]

    def test_summary_notable_features(self, bc_8ndl51_sim_file):
        """Test summary generates notable features."""
        summary = get_simulation_summary(bc_8ndl51_sim_file)

        # Should have notable features
        assert len(summary["notable_features"]) > 0

        # Should mention impedance peak
        impedance_features = [f for f in summary["notable_features"] if "Impedance peak" in f]
        assert len(impedance_features) > 0

        # Should mention max SPL
        spl_features = [f for f in summary["notable_features"] if "Maximum SPL" in f]
        assert len(spl_features) > 0

    # ============== extract_columns tests ==============

    def test_extract_single_column(self, bc_8ndl51_sim_file):
        """Test extracting single column."""
        data = extract_columns(bc_8ndl51_sim_file, columns=["spl_db"])

        # Should return dict with one key
        assert "spl_db" in data
        assert len(data) == 1

        # Should be numpy array
        assert isinstance(data["spl_db"], np.ndarray)

        # Should have data points
        assert len(data["spl_db"]) > 0

    def test_extract_multiple_columns(self, bc_8ndl51_sim_file):
        """Test extracting multiple columns."""
        columns = ["frequency", "spl_db", "ze_ohms"]
        data = extract_columns(bc_8ndl51_sim_file, columns=columns)

        # Should return dict with requested columns
        assert len(data) == 3
        assert "frequency" in data
        assert "spl_db" in data
        assert "ze_ohms" in data

        # All columns should have same length
        assert len(data["frequency"]) == len(data["spl_db"])
        assert len(data["frequency"]) == len(data["ze_ohms"])

    def test_extract_invalid_column(self, bc_8ndl51_sim_file):
        """Test extracting invalid column raises error."""
        with pytest.raises(ValueError, match="Invalid column names"):
            extract_columns(bc_8ndl51_sim_file, columns=["invalid_column"])

    def test_extract_with_frequency_range(self, bc_8ndl51_sim_file):
        """Test extracting columns with frequency range filter."""
        data = extract_columns(
            bc_8ndl51_sim_file,
            columns=["frequency", "spl_db"],
            freq_range=(50, 200),
        )

        # Should only include data in specified range
        assert data["frequency"][0] >= 50
        assert data["frequency"][-1] <= 200

    def test_extract_as_array(self, bc_8ndl51_sim_file):
        """Test extracting columns as numpy array instead of dict."""
        columns = ["frequency", "spl_db"]
        data = extract_columns(bc_8ndl51_sim_file, columns=columns, as_dict=False)

        # Should return numpy array
        assert isinstance(data, np.ndarray)

        # Should have 2 columns
        assert data.shape[1] == 2

        # Number of rows should match frequency array
        assert data.shape[0] > 0

    # ============== query_frequency_range tests ==============

    def test_query_frequency_range_basic(self, bc_8ndl51_sim_file):
        """Test querying frequency range."""
        result = query_frequency_range(bc_8ndl51_sim_file, 20, 100)

        # Should have expected structure
        assert "num_points" in result
        assert "frequency" in result
        assert "data" in result

        # Should have data in range
        assert result["num_points"] > 0
        assert len(result["frequency"]) == result["num_points"]

        # All frequencies should be in range
        assert np.all(result["frequency"] >= 20)
        assert np.all(result["frequency"] <= 100)

    def test_query_frequency_range_with_columns(self, bc_8ndl51_sim_file):
        """Test querying frequency range with specific columns."""
        result = query_frequency_range(
            bc_8ndl51_sim_file, 50, 200, columns=["spl_db", "ze_ohms"]
        )

        # Should have only requested columns
        assert "spl_db" in result["data"]
        assert "ze_ohms" in result["data"]
        assert "frequency" not in result["data"]  # frequency is separate

    def test_query_frequency_range_invalid_range(self, bc_8ndl51_sim_file):
        """Test querying with invalid frequency range."""
        # min >= max should raise error
        with pytest.raises(ValueError, match="freq_min .* must be less than freq_max"):
            query_frequency_range(bc_8ndl51_sim_file, 100, 50)

    def test_query_frequency_range_out_of_data_range(self, bc_8ndl51_sim_file):
        """Test querying frequency range outside data range."""
        # Range outside data should raise error
        with pytest.raises(ValueError, match="No data points found"):
            query_frequency_range(bc_8ndl51_sim_file, 100000, 200000)

    # ============== find_extremes tests ==============

    def test_find_extremes_spl(self, bc_8ndl51_sim_file):
        """Test finding SPL extremes."""
        extremes = find_extremes(bc_8ndl51_sim_file, metric="spl_db", n=3)

        # Should have expected structure
        assert "highest" in extremes
        assert "lowest" in extremes

        # Should return 3 each
        assert len(extremes["highest"]) == 3
        assert len(extremes["lowest"]) == 3

        # Highest should be in descending order
        assert extremes["highest"][0]["value"] >= extremes["highest"][1]["value"]
        assert extremes["highest"][1]["value"] >= extremes["highest"][2]["value"]

        # Lowest should be in ascending order
        assert extremes["lowest"][0]["value"] <= extremes["lowest"][1]["value"]
        assert extremes["lowest"][1]["value"] <= extremes["lowest"][2]["value"]

        # Each extreme should have frequency, value, and index
        for extreme in extremes["highest"] + extremes["lowest"]:
            assert "frequency" in extreme
            assert "value" in extreme
            assert "index" in extreme

    def test_find_extremes_impedance(self, bc_8ndl51_sim_file):
        """Test finding impedance extremes."""
        extremes = find_extremes(bc_8ndl51_sim_file, metric="ze_ohms", n=5)

        # Max impedance should identify resonance peak
        max_z = extremes["highest"][0]
        assert max_z["value"] > 20  # Should be > 20 ohms for resonance

    def test_find_extremes_efficiency(self, bc_8ndl51_sim_file):
        """Test finding efficiency extremes."""
        extremes = find_extremes(bc_8ndl51_sim_file, metric="efficiency_percent", n=3)

        # Efficiency should be positive
        for extreme in extremes["highest"]:
            assert extreme["value"] >= 0

    def test_find_extremes_invalid_metric(self, bc_8ndl51_sim_file):
        """Test finding extremes with invalid metric."""
        with pytest.raises(ValueError, match="Invalid metric"):
            find_extremes(bc_8ndl51_sim_file, metric="invalid_metric")

    # ============== Helper function tests ==============

    def test_detect_peaks_basic(self):
        """Test peak detection on synthetic data."""
        # Create synthetic data with known peaks
        frequencies = np.linspace(0, 100, 1000)

        # Create signal with peaks at 25, 50, 75
        values = (
            np.exp(-((frequencies - 25) ** 2) / 50)
            + 2 * np.exp(-((frequencies - 50) ** 2) / 50)
            + 1.5 * np.exp(-((frequencies - 75) ** 2) / 50)
        )

        peaks = _detect_peaks(values, frequencies, min_height=0.5, min_distance=50)

        # Should detect peaks near expected locations
        assert len(peaks) >= 2

        # Highest peak should be near 50
        assert abs(peaks[0]["freq_hz"] - 50) < 5

    def test_detect_peaks_no_peaks(self):
        """Test peak detection with no peaks."""
        # Flat signal
        values = np.ones(100)
        frequencies = np.linspace(0, 100, 100)

        peaks = _detect_peaks(values, frequencies, min_height=2.0)

        # Should detect no peaks
        assert len(peaks) == 0

    def test_calculate_bandwidth_basic(self):
        """Test bandwidth calculation."""
        # Create simple SPL response
        frequencies = np.linspace(10, 200, 1000)

        # Gaussian response centered at 100 Hz
        spl = 90 * np.exp(-((frequencies - 100) ** 2) / 1000)

        # Calculate -3dB bandwidth (should be near 100 Hz)
        bandwidth = _calculate_bandwidth(spl, frequencies, db_down=3, reference=90)

        # Should find frequency near peak
        assert bandwidth is not None
        assert abs(bandwidth - 100) < 20

    def test_calculate_bandwidth_not_found(self):
        """Test bandwidth calculation when target not reached."""
        # Flat response never reaches -3dB from max
        frequencies = np.linspace(10, 200, 1000)
        spl = np.ones(1000) * 90  # All 90 dB

        # Should return None since never drops to 87 dB
        bandwidth = _calculate_bandwidth(spl, frequencies, db_down=3, reference=90)

        assert bandwidth is None

    # ============== Error handling tests ==============

    def test_get_simulation_summary_file_not_found(self):
        """Test summary generation with non-existent file."""
        with pytest.raises(FileNotFoundError):
            get_simulation_summary("nonexistent_file.txt")

    def test_extract_columns_file_not_found(self):
        """Test column extraction with non-existent file."""
        with pytest.raises(FileNotFoundError):
            extract_columns("nonexistent_file.txt", columns=["spl_db"])

    def test_find_extremes_file_not_found(self):
        """Test find_extremes with non-existent file."""
        with pytest.raises(FileNotFoundError):
            find_extremes("nonexistent_file.txt")

    def test_query_frequency_range_file_not_found(self):
        """Test query_frequency_range with non-existent file."""
        with pytest.raises(FileNotFoundError):
            query_frequency_range("nonexistent_file.txt", 20, 100)
