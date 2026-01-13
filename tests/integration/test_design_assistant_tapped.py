#!/usr/bin/env python3
"""Test design assistant for tapped horn with BC_15PS100."""

import sys
sys.path.insert(0, 'src')

from gsd.optimization.api.design_assistant import DesignAssistant
from gsd.driver import load_driver, list_drivers

print("=" * 80)
print("Testing Design Assistant for Tapped Horn with BC_15PS100")
print("=" * 80)
print()

# First, verify BC_15PS100 driver exists
print("1. Checking available drivers...")
print("-" * 80)
drivers = list_drivers()

if "BC_15PS100" in drivers:
    print(f"✅ BC_15PS100 found: {drivers['BC_15PS100']}")
else:
    print(f"❌ BC_15PS100 not found")
    print(f"Available drivers: {', '.join(list(drivers.keys())[:10])}")
    sys.exit(1)

print()

# Load the driver
print("2. Loading BC_15PS100 driver parameters...")
print("-" * 80)
driver = load_driver("BC_15PS100")
print(f"✅ Driver loaded successfully")
print(f"   F_s: {driver.F_s:.1f} Hz")
print(f"   Q_ts: {driver.Q_ts:.3f}")
print(f"   S_d: {driver.S_d*10000:.1f} cm²")
print(f"   V_as: {driver.V_as*1000:.1f} liters")
print(f"   BL: {driver.BL:.1f} T·m")
print(f"   M_md: {driver.M_md*1000:.1f} g")
print()

# Initialize design assistant
print("3. Initializing Design Assistant...")
print("-" * 80)
assistant = DesignAssistant(validation_mode=True)
print(f"✅ Design assistant ready (validation_mode=True)")
print()

# Get recommendation for tapped horn
print("4. Getting tapped horn recommendation...")
print("-" * 80)

try:
    rec = assistant.recommend_design(
        driver_name="BC_15PS100",
        objectives=["f3", "spl", "efficiency"],
        max_volume_liters=500,  # 500L max for subwoofer
        target_f3=40,  # Target 40 Hz cutoff
        enclosure_preference="tapped_horn"
    )

    print(f"✅ Recommendation received")
    print(f"   Enclosure type: {rec.enclosure_type}")
    print(f"   Confidence: {rec.confidence}")
    print()
    print("   Reasoning:")
    print(f"   {rec.reasoning[:500]}...")
    print()

    if hasattr(rec, 'initial_parameters') and rec.initial_parameters:
        print(f"   Initial parameters suggested:")
        for key, value in rec.initial_parameters.items():
            print(f"     {key}: {value}")

except Exception as e:
    print(f"❌ Error getting recommendation: {e}")
    print(f"   {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print()

# Now try to optimize a tapped horn design
print("5. Optimizing tapped horn design...")
print("-" * 80)

try:
    result = assistant.optimize_design(
        driver_name="BC_15PS100",
        enclosure_type="tapped_horn",
        objectives=["f3", "spl"],
        n_generations=10,  # Small number for quick test
        population_size=5
    )

    print(f"✅ Optimization complete")
    print(f"   Best design score: {result.best_score:.4f}")
    print()
    print("   Top 3 designs:")
    for i, design in enumerate(result.best_designs[:3], 1):
        print(f"   Design {i}:")
        print(f"     Score: {design['score']:.4f}")
        params = design['parameters']
        print(f"     Parameters: Vb={params.get('Vb', 'N/A')}L, Fb={params.get('Fb', 'N/A')}Hz")

except Exception as e:
    print(f"❌ Error during optimization: {e}")
    print(f"   {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("Test complete!")
print("=" * 80)
