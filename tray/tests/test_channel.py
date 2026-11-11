"""
test_channel.py — Tests for channel.py (packaged installs, Issue #78).

Covers:
  • enabled_channels: stable / beta / both / disabled / duplicate repo ids
  • compare_evr: RPM semantics incl. Release and epoch (python3-rpm and the
    `rpm --eval` Lua fallback)
  • newest_in_repo / newest_offered: repo metadata parsing, $releasever/$basearch
  • pending_package: staged deployment from rpm-ostree status --json
  • check: up to date / update available / restart required / errors
  • system_update_command: no ujust → None, no terminal → None, terminal order,
    never distrobox-host-exec / get.sh / install.sh

subprocess and urllib are mocked; nothing touches the network or the system.
"""

import gzip
import json
import os
import shutil
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import channel as ch
from channel import EVR

HAVE_PY_RPM = True
try:
    import rpm  # noqa: F401
except ImportError:
    HAVE_PY_RPM = False

STABLE_ID = "copr:copr.fedorainfracloud.org:phischx:Deckery"
BETA_ID   = "copr:copr.fedorainfracloud.org:phischx:Deckery-beta"


def _repo_file(d, filename, repo_id, enabled="1", project=None):
    project = project or repo_id.rsplit(":", 1)[1]
    (d / filename).write_text(
        f"[{repo_id}]\n"
        f"name=Copr repo for {project} owned by phischx\n"
        f"baseurl=https://download.copr.fedorainfracloud.org/results/phischx/"
        f"{project}/fedora-$releasever-$basearch/\n"
        "type=rpm-md\n"
        f"enabled={enabled}\n"
    )


# ── compare_evr ───────────────────────────────────────────────────────────────

def _lua_vercmp(argv, **kw):
    """Stand-in for `rpm --eval '%{lua: print(rpm.vercmp(a, b))}'`."""
    import re
    a, b = re.findall(r'"([^"]+)"', argv[2])
    def key(s):
        e, vr = s.split(":", 1)
        v, r = vr.rsplit("-", 1)
        return (int(e), [int(x) for x in v.split(".")], [int(x) for x in r.split(".fc")[0].split(".")])
    ka, kb = key(a), key(b)
    out = MagicMock(returncode=0, stderr="")
    out.stdout = "1\n" if ka > kb else "-1\n" if ka < kb else "0\n"
    return out


class TestCompareEvr:

    @pytest.fixture(params=["python-rpm", "lua"])
    def backend(self, request, monkeypatch):
        if request.param == "python-rpm":
            if not HAVE_PY_RPM:
                pytest.skip("python3-rpm not installed here")
        else:
            # Hide python3-rpm so the Lua fallback runs.
            monkeypatch.setitem(sys.modules, "rpm", None)
            monkeypatch.setattr(ch.subprocess, "run", _lua_vercmp)
        return request.param

    def test_release_matters(self, backend):
        assert ch.compare_evr(EVR("0", "0.5.0", "2.fc44"), EVR("0", "0.5.0", "3.fc44")) == -1

    def test_release_numeric_not_lexicographic(self, backend):
        assert ch.compare_evr(EVR("0", "0.5.0", "10.fc44"), EVR("0", "0.5.0", "9.fc44")) == 1

    def test_equal(self, backend):
        assert ch.compare_evr(EVR("0", "0.5.0", "2.fc44"), EVR("0", "0.5.0", "2.fc44")) == 0

    def test_version_beats_release(self, backend):
        assert ch.compare_evr(EVR("0", "0.6.0", "1.fc44"), EVR("0", "0.5.0", "9.fc44")) == 1

    def test_epoch_beats_version(self, backend):
        assert ch.compare_evr(EVR("1", "0.1.0", "1"), EVR("0", "0.9.0", "1")) == 1

    @pytest.mark.skipif(not HAVE_PY_RPM, reason="python3-rpm not installed here")
    def test_tilde_prerelease_sorts_before_release(self):
        assert ch.compare_evr(EVR("0", "0.6.0~rc1", "1"), EVR("0", "0.6.0", "1")) == -1

    def test_no_backend_raises(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "rpm", None)
        monkeypatch.setattr(ch.subprocess, "run",
                            MagicMock(return_value=MagicMock(returncode=1, stdout="", stderr="x")))
        with pytest.raises(RuntimeError):
            ch.compare_evr(EVR("0", "1", "1"), EVR("0", "1", "2"))


