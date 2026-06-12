"""Unit tests for cli-anything-labview core modules.

Tests all core modules with synthetic data. No LabVIEW installation required.
"""

import os
import sys
import json
import tempfile
import pytest

# Add harness to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from cli_anything.labview.core import project, session, export


# ---------------------------------------------------------------------------
# Session tests
# ---------------------------------------------------------------------------

class TestSession:
    """Tests for session.py — state management, undo/redo, serialization."""

    def test_create_session(self):
        """Session creation with defaults."""
        s = session.Session()
        assert s.session_id is not None
        assert len(s.session_id) == 8
        assert s.project_name is None
        assert s.open_vis == []
        assert s.running_vis == []
        assert s.variables == {}
        assert s.can_undo is False
        assert s.can_redo is False

    def test_session_with_id(self):
        """Session with custom ID."""
        s = session.Session(session_id="test123")
        assert s.session_id == "test123"

    def test_undo_redo(self):
        """Basic undo/redo flow."""
        s = session.Session()
        s.push_state()
        s.project_name = "TestProject"
        assert s.project_name == "TestProject"

        # Undo
        assert s.undo() is True
        assert s.project_name is None

        # Redo
        assert s.redo() is True
        assert s.project_name == "TestProject"

    def test_undo_nothing(self):
        """Undo with empty stack returns False."""
        s = session.Session()
        assert s.undo() is False

    def test_redo_nothing(self):
        """Redo with empty stack returns False."""
        s = session.Session()
        assert s.redo() is False

    def test_undo_stack_limit(self):
        """Undo stack respects MAX_UNDO limit."""
        s = session.Session()
        # Push MAX_UNDO + 10 states
        for i in range(session.Session.MAX_UNDO + 10):
            s.push_state()
            s.project_name = f"Project_{i}"

        # Should have at most MAX_UNDO entries
        assert s.undo_depth <= session.Session.MAX_UNDO

    def test_redo_cleared_on_push(self):
        """Redo stack is cleared when a new state is pushed."""
        s = session.Session()
        s.push_state()
        s.project_name = "A"
        s.undo()
        assert s.can_redo is True

        # Push new state — redo should be cleared
        s.push_state()
        s.project_name = "B"
        assert s.can_redo is False

    def test_vi_tracking(self):
        """Open/close VI tracking."""
        s = session.Session()
        vi_path = "C:/test/my_vi.vi"
        s.add_open_vi(vi_path)
        assert os.path.abspath(vi_path) in s.open_vis

        s.remove_open_vi(vi_path)
        assert vi_path not in s.open_vis

    def test_running_vi_tracking(self):
        """Running VI tracking."""
        s = session.Session()
        vi_path = "C:/test/running.vi"
        s.add_running_vi(vi_path)
        assert os.path.abspath(vi_path) in s.running_vis

        s.remove_running_vi(vi_path)
        assert vi_path not in s.running_vis

    def test_control_value_cache(self):
        """Control value caching in session."""
        s = session.Session()
        s.cache_control_value("test.vi", "input_a", 42)
        s.cache_control_value("test.vi", "input_b", "hello")

        assert s.get_cached_value("test.vi", "input_a") == 42
        assert s.get_cached_value("test.vi", "input_b") == "hello"
        assert s.get_cached_value("test.vi", "nonexistent") is None

    def test_variables(self):
        """Session variable store."""
        s = session.Session()
        s.set_var("count", 10)
        s.set_var("name", "test")

        assert s.get_var("count") == 10
        assert s.get_var("name") == "test"
        assert s.get_var("missing") is None
        assert len(s.list_vars()) == 2

    def test_serialize_to_dict(self):
        """Session serialization to dict."""
        s = session.Session(session_id="abc12345")
        s.project_name = "MyProject"
        s.project_path = "/path/to/project.json"
        s.add_open_vi("/path/to/vi.vi")
        s.set_var("key", "value")

        d = s.to_dict()
        assert d["session_id"] == "abc12345"
        assert d["project_name"] == "MyProject"
        assert len(d["open_vis"]) == 1
        assert d["variables"]["key"] == "value"

    def test_save_load_roundtrip(self):
        """Session save/load roundtrip."""
        s = session.Session(session_id="roundtrip")
        s.project_name = "RoundTripProject"
        s.project_path = "/tmp/test.json"
        s.set_var("answer", 42)
        s.cache_control_value("vi.vi", "result", 3.14)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            s.save(tmp_path)
            assert os.path.exists(tmp_path)

            loaded = session.Session.load(tmp_path)
            assert loaded.session_id == "roundtrip"
            assert loaded.project_name == "RoundTripProject"
            assert loaded.get_var("answer") == 42
        finally:
            os.unlink(tmp_path)

    def test_dirty_flag(self):
        """Dirty flag tracking."""
        s = session.Session()
        assert s.is_dirty is False
        s.push_state()
        assert s.is_dirty is True
        s.mark_clean()
        assert s.is_dirty is False


