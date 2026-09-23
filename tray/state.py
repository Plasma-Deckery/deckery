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

_RUNTIME_STATE = os.path.join(
    os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}",
    "makima-state.json")
_LEGACY_STATE = "/tmp/makima-state.json"


def state_path() -> str:
    """Where makima's state file is, preferring the runtime directory.

    makima writes to `$XDG_RUNTIME_DIR` — a per-user tmpfs, mode 0700, the same
    place the control socket lives, and for the same reason: `/tmp` is mode
    1777, so anything able to create the path first decides what every reader
    here believes.

    The `/tmp` fallback is for a makima from before the move, which still
    writes there. The three components ship together, so that window is short,
    but it is not zero.

    The test is deliberately one-sided: `/tmp` is chosen only when there is a
    file there and none in the runtime directory. The tray starts *before*
    makima — deckery-hud and makima are both `BindsTo` it — so at the moment
    this runs neither file need exist yet, and defaulting to the legacy path
    then would leave the tray watching a directory nothing will ever write to.
    """
    if os.path.exists(_RUNTIME_STATE):
        return _RUNTIME_STATE
    if os.path.exists(_LEGACY_STATE):
        return _LEGACY_STATE
    return _RUNTIME_STATE


STATE_JSON = state_path()

# Where the shipped configs are when makima has not said. Only used before it
# has ever run — which is exactly when the setup wizard is on screen.
_REPO_CONFIGS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs")
_RPM_CONFIGS  = "/usr/share/deckery/configs"
USER_CONFIGS  = os.path.expanduser("~/.config/deckery")


def read(path: str = STATE_JSON) -> dict:
    """The state file as a mapping, or `{}` if it is not there or not usable.

    A missing file is the normal state of a stopped makima and says nothing.
    Anything else — truncated JSON, a permission problem — is worth a line in
    the log, because it looks identical from the caller's side and is not.

    The isinstance check is not paranoia about our own writer. Under the `/tmp`
    fallback the file sits in a world-writable directory, where any local
    process can create it first — and `null`, `[]` and `"text"` are all valid
    JSON, while every caller here goes on to treat the result as a mapping.
    """
    try:
        with open(path) as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        log.warning("Failed to read %s", path, exc_info=True)
        return {}
    if not isinstance(data, dict):
        log.warning("%s holds %s, not an object — ignoring it",
                    path, type(data).__name__)
        return {}
    return data


def config_roots(path: str = STATE_JSON) -> list:
    """Both directories configs are read from, the shipped one first.

    Deckery stopped copying its configs into the user's directory, so looking
    only there finds nothing on a fresh install. makima publishes both roots in
    its state file — it is the only party that knows whether this is a git
    checkout or an RPM install.

    The fallback covers the window before makima has ever written that file.
    """
    roots = read(path).get("config_roots")
    if not isinstance(roots, dict):
        roots = {}
    if roots.get("system") and roots.get("user"):
        return [roots["system"], roots["user"]]
    shipped = _REPO_CONFIGS if os.path.isdir(_REPO_CONFIGS) else _RPM_CONFIGS
    return [shipped, USER_CONFIGS]
