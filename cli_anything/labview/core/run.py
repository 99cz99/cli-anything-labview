"""VI execution control for cli-anything-labview.

Run, stop, and monitor LabVIEW VIs via the backend.
"""

from typing import Any, Optional, Dict, List

from ..utils.labview_backend import LabVIEWBackend


def run_vi(
    backend: LabVIEWBackend,
    vi_path: str,
    wait: bool = False,
    session=None,
) -> Dict[str, Any]:
    """Run a VI.

    Args:
        backend: Connected LabVIEW backend.
        vi_path: Path to the VI.
        wait: If True, block until VI completes execution.
        session: Optional Session for state tracking.

    Returns:
        Dict with run status.
    """
    result = backend.run_vi(vi_path, wait=wait)
    if session:
        session.add_running_vi(vi_path)
    return result


def stop_vi(
    backend: LabVIEWBackend,
    vi_path: str,
    session=None,
) -> Dict[str, Any]:
    """Abort a running VI.

    Args:
        backend: Connected LabVIEW backend.
        vi_path: Path to the VI to stop.
        session: Optional Session for state tracking.

    Returns:
        Dict with stop status.
    """
    result = backend.stop_vi(vi_path)
    if session:
        session.remove_running_vi(vi_path)
    return result


def get_status(
    backend: LabVIEWBackend,
    vi_path: str,
) -> Dict[str, Any]:
    """Get the execution status of a VI.

    Args:
        backend: Connected LabVIEW backend.
        vi_path: Path to the VI.

    Returns:
        Dict with execution_state, is_open, vi_path.
    """
    return backend.get_vi_status(vi_path)


def run_with_args(
    backend: LabVIEWBackend,
    vi_path: str,
    args: List[str],
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    """Run a VI via LabVIEW.exe command line with arguments.

    This launches LabVIEW as a separate process with the VI and args.
    The VI receives args via the 'Command Line Arguments' property.

    Args:
        backend: Connected LabVIEW backend.
        vi_path: Path to the VI.
        args: Command-line arguments to pass to the VI.
        timeout: Optional timeout in seconds.

    Returns:
        Dict with stdout, stderr, returncode.
    """
    return backend.run_vi_cli(vi_path, args, timeout)


def run_and_read(
    backend: LabVIEWBackend,
    vi_path: str,
    inputs: Dict[str, Any],
    outputs: List[str],
    timeout: Optional[float] = None,
    session=None,
) -> Dict[str, Any]:
    """Run a VI with inputs and read outputs.

    This is a convenience wrapper that:
    1. Sets all input control values
    2. Runs the VI (wait=True)
    3. Reads all output indicator values

    Args:
        backend: Connected LabVIEW backend.
        vi_path: Path to the VI.
        inputs: Dict of control_name -> value to set before running.
        outputs: List of indicator names to read after running.
        timeout: Optional timeout (not used in COM mode, VI must complete).
        session: Optional Session for state tracking.

    Returns:
        Dict with inputs, outputs, status.
    """
    if session:
        session.push_state()

    # Set inputs
    for name, value in inputs.items():
        backend.set_control_value(vi_path, name, value)

    # Run and wait
    backend.run_vi(vi_path, wait=True)

    # Read outputs
    output_values = {}
    for name in outputs:
        output_values[name] = backend.get_control_value(vi_path, name)

    if session:
        for name, value in inputs.items():
            session.cache_control_value(vi_path, name, value)
        for name, value in output_values.items():
            session.cache_control_value(vi_path, name, value)

    return {
        "vi_path": vi_path,
        "status": "completed",
        "inputs": inputs,
        "outputs": output_values,
    }


def run_cli_mode(
    backend: LabVIEWBackend,
    vi_path: str,
    args: Optional[List[str]] = None,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    """Run a VI via LabVIEW.exe process launch.

    This is the CLI mode — LabVIEW starts, runs the VI, and exits.
    Useful for batch processing and scripted execution.

    Args:
        backend: Connected LabVIEW backend.
        vi_path: Path to the VI.
        args: Command-line arguments.
        timeout: Timeout in seconds.

    Returns:
        Dict with status, stdout, stderr, returncode.
    """
    return backend.run_vi_cli(vi_path, args, timeout)


def is_labview_running(backend: LabVIEWBackend) -> bool:
    """Check if LabVIEW process is currently running.

    Returns:
        True if LabVIEW.exe is found in process list.
    """
    return backend.is_labview_running()
