"""Configuration loader and toolchain discovery for Folio."""

from __future__ import annotations

import os
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Any


def load_user_config() -> dict[str, Any]:
    """Loads optional user defaults from ~/.config/folio/folio.toml."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg_config) if xdg_config else Path.home() / ".config"
    cfg_path = base / "folio" / "folio.toml"
    if cfg_path.is_file():
        try:
            with cfg_path.open("rb") as f:
                data = tomllib.load(f)
            return data.get("general", data) if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def get_tool_version(cmd: str) -> str | None:
    """Returns the first version string from a CLI tool, or None if unavailable."""
    path = shutil.which(cmd)
    if not path:
        return None
    try:
        res = subprocess.run(
            [cmd, "--version"],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        first_line = (res.stdout or res.stderr).splitlines()
        return first_line[0].strip() if first_line else "available"
    except Exception:
        return "available"


def check_toolchain() -> dict[str, dict[str, Any]]:
    """Checks the availability and version of document compilation backends."""
    tools = ["typst", "tectonic", "pandoc"]
    status: dict[str, dict[str, Any]] = {}
    for tool in tools:
        path = shutil.which(tool)
        version = get_tool_version(tool) if path else None
        status[tool] = {
            "installed": path is not None,
            "path": path,
            "version": version,
        }
    return status
