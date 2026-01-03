# Validation Data

This directory contains **permanent validation data** for comparing GSD
calculations against Hornresp simulations.

## Directory Structure

```
tests/validation/
└── drivers/
    ├── bc_8ndl51/
    │   └── infinite_baffle/
    │       ├── bc_8ndl51_inf.txt       # Hornresp input file
    │       ├── bc_8ndl51_inf_sim.txt   # Hornresp simulation results
    │       └── metadata.json           # Validation metadata
    ├── bc_12ndl76/
    │   └── infinite_baffle/
    │       └── ...
    └── ...
```

## File Naming Convention

**Input files:** `{driver}_{config}.txt` (max 16 chars for Hornresp)
- `bc_8ndl51_inf.txt` - infinite baffle
- `bc_12ndl76_inf.txt` - infinite baffle
- Future: `bc_8ndl51_exp.txt` - exponential horn

**Output files:** `{driver}_{config}_sim.txt`
- `bc_8ndl51_inf_sim.txt` - simulation results
- `bc_12ndl76_inf_sim.txt` - simulation results

## Metadata

Each configuration has a `metadata.json` file:
```json
{
  "driver": "BC_8NDL51",
  "configuration": "infinite_baffle",
  "date_created": "2025-12-26",
  "date_run": "2025-12-26",
  "hornresp_version": null,
  "notes": "Driver description and validation notes"
}
```

## Working Directories

For day-to-day workflow, use the staging directories:
- `exports/` - GSD parameter outputs (Hornresp inputs)
- `imports/` - Hornresp simulation results

Move completed validations to this directory for permanent storage.

## Version Control

This directory **is version controlled**. All committed files represent
validated reference data for testing.
