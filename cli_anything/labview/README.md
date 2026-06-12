# cli-anything-labview

CLI harness for **NI LabVIEW 2025** — control LabVIEW from the command line.

## Overview

`cli-anything-labview` provides a stateful command-line interface for interacting with
LabVIEW via ActiveX/COM automation on Windows. It supports both one-shot commands
(for scripting/CI) and an interactive REPL mode (for development).

## Capabilities

- **Project management** — create, open, save LabVIEW project definitions
- **VI operations** — open, close, create, save, and inspect VIs
- **Front panel control** — read and write control/indicator values
- **VI execution** — run, stop, and monitor VI status
- **Build specifications** — define and manage build configs
- **Session management** — undo/redo, state persistence
- **REPL mode** — interactive development with command history

## System Requirements

- **Windows** (ActiveX/COM is Windows-only)
- **Python 3.10+**
- **pywin32** — `pip install pywin32`
- **LabVIEW 2025** (or compatible version)
- LabVIEW ActiveX Server enabled (Tools → Options → VI Server → ActiveX)

## Installation

```bash
# From source (recommended)
git clone https://github.com/99cz99/cli-anything-labview.git
cd cli-anything-labview
pip install -e .
```

## Quick Start

```bash
# Verify installation
cli-anything-labview status check

# Find VIs in examples directory
cli-anything-labview vi find "E:\labview\LabVIEW 2025\examples"

# Enter interactive REPL
cli-anything-labview

# JSON output for scripting
cli-anything-labview --json status check
```

## Command Groups

### Project (`project`)

```bash
# Create a new project
cli-anything-labview project new -n "MyProject" -o project.json

# Open an existing project
cli-anything-labview project open project.json

# View project info
cli-anything-labview project info
```

### VI Operations (`vi`)

```bash
# Find VIs
cli-anything-labview vi find "E:\labview\LabVIEW 2025\examples" -p "*.vi"

# Get VI info
cli-anything-labview vi info "path/to/vi.vi"

# Open/close VIs (COM)
cli-anything-labview vi open "path/to/vi.vi"
cli-anything-labview vi close "path/to/vi.vi"
```

### Controls (`control`)

```bash
# List all controls on a VI
cli-anything-labview control list "path/to/vi.vi"

# Get a control value
cli-anything-labview control get "path/to/vi.vi" "control_name"

# Set a control value
cli-anything-labview control set "path/to/vi.vi" "input" 3.14
cli-anything-labview control set "path/to/vi.vi" "enable" true
cli-anything-labview control set "path/to/vi.vi" "label" "hello"

# Set multiple controls from JSON
cli-anything-labview control set-multiple "path/to/vi.vi" '{"a": 1, "b": 2}'
```

### Execution (`run`)

```bash
# Run a VI (non-blocking)
cli-anything-labview run start "path/to/vi.vi"

# Run and wait for completion
cli-anything-labview run start "path/to/vi.vi" --wait

# Stop a VI
cli-anything-labview run stop "path/to/vi.vi"

# Check VI status
cli-anything-labview run status "path/to/vi.vi"

# Run with inputs and read outputs
cli-anything-labview run io "path/to/vi.vi" '{"input": 42}' '["result"]'

# Run via LabVIEW command line (process launch)
cli-anything-labview run cli "path/to/vi.vi" -- arg1 arg2
```

### Session (`session`)

```bash
# View session state
cli-anything-labview session status

# Undo/redo operations
cli-anything-labview session undo
cli-anything-labview session redo

# Save/load session
cli-anything-labview session save mysession.json
cli-anything-labview session load mysession.json
```

### Status (`status`)

```bash
# Check LabVIEW installation
cli-anything-labview status check
```

## JSON Output Mode

All commands support `--json` for machine-readable output:

```bash
cli-anything-labview --json vi find "E:\labview\LabVIEW 2025\examples"
cli-anything-labview --json status check
cli-anything-labview --json control list "path/to/vi.vi"
```

JSON responses follow this envelope:
```json
{
  "success": true,
  "data": { ... }
}
```

Errors:
```json
{
  "error": true,
  "message": "description",
  "code": 1
}
```

## Known Limitations

1. **ActiveX type library quirks** — LabVIEW's ActiveX type library doesn't properly
   flag some methods (Run, Abort, OpenFrontPanel, etc.). The backend uses
   `_FlagAsMethod()` to work around this. Reference: NI KB kA0VU0000008tNV0AY.

2. **COM is Windows-only** — The ActiveX backend only works on Windows.
   For cross-platform control, use VI Server TCP or LabVIEW Web Server.

3. **VI Server TCP** — The VI Server's TCP protocol is proprietary and not publicly
   documented. For remote control, consider using the LabVIEW Web Server or
   running the CLI on the same machine.

4. **Build execution** — Full build execution requires LabVIEWCLI.exe or the
   LabVIEW IDE. The CLI can manage build specifications but actual compilation
   needs LabVIEW's build tools.

## Troubleshooting

### "Failed to connect to LabVIEW via COM"
- Ensure LabVIEW 2025 is installed
- Enable ActiveX Server: Tools → Options → VI Server → ActiveX → ✓ Enable
- Install pywin32: `pip install pywin32`
- Match Python bitness with LabVIEW (32-bit vs 64-bit)

### "'NoneType' object is not callable" on Run/Abort
- This is a known LabVIEW ActiveX bug. The backend handles it via `_FlagAsMethod()`.
  Report if the issue persists.

### "LabVIEW.exe not found"
- Set the `LABVIEW_PATH` environment variable to your LabVIEW.exe location:
  ```bash
  set LABVIEW_PATH=E:\labview\LabVIEW 2025\LabVIEW.exe
  ```
  Or pass `--labview-path` to any command.

## License

Apache License 2.0
