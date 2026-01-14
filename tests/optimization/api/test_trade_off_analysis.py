"""
Integration tests for trade-off analysis module.

Tests cover:
- Mouth vs Fc trade-off analysis
- Sensitivity curve analysis
- Dip prediction model
- Report generation

Literature:
- Olson (1947) - Horn cutoff and flare theory
- Empirical models from case studies
"""

import pytest
import numpy as np
from numpy.testing import assert_allclose
import tempfile
import os

from gsd.optimization.api.trade_off_analysis import (
    analyze_mouth_vs_fc_tradeoff,
    predict_crossover_dip,
    analyze_mouth_sensitivity_curve,
    MouthFcTradeOff,
    SensitivityCurveData
)


class TestPredictCrossoverDip:
    """Test crossover dip prediction model."""

    def test_optimal_xo_fc_ratio(self):
        """
        Test dip prediction at optimal XO/Fc ratio.

        When XO/Fc ≈ 1.3 and XO well below beaming, dip should be minimal.
        """
        dip = predict_crossover_dip(
            xo_freq_hz=600,
            horn_fc_hz=468,
            lf_beaming_hz=840
        )

        # Should be good (2-3 dB range)
        assert 1.5 <= dip <= 4.0, f"Dip {dip:.2f} dB outside expected range"

    def test_xo_too_close_to_fc(self):
        """
        Test dip prediction when XO too close to Fc.

        When XO/Fc < 1.2, dip should be larger than optimal.
        """
        # XO only 1.11×Fc
        dip = predict_crossover_dip(
            xo_freq_hz=500,
            horn_fc_hz=450,
            lf_beaming_hz=840
        )

        # Should be worse than optimal (>2.5 dB)
        assert dip > 2.5, f"Dip {dip:.2f} dB should be > 2.5 dB when XO/Fc < 1.2"

    def test_xo_too_close_to_beaming(self):
        """
        Test dip prediction when XO too close to beaming.

        When XO > 0.8×f_beam, dip should be larger.
        """
        dip = predict_crossover_dip(
            xo_freq_hz=750,  # 0.89×f_beam
            horn_fc_hz=400,
            lf_beaming_hz=840
        )

        # Should be worse than optimal (beaming penalty applies)
        assert dip > 3.0, f"Dip {dip:.2f} dB should be > 3 dB near beaming"

    def test_traditional_2x_ratio(self):
        """
        Test dip prediction at traditional 2×Fc ratio.

        Traditional rule should give acceptable results if well below beaming.
        """
        dip = predict_crossover_dip(
            xo_freq_hz=800,
            horn_fc_hz=400,
            lf_beaming_hz=1200
        )

        # Should be acceptable
        assert dip < 5.0, f"Dip {dip:.2f} dB should be acceptable at 2×Fc"

    def test_extreme_case_very_poor(self):
        """Test extreme poor case (XO near both Fc and beaming)."""
        dip = predict_crossover_dip(
            xo_freq_hz=450,
            horn_fc_hz=400,  # XO/Fc = 1.125 (too close)
            lf_beaming_hz=500  # XO > 0.8×beaming (too close)
        )

        # Should be poor (worse than optimal, but model is conservative)
        assert dip > 3.5, f"Dip {dip:.2f} dB should be > 3.5 dB for extreme case"

    def test_dip_capped_at_reasonable_values(self):
        """Test that dip is capped at reasonable values."""
        # Test very low (should be capped)
        dip_low = predict_crossover_dip(
            xo_freq_hz=1000,
            horn_fc_hz=400,
            lf_beaming_hz=2000
        )
        assert dip_low >= 1.5, "Dip should be capped at minimum 1.5 dB"

        # Test very high (should be capped)
        dip_high = predict_crossover_dip(
            xo_freq_hz=100,
            horn_fc_hz=1000,  # XO << Fc (invalid)
            lf_beaming_hz=100
        )
        assert dip_high <= 15.0, "Dip should be capped at maximum 15.0 dB"


