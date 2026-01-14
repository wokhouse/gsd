"""
Interactive decision tree guide for two-way system design.

This module provides an interactive helper that asks user questions and
recommends design strategy based on their requirements.

Literature:
- Olson (1947) - Horn cutoff and operating range
- Beranek (1954) - Directivity and beaming
- Case study: docs/two_way_design_review_12fw88_dh450.md
"""

import sys
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

from gsd.driver import load_driver
from gsd.optimization.api.horn_physics import (
    calculate_lf_beaming_frequency,
    calculate_target_horn_fc,
    calculate_mouth_area_for_fc,
    calculate_fc_from_mouth,
    assess_mouth_area_feasibility
)


# =============================================================================
# PRINTER CONSTRAINT PRESETS
# =============================================================================

PRINTER_PRESETS = {
    "250mm_cube": {
        "max_length": 0.25,  # 25 cm
        "max_mouth_area": 0.0625,  # 625 cm² (25×25 cm)
    },
    "500mm_cube": {
        "max_length": 0.50,  # 50 cm
        "max_mouth_area": 0.25,  # 2500 cm² (50×50 cm)
    },
    "large_format": {
        "max_length": 1.0,  # 100 cm
        "max_mouth_area": 1.0,  # 10000 cm² (100×100 cm)
    }
}


