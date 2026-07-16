"""
steam_bridge.py — Manages the Steam Desktop Controller Config (App ID 413080).

Instead of overwriting and locking controller_base/desktop_neptune.vdf (which
breaks on Steam updates), we write a single entry into configset_controller_neptune.vdf.
This is Steam's own "Local Selection" mechanism — it takes priority over the
system default and points to Steam's built-in empty.vdf, which has no bindings.

The configset file may contain entries for other apps (e.g. EmuDeck game
configs). These are always preserved — only the "413080" block is touched.

All Steam accounts on this machine receive the same setting (glob over all
per-account config directories), since the Desktop config preference should
be identical for every account that has Deckery installed.
"""

from __future__ import annotations

import glob
import logging
import os
import re
import sys

log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

DESKTOP_APP_ID = "413080"   # Steam's internal ID for the Desktop controller config
TEMPLATE_EMPTY = "LOCAL_controller_base/empty.vdf"

_CONFIGSET_GLOB = os.path.expanduser(
    "~/.local/share/Steam/steamapps/common/"
    "Steam Controller Configs/*/config/configset_controller_neptune.vdf"
)
_EMPTY_VDF = os.path.expanduser(
    "~/.local/share/Steam/controller_base/empty.vdf"
)

# ── Internal helpers ──────────────────────────────────────────────────────────

def _find_configset_paths() -> list[str]:
    paths = glob.glob(_CONFIGSET_GLOB)
    if not paths:
        log.warning("steam_bridge: no configset_controller_neptune.vdf found")
    return paths


def _read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        log.warning("steam_bridge: cannot read %s: %s", path, e)
        return ""


def _write(path: str, content: str) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except OSError as e:
        log.error("steam_bridge: cannot write %s: %s", path, e)
        return False


_BLOCK_RE = re.compile(r'("413080"\s*\{[^}]*\})', re.DOTALL)

def _build_block() -> str:
    return f'"{DESKTOP_APP_ID}"\n\t{{\n\t\t"template"\t\t"{TEMPLATE_EMPTY}"\n\t}}'

def _get_template(text: str) -> str | None:
    m = _BLOCK_RE.search(text)
    if not m:
        return None
    tm = re.search(r'"template"\s+"([^"]+)"', m.group(1))
    return tm.group(1) if tm else None

def _set_template(text: str) -> str:
    block = _build_block()
    if _BLOCK_RE.search(text):
        return _BLOCK_RE.sub(block, text)
    return text.rstrip().rstrip("}").rstrip() + "\n\t" + block + "\n}\n"

# ── Public API ────────────────────────────────────────────────────────────────

def is_configured() -> bool:
    """Return True if ALL configset files have the 413080 entry pointing to empty.vdf."""
    paths = _find_configset_paths()
    if not paths:
        return False
    return all(_get_template(_read(p)) == TEMPLATE_EMPTY for p in paths)


def apply() -> bool:
    """
    Write the empty.vdf entry for App ID 413080 into all configset files.
    Returns True if all writes succeeded.
    """
    if not os.path.exists(_EMPTY_VDF):
        log.error(
            "steam_bridge: empty.vdf not found at %s — "
            "Steam installation may be broken or incomplete", _EMPTY_VDF
        )
        return False

    paths = _find_configset_paths()
    if not paths:
        log.error("steam_bridge: no configset paths found — cannot apply")
        return False

    ok = True
    for path in paths:
        text = _read(path) or '"controller_config"\n{\n}\n'
        if not _write(path, _set_template(text)):
            ok = False
        else:
            log.info("steam_bridge: applied empty.vdf config in %s", path)
    return ok


def remove() -> bool:
    """
    Remove the 413080 entry from all configset files, restoring Steam's default.
    Returns True if all writes succeeded (or there was nothing to remove).
    """
    paths = _find_configset_paths()
    if not paths:
        return True
    ok = True
    for path in paths:
        text = _read(path)
        if not text or not _BLOCK_RE.search(text):
            continue
        new_text = _BLOCK_RE.sub("", text)
        if not _write(path, new_text):
            ok = False
        else:
            log.info("steam_bridge: removed Desktop config entry from %s", path)
    return ok


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if len(sys.argv) > 1 and sys.argv[1] == "--remove":
        sys.exit(0 if remove() else 1)
    sys.exit(0 if apply() else 1)
