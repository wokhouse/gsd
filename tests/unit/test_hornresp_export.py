"""
Unit tests for Hornresp export functionality.

Tests the export_front_loaded_horn_to_hornresp() function with
various horn and chamber configurations.
"""

import pytest
import tempfile
from pathlib import Path

from gsd.simulation import ExponentialHorn
from gsd.hornresp import export_front_loaded_horn_to_hornresp
from gsd.driver.parameters import ThieleSmallParameters


@pytest.fixture
def tc4_driver():
    """TC4 test driver parameters."""
    return ThieleSmallParameters(
        M_md=0.008,
        C_ms=5.0e-5,
        R_ms=3.0,
        R_e=6.5,
        L_e=0.1e-3,
        BL=12.0,
        S_d=0.0008,
    )


@pytest.fixture
def tc4_horn():
    """TC4 test horn parameters."""
    return ExponentialHorn(
        throat_area=0.0005,  # 5 cm²
        mouth_area=0.02,      # 200 cm²
        length=0.5,           # 0.5 m
    )


class TestExportFrontLoadedHorn:
    """Test front-loaded horn export to Hornresp format."""

    def test_export_simple_horn(self, tc4_driver, tc4_horn):
        """Test export of horn without chambers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "simple.txt"

            export_front_loaded_horn_to_hornresp(
                driver=tc4_driver,
                horn=tc4_horn,
                driver_name="SimpleHorn",
                output_path=str(output_path),
            )

            # Verify file was created
            assert output_path.exists()

            # Read and verify content
            content = output_path.read_text()

            # Check driver parameters
            assert "Sd = 8.00" in content
            assert "Bl = 12.00" in content
            assert "Mmd = 8.00" in content
            assert "Re = 6.50" in content

            # Check horn parameters
            assert "S1 = 5.00" in content
            assert "S2 = 200.00" in content

            # Check chamber parameters (no chambers)
            assert "Vrc = 0.00" in content
            assert "Vtc = 0.00" in content

    def test_export_with_throat_chamber(self, tc4_driver, tc4_horn):
        """Test export of horn with throat chamber."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "throat.txt"

            export_front_loaded_horn_to_hornresp(
                driver=tc4_driver,
                horn=tc4_horn,
                driver_name="ThroatChamber",
                output_path=str(output_path),
                V_tc_liters=0.05,  # 50 cm³
                A_tc_cm2=5.0,
            )

            content = output_path.read_text()

            # Check throat chamber parameters (Vtc in cm³ for Hornresp)
            assert "Vtc = 50.00" in content  # 0.05 L = 50 cm³
            assert "Atc = 5.00" in content

            # Rear chamber should be 0
            assert "Vrc = 0.00" in content

    def test_export_with_rear_chamber(self, tc4_driver, tc4_horn):
        """Test export of horn with rear chamber."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "rear.txt"

            export_front_loaded_horn_to_hornresp(
                driver=tc4_driver,
                horn=tc4_horn,
                driver_name="RearChamber",
                output_path=str(output_path),
                V_rc_liters=2.0,  # 2 L
                L_rc_cm=12.6,
            )

            content = output_path.read_text()

            # Check rear chamber parameters
            assert "Vrc = 2.00" in content
            assert "Lrc = 12.60" in content

            # Throat chamber should be 0
            assert "Vtc = 0.00" in content

    def test_export_with_both_chambers(self, tc4_driver, tc4_horn):
        """Test export of horn with both chambers (TC4)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "both.txt"

            export_front_loaded_horn_to_hornresp(
                driver=tc4_driver,
                horn=tc4_horn,
                driver_name="BothChambers",
                output_path=str(output_path),
                V_tc_liters=0.05,  # 50 cm³
                A_tc_cm2=5.0,
                V_rc_liters=2.0,   # 2 L
                L_rc_cm=12.6,
            )

            content = output_path.read_text()

            # Check both chambers (Vtc in cm³ for Hornresp)
            assert "Vtc = 50.00" in content  # 0.05 L = 50 cm³
            assert "Atc = 5.00" in content
            assert "Vrc = 2.00" in content
            assert "Lrc = 12.60" in content

    def test_export_auto_calculate_lrc(self, tc4_driver, tc4_horn):
        """Test auto-calculation of rear chamber depth."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "auto_lrc.txt"

            # Don't specify L_rc_cm - should be auto-calculated
            export_front_loaded_horn_to_hornresp(
                driver=tc4_driver,
                horn=tc4_horn,
                driver_name="AutoLrc",
                output_path=str(output_path),
                V_rc_liters=2.0,  # 2 L
                # L_rc_cm omitted
            )

            content = output_path.read_text()

            # Should have calculated Lrc
            assert "Lrc = " in content
            # For 2L cube: Lrc = ∛2000 ≈ 12.6 cm
            # But clamped to physical constraints, so exact value may vary
            assert "Vrc = 2.00" in content

    def test_export_with_comment(self, tc4_driver, tc4_horn):
        """Test export with custom comment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "comment.txt"

            export_front_loaded_horn_to_hornresp(
                driver=tc4_driver,
                horn=tc4_horn,
                driver_name="WithComment",
                output_path=str(output_path),
                comment="Custom test system for validation",
            )

            content = output_path.read_text()

            # Check comment appears
            assert "Custom test system for validation" in content

    def test_export_crlf_line_endings(self, tc4_driver, tc4_horn):
        """Test that exported files use CRLF line endings (Hornresp requirement)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "crlf.txt"

            export_front_loaded_horn_to_hornresp(
                driver=tc4_driver,
                horn=tc4_horn,
                driver_name="CRLFTest",
                output_path=str(output_path),
            )

            # Read as binary to check line endings
            with open(output_path, 'rb') as f:
                content = f.read()

            # Should contain CRLF (\r\n)
            assert b'\r\n' in content

            # Count line endings
            crlf_count = content.count(b'\r\n')
            # Should have many CRLF (file has ~160 lines)
            assert crlf_count > 100

    def test_export_includes_all_sections(self, tc4_driver, tc4_horn):
        """Test that all required Hornresp sections are present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "sections.txt"

            export_front_loaded_horn_to_hornresp(
                driver=tc4_driver,
                horn=tc4_horn,
                driver_name="AllSections",
                output_path=str(output_path),
            )

            content = output_path.read_text()

            # Check all required sections
            required_sections = [
                "|RADIATION, SOURCE AND MOUTH PARAMETER VALUES:",
                "|HORN PARAMETER VALUES:",
                "|TRADITIONAL DRIVER PARAMETER VALUES:",
                "|CHAMBER PARAMETER VALUES:",
                "|MAXIMUM SPL PARAMETER VALUES:",
                "|STATUS FLAGS:",
            ]

            for section in required_sections:
                assert section in content, f"Missing section: {section}"

    def test_export_radiation_angle(self, tc4_driver, tc4_horn):
        """Test radiation angle parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test 2pi (half-space)
            output_2pi = Path(tmpdir) / "2pi.txt"
            export_front_loaded_horn_to_hornresp(
                driver=tc4_driver,
                horn=tc4_horn,
                driver_name="2pi",
                output_path=str(output_2pi),
                radiation_angle="2pi",
            )
            content_2pi = output_2pi.read_text()
            assert "Ang = 2.0 x Pi" in content_2pi

            # Test pi (quarter-space)
            output_pi = Path(tmpdir) / "pi.txt"
            export_front_loaded_horn_to_hornresp(
                driver=tc4_driver,
                horn=tc4_horn,
                driver_name="pi",
                output_path=str(output_pi),
                radiation_angle="pi",
            )
            content_pi = output_pi.read_text()
            assert "Ang = 1.0 x Pi" in content_pi

    def test_export_invalid_radiation_angle(self, tc4_driver, tc4_horn):
        """Test that invalid radiation angle raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "invalid.txt"

            with pytest.raises(ValueError, match="Invalid radiation_angle"):
                export_front_loaded_horn_to_hornresp(
                    driver=tc4_driver,
                    horn=tc4_horn,
                    driver_name="Invalid",
                    output_path=str(output_path),
                    radiation_angle="invalid",
                )

    def test_export_wrong_horn_type(self, tc4_driver):
        """Test that wrong horn type raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "wrong.txt"

            with pytest.raises(TypeError, match="horn must be ExponentialHorn"):
                export_front_loaded_horn_to_hornresp(
                    driver=tc4_driver,
                    horn="not_a_horn",  # type: ignore
                    driver_name="Wrong",
                    output_path=str(output_path),
                )
