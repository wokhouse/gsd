# Throat Chamber Impedance Bug Fix

**Date:** 2024-12-31
**Severity:** Critical (50 dB SPL loss)
**Status:** Fixed ✓

## Problem Description

The bass extension optimization was producing extremely low SPL values (30-60 dB below expected). Investigation revealed that the throat chamber impedance calculation was causing a massive acoustic power loss.

### Symptoms
- BC_8NDL51 horn: 40.7 dB @ 100 Hz (expected: 90-100 dB)
- BC_DE250 horn: Similar massive losses
- All bass frequencies severely affected
- High frequencies less affected (suggestive of frequency-dependent issue)

### Root Cause

The throat chamber compliance and horn throat impedance were combined in **SERIES**, when they should be in **PARALLEL** according to acoustic circuit theory for compression driver topology.

**Acoustic Circuit Analysis at 100 Hz:**
```
Throat chamber (14 cm³): Z_tc = 1.62e+07 Pa·s/m³
Horn throat:              Z_horn = 2.22e+04 Pa·s/m³

SERIES (wrong):    Z_total = 1.62e+07 Pa·s/m³ (dominated by throat chamber)
                   → SPL = 40.7 dB (50 dB loss!)

PARALLEL (correct): Z_total = 2.22e+04 Pa·s/m³ (dominated by horn)
                   → SPL = 91.3 dB (correct!)
```

The throat chamber impedance is 730x larger than the horn impedance. In series, this creates an acoustic "wall" that blocks power flow. In parallel, the lower horn impedance dominates, allowing normal power transfer.

### Physical Explanation

For a compression driver with throat chamber:
```
Driver → [Throat Chamber] ←──┐
         ↓                   │
       [Horn → Mouth]        │
                            ↓
                         Parallel junction
```

At the throat chamber, the driver sees BOTH:
1. The compliance of the throat chamber (high impedance)
2. The horn impedance (lower impedance)

These are in **parallel** because they share the same pressure point. Volume velocity splits between them, with most flowing through the lower-impedance horn path.

**Series vs Parallel:**
- **Series:** Same volume velocity through both, pressures add
  - High Z_tc blocks flow → power loss
- **Parallel:** Same pressure, volume velocities add
  - Most U flows through low Z_horn → normal power transfer

## The Fix

**File:** `src/gsd/simulation/horn_driver_integration.py`
**Function:** `horn_system_acoustic_impedance()`

### Before (Buggy Code)
```python
# Add throat chamber compliance (series element)
if V_tc > 0:
    Z_tc = throat_chamber_impedance(frequencies, V_tc, A_tc, medium)
    Z_front = Z_tc + Z_horn_throat  # ← BUG: Series combination
else:
    Z_front = Z_horn_throat
```

### After (Fixed Code)
```python
# Add throat chamber compliance (parallel element)
# For compression driver topology, the throat chamber is in parallel with
# the horn impedance, not in series.
#
# Literature: Beranek (1954), Chapter 5 - Acoustic circuits
# Parallel combination: 1/Z_total = 1/Z_tc + 1/Z_horn
if V_tc > 0:
    Z_tc = throat_chamber_impedance(frequencies, V_tc, A_tc, medium)
    # Parallel combination: Z_front = Z_tc || Z_horn_throat
    Z_front = 1.0 / (1.0 / Z_tc + 1.0 / Z_horn_throat)
else:
    Z_front = Z_horn_throat
```

## Validation Results

**Test Horn:** BC_8NDL51 with mixed-profile horn
- Throat: 44.5 cm²
- Mouth: 572 cm²
- Length: 0.32 m
- Throat chamber: 14 cm³
- Rear chamber: 7.6 L

### Frequency Response After Fix
```
Freq (Hz)    SPL (dB)    Status
--------------------------------
20           61.8        ✓ (good bass extension)
30           69.1        ✓
40           74.5        ✓
50           78.9        ✓
75           87.0        ✓
100          91.3        ✓ (target range)
150          93.0        ✓
200          94.2        ✓
300          99.9        ✓
500          100.7       ✓ (excellent sensitivity)
1000         97.8        ✓
```

### Key Improvements
- **100 Hz:** 40.7 dB → 91.3 dB (+50.6 dB gain!)
- **Bass extension:** Now reaches 61.8 dB @ 20 Hz
- **Sensitivity:** 100.7 dB @ 500 Hz (excellent for a horn)
- **All frequencies:** Now within expected ranges

## Impact on Optimization

This fix enables the bass extension optimization to work correctly. Previously:
- All designs hit F3 = 20 Hz floor (frequency array lower bound)
- Extremely low efficiencies (<1%)
- Optimizer couldn't find valid designs

After fix:
- F3 will be calculated correctly from actual SPL response
- Efficiencies should be reasonable (10-40% for horns)
- Optimizer can find meaningful trade-offs

## Literature References

- **Beranek (1954), Chapter 5** - Acoustic circuit analysis
  - Series vs parallel impedance combinations
  - Compliance in acoustic circuits

- **Olson (1947), Chapter 8** - Horn driver systems
  - Throat chamber modeling
  - Compression driver topology

## Lessons Learned

1. **Always validate against expected values**: 40 dB is obviously wrong for a horn
2. **Debug with minimal cases**: Testing V_tc=0 revealed the issue
3. **Acoustic circuit topology matters**: Series vs parallel is critical
4. **Impedance magnitudes matter**: 730x ratio should have been a red flag

## Related Issues

This fix may also affect:
- Midrange horn simulations with throat chambers
- Compression driver simulations
- Any design using `V_tc > 0`

All such simulations should now show much higher (correct) SPL values.

## Next Steps

1. ✓ Fix implemented and committed
2. ✓ Validated with BC_8NDL51 test case
3. **TODO:** Re-run bass extension optimization with correct SPL
4. **TODO:** Validate against Hornresp for complete verification
5. **TODO:** Test with BC_DE250 compression driver

## Commit

**Commit:** `241cbc9` - "fix: Correct throat chamber impedance from series to parallel"
**Branch:** `feature/mixed-profile-horns`
