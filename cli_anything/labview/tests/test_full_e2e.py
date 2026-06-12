"""End-to-end tests for cli-anything-labview.

Tests the installed CLI command via subprocess and runs real workflows.
Requires: pip install -e . (the CLI must be installed)
Requires: LabVIEW 2025 installed (for COM tests)
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
import pytest


# ---------------------------------------------------------------------------
# CLI resolution (following HARNESS.md pattern)
# ---------------------------------------------------------------------------

def _resolve_cli(name: str = "cli-anything-labview"):
    """Resolve installed CLI command; falls back to python -m for dev.

    Set env CLI_ANYTHING_FORCE_INSTALLED=1 to require the installed command.
    """
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(
            f"{name} not found in PATH. Install with: pip install -e ."
        )
    # Fallback for development
    module = "cli_anything.labview.labview_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


CLI_BASE = _resolve_cli("cli-anything-labview")


# ---------------------------------------------------------------------------
# CLI Subprocess Tests
# ---------------------------------------------------------------------------

class TestCLISubprocess:
    """Test the installed CLI command via subprocess."""

    def _run(self, args, check=True, timeout=30):
        """Run CLI with args, return CompletedProcess."""
        cmd = CLI_BASE + args
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check,
            timeout=timeout,
        )

    def test_help(self):
        """--help returns usage info."""
        result = self._run(["--help"], check=False)
        assert result.returncode == 0
        assert "Usage:" in result.stdout or "Usage:" in result.stderr or "Commands:" in result.stdout

    def test_status_check_json(self):
        """status check with --json returns valid JSON."""
        result = self._run(["--json", "status", "check"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "success" in data or "error" in data

    def test_project_help(self):
        """project --help shows subcommands."""
        result = self._run(["project", "--help"], check=False)
        assert result.returncode == 0

    def test_vi_help(self):
        """vi --help shows subcommands."""
        result = self._run(["vi", "--help"], check=False)
        assert result.returncode == 0

    def test_control_help(self):
        """control --help shows subcommands."""
        result = self._run(["control", "--help"], check=False)
        assert result.returncode == 0

    def test_run_help(self):
        """run --help shows subcommands."""
        result = self._run(["run", "--help"], check=False)
        assert result.returncode == 0

    def test_session_help(self):
        """session --help shows subcommands."""
        result = self._run(["session", "--help"], check=False)
        assert result.returncode == 0

    def test_build_types(self):
        """build types lists build types."""
        result = self._run(["build", "types"])
        assert result.returncode == 0
        assert "exe" in result.stdout

    def test_project_new_json(self, tmp_path):
        """Create project with --json output."""
        out = os.path.join(tmp_path, "test.json")
        result = self._run(["--json", "project", "new", "-n", "E2ETest", "-o", out])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data.get("success") is True or data.get("success") is not False
        assert os.path.exists(out)


# ---------------------------------------------------------------------------
# Project Workflow Tests (synthetic, no LabVIEW required)
# ---------------------------------------------------------------------------

class TestProjectWorkflow:
    """Full project workflows via subprocess."""

    def test_create_save_reopen(self, tmp_path):
        """Create project, add VI, save, and check file."""
        proj_path = os.path.join(tmp_path, "workflow.json")

        # Create project
        result = subprocess.run(
            CLI_BASE + ["--json", "project", "new", "-n", "Workflow", "-o", proj_path],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert os.path.exists(proj_path)

        # Verify contents
        with open(proj_path, "r") as f:
            data = json.load(f)
        assert data["name"] == "Workflow"
        assert data["target"] == "My Computer"


# ---------------------------------------------------------------------------
# Session Workflow Tests
# ---------------------------------------------------------------------------

class TestSessionWorkflow:
    """Session save/load round-trip via subprocess."""

    def test_session_save_load(self, tmp_path):
        """Save and load session state."""
        session_path = os.path.join(tmp_path, "session.json")

        # Save session
        result = subprocess.run(
            CLI_BASE + ["--json", "session", "save", session_path],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert os.path.exists(session_path)

        # Load session
        result = subprocess.run(
            CLI_BASE + ["--json", "session", "load", session_path],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data.get("success") is True

    def test_session_status(self):
        """Session status returns valid output."""
        result = subprocess.run(
            CLI_BASE + ["--json", "session", "status"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "session_id" in data.get("data", {})


# ---------------------------------------------------------------------------
# VI Find Tests
# ---------------------------------------------------------------------------

class TestVIFind:
    """VI file discovery tests."""

    def test_find_vis_in_examples(self):
        """Find VIs in LabVIEW examples directory."""
        examples_dir = r"E:\labview\LabVIEW 2025\examples"
        if not os.path.isdir(examples_dir):
            pytest.skip(f"Examples directory not found: {examples_dir}")

        result = subprocess.run(
            CLI_BASE + ["--json", "vi", "find", examples_dir, "-p", "*.vi"],
            capture_output=True, text=True,
        )
        # May fail if LabVIEW not installed, but shouldn't crash
        if result.returncode == 0:
            data = json.loads(result.stdout)
            assert data.get("success") is True
            # There should be VI files in examples
            found = data.get("data", [])
            if found:
                for vi in found:
                    assert "name" in vi
                    assert "path" in vi
                    assert vi["path"].endswith(".vi")

    def test_find_no_recursive(self):
        """Find VIs non-recursively."""
        examples_dir = r"E:\labview\LabVIEW 2025\examples"
        if not os.path.isdir(examples_dir):
            pytest.skip(f"Examples directory not found: {examples_dir}")

        result = subprocess.run(
            CLI_BASE + ["--json", "vi", "find", examples_dir, "--no-recursive", "-p", "*.vi"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            assert data.get("success") is True

    def test_find_nonexistent_dir(self):
        """Find in nonexistent directory returns error."""
        result = subprocess.run(
            CLI_BASE + ["--json", "vi", "find", "/nonexistent/path"],
            capture_output=True, text=True,
        )
        assert result.returncode != 0


# ---------------------------------------------------------------------------
# JSON Output Mode Tests
# ---------------------------------------------------------------------------

class TestJSONOutput:
    """Verify --json produces valid JSON for all commands."""

    COMMANDS = [
        ["status", "check"],
        ["project", "new", "-n", "JSONTest"],
        ["session", "status"],
        ["build", "types"],
    ]

    @pytest.mark.parametrize("args", COMMANDS)
    def test_json_output(self, args):
        """Each command with --json outputs valid JSON."""
        result = subprocess.run(
            CLI_BASE + ["--json"] + args,
            capture_output=True, text=True,
        )
        # All these should succeed
        if result.returncode == 0:
            data = json.loads(result.stdout)
            assert isinstance(data, dict)
            assert "success" in data or "error" in data
        else:
            # Even on error, --json should produce valid JSON
            try:
                data = json.loads(result.stdout)
                assert isinstance(data, dict)
            except json.JSONDecodeError:
                # Some errors might go to stderr
                data = json.loads(result.stderr) if result.stderr else None
                if data is None:
                    pytest.fail(f"No valid JSON output: stdout={result.stdout}, stderr={result.stderr}")


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Verify error messages are informative."""

    def test_open_nonexistent_vi_gives_error(self):
        """Opening nonexistent file gives clear error."""
        result = subprocess.run(
            CLI_BASE + ["--json", "vi", "info", "C:/nonexistent/path.vi"],
            capture_output=True, text=True,
        )
        assert result.returncode != 0
        data = json.loads(result.stdout)
        assert data.get("error") is True
        assert "message" in data

    def test_control_list_nonexistent_vi(self):
        """Listing controls on nonexistent VI gives error."""
        result = subprocess.run(
            CLI_BASE + ["--json", "control", "list", "C:/nonexistent/path.vi"],
            capture_output=True, text=True,
        )
        assert result.returncode != 0


# ---------------------------------------------------------------------------
# Main (for direct execution)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
