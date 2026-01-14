# File Organization and Workflow

## Overview

This document defines the workflow for organizing files in the GSD repository to keep it clean and maintainable.

## File Locations by Type

### Source Code (Git Tracked)

**Location:** `src/gsd/`

All production Python code:
- Module implementations
- Package initialization files
- Type definitions and data structures

**Example:**
```
src/gsd/optimization/api/horn_physics.py  ✓ (tracked)
```

### Documentation (Git Tracked)

**Location:** `docs/`

Permanent reference documentation:
- User guides
- Technical specifications
- Validation investigation reports (after completion)
- Literature summaries

**Example:**
```
docs/two_way_design_guide.md  ✓ (tracked)
docs/validation/sealed_box_spl_investigation.md  ✓ (tracked)
```

### Tests (Git Tracked)

**Location:** `tests/`

Test infrastructure and validation data:
- Unit tests
- Integration tests
- Hornresp reference data (for validation)
- Test configurations

**Example:**
```
tests/optimization/api/test_horn_physics.py  ✓ (tracked)
tests/validation/drivers/BC_12FW88/ported/sim.txt  ✓ (tracked reference)
```

### Active Tasks (Git Tracked)

**Location:** `tasks/`

Working documents for active development:
- Research plans (TODO.md, research_plan.md)
- Status tracking (driver_validation_status.md)
- Working scripts for active features

**Naming Convention:** Use descriptive, non-generic names

**Examples:**
```
tasks/research_validation_plan.md  ✓ (tracked - active research)
tasks/driver_validation_status.md  ✓ (tracked - status tracking)
tasks/optimize_bc15ds115_ported.py  ✓ (tracked - specific driver optimization)
```

**❌ AVOID in tasks/:**
- Generic investigation scripts
- Generated plots (PDF, PNG)
- Hornresp export files
- Intermediate analysis results

### Investigation Files (Git Untracked)

**Location:** `/tmp/` or user's local workspace (outside repo)

Temporary investigation and analysis artifacts:
- One-off analysis scripts
- Generated plots (PDF, PNG, JPG)
- Hornresp export files (.txt)
- Intermediate design JSON files
- Analysis results

**Examples:**
```
/tmp/analyze_physics_constraint.py  ✗ (untracked - temporary investigation)
~/Desktop/design_exploration/  ✗ (untracked - user workspace)
/tmp/horn_export.txt  ✗ (untracked - temporary validation)
```

### Examples (Git Tracked)

**Location:** `examples/`

Demonstration scripts showing how to use the API:
- Complete working examples
- Tutorial-style code
- Well-documented usage patterns

**Example:**
```
examples/complete_two_way_workflow.py  ✓ (tracked - tutorial example)
```

## When to Commit What

### ✅ DO Commit to Repository

**Source Code:**
- All code in `src/gsd/`
- Production-ready implementations
- Unit and integration tests

**Documentation:**
- User guides (`docs/*.md`)
- API documentation
- Completed investigation reports (summarized findings)
- Literature citations and references

**Test Data:**
- Hornresp reference outputs for validation
- Test configurations
- Validation status files

**Examples:**
- Tutorial scripts showing API usage
- Well-documented working examples

**Active Tasks:**
- Research plans with future work items
- Status tracking documents
- Driver-specific optimization scripts (finalized, not investigation)

### ❌ DO NOT Commit to Repository

**Investigation Artifacts:**
- Generated plots (PDF, PNG, JPG) - use `/tmp/`
- Hornresp export files - use `/tmp/`
- Intermediate JSON files - use `/tmp/`
- One-off analysis scripts - use `/tmp/`

**Why:**
- Investigation files are temporary and clutter the repository
- Plots can be regenerated from source code
- Export files are large and not needed after validation
- Makes git history cleaner and faster

**Temporary Files:**
- Scratch scripts (demonstrate_*.py, test_*.py, redo_*.py)
- Analysis outputs (response_*.txt, design_summary.json)
- Working plots (system_response.png, flatness_analysis.png)

## Workflow Examples

### Example 1: Investigating a Physics Issue

**❌ WRONG (clutters repo):**
```bash
# Create investigation in tasks/
tasks/two_way_design_12fw88_dh450/
├── investigate_dip_issue.py
├── plot_response_curves.py
├── system_response.png
├── dip_analysis.pdf
└── hornresp_export.txt
```

