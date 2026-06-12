"""Front panel control operations for cli-anything-labview.

Read and write control/indicator values on LabVIEW VI front panels.
"""

from typing import Any, Optional, Dict, List

from ..utils.labview_backend import LabVIEWBackend


def get_control(
    backend: LabVIEWBackend,
    vi_path: str,
    control_name: str,
    session=None,
) -> Any:
    """Get the value of a front panel control or indicator.

    Args:
        backend: Connected LabVIEW backend.
        vi_path: Path to the VI.
        control_name: Label of the control/indicator.
        session: Optional Session for caching.

    Returns:
        The control's current value.
    """
    value = backend.get_control_value(vi_path, control_name)
    if session:
        session.cache_control_value(vi_path, control_name, value)
    return {"control": control_name, "value": value, "vi_path": vi_path}


def set_control(
    backend: LabVIEWBackend,
    vi_path: str,
    control_name: str,
    value: Any,
    session=None,
) -> Dict[str, Any]:
    """Set the value of a front panel control.

    Args:
        backend: Connected LabVIEW backend.
        vi_path: Path to the VI.
        control_name: Label of the control.
        value: New value.
        session: Optional Session for state tracking.

    Returns:
        Dict with status.
    """
    if session:
        session.push_state()

    result = backend.set_control_value(vi_path, control_name, value)

    if session:
        session.cache_control_value(vi_path, control_name, value)

    return result


def list_controls(
    backend: LabVIEWBackend,
    vi_path: str,
) -> List[Dict[str, Any]]:
    """List all controls and indicators on a VI's front panel.

    Args:
        backend: Connected LabVIEW backend.
        vi_path: Path to the VI.

    Returns:
        List of control dicts with name, value, type.
    """
    return backend.list_controls(vi_path)


def get_all_control_values(
    backend: LabVIEWBackend,
    vi_path: str,
) -> Dict[str, Any]:
    """Get all control/indicator values as a dict.

    Args:
        backend: Connected LabVIEW backend.
        vi_path: Path to the VI.

    Returns:
        Dict mapping control name to value.
    """
    controls = backend.list_controls(vi_path)
    return {c["name"]: c["value"] for c in controls}


def set_multiple_controls(
    backend: LabVIEWBackend,
    vi_path: str,
    values: Dict[str, Any],
    session=None,
) -> Dict[str, Any]:
    """Set multiple control values at once.

    Args:
        backend: Connected LabVIEW backend.
        vi_path: Path to the VI.
        values: Dict of control_name -> value.
        session: Optional Session for state tracking.

    Returns:
        Dict with results per control.
    """
    results = {}
    for name, value in values.items():
        try:
            result = set_control(backend, vi_path, name, value, session)
            results[name] = {"status": "ok", "value": value}
        except Exception as e:
            results[name] = {"status": "error", "message": str(e)}
    return {"vi_path": vi_path, "results": results}
