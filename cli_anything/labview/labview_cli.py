#!/usr/bin/env python3
"""cli-anything-labview — CLI harness for NI LabVIEW.

Stateful command-line interface for controlling LabVIEW via ActiveX/COM,
VI Server, and command-line invocation. Supports both one-shot commands
and interactive REPL mode.

Usage:
    cli-anything-labview --help          # Show help
    cli-anything-labview                 # Enter REPL mode (default)
    cli-anything-labview --json ...      # Machine-readable JSON output
"""

import os
import sys
import json
from typing import Any
import click

from .core import project, vi, control, run, export, session as session_mod
from .utils.labview_backend import LabVIEWBackend, check_labview_installation
from .utils.repl_skin import ReplSkin, json_output, json_error, json_success


# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

_skin = ReplSkin("labview", version="1.0.0")
_backend: LabVIEWBackend = LabVIEWBackend()
_session: session_mod.Session = session_mod.Session()


def _get_json_mode() -> bool:
    """Read --json flag from the root CLI context."""
    try:
        ctx = click.get_current_context()
        root = ctx.find_root()
        return root.obj.get("use_json", False) if root.obj else False
    except (RuntimeError, AttributeError):
        return False


# ---------------------------------------------------------------------------
# Output helper
# ---------------------------------------------------------------------------

def _emit(result_fn, success_msg=None):
    """Emit command result in current mode.

    result_fn(result) is called in non-JSON mode.
    In JSON mode, the function's return value is serialized as JSON.
    """
    pass  # Marker — actual logic inlined below


# ---------------------------------------------------------------------------
# Project commands
# ---------------------------------------------------------------------------

@click.group(name="project")
def project_group():
    """Project management — create, open, save, and inspect LabVIEW projects."""
    pass


@project_group.command("new")
@click.option("-n", "--name", required=True, help="Project name.")
@click.option("-o", "--output", "output_path", default=None, help="Output path for project JSON.")
@click.option("-t", "--target", default="My Computer", help="Target hardware label.")
def project_new(name, output_path, target):
    """Create a new LabVIEW project."""
    use_json = _get_json_mode()
    try:
        result = project.create_project(name, output_path, target)
        _session.project_name = name
        _session.project_path = output_path
        if use_json:
            click.echo(json_success(result))
        else:
            _skin.success(f"Project '{name}' created.")
            if output_path:
                _skin.status("Output", output_path)
            _skin.status("Target", target)
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


@project_group.command("open")
@click.argument("project_path")
def project_open(project_path):
    """Open a LabVIEW project from a .lvproj or .json file."""
    use_json = _get_json_mode()
    try:
        result = project.open_project(project_path)
        _session.project_path = project_path
        _session.project_name = result.get("name")
        if use_json:
            click.echo(json_success(result))
        else:
            _skin.success(f"Project '{result.get('name')}' opened.")
            info = project.get_project_info(result)
            _skin.status("Files", str(info.get("file_count", 0)))
            _skin.status("Build Specs", str(info.get("build_spec_count", 0)))
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


@project_group.command("save")
@click.option("-o", "--output", "output_path", help="Output path (defaults to project path).")
def project_save(output_path):
    """Save the current project."""
    use_json = _get_json_mode()
    try:
        proj_data = {
            "name": _session.project_name or "Untitled",
            "path": _session.project_path,
        }
        result = project.save_project(proj_data, output_path)
        _session.project_path = result.get("path")
        if use_json:
            click.echo(json_success(result))
        else:
            _skin.success(f"Project saved to {result.get('path')}")
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