# ---------------------------------------------------------------------------
# Project tests
# ---------------------------------------------------------------------------

class TestProject:
    """Tests for project.py — project management."""

    def test_create_project_minimal(self):
        """Create project with minimal args."""
        result = project.create_project(name="TestProject")
        assert result["name"] == "TestProject"
        assert result["type"] == "lvproj"
        assert result["version"] == "2025"
        assert result["target"] == "My Computer"
        assert "created" in result
        assert result["files"] == []
        assert result["build_specs"] == []

    def test_create_project_with_output(self):
        """Create project and save to file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            result = project.create_project(
                name="FileProject",
                output_path=tmp_path,
                target="My Computer",
            )
            assert os.path.exists(tmp_path)
            assert result["path"] == tmp_path

            with open(tmp_path, "r") as f:
                data = json.load(f)
            assert data["name"] == "FileProject"
        finally:
            os.unlink(tmp_path)

    def test_open_project(self):
        """Open a project JSON file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump({"name": "SavedProject", "type": "lvproj", "version": "2025",
                        "target": "My Computer", "files": [], "build_specs": [],
                        "created": "2025-01-01T00:00:00"}, f)
            tmp_path = f.name

        try:
            result = project.open_project(tmp_path)
            assert result["name"] == "SavedProject"
            assert result["path"] == tmp_path
        finally:
            os.unlink(tmp_path)

    def test_open_project_not_found(self):
        """Open nonexistent project raises error."""
        with pytest.raises(FileNotFoundError):
            project.open_project("/nonexistent/path.json")

    def test_get_project_info(self):
        """Project info summary."""
        proj = project.create_project("InfoProject")
        proj["files"].append({
            "id": "abc", "path": "/test.vi",
            "name": "test", "category": "main",
            "added": "2025-01-01T00:00:00",
        })

        info = project.get_project_info(proj)
        assert info["name"] == "InfoProject"
        assert info["file_count"] == 1
        assert info["build_spec_count"] == 0

    def test_add_vi_to_project(self):
        """Add VI reference to project."""
        proj = project.create_project("Test")
        proj = project.add_vi_to_project(proj, "C:/test/main.vi", "main")
        assert len(proj["files"]) == 1
        assert proj["files"][0]["name"] == "main"
        assert proj["files"][0]["category"] == "main"

    def test_add_duplicate_vi(self):
        """Adding duplicate VI is idempotent."""
        proj = project.create_project("Test")
        proj = project.add_vi_to_project(proj, "C:/test/main.vi")
        proj = project.add_vi_to_project(proj, "C:/test/main.vi")
        assert len(proj["files"]) == 1  # No duplicates

    def test_remove_vi_from_project(self):
        """Remove VI from project."""
        proj = project.create_project("Test")
        proj = project.add_vi_to_project(proj, "C:/test/main.vi")
        assert len(proj["files"]) == 1
        proj = project.remove_vi_from_project(proj, "C:/test/main.vi")
        assert len(proj["files"]) == 0

    def test_add_build_spec(self):
        """Add build specification."""
        proj = project.create_project("Test")
        proj = project.add_build_spec(
            proj, "MyApp", build_type="exe",
            source_vi="C:/test/main.vi",
            output_dir="C:/builds",
        )
        assert len(proj["build_specs"]) == 1
        spec = proj["build_specs"][0]
        assert spec["name"] == "MyApp"
        assert spec["type"] == "exe"
        assert spec["source_vi"] == os.path.abspath("C:/test/main.vi")

    def test_save_project(self):
        """Save project to file."""
        proj = project.create_project("SaveTest")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            result = project.save_project(proj, tmp_path)
            assert os.path.exists(tmp_path)
            assert result["path"] == tmp_path
        finally:
            os.unlink(tmp_path)

    def test_list_project_files(self):
        """List project files."""
        proj = project.create_project("Test")
        proj = project.add_vi_to_project(proj, "C:/a.vi", "main")
        proj = project.add_vi_to_project(proj, "C:/b.vi", "subVI")

        files = project.list_project_files(proj)
        assert len(files) == 2

    def test_list_build_specs(self):
        """List build specs."""
        proj = project.create_project("Test")
        proj = project.add_build_spec(proj, "App1", "exe")
        proj = project.add_build_spec(proj, "Lib1", "dll")

        specs = project.list_build_specs(proj)
        assert len(specs) == 2


