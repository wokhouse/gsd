# Hornresp Imports Directory

This directory contains **Hornresp simulation result files** (validation data).

## Purpose
Temporary working directory for simulation results exported from Hornresp.
These files are used to validate GSD calculations against Hornresp.

## Usage
1. Run simulation in Hornresp using parameters from `exports/`
2. Export results from Hornresp
3. Save to this directory: `imports/{driver}_{config}_sim.txt`
4. Move to `tests/validation/drivers/{driver}/{config}/` for permanent storage

## File Format
Hornresp exports tab-separated text files with columns:
- Freq (Hz)
- Ra, Xa, Za (acoustic impedance)
- SPL (dB)
- Ze, ZePhase (electrical impedance)
- Xd (diaphragm displacement)
- Various phase and efficiency data

## Files in this directory
- Intended as a **staging area** for simulation results
- **Not version controlled** (see .gitignore)
- Move completed simulations to `tests/validation/drivers/` for permanent storage

## Related Directories
- `exports/` - GSD parameter outputs (Hornresp inputs)
- `tests/validation/drivers/` - Permanent validation data (version controlled)