@project_group.command("info")
def project_info():
    """Show current project information."""
    use_json = _get_json_mode()
    try:
        info = {
            "project_name": _session.project_name,
            "project_path": _session.project_path,
            "open_vis": _session.open_vis,
            "running_vis": _session.running_vis,
            "variables": _session.variables,
            "session_id": _session.session_id,
            "undo_depth": _session.undo_depth,
            "redo_depth": _session.redo_depth,
        }
        if use_json:
            click.echo(json_success(info))
        else:
            if _session.project_name:
                _skin.status("Project", _session.project_name)
                _skin.status("Path", _session.project_path or "(not saved)")
            else:
                _skin.info("No project open.")
            _skin.status("Open VIs", str(len(_session.open_vis)))
            for vi_path in _session.open_vis:
                print(f"    {vi_path}")
            _skin.status("Session", _session.session_id)
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


@project_group.command("add-vi")
@click.argument("vi_path")
@click.option("-c", "--category", default="main", help="VI category.")
def project_add_vi(vi_path, category):
    """Add a VI reference to the current project."""
    use_json = _get_json_mode()
    try:
        proj_data = {"name": _session.project_name, "path": _session.project_path, "files": []}
        result = project.add_vi_to_project(proj_data, vi_path, category)
        if use_json:
            click.echo(json_success(result))
        else:
            _skin.success(f"Added VI: {vi_path} ({category})")
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


@project_group.command("list-files")
def project_list_files():
    """List all VIs in the current project."""
    use_json = _get_json_mode()
    try:
        files = project.list_project_files({"files": []})
        if use_json:
            click.echo(json_success(files))
        else:
            if files:
                _skin.table(["Name", "Path", "Category"], [
                    [f.get("name", ""), f.get("path", ""), f.get("category", "")]
                    for f in files
                ])
            else:
                _skin.info("No files in project.")
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


# ---------------------------------------------------------------------------
# VI commands
# ---------------------------------------------------------------------------

@click.group(name="vi")
def vi_group():
    """VI operations — open, close, create, save, and inspect VIs."""
    pass


@vi_group.command("open")
@click.argument("vi_path")
def vi_open(vi_path):
    """Open a VI."""
    use_json = _get_json_mode()
    try:
        result = vi.open_vi(_backend, vi_path, _session)
        if use_json:
            click.echo(json_success(result))
        else:
            _skin.success(f"VI opened: {result['name']}")
            _skin.status("Path", result["vi_path"])
            _skin.status("Size", f"{result['file_size']:,} bytes")
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


@vi_group.command("close")
@click.argument("vi_path")
def vi_close(vi_path):
    """Close a VI."""
    use_json = _get_json_mode()
    try:
        result = vi.close_vi(_backend, vi_path, _session)
        if use_json:
            click.echo(json_success(result))
        else:
            _skin.success(f"VI closed: {vi_path}")
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


@vi_group.command("create")
@click.option("-o", "--output", "output_path", default=None, help="Save path for the new VI.")
def vi_create(output_path):
    """Create a new blank VI."""
    use_json = _get_json_mode()
    try:
        result = vi.create_vi(_backend, output_path, _session)
        if use_json:
            click.echo(json_success(result))
        else:
            _skin.success(f"New VI created: {result['vi_path']}")
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


@vi_group.command("save")
@click.argument("vi_path")
@click.option("--as", "new_path", default=None, help="Save as a new path.")
def vi_save(vi_path, new_path):
    """Save a VI."""
    use_json = _get_json_mode()
    try:
        result = vi.save_vi(_backend, vi_path, new_path)
        if use_json:
            click.echo(json_success(result))
        else:
            msg = f"Saved: {result.get('saved_as', vi_path)}" if new_path else f"Saved: {vi_path}"
            _skin.success(msg)
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


@vi_group.command("info")
@click.argument("vi_path")
def vi_info(vi_path):
    """Show detailed information about a VI."""
    use_json = _get_json_mode()
    try:
        result = vi.get_vi_info(_backend, vi_path)
        if use_json:
            click.echo(json_success(result))
        else:
            _skin.status("Name", result["name"])
            _skin.status("Path", result["path"])
            _skin.status("Directory", result["directory"])
            _skin.status("Size", f"{result['file_size']:,} bytes")
            _skin.status("Modified", result["modified"])
            _skin.status("Exec State", result.get("execution_state", "unknown"))
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


