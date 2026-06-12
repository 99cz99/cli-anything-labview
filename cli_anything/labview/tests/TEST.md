# TEST.md — cli-anything-labview

## Part 1: Test Plan

### Test Inventory

| File | Type | Planned Tests |
|------|------|---------------|
| `test_core.py` | Unit tests (synthetic data) | 29 |
| `test_full_e2e.py` | E2E + CLI subprocess tests | 18 |

### Unit Test Plan — `test_core.py`

| Module | Functions Tested | Edge Cases |
|--------|-----------------|------------|
| `session.py` | create, undo, redo, push_state, add_open_vi, remove_open_vi, cache_control_value, set_var/get_var, serialize/deserialize, save/load | Empty undo/redo stacks, MAX_UNDO limit, redo cleared on push, roundtrip fidelity |
| `project.py` | create_project, open_project, save_project, get_project_info, add_vi_to_project, remove_vi_from_project, add_build_spec, list_project_files, list_build_specs | Duplicate VIs, nonexistent files, missing paths, empty projects |
| `export.py` | build_type_options, add_build_spec, get_build_spec, remove_build_spec, export_build_config, run_build, list_build_specs | Missing specs, empty spec lists |

### E2E Test Plan — `test_full_e2e.py`

| Test Class | Description | Real Software Required |
|------------|-------------|----------------------|
| `TestCLISubprocess` | Invoke installed CLI via subprocess | No (help/text commands) |
| `TestProjectWorkflow` | Create → save → verify project end-to-end | No |
| `TestSessionWorkflow` | Save → load → verify session roundtrip | No |
| `TestVIFind` | Find VI files in LabVIEW examples directory | Yes (LabVIEW dir must exist) |
| `TestJSONOutput` | Parametrized: all commands produce valid JSON | No |
| `TestErrorHandling` | Error messages for invalid inputs | No |

### Realistic Workflow Scenarios

1. **Project Setup** — Create project, add VIs, save, reopen
2. **Session Persistence** — Run operations, save session, load in new session
3. **VI Discovery** — Find VIs in LabVIEW installation directories
4. **Error Recovery** — Invalid VIs produce clear error messages

---

## Part 2: Test Results

### Full Test Suite Run — 2026-06-12

```
[_resolve_cli] Using installed command: C:\Users\CAOZHI\AppData\Local\Programs\Python\Python311\Scripts\cli-anything-labview.EXE
============================= 56 passed in 10.75s ==============================

Unit Tests (test_core.py): 35/35 passed
  TestSession: 14 tests — session creation, undo/redo, VI tracking, serialization
  TestProject: 10 tests — project CRUD, VI management, build specs
  TestExport: 7 tests — build types, spec management, config export
  TestSessionUndoWithVis: 2 tests — undo/redo with VI and variable operations

E2E Tests (test_full_e2e.py): 21/21 passed
  TestCLISubprocess: 9 tests — help, JSON output, project creation via CLI
  TestProjectWorkflow: 1 test — create → save → verify
  TestSessionWorkflow: 2 tests — session save/load roundtrip
  TestVIFind: 3 tests — find VIs in examples, recursive/non-recursive, errors
  TestJSONOutput: 4 tests — parametrized JSON output across all command groups
  TestErrorHandling: 2 tests — clear error messages for invalid inputs

### Summary

| Metric | Value |
|--------|-------|
| Total Tests | 56 |
| Passed | 56 |
| Failed | 0 |
| Pass Rate | 100% |
| Execution Time | 10.75s |
| Backend | Installed command (`cli-anything-labview.EXE`) |
| Coverage | All core modules, CLI subprocess, JSON mode, error paths |

### Coverage Notes

- **Session management**: Full undo/redo, serialization, VI tracking tested
- **Project operations**: CRUD, VI management, build specs tested
- **CLI interface**: All subcommands verified via subprocess
- **JSON output**: All command groups produce valid JSON
- **Error handling**: Invalid inputs produce clear, parsed errors
- **LabVIEW backend**: COM availability detected, not tested in-depth (requires running LabVIEW)
- **COM operations**: VI open/close/run/control — tested structurally, real COM testing requires LabVIEW IDE interaction
- **VI Server TCP**: Not tested (requires network setup and documented protocol)

### Running Tests

```bash
# Unit tests only (no LabVIEW required)
cd E:\labview\LabVIEW 2025\agent-harness
python -m pytest cli_anything/labview/tests/test_core.py -v --tb=short

# Full test suite
python -m pytest cli_anything/labview/tests/ -v --tb=short

# Force installed command mode
CLI_ANYTHING_FORCE_INSTALLED=1 python -m pytest cli_anything/labview/tests/ -v -s
```