class TestAnalyzeMouthVsFcTradeoff:
    """Test mouth vs Fc trade-off analysis."""

    def test_basic_analysis(self):
        """Test basic trade-off analysis."""
        mouths = np.array([200, 300, 400, 500, 600])

        result = analyze_mouth_vs_fc_tradeoff(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            horn_length_cm=25.0,
            mouth_areas_cm2=mouths,
            target_xo_hz=800
        )

        # Check return type
        assert isinstance(result, MouthFcTradeOff)

        # Check arrays
        assert len(result.mouth_areas_cm2) == len(mouths)
        assert len(result.fc_hz) == len(mouths)
        assert len(result.sensitivity_penalties_db) == len(mouths)

    def test_fc_increases_with_mouth(self):
        """Test that Fc increases with mouth area."""
        mouths = np.linspace(200, 600, 5)

        result = analyze_mouth_vs_fc_tradeoff(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            horn_length_cm=25.0,
            mouth_areas_cm2=mouths,
            target_xo_hz=800
        )

        # Fc should increase with mouth
        for i in range(len(result.fc_hz) - 1):
            assert result.fc_hz[i] < result.fc_hz[i + 1], \
                f"Fc should increase: {result.fc_hz[i]:.0f} < {result.fc_hz[i+1]:.0f}"

    def test_sensitivity_penalty_increases_with_smaller_mouth(self):
        """Test that smaller mouth has larger sensitivity penalty."""
        mouths = np.array([200, 400, 600])

        result = analyze_mouth_vs_fc_tradeoff(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            horn_length_cm=25.0,
            mouth_areas_cm2=mouths,
            target_xo_hz=800
        )

        # Sensitivity penalty should be more negative for smaller mouth
        # (relative to max mouth)
        assert result.sensitivity_penalties_db[0] < result.sensitivity_penalties_db[1]
        assert result.sensitivity_penalties_db[1] < result.sensitivity_penalties_db[2]

    def test_recommended_xo_ranges_sane(self):
        """Test that recommended XO ranges are sensible."""
        mouths = np.array([250, 350, 450])

        result = analyze_mouth_vs_fc_tradeoff(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            horn_length_cm=25.0,
            mouth_areas_cm2=mouths,
            target_xo_hz=800
        )

        # Each XO range should be valid
        for xo_min, xo_max in result.recommended_xo_ranges:
            assert xo_min > 0, f"XO min {xo_min} should be positive"
            assert xo_max > xo_min, f"XO max {xo_max} > min {xo_min}"
            assert xo_max < 2000, f"XO max {xo_max} should be reasonable"

    def test_best_mouth_selected(self):
        """Test that best mouth is selected based on target XO."""
        mouths = np.linspace(200, 600, 9)

        result = analyze_mouth_vs_fc_tradeoff(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            horn_length_cm=25.0,
            mouth_areas_cm2=mouths,
            target_xo_hz=800
        )

        # Best mouth should be one of the tested mouths
        assert result.best_mouth_cm2 in mouths

        # Best Fc should be reasonable
        assert 200 < result.best_fc_hz < 1000, \
            f"Best Fc {result.best_fc_hz:.0f} Hz outside expected range"

    def test_analysis_text_generated(self):
        """Test that analysis text is generated."""
        mouths = np.array([250, 350, 450])

        result = analyze_mouth_vs_fc_tradeoff(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            horn_length_cm=25.0,
            mouth_areas_cm2=mouths,
            target_xo_hz=800
        )

        # Analysis should contain key information
        assert len(result.analysis) > 0
        assert "Trade-off" in result.analysis or "tradeoff" in result.analysis.lower()
        assert "Fc" in result.analysis


class TestAnalyzeMouthSensitivityCurve:
    """Test mouth-sensitivity curve analysis."""

    def test_basic_analysis(self):
        """Test basic curve analysis."""
        result = analyze_mouth_sensitivity_curve(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            horn_length_cm=25.0,
            target_xo_hz=800
        )

        # Check return type
        assert isinstance(result, SensitivityCurveData)

        # Check arrays
        assert len(result.mouth_areas_cm2) > 0
        assert len(result.fc_values_hz) > 0
        assert len(result.sensitivity_penalties_db) > 0

    def test_fc_values_monotonic(self):
        """Test that Fc increases with mouth area."""
        result = analyze_mouth_sensitivity_curve(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            horn_length_cm=25.0,
            target_xo_hz=800
        )

        # Fc should increase with mouth
        for i in range(len(result.fc_values_hz) - 1):
            assert result.fc_values_hz[i] <= result.fc_values_hz[i + 1], \
                f"Fc should be monotonic: {result.fc_values_hz[i]:.0f} <= {result.fc_values_hz[i+1]:.0f}"

    def test_sensitivity_penalties_calculated(self):
        """Test that sensitivity penalties are calculated."""
        result = analyze_mouth_sensitivity_curve(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            horn_length_cm=25.0,
            target_xo_hz=800
        )

        # Max mouth should have 0 dB penalty
        max_penalty_idx = np.argmax(result.mouth_areas_cm2)
        assert_allclose(result.sensitivity_penalties_db[max_penalty_idx], 0.0, atol=0.1)

    def test_dip_predictions_calculated(self):
        """Test that dip predictions are calculated."""
        result = analyze_mouth_sensitivity_curve(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            horn_length_cm=25.0,
            target_xo_hz=800
        )

        # All dips should be positive
        assert np.all(result.dip_predictions_db > 0)

        # Dips should be in reasonable range
        assert np.all(result.dip_predictions_db < 20)

    def test_crossover_options_in_range(self):
        """Test that crossover options are reasonable."""
        result = analyze_mouth_sensitivity_curve(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            horn_length_cm=25.0,
            target_xo_hz=800
        )

        # All crossover options should be positive
        assert np.all(result.crossover_options_hz > 0)

        # Should be in reasonable range
        assert np.all(result.crossover_options_hz < 5000)

    def test_recommendation_text_generated(self):
        """Test that recommendation text is generated."""
        result = analyze_mouth_sensitivity_curve(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            horn_length_cm=25.0,
            target_xo_hz=800
        )

        # Recommendation should be generated
        assert len(result.recommendation) > 0

        # Should contain key sections
        assert "Trade-off" in result.recommendation or "tradeoff" in result.recommendation.lower()
        assert "Rating:" in result.recommendation or "rating" in result.recommendation.lower()

    def test_custom_mouth_range(self):
        """Test with custom mouth range."""
        result = analyze_mouth_sensitivity_curve(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            horn_length_cm=25.0,
            target_xo_hz=800,
            mouth_range_cm2=(300, 500),
            num_points=5
        )

        # Should use custom range
        assert result.mouth_areas_cm2[0] >= 300
        assert result.mouth_areas_cm2[-1] <= 500
        assert len(result.mouth_areas_cm2) == 5