@vi_group.command("list")
def vi_list():
    """List all currently open VIs."""
    use_json = _get_json_mode()
    try:
        open_vis = vi.list_open_vis(_backend)
        if use_json:
            click.echo(json_success(open_vis))
        else:
            if open_vis:
                for vp in open_vis:
                    print(f"  {vp}")
            else:
                _skin.info("No VIs currently open.")
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


@vi_group.command("find")
@click.argument("directory")
@click.option("-p", "--pattern", default="*.vi", help="File pattern (default: *.vi).")
@click.option("-r", "--recursive/--no-recursive", default=True, help="Search recursively.")
def vi_find(directory, pattern, recursive):
    """Find VI files in a directory."""
    use_json = _get_json_mode()
    try:
        results = vi.find_vis(directory, pattern, recursive)
        if use_json:
            click.echo(json_success(results))
        else:
            if results:
                _skin.table(
                    ["Name", "Path", "Size", "Modified"],
                    [[r["name"], r["path"], f"{r['size']:,}", r["modified"]] for r in results[:50]]
                )
                if len(results) > 50:
                    _skin.info(f"... and {len(results) - 50} more VIs")
            else:
                _skin.info(f"No VIs found matching '{pattern}' in {directory}")
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


# ---------------------------------------------------------------------------
# Control commands
# ---------------------------------------------------------------------------

@click.group(name="control")
def control_group():
    """Front panel controls — get/set control and indicator values."""
    pass


@control_group.command("get")
@click.argument("vi_path")
@click.argument("control_name")
def control_get(vi_path, control_name):
    """Get a control or indicator value."""
    use_json = _get_json_mode()
    try:
        result = control.get_control(_backend, vi_path, control_name, _session)
        if use_json:
            click.echo(json_success(result))
        else:
            _skin.status("VI", vi_path)
            _skin.status("Control", control_name)
            _skin.status("Value", str(result.get("value")))
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


@control_group.command("set")
@click.argument("vi_path")
@click.argument("control_name")
@click.argument("value")
def control_set(vi_path, control_name, value):
    """Set a control value. VALUE: number, true/false, string, or JSON."""
    use_json = _get_json_mode()
    try:
        typed_value = _coerce_value(value)
        result = control.set_control(_backend, vi_path, control_name, typed_value, _session)
        if use_json:
            click.echo(json_success(result))
        else:
            _skin.success(f"Set '{control_name}' = {typed_value}")
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


@control_group.command("list")
@click.argument("vi_path")
def control_list(vi_path):
    """List all controls and indicators on a VI's front panel."""
    use_json = _get_json_mode()
    try:
        results = control.list_controls(_backend, vi_path)
        if use_json:
            click.echo(json_success(results))
        else:
            if results:
                _skin.table(
                    ["#", "Name", "Value", "Type"],
                    [[str(c["index"]), c["name"], str(c.get("value", "")), c.get("type", "")]
                     for c in results]
                )
            else:
                _skin.info("No controls found.")
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


@control_group.command("set-multiple")
@click.argument("vi_path")
@click.argument("values_json")
def control_set_multiple(vi_path, values_json):
    """Set multiple control values from a JSON string. Example: '{"a": 1, "b": "hello"}'"""
    use_json = _get_json_mode()
    try:
        values = json.loads(values_json)
        result = control.set_multiple_controls(_backend, vi_path, values, _session)
        if use_json:
            click.echo(json_success(result))
        else:
            for name, r in result.get("results", {}).items():
                if r["status"] == "ok":
                    _skin.success(f"  {name} = {r['value']}")
                else:
                    _skin.error(f"  {name}: {r['message']}")
    except json.JSONDecodeError as e:
        msg = f"Invalid JSON: {e}"
        if use_json:
            click.echo(json_error(msg))
        else:
            _skin.error(msg)
        sys.exit(1)
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


