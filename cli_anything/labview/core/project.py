"""Project management for cli-anything-labview.

Handles LabVIEW project (.lvproj) creation and manipulation.
LabVIEW project files are XML-based and contain build specifications,
VI references, and deployment targets.
"""

import os
import json
import uuid
from typing import Any, Optional, Dict, List
from datetime import datetime


def create_project(
    name: str,
    output_path: Optional[str] = None,
    target: str = "My Computer",
) -> Dict[str, Any]:
    """Create a new LabVIEW project definition.

    Args:
        name: Project name.
        output_path: Optional .lvproj file path to save.
        target: Target hardware label (default: "My Computer").

    Returns:
        Project metadata dict.
    """
    project = {
        "name": name,
        "type": "lvproj",
        "version": "2025",
        "created": datetime.now().isoformat(),
        "target": target,
        "files": [],       # VI file references
        "build_specs": [], # Build specifications
        "dependencies": [], # VI dependencies
        "variables": {},    # Project-level variables
    }

    if output_path:
        abs_path = os.path.abspath(output_path)
        _save_project_json(project, abs_path)
        project["path"] = abs_path

    return project


def open_project(project_path: str) -> Dict[str, Any]:
    """Open a LabVIEW project from a JSON definition file.

    Args:
        project_path: Path to .lvproj.json or .lvproj file.

    Returns:
        Project metadata dict.
    """
    abs_path = os.path.abspath(project_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Project file not found: {abs_path}")

    if abs_path.endswith(".json"):
        with open(abs_path, "r", encoding="utf-8") as f:
            project = json.load(f)
    elif abs_path.endswith(".lvproj"):
        # Parse real LabVIEW project XML
        project = _parse_lvproj_xml(abs_path)
    else:
        raise ValueError(f"Unsupported project file format: {abs_path}")

    project["path"] = abs_path
    return project


def save_project(project: Dict[str, Any], output_path: Optional[str] = None) -> Dict[str, Any]:
    """Save project definition to JSON.

    Args:
        project: Project dict.
        output_path: Output path (uses project['path'] if not specified).

    Returns:
        Updated project dict with path.
    """
    save_path = output_path or project.get("path")
    if not save_path:
        raise ValueError("No output path specified for project save.")

    abs_path = os.path.abspath(save_path)
    _save_project_json(project, abs_path)
    project["path"] = abs_path
    project["modified"] = datetime.now().isoformat()
    return project


def get_project_info(project: Dict[str, Any]) -> Dict[str, Any]:
    """Get summary information about a project.

    Returns dict with: name, path, file_count, build_spec_count, target.
    """
    return {
        "name": project.get("name", "Untitled"),
        "path": project.get("path", ""),
        "target": project.get("target", "My Computer"),
        "version": project.get("version", "unknown"),
        "file_count": len(project.get("files", [])),
        "build_spec_count": len(project.get("build_specs", [])),
        "dependency_count": len(project.get("dependencies", [])),
        "created": project.get("created"),
        "modified": project.get("modified"),
    }


def add_vi_to_project(project: Dict[str, Any], vi_path: str, category: str = "main") -> Dict[str, Any]:
    """Add a VI reference to the project.

    Args:
        project: Project dict.
        vi_path: Path to the VI file.
        category: Category label (e.g., "main", "subVI", "library").

    Returns:
        Updated project dict.
    """
    abs_path = os.path.abspath(vi_path)
    vi_entry = {
        "id": str(uuid.uuid4())[:8],
        "path": abs_path,
        "name": os.path.splitext(os.path.basename(abs_path))[0],
        "category": category,
        "added": datetime.now().isoformat(),
    }
    # Avoid duplicates
    existing = [f for f in project.get("files", []) if f["path"] == abs_path]
    if not existing:
        project.setdefault("files", []).append(vi_entry)
    return project


def remove_vi_from_project(project: Dict[str, Any], vi_path: str) -> Dict[str, Any]:
    """Remove a VI reference from the project."""
    abs_path = os.path.abspath(vi_path)
    project["files"] = [f for f in project.get("files", []) if f["path"] != abs_path]
    return project


def list_project_files(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List all VIs in the project."""
    return project.get("files", [])


def list_build_specs(project: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List all build specifications in the project."""
    return project.get("build_specs", [])


def add_build_spec(
    project: Dict[str, Any],
    name: str,
    build_type: str = "exe",
    source_vi: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Add a build specification to the project.

    Args:
        project: Project dict.
        name: Build specification name.
        build_type: One of 'exe', 'dll', 'installer', 'zip', 'source_distribution'.
        source_vi: Main VI for the build.
        output_dir: Build output directory.

    Returns:
        Updated project dict.
    """
    spec = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "type": build_type,
        "source_vi": os.path.abspath(source_vi) if source_vi else None,
        "output_dir": os.path.abspath(output_dir) if output_dir else None,
        "created": datetime.now().isoformat(),
    }
    project.setdefault("build_specs", []).append(spec)
    return project


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _save_project_json(project: Dict[str, Any], filepath: str):
    """Save project as JSON with temp file + atomic rename."""
    tmp_path = filepath + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(project, f, indent=2, default=str, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, filepath)


def _parse_lvproj_xml(filepath: str) -> Dict[str, Any]:
    """Parse a real LabVIEW .lvproj XML file.

    LabVIEW project files have this structure:
    <Project Version="..." Type="Project">
      <Item Name="My Computer" Type="My Computer">
        <Item Name="main.vi" Type="VI" URL="..."/>
      </Item>
    </Project>

    This is a simplified parser that extracts basic structure.
    """
    import xml.etree.ElementTree as ET

    tree = ET.parse(filepath)
    root = tree.getroot()

    project = {
        "name": os.path.splitext(os.path.basename(filepath))[0],
        "type": "lvproj",
        "version": root.get("Version", "unknown"),
        "target": "My Computer",
        "files": [],
        "build_specs": [],
        "dependencies": [],
        "variables": {},
        "created": datetime.now().isoformat(),
    }

    # Parse items recursively
    ns = ""  # LabVIEW XML may use namespaces
    for item in root.iter("Item"):
        item_name = item.get("Name", "")
        item_type = item.get("Type", "")
        item_url = item.get("URL", "")

        if item_type == "VI" and item_url:
            project["files"].append({
                "id": str(uuid.uuid4())[:8],
                "name": item_name,
                "path": item_url.replace("\\", "/"),
                "category": "project",
                "added": datetime.now().isoformat(),
            })

        if item_type == "My Computer":
            project["target"] = item_name

    return project
