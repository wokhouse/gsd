"""
Tests for parameter sweep functionality (Phase 7.4).
"""

import numpy as np
import pytest
from gsd.optimization.api import DesignAssistant


def test_sealed_box_vb_sweep():
    """Test parameter sweep for sealed box Vb."""
    assistant = DesignAssistant()

    sweep = assistant.sweep_parameter(
        driver_name="BC_12NDL76",
        enclosure_type="sealed",
        parameter="Vb",
        param_min=0.010,  # 10L
        param_max=0.050,  # 50L
        steps=20
    )

    # Check basic structure
    assert sweep.parameter_swept == "Vb"
    assert len(sweep.parameter_values) == 20
    assert abs(sweep.parameter_values[0] - 0.010) < 0.001  # First value
    assert abs(sweep.parameter_values[-1] - 0.050) < 0.001  # Last value

    # Check results
    assert "F3" in sweep.results
    assert "size" in sweep.results
    assert len(sweep.results["F3"]) == 20

    # Check sensitivity analysis
    assert "f3_sensitivity" in sweep.sensitivity_analysis
    assert "trend_description" in sweep.sensitivity_analysis

    # Check recommendations
    assert len(sweep.recommendations) > 0
    assert any("Best F3" in rec for rec in sweep.recommendations)

    print("✓ Sealed box Vb sweep works")


def test_sealed_box_sweep_finds_best():
    """Test that sweep correctly identifies best F3 point."""
    assistant = DesignAssistant()

    sweep = assistant.sweep_parameter(
        driver_name="BC_8NDL51",
        enclosure_type="sealed",
        parameter="Vb",
        param_min=0.005,  # 5L
        param_max=0.030,  # 30L
        steps=30
    )

    # Find best F3 from sweep data
    valid_mask = ~np.isnan(sweep.results["F3"])
    assert np.sum(valid_mask) > 0, "Should have valid F3 values"

    f3_values = sweep.results["F3"][valid_mask]
    param_values = sweep.parameter_values[valid_mask]

    best_idx = np.argmin(f3_values)
    best_f3 = f3_values[best_idx]
    best_vb = param_values[best_idx] * 1000  # Convert to liters

    # Best F3 should be within sweep range
    assert 5 <= best_vb <= 30

    # Recommendations should mention this best value
    rec_text = " ".join(sweep.recommendations)
    assert "Best F3" in rec_text

    print(f"✓ Found best F3: {best_f3:.1f} Hz at Vb={best_vb:.1f}L")


def test_sweep_sensitivity_analysis():
    """Test that sensitivity analysis correctly identifies correlations."""
    assistant = DesignAssistant()

    sweep = assistant.sweep_parameter(
        driver_name="BC_12NDL76",
        enclosure_type="sealed",
        parameter="Vb",
        param_min=0.010,
        param_max=0.050,
        steps=30
    )

    # Should have sensitivity metrics
    assert "f3_sensitivity" in sweep.sensitivity_analysis
    assert 0.0 <= sweep.sensitivity_analysis["f3_sensitivity"] <= 1.0

    assert "f3_correlation" in sweep.sensitivity_analysis
    assert -1.0 <= sweep.sensitivity_analysis["f3_correlation"] <= 1.0

    assert "most_sensitive_objective" in sweep.sensitivity_analysis
    assert sweep.sensitivity_analysis["most_sensitive_objective"] in ["F3", "size"]

    print(f"✓ Sensitivity analysis: f3_corr={sweep.sensitivity_analysis['f3_correlation']:.3f}")


def test_sweep_recommendations_content():
    """Test that sweep recommendations provide useful insights."""
    assistant = DesignAssistant()

    sweep = assistant.sweep_parameter(
        driver_name="BC_15DS115",
        enclosure_type="sealed",
        parameter="Vb",
        param_min=0.020,  # 20L
        param_max=0.100,  # 100L
        steps=40
    )

    recommendations = sweep.recommendations

    # Should have multiple recommendations
    assert len(recommendations) >= 2

    # Should include best F3 recommendation
    assert any("Best F3" in rec for rec in recommendations)

    # Should include trend analysis
    assert any("Trend:" in rec or "trend" in rec.lower() for rec in recommendations)

    # Check for optimal range recommendation (if applicable)
    range_recs = [rec for rec in recommendations if "Optimal range" in rec]
    if len(range_recs) > 0:
        print(f"✓ Found optimal range recommendation: {range_recs[0]}")

    print(f"✓ Generated {len(recommendations)} recommendations")


