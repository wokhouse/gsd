#!/usr/bin/env python3
"""
Analyze -3dB flatness deviation for the final system design.

Calculates:
1. Overall -3dB bandwidth (frequency range within 3dB of peak)
2. Flatness in crossover region (±1 octave around XO)
3. Detailed metrics at key frequencies
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
from pathlib import Path
import json

from gsd.driver import load_driver
from gsd.enclosure.ported_box import calculate_spl_ported_transfer_function
from gsd.optimization.api.two_way_system import (
    calculate_hf_horn_response,
    calculate_lr4_crossover_gains,
    calculate_f3_frequency,
    calculate_system_flatness,
)

rcParams['font.size'] = 11
rcParams['axes.labelsize'] = 12
rcParams['axes.titlesize'] = 14
rcParams['grid.alpha'] = 0.3


def load_final_design():
    """Load the final design parameters."""
    design_path = Path(__file__).parent / "final_design_floorstanding.json"

    if not design_path.exists():
        raise FileNotFoundError(f"Design file not found: {design_path}")

    with open(design_path) as f:
        design = json.load(f)

    return design


def calculate_minus_3db_band(freq, response, search_range=(100, 10000)):
    """
    Calculate the frequency range where response is within -3dB of peak.

    Returns:
        (f_low, f_high, peak_db, threshold_db, bandwidth_octaves)
    """
    # Find peak in specified range
    mask = (freq >= search_range[0]) & (freq <= search_range[1])

    if not np.any(mask):
        return np.nan, np.nan, np.nan, np.nan, np.nan

    peak_db = np.max(response[mask])
    threshold_db = peak_db - 3

    # Find lower bound (where response drops below -3dB)
    above_threshold = response > threshold_db
    above_idx = np.where(above_threshold)[0]

    if len(above_idx) == 0:
        return np.nan, np.nan, peak_db, threshold_db, np.nan

    f_low = freq[above_idx[0]]
    f_high = freq[above_idx[-1]]

    # Calculate bandwidth in octaves
    bandwidth_octaves = np.log2(f_high / f_low)

    return f_low, f_high, peak_db, threshold_db, bandwidth_octaves


def analyze_crossover_region(freq, response, xo_freq, xo_range_octaves=1):
    """
    Analyze flatness specifically in the crossover region.

    Args:
        freq: Frequency array
        response: System response (dB)
        xo_freq: Crossover frequency (Hz)
        xo_range_octaves: ±octaves around XO to analyze

    Returns:
        Dict with crossover region metrics
    """
    # Define crossover region
    f_low_xo = xo_freq / (2 ** xo_range_octaves)
    f_high_xo = xo_freq * (2 ** xo_range_octaves)

    xo_region = (freq >= f_low_xo) & (freq <= f_high_xo)

    if not np.any(xo_region):
        return {
            'f_low': f_low_xo,
            'f_high': f_high_xo,
            'min_db': np.nan,
            'max_db': np.nan,
            'peak_to_peak': np.nan,
            'std_dev': np.nan,
        }

    xo_response = response[xo_region]

    # Find minimum and maximum in crossover region
    min_db = np.min(xo_response)
    max_db = np.max(xo_response)
    peak_to_peak = max_db - min_db
    std_dev = np.std(xo_response)

    return {
        'f_low': f_low_xo,
        'f_high': f_high_xo,
        'min_db': min_db,
        'max_db': max_db,
        'peak_to_peak': peak_to_peak,
        'std_dev': std_dev,
    }


def analyze_deviation_from_flat(freq, response, reference_freq=1000):
    """
    Analyze deviation from a flat reference response.

    Calculates how much the response deviates from an ideal flat line
    drawn through the reference frequency.
    """
    # Find reference level
    ref_idx = np.argmin(np.abs(freq - reference_freq))
    reference_level = response[ref_idx]

    # Calculate deviation
    deviation = response - reference_level

    # Find min/max deviation
    min_dev = np.min(deviation)
    max_dev = np.max(deviation)

    # RMS deviation (in passband)
    passband = (freq >= 100) & (freq <= 10000)
    rms_dev = np.sqrt(np.mean(deviation[passband]**2))

    return {
        'reference_level': reference_level,
        'min_deviation_db': min_dev,
        'max_deviation_db': max_dev,
        'rms_deviation_db': rms_dev,
        'peak_to_peak_deviation_db': max_dev - min_dev,
    }


def main():
    """Main analysis workflow."""
    print("\n" + "=" * 80)
    print("-3dB FLATNESS ANALYSIS")
    print("DH450 + 12FW88 Floorstanding System")
    print("=" * 80)

    # Load design
    print("\nLoading final design...")
    design = load_final_design()

    # Extract parameters
    Vb = design['lf_enclosure']['Vb_liters'] / 1000
    Fb = design['lf_enclosure']['Fb_hz']
    xo_freq = design['crossover']['frequency_hz']
    hf_pad = design['crossover']['hf_padding_db']
    horn_fc = design['hf_horn']['cutoff_hz']

    print(f"  LF: Vb={Vb*1000:.1f}L, Fb={Fb:.1f}Hz")
    print(f"  HF: Fc={horn_fc:.0f}Hz")
    print(f"  XO: {xo_freq:.0f}Hz")
    print(f"  HF pad: {hf_pad:.1f}dB")

    # Calculate system response
    print("\nCalculating system response...")

    lf_driver = load_driver("BC_12FW88")
    freq = np.logspace(np.log10(20), np.log10(20000), 1000)  # Higher resolution

    # LF response
    lf_response = np.array([
        calculate_spl_ported_transfer_function(f, lf_driver, Vb, Fb)
        for f in freq
    ])

    # HF response
    hf_response = calculate_hf_horn_response(freq, horn_fc)
    hf_response_padded = hf_response + hf_pad

    # Crossover
    lp_gain_db, hp_gain_db = calculate_lr4_crossover_gains(freq, xo_freq)

    lf_combined = lf_response + lp_gain_db
    hf_combined = hf_response_padded + hp_gain_db

    # System response
    system_response = 10 * np.log10(
        10**(lf_combined/10) + 10**(hf_combined/10)
    )

    # =============================================================================
    # ANALYSIS 1: Overall -3dB Band
    # =============================================================================
    print("\n" + "=" * 80)
    print("ANALYSIS 1: OVERALL -3dB BANDWIDTH")
    print("=" * 80)

    f_low, f_high, peak_db, threshold_db, bandwidth_octaves = calculate_minus_3db_band(
        freq, system_response, search_range=(100, 10000)
    )

    print(f"\nSystem Peak: {peak_db:.2f} dB")
    print(f"-3dB Threshold: {threshold_db:.2f} dB")
    print(f"\n-3dB Band:")
    print(f"  Lower bound: {f_low:.1f} Hz")
    print(f"  Upper bound: {f_high:.1f} Hz")
    print(f"  Bandwidth: {bandwidth_octaves:.2f} octaves")
    print(f"  Range: {f_high/f_low:.1f}×")

    # Quality assessment
    if bandwidth_octaves >= 7:
        quality = "✅ Excellent (≥7 octaves)"
    elif bandwidth_octaves >= 6:
        quality = "✅ Good (6-7 octaves)"
    elif bandwidth_octaves >= 5:
        quality = "⚠️  Acceptable (5-6 octaves)"
    else:
        quality = "❌ Poor (<5 octaves)"

    print(f"\nQuality: {quality}")

    # =============================================================================
    # ANALYSIS 2: Crossover Region Flatness
    # =============================================================================
    print("\n" + "=" * 80)
    print("ANALYSIS 2: CROSSOVER REGION FLATNESS")
    print("=" * 80)

    # Analyze ±1 octave around crossover
    xo_metrics = analyze_crossover_region(freq, system_response, xo_freq, xo_range_octaves=1)

    print(f"\nCrossover Region (±1 octave: {xo_metrics['f_low']:.0f}-{xo_metrics['f_high']:.0f} Hz):")
    print(f"  Minimum: {xo_metrics['min_db']:.2f} dB")
    print(f"  Maximum: {xo_metrics['max_db']:.2f} dB")
    print(f"  Peak-to-peak: {xo_metrics['peak_to_peak']:.2f} dB")
    print(f"  Std deviation: {xo_metrics['std_dev']:.2f} dB")

    # Dip analysis
    xo_spl = np.interp(xo_freq, freq, system_response)
    dip_db = xo_metrics['max_db'] - xo_spl

    print(f"\n  At crossover ({xo_freq:.0f} Hz): {xo_spl:.2f} dB")
    print(f"  Dip from peak: {dip_db:.2f} dB")

    if dip_db < 1:
        print(f"  Assessment: ✅ Excellent (<1 dB dip)")
    elif dip_db < 2:
        print(f"  Assessment: ✅ Good (1-2 dB dip)")
    elif dip_db < 3:
        print(f"  Assessment: ⚠️  Acceptable (2-3 dB dip)")
    else:
        print(f"  Assessment: ❌ Poor (>3 dB dip)")

    # =============================================================================
    # ANALYSIS 3: Frequency Range Breakdown
    # =============================================================================
    print("\n" + "=" * 80)
    print("ANALYSIS 3: FLATNESS BY FREQUENCY RANGE")
    print("=" * 80)

    ranges = [
        ("Bass (20-100 Hz)", 20, 100),
        ("Mid-bass (100-500 Hz)", 100, 500),
        ("Lower midrange (500-1000 Hz)", 500, 1000),
        ("Midrange (1-2 kHz)", 1000, 2000),
        ("Upper midrange (2-5 kHz)", 2000, 5000),
        ("Treble (5-10 kHz)", 5000, 10000),
        ("Air (10-20 kHz)", 10000, 20000),
    ]

    print(f"\n{'Range':<30} {'Min':>8} {'Max':>8} {'P-P':>8} {'StdDev':>8}")
    print("-" * 70)

    for name, f_min, f_max in ranges:
        mask = (freq >= f_min) & (freq <= f_max)
        if np.any(mask):
            range_response = system_response[mask]
            min_db = np.min(range_response)
            max_db = np.max(range_response)
            p_p = max_db - min_db
            std = np.std(range_response)

            print(f"{name:<30} {min_db:>8.2f} {max_db:>8.2f} {p_p:>8.2f} {std:>8.2f}")

    # =============================================================================
    # ANALYSIS 4: Deviation from Flat Reference
    # =============================================================================
    print("\n" + "=" * 80)
    print("ANALYSIS 4: DEVIATION FROM FLAT REFERENCE")
    print("=" * 80)

    deviation_metrics = analyze_deviation_from_flat(freq, system_response, reference_freq=1000)

    print(f"\nReference frequency: 1000 Hz")
    print(f"Reference level: {deviation_metrics['reference_level']:.2f} dB")
    print(f"\nDeviation from reference:")
    print(f"  Minimum: {deviation_metrics['min_deviation_db']:+.2f} dB")
    print(f"  Maximum: {deviation_metrics['max_deviation_db']:+.2f} dB")
    print(f"  Peak-to-peak: {deviation_metrics['peak_to_peak_deviation_db']:.2f} dB")
    print(f"  RMS: {deviation_metrics['rms_deviation_db']:.2f} dB")

    # =============================================================================
    # ANALYSIS 5: Key Frequencies
    # =============================================================================
    print("\n" + "=" * 80)
    print("ANALYSIS 5: RESPONSE AT KEY FREQUENCIES")
    print("=" * 80)

    key_freqs = [
        30, 50, 100, 200, 500, 1000, 1500, 2000, 2238, 3000, 5000, 8000, 10000, 15000, 20000
    ]

    print(f"\n{'Freq':>10} {'SPL':>8} {'Dev from Peak':>15} {'Dev from 1kHz':>15}")
    print("-" * 55)

    for f in key_freqs:
        spl = np.interp(f, freq, system_response)
        dev_peak = spl - peak_db
        dev_1k = spl - deviation_metrics['reference_level']

        print(f"{f:>10.0f} {spl:>8.2f} {dev_peak:>+14.2f} dB {dev_1k:>+14.2f} dB")

    # =============================================================================
    # PLOT WITH -3dB BAND
    # =============================================================================
    print("\n" + "=" * 80)
    print("CREATING VISUALIZATION")
    print("=" * 80)

    fig, ax = plt.subplots(figsize=(14, 8))

    # Plot system response
    ax.semilogx(freq, system_response, 'k-', linewidth=2.5, label='System Response')

    # Plot -3dB band
    ax.axhspan(threshold_db, peak_db, alpha=0.15, color='green',
                label=f'-3dB Band ({f_low:.0f}-{f_high:.0f} Hz, {bandwidth_octaves:.1f} octaves)')

    # Mark peak
    ax.axhline(peak_db, color='green', linestyle='-', alpha=0.5, linewidth=1)
    ax.text(f_high * 1.5, peak_db + 0.5, f'Peak: {peak_db:.2f} dB',
            color='green', fontweight='bold', fontsize=10)

    # Mark -3dB threshold
    ax.axhline(threshold_db, color='green', linestyle='--', alpha=0.5, linewidth=1)
    ax.text(f_high * 1.5, threshold_db + 0.5, f'-3dB: {threshold_db:.2f} dB',
            color='green', fontsize=10)

    # Mark -3dB band edges
    ax.axvline(f_low, color='green', linestyle=':', alpha=0.7, linewidth=1.5)
    ax.text(f_low * 1.05, threshold_db - 2, f'{f_low:.0f} Hz\n(-3dB)',
            color='green', fontsize=9, va='top')

    ax.axvline(f_high, color='green', linestyle=':', alpha=0.7, linewidth=1.5)
    ax.text(f_high * 0.95, threshold_db - 2, f'{f_high:.0f} Hz\n(-3dB)',
            color='green', fontsize=9, va='top', ha='right')

    # Shade crossover region
    ax.axvspan(xo_metrics['f_low'], xo_metrics['f_high'], alpha=0.1, color='purple',
                label=f'XO Region (±1 octave: {xo_metrics["f_low"]:.0f}-{xo_metrics["f_high"]:.0f} Hz)')

    # Mark crossover
    ax.axvline(xo_freq, color='purple', linestyle='--', alpha=0.8, linewidth=2)
    ax.text(xo_freq * 1.05, xo_spl + 2, f'XO = {xo_freq:.0f} Hz',
            color='purple', fontweight='bold')

    # Mark horn cutoff
    ax.axvline(horn_fc, color='orange', linestyle=':', alpha=0.7, linewidth=1.5)
    ax.text(horn_fc * 0.85, 70, f'Horn Fc = {horn_fc:.0f} Hz',
            color='orange', fontsize=9, ha='right')

    # Formatting
    ax.set_xlabel('Frequency (Hz)', fontsize=13)
    ax.set_ylabel('SPL (dB) @ 1m, 2.83V', fontsize=13)
    ax.set_title(f'System Flatness Analysis: -3dB Band & Crossover Region\n'
                 f'DH450 + 12FW88 | XO: {xo_freq:.0f}Hz | Bandwidth: {bandwidth_octaves:.1f} octaves',
                 fontsize=14)
    ax.grid(True, which='both', alpha=0.3)
    ax.legend(loc='lower left', fontsize=10)
    ax.set_xlim(20, 20000)
    ax.set_ylim(40, 100)

    plt.tight_layout()

    # Save plot
    output_dir = Path(__file__).parent
    path = output_dir / "flatness_analysis_with_minus_3db_band.png"
    fig.savefig(path, dpi=150, bbox_inches='tight')
    print(f"\n✓ Plot saved: {path}")

    # =============================================================================
    # SUMMARY
    # =============================================================================
    print("\n" + "=" * 80)
    print("FLATNESS SUMMARY")
    print("=" * 80)

    print(f"\n📊 OVERALL SYSTEM PERFORMANCE:")
    print(f"   System peak: {peak_db:.2f} dB")
    print(f"   -3dB bandwidth: {bandwidth_octaves:.2f} octaves ({f_low:.0f}-{f_high:.0f} Hz)")
    print(f"   Overall flatness (100Hz-10kHz): {deviation_metrics['peak_to_peak_deviation_db']:.2f} dB")
    print(f"   RMS deviation: {deviation_metrics['rms_deviation_db']:.2f} dB")

    print(f"\n🎯 CROSSOVER REGION (±1 octave around {xo_freq:.0f} Hz):")
    print(f"   Peak-to-peak variation: {xo_metrics['peak_to_peak']:.2f} dB")
    print(f"   Dip at crossover: {dip_db:.2f} dB")
    print(f"   Std deviation: {xo_metrics['std_dev']:.2f} dB")

    # Rating
    print(f"\n⭐ PERFORMANCE RATING:")

    if bandwidth_octaves >= 7 and dip_db < 2:
        rating = "EXCELLENT - Wide bandwidth with smooth crossover"
    elif bandwidth_octaves >= 6 and dip_db < 3:
        rating = "GOOD - Adequate bandwidth, minor crossover dip"
    elif bandwidth_octaves >= 5:
        rating = "ACCEPTABLE - Usable system with some limitations"
    else:
        rating = "POOR - Significant response variations"

    print(f"   {rating}")

    print("\n" + "=" * 80)

    # Save metrics to JSON
    metrics = {
        'overall': {
            'peak_db': peak_db,
            'minus_3db_threshold_db': threshold_db,
            'f_low_hz': f_low,
            'f_high_hz': f_high,
            'bandwidth_octaves': bandwidth_octaves,
        },
        'crossover_region': {
            'xo_freq_hz': xo_freq,
            'f_low_hz': xo_metrics['f_low'],
            'f_high_hz': xo_metrics['f_high'],
            'peak_to_peak_db': xo_metrics['peak_to_peak'],
            'dip_at_xo_db': dip_db,
            'std_dev_db': xo_metrics['std_dev'],
        },
        'deviation_from_flat': deviation_metrics,
        'rating': rating,
    }

    metrics_path = output_dir / "flatness_metrics.json"
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"\n✓ Metrics saved: {metrics_path}")

    return metrics


if __name__ == "__main__":
    main()
