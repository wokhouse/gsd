"""
Unit tests for constraint functions.

Tests for constraint functions that ensure optimized designs satisfy
physical and performance requirements.
"""

import numpy as np
import pytest

from gsd.driver import load_driver
from gsd.optimization.constraints.physical import (
    constraint_total_length,
    constraint_multisegment_continuity,
    constraint_multisegment_flare_limits,
)
from gsd.optimization.parameters.multisegment_horn_params import (
    get_multisegment_horn_parameter_space,
)


def test_constraint_total_length_symmetric():
    """Test total_length constraint with symmetric segment lengths."""
    driver = load_driver("BC_DH450")

    # Symmetric design: 12.5cm + 12.5cm = 25cm
    design = np.array([0.000212, 0.010, 0.04084, 0.125, 0.125, 0.0])

    violation = constraint_total_length(
        design, driver, "multisegment_horn",
        max_length=0.25, num_segments=2
    )

    # Should be satisfied (total = 25cm, max = 25cm)
    # Return value is total - max = 0.25 - 0.25 = 0.0
    assert violation == 0.0, f"Expected 0.0, got {violation}"


def test_constraint_total_length_asymmetric():
    """Test total_length constraint with asymmetric segment lengths."""
    driver = load_driver("BC_DH450")

    # Asymmetric design: 18cm + 7cm = 25cm
    design = np.array([0.000212, 0.010, 0.04084, 0.18, 0.07, 0.0])

    violation = constraint_total_length(
        design, driver, "multisegment_horn",
        max_length=0.25, num_segments=2
    )

    # Should be satisfied (total = 25cm, max = 25cm)
    assert abs(violation) < 1e-6, f"Expected ~0.0, got {violation}"


def test_constraint_total_length_exceeds():
    """Test total_length constraint when design exceeds max_length."""
    driver = load_driver("BC_DH450")

    # Design exceeds limit: 20cm + 15cm = 35cm > 25cm
    design = np.array([0.000212, 0.010, 0.04084, 0.20, 0.15, 0.0])

    violation = constraint_total_length(
        design, driver, "multisegment_horn",
        max_length=0.25, num_segments=2
    )

    # Should be violated (total = 35cm, max = 25cm, violation = 0.10)
    assert violation > 0, f"Expected positive violation, got {violation}"
    assert abs(violation - 0.10) < 1e-6, f"Expected 0.10, got {violation}"


def test_constraint_total_length_under():
    """Test total_length constraint when design is under max_length."""
    driver = load_driver("BC_DH450")

    # Design under limit: 10cm + 10cm = 20cm < 25cm
    design = np.array([0.000212, 0.010, 0.04084, 0.10, 0.10, 0.0])

    violation = constraint_total_length(
        design, driver, "multisegment_horn",
        max_length=0.25, num_segments=2
    )

    # Should be satisfied (total = 20cm, max = 25cm, violation = -0.05)
    assert violation < 0, f"Expected negative violation, got {violation}"


def test_constraint_total_length_3_segment():
    """Test total_length constraint with 3 segments."""
    driver = load_driver("BC_DH450")

    # 3-segment design: 8cm + 8cm + 9cm = 25cm
    design = np.array([
        0.000212, 0.010, 0.025, 0.04084,  # areas
        0.08, 0.08, 0.09,  # lengths
        0.0  # V_tc
    ])

    violation = constraint_total_length(
        design, driver, "multisegment_horn",
        max_length=0.25, num_segments=3
    )

    # Should be satisfied (total = 25cm, max = 25cm)
    assert abs(violation) < 1e-6, f"Expected ~0.0, got {violation}"


def test_constraint_total_length_not_applicable():
    """Test total_length constraint returns 0 for non-multisegment horns."""
    driver = load_driver("BC_DH450")

    design = np.array([0.001, 0.10, 1.5, 0.0, 0.0])  # Exponential horn

    violation = constraint_total_length(
        design, driver, "exponential_horn",
        max_length=0.25, num_segments=2
    )

    # Should return 0 (not applicable)
    assert violation == 0.0, f"Expected 0.0 for non-applicable, got {violation}"


