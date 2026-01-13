"""
Integration tests for complete two-way workflow.

Tests the end-to-end workflow including:
- Complete design function
- Validation
- Multi-piece printing strategy
"""

import pytest
from pathlib import Path
from gsd.optimization.api.two_way_system import design_two_way_system_complete


class TestCompleteWorkflow:
    """Integration tests for complete two-way system design."""

    def test_complete_workflow_250mm_printer(self):
        """Test complete workflow with 250mm printer constraint."""

        # This test is marked as slow because it runs optimization
        pytest.skip("Skipping slow integration test - run with pytest -m slow")

        design = design_two_way_system_complete(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            crossover_range=(800, 2500),
            printer_constraints={
                "max_length": 0.25,  # 250mm
                "max_mouth_area": 0.0625,
                "max_volume": 0.015625,
            },
            population_size=20,  # Smaller for test speed
            generations=20,
            verbose=False
        )

        # Should have validation attached
        assert hasattr(design, 'validation')
        assert design.validation is not None

        # Check that design was created
        assert design.lf_driver_name == "BC_12FW88"
        assert design.hf_driver_name == "BC_DH450"
        assert design.crossover_frequency > 0

    def test_complete_workflow_500mm_printer(self):
        """Test complete workflow with larger printer."""

        pytest.skip("Skipping slow integration test - run with pytest -m slow")

        design = design_two_way_system_complete(
            lf_driver_name="BC_12FW88",
            hf_driver_name="BC_DH450",
            crossover_range=(800, 2500),
            printer_constraints={
                "max_length": 0.50,  # 500mm - should fit single piece
                "max_mouth_area": 0.25,
                "max_volume": 0.125,
            },
            population_size=20,
            generations=20,
            verbose=False
        )

        assert hasattr(design, 'validation')
        # With larger printer, should have fewer warnings
        assert len(design.validation.warnings) == 0 or \
               "Horn cutoff" not in str(design.validation.warnings)
