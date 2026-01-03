# Tasks Directory

This directory contains active implementation work and reference materials for the gsd project. Following the project's [CLAUDE.md](../CLAUDE.md) guidelines, the tasks directory holds work-in-progress files, while completed work is archived or moved to appropriate locations in the codebase.

## Directory Organization

```
tasks/
├── README.md                      # This file
├── [active implementation plans]  # Current work in progress
├── [specialized scripts]          # Domain-specific analysis tools
├── correct_hornresp_params.txt    # Key reference for Hornresp format
├── results/                       # Timestamped optimization results (JSON)
├── plots/                         # Generated visualizations (PNG)
├── examples/                      # Example usage scripts
└── archive/                       # Historical work and reference docs
```

## Files at Top Level

### Active Implementation Plans
- **`cli_implementation_plan.md`** - Plan for implementing CLI factory commands
- **`baffle_step_implementation_plan.md`** - Plan for baffle step correction feature

### Specialized Scripts
These scripts perform specialized analysis not covered by CLI factories:
- **`analyze_bass_offset.py`** - Analyze bass response offset characteristics
- **`bc_8ndl51_bass_horn_redesign.py`** - Legacy BC 8NDL51 bass horn redesign reference
- **`folded_horn_implementation_guide.py`** - Guide for implementing folded horn designs

### Reference Documents
- **`correct_hornresp_params.txt`** - Critical reference for Hornresp parameter format

## Subdirectories

### `results/`
Timestamped JSON optimization results from CLI `optimize` commands. These are output files that can be regenerated if needed.

**Pattern:** `{driver}_design_{timestamp}.json`
**Example:** `BC_15DS115_multisegment_horn_20251231_165015.json`

**Usage:**
```bash
# Generate new results
gsd optimize preset --driver BC_15DS115 --preset bass_horn --output results/
```

### `plots/`
Generated visualizations from CLI `plot` commands. Includes PNG files and subdirectories with organized plot outputs.

**Usage:**
```bash
# Generate plots from results
gsd plot auto --input results/my_design.json --output-dir plots/
```

### `examples/`
Example scripts demonstrating how to use gsd for common tasks:
- `optimize_practical.py` - Practical optimization example
- `plot_final_validated.py` - Plotting validated design
- `plot_two_way_response.py` - Two-way system response plotting

### `archive/`
Historical work and completed documentation:

#### `archive/docs/`
Driver-specific and project-specific implementation summaries that are not general theory:
- BC15DS115 and BC21DS115 design summaries
- Hornresp format documentation
- Project-specific bug fixes and investigations

#### `archive/reference/`
Agent instructions and reference documentation:
- `agent_instructions_spl_transfer_function.md` - SPL calibration research prompts
- `agent_instructions_update_optimizer.md` - Optimizer update instructions

#### `archive/scripts/`
Old scripts that have been replaced by CLI factories:
- Analysis and debugging scripts
- Original optimization/plotting scripts
- Validation comparison scripts

## What Was Removed (Cleanup 2025-12-31)

During the cleanup, ~70-80 redundant files were removed:

### Deleted Scripts (replaced by CLI factories)
- **16 plotting scripts** → `gsd plot create/batch/auto`
- **14 optimization scripts** → `gsd optimize run/preset`
- **12 design/analysis scripts** → CLI optimization with presets
- **5 validation scripts** → `gsd validate compare/generate-input`
- **5 export scripts** → `gsd export`
- **5 test scripts** → Integration tests in tests/

### Moved to Literature
Implementation guides and theoretical foundations moved to appropriate locations in `literature/`:
- Horn theory → `literature/horns/`
- Thiele-Small parameters → `literature/thiele_small/`
- Simulation methods → `literature/simulation_methods/`

### Migrated to Tests
Validation data moved to `tests/validation/drivers/`:
- BC15DS115 validation package → `tests/validation/drivers/bc_15ds115/`
- BC8NDL51 validation → `tests/validation/drivers/bc_8ndl51/`

### Deleted Reference Data
- Redundant result TXT files (can be regenerated)
- Quick reference summaries (information now in CLI help)
- Hornresp simulation outputs (in tests/validation/)

## Using This Directory

### For Active Development
1. **Create implementation plans** at top level (like `baffle_step_implementation_plan.md`)
2. **Work on specialized scripts** for analysis not covered by CLI
3. **Generate results** to `results/` using CLI `optimize` commands
4. **Create plots** in `plots/` using CLI `plot` commands

### For Reference
1. **Check `correct_hornresp_params.txt`** for Hornresp format reference
2. **Review `archive/`** for historical implementation details
3. **Use `examples/`** as templates for common workflows

### For Cleanup
When work is complete:
1. **Move theory/docs** to appropriate `literature/` subdirectory
2. **Migrate validation** to `tests/validation/drivers/{driver}/`
3. **Archive summaries** to `archive/docs/`
4. **Delete redundant scripts** if replaced by CLI factories

## CLI Factory Commands (Primary Interface)

Most tasks that previously required standalone scripts can now be done via CLI:

### Optimization
```bash
gsd optimize preset --driver BC_15DS115 --preset bass_horn --plot
gsd optimize run --config my_config.yaml
```

### Plotting
```bash
gsd plot auto --input results.json --preset overview
gsd plot create --type spl_response --input results.json
```

### Validation
```bash
gsd validate compare BC_8NDL51 sealed/Vb31.6L
gsd validate generate-input --driver BC_15DS115
```

### Export
```bash
gsd export BC_18PZW100 -o hornresp.txt
```

## Guidelines

### What Belongs Here
- ✅ Active implementation plans (WIP)
- ✅ Specialized analysis scripts (not covered by CLI)
- ✅ Key reference documents
- ✅ Generated results (timestamped JSON)
- ✅ Generated plots (PNG)

### What Doesn't Belong Here
- ❌ Theory/literature → `literature/`
- ❌ Validation test data → `tests/validation/`
- ❌ Completed documentation → `literature/` or `docs/`
- ❌ Redundant scripts (replaced by CLI) → DELETE
- ❌ Driver-specific summaries → `archive/docs/`

## Maintenance

Keep this directory clean by:
1. **Archiving completed work** promptly
2. **Deleting redundant scripts** replaced by CLI
3. **Moving results to appropriate locations** when complete
4. **Using CLI factories** instead of creating new scripts
5. **Documenting specialized scripts** with clear purpose

For more information, see the project's [CLAUDE.md](../CLAUDE.md) file.