def test_display_version():
    inst = EVR("0", "0.5.0", "2.fc44")
    assert ch.display_version(EVR("0", "0.6.0", "1.fc44"), inst) == "0.6.0"
    assert ch.display_version(EVR("0", "0.5.0", "3.fc44"), inst) == "0.5.0-3"


# ── enabled_channels ──────────────────────────────────────────────────────────

class TestEnabledChannels:

    def test_stable(self, tmp_path):
        _repo_file(tmp_path, "_copr:copr.fedorainfracloud.org:phischx:Deckery.repo", STABLE_ID)
        assert list(ch.enabled_channels(str(tmp_path))) == ["stable"]

    def test_beta(self, tmp_path):
        _repo_file(tmp_path, "_copr:copr.fedorainfracloud.org:phischx:Deckery-beta.repo", BETA_ID)
        found = ch.enabled_channels(str(tmp_path))
        assert list(found) == ["beta"]
        assert "/Deckery-beta/fedora-$releasever-$basearch/" in found["beta"]

    def test_both(self, tmp_path):
        _repo_file(tmp_path, "a.repo", STABLE_ID)
        _repo_file(tmp_path, "b.repo", BETA_ID)
        assert set(ch.enabled_channels(str(tmp_path))) == {"stable", "beta"}

    def test_disabled_is_ignored(self, tmp_path):
        _repo_file(tmp_path, "a.repo", STABLE_ID, enabled="0")
        _repo_file(tmp_path, "b.repo", BETA_ID)
        assert list(ch.enabled_channels(str(tmp_path))) == ["beta"]

    def test_duplicate_id_counts_once_and_any_enabled_copy_wins(self, tmp_path):
        _repo_file(tmp_path, "a.repo", BETA_ID, enabled="0")
        _repo_file(tmp_path, "b.repo", BETA_ID, enabled="1")
        _repo_file(tmp_path, "c.repo", BETA_ID, enabled="1")
        assert list(ch.enabled_channels(str(tmp_path))) == ["beta"]

    def test_duplicate_section_in_one_file(self, tmp_path):
        (tmp_path / "x.repo").write_text(
            f"[{STABLE_ID}]\nbaseurl=https://a/\nenabled=1\n"
            f"[{STABLE_ID}]\nbaseurl=https://b/\nenabled=1\n")
        assert "stable" in ch.enabled_channels(str(tmp_path))

    def test_other_repos_and_none(self, tmp_path):
        _repo_file(tmp_path, "u.repo", "copr:copr.fedorainfracloud.org:ublue-os:bazzite")
        assert ch.enabled_channels(str(tmp_path)) == {}

    def test_missing_enabled_means_enabled(self, tmp_path):
        (tmp_path / "x.repo").write_text(f"[{STABLE_ID}]\nbaseurl=https://a/\n")
        assert ch.enabled_channels(str(tmp_path)) == {"stable": "https://a/"}

    def test_broken_file_is_skipped(self, tmp_path):
        (tmp_path / "bad.repo").write_text("this is not ini\n[")
        _repo_file(tmp_path, "b.repo", BETA_ID)
        assert list(ch.enabled_channels(str(tmp_path))) == ["beta"]


# ── Repo metadata ─────────────────────────────────────────────────────────────

REPOMD = b"""<?xml version="1.0" encoding="UTF-8"?>
<repomd xmlns="http://linux.duke.edu/metadata/repo">
  <data type="filelists"><location href="repodata/x-filelists.xml.gz"/></data>
  <data type="primary"><location href="repodata/abc-primary.xml.gz"/></data>
</repomd>"""


def _primary(*pkgs):
    body = "".join(
        f'<package type="rpm"><name>{n}</name><arch>{a}</arch>'
        f'<version epoch="{e}" ver="{v}" rel="{r}"/></package>'
        for n, a, e, v, r in pkgs)
    return gzip.compress(
        ('<?xml version="1.0"?><metadata xmlns="http://linux.duke.edu/metadata/common" '
         f'packages="{len(pkgs)}">{body}</metadata>').encode())


def _fake_fetch(repos: dict):
    """repos: {base url: primary bytes}. Records requested URLs."""
    seen = []
    def fetch(url):
        seen.append(url)
        for base, primary in repos.items():
            if url == base + "repodata/repomd.xml":
                return REPOMD
            if url == base + "repodata/abc-primary.xml.gz":
                return primary
        raise OSError(f"404 {url}")
    fetch.seen = seen
    return fetch


