# cli-anything-labview

CLI harness for **NI LabVIEW 2025** — control LabVIEW from the command line via ActiveX/COM automation.

[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)]()

## Quick Install

```bash
git clone https://github.com/99cz99/cli-anything-labview.git
cd cli-anything-labview
pip install -e .
cli-anything-labview status check
```

## What It Does

| Group | Capability |
|-------|------------|
| `project` | Create, open, save LabVIEW project definitions |
| `vi` | Open, close, create, save, find, inspect VIs |
| `control` | Read/write front panel control/indicator values |
| `run` | Execute, stop, and monitor VIs; I/O passthrough |
| `build` | Define and manage build specifications |
| `session` | Stateful undo/redo (50-level stack), persistence |
| `status` | Verify LabVIEW installation and COM connectivity |

Supports both **one-shot commands** (for scripting/CI) and an **interactive REPL** mode.

## Quick Examples

```bash
# JSON output for scripting
cli-anything-labview --json status check

# Find all VIs recursively
cli-anything-labview vi find "E:\labview\LabVIEW 2025\examples" -p "*.vi"

# Create a project, add a VI, save
cli-anything-labview project new -n "MyProject" -o project.json

# Read/write front panel controls
cli-anything-labview control set "path/to/vi.vi" "input" 3.14
cli-anything-labview control get "path/to/vi.vi" "result"

# Interactive REPL
cli-anything-labview
```

## Requirements

- **Windows** (ActiveX/COM is Windows-only)
- **Python 3.10+** with `pywin32>=300`, `click>=8.0`
- **LabVIEW 2025** with ActiveX Server enabled
- For dev: `pip install -e ".[dev]"` (adds pytest)

## Architecture

```
CLI Layer (labview_cli.py)    ← Click groups, JSON output, REPL
Core Layer (core/*.py)        ← project, vi, control, run, session, export
Backend Layer (utils/*.py)    ← ActiveX/COM (primary) + subprocess (fallback)
```

Full docs: [CLAUDE.md](CLAUDE.md) · [LABVIEW.md](LABVIEW.md) · [README (package)](cli_anything/labview/README.md)

## Tests

```bash
# Unit tests (no LabVIEW required)
pytest cli_anything/labview/tests/test_core.py -v

# Full suite
pytest cli_anything/labview/tests/ -v

# Force installed-command mode
CLI_ANYTHING_FORCE_INSTALLED=1 pytest cli_anything/labview/tests/ -v -s
```

56 tests, 100% pass rate. See [TEST.md](cli_anything/labview/tests/TEST.md).

## License

Apache License 2.0 — see [LICENSE](LICENSE).