**✅ RIGHT (clean repo):**
```bash
# 1. Work in /tmp/
/tmp/investigate_dip/
├── investigate_dip_issue.py
├── plot_response_curves.py
├── system_response.png
└── hornresp_export.txt

# 2. Summarize findings in docs/
docs/validation/dip_investigation.md
# Describe the issue, investigation process, and conclusions

# 3. If bug fix needed, create PR with fix
# 4. Delete /tmp/investigate_dip/ when done
```

### Example 2: Driver-Specific Design

**❌ WRONG (clutters repo):**
```bash
# Commit all intermediate files
tasks/design_bc_12fw88/
├── attempt_1.py
├── attempt_2.py
├── attempt_3.py
├── final_design.json
├── optimization_trace.json
└── response_plots/
```

**✅ RIGHT (clean repo):**
```bash
# 1. Work in /tmp/
/tmp/bc12fw88_design/
├── exploration.py  # scratch scripts
├── design_iterations.json
└── response.png

# 2. Create final example
examples/design_ported_box_bc12fw88.py
# Show the final design process

# 3. Update documentation if needed
docs/case_studies/bc12fw88_ported_box.md

# 4. Delete /tmp/bc12fw88_design/ when done
```

### Example 3: Validating Against Hornresp

**❌ WRONG (clutters repo):**
```bash
# Commit all Hornresp exports
tasks/validation/
├── driver1_hornresp.txt
├── driver1_hornresp_v2.txt
├── driver1_hornresp_final.txt
└── driver2_hornresp.txt
```

**✅ RIGHT (clean repo):**
```bash
# 1. Generate exports in /tmp/ during validation
/tmp/validate_driver1/
└── hornresp_export.txt

# 2. Compare results programmatically
# Use gsd.validation.compare module

# 3. If reference data needed for tests, commit to tests/validation/
tests/validation/drivers/driver_name/enclosure_type/
├── README.md  # Document what this validates
├── sim.txt    # Hornresp reference output (only final, validated version)
└── VALIDATION_ISSUE.md  # Document any discrepancies

# 4. Delete /tmp/validate_driver1/ when done
```

## Cleanup Checklist

Before committing, ask yourself:

1. **Is this source code?**
   - YES → Commit to `src/gsd/`
   - NO → Continue

2. **Is this documentation?**
   - YES → Commit to `docs/`
   - NO → Continue

3. **Is this a test or reference data?**
   - YES → Commit to `tests/`
   - NO → Continue

4. **Is this a tutorial/example?**
   - YES → Commit to `examples/`
   - NO → Continue

5. **Is this a working task plan?**
   - YES → Commit to `tasks/` (use descriptive name)
   - NO → Continue

6. **Is this an investigation artifact?**
   - YES → **DO NOT COMMIT** (use `/tmp/` instead)

## .gitignore Patterns

The repository `.gitignore` excludes common investigation artifacts:

```
# Generated plots and visualizations
tasks/*/*.pdf
tasks/*/*.png
tasks/*/*.jpg

# Hornresp exports (temporary)
tasks/*/*.txt

# Intermediate design files
tasks/*/design_*.json
tasks/*/final_*.json
tasks/*/optimized_*.json

# One-off investigation scripts
tasks/*/analysis*.py
tasks/*/complete_*.py
tasks/*/demonstrate*.py
tasks/*/plot_*.py
```

## Migration Path

If you have investigation files in the repository:

1. **Move to /tmp/**
   ```bash
   mv tasks/investigation_dir/ /tmp/
   ```

2. **Document findings**
   - Create summary in `docs/validation/` if useful
   - Or just delete if investigation is complete

3. **Remove from git**
   ```bash
   git rm -r tasks/investigation_dir/
   git commit -m "chore: Remove temporary investigation files"
   ```

## Summary

| File Type | Location | Tracked? |
|-----------|----------|----------|
| Source code | `src/gsd/` | ✅ Yes |
| Documentation | `docs/` | ✅ Yes |
| Tests | `tests/` | ✅ Yes |
| Examples | `examples/` | ✅ Yes |
| Active tasks | `tasks/` (descriptive names) | ✅ Yes |
| Investigation artifacts | `/tmp/` or local | ❌ No |
| Generated plots | `/tmp/` | ❌ No |
| Hornresp exports | `/tmp/` or `tests/validation/` | ⚠️ Only if reference data |
| Analysis scripts | `/tmp/` | ❌ No |

**Key Principle:** Keep the repository clean. Only commit what others need - source code, tests, documentation, and examples. Investigation artifacts belong in `/tmp/` and should be deleted after use.