# ---------------------------------------------------------------------------
# Run commands
# ---------------------------------------------------------------------------

@click.group(name="run")
def run_group():
    """VI execution — run, stop, and monitor VIs."""
    pass


@run_group.command("start")
@click.argument("vi_path")
@click.option("-w", "--wait/--no-wait", default=False, help="Wait for VI to complete.")
def run_start(vi_path, wait):
    """Run a VI."""
    use_json = _get_json_mode()
    try:
        result = run.run_vi(_backend, vi_path, wait=wait, session=_session)
        if use_json:
            click.echo(json_success(result))
        else:
            status = "completed" if wait else "running"
            _skin.success(f"VI {status}: {vi_path}")
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


@run_group.command("stop")
@click.argument("vi_path")
def run_stop(vi_path):
    """Abort a running VI."""
    use_json = _get_json_mode()
    try:
        result = run.stop_vi(_backend, vi_path, _session)
        if use_json:
            click.echo(json_success(result))
        else:
            _skin.success(f"VI stopped: {vi_path}")
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


@run_group.command("status")
@click.argument("vi_path")
def run_status(vi_path):
    """Get execution status of a VI."""
    use_json = _get_json_mode()
    try:
        result = run.get_status(_backend, vi_path)
        if use_json:
            click.echo(json_success(result))
        else:
            _skin.status("VI", result["vi_path"])
            _skin.status("State", result.get("execution_state", "unknown"))
            _skin.status("Open", str(result.get("is_open", False)))
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


@run_group.command("io")
@click.argument("vi_path")
@click.argument("inputs_json")
@click.argument("outputs_json")
def run_io(vi_path, inputs_json, outputs_json):
    """Run a VI with inputs and read outputs.
    INPUTS_JSON: '{"control_name": value, ...}'
    OUTPUTS_JSON: '["indicator_name", ...]'
    """
    use_json = _get_json_mode()
    try:
        inputs = json.loads(inputs_json)
        outputs = json.loads(outputs_json)
        result = run.run_and_read(_backend, vi_path, inputs, outputs, session=_session)
        if use_json:
            click.echo(json_success(result))
        else:
            _skin.success(f"VI completed: {vi_path}")
            _skin.status("Inputs", str(inputs))
            _skin.status("Outputs", str(result["outputs"]))
    except json.JSONDecodeError as e:
        msg = f"Invalid JSON: {e}"
        if use_json:
            click.echo(json_error(msg))
        else:
            _skin.error(msg)
        sys.exit(1)
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


@run_group.command("cli")
@click.argument("vi_path")
@click.argument("args", nargs=-1)
@click.option("-t", "--timeout", type=int, default=None, help="Timeout in seconds.")
def run_cli(vi_path, args, timeout):
    """Run a VI via LabVIEW.exe command line. Passes arguments to the VI."""
    use_json = _get_json_mode()
    try:
        result = run.run_cli_mode(_backend, vi_path, list(args) if args else None, timeout)
        if use_json:
            click.echo(json_success(result))
        else:
            _skin.status("Return code", str(result.get("returncode", "N/A")))
            if result.get("stdout"):
                print(result["stdout"])
            if result.get("stderr"):
                _skin.warning(result["stderr"])
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


# ---------------------------------------------------------------------------
# Build commands
# ---------------------------------------------------------------------------

@click.group(name="build")
def build_group():
    """Build and deployment — manage build specifications."""
    pass


@build_group.command("types")
def build_types():
    """List available build types."""
    use_json = _get_json_mode()
    types = export.build_type_options()
    if use_json:
        click.echo(json_success(types))
    else:
        for t, desc in types.items():
            print(f"  {click.style(t, fg='cyan'):<24} {desc}")


