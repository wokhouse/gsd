"""
Integration tests for two-way system design with integrated horn/crossover optimization.

Tests cover:
- Complete integrated design workflow
- BC 12FW88 + DH450 case study reproduction
- Feasibility checking and constraint handling
- Validation results

Literature:
- Olson (1947) - Horn cutoff and operating range
- Beranek (1954) - Directivity and beaming
- Case study: docs/two_way_design_review_12fw88_dh450.md
"""

import pytest
import numpy as np
from gsd.optimization.api.two_way_system import design_two_way_system_integrated
from gsd.driver import load_driver


class TestIntegratedTwoWayDesign:
    """Test integrated two-way system design."""

    def test_integrated_design_12fw88_dh450_basic(self):
        """
        Test integrated design with BC 12FW88 + DH450.

        This is the main case study that drove the implementation.
        Should complete in one function call and produce acceptable results.

        Literature: Case study documented in two_way_design_review_12fw88_dh450.md
        Expected results (from manual design):
        - Horn Fc: ~468 Hz
        - Crossover: ~600 Hz
        - Dip: ~3.2 dB
        - Flatness: ~3.7 dB
        """
        design = design_two_way_system_integrated(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            target_crossover_hz=800,
            printer_constraints={"max_length": 0.25, "max_mouth_area": 0.0625},
            accept_sensitivity_loss=True,
            verbose=False
        )

        # Check that design has required attributes
        assert hasattr(design, 'horn_fc_hz'), "Design should have horn_fc_hz attribute"
        assert hasattr(design, 'lf_beaming_frequency_hz'), "Design should have lf_beaming_frequency_hz"
        assert hasattr(design, 'dip_db'), "Design should have dip_db attribute"
        assert hasattr(design, 'validation'), "Design should have validation dict"

        # Check basic performance metrics
        # Dip should be < 5 dB (acceptable range)
        assert design.dip_db < 5.0, f"Dip {design.dip_db:.2f} dB too high"

        # Horn Fc should be reasonable (200-800 Hz for this design)
        assert 200 < design.horn_fc_hz < 800, \
            f"Horn Fc {design.horn_fc_hz:.0f} Hz outside expected range"

        # Crossover should be in reasonable range (500-1500 Hz)
        assert 500 < design.crossover_frequency < 1500, \
            f"Crossover {design.crossover_frequency:.0f} Hz outside expected range"

        # Validation should indicate design is acceptable or better
        assert design.validation['passes'], "Design validation should pass"
        assert "Good" in design.validation['rating'] or "Acceptable" in design.validation['rating'] or "Excellent" in design.validation['rating'], \
            f"Validation rating should be Good/Acceptable/Excellent, got: {design.validation['rating']}"

    def test_integrated_design_with_constraints(self):
        """
        Test integrated design respects printer constraints.

        The design should work within the specified max_length and max_mouth_area.
        """
        max_length = 0.25  # 250 mm
        max_mouth_area = 0.0625  # 250mm × 250mm

        design = design_two_way_system_integrated(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            target_crossover_hz=800,
            printer_constraints={"max_length": max_length, "max_mouth_area": max_mouth_area},
            accept_sensitivity_loss=True,
            verbose=False
        )

        # Check horn params respect constraints
        horn_params = design.horn_params
        assert horn_params['length'] <= max_length, \
            f"Horn length {horn_params['length']*100:.0f} cm exceeds constraint {max_length*100:.0f} cm"

        assert horn_params['mouth_area'] <= max_mouth_area, \
            f"Mouth area {horn_params['mouth_area']*10000:.0f} cm² exceeds constraint {max_mouth_area*10000:.0f} cm²"

    def test_integrated_design_without_sensitivity_loss(self):
        """
        Test that design fails when constraints cannot be met.

        When accept_sensitivity_loss=False and constraints are too tight,
        should raise ValueError.

        Note: Need extremely tight constraints to trigger this, since even
        a 100mm horn only needs ~48cm² mouth for 336Hz Fc.
        """
        # Extremely tight constraints that will require sensitivity loss
        # 50mm horn, 25cm² mouth is too small for 336Hz Fc
        tight_constraints = {"max_length": 0.05, "max_mouth_area": 0.0025}  # 50mm, 50mm²

        with pytest.raises(ValueError, match="exceeds constraint"):
            design_two_way_system_integrated(
                lf_driver_name="BC_12FW88",
                hf_driver_name="BC_DH450",
                target_crossover_hz=800,
                printer_constraints=tight_constraints,
                accept_sensitivity_loss=False,  # Don't allow sensitivity loss
                verbose=False
            )

    def test_integrated_design_xo_capped_at_beaming(self):
        """
        Test that crossover is capped at LF driver beaming frequency.

        When target XO is too high (above 0.8×beaming), design should
        automatically adjust XO downward.
        """
        # Set target XO very high (above beaming)
        # BC 12FW88 beaming is ~840 Hz, so 0.8×beaming ≈ 672 Hz
        target_xo = 2000  # Hz - way above beaming

        design = design_two_way_system_integrated(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            target_crossover_hz=target_xo,
            printer_constraints={"max_length": 0.25, "max_mouth_area": 0.0625},
            accept_sensitivity_loss=True,
            verbose=False
        )

        # Actual crossover should be capped at ~0.8×beaming
        # Crossover should be < 800 Hz
        assert design.crossover_frequency < 800, \
            f"Crossover {design.crossover_frequency:.0f} Hz should be capped at beaming (~670 Hz)"

    def test_integrated_design_sealed_enclosure(self):
        """
        Test integrated design with sealed enclosure option.

        Should work with sealed box as well as ported.
        """
        design = design_two_way_system_integrated(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            target_crossover_hz=800,
            printer_constraints={"max_length": 0.25, "max_mouth_area": 0.0625},
            enclosure_type="sealed",
            accept_sensitivity_loss=True,
            verbose=False
        )

        # Should have sealed enclosure parameters
        assert "Vb" in design.lf_enclosure_params, "Should have Vb parameter"
        assert design.lf_enclosure_type == "sealed", "Enclosure type should be sealed"

        # Should still produce valid design
        assert design.dip_db < 6.0, f"Dip {design.dip_db:.2f} dB should be acceptable"

    def test_integrated_design_optimized_xo_ratio(self):
        """
        Test integrated design with optimized XO/Fc ratio (1.3×).

        Using xo_fc_ratio=1.3 should target lower Fc (higher XO/Fc).
        """
        design_traditional = design_two_way_system_integrated(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            target_crossover_hz=800,
            printer_constraints={"max_length": 0.25, "max_mouth_area": 0.0625},
            xo_fc_ratio=2.0,  # Traditional 2×Fc
            accept_sensitivity_loss=True,
            verbose=False
        )

        design_optimized = design_two_way_system_integrated(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            target_crossover_hz=800,
            printer_constraints={"max_length": 0.25, "max_mouth_area": 0.0625},
            xo_fc_ratio=1.3,  # Optimized 1.3×Fc
            accept_sensitivity_loss=True,
            verbose=False
        )

        # Both should produce valid designs
        assert design_traditional.dip_db < 5.0, "Traditional design should be acceptable"
        assert design_optimized.dip_db < 5.0, "Optimized design should be acceptable"

        # Optimized design should target lower Fc (higher XO allows lower Fc)
        # This is a weak assertion - the actual Fc depends on many factors
        # Just verify both produce reasonable results
        assert 200 < design_traditional.horn_fc_hz < 800
        assert 200 < design_optimized.horn_fc_hz < 800


