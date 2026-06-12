"""VI operations for cli-anything-labview.

Handles VI creation, opening, closing, listing, and info queries.
"""

import os
import glob
from typing import Any, Optional, Dict, List
from datetime import datetime

from ..utils.labview_backend import LabVIEWBackend


def open_vi(
    backend: LabVIEWBackend,
    vi_path: str,
    session=None,
) -> Dict[str, Any]:
    """Open a VI and return its info.

    Args:
        backend: Connected LabVIEW backend.
        vi_path: Path to .vi file.
        session: Optional Session for state tracking.

    Returns:
        Dict with vi_path, name, status.
    """
    abs_path = os.path.abspath(vi_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"VI not found: {abs_path}")

    vi_ref = backend.open_vi(abs_path)
    if session:
        session.add_open_vi(abs_path)

    return {
        "vi_path": abs_path,
        "name": os.path.splitext(os.path.basename(abs_path))[0],
        "status": "opened",
        "file_size": os.path.getsize(abs_path),
    }


def close_vi(
    backend: LabVIEWBackend,
    vi_path: str,
    session=None,
) -> Dict[str, Any]:
    """Close a VI.

    Args:
        backend: Connected LabVIEW backend.
        vi_path: Path to .vi file.
        session: Optional Session for state tracking.

    Returns:
        Dict with status.
    """
    abs_path = os.path.abspath(vi_path)
    backend.close_vi(abs_path)
    if session:
        session.remove_open_vi(abs_path)

    return {"vi_path": abs_path, "status": "closed"}


def create_vi(
    backend: LabVIEWBackend,
    save_path: Optional[str] = None,
    session=None,
) -> Dict[str, Any]:
    """Create a new blank VI.

    Args:
        backend: Connected LabVIEW backend.
        save_path: Optional path to save the new VI.
        session: Optional Session for state tracking.

    Returns:
        Dict with status and vi_path.
    """
    result = backend.create_vi(save_path)
    if session and result.get("vi_path"):
        session.add_open_vi(result["vi_path"])
    return result


def save_vi(
    backend: LabVIEWBackend,
    vi_path: str,
    new_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Save a VI, optionally to a new path.

    Args:
        backend: Connected LabVIEW backend.
        vi_path: Path of the VI to save.
        new_path: Optional new save path.

    Returns:
        Dict with save status.
    """
    result = backend.save_vi(vi_path, new_path)
    return result


def get_vi_info(
    backend: LabVIEWBackend,
    vi_path: str,
) -> Dict[str, Any]:
    """Get detailed information about a VI.

    Args:
        backend: Connected LabVIEW backend.
        vi_path: Path to .vi file.

    Returns:
        Dict with vi info: path, name, size, modified, execution_state, etc.
    """
    abs_path = os.path.abspath(vi_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"VI not found: {abs_path}")

    stat = os.stat(abs_path)
    info = {
        "path": abs_path,
        "name": os.path.splitext(os.path.basename(abs_path))[0],
        "directory": os.path.dirname(abs_path),
        "file_size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
    }

    # Try to get execution state via backend
    try:
        status = backend.get_vi_status(abs_path)
        info["execution_state"] = status.get("execution_state", "unknown")
        info["is_open"] = status.get("is_open", False)
    except Exception:
        info["execution_state"] = "unknown"
        info["is_open"] = False

    return info


def list_open_vis(backend: LabVIEWBackend) -> List[str]:
    """List paths of all currently open VIs."""
    return backend.list_open_vis()


def find_vis(
    directory: str,
    pattern: str = "*.vi",
    recursive: bool = True,
) -> List[Dict[str, Any]]:
    """Find VI files in a directory.

    Args:
        directory: Directory to search.
        pattern: File pattern (default: *.vi).
        recursive: Search subdirectories.

    Returns:
        List of dicts with path, name, size.
    """
    abs_dir = os.path.abspath(directory)
    if not os.path.isdir(abs_dir):
        raise NotADirectoryError(f"Not a directory: {abs_dir}")

    glob_pattern = os.path.join(abs_dir, "**" if recursive else "", pattern)
    results = []
    for filepath in glob.glob(glob_pattern, recursive=recursive):
        stat = os.stat(filepath)
        results.append({
            "path": filepath,
            "name": os.path.splitext(os.path.basename(filepath))[0],
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })

    return sorted(results, key=lambda x: x["name"])


def list_vi_hierarchy(vi_path: str) -> Dict[str, Any]:
    """List subVIs and dependencies of a VI.

    Note: This requires parsing the VI binary format or using VI Server
    to enumerate subVIs. For now, returns a placeholder structure.

    Args:
        vi_path: Path to the VI to analyze.

    Returns:
        Dict with vi_path, subvis, callers.
    """
    abs_path = os.path.abspath(vi_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"VI not found: {abs_path}")

    # VI files are binary; full dependency analysis requires VI Server.
    # This function provides the structure for future implementation.
    return {
        "vi_path": abs_path,
        "name": os.path.splitext(os.path.basename(abs_path))[0],
        "subvis": [],    # Would be populated via VI Server: VI.Callees[]
        "callers": [],   # Would be populated via VI Server: VI.Callers[]
        "note": "Full hierarchy requires COM/ActiveX VI Server connection.",
    }
