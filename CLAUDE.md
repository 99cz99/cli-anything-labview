# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Identity

This is a **CLI-Anything harness for NI LabVIEW 2025** — a Python CLI that controls LabVIEW via ActiveX/COM automation. The harness lives in `agent-harness/` and follows the cli-anything methodology (HARNESS.md).

The root directory (`E:\labview\LabVIEW 2025`) is a LabVIEW 2025 installation. The harness code lives entirely within `agent-harness/`.

## Essential Commands

```bash
# Install the CLI in development mode
cd agent-harness && pip install -e .

# Run unit tests (no LabVIEW required, fast)
python -m pytest agent-harness/cli_anything/labview/tests/test_core.py -v

# Run full test suite (requires LabVIEW installation directory)
python -m pytest agent-harness/cli_anything/labview/tests/ -v

# Force installed-command mode for E2E tests
CLI_ANYTHING_FORCE_INSTALLED=1 python -m pytest agent-harness/cli_anything/labview/tests/ -v -s

# Run the CLI directly
cli-anything-labview status check
cli-anything-labview --json vi find "E:/labview/LabVIEW 2025/examples"
cli-anything-labview --json project new -n "Test" -o test.json

# Enter interactive REPL
cli-anything-labview
```

## Architecture

### Layered Design

```
CLI Layer (labview_cli.py)
    │  Click groups: project, vi, control, run, build, session, status
    │  Dual output: human-readable (ReplSkin) + JSON (--json flag)
    │  Default: REPL mode via invoke_without_command=True
    │
Core Layer (core/*.py)
    │  project.py — project CRUD, VI management, build specs
    │  vi.py — VI open/close/create/save/info/find
    │  control.py — front panel control read/write
    │  run.py — VI execution, I/O, CLI launch
    │  session.py — stateful session, undo/redo (50-level deep-copy stack)
    │  export.py — build specifications, deployment config
    │
Backend Layer (utils/labview_backend.py)
    │  Primary: ActiveX/COM via pywin32 (LabVIEW.Application)
    │  Fallback: subprocess launch (LabVIEW.exe <vi> -- args)
    │  Future: VI Server TCP (port 3363)
    │
Session Layer (utils/repl_skin.py)
       ReplSkin: branded banner, colored prompts, tables, progress bars
       All ASCII-safe for Windows GBK terminal compatibility
```

### Key Design Decisions

**PEP 420 namespace package**: `cli_anything/` has NO `__init__.py`. The sub-package `cli_anything/labview/` HAS `__init__.py`. This allows multiple independently-installed `cli-anything-*` packages to coexist.

**Session state management**: The `Session` class in `core/session.py` maintains undo/redo via deep-copy snapshots (capped at 50 levels). State is persisted as JSON using atomic write (tmp file + rename). `push_state()` must be called before any mutation.

**JSON output mode**: `--json` is defined ONLY on the root `cli` Click group, NOT on individual subcommands. Subcommands read the flag via `_get_json_mode()` which calls `click.get_current_context().find_root().obj.get("use_json")`. This avoids Click option shadowing issues.

**ActiveX `_FlagAsMethod()` workaround**: LabVIEW's type library doesn't flag `Run()`, `Abort()`, `OpenFrontPanel()`, `Close()` etc. as callable methods. Every VI reference opened via COM must have `_flag_vi_methods()` called on it, or calling those methods returns `TypeError: 'NoneType' object is not callable`.

**Terminal encoding**: All output is ASCII-safe. Unicode marks (✓, ✗) and box-drawing characters are replaced with ASCII equivalents to avoid `UnicodeEncodeError` on Windows GBK terminals.

### Backend: Two-Tier Strategy

1. **COM (primary)**: `LabVIEWBackend.connect()` → `win32com.client.Dispatch("LabVIEW.Application")` → `.GetVIReference(path)` → operate via `VI` object methods
2. **CLI (fallback)**: `LabVIEWBackend.run_vi_cli()` → `subprocess.run([labview_path, vi_path, "--", *args])`

The COM backend tracks open VI references in `_open_vis: Dict[str, VI]`. Always call `_flag_vi_methods(vi)` after opening a VI reference.

### Session Pattern

Every mutation command must:
1. Call `session.push_state()` before mutating (enables undo)
2. Track relevant state changes (open VIs, control values, variables)
3. Use `session.add_open_vi()` / `session.remove_open_vi()` for VI tracking

Session saves use atomic write: write to `<path>.tmp`, `fsync()`, then `os.replace(tmp, path)`.

## Adding New Commands

1. Define the core logic in `core/<module>.py` (takes `backend` + `session` as parameters)
2. Add a Click command in `labview_cli.py` under the appropriate group
3. Use `use_json = _get_json_mode()` at function start (do NOT add `--json` option to the command decorator)
4. Follow the dual-output pattern: `if use_json: click.echo(json_success(...)) else: _skin.success(...)`
5. Add tests to both `test_core.py` (unit, synthetic data) and `test_full_e2e.py` (CLI subprocess)

## Package Structure

```
agent-harness/
├── LABVIEW.md              # Architecture SOP (read this before major changes)
├── setup.py                # PEP 420 namespace package config
├── skills/
│   └── cli-anything-labview/
│       └── SKILL.md        # Canonical skill definition (YAML frontmatter)
└── cli_anything/           # NO __init__.py (namespace package)
    └── labview/            # HAS __init__.py
        ├── labview_cli.py  # Click CLI entry point (console_scripts)
        ├── __main__.py     # python -m cli_anything.labview
        ├── README.md
        ├── skills/SKILL.md # Packaged SKILL.md copy
        ├── core/
        │   ├── session.py  # Stateful session + undo/redo
        │   ├── project.py  # Project CRUD, VI references, build specs
        │   ├── vi.py       # VI operations
        │   ├── control.py  # Front panel control read/write
        │   ├── run.py      # VI execution
        │   └── export.py   # Build specifications
        ├── utils/
        │   ├── labview_backend.py  # COM/ActiveX backend
        │   └── repl_skin.py        # Terminal output formatting
        └── tests/
            ├── TEST.md            # Test plan + results
            ├── test_core.py       # 35 unit tests (synthetic data)
            └── test_full_e2e.py   # 21 E2E + CLI subprocess tests
```

## Constraints

- **Windows only** — COM/ActiveX requires Windows. `fcntl` is Unix-only; the codebase handles this with `try/except ImportError`.
- **LabVIEW is a hard dependency** — tests verify LabVIEW installation but COM-level tests require actual LabVIEW IDE interaction.
- **ActiveX Server must be enabled** — LabVIEW → Tools → Options → VI Server → ActiveX → Enable.
- **Python 3.10+** with `pywin32>=300` and `click>=8.0`.
- **`--json` must be on the root group only** — do not add `--json` to individual subcommands; use `_get_json_mode()`.