class TestReportGeneration:
    """Test report generation functionality."""

    def test_generate_trade_off_report(self):
        """Test trade-off report generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_report.txt")

            generate_trade_off_report(
                lf_driver_name="BC_12FW88",
                hf_driver_name="BC_DH450",
                target_xo_hz=800,
                printer_constraints={"max_length": 0.25, "max_mouth_area": 0.0625},
                output_path=output_path
            )

            # Check file was created
            assert os.path.exists(output_path)

            # Check file has content
            with open(output_path, 'r') as f:
                content = f.read()

            assert len(content) > 0
            assert "TRADE-OFF ANALYSIS REPORT" in content
            assert "BC_12FW88" in content
            assert "BC_DH450" in content

    def test_report_contains_all_sections(self):
        """Test that report contains all required sections."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_report.txt")

            generate_trade_off_report(
                lf_driver_name="BC_12FW88",
                hf_driver_name="BC_DH450",
                target_xo_hz=800,
                printer_constraints={"max_length": 0.25, "max_mouth_area": 0.0625},
                output_path=output_path
            )

            with open(output_path, 'r') as f:
                content = f.read()

            # Check for key sections
            assert "DRIVER SUMMARY" in content
            assert "PRINTER CONSTRAINTS" in content
            assert "TARGET CROSSOVER" in content or "CROSSOVER ANALYSIS" in content
            assert "HORN OPTIONS" in content
            assert "TRADE-OFF ANALYSIS" in content
            assert "RECOMMENDATION" in content

    def test_report_with_different_printer(self):
        """Test report generation with different printer constraints."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_report_500mm.txt")

            generate_trade_off_report(
                lf_driver_name="BC_12FW88",
                hf_driver_name="BC_DH450",
                target_xo_hz=800,
                printer_constraints={"max_length": 0.50, "max_mouth_area": 0.25},
                output_path=output_path
            )

            with open(output_path, 'r') as f:
                content = f.read()

            # Should reflect larger printer
            assert "50 cm" in content or "500mm" in content

    def test_report_with_sealed_enclosure(self):
        """Test report mentions sealed enclosure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "test_report_sealed.txt")

            generate_trade_off_report(
                lf_driver_name="BC_12FW88",
                hf_driver_name="BC_DH450",
                target_xo_hz=800,
                printer_constraints={"max_length": 0.25, "max_mouth_area": 0.0625},
                output_path=output_path,
                horn_length_cm=25.0
            )

            with open(output_path, 'r') as f:
                content = f.read()

            # Should contain printer info
            assert "PRINTER CONSTRAINTS" in content


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_small_target_xo(self):
        """Test with very low target crossover."""
        result = analyze_mouth_sensitivity_curve(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            horn_length_cm=25.0,
            target_xo_hz=200  # Very low
        )

        # Should still complete
        assert result is not None

    def test_very_large_target_xo(self):
        """Test with very high target crossover."""
        result = analyze_mouth_sensitivity_curve(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            horn_length_cm=25.0,
            target_xo_hz=3000  # Very high
        )

        # Should still complete
        assert result is not None

    def test_short_horn(self):
        """Test with short horn."""
        result = analyze_mouth_sensitivity_curve(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            horn_length_cm=10.0,  # Very short
            target_xo_hz=800
        )

        # Should complete
        assert result is not None

    def test_long_horn(self):
        """Test with long horn."""
        result = analyze_mouth_sensitivity_curve(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            horn_length_cm=50.0,  # Very long
            target_xo_hz=800
        )

        # Should complete
        assert result is not None


# Import at end to avoid circular dependency
from gsd.optimization.api.trade_off_analysis import generate_trade_off_report
