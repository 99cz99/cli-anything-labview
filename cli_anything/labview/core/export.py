"""Build and deployment operations for cli-anything-labview.

Handles LabVIEW build specifications, executable generation,
and deployment operations.
"""

import os
import json
from typing import Any, Optional, Dict, List
from datetime import datetime

from ..utils.labview_backend import LabVIEWBackend


def list_build_specs(
    project: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """List build specifications in a project.

    Args:
        project: Project dict from core.project.

    Returns:
        List of build spec dicts.
    """
    return project.get("build_specs", [])


def get_build_spec(
    project: Dict[str, Any],
    spec_name: str,
) -> Optional[Dict[str, Any]]:
    """Get a specific build specification by name.

    Args:
        project: Project dict.
        spec_name: Name of the build spec.

    Returns:
        Build spec dict or None if not found.
    """
    for spec in project.get("build_specs", []):
        if spec["name"] == spec_name:
            return spec
    return None


def add_build_spec(
    project: Dict[str, Any],
    name: str,
    build_type: str = "exe",
    source_vi: Optional[str] = None,
    output_dir: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Add a build specification.

    Args:
        project: Project dict.
        name: Build spec name.
        build_type: 'exe', 'dll', 'installer', 'zip', 'source_distribution'.
        source_vi: Main VI for the build.
        output_dir: Build output directory.
        **kwargs: Additional build options (icon, version, etc.).

    Returns:
        Updated project dict.
    """
    from .project import add_build_spec as _add
    return _add(project, name, build_type, source_vi, output_dir)


def remove_build_spec(
    project: Dict[str, Any],
    spec_name: str,
) -> Dict[str, Any]:
    """Remove a build specification.

    Args:
        project: Project dict.
        spec_name: Name of the spec to remove.

    Returns:
        Updated project dict.
    """
    project["build_specs"] = [
        s for s in project.get("build_specs", []) if s["name"] != spec_name
    ]
    return project


def run_build(
    backend: LabVIEWBackend,
    project: Dict[str, Any],
    spec_name: str,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a build specification.

    Note: Full build execution requires LabVIEWCLI.exe or VI Server.
    This function provides the structure and attempts COM automation.

    Args:
        backend: Connected LabVIEW backend.
        project: Project dict.
        spec_name: Name of the build spec to execute.
        output_dir: Override output directory.

    Returns:
        Dict with build results.
    """
    spec = get_build_spec(project, spec_name)
    if not spec:
        raise ValueError(f"Build spec not found: {spec_name}")

    build_dir = output_dir or spec.get("output_dir") or os.path.join(
        os.path.dirname(project.get("path", ".")), "builds", spec_name
    )
    os.makedirs(build_dir, exist_ok=True)

    # Build info
    result = {
        "build_spec": spec_name,
        "build_type": spec.get("type", "exe"),
        "output_dir": build_dir,
        "started": datetime.now().isoformat(),
        "status": "initiated",
        "note": "Full build requires LabVIEWCLI. Use LabVIEW IDE or LabVIEWCLI for complete build execution.",
    }

    # If source VI specified, verify it exists
    if spec.get("source_vi"):
        if os.path.exists(spec["source_vi"]):
            result["source_vi_verified"] = True
        else:
            result["source_vi_verified"] = False
            result["warning"] = f"Source VI not found: {spec['source_vi']}"

    return result


def export_build_config(
    project: Dict[str, Any],
    output_path: str,
) -> Dict[str, Any]:
    """Export build specifications as a standalone JSON config.

    This can be used by CI/CD pipelines for automated builds.

    Args:
        project: Project dict.
        output_path: Output JSON file path.

    Returns:
        Dict with export status.
    """
    config = {
        "project": project.get("name"),
        "project_path": project.get("path"),
        "build_specs": project.get("build_specs", []),
        "exported_at": datetime.now().isoformat(),
    }

    abs_path = os.path.abspath(output_path)
    with open(abs_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, default=str, ensure_ascii=False)

    return {
        "status": "exported",
        "output_path": abs_path,
        "spec_count": len(config["build_specs"]),
    }


def build_type_options() -> Dict[str, str]:
    """Get available build types and their descriptions."""
    return {
        "exe": "Standalone executable application",
        "dll": "Shared library (DLL)",
        "installer": "Windows installer package",
        "zip": "ZIP file distribution",
        "source_distribution": "Source code distribution",
        "packed_library": "Packed project library",
        "web_service": "Web service deployment",
    }