class TestNewestInRepo:

    def test_picks_newest_binary_build_by_release(self, monkeypatch):
        prim = _primary(
            ("deckery-tray", "noarch", "0", "0.5.0", "2.fc44"),
            ("deckery-tray", "src",    "0", "0.5.0", "9.fc44"),   # source rpm: ignored
            ("deckery-tray", "noarch", "0", "0.5.0", "3.fc44"),
            ("deckery-hud",  "x86_64", "0", "0.9.0", "1.fc44"),   # other package
            ("deckery-tray", "noarch", "0", "0.4.1", "1.fc44"),
        )
        monkeypatch.setattr(ch, "_fetch", _fake_fetch({"https://r/": prim}))
        assert ch.newest_in_repo("https://r", "deckery-tray") == EVR("0", "0.5.0", "3.fc44")

    def test_no_build_is_none(self, monkeypatch):
        monkeypatch.setattr(ch, "_fetch", _fake_fetch({"https://r/": _primary()}))
        assert ch.newest_in_repo("https://r/", "deckery-tray") is None

    def test_network_error_raises(self, monkeypatch):
        monkeypatch.setattr(ch, "_fetch", MagicMock(side_effect=OSError("offline")))
        with pytest.raises(OSError):
            ch.newest_in_repo("https://r/", "deckery-tray")


class TestNewestOffered:

    def _setup(self, tmp_path, monkeypatch, repos, beta=True, stable=True):
        if stable:
            _repo_file(tmp_path, "s.repo", STABLE_ID)
        if beta:
            _repo_file(tmp_path, "b.repo", BETA_ID)
        osr = tmp_path / "os-release"
        osr.write_text('NAME="Bazzite"\nVERSION_ID="44"\n')
        monkeypatch.setattr(ch.platform, "machine", lambda: "x86_64")
        fetch = _fake_fetch(repos)
        monkeypatch.setattr(ch, "_fetch", fetch)
        return str(tmp_path), str(osr), fetch

    BASE = "https://download.copr.fedorainfracloud.org/results/phischx/{}/fedora-44-x86_64/"

    def test_expands_releasever_and_basearch(self, tmp_path, monkeypatch):
        repos = {self.BASE.format("Deckery"):
                 _primary(("deckery-tray", "noarch", "0", "0.5.0", "2.fc44"))}
        d, osr, fetch = self._setup(tmp_path, monkeypatch, repos, beta=False)
        assert ch.newest_offered("deckery-tray", d, osr) == ("stable", EVR("0", "0.5.0", "2.fc44"))
        assert fetch.seen[0] == self.BASE.format("Deckery") + "repodata/repomd.xml"

    def test_beta_only(self, tmp_path, monkeypatch):
        repos = {self.BASE.format("Deckery-beta"):
                 _primary(("deckery-tray", "noarch", "0", "0.5.0", "3.fc44"))}
        d, osr, _ = self._setup(tmp_path, monkeypatch, repos, stable=False)
        assert ch.newest_offered("deckery-tray", d, osr) == ("beta", EVR("0", "0.5.0", "3.fc44"))

    def test_both_channels_take_the_newer(self, tmp_path, monkeypatch):
        repos = {
            self.BASE.format("Deckery"):      _primary(("deckery-tray", "noarch", "0", "0.5.0", "2.fc44")),
            self.BASE.format("Deckery-beta"): _primary(("deckery-tray", "noarch", "0", "0.5.0", "3.fc44")),
        }
        d, osr, _ = self._setup(tmp_path, monkeypatch, repos)
        assert ch.newest_offered("deckery-tray", d, osr) == ("beta", EVR("0", "0.5.0", "3.fc44"))

    def test_no_channel_is_none(self, tmp_path, monkeypatch):
        d, osr, fetch = self._setup(tmp_path, monkeypatch, {}, beta=False, stable=False)
        assert ch.newest_offered("deckery-tray", d, osr) is None
        assert fetch.seen == []


# ── Installed / pending ───────────────────────────────────────────────────────

def _proc(stdout="", returncode=0):
    return MagicMock(stdout=stdout, returncode=returncode, stderr="")