@dataclass
class DesignRecommendation:
    """
    Result of interactive design guide.

    Attributes:
        lf_driver_name: Low-frequency driver name
        hf_driver_name: High-frequency driver name
        target_crossover_hz: Recommended crossover frequency (Hz)
        printer_constraints: Printer size constraints
        xo_fc_ratio: Recommended XO/Fc ratio
        accept_sensitivity_loss: Whether to accept HF sensitivity loss
        enclosure_type: "ported" or "sealed"
        reasoning: Explanation of recommendations
        trade_offs: Description of trade-offs
    """
    lf_driver_name: str
    hf_driver_name: str
    target_crossover_hz: float
    printer_constraints: Dict[str, float]
    xo_fc_ratio: float
    accept_sensitivity_loss: bool
    enclosure_type: str
    reasoning: str
    trade_offs: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for passing to design_two_way_system_integrated()."""
        return {
            "lf_driver_name": self.lf_driver_name,
            "hf_driver_name": self.hf_driver_name,
            "target_crossover_hz": self.target_crossover_hz,
            "printer_constraints": self.printer_constraints,
            "enclosure_type": self.enclosure_type
        }


def _get_input(prompt: str, default: Any = None, validator = None) -> Any:
    """
    Get user input with validation.

    Args:
        prompt: Prompt text
        default: Default value if user presses Enter
        validator: Optional validation function (returns True if valid)

    Returns:
        Validated user input or default
    """
    if default is not None:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "

    while True:
        try:
            user_input = input(full_prompt).strip()

            if user_input == "" and default is not None:
                return default

            if validator is not None:
                if validator(user_input):
                    return user_input
                else:
                    print("  ❌ Invalid input. Please try again.")
            else:
                return user_input

        except KeyboardInterrupt:
            print("\n\n✗ Cancelled by user.")
            sys.exit(0)
        except EOFError:
            # Non-interactive mode, use default
            if default is not None:
                print(f"  Using default: {default}")
                return default
            else:
                print("\n  ❌ No default available. Exiting.")
                sys.exit(1)


def _yes_no_prompt(prompt: str, default: bool = False) -> bool:
    """
    Ask yes/no question.

    Args:
        prompt: Question text
        default: Default answer if user presses Enter

    Returns:
        True for yes, False for no
    """
    default_str = "Y" if default else "N"
    response = _get_input(prompt, default_str)

    return response.upper() in ['Y', 'YES', '1']


def _select_option(prompt: str, options: Dict[str, str], default: str = None) -> str:
    """
    Ask user to select from options.

    Args:
        prompt: Question text
        options: Dict of {key: description}
        default: Default key if user presses Enter

    Returns:
        Selected key
    """
    print(f"\n  {prompt}")
    for key, desc in options.items():
        default_marker = " (default)" if key == default else ""
        print(f"    {key}. {desc}{default_marker}")

    while True:
        choice = _get_input("  Select option", default)

        if choice in options:
            return choice
        else:
            print(f"  ❌ Invalid choice. Please select from: {', '.join(options.keys())}")


def guide_two_way_design_decisions(
    lf_driver_name: Optional[str] = None,
    hf_driver_name: Optional[str] = None,
    target_crossover_hz: Optional[float] = None,
    printer_preset: Optional[str] = None,
    enclosure_type: Optional[str] = None
) -> DesignRecommendation:
    """
    Interactive design guide that asks user questions and recommends strategy.

    This function walks the user through the key decisions in two-way system
    design, providing recommendations based on driver parameters and physics.

    Workflow:
    1. Ask for LF and HF drivers (with suggestions)
    2. Ask target crossover frequency (with suggestions based on LF driver)
    3. Ask printer constraints (with presets: 250mm cube, 500mm cube, custom)
    4. Ask priority: HF sensitivity vs crossover integration quality
    5. Calculate options and show trade-offs
    6. Ask if accept_sensitivity_loss=True should be used
    7. Return configuration dict for design_two_way_system_integrated()

    Args:
        lf_driver_name: LF driver name (non-interactive mode)
        hf_driver_name: HF driver name (non-interactive mode)
        target_crossover_hz: Target crossover in Hz (non-interactive mode)
        printer_preset: Printer preset name (non-interactive mode)
        enclosure_type: Enclosure type (non-interactive mode)

    Returns:
        DesignRecommendation with configuration and reasoning

    Example (interactive):
        >>> rec = guide_two_way_design_decisions()
        >>> # Follow prompts...
        >>> config = rec.to_dict()
        >>> design = design_two_way_system_integrated(**config)

    Example (non-interactive):
        >>> rec = guide_two_way_design_decisions(
        ...     lf_driver_name="BC_12FW88",
        ...     hf_driver_name="BC_DH450",
        ...     target_crossover_hz=800,
        ...     printer_preset="250mm_cube"
        ... )
        >>> design = design_two_way_system_integrated(**rec.to_dict())
    """
    from gsd.driver import list_drivers

    # ========================================================================
    # STEP 1: LF Driver Selection
    # ========================================================================

    print("\n" + "=" * 70)
    print("STEP 1: LF Driver Selection")
    print("=" * 70)

    available_drivers = list_drivers()

    if lf_driver_name is None:
        # Interactive mode
        print("\n  Available LF drivers:")
        lf_drivers = [d for d in available_drivers if not any(x in d for x in ['DH', 'DE', 'TD'])]
        for driver in lf_drivers[:10]:  # Show first 10
            print(f"    - {driver}")

        lf_driver_name = _get_input(
            "\n  Enter LF driver name",
            "BC_12FW88",
            lambda x: x in available_drivers
        )

    lf_driver = load_driver(lf_driver_name)
    f_beam = calculate_lf_beaming_frequency(lf_driver)

    print(f"  ✓ LF driver: {lf_driver_name}")
    print(f"  ✓ Beaming frequency: {f_beam:.0f} Hz")

    # ========================================================================
    # STEP 2: HF Driver Selection
    # ========================================================================

    print("\n" + "=" * 70)
    print("STEP 2: HF Driver Selection")
    print("=" * 70)

    if hf_driver_name is None:
        # Interactive mode
        print("\n  Available HF drivers:")
        hf_drivers = [d for d in available_drivers if any(x in d for x in ['DH', 'DE', 'TD'])]
        for driver in hf_drivers[:10]:  # Show first 10
            print(f"    - {driver}")

        hf_driver_name = _get_input(
            "\n  Enter HF driver name",
            "BC_DH450",
            lambda x: x in available_drivers
        )

    hf_driver = load_driver(hf_driver_name)

    print(f"  ✓ HF driver: {hf_driver_name}")

    # ========================================================================
    # STEP 3: Target Crossover Frequency
    # ========================================================================

    print("\n" + "=" * 70)
    print("STEP 3: Target Crossover Frequency")
    print("=" * 70)

    # Calculate suggested crossover range
    suggested_min = max(400, int(f_beam * 0.6))
    suggested_max = int(f_beam * 0.8)
    suggested_xo = (suggested_min + suggested_max) // 2

    print(f"\n  LF driver beaming: {f_beam:.0f} Hz")
    print(f"  Suggested crossover range: {suggested_min}-{suggested_max} Hz")
    print(f"  (Crossover should be < 0.8×beaming for flat response)")

    if target_crossover_hz is None:
        # Interactive mode
        target_crossover_hz = float(_get_input(
            f"\n  Enter target crossover frequency (Hz)",
            str(suggested_xo),
            lambda x: x.replace('.', '', 1).isdigit() and float(x) > 0
        ))

    # Cap at beaming if needed
    adjusted_xo = min(target_crossover_hz, 0.8 * f_beam)
    if adjusted_xo < target_crossover_hz:
        print(f"  ⚠ Target XO ({target_crossover_hz:.0f} Hz) > 0.8×beaming")
        print(f"  → Will use {adjusted_xo:.0f} Hz for best integration")
        target_crossover_hz = adjusted_xo

    print(f"  ✓ Target crossover: {target_crossover_hz:.0f} Hz")

    # ========================================================================
    # STEP 4: Printer Constraints
    # ========================================================================

    print("\n" + "=" * 70)
    print("STEP 4: Printer Constraints")
    print("=" * 70)

    printer_constraints = {}

    if printer_preset is None:
        # Interactive mode
        print("\n  Common printer presets:")
        print("    1. 250mm_cube (250×250×250mm)")
        print("    2. 500mm_cube (500×500×500mm)")
        print("    3. large_format (1000×1000×1000mm)")
        print("    4. custom")

        choice = _get_input("\n  Select preset", "1")

        if choice == "1":
            printer_preset = "250mm_cube"
        elif choice == "2":
            printer_preset = "500mm_cube"
        elif choice == "3":
            printer_preset = "large_format"
        else:
            printer_preset = "custom"

    if printer_preset == "custom":
        max_length = float(_get_input("  Max horn length (m)", "0.25"))
        max_mouth = float(_get_input("  Max mouth area (m²)", "0.0625"))
        printer_constraints = {
            "max_length": max_length,
            "max_mouth_area": max_mouth
        }
    else:
        printer_constraints = PRINTER_PRESETS[printer_preset].copy()

    print(f"  ✓ Max length: {printer_constraints['max_length']*100:.0f} cm")
    print(f"  ✓ Max mouth: {printer_constraints['max_mouth_area']*10000:.0f} cm²")

    # ========================================================================
    # STEP 5: Design Priority (HF Sensitivity vs Integration)
    # ========================================================================

    print("\n" + "=" * 70)
    print("STEP 5: Design Priority")
    print("=" * 70)

    # Check if we're in non-interactive mode (all parameters provided)
    non_interactive_mode = (
        lf_driver_name is not None and
        hf_driver_name is not None and
        target_crossover_hz is not None and
        printer_preset is not None and
        enclosure_type is not None
    )

    if non_interactive_mode:
        # Non-interactive mode: default to best integration
        priority_choice = "1"
    else:
        # Interactive mode: ask user
        print("\n  What's your priority?")
        print("    1. Best crossover integration (may sacrifice HF sensitivity)")
        print("    2. Max HF sensitivity (may require compromise on integration)")

        priority_choice = _get_input("\n  Select priority", "1")

    if priority_choice == "1":
        # Priority: Integration quality
        xo_fc_ratio = 1.3  # Optimized ratio
        priority_desc = "Best integration quality"
        print("\n  → Will use optimized XO/Fc ratio (1.2-1.5)")
        print("  → Horn will operate closer to cutoff for better integration")
    else:
        # Priority: HF sensitivity
        xo_fc_ratio = 2.0  # Traditional ratio
        priority_desc = "Max HF sensitivity"
        print("\n  → Will use traditional 2×Fc rule")
        print("  → Larger mouth for better HF sensitivity")

    # ========================================================================
    # STEP 6: Calculate Requirements and Check Feasibility
    # ========================================================================

    print("\n" + "=" * 70)
    print("STEP 6: Horn Requirements Analysis")
    print("=" * 70)

    # Calculate target Fc
    target_fc = calculate_target_horn_fc(
        target_crossover_hz,
        f_beam,
        xo_fc_ratio
    )

    # Calculate required mouth
    throat_area = hf_driver.S_d * 10000  # m² to cm²
    max_length = printer_constraints["max_length"]
    max_mouth_area = printer_constraints["max_mouth_area"]

    required_mouth = calculate_mouth_area_for_fc(
        throat_area,
        max_length * 100,  # m to cm
        target_fc
    )

    print(f"\n  Target XO: {target_crossover_hz:.0f} Hz")
    print(f"  Target Fc: {target_fc:.0f} Hz (XO/Fc = {target_crossover_hz/target_fc:.2f})")
    print(f"  Required mouth: {required_mouth:.0f} cm²")
    print(f"  Available mouth: {max_mouth_area*10000:.0f} cm²")

    # Check feasibility
    feasibility = assess_mouth_area_feasibility(
        required_mouth,
        max_mouth_area * 10000,
        target_fc,
        throat_area,
        max_length * 100
    )

    # ========================================================================
    # STEP 7: Handle Infeasibility
    # ========================================================================

    accept_sensitivity_loss = False

    if not feasibility.feasible:
        print("\n  ⚠ CONSTRAINT VIOLATION DETECTED")
        print("\n" + feasibility.recommendation)

        print("\n  Trade-off analysis:")
        print(f"    • Required mouth: {required_mouth:.0f} cm²")
        print(f"    • Available mouth: {max_mouth_area*10000:.0f} cm²")
        print(f"    • Resulting Fc with max mouth: {feasibility.resulting_fc_hz:.0f} Hz")
        print(f"    • Sensitivity penalty: {feasibility.sensitivity_penalty_db:+.1f} dB")

        if non_interactive_mode:
            # In non-interactive mode, accept sensitivity loss automatically
            # (User can set accept_sensitivity_loss parameter if needed in future)
            print("\n  ⚠ Non-interactive mode: Auto-accepting sensitivity loss")
            accept_loss = True
        else:
            # Ask if user accepts sensitivity loss
            accept_loss = _yes_no_prompt(
                f"\n  Accept {feasibility.sensitivity_penalty_db:+.1f} dB sensitivity loss for better integration?",
                default=False
            )

        if not accept_loss:
            print("\n  → Design not feasible with current constraints.")
            print("  → Options:")
            print("    1. Use larger printer")
            print("    2. Use multi-piece horn (2-4 sections)")
            print("    3. Accept higher crossover frequency")
            print("    4. Accept sensitivity loss")
            sys.exit(1)
        else:
            accept_sensitivity_loss = True
            print(f"\n  ✓ Proceeding with {feasibility.sensitivity_penalty_db:+.1f} dB sensitivity loss")
    else:
        print("\n  ✓ Design is FEASIBLE within constraints")

    # ========================================================================
    # STEP 8: Enclosure Type
    # ========================================================================

    print("\n" + "=" * 70)
    print("STEP 7: Enclosure Type")
    print("=" * 70)

    if enclosure_type is None:
        print("\n  Select LF enclosure type:")
        print("    1. Ported (deeper bass, larger box)")
        print("    2. Sealed (tighter bass, smaller box)")

        enc_choice = _get_input("\n  Select type", "1")
        enclosure_type = "ported" if enc_choice == "1" else "sealed"

    print(f"  ✓ Enclosure: {enclosure_type}")

    # ========================================================================
    # STEP 9: Generate Recommendation
    # ========================================================================

    # Build reasoning string
    reasoning_lines = [
        f"Design Strategy for {lf_driver_name} + {hf_driver_name}",
        "=" * 70,
        "",
        f"**Crossover Strategy:**",
        f"  • Target XO: {target_crossover_hz:.0f} Hz (< 0.8×beaming at {f_beam:.0f} Hz)",
        f"  • Target Fc: {target_fc:.0f} Hz (XO/Fc ratio: {target_crossover_hz/target_fc:.2f})",
        f"  • Priority: {priority_desc}",
        "",
        f"**Horn Design:**",
        f"  • Length: {max_length*100:.0f} cm (printer constraint)",
        f"  • Throat: {throat_area:.1f} cm² (from {hf_driver_name})",
    ]

    if feasibility.feasible:
        reasoning_lines.extend([
            f"  • Mouth: {required_mouth:.0f} cm² (fits constraint)",
            f"  • Status: ✅ FEASIBLE",
        ])
    else:
        reasoning_lines.extend([
            f"  • Required mouth: {required_mouth:.0f} cm²",
            f"  • Max mouth: {max_mouth_area*10000:.0f} cm²",
            f"  • Actual Fc: {feasibility.resulting_fc_hz:.0f} Hz",
            f"  • Sensitivity loss: {feasibility.sensitivity_penalty_db:+.1f} dB",
            f"  • Status: ⚠️ ACCEPTED with trade-off",
        ])

    # Build trade-offs string
    if feasibility.feasible:
        trade_offs = (
            f"**Design fits within printer constraints.**\n\n"
            f"Trade-offs:\n"
            f"  • XO/Fc ratio of {target_crossover_hz/target_fc:.2f} balances integration and sensitivity\n"
            f"  • Horn operates {target_crossover_hz/target_fc:.1f}× above cutoff (optimal range: 1.2-2.0)"
        )
    else:
        actual_fc = feasibility.resulting_fc_hz
        actual_xo_fc_ratio = target_crossover_hz / actual_fc
        trade_offs = (
            f"**Design requires compromise due to printer constraints.**\n\n"
            f"Trade-offs:\n"
            f"  • Smaller mouth ({max_mouth_area*10000:.0f} cm² vs {required_mouth:.0f} cm² required)\n"
            f"  • Higher Fc ({actual_fc:.0f} Hz vs {target_fc:.0f} Hz target)\n"
            f"  • XO/Fc ratio of {actual_xo_fc_ratio:.2f} (lower than {target_crossover_hz/target_fc:.2f} target)\n"
            f"  • {feasibility.sensitivity_penalty_db:+.1f} dB HF sensitivity loss\n"
            f"  • Better crossover integration (lower XO possible)"
        )

    reasoning = "\n".join(reasoning_lines)

    return DesignRecommendation(
        lf_driver_name=lf_driver_name,
        hf_driver_name=hf_driver_name,
        target_crossover_hz=target_crossover_hz,
        printer_constraints=printer_constraints,
        xo_fc_ratio=xo_fc_ratio,
        accept_sensitivity_loss=accept_sensitivity_loss,
        enclosure_type=enclosure_type,
        reasoning=reasoning,
        trade_offs=trade_offs
    )


def print_recommendation_summary(recommendation: DesignRecommendation) -> None:
    """
    Print formatted recommendation summary.

    Args:
        recommendation: DesignRecommendation from guide_two_way_design_decisions()
    """
    print("\n" + "=" * 70)
    print("DESIGN RECOMMENDATION SUMMARY")
    print("=" * 70)
    print(recommendation.reasoning)
    print("\n" + "-" * 70)
    print("TRADE-OFFS")
    print("-" * 70)
    print(recommendation.trade_offs)
    print("\n" + "=" * 70)

    # Show how to use
    print("\nTo generate the design, run:")
    print("  from gsd.optimization.api.two_way_system import design_two_way_system_integrated")
    print("  design = design_two_way_system_integrated(**config)")
    print("=" * 70 + "\n")
