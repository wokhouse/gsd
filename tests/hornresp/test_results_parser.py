"""
Unit tests for Hornresp results parser.

Tests the load_hornresp_sim_file() function for correct parsing of
Hornresp simulation output files.
"""

import pytest
import numpy as np
from pathlib import Path

from gsd.hornresp.results_parser import load_hornresp_sim_file, HornrespSimulationResult


class TestHornrespResultsParser:
    """Test Hornresp simulation results parser."""

    @pytest.fixture
    def bc_8ndl51_sim_file(self):
        """Get path to BC 8NDL51 Hornresp simulation file."""
        return Path(__file__).parent.parent / "validation" / "drivers" / "bc_8ndl51" / "infinite_baffle" / "bc_8ndl51_inf_sim.txt"

    def test_load_sim_file(self, bc_8ndl51_sim_file):
        """Test loading Hornresp simulation file."""
        result = load_hornresp_sim_file(bc_8ndl51_sim_file)

        # Should return HornrespSimulationResult
        assert isinstance(result, HornrespSimulationResult)

    def test_has_all_attributes(self, bc_8ndl51_sim_file):
        """Test that result has all expected attributes."""
        result = load_hornresp_sim_file(bc_8ndl51_sim_file)

        # Check all numpy array attributes exist
        assert hasattr(result, 'frequency')
        assert hasattr(result, 'ra_norm')
        assert hasattr(result, 'xa_norm')
        assert hasattr(result, 'za_norm')
        assert hasattr(result, 'spl_db')
        assert hasattr(result, 'ze_ohms')
        assert hasattr(result, 'xd_mm')
        assert hasattr(result, 'wphase_deg')
        assert hasattr(result, 'uphase_deg')
        assert hasattr(result, 'cphase_deg')
        assert hasattr(result, 'delay_msec')
        assert hasattr(result, 'efficiency_percent')
        assert hasattr(result, 'ein_volts')
        assert hasattr(result, 'pin_watts')
        assert hasattr(result, 'iin_amps')
        assert hasattr(result, 'zephase_deg')
        assert hasattr(result, 'metadata')

    def test_frequency_array(self, bc_8ndl51_sim_file):
        """Test frequency array is loaded correctly."""
        result = load_hornresp_sim_file(bc_8ndl51_sim_file)

        # Frequency should be a numpy array
        assert isinstance(result.frequency, np.ndarray)

        # Should have data points
        assert len(result.frequency) > 0

        # First frequency should be around 10 Hz (Hornresp default start)
        assert result.frequency[0] == pytest.approx(10.0, abs=0.1)

        # Frequencies should be monotonically increasing
        assert np.all(np.diff(result.frequency) > 0)

    def test_impedance_data(self, bc_8ndl51_sim_file):
        """Test electrical impedance data is loaded correctly."""
        result = load_hornresp_sim_file(bc_8ndl51_sim_file)

        # Ze should be a numpy array
        assert isinstance(result.ze_ohms, np.ndarray)

        # Should have same length as frequency
        assert len(result.ze_ohms) == len(result.frequency)

        # All impedances should be positive
        assert np.all(result.ze_ohms > 0)

        # First impedance value should be reasonable (>0 and <1000 Ω)
        assert 0 < result.ze_ohms[0] < 1000

    def test_spl_data(self, bc_8ndl51_sim_file):
        """Test SPL data is loaded correctly."""
        result = load_hornresp_sim_file(bc_8ndl51_sim_file)

        # SPL should be a numpy array
        assert isinstance(result.spl_db, np.ndarray)

        # Should have same length as frequency
        assert len(result.spl_db) == len(result.frequency)

        # All SPL values should be finite
        assert np.all(np.isfinite(result.spl_db))

    def test_phase_data(self, bc_8ndl51_sim_file):
        """Test phase data is loaded correctly."""
        result = load_hornresp_sim_file(bc_8ndl51_sim_file)

        # Ze phase should be a numpy array
        assert isinstance(result.zephase_deg, np.ndarray)

        # Should have same length as frequency
        assert len(result.zephase_deg) == len(result.frequency)

        # Phase values should be in reasonable range (-180 to 180 degrees)
        assert np.all(result.zephase_deg >= -180)
        assert np.all(result.zephase_deg <= 180)

    def test_metadata(self, bc_8ndl51_sim_file):
        """Test metadata is extracted correctly."""
        result = load_hornresp_sim_file(bc_8ndl51_sim_file)

        # Metadata should be a dictionary
        assert isinstance(result.metadata, dict)

        # Should have expected keys
        assert 'filepath' in result.metadata
        assert 'filename' in result.metadata
        assert 'num_points' in result.metadata
        assert 'freq_min' in result.metadata
        assert 'freq_max' in result.metadata
        assert 'input_voltage' in result.metadata

    def test_metadata_values(self, bc_8ndl51_sim_file):
        """Test metadata values are correct."""
        result = load_hornresp_sim_file(bc_8ndl51_sim_file)

        # Filename should match
        assert result.metadata['filename'] == 'bc_8ndl51_inf_sim.txt'

        # Num points should match array length
        assert result.metadata['num_points'] == len(result.frequency)

        # Freq min/max should match array
        assert result.metadata['freq_min'] == pytest.approx(result.frequency[0])
        assert result.metadata['freq_max'] == pytest.approx(result.frequency[-1])

        # Input voltage should be around 2.83V
        assert result.metadata['input_voltage'] == pytest.approx(2.83, abs=0.01)

    def test_len_function(self, bc_8ndl51_sim_file):
        """Test __len__ returns number of frequency points."""
        result = load_hornresp_sim_file(bc_8ndl51_sim_file)

        # len() should return number of frequency points
        assert len(result) == len(result.frequency)

        # Should be > 0
        assert len(result) > 0

    def test_getitem(self, bc_8ndl51_sim_file):
        """Test __getitem__ returns dictionary for single point."""
        result = load_hornresp_sim_file(bc_8ndl51_sim_file)

        # Get first point
        point = result[0]

        # Should be a dictionary
        assert isinstance(point, dict)

        # Should have all expected keys
        expected_keys = {
            'frequency', 'ra_norm', 'xa_norm', 'za_norm', 'spl_db', 'ze_ohms',
            'xd_mm', 'wphase_deg', 'uphase_deg', 'cphase_deg', 'delay_msec',
            'efficiency_percent', 'ein_volts', 'pin_watts', 'iin_amps', 'zephase_deg'
        }
        assert set(point.keys()) == expected_keys

        # Values should match first row of arrays
        assert point['frequency'] == result.frequency[0]
        assert point['ze_ohms'] == result.ze_ohms[0]
        assert point['spl_db'] == result.spl_db[0]

    def test_file_not_found(self):
        """Test FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            load_hornresp_sim_file("nonexistent_file.txt")

    def test_invalid_file_format(self, tmp_path):
        """Test ValueError for invalid file format."""
        # Create a file with invalid content
        invalid_file = tmp_path / "invalid.txt"
        invalid_file.write_text("Invalid header\n\nnot a number")

        with pytest.raises(ValueError, match="Failed to parse"):
            load_hornresp_sim_file(invalid_file)

    def test_data_consistency(self, bc_8ndl51_sim_file):
        """Test data consistency across all arrays."""
        result = load_hornresp_sim_file(bc_8ndl51_sim_file)

        num_points = len(result.frequency)

        # All arrays should have same length
        assert len(result.ra_norm) == num_points
        assert len(result.xa_norm) == num_points
        assert len(result.za_norm) == num_points
        assert len(result.spl_db) == num_points
        assert len(result.ze_ohms) == num_points
        assert len(result.xd_mm) == num_points
        assert len(result.wphase_deg) == num_points
        assert len(result.uphase_deg) == num_points
        assert len(result.cphase_deg) == num_points
        assert len(result.delay_msec) == num_points
        assert len(result.efficiency_percent) == num_points
        assert len(result.ein_volts) == num_points
        assert len(result.pin_watts) == num_points
        assert len(result.iin_amps) == num_points
        assert len(result.zephase_deg) == num_points