class TestInstalledPackage:

    def test_reads_owner(self):
        with patch.object(ch.subprocess, "run",
                          return_value=_proc("deckery-tray 0 0.5.0 2.fc44")) as run:
            assert ch.installed_package("/usr/lib/deckery/tray/updater.py") == \
                ("deckery-tray", EVR("0", "0.5.0", "2.fc44"))
        assert run.call_args[0][0][:2] == ["rpm", "-qf"]

    def test_not_owned(self):
        with patch.object(ch.subprocess, "run", return_value=_proc("not owned", 1)):
            assert ch.installed_package("/x") is None


def _status(*deployments):
    return json.dumps({"deployments": list(deployments)})


class TestPendingPackage:

    @pytest.fixture(autouse=True)
    def _has_rpm_ostree(self, monkeypatch):
        monkeypatch.setattr(ch.shutil, "which", lambda n: f"/usr/bin/{n}")

    def _run(self, status_json, db_out="", db_rc=0):
        def run(argv, **kw):
            if argv[:2] == ["rpm-ostree", "status"]:
                return _proc(status_json)
            if argv[:3] == ["rpm-ostree", "db", "list"]:
                assert argv[3] == "new"
                return _proc(db_out, db_rc)
            raise AssertionError(argv)
        return run

    def test_staged_deployment(self):
        st = _status({"checksum": "new", "booted": False, "staged": True},
                     {"checksum": "old", "booted": True})
        out = "ostree commit: new\n deckery-tray-0.5.0-3.fc44.noarch\n"
        with patch.object(ch.subprocess, "run", side_effect=self._run(st, out)):
            assert ch.pending_package("deckery-tray") == EVR("0", "0.5.0", "3.fc44")

    def test_epoch_in_nevra(self):
        st = _status({"checksum": "new", "booted": False}, {"checksum": "old", "booted": True})
        out = "ostree commit: new\n deckery-tray-1:0.5.0-3.fc44.noarch\n"
        with patch.object(ch.subprocess, "run", side_effect=self._run(st, out)):
            assert ch.pending_package("deckery-tray") == EVR("1", "0.5.0", "3.fc44")

    def test_nothing_pending(self):
        st = _status({"checksum": "old", "booted": True}, {"checksum": "older", "booted": False})
        with patch.object(ch.subprocess, "run", side_effect=self._run(st)):
            assert ch.pending_package("deckery-tray") is None

    def test_not_in_pending_deployment(self):
        st = _status({"checksum": "new", "booted": False}, {"checksum": "old", "booted": True})
        with patch.object(ch.subprocess, "run", side_effect=self._run(st, "ostree commit: new\n")):
            assert ch.pending_package("deckery-tray") is None

    def test_no_rpm_ostree(self, monkeypatch):
        monkeypatch.setattr(ch.shutil, "which", lambda n: None)
        with patch.object(ch.subprocess, "run") as run:
            assert ch.pending_package("deckery-tray") is None
        run.assert_not_called()

    def test_garbage_json(self):
        with patch.object(ch.subprocess, "run", return_value=_proc("{not json")):
            assert ch.pending_package("deckery-tray") is None


# ── check ─────────────────────────────────────────────────────────────────────

def _cmp(a, b):
    def k(e):
        return (int(e.epoch), [int(x) for x in e.version.split(".")],
                [int(x) for x in e.release.split(".fc")[0].split(".")])
    return (k(a) > k(b)) - (k(a) < k(b))