def test_multisegment_parameter_space_max_length_constraint():
    """Test that max_length constraint is properly added to parameter space."""
    driver = load_driver("BC_DH450")

    param_space = get_multisegment_horn_parameter_space(
        driver,
        preset="midrange_horn",
        num_segments=2,
        max_length=0.25  # 250mm total length
    )

    # Check that total_length constraint is in the list
    assert "total_length" in param_space.constraints, \
        "total_length constraint should be added when max_length is specified"

    # Check that max_length is in metadata
    assert param_space.metadata.get("max_length") == 0.25, \
        "max_length should be stored in metadata"

    # Check that num_segments is in metadata
    assert param_space.metadata.get("num_segments") == 2, \
        "num_segments should be stored in metadata"


def test_multisegment_parameter_space_no_max_length():
    """Test parameter space without max_length constraint."""
    driver = load_driver("BC_DH450")

    param_space = get_multisegment_horn_parameter_space(
        driver,
        preset="midrange_horn",
        num_segments=2
    )

    # Check that total_length constraint is NOT in the list
    assert "total_length" not in param_space.constraints, \
        "total_length constraint should NOT be added when max_length is not specified"

    # Check that max_length is None in metadata
    assert param_space.metadata.get("max_length") is None, \
        "max_length should be None in metadata when not specified"


def test_multisegment_parameter_space_max_mouth_area_constraint():
    """Test that max_mouth_area constraint properly limits mouth area."""
    driver = load_driver("BC_DH450")

    # Apply max_mouth_area constraint
    param_space = get_multisegment_horn_parameter_space(
        driver,
        preset="midrange_horn",
        num_segments=2,
        max_mouth_area=0.05  # 500 cm² (smaller than preset default of 600 cm²)
    )

    # Find mouth_area parameter
    mouth_param = next(p for p in param_space.parameters if p.name == "mouth_area")

    # Check that mouth_max is clamped to max_mouth_area
    assert mouth_param.max_value <= 0.05, \
        f"mouth_max should be <= 0.05, got {mouth_param.max_value}"


def test_multisegment_parameter_space_asymmetric_lengths_enabled():
    """Test that parameter space allows asymmetric segment lengths."""
    driver = load_driver("BC_DH450")

    param_space = get_multisegment_horn_parameter_space(
        driver,
        preset="midrange_horn",
        num_segments=2,
        max_length=0.25  # 250mm total length
    )

    # Find length parameters
    length1_param = next(p for p in param_space.parameters if p.name == "length1")
    length2_param = next(p for p in param_space.parameters if p.name == "length2")

    # Both length1 and length2 should have the full preset range
    # NOT clamped to max_length/2 (which would be 0.125)
    # The constraint function enforces total length, not per-segment bounds
    assert length1_param.max_value > 0.125, \
        f"length1 max should be > 0.125 (asymmetric allowed), got {length1_param.max_value}"
    assert length2_param.max_value > 0.125, \
        f"length2 max should be > 0.125 (asymmetric allowed), got {length2_param.max_value}"

    # Verify the preset range is preserved (should be 0.6 for midrange_horn)
    assert abs(length1_param.max_value - 0.6) < 1e-6, \
        f"length1 max should preserve preset value (0.6), got {length1_param.max_value}"


def test_constraint_continuity_still_works():
    """Test that segment_continuity constraint still works correctly."""
    driver = load_driver("BC_DH450")

    # Good design: throat < middle < mouth
    design = np.array([0.000212, 0.010, 0.04084, 0.20, 0.394, 0.0])
    violation = constraint_multisegment_continuity(
        design, driver, "multisegment_horn", num_segments=2
    )
    assert violation < 0, "Should satisfy continuity constraint"

    # Bad design: middle > mouth (not monotonic)
    design_bad = np.array([0.000212, 0.04084, 0.010, 0.20, 0.394, 0.0])
    violation_bad = constraint_multisegment_continuity(
        design_bad, driver, "multisegment_horn", num_segments=2
    )
    assert violation_bad > 0, "Should violate continuity constraint"


def test_constraint_f3_limit_still_works():
    """Test that other constraint functions still work."""
    driver = load_driver("BC_DH450")

    # Design with reasonable flare rates
    design = np.array([0.000212, 0.010, 0.04084, 0.20, 0.394, 0.0])
    violation = constraint_multisegment_flare_limits(
        design, driver, "multisegment_horn", num_segments=2
    )
    # Should satisfy the constraint (negative or zero)
    assert violation <= 0, f"Should satisfy flare limits constraint, got {violation}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
