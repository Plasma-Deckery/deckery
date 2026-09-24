#!/usr/bin/env python3
"""
acceptance.py — exercise a running Deckery against the promises it makes.

Unit tests cover the pieces. This covers the seams: real IPC commands over the
control socket, real files in ~/.config/deckery, and the state file the tray
actually reads. Several of the checks below have no unit-test equivalent,
because what they test is the round trip — a command going out, the daemon
rewriting preferences.toml, and the result coming back through state.json.

Run it on the machine Deckery is running on: the host after a local install, or
inside a test VM after deploying there (see README.md).

    python3 testing/acceptance.py

Exit code 0 when every check passes, 1 otherwise.

## Safety

The script writes config files and toggles modules, so it borrows the live
configuration for the length of the run. Everything it touches is backed up
first and restored on the way out, including on Ctrl-C — `preferences.toml`,
plus any config file whose name it needs. It refuses to start if Deckery is not
running, rather than reporting failures that only mean "nothing was listening".
"""

import atexit
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time

CFG   = os.path.expanduser("~/.config/deckery")
# Where the tray looks, so a run against an older makima still finds the file.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tray"))
import state as _tray_state          # noqa: E402
STATE = _tray_state.STATE_JSON
SOCK  = os.path.join(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"),
                     "makima-control.sock")
PREFS = os.path.join(CFG, "preferences.toml")

results = []
_backups = {}          # live path -> temp copy, or None when it did not exist
_settle  = 1.5         # the file watcher debounces; give it room


# ── Plumbing ──────────────────────────────────────────────────────────────────

def ipc(cmd):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(2)
    s.connect(SOCK)
    s.sendall((cmd + "\n").encode())
    s.close()


def state(settle=None):
    time.sleep(_settle if settle is None else settle)
    with open(STATE) as f:
        return json.load(f)


def config(doc, name):
    return next((c for c in doc["configs"] if c["name"] == name), None)


def check(label, ok, detail=""):
    results.append((bool(ok), label, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"  — {detail}" if detail else ""))


def borrow(rel):
    """Take a config file's name for the run, saving whatever was there."""
    path = os.path.join(CFG, rel)
    if path in _backups:
        return path
    if os.path.exists(path):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".bak")
        tmp.close()
        shutil.copy2(path, tmp.name)
        _backups[path] = tmp.name
    else:
        _backups[path] = None
    return path


def write(rel, text):
    path = borrow(rel)
    with open(path, "w") as f:
        f.write(text)
    return path


def drop(rel):
    """Remove the file the run put there; the original comes back at exit."""
    try:
        os.unlink(os.path.join(CFG, rel))
    except FileNotFoundError:
        pass


@atexit.register
def restore():
    for path, backup in _backups.items():
        if backup is None:
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass
        else:
            shutil.move(backup, path)
    if _backups:
        print("\nRestored:", ", ".join(sorted(os.path.basename(p) for p in _backups)))


# ── Preconditions ─────────────────────────────────────────────────────────────

def require_running():
    if not os.path.exists(SOCK):
        sys.exit(f"Deckery is not running — no control socket at {SOCK}")
    if not os.path.exists(STATE):
        sys.exit(f"No state file at {STATE} — is makima.service up?")
    doc = state(0)
    if doc.get("lifecycle") != "ready":
        sys.exit(f"makima is {doc.get('lifecycle')!r}, not ready — try again in a moment")
    if not any(c["kind"] == "base" for c in doc["configs"]):
        sys.exit("No base config is loaded — nothing to accept")
    return doc


# ── The checks ────────────────────────────────────────────────────────────────

