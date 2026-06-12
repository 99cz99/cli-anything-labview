"""LabVIEW backend: COM/ActiveX automation wrapper.

Handles all communication with LabVIEW via:
1. ActiveX/COM (pywin32) — primary, local control
2. Command line invocation — secondary, process launch
3. VI Server TCP — future, remote control

Known ActiveX quirks:
- Methods like Run(), OpenFrontPanel(), Abort() are not properly flagged
  in LabVIEW's type library — must use _FlagAsMethod() before calling.
"""

import os
import sys
import time
import json
import subprocess
from typing import Any, Optional, Dict, List, Tuple

# ---------------------------------------------------------------------------
# COM backend (Windows-only)
# ---------------------------------------------------------------------------

_COM_AVAILABLE = False
_com_dispatch = None

if sys.platform == "win32":
    try:
        import win32com.client
        import pythoncom
        _COM_AVAILABLE = True
        _com_dispatch = win32com.client.Dispatch
    except ImportError:
        pass


class LabVIEWBackend:
    """Unified backend for controlling LabVIEW."""

    def __init__(self, labview_path: Optional[str] = None):
        """Initialize the backend.

        Args:
            labview_path: Optional path to LabVIEW.exe. If not provided,
                          will search standard locations.
        """
        self._labview_path = labview_path or self._find_labview()
        self._app = None  # COM Application object
        self._open_vis: Dict[str, Any] = {}  # path -> VI reference

    # ------------------------------------------------------------------
    # LabVIEW discovery
    # ------------------------------------------------------------------

    @staticmethod
    def _find_labview() -> Optional[str]:
        """Find LabVIEW.exe in standard locations."""
        candidates = [
            r"E:\labview\LabVIEW 2025\LabVIEW.exe",
            r"C:\Program Files\National Instruments\LabVIEW 2025\LabVIEW.exe",
            r"C:\Program Files (x86)\National Instruments\LabVIEW 2025\LabVIEW.exe",
        ]
        # Also check environment
        env_path = os.environ.get("LABVIEW_PATH")
        if env_path:
            candidates.insert(0, env_path)

        for path in candidates:
            if os.path.isfile(path):
                return path
        return None

    @property
    def labview_path(self) -> Optional[str]:
        return self._labview_path

    @property
    def labview_dir(self) -> Optional[str]:
        if self._labview_path:
            return os.path.dirname(self._labview_path)
        return None

    @property
    def com_available(self) -> bool:
        return _COM_AVAILABLE

    # ------------------------------------------------------------------
    # COM connection management
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Connect to LabVIEW via ActiveX COM.

        Returns True if connected successfully.
        """
        if not _COM_AVAILABLE:
            raise RuntimeError(
                "pywin32 is not installed. Install with: pip install pywin32"
            )
        try:
            import pythoncom
            pythoncom.CoInitialize()
            self._app = _com_dispatch("LabVIEW.Application")
            return True
        except Exception as e:
            raise RuntimeError(
                f"Failed to connect to LabVIEW via COM: {e}\n"
                "Ensure LabVIEW is installed and ActiveX server is enabled:\n"
                "  Tools → Options → VI Server → ActiveX → Enable ActiveX Server"
            )

    def disconnect(self):
        """Disconnect from LabVIEW COM."""
        for vi in self._open_vis.values():
            try:
                vi.Close()
            except Exception:
                pass
        self._open_vis.clear()
        self._app = None

    @property
    def connected(self) -> bool:
        return self._app is not None

    def _ensure_connected(self):
        """Ensure COM connection is active."""
        if not self.connected:
            self.connect()

    # ------------------------------------------------------------------
    # VI reference management
    # ------------------------------------------------------------------

    @staticmethod
    def _flag_vi_methods(vi):
        """Flag LabVIEW ActiveX methods that are not properly exposed
        in the type library as callable methods.

        Without this, calling vi.Run() or vi.OpenFrontPanel()
        returns TypeError: 'NoneType' object is not callable.

        Reference: https://knowledge.ni.com/KnowledgeArticleDetails?id=kA0VU0000008tNV0AY
        """
        methods_to_flag = [
            "Run",
            "Abort",
            "OpenFrontPanel",
            "CloseFrontPanel",
            "Save",
            "Close",
            "Print",
            "MakeCurrentValuesDefault",
            "ReinitializeAllToDefault",
            "ReinitializeValuesToDefault",
            "RemotePanelOpen",
            "RemotePanelClose",
        ]
        for method_name in methods_to_flag:
            try:
                vi._FlagAsMethod(method_name)
            except Exception:
                pass  # Method may not exist on this object

    def open_vi(self, vi_path: str) -> Any:
        """Open a VI and return its reference.

        Args:
            vi_path: Absolute path to the .vi file.

        Returns:
            COM reference to the opened VI.
        """
        self._ensure_connected()
        abs_path = os.path.abspath(vi_path)
        if abs_path in self._open_vis:
            return self._open_vis[abs_path]

        try:
            vi = self._app.GetVIReference(abs_path)
            self._flag_vi_methods(vi)
            self._open_vis[abs_path] = vi
            return vi
        except Exception as e:
            raise RuntimeError(
                f"Failed to open VI: {abs_path}\nError: {e}"
            )

    def get_vi(self, vi_path: str) -> Optional[Any]:
        """Get an already-opened VI reference."""
        abs_path = os.path.abspath(vi_path)
        return self._open_vis.get(abs_path)

    def close_vi(self, vi_path: str):
        """Close a specific VI."""
        abs_path = os.path.abspath(vi_path)
        vi = self._open_vis.pop(abs_path, None)
        if vi:
            try:
                vi.Close()
            except Exception:
                pass

    def list_open_vis(self) -> List[str]:
        """List paths of all open VIs."""
        return list(self._open_vis.keys())

    # ------------------------------------------------------------------
    # VI operations
    # ------------------------------------------------------------------

    def run_vi(self, vi_path: str, wait: bool = False) -> Dict[str, Any]:
        """Run a VI.

        Args:
            vi_path: Path to the VI.
            wait: If True, block until VI completes.

        Returns:
            Dict with status information.
        """
        self._ensure_connected()
        vi = self.open_vi(vi_path)
        try:
            vi.Run(int(wait))
            return {
                "status": "running" if not wait else "completed",
                "vi_path": vi_path,
                "wait": wait,
            }
        except Exception as e:
            raise RuntimeError(f"Failed to run VI '{vi_path}': {e}")

    def stop_vi(self, vi_path: str) -> Dict[str, Any]:
        """Abort a running VI.

        Args:
            vi_path: Path to the VI to abort.
        """
        vi = self.get_vi(vi_path)
        if not vi:
            # Try to open and abort
            vi = self.open_vi(vi_path)
        try:
            vi.Abort()
            return {"status": "stopped", "vi_path": vi_path}
        except Exception as e:
            raise RuntimeError(f"Failed to stop VI '{vi_path}': {e}")

    def get_vi_status(self, vi_path: str) -> Dict[str, Any]:
        """Get execution status of a VI.

        Returns dict with: vi_path, execution_state, reserved_by_cli
        Execution states: 'idle', 'running', 'bad'
        """
        vi = self.get_vi(vi_path)
        if not vi:
            # Try to open
            vi = self.open_vi(vi_path)
        try:
            state = vi.GetExecState()
            state_names = {0: "idle", 1: "running", 2: "bad"}
            return {
                "vi_path": vi_path,
                "execution_state": state_names.get(state, f"unknown({state})"),
                "is_open": vi_path in self._open_vis,
            }
        except Exception as e:
            return {
                "vi_path": vi_path,
                "error": str(e),
                "is_open": vi_path in self._open_vis,
            }

    # ------------------------------------------------------------------
    # Control value operations
    # ------------------------------------------------------------------

    def get_control_value(self, vi_path: str, control_name: str) -> Any:
        """Get the value of a front panel control or indicator.

        Args:
            vi_path: Path to the VI.
            control_name: Label of the control/indicator.

        Returns:
            The current value (type depends on control type).
        """
        self._ensure_connected()
        vi = self.open_vi(vi_path)
        try:
            value = vi.GetControlValue(control_name)
            return value
        except Exception as e:
            raise RuntimeError(
                f"Failed to get control '{control_name}' on VI '{vi_path}': {e}"
            )

    def set_control_value(self, vi_path: str, control_name: str, value: Any) -> Dict[str, Any]:
        """Set the value of a front panel control.

        Args:
            vi_path: Path to the VI.
            control_name: Label of the control.
            value: New value to set.

        Returns:
            Dict with status.
        """
        self._ensure_connected()
        vi = self.open_vi(vi_path)
        try:
            vi.SetControlValue(control_name, value)
            return {
                "status": "ok",
                "vi_path": vi_path,
                "control": control_name,
                "value": value,
            }
        except Exception as e:
            raise RuntimeError(
                f"Failed to set control '{control_name}' on VI '{vi_path}': {e}"
            )

    def list_controls(self, vi_path: str) -> List[Dict[str, Any]]:
        """List all controls and indicators on a VI's front panel.

        Returns:
            List of dicts with name, label, type, is_indicator.
        """
        self._ensure_connected()
        vi = self.open_vi(vi_path)
        try:
            controls = []
            # Enumerate controls on the front panel
            control_count = 0
            try:
                control_count = vi.GetNumControlIndicators()
            except Exception:
                pass

            for i in range(control_count):
                try:
                    name = vi.GetControlIndicatorName(i)
                    value = vi.GetControlValue(name)
                    controls.append({
                        "index": i,
                        "name": name,
                        "value": value,
                        "type": type(value).__name__,
                    })
                except Exception:
                    pass
            return controls
        except Exception as e:
            raise RuntimeError(
                f"Failed to list controls on VI '{vi_path}': {e}"
            )

    # ------------------------------------------------------------------
    # VI front panel
    # ------------------------------------------------------------------

    def open_front_panel(self, vi_path: str) -> Dict[str, Any]:
        """Open the front panel window of a VI."""
        self._ensure_connected()
        vi = self.open_vi(vi_path)
        try:
            vi.OpenFrontPanel()
            return {"status": "ok", "action": "front_panel_opened", "vi_path": vi_path}
        except Exception as e:
            raise RuntimeError(f"Failed to open front panel for '{vi_path}': {e}")

    def close_front_panel(self, vi_path: str) -> Dict[str, Any]:
        """Close the front panel window of a VI."""
        vi = self.get_vi(vi_path)
        if not vi:
            return {"status": "not_open", "vi_path": vi_path}
        try:
            vi.CloseFrontPanel()
            return {"status": "ok", "action": "front_panel_closed", "vi_path": vi_path}
        except Exception as e:
            raise RuntimeError(f"Failed to close front panel for '{vi_path}': {e}")

    # ------------------------------------------------------------------
    # VI save and file operations
    # ------------------------------------------------------------------

    def save_vi(self, vi_path: str, new_path: Optional[str] = None) -> Dict[str, Any]:
        """Save a VI, optionally to a new path."""
        self._ensure_connected()
        vi = self.open_vi(vi_path)
        try:
            if new_path:
                vi.SaveAs(new_path)
                return {"status": "saved", "vi_path": vi_path, "saved_as": new_path}
            else:
                vi.Save()
                return {"status": "saved", "vi_path": vi_path}
        except Exception as e:
            raise RuntimeError(f"Failed to save VI '{vi_path}': {e}")

    def create_vi(self, save_path: Optional[str] = None) -> Dict[str, Any]:
        """Create a new blank VI.

        Args:
            save_path: Optional path to save the new VI.

        Returns:
            Dict with vi_path and status.
        """
        self._ensure_connected()
        try:
            vi = self._app.NewVI()
            self._flag_vi_methods(vi)
            vi_path = save_path or "Untitled.vi"
            if save_path:
                vi.SaveAs(os.path.abspath(save_path))
                self._open_vis[os.path.abspath(save_path)] = vi
            else:
                self._open_vis[vi_path] = vi
            return {"status": "created", "vi_path": vi_path}
        except Exception as e:
            raise RuntimeError(f"Failed to create new VI: {e}")

    # ------------------------------------------------------------------
    # Command-line fallback
    # ------------------------------------------------------------------

    def run_vi_cli(
        self,
        vi_path: str,
        args: Optional[List[str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run a VI by launching LabVIEW.exe with arguments.

        This bypasses COM and launches LabVIEW as a subprocess.

        Args:
            vi_path: Path to the .vi file.
            args: Command-line arguments to pass to the VI.
            timeout: Optional timeout in seconds.

        Returns:
            Dict with stdout, stderr, returncode, pid.
        """
        if not self._labview_path:
            raise RuntimeError(
                "LabVIEW.exe not found. Set LABVIEW_PATH environment variable."
            )

        if not os.path.isfile(vi_path):
            raise FileNotFoundError(f"VI not found: {vi_path}")

        cmd = [self._labview_path, vi_path]
        if args:
            cmd.append("--")
            cmd.extend(args)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "status": "launched",
                "vi_path": vi_path,
                "args": args or [],
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "vi_path": vi_path,
                "timeout": timeout,
            }
        except Exception as e:
            raise RuntimeError(f"Failed to launch LabVIEW for '{vi_path}': {e}")

    def is_labview_running(self) -> bool:
        """Check if LabVIEW process is running."""
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq LabVIEW.exe"],
                capture_output=True, text=True,
            )
            return "LabVIEW.exe" in result.stdout
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False


# ---------------------------------------------------------------------------
# Utility: find and test LabVIEW installation
# ---------------------------------------------------------------------------

def check_labview_installation() -> Dict[str, Any]:
    """Check LabVIEW installation status.

    Returns dict with keys:
        installed, labview_path, com_available, labview_running, version_info
    """
    backend = LabVIEWBackend()
    info = {
        "installed": backend.labview_path is not None,
        "labview_path": backend.labview_path,
        "labview_dir": backend.labview_dir,
        "com_available": backend.com_available,
        "labview_running": backend.is_labview_running(),
    }

    # Try to get version from the executable
    if backend.labview_path:
        try:
            import win32api
            info_dict = win32api.GetFileVersionInfo(
                backend.labview_path, "\\"
            )
            ms = info_dict.get("FileVersionMS", 0)
            ls = info_dict.get("FileVersionLS", 0)
            version = f"{(ms >> 16) & 0xFFFF}.{(ms >> 0) & 0xFFFF}.{(ls >> 16) & 0xFFFF}.{(ls >> 0) & 0xFFFF}"
            info["version"] = version
        except Exception:
            info["version"] = "unknown"

    return info
