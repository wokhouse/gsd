# Two-Way System Troubleshooting Guide

## Common Issues and Solutions

### Issue: Horn Cutoff Too High

**Symptoms:**
- Dip in frequency response around crossover
- Flatness > 6 dB
- Validation warning: "Horn cutoff > 0.5 × crossover"

**Diagnosis:**
```python
if horn_params['cutoff'] > crossover_freq * 0.5:
    print("Horn cutoff too high for clean integration")
```

**Solutions (in order of preference):**

1. **Use Multi-Piece Printing**
   ```python
   design = design_two_way_system_complete(
       ...,
       allow_multi_piece=True  # Automatically enables
   )
   ```

2. **Increase Crossover Frequency**
   ```python
   # Try 1.5-2 kHz for 12" woofers
   crossover_range=(1500, 3000)
   ```

3. **Use Larger Printer**
   ```python
   printer_constraints = {"max_length": 0.50}  # 500mm
   ```

4. **Accept + EQ**
   - Raise crossover to 1 kHz+
   - Use EQ to fill in dip below crossover
   - Only for minor corrections (< 3 dB)

---

### Issue: Poor Flatness (> 6 dB)

**Symptoms:**
- Visible peaks/dips in response
- Validation warning about flatness

**Diagnosis:**
```python
if design.flatness > 6:
    # Identify problem frequency range
    freq, response = calculate_response(design)
    dip_freq = freq[np.argmin(response)]
    peak_freq = freq[np.argmax(response)]
    print(f"Dip: {dip_freq:.0f} Hz, Peak: {peak_freq:.0f} Hz")
```

**Solutions:**

1. **Adjust Crossover Frequency**
   - Move closer to HF driver's optimum range
   - For DH450: Try 1-1.5 kHz instead of 800 Hz

2. **Optimize HF Padding**
   ```python
   # Auto-optimize padding for flatness
   design = optimize_hf_padding_for_flatness(design)
   ```

3. **Check Horn Cutoff**
   - If cutoff > 0.5 × crossover, see previous issue

4. **Consider Different Crossover Type**
   - LR4 (default): Steep slopes, good summation
   - LR2: Gentler slopes, sometimes better integration
   - Butterworth: Different characteristics

---

### Issue: Impossible F3 Values

**Symptoms:**
- F3 = 10 Hz for 47 Hz tuning
- F3 below driver Fs

**Root Cause:**
Using wrong F3 calculation method (high-pass vs low-pass)

**Fix:**
```python
# WRONG
f3 = freq[np.where(spl <= passband - 3)[0][0]]

# CORRECT
from gsd.simulation.response_metrics import find_f3_frequency
f3 = find_f3_frequency(freq, spl, passband,
                       filter_type="highpass")  # or "lowpass"
```

---

### Issue: Constraint Not Enforced

**Symptoms:**
- Optimized horn longer than max_length constraint
- "Design fits in 250mm: ✓" but actual length is 500mm

**Root Cause:**
Bug in constraint parameter passing (fixed in Phase 1, Task 1.1)

**Workaround until fix:**
```python
# Manually divide by num_segments
length_max = printer_max_length / num_segments

param_space = get_multisegment_horn_parameter_space(
    ...,
    # Manually constrain each segment
    length_max=length_max
)
```

---

## Getting Help

If you encounter issues not covered here:

1. **Check validation output:**
   ```python
   print(design.validation)
   ```

2. **Review design summary:**
   ```python
   print(design)
   ```

3. **Compare with Hornresp:**
   - Export to Hornresp format
   - Run simulations
   - Compare responses

4. **Check examples:**
   - `examples/complete_two_way_workflow.py`
   - `examples/two_way_system_example.py`

5. **Report bugs:**
   - Include: driver names, constraints, validation output
   - Include: plots showing the issue
   - Check: `docs/two_way_workflow_improvements.md` for known issues
