"""
Horn Profile Export Module

Exports exponential horn profiles to DXF format for CAD/CAM software
and 3D printing.

Literature:
- Olson (1947) - Exponential horn theory
- Beranek (1954) - Horn impedance calculations
"""

import numpy as np
from typing import Tuple, Optional
from pathlib import Path


def calculate_exponential_horn_profile(
    throat_area_cm2: float,
    mouth_area_cm2: float,
    length_cm: float,
    num_points: int = 100
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    """
    Calculate exponential horn profile.

    For an exponential horn, the area varies as:
        S(x) = S_t * exp(m * x)

    where:
        S_t = throat area
        m = flare constant = ln(S_m/S_t) / L
        S_m = mouth area
        L = horn length

    The radius at each point is: r(x) = sqrt(S(x) / π)

    Literature:
        - Olson (1947), Section 5.4 - Exponential horn theory
        - Beranek (1954), Chapter 5 - Horn profiles

    Args:
        throat_area_cm2: Throat area (cm²)
        mouth_area_cm2: Mouth area (cm²)
        length_cm: Horn length (cm)
        num_points: Number of points along horn length

    Returns:
        (x_cm, radius_cm, area_cm2, fc_hz, m) - Position, radius, area,
        cutoff frequency, and flare constant

    Example:
        >>> x, r, a, fc, m = calculate_exponential_horn_profile(5.07, 491, 25)
        >>> print(f"Fc = {fc:.0f} Hz")
        499
    """
    # Convert to consistent units (cm)
    S_t = throat_area_cm2
    S_m = mouth_area_cm2
    L = length_cm

    # Calculate flare constant
    # From exponential horn definition: S_m = S_t * exp(m * L)
    # Solving: m = ln(S_m / S_t) / L
    m = np.log(S_m / S_t) / L

    # Generate position array
    x = np.linspace(0, L, num_points)

    # Calculate area at each point: S(x) = S_t * exp(m * x)
    area = S_t * np.exp(m * x)

    # Calculate radius: r = sqrt(S / π)
    radius = np.sqrt(area / np.pi)

    # Calculate cutoff frequency
    # From Olson Eq. 5.18: Fc = (c * m) / (2π)
    # Note: Olson's m is defined as S(x) = S_t * exp(m*x)
    # Kolbrek's m uses S(x) = S_t * exp(2*m*x), hence factor of 2 difference
    # Literature: Olson (1947), Eq. 5.18; implementation_guide.md
    c = 34300  # cm/s at 20°C
    fc = (c * m) / (2 * np.pi)

    return x, radius, area, fc, m


def export_horn_profile_dxf(
    throat_area_cm2: float,
    mouth_area_cm2: float,
    length_cm: float,
    output_path: Path,
    num_points: int = 100,
    title: str = "Horn Profile"
) -> Path:
    """
    Export exponential horn profile to DXF format.

    Creates a 2D profile showing:
    - Centerline
    - Upper wall (exponential curve)
    - Lower wall (mirror image)
    - Cross-section lines at intervals
    - Dimensions and annotations

    Args:
        throat_area_cm2: Throat area (cm²)
        mouth_area_cm2: Mouth area (cm²)
        length_cm: Horn length (cm)
        output_path: Output DXF file path
        num_points: Number of points along horn length
        title: Title for the DXF file

    Returns:
        Path to exported DXF file

    Raises:
        ImportError: If ezdxf is not installed
        OSError: If output file cannot be written

    Example:
        >>> export_horn_profile_dxf(
        ...     5.07, 491, 25,
        ...     Path("horn_profile.dxf")
        ... )
        PosixPath('horn_profile.dxf')
    """
    try:
        import ezdxf
        from ezdxf import colors
    except ImportError:
        raise ImportError(
            "ezdxf library is required for DXF export. "
            "Install with: pip install ezdxf"
        )

    # Calculate horn profile
    x_cm, radius_cm, area_cm2, fc_hz, m = calculate_exponential_horn_profile(
        throat_area_cm2,
        mouth_area_cm2,
        length_cm,
        num_points
    )

    # Create new DXF document
    doc = ezdxf.new('R2010', setup=True)
    msp = doc.modelspace()

    # Create layers
    doc.layers.add('CENTERLINE', dxfattribs={'color': colors.RED})
    doc.layers.add('WALL', dxfattribs={'color': colors.WHITE})
    doc.layers.add('CROSS_SECTION', dxfattribs={'color': colors.CYAN})
    doc.layers.add('DIMENSIONS', dxfattribs={'color': colors.GREEN})
    doc.layers.add('TEXT', dxfattribs={'color': colors.YELLOW})

    # Scale factor (convert cm to mm for typical CNC)
    scale = 10.0  # 1 cm = 10 mm

    # Centerline
    msp.add_line(
        (0, 0),
        (x_cm[-1] * scale, 0),
        dxfattribs={'layer': 'CENTERLINE'}
    )

    # Upper wall (horn profile)
    upper_wall = [(x * scale, r * scale) for x, r in zip(x_cm, radius_cm)]
    msp.add_lwpolyline(upper_wall, dxfattribs={'layer': 'WALL'})

    # Lower wall (mirror image)
    lower_wall = [(x * scale, -r * scale) for x, r in zip(x_cm, radius_cm)]
    msp.add_lwpolyline(lower_wall, dxfattribs={'layer': 'WALL'})

    # Cross-section lines (every 10% of length)
    num_sections = 10
    indices = np.linspace(0, len(x_cm) - 1, num_sections, dtype=int)
    for i in indices:
        x_pos = x_cm[i] * scale
        y_pos = radius_cm[i] * scale
        msp.add_line(
            (x_pos, -y_pos),
            (x_pos, y_pos),
            dxfattribs={'layer': 'CROSS_SECTION'}
        )

    # Add dimensions
    text_height = 2.5  # mm

    # Length dimension
    msp.add_text(
        f"Length: {x_cm[-1]:.1f} cm",
        dxfattribs={
            'layer': 'TEXT',
            'height': text_height,
            'insert': (x_cm[-1] * scale / 2, radius_cm[-1] * scale + 20)
        }
    )

    # Throat radius
    msp.add_text(
        f"Throat: {radius_cm[0]:.2f} cm",
        dxfattribs={
            'layer': 'TEXT',
            'height': text_height,
            'insert': (10, radius_cm[0] * scale + 10)
        }
    )

    # Mouth radius
    mouth_diameter_cm = 2 * radius_cm[-1]
    msp.add_text(
        f"Mouth: Ø{mouth_diameter_cm:.1f} cm",
        dxfattribs={
            'layer': 'TEXT',
            'height': text_height,
            'insert': (x_cm[-1] * scale - 50, radius_cm[-1] * scale + 10)
        }
    )

    # Add title block
    title_y = radius_cm[-1] * scale + 40
    msp.add_text(
        title,
        dxfattribs={
            'layer': 'TEXT',
            'height': text_height * 1.5,
            'insert': (0, title_y)
        }
    )

    msp.add_text(
        f"Throat: {throat_area_cm2} cm²  |  Mouth: {mouth_area_cm2:.1f} cm²  |  Length: {length_cm} cm",
        dxfattribs={
            'layer': 'TEXT',
            'height': text_height * 0.8,
            'insert': (0, title_y - 8)
        }
    )

    msp.add_text(
        f"F c = {fc_hz:.0f} Hz",
        dxfattribs={
            'layer': 'TEXT',
            'height': text_height * 0.8,
            'insert': (0, title_y - 16)
        }
    )

    # Save file
    try:
        doc.saveas(output_path)
    except OSError as e:
        raise OSError(f"Failed to write DXF file to {output_path}: {e}")

    return output_path


def export_horn_profile_csv(
    throat_area_cm2: float,
    mouth_area_cm2: float,
    length_cm: float,
    output_path: Path,
    num_points: int = 100
) -> Path:
    """
    Export exponential horn profile to CSV format (fallback).

    Creates a CSV file with columns:
    - Position (cm)
    - Radius (cm)
    - Area (cm²)

    Args:
        throat_area_cm2: Throat area (cm²)
        mouth_area_cm2: Mouth area (cm²)
        length_cm: Horn length (cm)
        output_path: Output CSV file path
        num_points: Number of points along horn length

    Returns:
        Path to exported CSV file

    Example:
        >>> export_horn_profile_csv(5.07, 491, 25, Path("horn.csv"))
        PosixPath('horn.csv')
    """
    # Calculate horn profile
    x_cm, radius_cm, area_cm2, fc_hz, m = calculate_exponential_horn_profile(
        throat_area_cm2,
        mouth_area_cm2,
        length_cm,
        num_points
    )

    # Write CSV
    with open(output_path, 'w') as f:
        f.write("# Exponential Horn Profile\n")
        f.write("# Generated by GSD horn optimizer\n")
        f.write(f"# Throat: {throat_area_cm2} cm²\n")
        f.write(f"# Mouth: {mouth_area_cm2:.1f} cm²\n")
        f.write(f"# Length: {length_cm} cm\n")
        f.write(f"# Fc: {fc_hz:.0f} Hz\n")
        f.write("#\n")
        f.write("# Position (cm), Radius (cm), Area (cm²)\n")

        for i, (pos, rad, area) in enumerate(zip(x_cm, radius_cm, area_cm2)):
            f.write(f"{pos:.3f}, {rad:.3f}, {area:.3f}\n")

    return output_path


def export_horn_profile(
    throat_area_cm2: float,
    mouth_area_cm2: float,
    length_cm: float,
    output_file: str,
    format: str = 'dxf',
    **kwargs
) -> Path:
    """
    Export horn profile to specified format.

    This is the main export function that routes to the appropriate
    exporter based on the requested format.

    Args:
        throat_area_cm2: Throat area (cm²)
        mouth_area_cm2: Mouth area (cm²)
        length_cm: Horn length (cm)
        output_file: Output file path (with or without extension)
        format: Export format ('dxf' or 'csv')
        **kwargs: Additional arguments passed to exporter

    Returns:
        Path to exported file

    Raises:
        ValueError: If format is not supported

    Example:
        >>> export_horn_profile(5.07, 491, 25, "my_horn", format='dxf')
        PosixPath('my_horn.dxf')

        >>> export_horn_profile(5.07, 491, 25, "my_horn.csv", format='csv')
        PosixPath('my_horn.csv')
    """
    output_path = Path(output_file)

    # Add extension if not present
    if output_path.suffix == '':
        if format == 'dxf':
            output_path = output_path.with_suffix('.dxf')
        elif format == 'csv':
            output_path = output_path.with_suffix('.csv')

    # Route to appropriate exporter
    if format.lower() == 'dxf':
        return export_horn_profile_dxf(
            throat_area_cm2,
            mouth_area_cm2,
            length_cm,
            output_path,
            **kwargs
        )
    elif format.lower() == 'csv':
        return export_horn_profile_csv(
            throat_area_cm2,
            mouth_area_cm2,
            length_cm,
            output_path,
            **kwargs
        )
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'dxf' or 'csv'.")