def modifiers_survive_a_user_module(doc):
    print("\n=== Modifiers survive a module of the user's own ===")
    # A one-line file in the user's directory merges on top of the base config.
    # That merge used to start from an empty shell and drop the derived modifier
    # set with it, so every combo the base declares stopped firing.
    write("Acceptance Tweaks.toml", "[remap]\nBTN_NORTH = [\"KEY_TAB\"]\n")
    doc = state(2)
    combos = [k for k in doc.get("bindings", {}) if "-" in str(k)]
    check("combo bindings are still reported", len(combos) > 0,
          f"{len(combos)} combos, e.g. {combos[:2]}")
    entry = config(doc, "Acceptance Tweaks")
    check("the user's module loaded", entry is not None and entry["status"] == "ok")
    drop("Acceptance Tweaks.toml")


def broken_override_falls_back(doc):
    print("\n=== A broken override falls back to the shipped config ===")
    shipped = next((c["name"] for c in doc["configs"]
                    if c["kind"] == "module" and not c.get("exclusive_group")), None)
    if shipped is None:
        check("a shipped module to shadow", False, "none found — cannot test")
        return
    write(f"{shipped}.toml", "[remap\nnot toml\n")
    doc = state()
    entry = config(doc, shipped)
    check("status is warning, not error", entry["status"] == "warning", entry["status"])
    check("the config stays active", entry["enabled"] is True)
    msg = entry["errors"][0]["message"] if entry["errors"] else ""
    check("the message names the file that was skipped", f"{shipped}.toml" in msg)
    check("no global error — the tray stays green", doc.get("errors") == {})
    drop(f"{shipped}.toml")


def unknown_keys_are_refused(doc):
    print("\n=== Unknown keys in the fixed sections are refused ===")
    # A misspelt match_window_class used to be dropped silently, turning an app
    # override into a plain module that applied to every window.
    write("Acceptance Bad Key.toml",
          "[module]\nmatch_window_classes = [\"firefox\"]\n")
    doc = state()
    entry = config(doc, "Acceptance Bad Key")
    check("a misspelt [module] key is a hard error", entry["status"] == "error")
    check("the message names the key",
          "match_window_classes" in (entry["errors"][0]["message"] if entry["errors"] else ""))
    drop("Acceptance Bad Key.toml")

    write("Acceptance Bad Section.toml", "[remaps]\nBTN_SOUTH = [\"KEY_B\"]\n")
    doc = state()
    check("a misspelt section name is refused",
          config(doc, "Acceptance Bad Section")["status"] == "error")
    drop("Acceptance Bad Section.toml")

    # The guard must not reach into the binding maps: their keys are button
    # names and there is no list of legal ones.
    write("Acceptance Combos.toml", "[remap]\nBTN_TL-BTN_SOUTH = [\"KEY_A\"]\n")
    doc = state()
    check("button names stay free-form",
          config(doc, "Acceptance Combos")["status"] == "ok")
    drop("Acceptance Combos.toml")


def a_group_switches_off_and_remembers(doc):
    print("\n=== A whole group switches off, and remembers the choice ===")
    doc = state(2)
    groups = {c["exclusive_group"] for c in doc["configs"] if c.get("exclusive_group")}
    if not groups:
        check("an exclusive group to test", False, "none configured — skipped")
        return
    slug = sorted(groups)[0]
    borrow("preferences.toml")

    active = [c["name"] for c in doc["configs"]
              if c.get("exclusive_group") == slug and c["enabled"]]
    check("exactly one member is active", len(active) == 1,
          active[0] if active else "none")
    if not active:
        return

    ipc(f"config group disable {slug}")
    doc = state()
    off = [c["name"] for c in doc["configs"]
           if c.get("exclusive_group") == slug and c["enabled"]]
    check("no member is active any more", off == [], str(off))
    prefs = open(PREFS).read()
    check("the group is listed under [groups] disabled", slug in prefs.split("[modules]")[0])
    check("the member choice is kept while it is off", active[0] in prefs)

    ipc(f"config group enable {slug}")
    doc = state()
    back = [c["name"] for c in doc["configs"]
            if c.get("exclusive_group") == slug and c["enabled"]]
    check("the remembered member returns, not the alphabetically first one",
          back == active, f"{back} (was {active})")


