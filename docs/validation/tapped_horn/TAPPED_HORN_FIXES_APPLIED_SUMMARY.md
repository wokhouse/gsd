# Tapped Horn Simulation - Research Agent Fixes Applied

## Summary

Applied three fixes recommended by the research agent based on literature validation. Results show improvement but still not meeting <2 dB RMS target.

## Fixes Applied

### 1. Roughness Factor Default Changed ✓
**File**: `src/gsd/simulation/tapped_horn_theory.py`
**Lines**: 1434, 1509

**Change**: Default `roughness_factor` changed from 4.0 to 1.0
- **Before**: `roughness_factor: float = 4.0` (folded horn)
- **After**: `roughness_factor: float = 1.0` (smooth pipe, matches Hornresp)

**Rationale**: Hornresp assumes smooth adiabatic walls by default. Using roughness_factor=4.0 was over-damping the reflected wave in the upstream stub, preventing proper destructive interference at quarter-wave resonance.

**Impact**: Quarter-wave notch deepened from 75.6 dB to 64.6 dB (11 dB improvement).

### 2. RMS Voltage Power Calculation Fixed ✓
**File**: `src/gsd/simulation/tapped_horn_theory.py`
**Lines**: 1773-1778, 1823-1825

**Change**: Removed 0.5 factor from both acoustic and electrical power calculations
- **Before**: `radiated_power = 0.5 * (np.abs(U_mouth) ** 2) * np.real(Z_rad)`
- **After**: `radiated_power = (np.abs(U_mouth) ** 2) * np.real(Z_rad)`

**Rationale**: Standard audio simulation treats 2.83V as RMS (1W into 8Ω), not peak. For RMS quantities, use W = |I_rms|² × Re(Z), not W = 0.5 × |I_peak|² × Re(Z).

**Impact**: Systematic SPL offset reduced by +3.01 dB across all frequencies.

### 3. Upstream Contracting Geometry Verified ✓
**File**: `src/gsd/simulation/tapped_horn_theory.py`
**Lines**: 1614-1628

**Verification**: Confirmed upstream section is explicitly modeled as contracting horn (Tap → Throat), not mathematically inverted expanding horn.

```python
upstream_contracting = ExponentialHorn(
    throat_area=tapped_horn.tap_area / 10000.0,              # INPUT at Tap (m²)
    mouth_area=tapped_horn.upstream_throat_area / 10000.0,    # OUTPUT at Throat (m²)
    length=tapped_horn.upstream_length / 100.0,               # Convert cm to m
)
```

**Rationale**: Contracting horns have different impedance transformation than expanding horns; mathematical inversion of T-matrix is incorrect.

**Impact**: No change needed (already correct).

## Validation Results

### Before Fixes
| Metric | Value |
|--------|-------|
| RMS Error | 8.78 dB |
| Mean Error | -4.08 dB |
| Peak Error | 29.86 dB |
| Notch Depth | 75.6 dB |
| Max SPL | 103.7 dB |
| Efficiency | 28.3% |

### After Fixes
| Metric | Value | Change |
|--------|-------|--------|
| RMS Error | 7.94 dB | -0.84 dB (improved) |
| Mean Error | -1.45 dB | +2.63 dB (improved) |
| Peak Error | 37.01 dB | +7.15 dB (worsened) |
| Notch Depth | 64.6 dB @ 78.6 Hz | -11 dB (deeper) |
| Max SPL | 107.1 dB | +3.4 dB |
| Efficiency | 30.8% | +2.5% (corrected) |

### Frequency-by-Frequency Comparison
```
Freq(Hz)  GSD_SPL  HR_SPL  Error(dB)  Notes
40        102.03   106.21  -4.18      Improved (was -7.41)
50        98.84    96.98   +1.86      ✓ Good (was -1.24)
60        94.62    97.86   -3.24      Improved (was -6.29)
70        91.69    105.68  -13.98     Large error persists
79        75.69    78.97   -3.28      ✓ Good
80        88.35    55.14   +33.21     Notch freq mismatch
85        95.44    88.83   +6.61      Slightly high
90        94.91    93.94   +0.97      ✓ Excellent
100       95.61    100.16  -4.55      Improved (was -7.60)
```

## Remaining Issues

### 1. Quarter-Wave Notch Mismatch (Critical)
- **GSD**: Notch at 78.6 Hz, depth 64.6 dB
- **Hornresp**: Notch at 80 Hz, depth 55.1 dB
- **Error**: 9.5 dB depth difference + 1.4 Hz frequency shift

**Possible Causes**:
- End correction calculation differs between GSD and Hornresp
- T-matrix calculation for contracting horn may have subtle error
- Parallel impedance combination may need adjustment
- Loss distribution between upstream/downstream may be incorrect

### 2. Low Frequency Error (70 Hz)
- **Error**: -13.98 dB at 70 Hz
- **Character**: GSD reading much lower than Hornresp
- **Possible**: Acoustic impedance calculation error in specific frequency range

### 3. Electrical Impedance Spike at 60 Hz
- **GSD**: 20.39 Ω
- **Hornresp**: 10.96 Ω
- **Error**: +86%

**Note**: Research agent identified this as driver data mismatch (M_ms = 43g in test vs 105g in real driver). This is a test data issue, not a code issue.

## What Worked

1. ✓ **Systematic offset fixed**: Removing 0.5 factor correctly added +3.01 dB
2. ✓ **Notch depth improved**: Changing roughness_factor from 4.0 to 1.0 deepened notch by 11 dB
3. ✓ **Multiple frequencies now excellent**: 50 Hz (+1.86 dB), 90 Hz (+0.97 dB)

## What Didn't Work

1. ✗ **RMS error still 7.94 dB**: Target is <2 dB
2. ✗ **Peak error worse**: 37 dB due to notch frequency mismatch
3. ✗ **Large errors at specific frequencies**: 70 Hz (-14 dB), 80 Hz (+33 dB)

## Next Steps

To achieve <2 dB RMS accuracy, need to investigate:

1. **Quarter-wave resonance physics**: Why is notch at 78.6 Hz instead of 80 Hz?
   - Check effective acoustic length calculation
   - Verify end correction formulas
   - Compare T-matrix elements with Hornresp

2. **Parallel impedance combination**: Is Z_up || Z_down correct?
   - May need phase weighting instead of simple parallel
   - Check if driver-tap junction model needs adjustment

3. **Loss distribution**: Are losses applied correctly to upstream/downstream?
   - May need different roughness factors per section
   - Check if boundary layer thickness calculation is correct

## Files Modified

- `src/gsd/simulation/tapped_horn_theory.py` - Applied all three fixes
- `tasks/validate_tapped_horn_final.py` - Updated to use roughness_factor=1.0
- `tasks/detailed_comparison.py` - Updated for new defaults
- `tasks/investigate_notch.py` - Created for notch analysis

## Recommendation

The research agent's fixes addressed the systematic offset and damping issues correctly. The remaining errors require deeper investigation into the quarter-wave interference physics and T-matrix calculations. Consider consulting additional literature on:
- Tapped horn quarter-wave resonance theory
- End corrections for contracting horns
- Parallel impedance combination in three-port networks
