"""S7g: the privileged store root, resolved once for every OS (spec §4.1).

Before this module the store root existed only in the ops shell scripts — three times,
once per OS (`p07_setup_linux.sh`, `p07_setup_windows.ps1`, and the macOS scripts
hardcoding the IronFleetPriv volume). RUNBOOK_P0_7 lines 33-34 deferred the Python
core's own wiring; S7g shipped the RESOLVER for that wiring, and the launcher
(`harness.ops.ironfleet_launcher`) is now its first core consumer — it stands the
egress proxy up on `<store-root>` directly. The ops scripts keep their own copy because
they run before the core is installed.

The resolution carries a `source` string — the same discipline as `capacity.py`, because
"the store is at X" without "because HARNESS_HOME said so / this is the encrypted volume
/ we fell back" is a claim an operator cannot audit. On macOS the difference is a
privilege question: the fallback sits OFF the encrypted volume, so its source string is
what lets the verifier distinguish "protected" from "relocated".
"""
from __future__ import annotations

import os
import platform
from pathlib import Path

# The macOS privileged store: an encrypted APFS volume created by p07_setup_macos.sh.
# Named, not constructed, so the ops script and the core cannot drift apart on it.
MACOS_VOLUME = "IronFleetPriv"
MACOS_STORE = f"/Volumes/{MACOS_VOLUME}/harness"


def _macos_volume_present() -> bool:
    """Whether the encrypted volume is mounted. A seam for tests — Path.is_dir() on a
    macOS absolute path cannot be forced to return True on a Windows test box."""
    return Path(MACOS_STORE).is_dir()


def resolve_store_root() -> tuple[Path, str]:
    """HARNESS_HOME wins; else the platform default. Returns (root, source).

    Never raises: an unrecognised platform gets a home-relative root and a source string
    that names the guess, mirroring machine_capacity()'s never-raise contract — a
    store-resolution failure must not kill dispatch.
    """
    env = os.environ.get("HARNESS_HOME")
    if env:
        return Path(env), "HARNESS_HOME"
    system = platform.system()
    if system == "Darwin":
        if _macos_volume_present():
            return Path(MACOS_STORE), "ironfleetpriv-volume"
        return (Path.home() / "Library" / "Application Support" / "IronFleet" / "harness",
                "library-fallback")
    if system == "Windows":
        local = os.environ.get("LOCALAPPDATA")
        base = Path(local) if local else Path.home() / "AppData" / "Local"
        return base / "IronFleet" / "harness", "localappdata"
    if system == "Linux":
        xdg = os.environ.get("XDG_DATA_HOME")
        base = Path(xdg) if xdg else Path.home() / ".local" / "share"
        return base / "ironfleet" / "harness", "xdg"
    return (Path.home() / "ironfleet" / "harness",
            f"home-relative (unknown platform {system})")
