# LabVIEW 2025 — Software-Specific SOP

## Overview

LabVIEW (Laboratory Virtual Instrument Engineering Workbench) is a system-design platform
and development environment for visual programming from National Instruments (NI). It's widely
used for data acquisition, instrument control, and industrial automation.

## Architecture Analysis

### Backend Engine

LabVIEW's automation interfaces are:

| Interface | Protocol | Port/ID | Status | Notes |
|-----------|----------|---------|--------|-------|
| ActiveX/COM | COM Automation | `LabVIEW.Application` | Stable | Primary for Windows automation |
| VI Server (local) | Internal messaging | — | Stable | Local VI-to-VI communication |
| VI Server (TCP) | Proprietary binary | 3363 (default) | Stable | Remote control, undocumented wire protocol |
| LabVIEW CLI | CLI tool | TCP port 3363 | 2014+ | Build automation, VI execution |
| LabVIEW Web Server | HTTP/REST | 8080 (default) | Available | Web-based VI execution |
| Command Line | Process launch | `LabVIEW.exe <vi>` | Always | Simplest form of automation |

### Data Model

- **VI files**: Binary `.vi` format containing front panel + block diagram
- **Project files**: `.lvproj` (XML) for multi-VI projects
- **Control files**: `.ctl` for custom control/type definitions
- **Build specs**: Embedded in project files
- **VI Server refnums**: Application, VI, Control references
- **State**: In-memory only; no built-in session persistence

### Existing CLI Tools

1. **LabVIEW.exe** — Can launch VIs directly with arguments: `LabVIEW.exe "path\to\vi.vi" -- arg1 arg2`
2. **LabVIEWCLI.exe** — Dedicated CLI for build operations (separate install)
3. **VI Server** — Rich programmatic control via ActiveX/TCP

### GUI-to-API Mappings

| GUI Action | ActiveX/VI Server API | CLI Command |
|------------|----------------------|-------------|
| File → New VI | `Application.NewVI()` | `vi create` |
| File → Open VI | `Application.GetVIReference(path)` | `vi open` |
| Operate → Run | `VI.Run(wait)` | `run start` |
| Operate → Stop | `VI.Abort()` | `run stop` |
| Set control value | `VI.SetControlValue(name, value)` | `control set` |
| Get indicator value | `VI.GetControlValue(name)` | `control get` |
| Save VI | `VI.Save()` | `vi save` |
| Close VI | `VI.Close()` | `vi close` |
| Project → New | `Application.NewProject()` | `project new` |
| Build Application | Build spec in project | `build run` |

## Automation Approach

### Primary: ActiveX/COM via pywin32

```python
import win32com.client

labview = win32com.client.Dispatch("LabVIEW.Application")
vi = labview.GetVIReference(r"C:\path\to\vi.vi")
vi.SetControlValue("input", 3.14)
vi.Run(True)  # Wait until done
result = vi.GetControlValue("output")
vi.Close()
```

**Critical:** LabVIEW ActiveX type library doesn't flag all methods properly.
Use `_FlagAsMethod()` for: Run, OpenFrontPanel, CloseFrontPanel, Abort, etc.

### Secondary: Command Line Invocation

```python
import subprocess
subprocess.run(["LabVIEW.exe", r"C:\path\to\vi.vi", "--", "arg1", "arg2"])
```

### Tertiary: VI Server TCP

For remote deployments, connect via TCP to port 3363. Proprietary protocol
requires LabVIEW's built-in VI Server functions as the intermediary.