@build_group.command("list")
def build_list():
    """List build specifications in the current project."""
    use_json = _get_json_mode()
    try:
        specs = export.list_build_specs({"build_specs": []})
        if use_json:
            click.echo(json_success(specs))
        else:
            if specs:
                _skin.table(
                    ["Name", "Type", "Source VI", "Output Dir"],
                    [[s.get("name"), s.get("type"), s.get("source_vi", ""), s.get("output_dir", "")]
                     for s in specs]
                )
            else:
                _skin.info("No build specifications defined.")
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


# ---------------------------------------------------------------------------
# Session commands
# ---------------------------------------------------------------------------

@click.group(name="session")
def session_group():
    """Session management — undo, redo, save, load session state."""
    pass


@session_group.command("status")
def session_status():
    """Show session status."""
    use_json = _get_json_mode()
    data = _session.to_dict()
    if use_json:
        click.echo(json_success(data))
    else:
        _skin.status("Session ID", data["session_id"])
        _skin.status("Project", data.get("project_name", "(none)"))
        _skin.status("Open VIs", str(len(data.get("open_vis", []))))
        _skin.status("Running VIs", str(len(data.get("running_vis", []))))
        _skin.status("Variables", str(len(data.get("variables", {}))))
        _skin.status("Undo depth", str(data.get("undo_depth", 0)))
        _skin.status("Redo depth", str(data.get("redo_depth", 0)))


@session_group.command("undo")
def session_undo():
    """Undo the last operation."""
    use_json = _get_json_mode()
    try:
        if _session.undo():
            if use_json:
                click.echo(json_success({"action": "undo", "remaining": _session.undo_depth}))
            else:
                _skin.success(f"Undo ({_session.undo_depth} remaining)")
        else:
            msg = "Nothing to undo."
            if use_json:
                click.echo(json_output({"action": "undo", "status": "nothing_to_undo"}))
            else:
                _skin.info(msg)
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


@session_group.command("redo")
def session_redo():
    """Redo the last undone operation."""
    use_json = _get_json_mode()
    try:
        if _session.redo():
            if use_json:
                click.echo(json_success({"action": "redo", "remaining": _session.redo_depth}))
            else:
                _skin.success(f"Redo ({_session.redo_depth} remaining)")
        else:
            msg = "Nothing to redo."
            if use_json:
                click.echo(json_output({"action": "redo", "status": "nothing_to_redo"}))
            else:
                _skin.info(msg)
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


@session_group.command("save")
@click.argument("filepath")
def session_save(filepath):
    """Save session state to a file."""
    use_json = _get_json_mode()
    try:
        _session.save(filepath)
        if use_json:
            click.echo(json_success({"saved": filepath}))
        else:
            _skin.success(f"Session saved to {filepath}")
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


@session_group.command("load")
@click.argument("filepath")
def session_load(filepath):
    """Load session state from a file."""
    global _session
    use_json = _get_json_mode()
    try:
        _session = session_mod.Session.load(filepath)
        if use_json:
            click.echo(json_success({"loaded": filepath, "session_id": _session.session_id}))
        else:
            _skin.success(f"Session loaded: {_session.session_id}")
            _skin.status("Project", _session.project_name or "(none)")
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


# ---------------------------------------------------------------------------
# Status commands
# ---------------------------------------------------------------------------

@click.group(name="status")
def status_cmd_group():
    """System status — check LabVIEW installation and backend connectivity."""
    pass


@status_cmd_group.command("check")
def status_check():
    """Check LabVIEW installation and connectivity."""
    use_json = _get_json_mode()
    try:
        info = check_labview_installation()
        if use_json:
            click.echo(json_success(info))
        else:
            _skin.status("LabVIEW", "Found" if info["installed"] else "Not found")
            if info.get("labview_path"):
                _skin.status("Path", info["labview_path"])
                _skin.status("Version", info.get("version", "unknown"))
            _skin.status("COM Available", "Yes" if info["com_available"] else "No (pip install pywin32)")
            _skin.status("Running", "Yes" if info["labview_running"] else "No")
    except Exception as e:
        if use_json:
            click.echo(json_error(str(e)))
        else:
            _skin.error(str(e))
        sys.exit(1)