# ---------------------------------------------------------------------------
# Export tests
# ---------------------------------------------------------------------------

class TestExport:
    """Tests for export.py — build and deployment."""

    def test_build_type_options(self):
        """Build type options returns dict."""
        types = export.build_type_options()
        assert isinstance(types, dict)
        assert "exe" in types
        assert "dll" in types
        assert "installer" in types

    def test_add_build_spec(self):
        """Add build spec to project."""
        proj = project.create_project("Test")
        proj = export.add_build_spec(proj, "MyExe", "exe", "C:/main.vi", "C:/builds")
        assert len(proj["build_specs"]) == 1

    def test_get_build_spec(self):
        """Get specific build spec by name."""
        proj = project.create_project("Test")
        proj = export.add_build_spec(proj, "App1", "exe")
        proj = export.add_build_spec(proj, "App2", "dll")

        spec = export.get_build_spec(proj, "App1")
        assert spec is not None
        assert spec["name"] == "App1"

        assert export.get_build_spec(proj, "Nonexistent") is None

    def test_remove_build_spec(self):
        """Remove build spec."""
        proj = project.create_project("Test")
        proj = export.add_build_spec(proj, "App1", "exe")
        assert len(proj["build_specs"]) == 1

        proj = export.remove_build_spec(proj, "App1")
        assert len(proj["build_specs"]) == 0

    def test_export_build_config(self):
        """Export build config to JSON."""
        proj = project.create_project("Test")
        proj = export.add_build_spec(proj, "App1", "exe")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            result = export.export_build_config(proj, tmp_path)
            assert result["status"] == "exported"
            assert os.path.exists(tmp_path)

            with open(tmp_path, "r") as f:
                data = json.load(f)
            assert data["project"] == "Test"
            assert len(data["build_specs"]) == 1
        finally:
            os.unlink(tmp_path)

    def test_list_empty_build_specs(self):
        """List build specs on empty project."""
        specs = export.list_build_specs({"build_specs": []})
        assert specs == []

    def test_run_build_spec_not_found(self):
        """Run build with nonexistent spec raises error."""
        import sys
        # Skip this test if pywin32 not available (no backend connection possible)
        if sys.platform != "win32":
            pytest.skip("Requires Windows")

        proj = project.create_project("Test")
        from ..utils.labview_backend import LabVIEWBackend
        backend = LabVIEWBackend()

        with pytest.raises(ValueError, match="Build spec not found"):
            export.run_build(backend, proj, "Nonexistent")


# ---------------------------------------------------------------------------
# Session undoes VI tracking
# ---------------------------------------------------------------------------

class TestSessionUndoWithVis:
    """Undo/redo for VI and control operations."""

    def test_undo_vi_open(self):
        """Undoing a VI open restores open_vis list."""
        s = session.Session()
        vi_path = os.path.abspath("C:/test/a.vi")
        s.push_state()
        s.add_open_vi(vi_path)
        assert vi_path in s.open_vis

        s.undo()
        assert vi_path not in s.open_vis

    def test_undo_variable_set(self):
        """Undoing a variable set restores previous value."""
        s = session.Session()
        s.set_var("x", 1)
        assert s.get_var("x") == 1

        s.push_state()
        s.set_var("x", 2)
        assert s.get_var("x") == 2

        s.undo()
        assert s.get_var("x") == 1
