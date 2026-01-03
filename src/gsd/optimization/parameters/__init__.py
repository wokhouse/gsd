"""
Parameter space definitions for enclosure optimization.

This module provides parameter bounds and design space definitions for
different enclosure types:
- Sealed box: Vb range based on driver Vas
- Ported box: Vb, Fb, port dimensions
- Horn: Throat area, mouth area, length, flare constant
- Multi-segment horn: Variable flare rate profiles

Parameter ranges are based on practical design limits from literature.
"""

from gsd.optimization.parameters.parameter_space import (
    ParameterRange,
    EnclosureParameterSpace,
)
from gsd.optimization.parameters.sealed_box_params import get_sealed_box_parameter_space
from gsd.optimization.parameters.ported_box_params import get_ported_box_parameter_space
from gsd.optimization.parameters.exponential_horn_params import (
    get_exponential_horn_parameter_space,
    calculate_horn_cutoff_frequency,
    calculate_horn_volume,
)
from gsd.optimization.parameters.multisegment_horn_params import (
    get_multisegment_horn_parameter_space,
    decode_multisegment_design,
    calculate_multisegment_horn_cutoff,
    calculate_multisegment_horn_volume,
)
from gsd.optimization.parameters.conical_horn_params import (
    get_conical_horn_parameter_space,
    calculate_conical_horn_volume,
    calculate_conical_expansion_ratio,
    decode_conical_design,
    build_conical_horn,
)
from gsd.optimization.parameters.multisegment_horn_params import (
    get_mixed_profile_parameter_space,
    decode_mixed_profile_design,
    build_mixed_profile_horn,
)

__all__ = [
    "ParameterRange",
    "EnclosureParameterSpace",
    "get_sealed_box_parameter_space",
    "get_ported_box_parameter_space",
    "get_exponential_horn_parameter_space",
    "calculate_horn_cutoff_frequency",
    "calculate_horn_volume",
    "get_multisegment_horn_parameter_space",
    "decode_multisegment_design",
    "calculate_multisegment_horn_cutoff",
    "calculate_multisegment_horn_volume",
    "get_conical_horn_parameter_space",
    "calculate_conical_horn_volume",
    "calculate_conical_expansion_ratio",
    "decode_conical_design",
    "build_conical_horn",
    "get_mixed_profile_parameter_space",
    "decode_mixed_profile_design",
    "build_mixed_profile_horn",
]