# ---------------------------------------------------------------------------
# REPL mode
# ---------------------------------------------------------------------------

@click.command(name="repl")
def repl_cmd():
    """Enter interactive REPL mode (default when no subcommand is specified)."""
    import shlex

    _skin.print_banner()
    _skin.info("Type 'help' for commands, 'quit' to exit.")

    commands = {
        "project new|open|save|info|add-vi|list-files": "Project management",
        "vi open|close|create|save|info|list|find": "VI operations",
        "control get|set|list|set-multiple": "Front panel controls",
        "run start|stop|status|io|cli": "VI execution",
        "build types|list": "Build specifications",
        "session status|undo|redo|save|load": "Session management",
        "status check": "Check LabVIEW installation",
        "help": "Show this help",
        "quit": "Exit REPL",
    }

    ctx = click.get_current_context()

    while True:
        try:
            prompt = _skin.get_prompt(
                project_name=_session.project_name,
                modified=_session.is_dirty,
            )
            line = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue

        if line.lower() in ("quit", "exit", "q"):
            break

        if line.lower() in ("help", "?"):
            _skin.help(commands)
            continue

        try:
            args = shlex.split(line)
        except ValueError:
            _skin.error(f"Invalid quoting: {line}")
            continue

        try:
            from click.testing import CliRunner
            runner = CliRunner()
            result = runner.invoke(cli, args, catch_exceptions=False)
            if result.output:
                print(result.output.rstrip())
        except SystemExit:
            pass
        except Exception as e:
            _skin.error(f"{type(e).__name__}: {e}")

    _skin.print_goodbye()


# ---------------------------------------------------------------------------
# Main CLI group
# ---------------------------------------------------------------------------

@click.group(invoke_without_command=True)
@click.option("--json", "use_json", is_flag=True, help="Machine-readable JSON output.")
@click.option("--labview-path", envvar="LABVIEW_PATH", help="Path to LabVIEW.exe.")
@click.pass_context
def cli(ctx, use_json, labview_path):
    """cli-anything-labview — CLI harness for NI LabVIEW.

    Stateful command-line interface for controlling LabVIEW via ActiveX/COM
    automation, VI Server, and command-line invocation.

    \b
    Examples:
      cli-anything-labview status check
      cli-anything-labview vi find "E:/labview/LabVIEW 2025/examples"
      cli-anything-labview --json project new -n "TestProject" -o project.json
      cli-anything-labview run cli "path/to/vi.vi" -- arg1 arg2
    """
    global _backend, _session

    ctx.ensure_object(dict)
    ctx.obj["use_json"] = use_json

    if labview_path:
        _backend = LabVIEWBackend(labview_path)

    if ctx.invoked_subcommand is None:
        ctx.invoke(repl_cmd)


# Attach subcommand groups
cli.add_command(project_group)
cli.add_command(vi_group)
cli.add_command(control_group)
cli.add_command(run_group)
cli.add_command(build_group)
cli.add_command(session_group)
cli.add_command(status_cmd_group)
cli.add_command(repl_cmd)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _coerce_value(value_str: str) -> Any:
    """Coerce a string value to an appropriate Python type: int > float > bool > JSON > string."""
    try:
        return int(value_str)
    except ValueError:
        pass
    try:
        return float(value_str)
    except ValueError:
        pass
    lower = value_str.lower()
    if lower in ("true", "yes", "on"):
        return True
    if lower in ("false", "no", "off"):
        return False
    try:
        return json.loads(value_str)
    except (json.JSONDecodeError, ValueError):
        pass
    return value_str


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
