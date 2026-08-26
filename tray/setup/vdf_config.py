"""
vdf_config.py -- Read and write Steam controller VDF config files.

Uses the 'vdf' Python package (v3.4+, already installed system-wide).
Duplicate keys (multiple 'group' entries) are handled correctly via VDFDict
with merge_duplicate_keys=False.

Locking/unlocking uses distrobox-host-exec + sudo chattr, which requires the
deckery-chattr sudoers rule (see requirements_check.py).
"""
import glob
import io
import os
import subprocess

import vdf as _vdf

from .common import DECKERY_CONFIGS


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def find_vdf() -> str | None:
    """Return path to the desktop VDF (desktop_neptune.vdf or similar)."""
    candidates = glob.glob(os.path.join(DECKERY_CONFIGS, "desktop_*.vdf"))
    return candidates[0] if candidates else None


# ---------------------------------------------------------------------------
# chattr lock / unlock
# ---------------------------------------------------------------------------

def _chattr(path: str, lock: bool) -> bool:
    flag = "+i" if lock else "-i"
    r = subprocess.run(
        ["distrobox-host-exec", "sudo", "chattr", flag, path],
        capture_output=True,
    )
    return r.returncode == 0


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------

def _load(path: str) -> _vdf.VDFDict:
    with open(path, "r", encoding="utf-8") as f:
        return _vdf.load(f, mapper=_vdf.VDFDict, merge_duplicate_keys=False)


def _save(data: _vdf.VDFDict, path: str) -> None:
    """Unlock, write, re-lock."""
    _chattr(path, lock=False)
    try:
        buf = io.StringIO()
        _vdf.dump(data, buf, pretty=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(buf.getvalue())
    finally:
        _chattr(path, lock=True)


# ---------------------------------------------------------------------------
# Tree walker
# ---------------------------------------------------------------------------

def _walk(node, fn):
    """Call fn(node) on every VDFDict node in the tree (depth-first)."""
    if not hasattr(node, "items"):
        return
    fn(node)
    for _, child in node.items():
        _walk(child, fn)


# ---------------------------------------------------------------------------
# Public operations
# ---------------------------------------------------------------------------

def clear_all_bindings(path: str) -> None:
    """
    Move all active button bindings to disabled_activators.

    Every input block in the VDF has:
        "activators"          { ... bindings ... }
        "disabled_activators" { }

    This moves content from activators -> disabled_activators so Steam
    no longer processes the bindings, but nothing is deleted (reversible).
    """
    data = _load(path)

    def _disable(node):
        if "activators" not in node or "disabled_activators" not in node:
            return
        src = node["activators"]
        dst = node["disabled_activators"]
        if len(src) == 0:
            return
        # Move every activator type (Full_Press, Long_Press, etc.) over
        for act_type, act_data in list(src.items()):
            dst[act_type] = act_data
        # Clear activators
        for act_type in list(src.keys()):
            del src[act_type]

    _walk(data, _disable)
    _save(data, path)


def restore_all_bindings(path: str) -> None:
    """
    Reverse of clear_all_bindings: move content back from
    disabled_activators -> activators.
    """
    data = _load(path)

    def _restore(node):
        if "activators" not in node or "disabled_activators" not in node:
            return
        src = node["disabled_activators"]
        dst = node["activators"]
        if len(src) == 0:
            return
        for act_type, act_data in list(src.items()):
            dst[act_type] = act_data
        for act_type in list(src.keys()):
            del src[act_type]

    _walk(data, _restore)
    _save(data, path)


def set_group_mode(path: str, group_id: int, mode: str) -> None:
    """
    Change the mode of a specific group by ID.
    E.g. set_group_mode(path, 8, "absolute_mouse")
    """
    data = _load(path)

    def _set_mode(node):
        if node.get("id") == str(group_id) and "mode" in node:
            node["mode"] = mode

    _walk(data, _set_mode)
    _save(data, path)


def get_group_ids_by_mode(path: str, mode: str) -> list[int]:
    """Return IDs of all groups that currently use the given mode."""
    data = _load(path)
    result = []

    def _collect(node):
        if node.get("mode") == mode and "id" in node:
            result.append(int(node["id"]))

    _walk(data, _collect)
    return result


def count_active_bindings(path: str) -> int:
    """Return number of activator blocks that still have content."""
    data = _load(path)
    count = [0]

    def _count(node):
        if "activators" in node and len(node["activators"]) > 0:
            count[0] += 1

    _walk(data, _count)
    return count[0]
