"""
channel.py — Update check and system update for packaged (RPM) installs.

On a packaged install the tray never installs anything itself: Deckery comes
with the system update (Issue #78). This module answers two questions for that
case:

1. Does the user's enabled package channel offer a newer deckery-tray build
   than the installed one?  (check() — the channel, not git tags, is the
   reference, so "update available" only appears when the system update can
   actually deliver it.)
2. Can the tray start the system update?  (system_update_command() — only on
   images that ship `ujust`, i.e. Universal Blue / Bazzite.)

Channel source: the repository metadata (repomd.xml → primary.xml.gz) at the
baseurl of the enabled repo file. That is exactly what the system update reads,
for the user's own Fedora release and architecture: a build that failed or was
never made for that chroot is not offered. The COPR API's "latest succeeded
build" is per package, not per chroot, and would add a second service to
depend on. The metadata is a few KB per channel.

Nothing here touches GTK; everything is testable with subprocess and urllib
mocked.
"""

import configparser
import glob
import gzip
import json
import logging
import os
import platform
import re
import shlex
import shutil
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
from typing import NamedTuple

log = logging.getLogger("updater.channel")

REPO_DIR = "/etc/yum.repos.d"
OS_RELEASE = "/etc/os-release"

# Repo ids as written by `dnf copr enable` / the Deckery install docs.
CHANNELS = {
    "copr:copr.fedorainfracloud.org:phischx:Deckery":      "stable",
    "copr:copr.fedorainfracloud.org:phischx:Deckery-beta": "beta",
}

_NS_REPO   = "{http://linux.duke.edu/metadata/repo}"
_NS_COMMON = "{http://linux.duke.edu/metadata/common}"


# ── EVR ───────────────────────────────────────────────────────────────────────

class EVR(NamedTuple):
    epoch:   str
    version: str
    release: str

    def __str__(self) -> str:
        e = "" if self.epoch in ("", "0") else f"{self.epoch}:"
        return f"{e}{self.version}-{self.release}"


def _evr_string(e: EVR) -> str:
    return f"{e.epoch or '0'}:{e.version}-{e.release}"


def compare_evr(a: EVR, b: EVR) -> int:
    """RPM comparison of two EVRs: -1, 0 or 1. Uses python3-rpm when present
    (it is on Bazzite), else rpm's own Lua vercmp. Raises if neither works —
    a wrong guess here would show a false update."""
    try:
        import rpm  # python3-rpm
        return rpm.labelCompare((a.epoch or "0", a.version, a.release),
                                (b.epoch or "0", b.version, b.release))
    except ImportError:
        pass
    expr = (f'%{{lua: print(rpm.vercmp("{_evr_string(a)}", '
            f'"{_evr_string(b)}"))}}')
    r = subprocess.run(["rpm", "--eval", expr],
                       capture_output=True, text=True, timeout=5)
    out = r.stdout.strip()
    if r.returncode != 0 or out not in ("-1", "0", "1"):
        raise RuntimeError(f"rpm vercmp failed: {r.stderr.strip() or out!r}")
    return int(out)


def display_version(offered: EVR, installed: EVR) -> str:
    """Version for the menu label. The plain version normally ('0.6.0'); with
    the package build number when only that changed ('0.5.0-3'), so the label
    never names the version the user already has. The distribution suffix
    ('.fc44') is left out."""
    if offered.version != installed.version:
        return offered.version
    return f"{offered.version}-{re.sub(r'\.fc\d+.*$', '', offered.release)}"


# ── Installed / pending ───────────────────────────────────────────────────────

def installed_package(path: str) -> tuple[str, EVR] | None:
    """(name, EVR) of the RPM that owns path (the running tray), or None."""
    try:
        r = subprocess.run(
            ["rpm", "-qf", "--qf", "%{NAME} %{EPOCHNUM} %{VERSION} %{RELEASE}", path],
            capture_output=True, text=True, timeout=5,
        )
        parts = r.stdout.split()
        if r.returncode == 0 and len(parts) == 4:
            return parts[0], EVR(parts[1], parts[2], parts[3])
    except Exception:
        pass
    return None