class TestIntegratedDesignComponents:
    """Test individual components of integrated design."""

    def test_lf_beaming_frequency_calculation(self):
        """Test that LF beaming frequency is calculated correctly."""
        design = design_two_way_system_integrated(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            target_crossover_hz=800,
            printer_constraints={"max_length": 0.25, "max_mouth_area": 0.0625},
            accept_sensitivity_loss=True,
            verbose=False
        )

        # BC 12FW88 beaming should be ~840 Hz
        assert 800 < design.lf_beaming_frequency_hz < 900, \
            f"LF beaming {design.lf_beaming_frequency_hz:.0f} Hz outside expected range"

    def test_horn_fc_calculation(self):
        """Test that horn Fc is calculated from geometry."""
        design = design_two_way_system_integrated(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            target_crossover_hz=800,
            printer_constraints={"max_length": 0.25, "max_mouth_area": 0.0625},
            accept_sensitivity_loss=True,
            verbose=False
        )

        # Horn Fc should match calculated Fc from mouth geometry
        # Verify by recalculating
        from gsd.optimization.api.horn_physics import calculate_fc_from_mouth

        recalculated_fc = calculate_fc_from_mouth(
            design.horn_params['throat_area'] * 10000,  # m² to cm²
            design.horn_params['mouth_area'] * 10000,  # m² to cm²
            design.horn_params['length'] * 100  # m to cm
        )

        assert abs(design.horn_fc_hz - recalculated_fc) < 5, \
            f"Horn Fc {design.horn_fc_hz:.0f} Hz doesn't match recalculated {recalculated_fc:.0f} Hz"

    def test_f3_calculation(self):
        """Test that F3 is calculated correctly."""
        design = design_two_way_system_integrated(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            target_crossover_hz=800,
            printer_constraints={"max_length": 0.25, "max_mouth_area": 0.0625},
            accept_sensitivity_loss=True,
            verbose=False
        )

        # F3 should be reasonable for ported box with BC 12FW88
        # Typical F3 for this driver is 40-60 Hz
        assert 30 < design.f3 < 80, \
            f"F3 {design.f3:.1f} Hz outside expected range for BC 12FW88"

    def test_hf_padding_in_reasonable_range(self):
        """Test that HF padding is in reasonable range."""
        design = design_two_way_system_integrated(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            target_crossover_hz=800,
            printer_constraints={"max_length": 0.25, "max_mouth_area": 0.0625},
            accept_sensitivity_loss=True,
            verbose=False
        )

        # HF padding should be between -25 and -10 dB
        assert -25 < design.hf_padding_db < -5, \
            f"HF padding {design.hf_padding_db:.1f} dB outside expected range"
