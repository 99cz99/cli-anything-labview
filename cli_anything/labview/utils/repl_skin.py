"""Unified REPL skin for cli-anything-labview.

Provides branded banner, colored prompts, styled messages, and
formatted output tables. Based on the cli-anything ReplSkin template.
"""

import os
import sys
from typing import Optional, Dict, List, Any


# ---------------------------------------------------------------------------
# ANSI color helpers
# ---------------------------------------------------------------------------

def _ansi(code: int) -> str:
    return f"\033[{code}m"


RESET = _ansi(0)
BOLD = _ansi(1)
DIM = _ansi(2)

# Foreground colors
RED = _ansi(31)
GREEN = _ansi(32)
YELLOW = _ansi(33)
BLUE = _ansi(34)
MAGENTA = _ansi(35)
CYAN = _ansi(36)
WHITE = _ansi(37)
GRAY = _ansi(90)

# LabVIEW brand colors (blue/teal theme)
LABVIEW_BLUE = _ansi(94)
LABVIEW_TEAL = _ansi(36)

# Background colors
BG_BLUE = _ansi(44)

# Marks (ASCII-safe for maximum terminal compatibility)
CHECK = "OK"
CROSS = "X"
WARN = "!"
INFO = "*"
ARROW = "->"
BULLET = "-"


class ReplSkin:
    """Unified REPL skin for cli-anything-labview."""

    def __init__(self, software: str = "labview", version: str = "1.0.0"):
        self.software = software
        self.version = version
        self._use_color = sys.stdout.isatty()

    def _c(self, text: str, color: str) -> str:
        """Apply color if terminal supports it."""
        if self._use_color:
            return f"{color}{text}{RESET}"
        return text

    # ------------------------------------------------------------------
    # Banner
    # ------------------------------------------------------------------

    def print_banner(self):
        """Print the startup banner."""
        lines = [
            "",
            f"  {LABVIEW_TEAL}+==========================================+{RESET}",
            f"  {LABVIEW_TEAL}|{RESET}  {BOLD}cli-anything-labview{RESET}                     {LABVIEW_TEAL}|{RESET}",
            f"  {LABVIEW_TEAL}|{RESET}  NI LabVIEW CLI Harness v{self.version}            {LABVIEW_TEAL}|{RESET}",
            f"  {LABVIEW_TEAL}|{RESET}  Type {CYAN}help{RESET} for commands, {CYAN}quit{RESET} to exit          {LABVIEW_TEAL}|{RESET}",
            f"  {LABVIEW_TEAL}+==========================================+{RESET}",
            "",
        ]
        for line in lines:
            print(line)

    def print_goodbye(self):
        """Print exit message."""
        print(f"\n  {self._c('Goodbye!', GREEN)}\n")

    # ------------------------------------------------------------------
    # Prompt
    # ------------------------------------------------------------------

    def get_prompt(self, project_name: Optional[str] = None, modified: bool = False) -> str:
        """Build the REPL prompt string."""
        parts = [f"{LABVIEW_TEAL}labview{RESET}"]
        if project_name:
            parts.append(f":{CYAN}{project_name}{RESET}")
        if modified:
            parts.append(f"{YELLOW}*{RESET}")
        parts.append(f"{GRAY}>{RESET} ")
        return "".join(parts)

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def success(self, message: str):
        """Print a success message."""
        print(f"  {self._c(CHECK, GREEN)} {message}")

    def error(self, message: str):
        """Print an error message."""
        print(f"  {self._c(CROSS, RED)} {self._c(message, RED)}")

    def warning(self, message: str):
        """Print a warning message."""
        print(f"  {self._c(WARN, YELLOW)} {self._c(message, YELLOW)}")

    def info(self, message: str):
        """Print an info message."""
        print(f"  {self._c(INFO, BLUE)} {message}")

    def status(self, key: str, value: str):
        """Print a key-value status line."""
        print(f"  {self._c(key + ':', GRAY)} {self._c(value, WHITE)}")

    # ------------------------------------------------------------------
    # Table display
    # ------------------------------------------------------------------

    def table(self, headers: List[str], rows: List[List[Any]]):
        """Print a formatted table.

        Args:
            headers: Column header names.
            rows: List of row lists.
        """
        if not rows:
            print(f"  {self._c('(empty)', GRAY)}")
            return

        # Calculate column widths
        all_data = [headers] + [[str(c) for c in row] for row in rows]
        col_widths = [
            max(len(str(row[i])) for row in all_data)
            for i in range(len(headers))
        ]

        # Separator (ASCII for cross-platform compatibility)
        sep = "  " + "  ".join("-" * w for w in col_widths)

        # Header
        header_cells = [
            self._c(h.ljust(col_widths[i]), BOLD + WHITE)
            for i, h in enumerate(headers)
        ]
        print(f"\n  {'  '.join(header_cells)}")
        print(sep)

        # Rows
        for row in rows:
            cells = [
                str(c).ljust(col_widths[i])
                for i, c in enumerate(row)
            ]
            print(f"  {'  '.join(cells)}")
        print()

    # ------------------------------------------------------------------
    # Progress bar
    # ------------------------------------------------------------------

    def progress(self, current: int, total: int, label: str = ""):
        """Print a progress bar."""
        if total == 0:
            return
        pct = current / total
        bar_width = 30
        filled = int(bar_width * pct)
        bar = "#" * filled + "." * (bar_width - filled)
        line = f"  [{bar}] {current}/{total} {label}"
        print(f"\r{line}", end="", flush=True)
        if current >= total:
            print()

    # ------------------------------------------------------------------
    # Help display
    # ------------------------------------------------------------------

    def help(self, commands: Dict[str, str]):
        """Print formatted help listing.

        Args:
            commands: Dict mapping command name to description.
        """
        print(f"\n  {BOLD}Available Commands:{RESET}\n")
        for name, desc in sorted(commands.items()):
            print(f"  {self._c(name, CYAN):<24} {desc}")
        print(f"\n  Use {self._c('<command> --help', GRAY)} for detailed options.\n")


# ---------------------------------------------------------------------------
# JSON formatting helpers (for --json output)
# ---------------------------------------------------------------------------

def json_output(data: Any) -> str:
    """Format data as JSON string for --json mode."""
    import json
    return json.dumps(data, indent=2, default=str, ensure_ascii=False)


def json_error(message: str, code: int = 1) -> str:
    """Format an error as JSON."""
    import json
    return json.dumps({"error": True, "message": message, "code": code}, indent=2)


def json_success(data: Any) -> str:
    """Wrap data in a success envelope."""
    import json
    return json.dumps({"success": True, "data": data}, indent=2, default=str)