def _parse_nevra(line: str, name: str) -> EVR | None:
    """'deckery-tray-0.5.0-3.fc44.noarch' (optionally 'name-E:V-R.arch')."""
    m = re.fullmatch(re.escape(name) + r"-(?:(\d+):)?([^-]+)-([^-]+)\.[^.]+",
                     line.strip())
    if not m:
        return None
    return EVR(m.group(1) or "0", m.group(2), m.group(3))


def pending_package(name: str) -> EVR | None:
    """EVR of `name` in the deployment that the next boot will use, if that is
    not the booted one (an update downloaded and waiting for a restart).
    None on non-ostree systems, when nothing is pending, or on any error."""
    if not shutil.which("rpm-ostree"):
        return None
    try:
        r = subprocess.run(["rpm-ostree", "status", "--json"],
                           capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return None
        deployments = json.loads(r.stdout).get("deployments") or []
        # Deployment 0 is the one the next boot uses.
        if not deployments or deployments[0].get("booted"):
            return None
        checksum = deployments[0].get("checksum")
        if not checksum:
            return None
        r = subprocess.run(["rpm-ostree", "db", "list", checksum, name],
                           capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return None
        for line in r.stdout.splitlines():
            evr = _parse_nevra(line, name)
            if evr:
                return evr
    except Exception as e:
        log.info("pending deployment not readable: %s", e)
    return None


# ── Channel ───────────────────────────────────────────────────────────────────

def _truthy(v: str) -> bool:
    return v.strip().lower() in ("1", "yes", "true", "on")


def enabled_channels(repo_dir: str = REPO_DIR) -> dict[str, str]:
    """Enabled Deckery channels: {channel name: baseurl (unexpanded)}.

    Reads every *.repo file. A repo id can appear in more than one file
    (copies left by a re-enable, or by hand); it counts once, and as enabled
    if any copy is enabled with a baseurl. Both channels may be enabled at
    once — then both are checked, as the system update would."""
    found: dict[str, str] = {}
    for path in sorted(glob.glob(os.path.join(repo_dir, "*.repo"))):
        cp = configparser.ConfigParser(interpolation=None, strict=False)
        try:
            cp.read(path, encoding="utf-8")
        except (configparser.Error, OSError, UnicodeDecodeError) as e:
            log.info("skipping unreadable repo file %s: %s", path, e)
            continue
        for repo_id in cp.sections():
            channel = CHANNELS.get(repo_id)
            if not channel or channel in found:
                continue
            sec = cp[repo_id]
            # dnf treats a missing "enabled" as enabled.
            if not _truthy(sec.get("enabled", "1")):
                continue
            baseurl = sec.get("baseurl", "").split()
            if baseurl:
                found[channel] = baseurl[0]
    return found


def _releasever(os_release: str = OS_RELEASE) -> str:
    try:
        with open(os_release, encoding="utf-8") as f:
            for line in f:
                if line.startswith("VERSION_ID="):
                    return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    raise RuntimeError("cannot determine the Fedora release")


def expand_baseurl(url: str, releasever: str, basearch: str) -> str:
    return url.replace("$releasever", releasever).replace("$basearch", basearch)


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "deckery-tray"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()


def newest_in_repo(baseurl: str, name: str) -> EVR | None:
    """Newest binary build of `name` in the repo at baseurl, or None if the
    repo has none. Raises on network or format errors."""
    base = baseurl.rstrip("/") + "/"
    repomd = ET.fromstring(_fetch(base + "repodata/repomd.xml"))
    href = None
    for data in repomd.findall(f"{_NS_REPO}data"):
        if data.get("type") == "primary":
            loc = data.find(f"{_NS_REPO}location")
            href = loc.get("href") if loc is not None else None
    if not href:
        raise ValueError("repo metadata has no primary entry")
    raw = _fetch(base + href)
    if href.endswith(".gz"):
        raw = gzip.decompress(raw)
    elif not href.endswith(".xml"):
        raise ValueError(f"unsupported metadata compression: {href}")
    best: EVR | None = None
    for pkg in ET.fromstring(raw).findall(f"{_NS_COMMON}package"):
        if pkg.findtext(f"{_NS_COMMON}name") != name:
            continue
        if pkg.findtext(f"{_NS_COMMON}arch") == "src":
            continue
        v = pkg.find(f"{_NS_COMMON}version")
        if v is None:
            continue
        evr = EVR(v.get("epoch") or "0", v.get("ver", ""), v.get("rel", ""))
        if best is None or compare_evr(evr, best) > 0:
            best = evr
    return best


def newest_offered(name: str, repo_dir: str = REPO_DIR,
                   os_release: str = OS_RELEASE) -> tuple[str, EVR] | None:
    """(channel, EVR) of the newest build any enabled channel offers, or None
    if no Deckery channel is enabled or none has a build. Raises on network
    errors."""
    channels = enabled_channels(repo_dir)
    if not channels:
        return None
    releasever = _releasever(os_release)
    basearch = platform.machine()
    best: tuple[str, EVR] | None = None
    for channel, url in channels.items():
        evr = newest_in_repo(expand_baseurl(url, releasever, basearch), name)
        log.info("channel %s offers %s", channel, evr)
        if evr and (best is None or compare_evr(evr, best[1]) > 0):
            best = (channel, evr)
    return best


# ── Result of a packaged check ────────────────────────────────────────────────

class Result(NamedTuple):
    status:  str          # "up_to_date" | "update_available" | "restart_required"
    version: str | None   # for the label; None when up to date


def check(tray_file: str) -> Result:
    """Channel-aware check for a packaged install. Raises on any failure that
    should show as the error state (network, unreadable package database)."""
    owner = installed_package(tray_file)
    if owner is None:
        raise RuntimeError("installed package version not readable")
    name, installed = owner
    offered = newest_offered(name)
    if offered is None:
        log.info("no enabled Deckery channel offers %s", name)
        return Result("up_to_date", None)
    channel, evr = offered
    pending = pending_package(name)
    log.info("installed %s  offered %s (%s)  pending %s", installed, evr, channel, pending)
    if (pending is not None and compare_evr(pending, installed) > 0
            and compare_evr(pending, evr) >= 0):
        return Result("restart_required", display_version(pending, installed))
    if compare_evr(evr, installed) > 0:
        return Result("update_available", display_version(evr, installed))
    return Result("up_to_date", None)


# ── Starting the system update ────────────────────────────────────────────────

# Shown inside the terminal window. Plain words, no tool names.
TERMINAL_SCRIPT = """\
echo "Updating your system. This can take a while. Please keep this window open."
echo
ujust update
status=$?
echo
if [ "$status" -eq 0 ]; then
  echo "Done. Restart your device to finish the update."
else
  echo "The update did not finish. You can close this window and try again later."
fi
echo
read -r -p "Press Enter to close this window." _
"""


def _terminal_argv(script: str) -> list[str] | None:
    """Command line that opens a new terminal window running script, or None
    if no supported terminal is installed. Checked in order: Konsole (KDE,
    Bazzite's desktop), Ptyxis (GNOME images), xdg-terminal-exec (whatever
    the user set as default)."""
    inner = ["bash", "-c", script]
    if shutil.which("konsole"):
        return ["konsole", "-e", *inner]
    if shutil.which("ptyxis"):
        return ["ptyxis", "--", *inner]
    if shutil.which("xdg-terminal-exec"):
        return ["xdg-terminal-exec", *inner]
    return None


def system_update_command() -> list[str] | None:
    """argv that runs the system update in a visible terminal, or None when the
    tray cannot offer it (no `ujust`, i.e. not a Universal Blue image, or no
    terminal). Runs natively — the packaged tray is not in a container."""
    if not shutil.which("ujust"):
        return None
    return _terminal_argv(TERMINAL_SCRIPT)


def describe(argv: list[str]) -> str:
    return shlex.join(argv)