class TestCheck:

    INSTALLED = ("deckery-tray", EVR("0", "0.5.0", "2.fc44"))

    @pytest.fixture(autouse=True)
    def _cmp(self, monkeypatch):
        monkeypatch.setattr(ch, "compare_evr", _cmp)

    def _run(self, monkeypatch, offered, pending=None, installed=INSTALLED):
        monkeypatch.setattr(ch, "installed_package", lambda p: installed)
        monkeypatch.setattr(ch, "newest_offered", lambda n: offered)
        monkeypatch.setattr(ch, "pending_package", lambda n: pending)
        return ch.check("/usr/lib/deckery/tray/updater.py")

    def test_same_build_is_up_to_date(self, monkeypatch):
        r = self._run(monkeypatch, ("stable", EVR("0", "0.5.0", "2.fc44")))
        assert r == ch.Result("up_to_date", None)

    def test_newer_release_is_update(self, monkeypatch):
        r = self._run(monkeypatch, ("beta", EVR("0", "0.5.0", "3.fc44")))
        assert r == ch.Result("update_available", "0.5.0-3")

    def test_newer_version_is_update(self, monkeypatch):
        r = self._run(monkeypatch, ("stable", EVR("0", "0.6.0", "1.fc44")))
        assert r == ch.Result("update_available", "0.6.0")

    def test_channel_behind_installed_is_up_to_date(self, monkeypatch):
        # e.g. a git tag exists but the channel has not built it: no update.
        r = self._run(monkeypatch, ("stable", EVR("0", "0.4.1", "1.fc44")))
        assert r.status == "up_to_date"

    def test_downloaded_update_needs_restart(self, monkeypatch):
        r = self._run(monkeypatch, ("beta", EVR("0", "0.5.0", "3.fc44")),
                      pending=EVR("0", "0.5.0", "3.fc44"))
        assert r == ch.Result("restart_required", "0.5.0-3")

    def test_pending_older_than_offered_still_offers(self, monkeypatch):
        r = self._run(monkeypatch, ("beta", EVR("0", "0.6.0", "1.fc44")),
                      pending=EVR("0", "0.5.0", "3.fc44"))
        assert r == ch.Result("update_available", "0.6.0")

    def test_pending_same_as_booted_is_ignored(self, monkeypatch):
        r = self._run(monkeypatch, ("stable", EVR("0", "0.5.0", "2.fc44")),
                      pending=EVR("0", "0.5.0", "2.fc44"))
        assert r.status == "up_to_date"

    def test_no_channel_is_not_up_to_date(self, monkeypatch):
        assert self._run(monkeypatch, None) == ch.Result("no_channel", None)

    def test_unreadable_installed_version_raises(self, monkeypatch):
        with pytest.raises(RuntimeError):
            self._run(monkeypatch, None, installed=None)

    def test_network_error_propagates(self, monkeypatch):
        monkeypatch.setattr(ch, "installed_package", lambda p: self.INSTALLED)
        monkeypatch.setattr(ch, "newest_offered", MagicMock(side_effect=OSError("offline")))
        with pytest.raises(OSError):
            ch.check("/x")


# ── system_update_command ─────────────────────────────────────────────────────

class TestSystemUpdateCommand:

    def _which(self, *present):
        return lambda n: f"/usr/bin/{n}" if n in present else None

    def test_no_ujust_no_command(self, monkeypatch):
        monkeypatch.setattr(ch.shutil, "which", self._which("konsole", "ptyxis"))
        assert ch.system_update_command() is None

    def test_no_terminal_no_command(self, monkeypatch):
        monkeypatch.setattr(ch.shutil, "which", self._which("ujust"))
        assert ch.system_update_command() is None

    @pytest.mark.parametrize("present,first", [
        (("ujust", "konsole", "ptyxis", "xdg-terminal-exec"), ["konsole", "-e"]),
        (("ujust", "ptyxis", "xdg-terminal-exec"),            ["ptyxis", "--"]),
        (("ujust", "xdg-terminal-exec"),                      ["xdg-terminal-exec"]),
    ])
    def test_terminal_order(self, monkeypatch, present, first):
        monkeypatch.setattr(ch.shutil, "which", self._which(*present))
        argv = ch.system_update_command()
        assert argv[:len(first)] == first
        assert argv[len(first):len(first) + 2] == ["bash", "-c"]
        assert argv[-1] == ch.TERMINAL_SCRIPT

    def test_runs_ujust_update_natively(self, monkeypatch):
        monkeypatch.setattr(ch.shutil, "which", self._which("ujust", "konsole"))
        argv = ch.system_update_command()
        joined = " ".join(argv)
        assert "ujust update" in ch.TERMINAL_SCRIPT
        assert "distrobox-host-exec" not in joined
        assert "get.sh" not in joined and "install.sh" not in joined

    def test_script_keeps_window_open_and_mentions_restart(self):
        assert "read -r" in ch.TERMINAL_SCRIPT
        assert "Restart your device" in ch.TERMINAL_SCRIPT

    def test_script_is_valid_bash(self):
        bash = shutil.which("bash")
        if not bash:
            pytest.skip("no bash")
        r = subprocess.run([bash, "-n", "-c", ch.TERMINAL_SCRIPT],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
