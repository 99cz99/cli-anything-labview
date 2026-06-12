"""Session management for cli-anything-labview.

Provides stateful session handling with undo/redo support
for LabVIEW operations. Sessions are persisted as JSON files.
"""

import os
import json
import copy
import time
import uuid
from typing import Any, Optional, Dict, List
from datetime import datetime

# fcntl is Unix-only; not available on Windows
try:
    import fcntl
    _has_fcntl = True
except ImportError:
    _has_fcntl = False


class Session:
    """Stateful session for LabVIEW CLI operations.

    Maintains:
    - Project state (VI references, control values)
    - Undo/redo history (deep-copy snapshots, 50 levels)
    - Session metadata (created, modified timestamps)
    """

    MAX_UNDO = 50

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.created_at = datetime.now().isoformat()
        self.modified_at = self.created_at

        # State
        self.project_path: Optional[str] = None
        self.project_name: Optional[str] = None
        self.open_vis: List[str] = []   # List of open VI paths
        self.control_values: Dict[str, Dict[str, Any]] = {}  # vi_path -> {control: value}
        self.running_vis: List[str] = []  # VIs currently executing
        self.variables: Dict[str, Any] = {}  # User-defined session variables

        # Undo/redo
        self._undo_stack: List[Dict[str, Any]] = []
        self._redo_stack: List[Dict[str, Any]] = []
        self._dirty = False

    # ------------------------------------------------------------------
    # State snapshot (for undo/redo)
    # ------------------------------------------------------------------

    def _snapshot(self) -> Dict[str, Any]:
        """Create a deep-copy snapshot of current state."""
        return {
            "project_path": self.project_path,
            "project_name": self.project_name,
            "open_vis": list(self.open_vis),
            "control_values": copy.deepcopy(self.control_values),
            "running_vis": list(self.running_vis),
            "variables": copy.deepcopy(self.variables),
            "modified_at": self.modified_at,
        }

    def _restore(self, snapshot: Dict[str, Any]):
        """Restore state from a snapshot."""
        self.project_path = snapshot["project_path"]
        self.project_name = snapshot["project_name"]
        self.open_vis = list(snapshot["open_vis"])
        self.control_values = copy.deepcopy(snapshot["control_values"])
        self.running_vis = list(snapshot["running_vis"])
        self.variables = copy.deepcopy(snapshot["variables"])
        self.modified_at = snapshot["modified_at"]

    # ------------------------------------------------------------------
    # Undo/redo
    # ------------------------------------------------------------------

    def push_state(self):
        """Push current state onto undo stack before a mutation."""
        snapshot = self._snapshot()
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self.MAX_UNDO:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._dirty = True
        self.modified_at = datetime.now().isoformat()

    def undo(self) -> bool:
        """Undo the last operation. Returns True if successful."""
        if not self._undo_stack:
            return False
        current = self._snapshot()
        self._redo_stack.append(current)
        previous = self._undo_stack.pop()
        self._restore(previous)
        self.modified_at = datetime.now().isoformat()
        return True

    def redo(self) -> bool:
        """Redo the last undone operation. Returns True if successful."""
        if not self._redo_stack:
            return False
        current = self._snapshot()
        self._undo_stack.append(current)
        next_state = self._redo_stack.pop()
        self._restore(next_state)
        self.modified_at = datetime.now().isoformat()
        return True

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    @property
    def undo_depth(self) -> int:
        return len(self._undo_stack)

    @property
    def redo_depth(self) -> int:
        return len(self._redo_stack)

    # ------------------------------------------------------------------
    # VI tracking
    # ------------------------------------------------------------------

    def add_open_vi(self, vi_path: str):
        """Track an opened VI."""
        abs_path = os.path.abspath(vi_path)
        if abs_path not in self.open_vis:
            self.push_state()
            self.open_vis.append(abs_path)

    def remove_open_vi(self, vi_path: str):
        """Stop tracking a VI."""
        abs_path = os.path.abspath(vi_path)
        if abs_path in self.open_vis:
            self.push_state()
            self.open_vis.remove(abs_path)
            self.control_values.pop(abs_path, None)

    def add_running_vi(self, vi_path: str):
        """Track a running VI."""
        abs_path = os.path.abspath(vi_path)
        if abs_path not in self.running_vis:
            self.running_vis.append(abs_path)

    def remove_running_vi(self, vi_path: str):
        """Stop tracking a running VI."""
        abs_path = os.path.abspath(vi_path)
        if abs_path in self.running_vis:
            self.running_vis.remove(abs_path)

    # ------------------------------------------------------------------
    # Control value cache
    # ------------------------------------------------------------------

    def cache_control_value(self, vi_path: str, control_name: str, value: Any):
        """Cache a control value in the session."""
        abs_path = os.path.abspath(vi_path)
        if abs_path not in self.control_values:
            self.control_values[abs_path] = {}
        self.control_values[abs_path][control_name] = value

    def get_cached_value(self, vi_path: str, control_name: str) -> Optional[Any]:
        """Get a cached control value."""
        abs_path = os.path.abspath(vi_path)
        return self.control_values.get(abs_path, {}).get(control_name)

    # ------------------------------------------------------------------
    # Variable store
    # ------------------------------------------------------------------

    def set_var(self, name: str, value: Any):
        """Set a session variable."""
        self.push_state()
        self.variables[name] = value

    def get_var(self, name: str) -> Optional[Any]:
        """Get a session variable."""
        return self.variables.get(name)

    def list_vars(self) -> Dict[str, Any]:
        """List all session variables."""
        return dict(self.variables)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session to dict."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "project_path": self.project_path,
            "project_name": self.project_name,
            "open_vis": self.open_vis,
            "control_values": self.control_values,
            "running_vis": self.running_vis,
            "variables": self.variables,
            "undo_depth": len(self._undo_stack),
            "redo_depth": len(self._redo_stack),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Deserialize session from dict."""
        session = cls(session_id=data.get("session_id"))
        session.created_at = data.get("created_at", session.created_at)
        session.modified_at = data.get("modified_at", session.modified_at)
        session.project_path = data.get("project_path")
        session.project_name = data.get("project_name")
        session.open_vis = data.get("open_vis", [])
        session.control_values = data.get("control_values", {})
        session.running_vis = data.get("running_vis", [])
        session.variables = data.get("variables", {})
        return session

    def save(self, filepath: str):
        """Save session to a JSON file with file locking."""
        data = self.to_dict()
        self._locked_save_json(filepath, data)
        self._dirty = False

    @staticmethod
    def _locked_save_json(filepath: str, data: Dict[str, Any]):
        """Save JSON atomically: write to temp file then rename.

        On Unix, uses fcntl advisory lock for concurrent-write safety.
        On Windows, atomic rename provides sufficient safety.
        """
        tmp_path = filepath + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            if _has_fcntl:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    json.dump(data, f, indent=2, default=str, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                except (AttributeError, OSError):
                    json.dump(data, f, indent=2, default=str, ensure_ascii=False)
                    f.flush()
            else:
                # Windows: atomic rename provides safety; just write and sync
                json.dump(data, f, indent=2, default=str, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
        os.replace(tmp_path, filepath)

    @classmethod
    def load(cls, filepath: str) -> "Session":
        """Load session from a JSON file."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Session file not found: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def mark_clean(self):
        """Mark session as clean (saved)."""
        self._dirty = False
