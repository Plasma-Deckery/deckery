"""
state.py — the one reader of makima's state file.

Two places used to open `/tmp/makima-state.json` independently: the tray, for
service status and the config list, and the setup wizard, for the two config
directories. Same file, two parsers, two sets of fallbacks — and the wizard's
copy sat in `setup/common.py`, which is a module about widget helpers and CSS.

Deliberately free of GTK and of any other tray module, so both sides can import
it without dragging the other along.
"""

import json
import logging
import os

log = logging.getLogger("deckery-tray")

STATE_JSON = "/tmp/makima-state.json"

# Where the shipped configs are when makima has not said. Only used before it
# has ever run — which is exactly when the setup wizard is on screen.
_REPO_CONFIGS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs")
_RPM_CONFIGS  = "/usr/share/deckery/configs"
USER_CONFIGS  = os.path.expanduser("~/.config/deckery")


def read(path: str = STATE_JSON) -> dict:
    """The state file as a mapping, or `{}` if it is not there or not readable.

    A missing file is the normal state of a stopped makima and says nothing.
    Anything else — truncated JSON, a permission problem — is worth a line in
    the log, because it looks identical from the caller's side and is not.
    """
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        log.warning("Failed to read %s", path, exc_info=True)
        return {}


def config_roots(path: str = STATE_JSON) -> list:
    """Both directories configs are read from, the shipped one first.

    Deckery stopped copying its configs into the user's directory, so looking
    only there finds nothing on a fresh install. makima publishes both roots in
    its state file — it is the only party that knows whether this is a git
    checkout or an RPM install.

    The fallback covers the window before makima has ever written that file.
    """
    roots = read(path).get("config_roots") or {}
    if roots.get("system") and roots.get("user"):
        return [roots["system"], roots["user"]]
    shipped = _REPO_CONFIGS if os.path.isdir(_REPO_CONFIGS) else _RPM_CONFIGS
    return [shipped, USER_CONFIGS]