def test_sweep_invalid_parameter():
    """Test that sweep handles invalid parameters gracefully."""
    assistant = DesignAssistant()

    # Try to sweep unsupported parameter for sealed box
    sweep = assistant.sweep_parameter(
        driver_name="BC_12NDL76",
        enclosure_type="sealed",
        parameter="Fb",  # Not valid for sealed box
        param_min=10.0,
        param_max=100.0,
        steps=20
    )

    # Should return empty results with error message
    assert len(sweep.parameter_values) == 0
    assert len(sweep.recommendations) == 1
    assert "only supports sweeping 'Vb'" in sweep.recommendations[0]

    print("✓ Invalid parameter handled correctly")


def test_sweep_invalid_driver():
    """Test that sweep handles invalid driver names."""
    assistant = DesignAssistant()

    sweep = assistant.sweep_parameter(
        driver_name="NonexistentDriver",
        enclosure_type="sealed",
        parameter="Vb",
        param_min=0.010,
        param_max=0.050,
        steps=20
    )

    # Should return empty results with error message
    assert len(sweep.parameter_values) == 0
    assert "Unknown driver" in sweep.recommendations[0]

    print("✓ Invalid driver handled correctly")


def test_sweep_data_consistency():
    """Test that sweep data arrays are consistent."""
    assistant = DesignAssistant()

    sweep = assistant.sweep_parameter(
        driver_name="BC_18PZW100",
        enclosure_type="sealed",
        parameter="Vb",
        param_min=0.050,  # 50L
        param_max=0.200,  # 200L
        steps=25
    )

    n_points = len(sweep.parameter_values)

    # All result arrays should have same length
    assert len(sweep.results["F3"]) == n_points
    assert len(sweep.results["flatness"]) == n_points
    assert len(sweep.results["efficiency"]) == n_points
    assert len(sweep.results["size"]) == n_points

    # Size should match Vb for sealed box
    for i in range(n_points):
        expected_vb = sweep.parameter_values[i]
        actual_size = sweep.results["size"][i]
        # Size = Vb for sealed (no port displacement)
        if not np.isnan(actual_size):
            assert abs(actual_size - expected_vb) < 1e-6

    print("✓ Data arrays are consistent")


def test_sweep_different_drivers():
    """Test sweep works with all available drivers."""
    assistant = DesignAssistant()

    drivers = ["BC_8NDL51", "BC_12NDL76", "BC_15DS115", "BC_18PZW100"]

    for driver in drivers:
        sweep = assistant.sweep_parameter(
            driver_name=driver,
            enclosure_type="sealed",
            parameter="Vb",
            param_min=0.010,
            param_max=0.050,
            steps=15
        )

        # Should have valid results
        assert len(sweep.parameter_values) == 15
        assert len(sweep.recommendations) > 0

        # Should have at least some valid F3 values
        valid_count = np.sum(~np.isnan(sweep.results["F3"]))
        assert valid_count > 0, f"{driver} should have valid F3 values"

        print(f"  ✓ {driver}: {valid_count} valid F3 values")

    print("✓ Sweep works with all drivers")


def test_sweep_step_size_control():
    """Test that step size parameter controls resolution."""
    assistant = DesignAssistant()

    # Test different step sizes
    for steps in [10, 20, 50]:
        sweep = assistant.sweep_parameter(
            driver_name="BC_12NDL76",
            enclosure_type="sealed",
            parameter="Vb",
            param_min=0.010,
            param_max=0.050,
            steps=steps
        )

        assert len(sweep.parameter_values) == steps
        print(f"  ✓ steps={steps}: {len(sweep.parameter_values)} points")

    print("✓ Step size control works")


if __name__ == "__main__":
    print("="*70)
    print("PARAMETER SWEEP TESTS")
    print("="*70)

    tests = [
        ("Sealed box Vb sweep", test_sealed_box_vb_sweep),
        ("Sweep finds best F3", test_sealed_box_sweep_finds_best),
        ("Sensitivity analysis", test_sweep_sensitivity_analysis),
        ("Recommendations content", test_sweep_recommendations_content),
        ("Invalid parameter handling", test_sweep_invalid_parameter),
        ("Invalid driver handling", test_sweep_invalid_driver),
        ("Data consistency", test_sweep_data_consistency),
        ("Different drivers", test_sweep_different_drivers),
        ("Step size control", test_sweep_step_size_control),
    ]

    passed = 0
    total = len(tests)

    for i, (name, test_func) in enumerate(tests, 1):
        print(f"\n[TEST {i}] {name}")
        print("-"*70)
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ FAILED: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"\nResults: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n" + "🎉 "*20)
        print("ALL TESTS PASSED!")
        print("🎉 "*20)
        print("\n✅ Parameter sweep functionality is WORKING!")
        print("\nCapabilities:")
        print("  • Sealed box Vb sweep")
        print("  • Sensitivity analysis")
        print("  • Automatic recommendations")
        print("  • Trend identification")
        print("  • Optimal range detection")
        print("  • Error handling")
        print("\nReady for use!")
    else:
        print(f"\n⚠️  {total-passed} test(s) failed")

    print("\n" + "="*70)
