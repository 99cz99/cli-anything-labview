---
name: "cli-anything-labview"
description: "CLI harness for NI LabVIEW 2025 — control VIs, projects, front panel controls, and build specs from the command line via ActiveX/COM automation. Use when users want to automate LabVIEW, run VIs from CLI, read/write control values, manage projects, or script LabVIEW operations."
---

# cli-anything-labview

CLI harness for **NI LabVIEW 2025** — control LabVIEW from the command line via ActiveX/COM automation.

## Prerequisites

- Windows with LabVIEW 2025 installed
- Python 3.10+ with `pywin32` (`pip install pywin32`)
- LabVIEW ActiveX Server enabled (Tools → Options → VI Server → ActiveX)

## Command Groups

| Group | Description |
|-------|-------------|
| `project` | Project management (new, open, save, info, add-vi, list-files) |
| `vi` | VI operations (open, close, create, save, info, list, find) |
| `control` | Front panel controls (get, set, list, set-multiple) |
| `run` | VI execution (start, stop, status, io, cli) |
| `session` | Session management (status, undo, redo, save, load) |
| `build` | Build specifications (types, list) |
| `status` | System status (check) |

## Agent-Specific Guidance

### Always use `--json` for programmatic usage
```bash
cli-anything-labview --json <command>
```

All JSON responses follow the envelope:
```json
{"success": true, "data": {...}}
// or
{"error": true, "message": "...", "code": 1}
```

### Key workflows for AI agents

**Check LabVIEW is available:**
```bash
cli-anything-labview --json status check
```

**Find VIs:**
```bash
cli-anything-labview --json vi find "/path/to/search" -p "*.vi"
```

**Run a VI and read outputs:**
```bash
cli-anything-labview --json run io "path.vi" '{"input_name": value}' '["output_name"]'
```

**Set controls before running:**
```bash
cli-anything-labview --json control set "path.vi" "control_name" value
cli-anything-labview --json run start "path.vi" --wait
cli-anything-labview --json control get "path.vi" "indicator_name"
```

**Run a VI via command line (process launch, no COM):**
```bash
cli-anything-labview --json run cli "path.vi" -- arg1 arg2
```

### COM Backend Quirks

The LabVIEW ActiveX type library has known bugs where methods like `Run()`,
`Abort()`, `OpenFrontPanel()` return `TypeError: 'NoneType' object is not callable`.
The backend automatically applies `_FlagAsMethod()` to fix this.
Reference: https://knowledge.ni.com/KnowledgeArticleDetails?id=kA0VU0000008tNV0AY

### LabVIEW Path

If LabVIEW.exe is not found automatically, set it:
```bash
# Environment variable
set LABVIEW_PATH=E:\labview\LabVIEW 2025\LabVIEW.exe

# Or per-command
cli-anything-labview --labview-path "E:\labview\LabVIEW 2025\LabVIEW.exe" ...
```

## Examples

```bash
# Create a project
cli-anything-labview --json project new -n "TestProject" -o test.json

# Find VIs in examples
cli-anything-labview --json vi find "E:\labview\LabVIEW 2025\examples"

# Run a VI with I/O
cli-anything-labview --json run io "example.vi" '{"input": 10}' '["output"]'

# Check system status
cli-anything-labview --json status check

# Session management
cli-anything-labview --json session status
cli-anything-labview --json session save state.json
```