def the_base_config_cannot_be_switched_off(doc):
    print("\n=== The base config cannot be switched off ===")
    # resolve() would have no answer on any layout, and update_config used to
    # recurse into change_active_layout over it, one heap allocation per turn.
    base = next(c for c in state(0)["configs"] if c["kind"] == "base")
    ipc(f"config disable {base['name']}")
    doc = state()
    still = next(c for c in doc["configs"] if c["kind"] == "base")
    check("the base config stays active", still["enabled"] is True)
    check("the daemon is ready and reports no error",
          doc.get("lifecycle") == "ready" and doc.get("errors") == {})
    out = subprocess.run(["systemctl", "--user", "show", "makima.service",
                          "-p", "MemoryCurrent", "--value"],
                         capture_output=True, text=True).stdout.strip()
    if out.isdigit():
        mb = int(out) / 1048576
        check("memory is not running away", mb < 60, f"{mb:.1f} MB")


def the_state_file_comes_back(doc):
    print("\n=== The state file is recreated when it disappears ===")
    # flush() skips a write whose content is unchanged, so a state file swept
    # out of /tmp used to stay gone until something else changed.
    module = next((c["name"] for c in doc["configs"]
                   if c["kind"] == "module" and not c.get("exclusive_group")), None)
    if module is None:
        check("a module to toggle", False, "none found — skipped")
        return
    borrow("preferences.toml")
    os.unlink(STATE)
    ipc(f"config disable {module}")
    time.sleep(2)
    check("the file is there again", os.path.exists(STATE))
    ipc(f"config enable {module}")
    time.sleep(_settle)


def a_malformed_state_file_does_not_blank_the_tray(doc):
    print("\n=== A malformed state file does not blank the tray ===")
    # /tmp is mode 1777, so the shape of this file is not the tray's to assume.
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tray_dir = os.path.join(repo, "tray")
    if not os.path.isdir(os.path.join(tray_dir, "tests")):
        check("the tray sources to test against", False, "not next to this script — skipped")
        return
    sys.path.insert(0, tray_dir)
    sys.path.insert(0, os.path.join(tray_dir, "tests"))
    import conftest  # noqa: F401  — installs the GTK mocks
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "acceptance_tray", os.path.join(tray_dir, "deckery-tray.py"))
    tray = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tray)

    live = state(0)
    cases = [
        ("an errors entry is a string", lambda d: d.update(errors={"no_device": "x"}), len(live["configs"])),
        ("errors itself is a list",     lambda d: d.update(errors=["x"]),              len(live["configs"])),
        ("a config entry is a string",  lambda d: d["configs"].append("x"),            len(live["configs"])),
        ("context is a string",         lambda d: d.update(context="x"),               len(live["configs"])),
        ("the whole file is null",      None,                                          0),
    ]
    for label, mutate, expected in cases:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            if mutate is None:
                f.write("null")
            else:
                doc = json.loads(json.dumps(live))
                mutate(doc)
                json.dump(doc, f)
            path = f.name
        tray._STATE_JSON = path
        parsed = tray._makima_state()
        check(f"{label}: the menu survives", len(parsed.configs) == expected,
              f"configs={len(parsed.configs)}")
        os.unlink(path)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    doc = require_running()
    print(f"Deckery is ready — {len(doc['configs'])} configs loaded")

    modifiers_survive_a_user_module(doc)
    broken_override_falls_back(doc)
    unknown_keys_are_refused(doc)
    a_group_switches_off_and_remembers(doc)
    the_base_config_cannot_be_switched_off(doc)
    the_state_file_comes_back(doc)
    a_malformed_state_file_does_not_blank_the_tray(doc)

    failed = [r for r in results if not r[0]]
    print("\n" + "=" * 62)
    print(f"{len(results) - len(failed)}/{len(results)} passed")
    for _, label, detail in failed:
        print(f"  FAILED: {label}" + (f" — {detail}" if detail else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
